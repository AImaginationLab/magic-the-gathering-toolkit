#!/usr/bin/env python3
"""Download and create MTG database files.

Downloads:
- MTGJson AllPrintings.sqlite (card data, rules, legalities)
- Scryfall unique-artwork bulk data (images, prices) -> converts to SQLite

Usage:
    uv run create-datasources [--output-dir DIR]
"""

from __future__ import annotations

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


def get_scryfall_download_url(bulk_type: str = "unique_artwork") -> tuple[str, str]:
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
        ("idx_cardLegalities_uuid", "cardLegalities", "uuid"),
        ("idx_cardLegalities_format", "cardLegalities", "format"),
        ("idx_cardRulings_uuid", "cardRulings", "uuid"),
    ]

    created = 0
    for idx_name, table, column in indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
            created += 1
        except sqlite3.OperationalError:
            pass  # Index may already exist or column doesn't exist

    conn.commit()
    conn.close()
    console.print(f"[green]✓[/] Created {created} indexes")


def download_mtgjson(output_dir: Path) -> Path:
    """Download and extract MTGJson AllPrintings.sqlite."""
    console.print("\n[bold]Downloading MTGJson AllPrintings.sqlite...[/]")

    output_file = output_dir / "AllPrintings.sqlite"

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

    # Check file size
    size_mb = output_file.stat().st_size / (1024 * 1024)
    console.print(f"[green]✓[/] Saved AllPrintings.sqlite ({size_mb:.1f} MB)")

    return output_file


def download_scryfall(output_dir: Path) -> Path:
    """Download Scryfall unique-artwork JSON and convert to SQLite."""
    console.print("\n[bold]Downloading Scryfall unique-artwork data...[/]")

    # Get download URL
    download_url, updated_at = get_scryfall_download_url("unique_artwork")
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
) -> None:
    """Download MTG databases and initialize combo data.

    By default, downloads MTGJson, Scryfall data, and initializes the combo database.
    """
    # Only run if no subcommand was invoked
    if ctx.invoked_subcommand is not None:
        return

    import asyncio

    from ..config import get_settings
    from ..data.database.combos import ComboDatabase
    from ..tools.synergy.constants import KNOWN_COMBOS

    console.print("[bold]MTG Database Setup[/]\n")

    # Create output directory
    output_dir_resolved = output_dir.expanduser().resolve()
    output_dir_resolved.mkdir(parents=True, exist_ok=True)
    console.print(f"Output directory: [cyan]{output_dir_resolved}[/]")

    if not skip_mtgjson:
        download_mtgjson(output_dir_resolved)

    if not skip_scryfall:
        download_scryfall(output_dir_resolved)

    if not skip_combos:

        async def _init_combos() -> None:
            settings = get_settings()
            db_path = settings.combo_db_path
            db_path.parent.mkdir(parents=True, exist_ok=True)

            console.print("\n[bold]Initializing Combo Database[/]")
            console.print(f"Output: [cyan]{db_path}[/]\n")

            combo_db = ComboDatabase(db_path)
            await combo_db.connect()

            try:
                console.print("[dim]Importing hardcoded KNOWN_COMBOS...[/]")
                count = await combo_db.import_from_legacy_format(KNOWN_COMBOS)
                console.print(f"[green]✓[/] Imported {count} combos from KNOWN_COMBOS")

                # Also import from new_combos_draft.json if it exists
                json_path = Path("new_combos_draft.json")
                if json_path.exists():
                    console.print(f"[dim]Importing from {json_path}...[/]")
                    json_count = await combo_db.import_from_json(json_path)
                    console.print(f"[green]✓[/] Imported {json_count} combos from JSON")

                final_count = await combo_db.get_combo_count()
                console.print(f"[green]✓[/] Combo database has {final_count} combos")
            finally:
                await combo_db.close()

        asyncio.run(_init_combos())

    console.print("\n[bold green]Done![/] All databases are ready to use.")
    console.print("\n[dim]Set environment variables if using a custom location:[/]")
    console.print(f"  MTG_DB_PATH={output_dir_resolved}/AllPrintings.sqlite")
    console.print(f"  SCRYFALL_DB_PATH={output_dir_resolved}/scryfall.sqlite")


@app.command("create-indexes")
def create_indexes(
    db_path: Annotated[
        Path,
        typer.Argument(help="Path to AllPrintings.sqlite"),
    ],
) -> None:
    """Add performance indexes to an existing MTGJson database."""
    console.print("[bold]Adding indexes to MTGJson database[/]\n")

    if not db_path.exists():
        console.print(f"[red]Error:[/] Database not found: {db_path}")
        raise typer.Exit(1)

    create_mtgjson_indexes(db_path)
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


if __name__ == "__main__":
    app()
