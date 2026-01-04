"""Interaction density validation for deck analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..constants import INTERACTION_MINIMUMS
from ..utils.patterns import matches_interaction

if TYPE_CHECKING:
    from ..models import CardData


def count_interaction(cards: list[CardData]) -> tuple[int, list[str]]:
    """Count interaction spells (removal, counterspells, etc).

    Args:
        cards: List of cards in the deck

    Returns:
        (count, interaction_card_names)
    """
    interaction_cards: list[str] = []

    for card in cards:
        if not card.text:
            continue
        if matches_interaction(card.text):
            interaction_cards.append(card.name)

    return len(interaction_cards), interaction_cards


def validate_interaction_density(
    cards: list[CardData],
    format_type: str,
) -> tuple[bool, list[str], float]:
    """Validate deck has enough interaction (removal/counterspells).

    Args:
        cards: List of cards in the deck
        format_type: Format (commander, standard, etc.)

    Returns:
        (is_valid, warnings, score_adjustment)
    """
    count, _ = count_interaction(cards)
    minimum = INTERACTION_MINIMUMS.get(format_type, 6)

    warnings: list[str] = []
    score_adj = 0.0

    if count < minimum:
        deficit = minimum - count
        warnings.append(f"Low interaction ({count} cards, need {minimum}+)")
        score_adj -= 0.3 * (deficit / minimum)  # Proportional penalty
        return False, warnings, score_adj
    elif count >= minimum * 1.5:
        # Bonus for good interaction density
        score_adj += 0.2

    return True, warnings, score_adj
