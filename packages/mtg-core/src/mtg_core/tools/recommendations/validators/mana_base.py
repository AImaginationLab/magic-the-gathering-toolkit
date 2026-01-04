"""Mana base validation and color source counting for deck analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..constants import BASIC_LAND_NAMES, COLOR_FIXING_REQUIREMENTS
from ..utils.patterns import DUAL_LAND_PATTERNS_COMPILED, matches_any_pattern

if TYPE_CHECKING:
    from ..models import CardData


def count_color_sources(cards: list[CardData], colors: list[str]) -> dict[str, int]:
    """Count mana sources for each color.

    Args:
        cards: List of cards in the deck
        colors: Colors to count sources for

    Returns:
        Dict mapping color to number of sources.
    """
    sources: dict[str, int] = dict.fromkeys(colors, 0)

    for card in cards:
        if not card.type_line or "Land" not in card.type_line:
            continue

        # Check if it's a basic land
        matched_basic = False
        for color, basic_name in BASIC_LAND_NAMES.items():
            if color in colors and basic_name in card.name:
                sources[color] = sources.get(color, 0) + 1
                matched_basic = True
                break

        if not matched_basic:
            # Check dual/multi lands by text
            if card.text:
                text_lower = card.text.lower()
                for color in colors:
                    color_symbol = "{" + color + "}"
                    if (
                        color_symbol.lower() in text_lower
                        or f"add {color_symbol}".lower() in text_lower
                    ):
                        sources[color] = sources.get(color, 0) + 1

            # Check color_identity for lands
            if card.color_identity:
                for color in colors:
                    if color in card.color_identity:
                        sources[color] = sources.get(color, 0) + 1

    return sources


def count_fixing_lands(cards: list[CardData]) -> int:
    """Count lands that provide color fixing (non-basic lands that produce multiple colors).

    Args:
        cards: List of cards in the deck

    Returns:
        Number of color-fixing lands
    """
    fixing_count = 0

    for card in cards:
        if not card.type_line or "Land" not in card.type_line:
            continue

        # Skip basic lands
        if card.type_line and "Basic" in card.type_line:
            continue

        # Check for dual land patterns
        if card.text and matches_any_pattern(card.text, DUAL_LAND_PATTERNS_COMPILED):
            fixing_count += 1
        elif card.color_identity and len(card.color_identity) >= 2:
            # Check if land produces 2+ colors from color_identity
            fixing_count += 1

    return fixing_count


def validate_mana_base(
    cards: list[CardData],
    colors: list[str],
    format_type: str,
) -> tuple[bool, list[str], float]:
    """Validate mana base has adequate color fixing.

    Args:
        cards: List of cards in the deck
        colors: Deck's color identity
        format_type: Format (commander, standard, etc.)

    Returns:
        (is_valid, warnings, score_adjustment)
    """
    num_colors = len(colors)
    if num_colors <= 1:
        return True, [], 0.0  # Mono-color needs no fixing

    warnings: list[str] = []
    score_adj = 0.0

    # Count fixing lands
    fixing_count = count_fixing_lands(cards)
    required = COLOR_FIXING_REQUIREMENTS.get(num_colors, 18)

    if fixing_count < required:
        deficit = required - fixing_count
        warnings.append(
            f"Low color fixing ({fixing_count} dual lands, need {required}+ for {num_colors} colors)"
        )
        score_adj -= 0.3 * (deficit / required)

        # Suggest improvement
        if num_colors >= 3:
            warnings.append("Consider adding: Command Tower, Exotic Orchard, or fetch lands")
    elif fixing_count >= required * 1.2:
        # Bonus for excellent mana base
        score_adj += 0.2

    # Check color distribution
    sources = count_color_sources(cards, colors)

    # Calculate pip requirements (simplified - could be enhanced)
    min_sources_per_color = 10 if format_type == "commander" else 6

    for color, count in sources.items():
        if count < min_sources_per_color:
            warnings.append(
                f"Low {BASIC_LAND_NAMES.get(color, color)} sources ({count}, want {min_sources_per_color}+)"
            )
            score_adj -= 0.1

    is_valid = len(warnings) == 0
    return is_valid, warnings, score_adj
