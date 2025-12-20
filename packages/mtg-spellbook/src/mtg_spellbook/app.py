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
from textual.widgets import Footer, Input, Label, ListItem, ListView, Static

from mtg_core.exceptions import CardNotFoundError
from mtg_spellbook.context import DatabaseContext

from .collection import (
    AddToCollectionModal,
    CollectionCardSelected,
    CollectionListPanel,
    FullCollectionScreen,
)
from .commands import CommandHandlersMixin
from .deck import (
    AddToDeckModal,
    AddToDeckRequested,
    CardAddedToDeck,
    DeckCreated,
    DeckEditorPanel,
    DeckListPanel,
    DeckSelected,
    NewDeckModal,
)
from .pagination import PaginationState
from .styles import APP_CSS
from .ui.theme import ui_colors
from .widgets import (
    CardPanel,
    ClosePortfolio,
    Dashboard,
    EnhancedSynergyPanel,
    ResultsList,
    SetDetailClosed,
    SynergyPanelClosed,
    SynergySelected,
    ViewArtwork,
)
from .widgets.art_navigator.image_loader import close_http_client
from .widgets.art_navigator.messages import ArtistSelected as ArtNavigatorArtistSelected
from .widgets.artist_browser import ArtistBrowserClosed, ArtistSelected
from .widgets.dashboard import QuickLinkActivated, SearchResultSelected, SearchSubmitted


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

    from .collection_manager import CollectionManager
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
        Binding("ctrl+h", "help", "Help", show=True),
        Binding("escape", "focus_input", "Input"),
        Binding("tab", "next_tab", "Next Tab"),
        Binding("shift+tab", "prev_tab", "Prev Tab"),
        # Dashboard quick actions - work from ANYWHERE (app-level)
        Binding("a", "browse_artists", "Artists", show=True),
        Binding("s", "browse_sets", "Sets", show=True),
        Binding("d", "browse_decks", "Decks", show=True),
        Binding("c", "browse_collection", "Collection", show=True),
        Binding("r", "random_card", "Random", show=True),
        # Quick actions for current card (ctrl+key to avoid conflicting with text input)
        Binding("ctrl+s", "synergy_current", "Synergy"),
        Binding("ctrl+o", "combos_current", "Combos"),
        Binding("ctrl+a", "art_current", "Art"),
        Binding("ctrl+p", "price_current", "Price"),
        # Deck management
        Binding("ctrl+d", "toggle_decks", "Decks", show=True),
        Binding("ctrl+b", "full_deck_builder", "Decks", show=False),
        Binding("ctrl+n", "new_deck", "New Deck"),
        Binding("ctrl+e", "add_to_deck", "Add to Deck"),
        # Collection management
        Binding("ctrl+shift+e", "add_to_collection", "Add to Collection"),
        # Pagination
        Binding("n", "next_page", "Next Page", show=False),
        Binding("p", "prev_page", "Prev Page", show=False),
        Binding("pagedown", "next_page", "Next Page", show=False),
        Binding("pageup", "prev_page", "Prev Page", show=False),
        Binding("home", "first_page", "First Page", show=False),
        Binding("end", "last_page", "Last Page", show=False),
        Binding("g", "goto_page", "Go to Page", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._ctx = DatabaseContext()
        self._db: MTGDatabase | None = None
        self._scryfall: ScryfallDatabase | None = None
        self._deck_manager: DeckManager | None = None
        self._collection_manager: CollectionManager | None = None
        self._card_count = 0
        self._set_count = 0
        self._current_results: list[CardDetail] = []
        self._current_card: CardDetail | None = None
        self._synergy_mode: bool = False
        self._synergy_info: dict[str, dict[str, object]] = {}
        self._artist_mode: bool = False
        self._artist_name: str = ""
        self._deck_panel_visible: bool = False
        self._collection_panel_visible: bool = False
        self._viewing_deck_id: int | None = None  # Currently viewed deck
        self._deck_editor_visible: bool = False  # Is deck editor open?
        self._pagination: PaginationState | None = None  # Pagination state
        self._dashboard_visible: bool = True  # Show dashboard on launch

    def compose(self) -> ComposeResult:
        # Header - Epic ASCII banner (enhanced styling)
        yield Static(
            f"[#555]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]\n"
            f"     [bold {ui_colors.GOLD_DIM}]✦[/]  "
            f"[bold {ui_colors.GOLD}]M T G   S P E L L B O O K[/]  "
            f"[bold {ui_colors.GOLD_DIM}]✦[/]     "
            f"[dim]Loading...[/]\n"
            f"[#555]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]",
            id="header-content",
        )

        # Main content area - dashboard (on launch) OR results + details
        with Horizontal(id="main-container"):
            # Dashboard (shown on launch, hidden after first search)
            yield Dashboard(id="dashboard", classes="dashboard-view")

            # Deck panel (hidden by default)
            yield DeckListPanel(id="deck-panel")
            # Collection panel (hidden by default)
            yield CollectionListPanel(id="collection-panel")
            with Vertical(id="results-container", classes="hidden"):
                # Search input integrated into results pane
                yield Input(
                    placeholder="Search: name or t:type c:colors set:code artist:name",
                    id="search-input",
                )
                yield Static("Results", id="results-header")
                yield ResultsList(id="results-list")
            # Enhanced synergy panel (hidden by default)
            yield EnhancedSynergyPanel(id="synergy-panel", classes="hidden")
            with Vertical(id="detail-container", classes="hidden"):
                with Horizontal(id="card-comparison-container"):
                    # Side-by-side: source on left, selected on right
                    yield CardPanel(id="source-card-panel")
                    yield CardPanel(id="card-panel")
                # Deck editor (hidden by default, replaces detail view when active)
                with Vertical(id="deck-editor-container"):
                    yield DeckEditorPanel(id="deck-editor")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize database connections."""
        # Use dark mode for our custom styling
        self.dark = True

        self._db = await self._ctx.get_db()
        self._scryfall = await self._ctx.get_scryfall()
        self._deck_manager = await self._ctx.get_deck_manager()
        self._collection_manager = await self._ctx.get_collection_manager()

        # Load keywords from database and set on card panels
        keywords = await self._ctx.get_keywords()
        for panel in self.query(CardPanel):
            panel.set_keywords(keywords)

        # Initialize deck editor with deck manager
        if self._deck_manager:
            deck_editor = self.query_one("#deck-editor", DeckEditorPanel)
            deck_editor.set_deck_manager(self._deck_manager)

        # Initialize collection panel with collection manager
        if self._collection_manager:
            collection_panel = self.query_one("#collection-panel", CollectionListPanel)
            collection_panel.set_manager(self._collection_manager)

        # Get stats
        stats = await self._db.get_database_stats()
        self._card_count = stats.get("unique_cards", 0)
        self._set_count = stats.get("total_sets", 0)

        # Update header with stats (enhanced styling)
        header = self.query_one("#header-content", Static)
        header.update(
            f"[#555]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]\n"
            f"     [bold {ui_colors.GOLD_DIM}]✦[/]  "
            f"[bold {ui_colors.GOLD}]M T G   S P E L L B O O K[/]  "
            f"[bold {ui_colors.GOLD_DIM}]✦[/]     "
            f"[{ui_colors.GOLD}]{self._card_count:,}[/] [dim]cards[/] "
            f"[#555]·[/] "
            f"[{ui_colors.GOLD}]{self._set_count}[/] [dim]sets[/]\n"
            f"[#555]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
        )

        # Load dashboard with database (background data)
        dashboard = self.query_one("#dashboard", Dashboard)
        if self._db:
            dashboard.set_database(self._db)
            if self._scryfall:
                dashboard.set_scryfall(self._scryfall)
            dashboard.load_dashboard()

        # Focus the search input after app initialization
        dashboard.focus_search()

    async def on_unmount(self) -> None:
        """Clean up database connections and HTTP client on exit."""
        await self._ctx.close()
        await close_http_client()
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

        # Close artist browser if open (user is searching)
        self._close_artist_browser()

        # Hide dashboard when user starts searching
        self._hide_dashboard()

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
        """Handle result selection - card panel auto-updates via highlight."""
        pass  # Card panel updates via ListView.Highlighted event

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

    def _on_help_action(self, action: str | None) -> None:
        """Handle action from help screen."""
        if action is None:
            return

        # Execute the requested action
        if action == "focus_search":
            self.action_focus_input()
        elif action == "random":
            self.lookup_random()
        elif action == "sets":
            self.list_sets()
        elif action == "toggle_deck":
            self.action_toggle_decks()
        elif action == "collection":
            self.action_browse_collection()

    def action_next_tab(self) -> None:
        """Cycle to next view mode (focus -> gallery -> compare)."""
        try:
            from .widgets.art_navigator import EnhancedArtNavigator
            from .widgets.art_navigator.view_toggle import ViewMode

            panel = self.query_one("#card-panel", CardPanel)
            art_nav = panel.query_one(panel.get_child_id("art-navigator"), EnhancedArtNavigator)
            modes = [ViewMode.FOCUS, ViewMode.GALLERY, ViewMode.COMPARE]
            current = art_nav.current_view
            if current in modes:
                idx = modes.index(current)
                art_nav.current_view = modes[(idx + 1) % len(modes)]
        except (LookupError, ValueError):
            pass

    def action_prev_tab(self) -> None:
        """Cycle to previous view mode (focus <- gallery <- compare)."""
        try:
            from .widgets.art_navigator import EnhancedArtNavigator
            from .widgets.art_navigator.view_toggle import ViewMode

            panel = self.query_one("#card-panel", CardPanel)
            art_nav = panel.query_one(panel.get_child_id("art-navigator"), EnhancedArtNavigator)
            modes = [ViewMode.FOCUS, ViewMode.GALLERY, ViewMode.COMPARE]
            current = art_nav.current_view
            if current in modes:
                idx = modes.index(current)
                art_nav.current_view = modes[(idx - 1) % len(modes)]
        except (LookupError, ValueError):
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
        self._hide_dashboard()
        self.lookup_random()

    def action_browse_artists(self) -> None:
        """Browse all artists - hides dashboard automatically."""
        self._hide_dashboard()
        self.browse_artists()

    def action_browse_sets(self) -> None:
        """Browse all sets - hides dashboard automatically."""
        self._hide_dashboard()
        self.browse_sets("")

    def action_browse_decks(self) -> None:
        """Browse decks - hides dashboard automatically."""
        self._hide_dashboard()
        self.action_toggle_decks()

    def action_browse_collection(self) -> None:
        """Open the full collection screen."""
        if self._collection_manager and self._db:
            self.push_screen(
                FullCollectionScreen(self._collection_manager, self._db, self._scryfall)
            )

    @on(CollectionCardSelected)
    def on_collection_card_selected(self, event: CollectionCardSelected) -> None:
        """Handle card selection from collection - show in card panel with correct printing."""
        self.lookup_card(
            event.card_name,
            target_set=event.set_code,
            target_number=event.collector_number,
        )

    def action_add_to_collection(self) -> None:
        """Add the current card to the collection."""
        if not self._current_card:
            self._show_message("[yellow]Select a card first (↑↓ to navigate)[/]")
            return

        self.push_screen(
            AddToCollectionModal(card_name=self._current_card.name),
            callback=self._on_add_to_collection_result,
        )

    def _on_add_to_collection_result(self, result: tuple[str, int, bool] | None) -> None:
        """Handle add to collection modal result."""
        if result is not None and self._collection_manager:
            card_name, quantity, foil = result
            self._do_add_to_collection(card_name, quantity, foil)

    @work
    async def _do_add_to_collection(self, card_name: str, quantity: int, foil: bool) -> None:
        """Actually add the card to the collection."""
        if not self._collection_manager:
            return

        result = await self._collection_manager.add_card(card_name, quantity, foil)
        if result.success:
            self.notify(f"Added {quantity}x {card_name} to collection")
            # Refresh collection panel if visible
            if self._collection_panel_visible:
                collection_panel = self.query_one("#collection-panel", CollectionListPanel)
                collection_panel.refresh_collection()
        else:
            self.notify(result.error or "Failed to add card", severity="error")

    def list_sets(self) -> None:
        """List available sets (not yet implemented)."""
        self.notify("Set browser not yet implemented", severity="warning")

    # ─────────────────────────────────────────────────────────────────────────
    # Deck Management
    # ─────────────────────────────────────────────────────────────────────────

    def action_toggle_decks(self) -> None:
        """Open full-screen deck manager."""
        self._open_deck_screen()

    def action_full_deck_builder(self) -> None:
        """Open full-screen deck manager (alias for toggle_decks)."""
        self._open_deck_screen()

    def _open_deck_screen(self) -> None:
        """Open the full deck management screen."""
        if not self._deck_manager:
            self.notify("Deck manager not available", severity="error")
            return

        from .deck import FullDeckScreen

        self.push_screen(
            FullDeckScreen(
                self._deck_manager,
                self._db,
                self._scryfall,
                self._collection_manager,
            )
        )

    def open_deck(self, deck_id: int) -> None:
        """Open the deck screen with a specific deck selected."""
        if not self._deck_manager:
            self.notify("Deck manager not available", severity="error")
            return

        from .deck import FullDeckScreen

        screen = FullDeckScreen(
            self._deck_manager,
            self._db,
            self._scryfall,
            self._collection_manager,
        )
        # Set deck_id before pushing to avoid race condition during screen mount
        screen.current_deck_id = deck_id
        self.push_screen(screen)

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
        self.push_screen(
            AddToDeckModal(
                self._current_card.name,
                decks,
                set_code=self._current_card.set_code,
                collector_number=self._current_card.number,
            )
        )

    @on(DeckSelected)
    def on_deck_selected(self, event: DeckSelected) -> None:
        """Handle deck selection from deck panel."""
        if event.deck_id == -1:
            # Back to list / close editor signal
            self._close_deck_editor()
            self._refresh_deck_list()
        else:
            # Open deck in editor
            self._open_deck_in_editor(event.deck_id)

    @work
    async def _open_deck_in_editor(self, deck_id: int) -> None:
        """Open a deck in the editor panel."""
        if not self._deck_manager:
            return

        deck = await self._deck_manager.get_deck(deck_id)
        if not deck:
            self.notify("Deck not found", severity="error")
            return

        self._viewing_deck_id = deck_id
        self._deck_editor_visible = True

        # Update deck list to highlight active deck
        deck_panel = self.query_one("#deck-panel", DeckListPanel)
        deck_panel.set_active_deck(deck_id)
        await deck_panel.refresh_decks(self._deck_manager, deck_id)

        # Show editor, hide card panels
        editor_container = self.query_one("#deck-editor-container")
        card_container = self.query_one("#card-comparison-container")
        editor_container.add_class("visible")
        card_container.add_class("hidden")

        # Load deck into editor
        deck_editor = self.query_one("#deck-editor", DeckEditorPanel)
        deck_editor.update_deck(deck)
        deck_editor.focus()

    def _close_deck_editor(self) -> None:
        """Close the deck editor and return to card view."""
        self._deck_editor_visible = False
        self._viewing_deck_id = None

        # Hide editor, show card panels
        editor_container = self.query_one("#deck-editor-container")
        card_container = self.query_one("#card-comparison-container")
        editor_container.remove_class("visible")
        card_container.remove_class("hidden")

        # Clear active deck highlight
        deck_panel = self.query_one("#deck-panel", DeckListPanel)
        deck_panel.set_active_deck(None)

        # Clear editor
        deck_editor = self.query_one("#deck-editor", DeckEditorPanel)
        deck_editor.update_deck(None)

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
                except CardNotFoundError:
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
        self.push_screen(
            AddToDeckModal(
                event.card_name,
                decks,
                set_code=event.set_code,
                collector_number=event.collector_number,
            )
        )

    @on(CardAddedToDeck)
    def on_card_added_to_deck(self, _event: CardAddedToDeck) -> None:
        """Handle card added to deck."""
        self._refresh_deck_list()

    @on(QuickLinkActivated)
    def on_quick_link_activated(self, event: QuickLinkActivated) -> None:
        """Handle quick link activation from dashboard."""
        self._hide_dashboard()
        match event.action:
            case "artists":
                self.action_browse_artists()
            case "sets":
                self.action_browse_sets()
            case "decks":
                self.action_browse_decks()
            case "collection":
                self.action_browse_collection()
            case "random":
                self.action_random_card()

    @on(SearchResultSelected)
    def on_search_result_selected(self, event: SearchResultSelected) -> None:
        """Handle search result selection from dashboard dropdown."""
        self._hide_dashboard()
        # Use uuid for exact printing (e.g., SpongeBob vs regular Jodah)
        self.lookup_card(event.card.name, uuid=event.card.uuid)

    @on(SearchSubmitted)
    def on_search_submitted(self, event: SearchSubmitted) -> None:
        """Handle search submission from dashboard."""
        self._hide_dashboard()
        self.handle_command(event.query)

    def _hide_dashboard(self) -> None:
        """Hide dashboard and show search results view."""
        if self._dashboard_visible:
            self._dashboard_visible = False
            dashboard = self.query_one("#dashboard", Dashboard)
            results = self.query_one("#results-container")
            detail = self.query_one("#detail-container")

            dashboard.add_class("hidden")
            results.remove_class("hidden")
            detail.remove_class("hidden")

    def _show_dashboard(self) -> None:
        """Show dashboard and hide search results view."""
        if not self._dashboard_visible:
            self._dashboard_visible = True
            dashboard = self.query_one("#dashboard", Dashboard)
            results = self.query_one("#results-container")
            detail = self.query_one("#detail-container")

            dashboard.remove_class("hidden")
            results.add_class("hidden")
            detail.add_class("hidden")

            # Reload dashboard content
            if self._db:
                dashboard.set_database(self._db)
                if self._scryfall:
                    dashboard.set_scryfall(self._scryfall)
                dashboard.load_dashboard()

            # Focus the search input
            dashboard.focus_search()

    @on(ArtistBrowserClosed)
    def on_artist_browser_closed(self, _event: ArtistBrowserClosed) -> None:
        """Handle artist browser closed - hide/remove the overlay and show dashboard."""
        self._close_artist_browser()
        # Return to dashboard when closing browser without selection
        self._show_dashboard()

    def _close_artist_browser(self) -> None:
        """Close/hide the artist browser overlay."""
        from textual.css.query import NoMatches

        from .widgets import ArtistBrowser

        try:
            browser = self.query_one("#artist-browser", ArtistBrowser)
            browser.remove()
        except NoMatches:
            pass

    def _open_artist_portfolio(self, artist_name: str, select_card: str | None = None) -> None:
        """Common handler for opening an artist portfolio from any source."""
        self._close_artist_browser()  # Safe to call even if not open
        self.notify(f"Loading cards by {artist_name}...", timeout=2)
        self.show_artist(artist_name, select_card=select_card)

    @on(ArtistSelected)
    def on_artist_selected(self, event: ArtistSelected) -> None:
        """Handle artist selection from artist browser."""
        self._open_artist_portfolio(event.artist.name)

    @on(ArtNavigatorArtistSelected)
    def on_art_navigator_artist_selected(self, event: ArtNavigatorArtistSelected) -> None:
        """Handle artist selection from art navigator (focus view)."""
        self._open_artist_portfolio(event.artist_name, select_card=event.card_name)

    @on(ViewArtwork)
    def on_view_artwork(self, event: ViewArtwork) -> None:
        """Handle view artwork request - show card in main panel."""
        card_name = event.card.name
        self.notify(f"Loading {card_name}...", timeout=2)
        self.lookup_card(card_name)

    @on(ClosePortfolio)
    def on_close_portfolio(self, _event: ClosePortfolio) -> None:
        """Handle close portfolio request."""
        from textual.css.query import NoMatches

        from .widgets import ArtistPortfolioView

        try:
            portfolio = self.query_one("#artist-portfolio", ArtistPortfolioView)
            portfolio.add_class("hidden")
        except NoMatches:
            pass

    @on(SetDetailClosed)
    def on_set_detail_closed(self, _event: SetDetailClosed) -> None:
        """Handle set detail view closed."""
        from textual.css.query import NoMatches

        from .widgets import SetDetailView

        try:
            set_detail = self.query_one("#set-detail", SetDetailView)
            set_detail.add_class("hidden")
        except NoMatches:
            pass

    @on(SynergyPanelClosed)
    def on_synergy_panel_closed(self, _event: SynergyPanelClosed) -> None:
        """Handle synergy panel closed - return to normal view."""
        from textual.css.query import NoMatches

        self._synergy_mode = False
        self._hide_synergy_panel()
        # Hide the enhanced synergy panel
        try:
            synergy_panel = self.query_one("#synergy-panel", EnhancedSynergyPanel)
            synergy_panel.add_class("hidden")
        except NoMatches:
            pass
        # Show the results container again and exit synergy layout mode
        self.query_one("#results-container").remove_class("hidden")
        self.query_one("#main-container").remove_class("synergy-layout")
        self.action_focus_input()

    @on(SynergySelected)
    def on_synergy_selected(self, event: SynergySelected) -> None:
        """Handle synergy card selected - show in card panel."""
        synergy = event.synergy
        # Look up the full card details
        self._load_synergy_card(synergy.name)

    @work
    async def _load_synergy_card(self, card_name: str) -> None:
        """Load and display a synergy card."""
        if not self._db:
            return
        from mtg_core.tools import cards

        try:
            card = await cards.get_card(self._db, self._scryfall, name=card_name)
            self._current_card = card
            self._update_card_panel_with_synergy(card)
            await self._load_card_extras(card)
        except CardNotFoundError:
            pass
