"""Database building utilities."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any


def _to_float(value: Any) -> float | None:
    """Convert a value to float, handling Decimal from ijson."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _to_int(value: Any) -> int | None:
    """Convert a value to int, handling Decimal from ijson."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


class DatabaseBuilder:
    """Builds the unified MTG database from downloaded data."""

    def __init__(
        self,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> None:
        """Initialize builder.

        Args:
            progress_callback: Called with (progress 0-1, message) during build
        """
        self._progress_callback = progress_callback or (lambda _p, _m: None)

    def _report(self, progress: float, message: str) -> None:
        """Report progress to callback."""
        self._progress_callback(progress, message)

    def create_schema(self, cursor: sqlite3.Cursor) -> None:
        """Create the unified database schema."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cards (
                id TEXT PRIMARY KEY,
                oracle_id TEXT,
                name TEXT NOT NULL,
                flavor_name TEXT,
                layout TEXT,
                mana_cost TEXT,
                cmc REAL,
                colors TEXT,
                color_identity TEXT,
                type_line TEXT,
                oracle_text TEXT,
                flavor_text TEXT,
                power TEXT,
                toughness TEXT,
                loyalty TEXT,
                defense TEXT,
                keywords TEXT,
                set_code TEXT NOT NULL,
                set_name TEXT,
                rarity TEXT CHECK(rarity IN ('common','uncommon','rare','mythic','special','bonus') OR rarity IS NULL),
                collector_number TEXT NOT NULL,
                artist TEXT,
                release_date TEXT,
                is_token INTEGER DEFAULT 0 CHECK(is_token IN (0, 1)),
                is_promo INTEGER DEFAULT 0 CHECK(is_promo IN (0, 1)),
                is_digital_only INTEGER DEFAULT 0 CHECK(is_digital_only IN (0, 1)),
                edhrec_rank INTEGER,
                image_small TEXT,
                image_normal TEXT,
                image_large TEXT,
                image_png TEXT,
                image_art_crop TEXT,
                image_border_crop TEXT,
                price_usd INTEGER,
                price_usd_foil INTEGER,
                price_eur INTEGER,
                price_eur_foil INTEGER,
                purchase_tcgplayer TEXT,
                purchase_cardmarket TEXT,
                purchase_cardhoarder TEXT,
                link_edhrec TEXT,
                link_gatherer TEXT,
                illustration_id TEXT,
                highres_image INTEGER DEFAULT 0,
                border_color TEXT,
                frame TEXT,
                full_art INTEGER DEFAULT 0,
                art_priority INTEGER DEFAULT 2,
                finishes TEXT,
                legalities TEXT NOT NULL,
                legal_commander INTEGER GENERATED ALWAYS AS (
                    json_extract(legalities, '$.commander') = 'legal'
                ) STORED,
                legal_modern INTEGER GENERATED ALWAYS AS (
                    json_extract(legalities, '$.modern') = 'legal'
                ) STORED,
                legal_standard INTEGER GENERATED ALWAYS AS (
                    json_extract(legalities, '$.standard') = 'legal'
                ) STORED
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sets (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                set_type TEXT,
                release_date TEXT,
                card_count INTEGER,
                icon_svg_uri TEXT,
                block TEXT,
                base_set_size INTEGER,
                total_set_size INTEGER,
                is_online_only INTEGER DEFAULT 0,
                is_foil_only INTEGER DEFAULT 0,
                keyrune_code TEXT
            ) WITHOUT ROWID
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rulings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                oracle_id TEXT,
                published_at TEXT,
                comment TEXT,
                source TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

    def create_indexes(self, cursor: sqlite3.Cursor) -> None:
        """Create performance indexes."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_cards_oracle_id ON cards(oracle_id)",
            "CREATE INDEX IF NOT EXISTS idx_cards_name ON cards(name COLLATE NOCASE)",
            "CREATE INDEX IF NOT EXISTS idx_cards_set_number ON cards(set_code, collector_number)",
            "CREATE INDEX IF NOT EXISTS idx_cards_type_line ON cards(type_line)",
            "CREATE INDEX IF NOT EXISTS idx_cards_artist ON cards(artist)",
            "CREATE INDEX IF NOT EXISTS idx_cards_cmc ON cards(cmc)",
            "CREATE INDEX IF NOT EXISTS idx_cards_rarity ON cards(rarity)",
            "CREATE INDEX IF NOT EXISTS idx_cards_illustration ON cards(name, illustration_id, art_priority)",
            "CREATE INDEX IF NOT EXISTS idx_rulings_oracle_id ON rulings(oracle_id)",
            """CREATE INDEX IF NOT EXISTS idx_cards_name_covering ON cards(
                name COLLATE NOCASE, release_date DESC,
                set_code, collector_number, mana_cost, type_line,
                image_normal, price_usd
            )""",
            "CREATE INDEX IF NOT EXISTS idx_cards_real ON cards(name, set_code) WHERE is_token = 0 AND is_digital_only = 0",
            "CREATE INDEX IF NOT EXISTS idx_cards_price ON cards(price_usd) WHERE price_usd IS NOT NULL",
            "CREATE INDEX IF NOT EXISTS idx_cards_tokens ON cards(name, set_code) WHERE is_token = 1",
            "CREATE INDEX IF NOT EXISTS idx_legal_commander ON cards(legal_commander) WHERE legal_commander = 1",
            "CREATE INDEX IF NOT EXISTS idx_legal_modern ON cards(legal_modern) WHERE legal_modern = 1",
            "CREATE INDEX IF NOT EXISTS idx_legal_standard ON cards(legal_standard) WHERE legal_standard = 1",
        ]
        for sql in indexes:
            cursor.execute(sql)

    def create_fts_index(self, cursor: sqlite3.Cursor) -> None:
        """Create full-text search index."""
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
                name, type_line, oracle_text, keywords,
                content='cards',
                content_rowid='rowid',
                tokenize='porter unicode61'
            )
        """)
        cursor.execute("""
            INSERT OR REPLACE INTO cards_fts(cards_fts) VALUES('rebuild')
        """)

    def _price_to_cents(self, price: str | float | None) -> int | None:
        """Convert price string/number to cents.

        Note: ijson returns decimal.Decimal for numbers, so we handle that too.
        """
        if price is None:
            return None
        try:
            # Convert to float first (handles str, int, float, Decimal)
            return int(float(price) * 100)
        except (ValueError, TypeError):
            return None

    def _calculate_art_priority(self, card: dict[str, Any]) -> int:
        """Calculate art priority: 0=borderless, 1=full_art, 2=regular."""
        if card.get("border_color") == "borderless":
            return 0
        if card.get("full_art"):
            return 1
        return 2

    def import_sets(
        self, cursor: sqlite3.Cursor, sets_json: Path, mtgjson_path: Path | None = None
    ) -> int:
        """Import sets from Scryfall and optionally MTGJson for extra metadata."""
        with sets_json.open() as f:
            data = json.load(f)

        sets_data = data if isinstance(data, list) else data.get("data", [])

        # Load MTGJson set metadata if available
        mtgjson_sets: dict[str, dict[str, Any]] = {}
        if mtgjson_path and mtgjson_path.exists():
            with mtgjson_path.open() as f:
                mtgjson_data = json.load(f)
                for s in mtgjson_data.get("data", []):
                    code = s.get("code", "").lower()
                    mtgjson_sets[code] = s

        count = 0
        for s in sets_data:
            code = s.get("code", "").lower()
            mtg_extra = mtgjson_sets.get(code, {})

            cursor.execute(
                """INSERT OR REPLACE INTO sets
                   (code, name, set_type, release_date, card_count, icon_svg_uri,
                    block, base_set_size, total_set_size, is_online_only, is_foil_only, keyrune_code)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    code,
                    s.get("name"),
                    s.get("set_type"),
                    s.get("released_at"),
                    s.get("card_count"),
                    s.get("icon_svg_uri"),
                    mtg_extra.get("block"),
                    mtg_extra.get("baseSetSize"),
                    mtg_extra.get("totalSetSize"),
                    1 if s.get("digital") else 0,
                    1 if s.get("foil_only") else 0,
                    mtg_extra.get("keyruneCode"),
                ),
            )
            count += 1

        return count

    def import_cards_streaming(
        self,
        cursor: sqlite3.Cursor,
        cards_json: Path,
        batch_size: int = 5000,
    ) -> int:
        """Import cards using streaming JSON parser to minimize memory usage."""
        import ijson

        self._report(0.55, "Importing cards...")

        count = 0
        batch: list[tuple[Any, ...]] = []

        with cards_json.open("rb") as f:
            for card in ijson.items(f, "item"):
                row = self._card_to_row(card)
                batch.append(row)
                count += 1

                if len(batch) >= batch_size:
                    self._insert_card_batch(cursor, batch)
                    batch = []
                    # Report progress periodically
                    if count % 10000 == 0:
                        self._report(
                            0.55 + 0.25 * min(count / 110000, 1.0), f"Imported {count:,} cards..."
                        )

        # Insert remaining batch
        if batch:
            self._insert_card_batch(cursor, batch)

        return count

    def _card_to_row(self, card: dict[str, Any]) -> tuple[Any, ...]:
        """Convert a card dict to a database row tuple."""
        images = card.get("image_uris", {})
        if not images and "card_faces" in card:
            faces = card.get("card_faces", [])
            if faces:
                images = faces[0].get("image_uris", {})

        prices = card.get("prices", {})
        purchase = card.get("purchase_uris", {})
        related = card.get("related_uris", {})
        legalities = json.dumps(card.get("legalities", {}))
        layout = card.get("layout", "")
        is_token = 1 if layout in ("token", "double_faced_token", "emblem") else 0

        return (
            card.get("id"),
            card.get("oracle_id"),
            card.get("name"),
            card.get("flavor_name"),
            layout,
            card.get("mana_cost"),
            _to_float(card.get("cmc")),  # ijson returns Decimal
            json.dumps(card.get("colors", [])),
            json.dumps(card.get("color_identity", [])),
            card.get("type_line"),
            card.get("oracle_text"),
            card.get("flavor_text"),
            card.get("power"),
            card.get("toughness"),
            card.get("loyalty"),
            card.get("defense"),
            json.dumps(card.get("keywords", [])),
            card.get("set"),
            card.get("set_name"),
            card.get("rarity"),
            card.get("collector_number"),
            card.get("artist"),
            card.get("released_at"),
            is_token,
            1 if card.get("promo") else 0,
            1 if card.get("digital") else 0,
            _to_int(card.get("edhrec_rank")),  # ijson returns Decimal
            images.get("small"),
            images.get("normal"),
            images.get("large"),
            images.get("png"),
            images.get("art_crop"),
            images.get("border_crop"),
            self._price_to_cents(prices.get("usd")),
            self._price_to_cents(prices.get("usd_foil")),
            self._price_to_cents(prices.get("eur")),
            self._price_to_cents(prices.get("eur_foil")),
            purchase.get("tcgplayer"),
            purchase.get("cardmarket"),
            purchase.get("cardhoarder"),
            related.get("edhrec"),
            related.get("gatherer"),
            card.get("illustration_id"),
            1 if card.get("highres_image") else 0,
            card.get("border_color"),
            card.get("frame"),
            1 if card.get("full_art") else 0,
            self._calculate_art_priority(card),
            json.dumps(card.get("finishes", [])),
            legalities,
        )

    def _insert_card_batch(self, cursor: sqlite3.Cursor, batch: list[tuple[Any, ...]]) -> None:
        """Insert a batch of cards."""
        cursor.executemany(
            """INSERT OR REPLACE INTO cards (
                id, oracle_id, name, flavor_name, layout, mana_cost, cmc, colors, color_identity,
                type_line, oracle_text, flavor_text, power, toughness, loyalty, defense, keywords,
                set_code, set_name, rarity, collector_number, artist, release_date,
                is_token, is_promo, is_digital_only, edhrec_rank,
                image_small, image_normal, image_large, image_png, image_art_crop, image_border_crop,
                price_usd, price_usd_foil, price_eur, price_eur_foil,
                purchase_tcgplayer, purchase_cardmarket, purchase_cardhoarder, link_edhrec, link_gatherer,
                illustration_id, highres_image, border_color, frame, full_art, art_priority, finishes, legalities
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            batch,
        )

    def import_rulings(self, cursor: sqlite3.Cursor, rulings_json: Path) -> int:
        """Import rulings from Scryfall."""
        self._report(0.82, "Importing rulings...")

        with rulings_json.open() as f:
            rulings = json.load(f)

        count = 0
        batch: list[tuple[str | None, str | None, str | None, str | None]] = []

        for ruling in rulings:
            batch.append(
                (
                    ruling.get("oracle_id"),
                    ruling.get("published_at"),
                    ruling.get("comment"),
                    ruling.get("source"),
                )
            )
            count += 1

            if len(batch) >= 5000:
                cursor.executemany(
                    "INSERT INTO rulings (oracle_id, published_at, comment, source) VALUES (?, ?, ?, ?)",
                    batch,
                )
                batch = []

        if batch:
            cursor.executemany(
                "INSERT INTO rulings (oracle_id, published_at, comment, source) VALUES (?, ?, ?, ?)",
                batch,
            )

        return count

    def build_database(
        self,
        db_path: Path,
        cards_json: Path,
        sets_json: Path,
        rulings_json: Path,
        mtgjson_path: Path | None = None,
        scryfall_updated_at: str | None = None,
    ) -> None:
        """Build the complete database from downloaded files."""
        self._report(0.52, "Creating database schema...")

        # Remove existing database if present
        if db_path.exists():
            db_path.unlink()

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            # Optimize for bulk import
            cursor.execute("PRAGMA journal_mode = OFF")
            cursor.execute("PRAGMA synchronous = OFF")
            cursor.execute("PRAGMA cache_size = -64000")  # 64MB cache

            # Create schema
            self.create_schema(cursor)

            # Import sets
            self._report(0.53, "Importing sets...")
            set_count = self.import_sets(cursor, sets_json, mtgjson_path)
            self._report(0.54, f"Imported {set_count} sets")

            # Import cards (streaming)
            card_count = self.import_cards_streaming(cursor, cards_json)
            self._report(0.80, f"Imported {card_count:,} cards")

            # Import rulings
            ruling_count = self.import_rulings(cursor, rulings_json)
            self._report(0.84, f"Imported {ruling_count:,} rulings")

            # Create indexes
            self._report(0.85, "Creating indexes...")
            self.create_indexes(cursor)

            # Create FTS index
            self._report(0.86, "Creating search index...")
            self.create_fts_index(cursor)

            # Store metadata
            self._report(0.87, "Finalizing...")
            if scryfall_updated_at:
                cursor.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                    ("scryfall_updated_at", scryfall_updated_at),
                )

            conn.commit()

        finally:
            conn.close()
