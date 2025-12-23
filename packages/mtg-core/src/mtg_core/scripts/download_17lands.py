#!/usr/bin/env python3
"""Download and process 17lands Limited data using DuckDB.

Downloads game data from 17lands public datasets, aggregates card statistics,
and stores them in a SQLite database for use in recommendations.

Performance optimizations:
- Async concurrent downloads with aiohttp
- DuckDB for blazing-fast CSV parsing and aggregation
- SQL self-join for pair computation
- Direct gzipped CSV querying

Usage:
    uv run download-17lands [--sets SET1,SET2] [--output-dir DIR]

Example:
    uv run download-17lands --sets BLB,OTJ,MKM,LCI
"""

from __future__ import annotations

import asyncio
import csv
import io
import sqlite3
import time
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import polars as pl
import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

if TYPE_CHECKING:
    import aiohttp

console = Console(force_terminal=True)
app = typer.Typer(help="Download and process 17lands Limited data")

# 17lands S3 bucket URL pattern
SEVENTEEN_LANDS_BASE = "https://17lands-public.s3.amazonaws.com/analysis_data"
GAME_DATA_PATTERN = "{base}/game_data/game_data_public.{set_code}.{event_type}.csv.gz"
PUBLIC_DATASETS_URL = "https://www.17lands.com/public_datasets"

# Dictionary URLs (card/ability definitions)
ABILITIES_URL = f"{SEVENTEEN_LANDS_BASE}/cards/abilities.csv"
CARDS_DICT_URL = f"{SEVENTEEN_LANDS_BASE}/cards/cards.csv"

# All event types available on 17lands
ALL_EVENT_TYPES = [
    "PremierDraft",
    "TradDraft",
    "QuickDraft",
    "Sealed",
    "TradSealed",
    "PickTwoDraft",
    "PickTwoTradDraft",
]

# Primary event types to download (have most data)
EVENT_TYPES = ["PremierDraft", "TradDraft"]

# All known 17lands sets (from https://www.17lands.com/public_datasets)
# This is a comprehensive list - the download will probe each and skip 404s
KNOWN_SETS = [
    # 2025 (current/upcoming)
    "TLA",  # Terra Lumen Arcana
    "EOE",  # Echoes of Eternity
    "FIN",  # Final Fantasy collab
    "TDM",  # Thunder Junction
    # 2024-2025
    "FDN",  # Foundations
    "DSK",  # Duskmourn
    "BLB",  # Bloomburrow
    "MH3",  # Modern Horizons 3
    "OTJ",  # Outlaws of Thunder Junction
    "MKM",  # Murders at Karlov Manor
    "DFT",  # Draft format
    "PIO",  # Pioneer Masters
    "OM1",  # Otaria Masters
    # 2023
    "LCI",  # Lost Caverns of Ixalan
    "WOE",  # Wilds of Eldraine
    "LTR",  # Lord of the Rings
    "MOM",  # March of the Machine
    "ONE",  # Phyrexia: All Will Be One
    # 2022
    "BRO",  # Brothers' War
    "DMU",  # Dominaria United
    "SNC",  # Streets of New Capenna
    "NEO",  # Kamigawa: Neon Dynasty
    "VOW",  # Crimson Vow
    "HBG",  # Alchemy Horizons: Baldur's Gate
    # 2021
    "MID",  # Midnight Hunt
    "AFR",  # Adventures in the Forgotten Realms
    "STX",  # Strixhaven
    "KHM",  # Kaldheim
    # 2020
    "ZNR",  # Zendikar Rising
    "M21",  # Core Set 2021
    "IKO",  # Ikoria
    "THB",  # Theros Beyond Death
    # 2019
    "ELD",  # Throne of Eldraine
    "M20",  # Core Set 2020
    "WAR",  # War of the Spark
    "RNA",  # Ravnica Allegiance
    "GRN",  # Guilds of Ravnica
    # Masters/Remastered sets
    "2XM",  # Double Masters
    "2X2",  # Double Masters 2022
    "DMR",  # Dominaria Remastered
    "SIR",  # Shadows over Innistrad Remastered
    "KTK",  # Khans of Tarkir (remastered on Arena)
    "AKR",  # Amonkhet Remastered
    "KLR",  # Kaladesh Remastered
    # Cube and special formats
    "Cube_-_Powered",  # Powered Vintage Cube
    "Cube_-_Legacy",  # Legacy Cube
    "Cube_-_Artifact",  # Artifact Cube
]

# Cache for discovered sets (populated by probing S3)
_discovered_sets_cache: dict[str, list[str]] | None = None
SETS_CACHE_PATH = Path.home() / ".cache" / "mtg-toolkit" / "17lands_sets.json"


async def _probe_set_availability(
    session: Any,  # aiohttp.ClientSession
    set_code: str,
) -> tuple[str, list[str]]:
    """Probe S3 to find which event types are available for a set."""
    available: list[str] = []

    for event_type in ALL_EVENT_TYPES:
        url = GAME_DATA_PATTERN.format(
            base=SEVENTEEN_LANDS_BASE,
            set_code=set_code,
            event_type=event_type,
        )
        try:
            async with session.head(url, timeout=5) as response:
                if response.status == 200:
                    available.append(event_type)
        except Exception:
            pass

    return set_code, available


async def _discover_available_sets(show_progress: bool = True) -> dict[str, list[str]]:
    """Probe S3 to discover which sets and event types are available."""
    import aiohttp

    sets_data: dict[str, list[str]] = {}

    if show_progress:
        console.print("[dim]Probing 17lands for available sets...[/]")

    timeout = aiohttp.ClientTimeout(total=120, connect=10)
    connector = aiohttp.TCPConnector(limit=10, force_close=True)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        tasks = [_probe_set_availability(session, set_code) for set_code in KNOWN_SETS]

        for coro in asyncio.as_completed(tasks):
            set_code, available = await coro
            if available:
                sets_data[set_code] = available
                if show_progress:
                    console.print(f"  [green]✓[/] {set_code}: {', '.join(available)}")

    return sets_data


def _fetch_available_sets(force_refresh: bool = False) -> dict[str, list[str]]:
    """Get available sets, using cache if valid.

    Returns a dict mapping set_code -> list of available event_types.
    """
    import json

    # Check cache first (valid for 7 days)
    if not force_refresh and SETS_CACHE_PATH.exists():
        try:
            age_days = (time.time() - SETS_CACHE_PATH.stat().st_mtime) / 86400
            if age_days < 7:
                with open(SETS_CACHE_PATH) as f:
                    data: dict[str, list[str]] = json.load(f)
                    console.print(f"[dim]Using cached set list ({len(data)} sets)[/]")
                    return data
        except Exception:
            pass

    # Probe S3 to discover available sets
    try:
        sets_data = asyncio.run(_discover_available_sets())

        if sets_data:
            # Cache the results
            SETS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(SETS_CACHE_PATH, "w") as f:
                json.dump(sets_data, f)
            console.print(f"[dim]Discovered {len(sets_data)} sets with data[/]")

        return sets_data

    except Exception as e:
        console.print(f"[yellow]Warning: Could not probe sets: {e}[/]")
        return {}


def get_available_sets(event_types: list[str] | None = None) -> list[str]:
    """Get list of all available sets from 17lands.

    Args:
        event_types: Filter to sets that have at least one of these event types.
                     If None, returns all sets.

    Returns list of set codes.
    """
    global _discovered_sets_cache

    if _discovered_sets_cache is None:
        _discovered_sets_cache = _fetch_available_sets()

    if not _discovered_sets_cache:
        # Fallback to known sets (download will skip 404s)
        console.print("[yellow]Using known set list (will skip unavailable)[/]")
        return KNOWN_SETS[:20]  # Return top 20 known sets

    if event_types:
        # Filter to sets that have at least one requested event type
        filtered = [
            set_code
            for set_code, available_events in _discovered_sets_cache.items()
            if any(et in available_events for et in event_types)
        ]
    else:
        filtered = list(_discovered_sets_cache.keys())

    return filtered


def get_set_event_types(set_code: str) -> list[str]:
    """Get available event types for a specific set."""
    global _discovered_sets_cache

    if _discovered_sets_cache is None:
        _discovered_sets_cache = _fetch_available_sets()

    return _discovered_sets_cache.get(set_code, EVENT_TYPES)

# Dictionary cache directory
DICT_CACHE_DIR = Path.home() / ".cache" / "mtg-toolkit" / "dictionaries"


def download_dictionary(url: str, filename: str) -> Path | None:
    """Download a dictionary file if not cached.

    Returns path to the cached file, or None if download failed.
    """
    import urllib.request

    DICT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = DICT_CACHE_DIR / filename

    # Return cached file if it exists and is less than 7 days old
    if cache_path.exists():
        age_days = (time.time() - cache_path.stat().st_mtime) / 86400
        if age_days < 7:
            return cache_path

    try:
        console.print(f"[dim]Downloading {filename}...[/]")
        urllib.request.urlretrieve(url, cache_path)
        return cache_path
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to download {filename}: {e}[/]")
        # Return stale cache if available
        if cache_path.exists():
            return cache_path
        return None


# Processing configuration
MAX_CONCURRENT_DOWNLOADS = 4  # Parallel download limit
MAX_CONCURRENT_PROCESSING = 4  # Parallel processing limit (uses threads)
PAIR_MIN_GAMES = 20  # Minimum games for pair tracking


# Format categories for segmentation
FORMAT_DRAFT = "draft"  # PremierDraft, TradDraft, QuickDraft
FORMAT_SEALED = "sealed"  # Sealed, TradSealed
FORMAT_OTHER = "other"  # PickTwoDraft, etc.

# Map event types to format categories
EVENT_TYPE_TO_FORMAT = {
    "PremierDraft": FORMAT_DRAFT,
    "TradDraft": FORMAT_DRAFT,
    "QuickDraft": FORMAT_DRAFT,
    "Sealed": FORMAT_SEALED,
    "TradSealed": FORMAT_SEALED,
    "PickTwoDraft": FORMAT_OTHER,
    "PickTwoTradDraft": FORMAT_OTHER,
}

# Bayesian averaging parameters
BAYESIAN_PRIOR_WR = 0.50  # Prior win rate (average)
BAYESIAN_CONFIDENCE = 200  # Higher = more regression for low-sample cards


@dataclass
class CardStats:
    """Aggregated statistics for a single card."""

    card_name: str
    set_code: str
    format: str = FORMAT_DRAFT  # draft, sealed, or other
    games_in_hand: int = 0
    games_in_hand_won: int = 0
    games_in_opening_hand: int = 0
    games_in_opening_hand_won: int = 0
    games_not_drawn: int = 0
    games_not_drawn_won: int = 0

    @property
    def gih_wr(self) -> float | None:
        """Raw GIH win rate (no Bayesian adjustment)."""
        if self.games_in_hand < 100:
            return None
        return self.games_in_hand_won / self.games_in_hand

    @property
    def gih_wr_adjusted(self) -> float | None:
        """Bayesian-adjusted GIH win rate (regresses small samples to prior)."""
        if self.games_in_hand < 50:
            return None
        return (self.games_in_hand_won + BAYESIAN_CONFIDENCE * BAYESIAN_PRIOR_WR) / (
            self.games_in_hand + BAYESIAN_CONFIDENCE
        )

    @property
    def oh_wr(self) -> float | None:
        if self.games_in_opening_hand < 50:
            return None
        return self.games_in_opening_hand_won / self.games_in_opening_hand

    @property
    def gnd_wr(self) -> float | None:
        if self.games_not_drawn < 100:
            return None
        return self.games_not_drawn_won / self.games_not_drawn

    @property
    def iwd(self) -> float | None:
        gih = self.gih_wr
        gnd = self.gnd_wr
        if gih is None or gnd is None:
            return None
        return gih - gnd

    @property
    def tier(self) -> str:
        gih = self.gih_wr
        if gih is None:
            return "?"
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
class SynergyPairStats:
    """Tracks how well two cards perform together."""

    card_a: str
    card_b: str
    set_code: str
    format: str = FORMAT_DRAFT  # draft, sealed, or other
    games_together: int = 0
    wins_together: int = 0

    @property
    def win_rate(self) -> float | None:
        if self.games_together < 50:
            return None
        return self.wins_together / self.games_together


@dataclass
class SetAggregator:
    """Aggregates card stats for a single set and format."""

    set_code: str
    format: str = FORMAT_DRAFT  # draft, sealed, or other
    cards: dict[str, CardStats] = field(default_factory=dict)
    pairs: dict[tuple[str, str], SynergyPairStats] = field(default_factory=dict)
    games_processed: int = 0
    track_pairs: bool = True


@dataclass
class DownloadResult:
    """Result from downloading a file."""

    set_code: str
    event_type: str
    data: bytes | None
    error: str | None = None


async def download_file_async(
    session: Any,  # aiohttp.ClientSession
    url: str,
    set_code: str,
    event_type: str,
    semaphore: asyncio.Semaphore,
) -> DownloadResult:
    """Download a single file asynchronously."""
    async with semaphore:
        try:
            async with session.head(url) as response:
                if response.status == 404:
                    return DownloadResult(set_code, event_type, None)

            async with session.get(url) as response:
                if response.status == 404:
                    return DownloadResult(set_code, event_type, None)
                response.raise_for_status()
                data = await response.read()
                return DownloadResult(set_code, event_type, data)

        except Exception as e:
            return DownloadResult(set_code, event_type, None, str(e))


async def download_all_files(
    set_list: list[str],
    progress: Progress,
    task_id: TaskID,
) -> dict[str, dict[str, bytes]]:
    """Download all files concurrently."""
    import aiohttp

    results: dict[str, dict[str, bytes]] = {s: {} for s in set_list}
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

    timeout = aiohttp.ClientTimeout(total=300, connect=30)
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_DOWNLOADS, force_close=True)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        tasks = []
        for set_code in set_list:
            for event_type in EVENT_TYPES:
                url = GAME_DATA_PATTERN.format(
                    base=SEVENTEEN_LANDS_BASE,
                    set_code=set_code,
                    event_type=event_type,
                )
                tasks.append(download_file_async(session, url, set_code, event_type, semaphore))

        for completed, coro in enumerate(asyncio.as_completed(tasks), start=1):
            result = await coro
            progress.update(task_id, completed=completed)

            if result.data is not None:
                results[result.set_code][result.event_type] = result.data
            elif result.error:
                console.print(f"[yellow]  {result.set_code}/{result.event_type}: {result.error}[/]")

    return results


def process_with_polars(
    data: bytes,
    set_code: str,
    progress: Progress | None,
    task_id: TaskID | None,
    track_pairs: bool = True,
) -> SetAggregator:
    """Process gzipped CSV game data using Polars for fast aggregation.

    Polars is 10-22x faster than pandas and uses lazy evaluation.
    """
    import gzip
    import tarfile

    def update_progress(description: str | None = None, **kwargs: Any) -> None:
        if progress and task_id is not None:
            if description:
                progress.update(task_id, description=description, **kwargs)
            else:
                progress.update(task_id, **kwargs)

    aggregator = SetAggregator(set_code=set_code, track_pairs=track_pairs)

    update_progress(description=f"{set_code}: Decompressing...")

    # Try tar.gz first (some files are tar archives), fall back to plain gzip
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            members = tar.getmembers()
            if members:
                csv_file = tar.extractfile(members[0])
                csv_data = csv_file.read() if csv_file else gzip.decompress(data)
            else:
                csv_data = gzip.decompress(data)
    except tarfile.ReadError:
        # Not a tar archive, just gzip-compressed CSV
        csv_data = gzip.decompress(data)

    update_progress(description=f"{set_code}: Reading CSV...")

    # Read CSV with Polars (very fast, parallel parsing)
    df = pl.read_csv(io.BytesIO(csv_data), infer_schema_length=1000)

    total_games = len(df)
    aggregator.games_processed = total_games

    # Early exit if no data (empty CSV with just headers)
    if total_games == 0:
        update_progress(description=f"{set_code}: No data (empty file)")
        return aggregator

    # Get column names
    all_cols = df.columns
    deck_cols = [c for c in all_cols if c.startswith("deck_")]
    drawn_cols = {c for c in all_cols if c.startswith("drawn_")}
    opening_cols = {c for c in all_cols if c.startswith("opening_hand_")}

    n_cards = len(deck_cols)
    update_progress(description=f"{set_code}: {total_games:,} games, {n_cards} cards...")

    # Build aggregation expressions for all cards at once
    # Cast columns to ensure numeric types (CSV may infer as string)
    agg_exprs = []
    card_info = []  # Track card name and column mappings

    # Helper to safely cast column to Int64 (handles string columns from CSV)
    def numeric_col(col_name: str) -> pl.Expr:
        return pl.col(col_name).cast(pl.Int64, strict=False).fill_null(0)

    for deck_col in deck_cols:
        card_name = deck_col[5:].replace("_", " ")
        drawn_col = f"drawn_{deck_col[5:]}"
        opening_col = f"opening_hand_{deck_col[5:]}"

        has_drawn = drawn_col in drawn_cols
        has_opening = opening_col in opening_cols

        if has_drawn and has_opening:
            card_info.append((card_name, deck_col, drawn_col, opening_col))

            # Games in hand (drawn > 0)
            agg_exprs.append((numeric_col(drawn_col) > 0).sum().alias(f"{card_name}__gih"))
            # Games in hand won
            agg_exprs.append(
                ((numeric_col(drawn_col) > 0) & pl.col("won"))
                .sum()
                .alias(f"{card_name}__gih_won")
            )
            # Games not drawn (in deck but not drawn)
            agg_exprs.append(
                ((numeric_col(deck_col) > 0) & (numeric_col(drawn_col) == 0))
                .sum()
                .alias(f"{card_name}__gnd")
            )
            # Games not drawn won
            agg_exprs.append(
                (
                    (numeric_col(deck_col) > 0)
                    & (numeric_col(drawn_col) == 0)
                    & pl.col("won")
                )
                .sum()
                .alias(f"{card_name}__gnd_won")
            )
            # Opening hand
            agg_exprs.append((numeric_col(opening_col) > 0).sum().alias(f"{card_name}__oh"))
            # Opening hand won
            agg_exprs.append(
                ((numeric_col(opening_col) > 0) & pl.col("won"))
                .sum()
                .alias(f"{card_name}__oh_won")
            )

    update_progress(description=f"{set_code}: Computing card stats...")

    # Run single aggregation for all cards
    result = df.select(agg_exprs)
    row = result.row(0)

    # Parse results into CardStats
    for i, (card_name, _, _, _) in enumerate(card_info):
        base_idx = i * 6
        stats = CardStats(
            card_name=card_name,
            set_code=set_code,
            games_in_hand=row[base_idx] or 0,
            games_in_hand_won=row[base_idx + 1] or 0,
            games_not_drawn=row[base_idx + 2] or 0,
            games_not_drawn_won=row[base_idx + 3] or 0,
            games_in_opening_hand=row[base_idx + 4] or 0,
            games_in_opening_hand_won=row[base_idx + 5] or 0,
        )
        if stats.games_in_hand >= 100:
            aggregator.cards[card_name] = stats

    update_progress(description=f"{set_code}: {len(aggregator.cards)} cards, computing pairs...")

    # Compute pair stats using matrix multiplication (much faster than self-join)
    if track_pairs and len(deck_cols) > 1:
        update_progress(description=f"{set_code}: Computing pairs (matrix)...")

        try:
            import numpy as np

            # Build int matrix: (games x cards) where 1 = card in deck, 0 = not
            # Cast to Int64 to handle CSV columns inferred as strings, then to int8 for matmul
            deck_matrix = (
                df.select([pl.col(c).cast(pl.Int64, strict=False).fill_null(0) for c in deck_cols])
                .to_numpy()
                > 0
            ).astype(np.int8)  # Shape: (N_games, N_cards) - int8 for efficient matmul
            won_array = df.select(numeric_col("won")).to_series().to_numpy().astype(np.int8)

            # Matrix multiplication gives co-occurrence counts
            # M.T @ M gives (N_cards x N_cards) matrix where [i,j] = count of games with both cards
            co_occur = deck_matrix.T @ deck_matrix  # (N_cards x N_cards)

            # For wins: weight each game by won status
            wins_matrix = (deck_matrix * won_array[:, np.newaxis]).T @ deck_matrix

            # Extract upper triangle (avoid double counting pairs)
            n_cards = len(deck_cols)
            for i in range(n_cards):
                for j in range(i + 1, n_cards):
                    games = int(co_occur[i, j])
                    if games >= PAIR_MIN_GAMES:
                        wins = int(wins_matrix[i, j])
                        card_a = deck_cols[i][5:].replace("_", " ")
                        card_b = deck_cols[j][5:].replace("_", " ")

                        if card_a > card_b:
                            card_a, card_b = card_b, card_a

                        aggregator.pairs[(card_a, card_b)] = SynergyPairStats(
                            card_a=card_a,
                            card_b=card_b,
                            set_code=set_code,
                            games_together=games,
                            wins_together=wins,
                        )

        except Exception as e:
            console.print(f"[yellow]  Pair analysis failed: {e}[/]")

    update_progress(
        description=f"{set_code}: Complete ({total_games:,} games, {len(aggregator.pairs):,} pairs)"
    )

    return aggregator


def create_database(db_path: Path) -> None:
    """Create the limited_stats database schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS card_stats (
            id INTEGER PRIMARY KEY,
            card_name TEXT NOT NULL,
            set_code TEXT NOT NULL,
            format TEXT NOT NULL DEFAULT 'draft',
            games_in_hand INTEGER DEFAULT 0,
            games_in_opening_hand INTEGER DEFAULT 0,
            games_not_drawn INTEGER DEFAULT 0,
            gih_wr REAL,
            gih_wr_adjusted REAL,
            oh_wr REAL,
            gnd_wr REAL,
            iwd REAL,
            ata REAL,
            tier TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(card_name, set_code, format)
        );

        CREATE INDEX IF NOT EXISTS idx_card_stats_set ON card_stats(set_code);
        CREATE INDEX IF NOT EXISTS idx_card_stats_name ON card_stats(card_name);
        CREATE INDEX IF NOT EXISTS idx_card_stats_format ON card_stats(format);
        CREATE INDEX IF NOT EXISTS idx_card_stats_set_format ON card_stats(set_code, format);
        CREATE INDEX IF NOT EXISTS idx_card_stats_tier ON card_stats(set_code, format, tier);
        CREATE INDEX IF NOT EXISTS idx_card_stats_gih ON card_stats(set_code, format, gih_wr DESC);

        CREATE TABLE IF NOT EXISTS synergy_pairs (
            id INTEGER PRIMARY KEY,
            set_code TEXT NOT NULL,
            format TEXT NOT NULL DEFAULT 'draft',
            card_a TEXT NOT NULL,
            card_b TEXT NOT NULL,
            co_occurrence_count INTEGER,
            win_rate_together REAL,
            synergy_lift REAL,
            UNIQUE(set_code, format, card_a, card_b)
        );

        CREATE INDEX IF NOT EXISTS idx_synergy_set ON synergy_pairs(set_code);
        CREATE INDEX IF NOT EXISTS idx_synergy_format ON synergy_pairs(format);
        CREATE INDEX IF NOT EXISTS idx_synergy_set_format ON synergy_pairs(set_code, format);
        CREATE INDEX IF NOT EXISTS idx_synergy_card ON synergy_pairs(card_a);

        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS abilities (
            id INTEGER PRIMARY KEY,
            text TEXT NOT NULL,
            category TEXT DEFAULT 'keyword'
        );

        CREATE INDEX IF NOT EXISTS idx_abilities_category ON abilities(category);

        CREATE TABLE IF NOT EXISTS card_themes (
            card_name TEXT NOT NULL,
            theme TEXT NOT NULL,
            PRIMARY KEY (card_name, theme)
        );

        CREATE INDEX IF NOT EXISTS idx_card_themes_theme ON card_themes(theme);
    """)

    conn.commit()
    conn.close()


def save_stats_batch(db_path: Path, aggregator: SetAggregator) -> int:
    """Save aggregated stats to database using batch inserts."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Prepare batch data
    batch = []
    for stats in aggregator.cards.values():
        if stats.games_in_hand < 100:
            continue

        batch.append(
            (
                stats.card_name,
                stats.set_code,
                aggregator.format,  # Use aggregator's format
                stats.games_in_hand,
                stats.games_in_opening_hand,
                stats.games_not_drawn,
                stats.gih_wr,
                stats.gih_wr_adjusted,  # Bayesian adjusted
                stats.oh_wr,
                stats.gnd_wr,
                stats.iwd,
                None,  # ata
                stats.tier,
            )
        )

    if batch:
        cursor.executemany(
            """
            INSERT OR REPLACE INTO card_stats
            (card_name, set_code, format, games_in_hand, games_in_opening_hand, games_not_drawn,
             gih_wr, gih_wr_adjusted, oh_wr, gnd_wr, iwd, ata, tier, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            batch,
        )

    conn.commit()
    conn.close()
    return len(batch)


def save_synergy_pairs_batch(db_path: Path, aggregator: SetAggregator, min_games: int = 50) -> int:
    """Save synergy pair stats using batch inserts."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Calculate average set win rate
    total_games = 0
    total_wins = 0
    for stats in aggregator.cards.values():
        if stats.games_in_hand >= 100 and stats.gih_wr is not None:
            total_games += stats.games_in_hand
            total_wins += stats.games_in_hand_won

    avg_wr = total_wins / total_games if total_games > 0 else 0.50

    # Prepare batch data
    batch = []
    for (card_a, card_b), pair in aggregator.pairs.items():
        if pair.games_together < min_games:
            continue

        win_rate = pair.win_rate
        if win_rate is None:
            continue

        synergy_lift = win_rate - avg_wr

        batch.append(
            (
                aggregator.set_code,
                aggregator.format,  # Include format
                card_a,
                card_b,
                pair.games_together,
                win_rate,
                synergy_lift,
            )
        )

    if batch:
        cursor.executemany(
            """
            INSERT OR REPLACE INTO synergy_pairs
            (set_code, format, card_a, card_b, co_occurrence_count, win_rate_together, synergy_lift)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            batch,
        )

    conn.commit()
    conn.close()
    return len(batch)


def save_abilities(db_path: Path) -> int:
    """Load abilities.csv into database (downloads if needed)."""
    import re

    # Try to download from 17lands S3
    abilities_csv = download_dictionary(ABILITIES_URL, "abilities.csv")
    if not abilities_csv:
        console.print("[yellow]Warning: abilities.csv not available, skipping[/]")
        return 0

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    def categorize(text: str, ability_id: int) -> str:
        if ability_id in {1, 2, 3, 6, 7, 8, 9, 10, 12, 13, 14, 15, 104}:
            return "keyword"
        if re.search(r"\{[^}]+\}.*:", text):
            return "activated"
        if re.search(r"^When(ever)?|^At the beginning", text, re.IGNORECASE):
            return "triggered"
        if len(text) < 20 and not any(c in text for c in "{}()"):
            return "keyword"
        return "complex"

    saved = 0
    with open(abilities_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ability_id = int(row["id"])
            text = row["text"]
            category = categorize(text, ability_id)
            cursor.execute(
                "INSERT OR REPLACE INTO abilities (id, text, category) VALUES (?, ?, ?)",
                (ability_id, text, category),
            )
            saved += 1

    conn.commit()
    conn.close()
    return saved


def show_top_synergies(aggregator: SetAggregator, n: int = 10) -> None:
    """Display top synergy pairs by win rate lift."""
    total_games = 0
    total_wins = 0
    for stats in aggregator.cards.values():
        if stats.games_in_hand >= 100 and stats.gih_wr is not None:
            total_games += stats.games_in_hand
            total_wins += stats.games_in_hand_won

    avg_wr = total_wins / total_games if total_games > 0 else 0.50

    valid_pairs = []
    for (card_a, card_b), pair in aggregator.pairs.items():
        if pair.games_together >= 100 and pair.win_rate is not None:
            lift = pair.win_rate - avg_wr
            if lift > 0.02:
                valid_pairs.append((card_a, card_b, pair, lift))

    valid_pairs.sort(key=lambda x: x[3], reverse=True)

    if not valid_pairs:
        return

    table = Table(title=f"Top {n} Synergy Pairs in {aggregator.set_code}")
    table.add_column("Card A", style="cyan")
    table.add_column("Card B", style="cyan")
    table.add_column("Together WR", justify="right")
    table.add_column("Lift", justify="right", style="green")
    table.add_column("Games", justify="right", style="dim")

    for card_a, card_b, pair, lift in valid_pairs[:n]:
        table.add_row(
            card_a[:20],
            card_b[:20],
            f"{pair.win_rate:.1%}" if pair.win_rate else "N/A",
            f"+{lift:.1%}",
            f"{pair.games_together:,}",
        )

    console.print(table)


def show_top_cards(aggregator: SetAggregator, n: int = 10) -> None:
    """Display top cards by GIH WR."""
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


def merge_aggregators(target: SetAggregator, source: SetAggregator) -> None:
    """Merge source aggregator into target."""
    for card_name, stats in source.cards.items():
        if card_name not in target.cards:
            target.cards[card_name] = stats
        else:
            existing = target.cards[card_name]
            existing.games_in_hand += stats.games_in_hand
            existing.games_in_hand_won += stats.games_in_hand_won
            existing.games_in_opening_hand += stats.games_in_opening_hand
            existing.games_in_opening_hand_won += stats.games_in_opening_hand_won
            existing.games_not_drawn += stats.games_not_drawn
            existing.games_not_drawn_won += stats.games_not_drawn_won

    for pair_key, pair in source.pairs.items():
        if pair_key not in target.pairs:
            target.pairs[pair_key] = pair
        else:
            existing_pair = target.pairs[pair_key]
            existing_pair.games_together += pair.games_together
            existing_pair.wins_together += pair.wins_together

    target.games_processed += source.games_processed


async def download_single_set(
    set_code: str,
    session: aiohttp.ClientSession,
    progress: Progress | None,
    task_id: TaskID | None,
    event_types: list[str] | None = None,
) -> dict[str, bytes]:
    """Download files for a single set."""
    results: dict[str, bytes] = {}
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    event_types = event_types or EVENT_TYPES

    tasks = []
    for event_type in event_types:
        url = GAME_DATA_PATTERN.format(
            base=SEVENTEEN_LANDS_BASE,
            set_code=set_code,
            event_type=event_type,
        )
        tasks.append(download_file_async(session, url, set_code, event_type, semaphore))

    for coro in asyncio.as_completed(tasks):
        result = await coro
        if progress and task_id is not None:
            progress.update(task_id, advance=1)
        if result.data is not None:
            results[result.event_type] = result.data
        elif result.error:
            console.print(f"[yellow]  {result.set_code}/{result.event_type}: {result.error}[/]")

    return results


def process_single_set(
    set_code: str,
    db_path: Path,
    downloaded: dict[str, bytes],
    skip_pairs: bool,
    show_stats: bool,
    progress: Progress | None,
    task_id: TaskID | None,
) -> tuple[int, int, int]:
    """Process a single set's downloaded data, returning (cards, games, pairs) counts.

    Data is segmented by format category (draft/sealed) for separate storage.
    """
    track_pairs = not skip_pairs

    # Group downloaded data by format category
    format_data: dict[str, list[tuple[str, bytes]]] = {
        FORMAT_DRAFT: [],
        FORMAT_SEALED: [],
        FORMAT_OTHER: [],
    }

    for event_type, data in downloaded.items():
        format_cat = EVENT_TYPE_TO_FORMAT.get(event_type, FORMAT_OTHER)
        format_data[format_cat].append((event_type, data))

    total_cards = 0
    total_games = 0
    total_pairs = 0

    # Process each format category separately
    for format_cat, events in format_data.items():
        if not events:
            continue

        # Skip "other" formats (PickTwo, etc.) - they're noise
        if format_cat == FORMAT_OTHER:
            continue

        aggregators: list[SetAggregator] = []
        for _event_type, data in events:
            aggregator = process_with_polars(
                data, set_code, progress, task_id, track_pairs=track_pairs
            )
            aggregator.format = format_cat  # Set format category
            aggregators.append(aggregator)
            if progress and task_id is not None:
                progress.update(task_id, advance=1)

        if not aggregators:
            continue

        # Merge all event types within this format category
        if progress and task_id is not None:
            progress.update(task_id, description=f"{set_code}: Merging {format_cat}...")
        format_aggregator = aggregators[0]
        for other in aggregators[1:]:
            merge_aggregators(format_aggregator, other)

        # Save to database
        if format_aggregator.cards:
            if progress and task_id is not None:
                progress.update(task_id, description=f"{set_code}: Saving {format_cat}...")
            cards_saved = save_stats_batch(db_path, format_aggregator)
            total_cards += cards_saved

            if not skip_pairs:
                pairs_saved = save_synergy_pairs_batch(db_path, format_aggregator, min_games=50)
                total_pairs += pairs_saved

            total_games += format_aggregator.games_processed

            if show_stats:
                console.print(f"  [{format_cat}] {cards_saved} cards, {format_aggregator.games_processed:,} games")

    if progress and task_id is not None:
        progress.update(task_id, advance=1)

    return total_cards, total_games, total_pairs


@app.command()
def download(
    sets: Annotated[
        str | None,
        typer.Option("--sets", "-s", help="Comma-separated set codes (e.g., BLB,OTJ,MKM)"),
    ] = None,
    output_dir: Annotated[
        Path, typer.Option("--output-dir", "-o", help="Output directory for database")
    ] = Path("resources"),
    show_stats: Annotated[
        bool, typer.Option("--show-stats", help="Show top cards after processing each set")
    ] = True,
    skip_pairs: Annotated[
        bool, typer.Option("--skip-pairs", help="Skip synergy pair calculation (faster)")
    ] = False,
    all_sets: Annotated[
        bool, typer.Option("--all", "-a", help="Download ALL available sets from 17lands")
    ] = False,
    all_events: Annotated[
        bool, typer.Option("--all-events", help="Download all event types, not just Premier/Trad")
    ] = False,
    list_sets: Annotated[
        bool, typer.Option("--list", "-l", help="List available sets and exit")
    ] = False,
    refresh: Annotated[
        bool, typer.Option("--refresh", help="Refresh the cached set list from 17lands")
    ] = False,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Quiet mode - minimal output")
    ] = False,
) -> None:
    """Download and process 17lands data for Limited card ratings."""
    import aiohttp

    global _discovered_sets_cache

    # Handle --refresh flag
    if refresh:
        console.print("[bold]Refreshing set list from 17lands...[/]")
        if SETS_CACHE_PATH.exists():
            SETS_CACHE_PATH.unlink()
        _discovered_sets_cache = None

    # Handle --list flag
    if list_sets:
        available = get_available_sets()
        console.print(f"\n[bold]Available sets from 17lands ({len(available)}):[/]\n")
        for set_code in available:
            event_types = get_set_event_types(set_code)
            console.print(f"  [cyan]{set_code:20}[/] {', '.join(event_types)}")
        return

    start_time = time.time()

    # Helper for conditional printing
    def log(msg: str) -> None:
        if not quiet:
            console.print(msg)

    if sets:
        set_list = [s.strip() for s in sets.split(",")]  # Keep original case for special sets
    elif all_sets:
        set_list = get_available_sets(EVENT_TYPES)
        log(f"[dim]Downloading ALL {len(set_list)} available sets[/]")
    else:
        # Default: get all available sets with Premier/Trad data
        set_list = get_available_sets(EVENT_TYPES)[:15]  # Top 15 by default
        log(f"[dim]No sets specified, using top {len(set_list)} sets[/]")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "limited_stats.sqlite"

    log(f"\n[bold]Creating database at {db_path}[/]")
    create_database(db_path)

    abilities_count = save_abilities(db_path)
    if abilities_count > 0:
        log(f"[dim]Loaded {abilities_count:,} abilities into dictionary[/]")

    total_cards = 0
    total_games = 0
    total_pairs = 0

    # Process each set one at a time (serial execution for memory efficiency)
    for i, set_code in enumerate(set_list, 1):
        # Get event types for this set
        set_event_types = get_set_event_types(set_code) if all_events else EVENT_TYPES

        log(f"\n[bold cyan]({i}/{len(set_list)}) {set_code}[/] [{', '.join(set_event_types)}]")

        # Steps per set: download (N files) + process (N files) + save (1)
        steps_per_set = len(set_event_types) * 2 + 1

        # Use nullcontext in quiet mode to skip progress bars
        progress_ctx = (
            nullcontext()
            if quiet
            else Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
                console=console,
            )
        )

        with progress_ctx as progress:
            # Create a task_id only when not in quiet mode
            task_id: TaskID | None = None
            if not quiet and progress is not None:
                task_id = progress.add_task(f"{set_code}: Downloading...", total=steps_per_set)

            # Download phase - capture loop vars via default args
            async def download_set(
                sc: str = set_code,
                prog: Progress | None = progress,
                tid: TaskID | None = task_id,
                evts: list[str] = set_event_types,
            ) -> dict[str, bytes]:
                timeout = aiohttp.ClientTimeout(total=300, connect=30)
                connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_DOWNLOADS, force_close=True)
                async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                    return await download_single_set(sc, session, prog, tid, evts)

            downloaded = asyncio.run(download_set())

            if not downloaded:
                if quiet:
                    console.print(f"{set_code}: [yellow]No data[/]")
                else:
                    console.print("[yellow]  No data available[/]")
                continue

            # Process phase
            cards, games, pairs = process_single_set(
                set_code, db_path, downloaded, skip_pairs, show_stats, progress, task_id
            )

            if progress and task_id is not None:
                progress.update(
                    task_id,
                    description=f"{set_code}: [green]Done![/] {cards} cards, {games:,} games",
                )

        total_cards += cards
        total_games += games
        total_pairs += pairs

        if quiet:
            pairs_str = f", {pairs:,} pairs" if not skip_pairs else ""
            console.print(f"{set_code}: [green]✓[/] {cards} cards, {games:,} games{pairs_str}")
        else:
            console.print(
                f"  [green]✓[/] {cards} cards from {games:,} games"
                + (f", {pairs:,} pairs" if not skip_pairs else "")
            )

    elapsed = time.time() - start_time
    console.print(f"\n[bold green]Complete in {elapsed:.1f}s![/]")
    console.print(f"  Total cards: {total_cards:,}")
    console.print(f"  Total synergy pairs: {total_pairs:,}")
    console.print(f"  Total games: {total_games:,}")
    console.print(f"  Database: {db_path}")

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
