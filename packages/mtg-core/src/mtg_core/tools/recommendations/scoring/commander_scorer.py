"""Commander scoring functions for deck recommendations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..constants import THEME_KEYWORDS
from .weights import DEFAULT_SCORING_CONFIG, ScoringConfig

if TYPE_CHECKING:
    from ..features import CardEncoder
    from ..models import CardData, CommanderMatch


def score_theme_match(
    oracle_text: str,
    archetype: str | None = None,
    tribe: str | None = None,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
) -> float:
    """Score how well commander matches the requested theme.

    Args:
        oracle_text: Commander's oracle text
        archetype: Optional archetype to match (e.g., "sacrifice", "tokens")
        tribe: Optional creature type to match (e.g., "zombie", "elf")
        config: Scoring configuration with weights

    Returns:
        Score from 0.0 to 1.0 indicating theme match strength
    """
    weights = config.theme_match
    score = 0.0
    text_lower = oracle_text.lower()

    # Tribal matching
    if tribe:
        tribe_lower = tribe.lower()
        if tribe_lower in text_lower:
            score += weights.TRIBE_TEXT_MATCH
        # Check for tribal lord patterns
        if f"other {tribe_lower}" in text_lower:
            score += weights.TRIBE_LORD_PATTERN
        if f"{tribe_lower}s you control" in text_lower:
            score += weights.TRIBE_CONTROL_PATTERN

    # Archetype matching
    if archetype and archetype in THEME_KEYWORDS:
        keywords = THEME_KEYWORDS[archetype]
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        score += min(weights.ARCHETYPE_MAX_BONUS, matches * weights.ARCHETYPE_KEYWORD_BONUS)

    return min(1.0, score)


def score_commander_combos(
    commander_name: str,
    collection_names: set[str],
    combo_detector: Any,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
) -> tuple[float, int]:
    """Score combo potential using SpellbookComboDetector.

    Args:
        commander_name: Name of the commander
        collection_names: Set of card names in user's collection
        combo_detector: SpellbookComboDetector instance
        config: Scoring configuration with weights

    Returns:
        Tuple of (combo_score, combo_count) where:
        - combo_score: 0.0 to 1.0 based on combo quality and ownership
        - combo_count: Total number of combos found
    """
    if not combo_detector.is_available:
        return 0.0, 0

    # Find all combos containing this commander
    combos = combo_detector.find_combos_for_card(commander_name, limit=50)

    if not combos:
        return 0.0, 0

    combo_count = len(combos)
    score = 0.0
    weights = config.combo_bracket

    # Score based on bracket quality and ownership
    for combo in combos[:20]:  # Top 20 by popularity
        # Bracket quality (R > S > P > C)
        bracket_score = weights.get(combo.bracket_tag)

        # Ownership - how many pieces does user have?
        owned_pieces = sum(1 for c in combo.card_names if c in collection_names)
        ownership_ratio = owned_pieces / len(combo.card_names) if combo.card_names else 0

        # Weighted contribution
        score += bracket_score * weights.BRACKET_WEIGHT + ownership_ratio * weights.OWNERSHIP_WEIGHT

    # Normalize to 0-1
    return min(1.0, score / weights.NORMALIZE_DIVISOR), combo_count


def score_commander_synergy(
    commander_data: dict[str, Any],
    collection: list[CardData] | None,
    card_encoder: CardEncoder,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
) -> tuple[float, list[str]]:
    """Score synergy between commander and user's collection.

    Args:
        commander_data: Dict with commander info (name, type_line, oracle_text, color_identity)
        collection: User's card collection
        card_encoder: CardEncoder for feature extraction
        config: Scoring configuration with weights

    Returns:
        Tuple of (synergy_score, top_synergy_cards) where:
        - synergy_score: 0.0 to 1.0 based on collection synergy
        - top_synergy_cards: Names of top synergistic cards owned
    """
    if not collection:
        return 0.0, []

    weights = config.synergy

    # Get commander's color identity
    cmd_identity = set(commander_data.get("color_identity") or [])

    # Filter collection to cards that fit commander's colors
    compatible_cards = [
        c
        for c in collection
        if set(c.get_color_identity()).issubset(cmd_identity) or not c.get_color_identity()
    ]

    if not compatible_cards:
        return 0.0, []

    # Get commander features
    cmd_dict = {
        "name": commander_data["name"],
        "type": commander_data.get("type_line", ""),
        "text": commander_data.get("oracle_text", ""),
    }
    cmd_features = card_encoder.encode(cmd_dict)

    # Score each compatible card for synergy
    synergy_scores: list[tuple[float, str]] = []
    for card in compatible_cards[:100]:  # Limit for performance
        card_dict = card.to_encoder_dict()
        card_features = card_encoder.encode(card_dict)

        # Check theme overlap
        theme_overlap = len(cmd_features.synergy_themes & card_features.synergy_themes)
        subtype_overlap = len(set(cmd_features.subtypes) & set(card_features.subtypes))

        card_score = (
            theme_overlap * weights.THEME_OVERLAP + subtype_overlap * weights.SUBTYPE_OVERLAP
        )
        if card_score > 0:
            synergy_scores.append((card_score, card.name))

    # Sort and get top synergy cards
    synergy_scores.sort(reverse=True)
    top_synergy_cards = [name for _, name in synergy_scores[:5]]

    # Overall synergy score
    total_synergy = sum(s for s, _ in synergy_scores)
    normalized = min(1.0, total_synergy / weights.SYNERGY_NORMALIZE_DIVISOR)

    return normalized, top_synergy_cards


def calculate_commander_total_score(
    match: CommanderMatch,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
) -> float:
    """Calculate weighted total score for commander.

    Args:
        match: CommanderMatch with individual scores
        config: Scoring configuration with commander weights

    Returns:
        Total score from 0.0 to 1.0
    """
    weights = config.commander

    total = (
        match.edhrec_score * weights.EDHREC
        + match.theme_score * weights.THEME
        + match.combo_score * weights.COMBO
        + match.synergy_score * weights.SYNERGY
        + match.limited_score * weights.LIMITED
        + match.ownership_bonus * weights.OWNERSHIP
    )

    return min(1.0, total)


def generate_commander_reasons(
    match: CommanderMatch,
    archetype: str | None,
    tribe: str | None,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
) -> list[str]:
    """Generate human-readable reasons for commander score.

    Args:
        match: CommanderMatch with scores
        archetype: Optional archetype filter
        tribe: Optional tribal filter
        config: Scoring configuration with thresholds

    Returns:
        List of human-readable reason strings
    """
    reasons: list[str] = []
    thresholds = config.edhrec_thresholds

    if match.is_owned:
        reasons.append("You own this commander")

    if match.edhrec_rank and match.edhrec_rank < thresholds.TOP_COMMANDER:
        reasons.append(f"Top EDHREC commander (#{match.edhrec_rank})")
    elif match.edhrec_rank and match.edhrec_rank < thresholds.POPULAR_COMMANDER:
        reasons.append(f"Popular commander (#{match.edhrec_rank})")

    if match.theme_score >= 0.5:
        if tribe:
            reasons.append(f"Strong {tribe} tribal synergy")
        if archetype:
            reasons.append(f"Strong {archetype} theme match")

    if match.combo_count > 5:
        reasons.append(f"Enables {match.combo_count} combos")
    elif match.combo_count > 0:
        reasons.append(f"Enables {match.combo_count} combo(s)")

    if match.synergy_cards:
        reasons.append(f"Synergizes with: {', '.join(match.synergy_cards[:3])}")

    return reasons
