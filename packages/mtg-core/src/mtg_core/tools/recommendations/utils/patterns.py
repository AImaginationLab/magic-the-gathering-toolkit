"""Pre-compiled regex patterns for deck analysis.

Compiles patterns at module load time for better performance.
All matching functions operate on lowercase text.
"""

from __future__ import annotations

import re
from re import Pattern

from ..constants import (
    CARD_ADVANTAGE_PATTERNS,
    DUAL_LAND_PATTERNS,
    INTERACTION_PATTERNS,
    LORD_PATTERNS,
    RAMP_PATTERNS,
    WIN_CONDITION_PATTERNS,
)

# Pre-compile all pattern lists
INTERACTION_PATTERNS_COMPILED: list[Pattern[str]] = [
    re.compile(p, re.IGNORECASE) for p in INTERACTION_PATTERNS
]

DUAL_LAND_PATTERNS_COMPILED: list[Pattern[str]] = [
    re.compile(p, re.IGNORECASE) for p in DUAL_LAND_PATTERNS
]

LORD_PATTERNS_COMPILED: list[Pattern[str]] = [re.compile(p, re.IGNORECASE) for p in LORD_PATTERNS]

RAMP_PATTERNS_COMPILED: list[Pattern[str]] = [re.compile(p, re.IGNORECASE) for p in RAMP_PATTERNS]

# Win condition patterns by type
WIN_CONDITION_PATTERNS_COMPILED: dict[str, list[Pattern[str]]] = {
    win_type: [re.compile(p, re.IGNORECASE) for p in patterns]
    for win_type, patterns in WIN_CONDITION_PATTERNS.items()
}

# Card advantage patterns by type
CARD_ADVANTAGE_PATTERNS_COMPILED: dict[str, list[Pattern[str]]] = {
    adv_type: [re.compile(p, re.IGNORECASE) for p in patterns]
    for adv_type, patterns in CARD_ADVANTAGE_PATTERNS.items()
}

# Mana rock pattern for artifact ramp detection
MANA_ROCK_PATTERN: Pattern[str] = re.compile(r"add \{[WUBRGC]\}", re.IGNORECASE)


def matches_any_pattern(text: str, patterns: list[Pattern[str]]) -> bool:
    """Check if text matches any of the pre-compiled patterns."""
    return any(pattern.search(text) for pattern in patterns)


def matches_interaction(text: str) -> bool:
    """Check if text contains interaction keywords (removal, counterspells, etc.)."""
    return matches_any_pattern(text, INTERACTION_PATTERNS_COMPILED)


def matches_ramp(text: str) -> bool:
    """Check if text contains ramp patterns."""
    return matches_any_pattern(text, RAMP_PATTERNS_COMPILED)


def matches_lord_for_type(text: str, creature_type: str) -> bool:
    """Check if text indicates a lord effect for a specific creature type.

    Args:
        text: Card oracle text (will be lowercased)
        creature_type: The creature type to check for (e.g., "zombie")

    Returns:
        True if the card appears to be a lord for this creature type.
    """
    text_lower = text.lower()
    type_lower = creature_type.lower()

    # First check if any lord pattern matches
    for pattern in LORD_PATTERNS_COMPILED:
        if pattern.search(text_lower):
            # Verify it references the creature type
            type_pattern = re.compile(rf"(other |another )?{type_lower}", re.IGNORECASE)
            if type_pattern.search(text_lower):
                return True
    return False


def matches_win_condition(text: str, type_line: str = "") -> dict[str, bool]:
    """Check which win condition types match the text.

    Args:
        text: Card oracle text
        type_line: Card type line (optional, for additional matching)

    Returns:
        Dict mapping win condition type to whether it matches.
    """
    text_lower = text.lower()
    type_lower = type_line.lower()

    results: dict[str, bool] = {}
    for win_type, patterns in WIN_CONDITION_PATTERNS_COMPILED.items():
        matched = False
        for pattern in patterns:
            if pattern.search(text_lower) or (type_lower and pattern.search(type_lower)):
                matched = True
                break
        results[win_type] = matched
    return results


def matches_card_advantage(text: str) -> dict[str, bool]:
    """Check which card advantage types match the text.

    Args:
        text: Card oracle text

    Returns:
        Dict mapping advantage type (draw, selection, recursion) to whether it matches.
    """
    text_lower = text.lower()

    results: dict[str, bool] = {}
    for adv_type, patterns in CARD_ADVANTAGE_PATTERNS_COMPILED.items():
        matched = False
        for pattern in patterns:
            if pattern.search(text_lower):
                matched = True
                break
        results[adv_type] = matched
    return results
