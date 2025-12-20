"""Hybrid recommendation system combining TF-IDF with structured features."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .features import CardEncoder, CardFeatures, DeckEncoder, DeckFeatures
from .spellbook_combos import SpellbookComboDetector, get_spellbook_detector
from .tfidf import CardRecommender

if TYPE_CHECKING:
    from mtg_core.data.database import MTGDatabase

logger = logging.getLogger(__name__)


# ============================================================================
# COMBO PIECE DETECTION (Missing Piece Algorithm)
# ============================================================================


@dataclass
class ComboMatch:
    """A detected combo match with missing pieces."""

    combo_id: str
    combo_type: str
    description: str
    present_cards: list[str]
    missing_cards: list[str]
    completion_ratio: float

    @property
    def missing_count(self) -> int:
        return len(self.missing_cards)

    @property
    def is_complete(self) -> bool:
        return self.missing_count == 0


class ComboPieceDetector:
    """Detects missing combo pieces using an inverted index."""

    def __init__(self) -> None:
        # Build inverted index from KNOWN_COMBOS
        from mtg_core.tools.synergy.constants import KNOWN_COMBOS

        self._card_to_combos: dict[str, list[str]] = {}  # card_name_lower -> combo_ids
        self._combo_cards: dict[str, list[str]] = {}  # combo_id -> [card_names]
        self._combo_meta: dict[str, dict[str, Any]] = {}  # combo_id -> metadata

        for combo in KNOWN_COMBOS:
            combo_id = combo["id"]
            card_names = [card[0].lower() for card in combo["cards"]]

            self._combo_cards[combo_id] = card_names
            self._combo_meta[combo_id] = {
                "type": combo.get("type", "value"),
                "desc": combo.get("desc", ""),
                "colors": combo.get("colors", []),
            }

            for card_name in card_names:
                if card_name not in self._card_to_combos:
                    self._card_to_combos[card_name] = []
                self._card_to_combos[card_name].append(combo_id)

    def find_missing_pieces(
        self,
        deck_cards: list[str],
        max_missing: int = 2,
    ) -> tuple[list[ComboMatch], dict[str, list[str]]]:
        """Find combos the deck is close to completing.

        Args:
            deck_cards: List of card names in the deck
            max_missing: Maximum number of missing pieces to consider

        Returns:
            Tuple of (combo matches, missing_card -> combo_ids it completes)
        """
        deck_lower = {card.lower() for card in deck_cards}

        # Count matches per combo
        combo_matches: dict[str, set[str]] = {}
        for card in deck_lower:
            for combo_id in self._card_to_combos.get(card, []):
                if combo_id not in combo_matches:
                    combo_matches[combo_id] = set()
                combo_matches[combo_id].add(card)

        # Find partial matches
        results: list[ComboMatch] = []
        missing_to_combos: dict[str, list[str]] = {}

        for combo_id, present in combo_matches.items():
            all_cards = set(self._combo_cards[combo_id])
            missing = all_cards - present

            if len(missing) > max_missing:
                continue

            meta = self._combo_meta[combo_id]
            results.append(
                ComboMatch(
                    combo_id=combo_id,
                    combo_type=meta["type"],
                    description=meta["desc"],
                    present_cards=list(present),
                    missing_cards=list(missing),
                    completion_ratio=len(present) / len(all_cards),
                )
            )

            # Track which cards complete which combos
            for card in missing:
                if card not in missing_to_combos:
                    missing_to_combos[card] = []
                missing_to_combos[card].append(combo_id)

        # Sort by completion ratio (most complete first)
        results.sort(key=lambda x: -x.completion_ratio)
        return results, missing_to_combos

    def get_combo_type_score(self, combo_type: str) -> float:
        """Score combo by type (win > infinite > lock > value)."""
        scores = {"win": 1.0, "infinite": 0.9, "lock": 0.7, "value": 0.5}
        return scores.get(combo_type, 0.3)


@dataclass
class ScoredRecommendation:
    """A recommendation with detailed scoring breakdown."""

    name: str
    total_score: float
    tfidf_score: float = 0.0
    synergy_score: float = 0.0
    curve_score: float = 0.0
    tribal_score: float = 0.0
    popularity_score: float = 0.0
    combo_score: float = 0.0  # Bonus for completing combos
    limited_score: float = 0.0  # 17lands GIH WR based score
    uuid: str | None = None
    type_line: str | None = None
    mana_cost: str | None = None
    colors: list[str] | None = None
    # Explanation
    reasons: list[str] = field(default_factory=list)
    completes_combos: list[str] = field(default_factory=list)  # Combo IDs this card completes
    # Limited stats (for display)
    limited_tier: str | None = None  # S/A/B/C/D/F from 17lands
    limited_gih_wr: float | None = None  # Games in Hand Win Rate
    # Collection tracking
    in_collection: bool = False  # Whether user owns this card


class SynergyScorer:
    """Scores cards based on mechanical synergy with a deck."""

    def __init__(self) -> None:
        self.card_encoder = CardEncoder()
        self.deck_encoder = DeckEncoder()

    def score_candidate(
        self,
        candidate: CardFeatures,
        deck: DeckFeatures,
    ) -> tuple[float, list[str]]:
        """Score a candidate card for the deck.

        Returns:
            Tuple of (score 0-1, list of reasons for the score)
        """
        scores: list[float] = []
        reasons: list[str] = []

        # 1. Theme synergy (most important)
        theme_score, theme_reasons = self._score_theme_synergy(candidate, deck)
        scores.append(theme_score * 2.0)  # Weight 2x
        reasons.extend(theme_reasons)

        # 2. Tribal synergy
        tribal_score, tribal_reason = self._score_tribal(candidate, deck)
        scores.append(tribal_score * 1.5)  # Weight 1.5x
        if tribal_reason:
            reasons.append(tribal_reason)

        # 3. Mana curve fit
        curve_score, curve_reason = self._score_curve_fit(candidate, deck)
        scores.append(curve_score)
        if curve_reason:
            reasons.append(curve_reason)

        # 4. Keyword synergy (combat keywords)
        keyword_score, keyword_reason = self._score_keywords(candidate, deck)
        scores.append(keyword_score)
        if keyword_reason:
            reasons.append(keyword_reason)

        # 5. Type balance
        type_score, type_reason = self._score_type_balance(candidate, deck)
        scores.append(type_score)
        if type_reason:
            reasons.append(type_reason)

        # Combine scores
        total = sum(scores) / (2.0 + 1.5 + 1.0 + 1.0 + 1.0)  # Weighted average
        return min(total, 1.0), reasons

    def _score_theme_synergy(
        self, candidate: CardFeatures, deck: DeckFeatures
    ) -> tuple[float, list[str]]:
        """Score based on matching synergy themes."""
        score = 0.0
        reasons: list[str] = []

        deck_themes = deck.dominant_themes
        if not deck_themes:
            return 0.0, []

        # Check if candidate has themes that match deck
        matching_themes = candidate.synergy_themes & set(deck_themes)
        if matching_themes:
            # More matching themes = higher score
            score = len(matching_themes) / len(deck_themes)
            theme_names = [self._theme_display_name(t) for t in matching_themes]
            reasons.append(f"Synergizes with: {', '.join(theme_names)}")

        # Bonus for cards that ENABLE themes (have the theme + deck has payoffs)
        enabling_themes = {
            "sacrifice": ["death_trigger", "aristocrats"],
            "death_trigger": ["sacrifice", "aristocrats"],
            "etb": ["blink"],
            "blink": ["etb"],
            "tokens": ["go_wide", "sacrifice"],
            "counters": ["counters"],  # Self-synergy
            "graveyard": ["self_mill"],
            "self_mill": ["graveyard"],
            "spellslinger": ["draw", "storm"],
        }

        for theme in candidate.synergy_themes:
            enables = enabling_themes.get(theme, [])
            for enabled in enables:
                if deck.synergy_themes.get(enabled, 0) >= 2:
                    score += 0.3
                    reasons.append(f"Enables {self._theme_display_name(enabled)} synergy")
                    break

        return min(score, 1.0), reasons

    def _score_tribal(
        self, candidate: CardFeatures, deck: DeckFeatures
    ) -> tuple[float, str | None]:
        """Score based on tribal synergy."""
        dominant = deck.dominant_tribe
        if not dominant:
            return 0.0, None

        # Check if candidate is the same tribe
        if dominant in candidate.subtypes:
            return 1.0, f"Same tribe: {dominant}"

        # Check if candidate is a tribal lord
        if "tribal_lord" in candidate.synergy_themes or "tribal_synergy" in candidate.synergy_themes:
            return 0.8, f"Tribal support for {dominant}"

        return 0.0, None

    def _score_curve_fit(
        self, candidate: CardFeatures, deck: DeckFeatures
    ) -> tuple[float, str | None]:
        """Score based on filling mana curve gaps."""
        if candidate.is_land:
            return 0.5, None  # Neutral for lands

        cmc = int(candidate.cmc)
        gap = deck.curve_gap_at(cmc)

        if gap > 0.1:
            return gap * 2, f"Fills curve gap at {cmc} CMC"
        elif gap < -0.1:
            return 0.2, None  # Slight penalty for oversaturated spot
        return 0.5, None

    def _score_keywords(
        self, candidate: CardFeatures, deck: DeckFeatures
    ) -> tuple[float, str | None]:
        """Score based on keyword ability synergy."""
        if not deck.keyword_presence:
            return 0.0, None

        # Keywords that synergize with each other
        keyword_synergies = {
            "flying": ["flying", "reach"],
            "deathtouch": ["first strike", "double strike", "trample"],
            "first strike": ["deathtouch"],
            "double strike": ["deathtouch", "lifelink"],
            "lifelink": ["double strike", "trample"],
            "trample": ["deathtouch"],
        }

        matching_keywords = candidate.keyword_abilities & deck.keyword_presence
        if matching_keywords:
            # Check for actual synergy, not just same keywords
            synergy_found = False
            for kw in candidate.keyword_abilities:
                synergizes_with = keyword_synergies.get(kw, [])
                if any(s in deck.keyword_presence for s in synergizes_with):
                    synergy_found = True
                    break

            if synergy_found:
                return 0.7, f"Keyword synergy: {', '.join(candidate.keyword_abilities)}"

        return 0.0, None

    def _score_type_balance(
        self, candidate: CardFeatures, deck: DeckFeatures
    ) -> tuple[float, str | None]:
        """Score based on balancing card type distribution."""
        # Ideal ratios (for a 60 card deck, adjustable)
        ideal_creature_ratio = 0.35
        ideal_spell_ratio = 0.25

        current_creature_ratio = deck.creature_ratio
        current_spell_ratio = deck.spell_ratio

        if candidate.is_creature:
            if current_creature_ratio < ideal_creature_ratio - 0.1:
                return 0.8, "Deck needs more creatures"
            elif current_creature_ratio > ideal_creature_ratio + 0.1:
                return 0.3, None
        elif (candidate.is_instant or candidate.is_sorcery) and current_spell_ratio < ideal_spell_ratio - 0.1:
            return 0.8, "Deck needs more spells"

        return 0.5, None

    def _theme_display_name(self, theme: str) -> str:
        """Convert theme key to display name."""
        display_names = {
            "sacrifice": "Sacrifice",
            "death_trigger": "Death triggers",
            "aristocrats": "Aristocrats",
            "etb": "ETB effects",
            "blink": "Blink",
            "graveyard": "Graveyard",
            "self_mill": "Self-mill",
            "tokens": "Tokens",
            "go_wide": "Go-wide",
            "counters": "+1/+1 counters",
            "draw": "Card draw",
            "impulse_draw": "Impulse draw",
            "ramp": "Ramp",
            "cost_reduction": "Cost reduction",
            "counterspell": "Counterspells",
            "removal": "Removal",
            "board_wipe": "Board wipes",
            "evasion": "Evasion",
            "combat_trigger": "Combat triggers",
            "equipment": "Equipment",
            "spellslinger": "Spellslinger",
            "storm": "Storm",
            "tribal_lord": "Tribal lords",
            "tribal_synergy": "Tribal synergy",
        }
        return display_names.get(theme, theme.replace("_", " ").title())


@dataclass
class HybridRecommender:
    """Hybrid recommendation engine combining TF-IDF with structured features."""

    _tfidf: CardRecommender | None = field(default=None, repr=False)
    _scorer: SynergyScorer = field(default_factory=SynergyScorer, repr=False)
    _combo_detector: ComboPieceDetector | None = field(default=None, repr=False)  # Legacy fallback
    _spellbook_detector: SpellbookComboDetector | None = field(default=None, repr=False)  # 73K+ combos
    _limited_stats: Any = field(default=None, repr=False)  # LimitedStatsDB
    _card_encoder: CardEncoder = field(default_factory=CardEncoder, repr=False)
    _deck_encoder: DeckEncoder = field(default_factory=DeckEncoder, repr=False)
    _card_data: dict[str, dict[str, Any]] = field(default_factory=dict, repr=False)
    _initialized: bool = False
    _init_time: float = 0.0

    # Weights for combining scores (now sum to 1.0)
    tfidf_weight: float = 0.20
    synergy_weight: float = 0.35
    popularity_weight: float = 0.10
    combo_weight: float = 0.20  # Bonus weight for combo completion
    limited_weight: float = 0.15  # 17lands Limited performance

    async def initialize(self, db: MTGDatabase) -> float:
        """Initialize both TF-IDF and structured features."""
        if self._initialized:
            return self._init_time

        start = time.perf_counter()
        logger.info("Initializing hybrid recommender...")

        # Initialize TF-IDF
        from .tfidf import CardRecommender
        self._tfidf = CardRecommender()
        await self._tfidf.initialize(db)

        # Store card data for feature encoding
        self._card_data = self._tfidf._card_data

        # Initialize Commander Spellbook combo detector (73K+ combos)
        try:
            self._spellbook_detector = get_spellbook_detector()
            if self._spellbook_detector.is_available:
                logger.info(f"Loaded {self._spellbook_detector.combo_count:,} combos from Commander Spellbook")
            else:
                logger.info("Commander Spellbook database not available, falling back to legacy combos")
                self._spellbook_detector = None
        except Exception as e:
            logger.warning(f"Could not load Spellbook detector: {e}")
            self._spellbook_detector = None

        # Fallback to legacy combo detector if Spellbook not available
        if not self._spellbook_detector:
            try:
                self._combo_detector = ComboPieceDetector()
                logger.info(f"Loaded {len(self._combo_detector._combo_cards)} legacy combos")
            except Exception as e:
                logger.warning(f"Could not load legacy combo detector: {e}")
                self._combo_detector = None

        # Initialize 17lands limited stats (optional)
        try:
            from .limited_stats import LimitedStatsDB
            self._limited_stats = LimitedStatsDB()
            if self._limited_stats.is_available:
                self._limited_stats.connect()
                sets = self._limited_stats.get_set_codes()
                logger.info(f"Loaded 17lands stats for {len(sets)} sets: {', '.join(sets[:5])}...")
            else:
                logger.info("17lands limited_stats.sqlite not found (optional)")
                self._limited_stats = None
        except Exception as e:
            logger.warning(f"Could not load 17lands stats: {e}")
            self._limited_stats = None

        self._init_time = time.perf_counter() - start
        self._initialized = True
        logger.info(f"Hybrid recommender initialized in {self._init_time:.2f}s")

        return self._init_time

    def recommend_for_deck(
        self,
        deck_cards: list[dict[str, Any]],
        n: int = 20,
        explain: bool = True,
    ) -> list[ScoredRecommendation]:
        """Get recommendations for a deck with detailed scoring.

        Args:
            deck_cards: List of card dicts in the deck
            n: Number of recommendations
            explain: Whether to include scoring explanations

        Returns:
            List of ScoredRecommendation sorted by total score
        """
        if not self._initialized or not self._tfidf:
            raise RuntimeError("Recommender not initialized")

        # Encode deck
        deck_features = self._deck_encoder.encode(deck_cards)
        deck_card_names = {c.get("name", "") for c in deck_cards}

        # Get TF-IDF candidates (broader pool)
        tfidf_results = self._tfidf.find_similar_to_cards(
            list(deck_card_names), n=200, exclude_input=True
        )

        # Detect missing combo pieces (prefer Spellbook's 73K+ combos)
        missing_card_to_combos: dict[str, list[str]] = {}
        combo_meta: dict[str, dict[str, Any]] = {}  # combo_id -> metadata for scoring

        if self._spellbook_detector:
            spellbook_matches, missing_card_to_combos = self._spellbook_detector.find_missing_pieces(
                list(deck_card_names), max_missing=2
            )
            # Build meta for scoring
            for match in spellbook_matches:
                combo_meta[match.combo.id] = {
                    "type": "win" if any("win" in f.lower() or "infinite" in f.lower() for f in match.combo.produces) else "value",
                    "bracket": match.combo.bracket_tag,
                    "popularity": match.combo.popularity,
                }
        elif self._combo_detector:
            _legacy_matches, missing_card_to_combos = self._combo_detector.find_missing_pieces(
                list(deck_card_names), max_missing=2
            )
            # Build meta from legacy detector
            for combo_ids in missing_card_to_combos.values():
                for cid in combo_ids:
                    if cid not in combo_meta and self._combo_detector:
                        meta = self._combo_detector._combo_meta.get(cid, {})
                        combo_meta[cid] = {"type": meta.get("type", "value")}

        # Score each candidate with synergy
        scored: list[ScoredRecommendation] = []
        for tfidf_rec in tfidf_results:
            if tfidf_rec.name in deck_card_names:
                continue

            # Get full card data
            card_data = self._card_data.get(tfidf_rec.name)
            if not card_data:
                continue

            # Encode candidate
            candidate_features = self._card_encoder.encode(card_data)

            # Filter by color identity - card must fit within deck's colors
            if (
                deck_features.color_identity
                and candidate_features.color_identity
                and not candidate_features.color_identity.issubset(deck_features.color_identity)
            ):
                continue  # Skip cards with incompatible color identity

            # Get synergy score
            synergy_score, reasons = self._scorer.score_candidate(
                candidate_features, deck_features
            )

            # Get popularity score from EDHRec rank
            edhrec_rank = card_data.get("edhrecRank")
            popularity_score = max(0, 1.0 - edhrec_rank / 30000.0) if edhrec_rank else 0.5

            # Check if this card completes any combos
            combo_score = 0.0
            completes_combos: list[str] = []
            card_name_lower = tfidf_rec.name.lower()
            if card_name_lower in missing_card_to_combos:
                combo_ids = missing_card_to_combos[card_name_lower]
                completes_combos = combo_ids

                # Score based on number and type of combos completed
                for combo_id in combo_ids:
                    meta = combo_meta.get(combo_id, {})
                    if self._spellbook_detector:
                        # Use bracket-based scoring for Spellbook combos
                        bracket = meta.get("bracket", "C")
                        type_score = self._spellbook_detector.get_bracket_score(bracket)
                        # Bonus for win conditions
                        if meta.get("type") == "win":
                            type_score = min(type_score + 0.2, 1.0)
                    elif self._combo_detector:
                        combo_type = meta.get("type", "value")
                        type_score = self._combo_detector.get_combo_type_score(combo_type)
                    else:
                        type_score = 0.5
                    combo_score += type_score

                # Normalize and cap at 1.0
                combo_score = min(combo_score / len(combo_ids), 1.0) if combo_ids else 0.0

                if explain and combo_ids:
                    combo_desc = f"Completes {len(combo_ids)} combo(s)"
                    reasons.append(combo_desc)

            # Get 17lands limited stats (if available)
            limited_score = 0.5  # Neutral default
            limited_tier: str | None = None
            limited_gih_wr: float | None = None
            if self._limited_stats:
                stats = self._limited_stats.get_card_stats(tfidf_rec.name)
                if stats:
                    limited_score = self._limited_stats.get_limited_score(tfidf_rec.name)
                    limited_tier = stats.tier
                    limited_gih_wr = stats.gih_wr
                    if explain and limited_tier in ("S", "A"):
                        reasons.append(f"Limited powerhouse ({limited_tier}-tier)")

            # Combine scores
            total = (
                tfidf_rec.score * self.tfidf_weight
                + synergy_score * self.synergy_weight
                + popularity_score * self.popularity_weight
                + combo_score * self.combo_weight
                + limited_score * self.limited_weight
            )

            scored.append(
                ScoredRecommendation(
                    name=tfidf_rec.name,
                    total_score=total,
                    tfidf_score=tfidf_rec.score,
                    synergy_score=synergy_score,
                    popularity_score=popularity_score,
                    combo_score=combo_score,
                    limited_score=limited_score,
                    uuid=tfidf_rec.uuid,
                    type_line=tfidf_rec.type_line,
                    mana_cost=tfidf_rec.mana_cost,
                    colors=tfidf_rec.colors,
                    reasons=reasons if explain else [],
                    completes_combos=completes_combos,
                    limited_tier=limited_tier,
                    limited_gih_wr=limited_gih_wr,
                )
            )

        # Sort by total score
        scored.sort(key=lambda x: -x.total_score)
        return scored[:n]

    def get_near_combos(
        self,
        deck_cards: list[dict[str, Any]],
        max_missing: int = 2,
    ) -> list[ComboMatch]:
        """Get combos that the deck is close to completing.

        Args:
            deck_cards: List of card dicts in the deck
            max_missing: Maximum missing pieces (1 or 2)

        Returns:
            List of ComboMatch objects sorted by completion ratio
        """
        deck_card_names = [c.get("name", "") for c in deck_cards]

        # Prefer Spellbook (73K+ combos) over legacy detector
        if self._spellbook_detector:
            matches, _ = self._spellbook_detector.find_missing_pieces(
                deck_card_names, max_missing=max_missing
            )
            # Convert SpellbookComboMatch to ComboMatch for API compatibility
            return [
                ComboMatch(
                    combo_id=m.combo.id,
                    combo_type="win" if any("win" in f.lower() or "infinite" in f.lower() for f in m.combo.produces) else "value",
                    description=m.combo.description,
                    present_cards=m.present_cards,
                    missing_cards=m.missing_cards,
                    completion_ratio=m.completion_ratio,
                )
                for m in matches[:50]  # Limit to top 50
            ]

        if self._combo_detector:
            combo_matches, _ = self._combo_detector.find_missing_pieces(
                deck_card_names, max_missing=max_missing
            )
            return combo_matches

        return []

    def analyze_deck(self, deck_cards: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze a deck's features and themes."""
        features = self._deck_encoder.encode(deck_cards)

        return {
            "card_count": features.card_count,
            "avg_cmc": round(features.avg_cmc, 2),
            "colors": {c: int(v) for c, v in features.color_intensity.items() if v > 0},
            "type_distribution": {
                "creatures": features.creature_count,
                "instants": features.instant_count,
                "sorceries": features.sorcery_count,
                "artifacts": features.artifact_count,
                "enchantments": features.enchantment_count,
                "planeswalkers": features.planeswalker_count,
                "lands": features.land_count,
            },
            "dominant_themes": features.dominant_themes,
            "dominant_tribe": features.dominant_tribe,
            "keywords": list(features.keyword_presence),
            "curve_gaps": {
                str(i): round(features.curve_gap_at(i), 2)
                for i in range(7)
                if features.curve_gap_at(i) > 0.05
            },
        }

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def card_count(self) -> int:
        return len(self._card_data) if self._card_data else 0


# Global singleton
_hybrid_recommender: HybridRecommender | None = None


def get_hybrid_recommender() -> HybridRecommender:
    """Get or create the global hybrid recommender."""
    global _hybrid_recommender
    if _hybrid_recommender is None:
        _hybrid_recommender = HybridRecommender()
    return _hybrid_recommender


async def initialize_hybrid_recommender(db: MTGDatabase) -> float:
    """Initialize the global hybrid recommender."""
    recommender = get_hybrid_recommender()
    return await recommender.initialize(db)
