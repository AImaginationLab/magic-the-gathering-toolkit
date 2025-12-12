"""Scryfall database access for images and prices."""

from __future__ import annotations

from typing import Any

import aiosqlite

from ..models import CardImage


class ScryfallDatabase:
    """Database access to Scryfall data (images, prices, links)."""

    def __init__(self, db: aiosqlite.Connection):
        self._db = db

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

    async def get_card_image(self, name: str, set_code: str | None = None) -> CardImage | None:
        """Get image and price data for a card by name."""
        # Try with set code first if provided
        if set_code:
            async with self._db.execute(
                "SELECT * FROM cards WHERE name = ? AND set_code = ? LIMIT 1",
                (name, set_code.upper()),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_card_image(row)

        # Fall back to any printing
        async with self._db.execute(
            "SELECT * FROM cards WHERE name = ? ORDER BY scryfall_id DESC LIMIT 1",
            (name,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_card_image(row)

        return None

    async def get_card_image_by_scryfall_id(self, scryfall_id: str) -> CardImage | None:
        """Get image data by Scryfall ID."""
        async with self._db.execute(
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
        async with self._db.execute(
            "SELECT * FROM cards WHERE name = ? ORDER BY set_code",
            (name,),
        ) as cursor:
            async for row in cursor:
                images.append(self._row_to_card_image(row))
        return images

    async def get_unique_artworks(self, name: str) -> list[CardImage]:
        """Get all unique artworks for a card (one per illustration_id).

        Uses a subquery to deterministically select the preferred printing
        for each unique artwork: borderless > full-art > alphabetically first set.
        """
        images = []
        async with self._db.execute(
            """
            SELECT c.* FROM cards c
            INNER JOIN (
                SELECT illustration_id, MIN(
                    -- Priority: borderless=0, full_art=1, others=2, then set_code
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
        async with self._db.execute(
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

    async def get_database_stats(self) -> dict[str, Any]:
        """Get Scryfall database statistics."""
        stats: dict[str, Any] = {}

        async with self._db.execute("SELECT COUNT(*) FROM cards") as cursor:
            row = await cursor.fetchone()
            stats["total_cards"] = row[0] if row else 0

        async with self._db.execute(
            "SELECT COUNT(*) FROM cards WHERE price_usd IS NOT NULL"
        ) as cursor:
            row = await cursor.fetchone()
            stats["cards_with_prices"] = row[0] if row else 0

        async with self._db.execute("SELECT value FROM meta WHERE key = 'created_at'") as cursor:
            row = await cursor.fetchone()
            if row:
                stats["created_at"] = row[0]

        return stats
