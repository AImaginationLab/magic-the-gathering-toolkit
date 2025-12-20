#!/usr/bin/env python3
"""Download Commander Spellbook combo database.

Downloads all combo variants from Commander Spellbook API and stores them
in a SQLite database for offline combo detection.

Usage:
    uv run download-spellbook [--output-dir DIR]
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Annotated, Any

import httpx
import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

console = Console()
app = typer.Typer(help="Download Commander Spellbook combo database")

BASE_URL = "https://backend.commanderspellbook.com"
PAGE_SIZE = 100


def create_database(db_path: Path) -> sqlite3.Connection:
    """Create the combos database schema."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS combos (
            id TEXT PRIMARY KEY,
            identity TEXT NOT NULL,
            mana_needed TEXT,
            mana_value INTEGER,
            bracket_tag TEXT,
            popularity INTEGER,
            description TEXT,
            card_names TEXT NOT NULL,  -- JSON array of card names
            produces TEXT,  -- JSON array of feature names
            status TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS combo_cards (
            combo_id TEXT NOT NULL,
            card_name TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            zone_locations TEXT,  -- JSON array
            must_be_commander INTEGER DEFAULT 0,
            PRIMARY KEY (combo_id, card_name),
            FOREIGN KEY (combo_id) REFERENCES combos(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS features (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            status TEXT,
            uncountable INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_combo_cards_name ON combo_cards(card_name)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_combos_identity ON combos(identity)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_combos_bracket ON combos(bracket_tag)
    """)
    conn.commit()
    return conn


def insert_combo(conn: sqlite3.Connection, variant: dict[str, Any]) -> None:
    """Insert a combo variant into the database."""
    combo_id = variant["id"]
    identity = variant.get("identity", "")
    mana_needed = variant.get("manaNeeded", "")
    mana_value = variant.get("manaValueNeeded", 0)
    bracket_tag = variant.get("bracketTag", "")
    popularity = variant.get("popularity", 0)
    description = variant.get("description", "")
    status = variant.get("status", "")

    # Extract card names
    card_names = []
    for use in variant.get("uses", []):
        card = use.get("card", {})
        card_name = card.get("name", "")
        if card_name:
            card_names.append(card_name)

            # Insert into combo_cards
            conn.execute(
                """
                INSERT OR REPLACE INTO combo_cards
                (combo_id, card_name, quantity, zone_locations, must_be_commander)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    combo_id,
                    card_name,
                    use.get("quantity", 1),
                    json.dumps(use.get("zoneLocations", [])),
                    1 if use.get("mustBeCommander") else 0,
                ),
            )

    # Extract produced features
    produces = []
    for prod in variant.get("produces", []):
        feature = prod.get("feature", {})
        feature_name = feature.get("name", "")
        if feature_name:
            produces.append(feature_name)

            # Insert feature if not exists
            conn.execute(
                """
                INSERT OR IGNORE INTO features (id, name, status, uncountable)
                VALUES (?, ?, ?, ?)
                """,
                (
                    feature.get("id"),
                    feature_name,
                    feature.get("status", ""),
                    1 if feature.get("uncountable") else 0,
                ),
            )

    # Insert combo
    conn.execute(
        """
        INSERT OR REPLACE INTO combos
        (id, identity, mana_needed, mana_value, bracket_tag, popularity,
         description, card_names, produces, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            combo_id,
            identity,
            mana_needed,
            mana_value,
            bracket_tag,
            popularity,
            description,
            json.dumps(card_names),
            json.dumps(produces),
            status,
        ),
    )


async def fetch_all_variants(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    """Fetch all combo variants from the API with pagination."""
    all_variants: list[dict[str, Any]] = []
    offset = 0

    # First request to get total count
    response = await client.get(
        f"{BASE_URL}/variants/",
        params={"limit": PAGE_SIZE, "offset": 0},
    )
    response.raise_for_status()
    data = response.json()
    total = data["count"]
    all_variants.extend(data["results"])
    offset += PAGE_SIZE

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "Downloading combos...",
            total=total,
            completed=len(all_variants),
        )

        while offset < total:
            response = await client.get(
                f"{BASE_URL}/variants/",
                params={"limit": PAGE_SIZE, "offset": offset},
            )
            response.raise_for_status()
            data = response.json()
            all_variants.extend(data["results"])
            offset += PAGE_SIZE
            progress.update(task, completed=len(all_variants))

    return all_variants


@app.command()
def download(
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Output directory for database"),
    ] = Path("resources"),
) -> None:
    """Download Commander Spellbook combo database."""
    import asyncio

    async def _download() -> None:
        db_path = output_dir / "combos.sqlite"
        console.print(f"\nCreating database at [cyan]{db_path}[/]")

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Fetch all variants
        async with httpx.AsyncClient(timeout=60.0) as client:
            variants = await fetch_all_variants(client)

        console.print(f"\nProcessing [green]{len(variants)}[/] combos...")

        # Create database and insert data
        conn = create_database(db_path)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Inserting combos...", total=len(variants))

            for variant in variants:
                insert_combo(conn, variant)
                progress.update(task, advance=1)

        conn.commit()

        # Get stats
        cursor = conn.cursor()
        combo_count = cursor.execute("SELECT COUNT(*) FROM combos").fetchone()[0]
        card_count = cursor.execute(
            "SELECT COUNT(DISTINCT card_name) FROM combo_cards"
        ).fetchone()[0]
        feature_count = cursor.execute("SELECT COUNT(*) FROM features").fetchone()[0]

        # Show bracket distribution
        bracket_dist = cursor.execute("""
            SELECT bracket_tag, COUNT(*) as cnt
            FROM combos
            GROUP BY bracket_tag
            ORDER BY cnt DESC
        """).fetchall()

        conn.close()

        # Show summary
        console.print("\n[bold green]Download complete![/]")
        console.print(f"  Combos: [cyan]{combo_count:,}[/]")
        console.print(f"  Unique cards: [cyan]{card_count:,}[/]")
        console.print(f"  Features: [cyan]{feature_count:,}[/]")
        console.print(f"  Database: [cyan]{db_path}[/]")
        console.print(f"  Size: [cyan]{db_path.stat().st_size / 1024 / 1024:.1f} MB[/]")

        # Show bracket distribution
        table = Table(title="\nBracket Distribution")
        table.add_column("Bracket", style="cyan")
        table.add_column("Count", justify="right")
        table.add_column("Description")

        bracket_names = {
            "C": "Casual (Bracket 1)",
            "P": "Precon (Bracket 2)",
            "O": "Oddball (Bracket 2)",
            "S": "Spicy (Bracket 3)",
            "W": "Powerful (Bracket 3)",
            "R": "Ruthless (Bracket 4)",
        }

        for bracket, count in bracket_dist:
            if bracket:
                table.add_row(
                    bracket, f"{count:,}", bracket_names.get(bracket, "Unknown")
                )

        console.print(table)

        # Show top combos by popularity
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        top_combos = cursor.execute("""
            SELECT card_names, bracket_tag, popularity
            FROM combos
            ORDER BY popularity DESC
            LIMIT 10
        """).fetchall()
        conn.close()

        table = Table(title="\nTop 10 Most Popular Combos")
        table.add_column("Cards", style="cyan")
        table.add_column("Bracket")
        table.add_column("Popularity", justify="right")

        for card_names_json, bracket, popularity in top_combos:
            cards = json.loads(card_names_json)
            cards_str = " + ".join(cards[:3])
            if len(cards) > 3:
                cards_str += f" (+{len(cards) - 3})"
            table.add_row(cards_str, bracket or "-", f"{popularity:,}")

        console.print(table)

    asyncio.run(_download())


@app.command()
def show(
    card: Annotated[
        str | None,
        typer.Option("--card", "-c", help="Show combos containing this card"),
    ] = None,
    bracket: Annotated[
        str | None,
        typer.Option("--bracket", "-b", help="Filter by bracket (C/P/O/S/W/R)"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Max results to show"),
    ] = 20,
    db_path: Annotated[
        Path,
        typer.Option("--db", help="Database path"),
    ] = Path("resources/combos.sqlite"),
) -> None:
    """Show combos from the database."""
    if not db_path.exists():
        console.print(f"[red]Database not found: {db_path}[/]")
        console.print("Run 'download-spellbook download' first.")
        raise typer.Exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = "SELECT id, card_names, bracket_tag, popularity, description FROM combos WHERE 1=1"
    params: list[Any] = []

    if card:
        query += " AND EXISTS (SELECT 1 FROM combo_cards WHERE combo_id = combos.id AND card_name LIKE ?)"
        params.append(f"%{card}%")

    if bracket:
        query += " AND bracket_tag = ?"
        params.append(bracket.upper())

    query += " ORDER BY popularity DESC LIMIT ?"
    params.append(limit)

    results = cursor.execute(query, params).fetchall()
    conn.close()

    if not results:
        console.print("[yellow]No combos found matching criteria.[/]")
        return

    table = Table(title=f"Combos ({len(results)} results)")
    table.add_column("ID", style="dim")
    table.add_column("Cards", style="cyan")
    table.add_column("Bracket")
    table.add_column("Pop", justify="right")

    for combo_id, card_names_json, bracket_tag, popularity, _desc in results:
        cards = json.loads(card_names_json)
        cards_str = " + ".join(cards[:3])
        if len(cards) > 3:
            cards_str += f" (+{len(cards) - 3})"
        table.add_row(combo_id[:15], cards_str, bracket_tag or "-", f"{popularity:,}")

    console.print(table)


if __name__ == "__main__":
    app()
