"""Quick links bar for dashboard navigation."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Static

from .messages import QuickLinkAction, QuickLinkActivated

if TYPE_CHECKING:
    from textual.events import Click, Key


class QuickLinkButton(Static, can_focus=True):
    """Focusable quick link button with underlined shortcut letter."""

    DEFAULT_CSS = """
    QuickLinkButton {
        width: auto;
        height: auto;
        padding: 0 2;
        margin: 0 1;
        color: #888888;
        background: transparent;
    }

    QuickLinkButton:hover {
        background: #2a2a4e;
        color: #c9a227;
    }

    QuickLinkButton:focus {
        color: #e6c84a;
        text-style: bold;
        background: #1a1a2e;
    }
    """

    def __init__(
        self,
        label: str,
        action: QuickLinkAction,
        shortcut: str,
        *,
        id: str | None = None,
    ) -> None:
        # Format label with underlined shortcut letter
        formatted = self._format_label(label, shortcut)
        super().__init__(formatted, id=id)
        self.action = action
        self.shortcut = shortcut
        self._label = label

    def _format_label(self, label: str, shortcut: str) -> str:
        """Format label with underlined shortcut letter."""
        # Find the shortcut letter (case-insensitive) and underline it
        lower_label = label.lower()
        lower_shortcut = shortcut.lower()

        idx = lower_label.find(lower_shortcut)
        if idx >= 0:
            # Underline the shortcut letter
            return f"{label[:idx]}[u]{label[idx]}[/u]{label[idx + 1 :]}"
        # Fallback: just show the label
        return label

    def on_click(self, _event: Click) -> None:
        """Handle click on button."""
        self.post_message(QuickLinkActivated(self.action))

    def on_key(self, event: Key) -> None:
        """Handle key press on focused button."""
        if event.key in ("enter", "space"):
            self.post_message(QuickLinkActivated(self.action))
            event.stop()
            event.prevent_default()


class QuickLinksBar(Horizontal, can_focus=False):
    """Horizontal bar of quick link buttons for dashboard navigation."""

    DEFAULT_CSS = """
    QuickLinksBar {
        height: auto;
        width: 100%;
        align: center middle;
        padding: 1 2;
        margin: 1 0 2 0;
        background: #1a1a1a;
        border: round #3d3d3d;
    }
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        # Letter shortcuts work when any button is focused
        Binding("a", "activate('artists')", "Artists", show=False),
        Binding("s", "activate('sets')", "Sets", show=False),
        Binding("d", "activate('decks')", "Decks", show=False),
        Binding("c", "activate('collection')", "Collection", show=False),
        Binding("r", "activate('random')", "Random", show=False),
    ]

    def compose(self) -> ComposeResult:
        """Compose the quick link buttons."""
        yield QuickLinkButton("Artists", "artists", "a", id="ql-artists")
        yield QuickLinkButton("Sets", "sets", "s", id="ql-sets")
        yield QuickLinkButton("Decks", "decks", "d", id="ql-decks")
        yield QuickLinkButton("Collection", "collection", "c", id="ql-collection")
        yield QuickLinkButton("Random", "random", "r", id="ql-random")

    def action_activate(self, action: str) -> None:
        """Activate a quick link by shortcut."""
        self.post_message(QuickLinkActivated(action))  # type: ignore[arg-type]

    def focus_first(self) -> bool:
        """Focus the first button."""
        try:
            first = self.query_one("#ql-artists", QuickLinkButton)
            first.focus()
            return True
        except Exception:
            return False
