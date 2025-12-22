"""Snapshot tests for screen layouts.

These tests capture SVG screenshots of screens and compare them against
saved snapshots to detect visual regressions.

Run with: uv run pytest tests/test_screen_snapshots.py -v
Update snapshots with: uv run pytest tests/test_screen_snapshots.py --snapshot-update
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import ListView, Static

from mtg_spellbook.screens import BaseScreen

if TYPE_CHECKING:
    from pytest_textual_snapshot import SnapCompare


class MockCollectionScreen(BaseScreen[None]):
    """Mock collection screen for snapshot testing."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "close", "Close"),
    ]

    show_footer: ClassVar[bool] = False

    CSS = """
    MockCollectionScreen {
        background: #0d0d0d;
    }

    #mock-header {
        height: 3;
        background: #0a0a14;
        border-bottom: heavy #c9a227;
        padding: 0 2;
        content-align: center middle;
    }

    #mock-main {
        width: 100%;
        height: 1fr;
    }

    #mock-left {
        width: 25%;
        height: 100%;
        background: #0f0f0f;
        border-right: solid #3d3d3d;
    }

    #mock-center {
        width: 40%;
        height: 100%;
        background: #0a0a14;
        border-right: solid #3d3d3d;
    }

    #mock-right {
        width: 35%;
        height: 100%;
        background: #0d0d0d;
    }

    #mock-statusbar {
        height: 2;
        background: #1a1a1a;
        border-top: solid #3d3d3d;
        padding: 0 1;
    }
    """

    def compose_content(self) -> ComposeResult:
        yield Static("[bold #c9a227]📦 MY COLLECTION[/]  [dim](100 cards)[/]", id="mock-header")
        with Horizontal(id="mock-main"):
            with Vertical(id="mock-left"):
                yield Static("[#c9a227]Stats Panel[/]")
                yield Static("Total: 100")
                yield Static("Creatures: 40")
                yield Static("Instants: 20")
            with Vertical(id="mock-center"):
                yield Static("[dim]Card List[/]")
                yield ListView(id="mock-list")
            with Vertical(id="mock-right"):
                yield Static("[dim]Preview[/]")
        yield Static(
            "[#c9a227]/[/]:Search  [#c9a227]+[/]:Add  [#c9a227]Del[/]:Remove", id="mock-statusbar"
        )

    def action_close(self) -> None:
        self.app.pop_screen()


class MockDeckScreen(BaseScreen[None]):
    """Mock deck screen for snapshot testing."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "close", "Close"),
    ]

    show_footer: ClassVar[bool] = False

    CSS = """
    MockDeckScreen {
        background: #0d0d0d;
    }

    #deck-header {
        height: 3;
        background: #0a0a14;
        border-bottom: heavy #c9a227;
        padding: 0 2;
        content-align: center middle;
    }

    #deck-main {
        width: 100%;
        height: 1fr;
    }

    #deck-list-pane {
        width: 20%;
        height: 100%;
        background: #0f0f0f;
        border-right: solid #3d3d3d;
    }

    #deck-content-pane {
        width: 50%;
        height: 100%;
        background: #0a0a14;
        border-right: solid #3d3d3d;
    }

    #deck-preview-pane {
        width: 30%;
        height: 100%;
        background: #0d0d0d;
    }

    #deck-footer {
        height: 2;
        background: #1a1a1a;
        border-top: solid #3d3d3d;
        padding: 0 1;
    }
    """

    def compose_content(self) -> ComposeResult:
        yield Static("[bold #c9a227]🗂 DECK MANAGER[/]", id="deck-header")
        with Horizontal(id="deck-main"):
            with Vertical(id="deck-list-pane"):
                yield Static("[#c9a227]My Decks[/]")
                yield ListView(id="deck-list")
            with Vertical(id="deck-content-pane"):
                yield Static("[dim]Select a deck[/]")
            with Vertical(id="deck-preview-pane"):
                yield Static("[dim]Analysis[/]")
        yield Static(
            "[#c9a227]n[/]:New  [#c9a227]Enter[/]:Open  [#c9a227]Esc[/]:Back", id="deck-footer"
        )

    def action_close(self) -> None:
        self.app.pop_screen()


class SnapshotTestApp(App[None]):
    """App for snapshot testing screens."""

    CSS = """
    Screen {
        background: #0d0d0d;
    }
    """

    def __init__(self, screen_class: type[BaseScreen[None]]) -> None:
        super().__init__()
        self._screen_class = screen_class

    def on_mount(self) -> None:
        self.push_screen(self._screen_class())


class TestScreenSnapshots:
    """Snapshot tests for screen layouts."""

    def test_collection_screen_layout(self, snap_compare: SnapCompare) -> None:
        """Test that collection screen layout renders correctly."""
        app = SnapshotTestApp(MockCollectionScreen)
        assert snap_compare(app, terminal_size=(120, 40))

    def test_deck_screen_layout(self, snap_compare: SnapCompare) -> None:
        """Test that deck screen layout renders correctly."""
        app = SnapshotTestApp(MockDeckScreen)
        assert snap_compare(app, terminal_size=(120, 40))

    def test_collection_screen_with_menu_expanded(self, snap_compare: SnapCompare) -> None:
        """Test collection screen with menu expanded."""
        app = SnapshotTestApp(MockCollectionScreen)
        assert snap_compare(app, terminal_size=(120, 40), press=["f10"])

    def test_deck_screen_with_menu_expanded(self, snap_compare: SnapCompare) -> None:
        """Test deck screen with menu expanded."""
        app = SnapshotTestApp(MockDeckScreen)
        assert snap_compare(app, terminal_size=(120, 40), press=["f10"])
