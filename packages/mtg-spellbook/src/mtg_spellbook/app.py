"""Main Textual TUI app for MTG Spellbook."""

from __future__ import annotations

import atexit
import signal
import sys
from typing import TYPE_CHECKING, ClassVar

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Input, Label, ListItem, ListView, Static, TabbedContent

from mtg_spellbook.context import DatabaseContext

from .commands import CommandHandlersMixin
from .styles import APP_CSS
from .widgets import CardPanel, ResultsList, SynergyPanel


def _reset_terminal_mouse() -> None:
    """Reset terminal mouse tracking - called on exit."""
    sys.stdout.write("\x1b[?1000l")  # Disable mouse click tracking
    sys.stdout.write("\x1b[?1002l")  # Disable mouse button tracking
    sys.stdout.write("\x1b[?1003l")  # Disable mouse movement tracking
    sys.stdout.write("\x1b[?1006l")  # Disable SGR mouse mode
    sys.stdout.write("\x1b[?1004l")  # Disable focus reporting
    sys.stdout.write("\x1b[?25h")  # Show cursor
    sys.stdout.flush()


# Register cleanup at module load to ensure it runs on any exit
atexit.register(_reset_terminal_mouse)

# Also handle signals for cases where atexit doesn't run
def _signal_handler(signum: int, frame: object) -> None:
    """Handle termination signals by cleaning up terminal."""
    _reset_terminal_mouse()
    sys.exit(0)


# Register signal handlers (ignore errors if signals not available on platform)
try:
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGHUP, _signal_handler)
except (OSError, AttributeError):
    pass  # Some signals may not be available on all platforms

if TYPE_CHECKING:
    from mtg_core.data.database import MTGDatabase, ScryfallDatabase
    from mtg_core.data.models.responses import CardDetail


class MTGSpellbook(CommandHandlersMixin, App[None]):
    """MTG Spellbook - Interactive card lookup TUI."""

    TITLE = "MTG Spellbook"
    SUB_TITLE = "⚔️ Magic: The Gathering Card Database"

    CSS = APP_CSS

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("ctrl+c", "quit", "Quit", show=True, priority=True),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("f1", "help", "Help"),
        Binding("escape", "focus_input", "Input"),
        Binding("tab", "next_tab", "Next Tab"),
        Binding("shift+tab", "prev_tab", "Prev Tab"),
        Binding("left", "prev_art", "← Prev Art", show=False),
        Binding("right", "next_art", "→ Next Art", show=False),
        # Quick actions for current card (ctrl+key to avoid conflicting with text input)
        Binding("ctrl+s", "synergy_current", "Synergy", show=True),
        Binding("ctrl+o", "combos_current", "Combos", show=True),
        Binding("ctrl+a", "art_current", "Art", show=True),
        Binding("ctrl+p", "price_current", "Price", show=True),
        Binding("ctrl+r", "random_card", "Random", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._ctx = DatabaseContext()
        self._db: MTGDatabase | None = None
        self._scryfall: ScryfallDatabase | None = None
        self._card_count = 0
        self._set_count = 0
        self._current_results: list[CardDetail] = []
        self._current_card: CardDetail | None = None
        self._synergy_mode: bool = False
        self._synergy_info: dict[str, dict[str, object]] = {}

    def compose(self) -> ComposeResult:
        # Header - Epic ASCII banner
        yield Static(
            "[#555]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]\n"
            "              [bold #c9a227]✦  M T G   S P E L L B O O K  ✦[/]              [#444]Loading...[/]\n"
            "[#555]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]",
            id="header-content",
        )

        # Main content area - no sidebar, just results + details
        with Horizontal(id="main-container"):
            with Vertical(id="results-container"):
                yield Static("Search Results", id="results-header")
                yield ResultsList(id="results-list")
            with Vertical(id="detail-container"):
                yield CardPanel(id="card-panel")
                yield SynergyPanel(id="synergy-panel")

        # Input bar at bottom
        with Horizontal(id="input-bar"):
            yield Label("⚡")
            yield Input(
                placeholder="Card name, 'search t:creature c:red', or 'help'",
                id="search-input",
            )

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize database connections."""
        # Use dark mode for our custom styling
        self.dark = True

        self._db = await self._ctx.get_db()
        self._scryfall = await self._ctx.get_scryfall()

        # Get stats
        stats = await self._db.get_database_stats()
        self._card_count = stats.get("unique_cards", 0)
        self._set_count = stats.get("total_sets", 0)

        # Update header with stats
        header = self.query_one("#header-content", Static)
        header.update(
            "[#555]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]\n"
            f"              [bold #c9a227]✦  M T G   S P E L L B O O K  ✦[/]              "
            f"[#666]{self._card_count:,} cards · {self._set_count} sets[/]\n"
            "[#555]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
        )

        # Focus input
        self.query_one("#search-input", Input).focus()

    async def on_unmount(self) -> None:
        """Clean up database connections on exit."""
        await self._ctx.close()
        # Terminal mouse reset is handled by atexit handler

    async def action_quit(self) -> None:
        """Quit the application cleanly."""
        self.exit()

    @on(Input.Submitted, "#search-input")
    def handle_input(self, event: Input.Submitted) -> None:
        """Handle search input submission."""
        query = event.value.strip()
        if not query:
            return

        # Clear input
        event.input.value = ""

        # Delegate to command handler
        self.handle_command(query)

    def _show_message(self, message: str) -> None:
        """Show a message in the results area."""
        results_list = self.query_one("#results-list", ResultsList)
        results_list.clear()
        results_list.append(ListItem(Label(message)))

    @on(ListView.Highlighted, "#results-list")
    def on_result_highlighted(self, event: ListView.Highlighted) -> None:
        """Update card panel when navigating results."""
        if event.item and self._current_results:
            index = event.list_view.index or 0
            if 0 <= index < len(self._current_results):
                card = self._current_results[index]
                self._current_card = card
                # Use synergy-aware update if in synergy mode
                if self._synergy_mode:
                    self._update_card_panel_with_synergy(card)
                else:
                    self._update_card_panel(card)
                # Load extras in background
                self._load_extras_for_card(card)

    @work
    async def _load_extras_for_card(self, card: CardDetail) -> None:
        """Load extras for highlighted card."""
        await self._load_card_extras(card)

    @on(ListView.Selected, "#results-list")
    def on_result_selected(self, _event: ListView.Selected) -> None:
        """Handle result selection - switch to card tab."""
        panel = self.query_one("#card-panel", CardPanel)
        tabs = panel.query_one("#card-tabs", TabbedContent)
        tabs.active = "tab-card"

    def action_focus_input(self) -> None:
        """Focus the search input."""
        self.query_one("#search-input", Input).focus()

    def action_clear(self) -> None:
        """Clear the display."""
        results_list = self.query_one("#results-list", ResultsList)
        results_list.clear()
        self._current_results = []
        self._current_card = None
        self._update_card_panel(None)
        self._hide_synergy_panel()
        self.action_focus_input()

    def action_help(self) -> None:
        """Show help."""
        self.show_help()

    def action_next_tab(self) -> None:
        """Switch to next tab."""
        try:
            panel = self.query_one("#card-panel", CardPanel)
            tabs = panel.query_one("#card-tabs", TabbedContent)
            tab_ids = ["tab-card", "tab-art", "tab-rulings", "tab-legal", "tab-price"]
            current = tabs.active
            if current in tab_ids:
                idx = tab_ids.index(current)
                tabs.active = tab_ids[(idx + 1) % len(tab_ids)]
        except Exception:
            pass

    def action_prev_tab(self) -> None:
        """Switch to previous tab."""
        try:
            panel = self.query_one("#card-panel", CardPanel)
            tabs = panel.query_one("#card-tabs", TabbedContent)
            tab_ids = ["tab-card", "tab-art", "tab-rulings", "tab-legal", "tab-price"]
            current = tabs.active
            if current in tab_ids:
                idx = tab_ids.index(current)
                tabs.active = tab_ids[(idx - 1) % len(tab_ids)]
        except Exception:
            pass

    @work
    async def action_next_art(self) -> None:
        """Navigate to next printing in art gallery."""
        try:
            panel = self.query_one("#card-panel", CardPanel)
            tabs = panel.query_one("#card-tabs", TabbedContent)
            # Only navigate if on art tab
            if tabs.active == "tab-art":
                await panel.load_next_art()
        except Exception:
            pass

    @work
    async def action_prev_art(self) -> None:
        """Navigate to previous printing in art gallery."""
        try:
            panel = self.query_one("#card-panel", CardPanel)
            tabs = panel.query_one("#card-tabs", TabbedContent)
            # Only navigate if on art tab
            if tabs.active == "tab-art":
                await panel.load_prev_art()
        except Exception:
            pass

    def action_synergy_current(self) -> None:
        """Find synergies for currently selected card."""
        if self._current_card:
            self.find_synergies(self._current_card.name)
        else:
            self._show_message("[yellow]Select a card first (↑↓ to navigate)[/]")

    def action_combos_current(self) -> None:
        """Find combos for currently selected card."""
        if self._current_card:
            self.find_combos(self._current_card.name)
        else:
            self._show_message("[yellow]Select a card first (↑↓ to navigate)[/]")

    def action_art_current(self) -> None:
        """Show art for currently selected card."""
        if self._current_card:
            self.show_art(self._current_card.name)
        else:
            self._show_message("[yellow]Select a card first (↑↓ to navigate)[/]")

    def action_price_current(self) -> None:
        """Show price for currently selected card."""
        if self._current_card:
            self.show_price(self._current_card.name)
        else:
            self._show_message("[yellow]Select a card first (↑↓ to navigate)[/]")

    def action_random_card(self) -> None:
        """Get a random card."""
        self.lookup_random()
