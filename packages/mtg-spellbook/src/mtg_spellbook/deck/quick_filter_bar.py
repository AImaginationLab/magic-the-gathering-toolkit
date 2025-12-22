"""Quick filter bar widget for card search filtering."""

from __future__ import annotations

from typing import Any, ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Static

from ..ui.theme import mtg_colors


class CMCButton(Button):
    """Button for CMC filter toggle."""

    def __init__(self, cmc: int | str, **kwargs: Any) -> None:
        label = str(cmc) if isinstance(cmc, int) else cmc
        super().__init__(label, **kwargs)
        self.cmc_value = cmc


class ColorButton(Button):
    """Button for color filter toggle."""

    COLOR_STYLES: ClassVar[dict[str, tuple[str, str]]] = {
        "W": (mtg_colors.WHITE, "#000"),
        "U": (mtg_colors.BLUE, "#fff"),
        "B": (mtg_colors.BLACK, "#fff"),
        "R": (mtg_colors.RED, "#fff"),
        "G": (mtg_colors.GREEN, "#fff"),
    }

    def __init__(self, color: str, **kwargs: Any) -> None:
        super().__init__(color, **kwargs)
        self.color_value = color


class TypeButton(Button):
    """Button for type filter toggle."""

    def __init__(self, type_name: str, **kwargs: Any) -> None:
        # Use short labels for compact display
        short_names = {
            "Creature": "Cre",
            "Instant": "Ins",
            "Sorcery": "Sor",
            "Artifact": "Art",
            "Enchantment": "Enc",
            "Planeswalker": "PW",
            "Land": "Lnd",
        }
        label = short_names.get(type_name, type_name[:3])
        super().__init__(label, **kwargs)
        self.type_value = type_name


class QuickFilterBar(Widget):
    """Compact filter bar for quick card filtering.

    Features:
    - CMC toggles (0-6+)
    - Color checkboxes (WUBRG)
    - Type toggles (Creature, Instant, etc.)
    """

    class FiltersChanged(Message):
        """Sent when any filter changes."""

        def __init__(self, filters: dict[str, Any]) -> None:
            super().__init__()
            self.filters = filters

    # Reactive state for active filters
    active_cmc: reactive[int | None] = reactive(None)
    active_type: reactive[str | None] = reactive(None)

    DEFAULT_CSS = """
    QuickFilterBar {
        height: 5;
        width: 100%;
        background: #151515;
        border-bottom: solid #2a2a2a;
        padding: 0 1;
    }

    #filter-sections {
        height: 100%;
        width: 100%;
    }

    .filter-section {
        height: auto;
        width: 100%;
        padding: 0;
    }

    .filter-label {
        height: auto;
        width: auto;
        color: #888;
        padding: 0 1 0 0;
    }

    .filter-buttons {
        height: auto;
        width: 1fr;
    }

    .cmc-btn, .color-btn, .type-btn {
        width: auto;
        min-width: 3;
        height: 1;
        padding: 0 1;
        margin: 0;
        background: #252525;
        color: #888;
        border: none;
    }

    .cmc-btn:hover, .color-btn:hover, .type-btn:hover {
        background: #353535;
        color: #ccc;
    }

    .cmc-btn.-active {
        background: #c9a227;
        color: #0d0d0d;
        text-style: bold;
    }

    .color-btn.-active {
        text-style: bold;
    }

    .color-btn.-active.color-W {
        background: #F0E68C;
        color: #000;
    }

    .color-btn.-active.color-U {
        background: #0E86D4;
        color: #fff;
    }

    .color-btn.-active.color-B {
        background: #2C3639;
        color: #fff;
    }

    .color-btn.-active.color-R {
        background: #C7253E;
        color: #fff;
    }

    .color-btn.-active.color-G {
        background: #1A5D1A;
        color: #fff;
    }

    .type-btn.-active {
        background: #c9a227;
        color: #0d0d0d;
        text-style: bold;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._active_colors: set[str] = set()

    def compose(self) -> ComposeResult:
        with Horizontal(id="filter-sections"):
            # CMC filter row
            with Horizontal(classes="filter-section"):
                yield Static("CMC:", classes="filter-label")
                with Horizontal(classes="filter-buttons"):
                    for cmc in range(7):
                        yield CMCButton(cmc, id=f"cmc-{cmc}", classes="cmc-btn")
                    yield CMCButton("7+", id="cmc-7plus", classes="cmc-btn")

            # Color filter row
            with Horizontal(classes="filter-section"):
                yield Static("Color:", classes="filter-label")
                with Horizontal(classes="filter-buttons"):
                    for color in ["W", "U", "B", "R", "G"]:
                        yield ColorButton(
                            color, id=f"color-{color}", classes=f"color-btn color-{color}"
                        )

            # Type filter row
            with Horizontal(classes="filter-section"):
                yield Static("Type:", classes="filter-label")
                with Horizontal(classes="filter-buttons"):
                    for type_name in ["Creature", "Instant", "Sorcery", "Artifact", "Enchantment"]:
                        yield TypeButton(
                            type_name, id=f"type-{type_name.lower()}", classes="type-btn"
                        )

    @on(Button.Pressed, ".cmc-btn")
    def on_cmc_pressed(self, event: Button.Pressed) -> None:
        """Handle CMC button press."""
        btn = event.button
        if not isinstance(btn, CMCButton):
            return

        # Toggle off if already active
        if btn.has_class("-active"):
            btn.remove_class("-active")
            self.active_cmc = None
        else:
            # Deactivate all CMC buttons
            for cmc_btn in self.query(".cmc-btn"):
                cmc_btn.remove_class("-active")
            btn.add_class("-active")

            # Set active CMC
            if btn.cmc_value == "7+":
                self.active_cmc = 7
            else:
                self.active_cmc = int(btn.cmc_value)

        self._emit_filters()

    @on(Button.Pressed, ".color-btn")
    def on_color_pressed(self, event: Button.Pressed) -> None:
        """Handle color button press."""
        btn = event.button
        if not isinstance(btn, ColorButton):
            return

        color = btn.color_value

        # Toggle color
        if btn.has_class("-active"):
            btn.remove_class("-active")
            self._active_colors.discard(color)
        else:
            btn.add_class("-active")
            self._active_colors.add(color)

        self._emit_filters()

    @on(Button.Pressed, ".type-btn")
    def on_type_pressed(self, event: Button.Pressed) -> None:
        """Handle type button press."""
        btn = event.button
        if not isinstance(btn, TypeButton):
            return

        # Toggle off if already active
        if btn.has_class("-active"):
            btn.remove_class("-active")
            self.active_type = None
        else:
            # Deactivate all type buttons
            for type_btn in self.query(".type-btn"):
                type_btn.remove_class("-active")
            btn.add_class("-active")
            self.active_type = btn.type_value

        self._emit_filters()

    def _emit_filters(self) -> None:
        """Emit filter change message."""
        self.post_message(self.FiltersChanged(self.get_filters()))

    def get_filters(self) -> dict[str, Any]:
        """Get current filter state as dict."""
        filters: dict[str, Any] = {}

        if self.active_cmc is not None:
            filters["cmc"] = self.active_cmc

        if self._active_colors:
            filters["colors"] = list(self._active_colors)

        if self.active_type:
            filters["type"] = self.active_type

        return filters

    def clear_filters(self) -> None:
        """Clear all active filters."""
        # Reset CMC
        for btn in self.query(".cmc-btn"):
            btn.remove_class("-active")
        self.active_cmc = None

        # Reset colors
        for btn in self.query(".color-btn"):
            btn.remove_class("-active")
        self._active_colors.clear()

        # Reset type
        for btn in self.query(".type-btn"):
            btn.remove_class("-active")
        self.active_type = None

        self._emit_filters()
