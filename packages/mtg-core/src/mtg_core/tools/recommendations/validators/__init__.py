"""Deck validation functions for MTG deck analysis."""

from .interaction import count_interaction, validate_interaction_density
from .mana_base import count_color_sources, count_fixing_lands, validate_mana_base
from .mana_curve import calculate_average_cmc, validate_mana_curve
from .mtg_fundamentals import (
    assess_theme_strength,
    assess_tribal_strength,
    count_card_advantage,
    count_ramp_sources,
    count_tribal_lords,
    validate_card_advantage,
    validate_ramp_sufficiency,
)
from .win_conditions import detect_win_conditions, validate_win_conditions

__all__ = [
    "assess_theme_strength",
    "assess_tribal_strength",
    "calculate_average_cmc",
    "count_card_advantage",
    "count_color_sources",
    "count_fixing_lands",
    "count_interaction",
    "count_ramp_sources",
    "count_tribal_lords",
    "detect_win_conditions",
    "validate_card_advantage",
    "validate_interaction_density",
    "validate_mana_base",
    "validate_mana_curve",
    "validate_ramp_sufficiency",
    "validate_win_conditions",
]
