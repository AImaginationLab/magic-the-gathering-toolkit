"""Limited format card statistics from 17lands data."""

from __future__ import annotations

import gzip
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def _get_cache_dir() -> Path:
    """Get the cache directory for decompressed DB."""
    cache = Path.home() / ".cache" / "mtg-toolkit"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def _find_limited_stats_db() -> Path | None:
    """Find the limited stats database, decompressing if needed.

    Search order:
    1. Cache directory (already decompressed)
    2. Package resources (uncompressed)
    3. Package resources (compressed .gz) -> decompress to cache
    4. Repo resources (development)
    """
    cache_dir = _get_cache_dir()
    cached_db = cache_dir / "limited_stats.sqlite"

    # 1. Check cache first (fastest)
    if cached_db.exists():
        return cached_db

    # 2. Check package resources (uncompressed)
    pkg_resources = Path(__file__).parent / "data"
    pkg_db = pkg_resources / "limited_stats.sqlite"
    if pkg_db.exists():
        return pkg_db

    # 3. Check for compressed version -> decompress
    pkg_gz = pkg_resources / "limited_stats.sqlite.gz"
    if pkg_gz.exists():
        with gzip.open(pkg_gz, "rb") as f_in, open(cached_db, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        return cached_db

    # 4. Development: repo resources
    repo_db = Path(__file__).parents[6] / "resources" / "limited_stats.sqlite"
    if repo_db.exists():
        return repo_db

    return None


@dataclass
class LimitedCardStats:
    """Card statistics from 17lands Limited data."""

    card_name: str
    set_code: str
    games_in_hand: int
    gih_wr: float | None  # Games in Hand Win Rate (0.0-1.0)
    oh_wr: float | None  # Opening Hand Win Rate
    iwd: float | None  # Improvement When Drawn
    tier: str  # S/A/B/C/D/F


class LimitedStatsDB:
    """Query interface for limited_stats.sqlite database."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        """Initialize with database path.

        Args:
            db_path: Path to limited_stats.sqlite. If None, auto-discovers location.
        """
        if db_path is None:
            found = _find_limited_stats_db()
            self._db_path = found if found else Path("limited_stats.sqlite")
        else:
            self._db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None
        self._cache: dict[str, LimitedCardStats] = {}

    @property
    def is_available(self) -> bool:
        """Check if the database exists."""
        return self._db_path.exists()

    def connect(self) -> None:
        """Connect to the database."""
        if not self.is_available:
            return
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def get_card_stats(
        self, card_name: str, set_code: str | None = None
    ) -> LimitedCardStats | None:
        """Get limited stats for a card.

        Args:
            card_name: Card name to look up
            set_code: Optional set code to filter by. If None, returns most recent.

        Returns:
            LimitedCardStats or None if not found
        """
        if not self._conn:
            self.connect()
        if not self._conn:
            return None

        # Check cache
        cache_key = f"{card_name}:{set_code or 'any'}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        cursor = self._conn.cursor()

        if set_code:
            cursor.execute(
                """
                SELECT card_name, set_code, games_in_hand, gih_wr, oh_wr, iwd, tier
                FROM card_stats
                WHERE card_name = ? AND set_code = ?
                """,
                (card_name, set_code.upper()),
            )
        else:
            # Get most recent set data (by most games played)
            cursor.execute(
                """
                SELECT card_name, set_code, games_in_hand, gih_wr, oh_wr, iwd, tier
                FROM card_stats
                WHERE card_name = ?
                ORDER BY games_in_hand DESC
                LIMIT 1
                """,
                (card_name,),
            )

        row = cursor.fetchone()
        if not row:
            return None

        stats = LimitedCardStats(
            card_name=row["card_name"],
            set_code=row["set_code"],
            games_in_hand=row["games_in_hand"],
            gih_wr=row["gih_wr"],
            oh_wr=row["oh_wr"],
            iwd=row["iwd"],
            tier=row["tier"],
        )

        self._cache[cache_key] = stats
        return stats

    def get_tier(self, card_name: str, set_code: str | None = None) -> str | None:
        """Get just the tier for a card (S/A/B/C/D/F)."""
        stats = self.get_card_stats(card_name, set_code)
        return stats.tier if stats else None

    def get_gih_wr(self, card_name: str, set_code: str | None = None) -> float | None:
        """Get Games in Hand Win Rate for a card."""
        stats = self.get_card_stats(card_name, set_code)
        return stats.gih_wr if stats else None

    def get_limited_score(self, card_name: str, set_code: str | None = None) -> float:
        """Get a normalized score (0-1) based on GIH WR.

        Returns 0.5 if no data available (neutral).
        """
        stats = self.get_card_stats(card_name, set_code)
        if not stats or stats.gih_wr is None:
            return 0.5  # Neutral if no data

        # Normalize GIH WR to 0-1 scale
        # 17lands users average ~56% WR, so we center around that
        # 48% = 0.0, 56% = 0.5, 64% = 1.0
        gih = stats.gih_wr
        normalized = (gih - 0.48) / 0.16  # Maps 48%-64% to 0-1
        return max(0.0, min(1.0, normalized))

    def get_set_codes(self) -> list[str]:
        """Get list of available set codes."""
        if not self._conn:
            self.connect()
        if not self._conn:
            return []

        cursor = self._conn.cursor()
        cursor.execute("SELECT DISTINCT set_code FROM card_stats ORDER BY set_code")
        return [row[0] for row in cursor.fetchall()]

    def get_top_cards(
        self,
        set_code: str | None = None,
        tier: str | None = None,
        limit: int = 20,
    ) -> list[LimitedCardStats]:
        """Get top cards by GIH WR.

        Args:
            set_code: Filter by set
            tier: Filter by tier (S/A/B/C/D/F)
            limit: Max cards to return

        Returns:
            List of LimitedCardStats sorted by GIH WR descending
        """
        if not self._conn:
            self.connect()
        if not self._conn:
            return []

        cursor = self._conn.cursor()

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

        return [
            LimitedCardStats(
                card_name=row["card_name"],
                set_code=row["set_code"],
                games_in_hand=row["games_in_hand"],
                gih_wr=row["gih_wr"],
                oh_wr=row["oh_wr"],
                iwd=row["iwd"],
                tier=row["tier"],
            )
            for row in cursor.fetchall()
        ]


# Global singleton
_limited_stats_db: LimitedStatsDB | None = None


def get_limited_stats_db() -> LimitedStatsDB:
    """Get or create the global limited stats database instance."""
    global _limited_stats_db
    if _limited_stats_db is None:
        _limited_stats_db = LimitedStatsDB()
    return _limited_stats_db
