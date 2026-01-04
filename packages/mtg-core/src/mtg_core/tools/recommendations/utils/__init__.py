"""Utility functions for deck recommendations."""

from .colors import (
    color_fits_identity,
    colors_intersect,
    get_color_name,
)
from .patterns import (
    CARD_ADVANTAGE_PATTERNS_COMPILED,
    DUAL_LAND_PATTERNS_COMPILED,
    INTERACTION_PATTERNS_COMPILED,
    LORD_PATTERNS_COMPILED,
    MANA_ROCK_PATTERN,
    RAMP_PATTERNS_COMPILED,
    WIN_CONDITION_PATTERNS_COMPILED,
    matches_any_pattern,
    matches_card_advantage,
    matches_interaction,
    matches_lord_for_type,
    matches_ramp,
    matches_win_condition,
)

__all__ = [
    "CARD_ADVANTAGE_PATTERNS_COMPILED",
    "DUAL_LAND_PATTERNS_COMPILED",
    "INTERACTION_PATTERNS_COMPILED",
    "LORD_PATTERNS_COMPILED",
    "MANA_ROCK_PATTERN",
    "RAMP_PATTERNS_COMPILED",
    "WIN_CONDITION_PATTERNS_COMPILED",
    "color_fits_identity",
    "colors_intersect",
    "get_color_name",
    "matches_any_pattern",
    "matches_card_advantage",
    "matches_interaction",
    "matches_lord_for_type",
    "matches_ramp",
    "matches_win_condition",
]
