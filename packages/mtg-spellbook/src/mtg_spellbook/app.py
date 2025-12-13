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
from .deck import (
    AddToDeckModal,
    AddToDeckRequested,
    CardAddedToDeck,
    DeckCreated,
    DeckListPanel,
    DeckSelected,
    NewDeckModal,
)
from .styles import APP_CSS
from .widgets import CardPanel, ResultsList


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
def _signal_handler(_signum: int, _frame: object) -> None:
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

    from .deck_manager import DeckManager, DeckWithCards


class MTGSpellbook(CommandHandlersMixin, App[None]):  # type: ignore[misc]
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
        # Quick actions for current card (ctrl+key to avoid conflicting with text input)
        Binding("ctrl+s", "synergy_current", "Synergy", show=True),
        Binding("ctrl+o", "combos_current", "Combos", show=True),
        Binding("ctrl+a", "art_current", "Art", show=True),
        Binding("ctrl+p", "price_current", "Price", show=True),
        Binding("ctrl+r", "random_card", "Random", show=True),
        # Deck management
        Binding("ctrl+d", "toggle_decks", "Decks", show=True),
        Binding("ctrl+n", "new_deck", "New Deck", show=False),
        Binding("ctrl+e", "add_to_deck", "Add to Deck", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._ctx = DatabaseContext()
        self._db: MTGDatabase | None = None
        self._scryfall: ScryfallDatabase | None = None
        self._deck_manager: DeckManager | None = None
        self._card_count = 0
        self._set_count = 0
        self._current_results: list[CardDetail] = []
        self._current_card: CardDetail | None = None
        self._synergy_mode: bool = False
        self._synergy_info: dict[str, dict[str, object]] = {}
        self._deck_panel_visible: bool = False
        self._viewing_deck_id: int | None = None  # Currently viewed deck

    def compose(self) -> ComposeResult:
        # Header - Epic ASCII banner (enhanced styling)
        yield Static(
            "[#555]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]\n"
            "     [bold #c9a227]✦[/]  "
            "[bold #e6c84a]M T G   S P E L L B O O K[/]  "
            "[bold #c9a227]✦[/]     "
            "[dim]Loading...[/]\n"
            "[#555]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]",
            id="header-content",
        )

        # Main content area - results + details + optional deck panel
        with Horizontal(id="main-container"):
            # Deck panel (hidden by default)
            yield DeckListPanel(id="deck-panel")
            with Vertical(id="results-container"):
                yield Static("Search Results", id="results-header")
                yield ResultsList(id="results-list")
            with Vertical(id="detail-container"), Horizontal(id="card-comparison-container"):
                # Side-by-side card comparison: synergy on left, source on right
                yield CardPanel(id="card-panel")
                yield CardPanel(id="source-card-panel")

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
        self._deck_manager = await self._ctx.get_deck_manager()

        # Get stats
        stats = await self._db.get_database_stats()
        self._card_count = stats.get("unique_cards", 0)
        self._set_count = stats.get("total_sets", 0)

        # Update header with stats (enhanced styling)
        header = self.query_one("#header-content", Static)
        header.update(
            "[#555]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]\n"
            f"     [bold #c9a227]✦[/]  "
            f"[bold #e6c84a]M T G   S P E L L B O O K[/]  "
            f"[bold #c9a227]✦[/]     "
            f"[#e6c84a]{self._card_count:,}[/] [dim]cards[/] "
            f"[#555]·[/] "
            f"[#e6c84a]{self._set_count}[/] [dim]sets[/]\n"
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
        tabs = panel.query_one(panel.get_child_id("tabs"), TabbedContent)
        tabs.active = panel.get_child_name("tab-card")

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
            tabs = panel.query_one(panel.get_child_id("tabs"), TabbedContent)
            tab_names = ["tab-card", "tab-art", "tab-rulings", "tab-legal", "tab-price"]
            tab_ids = [panel.get_child_name(name) for name in tab_names]
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
            tabs = panel.query_one(panel.get_child_id("tabs"), TabbedContent)
            tab_names = ["tab-card", "tab-art", "tab-rulings", "tab-legal", "tab-price"]
            tab_ids = [panel.get_child_name(name) for name in tab_names]
            current = tabs.active
            if current in tab_ids:
                idx = tab_ids.index(current)
                tabs.active = tab_ids[(idx - 1) % len(tab_ids)]
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

    # ─────────────────────────────────────────────────────────────────────────
    # Deck Management
    # ─────────────────────────────────────────────────────────────────────────

    @work
    async def action_toggle_decks(self) -> None:
        """Toggle the deck panel visibility."""
        deck_panel = self.query_one("#deck-panel", DeckListPanel)
        self._deck_panel_visible = not self._deck_panel_visible

        if self._deck_panel_visible:
            deck_panel.add_class("visible")
            # Refresh deck list
            if self._deck_manager:
                await deck_panel.refresh_decks(self._deck_manager)
        else:
            deck_panel.remove_class("visible")

    def action_new_deck(self) -> None:
        """Create a new deck."""
        self.push_screen(NewDeckModal(), callback=self._on_deck_created)

    def _on_deck_created(self, deck_id: int | None) -> None:
        """Called when a new deck is created."""
        if deck_id is not None:
            self._refresh_deck_list()

    @work
    async def _refresh_deck_list(self) -> None:
        """Refresh the deck list panel."""
        if self._deck_manager:
            deck_panel = self.query_one("#deck-panel", DeckListPanel)
            await deck_panel.refresh_decks(self._deck_manager)

    @work
    async def action_add_to_deck(self) -> None:
        """Add the current card to a deck."""
        if not self._current_card:
            self._show_message("[yellow]Select a card first (↑↓ to navigate)[/]")
            return

        if not self._deck_manager:
            self._show_message("[red]Deck management not available[/]")
            return

        # Get list of decks
        decks = await self._deck_manager.list_decks()
        self.push_screen(AddToDeckModal(self._current_card.name, decks))

    @on(DeckSelected)
    def on_deck_selected(self, event: DeckSelected) -> None:
        """Handle deck selection from deck panel."""
        if event.deck_id == -1:
            # Refresh signal
            self._refresh_deck_list()
        else:
            # Load and display the deck's cards in the results pane
            self._load_deck_cards(event.deck_id)

    @work
    async def _load_deck_cards(self, deck_id: int) -> None:
        """Load deck cards and display them in the results list."""
        if not self._deck_manager or not self._db:
            return

        deck = await self._deck_manager.get_deck(deck_id)
        if not deck:
            self.notify("Deck not found", severity="error")
            return

        self._viewing_deck_id = deck_id
        self._synergy_mode = False
        self._hide_synergy_panel()

        # Load full card details for each card in the deck
        self._current_results = []
        deck_card_info: dict[str, dict[str, object]] = {}  # card_name -> {quantity, sideboard}

        for card_data in deck.cards:
            if card_data.card:
                # Convert DeckCardWithData.card to CardDetail
                from mtg_core.tools import cards as card_tools

                try:
                    detail = await card_tools.get_card(
                        self._db, self._scryfall, name=card_data.card_name
                    )
                    self._current_results.append(detail)
                    deck_card_info[card_data.card_name] = {
                        "quantity": card_data.quantity,
                        "sideboard": card_data.is_sideboard,
                        "commander": card_data.is_commander,
                    }
                except Exception:
                    pass

        # Update the results list with deck cards
        self._update_deck_results(deck, deck_card_info)

        # Show first card
        if self._current_results:
            self._current_card = self._current_results[0]
            self._update_card_panel(self._current_results[0])
            await self._load_card_extras(self._current_results[0])

    def _update_deck_results(
        self, deck: DeckWithCards, card_info: dict[str, dict[str, object]]
    ) -> None:
        """Update results list with deck cards."""
        from textual.widgets import Label, ListItem

        from .formatting import prettify_mana
        from .widgets import ResultsList

        results_list = self.query_one("#results-list", ResultsList)
        results_list.clear()

        # Sort: commanders first, then mainboard, then sideboard
        def sort_key(card: CardDetail) -> tuple[int, int, str]:
            info = card_info.get(card.name, {})
            is_commander = info.get("commander", False)
            is_sideboard = info.get("sideboard", False)
            return (0 if is_commander else 1, 1 if is_sideboard else 0, card.name)

        sorted_cards = sorted(self._current_results, key=sort_key)

        for card in sorted_cards:
            info = card_info.get(card.name, {})
            qty = info.get("quantity", 1)
            is_sideboard = info.get("sideboard", False)
            is_commander = info.get("commander", False)

            mana = prettify_mana(card.mana_cost) if card.mana_cost else ""

            # Build display line
            prefix = ""
            if is_commander:
                prefix = "[bold magenta]★[/] "
            elif is_sideboard:
                prefix = "[dim]SB[/] "

            line = f"{prefix}[cyan]{qty}x[/] [bold]{card.name}[/]"
            if mana:
                line += f"  {mana}"

            results_list.append(ListItem(Label(line)))

        # Update header with deck name and card count
        self._update_results_header(
            f"📚 {deck.name} ({deck.mainboard_count} + {deck.sideboard_count} SB)"
        )

        if sorted_cards:
            results_list.focus()
            results_list.index = 0

    @on(DeckCreated)
    def on_deck_created_message(self, _event: DeckCreated) -> None:
        """Handle deck created message."""
        self._refresh_deck_list()

    @on(AddToDeckRequested)
    async def on_add_to_deck_requested(self, event: AddToDeckRequested) -> None:
        """Handle request to add a card to a deck."""
        if not self._deck_manager:
            return

        decks = await self._deck_manager.list_decks()
        self.push_screen(AddToDeckModal(event.card_name, decks))

    @on(CardAddedToDeck)
    def on_card_added_to_deck(self, _event: CardAddedToDeck) -> None:
        """Handle card added to deck."""
        self._refresh_deck_list()
