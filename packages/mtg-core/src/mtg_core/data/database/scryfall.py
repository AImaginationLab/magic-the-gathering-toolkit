"""Scryfall database access for images and prices."""

from __future__ import annotations

import logging
from typing import Any

import aiosqlite

from ..models import CardImage
from .base import BaseDatabase

logger = logging.getLogger(__name__)


class ScryfallDatabase(BaseDatabase):
    """Database access to Scryfall data (images, prices, links)."""

    def __init__(self, db: aiosqlite.Connection, max_connections: int = 5):
        super().__init__(db, max_connections)

    def _row_to_card_image(self, row: aiosqlite.Row) -> CardImage:
        """Convert a database row to a CardImage model."""
        return CardImage(
            scryfall_id=row["scryfall_id"],
            oracle_id=row["oracle_id"],
            name=row["name"],
            set_code=row["set_code"],
            collector_number=row["collector_number"],
            image_small=row["image_small"],
            image_normal=row["image_normal"],
            image_large=row["image_large"],
            image_png=row["image_png"],
            image_art_crop=row["image_art_crop"],
            image_border_crop=row["image_border_crop"],
            price_usd=row["price_usd"],
            price_usd_foil=row["price_usd_foil"],
            price_eur=row["price_eur"],
            price_eur_foil=row["price_eur_foil"],
            purchase_tcgplayer=row["purchase_tcgplayer"],
            purchase_cardmarket=row["purchase_cardmarket"],
            purchase_cardhoarder=row["purchase_cardhoarder"],
            link_edhrec=row["link_edhrec"],
            link_gatherer=row["link_gatherer"],
            highres_image=bool(row["highres_image"]),
            full_art=bool(row["full_art"]),
            border_color=row["border_color"],
            illustration_id=row["illustration_id"],
            frame=row["frame"],
            finishes=row["finishes"],
        )

    async def get_card_image(
        self,
        name: str,
        set_code: str | None = None,
        collector_number: str | None = None,
    ) -> CardImage | None:
        """Get image and price data for a card by name.

        Args:
            name: Card name
            set_code: Optional set code to filter by
            collector_number: Optional collector number for exact printing match
        """
        # Try with set code + collector number for exact printing match
        if set_code and collector_number:
            async with self._execute(
                "SELECT * FROM cards WHERE name = ? AND LOWER(set_code) = LOWER(?) AND collector_number = ? LIMIT 1",
                (name, set_code, collector_number),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_card_image(row)

        # Try with just set code
        if set_code:
            async with self._execute(
                "SELECT * FROM cards WHERE name = ? AND LOWER(set_code) = LOWER(?) LIMIT 1",
                (name, set_code),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_card_image(row)

        # Fall back to cheapest regular printing
        async with self._execute(
            "SELECT * FROM cards WHERE name = ? ORDER BY art_priority DESC, price_usd ASC NULLS LAST LIMIT 1",
            (name,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_card_image(row)

        return None

    async def get_card_image_by_scryfall_id(self, scryfall_id: str) -> CardImage | None:
        """Get image data by Scryfall ID."""
        async with self._execute(
            "SELECT * FROM cards WHERE scryfall_id = ?",
            (scryfall_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_card_image(row)
        return None

    async def get_all_printings(self, name: str) -> list[CardImage]:
        """Get all printings of a card with images."""
        images = []
        async with self._execute(
            "SELECT * FROM cards WHERE name = ? ORDER BY set_code",
            (name,),
        ) as cursor:
            async for row in cursor:
                images.append(self._row_to_card_image(row))
        return images

    async def get_unique_artworks(self, name: str) -> list[CardImage]:
        """Get all unique artworks for a card (one per illustration_id).

        Uses the pre-computed art_priority column (0=borderless, 1=full_art, 2=regular)
        to efficiently select the preferred printing for each unique artwork.
        Falls back to legacy CASE-based query for databases without art_priority.
        """
        images = []

        # Try optimized query using art_priority column (new schema)
        try:
            async with self._execute(
                """
                SELECT c.* FROM cards c
                INNER JOIN (
                    SELECT illustration_id, MIN(art_priority || set_code || scryfall_id) AS best
                    FROM cards
                    WHERE name = ?
                    GROUP BY illustration_id
                ) ranked ON c.illustration_id = ranked.illustration_id
                    AND (c.art_priority || c.set_code || c.scryfall_id) = ranked.best
                WHERE c.name = ?
                ORDER BY c.art_priority, c.set_code
                """,
                (name, name),
            ) as cursor:
                async for row in cursor:
                    images.append(self._row_to_card_image(row))
            return images
        except aiosqlite.OperationalError:
            pass

        # Fallback: legacy query for databases without art_priority column
        async with self._execute(
            """
            SELECT c.* FROM cards c
            INNER JOIN (
                SELECT illustration_id, MIN(
                    CASE WHEN border_color = 'borderless' THEN '0'
                         WHEN full_art = 1 THEN '1'
                         ELSE '2'
                    END || set_code || scryfall_id
                ) AS best
                FROM cards
                WHERE name = ?
                GROUP BY illustration_id
            ) ranked ON c.illustration_id = ranked.illustration_id
                AND (
                    CASE WHEN c.border_color = 'borderless' THEN '0'
                         WHEN c.full_art = 1 THEN '1'
                         ELSE '2'
                    END || c.set_code || c.scryfall_id
                ) = ranked.best
            WHERE c.name = ?
            ORDER BY
                CASE WHEN c.border_color = 'borderless' THEN 0 ELSE 1 END,
                c.full_art DESC,
                c.set_code
            """,
            (name, name),
        ) as cursor:
            async for row in cursor:
                images.append(self._row_to_card_image(row))
        return images

    async def search_by_price(
        self,
        min_price: float | None = None,
        max_price: float | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> list[CardImage]:
        """Search cards by price range (prices in USD)."""
        conditions = ["price_usd IS NOT NULL"]
        params: list[Any] = []

        if min_price is not None:
            conditions.append("price_usd >= ?")
            params.append(int(min_price * 100))
        if max_price is not None:
            conditions.append("price_usd <= ?")
            params.append(int(max_price * 100))

        where_clause = " AND ".join(conditions)
        offset = (page - 1) * page_size

        images = []
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
                images.append(self._row_to_card_image(row))
        return images

    async def get_card_images_batch(
        self,
        names: list[str],
    ) -> dict[str, CardImage]:
        """Get image and price data for multiple cards by name in a single query.

        Args:
            names: List of card names to fetch

        Returns:
            Dict mapping card name (lowercase) to CardImage. Missing cards are omitted.
        """
        if not names:
            return {}

        # Build parameterized IN query
        # Order by art_priority DESC (2=regular first, 0=borderless last) then price
        # This ensures we get the cheapest regular printing by default
        placeholders = ",".join("?" * len(names))
        query = f"""
            SELECT * FROM cards
            WHERE name IN ({placeholders})
            ORDER BY name, art_priority DESC, price_usd ASC NULLS LAST
        """

        # Fetch all matching cards, group by name to get one per name
        name_to_image: dict[str, CardImage] = {}
        async with self._execute(query, names) as cursor:
            async for row in cursor:
                name_lower = row["name"].lower()
                # Keep only first per name (most recent due to ORDER BY)
                if name_lower not in name_to_image:
                    name_to_image[name_lower] = self._row_to_card_image(row)

        return name_to_image

    async def get_database_stats(self) -> dict[str, Any]:
        """Get Scryfall database statistics."""
        stats: dict[str, Any] = {}

        async with self._execute("SELECT COUNT(*) FROM cards") as cursor:
            row = await cursor.fetchone()
            stats["total_cards"] = row[0] if row else 0

        async with self._execute(
            "SELECT COUNT(*) FROM cards WHERE price_usd IS NOT NULL"
        ) as cursor:
            row = await cursor.fetchone()
            stats["cards_with_prices"] = row[0] if row else 0

        async with self._execute("SELECT value FROM meta WHERE key = 'created_at'") as cursor:
            row = await cursor.fetchone()
            if row:
                stats["created_at"] = row[0]

        return stats
