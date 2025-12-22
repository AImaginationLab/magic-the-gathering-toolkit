"""Clickable menu item widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.events import Key


class MenuItem(Static, can_focus=True):
    """A clickable menu item with label and hotkey hint.

    Displays as: "  Artists                    [a]"
    """

    DEFAULT_CSS = """
    MenuItem {
        width: 100%;
        height: 1;
        padding: 0 2;
        background: transparent;
    }

    MenuItem:hover {
        background: #1a1a2e;
    }

    MenuItem:focus {
        background: #2a2a4e;
    }

    MenuItem.disabled {
        color: #666666;
    }
    """

    is_disabled: reactive[bool] = reactive(False, toggle_class="disabled")

    class Selected(Message):
        """Posted when this menu item is selected (clicked or Enter pressed)."""

        def __init__(self, item: MenuItem) -> None:
            super().__init__()
            self.item = item

    def __init__(
        self,
        label: str,
        hotkey: str,
        action: str,
        *,
        disabled: bool = False,
        id: str | None = None,
    ) -> None:
        """Create a menu item.

        Args:
            label: Display text (e.g., "Artists")
            hotkey: Hotkey hint (e.g., "a" or "Ctrl+S")
            action: Action name without "action_" prefix (e.g., "browse_artists")
            disabled: Whether the item is disabled
            id: Optional widget ID
        """
        super().__init__(id=id)
        self.label = label
        self.hotkey = hotkey
        self.action = action
        self.is_disabled = disabled

    def compose(self) -> ComposeResult:
        # Content is rendered via render() method
        return []

    def render(self) -> str:
        """Render the menu item with label and hotkey."""
        # Pad label to align hotkeys
        padded_label = f"{self.label:<30}"
        # Escape the hotkey to prevent Rich markup interpretation
        escaped_hotkey = self.hotkey.replace("[", r"\[").replace("]", r"\]")
        hotkey_display = f"[dim]\\[{escaped_hotkey}][/dim]"
        return f"  {padded_label} {hotkey_display}"

    def on_click(self) -> None:
        """Handle click on menu item."""
        if not self.is_disabled:
            self.post_message(self.Selected(self))

    def on_key(self, event: Key) -> None:
        """Handle key press on focused menu item."""
        if event.key in ("enter", "space") and not self.is_disabled:
            self.post_message(self.Selected(self))
            event.stop()
