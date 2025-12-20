"""Full-screen deck builder mode with split-pane layout."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.screen import Screen
from textual.widgets import Input, Label, ListItem, ListView, Static

from ..search import parse_search_query
from ..ui.theme import ui_colors
from ..widgets import CardPanel
from .editor_panel import DeckCardItem, DeckEditorPanel
from .quick_filter_bar import QuickFilterBar

if TYPE_CHECKING:
    from mtg_core.data.database import DeckSummary, MTGDatabase, ScryfallDatabase
    from mtg_core.data.models.responses import CardSummary

    from ..deck_manager import DeckManager, DeckWithCards


class SearchResultItem(ListItem):
    """A card in the search results list.

    Uses shared CardResultItem formatting for consistency with main search.
    """

    DEFAULT_CSS = """
    SearchResultItem {
        height: auto;
        min-height: 3;
    }

    SearchResultItem Static {
        width: 100%;
    }
    """

    def __init__(self, card: CardSummary) -> None:
        super().__init__()
        self.card = card

    def compose(self) -> ComposeResult:
        from ..widgets.card_result_item import CardResultFormatter

        yield Static(CardResultFormatter.format(self.card))


class FullDeckBuilder(Screen[None]):
    """Full-screen deck builder with split-pane layout.

    Layout:
    - Left (40%): Search pane with QuickFilterBar and results
    - Right (60%): Deck editor with mainboard/sideboard and stats

    Key features:
    - Tab to switch focus between search and deck
    - Quick-add shortcuts (Space=1x, 1-4=Nx, Shift+Space=sideboard)
    - Real-time filter toggles for CMC/Color/Type
    """

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape", "exit_builder", "Exit", show=True),
        Binding("tab", "switch_pane", "Switch Pane", show=True),
        Binding("slash", "focus_search", "Search", show=True),
        Binding("v", "validate", "Validate", show=True),
        Binding("left_square_bracket", "prev_deck", "Prev Deck", show=True),
        Binding("right_square_bracket", "next_deck", "Next Deck", show=True),
    ]

    CSS = """
    FullDeckBuilder {
        background: #0d0d0d;
    }

    #builder-header {
        height: 3;
        background: #0a0a14;
        border-bottom: heavy #c9a227;
        padding: 0 2;
        content-align: center middle;
    }

    #builder-main {
        width: 100%;
        height: 1fr;
    }

    #search-pane {
        width: 20%;
        height: 100%;
        background: #0f0f0f;
        border-right: solid #3d3d3d;
    }

    #search-header {
        height: 3;
        padding: 0 1;
        background: #1a1a2e;
        border-bottom: solid #3d3d3d;
    }

    #search-input-container {
        height: 3;
        padding: 0 1;
        background: #151515;
        border-bottom: solid #2a2a2a;
    }

    #builder-search-input {
        width: 100%;
        background: #1a1a2e;
        border: tall #3d3d3d;
    }

    #builder-search-input:focus {
        border: tall #c9a227;
        background: #1e1e32;
    }

    #search-results {
        height: 1fr;
        scrollbar-color: #c9a227;
        scrollbar-color-hover: #e6c84a;
    }

    #search-results > ListItem {
        padding: 0 1;
        height: auto;
        border-bottom: solid #1a1a1a;
        background: #121212;
    }

    #search-results > ListItem:hover {
        background: #1a1a2e;
        border-left: solid #5a5a6e;
    }

    #search-results > ListItem.-highlight {
        background: #2a2a4e;
        border-left: heavy #c9a227;
    }

    #search-footer {
        height: 2;
        padding: 0 1;
        background: #1a1a1a;
        border-top: solid #3d3d3d;
        content-align: left middle;
    }

    #card-preview-pane {
        width: 35%;
        height: 100%;
        background: #0d0d0d;
        border-right: solid #3d3d3d;
    }

    #builder-card-panel {
        height: 70%;
    }

    #deck-pane {
        width: 45%;
        height: 100%;
        background: #0d0d0d;
    }

    #builder-footer {
        height: 2;
        padding: 0 2;
        background: #0a0a14;
        border-top: heavy #c9a227;
        content-align: center middle;
    }
    """

    def __init__(
        self,
        deck: DeckWithCards,
        deck_manager: DeckManager,
        db: MTGDatabase,
        scryfall: ScryfallDatabase | None = None,
    ) -> None:
        super().__init__()
        self._deck = deck
        self._deck_manager = deck_manager
        self._db = db
        self._scryfall = scryfall
        self._search_results: list[CardSummary] = []
        self._active_pane: str = "search"  # "search" or "deck"
        self._all_deck_summaries: list[DeckSummary] = []
        self._deck_index: int = 0

    def compose(self) -> ComposeResult:
        # Header
        format_str = f" ({self._deck.format})" if self._deck.format else ""
        yield Static(
            f"[bold {ui_colors.GOLD}]Deck Builder:[/] [bold]{self._deck.name}[/]{format_str}",
            id="builder-header",
        )

        # Main content area - 3 columns: search | card preview | deck
        with Horizontal(id="builder-main"):
            # Search pane (left - 25%)
            with Vertical(id="search-pane"):
                yield Static(
                    f"[bold {ui_colors.GOLD_DIM}]Search[/]",
                    id="search-header",
                )
                with Horizontal(id="search-input-container"):
                    yield Input(
                        placeholder="Search... (t:creature)",
                        id="builder-search-input",
                    )
                yield QuickFilterBar(id="quick-filter-bar")
                yield ListView(id="search-results")
                yield Static(
                    f"[{ui_colors.GOLD}]Space[/] +1  [{ui_colors.GOLD}]1-4[/] +N",
                    id="search-footer",
                )

            # Card preview pane (middle - 35%)
            with Vertical(id="card-preview-pane"):
                yield CardPanel(id="builder-card-panel")

            # Deck pane (right - 40%)
            with Vertical(id="deck-pane"):
                yield DeckEditorPanel(id="builder-deck-editor")

        # Footer with shortcuts
        yield Static(
            f"[{ui_colors.GOLD}]Tab[/] Switch Pane  "
            f"[{ui_colors.GOLD}][ ][/] Prev/Next Deck  "
            f"[{ui_colors.GOLD}]/[/] Search  "
            f"[{ui_colors.GOLD}]V[/] Validate  "
            f"[{ui_colors.GOLD}]Esc[/] Exit",
            id="builder-footer",
        )

    def on_mount(self) -> None:
        """Initialize after mounting."""
        # Set up deck editor
        editor = self.query_one("#builder-deck-editor", DeckEditorPanel)
        editor.set_deck_manager(self._deck_manager)
        editor.update_deck(self._deck)

        # Load all decks for switching
        self._load_decks()

        # Load first deck card into preview
        self._load_first_deck_card()

        # Focus search input
        self.query_one("#builder-search-input", Input).focus()

    @work
    async def _load_decks(self) -> None:
        """Load all deck summaries and find current index."""
        self._all_deck_summaries = await self._deck_manager.list_decks()
        # Find current deck's index
        for i, deck in enumerate(self._all_deck_summaries):
            if deck.id == self._deck.id:
                self._deck_index = i
                break
        self._update_header()

    @work
    async def _load_first_deck_card(self) -> None:
        """Load the first deck card into the preview panel."""
        # Get first card from deck (mainboard preferred, then sideboard)
        cards = self._deck.mainboard or self._deck.sideboard
        if not cards:
            return

        first_card = cards[0]

        # Select first item in mainboard list
        editor = self.query_one("#builder-deck-editor", DeckEditorPanel)
        try:
            mainboard_list = editor.query_one("#mainboard-list", ListView)
            if mainboard_list.children:
                mainboard_list.index = 0
        except Exception:
            pass

        # Load card into preview panel
        panel = self.query_one("#builder-card-panel", CardPanel)
        await panel.load_printings(
            self._scryfall,
            self._db,
            first_card.card_name,
        )

    def action_exit_builder(self) -> None:
        """Exit the deck builder."""
        self.dismiss()

    def action_switch_pane(self) -> None:
        """Switch focus between search and deck panes."""
        if self._active_pane == "search":
            self._active_pane = "deck"
            editor = self.query_one("#builder-deck-editor", DeckEditorPanel)
            # Focus the mainboard list in the editor
            try:
                mainboard = editor.query_one("#mainboard-list", ListView)
                mainboard.focus()
            except Exception:
                editor.focus()
        else:
            self._active_pane = "search"
            results = self.query_one("#search-results", ListView)
            if results.children:
                results.focus()
            else:
                self.query_one("#builder-search-input", Input).focus()

    def action_focus_search(self) -> None:
        """Focus the search input."""
        self._active_pane = "search"
        self.query_one("#builder-search-input", Input).focus()

    def action_validate(self) -> None:
        """Validate the deck."""
        editor = self.query_one("#builder-deck-editor", DeckEditorPanel)
        editor.action_validate()

    def _update_header(self) -> None:
        """Update header with current deck info and position."""
        format_str = f" ({self._deck.format})" if self._deck.format else ""
        if len(self._all_deck_summaries) > 1:
            pos = f" [{self._deck_index + 1}/{len(self._all_deck_summaries)}]"
        else:
            pos = ""
        header = self.query_one("#builder-header", Static)
        header.update(
            f"[bold {ui_colors.GOLD}]Deck Builder:[/] [bold]{self._deck.name}[/]{format_str}{pos}"
        )

    @work
    async def action_prev_deck(self) -> None:
        """Switch to the previous deck."""
        if len(self._all_deck_summaries) <= 1:
            self.notify("No other decks to switch to", timeout=2)
            return
        self._deck_index = (self._deck_index - 1) % len(self._all_deck_summaries)
        await self._switch_to_deck(self._deck_index)

    @work
    async def action_next_deck(self) -> None:
        """Switch to the next deck."""
        if len(self._all_deck_summaries) <= 1:
            self.notify("No other decks to switch to", timeout=2)
            return
        self._deck_index = (self._deck_index + 1) % len(self._all_deck_summaries)
        await self._switch_to_deck(self._deck_index)

    async def _switch_to_deck(self, index: int) -> None:
        """Switch to deck at given index."""
        deck_id = self._all_deck_summaries[index].id
        deck = await self._deck_manager.get_deck(deck_id)
        if deck:
            self._deck = deck
            editor = self.query_one("#builder-deck-editor", DeckEditorPanel)
            editor.update_deck(deck)
            self._update_header()

    @on(Input.Submitted, "#builder-search-input")
    def on_search_submitted(self, event: Input.Submitted) -> None:
        """Handle search submission."""
        query = event.value.strip()
        if query:
            self._do_search(query)

    @on(Input.Changed, "#builder-search-input")
    def on_search_changed(self, event: Input.Changed) -> None:
        """Handle search input changes for live search."""
        query = event.value.strip()
        if len(query) >= 2:
            self._do_search(query)
        elif not query:
            self._clear_results()

    @work
    async def _do_search(self, query: str) -> None:
        """Execute search with current filters."""
        from mtg_core.tools import cards as card_tools

        # Get filter state from QuickFilterBar
        filter_bar = self.query_one("#quick-filter-bar", QuickFilterBar)
        filters = filter_bar.get_filters()

        # Parse the query
        search_input = parse_search_query(query)

        # Apply filter bar filters
        if filters.get("cmc") is not None:
            search_input.cmc = filters["cmc"]
        if filters.get("colors"):
            search_input.colors = filters["colors"]
        if filters.get("type"):
            search_input.type = filters["type"]

        # Limit results for performance
        search_input.page_size = 50

        try:
            result = await card_tools.search_cards(self._db, self._scryfall, search_input)
            self._search_results = result.cards
            self._update_search_results()
        except Exception as e:
            self.notify(f"Search error: {e}", severity="error")

    def _update_search_results(self) -> None:
        """Update the search results list."""
        results_list = self.query_one("#search-results", ListView)
        results_list.clear()

        if not self._search_results:
            results_list.append(ListItem(Label("[dim]No results. Try a different search.[/]")))
            return

        for card in self._search_results:
            results_list.append(SearchResultItem(card))

        # Update header with count
        header = self.query_one("#search-header", Static)
        header.update(
            f"[bold {ui_colors.GOLD_DIM}]Results[/] "
            f"[{ui_colors.GOLD}]{len(self._search_results)}[/]"
        )

    def _clear_results(self) -> None:
        """Clear search results."""
        self._search_results = []
        results_list = self.query_one("#search-results", ListView)
        results_list.clear()
        header = self.query_one("#search-header", Static)
        header.update(f"[bold {ui_colors.GOLD_DIM}]Search & Browse[/]")

    def on_key(self, event: Key) -> None:
        """Handle key events for quick-add shortcuts."""
        # Only handle when search results are focused
        results_list = self.query_one("#search-results", ListView)
        if not results_list.has_focus:
            return

        highlighted = results_list.highlighted_child
        if not highlighted or not isinstance(highlighted, SearchResultItem):
            return

        card = highlighted.card

        # Space = add 1x to mainboard
        if event.key == "space":
            self._quick_add(
                card.name,
                1,
                sideboard=False,
                set_code=card.set_code,
                collector_number=card.collector_number,
            )
            event.stop()
            event.prevent_default()

        # Shift+Space = add 1x to sideboard
        elif event.key == "shift+space":
            self._quick_add(
                card.name,
                1,
                sideboard=True,
                set_code=card.set_code,
                collector_number=card.collector_number,
            )
            event.stop()
            event.prevent_default()

        # 1-4 = add Nx to mainboard
        elif event.key in ("1", "2", "3", "4"):
            qty = int(event.key)
            self._quick_add(
                card.name,
                qty,
                sideboard=False,
                set_code=card.set_code,
                collector_number=card.collector_number,
            )
            event.stop()
            event.prevent_default()

    @work
    async def _quick_add(
        self,
        card_name: str,
        quantity: int,
        sideboard: bool,
        set_code: str | None = None,
        collector_number: str | None = None,
    ) -> None:
        """Quickly add a card to the deck."""
        result = await self._deck_manager.add_card(
            self._deck.id,
            card_name,
            quantity,
            sideboard=sideboard,
            set_code=set_code,
            collector_number=collector_number,
        )

        if result.success:
            location = "sideboard" if sideboard else "mainboard"
            self.notify(
                f"[{ui_colors.GOLD}]+{quantity}x[/] {card_name} ({location})",
                timeout=2,
            )
            # Refresh deck display
            await self._refresh_deck()
        else:
            self.notify(result.error or "Failed to add card", severity="error")

    async def _refresh_deck(self) -> None:
        """Refresh the deck data and editor."""
        updated = await self._deck_manager.get_deck(self._deck.id)
        if updated:
            self._deck = updated
            editor = self.query_one("#builder-deck-editor", DeckEditorPanel)
            editor.update_deck(updated)

    @on(QuickFilterBar.FiltersChanged)
    def on_filters_changed(self, _event: QuickFilterBar.FiltersChanged) -> None:
        """Handle filter changes from QuickFilterBar."""
        # Re-run search with new filters
        search_input = self.query_one("#builder-search-input", Input)
        query = search_input.value.strip()
        if query:
            self._do_search(query)

    @on(ListView.Highlighted, "#search-results")
    def on_search_highlighted(self, event: ListView.Highlighted) -> None:
        """Update card preview when search result is highlighted."""
        if isinstance(event.item, SearchResultItem):
            card = event.item.card
            self._load_card_preview(card)

    @on(ListView.Highlighted, "#mainboard-list")
    @on(ListView.Highlighted, "#sideboard-list")
    def on_deck_card_highlighted(self, event: ListView.Highlighted) -> None:
        """Update card preview when deck card is highlighted."""
        if isinstance(event.item, DeckCardItem):
            self._load_card_by_name(
                event.item.card_name,
                set_code=event.item.set_code,
                collector_number=event.item.collector_number,
            )

    @work
    async def _load_card_by_name(
        self,
        card_name: str,
        set_code: str | None = None,
        collector_number: str | None = None,
    ) -> None:
        """Load card into preview panel by name, optionally targeting a specific printing."""
        panel = self.query_one("#builder-card-panel", CardPanel)
        await panel.load_printings(
            self._scryfall,
            self._db,
            card_name,
            target_set=set_code,
            target_number=collector_number,
        )

    @work
    async def _load_card_preview(self, card: CardSummary) -> None:
        """Load card into preview panel."""
        panel = self.query_one("#builder-card-panel", CardPanel)
        await panel.load_printings(
            self._scryfall,
            self._db,
            card.name,
            flavor_name=card.flavor_name,
            target_set=card.set_code,
        )
