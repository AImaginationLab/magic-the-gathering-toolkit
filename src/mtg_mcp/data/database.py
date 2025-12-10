"""Direct SQLite database access for MTGJson AllPrintings data."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import aiosqlite

from ..config import Settings, get_settings
from ..exceptions import CardNotFoundError, SetNotFoundError
from .models import Card, CardImage, CardLegality, CardRuling, Set

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from .models.inputs import SearchCardsInput

logger = logging.getLogger(__name__)

# SQL fragments for excluding promo/funny cards (MTGJson uses NULL for false)
EXCLUDE_PROMOS = "(c.isPromo IS NULL OR c.isPromo = 0)"
EXCLUDE_FUNNY = "(c.isFunny IS NULL OR c.isFunny = 0)"
EXCLUDE_EXTRAS = f"{EXCLUDE_PROMOS} AND {EXCLUDE_FUNNY}"

# Base card columns for queries
CARD_COLUMNS = """
    c.uuid, c.name, c.manaCost, c.manaValue, c.colors, c.colorIdentity,
    c.type, c.supertypes, c.types, c.subtypes, c.text, c.flavorText,
    c.power, c.toughness, c.loyalty, c.defense, c.setCode, c.rarity,
    c.number, c.artist, c.layout, c.keywords, c.edhrecRank
""".strip()

# Valid format columns in cardLegalities table
VALID_FORMATS = frozenset(
    {
        "standard",
        "modern",
        "legacy",
        "vintage",
        "commander",
        "pioneer",
        "pauper",
        "historic",
        "brawl",
        "alchemy",
        "explorer",
        "timeless",
        "oathbreaker",
        "penny",
        "duel",
        "gladiator",
        "premodern",
        "oldschool",
        "predh",
        "paupercommander",
    }
)


@dataclass
class QueryBuilder:
    """Builds parameterized SQL queries for card searches."""

    conditions: list[str] = field(default_factory=list)
    params: list[Any] = field(default_factory=list)

    def add_like(self, column: str, value: str | None, pattern: str = "%{value}%") -> None:
        """Add a LIKE condition."""
        if value:
            self.conditions.append(f"{column} LIKE ?")
            self.params.append(pattern.format(value=value))

    def add_exact(self, column: str, value: Any, case_insensitive: bool = False) -> None:
        """Add an exact match condition."""
        if value is not None:
            if case_insensitive:
                self.conditions.append(f"LOWER({column}) = LOWER(?)")
            else:
                self.conditions.append(f"{column} = ?")
            self.params.append(value)

    def add_comparison(self, column: str, op: str, value: float | None) -> None:
        """Add a comparison condition (=, >=, <=, etc)."""
        if value is not None:
            self.conditions.append(f"{column} {op} ?")
            self.params.append(value)

    def add_not_like(self, column: str, value: str, nullable: bool = True) -> None:
        """Add a NOT LIKE condition, handling NULL if nullable."""
        if nullable:
            self.conditions.append(f"({column} IS NULL OR {column} NOT LIKE ?)")
        else:
            self.conditions.append(f"{column} NOT LIKE ?")
        self.params.append(f"%{value}%")

    def add_colors(self, colors: list[str] | None) -> None:
        """Add color filter conditions (card must have all colors)."""
        if colors:
            for color in colors:
                self.add_like("c.colors", color)

    def add_color_identity(self, identity: list[str] | None) -> None:
        """Add color identity filter (card must be subset of identity)."""
        if identity:
            # Card must NOT contain any colors outside the given identity
            excluded = [c for c in ["W", "U", "B", "R", "G"] if c not in identity]
            for color in excluded:
                self.add_not_like("c.colorIdentity", color)

    def add_format_legality(self, format_name: str | None) -> None:
        """Add format legality subquery condition."""
        if format_name and format_name.lower() in VALID_FORMATS:
            fmt = format_name.lower()
            self.conditions.append(f"""
                c.uuid IN (
                    SELECT uuid FROM cardLegalities
                    WHERE {fmt} = 'Legal' OR {fmt} = 'Restricted'
                )
            """)

    def add_keywords(self, keywords: list[str] | None) -> None:
        """Add keyword filter conditions."""
        if keywords:
            for keyword in keywords:
                self.add_like("c.keywords", keyword)

    def build_where(self) -> str:
        """Build the WHERE clause."""
        return " AND ".join(self.conditions) if self.conditions else "1=1"

    @classmethod
    def from_filters(cls, filters: SearchCardsInput) -> QueryBuilder:
        """Build a QueryBuilder from SearchCardsInput."""
        qb = cls()
        qb.add_like("c.name", filters.name)
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
        qb.add_like("c.text", filters.text)
        qb.add_keywords(filters.keywords)
        qb.add_format_legality(filters.format_legal)
        return qb


@dataclass
class CardCache:
    """Simple async-safe LRU cache for cards."""

    _cache: dict[str, Card] = field(default_factory=dict)
    _access_order: list[str] = field(default_factory=list)
    max_size: int = 1000
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def get(self, key: str) -> Card | None:
        """Get a card from cache."""
        async with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._access_order.remove(key)
                self._access_order.append(key)
                return self._cache[key]
            return None

    async def set(self, key: str, card: Card) -> None:
        """Add a card to cache."""
        async with self._lock:
            if key in self._cache:
                self._access_order.remove(key)
            elif len(self._cache) >= self.max_size:
                # Remove least recently used
                oldest = self._access_order.pop(0)
                del self._cache[oldest]
            self._cache[key] = card
            self._access_order.append(key)

    async def clear(self) -> None:
        """Clear the cache."""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()


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
        return Card(
            uuid=row["uuid"],
            name=row["name"],
            mana_cost=row["manaCost"],
            cmc=row["manaValue"],
            colors=self._parse_list(row["colors"]),
            color_identity=self._parse_list(row["colorIdentity"]),
            type=row["type"],
            supertypes=self._parse_list(row["supertypes"]),
            types=self._parse_list(row["types"]),
            subtypes=self._parse_list(row["subtypes"]),
            text=row["text"],
            flavor=row["flavorText"],
            power=row["power"],
            toughness=row["toughness"],
            loyalty=row["loyalty"],
            defense=row["defense"],
            set_code=row["setCode"],
            rarity=row["rarity"],
            number=row["number"],
            artist=row["artist"],
            layout=row["layout"],
            keywords=self._parse_list(row["keywords"]),
            edhrec_rank=row["edhrecRank"],
        )

    def _row_to_set(self, row: aiosqlite.Row) -> Set:
        """Convert a database row to a Set model."""
        return Set(
            code=row["code"],
            name=row["name"],
            type=row["type"],
            release_date=row["releaseDate"],
            block=row["block"],
            base_set_size=row["baseSetSize"],
            total_set_size=row["totalSetSize"],
            is_online_only=bool(row["isOnlineOnly"]),
            is_foil_only=bool(row["isFoilOnly"]),
            keyrune_code=row["keyruneCode"],
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
        # Check cache first
        cached = await self._cache.get(f"name:{name.lower()}")
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
                await self._cache.set(f"name:{name.lower()}", card)
                return card
        raise CardNotFoundError(name)

    async def search_cards(self, filters: SearchCardsInput) -> list[Card]:
        """Search for cards matching the given filters."""
        qb = QueryBuilder.from_filters(filters)
        where_clause = qb.build_where()

        query = f"""
            SELECT DISTINCT {CARD_COLUMNS}
            FROM cards c
            JOIN sets s ON c.setCode = s.code
            WHERE {where_clause} AND {EXCLUDE_EXTRAS}
            GROUP BY c.name
            ORDER BY c.name
            LIMIT ? OFFSET ?
        """
        qb.params.extend([filters.page_size, (filters.page - 1) * filters.page_size])

        cards = []
        async with self._db.execute(query, qb.params) as cursor:
            async for row in cursor:
                cards.append(self._row_to_card(row))

        return cards

    async def _get_legalities(self, uuid: str) -> list[CardLegality]:
        """Get format legalities for a card."""
        async with self._db.execute(
            "SELECT * FROM cardLegalities WHERE uuid = ?",
            (uuid,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return []

            return [
                CardLegality(format=fmt, legality=row[fmt]) for fmt in VALID_FORMATS if row[fmt]
            ]

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
                return card
        raise CardNotFoundError("random")


# -----------------------------------------------------------------------------
# Scryfall Database (Images & Prices)
# -----------------------------------------------------------------------------


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


# -----------------------------------------------------------------------------
# Database Connection Management
# -----------------------------------------------------------------------------


class DatabaseManager:
    """Manages database lifecycle for the MCP server."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._conn: aiosqlite.Connection | None = None
        self._scryfall_conn: aiosqlite.Connection | None = None
        self._db: MTGDatabase | None = None
        self._scryfall: ScryfallDatabase | None = None
        self._cache = CardCache(max_size=self._settings.cache_max_size)

    @property
    def db(self) -> MTGDatabase:
        """Get the MTGJson database instance."""
        if self._db is None:
            raise RuntimeError("DatabaseManager not started. Call start() first.")
        return self._db

    @property
    def scryfall(self) -> ScryfallDatabase | None:
        """Get the Scryfall database instance (may be None)."""
        return self._scryfall

    async def start(self) -> None:
        """Open the database connections."""
        db_path = self._settings.mtg_db_path
        if not db_path.exists():
            raise FileNotFoundError(
                f"MTGJson database not found at {db_path}. "
                "Download AllPrintings.sqlite from https://mtgjson.com/downloads/all-files/"
            )

        self._conn = await aiosqlite.connect(db_path)
        self._conn.row_factory = aiosqlite.Row
        self._db = MTGDatabase(self._conn, self._cache)

        # Scryfall database (optional)
        scryfall_path = self._settings.scryfall_db_path
        if scryfall_path.exists():
            self._scryfall_conn = await aiosqlite.connect(scryfall_path)
            self._scryfall_conn.row_factory = aiosqlite.Row
            self._scryfall = ScryfallDatabase(self._scryfall_conn)
            logger.info("Scryfall database loaded from %s", scryfall_path)
        else:
            logger.warning("Scryfall database not found at %s", scryfall_path)

    async def stop(self) -> None:
        """Close the database connections."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            self._db = None
        if self._scryfall_conn:
            await self._scryfall_conn.close()
            self._scryfall_conn = None
            self._scryfall = None
        await self._cache.clear()


@asynccontextmanager
async def create_database(settings: Settings | None = None) -> AsyncIterator[MTGDatabase]:
    """Create a database instance as a context manager."""
    manager = DatabaseManager(settings)
    await manager.start()
    try:
        yield manager.db
    finally:
        await manager.stop()
