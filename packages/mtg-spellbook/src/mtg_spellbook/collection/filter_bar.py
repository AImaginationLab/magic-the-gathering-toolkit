"""Filter bar widget for collection filtering."""

from __future__ import annotations

from enum import Enum
from typing import ClassVar

from textual.widgets import Static

from ..ui.theme import ui_colors


class SortOrder(Enum):
    """Sort order options for collection."""

    NAME_ASC = "name"
    CMC_ASC = "cmc"
    TYPE_ASC = "type"
    QUANTITY_DESC = "quantity"
    RECENT = "recent"


# MTG-themed type icons
TYPE_ICONS: dict[str, str] = {
    "all": "◈",
    "creature": "👹",
    "instant": "⚡",
    "sorcery": "✨",
    "artifact": "⚙️",
    "enchantment": "🔮",
    "planeswalker": "🌟",
    "land": "🏔️",
}

# Type colors (matching card frame colors loosely)
TYPE_COLORS: dict[str, str] = {
    "all": ui_colors.GOLD,
    "creature": "#7ec850",  # Green-ish for creatures
    "instant": "#6eb5ff",  # Blue for instants
    "sorcery": "#e57373",  # Red-ish for sorceries
    "artifact": "#b0bec5",  # Gray for artifacts
    "enchantment": "#ce93d8",  # Purple for enchantments
    "planeswalker": "#ffb74d",  # Orange/gold for planeswalkers
    "land": "#8d6e63",  # Brown for lands
}


class CollectionTypeIndex(Static):
    """Type filter pills for collection with MTG-themed icons."""

    TYPE_KEYS: ClassVar[dict[str, str]] = {
        "all": "a",
        "creature": "c",
        "instant": "i",
        "sorcery": "s",
        "artifact": "t",  # arTifact (t to avoid conflict with 'r' for red color)
        "enchantment": "e",
        "planeswalker": "p",
        "land": "l",
    }

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._type_counts: dict[str, int] = {}
        self._active_type: str = "all"

    def update_counts(self, counts: dict[str, int], active: str = "all") -> None:
        """Update type counts and active filter."""
        self._type_counts = counts
        self._active_type = active
        self.update(self._render_index())

    def _render_index(self) -> str:
        """Render horizontal filter pills with icons and colors."""
        types = [
            ("all", "All"),
            ("creature", "Crt"),
            ("instant", "Ins"),
            ("sorcery", "Src"),
            ("artifact", "Art"),
            ("enchantment", "Enc"),
            ("planeswalker", "Pw"),
            ("land", "Lnd"),
        ]

        pills = []
        for type_key, label in types:
            count = self._type_counts.get(type_key, 0)
            key = self.TYPE_KEYS.get(type_key, "")
            icon = TYPE_ICONS.get(type_key, "")
            color = TYPE_COLORS.get(type_key, ui_colors.TEXT_DIM)

            if type_key == self._active_type:
                # Active: highlighted with background
                pills.append(f"[bold {ui_colors.GOLD} on #2a2a4e]{key}:{icon}{label}({count})[/]")
            elif count > 0:
                # Has items: colored
                pills.append(f"[{color}]{key}:{icon}{label}[/][dim]({count})[/]")
            else:
                # Empty: dim
                pills.append(f"[dim]{key}:{icon}{label}(0)[/]")

        return " ".join(pills)


# Mana color display with proper MTG colors
MANA_COLORS: dict[str, tuple[str, str, str]] = {
    # color_key: (symbol, bg_color, fg_color)
    "all": ("◈", "#333", ui_colors.GOLD),
    "W": ("☀", "#f8f6d8", "#1a1a1a"),  # White - sun symbol, cream bg
    "U": ("💧", "#0e68ab", "#ffffff"),  # Blue - water drop
    "B": ("💀", "#1a1a1a", "#a0a0a0"),  # Black - skull
    "R": ("🔥", "#d3202a", "#ffffff"),  # Red - fire
    "G": ("🌲", "#00733e", "#ffffff"),  # Green - tree
    "C": ("◇", "#888888", "#1a1a1a"),  # Colorless - diamond
    "M": ("🌈", ui_colors.GOLD, "#1a1a1a"),  # Multicolor - rainbow
}


class CollectionColorIndex(Static):
    """Color filter pills for collection with mana symbols."""

    COLOR_KEYS: ClassVar[dict[str, str]] = {
        "all": "*",
        "W": "w",
        "U": "u",
        "B": "b",
        "R": "r",
        "G": "g",
        "C": "0",
        "M": "m",
    }

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._color_counts: dict[str, int] = {}
        self._active_color: str = "all"

    def update_counts(self, counts: dict[str, int], active: str = "all") -> None:
        """Update color counts and active filter."""
        self._color_counts = counts
        self._active_color = active
        self.update(self._render_index())

    def _render_index(self) -> str:
        """Render horizontal color filter pills with mana-like styling."""
        colors = ["all", "W", "U", "B", "R", "G", "C", "M"]

        pills = []
        for color in colors:
            count = self._color_counts.get(color, 0)
            key = self.COLOR_KEYS.get(color, "")
            symbol, bg_color, fg_color = MANA_COLORS.get(color, ("?", "#333", ui_colors.TEXT_DIM))

            if color == self._active_color:
                # Active: fully highlighted
                pills.append(f"[bold {ui_colors.GOLD} on #2a2a4e]{key}:{symbol}({count})[/]")
            elif count > 0:
                # Has items: show with mana color
                if color == "all":
                    pills.append(f"[{fg_color}]{key}:{symbol}[/][dim]({count})[/]")
                else:
                    pills.append(f"[{bg_color}]{symbol}[/][dim]{key}({count})[/]")
            else:
                # Empty: dim
                pills.append(f"[dim]{key}:{symbol}(0)[/]")

        return " ".join(pills)


class CollectionAvailIndex(Static):
    """Availability filter pills for collection."""

    AVAIL_KEYS: ClassVar[dict[str, str]] = {
        "all": "1",
        "available": "2",
        "in_decks": "3",
    }

    # Availability icons and colors
    AVAIL_DISPLAY: ClassVar[dict[str, tuple[str, str]]] = {
        "all": ("📚", ui_colors.TEXT_DIM),
        "available": ("✅", "#7ec850"),
        "in_decks": ("📋", "#6eb5ff"),
    }

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._avail_counts: dict[str, int] = {}
        self._active_avail: str = "all"

    def update_counts(self, counts: dict[str, int], active: str = "all") -> None:
        """Update availability counts and active filter."""
        self._avail_counts = counts
        self._active_avail = active
        self.update(self._render_index())

    def _render_index(self) -> str:
        """Render horizontal availability filter pills."""
        avails = [
            ("all", "All"),
            ("available", "Free"),
            ("in_decks", "Used"),
        ]

        pills = []
        for avail_key, label in avails:
            count = self._avail_counts.get(avail_key, 0)
            key = self.AVAIL_KEYS.get(avail_key, "")
            icon, color = self.AVAIL_DISPLAY.get(avail_key, ("", ui_colors.TEXT_DIM))

            if avail_key == self._active_avail:
                pills.append(f"[bold {ui_colors.GOLD} on #2a2a4e]{key}:{icon}{label}({count})[/]")
            elif count > 0:
                pills.append(f"[{color}]{key}:{icon}{label}[/][dim]({count})[/]")
            else:
                pills.append(f"[dim]{key}:{icon}{label}(0)[/]")

        return " ".join(pills)
