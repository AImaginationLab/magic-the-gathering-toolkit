"""MTG deck fundamentals: lords, ramp, card advantage, and theme assessment."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..constants import (
    CARD_ADVANTAGE_MINIMUMS,
    RAMP_THRESHOLDS,
    THEME_THRESHOLD_STRONG,
    THEME_THRESHOLD_VIABLE,
    THEME_THRESHOLD_WEAK,
    TRIBAL_THRESHOLD_STRONG,
    TRIBAL_THRESHOLD_VIABLE,
    TRIBAL_THRESHOLD_WEAK,
)
from ..utils.patterns import (
    MANA_ROCK_PATTERN,
    matches_card_advantage,
    matches_lord_for_type,
    matches_ramp,
)

if TYPE_CHECKING:
    from ..models import CardData


def count_tribal_lords(cards: list[CardData], creature_type: str) -> tuple[int, list[str]]:
    """Count tribal lords that buff a specific creature type.

    Lords are cards that buff other creatures of a type but may not
    be that type themselves (e.g., "Other Zombies get +1/+1").

    Args:
        cards: List of cards in the deck
        creature_type: The creature type to check for lords

    Returns:
        (lord_count, lord_names)
    """
    lord_count = 0
    lord_names: list[str] = []

    for card in cards:
        if not card.text:
            continue
        if matches_lord_for_type(card.text, creature_type):
            lord_count += 1
            lord_names.append(card.name)

    return lord_count, lord_names


def count_ramp_sources(cards: list[CardData]) -> tuple[int, list[str]]:
    """Count mana ramp sources in the deck.

    Args:
        cards: List of cards in the deck

    Returns:
        (ramp_count, ramp_card_names)
    """
    ramp_count = 0
    ramp_names: list[str] = []

    for card in cards:
        # Check type line for mana rocks
        if (
            card.type_line
            and "artifact" in card.type_line.lower()
            and card.text
            and MANA_ROCK_PATTERN.search(card.text)
        ):
            ramp_count += 1
            ramp_names.append(card.name)
            continue

        # Check card text for ramp patterns
        if not card.text:
            continue
        if matches_ramp(card.text):
            ramp_count += 1
            ramp_names.append(card.name)

    return ramp_count, ramp_names


def count_card_advantage(cards: list[CardData]) -> tuple[int, dict[str, int]]:
    """Count card advantage sources by type.

    Args:
        cards: List of cards in the deck

    Returns:
        (total_count, breakdown_by_type)
    """
    counts: dict[str, int] = {"draw": 0, "selection": 0, "recursion": 0}

    for card in cards:
        if not card.text:
            continue

        matches = matches_card_advantage(card.text)
        for advantage_type, matched in matches.items():
            if matched:
                counts[advantage_type] += 1

    total = sum(counts.values())
    return total, counts


def validate_ramp_sufficiency(
    cards: list[CardData],
    avg_cmc: float,
    format_type: str = "commander",
) -> tuple[bool, list[str], float]:
    """Validate that the deck has sufficient ramp for its mana curve.

    Args:
        cards: List of cards in the deck
        avg_cmc: Average converted mana cost of non-land cards
        format_type: Format (commander, standard, etc.)

    Returns:
        (is_sufficient, warnings, score_adjustment)
    """
    ramp_count, _ = count_ramp_sources(cards)
    thresholds = RAMP_THRESHOLDS.get(format_type, RAMP_THRESHOLDS["commander"])

    warnings: list[str] = []
    score_adj = 0.0

    # Determine required ramp based on average CMC
    if avg_cmc > 3.5:
        required = thresholds["high_cmc"]
        level = "high"
    elif avg_cmc >= 3.0:
        required = thresholds["medium_cmc"]
        level = "medium"
    else:
        required = thresholds["low_cmc"]
        level = "low"

    if ramp_count < required:
        deficit = required - ramp_count
        warnings.append(
            f"Only {ramp_count} ramp sources for {level} CMC deck (recommend {required}+)"
        )
        # Penalty scales with deficit
        score_adj = -0.1 * min(deficit, 5)
        return False, warnings, score_adj

    # Bonus for exceeding ramp requirements significantly
    if ramp_count >= required * 1.5:
        score_adj = 0.1
    return True, warnings, score_adj


def validate_card_advantage(
    cards: list[CardData],
    archetype: str | None,
    format_type: str = "commander",
) -> tuple[bool, list[str], float]:
    """Validate card advantage sources by archetype.

    Control and combo decks need more draw than aggro.

    Args:
        cards: List of cards in the deck
        archetype: Deck archetype (control, aggro, combo, etc.)
        format_type: Format (commander, standard, etc.)

    Returns:
        (is_sufficient, warnings, score_adjustment)
    """
    total_ca, _breakdown = count_card_advantage(cards)

    # Determine archetype style
    style = "midrange"  # default
    if archetype:
        arch_lower = archetype.lower()
        if any(x in arch_lower for x in ["control", "stax"]):
            style = "control"
        elif any(x in arch_lower for x in ["aggro", "voltron"]):
            style = "aggro"
        elif "combo" in arch_lower:
            style = "combo"

    key = f"{format_type}_{style}"
    minimum = CARD_ADVANTAGE_MINIMUMS.get(key, 6)

    warnings: list[str] = []
    score_adj = 0.0

    if total_ca < minimum:
        deficit = minimum - total_ca
        warnings.append(
            f"Only {total_ca} card advantage sources for {style} (recommend {minimum}+)"
        )
        score_adj = -0.1 * min(deficit, 4)
        return False, warnings, score_adj

    # Bonus for healthy card advantage
    if total_ca >= minimum * 1.5:
        score_adj = 0.1
    return True, warnings, score_adj


def assess_tribal_strength(
    _creature_type: str, count: int, lord_count: int = 0
) -> tuple[str, float]:
    """Assess tribal theme strength.

    Lords count as 2 creatures for tribal density, as they provide
    crucial tribal synergy beyond just being a body.

    Args:
        _creature_type: The creature type (unused, for future expansion)
        count: Number of creatures of this type
        lord_count: Number of lords for this type

    Returns:
        (strength_label, score_modifier)
    """
    # Lords count double for tribal density calculations
    effective_count = count + lord_count

    if effective_count >= TRIBAL_THRESHOLD_STRONG:
        return "strong", 0.3
    elif effective_count >= TRIBAL_THRESHOLD_VIABLE:
        return "viable", 0.1
    elif effective_count >= TRIBAL_THRESHOLD_WEAK:
        return "weak", 0.0
    else:
        return "minimal", -0.2


def assess_theme_strength(_theme: str, supporting_cards: int) -> tuple[str, float]:
    """Assess theme strength.

    Args:
        _theme: The theme (unused, for future expansion)
        supporting_cards: Number of cards supporting this theme

    Returns:
        (strength_label, score_modifier)
    """
    if supporting_cards >= THEME_THRESHOLD_STRONG:
        return "strong", 0.3
    elif supporting_cards >= THEME_THRESHOLD_VIABLE:
        return "viable", 0.1
    elif supporting_cards >= THEME_THRESHOLD_WEAK:
        return "weak", 0.0
    else:
        return "minimal", -0.2
