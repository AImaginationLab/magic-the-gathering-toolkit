"""Gameplay statistics from 17lands data.

Uses the gameplay.duckdb database downloaded from GitHub releases.
DuckDB provides fast columnar analytics for win rate queries.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb

# Format categories matching download_17lands.py
FORMAT_DRAFT = "draft"
FORMAT_SEALED = "sealed"

# Default weights for combining Draft/Sealed scores
DEFAULT_DRAFT_WEIGHT = 0.7
DEFAULT_SEALED_WEIGHT = 0.3


def _find_gameplay_db() -> Path | None:
    """Find the gameplay database (17lands stats).

    Always uses ~/.mtg-spellbook/gameplay.duckdb (downloaded from GitHub releases).
    """
    from mtg_core.config import get_settings

    settings = get_settings()
    if settings.gameplay_db_path.exists():
        return settings.gameplay_db_path

    return None


@dataclass
class GameplayCardStats:
    """Card statistics from 17lands gameplay data."""

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


@dataclass
class ArchetypeCardStats:
    """Card performance in a specific archetype (color pair)."""

    card_name: str
    set_code: str
    archetype: str  # WU, UB, BR, RG, GW, WB, UR, BG, RW, GU
    gih_wr: float | None
    games_in_hand: int


class GameplayDB:
    """Query interface for gameplay.duckdb database.

    Uses DuckDB for fast columnar analytics on 17lands data.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        """Initialize with database path.

        Args:
            db_path: Path to gameplay.duckdb. If None, auto-discovers location.
        """
        if db_path is None:
            found = _find_gameplay_db()
            self._db_path = found if found else Path("gameplay.duckdb")
        else:
            self._db_path = Path(db_path)
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._cache: dict[str, GameplayCardStats] = {}

    @property
    def is_available(self) -> bool:
        """Check if the database exists."""
        return self._db_path.exists()

    def connect(self) -> None:
        """Connect to the database (read-only)."""
        if not self.is_available:
            return
        self._conn = duckdb.connect(str(self._db_path), read_only=True)

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
    ) -> GameplayCardStats | None:
        """Get gameplay stats for a card.

        Args:
            card_name: Card name to look up
            set_code: Optional set code to filter by. If None, returns most recent.
            format: Optional format (draft/sealed). If None, prefers draft.

        Returns:
            GameplayCardStats or None if not found
        """
        if not self._conn:
            self.connect()
        if not self._conn:
            return None

        # Check cache
        cache_key = f"{card_name}:{set_code or 'any'}:{format or 'any'}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Build query based on parameters
        if set_code and format:
            result = self._conn.execute(
                """
                SELECT card_name, set_code, format, games_in_hand, gih_wr,
                       gih_wr_adjusted, oh_wr, iwd, tier
                FROM card_stats
                WHERE card_name = ? AND set_code = ? AND format = ?
                """,
                [card_name, set_code.upper(), format],
            ).fetchone()
        elif set_code:
            result = self._conn.execute(
                """
                SELECT card_name, set_code, format, games_in_hand, gih_wr,
                       gih_wr_adjusted, oh_wr, iwd, tier
                FROM card_stats
                WHERE card_name = ? AND set_code = ?
                ORDER BY CASE format WHEN 'draft' THEN 0 ELSE 1 END, games_in_hand DESC
                LIMIT 1
                """,
                [card_name, set_code.upper()],
            ).fetchone()
        elif format:
            result = self._conn.execute(
                """
                SELECT card_name, set_code, format, games_in_hand, gih_wr,
                       gih_wr_adjusted, oh_wr, iwd, tier
                FROM card_stats
                WHERE card_name = ? AND format = ?
                ORDER BY games_in_hand DESC
                LIMIT 1
                """,
                [card_name, format],
            ).fetchone()
        else:
            result = self._conn.execute(
                """
                SELECT card_name, set_code, format, games_in_hand, gih_wr,
                       gih_wr_adjusted, oh_wr, iwd, tier
                FROM card_stats
                WHERE card_name = ?
                ORDER BY CASE format WHEN 'draft' THEN 0 ELSE 1 END, games_in_hand DESC
                LIMIT 1
                """,
                [card_name],
            ).fetchone()

        if not result:
            return None

        stats = GameplayCardStats(
            card_name=result[0],
            set_code=result[1],
            format=result[2] or FORMAT_DRAFT,
            games_in_hand=result[3],
            gih_wr=result[4],
            gih_wr_adjusted=result[5],
            oh_wr=result[6],
            iwd=result[7],
            tier=result[8],
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

    def get_gameplay_score(
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
        draft_score = self.get_gameplay_score(card_name, set_code, FORMAT_DRAFT, use_adjusted)
        sealed_score = self.get_gameplay_score(card_name, set_code, FORMAT_SEALED, use_adjusted)

        # Check what data we actually have
        draft_stats = self.get_card_stats(card_name, set_code, FORMAT_DRAFT)
        sealed_stats = self.get_card_stats(card_name, set_code, FORMAT_SEALED)

        has_draft = draft_stats is not None and draft_stats.gih_wr is not None
        has_sealed = sealed_stats is not None and sealed_stats.gih_wr is not None

        if has_draft and has_sealed:
            total_weight = draft_weight + sealed_weight
            return (draft_score * draft_weight + sealed_score * sealed_weight) / total_weight
        elif has_draft:
            return draft_score
        elif has_sealed:
            return sealed_score
        else:
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

        result = self._conn.execute(
            "SELECT DISTINCT set_code FROM card_stats ORDER BY set_code"
        ).fetchall()
        return [row[0] for row in result]

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

        query = """
            SELECT card_a, card_b, set_code, format, co_occurrence_count,
                   win_rate_together, synergy_lift
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
            query += " ORDER BY synergy_lift DESC LIMIT 20"
        else:
            query += (
                " ORDER BY CASE format WHEN 'draft' THEN 0 ELSE 1 END, synergy_lift DESC LIMIT 20"
            )

        rows = self._conn.execute(query, params).fetchall()

        results = []
        for row in rows:
            # Normalize so card_a is always the queried card
            card_a, card_b = row[0], row[1]
            if card_b == card_name:
                card_a, card_b = card_b, card_a

            results.append(
                SynergyPair(
                    card_a=card_a,
                    card_b=card_b,
                    set_code=row[2],
                    format=row[3] or FORMAT_DRAFT,
                    co_occurrence_count=row[4],
                    win_rate_together=row[5],
                    synergy_lift=row[6],
                )
            )

        return results

    def get_top_cards(
        self,
        set_code: str | None = None,
        format: str | None = None,
        tier: str | None = None,
        limit: int = 20,
    ) -> list[GameplayCardStats]:
        """Get top cards by GIH WR.

        Args:
            set_code: Filter by set
            format: Filter by format (draft/sealed)
            tier: Filter by tier (S/A/B/C/D/F)
            limit: Max cards to return

        Returns:
            List of GameplayCardStats sorted by GIH WR descending
        """
        if not self._conn:
            self.connect()
        if not self._conn:
            return []

        query = """
            SELECT card_name, set_code, format, games_in_hand, gih_wr,
                   gih_wr_adjusted, oh_wr, iwd, tier
            FROM card_stats
            WHERE gih_wr IS NOT NULL
        """
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

        rows = self._conn.execute(query, params).fetchall()

        results = []
        for row in rows:
            results.append(
                GameplayCardStats(
                    card_name=row[0],
                    set_code=row[1],
                    format=row[2] or FORMAT_DRAFT,
                    games_in_hand=row[3],
                    gih_wr=row[4],
                    gih_wr_adjusted=row[5],
                    oh_wr=row[6],
                    iwd=row[7],
                    tier=row[8],
                )
            )
        return results

    def get_archetype_cards(
        self,
        archetype: str,
        set_code: str | None = None,
        min_games: int = 100,
        limit: int = 30,
    ) -> list[ArchetypeCardStats]:
        """Get top cards for a specific archetype (color pair).

        Args:
            archetype: Two-color archetype (WU, UB, BR, RG, GW, WB, UR, BG, RW, GU)
                       Can be in any order - UB and BU are treated the same.
            set_code: Filter by set (optional)
            min_games: Minimum games in hand for statistical significance
            limit: Max cards to return

        Returns:
            List of ArchetypeCardStats sorted by GIH WR descending
        """
        if not self._conn:
            self.connect()
        if not self._conn:
            return []

        # Normalize archetype - database may use either order (UB or BU)
        arch = archetype.upper()
        arch_reversed = arch[::-1] if len(arch) == 2 else arch

        query = """
            SELECT card_name, set_code, archetype, gih_wr, games_in_hand
            FROM card_archetype_stats
            WHERE (archetype = ? OR archetype = ?)
              AND gih_wr IS NOT NULL
              AND games_in_hand >= ?
        """
        params: list[str | int] = [arch, arch_reversed, min_games]

        if set_code:
            query += " AND set_code = ?"
            params.append(set_code.upper())

        query += " ORDER BY gih_wr DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(query, params).fetchall()

        results = []
        for row in rows:
            results.append(
                ArchetypeCardStats(
                    card_name=row[0],
                    set_code=row[1],
                    archetype=row[2],
                    gih_wr=row[3],
                    games_in_hand=row[4],
                )
            )
        return results

    def get_available_archetypes(self, set_code: str) -> list[str]:
        """Get available archetypes for a set."""
        if not self._conn:
            self.connect()
        if not self._conn:
            return []

        result = self._conn.execute(
            "SELECT DISTINCT archetype FROM card_archetype_stats WHERE set_code = ? ORDER BY archetype",
            [set_code.upper()],
        ).fetchall()
        return [row[0] for row in result]


# Global singleton
_gameplay_db: GameplayDB | None = None


def get_gameplay_db() -> GameplayDB:
    """Get or create the global gameplay database instance."""
    global _gameplay_db
    if _gameplay_db is None:
        _gameplay_db = GameplayDB()
    return _gameplay_db
