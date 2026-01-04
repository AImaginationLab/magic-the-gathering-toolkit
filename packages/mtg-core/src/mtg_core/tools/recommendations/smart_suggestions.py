"""Smart deck suggestions using integrated data sources.

Uses:
- 17Lands gameplay data (synergy pairs, archetype performance, card tiers)
- Commander Spellbook (73K+ combos for combo potential)
- MTG database (card types, color identity, EDHREC rank)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .gameplay import GameplayDB, get_gameplay_db
from .spellbook_combos import (
    SpellbookComboDetector,
    get_spellbook_detector,
)

if TYPE_CHECKING:
    from mtg_core.data.database import UnifiedDatabase

logger = logging.getLogger(__name__)


@dataclass
class SmartCardScore:
    """Card with multi-source scoring."""

    name: str
    edhrec_rank: int | None = None  # Lower = more popular
    tier: str | None = None  # S/A/B/C/D/F from 17Lands
    gih_wr: float | None = None  # Win rate from 17Lands
    synergy_lift: float = 0.0  # Synergy bonus from pairs
    combo_potential: int = 0  # Number of combos containing this card
    relevance_score: float = 0.0  # Computed overall score


@dataclass
class ComboInfo:
    """Combo information for a suggestion."""

    name: str  # Brief combo name
    cards: list[str]
    owned_cards: list[str]
    missing_cards: list[str]
    produces: list[str]  # e.g., ["Infinite mana", "Win the game"]
    completion_pct: float


@dataclass
class SmartDeckSuggestion:
    """Enhanced deck suggestion with rich scoring data."""

    name: str
    format: str
    commander: str | None = None
    archetype: str | None = None
    colors: list[str] = field(default_factory=list)

    # Core cards
    key_cards_owned: list[str] = field(default_factory=list)
    key_cards_missing: list[str] = field(default_factory=list)

    # Scoring breakdown
    completion_pct: float = 0.0
    synergy_score: float = 0.0  # 0-1, based on synergy pairs
    power_score: float = 0.0  # 0-1, based on card quality
    combo_score: float = 0.0  # 0-1, combo potential

    # Intelligence
    dominant_themes: list[str] = field(default_factory=list)
    tribal_type: str | None = None
    near_combos: list[ComboInfo] = field(default_factory=list)
    complete_combos: list[ComboInfo] = field(default_factory=list)
    limited_bombs: list[str] = field(default_factory=list)  # S/A tier cards

    reasons: list[str] = field(default_factory=list)


class SmartSuggestionEngine:
    """Intelligent deck suggestion engine using all available data."""

    def __init__(
        self,
        db: UnifiedDatabase | None = None,
        gameplay_db: GameplayDB | None = None,
        combo_detector: SpellbookComboDetector | None = None,
    ) -> None:
        self._db = db
        self._gameplay_db = gameplay_db or get_gameplay_db()
        self._combo_detector = combo_detector
        self._combo_detector_initialized = combo_detector is not None

    async def _get_combo_detector(self) -> SpellbookComboDetector | None:
        """Get combo detector, initializing lazily if needed."""
        if not self._combo_detector_initialized:
            self._combo_detector = await get_spellbook_detector()
            self._combo_detector_initialized = True
        return self._combo_detector

    def initialize(self, db: UnifiedDatabase) -> None:
        """Initialize with database connection."""
        self._db = db

    def find_tribal_commanders(
        self,
        creature_type: str,
        colors: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, str | int | None]]:
        """Find commanders that synergize with a creature type.

        Queries the MTG database for legendary creatures that:
        1. Are the specified creature type (e.g., Horror)
        2. Mention the creature type in oracle text
        3. Have general tribal support text

        Returns:
            List of commander dicts with name, type_line, oracle_text, edhrec_rank
        """
        # Build SQL query based on database agent's recommendations
        import sqlite3

        # Get database path from settings
        from mtg_core.config import get_settings

        settings = get_settings()
        db_path = settings.mtg_db_path

        if not db_path.exists():
            return []

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row

            type_lower = creature_type.lower()

            # Query for commanders matching tribal
            query = """
                SELECT DISTINCT
                    name,
                    type_line,
                    oracle_text,
                    color_identity,
                    edhrec_rank,
                    CASE
                        WHEN LOWER(oracle_text) LIKE ? THEN 1
                        WHEN LOWER(type_line) LIKE ? THEN 2
                        WHEN LOWER(oracle_text) LIKE '%creature type%' THEN 3
                        WHEN LOWER(oracle_text) LIKE '%creatures you control%' THEN 4
                        ELSE 5
                    END AS relevance_tier
                FROM cards
                WHERE LOWER(type_line) LIKE '%legendary%'
                  AND LOWER(type_line) LIKE '%creature%'
                  AND legal_commander = 1
                  AND (is_token = 0 OR is_token IS NULL)
                  AND (
                      LOWER(oracle_text) LIKE ?
                      OR LOWER(type_line) LIKE ?
                      OR LOWER(oracle_text) LIKE '%changeling%'
                  )
                ORDER BY relevance_tier ASC, edhrec_rank ASC NULLS LAST
                LIMIT ?
            """

            params = [
                f"%{type_lower}%",  # oracle text like
                f"%{type_lower}%",  # type_line like for tier
                f"%{type_lower}%",  # oracle text filter
                f"%{type_lower}%",  # type_line filter
                limit,
            ]

            cursor = conn.execute(query, params)
            results = []

            for row in cursor:
                # Apply color filter if specified
                if colors:
                    import json

                    card_identity = json.loads(row["color_identity"] or "[]")
                    if card_identity and not set(card_identity).issubset(set(colors)):
                        continue

                results.append(
                    {
                        "name": row["name"],
                        "type_line": row["type_line"],
                        "oracle_text": row["oracle_text"],
                        "edhrec_rank": row["edhrec_rank"],
                    }
                )

            conn.close()
            return results

        except Exception as e:
            logger.error(f"Error querying tribal commanders: {e}")
            return []

    def find_tribal_creatures(
        self,
        creature_type: str,
        colors: list[str] | None = None,
        collection_cards: set[str] | None = None,
        limit: int = 50,
    ) -> list[dict[str, str | int | None]]:
        """Find creatures of a specific type, optionally filtering to collection.

        Args:
            creature_type: Creature type to search for (e.g., "Horror")
            colors: Optional color identity filter
            collection_cards: If provided, only return cards in this set
            limit: Maximum cards to return

        Returns:
            List of creature dicts with name, type_line, mana_cost, edhrec_rank
        """
        import sqlite3

        from mtg_core.config import get_settings

        settings = get_settings()
        db_path = settings.mtg_db_path

        if not db_path.exists():
            return []

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row

            type_lower = creature_type.lower()

            query = """
                SELECT DISTINCT
                    name,
                    type_line,
                    mana_cost,
                    color_identity,
                    edhrec_rank
                FROM cards
                WHERE LOWER(type_line) LIKE '%creature%'
                  AND LOWER(type_line) LIKE ?
                  AND legal_commander = 1
                  AND (is_token = 0 OR is_token IS NULL)
                ORDER BY edhrec_rank ASC NULLS LAST
                LIMIT ?
            """

            cursor = conn.execute(query, [f"%{type_lower}%", limit * 2])
            results = []

            for row in cursor:
                name = row["name"]

                # Filter to collection if provided
                if collection_cards and name not in collection_cards:
                    continue

                # Apply color filter
                if colors:
                    import json

                    card_identity = json.loads(row["color_identity"] or "[]")
                    if card_identity and not set(card_identity).issubset(set(colors)):
                        continue

                results.append(
                    {
                        "name": name,
                        "type_line": row["type_line"],
                        "mana_cost": row["mana_cost"],
                        "edhrec_rank": row["edhrec_rank"],
                    }
                )

                if len(results) >= limit:
                    break

            conn.close()
            return results

        except Exception as e:
            logger.error(f"Error querying tribal creatures: {e}")
            return []

    def find_theme_cards(
        self,
        theme: str,
        colors: list[str] | None = None,
        collection_cards: set[str] | None = None,
        limit: int = 50,
    ) -> list[dict[str, str | int | None]]:
        """Find cards supporting a theme using pattern matching.

        Uses the theme patterns from the database agent's design.
        """
        # Theme pattern definitions
        theme_patterns: dict[str, list[str]] = {
            "graveyard": [
                "%graveyard%",
                "%dies%",
                "%sacrifice%",
                "%mill%",
                "%flashback%",
                "%unearth%",
            ],
            "tokens": [
                "%create%token%",
                "%token%enters%",
                "%populate%",
            ],
            "counters": [
                "%+1/+1 counter%",
                "%proliferate%",
                "%counter on%",
            ],
            "spellslinger": [
                "%instant%sorcery%",
                "%cast%spell%",
                "%magecraft%",
            ],
            "artifacts": [
                "%artifact%enters%",
                "%affinity%",
                "%metalcraft%",
            ],
            "enchantments": [
                "%enchantment%enters%",
                "%constellation%",
                "%bestow%",
            ],
            "lifegain": [
                "%gain%life%",
                "%lifelink%",
                "%whenever you gain life%",
            ],
            "blink": [
                "%exile%return%battlefield%",
                "%flicker%",
                "%enters%trigger%",
            ],
            "reanimator": [
                "%graveyard to the battlefield%",
                "%return%creature%",
                "%reanimate%",
            ],
        }

        theme_lower = theme.lower()
        patterns = theme_patterns.get(theme_lower, [f"%{theme_lower}%"])

        import sqlite3

        from mtg_core.config import get_settings

        settings = get_settings()
        db_path = settings.mtg_db_path

        if not db_path.exists():
            return []

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row

            # Build OR conditions for patterns
            pattern_conditions = " OR ".join(["LOWER(oracle_text) LIKE ?" for _ in patterns])

            query = f"""
                SELECT DISTINCT
                    name,
                    type_line,
                    oracle_text,
                    mana_cost,
                    color_identity,
                    edhrec_rank
                FROM cards
                WHERE legal_commander = 1
                  AND (is_token = 0 OR is_token IS NULL)
                  AND ({pattern_conditions})
                ORDER BY edhrec_rank ASC NULLS LAST
                LIMIT ?
            """

            cursor = conn.execute(query, [*patterns, limit * 2])
            results = []

            for row in cursor:
                name = row["name"]

                # Filter to collection if provided
                if collection_cards and name not in collection_cards:
                    continue

                # Apply color filter
                if colors:
                    import json

                    card_identity = json.loads(row["color_identity"] or "[]")
                    if card_identity and not set(card_identity).issubset(set(colors)):
                        continue

                results.append(
                    {
                        "name": name,
                        "type_line": row["type_line"],
                        "oracle_text": row["oracle_text"],
                        "mana_cost": row["mana_cost"],
                        "edhrec_rank": row["edhrec_rank"],
                    }
                )

                if len(results) >= limit:
                    break

            conn.close()
            return results

        except Exception as e:
            logger.error(f"Error querying theme cards: {e}")
            return []

    def get_synergy_pairs_for_deck(
        self,
        card_names: list[str],
        set_code: str | None = None,
    ) -> dict[tuple[str, str], float]:
        """Get synergy lifts between cards in a deck.

        Returns:
            Dict mapping (card_a, card_b) -> synergy_lift
        """
        synergies: dict[tuple[str, str], float] = {}

        if not self._gameplay_db.is_available:
            return synergies

        self._gameplay_db.connect()

        for card_name in card_names[:30]:  # Limit for performance
            pairs = self._gameplay_db.get_synergy_pairs(
                card_name, set_code, min_games=50, min_lift=0.01
            )
            for pair in pairs:
                if pair.card_b in card_names:
                    key = (pair.card_a, pair.card_b)
                    synergies[key] = pair.synergy_lift or 0.0

        return synergies

    async def analyze_combo_potential(
        self,
        card_names: list[str],
        color_identity: list[str] | None = None,
    ) -> tuple[list[ComboInfo], list[ComboInfo]]:
        """Analyze combo potential for a set of cards.

        Args:
            card_names: Cards to analyze
            color_identity: Optional color filter for combos

        Returns:
            Tuple of (complete_combos, near_combos)
        """
        combo_detector = await self._get_combo_detector()
        if not combo_detector or not combo_detector.is_available:
            return [], []

        await combo_detector.initialize()

        # Find combos we're close to completing
        matches, _ = await combo_detector.find_missing_pieces(
            card_names,
            max_missing=2,
            min_present=2,
        )

        complete: list[ComboInfo] = []
        near: list[ComboInfo] = []

        for match in matches[:10]:  # Limit results
            # Filter by color identity if specified
            if color_identity:
                combo_identity = set(match.combo.identity.upper())
                if combo_identity and not combo_identity.issubset(
                    {c.upper() for c in color_identity}
                ):
                    continue

            info = ComboInfo(
                name=match.combo.produces[0] if match.combo.produces else "Combo",
                cards=match.combo.card_names,
                owned_cards=match.present_cards,
                missing_cards=match.missing_cards,
                produces=match.combo.produces,
                completion_pct=match.completion_ratio,
            )

            if match.is_complete:
                complete.append(info)
            else:
                near.append(info)

        return complete, near

    async def score_card_power(
        self,
        card_name: str,
        set_code: str | None = None,
    ) -> SmartCardScore:
        """Get power score for a card using all data sources."""
        score = SmartCardScore(name=card_name)

        # Get 17Lands data if available
        if self._gameplay_db.is_available:
            self._gameplay_db.connect()
            stats = self._gameplay_db.get_card_stats(card_name, set_code)
            if stats:
                score.tier = stats.tier
                score.gih_wr = stats.gih_wr

        # Get combo potential
        combo_detector = await self._get_combo_detector()
        if combo_detector and combo_detector.is_available:
            await combo_detector.initialize()
            combos = await combo_detector.find_combos_for_card(card_name, limit=50)
            score.combo_potential = len(combos)

        # Calculate relevance score
        tier_scores = {"S": 1.0, "A": 0.8, "B": 0.6, "C": 0.4, "D": 0.2, "F": 0.1}
        tier_score = tier_scores.get(score.tier or "", 0.5)

        # Normalize combo potential (log scale)
        import math

        combo_score = math.log10(score.combo_potential + 1) / 2.0  # ~50 combos = 0.85
        combo_score = min(combo_score, 1.0)

        score.relevance_score = (tier_score * 0.6) + (combo_score * 0.4)

        return score

    def find_bombs(
        self,
        card_names: list[str],
        set_code: str | None = None,
    ) -> list[str]:
        """Find high-performing cards (S/A tier) in a list."""
        if not self._gameplay_db.is_available:
            return []

        self._gameplay_db.connect()
        bombs = []

        for card_name in card_names:
            tier = self._gameplay_db.get_tier(card_name, set_code)
            if tier in ("S", "A"):
                bombs.append(card_name)

        return bombs


# Global singleton
_smart_engine: SmartSuggestionEngine | None = None


def get_smart_engine() -> SmartSuggestionEngine:
    """Get or create the global smart suggestion engine."""
    global _smart_engine
    if _smart_engine is None:
        _smart_engine = SmartSuggestionEngine()
    return _smart_engine
