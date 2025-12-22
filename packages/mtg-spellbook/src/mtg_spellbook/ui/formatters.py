"""Shared card formatting utilities."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

from .theme import card_type_colors, rarity_colors, ui_colors

if TYPE_CHECKING:
    pass


class CardLike(Protocol):
    """Protocol for card-like objects (CardSummary, CardDetail, etc.)."""

    name: str
    flavor_name: str | None
    mana_cost: str | None
    rarity: str | None
    set_code: str | None


class CardFormatters:
    """Shared formatting utilities for card display."""

    @staticmethod
    def get_type_icon(card_type: str) -> str:
        """Get icon for card type."""
        type_lower = card_type.lower()
        if "creature" in type_lower:
            return "⚔"
        elif "instant" in type_lower:
            return "⚡"
        elif "sorcery" in type_lower:
            return "📜"
        elif "artifact" in type_lower:
            return "⚙"
        elif "enchantment" in type_lower:
            return "✨"
        elif "planeswalker" in type_lower:
            return "👤"
        elif "land" in type_lower:
            return "🌍"
        return ""

    @staticmethod
    def get_type_color(card_type: str) -> str:
        """Get theme color for card type."""
        type_lower = card_type.lower()
        if "creature" in type_lower:
            return card_type_colors.CREATURE
        elif "instant" in type_lower or "sorcery" in type_lower:
            return card_type_colors.INSTANT
        elif "artifact" in type_lower:
            return card_type_colors.ARTIFACT
        elif "enchantment" in type_lower:
            return card_type_colors.ENCHANTMENT
        elif "planeswalker" in type_lower:
            return card_type_colors.PLANESWALKER
        elif "land" in type_lower:
            return card_type_colors.LAND
        return card_type_colors.DEFAULT

    @staticmethod
    def get_short_type(card_type: str) -> str:
        """Get abbreviated type name."""
        type_lower = card_type.lower()
        if "creature" in type_lower:
            return "Creature"
        elif "instant" in type_lower:
            return "Instant"
        elif "sorcery" in type_lower:
            return "Sorcery"
        elif "artifact" in type_lower:
            return "Artifact"
        elif "enchantment" in type_lower:
            return "Enchant"
        elif "planeswalker" in type_lower:
            return "PW"
        elif "land" in type_lower:
            return "Land"
        return ""

    @staticmethod
    def get_rarity_color(rarity: str | None) -> str:
        """Get color for rarity display."""
        rarity_map = {
            "mythic": rarity_colors.MYTHIC,
            "rare": rarity_colors.RARE,
            "uncommon": rarity_colors.UNCOMMON,
            "common": rarity_colors.COMMON,
        }
        return rarity_map.get((rarity or "").lower(), rarity_colors.DEFAULT)

    @staticmethod
    def get_rarity_symbol(rarity: str | None) -> str:
        """Get symbol for card rarity."""
        symbols = {
            "mythic": "●",
            "rare": "●",
            "uncommon": "●",
            "common": "●",
        }
        return symbols.get((rarity or "").lower(), "●")

    @staticmethod
    def format_result_line(card: CardLike, prettify_mana_fn: Callable[[str], str]) -> str:
        """Format a card for list display with flavor name support.

        Shows flavor name as primary with actual name below if different.
        Used by both main search results and artist gallery.

        Args:
            card: Card-like object with name, flavor_name, mana_cost, rarity, set_code
            prettify_mana_fn: Function to format mana cost string

        Returns:
            Formatted string with Rich markup for display in list
        """
        rarity_color = CardFormatters.get_rarity_color(card.rarity)
        rarity_symbol = CardFormatters.get_rarity_symbol(card.rarity)
        set_code = card.set_code or "???"
        mana_display = prettify_mana_fn(card.mana_cost) if card.mana_cost else ""

        # Use flavor_name as primary display if present
        display_name = card.flavor_name if card.flavor_name else card.name

        # Build first line: rarity symbol, name, mana cost
        line = f"[{rarity_color}]{rarity_symbol}[/] [bold {ui_colors.WHITE}]{display_name}[/]"
        if mana_display:
            line += f"  {mana_display}"

        # Add second line with actual name if flavor_name was used
        if card.flavor_name and card.flavor_name != card.name:
            line += f"\n   [dim]{card.name}[/]  [dim]{set_code.upper()}[/]"
        else:
            line += f"\n   [dim]{set_code.upper()}[/]"

        return line
