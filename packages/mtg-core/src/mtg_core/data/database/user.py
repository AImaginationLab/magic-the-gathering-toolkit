"""User database for decks and collections."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

# Schema version for migrations
SCHEMA_VERSION = 4

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
CREATE TABLE IF NOT EXISTS deck_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    card_name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    is_sideboard INTEGER NOT NULL DEFAULT 0,
    is_commander INTEGER NOT NULL DEFAULT 0,
    set_code TEXT,
    collector_number TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(deck_id, card_name, is_sideboard)
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

-- Trigger to update updated_at on collection changes
CREATE TRIGGER IF NOT EXISTS update_collection_timestamp
AFTER UPDATE ON collection_cards
BEGIN
    UPDATE collection_cards SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
"""


@dataclass
class DeckSummary:
    """Lightweight deck info for listing."""

    id: int
    name: str
    format: str | None
    card_count: int
    sideboard_count: int
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

    def __init__(self, db_path: Path, max_connections: int = 5):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None
        self._semaphore = asyncio.Semaphore(max_connections)

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

        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
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

    async def list_decks(self) -> list[DeckSummary]:
        """List all decks with card counts."""
        query = """
        SELECT
            d.id,
            d.name,
            d.format,
            d.commander,
            d.updated_at,
            COALESCE(SUM(CASE WHEN dc.is_sideboard = 0 THEN dc.quantity ELSE 0 END), 0) as card_count,
            COALESCE(SUM(CASE WHEN dc.is_sideboard = 1 THEN dc.quantity ELSE 0 END), 0) as sideboard_count
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
        is_commander: bool = False,
        set_code: str | None = None,
        collector_number: str | None = None,
    ) -> None:
        """Add a card to a deck. If card exists, increases quantity and updates printing."""
        await self.conn.execute(
            """
            INSERT INTO deck_cards (deck_id, card_name, quantity, is_sideboard, is_commander, set_code, collector_number)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (deck_id, card_name, is_sideboard)
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
                int(is_commander),
                set_code,
                collector_number,
            ),
        )
        await self.conn.commit()

    async def remove_card(self, deck_id: int, card_name: str, sideboard: bool = False) -> bool:
        """Remove a card entirely from a deck."""
        async with self.conn.execute(
            """
            DELETE FROM deck_cards
            WHERE deck_id = ? AND card_name = ? AND is_sideboard = ?
            """,
            (deck_id, card_name, int(sideboard)),
        ) as cursor:
            removed = cursor.rowcount > 0
        await self.conn.commit()
        return removed

    async def set_quantity(
        self, deck_id: int, card_name: str, quantity: int, sideboard: bool = False
    ) -> None:
        """Set the quantity of a card. If quantity is 0, removes the card."""
        if quantity <= 0:
            await self.remove_card(deck_id, card_name, sideboard)
            return

        await self.conn.execute(
            """
            UPDATE deck_cards
            SET quantity = ?
            WHERE deck_id = ? AND card_name = ? AND is_sideboard = ?
            """,
            (quantity, deck_id, card_name, int(sideboard)),
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

    # ─────────────────────────────────────────────────────────────────────────
    # Queries
    # ─────────────────────────────────────────────────────────────────────────

    async def get_deck_cards(self, deck_id: int) -> list[DeckCardRow]:
        """Get all cards in a deck."""
        async with self.conn.execute(
            """
            SELECT * FROM deck_cards
            WHERE deck_id = ?
            ORDER BY is_sideboard, card_name
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
            COALESCE(SUM(CASE WHEN dc2.is_sideboard = 0 THEN dc2.quantity ELSE 0 END), 0) as card_count,
            COALESCE(SUM(CASE WHEN dc2.is_sideboard = 1 THEN dc2.quantity ELSE 0 END), 0) as sideboard_count
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
            COALESCE(SUM(CASE WHEN dc.is_sideboard = 0 THEN dc.quantity ELSE 0 END), 0) as card_count,
            COALESCE(SUM(CASE WHEN dc.is_sideboard = 1 THEN dc.quantity ELSE 0 END), 0) as sideboard_count
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
        """Add a card to the collection. If card exists, increases quantity."""
        await self.conn.execute(
            """
            INSERT INTO collection_cards (card_name, quantity, foil_quantity, set_code, collector_number)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (card_name)
            DO UPDATE SET
                quantity = quantity + excluded.quantity,
                foil_quantity = foil_quantity + excluded.foil_quantity,
                set_code = COALESCE(excluded.set_code, set_code),
                collector_number = COALESCE(excluded.collector_number, collector_number)
            """,
            (card_name, quantity, foil_quantity, set_code, collector_number),
        )
        # Log history
        await self._log_collection_history(
            card_name, "add", quantity, foil_quantity, set_code, collector_number
        )
        await self.conn.commit()

    async def remove_from_collection(self, card_name: str) -> bool:
        """Remove a card entirely from the collection."""
        # Get current quantities for history before deleting
        async with self.conn.execute(
            "SELECT quantity, foil_quantity, set_code, collector_number FROM collection_cards WHERE card_name = ?",
            (card_name,),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return False

        quantity = row["quantity"]
        foil_quantity = row["foil_quantity"]
        set_code = row["set_code"]
        collector_number = row["collector_number"]

        async with self.conn.execute(
            "DELETE FROM collection_cards WHERE card_name = ?",
            (card_name,),
        ) as cursor:
            removed = cursor.rowcount > 0

        if removed:
            # Log history with negative quantities
            await self._log_collection_history(
                card_name, "remove", -quantity, -foil_quantity, set_code, collector_number
            )
        await self.conn.commit()
        return removed

    async def set_collection_quantity(
        self,
        card_name: str,
        quantity: int,
        foil_quantity: int = 0,
    ) -> None:
        """Set the quantity of a card in collection. Removes if both are 0."""
        total = quantity + foil_quantity
        if total <= 0:
            await self.remove_from_collection(card_name)
            return

        # Get old quantities for history
        async with self.conn.execute(
            "SELECT quantity, foil_quantity, set_code, collector_number FROM collection_cards WHERE card_name = ?",
            (card_name,),
        ) as cursor:
            row = await cursor.fetchone()

        old_qty = row["quantity"] if row else 0
        old_foil = row["foil_quantity"] if row else 0
        set_code = row["set_code"] if row else None
        collector_number = row["collector_number"] if row else None

        await self.conn.execute(
            """
            UPDATE collection_cards
            SET quantity = ?, foil_quantity = ?
            WHERE card_name = ?
            """,
            (quantity, foil_quantity, card_name),
        )

        # Log history with the change (can be negative if reducing)
        qty_change = quantity - old_qty
        foil_change = foil_quantity - old_foil
        if qty_change != 0 or foil_change != 0:
            await self._log_collection_history(
                card_name, "update", qty_change, foil_change, set_code, collector_number
            )
        await self.conn.commit()

    async def update_collection_printing(
        self,
        card_name: str,
        set_code: str,
        collector_number: str,
    ) -> bool:
        """Update the printing (set code and collector number) for a collection card."""
        cursor = await self.conn.execute(
            """
            UPDATE collection_cards
            SET set_code = ?, collector_number = ?
            WHERE card_name = ?
            """,
            (set_code, collector_number, card_name),
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def get_collection_card(self, card_name: str) -> CollectionCardRow | None:
        """Get a single card from the collection."""
        async with self.conn.execute(
            "SELECT * FROM collection_cards WHERE card_name = ?",
            (card_name,),
        ) as cursor:
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
    ) -> list[CollectionCardRow]:
        """Get cards from the collection with pagination."""
        async with self.conn.execute(
            """
            SELECT * FROM collection_cards
            ORDER BY card_name
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
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
