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

    # Primary gold colors (brighter)
    GOLD: str = "#FFD700"  # Richer gold for headers
    GOLD_PRIMARY: str = "#FFD700"  # Alias for main gold
    GOLD_DIM: str = "#DAA520"  # Darker gold for supporting elements
    GOLD_SECONDARY: str = "#DAA520"  # Alias for dim gold

    # Base colors
    WHITE: str = "#ffffff"
    GRAY_LIGHT: str = "#888"
    GRAY_MEDIUM: str = "#3d3d3d"
    GRAY_DARK: str = "#1a1a1a"

    # Border colors (updated to match brighter gold)
    BORDER_DEFAULT: str = "#3d3d3d"
    BORDER_FOCUS: str = "#DAA520"
    BORDER_ACTIVE: str = "#FFD700"

    # Background layers (with more depth)
    BACKGROUND_DARK: str = "#0d0d0d"
    BACKGROUND_PANEL: str = "#151515"
    BACKGROUND_HEADER: str = "#0a0a14"
    BACKGROUND_MODAL: str = "#1e1e2e"
    BACKGROUND_HOVER: str = "#2a2a4e"
    BACKGROUND_SELECTED: str = "#2e2e58"
    BACKGROUND_CARD_PRIMARY: str = "#1a1a2e"  # For important cards
    BACKGROUND_CARD_SECONDARY: str = "#151520"  # For standard cards

    # Scrollbar colors (brighter gold)
    SCROLLBAR: str = "#DAA520"
    SCROLLBAR_HOVER: str = "#FFD700"
    SCROLLBAR_ACTIVE: str = "#fff8dc"

    # Text colors
    TEXT_DIM: str = "#888"
    TEXT_ERROR: str = "#FF4444"  # Vibrant red

    # Status colors (more distinctive)
    SUCCESS: str = "#00FF00"  # Bright green
    WARNING: str = "#FFA500"  # True orange
    ERROR: str = "#FF4444"  # Vibrant red
    INFO: str = "#4A9FD8"  # Bright blue

    # Synergy colors (brighter)
    SYNERGY_STRONG: str = "#32FF32"  # Brighter green
    SYNERGY_MODERATE: str = "#FFD700"  # Bright yellow/gold
    SYNERGY_WEAK: str = "#FFA500"  # Bright orange

    # Tier colors (for ratings)
    TIER_S: str = "#FFD700"  # Bright gold
    TIER_A: str = "#32CD32"  # Bright green
    TIER_B: str = "#87CEEB"  # Bright blue
    TIER_C: str = "#FFA500"  # Orange
    TIER_D: str = "#FF6B6B"  # Soft red
    TIER_F: str = "#888888"  # Gray

    # Price colors
    PRICE_HIGH: str = "#FFA500"  # Orange
    PRICE_MEDIUM: str = "#FFFF00"  # Yellow
    PRICE_LOW: str = "#00FF00"  # Green


mtg_colors = MTGColors()
card_type_colors = CardTypeColors()
rarity_colors = RarityColors()
ui_colors = UIColors()


def get_price_color(price: float | None) -> str:
    """Get color for price display based on value tier."""
    if price is None:
        return ui_colors.TEXT_DIM
    if price >= 100:
        return ui_colors.TEXT_ERROR
    elif price >= 20:
        return ui_colors.PRICE_HIGH
    elif price >= 5:
        return ui_colors.PRICE_MEDIUM
    return ui_colors.PRICE_LOW


def get_rarity_style(rarity: str) -> tuple[str, str]:
    """Get icon and color for rarity display.

    Args:
        rarity: Card rarity string (common, uncommon, rare, mythic, special, bonus)

    Returns:
        Tuple of (icon, color) for rich text formatting
    """
    rarity_styles = {
        "common": ("●", rarity_colors.COMMON),
        "uncommon": ("◆", rarity_colors.UNCOMMON),
        "rare": ("♦", rarity_colors.RARE),
        "mythic": ("★", rarity_colors.MYTHIC),
        "special": ("✦", rarity_colors.MYTHIC),
        "bonus": ("✧", rarity_colors.RARE),
    }
    return rarity_styles.get(rarity.lower(), ("○", rarity_colors.DEFAULT))


def get_name_color_for_rarity(rarity: str | None) -> str:
    """Get text color for card name based on rarity.

    Args:
        rarity: Card rarity string or None

    Returns:
        Color hex code for rich text formatting
    """
    rarity_lower = (rarity or "").lower()
    if rarity_lower == "mythic":
        return rarity_colors.MYTHIC
    elif rarity_lower == "rare":
        return rarity_colors.RARE
    return ui_colors.WHITE


def get_synergy_score_color(score: float) -> str:
    """Get color for synergy score display.

    Args:
        score: Synergy score between 0.0 and 1.0

    Returns:
        Color for rich text formatting
    """
    if score >= 0.7:
        return ui_colors.SYNERGY_STRONG
    elif score >= 0.4:
        return ui_colors.SYNERGY_MODERATE
    return ui_colors.SYNERGY_WEAK
