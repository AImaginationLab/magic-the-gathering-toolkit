"""Mana curve validation for deck analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..constants import CURVE_THRESHOLDS

if TYPE_CHECKING:
    from ..models import CardData


def validate_mana_curve(
    cards: list[CardData],
    format_type: str,
    archetype: str | None = None,
) -> tuple[bool, list[str], float]:
    """Validate mana curve is healthy for the format/archetype.

    Args:
        cards: List of cards in the deck
        format_type: Format (commander, standard, etc.)
        archetype: Optional archetype (aggro, control, etc.)

    Returns:
        (is_valid, warnings, score_adjustment)
    """
    warnings: list[str] = []
    score_adj = 0.0

    # Calculate average CMC (excluding lands)
    non_lands = [c for c in cards if c.type_line and "Land" not in c.type_line]
    if not non_lands:
        return True, [], 0.0

    cmcs: list[int] = []
    for card in non_lands:
        cmc = card.get_cmc()
        cmcs.append(cmc)

    if not cmcs:
        return True, [], 0.0

    avg_cmc = sum(cmcs) / len(cmcs)
    low_cmc_count = sum(1 for c in cmcs if c <= 2)
    low_cmc_ratio = low_cmc_count / len(cmcs)

    # Get thresholds based on format/archetype
    key = f"{format_type}_{archetype}" if archetype else format_type
    thresholds = CURVE_THRESHOLDS.get(
        key, CURVE_THRESHOLDS.get(format_type, CURVE_THRESHOLDS["commander"])
    )

    is_valid = True

    if avg_cmc > thresholds["avg_cmc_max"]:
        is_valid = False
        warnings.append(f"High avg CMC ({avg_cmc:.1f} > {thresholds['avg_cmc_max']})")
        score_adj -= 0.5

    if low_cmc_ratio < thresholds["low_cmc_ratio_min"]:
        warnings.append(
            f"Low early game ({low_cmc_ratio:.0%} < "
            f"{thresholds['low_cmc_ratio_min']:.0%} at CMC 1-2)"
        )
        score_adj -= 0.3

    return is_valid, warnings, score_adj


def calculate_average_cmc(cards: list[CardData]) -> float:
    """Calculate average converted mana cost of non-land cards.

    Args:
        cards: List of cards in the deck

    Returns:
        Average CMC, or 0.0 if no non-land cards
    """
    non_lands = [c for c in cards if c.type_line and "Land" not in c.type_line]
    if not non_lands:
        return 0.0

    cmcs = [card.get_cmc() for card in non_lands]
    return sum(cmcs) / len(cmcs) if cmcs else 0.0
