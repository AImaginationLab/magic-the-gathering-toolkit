"""Commander Spellbook combo detection using downloaded database.

Uses the combos.sqlite database from Commander Spellbook (73K+ combos) for
detecting missing combo pieces in decks.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SpellbookCombo:
    """A combo from Commander Spellbook."""

    id: str
    card_names: list[str]
    description: str
    bracket_tag: str  # C=Casual, P=Precon, S=Spicy, R=Ruthless
    popularity: int
    identity: str  # Color identity (e.g., "UB", "WRG")
    produces: list[str]  # Feature names like "Infinite mana", "Win the game"


@dataclass
class SpellbookComboMatch:
    """A detected combo match with missing pieces."""

    combo: SpellbookCombo
    present_cards: list[str]
    missing_cards: list[str]
    completion_ratio: float

    @property
    def missing_count(self) -> int:
        return len(self.missing_cards)

    @property
    def is_complete(self) -> bool:
        return self.missing_count == 0


def _find_combos_db() -> Path | None:
    """Find the Commander Spellbook combos database."""
    # Check common locations
    candidates = [
        Path(__file__).parents[6] / "resources" / "combos.sqlite",  # Repo root
        Path.home() / ".cache" / "mtg-toolkit" / "combos.sqlite",  # Cache
        Path("resources") / "combos.sqlite",  # CWD
    ]

    for path in candidates:
        if path.exists():
            return path

    return None


class SpellbookComboDetector:
    """Detects missing combo pieces using Commander Spellbook database.

    Builds an inverted index at startup for fast lookup of combos containing
    specific cards. Supports filtering by bracket (power level).
    """

    def __init__(self, db_path: Path | None = None, min_popularity: int = 0):
        """Initialize the combo detector.

        Args:
            db_path: Path to combos.sqlite. Auto-detected if None.
            min_popularity: Minimum popularity score to include (filters obscure combos)
        """
        self._db_path = db_path or _find_combos_db()
        self._min_popularity = min_popularity

        # Inverted index: card_name_lower -> set of combo_ids
        self._card_to_combos: dict[str, set[str]] = {}
        # Combo data: combo_id -> SpellbookCombo
        self._combos: dict[str, SpellbookCombo] = {}

        self._initialized = False
        self._combo_count = 0

    @property
    def is_available(self) -> bool:
        """Check if the database is available."""
        return self._db_path is not None and self._db_path.exists()

    @property
    def combo_count(self) -> int:
        """Number of loaded combos."""
        return self._combo_count

    def initialize(self) -> bool:
        """Load combos and build inverted index.

        Returns:
            True if successful, False if database not available.
        """
        if self._initialized:
            return True

        if not self.is_available:
            logger.warning("Commander Spellbook database not found")
            return False

        try:
            self._load_combos()
            self._initialized = True
            logger.info(
                f"Loaded {self._combo_count:,} combos from Commander Spellbook "
                f"({len(self._card_to_combos):,} unique cards)"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to load combos: {e}")
            return False

    def _load_combos(self) -> None:
        """Load combos from database and build inverted index."""
        assert self._db_path is not None

        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row

        # Query combos (filter by popularity if specified)
        query = """
            SELECT id, card_names, description, bracket_tag, popularity,
                   identity, produces
            FROM combos
            WHERE popularity >= ?
            ORDER BY popularity DESC
        """

        cursor = conn.execute(query, (self._min_popularity,))

        for row in cursor:
            combo_id = row["id"]
            card_names = json.loads(row["card_names"])

            combo = SpellbookCombo(
                id=combo_id,
                card_names=card_names,
                description=row["description"] or "",
                bracket_tag=row["bracket_tag"] or "C",
                popularity=row["popularity"] or 0,
                identity=row["identity"] or "",
                produces=json.loads(row["produces"]) if row["produces"] else [],
            )

            self._combos[combo_id] = combo

            # Build inverted index
            for card_name in card_names:
                card_lower = card_name.lower()
                if card_lower not in self._card_to_combos:
                    self._card_to_combos[card_lower] = set()
                self._card_to_combos[card_lower].add(combo_id)

        conn.close()
        self._combo_count = len(self._combos)

    def find_missing_pieces(
        self,
        deck_cards: list[str],
        max_missing: int = 2,
        bracket_filter: str | None = None,
        min_present: int = 1,
    ) -> tuple[list[SpellbookComboMatch], dict[str, list[str]]]:
        """Find combos the deck is close to completing.

        Args:
            deck_cards: List of card names in the deck
            max_missing: Maximum number of missing pieces to consider
            bracket_filter: Only include combos of this bracket (C/P/S/R)
            min_present: Minimum cards from combo that must be present

        Returns:
            Tuple of (combo matches, missing_card -> combo_ids it completes)
        """
        if not self._initialized:
            self.initialize()

        if not self._initialized:
            return [], {}

        deck_lower = {card.lower() for card in deck_cards}

        # Find combos that share cards with the deck
        candidate_combo_ids: set[str] = set()
        for card in deck_lower:
            if card in self._card_to_combos:
                candidate_combo_ids.update(self._card_to_combos[card])

        results: list[SpellbookComboMatch] = []
        missing_to_combos: dict[str, list[str]] = {}

        for combo_id in candidate_combo_ids:
            combo = self._combos[combo_id]

            # Apply bracket filter
            if bracket_filter and combo.bracket_tag != bracket_filter:
                continue

            combo_cards_lower = {c.lower() for c in combo.card_names}
            present = combo_cards_lower & deck_lower
            missing = combo_cards_lower - deck_lower

            # Check constraints
            if len(missing) > max_missing:
                continue
            if len(present) < min_present:
                continue

            match = SpellbookComboMatch(
                combo=combo,
                present_cards=[c for c in combo.card_names if c.lower() in present],
                missing_cards=[c for c in combo.card_names if c.lower() in missing],
                completion_ratio=len(present) / len(combo.card_names),
            )
            results.append(match)

            # Track which cards complete which combos
            for card in missing:
                if card not in missing_to_combos:
                    missing_to_combos[card] = []
                missing_to_combos[card].append(combo_id)

        # Sort by popularity (most popular first), then completion ratio
        results.sort(key=lambda x: (-x.combo.popularity, -x.completion_ratio))
        return results, missing_to_combos

    def find_combos_for_card(
        self,
        card_name: str,
        limit: int = 20,
        bracket_filter: str | None = None,
    ) -> list[SpellbookCombo]:
        """Find all combos containing a specific card.

        Args:
            card_name: Card name to search for
            limit: Maximum number of combos to return
            bracket_filter: Only include combos of this bracket

        Returns:
            List of combos containing the card, sorted by popularity
        """
        if not self._initialized:
            self.initialize()

        if not self._initialized:
            return []

        card_lower = card_name.lower()
        combo_ids = self._card_to_combos.get(card_lower, set())

        combos = []
        for combo_id in combo_ids:
            combo = self._combos[combo_id]
            if bracket_filter and combo.bracket_tag != bracket_filter:
                continue
            combos.append(combo)

        # Sort by popularity
        combos.sort(key=lambda x: -x.popularity)
        return combos[:limit]

    def get_bracket_score(self, bracket_tag: str) -> float:
        """Score combo by bracket (power level).

        R (Ruthless/cEDH) > S (Spicy) > P (Precon) > C (Casual)
        """
        scores = {"R": 1.0, "S": 0.8, "P": 0.6, "C": 0.4, "O": 0.5}
        return scores.get(bracket_tag, 0.3)

    def get_combo(self, combo_id: str) -> SpellbookCombo | None:
        """Get a combo by ID."""
        if not self._initialized:
            self.initialize()
        return self._combos.get(combo_id)

    def get_combo_score(self, combo: SpellbookCombo) -> float:
        """Calculate a combined score for a combo.

        Factors in bracket (power level), popularity, and outcome.
        """
        # Base score from bracket
        score = self.get_bracket_score(combo.bracket_tag)

        # Bonus for win conditions
        win_keywords = ["win the game", "infinite", "loop"]
        for feature in combo.produces:
            feature_lower = feature.lower()
            if any(kw in feature_lower for kw in win_keywords):
                score += 0.2
                break

        # Popularity boost (normalized to 0-0.2)
        # Top combos have ~250k popularity
        pop_score = min(combo.popularity / 250000, 1.0) * 0.2
        score += pop_score

        return min(score, 1.0)


# Global singleton
_spellbook_detector: SpellbookComboDetector | None = None


def get_spellbook_detector() -> SpellbookComboDetector:
    """Get or create the global spellbook combo detector."""
    global _spellbook_detector
    if _spellbook_detector is None:
        _spellbook_detector = SpellbookComboDetector()
        _spellbook_detector.initialize()
    return _spellbook_detector
