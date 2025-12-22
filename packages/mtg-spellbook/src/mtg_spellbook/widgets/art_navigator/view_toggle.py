"""View mode toggle component for switching between gallery, focus, and compare modes."""

from __future__ import annotations

from enum import Enum

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static


class ViewMode(Enum):
    """Available view modes for art navigation."""

    GALLERY = "gallery"
    FOCUS = "focus"
    COMPARE = "compare"


class ModeButton(Static, can_focus=True):
    """Clickable mode button."""

    def __init__(
        self,
        label: str,
        mode: ViewMode,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(label, id=id, classes=classes)
        self.mode = mode

    def on_click(self) -> None:
        """Handle click on mode button."""
        self.post_message(ViewModeToggle.ModeSelected(self.mode))


class ViewModeToggle(Horizontal):
    """Toggle bar for switching between view modes."""

    current_mode: reactive[ViewMode] = reactive(ViewMode.GALLERY)

    class ModeSelected(Message):
        """Posted when a mode button is clicked."""

        def __init__(self, mode: ViewMode) -> None:
            super().__init__()
            self.mode = mode

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)

    def compose(self) -> ComposeResult:
        """Build toggle buttons."""
        yield ModeButton(
            "[G Gallery]",
            ViewMode.GALLERY,
            id="mode-gallery",
            classes="mode-button mode-active",
        )
        yield ModeButton(
            "[F Focus]",
            ViewMode.FOCUS,
            id="mode-focus",
            classes="mode-button",
        )
        yield ModeButton(
            "[C Compare]",
            ViewMode.COMPARE,
            id="mode-compare",
            classes="mode-button",
        )

    def watch_current_mode(self, new_mode: ViewMode) -> None:
        """Update button styles when mode changes."""
        try:
            for mode in ViewMode:
                button = self.query_one(f"#mode-{mode.value}", ModeButton)
                if mode == new_mode:
                    button.add_class("mode-active")
                    button.remove_class("mode-inactive")
                else:
                    button.add_class("mode-inactive")
                    button.remove_class("mode-active")
        except NoMatches:
            pass

    def set_mode(self, mode: ViewMode) -> None:
        """Set the current view mode."""
        self.current_mode = mode
