#!/usr/bin/env python3
"""Download and process 17lands Limited data.

Downloads game data from 17lands public datasets, aggregates card statistics,
and stores them in a SQLite database for use in recommendations.

Usage:
    uv run download-17lands [--sets SET1,SET2] [--output-dir DIR]

Example:
    uv run download-17lands --sets BLB,OTJ,MKM,LCI
"""

from __future__ import annotations

import csv
import gzip
import io
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

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
from rich.table import Table

console = Console()
app = typer.Typer(help="Download and process 17lands Limited data")

# 17lands S3 bucket URL pattern
SEVENTEEN_LANDS_BASE = "https://17lands-public.s3.amazonaws.com/analysis_data"
GAME_DATA_PATTERN = "{base}/game_data/game_data_public.{set_code}.{event_type}.csv.gz"

# Recent sets with good 17lands data coverage
RECENT_SETS = [
    "FDN",  # Foundations (2024)
    "DSK",  # Duskmourn (2024)
    "BLB",  # Bloomburrow (2024)
    "MH3",  # Modern Horizons 3 (2024)
    "OTJ",  # Outlaws of Thunder Junction (2024)
    "MKM",  # Murders at Karlov Manor (2024)
    "LCI",  # Lost Caverns of Ixalan (2023)
    "WOE",  # Wilds of Eldraine (2023)
    "LTR",  # Lord of the Rings (2023)
    "MOM",  # March of the Machine (2023)
    "ONE",  # Phyrexia: All Will Be One (2023)
    "BRO",  # Brothers' War (2022)
    "DMU",  # Dominaria United (2022)
    "SNC",  # Streets of New Capenna (2022)
    "NEO",  # Kamigawa: Neon Dynasty (2022)
]

# Event types to download (Premier has most data)
EVENT_TYPES = ["PremierDraft", "TradDraft"]


@dataclass
class CardStats:
    """Aggregated statistics for a single card."""

    card_name: str
    set_code: str

    # Counters
    games_in_hand: int = 0
    games_in_hand_won: int = 0
    games_in_opening_hand: int = 0
    games_in_opening_hand_won: int = 0
    games_not_drawn: int = 0
    games_not_drawn_won: int = 0
    times_picked: int = 0
    pick_sum: float = 0.0  # Sum of pick positions for average

    @property
    def gih_wr(self) -> float | None:
        """Games in Hand Win Rate."""
        if self.games_in_hand < 100:  # Minimum sample size
            return None
        return self.games_in_hand_won / self.games_in_hand

    @property
    def oh_wr(self) -> float | None:
        """Opening Hand Win Rate."""
        if self.games_in_opening_hand < 50:
            return None
        return self.games_in_opening_hand_won / self.games_in_opening_hand

    @property
    def gnd_wr(self) -> float | None:
        """Games Not Drawn Win Rate (baseline)."""
        if self.games_not_drawn < 100:
            return None
        return self.games_not_drawn_won / self.games_not_drawn

    @property
    def iwd(self) -> float | None:
        """Improvement When Drawn (GIH WR - GND WR)."""
        gih = self.gih_wr
        gnd = self.gnd_wr
        if gih is None or gnd is None:
            return None
        return gih - gnd

    @property
    def ata(self) -> float | None:
        """Average Taken At (pick position)."""
        if self.times_picked < 50:
            return None
        return self.pick_sum / self.times_picked

    @property
    def tier(self) -> str:
        """Compute tier based on GIH WR."""
        gih = self.gih_wr
        if gih is None:
            return "?"
        # Tiers based on 17lands community standards
        # Note: 17lands users average ~56% WR, not 50%
        if gih >= 0.60:
            return "S"
        elif gih >= 0.57:
            return "A"
        elif gih >= 0.54:
            return "B"
        elif gih >= 0.51:
            return "C"
        elif gih >= 0.48:
            return "D"
        else:
            return "F"


@dataclass
class SetAggregator:
    """Aggregates card stats for a single set."""

    set_code: str
    cards: dict[str, CardStats] = field(default_factory=dict)
    games_processed: int = 0

    def process_row(self, row: dict[str, str]) -> None:
        """Process a single game row from 17lands CSV."""
        won = row.get("won", "").lower() == "true"
        self.games_processed += 1

        # Find all card columns (deck_*, drawn_*, sideboard_*)
        for key, value in row.items():
            if not key.startswith("deck_"):
                continue

            # Extract card name from column (e.g., "deck_Mosswood_Dreadknight")
            card_name = key[5:].replace("_", " ")

            # Get counts
            try:
                in_deck = int(value or 0)
            except ValueError:
                continue

            if in_deck == 0:
                continue

            # Get corresponding drawn count
            drawn_key = f"drawn_{key[5:]}"
            opening_key = f"opening_hand_{key[5:]}"

            try:
                drawn = int(row.get(drawn_key, 0) or 0)
                opening = int(row.get(opening_key, 0) or 0)
            except ValueError:
                drawn = 0
                opening = 0

            # Get or create card stats
            if card_name not in self.cards:
                self.cards[card_name] = CardStats(card_name=card_name, set_code=self.set_code)

            stats = self.cards[card_name]

            # Update stats based on whether card was drawn
            if drawn > 0:
                stats.games_in_hand += 1
                if won:
                    stats.games_in_hand_won += 1
            else:
                stats.games_not_drawn += 1
                if won:
                    stats.games_not_drawn_won += 1

            if opening > 0:
                stats.games_in_opening_hand += 1
                if won:
                    stats.games_in_opening_hand_won += 1


def download_with_progress(url: str, description: str) -> bytes | None:
    """Download a file with progress bar, return None if not found."""
    timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)

    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            # First check if file exists
            head_response = client.head(url)
            if head_response.status_code == 404:
                return None

            with client.stream("GET", url) as response:
                if response.status_code == 404:
                    return None
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
                    chunks = []
                    for chunk in response.iter_bytes():
                        chunks.append(chunk)
                        progress.update(task, advance=len(chunk))

                    return b"".join(chunks)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return None
        raise


def process_game_data(data: bytes, set_code: str) -> SetAggregator:
    """Process gzipped CSV game data into aggregated stats."""
    aggregator = SetAggregator(set_code=set_code)

    # Decompress
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as f:
        text = f.read().decode("utf-8")

    # Parse CSV
    reader = csv.DictReader(io.StringIO(text))

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]Processing {task.description}"),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"{set_code} games", total=None)

        for i, row in enumerate(reader):
            aggregator.process_row(row)
            if i % 10000 == 0:
                progress.update(task, description=f"{set_code} games ({i:,} processed)")

        progress.update(
            task, description=f"{set_code} complete ({aggregator.games_processed:,} games)"
        )

    return aggregator


def create_database(db_path: Path) -> None:
    """Create the limited_stats database schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
        -- Card statistics from 17lands
        CREATE TABLE IF NOT EXISTS card_stats (
            id INTEGER PRIMARY KEY,
            card_name TEXT NOT NULL,
            set_code TEXT NOT NULL,

            -- Sample sizes
            games_in_hand INTEGER DEFAULT 0,
            games_in_opening_hand INTEGER DEFAULT 0,
            games_not_drawn INTEGER DEFAULT 0,

            -- Win rates (computed, 0.0-1.0)
            gih_wr REAL,           -- Games in Hand Win Rate
            oh_wr REAL,            -- Opening Hand Win Rate
            gnd_wr REAL,           -- Games Not Drawn Win Rate
            iwd REAL,              -- Improvement When Drawn

            -- Pick data
            ata REAL,              -- Average Taken At

            -- Tier (S/A/B/C/D/F)
            tier TEXT,

            -- Metadata
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(card_name, set_code)
        );

        CREATE INDEX IF NOT EXISTS idx_card_stats_set ON card_stats(set_code);
        CREATE INDEX IF NOT EXISTS idx_card_stats_name ON card_stats(card_name);
        CREATE INDEX IF NOT EXISTS idx_card_stats_tier ON card_stats(set_code, tier);
        CREATE INDEX IF NOT EXISTS idx_card_stats_gih ON card_stats(set_code, gih_wr DESC);

        -- Synergy pairs (cards that perform well together)
        CREATE TABLE IF NOT EXISTS synergy_pairs (
            id INTEGER PRIMARY KEY,
            set_code TEXT NOT NULL,
            card_a TEXT NOT NULL,
            card_b TEXT NOT NULL,
            co_occurrence_count INTEGER,
            win_rate_together REAL,
            synergy_lift REAL,  -- How much better than expected

            UNIQUE(set_code, card_a, card_b)
        );

        CREATE INDEX IF NOT EXISTS idx_synergy_set ON synergy_pairs(set_code);
        CREATE INDEX IF NOT EXISTS idx_synergy_card ON synergy_pairs(card_a);

        -- Metadata
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)

    conn.commit()
    conn.close()


def save_stats(db_path: Path, aggregator: SetAggregator) -> int:
    """Save aggregated stats to database. Returns number of cards saved."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    saved = 0
    for _card_name, stats in aggregator.cards.items():
        # Only save cards with enough data
        if stats.games_in_hand < 100:
            continue

        cursor.execute(
            """
            INSERT OR REPLACE INTO card_stats
            (card_name, set_code, games_in_hand, games_in_opening_hand, games_not_drawn,
             gih_wr, oh_wr, gnd_wr, iwd, ata, tier, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
            (
                stats.card_name,
                stats.set_code,
                stats.games_in_hand,
                stats.games_in_opening_hand,
                stats.games_not_drawn,
                stats.gih_wr,
                stats.oh_wr,
                stats.gnd_wr,
                stats.iwd,
                stats.ata,
                stats.tier,
            ),
        )
        saved += 1

    conn.commit()
    conn.close()
    return saved


def show_top_cards(aggregator: SetAggregator, n: int = 10) -> None:
    """Display top cards by GIH WR."""
    # Sort cards by GIH WR
    valid_cards = [
        (name, stats) for name, stats in aggregator.cards.items() if stats.gih_wr is not None
    ]
    valid_cards.sort(key=lambda x: x[1].gih_wr or 0, reverse=True)

    table = Table(title=f"Top {n} Cards in {aggregator.set_code}")
    table.add_column("Card", style="cyan")
    table.add_column("Tier", style="bold")
    table.add_column("GIH WR", justify="right")
    table.add_column("IWD", justify="right")
    table.add_column("Games", justify="right")

    for name, stats in valid_cards[:n]:
        tier_color = {
            "S": "bold magenta",
            "A": "green",
            "B": "blue",
            "C": "yellow",
            "D": "orange3",
            "F": "red",
        }.get(stats.tier, "white")

        table.add_row(
            name,
            f"[{tier_color}]{stats.tier}[/]",
            f"{stats.gih_wr:.1%}" if stats.gih_wr else "N/A",
            f"{stats.iwd:+.1%}" if stats.iwd else "N/A",
            f"{stats.games_in_hand:,}",
        )

    console.print(table)


@app.command()
def download(
    sets: Annotated[
        str | None,
        typer.Option("--sets", "-s", help="Comma-separated set codes (e.g., BLB,OTJ,MKM)"),
    ] = None,
    output_dir: Annotated[
        Path, typer.Option("--output-dir", "-o", help="Output directory for database")
    ] = Path("resources"),
    delay: Annotated[
        float,
        typer.Option("--delay", "-d", help="Delay between downloads in seconds (rate limiting)"),
    ] = 2.0,
    show_stats: Annotated[
        bool, typer.Option("--show-stats", help="Show top cards after processing each set")
    ] = True,
) -> None:
    """Download and process 17lands data for Limited card ratings."""

    # Determine which sets to download
    if sets:
        set_list = [s.strip().upper() for s in sets.split(",")]
    else:
        set_list = RECENT_SETS[:5]  # Default to 5 most recent
        console.print(f"[dim]No sets specified, using recent sets: {', '.join(set_list)}[/]")

    # Ensure output directory exists
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "limited_stats.sqlite"

    # Create database
    console.print(f"\n[bold]Creating database at {db_path}[/]")
    create_database(db_path)

    # Process each set
    total_cards = 0
    total_games = 0

    for i, set_code in enumerate(set_list):
        console.print(f"\n[bold cyan]Processing {set_code} ({i + 1}/{len(set_list)})[/]")

        set_aggregator = SetAggregator(set_code=set_code)

        # Try each event type
        for event_type in EVENT_TYPES:
            url = GAME_DATA_PATTERN.format(
                base=SEVENTEEN_LANDS_BASE,
                set_code=set_code,
                event_type=event_type,
            )

            console.print(f"[dim]Downloading {event_type}...[/]")
            data = download_with_progress(url, f"{set_code} {event_type}")

            if data is None:
                console.print(f"[yellow]  {event_type} not available for {set_code}[/]")
                continue

            # Process the data
            event_aggregator = process_game_data(data, set_code)

            # Merge into set aggregator
            for card_name, stats in event_aggregator.cards.items():
                if card_name not in set_aggregator.cards:
                    set_aggregator.cards[card_name] = stats
                else:
                    existing = set_aggregator.cards[card_name]
                    existing.games_in_hand += stats.games_in_hand
                    existing.games_in_hand_won += stats.games_in_hand_won
                    existing.games_in_opening_hand += stats.games_in_opening_hand
                    existing.games_in_opening_hand_won += stats.games_in_opening_hand_won
                    existing.games_not_drawn += stats.games_not_drawn
                    existing.games_not_drawn_won += stats.games_not_drawn_won

            set_aggregator.games_processed += event_aggregator.games_processed

            # Rate limiting delay
            if delay > 0:
                console.print(f"[dim]  Waiting {delay}s (rate limiting)...[/]")
                time.sleep(delay)

        # Save to database
        if set_aggregator.cards:
            saved = save_stats(db_path, set_aggregator)
            total_cards += saved
            total_games += set_aggregator.games_processed
            console.print(
                f"[green]  Saved {saved} cards from {set_aggregator.games_processed:,} games[/]"
            )

            if show_stats:
                show_top_cards(set_aggregator)
        else:
            console.print(f"[yellow]  No data found for {set_code}[/]")

    # Summary
    console.print("\n[bold green]✓ Complete![/]")
    console.print(f"  Total cards: {total_cards:,}")
    console.print(f"  Total games: {total_games:,}")
    console.print(f"  Database: {db_path}")

    # Show database size
    db_size = db_path.stat().st_size
    console.print(f"  Size: {db_size / 1024:.1f} KB")


@app.command()
def show(
    db_path: Annotated[Path, typer.Argument(help="Path to limited_stats.sqlite")] = Path(
        "resources/limited_stats.sqlite"
    ),
    set_code: Annotated[str | None, typer.Option("--set", "-s", help="Filter by set code")] = None,
    tier: Annotated[
        str | None, typer.Option("--tier", "-t", help="Filter by tier (S/A/B/C/D/F)")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Number of cards to show")] = 20,
) -> None:
    """Show card statistics from the database."""
    if not db_path.exists():
        console.print(f"[red]Database not found: {db_path}[/]")
        console.print("[dim]Run 'download-17lands' first to create the database.[/]")
        raise typer.Exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Build query
    query = "SELECT * FROM card_stats WHERE gih_wr IS NOT NULL"
    params: list[str | int] = []

    if set_code:
        query += " AND set_code = ?"
        params.append(set_code.upper())

    if tier:
        query += " AND tier = ?"
        params.append(tier.upper())

    query += " ORDER BY gih_wr DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    if not rows:
        console.print("[yellow]No cards found matching criteria[/]")
        return

    table = Table(title="Limited Card Statistics")
    table.add_column("Card", style="cyan")
    table.add_column("Set", style="dim")
    table.add_column("Tier", style="bold")
    table.add_column("GIH WR", justify="right")
    table.add_column("IWD", justify="right")
    table.add_column("Games", justify="right", style="dim")

    for row in rows:
        tier_color = {
            "S": "bold magenta",
            "A": "green",
            "B": "blue",
            "C": "yellow",
            "D": "orange3",
            "F": "red",
        }.get(row["tier"], "white")

        table.add_row(
            row["card_name"],
            row["set_code"],
            f"[{tier_color}]{row['tier']}[/]",
            f"{row['gih_wr']:.1%}" if row["gih_wr"] else "N/A",
            f"{row['iwd']:+.1%}" if row["iwd"] else "N/A",
            f"{row['games_in_hand']:,}",
        )

    console.print(table)
    conn.close()


def main() -> None:
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
