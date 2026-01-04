"""User database for decks and collections."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

# Schema version for migrations
SCHEMA_VERSION = 7

SCHEMA_SQL = """
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

-- Decks table
CREATE TABLE IF NOT EXISTS decks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    format TEXT,
    commander TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_decks_name ON decks(name);
CREATE INDEX IF NOT EXISTS idx_decks_format ON decks(format);

-- Deck cards
-- board_type: 0=mainboard, 1=sideboard, 2=maybeboard (is_sideboard kept for backward compat)
CREATE TABLE IF NOT EXISTS deck_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    card_name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    is_sideboard INTEGER NOT NULL DEFAULT 0,
    is_maybeboard INTEGER NOT NULL DEFAULT 0,
    is_commander INTEGER NOT NULL DEFAULT 0,
    set_code TEXT,
    collector_number TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(deck_id, card_name, is_sideboard, is_maybeboard)
);

CREATE INDEX IF NOT EXISTS idx_deck_cards_deck ON deck_cards(deck_id);
CREATE INDEX IF NOT EXISTS idx_deck_cards_card ON deck_cards(card_name);

-- Deck tags for organization
CREATE TABLE IF NOT EXISTS deck_tags (
    deck_id INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    PRIMARY KEY (deck_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_deck_tags_tag ON deck_tags(tag);

-- Trigger to update updated_at on deck changes
CREATE TRIGGER IF NOT EXISTS update_deck_timestamp
AFTER UPDATE ON decks
BEGIN
    UPDATE decks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger to update deck timestamp when cards change
CREATE TRIGGER IF NOT EXISTS update_deck_on_card_change
AFTER INSERT ON deck_cards
BEGIN
    UPDATE decks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.deck_id;
END;

CREATE TRIGGER IF NOT EXISTS update_deck_on_card_update
AFTER UPDATE ON deck_cards
BEGIN
    UPDATE decks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.deck_id;
END;

CREATE TRIGGER IF NOT EXISTS update_deck_on_card_delete
AFTER DELETE ON deck_cards
BEGIN
    UPDATE decks SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.deck_id;
END;

-- Collection cards (user's owned cards inventory)
-- Each unique printing (card_name + set_code + collector_number) is stored separately
CREATE TABLE IF NOT EXISTS collection_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    foil_quantity INTEGER NOT NULL DEFAULT 0,
    set_code TEXT,
    collector_number TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(card_name, set_code, collector_number)
);

CREATE INDEX IF NOT EXISTS idx_collection_card ON collection_cards(card_name);
CREATE INDEX IF NOT EXISTS idx_collection_set ON collection_cards(set_code, collector_number);
CREATE INDEX IF NOT EXISTS idx_collection_added ON collection_cards(added_at DESC);

-- Trigger to update updated_at on collection changes
CREATE TRIGGER IF NOT EXISTS update_collection_timestamp
AFTER UPDATE ON collection_cards
BEGIN
    UPDATE collection_cards SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Price history for individual cards (tracks price changes over time)
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_name TEXT NOT NULL,
    set_code TEXT,
    collector_number TEXT,
    price_usd REAL,
    price_eur REAL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_price_history_card ON price_history(card_name);
CREATE INDEX IF NOT EXISTS idx_price_history_printing ON price_history(card_name, set_code, collector_number);
CREATE INDEX IF NOT EXISTS idx_price_history_date ON price_history(recorded_at DESC);

-- Collection value history (tracks total collection value over time)
CREATE TABLE IF NOT EXISTS collection_value_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total_value_usd REAL NOT NULL,
    total_value_eur REAL,
    card_count INTEGER NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_collection_value_date ON collection_value_history(recorded_at DESC);
"""


@dataclass
class DeckSummary:
    """Lightweight deck info for listing."""

    id: int
    name: str
    format: str | None
    card_count: int
    sideboard_count: int
    maybeboard_count: int
    commander: str | None
    updated_at: datetime


@dataclass
class DeckRow:
    """Full deck metadata."""

    id: int
    name: str
    format: str | None
    commander: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class DeckCardRow:
    """A card in a deck."""

    id: int
    deck_id: int
    card_name: str
    quantity: int
    is_sideboard: bool
    is_maybeboard: bool
    is_commander: bool
    set_code: str | None
    collector_number: str | None
    added_at: datetime


@dataclass
class CollectionCardRow:
    """A card in the user's collection."""

    id: int
    card_name: str
    quantity: int
    foil_quantity: int
    set_code: str | None
    collector_number: str | None
    added_at: datetime
    updated_at: datetime


@dataclass
class CollectionHistoryRow:
    """A history entry for collection changes."""

    id: int
    card_name: str
    action: str  # 'add', 'remove', 'update'
    quantity_change: int
    foil_quantity_change: int
    set_code: str | None
    collector_number: str | None
    created_at: datetime


class UserDatabase:
    """SQLite database for user data (decks, collections, etc.)."""

    def __init__(
        self,
        db_path: Path,
        max_connections: int = 5,
        semaphore: asyncio.Semaphore | None = None,
    ):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None
        # Use shared semaphore if provided, otherwise create our own
        self._semaphore = semaphore if semaphore is not None else asyncio.Semaphore(max_connections)

    @property
    def conn(self) -> aiosqlite.Connection:
        """Get the database connection."""
        if self._conn is None:
            raise RuntimeError("UserDatabase not connected. Call connect() first.")
        return self._conn

    @asynccontextmanager
    async def _execute(
        self, query: str, params: Sequence[Any] = ()
    ) -> AsyncIterator[aiosqlite.Cursor]:
        """Execute a query with concurrency limiting."""
        async with self._semaphore, self.conn.execute(query, params) as cursor:
            yield cursor

    async def connect(self) -> None:
        """Connect and initialize schema."""
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = await aiosqlite.connect(
            self.db_path,
            timeout=30.0,  # Increase timeout for concurrent access
            check_same_thread=False,  # Allow access from multiple async tasks
        )
        self._conn.row_factory = aiosqlite.Row

        # Enable WAL mode for better concurrent read/write performance
        await self._conn.execute("PRAGMA journal_mode = WAL")
        await self._conn.execute("PRAGMA synchronous = NORMAL")
        await self._conn.execute("PRAGMA busy_timeout = 10000")  # 10 seconds
        await self._conn.execute("PRAGMA foreign_keys = ON")

        await self._create_schema()
        logger.info("User database connected at %s", self.db_path)

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _create_schema(self) -> None:
        """Create tables if they don't exist."""
        await self.conn.executescript(SCHEMA_SQL)

        # Check current schema version
        async with self.conn.execute("SELECT version FROM schema_version LIMIT 1") as cursor:
            row = await cursor.fetchone()
            current_version = row["version"] if row else 0

        # Run migrations if needed
        if current_version < SCHEMA_VERSION:
            await self._run_migrations(current_version)

        # Set schema version if not exists, or update it
        if row is None:
            await self.conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,)
            )
        elif current_version < SCHEMA_VERSION:
            await self.conn.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))

        await self.conn.commit()

    async def _column_exists(self, table: str, column: str) -> bool:
        """Check if a column exists in a table."""
        async with self.conn.execute(f"PRAGMA table_info({table})") as cursor:
            rows = await cursor.fetchall()
            return any(row["name"] == column for row in rows)

    async def _add_column_if_missing(self, table: str, column: str, column_type: str) -> None:
        """Add a column to a table if it doesn't exist."""
        if not await self._column_exists(table, column):
            try:
                await self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
                logger.debug("Added column %s to table %s", column, table)
            except sqlite3.OperationalError as e:
                logger.warning("Failed to add column %s to %s: %s", column, table, e)
                raise

    async def _run_migrations(self, from_version: int) -> None:
        """Run database migrations."""
        if from_version < 2:
            # Migration 1 -> 2: Add set_code and collector_number to deck_cards
            logger.info("Running migration 1 -> 2: Adding printing columns to deck_cards")
            await self._add_column_if_missing("deck_cards", "set_code", "TEXT")
            await self._add_column_if_missing("deck_cards", "collector_number", "TEXT")
            logger.info("Migration 1 -> 2 complete")

        if from_version < 3:
            # Migration 2 -> 3: Add collection_cards table
            logger.info("Running migration 2 -> 3: Adding collection_cards table")
            await self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS collection_cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_name TEXT NOT NULL UNIQUE,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    foil_quantity INTEGER NOT NULL DEFAULT 0,
                    set_code TEXT,
                    collector_number TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_collection_card ON collection_cards(card_name);
                CREATE INDEX IF NOT EXISTS idx_collection_added ON collection_cards(added_at DESC);
                CREATE TRIGGER IF NOT EXISTS update_collection_timestamp
                AFTER UPDATE ON collection_cards
                BEGIN
                    UPDATE collection_cards SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END;
            """)
            logger.info("Migration 2 -> 3 complete")

        if from_version < 4:
            # Migration 3 -> 4: Add collection_history table
            logger.info("Running migration 3 -> 4: Adding collection_history table")
            await self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS collection_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity_change INTEGER NOT NULL DEFAULT 0,
                    foil_quantity_change INTEGER NOT NULL DEFAULT 0,
                    set_code TEXT,
                    collector_number TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_collection_history_card ON collection_history(card_name);
                CREATE INDEX IF NOT EXISTS idx_collection_history_action ON collection_history(action);
                CREATE INDEX IF NOT EXISTS idx_collection_history_date ON collection_history(created_at DESC);
            """)
            logger.info("Migration 3 -> 4 complete")

        if from_version < 5:
            # Migration 4 -> 5: Change unique constraint to include printing info
            # This allows tracking multiple printings of the same card separately
            logger.info(
                "Running migration 4 -> 5: Changing collection unique constraint to include printing"
            )
            await self.conn.executescript("""
                -- Create new table with correct unique constraint
                CREATE TABLE collection_cards_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    foil_quantity INTEGER NOT NULL DEFAULT 0,
                    set_code TEXT,
                    collector_number TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(card_name, set_code, collector_number)
                );

                -- Copy data from old table
                INSERT INTO collection_cards_new
                    (id, card_name, quantity, foil_quantity, set_code, collector_number, added_at, updated_at)
                SELECT id, card_name, quantity, foil_quantity, set_code, collector_number, added_at, updated_at
                FROM collection_cards;

                -- Drop old table and triggers
                DROP TRIGGER IF EXISTS update_collection_timestamp;
                DROP INDEX IF EXISTS idx_collection_card;
                DROP INDEX IF EXISTS idx_collection_added;
                DROP TABLE collection_cards;

                -- Rename new table
                ALTER TABLE collection_cards_new RENAME TO collection_cards;

                -- Recreate indexes and trigger
                CREATE INDEX idx_collection_card ON collection_cards(card_name);
                CREATE INDEX idx_collection_set ON collection_cards(set_code, collector_number);
                CREATE INDEX idx_collection_added ON collection_cards(added_at DESC);

                CREATE TRIGGER update_collection_timestamp
                AFTER UPDATE ON collection_cards
                BEGIN
                    UPDATE collection_cards SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END;
            """)
            logger.info("Migration 4 -> 5 complete")

        if from_version < 6:
            # Migration 5 -> 6: Add price history tables
            logger.info("Running migration 5 -> 6: Adding price history tables")
            await self.conn.executescript("""
                -- Price history for individual cards
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_name TEXT NOT NULL,
                    set_code TEXT,
                    collector_number TEXT,
                    price_usd REAL,
                    price_eur REAL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_price_history_card ON price_history(card_name);
                CREATE INDEX IF NOT EXISTS idx_price_history_printing ON price_history(card_name, set_code, collector_number);
                CREATE INDEX IF NOT EXISTS idx_price_history_date ON price_history(recorded_at DESC);

                -- Collection value history
                CREATE TABLE IF NOT EXISTS collection_value_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_value_usd REAL NOT NULL,
                    total_value_eur REAL,
                    card_count INTEGER NOT NULL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_collection_value_date ON collection_value_history(recorded_at DESC);
            """)
            logger.info("Migration 5 -> 6 complete")

        if from_version < 7:
            logger.info("Running migration 6 -> 7: Adding is_maybeboard column to deck_cards")
            # Add is_maybeboard column
            await self.conn.execute("""
                ALTER TABLE deck_cards ADD COLUMN is_maybeboard INTEGER NOT NULL DEFAULT 0
            """)
            # Recreate unique constraint to include is_maybeboard
            # SQLite doesn't support dropping constraints, so we need to recreate the table
            await self.conn.executescript("""
                -- Create new table with updated constraint
                CREATE TABLE deck_cards_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    deck_id INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
                    card_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    is_sideboard INTEGER NOT NULL DEFAULT 0,
                    is_maybeboard INTEGER NOT NULL DEFAULT 0,
                    is_commander INTEGER NOT NULL DEFAULT 0,
                    set_code TEXT,
                    collector_number TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(deck_id, card_name, is_sideboard, is_maybeboard)
                );

                -- Copy data
                INSERT INTO deck_cards_new (id, deck_id, card_name, quantity, is_sideboard, is_maybeboard, is_commander, set_code, collector_number, added_at)
                SELECT id, deck_id, card_name, quantity, is_sideboard, 0, is_commander, set_code, collector_number, added_at
                FROM deck_cards;

                -- Drop old table and rename
                DROP TABLE deck_cards;
                ALTER TABLE deck_cards_new RENAME TO deck_cards;

                -- Recreate indexes
                CREATE INDEX IF NOT EXISTS idx_deck_cards_deck ON deck_cards(deck_id);
                CREATE INDEX IF NOT EXISTS idx_deck_cards_card ON deck_cards(card_name);
            """)
            logger.info("Migration 6 -> 7 complete")

    # ─────────────────────────────────────────────────────────────────────────
    # Deck CRUD
    # ─────────────────────────────────────────────────────────────────────────

    async def create_deck(
        self,
        name: str,
        format: str | None = None,
        commander: str | None = None,
        description: str | None = None,
    ) -> int:
        """Create a new deck and return its ID."""
        async with self.conn.execute(
            """
            INSERT INTO decks (name, format, commander, description)
            VALUES (?, ?, ?, ?)
            """,
            (name, format, commander, description),
        ) as cursor:
            deck_id = cursor.lastrowid
        await self.conn.commit()
        return deck_id  # type: ignore

    async def get_deck(self, deck_id: int) -> DeckRow | None:
        """Get deck metadata by ID."""
        async with self.conn.execute("SELECT * FROM decks WHERE id = ?", (deck_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return DeckRow(
                id=row["id"],
                name=row["name"],
                format=row["format"],
                commander=row["commander"],
                description=row["description"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    async def get_deck_with_cards(self, deck_id: int) -> tuple[DeckRow | None, list[DeckCardRow]]:
        """Get deck metadata and all its cards in a single semaphore acquisition.

        More efficient than calling get_deck() + get_deck_cards() separately,
        especially under high concurrency. Reduces semaphore pressure by 50%.

        Returns:
            Tuple of (deck metadata, list of cards). If deck not found, returns (None, []).
        """
        async with self._semaphore:
            # Get deck metadata
            async with self.conn.execute("SELECT * FROM decks WHERE id = ?", (deck_id,)) as cursor:
                deck_row = await cursor.fetchone()
                if deck_row is None:
                    return None, []

            # Get cards
            async with self.conn.execute(
                """
                SELECT * FROM deck_cards
                WHERE deck_id = ?
                ORDER BY is_sideboard, card_name
                """,
                (deck_id,),
            ) as cursor:
                card_rows = await cursor.fetchall()

        deck = DeckRow(
            id=deck_row["id"],
            name=deck_row["name"],
            format=deck_row["format"],
            commander=deck_row["commander"],
            description=deck_row["description"],
            created_at=datetime.fromisoformat(deck_row["created_at"]),
            updated_at=datetime.fromisoformat(deck_row["updated_at"]),
        )

        cards = [
            DeckCardRow(
                id=row["id"],
                deck_id=row["deck_id"],
                card_name=row["card_name"],
                quantity=row["quantity"],
                is_sideboard=bool(row["is_sideboard"]),
                is_maybeboard=bool(row["is_maybeboard"]),
                is_commander=bool(row["is_commander"]),
                set_code=row["set_code"],
                collector_number=row["collector_number"],
                added_at=datetime.fromisoformat(row["added_at"]),
            )
            for row in card_rows
        ]

        return deck, cards

    async def list_decks(self) -> list[DeckSummary]:
        """List all decks with card counts."""
        query = """
        SELECT
            d.id,
            d.name,
            d.format,
            d.commander,
            d.updated_at,
            COALESCE(SUM(CASE WHEN dc.is_sideboard = 0 AND dc.is_maybeboard = 0 THEN dc.quantity ELSE 0 END), 0) as card_count,
            COALESCE(SUM(CASE WHEN dc.is_sideboard = 1 THEN dc.quantity ELSE 0 END), 0) as sideboard_count,
            COALESCE(SUM(CASE WHEN dc.is_maybeboard = 1 THEN dc.quantity ELSE 0 END), 0) as maybeboard_count
        FROM decks d
        LEFT JOIN deck_cards dc ON d.id = dc.deck_id
        GROUP BY d.id
        ORDER BY d.updated_at DESC
        """
        async with self.conn.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [
                DeckSummary(
                    id=row["id"],
                    name=row["name"],
                    format=row["format"],
                    card_count=row["card_count"],
                    sideboard_count=row["sideboard_count"],
                    maybeboard_count=row["maybeboard_count"],
                    commander=row["commander"],
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                for row in rows
            ]

    async def update_deck(
        self,
        deck_id: int,
        name: str | None = None,
        format: str | None = None,
        commander: str | None = None,
        description: str | None = None,
    ) -> None:
        """Update deck metadata."""
        updates: list[str] = []
        params: list[str | int] = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if format is not None:
            updates.append("format = ?")
            params.append(format)
        if commander is not None:
            updates.append("commander = ?")
            params.append(commander)
        if description is not None:
            updates.append("description = ?")
            params.append(description)

        if not updates:
            return

        params.append(deck_id)
        query = f"UPDATE decks SET {', '.join(updates)} WHERE id = ?"
        await self.conn.execute(query, params)
        await self.conn.commit()

    async def delete_deck(self, deck_id: int) -> bool:
        """Delete a deck and all its cards. Returns True if deck existed."""
        async with self.conn.execute("DELETE FROM decks WHERE id = ?", (deck_id,)) as cursor:
            deleted = cursor.rowcount > 0
        await self.conn.commit()
        return deleted

    # ─────────────────────────────────────────────────────────────────────────
    # Card Operations
    # ─────────────────────────────────────────────────────────────────────────

    async def add_card(
        self,
        deck_id: int,
        card_name: str,
        quantity: int = 1,
        sideboard: bool = False,
        maybeboard: bool = False,
        is_commander: bool = False,
        set_code: str | None = None,
        collector_number: str | None = None,
    ) -> None:
        """Add a card to a deck. If card exists, increases quantity and updates printing."""
        await self.conn.execute(
            """
            INSERT INTO deck_cards (deck_id, card_name, quantity, is_sideboard, is_maybeboard, is_commander, set_code, collector_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (deck_id, card_name, is_sideboard, is_maybeboard)
            DO UPDATE SET
                quantity = quantity + excluded.quantity,
                set_code = COALESCE(excluded.set_code, set_code),
                collector_number = COALESCE(excluded.collector_number, collector_number)
            """,
            (
                deck_id,
                card_name,
                quantity,
                int(sideboard),
                int(maybeboard),
                int(is_commander),
                set_code,
                collector_number,
            ),
        )
        await self.conn.commit()

    async def remove_card(
        self, deck_id: int, card_name: str, sideboard: bool = False, maybeboard: bool = False
    ) -> bool:
        """Remove a card entirely from a deck."""
        async with self.conn.execute(
            """
            DELETE FROM deck_cards
            WHERE deck_id = ? AND card_name = ? AND is_sideboard = ? AND is_maybeboard = ?
            """,
            (deck_id, card_name, int(sideboard), int(maybeboard)),
        ) as cursor:
            removed = cursor.rowcount > 0
        await self.conn.commit()
        return removed

    async def set_quantity(
        self,
        deck_id: int,
        card_name: str,
        quantity: int,
        sideboard: bool = False,
        maybeboard: bool = False,
    ) -> None:
        """Set the quantity of a card. If quantity is 0, removes the card."""
        if quantity <= 0:
            await self.remove_card(deck_id, card_name, sideboard, maybeboard)
            return

        await self.conn.execute(
            """
            UPDATE deck_cards
            SET quantity = ?
            WHERE deck_id = ? AND card_name = ? AND is_sideboard = ? AND is_maybeboard = ?
            """,
            (quantity, deck_id, card_name, int(sideboard), int(maybeboard)),
        )
        await self.conn.commit()

    async def move_to_sideboard(self, deck_id: int, card_name: str) -> None:
        """Move a card from mainboard to sideboard."""
        # Check if already in sideboard
        async with self.conn.execute(
            """
            SELECT quantity FROM deck_cards
            WHERE deck_id = ? AND card_name = ? AND is_sideboard = 1
            """,
            (deck_id, card_name),
        ) as cursor:
            existing = await cursor.fetchone()

        if existing:
            # Merge quantities
            await self.conn.execute(
                """
                UPDATE deck_cards
                SET quantity = quantity + (
                    SELECT quantity FROM deck_cards
                    WHERE deck_id = ? AND card_name = ? AND is_sideboard = 0
                )
                WHERE deck_id = ? AND card_name = ? AND is_sideboard = 1
                """,
                (deck_id, card_name, deck_id, card_name),
            )
            await self.conn.execute(
                """
                DELETE FROM deck_cards
                WHERE deck_id = ? AND card_name = ? AND is_sideboard = 0
                """,
                (deck_id, card_name),
            )
        else:
            # Just flip the flag
            await self.conn.execute(
                """
                UPDATE deck_cards
                SET is_sideboard = 1
                WHERE deck_id = ? AND card_name = ? AND is_sideboard = 0
                """,
                (deck_id, card_name),
            )
        await self.conn.commit()

    async def move_to_mainboard(self, deck_id: int, card_name: str) -> None:
        """Move a card from sideboard to mainboard."""
        # Check if already in mainboard
        async with self.conn.execute(
            """
            SELECT quantity FROM deck_cards
            WHERE deck_id = ? AND card_name = ? AND is_sideboard = 0
            """,
            (deck_id, card_name),
        ) as cursor:
            existing = await cursor.fetchone()

        if existing:
            # Merge quantities
            await self.conn.execute(
                """
                UPDATE deck_cards
                SET quantity = quantity + (
                    SELECT quantity FROM deck_cards
                    WHERE deck_id = ? AND card_name = ? AND is_sideboard = 1
                )
                WHERE deck_id = ? AND card_name = ? AND is_sideboard = 0
                """,
                (deck_id, card_name, deck_id, card_name),
            )
            await self.conn.execute(
                """
                DELETE FROM deck_cards
                WHERE deck_id = ? AND card_name = ? AND is_sideboard = 1
                """,
                (deck_id, card_name),
            )
        else:
            # Just flip the flag
            await self.conn.execute(
                """
                UPDATE deck_cards
                SET is_sideboard = 0
                WHERE deck_id = ? AND card_name = ? AND is_sideboard = 1
                """,
                (deck_id, card_name),
            )
        await self.conn.commit()

    async def move_card(
        self,
        deck_id: int,
        card_name: str,
        from_sideboard: bool,
        from_maybeboard: bool,
        to_sideboard: bool,
        to_maybeboard: bool,
    ) -> None:
        """Move a card between mainboard, sideboard, and maybeboard."""
        # Check if card already exists in target location
        async with self.conn.execute(
            """
            SELECT quantity FROM deck_cards
            WHERE deck_id = ? AND card_name = ? AND is_sideboard = ? AND is_maybeboard = ?
            """,
            (deck_id, card_name, int(to_sideboard), int(to_maybeboard)),
        ) as cursor:
            existing = await cursor.fetchone()

        if existing:
            # Merge quantities - add source quantity to target
            await self.conn.execute(
                """
                UPDATE deck_cards
                SET quantity = quantity + (
                    SELECT quantity FROM deck_cards
                    WHERE deck_id = ? AND card_name = ? AND is_sideboard = ? AND is_maybeboard = ?
                )
                WHERE deck_id = ? AND card_name = ? AND is_sideboard = ? AND is_maybeboard = ?
                """,
                (
                    deck_id,
                    card_name,
                    int(from_sideboard),
                    int(from_maybeboard),
                    deck_id,
                    card_name,
                    int(to_sideboard),
                    int(to_maybeboard),
                ),
            )
            # Delete source
            await self.conn.execute(
                """
                DELETE FROM deck_cards
                WHERE deck_id = ? AND card_name = ? AND is_sideboard = ? AND is_maybeboard = ?
                """,
                (deck_id, card_name, int(from_sideboard), int(from_maybeboard)),
            )
        else:
            # Just update the flags
            await self.conn.execute(
                """
                UPDATE deck_cards
                SET is_sideboard = ?, is_maybeboard = ?
                WHERE deck_id = ? AND card_name = ? AND is_sideboard = ? AND is_maybeboard = ?
                """,
                (
                    int(to_sideboard),
                    int(to_maybeboard),
                    deck_id,
                    card_name,
                    int(from_sideboard),
                    int(from_maybeboard),
                ),
            )
        await self.conn.commit()

    # ─────────────────────────────────────────────────────────────────────────
    # Queries
    # ─────────────────────────────────────────────────────────────────────────

    async def get_deck_cards(self, deck_id: int) -> list[DeckCardRow]:
        """Get all cards in a deck."""
        async with self.conn.execute(
            """
            SELECT * FROM deck_cards
            WHERE deck_id = ?
            ORDER BY is_maybeboard, is_sideboard, card_name
            """,
            (deck_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                DeckCardRow(
                    id=row["id"],
                    deck_id=row["deck_id"],
                    card_name=row["card_name"],
                    quantity=row["quantity"],
                    is_sideboard=bool(row["is_sideboard"]),
                    is_maybeboard=bool(row["is_maybeboard"]),
                    is_commander=bool(row["is_commander"]),
                    set_code=row["set_code"],
                    collector_number=row["collector_number"],
                    added_at=datetime.fromisoformat(row["added_at"]),
                )
                for row in rows
            ]

    async def find_decks_with_card(self, card_name: str) -> list[DeckSummary]:
        """Find all decks containing a specific card."""
        query = """
        SELECT DISTINCT
            d.id,
            d.name,
            d.format,
            d.commander,
            d.updated_at,
            COALESCE(SUM(CASE WHEN dc2.is_sideboard = 0 AND dc2.is_maybeboard = 0 THEN dc2.quantity ELSE 0 END), 0) as card_count,
            COALESCE(SUM(CASE WHEN dc2.is_sideboard = 1 THEN dc2.quantity ELSE 0 END), 0) as sideboard_count,
            COALESCE(SUM(CASE WHEN dc2.is_maybeboard = 1 THEN dc2.quantity ELSE 0 END), 0) as maybeboard_count
        FROM decks d
        JOIN deck_cards dc ON d.id = dc.deck_id AND dc.card_name = ?
        LEFT JOIN deck_cards dc2 ON d.id = dc2.deck_id
        GROUP BY d.id
        ORDER BY d.updated_at DESC
        """
        async with self.conn.execute(query, (card_name,)) as cursor:
            rows = await cursor.fetchall()
            return [
                DeckSummary(
                    id=row["id"],
                    name=row["name"],
                    format=row["format"],
                    card_count=row["card_count"],
                    sideboard_count=row["sideboard_count"],
                    maybeboard_count=row["maybeboard_count"],
                    commander=row["commander"],
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                for row in rows
            ]

    async def get_deck_card_count(self, deck_id: int, card_name: str) -> int:
        """Get total quantity of a card in a deck (mainboard + sideboard)."""
        async with self.conn.execute(
            """
            SELECT COALESCE(SUM(quantity), 0) as total
            FROM deck_cards
            WHERE deck_id = ? AND card_name = ?
            """,
            (deck_id, card_name),
        ) as cursor:
            row = await cursor.fetchone()
            return row["total"] if row else 0

    # ─────────────────────────────────────────────────────────────────────────
    # Tags
    # ─────────────────────────────────────────────────────────────────────────

    async def add_tag(self, deck_id: int, tag: str) -> None:
        """Add a tag to a deck."""
        await self.conn.execute(
            "INSERT OR IGNORE INTO deck_tags (deck_id, tag) VALUES (?, ?)",
            (deck_id, tag),
        )
        await self.conn.commit()

    async def remove_tag(self, deck_id: int, tag: str) -> None:
        """Remove a tag from a deck."""
        await self.conn.execute(
            "DELETE FROM deck_tags WHERE deck_id = ? AND tag = ?",
            (deck_id, tag),
        )
        await self.conn.commit()

    async def get_deck_tags(self, deck_id: int) -> list[str]:
        """Get all tags for a deck."""
        async with self.conn.execute(
            "SELECT tag FROM deck_tags WHERE deck_id = ? ORDER BY tag",
            (deck_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [row["tag"] for row in rows]

    async def find_decks_by_tag(self, tag: str) -> list[DeckSummary]:
        """Find all decks with a specific tag."""
        query = """
        SELECT
            d.id,
            d.name,
            d.format,
            d.commander,
            d.updated_at,
            COALESCE(SUM(CASE WHEN dc.is_sideboard = 0 AND dc.is_maybeboard = 0 THEN dc.quantity ELSE 0 END), 0) as card_count,
            COALESCE(SUM(CASE WHEN dc.is_sideboard = 1 THEN dc.quantity ELSE 0 END), 0) as sideboard_count,
            COALESCE(SUM(CASE WHEN dc.is_maybeboard = 1 THEN dc.quantity ELSE 0 END), 0) as maybeboard_count
        FROM decks d
        JOIN deck_tags dt ON d.id = dt.deck_id AND dt.tag = ?
        LEFT JOIN deck_cards dc ON d.id = dc.deck_id
        GROUP BY d.id
        ORDER BY d.updated_at DESC
        """
        async with self.conn.execute(query, (tag,)) as cursor:
            rows = await cursor.fetchall()
            return [
                DeckSummary(
                    id=row["id"],
                    name=row["name"],
                    format=row["format"],
                    card_count=row["card_count"],
                    sideboard_count=row["sideboard_count"],
                    maybeboard_count=row["maybeboard_count"],
                    commander=row["commander"],
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                for row in rows
            ]

    # ─────────────────────────────────────────────────────────────────────────
    # Collection
    # ─────────────────────────────────────────────────────────────────────────

    async def _log_collection_history(
        self,
        card_name: str,
        action: str,
        quantity_change: int = 0,
        foil_quantity_change: int = 0,
        set_code: str | None = None,
        collector_number: str | None = None,
    ) -> None:
        """Log a collection change to history."""
        await self.conn.execute(
            """
            INSERT INTO collection_history
            (card_name, action, quantity_change, foil_quantity_change, set_code, collector_number)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (card_name, action, quantity_change, foil_quantity_change, set_code, collector_number),
        )

    async def add_to_collection(
        self,
        card_name: str,
        quantity: int = 1,
        foil_quantity: int = 0,
        set_code: str | None = None,
        collector_number: str | None = None,
    ) -> None:
        """Add a card to the collection. If same printing exists, increases quantity."""
        await self.conn.execute(
            """
            INSERT INTO collection_cards (card_name, quantity, foil_quantity, set_code, collector_number)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (card_name, set_code, collector_number)
            DO UPDATE SET
                quantity = quantity + excluded.quantity,
                foil_quantity = foil_quantity + excluded.foil_quantity
            """,
            (card_name, quantity, foil_quantity, set_code, collector_number),
        )
        # Log history
        await self._log_collection_history(
            card_name, "add", quantity, foil_quantity, set_code, collector_number
        )
        await self.conn.commit()

    async def add_to_collection_batch(
        self,
        cards: list[tuple[str, int, int, str | None, str | None]],
    ) -> int:
        """Add multiple cards to the collection in a single transaction.

        Args:
            cards: List of (card_name, quantity, foil_quantity, set_code, collector_number) tuples

        Returns:
            Number of cards processed
        """
        if not cards:
            return 0

        await self.conn.executemany(
            """
            INSERT INTO collection_cards (card_name, quantity, foil_quantity, set_code, collector_number)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (card_name, set_code, collector_number)
            DO UPDATE SET
                quantity = quantity + excluded.quantity,
                foil_quantity = foil_quantity + excluded.foil_quantity
            """,
            cards,
        )
        await self.conn.commit()
        return len(cards)

    async def remove_from_collection(
        self,
        card_name: str,
        set_code: str | None = None,
        collector_number: str | None = None,
    ) -> bool:
        """Remove a card from the collection.

        If set_code and collector_number are provided, removes that specific printing.
        Otherwise removes all printings of the card.
        """
        # Build query based on whether we have printing info
        if set_code is not None and collector_number is not None:
            where_clause = "WHERE card_name = ? AND set_code = ? AND collector_number = ?"
            params: tuple[str, ...] = (card_name, set_code, collector_number)
        else:
            where_clause = "WHERE card_name = ?"
            params = (card_name,)

        # Get current quantities for history before deleting
        async with self.conn.execute(
            f"SELECT quantity, foil_quantity, set_code, collector_number FROM collection_cards {where_clause}",
            params,
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return False

        async with self.conn.execute(
            f"DELETE FROM collection_cards {where_clause}",
            params,
        ) as cursor:
            removed = cursor.rowcount > 0

        if removed:
            # Log history with negative quantities for each row deleted
            for row in rows:
                await self._log_collection_history(
                    card_name,
                    "remove",
                    -row["quantity"],
                    -row["foil_quantity"],
                    row["set_code"],
                    row["collector_number"],
                )
        await self.conn.commit()
        return removed

    async def set_collection_quantity(
        self,
        card_name: str,
        quantity: int,
        foil_quantity: int = 0,
        set_code: str | None = None,
        collector_number: str | None = None,
    ) -> None:
        """Set the quantity of a card in collection. Removes if both are 0.

        Args:
            card_name: The card name
            quantity: Non-foil quantity
            foil_quantity: Foil quantity
            set_code: Set code for specific printing (required for targeting)
            collector_number: Collector number for specific printing (required for targeting)
        """
        total = quantity + foil_quantity
        if total <= 0:
            await self.remove_from_collection(card_name, set_code, collector_number)
            return

        # Build query based on whether we have printing info
        if set_code is not None and collector_number is not None:
            where_clause = "WHERE card_name = ? AND set_code = ? AND collector_number = ?"
            select_params: tuple[str, ...] = (card_name, set_code, collector_number)
            update_params: tuple[int | str, ...] = (
                quantity,
                foil_quantity,
                card_name,
                set_code,
                collector_number,
            )
        else:
            where_clause = "WHERE card_name = ?"
            select_params = (card_name,)
            update_params = (quantity, foil_quantity, card_name)

        # Get old quantities for history
        async with self.conn.execute(
            f"SELECT quantity, foil_quantity, set_code, collector_number FROM collection_cards {where_clause}",
            select_params,
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return

        old_qty = row["quantity"]
        old_foil = row["foil_quantity"]
        row_set_code = row["set_code"]
        row_collector_number = row["collector_number"]

        await self.conn.execute(
            f"""
            UPDATE collection_cards
            SET quantity = ?, foil_quantity = ?
            {where_clause}
            """,
            update_params,
        )

        # Log history with the change (can be negative if reducing)
        qty_change = quantity - old_qty
        foil_change = foil_quantity - old_foil
        if qty_change != 0 or foil_change != 0:
            await self._log_collection_history(
                card_name, "update", qty_change, foil_change, row_set_code, row_collector_number
            )
        await self.conn.commit()

    async def get_collection_card_printings(
        self,
        card_name: str,
    ) -> list[CollectionCardRow]:
        """Get all printings of a card in the collection."""
        async with self.conn.execute(
            """
            SELECT * FROM collection_cards
            WHERE card_name = ?
            ORDER BY set_code, collector_number
            """,
            (card_name,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                CollectionCardRow(
                    id=row["id"],
                    card_name=row["card_name"],
                    quantity=row["quantity"],
                    foil_quantity=row["foil_quantity"],
                    set_code=row["set_code"],
                    collector_number=row["collector_number"],
                    added_at=datetime.fromisoformat(row["added_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                for row in rows
            ]

    async def update_collection_printing(
        self,
        card_name: str,
        set_code: str,
        collector_number: str,
    ) -> bool:
        """Update the printing (set/number) for a card in the collection.

        Updates the first entry for the card that has no printing set,
        or the first entry if all have printings.

        Args:
            card_name: The card name
            set_code: New set code
            collector_number: New collector number

        Returns:
            True if updated, False if card not found
        """
        # Find a card entry to update (prefer ones without printing set)
        async with self.conn.execute(
            """
            SELECT id FROM collection_cards
            WHERE card_name = ?
            ORDER BY (set_code IS NULL) DESC, id ASC
            LIMIT 1
            """,
            (card_name,),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return False

        card_id = row["id"]
        await self.conn.execute(
            """
            UPDATE collection_cards
            SET set_code = ?, collector_number = ?, updated_at = ?
            WHERE id = ?
            """,
            (set_code, collector_number, datetime.now(UTC).isoformat(), card_id),
        )
        await self.conn.commit()
        return True

    async def get_collection_card(
        self,
        card_name: str,
        set_code: str | None = None,
        collector_number: str | None = None,
    ) -> CollectionCardRow | None:
        """Get a card from the collection.

        If set_code and collector_number are provided, returns that specific printing.
        Otherwise returns the first printing found (for backwards compatibility).
        """
        if set_code is not None and collector_number is not None:
            query = "SELECT * FROM collection_cards WHERE card_name = ? AND set_code = ? AND collector_number = ?"
            params: tuple[str, ...] = (card_name, set_code, collector_number)
        else:
            query = "SELECT * FROM collection_cards WHERE card_name = ? LIMIT 1"
            params = (card_name,)

        async with self.conn.execute(query, params) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return CollectionCardRow(
                id=row["id"],
                card_name=row["card_name"],
                quantity=row["quantity"],
                foil_quantity=row["foil_quantity"],
                set_code=row["set_code"],
                collector_number=row["collector_number"],
                added_at=datetime.fromisoformat(row["added_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    async def get_collection_cards(
        self,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "name",
        sort_order: str = "asc",
        mtg_db_path: Path | None = None,
        gameplay_db_path: Path | None = None,
    ) -> list[CollectionCardRow]:
        """Get cards from the collection with sorting and pagination.

        Args:
            limit: Maximum number of cards to return
            offset: Number of cards to skip
            sort_by: Field to sort by. Fast fields: name, dateAdded, quantity, setCode.
                     Metadata fields (require mtg_db_path): price, rarity, cmc, type, color.
                     17Lands fields (require gameplay_db_path): winRate, tier, draftPick.
            sort_order: Sort order (asc or desc)
            mtg_db_path: Path to mtg.sqlite for metadata sorts
            gameplay_db_path: Path to gameplay.duckdb for 17Lands sorts

        Returns:
            List of CollectionCardRow objects
        """
        # Fast fields that only use the collection table
        fast_fields = {"name", "dateAdded", "quantity", "setCode"}

        # Metadata fields that require card metadata lookup
        metadata_fields = {"price", "rarity", "cmc", "type", "color"}

        # 17Lands fields that require gameplay database lookup
        gameplay_fields = {"winRate", "tier", "draftPick"}

        order_dir = "ASC" if sort_order == "asc" else "DESC"
        reverse = order_dir == "DESC"

        # Fast path: collection-only fields (use SQL sorting)
        if sort_by in fast_fields:
            order_clause = self._get_fast_sort_clause(sort_by, order_dir)
            async with self.conn.execute(
                f"""
                SELECT * FROM collection_cards
                ORDER BY {order_clause}, card_name ASC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ) as cursor:
                rows = list(await cursor.fetchall())
                return self._rows_to_collection_cards(rows)

        # Metadata path: fetch all cards, lookup metadata, sort in Python
        if sort_by in metadata_fields:
            return await self._get_collection_with_metadata_sort(
                limit, offset, sort_by, reverse, mtg_db_path
            )

        # 17Lands path: fetch all cards, lookup gameplay stats, sort in Python
        if sort_by in gameplay_fields:
            return await self._get_collection_with_gameplay_sort(
                limit, offset, sort_by, reverse, gameplay_db_path
            )

        # Default: sort by name
        async with self.conn.execute(
            """
            SELECT * FROM collection_cards
            ORDER BY card_name ASC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ) as cursor:
            rows = list(await cursor.fetchall())
            return self._rows_to_collection_cards(rows)

    async def _get_collection_with_metadata_sort(
        self,
        limit: int,
        offset: int,
        sort_by: str,
        reverse: bool,
        mtg_db_path: Path | None,
    ) -> list[CollectionCardRow]:
        """Sort collection by card metadata (price, rarity, cmc, type, color).

        Fetches all collection cards, looks up metadata from mtg.sqlite,
        sorts in Python, then applies pagination.
        """
        import sqlite3

        # Fetch all collection cards
        async with self.conn.execute("SELECT * FROM collection_cards ORDER BY card_name") as cursor:
            rows = list(await cursor.fetchall())

        if not rows:
            return []

        cards = self._rows_to_collection_cards(rows)

        # If no mtg database, fall back to name sort
        if mtg_db_path is None or not mtg_db_path.exists():
            sorted_cards = sorted(cards, key=lambda c: c.card_name.lower(), reverse=reverse)
            return sorted_cards[offset : offset + limit]

        # Build lookup of card metadata from mtg.sqlite
        # Use sync sqlite3 since we're doing a simple read
        card_names = list({c.card_name for c in cards})

        metadata: dict[str, dict[str, Any]] = {}
        try:
            mtg_conn = sqlite3.connect(str(mtg_db_path))
            mtg_conn.row_factory = sqlite3.Row
            mtg_cursor = mtg_conn.cursor()

            # Query metadata for all card names
            placeholders = ", ".join(["?"] * len(card_names))
            mtg_cursor.execute(
                f"""
                SELECT name, set_code, cmc, rarity, type_line, colors, price_usd
                FROM cards
                WHERE name IN ({placeholders})
                """,
                card_names,
            )

            for row in mtg_cursor.fetchall():
                key = row["name"].lower()
                # Store first match per card name (or could match by set_code too)
                if key not in metadata:
                    metadata[key] = {
                        "cmc": row["cmc"],
                        "rarity": row["rarity"],
                        "type": row["type_line"],
                        "colors": row["colors"],
                        "price": row["price_usd"],
                    }

            mtg_conn.close()
        except Exception:
            # If metadata lookup fails, fall back to name sort
            sorted_cards = sorted(cards, key=lambda c: c.card_name.lower(), reverse=reverse)
            return sorted_cards[offset : offset + limit]

        # Define sort key based on sort_by field
        rarity_order = {"mythic": 4, "rare": 3, "uncommon": 2, "common": 1}

        def get_sort_key(card: CollectionCardRow) -> tuple[Any, str]:
            meta = metadata.get(card.card_name.lower(), {})
            secondary = card.card_name.lower()

            if sort_by == "price":
                price = meta.get("price")
                # NULLS LAST for DESC, NULLS FIRST for ASC
                if price is None:
                    return (float("-inf") if reverse else float("inf"), secondary)
                return (float(price), secondary)

            elif sort_by == "rarity":
                rarity = meta.get("rarity", "").lower()
                return (rarity_order.get(rarity, 0), secondary)

            elif sort_by == "cmc":
                cmc = meta.get("cmc")
                if cmc is None:
                    return (float("inf") if not reverse else float("-inf"), secondary)
                return (float(cmc), secondary)

            elif sort_by == "type":
                type_line = meta.get("type") or ""
                return (type_line.lower(), secondary)

            elif sort_by == "color":
                colors = meta.get("colors") or "[]"
                return (self._color_sort_value(colors), secondary)

            return (secondary, secondary)

        sorted_cards = sorted(cards, key=get_sort_key, reverse=reverse)
        return sorted_cards[offset : offset + limit]

    async def _get_collection_with_gameplay_sort(
        self,
        limit: int,
        offset: int,
        sort_by: str,
        reverse: bool,
        gameplay_db_path: Path | None,
    ) -> list[CollectionCardRow]:
        """Sort collection by 17Lands gameplay stats (winRate, tier, draftPick).

        Fetches all collection cards, looks up gameplay stats from DuckDB,
        sorts in Python, then applies pagination.
        """
        # Fetch all collection cards
        async with self.conn.execute("SELECT * FROM collection_cards ORDER BY card_name") as cursor:
            rows = list(await cursor.fetchall())

        if not rows:
            return []

        cards = self._rows_to_collection_cards(rows)

        # If no gameplay database, fall back to name sort
        if gameplay_db_path is None or not gameplay_db_path.exists():
            sorted_cards = sorted(cards, key=lambda c: c.card_name.lower(), reverse=reverse)
            return sorted_cards[offset : offset + limit]

        # Build lookup of gameplay stats from gameplay.duckdb
        card_names = list({c.card_name for c in cards})

        stats: dict[str, dict[str, Any]] = {}
        try:
            import duckdb

            conn = duckdb.connect(str(gameplay_db_path), read_only=True)

            # Query stats for all card names - join card_stats with draft_stats for ATA
            placeholders = ", ".join(["?"] * len(card_names))
            result = conn.execute(
                f"""
                SELECT cs.card_name, cs.gih_wr, cs.tier, ds.ata
                FROM card_stats cs
                LEFT JOIN draft_stats ds ON cs.card_name = ds.card_name AND cs.set_code = ds.set_code
                WHERE cs.card_name IN ({placeholders})
                """,
                card_names,
            ).fetchall()

            for row in result:
                name, gih_wr, tier, ata = row
                key = name.lower()
                # Store first match per card name (prefer rows with ATA data)
                if key not in stats or (ata is not None and stats[key].get("draftPick") is None):
                    stats[key] = {
                        "winRate": gih_wr,
                        "tier": tier,
                        "draftPick": ata,
                    }

            conn.close()
        except Exception:
            # If gameplay lookup fails, fall back to name sort
            sorted_cards = sorted(cards, key=lambda c: c.card_name.lower(), reverse=reverse)
            return sorted_cards[offset : offset + limit]

        # Define tier order (S > A > B > C > D > F > None)
        tier_order = {"S": 6, "A": 5, "B": 4, "C": 3, "D": 2, "F": 1}

        def get_sort_key(card: CollectionCardRow) -> tuple[Any, ...]:
            stat = stats.get(card.card_name.lower(), {})
            secondary = card.card_name.lower()

            if sort_by == "winRate":
                win_rate = stat.get("winRate")
                # Cards with data first (0), cards without data last (1)
                if win_rate is None:
                    return (1, 0.0, secondary)
                return (0, float(win_rate), secondary)

            elif sort_by == "tier":
                tier = stat.get("tier")
                # Cards with data first (0), cards without data last (1)
                if tier is None:
                    return (1, 0, secondary)
                return (0, tier_order.get(tier, 0), secondary)

            elif sort_by == "draftPick":
                ata = stat.get("draftPick")
                # Cards with data first (0), cards without data last (1)
                if ata is None:
                    return (1, 0.0, secondary)
                return (0, float(ata), secondary)

            return (0, secondary, secondary)

        # Sort with custom key - the first tuple element (has_data flag) should always
        # sort ascending (0 before 1) so cards with data come first, while the second
        # element (actual value) respects the reverse flag
        def sort_key_with_nulls_last(card: CollectionCardRow) -> tuple[Any, ...]:
            key = get_sort_key(card)
            has_data, value, name = key
            # If reverse (DESC), negate the value so higher values come first,
            # but keep has_data as-is so cards with data always come first
            if reverse:
                if isinstance(value, (int, float)):
                    return (has_data, -value, name)
                return (has_data, value, name)
            return key

        sorted_cards = sorted(cards, key=sort_key_with_nulls_last)
        return sorted_cards[offset : offset + limit]

    def _color_sort_value(self, colors_json: str) -> int:
        """Get sort value for colors (WUBRG order, colorless last, multicolor after)."""
        if not colors_json or colors_json == "[]":
            return 6  # Colorless

        # Check for mono-colors in WUBRG order
        is_w = '"W"' in colors_json
        is_u = '"U"' in colors_json
        is_b = '"B"' in colors_json
        is_r = '"R"' in colors_json
        is_g = '"G"' in colors_json

        if is_w and not is_u and not is_b and not is_r and not is_g:
            return 1
        if is_u and not is_w and not is_b and not is_r and not is_g:
            return 2
        if is_b and not is_w and not is_u and not is_r and not is_g:
            return 3
        if is_r and not is_w and not is_u and not is_b and not is_g:
            return 4
        if is_g and not is_w and not is_u and not is_b and not is_r:
            return 5
        return 7  # Multicolor

    def _get_fast_sort_clause(self, sort_by: str, order_dir: str) -> str:
        """Get ORDER BY clause for fast (collection-only) sorts."""
        clauses = {
            "name": f"card_name {order_dir}",
            "dateAdded": f"added_at {order_dir}",
            "quantity": f"(quantity + foil_quantity) {order_dir}",
            "setCode": f"set_code {order_dir}",
        }
        return clauses.get(sort_by, f"card_name {order_dir}")

    def _rows_to_collection_cards(self, rows: Sequence[aiosqlite.Row]) -> list[CollectionCardRow]:
        """Convert database rows to CollectionCardRow objects."""
        return [
            CollectionCardRow(
                id=row["id"],
                card_name=row["card_name"],
                quantity=row["quantity"],
                foil_quantity=row["foil_quantity"],
                set_code=row["set_code"],
                collector_number=row["collector_number"],
                added_at=datetime.fromisoformat(row["added_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]

    async def get_collection_count(self) -> int:
        """Get total number of unique cards in collection."""
        async with self.conn.execute("SELECT COUNT(*) as count FROM collection_cards") as cursor:
            row = await cursor.fetchone()
            return row["count"] if row else 0

    async def get_collection_card_names(self) -> set[str]:
        """Get all card names in the collection (lightweight query)."""
        async with self.conn.execute("SELECT card_name FROM collection_cards") as cursor:
            rows = await cursor.fetchall()
            return {row["card_name"] for row in rows}

    async def get_collection_total_cards(self) -> int:
        """Get total number of cards (including quantities) in collection."""
        async with self.conn.execute(
            "SELECT COALESCE(SUM(quantity + foil_quantity), 0) as total FROM collection_cards"
        ) as cursor:
            row = await cursor.fetchone()
            return row["total"] if row else 0

    async def get_collection_foil_total(self) -> int:
        """Get total number of foil cards in collection (efficient query)."""
        async with self.conn.execute(
            "SELECT COALESCE(SUM(foil_quantity), 0) as total FROM collection_cards"
        ) as cursor:
            row = await cursor.fetchone()
            return row["total"] if row else 0

    async def get_card_deck_usage(self, card_name: str) -> list[tuple[str, int]]:
        """Get all decks that use a card and how many copies.

        Returns list of (deck_name, quantity) tuples.
        """
        async with self.conn.execute(
            """
            SELECT d.name, SUM(dc.quantity) as qty
            FROM deck_cards dc
            JOIN decks d ON dc.deck_id = d.id
            WHERE dc.card_name = ?
            GROUP BY d.id
            ORDER BY d.name
            """,
            (card_name,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [(row["name"], row["qty"]) for row in rows]

    async def get_card_total_deck_usage(self, card_name: str) -> int:
        """Get total copies of a card used across all decks."""
        async with self.conn.execute(
            """
            SELECT COALESCE(SUM(quantity), 0) as total
            FROM deck_cards
            WHERE card_name = ?
            """,
            (card_name,),
        ) as cursor:
            row = await cursor.fetchone()
            return row["total"] if row else 0

    async def get_cards_deck_usage_batch(
        self, card_names: list[str]
    ) -> dict[str, list[tuple[str, int]]]:
        """Get deck usage for multiple cards in a single query.

        Returns dict mapping card_name -> [(deck_name, quantity), ...]
        """
        if not card_names:
            return {}

        placeholders = ",".join("?" * len(card_names))
        async with self.conn.execute(
            f"""
            SELECT dc.card_name, d.name as deck_name, SUM(dc.quantity) as qty
            FROM deck_cards dc
            JOIN decks d ON dc.deck_id = d.id
            WHERE dc.card_name IN ({placeholders})
            GROUP BY dc.card_name, d.id
            ORDER BY dc.card_name, d.name
            """,
            card_names,
        ) as cursor:
            rows = await cursor.fetchall()

        # Group by card name
        result: dict[str, list[tuple[str, int]]] = {name: [] for name in card_names}
        for row in rows:
            card_name = row["card_name"]
            if card_name in result:
                result[card_name].append((row["deck_name"], row["qty"]))

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Collection History
    # ─────────────────────────────────────────────────────────────────────────

    async def get_collection_history(
        self,
        limit: int = 50,
        offset: int = 0,
        action: str | None = None,
    ) -> list[CollectionHistoryRow]:
        """Get collection history entries.

        Args:
            limit: Maximum number of entries to return
            offset: Offset for pagination
            action: Filter by action type ('add', 'remove', 'update'), or None for all

        Returns:
            List of history entries, most recent first
        """
        params: tuple[str, int, int] | tuple[int, int]
        if action:
            query = """
                SELECT * FROM collection_history
                WHERE action = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            params = (action, limit, offset)
        else:
            query = """
                SELECT * FROM collection_history
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            params = (limit, offset)

        async with self.conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [
                CollectionHistoryRow(
                    id=row["id"],
                    card_name=row["card_name"],
                    action=row["action"],
                    quantity_change=row["quantity_change"],
                    foil_quantity_change=row["foil_quantity_change"],
                    set_code=row["set_code"],
                    collector_number=row["collector_number"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                for row in rows
            ]

    async def get_recent_removals(self, limit: int = 20) -> list[CollectionHistoryRow]:
        """Get recently removed cards from collection.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of removal history entries, most recent first
        """
        return await self.get_collection_history(limit=limit, action="remove")

    async def clear_collection(self) -> int:
        """Clear all cards from the collection.

        Returns:
            Number of cards removed
        """
        async with self.conn.execute("SELECT COUNT(*) as count FROM collection_cards") as cursor:
            row = await cursor.fetchone()
            count = row["count"] if row else 0

        await self.conn.execute("DELETE FROM collection_cards")
        await self.conn.execute("DELETE FROM collection_history")
        await self.conn.commit()
        logger.info("Cleared collection: %d cards removed", count)
        return count
