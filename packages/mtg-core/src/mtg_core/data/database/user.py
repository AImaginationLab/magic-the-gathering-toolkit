"""User database for decks and collections."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import aiosqlite

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Schema version for migrations
SCHEMA_VERSION = 1

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
    added_at: datetime


class UserDatabase:
    """SQLite database for user data (decks, collections, etc.)."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    @property
    def conn(self) -> aiosqlite.Connection:
        """Get the database connection."""
        if self._conn is None:
            raise RuntimeError("UserDatabase not connected. Call connect() first.")
        return self._conn

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

        # Set schema version if not exists
        async with self.conn.execute("SELECT version FROM schema_version LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if row is None:
                await self.conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,)
                )

        await self.conn.commit()

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
    ) -> None:
        """Add a card to a deck. If card exists, increases quantity."""
        await self.conn.execute(
            """
            INSERT INTO deck_cards (deck_id, card_name, quantity, is_sideboard, is_commander)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (deck_id, card_name, is_sideboard)
            DO UPDATE SET quantity = quantity + excluded.quantity
            """,
            (deck_id, card_name, quantity, int(sideboard), int(is_commander)),
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
