"""MTGJson database access."""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING, Any

import aiosqlite

from ...exceptions import CardNotFoundError, SetNotFoundError
from ..models import Card, CardLegality, CardRuling, Set
from ..models.responses import (
    ArtistStats,
    ArtistSummary,
    BlockSummary,
    SetStats,
    SetSummary,
)
from .base import BaseDatabase
from .cache import CardCache
from .constants import (
    CARD_COLUMNS,
    CARD_COLUMNS_PLAIN,
    EXCLUDE_EXTRAS,
    EXCLUDE_PROMOS,
    VALID_FORMATS,
)
from .fts import check_fts_available, search_cards_fts
from .migrations import (
    get_cached_artist_for_spotlight,
    is_artist_cache_populated,
)
from .migrations import (
    refresh_artist_stats_cache as _refresh_artist_stats_cache,
)
from .query import QueryBuilder

if TYPE_CHECKING:
    from ..models.inputs import SearchCardsInput
    from ..models.responses import CardSummary
    from .scryfall import ScryfallDatabase

logger = logging.getLogger(__name__)


class MTGDatabase(BaseDatabase):
    """Direct database access to MTGJson AllPrintings SQLite database."""

    def __init__(
        self,
        db: aiosqlite.Connection,
        cache: CardCache | None = None,
        max_connections: int = 5,
    ):
        super().__init__(db, max_connections)
        self._cache = cache or CardCache()
        self._fts_available: bool | None = None
        self._artists_cache: list[ArtistSummary] | None = None
        self._artists_cache_min_cards: int = 0

    async def is_fts_available(self) -> bool:
        """Check if FTS5 table exists and is available."""
        if self._fts_available is None:
            self._fts_available = await check_fts_available(self._db)
        return self._fts_available

    async def search_fts(
        self,
        query: str,
        limit: int = 100,
        search_name: bool = True,
        search_type: bool = True,
        search_text: bool = True,
    ) -> list[str]:
        """Search cards using FTS5 full-text search.

        Args:
            query: Search query string
            limit: Maximum number of UUIDs to return
            search_name: Include card name in search
            search_type: Include card type in search
            search_text: Include oracle text in search

        Returns:
            List of matching card UUIDs, ordered by relevance (bm25 rank).
        """
        if not await self.is_fts_available():
            return []
        return await search_cards_fts(self._db, query, limit, search_name, search_type, search_text)

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
                "flavorName": row["flavorName"],
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

        async with self._execute(
            f"""
            SELECT {CARD_COLUMNS}
            FROM cards c
            JOIN sets s ON c.setCode = s.code
            WHERE c.uuid = ?
            """,
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

        async with self._execute(
            f"""
            SELECT {CARD_COLUMNS}
            FROM cards c
            JOIN sets s ON c.setCode = s.code
            WHERE c.name COLLATE NOCASE = ? AND {EXCLUDE_PROMOS}
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

    async def get_all_printings(self, name: str) -> list[Card]:
        """Get all printings of a card by name (across all sets)."""
        printings: list[Card] = []
        async with self._execute(
            f"""
            SELECT {CARD_COLUMNS}
            FROM cards c
            JOIN sets s ON c.setCode = s.code
            WHERE c.name COLLATE NOCASE = ?
            ORDER BY s.releaseDate DESC, c.setCode
            """,
            (name,),
        ) as cursor:
            async for row in cursor:
                printings.append(self._row_to_card(row))
        return printings

    async def get_card_by_set_and_number(self, set_code: str, collector_number: str) -> Card | None:
        """Look up a card by set code and collector number.

        Args:
            set_code: The set code (e.g., "FIN", "M21")
            collector_number: The collector number (e.g., "12", "0012", "123a")

        Returns:
            The card if found, None otherwise.
        """
        # Normalize collector number - remove leading zeros for comparison
        # but also try exact match since some cards have leading zeros
        normalized_number = collector_number.lstrip("0") or "0"

        async with self._execute(
            f"""
            SELECT {CARD_COLUMNS}
            FROM cards c
            JOIN sets s ON c.setCode = s.code
            WHERE c.setCode COLLATE NOCASE = ?
            AND (c.number = ? OR c.number = ? OR CAST(c.number AS TEXT) = ?)
            AND {EXCLUDE_PROMOS}
            LIMIT 1
            """,
            (set_code, collector_number, normalized_number, normalized_number),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_card(row)
        return None

    async def get_token_by_set_and_number(
        self, set_code: str, collector_number: str
    ) -> Card | None:
        """Look up a token by set code and collector number.

        Args:
            set_code: The set code (e.g., "TDOM", "TM21", "AFIN")
            collector_number: The collector number

        Returns:
            Token as a Card object if found, None otherwise.
            Also supports art series cards which are stored in the tokens table.
        """
        normalized_number = collector_number.lstrip("0") or "0"

        # Token columns - use NULL for columns that don't exist in tokens table
        # (manaValue, loyalty, defense, rarity, edhrecRank are not in tokens)
        async with self._execute(
            """
            SELECT
                t.uuid, t.name, t.flavorName, t.manaCost, NULL as manaValue,
                t.colors, t.colorIdentity, t.type, t.supertypes, t.types, t.subtypes,
                t.text, t.flavorText, t.power, t.toughness, NULL as loyalty, NULL as defense,
                t.setCode, 'special' as rarity, t.number, t.artist, t.layout,
                t.keywords, NULL as edhrecRank
            FROM tokens t
            JOIN sets s ON t.setCode = s.code
            WHERE t.setCode COLLATE NOCASE = ?
            AND (t.number = ? OR t.number = ? OR CAST(t.number AS TEXT) = ?)
            LIMIT 1
            """,
            (set_code, collector_number, normalized_number, normalized_number),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_card(row)
        return None

    async def get_token_by_name(self, name: str) -> Card | None:
        """Get a token by name. Returns most recent printing.

        Also supports art series cards which are stored in the tokens table.
        """
        # Token columns - use NULL for columns that don't exist in tokens table
        # (manaValue, loyalty, defense, rarity, edhrecRank are not in tokens)
        async with self._execute(
            """
            SELECT
                t.uuid, t.name, t.flavorName, t.manaCost, NULL as manaValue,
                t.colors, t.colorIdentity, t.type, t.supertypes, t.types, t.subtypes,
                t.text, t.flavorText, t.power, t.toughness, NULL as loyalty, NULL as defense,
                t.setCode, 'special' as rarity, t.number, t.artist, t.layout,
                t.keywords, NULL as edhrecRank
            FROM tokens t
            JOIN sets s ON t.setCode = s.code
            WHERE t.name COLLATE NOCASE = ?
            ORDER BY s.releaseDate DESC
            LIMIT 1
            """,
            (name,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_card(row)
        return None

    async def search_cards(self, filters: SearchCardsInput) -> tuple[list[Card], int]:
        """Search for cards matching the given filters.

        Returns:
            Tuple of (cards on this page, total matching count)
        """
        qb = QueryBuilder.from_filters(filters)
        where_clause = qb.build_where()

        # First, get the total count (without LIMIT/OFFSET)
        # Count distinct name+flavorName combinations to treat flavor variants as separate
        count_query = f"""
            SELECT COUNT(*) FROM (
                SELECT DISTINCT c.name, COALESCE(c.flavorName, '')
                FROM cards c
                JOIN sets s ON c.setCode = s.code
                WHERE {where_clause} AND {EXCLUDE_EXTRAS}
            )
        """
        async with self._execute(count_query, qb.params) as cursor:
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
        # Group by name+flavorName to treat flavor variants (SpongeBob, Walking Dead) as separate
        query = f"""
            SELECT DISTINCT {CARD_COLUMNS}
            FROM cards c
            JOIN sets s ON c.setCode = s.code
            WHERE {where_clause} AND {EXCLUDE_EXTRAS}
            GROUP BY c.name, COALESCE(c.flavorName, '')
            {order_clause}
            LIMIT ? OFFSET ?
        """
        # Create a copy of params for the paginated query
        page_params = list(qb.params)
        page_params.extend([filters.page_size, (filters.page - 1) * filters.page_size])

        cards = []
        async with self._execute(query, page_params) as cursor:
            async for row in cursor:
                cards.append(self._row_to_card(row))

        return cards, total_count

    async def search_cards_with_fts(
        self, filters: SearchCardsInput, use_fts: bool = True
    ) -> tuple[list[Card], int]:
        """Search for cards, using FTS5 for text search when available.

        Args:
            filters: Search filters
            use_fts: If True and FTS5 is available, use it for text searches

        Returns:
            Tuple of (cards on this page, total matching count)
        """
        # Check if we should use FTS for text search
        if use_fts and filters.text and await self.is_fts_available():
            # Get matching UUIDs from FTS first
            fts_uuids = await self.search_fts(
                filters.text,
                limit=10000,
                search_name=True,
                search_type=True,
                search_text=True,
            )

            if fts_uuids:
                # Build query that uses the FTS results as a filter
                qb = QueryBuilder()
                qb.add_name_search(filters.name)
                qb.add_colors(filters.colors)
                qb.add_color_identity(filters.color_identity)
                qb.add_like("c.type", filters.type)
                qb.add_like("c.subtypes", filters.subtype)
                qb.add_like("c.supertypes", filters.supertype)
                qb.add_exact("c.rarity", filters.rarity, case_insensitive=True)
                qb.add_exact("c.setCode", filters.set_code, case_insensitive=True)
                qb.add_comparison("c.manaValue", "=", filters.cmc)
                qb.add_comparison("c.manaValue", ">=", filters.cmc_min)
                qb.add_comparison("c.manaValue", "<=", filters.cmc_max)
                qb.add_exact("c.power", filters.power)
                qb.add_exact("c.toughness", filters.toughness)
                qb.add_keywords(filters.keywords)
                qb.add_format_legality(filters.format_legal)

                # Add FTS UUID constraint
                placeholders = ",".join("?" * len(fts_uuids))
                qb.conditions.append(f"c.uuid IN ({placeholders})")
                qb.params.extend(fts_uuids)

                where_clause = qb.build_where()

                # Get count (distinct name+flavorName combinations)
                count_query = f"""
                    SELECT COUNT(*) FROM (
                        SELECT DISTINCT c.name, COALESCE(c.flavorName, '')
                        FROM cards c
                        JOIN sets s ON c.setCode = s.code
                        WHERE {where_clause} AND {EXCLUDE_EXTRAS}
                    )
                """
                async with self._execute(count_query, qb.params) as cursor:
                    row = await cursor.fetchone()
                    total_count = row[0] if row else 0

                # Build ORDER BY
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

                # Get paginated results
                query = f"""
                    SELECT DISTINCT {CARD_COLUMNS}
                    FROM cards c
                    JOIN sets s ON c.setCode = s.code
                    WHERE {where_clause} AND {EXCLUDE_EXTRAS}
                    GROUP BY c.name, COALESCE(c.flavorName, '')
                    {order_clause}
                    LIMIT ? OFFSET ?
                """
                page_params = list(qb.params)
                page_params.extend([filters.page_size, (filters.page - 1) * filters.page_size])

                cards = []
                async with self._execute(query, page_params) as cursor:
                    async for row in cursor:
                        cards.append(self._row_to_card(row))

                return cards, total_count

        # Fall back to standard search
        return await self.search_cards(filters)

    async def _get_legalities(self, uuid: str) -> list[CardLegality]:
        """Get format legalities for a card."""
        async with self._execute(
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
        async with self._execute(
            "SELECT date, text FROM cardRulings WHERE uuid = ? ORDER BY date DESC",
            (uuid,),
        ) as cursor:
            async for row in cursor:
                rulings.append(CardRuling(date=str(row["date"]), text=row["text"]))
        return rulings

    async def get_card_rulings(self, name: str) -> list[CardRuling]:
        """Get rulings for a card by name."""
        async with self._execute(
            "SELECT uuid FROM cards WHERE name = ? LIMIT 1",
            (name,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return []
            return await self._get_rulings(row["uuid"])

    async def get_card_legalities(self, name: str) -> list[CardLegality]:
        """Get format legalities for a card by name."""
        async with self._execute(
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
        async with self._execute(
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
        async with self._execute(
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
        async with self._execute(
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

        async with self._execute("SELECT COUNT(*) FROM cards") as cursor:
            row = await cursor.fetchone()
            stats["total_cards"] = row[0] if row else 0

        async with self._execute("SELECT COUNT(DISTINCT name) FROM cards") as cursor:
            row = await cursor.fetchone()
            stats["unique_cards"] = row[0] if row else 0

        async with self._execute("SELECT COUNT(*) FROM sets") as cursor:
            row = await cursor.fetchone()
            stats["total_sets"] = row[0] if row else 0

        async with self._execute("SELECT date, version FROM meta") as cursor:
            row = await cursor.fetchone()
            if row:
                stats["data_date"] = str(row[0])
                stats["data_version"] = row[1]

        return stats

    async def get_random_card(self) -> Card:
        """Get a random card using O(1) rowid-based selection.

        Uses indexed rowid lookup instead of ORDER BY RANDOM() to avoid full table scan.
        Handles gaps in rowids by selecting the first valid card >= random rowid.
        """
        # Get max rowid for the cards table
        async with self._execute("SELECT MAX(rowid) FROM cards") as cursor:
            row = await cursor.fetchone()
            max_rowid = row[0] if row and row[0] else 0

        if max_rowid == 0:
            raise CardNotFoundError("random")

        # Try up to 10 times to find a valid non-extra card
        for _ in range(10):
            random_rowid = random.randint(1, max_rowid)
            async with self._execute(
                f"""
                SELECT {CARD_COLUMNS}
                FROM cards c
                JOIN sets s ON c.setCode = s.code
                WHERE c.rowid >= ? AND {EXCLUDE_EXTRAS}
                LIMIT 1
                """,
                (random_rowid,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    card = self._row_to_card(row)
                    card.legalities = await self._get_legalities(row["uuid"])
                    card.rulings = await self._get_rulings(row["uuid"])
                    return card

        # Fallback: if we consistently hit extras/gaps, start from beginning
        async with self._execute(
            f"""
            SELECT {CARD_COLUMNS}
            FROM cards c
            JOIN sets s ON c.setCode = s.code
            WHERE {EXCLUDE_EXTRAS}
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

    async def get_all_keywords(self) -> set[str]:
        """Get all unique keywords from the cards table.

        Keywords are stored as comma-separated strings in the database.
        """
        keywords: set[str] = set()
        async with self._execute(
            "SELECT DISTINCT keywords FROM cards WHERE keywords IS NOT NULL AND keywords != ''"
        ) as cursor:
            async for row in cursor:
                if row[0]:
                    # Keywords stored as comma-separated string
                    keyword_list = self._parse_list(row[0])
                    if keyword_list:
                        keywords.update(keyword_list)
        return keywords

    async def get_cards_by_names(
        self,
        names: list[str],
        include_extras: bool = False,
    ) -> dict[str, Card]:
        """Batch load cards by name, return name->Card mapping.

        Args:
            names: List of card names to fetch
            include_extras: If True, load legalities and rulings (slower)

        Returns:
            Dict mapping card name (lowercase) to Card. Missing cards are omitted.
        """
        if not names:
            return {}

        results: dict[str, Card] = {}
        names_to_fetch: list[str] = []

        # Check cache first
        for name in names:
            cache_key = f"name:{name.lower()}:extras={include_extras}"
            cached = await self._cache.get(cache_key)
            if cached:
                results[name.lower()] = cached
            else:
                names_to_fetch.append(name)

        if not names_to_fetch:
            return results

        # Build parameterized query for remaining names
        placeholders = ",".join("?" * len(names_to_fetch))
        query = f"""
            SELECT {CARD_COLUMNS}
            FROM cards c
            JOIN sets s ON c.setCode = s.code
            WHERE c.name IN ({placeholders}) AND {EXCLUDE_PROMOS}
            ORDER BY s.releaseDate DESC
        """

        # Fetch all matching cards, group by name to get most recent printing
        name_to_row: dict[str, aiosqlite.Row] = {}
        async with self._execute(query, names_to_fetch) as cursor:
            async for row in cursor:
                name_lower = row["name"].lower()
                # Keep only first (most recent due to ORDER BY)
                if name_lower not in name_to_row:
                    name_to_row[name_lower] = row

        # Convert rows to Card objects
        for name_lower, row in name_to_row.items():
            card = self._row_to_card(row)
            if include_extras:
                card.legalities = await self._get_legalities(row["uuid"])
                card.rulings = await self._get_rulings(row["uuid"])
            # Cache the result
            cache_key = f"name:{name_lower}:extras={include_extras}"
            await self._cache.set(cache_key, card)
            results[name_lower] = card

        return results

    async def get_cards_by_uuids(
        self,
        uuids: list[str],
        include_extras: bool = True,
    ) -> list[Card]:
        """Batch load cards by UUID list.

        Args:
            uuids: List of card UUIDs to fetch
            include_extras: If True, load legalities and rulings

        Returns:
            List of Card objects. Order matches input UUIDs (missing cards omitted).
        """
        if not uuids:
            return []

        results: dict[str, Card] = {}
        uuids_to_fetch: list[str] = []

        # Check cache first
        for uuid in uuids:
            cached = await self._cache.get(f"uuid:{uuid}")
            if cached:
                results[uuid] = cached
            else:
                uuids_to_fetch.append(uuid)

        if uuids_to_fetch:
            placeholders = ",".join("?" * len(uuids_to_fetch))
            query = f"""
                SELECT {CARD_COLUMNS}
                FROM cards c
                JOIN sets s ON c.setCode = s.code
                WHERE c.uuid IN ({placeholders})
            """

            async with self._execute(query, uuids_to_fetch) as cursor:
                async for row in cursor:
                    card = self._row_to_card(row)
                    uuid = row["uuid"]
                    if include_extras:
                        card.legalities = await self._get_legalities(uuid)
                        card.rulings = await self._get_rulings(uuid)
                    await self._cache.set(f"uuid:{uuid}", card)
                    results[uuid] = card

        # Return in original order, skipping missing
        return [results[uuid] for uuid in uuids if uuid in results]

    async def enrich_cards_batch(
        self,
        cards: list[CardSummary],
        scryfall_db: ScryfallDatabase | None = None,
    ) -> list[CardSummary]:
        """Enrich multiple CardSummary objects with Scryfall data in a single batch query.

        This eliminates N+1 queries by fetching all Scryfall data in one query
        instead of fetching each card's data individually.

        Args:
            cards: List of CardSummary objects to enrich
            scryfall_db: ScryfallDatabase instance for fetching images/prices.
                         If None, cards are returned unchanged.

        Returns:
            List of CardSummary objects with image, image_small, price_usd,
            and purchase_link fields populated from Scryfall data.
        """
        if not cards or scryfall_db is None:
            return cards

        # Extract unique card names for batch query
        names = list({card.name for card in cards})

        # Batch fetch all Scryfall data in one query
        scryfall_data = await scryfall_db.get_card_images_batch(names)

        # Enrich each card with Scryfall data
        for card in cards:
            image_data = scryfall_data.get(card.name.lower())
            if image_data:
                card.image = image_data.image_normal
                card.image_small = image_data.image_small
                card.price_usd = image_data.get_price_usd()
                card.purchase_link = image_data.purchase_tcgplayer

        return cards

    # -------------------------------------------------------------------------
    # Artist Methods
    # -------------------------------------------------------------------------

    async def get_cards_by_artist(self, artist: str) -> list[Card]:
        """Get unique cards illustrated by a specific artist.

        Returns one card per unique name (the newest printing), deduped in SQL
        using ROW_NUMBER() window function for efficiency.

        Includes collaborative works where the artist appears with others
        (e.g., "Artist A & Artist B" format).

        Args:
            artist: The artist name to search for.

        Returns:
            List of unique cards by this artist, sorted by release date (newest first).
        """
        cards: list[Card] = []
        # Match exact name, or collaborative works in any position (case-insensitive):
        # - "Artist & Other" (first)
        # - "Other & Artist" (last)
        # - "Other & Artist & Another" (middle)
        artist_lower = artist.lower()
        artist_first = f"{artist_lower} & %"
        artist_last = f"% & {artist_lower}"
        artist_middle = f"% & {artist_lower} & %"
        async with self._execute(
            f"""
            WITH artist_cards AS (
                SELECT {CARD_COLUMNS},
                    ROW_NUMBER() OVER (
                        PARTITION BY c.name, COALESCE(c.flavorName, '')
                        ORDER BY s.releaseDate DESC
                    ) as rn
                FROM cards c
                JOIN sets s ON c.setCode = s.code
                WHERE (LOWER(c.artist) = ? OR LOWER(c.artist) LIKE ? OR LOWER(c.artist) LIKE ? OR LOWER(c.artist) LIKE ?)
                    AND {EXCLUDE_EXTRAS}
            )
            SELECT {CARD_COLUMNS_PLAIN}
            FROM artist_cards
            WHERE rn = 1
            ORDER BY releaseDate DESC, name
            """,
            (artist_lower, artist_first, artist_last, artist_middle),
        ) as cursor:
            async for row in cursor:
                cards.append(self._row_to_card(row))
        return cards

    async def get_artist_stats(self, artist: str) -> ArtistStats:
        """Get statistics for an artist.

        Includes collaborative works where the artist appears with others.
        Search is case-insensitive.

        Args:
            artist: The artist name.

        Returns:
            ArtistStats with card count, sets featured, date range, and format distribution.
        """
        # Match exact name, or collaborative works in any position (case-insensitive)
        artist_lower = artist.lower()
        artist_first = f"{artist_lower} & %"
        artist_last = f"% & {artist_lower}"
        artist_middle = f"% & {artist_lower} & %"

        # Get basic stats: total cards, sets, date range
        async with self._execute(
            f"""
            SELECT
                COUNT(*) as total_cards,
                COUNT(DISTINCT c.setCode) as sets_count,
                MIN(s.releaseDate) as first_card,
                MAX(s.releaseDate) as most_recent,
                GROUP_CONCAT(DISTINCT c.setCode) as set_codes
            FROM cards c
            JOIN sets s ON c.setCode = s.code
            WHERE (LOWER(c.artist) = ? OR LOWER(c.artist) LIKE ? OR LOWER(c.artist) LIKE ? OR LOWER(c.artist) LIKE ?)
                AND {EXCLUDE_EXTRAS}
            """,
            (artist_lower, artist_first, artist_last, artist_middle),
        ) as cursor:
            row = await cursor.fetchone()
            if not row or row["total_cards"] == 0:
                return ArtistStats(
                    name=artist,
                    total_cards=0,
                    sets_featured=[],
                    first_card_date=None,
                    most_recent_date=None,
                    format_distribution={},
                )

            total_cards = row["total_cards"]
            first_card_date = row["first_card"]
            most_recent_date = row["most_recent"]
            set_codes_str = row["set_codes"]
            sets_featured = set_codes_str.split(",") if set_codes_str else []

        # Get format distribution using SQL aggregation for top formats only
        # This is much faster than fetching all rows and counting in Python
        format_distribution: dict[str, int] = {}
        top_formats = ["commander", "modern", "legacy", "vintage", "standard", "pioneer", "pauper"]
        format_cols = ", ".join(
            f"SUM(CASE WHEN l.{fmt} = 'Legal' THEN 1 ELSE 0 END) as {fmt}_count"
            for fmt in top_formats
        )
        async with self._execute(
            f"""
            SELECT {format_cols}
            FROM cards c
            JOIN cardLegalities l ON c.uuid = l.uuid
            WHERE (LOWER(c.artist) = ? OR LOWER(c.artist) LIKE ? OR LOWER(c.artist) LIKE ? OR LOWER(c.artist) LIKE ?)
                AND {EXCLUDE_EXTRAS}
            """,
            (artist_lower, artist_first, artist_last, artist_middle),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                for fmt in top_formats:
                    count = row[f"{fmt}_count"]
                    if count and count > 0:
                        format_distribution[fmt] = count

        return ArtistStats(
            name=artist,
            total_cards=total_cards,
            sets_featured=sets_featured,
            first_card_date=first_card_date,
            most_recent_date=most_recent_date,
            format_distribution=format_distribution,
        )

    async def get_all_artists(self, min_cards: int = 1) -> list[ArtistSummary]:
        """Get all artists with card counts.

        Uses in-memory caching since artist list changes infrequently but is
        expensive to compute (GROUP BY on 90k+ rows).

        Args:
            min_cards: Minimum number of cards to include an artist (default: 1).

        Returns:
            List of ArtistSummary, sorted by card count descending.
        """
        # Use cached results if available and compatible min_cards filter
        if self._artists_cache is not None and self._artists_cache_min_cards <= min_cards:
            if self._artists_cache_min_cards == min_cards:
                return self._artists_cache
            # Filter cached results for higher min_cards threshold
            return [a for a in self._artists_cache if a.card_count >= min_cards]

        artists: list[ArtistSummary] = []
        async with self._execute(
            f"""
            SELECT
                c.artist as name,
                COUNT(DISTINCT c.name) as card_count,
                COUNT(DISTINCT c.setCode) as sets_count,
                MIN(CAST(SUBSTR(s.releaseDate, 1, 4) AS INTEGER)) as first_year,
                MAX(CAST(SUBSTR(s.releaseDate, 1, 4) AS INTEGER)) as most_recent_year
            FROM cards c
            JOIN sets s ON c.setCode = s.code
            WHERE c.artist IS NOT NULL AND c.artist != '' AND {EXCLUDE_EXTRAS}
            GROUP BY c.artist
            HAVING COUNT(DISTINCT c.name) >= ?
            ORDER BY card_count DESC, c.artist
            """,
            (min_cards,),
        ) as cursor:
            async for row in cursor:
                artists.append(
                    ArtistSummary(
                        name=row["name"],
                        card_count=row["card_count"],
                        sets_count=row["sets_count"],
                        first_card_year=row["first_year"],
                        most_recent_year=row["most_recent_year"],
                    )
                )

        # Cache results for future calls
        self._artists_cache = artists
        self._artists_cache_min_cards = min_cards
        return artists

    # -------------------------------------------------------------------------
    # Set Extended Methods
    # -------------------------------------------------------------------------

    async def get_cards_in_set(self, set_code: str) -> list[Card]:
        """Get all cards in a set, sorted by collector number.

        Args:
            set_code: The set code (e.g., 'MKM', 'SNC').

        Returns:
            List of cards in the set, sorted by collector number.
        """
        cards: list[Card] = []
        async with self._execute(
            f"""
            SELECT {CARD_COLUMNS}
            FROM cards c
            JOIN sets s ON c.setCode = s.code
            WHERE LOWER(c.setCode) = LOWER(?) AND {EXCLUDE_EXTRAS}
            ORDER BY
                CAST(
                    CASE
                        WHEN c.number GLOB '[0-9]*'
                        THEN SUBSTR(c.number, 1, LENGTH(c.number) - LENGTH(LTRIM(c.number, '0123456789')))
                        ELSE '999999'
                    END AS INTEGER
                ),
                c.number
            """,
            (set_code,),
        ) as cursor:
            async for row in cursor:
                cards.append(self._row_to_card(row))
        return cards

    async def get_set_stats(self, set_code: str) -> SetStats:
        """Get statistics for a set.

        Args:
            set_code: The set code (e.g., 'MKM', 'SNC').

        Returns:
            SetStats with total cards, rarity/color distribution, mechanics, and avg CMC.
        """
        # Get total cards
        async with self._execute(
            f"""
            SELECT COUNT(*) as total
            FROM cards c
            WHERE LOWER(c.setCode) = LOWER(?) AND {EXCLUDE_EXTRAS}
            """,
            (set_code,),
        ) as cursor:
            row = await cursor.fetchone()
            total_cards = row["total"] if row else 0

        if total_cards == 0:
            return SetStats(
                set_code=set_code,
                total_cards=0,
                rarity_distribution={},
                color_distribution={},
                mechanics=[],
                avg_cmc=None,
            )

        # Get rarity distribution
        rarity_distribution: dict[str, int] = {}
        async with self._execute(
            f"""
            SELECT c.rarity, COUNT(*) as count
            FROM cards c
            WHERE LOWER(c.setCode) = LOWER(?) AND {EXCLUDE_EXTRAS} AND c.rarity IS NOT NULL
            GROUP BY c.rarity
            """,
            (set_code,),
        ) as cursor:
            async for row in cursor:
                rarity_distribution[row["rarity"]] = row["count"]

        # Get color distribution (count cards containing each color)
        color_distribution: dict[str, int] = {}
        async with self._execute(
            f"""
            SELECT c.colors
            FROM cards c
            WHERE LOWER(c.setCode) = LOWER(?) AND {EXCLUDE_EXTRAS} AND c.colors IS NOT NULL
            """,
            (set_code,),
        ) as cursor:
            async for row in cursor:
                colors = self._parse_list(row["colors"])
                if colors:
                    for color in colors:
                        color_distribution[color] = color_distribution.get(color, 0) + 1

        # Get unique mechanics/keywords
        mechanics: list[str] = []
        async with self._execute(
            f"""
            SELECT DISTINCT c.keywords
            FROM cards c
            WHERE LOWER(c.setCode) = LOWER(?) AND {EXCLUDE_EXTRAS}
                AND c.keywords IS NOT NULL AND c.keywords != ''
            """,
            (set_code,),
        ) as cursor:
            keywords_set: set[str] = set()
            async for row in cursor:
                keyword_list = self._parse_list(row["keywords"])
                if keyword_list:
                    keywords_set.update(keyword_list)
            mechanics = sorted(keywords_set)

        # Get average CMC (excluding lands)
        async with self._execute(
            f"""
            SELECT AVG(c.manaValue) as avg_cmc
            FROM cards c
            WHERE LOWER(c.setCode) = LOWER(?) AND {EXCLUDE_EXTRAS}
                AND c.manaValue IS NOT NULL
                AND c.type NOT LIKE '%Land%'
            """,
            (set_code,),
        ) as cursor:
            row = await cursor.fetchone()
            avg_cmc = round(row["avg_cmc"], 2) if row and row["avg_cmc"] else None

        return SetStats(
            set_code=set_code,
            total_cards=total_cards,
            rarity_distribution=rarity_distribution,
            color_distribution=color_distribution,
            mechanics=mechanics,
            avg_cmc=avg_cmc,
        )

    # -------------------------------------------------------------------------
    # Dashboard Methods (Landing Page)
    # -------------------------------------------------------------------------

    async def get_random_artist_for_spotlight(self, min_cards: int = 20) -> ArtistSummary | None:
        """Get a random artist for the dashboard spotlight.

        Uses a deterministic daily seed so the same artist appears all day.
        First checks the artist_stats_cache table (if populated), then falls back
        to in-memory cache, then to live database query.

        Args:
            min_cards: Minimum number of cards an artist must have to be eligible.

        Returns:
            ArtistSummary for the selected artist, or None if no eligible artists.
        """
        import hashlib
        from datetime import date

        # Get deterministic seed for today
        today = date.today().isoformat()
        seed = int(hashlib.md5(today.encode()).hexdigest()[:8], 16)

        # Try the artist_stats_cache table first (fastest if populated)
        if await is_artist_cache_populated(self._db):
            cached = await get_cached_artist_for_spotlight(self._db, min_cards)
            if cached:
                artist, card_count, sets_count, first_year, last_year = cached
                return ArtistSummary(
                    name=artist,
                    card_count=card_count,
                    sets_count=sets_count,
                    first_card_year=first_year,
                    most_recent_year=last_year,
                )

        # Use in-memory cached artists if available (instant lookup)
        if self._artists_cache is not None and self._artists_cache_min_cards <= min_cards:
            eligible = [a for a in self._artists_cache if a.card_count >= min_cards]
            if eligible:
                return eligible[seed % len(eligible)]
            return None

        # Fallback: query database directly
        async with self._execute(
            f"""
            SELECT c.artist as name, COUNT(DISTINCT c.name) as card_count
            FROM cards c
            WHERE c.artist IS NOT NULL AND c.artist != '' AND {EXCLUDE_EXTRAS}
            GROUP BY c.artist
            HAVING COUNT(DISTINCT c.name) >= ?
            ORDER BY c.artist
            LIMIT 100
            """,
            (min_cards,),
        ) as cursor:
            candidates = []
            async for row in cursor:
                candidates.append((row["name"], row["card_count"]))

        if not candidates:
            return None

        # Select artist deterministically based on seed
        selected_name, card_count = candidates[seed % len(candidates)]

        # Get full details for selected artist only
        async with self._execute(
            f"""
            SELECT
                COUNT(DISTINCT c.setCode) as sets_count,
                MIN(CAST(SUBSTR(s.releaseDate, 1, 4) AS INTEGER)) as first_year,
                MAX(CAST(SUBSTR(s.releaseDate, 1, 4) AS INTEGER)) as most_recent_year
            FROM cards c
            JOIN sets s ON c.setCode = s.code
            WHERE c.artist = ? AND {EXCLUDE_EXTRAS}
            """,
            (selected_name,),
        ) as cursor:
            detail_row = await cursor.fetchone()
            if detail_row is not None:
                return ArtistSummary(
                    name=selected_name,
                    card_count=card_count,
                    sets_count=detail_row["sets_count"],
                    first_card_year=detail_row["first_year"],
                    most_recent_year=detail_row["most_recent_year"],
                )

        # Fallback if details query fails
        return ArtistSummary(
            name=selected_name,
            card_count=card_count,
            sets_count=0,
            first_card_year=None,
            most_recent_year=None,
        )

    async def refresh_artist_stats_cache(self) -> int:
        """Refresh the artist stats cache table.

        This pre-computes artist statistics and stores them in the
        artist_stats_cache table for fast dashboard queries.

        Returns:
            Number of artists cached.
        """
        return await _refresh_artist_stats_cache(self._db)

    async def get_featured_cards_for_artist(self, artist_name: str, limit: int = 4) -> list[Card]:
        """Get featured cards for an artist (prioritizing rare/mythic).

        Args:
            artist_name: The artist's name.
            limit: Maximum number of cards to return.

        Returns:
            List of featured cards, prioritized by rarity.
        """
        cards: list[Card] = []
        async with self._execute(
            f"""
            SELECT {CARD_COLUMNS}
            FROM cards c
            JOIN sets s ON c.setCode = s.code
            WHERE c.artist = ? AND {EXCLUDE_EXTRAS}
            ORDER BY
                CASE c.rarity
                    WHEN 'mythic' THEN 1
                    WHEN 'rare' THEN 2
                    WHEN 'uncommon' THEN 3
                    ELSE 4
                END,
                s.releaseDate DESC
            LIMIT ?
            """,
            (artist_name, limit),
        ) as cursor:
            async for row in cursor:
                cards.append(self._row_to_card(row))
        return cards

    async def get_latest_sets(self, limit: int = 3) -> list[Set]:
        """Get the most recently released sets.

        Args:
            limit: Maximum number of sets to return.

        Returns:
            List of sets sorted by release date (newest first).
        """
        sets: list[Set] = []
        async with self._execute(
            """
            SELECT code, name, type, releaseDate, block, baseSetSize,
                   totalSetSize, isOnlineOnly, isFoilOnly, keyruneCode
            FROM sets
            WHERE releaseDate <= date('now')
              AND type IN ('expansion', 'core', 'masters', 'draft_innovation')
              AND (isOnlineOnly IS NULL OR isOnlineOnly = 0)
            ORDER BY releaseDate DESC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            async for row in cursor:
                sets.append(self._row_to_set(row))
        return sets

    async def get_random_card_of_day(self) -> Card:
        """Get a deterministic 'card of the day' (same card all day).

        Uses date-based seed with efficient rowid-based selection to avoid
        expensive COUNT + OFFSET queries.

        Returns:
            A Card object for the card of the day.

        Raises:
            CardNotFoundError: If no eligible cards exist.
        """
        import hashlib
        from datetime import date

        # Get deterministic seed for today (different from artist seed)
        today = f"card:{date.today().isoformat()}"
        seed = int(hashlib.md5(today.encode()).hexdigest()[:8], 16)

        # Get max rowid for efficient random selection
        async with self._execute("SELECT MAX(rowid) FROM cards") as cursor:
            row = await cursor.fetchone()
            max_rowid = row[0] if row and row[0] else 0

        if max_rowid == 0:
            raise CardNotFoundError("card_of_day")

        # Try multiple rowid offsets to find a valid rare/mythic card
        # This is much faster than COUNT + OFFSET on full table
        for attempt in range(20):
            # Use seed + attempt to generate different rowids
            random_rowid = ((seed + attempt * 7919) % max_rowid) + 1

            async with self._execute(
                f"""
                SELECT {CARD_COLUMNS}
                FROM cards c
                JOIN sets s ON c.setCode = s.code
                WHERE c.rowid >= ?
                  AND {EXCLUDE_EXTRAS}
                  AND c.rarity IN ('rare', 'mythic')
                  AND c.type NOT LIKE '%Basic%'
                LIMIT 1
                """,
                (random_rowid,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    card = self._row_to_card(row)
                    # Skip legalities for dashboard - not needed for preview
                    return card

        # Fallback: get any rare/mythic card
        async with self._execute(
            f"""
            SELECT {CARD_COLUMNS}
            FROM cards c
            JOIN sets s ON c.setCode = s.code
            WHERE {EXCLUDE_EXTRAS}
              AND c.rarity IN ('rare', 'mythic')
              AND c.type NOT LIKE '%Basic%'
            LIMIT 1
            """,
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_card(row)

        raise CardNotFoundError("card_of_day")

    # -------------------------------------------------------------------------
    # Block Browsing Methods
    # -------------------------------------------------------------------------

    async def get_all_blocks(self) -> list[BlockSummary]:
        """Get all blocks with their sets grouped by storyline.

        Returns:
            List of BlockSummary objects sorted by most recent release.
        """
        blocks: dict[str, BlockSummary] = {}

        # Query all sets that have a block, grouped by block name
        async with self._execute(
            """
            SELECT
                s.block,
                s.code,
                s.name,
                s.type,
                s.releaseDate,
                s.totalSetSize
            FROM sets s
            WHERE s.block IS NOT NULL AND s.block != ''
            ORDER BY s.block, s.releaseDate
            """,
        ) as cursor:
            async for row in cursor:
                block_name = row["block"]

                if block_name not in blocks:
                    blocks[block_name] = BlockSummary(
                        name=block_name,
                        set_count=0,
                        total_cards=0,
                        first_release=row["releaseDate"],
                        last_release=row["releaseDate"],
                        sets=[],
                    )

                block = blocks[block_name]
                block.sets.append(
                    SetSummary(
                        code=row["code"],
                        name=row["name"],
                        type=row["type"],
                        release_date=row["releaseDate"],
                    )
                )
                block.set_count += 1
                block.total_cards += row["totalSetSize"] or 0

                # Update date range
                if row["releaseDate"]:
                    if not block.first_release or row["releaseDate"] < block.first_release:
                        block.first_release = row["releaseDate"]
                    if not block.last_release or row["releaseDate"] > block.last_release:
                        block.last_release = row["releaseDate"]

        # Sort blocks by most recent release date (newest first)
        sorted_blocks = sorted(
            blocks.values(),
            key=lambda b: b.last_release or "",
            reverse=True,
        )

        return sorted_blocks

    async def get_sets_by_block(self, block_name: str) -> list[Set]:
        """Get all sets in a specific block.

        Args:
            block_name: The block name to search for.

        Returns:
            List of Set objects in the block, sorted by release date.
        """
        sets_list: list[Set] = []
        async with self._execute(
            """
            SELECT code, name, type, releaseDate, block, baseSetSize,
                   totalSetSize, isOnlineOnly, isFoilOnly, keyruneCode
            FROM sets
            WHERE LOWER(block) = LOWER(?)
            ORDER BY releaseDate
            """,
            (block_name,),
        ) as cursor:
            async for row in cursor:
                sets_list.append(self._row_to_set(row))
        return sets_list

    async def get_recent_sets(
        self,
        limit: int = 10,
        include_upcoming: bool = False,
        set_types: list[str] | None = None,
    ) -> list[Set]:
        """Get recent and optionally upcoming sets.

        Args:
            limit: Maximum number of sets to return.
            include_upcoming: If True, include sets with future release dates.
            set_types: Optional list of set types to filter by.

        Returns:
            List of sets sorted by release date (newest first).
        """
        conditions = ["(isOnlineOnly IS NULL OR isOnlineOnly = 0)"]
        params: list[Any] = []

        if not include_upcoming:
            conditions.append("releaseDate <= date('now')")

        if set_types:
            placeholders = ",".join("?" * len(set_types))
            conditions.append(f"LOWER(type) IN ({placeholders})")
            params.extend([t.lower() for t in set_types])

        where_clause = " AND ".join(conditions)

        recent_sets: list[Set] = []
        async with self._execute(
            f"""
            SELECT code, name, type, releaseDate, block, baseSetSize,
                   totalSetSize, isOnlineOnly, isFoilOnly, keyruneCode
            FROM sets
            WHERE {where_clause}
            ORDER BY releaseDate DESC
            LIMIT ?
            """,
            (*params, limit),
        ) as cursor:
            async for row in cursor:
                recent_sets.append(self._row_to_set(row))
        return recent_sets

    async def search_artists(self, query: str, min_cards: int = 1) -> list[ArtistSummary]:
        """Search artists by name.

        Uses cached artist list if available for instant filtering,
        otherwise falls back to database query.

        Args:
            query: Search query (partial name match).
            min_cards: Minimum number of cards to include an artist.

        Returns:
            List of matching ArtistSummary objects, sorted by card count.
        """
        # Use cached results if available - much faster for search
        if self._artists_cache is not None and self._artists_cache_min_cards <= min_cards:
            query_lower = query.lower()
            return [
                a
                for a in self._artists_cache
                if query_lower in a.name.lower() and a.card_count >= min_cards
            ][:100]

        # Fallback to database query
        artists: list[ArtistSummary] = []
        async with self._execute(
            f"""
            SELECT
                c.artist as name,
                COUNT(DISTINCT c.name) as card_count,
                COUNT(DISTINCT c.setCode) as sets_count,
                MIN(CAST(SUBSTR(s.releaseDate, 1, 4) AS INTEGER)) as first_year,
                MAX(CAST(SUBSTR(s.releaseDate, 1, 4) AS INTEGER)) as most_recent_year
            FROM cards c
            JOIN sets s ON c.setCode = s.code
            WHERE c.artist LIKE ? AND c.artist IS NOT NULL AND {EXCLUDE_EXTRAS}
            GROUP BY c.artist
            HAVING COUNT(DISTINCT c.name) >= ?
            ORDER BY card_count DESC, c.artist
            LIMIT 100
            """,
            (f"%{query}%", min_cards),
        ) as cursor:
            async for row in cursor:
                artists.append(
                    ArtistSummary(
                        name=row["name"],
                        card_count=row["card_count"],
                        sets_count=row["sets_count"],
                        first_card_year=row["first_year"],
                        most_recent_year=row["most_recent_year"],
                    )
                )
        return artists
