"""Synergy and strategy tools for MTG deck building."""

from .constants import (
    ABILITY_SYNERGIES,
    KEYWORD_SYNERGIES,
    KNOWN_COMBOS,
    SYNERGY_BASE_SCORES,
    THEME_INDICATORS,
    TYPE_SYNERGIES,
)
from .detection import (
    combo_to_model,
    detect_deck_colors,
    detect_themes,
    find_combos_for_card,
    find_combos_in_deck,
)
from .scoring import (
    calculate_synergy_score,
    card_has_pattern,
    create_synergy_result,
    normalize_card_name,
)
from .search import search_synergies
from .tools import detect_combos, find_synergies, suggest_cards

__all__ = [
    "ABILITY_SYNERGIES",
    "KEYWORD_SYNERGIES",
    "KNOWN_COMBOS",
    "SYNERGY_BASE_SCORES",
    "THEME_INDICATORS",
    "TYPE_SYNERGIES",
    "calculate_synergy_score",
    "card_has_pattern",
    "combo_to_model",
    "create_synergy_result",
    "detect_combos",
    "detect_deck_colors",
    "detect_themes",
    "find_combos_for_card",
    "find_combos_in_deck",
    "find_synergies",
    "normalize_card_name",
    "search_synergies",
    "suggest_cards",
]
