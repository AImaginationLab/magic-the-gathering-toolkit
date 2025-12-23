"""Combo database for storing and querying MTG combos."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

COMBO_SCHEMA_VERSION = 1

COMBO_SCHEMA_SQL = """
-- Schema version tracking
CREATE TABLE IF NOT EXISTS combo_schema_version (
    version INTEGER PRIMARY KEY
);

-- Combos table
CREATE TABLE IF NOT EXISTS combos (
    id TEXT PRIMARY KEY,
    combo_type TEXT NOT NULL,
    description TEXT NOT NULL,
    colors TEXT NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_combos_type ON combos(combo_type);

-- Combo cards (normalized)
CREATE TABLE IF NOT EXISTS combo_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    combo_id TEXT NOT NULL REFERENCES combos(id) ON DELETE CASCADE,
    card_name TEXT NOT NULL,
    card_name_lower TEXT NOT NULL,
    role TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_combo_cards_combo ON combo_cards(combo_id);
CREATE INDEX IF NOT EXISTS idx_combo_cards_name ON combo_cards(card_name_lower);
"""


@dataclass
class ComboRow:
    """A combo from the database."""

    id: str
    combo_type: str
    description: str
    colors: list[str]


@dataclass
class ComboCardRow:
    """A card in a combo."""

    combo_id: str
    card_name: str
    role: str
    position: int


class ComboDatabase:
    """SQLite database for combo data."""

    def __init__(self, db_path: Path, max_connections: int = 5):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None
        self._semaphore = asyncio.Semaphore(max_connections)

    @property
    def conn(self) -> aiosqlite.Connection:
        """Get the database connection."""
        if self._conn is None:
            raise RuntimeError("ComboDatabase not connected. Call connect() first.")
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
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._create_schema()
        logger.info("Combo database connected at %s", self.db_path)

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            # Save reference to thread before closing
            conn_thread = self._conn if hasattr(self._conn, "join") else None
            await self._conn.close()

            # Wait for aiosqlite thread to terminate to avoid hang on exit
            if conn_thread is not None:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, conn_thread.join, 2.0)

            self._conn = None

    async def _create_schema(self) -> None:
        """Create tables if they don't exist."""
        await self.conn.executescript(COMBO_SCHEMA_SQL)

        async with self.conn.execute("SELECT version FROM combo_schema_version LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if row is None:
                await self.conn.execute(
                    "INSERT INTO combo_schema_version (version) VALUES (?)",
                    (COMBO_SCHEMA_VERSION,),
                )

        await self.conn.commit()

    async def get_combo_count(self) -> int:
        """Get total number of combos."""
        async with self.conn.execute("SELECT COUNT(*) FROM combos") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def add_combo(
        self,
        combo_id: str,
        combo_type: str,
        description: str,
        cards: list[tuple[str, str]],  # [(name, role), ...]
        colors: list[str] | None = None,
    ) -> None:
        """Add a combo to the database."""
        colors_json = json.dumps(colors or [])

        await self.conn.execute(
            """
            INSERT OR REPLACE INTO combos (id, combo_type, description, colors)
            VALUES (?, ?, ?, ?)
            """,
            (combo_id, combo_type, description, colors_json),
        )

        # Delete existing cards for this combo
        await self.conn.execute("DELETE FROM combo_cards WHERE combo_id = ?", (combo_id,))

        # Insert cards
        for position, (name, role) in enumerate(cards):
            await self.conn.execute(
                """
                INSERT INTO combo_cards (combo_id, card_name, card_name_lower, role, position)
                VALUES (?, ?, ?, ?, ?)
                """,
                (combo_id, name, name.lower(), role, position),
            )

        await self.conn.commit()

    async def get_combo(self, combo_id: str) -> tuple[ComboRow, list[ComboCardRow]] | None:
        """Get a combo by ID with its cards."""
        async with self.conn.execute("SELECT * FROM combos WHERE id = ?", (combo_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None

            combo = ComboRow(
                id=row["id"],
                combo_type=row["combo_type"],
                description=row["description"],
                colors=json.loads(row["colors"]),
            )

        async with self.conn.execute(
            """
            SELECT * FROM combo_cards
            WHERE combo_id = ?
            ORDER BY position
            """,
            (combo_id,),
        ) as cursor:
            card_rows = await cursor.fetchall()
            cards = [
                ComboCardRow(
                    combo_id=r["combo_id"],
                    card_name=r["card_name"],
                    role=r["role"],
                    position=r["position"],
                )
                for r in card_rows
            ]

        return combo, cards

    async def find_combos_by_card(
        self, card_name: str
    ) -> list[tuple[ComboRow, list[ComboCardRow]]]:
        """Find all combos containing a specific card.

        Uses a single SQL query with JOINs to efficiently fetch combos and their
        cards without loading all combos into memory.
        """
        card_name_lower = card_name.lower()

        # Single query to get all combo data for combos containing this card
        query = """
            SELECT c.id, c.combo_type, c.description, c.colors,
                   cc.card_name, cc.role, cc.position
            FROM combos c
            JOIN combo_cards cc ON c.id = cc.combo_id
            WHERE c.id IN (
                SELECT DISTINCT combo_id FROM combo_cards
                WHERE card_name_lower = ?
            )
            ORDER BY c.id, cc.position
        """

        async with self.conn.execute(query, (card_name_lower,)) as cursor:
            rows = await cursor.fetchall()

        # Group rows by combo
        combos_map: dict[str, tuple[ComboRow, list[ComboCardRow]]] = {}
        for row in rows:
            combo_id = row["id"]
            if combo_id not in combos_map:
                combos_map[combo_id] = (
                    ComboRow(
                        id=combo_id,
                        combo_type=row["combo_type"],
                        description=row["description"],
                        colors=json.loads(row["colors"]),
                    ),
                    [],
                )
            combos_map[combo_id][1].append(
                ComboCardRow(
                    combo_id=combo_id,
                    card_name=row["card_name"],
                    role=row["role"],
                    position=row["position"],
                )
            )

        return list(combos_map.values())

    async def find_combos_in_deck(
        self, deck_card_names: list[str]
    ) -> tuple[
        list[tuple[ComboRow, list[ComboCardRow]]],
        list[tuple[ComboRow, list[ComboCardRow], list[str]]],
    ]:
        """Find complete and potential combos in a deck.

        Uses SQL filtering to only load combos that have at least one card present
        in the deck, rather than loading all combos and filtering in Python.

        Returns:
            Tuple of (complete_combos, potential_combos_with_missing)
            where potential_combos_with_missing is (combo, cards, missing_card_names)
        """
        if not deck_card_names:
            return [], []

        deck_names_lower = {name.lower() for name in deck_card_names}

        # Build parameterized query for deck card names
        placeholders = ",".join("?" * len(deck_names_lower))
        deck_names_list = list(deck_names_lower)

        # Find combos that have at least one card in the deck
        # This filters at the SQL level instead of loading all combos
        query = f"""
            SELECT c.id, c.combo_type, c.description, c.colors,
                   cc.card_name, cc.card_name_lower, cc.role, cc.position
            FROM combos c
            JOIN combo_cards cc ON c.id = cc.combo_id
            WHERE c.id IN (
                SELECT DISTINCT combo_id FROM combo_cards
                WHERE card_name_lower IN ({placeholders})
            )
            ORDER BY c.id, cc.position
        """

        async with self.conn.execute(query, deck_names_list) as cursor:
            rows = await cursor.fetchall()

        # Group rows by combo and track card presence
        combos_data: dict[str, tuple[ComboRow, list[ComboCardRow]]] = {}
        for row in rows:
            combo_id = row["id"]
            if combo_id not in combos_data:
                combos_data[combo_id] = (
                    ComboRow(
                        id=combo_id,
                        combo_type=row["combo_type"],
                        description=row["description"],
                        colors=json.loads(row["colors"]),
                    ),
                    [],
                )
            combos_data[combo_id][1].append(
                ComboCardRow(
                    combo_id=combo_id,
                    card_name=row["card_name"],
                    role=row["role"],
                    position=row["position"],
                )
            )

        # Categorize combos as complete or potential
        complete: list[tuple[ComboRow, list[ComboCardRow]]] = []
        potential: list[tuple[ComboRow, list[ComboCardRow], list[str]]] = []

        for combo, cards in combos_data.values():
            combo_card_names = {c.card_name.lower() for c in cards}
            present = combo_card_names & deck_names_lower
            missing = combo_card_names - deck_names_lower

            if not missing:
                complete.append((combo, cards))
            elif len(missing) <= 2 and len(present) >= 1:
                missing_names = [c.card_name for c in cards if c.card_name.lower() in missing]
                potential.append((combo, cards, missing_names))

        return complete, potential

    async def get_all_combos(self) -> list[tuple[ComboRow, list[ComboCardRow]]]:
        """Get all combos with their cards."""
        async with self.conn.execute("SELECT * FROM combos") as cursor:
            combo_rows = await cursor.fetchall()

        results = []
        for combo_row in combo_rows:
            combo = ComboRow(
                id=combo_row["id"],
                combo_type=combo_row["combo_type"],
                description=combo_row["description"],
                colors=json.loads(combo_row["colors"]),
            )

            async with self.conn.execute(
                """
                SELECT * FROM combo_cards
                WHERE combo_id = ?
                ORDER BY position
                """,
                (combo.id,),
            ) as cursor:
                card_rows = await cursor.fetchall()

            cards = [
                ComboCardRow(
                    combo_id=r["combo_id"],
                    card_name=r["card_name"],
                    role=r["role"],
                    position=r["position"],
                )
                for r in card_rows
            ]

            results.append((combo, cards))

        return results

    async def import_from_json(self, json_path: Path) -> int:
        """Import combos from a JSON file. Returns count of imported combos."""
        with open(json_path) as f:
            data = json.load(f)

        combos = data.get("combos", data) if isinstance(data, dict) else data
        count = 0

        for combo_data in combos:
            combo_id = combo_data["id"]
            combo_type = combo_data.get("type", "value")
            description = combo_data.get("description", combo_data.get("desc", ""))
            colors = combo_data.get("colors", [])

            # Handle both formats:
            # Old format: [("Name", "Role"), ...]
            # New format: [{"name": "Name", "role": "Role"}, ...]
            raw_cards = combo_data.get("cards", [])
            cards: list[tuple[str, str]] = []
            for card in raw_cards:
                if isinstance(card, dict):
                    cards.append((card["name"], card.get("role", "Combo piece")))
                elif isinstance(card, (list, tuple)):
                    cards.append((card[0], card[1] if len(card) > 1 else "Combo piece"))
                else:
                    cards.append((str(card), "Combo piece"))

            await self.add_combo(combo_id, combo_type, description, cards, colors)
            count += 1

        logger.info("Imported %d combos from %s", count, json_path)
        return count

    async def import_from_legacy_format(self, combos: list[dict[str, Any]]) -> int:
        """Import combos from the legacy Python list format (KNOWN_COMBOS)."""
        count = 0

        for combo_data in combos:
            combo_id = combo_data["id"]
            combo_type = combo_data.get("type", "value")
            description = combo_data.get("desc", "")
            colors = combo_data.get("colors", [])

            # Legacy format: [("Name", "Role"), ...]
            raw_cards = combo_data.get("cards", [])
            cards: list[tuple[str, str]] = []
            for card in raw_cards:
                if isinstance(card, (list, tuple)):
                    cards.append((card[0], card[1] if len(card) > 1 else "Combo piece"))
                else:
                    cards.append((str(card), "Combo piece"))

            await self.add_combo(combo_id, combo_type, description, cards, colors)
            count += 1

        logger.info("Imported %d combos from legacy format", count)
        return count

    async def clear_all(self) -> None:
        """Clear all combos from the database."""
        await self.conn.execute("DELETE FROM combo_cards")
        await self.conn.execute("DELETE FROM combos")
        await self.conn.commit()
