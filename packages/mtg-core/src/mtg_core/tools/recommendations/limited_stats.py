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


# Format categories matching download_17lands.py
FORMAT_DRAFT = "draft"
FORMAT_SEALED = "sealed"

# Default weights for combining Draft/Sealed scores
DEFAULT_DRAFT_WEIGHT = 0.7
DEFAULT_SEALED_WEIGHT = 0.3


@dataclass
class LimitedCardStats:
    """Card statistics from 17lands Limited data."""

    card_name: str
    set_code: str
    format: str  # draft, sealed
    games_in_hand: int
    gih_wr: float | None  # Games in Hand Win Rate (0.0-1.0)
    gih_wr_adjusted: float | None  # Bayesian-adjusted GIH WR
    oh_wr: float | None  # Opening Hand Win Rate
    iwd: float | None  # Improvement When Drawn
    tier: str  # S/A/B/C/D/F


@dataclass
class SynergyPair:
    """Card pair synergy data from 17Lands."""

    card_a: str
    card_b: str
    set_code: str
    format: str  # draft, sealed
    co_occurrence_count: int
    win_rate_together: float | None
    synergy_lift: float | None  # How much better than expected


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
        self,
        card_name: str,
        set_code: str | None = None,
        format: str | None = None,
    ) -> LimitedCardStats | None:
        """Get limited stats for a card.

        Args:
            card_name: Card name to look up
            set_code: Optional set code to filter by. If None, returns most recent.
            format: Optional format (draft/sealed). If None, prefers draft.

        Returns:
            LimitedCardStats or None if not found
        """
        if not self._conn:
            self.connect()
        if not self._conn:
            return None

        # Check cache
        cache_key = f"{card_name}:{set_code or 'any'}:{format or 'any'}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        cursor = self._conn.cursor()

        # Build query based on parameters
        base_cols = "card_name, set_code, format, games_in_hand, gih_wr, gih_wr_adjusted, oh_wr, iwd, tier"

        if set_code and format:
            cursor.execute(
                f"""
                SELECT {base_cols}
                FROM card_stats
                WHERE card_name = ? AND set_code = ? AND format = ?
                """,
                (card_name, set_code.upper(), format),
            )
        elif set_code:
            # Prefer draft format if available
            cursor.execute(
                f"""
                SELECT {base_cols}
                FROM card_stats
                WHERE card_name = ? AND set_code = ?
                ORDER BY CASE format WHEN 'draft' THEN 0 ELSE 1 END, games_in_hand DESC
                LIMIT 1
                """,
                (card_name, set_code.upper()),
            )
        elif format:
            # Get best data for this format
            cursor.execute(
                f"""
                SELECT {base_cols}
                FROM card_stats
                WHERE card_name = ? AND format = ?
                ORDER BY games_in_hand DESC
                LIMIT 1
                """,
                (card_name, format),
            )
        else:
            # Get best data overall (prefer draft, most games)
            cursor.execute(
                f"""
                SELECT {base_cols}
                FROM card_stats
                WHERE card_name = ?
                ORDER BY CASE format WHEN 'draft' THEN 0 ELSE 1 END, games_in_hand DESC
                LIMIT 1
                """,
                (card_name,),
            )

        row = cursor.fetchone()
        if not row:
            return None

        row_dict = dict(row)
        stats = LimitedCardStats(
            card_name=row_dict["card_name"],
            set_code=row_dict["set_code"],
            format=row_dict.get("format", FORMAT_DRAFT),
            games_in_hand=row_dict["games_in_hand"],
            gih_wr=row_dict["gih_wr"],
            gih_wr_adjusted=row_dict.get("gih_wr_adjusted"),
            oh_wr=row_dict["oh_wr"],
            iwd=row_dict["iwd"],
            tier=row_dict["tier"],
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

    def get_limited_score(
        self,
        card_name: str,
        set_code: str | None = None,
        format: str | None = None,
        use_adjusted: bool = True,
    ) -> float:
        """Get a normalized score (0-1) based on GIH WR.

        Args:
            card_name: Card name to look up
            set_code: Optional set code
            format: Optional format (draft/sealed)
            use_adjusted: Use Bayesian-adjusted WR if available

        Returns 0.5 if no data available (neutral).
        """
        stats = self.get_card_stats(card_name, set_code, format)
        if not stats:
            return 0.5  # Neutral if no data

        # Prefer adjusted WR if available and requested
        gih = None
        if use_adjusted and stats.gih_wr_adjusted is not None:
            gih = stats.gih_wr_adjusted
        elif stats.gih_wr is not None:
            gih = stats.gih_wr

        if gih is None:
            return 0.5

        # Normalize GIH WR to 0-1 scale
        # 17lands users average ~56% WR, so we center around that
        # 48% = 0.0, 56% = 0.5, 64% = 1.0
        normalized = (gih - 0.48) / 0.16  # Maps 48%-64% to 0-1
        return max(0.0, min(1.0, normalized))

    def get_weighted_score(
        self,
        card_name: str,
        set_code: str | None = None,
        draft_weight: float = DEFAULT_DRAFT_WEIGHT,
        sealed_weight: float = DEFAULT_SEALED_WEIGHT,
        use_adjusted: bool = True,
    ) -> float:
        """Get weighted score combining Draft and Sealed performance.

        This is the recommended method for recommendations - it balances
        synergy potential (Draft) with standalone power (Sealed).

        Args:
            card_name: Card name to look up
            set_code: Optional set code
            draft_weight: Weight for Draft data (default 0.7)
            sealed_weight: Weight for Sealed data (default 0.3)
            use_adjusted: Use Bayesian-adjusted WR if available

        Returns:
            Weighted score (0-1), 0.5 if no data
        """
        draft_score = self.get_limited_score(card_name, set_code, FORMAT_DRAFT, use_adjusted)
        sealed_score = self.get_limited_score(card_name, set_code, FORMAT_SEALED, use_adjusted)

        # Check what data we actually have
        draft_stats = self.get_card_stats(card_name, set_code, FORMAT_DRAFT)
        sealed_stats = self.get_card_stats(card_name, set_code, FORMAT_SEALED)

        has_draft = draft_stats is not None and draft_stats.gih_wr is not None
        has_sealed = sealed_stats is not None and sealed_stats.gih_wr is not None

        if has_draft and has_sealed:
            # Both available - use weighted average
            total_weight = draft_weight + sealed_weight
            return (draft_score * draft_weight + sealed_score * sealed_weight) / total_weight
        elif has_draft:
            # Only draft data
            return draft_score
        elif has_sealed:
            # Only sealed data
            return sealed_score
        else:
            # No data
            return 0.5

    def is_bomb(
        self,
        card_name: str,
        set_code: str | None = None,
        threshold: float = 0.03,
    ) -> bool:
        """Check if a card is a 'bomb' (better in Sealed than Draft).

        Bombs are cards that win games on their own without needing synergy.

        Args:
            card_name: Card name
            set_code: Optional set code
            threshold: Minimum Sealed - Draft WR difference to qualify

        Returns:
            True if card performs significantly better in Sealed
        """
        draft_stats = self.get_card_stats(card_name, set_code, FORMAT_DRAFT)
        sealed_stats = self.get_card_stats(card_name, set_code, FORMAT_SEALED)

        if not draft_stats or not sealed_stats:
            return False
        if draft_stats.gih_wr is None or sealed_stats.gih_wr is None:
            return False

        return (sealed_stats.gih_wr - draft_stats.gih_wr) >= threshold

    def is_synergy_dependent(
        self,
        card_name: str,
        set_code: str | None = None,
        threshold: float = 0.04,
    ) -> bool:
        """Check if a card is synergy-dependent (better in Draft than Sealed).

        These cards need archetype support to shine.

        Args:
            card_name: Card name
            set_code: Optional set code
            threshold: Minimum Draft - Sealed WR difference to qualify

        Returns:
            True if card performs significantly better in Draft
        """
        draft_stats = self.get_card_stats(card_name, set_code, FORMAT_DRAFT)
        sealed_stats = self.get_card_stats(card_name, set_code, FORMAT_SEALED)

        if not draft_stats or not sealed_stats:
            return False
        if draft_stats.gih_wr is None or sealed_stats.gih_wr is None:
            return False

        return (draft_stats.gih_wr - sealed_stats.gih_wr) >= threshold

    def get_set_codes(self) -> list[str]:
        """Get list of available set codes."""
        if not self._conn:
            self.connect()
        if not self._conn:
            return []

        cursor = self._conn.cursor()
        cursor.execute("SELECT DISTINCT set_code FROM card_stats ORDER BY set_code")
        return [row[0] for row in cursor.fetchall()]

    def get_synergy_pairs(
        self,
        card_name: str,
        set_code: str | None = None,
        format: str | None = None,
        min_games: int = 50,
        min_lift: float = 0.0,
    ) -> list[SynergyPair]:
        """Get synergy pairs for a card.

        Args:
            card_name: Card to find synergies for
            set_code: Filter by set (optional)
            format: Filter by format (draft/sealed). If None, prefers draft.
            min_games: Minimum co-occurrence games
            min_lift: Minimum synergy lift

        Returns:
            List of SynergyPair sorted by synergy_lift descending
        """
        if not self._conn:
            self.connect()
        if not self._conn:
            return []

        cursor = self._conn.cursor()

        query = """
            SELECT card_a, card_b, set_code, format, co_occurrence_count, win_rate_together, synergy_lift
            FROM synergy_pairs
            WHERE (card_a = ? OR card_b = ?)
              AND co_occurrence_count >= ?
              AND synergy_lift >= ?
        """
        params: list[str | int | float] = [card_name, card_name, min_games, min_lift]

        if set_code:
            query += " AND set_code = ?"
            params.append(set_code.upper())

        if format:
            query += " AND format = ?"
            params.append(format)
        else:
            # Prefer draft synergies (more meaningful for archetype detection)
            query += " ORDER BY CASE format WHEN 'draft' THEN 0 ELSE 1 END, synergy_lift DESC LIMIT 20"

        if format:
            query += " ORDER BY synergy_lift DESC LIMIT 20"

        cursor.execute(query, params)

        results = []
        for row in cursor.fetchall():
            # Normalize so card_a is always the queried card
            card_a, card_b = row[0], row[1]
            if card_b == card_name:
                card_a, card_b = card_b, card_a

            results.append(
                SynergyPair(
                    card_a=card_a,
                    card_b=card_b,
                    set_code=row[2],
                    format=row[3] if len(row) > 6 else FORMAT_DRAFT,
                    co_occurrence_count=row[4] if len(row) > 6 else row[3],
                    win_rate_together=row[5] if len(row) > 6 else row[4],
                    synergy_lift=row[6] if len(row) > 6 else row[5],
                )
            )

        return results

    def get_top_cards(
        self,
        set_code: str | None = None,
        format: str | None = None,
        tier: str | None = None,
        limit: int = 20,
    ) -> list[LimitedCardStats]:
        """Get top cards by GIH WR.

        Args:
            set_code: Filter by set
            format: Filter by format (draft/sealed)
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

        if format:
            query += " AND format = ?"
            params.append(format)

        if tier:
            query += " AND tier = ?"
            params.append(tier.upper())

        query += " ORDER BY gih_wr DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)

        results = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            results.append(
                LimitedCardStats(
                    card_name=row_dict["card_name"],
                    set_code=row_dict["set_code"],
                    format=row_dict.get("format", FORMAT_DRAFT),
                    games_in_hand=row_dict["games_in_hand"],
                    gih_wr=row_dict["gih_wr"],
                    gih_wr_adjusted=row_dict.get("gih_wr_adjusted"),
                    oh_wr=row_dict["oh_wr"],
                    iwd=row_dict["iwd"],
                    tier=row_dict["tier"],
                )
            )
        return results


# Global singleton
_limited_stats_db: LimitedStatsDB | None = None


def get_limited_stats_db() -> LimitedStatsDB:
    """Get or create the global limited stats database instance."""
    global _limited_stats_db
    if _limited_stats_db is None:
        _limited_stats_db = LimitedStatsDB()
    return _limited_stats_db
