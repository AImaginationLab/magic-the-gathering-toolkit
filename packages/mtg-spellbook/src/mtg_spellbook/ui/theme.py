"""MTG color theme constants.

Centralized color definitions for consistent theming across the UI.
All hex color codes should be defined here to avoid duplication.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MTGColors:
    """MTG mana color hex codes."""

    WHITE: str = "#F0E68C"
    BLUE: str = "#0E86D4"
    BLACK: str = "#2C3639"
    RED: str = "#C7253E"
    GREEN: str = "#1A5D1A"
    COLORLESS: str = "#95a5a6"
    MULTICOLOR: str = "#FFD700"


@dataclass(frozen=True)
class CardTypeColors:
    """Colors for card type display."""

    CREATURE: str = "#7ec850"
    INSTANT: str = "#4a9fd8"
    SORCERY: str = "#4a9fd8"
    ARTIFACT: str = "#9a9a9a"
    ENCHANTMENT: str = "#b86fce"
    PLANESWALKER: str = "#e6c84a"
    LAND: str = "#a67c52"
    DEFAULT: str = "#888"


@dataclass(frozen=True)
class RarityColors:
    """Colors for rarity display."""

    MYTHIC: str = "#e65c00"
    RARE: str = "#c9a227"
    UNCOMMON: str = "#c0c0c0"
    COMMON: str = "#888"
    DEFAULT: str = "#666"


@dataclass(frozen=True)
class UIColors:
    """General UI theme colors."""

    GOLD: str = "#e6c84a"
    GOLD_DIM: str = "#c9a227"
    WHITE: str = "#ffffff"
    GRAY_LIGHT: str = "#888"
    GRAY_MEDIUM: str = "#3d3d3d"
    GRAY_DARK: str = "#1a1a1a"
    BORDER_DEFAULT: str = "#3d3d3d"
    BORDER_FOCUS: str = "#c9a227"
    BORDER_ACTIVE: str = "#e6c84a"
    BACKGROUND_DARK: str = "#0d0d0d"
    BACKGROUND_PANEL: str = "#151515"
    BACKGROUND_HEADER: str = "#0a0a14"
    BACKGROUND_MODAL: str = "#1e1e2e"
    BACKGROUND_HOVER: str = "#2a2a4e"
    BACKGROUND_SELECTED: str = "#2e2e58"
    SCROLLBAR: str = "#c9a227"
    SCROLLBAR_HOVER: str = "#e6c84a"
    SCROLLBAR_ACTIVE: str = "#fff8dc"
    TEXT_DIM: str = "#888"
    TEXT_ERROR: str = "#ff6b6b"
    SYNERGY_STRONG: str = "#00ff00"
    SYNERGY_MODERATE: str = "#c9a227"
    SYNERGY_WEAK: str = "#e6c84a"


mtg_colors = MTGColors()
card_type_colors = CardTypeColors()
rarity_colors = RarityColors()
ui_colors = UIColors()
