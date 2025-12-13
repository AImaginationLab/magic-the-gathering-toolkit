"""Synergy tools - re-exports from synergy subpackage for backward compatibility."""

from .synergy import (
    ABILITY_SYNERGIES,
    KEYWORD_SYNERGIES,
    KNOWN_COMBOS,
    SYNERGY_BASE_SCORES,
    THEME_INDICATORS,
    TYPE_SYNERGIES,
    detect_combos,
    find_synergies,
    suggest_cards,
)

__all__ = [
    "ABILITY_SYNERGIES",
    "KEYWORD_SYNERGIES",
    "KNOWN_COMBOS",
    "SYNERGY_BASE_SCORES",
    "THEME_INDICATORS",
    "TYPE_SYNERGIES",
    "detect_combos",
    "find_synergies",
    "suggest_cards",
]
