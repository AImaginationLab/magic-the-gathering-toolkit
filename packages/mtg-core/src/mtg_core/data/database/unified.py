"""Unified MTG database combining card data, images, prices, and rulings.

This replaces the separate MTGDatabase and ScryfallDatabase classes with a single
database that has complete card data in every query.
"""

from __future__ import annotations

import json
import logging
import random
from typing import TYPE_CHECKING, Any, cast

import aiosqlite

from ...exceptions import CardNotFoundError, SetNotFoundError
from ..models import Card, CardLegality, CardRuling, Set
from ..models.responses import ArtistSummary
from .base import BaseDatabase
from .cache import CardCache

if TYPE_CHECKING:
    from ..models.inputs import SearchCardsInput

logger = logging.getLogger(__name__)

# Exclude extras from normal card searches
EXCLUDE_EXTRAS = "is_promo = 0 AND is_digital_only = 0"
EXCLUDE_TOKENS = "is_token = 0"


class UnifiedDatabase(BaseDatabase):
    """Unified database access for MTG cards, images, prices, and rulings.

    All card queries return complete data including images and prices.
    No more null checks or fallback logic required.
    """

    def __init__(
        self,
        db: aiosqlite.Connection,
        cache: CardCache | None = None,
        max_connections: int = 5,
    ):
        super().__init__(db, max_connections)
        self._cache = cache or CardCache()
        self._fts_available: bool | None = None

    @staticmethod
    def _parse_json_list(value: str | None) -> list[str] | None:
        """Parse JSON array string into list."""
        if not value:
            return None
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else None
        except (json.JSONDecodeError, TypeError):
            return None

    def _row_to_card(self, row: aiosqlite.Row) -> Card:
        """Convert a database row to a Card model with all data."""
        return Card(
            uuid=row["id"],
            name=row["name"],
            flavor_name=row["flavor_name"],
            layout=row["layout"],
            mana_cost=row["mana_cost"],
            cmc=row["cmc"],
            colors=self._parse_json_list(row["colors"]),
            color_identity=self._parse_json_list(row["color_identity"]),
            type=row["type_line"],
            text=row["oracle_text"],
            flavor=row["flavor_text"],
            power=row["power"],
            toughness=row["toughness"],
            loyalty=row["loyalty"],
            defense=row["defense"],
            keywords=self._parse_json_list(row["keywords"]),
            set_code=row["set_code"],
            set_name=row["set_name"],
            rarity=row["rarity"],
            number=row["collector_number"],
            artist=row["artist"],
            release_date=row["release_date"],
            edhrec_rank=row["edhrec_rank"],
            # Images
            image_small=row["image_small"],
            image_normal=row["image_normal"],
            image_large=row["image_large"],
            image_png=row["image_png"],
            image_art_crop=row["image_art_crop"],
            image_border_crop=row["image_border_crop"],
            # Prices
            price_usd=row["price_usd"],
            price_usd_foil=row["price_usd_foil"],
            price_eur=row["price_eur"],
            price_eur_foil=row["price_eur_foil"],
            # Links
            purchase_tcgplayer=row["purchase_tcgplayer"],
            purchase_cardmarket=row["purchase_cardmarket"],
            purchase_cardhoarder=row["purchase_cardhoarder"],
            link_edhrec=row["link_edhrec"],
            link_gatherer=row["link_gatherer"],
            # Visual
            illustration_id=row["illustration_id"],
            highres_image=bool(row["highres_image"]),
            border_color=row["border_color"],
            frame=row["frame"],
            full_art=bool(row["full_art"]),
            finishes=self._parse_json_list(row["finishes"]) or [],
        )

    def _row_to_set(self, row: aiosqlite.Row) -> Set:
        """Convert a database row to a Set model."""
        return Set(
            code=row["code"],
            name=row["name"],
            type=row["set_type"],
            release_date=row["release_date"],
            block=row["block"],
            base_set_size=row["base_set_size"],
            total_set_size=row["total_set_size"] or row["card_count"],
            card_count=row["card_count"],
            is_online_only=bool(row["is_online_only"])
            if row["is_online_only"] is not None
            else None,
            is_foil_only=bool(row["is_foil_only"]) if row["is_foil_only"] is not None else None,
            keyrune_code=row["keyrune_code"],
            icon_svg_uri=row["icon_svg_uri"],
        )

    async def get_card_by_name(self, name: str, include_extras: bool = True) -> Card:
        """Get a card by exact name. Returns most recent non-promo printing.

        Raises CardNotFoundError if not found.
        """
        cache_key = f"name:{name.lower()}:extras={include_extras}"
        cached = await self._cache.get(cache_key)
        if cached:
            return cached

        async with self._execute(
            f"""
            SELECT * FROM cards
            WHERE name COLLATE NOCASE = ?
            AND {EXCLUDE_EXTRAS}
            ORDER BY release_date DESC
            LIMIT 1
            """,
            (name,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                card = self._row_to_card(row)
                if include_extras:
                    card.legalities = await self._get_legalities(row["id"])
                    card.rulings = await self._get_rulings(row["oracle_id"])
                await self._cache.set(cache_key, card)
                return card

        raise CardNotFoundError(name)

    async def get_card_by_uuid(self, uuid: str, include_extras: bool = True) -> Card:
        """Get a card by Scryfall UUID.

        Raises CardNotFoundError if not found.
        """
        async with self._execute(
            "SELECT * FROM cards WHERE id = ?",
            (uuid,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                card = self._row_to_card(row)
                if include_extras:
                    card.legalities = await self._get_legalities(row["id"])
                    card.rulings = await self._get_rulings(row["oracle_id"])
                return card

        raise CardNotFoundError(uuid)

    async def get_card_by_set_and_number(self, set_code: str, collector_number: str) -> Card | None:
        """Look up a card by set code and collector number.

        Works for both regular cards AND tokens (tokens have is_token=1).
        """
        normalized_number = collector_number.lstrip("0") or "0"

        async with self._execute(
            """
            SELECT * FROM cards
            WHERE set_code COLLATE NOCASE = ?
            AND (collector_number = ? OR collector_number = ?)
            LIMIT 1
            """,
            (set_code, collector_number, normalized_number),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_card(row)
        return None

    async def get_prices_by_set_and_numbers(
        self, printings: list[tuple[str, str]]
    ) -> dict[tuple[str, str], tuple[int | None, int | None]]:
        """Batch lookup prices by (set_code, collector_number) pairs.

        Returns dict mapping (set_code.upper(), collector_number) -> (price_usd, price_usd_foil).
        Prices are in cents (divide by 100 for dollars).

        Much faster than get_cards_by_set_and_numbers() for price-only needs
        since it only fetches 4 columns instead of 40+.
        """
        if not printings:
            return {}

        results: dict[tuple[str, str], tuple[int | None, int | None]] = {}
        batch_size = 200

        for i in range(0, len(printings), batch_size):
            batch = printings[i : i + batch_size]

            conditions = []
            params: list[str] = []
            for set_code, collector_number in batch:
                normalized = collector_number.lstrip("0") or "0"
                conditions.append(
                    "(UPPER(set_code) = ? AND (collector_number = ? OR collector_number = ?))"
                )
                params.extend([set_code.upper(), collector_number, normalized])

            query = f"""
                SELECT set_code, collector_number, price_usd, price_usd_foil
                FROM cards
                WHERE {" OR ".join(conditions)}
            """

            async with self._execute(query, tuple(params)) as cursor:
                async for row in cursor:
                    if row[0] and row[1]:
                        key = (row[0].upper(), row[1])
                        results[key] = (row[2], row[3])

        return results

    async def get_prices_by_names(
        self, names: list[str]
    ) -> dict[str, tuple[int | None, int | None]]:
        """Batch lookup prices by card name.

        Returns dict mapping name.lower() -> (price_usd, price_usd_foil).
        Prices are in cents. Returns the first matching price found.

        Much faster than get_cards_by_names() for price-only needs.
        """
        if not names:
            return {}

        results: dict[str, tuple[int | None, int | None]] = {}
        batch_size = 200

        for i in range(0, len(names), batch_size):
            batch = names[i : i + batch_size]
            placeholders = ",".join("?" * len(batch))

            query = f"""
                SELECT name, price_usd, price_usd_foil
                FROM cards
                WHERE name IN ({placeholders})
                GROUP BY name
            """

            async with self._execute(query, batch) as cursor:
                async for row in cursor:
                    if row[0]:
                        results[row[0].lower()] = (row[1], row[2])

        return results

    async def get_all_printings(self, name: str) -> list[Card]:
        """Get all printings of a card by name (across all sets)."""
        printings: list[Card] = []
        async with self._execute(
            """
            SELECT * FROM cards
            WHERE name COLLATE NOCASE = ?
            ORDER BY release_date DESC, set_code
            """,
            (name,),
        ) as cursor:
            async for row in cursor:
                printings.append(self._row_to_card(row))
        return printings

    async def get_unique_artworks(self, name: str) -> list[Card]:
        """Get all unique artworks for a card (one per illustration_id).

        Uses art_priority to prefer borderless > full_art > regular.
        """
        artworks: list[Card] = []
        async with self._execute(
            """
            SELECT c.* FROM cards c
            INNER JOIN (
                SELECT illustration_id, MIN(art_priority || set_code || id) AS best
                FROM cards
                WHERE name COLLATE NOCASE = ?
                GROUP BY illustration_id
            ) ranked ON c.illustration_id = ranked.illustration_id
                AND (c.art_priority || c.set_code || c.id) = ranked.best
            WHERE c.name COLLATE NOCASE = ?
            ORDER BY c.art_priority, c.set_code
            """,
            (name, name),
        ) as cursor:
            async for row in cursor:
                artworks.append(self._row_to_card(row))
        return artworks

    async def search_cards(self, filters: SearchCardsInput) -> tuple[list[Card], int]:
        """Search for cards matching the given filters.

        Returns:
            Tuple of (cards on this page, total matching count)
        """
        conditions: list[str] = [EXCLUDE_EXTRAS]
        # Note: Tokens are included in searches. They are excluded from recommendations/synergy.
        params: list[Any] = []

        if filters.name:
            # Search both name and flavor_name (e.g., SpongeBob → Jodah, the Unifier)
            conditions.append("(name COLLATE NOCASE LIKE ? OR flavor_name COLLATE NOCASE LIKE ?)")
            params.append(f"%{filters.name}%")
            params.append(f"%{filters.name}%")

        if filters.type:
            conditions.append("type_line LIKE ?")
            params.append(f"%{filters.type}%")

        if filters.text:
            conditions.append("oracle_text LIKE ?")
            params.append(f"%{filters.text}%")

        if filters.set_code:
            conditions.append("set_code COLLATE NOCASE = ?")
            params.append(filters.set_code)

        if filters.rarity:
            conditions.append("rarity COLLATE NOCASE = ?")
            params.append(filters.rarity)

        if filters.cmc is not None:
            conditions.append("cmc = ?")
            params.append(filters.cmc)

        if filters.cmc_min is not None:
            conditions.append("cmc >= ?")
            params.append(filters.cmc_min)

        if filters.cmc_max is not None:
            conditions.append("cmc <= ?")
            params.append(filters.cmc_max)

        if filters.colors:
            for color in filters.colors:
                conditions.append("colors LIKE ?")
                params.append(f'%"{color}"%')

        if filters.color_identity:
            for color in filters.color_identity:
                conditions.append("color_identity LIKE ?")
                params.append(f'%"{color}"%')

        # Use generated columns for legality filtering
        if filters.format_legal:
            fmt = filters.format_legal.lower()
            if fmt == "commander":
                conditions.append("legal_commander = 1")
            elif fmt == "modern":
                conditions.append("legal_modern = 1")
            elif fmt == "standard":
                conditions.append("legal_standard = 1")
            else:
                conditions.append(f"json_extract(legalities, '$.{fmt}') = 'legal'")

        if filters.artist:
            conditions.append("artist COLLATE NOCASE LIKE ?")
            params.append(f"%{filters.artist}%")

        if filters.keywords:
            for kw in filters.keywords:
                conditions.append("keywords LIKE ?")
                params.append(f'%"{kw}"%')

        where_clause = " AND ".join(conditions)

        # Get total count
        count_query = f"""
            SELECT COUNT(*) FROM (
                SELECT DISTINCT name FROM cards WHERE {where_clause}
            )
        """
        async with self._execute(count_query, params) as cursor:
            row = await cursor.fetchone()
            total_count = row[0] if row else 0

        # Build ORDER BY
        order_direction = "DESC" if filters.sort_order == "desc" else "ASC"
        sort_map = {
            "name": "name",
            "cmc": "cmc",
            "rarity": "CASE rarity WHEN 'common' THEN 1 WHEN 'uncommon' THEN 2 WHEN 'rare' THEN 3 WHEN 'mythic' THEN 4 ELSE 0 END",
            "price": "price_usd",
        }
        sort_col = sort_map.get(filters.sort_by or "name", "name")

        # Get paginated results (one per card name)
        query = f"""
            SELECT * FROM cards
            WHERE {where_clause}
            GROUP BY name
            ORDER BY {sort_col} {order_direction}
            LIMIT ? OFFSET ?
        """
        page_params = [*params, filters.page_size, (filters.page - 1) * filters.page_size]

        cards: list[Card] = []
        async with self._execute(query, page_params) as cursor:
            async for row in cursor:
                cards.append(self._row_to_card(row))

        return cards, total_count

    async def _get_legalities(self, card_id: str) -> list[CardLegality]:
        """Get format legalities for a card from JSON."""
        async with self._execute(
            "SELECT legalities FROM cards WHERE id = ?",
            (card_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row or not row["legalities"]:
                return []

            legalities_dict = json.loads(row["legalities"])
            return [
                CardLegality(format=fmt, legality=status)
                for fmt, status in legalities_dict.items()
                if status  # Skip null/empty values
            ]

    async def _get_rulings(self, oracle_id: str) -> list[CardRuling]:
        """Get rulings for a card by oracle_id."""
        rulings: list[CardRuling] = []
        async with self._execute(
            "SELECT published_at, comment FROM rulings WHERE oracle_id = ? ORDER BY published_at DESC",
            (oracle_id,),
        ) as cursor:
            async for row in cursor:
                rulings.append(
                    CardRuling(date=row["published_at"] or "", text=row["comment"] or "")
                )
        return rulings

    async def get_card_rulings(self, name: str) -> list[CardRuling]:
        """Get rulings for a card by name."""
        async with self._execute(
            "SELECT oracle_id FROM cards WHERE name COLLATE NOCASE = ? LIMIT 1",
            (name,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return []
            return await self._get_rulings(row["oracle_id"])

    async def get_card_legalities(self, name: str) -> dict[str, str]:
        """Get format legalities for a card by name as a dict."""
        async with self._execute(
            "SELECT legalities FROM cards WHERE name COLLATE NOCASE = ? LIMIT 1",
            (name,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row or not row["legalities"]:
                return {}
            return cast(dict[str, str], json.loads(row["legalities"]))

    async def get_set(self, code: str) -> Set:
        """Get a set by its code. Raises SetNotFoundError if not found."""
        async with self._execute(
            "SELECT * FROM sets WHERE code COLLATE NOCASE = ?",
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
        """Get all sets, optionally filtered by type."""
        conditions: list[str] = []
        params: list[Any] = []

        if set_type:
            conditions.append("set_type COLLATE NOCASE = ?")
            params.append(set_type)

        if not include_online_only:
            conditions.append("(is_online_only IS NULL OR is_online_only = 0)")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sets: list[Set] = []
        async with self._execute(
            f"""
            SELECT * FROM sets
            WHERE {where_clause}
            ORDER BY release_date DESC
            """,
            params,
        ) as cursor:
            async for row in cursor:
                sets.append(self._row_to_set(row))
        return sets

    async def search_sets(self, name: str) -> list[Set]:
        """Search sets by name."""
        sets: list[Set] = []
        async with self._execute(
            """
            SELECT * FROM sets
            WHERE name LIKE ?
            ORDER BY release_date DESC
            """,
            (f"%{name}%",),
        ) as cursor:
            async for row in cursor:
                sets.append(self._row_to_set(row))
        return sets

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

        async with self._execute("SELECT value FROM meta WHERE key = 'created_at'") as cursor:
            row = await cursor.fetchone()
            if row:
                stats["created_at"] = row[0]

        async with self._execute("SELECT value FROM meta WHERE key = 'schema_version'") as cursor:
            row = await cursor.fetchone()
            if row:
                stats["schema_version"] = row[0]

        return stats

    async def get_random_card(self) -> Card:
        """Get a random card using efficient rowid selection."""
        async with self._execute("SELECT MAX(rowid) FROM cards") as cursor:
            row = await cursor.fetchone()
            max_rowid = row[0] if row and row[0] else 0

        if max_rowid == 0:
            raise CardNotFoundError("random")

        for _ in range(10):
            random_rowid = random.randint(1, max_rowid)
            async with self._execute(
                f"""
                SELECT * FROM cards
                WHERE rowid >= ? AND {EXCLUDE_EXTRAS} AND {EXCLUDE_TOKENS}
                LIMIT 1
                """,
                (random_rowid,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    card = self._row_to_card(row)
                    card.legalities = await self._get_legalities(row["id"])
                    card.rulings = await self._get_rulings(row["oracle_id"])
                    return card

        # Fallback
        async with self._execute(
            f"SELECT * FROM cards WHERE {EXCLUDE_EXTRAS} AND {EXCLUDE_TOKENS} LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                card = self._row_to_card(row)
                card.legalities = await self._get_legalities(row["id"])
                card.rulings = await self._get_rulings(row["oracle_id"])
                return card

        raise CardNotFoundError("random")

    async def get_cards_by_names(
        self,
        names: list[str],
        include_extras: bool = False,
    ) -> dict[str, Card]:
        """Batch load cards by name, return name->Card mapping."""
        if not names:
            return {}

        results: dict[str, Card] = {}
        names_to_fetch: list[str] = []

        for name in names:
            cache_key = f"name:{name.lower()}:extras={include_extras}"
            cached = await self._cache.get(cache_key)
            if cached:
                results[name.lower()] = cached
            else:
                names_to_fetch.append(name)

        if not names_to_fetch:
            return results

        placeholders = ",".join("?" * len(names_to_fetch))
        query = f"""
            SELECT * FROM cards
            WHERE name IN ({placeholders}) AND {EXCLUDE_EXTRAS}
            ORDER BY release_date DESC
        """

        name_to_row: dict[str, aiosqlite.Row] = {}
        async with self._execute(query, names_to_fetch) as cursor:
            async for row in cursor:
                name_lower = row["name"].lower()
                if name_lower not in name_to_row:
                    name_to_row[name_lower] = row

        for name_lower, row in name_to_row.items():
            card = self._row_to_card(row)
            if include_extras:
                card.legalities = await self._get_legalities(row["id"])
                card.rulings = await self._get_rulings(row["oracle_id"])
            cache_key = f"name:{name_lower}:extras={include_extras}"
            await self._cache.set(cache_key, card)
            results[name_lower] = card

        return results

    async def search_by_price(
        self,
        min_price: float | None = None,
        max_price: float | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> list[Card]:
        """Search cards by price range (prices in USD)."""
        conditions = ["price_usd IS NOT NULL", EXCLUDE_EXTRAS]
        params: list[Any] = []

        if min_price is not None:
            conditions.append("price_usd >= ?")
            params.append(int(min_price * 100))
        if max_price is not None:
            conditions.append("price_usd <= ?")
            params.append(int(max_price * 100))

        where_clause = " AND ".join(conditions)
        offset = (page - 1) * page_size

        cards: list[Card] = []
        async with self._execute(
            f"""
            SELECT * FROM cards
            WHERE {where_clause}
            ORDER BY price_usd DESC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ) as cursor:
            async for row in cursor:
                cards.append(self._row_to_card(row))
        return cards

    async def get_all_keywords(self) -> set[str]:
        """Get all unique keywords from the cards table.

        Keywords are stored as JSON arrays in the database.
        """
        keywords: set[str] = set()
        async with self._execute(
            "SELECT DISTINCT keywords FROM cards WHERE keywords IS NOT NULL AND keywords != ''"
        ) as cursor:
            async for row in cursor:
                if row[0]:
                    keyword_list = self._parse_json_list(row[0])
                    if keyword_list:
                        keywords.update(keyword_list)
        return keywords

    async def get_random_artist_for_spotlight(self, min_cards: int = 20) -> ArtistSummary | None:
        """Get a random artist for the dashboard spotlight.

        Uses a deterministic daily seed so the same artist appears all day.

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

        # Query database for eligible artists
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
                COUNT(DISTINCT c.set_code) as sets_count,
                MIN(CAST(SUBSTR(s.release_date, 1, 4) AS INTEGER)) as first_year,
                MAX(CAST(SUBSTR(s.release_date, 1, 4) AS INTEGER)) as most_recent_year
            FROM cards c
            JOIN sets s ON c.set_code = s.code
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
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY name, COALESCE(flavor_text, '')
                        ORDER BY release_date DESC
                    ) as rn
                FROM cards
                WHERE (LOWER(artist) = ? OR LOWER(artist) LIKE ? OR LOWER(artist) LIKE ? OR LOWER(artist) LIKE ?)
                    AND {EXCLUDE_EXTRAS}
            )
            SELECT *
            FROM artist_cards
            WHERE rn = 1
            ORDER BY release_date DESC, name
            """,
            (artist_lower, artist_first, artist_last, artist_middle),
        ) as cursor:
            async for row in cursor:
                cards.append(self._row_to_card(row))
        return cards

    async def get_all_artists(self, min_cards: int = 1) -> list[ArtistSummary]:
        """Get all artists with their card counts.

        Args:
            min_cards: Minimum number of cards an artist must have.

        Returns:
            List of ArtistSummary sorted by card count (descending).
        """
        artists: list[ArtistSummary] = []
        async with self._execute(
            f"""
            SELECT
                c.artist as name,
                COUNT(DISTINCT c.name) as card_count,
                COUNT(DISTINCT c.set_code) as sets_count,
                MIN(CAST(SUBSTR(c.release_date, 1, 4) AS INTEGER)) as first_year,
                MAX(CAST(SUBSTR(c.release_date, 1, 4) AS INTEGER)) as most_recent_year
            FROM cards c
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
        return artists

    async def search_artists(self, query: str, min_cards: int = 1) -> list[ArtistSummary]:
        """Search artists by name.

        Args:
            query: Search string to match against artist names.
            min_cards: Minimum number of cards an artist must have.

        Returns:
            List of matching ArtistSummary sorted by card count (descending).
        """
        artists: list[ArtistSummary] = []
        async with self._execute(
            f"""
            SELECT
                c.artist as name,
                COUNT(DISTINCT c.name) as card_count,
                COUNT(DISTINCT c.set_code) as sets_count,
                MIN(CAST(SUBSTR(c.release_date, 1, 4) AS INTEGER)) as first_year,
                MAX(CAST(SUBSTR(c.release_date, 1, 4) AS INTEGER)) as most_recent_year
            FROM cards c
            WHERE c.artist IS NOT NULL AND c.artist != ''
                AND c.artist LIKE ?
                AND {EXCLUDE_EXTRAS}
            GROUP BY c.artist
            HAVING COUNT(DISTINCT c.name) >= ?
            ORDER BY card_count DESC, c.artist
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
