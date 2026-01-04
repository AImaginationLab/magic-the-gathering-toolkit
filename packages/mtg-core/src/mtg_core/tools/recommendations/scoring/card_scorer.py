"""Card scoring functions for deck recommendations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .weights import DEFAULT_SCORING_CONFIG, ScoringConfig

if TYPE_CHECKING:
    from ..features import CardEncoder, DeckFeatures
    from ..gameplay import GameplayDB
    from ..hybrid import SynergyScorer
    from ..models import CardData


def score_limited_stats(
    card_name: str,
    gameplay_db: GameplayDB,
    set_code: str | None = None,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
) -> tuple[float, str | None, bool]:
    """Score a card based on 17Lands Limited performance data.

    Uses gameplay.duckdb to look up:
    - Tier (S/A/B/C/D/F) for quality assessment
    - GIH WR (game-in-hand win rate) for performance scoring
    - Bomb detection (cards better in Sealed than Draft = standalone power)

    Args:
        card_name: Card name to look up
        gameplay_db: GameplayDB instance for data lookup
        set_code: Optional set code for specific set data
        config: Scoring configuration with weights

    Returns:
        Tuple of (score_bonus, tier, is_bomb) where:
        - score_bonus: -0.5 to 1.8 extra score for high-performing cards
        - tier: S/A/B/C/D/F or None if no data
        - is_bomb: True if card is a standalone powerhouse
    """
    if not gameplay_db.is_available:
        return 0.0, None, False

    stats = gameplay_db.get_card_stats(card_name, set_code)
    if not stats:
        return 0.0, None, False

    tier = stats.tier
    is_bomb = gameplay_db.is_bomb(card_name, set_code)

    # Score bonus based on tier
    weights = config.limited_tier_weights
    score_bonus = weights.get(tier, 0.0)

    # Additional bonus for bombs (standalone power)
    if is_bomb:
        score_bonus += weights.BOMB_BONUS

    return score_bonus, tier, is_bomb


def score_card_for_deck(
    card: CardData,
    deck_features: DeckFeatures,
    synergy_scorer: SynergyScorer,
    card_encoder: CardEncoder,
    gameplay_db: GameplayDB,
    archetype: str | None = None,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
) -> tuple[float, list[str]]:
    """Score a card's fit for a specific deck using SynergyScorer.

    Uses the hybrid recommendation system's synergy scoring which considers:
    - Theme synergy (sacrifice, ETB, graveyard, tokens, etc.)
    - Tribal synergy (creature type matching, tribal lords)
    - Mana curve fit (fills gaps in the curve)
    - Keyword ability synergy (flying+reach, deathtouch+first strike)
    - Type balance (creature ratio, spell ratio)

    Args:
        card: The candidate card to score
        deck_features: Pre-computed features of the deck
        synergy_scorer: SynergyScorer instance
        card_encoder: CardEncoder for encoding card features
        gameplay_db: GameplayDB for Limited stats
        archetype: Optional archetype name for bonus scoring
        config: Scoring configuration with weights

    Returns:
        Tuple of (score, reasons) where score is 0.0+ and reasons explain the score
    """
    # Lands don't need synergy scoring - they're handled in Pass 1
    if card.is_land():
        return 0.0, []

    weights = config.card_scoring

    # Encode the candidate card
    card_dict = card.to_encoder_dict()
    candidate_features = card_encoder.encode(card_dict)

    # Use SynergyScorer for proper synergy analysis
    synergy_score, reasons = synergy_scorer.score_candidate(candidate_features, deck_features)

    # Base score from synergy (0-1 range, scale up for selection)
    score = synergy_score * weights.SYNERGY_SCALE

    # Archetype bonus (if card text mentions the archetype)
    if archetype:
        archetype_lower = archetype.lower()
        card_text = (card.text or "").lower()
        if archetype_lower in card_text:
            score += weights.ARCHETYPE_BONUS
            reasons.append(f"Supports {archetype} strategy")

    # EDHRec popularity bonus (lower rank = more popular)
    if card.edhrec_rank:
        pop_bonus = max(0, 1.0 - card.edhrec_rank / weights.EDHREC_DIVISOR)
        score += pop_bonus
        if pop_bonus > weights.EDHREC_POPULARITY_THRESHOLD:
            reasons.append("Popular in Commander")

    # 17Lands Limited performance bonus
    limited_bonus, tier, is_bomb = score_limited_stats(card.name, gameplay_db, config=config)
    if limited_bonus > 0:
        score += limited_bonus
        if tier in ("S", "A"):
            reasons.append(f"Limited {tier}-tier card")
        if is_bomb:
            reasons.append("Standalone bomb")

    return score, reasons


def score_edhrec_rank(
    rank: int | None,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
) -> float:
    """Convert EDHREC rank to 0-1 score (lower rank = higher score).

    Args:
        rank: EDHREC rank (lower = more popular)
        config: Scoring configuration with thresholds

    Returns:
        Score from 0.0 (unpopular) to 1.0 (very popular)
    """
    if rank is None:
        return config.edhrec_thresholds.UNKNOWN_SCORE
    # Top 1000 commanders = 1.0, rank 30000 = 0.0
    return max(0.0, 1.0 - (rank / config.card_scoring.EDHREC_DIVISOR))


def score_limited_for_commander(
    commander_name: str,
    gameplay_db: GameplayDB,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
) -> float:
    """Get 17Lands-based score for commander (if data exists).

    Args:
        commander_name: Name of the commander
        gameplay_db: GameplayDB instance for data lookup
        config: Scoring configuration with weights

    Returns:
        Score from 0.25 to 1.0 based on Limited tier
    """
    if not gameplay_db.is_available:
        return config.limited_tier_scores.UNKNOWN

    stats = gameplay_db.get_card_stats(commander_name)
    if stats is None:
        return config.limited_tier_scores.UNKNOWN

    return config.limited_tier_scores.get(stats.tier)
