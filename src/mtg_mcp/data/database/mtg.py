"""MTGJson database access."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import aiosqlite

from ...exceptions import CardNotFoundError, SetNotFoundError
from ..models import Card, CardLegality, CardRuling, Set
from .cache import CardCache
from .constants import CARD_COLUMNS, EXCLUDE_EXTRAS, EXCLUDE_PROMOS, VALID_FORMATS
from .query import QueryBuilder

if TYPE_CHECKING:
    from ..models.inputs import SearchCardsInput


class MTGDatabase:
    """Direct database access to MTGJson AllPrintings SQLite database."""

    def __init__(self, db: aiosqlite.Connection, cache: CardCache | None = None):
        self._db = db
        self._cache = cache or CardCache()

    @staticmethod
    def _parse_list(value: str | None) -> list[str] | None:
        """Parse comma-separated string into list."""
        if not value:
            return None
        return [v.strip() for v in value.split(",") if v.strip()]

    def _row_to_card(self, row: aiosqlite.Row) -> Card:
        """Convert a database row to a Card model."""
        return Card.model_validate(
            {
                "uuid": row["uuid"],
                "name": row["name"],
                "manaCost": row["manaCost"],
                "manaValue": row["manaValue"],
                "colors": self._parse_list(row["colors"]),
                "colorIdentity": self._parse_list(row["colorIdentity"]),
                "type": row["type"],
                "supertypes": self._parse_list(row["supertypes"]),
                "types": self._parse_list(row["types"]),
                "subtypes": self._parse_list(row["subtypes"]),
                "text": row["text"],
                "flavorText": row["flavorText"],
                "power": row["power"],
                "toughness": row["toughness"],
                "loyalty": row["loyalty"],
                "defense": row["defense"],
                "setCode": row["setCode"],
                "rarity": row["rarity"],
                "number": row["number"],
                "artist": row["artist"],
                "layout": row["layout"],
                "keywords": self._parse_list(row["keywords"]),
                "edhrecRank": row["edhrecRank"],
            }
        )

    def _row_to_set(self, row: aiosqlite.Row) -> Set:
        """Convert a database row to a Set model."""
        # Preserve None values for boolean fields (don't convert None to False)
        is_online_only = bool(row["isOnlineOnly"]) if row["isOnlineOnly"] is not None else None
        is_foil_only = bool(row["isFoilOnly"]) if row["isFoilOnly"] is not None else None
        return Set.model_validate(
            {
                "code": row["code"],
                "name": row["name"],
                "type": row["type"],
                "releaseDate": row["releaseDate"],
                "block": row["block"],
                "baseSetSize": row["baseSetSize"],
                "totalSetSize": row["totalSetSize"],
                "isOnlineOnly": is_online_only,
                "isFoilOnly": is_foil_only,
                "keyruneCode": row["keyruneCode"],
            }
        )

    # -------------------------------------------------------------------------
    # Card Methods
    # -------------------------------------------------------------------------

    async def get_card_by_uuid(self, uuid: str) -> Card:
        """Get a card by its UUID. Raises CardNotFoundError if not found."""
        # Check cache first
        cached = await self._cache.get(f"uuid:{uuid}")
        if cached:
            return cached

        async with self._db.execute(
            f"SELECT {CARD_COLUMNS} FROM cards c WHERE uuid = ?",
            (uuid,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                card = self._row_to_card(row)
                card.legalities = await self._get_legalities(uuid)
                card.rulings = await self._get_rulings(uuid)
                await self._cache.set(f"uuid:{uuid}", card)
                return card
        raise CardNotFoundError(uuid)

    async def get_card_by_name(self, name: str, include_extras: bool = True) -> Card:
        """Get a card by exact name. Returns most recent non-promo printing."""
        # Check cache first - include include_extras in cache key to avoid serving
        # incomplete data when the flag differs between calls
        cache_key = f"name:{name.lower()}:extras={include_extras}"
        cached = await self._cache.get(cache_key)
        if cached:
            return cached

        async with self._db.execute(
            f"""
            SELECT {CARD_COLUMNS}
            FROM cards c
            JOIN sets s ON c.setCode = s.code
            WHERE c.name = ? AND {EXCLUDE_PROMOS}
            ORDER BY s.releaseDate DESC
            LIMIT 1
            """,
            (name,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                card = self._row_to_card(row)
                if include_extras:
                    card.legalities = await self._get_legalities(row["uuid"])
                    card.rulings = await self._get_rulings(row["uuid"])
                await self._cache.set(cache_key, card)
                return card
        raise CardNotFoundError(name)

    async def search_cards(self, filters: SearchCardsInput) -> tuple[list[Card], int]:
        """Search for cards matching the given filters.

        Returns:
            Tuple of (cards on this page, total matching count)
        """
        qb = QueryBuilder.from_filters(filters)
        where_clause = qb.build_where()

        # First, get the total count (without LIMIT/OFFSET)
        count_query = f"""
            SELECT COUNT(DISTINCT c.name)
            FROM cards c
            JOIN sets s ON c.setCode = s.code
            WHERE {where_clause} AND {EXCLUDE_EXTRAS}
        """
        async with self._db.execute(count_query, qb.params) as cursor:
            row = await cursor.fetchone()
            total_count = row[0] if row else 0

        # Build ORDER BY clause based on sort_by and sort_order
        order_direction = "DESC" if filters.sort_order == "desc" else "ASC"
        sort_column_map = {
            "name": "c.name",
            "cmc": "c.manaValue",
            "color": "c.colors",
            "rarity": "CASE c.rarity WHEN 'common' THEN 1 WHEN 'uncommon' THEN 2 WHEN 'rare' THEN 3 WHEN 'mythic' THEN 4 ELSE 0 END",
            "type": "c.type",
        }
        sort_column = sort_column_map.get(filters.sort_by or "name", "c.name")
        order_clause = f"ORDER BY {sort_column} {order_direction}"

        # Then get the paginated results
        query = f"""
            SELECT DISTINCT {CARD_COLUMNS}
            FROM cards c
            JOIN sets s ON c.setCode = s.code
            WHERE {where_clause} AND {EXCLUDE_EXTRAS}
            GROUP BY c.name
            {order_clause}
            LIMIT ? OFFSET ?
        """
        # Create a copy of params for the paginated query
        page_params = list(qb.params)
        page_params.extend([filters.page_size, (filters.page - 1) * filters.page_size])

        cards = []
        async with self._db.execute(query, page_params) as cursor:
            async for row in cursor:
                cards.append(self._row_to_card(row))

        return cards, total_count

    async def _get_legalities(self, uuid: str) -> list[CardLegality]:
        """Get format legalities for a card."""
        async with self._db.execute(
            "SELECT * FROM cardLegalities WHERE uuid = ?",
            (uuid,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return []

            # Get column names from the row to check which formats exist
            row_keys = row.keys()
            legalities = []
            for fmt in VALID_FORMATS:
                if fmt in row_keys and row[fmt]:
                    legalities.append(CardLegality(format=fmt, legality=row[fmt]))
            return legalities

    async def _get_rulings(self, uuid: str) -> list[CardRuling]:
        """Get rulings for a card."""
        rulings = []
        async with self._db.execute(
            "SELECT date, text FROM cardRulings WHERE uuid = ? ORDER BY date DESC",
            (uuid,),
        ) as cursor:
            async for row in cursor:
                rulings.append(CardRuling(date=str(row["date"]), text=row["text"]))
        return rulings

    async def get_card_rulings(self, name: str) -> list[CardRuling]:
        """Get rulings for a card by name."""
        async with self._db.execute(
            "SELECT uuid FROM cards WHERE name = ? LIMIT 1",
            (name,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return []
            return await self._get_rulings(row["uuid"])

    async def get_card_legalities(self, name: str) -> list[CardLegality]:
        """Get format legalities for a card by name."""
        async with self._db.execute(
            "SELECT uuid FROM cards WHERE name = ? LIMIT 1",
            (name,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return []
            return await self._get_legalities(row["uuid"])

    # -------------------------------------------------------------------------
    # Set Methods
    # -------------------------------------------------------------------------

    async def get_set(self, code: str) -> Set:
        """Get a set by its code. Raises SetNotFoundError if not found."""
        async with self._db.execute(
            """
            SELECT code, name, type, releaseDate, block, baseSetSize,
                   totalSetSize, isOnlineOnly, isFoilOnly, keyruneCode
            FROM sets
            WHERE LOWER(code) = LOWER(?)
            """,
            (code,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_set(row)
        raise SetNotFoundError(code)

    async def get_all_sets(
        self,
        set_type: str | None = None,
        include_online_only: bool = True,
    ) -> list[Set]:
        """Get all sets, optionally filtered."""
        conditions = []
        params: list[Any] = []

        if set_type:
            conditions.append("LOWER(type) = LOWER(?)")
            params.append(set_type)

        if not include_online_only:
            conditions.append("(isOnlineOnly IS NULL OR isOnlineOnly = 0)")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sets = []
        async with self._db.execute(
            f"""
            SELECT code, name, type, releaseDate, block, baseSetSize,
                   totalSetSize, isOnlineOnly, isFoilOnly, keyruneCode
            FROM sets
            WHERE {where_clause}
            ORDER BY releaseDate DESC
            """,
            params,
        ) as cursor:
            async for row in cursor:
                sets.append(self._row_to_set(row))
        return sets

    async def search_sets(self, name: str) -> list[Set]:
        """Search sets by name."""
        sets = []
        async with self._db.execute(
            """
            SELECT code, name, type, releaseDate, block, baseSetSize,
                   totalSetSize, isOnlineOnly, isFoilOnly, keyruneCode
            FROM sets
            WHERE name LIKE ?
            ORDER BY releaseDate DESC
            """,
            (f"%{name}%",),
        ) as cursor:
            async for row in cursor:
                sets.append(self._row_to_set(row))
        return sets

    # -------------------------------------------------------------------------
    # Statistics / Utility
    # -------------------------------------------------------------------------

    async def get_database_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        stats: dict[str, Any] = {}

        async with self._db.execute("SELECT COUNT(*) FROM cards") as cursor:
            row = await cursor.fetchone()
            stats["total_cards"] = row[0] if row else 0

        async with self._db.execute("SELECT COUNT(DISTINCT name) FROM cards") as cursor:
            row = await cursor.fetchone()
            stats["unique_cards"] = row[0] if row else 0

        async with self._db.execute("SELECT COUNT(*) FROM sets") as cursor:
            row = await cursor.fetchone()
            stats["total_sets"] = row[0] if row else 0

        async with self._db.execute("SELECT date, version FROM meta") as cursor:
            row = await cursor.fetchone()
            if row:
                stats["data_date"] = str(row[0])
                stats["data_version"] = row[1]

        return stats

    async def get_random_card(self) -> Card:
        """Get a random card (useful for discovery)."""
        async with self._db.execute(
            f"""
            SELECT {CARD_COLUMNS}
            FROM cards c
            WHERE {EXCLUDE_EXTRAS}
            ORDER BY RANDOM()
            LIMIT 1
            """,
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                card = self._row_to_card(row)
                card.legalities = await self._get_legalities(row["uuid"])
                card.rulings = await self._get_rulings(row["uuid"])
                return card
        raise CardNotFoundError("random")
