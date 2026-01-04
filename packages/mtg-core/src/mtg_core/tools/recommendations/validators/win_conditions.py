"""Win condition detection and validation for deck analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..constants import WIN_CONDITION_THRESHOLDS
from ..utils.patterns import WIN_CONDITION_PATTERNS_COMPILED

if TYPE_CHECKING:
    from ..models import CardData


def detect_win_conditions(cards: list[CardData], _combo_count: int = 0) -> dict[str, list[str]]:
    """Detect win conditions in the deck.

    Args:
        cards: List of cards in the deck
        _combo_count: Number of combos detected (for future use)

    Returns:
        Dict mapping win condition type to list of card names.
    """
    win_cons: dict[str, list[str]] = {key: [] for key in WIN_CONDITION_PATTERNS_COMPILED}

    for card in cards:
        if not card.text:
            continue
        text_lower = card.text.lower()
        type_lower = (card.type_line or "").lower()

        for win_type, patterns in WIN_CONDITION_PATTERNS_COMPILED.items():
            for pattern in patterns:
                if pattern.search(text_lower) or pattern.search(type_lower):
                    win_cons[win_type].append(card.name)
                    break

    return win_cons


def validate_win_conditions(
    cards: list[CardData],
    format_type: str,
    archetype: str | None,
    combo_count: int,
) -> tuple[bool, list[str], float, list[str]]:
    """Validate deck has viable win conditions.

    Args:
        cards: List of cards in the deck
        format_type: Format (commander, standard, etc.)
        archetype: Optional archetype
        combo_count: Number of combos detected

    Returns:
        (is_valid, warnings, score_adjustment, win_condition_types)
    """
    win_cons = detect_win_conditions(cards, combo_count)

    key = f"{format_type}_{archetype}" if archetype else format_type
    thresholds = WIN_CONDITION_THRESHOLDS.get(key, WIN_CONDITION_THRESHOLDS.get(format_type, {}))

    warnings: list[str] = []
    score_adj = 0.0
    has_win_con = False
    win_con_types: list[str] = []

    # Check combo win condition
    if combo_count >= thresholds.get("combo_min", 1):
        has_win_con = True
        score_adj += 0.3
        win_con_types.append("combo")

    # Check evasion
    evasion_count = len(win_cons.get("evasion", []))
    if evasion_count >= thresholds.get("evasion_min", 6):
        has_win_con = True
        score_adj += 0.2
        win_con_types.append("evasion")
    elif evasion_count < 4 and format_type != "standard_control":
        warnings.append(f"Low evasion ({evasion_count} cards)")

    # Check finishers
    finisher_count = len(win_cons.get("finisher", []))
    if finisher_count >= thresholds.get("finisher_min", 2):
        has_win_con = True
        score_adj += 0.2
        win_con_types.append("finisher")

    # Check value engines (for control)
    value_count = len(win_cons.get("value_engine", []))
    if value_count >= thresholds.get("value_engine_min", 5):
        score_adj += 0.1
        win_con_types.append("value_engine")

    if not has_win_con and combo_count == 0:
        warnings.append("No clear win condition detected")
        score_adj -= 0.4

    return has_win_con, warnings, score_adj, win_con_types
