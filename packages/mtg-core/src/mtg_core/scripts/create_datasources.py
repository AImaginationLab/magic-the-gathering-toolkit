#!/usr/bin/env python3
"""Download and create MTG database files.

Downloads:
- MTGJson AllPrintings.sqlite (card data, rules, legalities)
- Scryfall default_cards bulk data (all printings with images, prices) -> converts to SQLite

Usage:
    uv run create-datasources [--output-dir DIR]
"""

from __future__ import annotations

import contextlib
import gzip
import json
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import httpx
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
MTGJSON_SQLITE_URL = "https://mtgjson.com/api/v5/AllPrintings.sqlite.gz"
SCRYFALL_BULK_API = "https://api.scryfall.com/bulk-data"


def get_scryfall_download_url(bulk_type: str = "default_cards") -> tuple[str, str]:
    """Get the download URL for Scryfall bulk data."""
    console.print("[dim]Fetching Scryfall bulk data info...[/]")

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
    # Use longer read timeout for large file downloads
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


def create_mtgjson_indexes(db_path: Path) -> None:
    """Create performance indexes on MTGJson database."""
    console.print("[dim]Creating performance indexes...[/]")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    indexes = [
        ("idx_cards_name", "cards", "name"),
        ("idx_cards_type", "cards", "type"),
        ("idx_cards_types", "cards", "types"),
        ("idx_cards_rarity", "cards", "rarity"),
        ("idx_cards_colors", "cards", "colors"),
        ("idx_cards_colorIdentity", "cards", "colorIdentity"),
        ("idx_cards_setCode", "cards", "setCode"),
        ("idx_cards_manaValue", "cards", "manaValue"),
        ("idx_cards_subtypes", "cards", "subtypes"),
        ("idx_cards_artist", "cards", "artist"),
        ("idx_cardLegalities_uuid", "cardLegalities", "uuid"),
        ("idx_cardLegalities_format", "cardLegalities", "format"),
        ("idx_cardRulings_uuid", "cardRulings", "uuid"),
        ("idx_sets_release_date", "sets", "releaseDate"),
    ]

    # Create composite indexes for common query patterns
    composite_indexes = [
        ("idx_cards_artist_setCode", "cards", "artist, setCode"),
        ("idx_cards_artist_extras", "cards", "artist, isPromo, isFunny"),
        # Covering index for artist aggregation queries (get_all_artists, search_artists)
        # Includes setCode for JOIN with sets table and extras flags for filtering
        ("idx_cards_artist_setCode_extras", "cards", "artist, setCode, isPromo, isFunny"),
        # Index for featured artist cards ordered by rarity
        ("idx_cards_artist_rarity", "cards", "artist, rarity"),
    ]

    created = 0
    for idx_name, table, column in indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
            created += 1
        except sqlite3.OperationalError:
            pass  # Index may already exist or column doesn't exist

    for idx_name, table, columns in composite_indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})")
            created += 1
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()
    console.print(f"[green]✓[/] Created {created} indexes")


def create_fts5_index(db_path: Path, force_rebuild: bool = False) -> None:
    """Create FTS5 full-text search index for card searches.

    Creates a virtual table with porter tokenizer for stemming on:
    - name: Card name
    - flavorName: Alternate name (e.g., crossover cards like Final Fantasy)
    - type: Full type line
    - text: Oracle text

    Uses batched inserts and WAL mode to prevent database corruption during
    large bulk operations.

    Args:
        db_path: Path to the SQLite database
        force_rebuild: If True, drops and recreates the FTS table even if it exists
    """
    console.print("[dim]Creating FTS5 full-text search index...[/]")

    # Batch size for bulk inserts to avoid memory exhaustion
    BATCH_SIZE = 10000

    # Use isolation_level=None for autocommit mode (required for PRAGMA commands)
    conn = sqlite3.connect(db_path, isolation_level=None)
    cursor = conn.cursor()

    try:
        # Enable WAL mode for better reliability during large writes
        # WAL prevents corruption during crashes and handles concurrent access better
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
        cursor.execute("PRAGMA temp_store=MEMORY")

        # Check if FTS table exists and is valid
        needs_rebuild = force_rebuild
        if not needs_rebuild:
            try:
                cursor.execute("SELECT COUNT(*) FROM cards_fts")
                fts_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM cards")
                cards_count = cursor.fetchone()[0]
                # Rebuild if counts don't match
                if fts_count != cards_count:
                    needs_rebuild = True
            except sqlite3.OperationalError:
                # Table doesn't exist
                needs_rebuild = True
            except sqlite3.DatabaseError as e:
                # FTS table is corrupted
                console.print(f"[yellow]FTS table corrupted: {e}[/]")
                needs_rebuild = True

        if needs_rebuild:
            # Drop existing FTS table and triggers to start fresh
            console.print("[dim]Dropping existing FTS table...[/]")

            # Start explicit transaction for cleanup
            cursor.execute("BEGIN IMMEDIATE")
            try:
                cursor.execute("DROP TRIGGER IF EXISTS cards_fts_insert")
                cursor.execute("DROP TRIGGER IF EXISTS cards_fts_update")
                cursor.execute("DROP TRIGGER IF EXISTS cards_fts_delete")

                # Try to drop the FTS table normally first
                try:
                    cursor.execute("DROP TABLE IF EXISTS cards_fts")
                except sqlite3.DatabaseError as e:
                    # FTS table corrupted - need to VACUUM to rebuild database
                    console.print(f"[yellow]Warning:[/] FTS table corrupted: {e}")
                    console.print("[dim]Running VACUUM to repair database...[/]")
                    cursor.execute("ROLLBACK")
                    cursor.execute("VACUUM")
                    cursor.execute("BEGIN IMMEDIATE")

                cursor.execute("COMMIT")
            except Exception:
                cursor.execute("ROLLBACK")
                raise

        # Create FTS5 virtual table with porter tokenizer for stemming
        cursor.execute("BEGIN IMMEDIATE")
        try:
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
                    uuid UNINDEXED,
                    name,
                    flavorName,
                    type,
                    text,
                    tokenize='porter unicode61'
                )
            """)
            cursor.execute("COMMIT")
        except Exception:
            cursor.execute("ROLLBACK")
            raise

        # Check if FTS table needs population
        cursor.execute("SELECT COUNT(*) FROM cards_fts")
        fts_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cards")
        cards_count = cursor.fetchone()[0]

        if fts_count == 0 or fts_count < cards_count:
            # Clear and repopulate the FTS table using batched inserts
            console.print(
                f"[dim]Populating FTS5 index ({cards_count:,} cards in batches of {BATCH_SIZE:,})...[/]"
            )

            # Clear existing data first
            cursor.execute("BEGIN IMMEDIATE")
            try:
                cursor.execute("DELETE FROM cards_fts")
                cursor.execute("COMMIT")
            except Exception:
                cursor.execute("ROLLBACK")
                raise

            # Use batched inserts to avoid memory issues with large datasets
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
                task = progress.add_task("Indexing", total=cards_count)

                while offset < cards_count:
                    cursor.execute("BEGIN IMMEDIATE")
                    try:
                        cursor.execute(
                            """
                            INSERT INTO cards_fts(uuid, name, flavorName, type, text)
                            SELECT uuid, name, flavorName, type, text FROM cards
                            LIMIT ? OFFSET ?
                            """,
                            (BATCH_SIZE, offset),
                        )
                        batch_count = cursor.rowcount
                        cursor.execute("COMMIT")

                        inserted += batch_count
                        offset += BATCH_SIZE
                        progress.update(task, completed=min(inserted, cards_count))

                    except Exception:
                        cursor.execute("ROLLBACK")
                        raise

            console.print(f"[green]OK[/] Indexed {inserted:,} cards for full-text search")
        else:
            console.print("[green]OK[/] FTS5 index already populated")

        # Create triggers to keep FTS in sync with cards table
        cursor.execute("BEGIN IMMEDIATE")
        try:
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS cards_fts_insert AFTER INSERT ON cards
                BEGIN
                    INSERT INTO cards_fts(uuid, name, flavorName, type, text)
                    VALUES (NEW.uuid, NEW.name, NEW.flavorName, NEW.type, NEW.text);
                END
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS cards_fts_update AFTER UPDATE ON cards
                BEGIN
                    UPDATE cards_fts SET name = NEW.name, flavorName = NEW.flavorName, type = NEW.type, text = NEW.text
                    WHERE uuid = NEW.uuid;
                END
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS cards_fts_delete AFTER DELETE ON cards
                BEGIN
                    DELETE FROM cards_fts WHERE uuid = OLD.uuid;
                END
            """)
            cursor.execute("COMMIT")
        except Exception:
            cursor.execute("ROLLBACK")
            raise

        console.print("[green]OK[/] FTS5 triggers created")

        # Optimize the FTS index after bulk insert for better query performance
        console.print("[dim]Optimizing FTS5 index...[/]")
        cursor.execute("INSERT INTO cards_fts(cards_fts) VALUES('optimize')")

        # Checkpoint WAL to main database file
        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")

        # Verify database integrity
        cursor.execute("PRAGMA integrity_check(1)")
        result = cursor.fetchone()
        if result[0] != "ok":
            console.print(f"[red]Warning:[/] Integrity check failed: {result[0]}")
        else:
            console.print("[green]OK[/] Database integrity verified")

    except sqlite3.OperationalError as e:
        if "no such module: fts5" in str(e).lower():
            console.print("[yellow]Warning:[/] FTS5 not available in this SQLite build")
            console.print("[dim]Card text search will fall back to LIKE queries[/]")
        else:
            raise
    finally:
        # Ensure WAL is checkpointed before closing
        with contextlib.suppress(sqlite3.Error):
            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()


def cleanup_wal_files(db_path: Path) -> None:
    """Remove stale WAL files that can cause database corruption.

    SQLite WAL (Write-Ahead Log) files are created when using WAL journal mode.
    If a database is replaced (e.g., fresh download) while stale WAL files exist,
    SQLite will try to recover from these mismatched files, causing corruption.
    """
    wal_file = db_path.parent / f"{db_path.name}-wal"
    shm_file = db_path.parent / f"{db_path.name}-shm"

    for f in [wal_file, shm_file]:
        if f.exists():
            console.print(f"[dim]Removing stale WAL file: {f.name}[/]")
            f.unlink()


def download_mtgjson(output_dir: Path) -> Path:
    """Download and extract MTGJson AllPrintings.sqlite."""
    console.print("\n[bold]Downloading MTGJson AllPrintings.sqlite...[/]")

    output_file = output_dir / "AllPrintings.sqlite"

    # CRITICAL: Remove stale WAL files before downloading
    # If old -wal/-shm files exist when we extract a new database, SQLite will
    # try to apply them to the new database, causing "database disk image is malformed"
    cleanup_wal_files(output_file)

    # Download gzipped file
    with tempfile.NamedTemporaryFile(suffix=".sqlite.gz", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        download_file(MTGJSON_SQLITE_URL, tmp_path, "MTGJson")

        # Extract
        console.print("[dim]Extracting...[/]")
        with gzip.open(tmp_path, "rb") as f_in, output_file.open("wb") as f_out:
            while chunk := f_in.read(8192):
                f_out.write(chunk)
    finally:
        tmp_path.unlink(missing_ok=True)

    # Create indexes for better query performance
    create_mtgjson_indexes(output_file)

    # Create FTS5 full-text search index
    create_fts5_index(output_file)

    # Check file size
    size_mb = output_file.stat().st_size / (1024 * 1024)
    console.print(f"[green]✓[/] Saved AllPrintings.sqlite ({size_mb:.1f} MB)")

    return output_file


def download_scryfall(output_dir: Path, bulk_type: str = "default_cards") -> Path:
    """Download Scryfall card data JSON and convert to SQLite.

    Args:
        output_dir: Directory to save the database
        bulk_type: Scryfall bulk data type:
            - "default_cards": All printings (recommended for price/printing accuracy)
            - "unique_artwork": One per unique art (smaller but missing printings)
    """
    console.print(f"\n[bold]Downloading Scryfall {bulk_type} data...[/]")

    # Get download URL
    download_url, updated_at = get_scryfall_download_url(bulk_type)
    console.print(f"[dim]Data updated: {updated_at}[/]")

    # Download JSON
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        download_file(download_url, tmp_path, "Scryfall")

        # Parse JSON and convert to SQLite
        console.print("[dim]Converting to SQLite...[/]")
        output_file = output_dir / "scryfall.sqlite"

        create_scryfall_db(tmp_path, output_file, updated_at)
    finally:
        tmp_path.unlink(missing_ok=True)

    size_mb = output_file.stat().st_size / (1024 * 1024)
    console.print(f"[green]✓[/] Saved scryfall.sqlite ({size_mb:.1f} MB)")

    return output_file


def create_scryfall_db(json_path: Path, db_path: Path, updated_at: str) -> None:
    """Create SQLite database from Scryfall JSON."""
    # Remove existing db
    db_path.unlink(missing_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE cards (
            scryfall_id TEXT PRIMARY KEY,
            oracle_id TEXT,
            name TEXT NOT NULL,
            set_code TEXT,
            collector_number TEXT,

            -- Images
            image_small TEXT,
            image_normal TEXT,
            image_large TEXT,
            image_png TEXT,
            image_art_crop TEXT,
            image_border_crop TEXT,

            -- Prices (in cents to avoid float issues, NULL if unavailable)
            price_usd INTEGER,
            price_usd_foil INTEGER,
            price_eur INTEGER,
            price_eur_foil INTEGER,

            -- Purchase links
            purchase_tcgplayer TEXT,
            purchase_cardmarket TEXT,
            purchase_cardhoarder TEXT,

            -- Related links
            link_edhrec TEXT,
            link_gatherer TEXT,

            -- Visual properties
            illustration_id TEXT,
            image_status TEXT,
            highres_image INTEGER,
            border_color TEXT,
            frame TEXT,
            full_art INTEGER,

            -- Art priority for efficient unique artwork queries (0=borderless, 1=full_art, 2=regular)
            art_priority INTEGER DEFAULT 2,

            -- Availability
            games TEXT,
            finishes TEXT
        )
    """)

    cursor.execute("CREATE INDEX idx_cards_oracle_id ON cards(oracle_id)")
    cursor.execute("CREATE INDEX idx_cards_name ON cards(name)")
    cursor.execute("CREATE INDEX idx_cards_set_code ON cards(set_code)")
    cursor.execute("CREATE INDEX idx_cards_name_set ON cards(name, set_code)")
    cursor.execute(
        "CREATE INDEX idx_cards_illustration_priority ON cards(illustration_id, art_priority, set_code)"
    )
    cursor.execute("CREATE INDEX idx_cards_name_illustration ON cards(name, illustration_id)")
    cursor.execute(
        "CREATE INDEX idx_cards_price_usd ON cards(price_usd) WHERE price_usd IS NOT NULL"
    )

    cursor.execute("""
        CREATE TABLE meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Load JSON
    with json_path.open() as f:
        cards = json.load(f)

    console.print(f"[dim]Processing {len(cards):,} cards...[/]")

    # Insert cards with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Importing cards"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Importing", total=len(cards))

        for card in cards:
            insert_card(cursor, card)
            progress.update(task, advance=1)

    # Insert metadata
    cursor.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?)",
        ("created_at", datetime.now().isoformat()),
    )
    cursor.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?)", ("scryfall_updated_at", updated_at)
    )
    cursor.execute("INSERT INTO meta (key, value) VALUES (?, ?)", ("card_count", str(len(cards))))

    conn.commit()
    conn.close()


def insert_card(cursor: sqlite3.Cursor, card: dict[str, Any]) -> None:
    """Insert a single card into the database."""

    def price_to_cents(price: str | None) -> int | None:
        if price is None:
            return None
        try:
            return int(float(price) * 100)
        except (ValueError, TypeError):
            return None

    def calculate_art_priority(card_data: dict[str, Any]) -> int:
        """Calculate art priority: 0=borderless, 1=full_art, 2=regular."""
        if card_data.get("border_color") == "borderless":
            return 0
        if card_data.get("full_art"):
            return 1
        return 2

    # Get image URIs
    images = card.get("image_uris", {})

    # Get prices
    prices = card.get("prices", {})

    # Get purchase URIs
    purchase = card.get("purchase_uris", {})

    # Get related URIs
    related = card.get("related_uris", {})

    cursor.execute(
        """
        INSERT OR REPLACE INTO cards (
            scryfall_id, oracle_id, name, set_code, collector_number,
            image_small, image_normal, image_large, image_png,
            image_art_crop, image_border_crop,
            price_usd, price_usd_foil, price_eur, price_eur_foil,
            purchase_tcgplayer, purchase_cardmarket, purchase_cardhoarder,
            link_edhrec, link_gatherer,
            illustration_id, image_status, highres_image, border_color,
            frame, full_art, art_priority, games, finishes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            card.get("id"),
            card.get("oracle_id"),
            card.get("name"),
            card.get("set"),
            card.get("collector_number"),
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
            card.get("image_status"),
            1 if card.get("highres_image") else 0,
            card.get("border_color"),
            card.get("frame"),
            1 if card.get("full_art") else 0,
            calculate_art_priority(card),
            json.dumps(card.get("games", [])),
            json.dumps(card.get("finishes", [])),
        ),
    )


GITHUB_COMBOS_URL = (
    "https://github.com/AImaginationLab/magic-the-gathering-toolkit"
    "/releases/latest/download/combos.sqlite"
)


def download_combos(output_path: Path) -> Path:
    """Download pre-built combo database from GitHub Releases.

    The combo database contains 70k+ combos from Commander Spellbook,
    pre-processed into SQLite format.
    """
    console.print("\n[bold]Downloading Commander Spellbook combos...[/]")

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Download directly to output path
    download_file(GITHUB_COMBOS_URL, output_path, "Combos")

    size_mb = output_path.stat().st_size / (1024 * 1024)
    console.print(f"[green]✓[/] Saved combos.sqlite ({size_mb:.1f} MB)")

    return output_path


def _clear_all_caches() -> None:
    """Clear all cached data (images, printings, synergies, artists)."""
    from ..cache import clear_data_cache, get_data_cache_stats
    from ..config import get_settings

    console.print("[bold]Clearing cached data...[/]\n")

    # Clear data cache (printings, synergies, artists)
    stats = get_data_cache_stats()
    if stats["total_files"] > 0:
        console.print(
            f"[dim]Data cache: {stats['total_files']} files, {stats['total_mb']:.1f} MB[/]"
        )
        clear_data_cache()
        console.print("[green]✓[/] Cleared data cache (printings, synergies, artists)")
    else:
        console.print("[dim]Data cache already empty[/]")

    # Clear image cache
    settings = get_settings()
    image_cache_dir = settings.image_cache_dir
    if image_cache_dir.exists():
        image_count = 0
        image_bytes = 0
        for pattern in ("*.webp", "*.png"):
            for f in image_cache_dir.glob(pattern):
                image_bytes += f.stat().st_size
                f.unlink(missing_ok=True)
                image_count += 1

        # Remove metadata file
        metadata_file = image_cache_dir / "cache_metadata.json"
        if metadata_file.exists():
            metadata_file.unlink(missing_ok=True)

        if image_count > 0:
            console.print(
                f"[green]✓[/] Cleared image cache ({image_count} files, {image_bytes / 1024 / 1024:.1f} MB)"
            )
        else:
            console.print("[dim]Image cache already empty[/]")
    else:
        console.print("[dim]Image cache directory doesn't exist[/]")

    console.print()


app = typer.Typer(
    name="create-datasources",
    help="Download and create MTG database files.",
    no_args_is_help=False,
    invoke_without_command=True,
)


@app.callback()
def main_callback(
    ctx: typer.Context,
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            "-o",
            help="Directory to save database files",
        ),
    ] = Path("resources"),
    skip_mtgjson: Annotated[
        bool,
        typer.Option("--skip-mtgjson", help="Skip downloading MTGJson"),
    ] = False,
    skip_scryfall: Annotated[
        bool,
        typer.Option("--skip-scryfall", help="Skip downloading Scryfall"),
    ] = False,
    skip_combos: Annotated[
        bool,
        typer.Option("--skip-combos", help="Skip initializing combo database"),
    ] = False,
    clear_cache: Annotated[
        bool,
        typer.Option(
            "--clear-cache", help="Clear all cached data (images, printings, synergies, artists)"
        ),
    ] = False,
) -> None:
    """Download MTG databases and combo data.

    By default, downloads MTGJson, Scryfall data, and the combo database from GitHub Releases.
    """
    # Only run if no subcommand was invoked
    if ctx.invoked_subcommand is not None:
        return

    from ..config import get_settings

    console.print("[bold]MTG Database Setup[/]\n")

    # Clear cache if requested
    if clear_cache:
        _clear_all_caches()

    # Create output directory
    output_dir_resolved = output_dir.expanduser().resolve()
    output_dir_resolved.mkdir(parents=True, exist_ok=True)
    console.print(f"Output directory: [cyan]{output_dir_resolved}[/]")

    if not skip_mtgjson:
        download_mtgjson(output_dir_resolved)

    if not skip_scryfall:
        download_scryfall(output_dir_resolved)

    if not skip_combos:
        settings = get_settings()
        download_combos(settings.combo_db_path)

    console.print("\n[bold green]Done![/] All databases are ready to use.")
    console.print("\n[dim]Set environment variables if using a custom location:[/]")
    console.print(f"  MTG_DB_PATH={output_dir_resolved}/AllPrintings.sqlite")
    console.print(f"  SCRYFALL_DB_PATH={output_dir_resolved}/scryfall.sqlite")


@app.command("update")
def update_existing(
    db_path: Annotated[
        Path | None,
        typer.Argument(help="Path to AllPrintings.sqlite (optional, uses default if not provided)"),
    ] = None,
    force_fts: Annotated[
        bool,
        typer.Option("--force-fts", help="Force rebuild of FTS index even if it exists"),
    ] = False,
) -> None:
    """Apply all indexes and FTS to an existing MTGJson database.

    This updates an existing database with performance indexes and full-text search
    without re-downloading. Useful after downloading databases separately or when
    indexes need to be rebuilt.
    """
    from ..config import get_settings

    # Use default path if not provided
    if db_path is None:
        db_path = get_settings().mtg_db_path

    console.print("[bold]Updating MTGJson database[/]\n")
    console.print(f"Database: [cyan]{db_path}[/]\n")

    if not db_path.exists():
        console.print(f"[red]Error:[/] Database not found: {db_path}")
        console.print("[dim]Run 'uv run create-datasources' to download the database first.[/]")
        raise typer.Exit(1)

    # Clean up stale WAL files that may cause corruption
    cleanup_wal_files(db_path)

    create_mtgjson_indexes(db_path)
    create_fts5_index(db_path, force_rebuild=force_fts)
    console.print("\n[bold green]Done![/] Database updated with all indexes.")


@app.command("create-indexes")
def create_indexes(
    db_path: Annotated[
        Path,
        typer.Argument(help="Path to AllPrintings.sqlite"),
    ],
) -> None:
    """Add performance indexes to an existing MTGJson database.

    DEPRECATED: Use 'update' command instead which applies both indexes and FTS.
    """
    console.print("[yellow]Note:[/] Consider using 'uv run create-datasources update' instead.\n")
    console.print("[bold]Adding indexes to MTGJson database[/]\n")

    if not db_path.exists():
        console.print(f"[red]Error:[/] Database not found: {db_path}")
        raise typer.Exit(1)

    create_mtgjson_indexes(db_path)
    console.print("\n[bold green]Done![/]")


@app.command("create-fts")
def create_fts(
    db_path: Annotated[
        Path,
        typer.Argument(help="Path to AllPrintings.sqlite"),
    ],
) -> None:
    """Create FTS5 full-text search index on an existing MTGJson database."""
    console.print("[bold]Creating FTS5 index on MTGJson database[/]\n")

    if not db_path.exists():
        console.print(f"[red]Error:[/] Database not found: {db_path}")
        raise typer.Exit(1)

    create_fts5_index(db_path)
    console.print("\n[bold green]Done![/]")


@app.command("init-combos")
def init_combos(
    output_path: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Path to combo database (default: ~/.mtg-spellbook/combos.sqlite)",
        ),
    ] = None,
    json_path: Annotated[
        Path | None,
        typer.Option(
            "--json",
            "-j",
            help="Path to additional combos JSON file to import",
        ),
    ] = None,
    include_legacy: Annotated[
        bool,
        typer.Option(
            "--include-legacy/--no-legacy",
            help="Include hardcoded combos from KNOWN_COMBOS",
        ),
    ] = True,
) -> None:
    """Initialize the combo database with known combos.

    By default, imports combos from the hardcoded KNOWN_COMBOS list.
    Optionally imports additional combos from a JSON file.
    """
    import asyncio

    from ..config import get_settings
    from ..data.database.combos import ComboDatabase
    from ..tools.synergy.constants import KNOWN_COMBOS

    async def _init_combos() -> None:
        # Determine output path
        db_path = output_path or get_settings().combo_db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

        console.print("[bold]Initializing Combo Database[/]")
        console.print(f"Output: [cyan]{db_path}[/]\n")

        # Connect to database
        combo_db = ComboDatabase(db_path)
        await combo_db.connect()

        try:
            total_imported = 0

            # Import legacy combos
            if include_legacy:
                console.print("[dim]Importing hardcoded KNOWN_COMBOS...[/]")
                count = await combo_db.import_from_legacy_format(KNOWN_COMBOS)
                console.print(f"[green]✓[/] Imported {count} combos from KNOWN_COMBOS")
                total_imported += count

            # Import from JSON file
            if json_path:
                if json_path.exists():
                    console.print(f"[dim]Importing from {json_path}...[/]")
                    count = await combo_db.import_from_json(json_path)
                    console.print(f"[green]✓[/] Imported {count} combos from JSON")
                    total_imported += count
                else:
                    console.print(f"[yellow]Warning:[/] JSON file not found: {json_path}")

            # Show final count
            final_count = await combo_db.get_combo_count()
            console.print(f"\n[bold green]Done![/] Combo database has {final_count} combos")

        finally:
            await combo_db.close()

    asyncio.run(_init_combos())


@app.command("clear-cache")
def clear_cache_cmd() -> None:
    """Clear all cached data (images, printings, synergies, artists).

    Use this when refreshing datasources or to free up disk space.
    Cached data will be regenerated on next access.
    """
    _clear_all_caches()
    console.print("[bold green]Done![/] All caches cleared.")


if __name__ == "__main__":
    app()
