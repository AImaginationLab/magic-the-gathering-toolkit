#!/usr/bin/env python3
"""Build unified MTG database from Scryfall and MTGJson sources.

Downloads:
- Scryfall default_cards bulk (all printings with images, prices, legalities)
- Scryfall rulings bulk (card rulings)
- Scryfall sets bulk (set metadata including token sets)
- MTGJson AllPrintings.json (EDHREC rank supplementation)

Creates a single mtg.sqlite with complete card data.

Usage:
    uv run create-mtg-db [--output-dir DIR]
"""

from __future__ import annotations

import gzip
import json
import sqlite3
import tempfile
from collections.abc import Generator, Iterator
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import httpx
import ijson
import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

if TYPE_CHECKING:
    pass

console = Console()

# URLs
SCRYFALL_BULK_API = "https://api.scryfall.com/bulk-data"
MTGJSON_ALLPRINTINGS_URL = "https://mtgjson.com/api/v5/AllPrintings.json.gz"
MTGJSON_SETLIST_URL = "https://mtgjson.com/api/v5/SetList.json"

# Schema version for migrations
SCHEMA_VERSION = 1

# Batch sizes for bulk operations
CARD_BATCH_SIZE = 5000
RULING_BATCH_SIZE = 10000
EDHREC_BATCH_SIZE = 5000


def get_scryfall_bulk_url(bulk_type: str) -> tuple[str, str]:
    """Get download URL for a Scryfall bulk data type."""
    console.print(f"[dim]Fetching Scryfall {bulk_type} info...[/]")

    with httpx.Client(timeout=30.0) as client:
        response = client.get(SCRYFALL_BULK_API)
        response.raise_for_status()
        data = response.json()

    for item in data["data"]:
        if item["type"] == bulk_type:
            return item["download_uri"], item["updated_at"]

    raise ValueError(f"Bulk data type '{bulk_type}' not found")


def download_file(url: str, dest: Path, description: str) -> None:
    """Download a file with progress bar."""
    timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)
    with (
        httpx.Client(follow_redirects=True, timeout=timeout) as client,
        client.stream("GET", url) as response,
    ):
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(description, total=total)

            with dest.open("wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    progress.update(task, advance=len(chunk))


def create_schema(cursor: sqlite3.Cursor) -> None:
    """Create the unified database schema."""
    # Cards table - one row per printing
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id TEXT PRIMARY KEY,
            oracle_id TEXT NOT NULL,
            name TEXT NOT NULL,

            -- Card data
            layout TEXT,
            flavor_name TEXT,
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

            -- Printing info
            set_code TEXT NOT NULL,
            set_name TEXT,
            rarity TEXT CHECK(rarity IN ('common','uncommon','rare','mythic','special','bonus') OR rarity IS NULL),
            collector_number TEXT NOT NULL,
            artist TEXT,
            release_date TEXT,

            -- Flags
            is_token INTEGER DEFAULT 0 CHECK(is_token IN (0, 1)),
            is_promo INTEGER DEFAULT 0 CHECK(is_promo IN (0, 1)),
            is_digital_only INTEGER DEFAULT 0 CHECK(is_digital_only IN (0, 1)),

            -- MTGJson supplement
            edhrec_rank INTEGER,

            -- Images
            image_small TEXT,
            image_normal TEXT,
            image_large TEXT,
            image_png TEXT,
            image_art_crop TEXT,
            image_border_crop TEXT,

            -- Prices (cents)
            price_usd INTEGER,
            price_usd_foil INTEGER,
            price_eur INTEGER,
            price_eur_foil INTEGER,

            -- Links
            purchase_tcgplayer TEXT,
            purchase_cardmarket TEXT,
            purchase_cardhoarder TEXT,
            link_edhrec TEXT,
            link_gatherer TEXT,

            -- Visual
            illustration_id TEXT,
            highres_image INTEGER DEFAULT 0,
            border_color TEXT,
            frame TEXT,
            full_art INTEGER DEFAULT 0,
            art_priority INTEGER DEFAULT 2,
            finishes TEXT,

            -- Legalities as JSON
            legalities TEXT NOT NULL,

            -- Generated columns for fast legality filtering (avoid json_extract in queries)
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

    # Sets table - combines Scryfall (base) + MTGJson (supplements)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sets (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            set_type TEXT,
            release_date TEXT,
            card_count INTEGER,
            icon_svg_uri TEXT,
            -- MTGJson supplements (NULL until supplemented)
            block TEXT,
            base_set_size INTEGER,
            total_set_size INTEGER,
            is_online_only INTEGER DEFAULT 0,
            is_foil_only INTEGER DEFAULT 0,
            keyrune_code TEXT
        ) WITHOUT ROWID
    """)

    # Rulings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rulings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            oracle_id TEXT NOT NULL,
            published_at TEXT,
            comment TEXT,
            source TEXT
        )
    """)

    # Meta table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)


def create_indexes(cursor: sqlite3.Cursor) -> None:
    """Create performance indexes."""
    console.print("[dim]Creating indexes...[/]")

    indexes = [
        ("idx_cards_oracle_id", "cards(oracle_id)"),
        ("idx_cards_name", "cards(name COLLATE NOCASE)"),
        ("idx_cards_set_number", "cards(set_code, collector_number)"),
        ("idx_cards_type_line", "cards(type_line)"),
        ("idx_cards_artist", "cards(artist)"),
        ("idx_cards_cmc", "cards(cmc)"),
        ("idx_cards_rarity", "cards(rarity)"),
        ("idx_cards_illustration", "cards(name, illustration_id, art_priority)"),
        ("idx_rulings_oracle_id", "rulings(oracle_id)"),
    ]

    # Covering index for <10ms name lookups (Performance Engineer recommendation)
    covering_indexes = [
        (
            "idx_cards_name_covering",
            """cards(
                name COLLATE NOCASE,
                release_date DESC,
                set_code, collector_number, mana_cost, type_line,
                image_normal, price_usd
            )""",
        ),
    ]

    # Partial indexes for common filters
    partial_indexes = [
        (
            "idx_cards_real",
            "cards(name, set_code) WHERE is_token = 0 AND is_digital_only = 0",
        ),
        ("idx_cards_price", "cards(price_usd) WHERE price_usd IS NOT NULL"),
        ("idx_cards_tokens", "cards(name, set_code) WHERE is_token = 1"),
    ]

    # Indexes on generated legality columns
    legality_indexes = [
        ("idx_legal_commander", "cards(legal_commander) WHERE legal_commander = 1"),
        ("idx_legal_modern", "cards(legal_modern) WHERE legal_modern = 1"),
        ("idx_legal_standard", "cards(legal_standard) WHERE legal_standard = 1"),
    ]

    for idx_name, idx_def in indexes:
        cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")

    for idx_name, idx_def in covering_indexes:
        cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")

    for idx_name, idx_def in partial_indexes:
        cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")

    for idx_name, idx_def in legality_indexes:
        cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")

    total = len(indexes) + len(covering_indexes) + len(partial_indexes) + len(legality_indexes)
    console.print(f"[green]OK[/] Created {total} indexes")


def create_fts_index(cursor: sqlite3.Cursor, card_count: int) -> None:
    """Create FTS5 full-text search index."""
    console.print("[dim]Creating FTS5 full-text search index...[/]")

    BATCH_SIZE = 10000

    # Create FTS5 virtual table
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
            id UNINDEXED,
            name,
            flavor_name,
            type_line,
            oracle_text,
            tokenize='porter unicode61'
        )
    """)

    # Populate FTS index in batches
    console.print(f"[dim]Indexing {card_count:,} cards...[/]")

    offset = 0
    inserted = 0
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Indexing cards"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Indexing", total=card_count)

        while offset < card_count:
            cursor.execute(
                """
                INSERT INTO cards_fts(id, name, flavor_name, type_line, oracle_text)
                SELECT id, name, flavor_name, type_line, oracle_text FROM cards
                LIMIT ? OFFSET ?
                """,
                (BATCH_SIZE, offset),
            )
            batch_count = cursor.rowcount
            inserted += batch_count
            offset += BATCH_SIZE
            progress.update(task, completed=min(inserted, card_count))

    # Optimize FTS index
    cursor.execute("INSERT INTO cards_fts(cards_fts) VALUES('optimize')")
    console.print(f"[green]OK[/] Indexed {inserted:,} cards")


def price_to_cents(price: str | None) -> int | None:
    """Convert price string to cents."""
    if price is None:
        return None
    try:
        return int(float(price) * 100)
    except (ValueError, TypeError):
        return None


def calculate_art_priority(card: dict[str, Any]) -> int:
    """Calculate art priority: 0=borderless, 1=full_art, 2=regular."""
    if card.get("border_color") == "borderless":
        return 0
    if card.get("full_art"):
        return 1
    return 2


def import_sets(cursor: sqlite3.Cursor, sets_json: Path) -> int:
    """Import sets from MTGJson SetList.json file."""
    console.print("[dim]Importing sets from MTGJson...[/]")

    with sets_json.open() as f:
        data = json.load(f)

    sets_data = data if isinstance(data, list) else data.get("data", [])
    count = 0

    for s in sets_data:
        cursor.execute(
            """
            INSERT OR REPLACE INTO sets (
                code, name, set_type, release_date, card_count,
                block, base_set_size, total_set_size,
                is_online_only, is_foil_only, keyrune_code
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                s.get("code"),
                s.get("name"),
                s.get("type"),  # MTGJson uses 'type' not 'set_type'
                s.get("releaseDate"),  # MTGJson uses camelCase
                s.get("totalSetSize"),  # Use totalSetSize as card_count
                s.get("block"),
                s.get("baseSetSize"),
                s.get("totalSetSize"),
                1 if s.get("isOnlineOnly") else 0,
                1 if s.get("isFoilOnly") else 0,
                s.get("keyruneCode"),
            ),
        )
        count += 1

    console.print(f"[green]OK[/] Imported {count:,} sets")
    return count


def card_to_tuple(card: dict[str, Any]) -> tuple[Any, ...]:
    """Transform a card dict into a tuple for bulk insert."""
    oracle_id = card.get("oracle_id") or card.get("id")

    # Get image URIs (handle double-faced cards)
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

    # Convert cmc from Decimal (ijson) to float (sqlite compatible)
    cmc = card.get("cmc")
    if cmc is not None:
        cmc = float(cmc)

    return (
        card.get("id"),
        oracle_id,
        card.get("name"),
        layout,
        card.get("flavor_name"),
        card.get("mana_cost"),
        cmc,
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
        card.get("edhrec_rank"),
        images.get("small"),
        images.get("normal"),
        images.get("large"),
        images.get("png"),
        images.get("art_crop"),
        images.get("border_crop"),
        price_to_cents(prices.get("usd")),
        price_to_cents(prices.get("usd_foil")),
        price_to_cents(prices.get("eur")),
        price_to_cents(prices.get("eur_foil")),
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
        calculate_art_priority(card),
        json.dumps(card.get("finishes", [])),
        legalities,
    )


def stream_cards(cards_json: Path) -> Iterator[dict[str, Any]]:
    """Stream cards from JSON file using ijson for memory efficiency."""
    with cards_json.open("rb") as f:
        # ijson.items yields each item in the top-level array
        yield from ijson.items(f, "item")


def batched(iterable: Iterator[Any], n: int) -> Generator[list[Any], None, None]:
    """Yield batches of n items from an iterable."""
    batch: list[Any] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= n:
            yield batch
            batch = []
    if batch:
        yield batch


def import_cards(cursor: sqlite3.Cursor, cards_json: Path) -> int:
    """Import cards from Scryfall default_cards bulk file using batch inserts."""
    console.print("[dim]Streaming cards with batch inserts...[/]")

    # Get total count for progress (quick scan)
    with cards_json.open("rb") as f:
        # Count items without loading full objects
        total = sum(1 for _ in ijson.items(f, "item"))

    console.print(f"[dim]Importing {total:,} cards in batches of {CARD_BATCH_SIZE:,}...[/]")

    # SQL for bulk insert
    insert_sql = """
        INSERT OR REPLACE INTO cards (
            id, oracle_id, name,
            layout, flavor_name, mana_cost, cmc, colors, color_identity,
            type_line, oracle_text, flavor_text,
            power, toughness, loyalty, defense, keywords,
            set_code, set_name, rarity, collector_number, artist, release_date,
            is_token, is_promo, is_digital_only, edhrec_rank,
            image_small, image_normal, image_large, image_png,
            image_art_crop, image_border_crop,
            price_usd, price_usd_foil, price_eur, price_eur_foil,
            purchase_tcgplayer, purchase_cardmarket, purchase_cardhoarder,
            link_edhrec, link_gatherer,
            illustration_id, highres_image, border_color, frame,
            full_art, art_priority, finishes, legalities
        ) VALUES (
            ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?
        )
    """

    imported = 0
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Importing cards"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Importing", total=total)

        # Stream and batch insert
        for batch in batched(stream_cards(cards_json), CARD_BATCH_SIZE):
            tuples = [card_to_tuple(card) for card in batch]
            cursor.executemany(insert_sql, tuples)
            imported += len(batch)
            progress.update(task, completed=imported)

    console.print(f"[green]OK[/] Imported {imported:,} cards")
    return imported


def stream_rulings(rulings_json: Path) -> Iterator[dict[str, Any]]:
    """Stream rulings from JSON file using ijson for memory efficiency."""
    with rulings_json.open("rb") as f:
        yield from ijson.items(f, "item")


def import_rulings(cursor: sqlite3.Cursor, rulings_json: Path) -> int:
    """Import rulings from Scryfall rulings bulk file using batch inserts."""
    console.print("[dim]Streaming rulings with batch inserts...[/]")

    # Get total count for progress
    with rulings_json.open("rb") as f:
        total = sum(1 for _ in ijson.items(f, "item"))

    console.print(f"[dim]Importing {total:,} rulings in batches of {RULING_BATCH_SIZE:,}...[/]")

    insert_sql = """
        INSERT INTO rulings (oracle_id, published_at, comment, source)
        VALUES (?, ?, ?, ?)
    """

    imported = 0
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Importing rulings"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Importing", total=total)

        for batch in batched(stream_rulings(rulings_json), RULING_BATCH_SIZE):
            tuples = [
                (r.get("oracle_id"), r.get("published_at"), r.get("comment"), r.get("source"))
                for r in batch
            ]
            cursor.executemany(insert_sql, tuples)
            imported += len(batch)
            progress.update(task, completed=imported)

    console.print(f"[green]OK[/] Imported {imported:,} rulings")
    return imported


def stream_edhrec_ranks(mtgjson_path: Path) -> Generator[tuple[str, int], None, None]:
    """Stream EDHREC ranks from MTGJson AllPrintings.json.gz.

    Uses ijson to stream the gzipped JSON without loading into memory.
    Yields (card_name, edhrec_rank) tuples, deduplicating by name.

    MTGJson structure: {"data": {"SET_CODE": {"cards": [...]}}}
    We use kvitems to iterate over the set codes (dynamic keys).
    """
    seen_names: set[str] = set()

    with gzip.open(mtgjson_path, "rb") as f:
        # kvitems yields (key, value) pairs for each set in data
        for _set_code, set_data in ijson.kvitems(f, "data"):
            if not isinstance(set_data, dict):
                continue
            cards = set_data.get("cards", [])
            for card in cards:
                name = card.get("name")
                rank = card.get("edhrecRank")
                if name and rank is not None and name not in seen_names:
                    seen_names.add(name)
                    yield (name, int(rank))


def supplement_edhrec_ranks(cursor: sqlite3.Cursor, mtgjson_path: Path) -> int:
    """Supplement EDHREC ranks from MTGJson AllPrintings using temp table + JOIN.

    This is dramatically faster than individual UPDATE statements because:
    1. We bulk-insert ranks into a temp table (fast)
    2. We do a single UPDATE...FROM with a JOIN (one table scan, not 30k)
    """
    console.print("[dim]Streaming EDHREC ranks from MTGJson...[/]")

    # Create temp table for ranks (unlogged, fast)
    cursor.execute("""
        CREATE TEMP TABLE IF NOT EXISTS temp_edhrec_ranks (
            name TEXT PRIMARY KEY,
            rank INTEGER NOT NULL
        )
    """)

    # Stream and batch insert ranks into temp table
    insert_sql = "INSERT OR IGNORE INTO temp_edhrec_ranks (name, rank) VALUES (?, ?)"

    rank_count = 0
    batch: list[tuple[str, int]] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Loading EDHREC ranks"),
        TextColumn("[dim]{task.completed:,} ranks"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading", total=None)  # Unknown total

        for name, rank in stream_edhrec_ranks(mtgjson_path):
            batch.append((name, rank))
            if len(batch) >= EDHREC_BATCH_SIZE:
                cursor.executemany(insert_sql, batch)
                rank_count += len(batch)
                progress.update(task, completed=rank_count)
                batch = []

        # Insert remaining
        if batch:
            cursor.executemany(insert_sql, batch)
            rank_count += len(batch)
            progress.update(task, completed=rank_count)

    console.print(f"[dim]Loaded {rank_count:,} EDHREC ranks into temp table[/]")

    # Create index on temp table for faster join
    cursor.execute("CREATE INDEX IF NOT EXISTS temp_idx_name ON temp_edhrec_ranks(name)")

    # Single UPDATE with JOIN - this is the key optimization
    # Instead of 30k individual UPDATEs scanning the full table each time,
    # we do one UPDATE that uses the indexed join
    console.print("[dim]Updating cards with EDHREC ranks (single JOIN)...[/]")

    cursor.execute("""
        UPDATE cards
        SET edhrec_rank = (
            SELECT rank FROM temp_edhrec_ranks WHERE temp_edhrec_ranks.name = cards.name
        )
        WHERE edhrec_rank IS NULL
          AND name IN (SELECT name FROM temp_edhrec_ranks)
    """)
    updated = cursor.rowcount

    # Clean up temp table
    cursor.execute("DROP TABLE IF EXISTS temp_edhrec_ranks")

    console.print(f"[green]OK[/] Updated {updated:,} cards with EDHREC ranks")
    return updated


def build_unified_db(
    output_path: Path,
    cards_json: Path,
    sets_json: Path,
    rulings_json: Path,
    mtgjson_path: Path | None = None,
) -> None:
    """Build the unified database from downloaded files."""
    console.print(f"\n[bold]Building unified database: {output_path}[/]\n")

    # Remove existing database
    output_path.unlink(missing_ok=True)

    conn = sqlite3.connect(output_path, isolation_level=None)
    cursor = conn.cursor()

    try:
        # Bulk loading optimizations - these are safe because we're building from scratch
        # and will switch to production settings at the end
        cursor.execute("PRAGMA page_size = 4096")  # Optimal for most systems
        cursor.execute(
            "PRAGMA journal_mode = OFF"
        )  # No journal during bulk load (rebuilding anyway)
        cursor.execute("PRAGMA synchronous = OFF")  # No fsync during bulk load
        cursor.execute("PRAGMA locking_mode = EXCLUSIVE")  # Single writer, no reader contention
        cursor.execute("PRAGMA cache_size = -256000")  # 256MB cache for bulk ops
        cursor.execute("PRAGMA temp_store = MEMORY")  # Temp tables in RAM
        cursor.execute("PRAGMA mmap_size = 1073741824")  # 1GB memory-mapped I/O

        # Create schema
        cursor.execute("BEGIN IMMEDIATE")
        create_schema(cursor)
        cursor.execute("COMMIT")

        # Import sets first (needed for set_name denormalization)
        cursor.execute("BEGIN IMMEDIATE")
        set_count = import_sets(cursor, sets_json)
        cursor.execute("COMMIT")

        # Import cards
        cursor.execute("BEGIN IMMEDIATE")
        card_count = import_cards(cursor, cards_json)
        cursor.execute("COMMIT")

        # Import rulings
        cursor.execute("BEGIN IMMEDIATE")
        ruling_count = import_rulings(cursor, rulings_json)
        cursor.execute("COMMIT")

        # Supplement EDHREC ranks from MTGJson AllPrintings
        if mtgjson_path and mtgjson_path.exists():
            cursor.execute("BEGIN IMMEDIATE")
            supplement_edhrec_ranks(cursor, mtgjson_path)
            cursor.execute("COMMIT")

        # Create indexes
        cursor.execute("BEGIN IMMEDIATE")
        create_indexes(cursor)
        cursor.execute("COMMIT")

        # Create FTS index
        cursor.execute("BEGIN IMMEDIATE")
        create_fts_index(cursor, card_count)
        cursor.execute("COMMIT")

        # Insert metadata
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )
        cursor.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            ("created_at", datetime.now().isoformat()),
        )
        cursor.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            ("card_count", str(card_count)),
        )
        cursor.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            ("set_count", str(set_count)),
        )
        cursor.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            ("ruling_count", str(ruling_count)),
        )
        cursor.execute("COMMIT")

        # Switch to production settings for the final database
        console.print("[dim]Finalizing database with production settings...[/]")

        # VACUUM to reclaim space and optimize storage
        cursor.execute("VACUUM")

        # Switch to WAL mode for production (better concurrent read performance)
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")

        # Analyze tables for query optimizer
        cursor.execute("ANALYZE")

        # Verify integrity
        cursor.execute("PRAGMA integrity_check(1)")
        result = cursor.fetchone()
        if result[0] != "ok":
            console.print(f"[red]Warning:[/] Integrity check failed: {result[0]}")
        else:
            console.print("[green]OK[/] Database integrity verified")

    finally:
        conn.close()

    size_mb = output_path.stat().st_size / (1024 * 1024)
    console.print(f"\n[green]OK[/] Created mtg.sqlite ({size_mb:.1f} MB)")


app = typer.Typer(
    name="create-mtg-db",
    help="Build unified MTG database from Scryfall and MTGJson sources.",
    no_args_is_help=False,
    invoke_without_command=True,
)


@app.callback()
def main(
    ctx: typer.Context,
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            "-o",
            help="Directory to save database",
        ),
    ] = Path("resources"),
    skip_mtgjson: Annotated[
        bool,
        typer.Option("--skip-mtgjson", help="Skip MTGJson download (no EDHREC ranks)"),
    ] = False,
) -> None:
    """Build unified MTG database from Scryfall and MTGJson."""
    if ctx.invoked_subcommand is not None:
        return

    console.print("[bold]Unified MTG Database Builder[/]\n")

    # Create output directory
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"Output directory: [cyan]{output_dir}[/]")

    # Download Scryfall bulk files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Download default_cards
        console.print("\n[bold]1. Downloading Scryfall default_cards...[/]")
        cards_url, cards_updated = get_scryfall_bulk_url("default_cards")
        console.print(f"[dim]Updated: {cards_updated}[/]")
        cards_json = tmp / "default_cards.json"
        download_file(cards_url, cards_json, "Cards")

        # Download sets from MTGJson (small ~100KB file with all set metadata)
        console.print("\n[bold]2. Downloading MTGJson SetList...[/]")
        sets_json = tmp / "SetList.json"
        download_file(MTGJSON_SETLIST_URL, sets_json, "Sets")

        # Download rulings
        console.print("\n[bold]3. Downloading Scryfall rulings...[/]")
        rulings_url, rulings_updated = get_scryfall_bulk_url("rulings")
        console.print(f"[dim]Updated: {rulings_updated}[/]")
        rulings_json = tmp / "rulings.json"
        download_file(rulings_url, rulings_json, "Rulings")

        # Download MTGJson for EDHREC ranks
        mtgjson_path: Path | None = None
        if not skip_mtgjson:
            console.print("\n[bold]4. Downloading MTGJson for EDHREC ranks...[/]")
            mtgjson_path = tmp / "AllPrintings.json.gz"
            download_file(MTGJSON_ALLPRINTINGS_URL, mtgjson_path, "MTGJson")

        # Build unified database
        output_path = output_dir / "mtg.sqlite"
        build_unified_db(output_path, cards_json, sets_json, rulings_json, mtgjson_path)

    console.print("\n[bold green]Done![/] Unified database ready to use.")
    console.print("\n[dim]Set environment variable:[/]")
    console.print(f"  MTG_DB_PATH={output_dir}/mtg.sqlite")


if __name__ == "__main__":
    app()
