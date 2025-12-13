"""Shared card formatting utilities."""

from __future__ import annotations

from .theme import card_type_colors


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
