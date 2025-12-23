"""Full-screen deck management with search, editing, and beautiful stats."""

from __future__ import annotations

import asyncio
import contextlib
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

from textual import events, on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import Input, ListItem, ListView, Static

from ..collection.card_preview import CollectionCardPreview
from ..recommendations.messages import AddCardToDeck
from ..screens import BaseScreen
from ..ui.theme import ui_colors
from ..widgets.card_result_item import CardResultItem
from ..widgets.recommendation_detail import (
    RecommendationDetailCollapse,
    RecommendationDetailView,
)
from .analysis_panel import DeckAnalysisPanel
from .editor_panel import SortOrder
from .list_panel import DeckListItem
from .messages import CardAddedToDeck
from .modals import ConfirmDeleteModal, NewDeckModal

if TYPE_CHECKING:
    from mtg_core.data.database import UnifiedDatabase
    from mtg_core.data.database.user import DeckSummary
    from mtg_core.data.models.responses import CardSummary
    from mtg_core.tools.recommendations import HybridRecommender
    from mtg_core.tools.recommendations.hybrid import ScoredRecommendation

    from ..collection_manager import CollectionManager
    from ..deck_manager import DeckCardWithData, DeckManager, DeckWithCards


class ViewMode(Enum):
    """Current view mode."""

    DECK_LIST = "deck_list"  # Viewing deck list, no deck selected
    DECK_VIEW = "deck_view"  # Viewing/editing a deck
    CARD_SEARCH = "card_search"  # Searching for cards to add


class DeckCardAdapter:
    """Adapter to make DeckCardWithData compatible with CardLike protocol.

    Uses attributes (not properties) to satisfy Protocol requirements.
    """

    name: str
    mana_cost: str | None
    type: str | None
    rarity: str | None
    set_code: str | None
    flavor_name: str | None
    # Extra fields for deck display
    quantity: int
    is_owned: bool | None

    def __init__(self, card_data: DeckCardWithData, is_owned: bool | None = None) -> None:
        card = card_data.card
        self.name = card_data.card_name
        self.mana_cost = card.mana_cost if card else None
        self.type = card.type if card else None
        self.rarity = card.rarity if card else None
        self.set_code = card_data.set_code or (card.set_code if card else None)
        self.flavor_name = card.flavor_name if card else None
        self.quantity = card_data.quantity
        self.is_owned = is_owned
        self.collector_number = card_data.collector_number


class DeckCardResultItem(ListItem):
    """Card item for deck list showing quantity and ownership.

    Similar to CardResultItem but with deck-specific display.
    """

    DEFAULT_CSS = """
    DeckCardResultItem {
        height: auto;
        min-height: 3;
        padding: 0 1;
        background: #121218;
    }

    DeckCardResultItem:hover {
        background: #1a1a2e;
    }

    DeckCardResultItem.-highlight {
        background: #2a2a4e;
    }
    """

    def __init__(self, card: DeckCardAdapter) -> None:
        super().__init__()
        self.card = card
        self.card_name = card.name  # For event handlers

    def compose(self) -> ComposeResult:
        from textual.widgets import Label

        yield Label(self._format_card())

    def _format_card(self) -> str:
        """Format the card for display."""
        from ..formatting import prettify_mana
        from ..ui.formatters import CardFormatters

        card = self.card

        # Ownership indicator
        if card.is_owned is True:
            owned_indicator = "[green]✓[/] "
        elif card.is_owned is False:
            owned_indicator = "[yellow]⚠[/] "
        else:
            owned_indicator = ""

        # Quantity
        qty_color = ui_colors.GOLD if card.quantity > 1 else "white"
        qty_str = f"[{qty_color}]{card.quantity}x[/] "

        # Get formatting helpers
        rarity_color = CardFormatters.get_rarity_color(card.rarity)
        rarity_symbol = CardFormatters.get_rarity_symbol(card.rarity)
        type_icon = CardFormatters.get_type_icon(card.type or "")
        type_color = CardFormatters.get_type_color(card.type or "")

        # Mana cost
        mana = prettify_mana(card.mana_cost or "")

        # Build Line 1: owned + qty + rarity symbol + name + mana
        line1 = f"{owned_indicator}{qty_str}[{rarity_color}]{rarity_symbol}[/] [bold {rarity_color}]{card.name}[/]"
        if mana:
            line1 += f"  {mana}"

        # Build Line 2: type icon + type + set
        line2_parts = []
        if type_icon:
            line2_parts.append(f"[{type_color}]{type_icon}[/]")
        if card.type:
            line2_parts.append(f"[dim]{card.type}[/]")
        if card.set_code:
            line2_parts.append(f"[dim]{card.set_code.upper()}[/]")

        line2 = "      " + "  ".join(line2_parts) if line2_parts else "      "

        return f"{line1}\n{line2}"


class FullDeckScreen(BaseScreen[None]):
    """Full-screen deck management interface.

    Three-pane layout:
    - Left: Deck list (always visible)
    - Middle: Deck contents or search results
    - Right: Stats panel or card preview

    Features:
    - Create, edit, delete decks
    - Search cards to add to decks
    - Beautiful statistics and analysis
    - Keyboard-driven workflow
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "back", "Back", show=True),
        Binding("n", "new_deck", "New Deck", show=True),
        Binding("slash", "focus_search", "Search", show=True),
        Binding("tab", "cycle_focus", "Switch Pane", show=False),
        Binding("shift+tab", "cycle_focus_reverse", "Switch Pane Back", show=False),
        # Deck editing
        Binding("plus,equal", "increase_qty", "+1", show=False),
        Binding("minus", "decrease_qty", "-1", show=False),
        Binding("delete", "remove_card", "Remove", show=False),
        Binding("s", "toggle_sideboard", "Sideboard", show=False),
        Binding("o", "cycle_sort", "Sort", show=False),
        Binding("v", "validate", "Validate", show=True),
        Binding("r", "recommend", "Recommend", show=True),
        Binding("a", "toggle_analysis", "Analysis", show=True),
        # Navigation
        Binding("up,k", "nav_up", "Up", show=False),
        Binding("down,j", "nav_down", "Down", show=False),
        # Quick add from search
        Binding("space", "quick_add_1", "Add 1x", show=False),
        Binding("1", "quick_add_1", "Add 1x", show=False),
        Binding("2", "quick_add_2", "Add 2x", show=False),
        Binding("3", "quick_add_3", "Add 3x", show=False),
        Binding("4", "quick_add_4", "Add 4x", show=False),
        # Recommendation details
        Binding("e,enter", "expand_recommendation", "Why?", show=False),
    ]

    # Don't show footer - this screen has its own footer
    show_footer: ClassVar[bool] = False

    CSS = """
    FullDeckScreen {
        background: #0d0d0d;
    }

    /* Override screen-content to use grid for proper height distribution */
    FullDeckScreen #screen-content {
        layout: grid;
        grid-size: 1;
        grid-rows: 4 1fr;
    }

    #deck-screen-header {
        background: #0a0a14;
        border-bottom: heavy #c9a227;
        padding: 0 2;
        content-align: center middle;
    }

    /* Grid child must fill its row; use grid layout for proper height distribution */
    #deck-screen-body {
        width: 100%;
        height: 1fr;
        layout: grid;
        grid-size: 1;
        grid-rows: 1fr auto;  /* main, footer */
    }

    #deck-screen-main {
        width: 100%;
        height: 100%;
    }

    /* Left pane - deck list */
    #deck-list-pane {
        width: 20;
        height: 100%;
        background: #0f0f0f;
        border-right: solid #3d3d3d;
    }

    #deck-list-header {
        height: 2;
        padding: 0 1;
        background: #1a1a1a;
        border-bottom: solid #3d3d3d;
    }

    #deck-list {
        height: 1fr;
        scrollbar-color: #c9a227;
    }

    #deck-list > ListItem {
        padding: 0 1;
        height: auto;
        min-height: 2;
    }

    #deck-list > ListItem:hover {
        background: #1a1a2e;
    }

    #deck-list > ListItem.-highlight {
        background: #2a2a4e;
        border-left: heavy #c9a227;
    }

    /* Middle pane - deck contents */
    #deck-content-pane {
        width: 1fr;
        height: 100%;
        background: #0a0a14;
    }

    #deck-search-container {
        height: auto;
        padding: 0 1;
        background: #151520;
        border-bottom: solid #3d3d3d;
    }

    #deck-search-input {
        width: 100%;
        background: #0d0d0d;
        border: solid #3d3d3d;
    }

    #deck-search-input:focus {
        border: solid #c9a227;
    }

    #deck-content-header {
        height: 2;
        padding: 0 1;
        background: #1a1a1a;
        border-bottom: solid #3d3d3d;
    }

    #mainboard-list, #sideboard-list, #search-results-list {
        height: 1fr;
        scrollbar-color: #c9a227;
    }

    #mainboard-list > ListItem, #sideboard-list > ListItem, #search-results-list > ListItem {
        padding: 0 1;
        height: auto;
    }

    #mainboard-list > ListItem:hover, #sideboard-list > ListItem:hover, #search-results-list > ListItem:hover {
        background: #1a1a2e;
    }

    #mainboard-list > ListItem.-highlight, #sideboard-list > ListItem.-highlight, #search-results-list > ListItem.-highlight {
        background: #2a2a4e;
        border-left: heavy #c9a227;
    }

    #sideboard-header {
        height: 2;
        padding: 0 1;
        background: #1a1a1a;
        border-top: solid #3d3d3d;
        border-bottom: solid #3d3d3d;
    }

    /* Right pane - analysis and card preview */
    #deck-preview-pane {
        width: 1fr;
        min-width: 45;
        height: 100%;
        background: #0d0d0d;
        border-left: solid #3d3d3d;
    }

    #deck-card-preview {
        width: 100%;
        height: 100%;
        display: none;  /* Hidden by default, shown when card highlighted */
    }

    #deck-card-preview.visible {
        display: block;
    }

    #deck-analysis-panel {
        width: 100%;
        height: 100%;
    }

    #deck-analysis-panel.hidden {
        display: none;
    }

    #deck-screen-footer {
        height: 2;
        padding: 0 2;
        background: #1a1a1a;
        border-top: solid #3d3d3d;
    }

    /* Hide/show based on mode */
    .search-mode #mainboard-container {
        display: none;
    }

    .search-mode #search-results-container {
        display: block;
    }

    #search-results-container {
        display: none;
        height: 100%;
    }

    #mainboard-container {
        height: 100%;
    }
    """

    # Reactive state
    current_view: reactive[ViewMode] = reactive(ViewMode.DECK_LIST)
    current_deck_id: reactive[int | None] = reactive(None)

    def __init__(
        self,
        deck_manager: DeckManager,
        db: UnifiedDatabase | None = None,
        collection_manager: CollectionManager | None = None,
    ) -> None:
        super().__init__()
        self._deck_manager = deck_manager
        self._db = db
        self._collection_manager = collection_manager
        self._collection_cards: set[str] = set()
        self._current_deck: DeckWithCards | None = None
        self._decks: list[DeckSummary] = []
        self._search_results: list[CardSummary] = []
        self._card_sort_order: SortOrder = SortOrder.NAME
        self._active_list: str = "mainboard"  # mainboard, sideboard, or search
        self._recommender: HybridRecommender | None = None
        self._recommender_initializing: bool = False
        self._recommendation_details: dict[str, ScoredRecommendation] = {}

    def compose_content(self) -> ComposeResult:
        yield Static(
            f"[bold {ui_colors.GOLD}]🗂 DECK MANAGER[/]",
            id="deck-screen-header",
        )

        with Vertical(id="deck-screen-body"):
            with Horizontal(id="deck-screen-main"):
                # Left pane - deck list
                with Vertical(id="deck-list-pane"):
                    yield Static(
                        f"[{ui_colors.GOLD_DIM}]My Decks[/]",
                        id="deck-list-header",
                    )
                    yield ListView(id="deck-list")

                # Middle pane - deck contents or search
                with Vertical(id="deck-content-pane"):
                    with Vertical(id="deck-search-container"):
                        yield Input(
                            placeholder="Search cards to add...",
                            id="deck-search-input",
                        )

                    # Deck contents (mainboard + sideboard)
                    with Vertical(id="mainboard-container"):
                        yield Static(
                            "[dim]Select a deck from the list[/]",
                            id="deck-content-header",
                        )
                        yield ListView(id="mainboard-list")
                        yield Static(
                            f"[{ui_colors.GOLD_DIM}]Sideboard[/]",
                            id="sideboard-header",
                        )
                        yield ListView(id="sideboard-list")

                    # Search results (hidden by default)
                    with Vertical(id="search-results-container"):
                        yield Static(
                            f"[{ui_colors.GOLD_DIM}]Search Results[/]",
                            id="search-results-header",
                        )
                        yield ListView(id="search-results-list")
                        # Recommendation detail view (inside container so it's visible)
                        yield RecommendationDetailView(id="recommendation-detail")

                # Right pane - analysis panel (default) and card preview (on highlight)
                with Vertical(id="deck-preview-pane"):
                    yield DeckAnalysisPanel(id="deck-analysis-panel")
                    yield CollectionCardPreview(id="deck-card-preview")

            # Footer with context-sensitive hints
            yield Static(
                self._render_footer(),
                id="deck-screen-footer",
            )

    async def on_mount(self) -> None:
        """Load decks on mount."""
        self._load_decks()

        # Focus deck list
        try:
            deck_list = self.query_one("#deck-list", ListView)
            deck_list.focus()
        except NoMatches:
            pass

    def _render_footer(self) -> str:
        """Render footer based on current view mode."""
        if self.current_view == ViewMode.CARD_SEARCH:
            # Show 'e' hint when viewing recommendations
            if self._recommendation_details:
                return (
                    f"[{ui_colors.GOLD}]1-4[/]:Add  "
                    f"[{ui_colors.GOLD}]e[/]:Why?  "
                    f"[{ui_colors.GOLD}]Esc[/]:Back  "
                )
            return (
                f"[{ui_colors.GOLD}]1-4[/]:Add  "
                f"[{ui_colors.GOLD}]Space[/]:Add 1x  "
                f"[{ui_colors.GOLD}]Esc[/]:Back to deck  "
            )
        elif self.current_view == ViewMode.DECK_VIEW:
            return (
                f"[{ui_colors.GOLD}]+/-[/]:Qty  "
                f"[{ui_colors.GOLD}]s[/]:Side  "
                f"[{ui_colors.GOLD}]o[/]:Sort  "
                f"[{ui_colors.GOLD}]a[/]:Analysis  "
                f"[{ui_colors.GOLD}]r[/]:Recommend  "
                f"[{ui_colors.GOLD}]/[/]:Search  "
                f"[{ui_colors.GOLD}]Esc[/]:Back"
            )
        else:
            return (
                f"[{ui_colors.GOLD}]n[/]:New Deck  "
                f"[{ui_colors.GOLD}]Enter[/]:Open  "
                f"[{ui_colors.GOLD}]d[/]:Delete  "
                f"[{ui_colors.GOLD}]Esc[/]:Exit"
            )

    def _update_footer(self) -> None:
        """Update footer text."""
        try:
            footer = self.query_one("#deck-screen-footer", Static)
            footer.update(self._render_footer())
        except NoMatches:
            pass

    @work
    async def _load_decks(self) -> None:
        """Load deck list from database."""
        self._decks = await self._deck_manager.list_decks()
        self._populate_deck_list()

    def _populate_deck_list(self) -> None:
        """Populate the deck list widget."""
        try:
            deck_list = self.query_one("#deck-list", ListView)
            deck_list.clear()

            if not self._decks:
                deck_list.append(ListItem(Static("[dim]No decks yet.\nPress N to create.[/]")))
            else:
                for deck in self._decks:
                    is_active = deck.id == self.current_deck_id
                    deck_list.append(DeckListItem(deck, is_active=is_active))
        except NoMatches:
            pass

    def watch_current_view(self, new_view: ViewMode) -> None:
        """React to view mode changes."""
        self._update_footer()

        # Toggle search mode class
        try:
            content_pane = self.query_one("#deck-content-pane", Vertical)
            if new_view == ViewMode.CARD_SEARCH:
                content_pane.add_class("search-mode")
            else:
                content_pane.remove_class("search-mode")
        except NoMatches:
            pass

    def watch_current_deck_id(self, new_id: int | None) -> None:
        """React to deck selection changes."""
        if new_id is not None:
            self._load_deck(new_id)
        else:
            self._current_deck = None
            self._clear_deck_display()

    @work
    async def _load_deck(self, deck_id: int) -> None:
        """Load a deck's full data and prices."""
        deck = await self._deck_manager.get_deck(deck_id)
        self._current_deck = deck
        self.current_view = ViewMode.DECK_VIEW

        # Load collection card names if not already loaded
        if self._collection_manager and not self._collection_cards:
            self._collection_cards = await self._collection_manager.get_collection_card_names()

        # Fetch prices from Scryfall
        prices = await self._fetch_deck_prices(deck)

        self._refresh_deck_display(prices=prices)

    async def _fetch_deck_prices(self, deck: DeckWithCards | None) -> dict[str, float]:
        """Fetch prices for all cards in the deck."""
        if deck is None or self._db is None:
            return {}

        card_names = list({c.card_name for c in deck.cards})
        prices: dict[str, float] = {}

        try:
            # Use batch lookup for prices
            cards = await self._db.get_cards_by_names(card_names, include_extras=False)
            for name, card in cards.items():
                if card and card.price_usd:
                    prices[name] = card.price_usd / 100  # Convert cents to dollars
        except Exception:
            pass

        return prices

    def _refresh_deck_display(self, prices: dict[str, float] | None = None) -> None:
        """Refresh the deck contents display."""
        deck = self._current_deck

        try:
            header = self.query_one("#deck-content-header", Static)
            mainboard = self.query_one("#mainboard-list", ListView)
            sideboard = self.query_one("#sideboard-list", ListView)
            side_header = self.query_one("#sideboard-header", Static)

            mainboard.clear()
            sideboard.clear()

            if deck is None:
                header.update("[dim]Select a deck from the list[/]")
                return

            # Update header with ownership counts if available
            format_str = f" ({deck.format})" if deck.format else ""
            sort_label = {"name": "A-Z", "cmc": "CMC", "type": "Type"}[self._card_sort_order.value]

            # Count owned/needed for header
            owned_count = 0
            needed_count = 0
            if self._collection_cards:
                for card in deck.mainboard:
                    if card.card_name in self._collection_cards:
                        owned_count += 1
                    else:
                        needed_count += 1

            if self._collection_cards and needed_count > 0:
                header.update(
                    f"[bold {ui_colors.GOLD}]{deck.name}[/]{format_str}  "
                    f"[green]✓{owned_count}[/] [yellow]⚠{needed_count}[/]  "
                    f"[dim]Sort:[/] [{ui_colors.GOLD}]{sort_label}[/]"
                )
            else:
                header.update(
                    f"[bold {ui_colors.GOLD}]{deck.name}[/]{format_str}  "
                    f"[dim]Mainboard[/] [{ui_colors.GOLD}]{deck.mainboard_count}[/]  "
                    f"[dim]Sort:[/] [{ui_colors.GOLD}]{sort_label}[/]"
                )

            # Split mainboard into owned/needed (owned first)
            sorted_main = self._sort_cards(deck.mainboard)
            owned_main = []
            needed_main = []

            if self._collection_cards:
                for card in sorted_main:
                    if card.card_name in self._collection_cards:
                        owned_main.append(card)
                    else:
                        needed_main.append(card)

                # Populate with owned first, then needed
                for card in owned_main:
                    mainboard.append(
                        self._create_card_item(card, is_sideboard=False, is_owned=True)
                    )
                for card in needed_main:
                    mainboard.append(
                        self._create_card_item(card, is_sideboard=False, is_owned=False)
                    )
            else:
                # No collection data - show all without ownership info
                for card in sorted_main:
                    mainboard.append(self._create_card_item(card, is_sideboard=False))

            # Update sideboard header and list
            side_header.update(
                f"[{ui_colors.GOLD_DIM}]Sideboard[/] [{ui_colors.GOLD}]{deck.sideboard_count}[/]"
            )
            sorted_side = self._sort_cards(deck.sideboard)
            for card in sorted_side:
                is_owned = (
                    card.card_name in self._collection_cards if self._collection_cards else None
                )
                sideboard.append(self._create_card_item(card, is_sideboard=True, is_owned=is_owned))

            # Update analysis panel
            self._update_analysis_panel(prices)

            # Update deck list to show active deck
            self._populate_deck_list()

            # Show analysis panel by default (hide card preview)
            self._show_analysis_panel()

        except NoMatches:
            pass

    def _clear_deck_display(self) -> None:
        """Clear deck display when no deck selected."""
        try:
            header = self.query_one("#deck-content-header", Static)
            header.update("[dim]Select a deck from the list[/]")
            self.query_one("#mainboard-list", ListView).clear()
            self.query_one("#sideboard-list", ListView).clear()
            # Clear analysis panel
            self.query_one("#deck-analysis-panel", DeckAnalysisPanel).update_analysis(None)
        except NoMatches:
            pass

    def _update_analysis_panel(self, prices: dict[str, float] | None = None) -> None:
        """Update the analysis panel with current deck data."""
        try:
            analysis = self.query_one("#deck-analysis-panel", DeckAnalysisPanel)
            analysis.update_analysis(
                self._current_deck,
                collection_cards=self._collection_cards or None,
                prices=prices,
            )
        except NoMatches:
            pass

    def _show_analysis_panel(self) -> None:
        """Show analysis panel, hide card preview."""
        try:
            analysis = self.query_one("#deck-analysis-panel", DeckAnalysisPanel)
            preview = self.query_one("#deck-card-preview", CollectionCardPreview)
            analysis.remove_class("hidden")
            preview.remove_class("visible")
        except NoMatches:
            pass

    def _show_card_preview(self) -> None:
        """Show card preview, hide analysis panel."""
        try:
            analysis = self.query_one("#deck-analysis-panel", DeckAnalysisPanel)
            preview = self.query_one("#deck-card-preview", CollectionCardPreview)
            analysis.add_class("hidden")
            preview.add_class("visible")
        except NoMatches:
            pass

    def _sort_cards(self, cards: list[DeckCardWithData]) -> list[DeckCardWithData]:
        """Sort cards based on current sort order."""
        if self._card_sort_order == SortOrder.NAME:
            return sorted(cards, key=lambda c: c.card_name.lower())
        elif self._card_sort_order == SortOrder.CMC:
            return sorted(
                cards,
                key=lambda c: (c.card.cmc or 0 if c.card else 0, c.card_name.lower()),
            )
        elif self._card_sort_order == SortOrder.TYPE:
            type_order = {
                "Creature": 0,
                "Planeswalker": 1,
                "Instant": 2,
                "Sorcery": 3,
                "Artifact": 4,
                "Enchantment": 5,
                "Land": 6,
            }

            def type_key(c: DeckCardWithData) -> tuple[int, str]:
                if c.card and c.card.type:
                    for t, order in type_order.items():
                        if t in c.card.type:
                            return (order, c.card_name.lower())
                return (99, c.card_name.lower())

            return sorted(cards, key=type_key)
        return list(cards)

    def _create_card_item(
        self,
        card: DeckCardWithData,
        is_sideboard: bool,  # noqa: ARG002
        is_owned: bool | None = None,
    ) -> DeckCardResultItem:
        """Create a DeckCardResultItem from card data."""
        adapter = DeckCardAdapter(card, is_owned=is_owned)
        return DeckCardResultItem(adapter)

    def _update_preview_from_deck_card(self, card_name: str) -> None:
        """Update preview pane from a deck card."""
        if not self._current_deck:
            return

        # Find the card in the current deck
        deck_card = None
        for c in self._current_deck.cards:
            if c.card_name == card_name:
                deck_card = c
                break

        if deck_card:
            self._load_deck_card_preview(deck_card)

    def _update_preview_from_search(self, card: CardSummary) -> None:
        """Update preview pane from a search result."""
        self._load_search_card_preview(card.name, card.set_code)

    @work(exclusive=True, group="preview")
    async def _load_deck_card_preview(self, deck_card: DeckCardWithData) -> None:
        """Load deck card into CollectionCardPreview."""
        try:
            preview = self.query_one("#deck-card-preview", CollectionCardPreview)

            # Create a fake CollectionCardWithData for the preview
            # This is a workaround since CollectionCardPreview expects that type
            from ..collection_manager import CollectionCardWithData

            fake_collection_card = CollectionCardWithData(
                card_name=deck_card.card_name,
                quantity=deck_card.quantity,
                foil_quantity=0,
                in_deck_count=0,
                set_code=deck_card.set_code,
                collector_number=deck_card.collector_number,
                card=deck_card.card,
                deck_usage=[],  # Will be populated below
            )

            # Get deck usage for this card
            deck_usage = []
            if self._deck_manager:
                decks = await self._deck_manager.list_decks()
                for deck in decks:
                    full_deck = await self._deck_manager.get_deck(deck.id)
                    if full_deck:
                        for card in full_deck.cards:
                            if card.card_name == deck_card.card_name:
                                deck_usage.append((full_deck.name, card.quantity))
                                break

            preview.update_card(fake_collection_card, deck_usage)

            # Load image and prices
            await preview.load_printing(
                self._db,
                deck_card.card_name,
                deck_card.set_code,
                deck_card.collector_number,
            )

        except NoMatches:
            pass

    @work(exclusive=True, group="preview")
    async def _load_search_card_preview(self, card_name: str, set_code: str | None) -> None:
        """Load search result card into CollectionCardPreview."""
        try:
            preview = self.query_one("#deck-card-preview", CollectionCardPreview)

            # For search results, we don't have full card data, just load the printing
            await preview.load_printing(
                self._db,
                card_name,
                set_code,
                None,
            )

        except NoMatches:
            pass

    # ===== Event handlers =====

    @on(ListView.Selected, "#deck-list")
    def on_deck_list_selected(self, event: ListView.Selected) -> None:
        """Handle deck selection from list."""
        if event.item and isinstance(event.item, DeckListItem):
            self.current_deck_id = event.item.deck.id

    @on(ListView.Highlighted, "#deck-list")
    def on_deck_list_highlighted(self, _event: ListView.Highlighted) -> None:
        """Track active list."""
        self._active_list = "deck-list"

    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        """Track which list has focus."""
        widget = event.widget
        if widget.id == "deck-list":
            self._active_list = "deck-list"
        elif widget.id == "mainboard-list":
            self._active_list = "mainboard"
        elif widget.id == "sideboard-list":
            self._active_list = "sideboard"
        elif widget.id == "search-results-list":
            self._active_list = "search"

    @on(ListView.Highlighted, "#mainboard-list")
    def on_mainboard_highlighted(self, event: ListView.Highlighted) -> None:
        """Track active list and update preview."""
        self._active_list = "mainboard"
        if event.item and isinstance(event.item, DeckCardResultItem):
            self._show_card_preview()
            self._update_preview_from_deck_card(event.item.card_name)

    @on(ListView.Highlighted, "#sideboard-list")
    def on_sideboard_highlighted(self, event: ListView.Highlighted) -> None:
        """Track active list and update preview."""
        self._active_list = "sideboard"
        if event.item and isinstance(event.item, DeckCardResultItem):
            self._show_card_preview()
            self._update_preview_from_deck_card(event.item.card_name)

    @on(ListView.Highlighted, "#search-results-list")
    def on_search_highlighted(self, event: ListView.Highlighted) -> None:
        """Track active list and update preview."""
        self._active_list = "search"
        if event.item and isinstance(event.item, CardResultItem):
            self._update_preview_from_search(event.item.card)

    @on(ListView.Selected, "#search-results-list")
    def on_search_selected(self, event: ListView.Selected) -> None:
        """Handle click on search result - show recommendation detail if available."""
        self._active_list = "search"
        if event.item and isinstance(event.item, CardResultItem):
            card_name = event.item.card.name
            # If we have recommendation details, show the explainer
            rec = self._recommendation_details.get(card_name)
            if rec:
                try:
                    detail_view = self.query_one("#recommendation-detail", RecommendationDetailView)
                    detail_view.show_recommendation(rec)
                except NoMatches:
                    pass

    @on(Input.Changed, "#deck-search-input")
    def on_search_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        query = event.value.strip()
        if query:
            self.current_view = ViewMode.CARD_SEARCH
            self._do_search(query)
        else:
            self.current_view = ViewMode.DECK_VIEW if self._current_deck else ViewMode.DECK_LIST

    @work(exclusive=True, group="deck_search")
    async def _do_search(self, query: str) -> None:
        """Execute card search."""
        if not self._db:
            return

        # Debounce
        await asyncio.sleep(0.15)

        from mtg_core.data.models.inputs import SearchCardsInput
        from mtg_core.tools import cards

        try:
            filters = SearchCardsInput(name=query)
            result = await cards.search_cards(self._db, filters)
            self._search_results = result.cards[:50]  # Limit results
            self._update_search_results()
        except Exception:
            self._search_results = []
            self._update_search_results()

    def _update_search_results(self) -> None:
        """Update search results list."""
        try:
            results_list = self.query_one("#search-results-list", ListView)
            results_header = self.query_one("#search-results-header", Static)
            results_list.clear()

            count = len(self._search_results)
            results_header.update(
                f"[{ui_colors.GOLD_DIM}]Search Results[/] [{ui_colors.GOLD}]{count}[/]"
            )

            for card in self._search_results:
                results_list.append(CardResultItem(card))

        except NoMatches:
            pass

    # ===== Actions =====

    def action_back(self) -> None:
        """Go back or exit."""
        if self.current_view == ViewMode.CARD_SEARCH:
            # Exit search mode
            try:
                search_input = self.query_one("#deck-search-input", Input)
                search_input.value = ""
            except NoMatches:
                pass
            self.current_view = ViewMode.DECK_VIEW if self._current_deck else ViewMode.DECK_LIST
        elif self.current_view == ViewMode.DECK_VIEW:
            # Go back to deck list
            self.current_deck_id = None
            self.current_view = ViewMode.DECK_LIST
            with contextlib.suppress(NoMatches):
                self.query_one("#deck-list", ListView).focus()
        else:
            # Exit screen
            self.dismiss()

    def action_new_deck(self) -> None:
        """Create a new deck."""
        self.app.push_screen(NewDeckModal(), callback=self._on_new_deck_result)

    def _on_new_deck_result(self, deck_id: int | None) -> None:
        """Handle new deck modal result."""
        if deck_id is not None:
            self.current_deck_id = deck_id
            self._load_decks()

    def action_focus_search(self) -> None:
        """Focus the search input."""
        try:
            search_input = self.query_one("#deck-search-input", Input)
            search_input.focus()
        except NoMatches:
            pass

    def action_cycle_focus(self) -> None:
        """Cycle focus between panes.

        Flow:
        - Deck view: deck-list → search-input → mainboard → sideboard → deck-list
        - Search mode: deck-list → search-input → search-results → deck-list
        - No deck: deck-list → search-input → deck-list
        """
        try:
            focused = self.app.focused
            search_input = self.query_one("#deck-search-input", Input)

            # If search input is focused, go to appropriate list
            if focused == search_input:
                if self.current_view == ViewMode.CARD_SEARCH:
                    self.query_one("#search-results-list", ListView).focus()
                    self._active_list = "search"
                elif self._current_deck:
                    self.query_one("#mainboard-list", ListView).focus()
                    self._active_list = "mainboard"
                else:
                    self.query_one("#deck-list", ListView).focus()
                    self._active_list = "deck-list"
                return

            # From deck list, go to search input
            if self._active_list == "deck-list":
                search_input.focus()
                return

            # From mainboard, go to sideboard
            if self._active_list == "mainboard":
                self.query_one("#sideboard-list", ListView).focus()
                self._active_list = "sideboard"
                return

            # From sideboard or search results, go back to deck list
            if self._active_list in ("sideboard", "search"):
                self.query_one("#deck-list", ListView).focus()
                self._active_list = "deck-list"
                return

            # Fallback: focus deck list
            self.query_one("#deck-list", ListView).focus()
            self._active_list = "deck-list"

        except NoMatches:
            pass

    def action_cycle_focus_reverse(self) -> None:
        """Cycle focus between panes in reverse.

        Flow (reverse of forward):
        - Deck view: deck-list ← search-input ← mainboard ← sideboard ← deck-list
        - Search mode: deck-list ← search-input ← search-results ← deck-list
        """
        try:
            focused = self.app.focused
            search_input = self.query_one("#deck-search-input", Input)

            # If search input is focused, go back to deck list
            if focused == search_input:
                self.query_one("#deck-list", ListView).focus()
                self._active_list = "deck-list"
                return

            # From mainboard, go back to search input
            if self._active_list == "mainboard":
                search_input.focus()
                return

            # From sideboard, go back to mainboard
            if self._active_list == "sideboard":
                self.query_one("#mainboard-list", ListView).focus()
                self._active_list = "mainboard"
                return

            # From search results, go back to search input
            if self._active_list == "search":
                search_input.focus()
                return

            # From deck list, go to sideboard (or search in search mode)
            if self._active_list == "deck-list":
                if self.current_view == ViewMode.CARD_SEARCH:
                    self.query_one("#search-results-list", ListView).focus()
                    self._active_list = "search"
                elif self._current_deck:
                    self.query_one("#sideboard-list", ListView).focus()
                    self._active_list = "sideboard"
                else:
                    search_input.focus()
                return

            # Fallback: focus deck list
            self.query_one("#deck-list", ListView).focus()
            self._active_list = "deck-list"

        except NoMatches:
            pass

    def action_nav_up(self) -> None:
        """Navigate up in active list."""
        list_map = {
            "deck-list": "#deck-list",
            "mainboard": "#mainboard-list",
            "sideboard": "#sideboard-list",
            "search": "#search-results-list",
        }
        list_id = list_map.get(self._active_list, "#mainboard-list")
        with contextlib.suppress(NoMatches):
            self.query_one(list_id, ListView).action_cursor_up()

    def action_nav_down(self) -> None:
        """Navigate down in active list."""
        list_map = {
            "deck-list": "#deck-list",
            "mainboard": "#mainboard-list",
            "sideboard": "#sideboard-list",
            "search": "#search-results-list",
        }
        list_id = list_map.get(self._active_list, "#mainboard-list")
        with contextlib.suppress(NoMatches):
            self.query_one(list_id, ListView).action_cursor_down()

    def action_cycle_sort(self) -> None:
        """Cycle sort order."""
        orders = list(SortOrder)
        current_idx = orders.index(self._card_sort_order)
        self._card_sort_order = orders[(current_idx + 1) % len(orders)]
        self._refresh_deck_display()
        self.notify(f"Sort: {self._card_sort_order.value}", timeout=1)

    def action_toggle_analysis(self) -> None:
        """Toggle between analysis panel and card preview."""
        if not self._current_deck:
            self.notify("No deck selected", severity="warning")
            return

        try:
            analysis = self.query_one("#deck-analysis-panel", DeckAnalysisPanel)
            if analysis.has_class("hidden"):
                self._show_analysis_panel()
                self.notify("Analysis view", timeout=1)
            else:
                self._show_card_preview()
                self.notify("Card preview", timeout=1)
        except NoMatches:
            pass

    def action_validate(self) -> None:
        """Validate the current deck."""
        if not self._current_deck:
            self.notify("No deck selected", severity="warning")
            return
        self._do_validate()

    @work
    async def _do_validate(self) -> None:
        """Execute deck validation."""
        if not self._current_deck:
            return

        try:
            result = await self._deck_manager.validate_deck(self._current_deck.id)
            if result.is_valid:
                self.notify(
                    f"[green]✓ Deck is valid![/] Format: {result.format}",
                    timeout=4,
                )
            else:
                issues = "\n".join(f"• {i.card_name}: {i.issue}" for i in result.issues[:5])
                self.notify(
                    f"[red]✗ {len(result.issues)} issues[/]\n{issues}",
                    severity="warning",
                    timeout=8,
                )
        except Exception as e:
            self.notify(f"Validation error: {e}", severity="error")

    def action_recommend(self) -> None:
        """Open full-screen recommendations view."""
        if not self._current_deck:
            self.notify("No deck selected", severity="warning")
            return
        if not self._current_deck.cards:
            self.notify("Deck is empty - add some cards first", severity="warning")
            return
        if not self._db:
            self.notify("Database not available", severity="error")
            return
        self._open_recommendation_screen()

    @work(exclusive=True, group="recommendations")
    async def _open_recommendation_screen(self) -> None:
        """Initialize and open the full-screen recommendations view."""
        if not self._current_deck or not self._db:
            return

        from mtg_core.tools.recommendations import HybridRecommender

        from ..recommendations import RecommendationScreen

        # Initialize recommender lazily
        if self._recommender is None:
            if self._recommender_initializing:
                self.notify("Recommendations loading, please wait...", timeout=2)
                return
            self._recommender_initializing = True
            self.notify("Initializing recommendations (first time may take ~2s)...", timeout=3)
            self._recommender = HybridRecommender()
            init_time = await self._recommender.initialize(self._db)
            self._recommender_initializing = False
            self.notify(
                f"Recommender ready ({init_time:.1f}s, {self._recommender.card_count:,} cards)",
                timeout=2,
            )

        # Load collection card names if we have a collection manager
        if self._collection_manager and not self._collection_cards:
            self._collection_cards = await self._collection_manager.get_collection_card_names()

        # Push the recommendation screen
        self.app.push_screen(
            RecommendationScreen(
                deck=self._current_deck,
                recommender=self._recommender,
                collection_cards=self._collection_cards,
                deck_manager=self._deck_manager,
            )
        )

    @on(AddCardToDeck)
    def on_add_card_to_deck(self, event: AddCardToDeck) -> None:
        """Handle add card request from recommendation screen."""
        if not self._current_deck:
            return
        self._add_card_from_recommendation(event.card_name, event.quantity)

    @work(exclusive=True, group="deck_edit")
    async def _add_card_from_recommendation(self, card_name: str, quantity: int) -> None:
        """Add a card from the recommendation screen."""
        if not self._current_deck:
            return
        result = await self._deck_manager.add_card(self._current_deck.id, card_name, quantity)
        if result.success:
            # Reload the current deck to reflect the change
            self._load_deck(self._current_deck.id)
        else:
            self.notify(f"Failed to add: {result.error}", severity="error")

    @work(exclusive=True, group="recommendations")
    async def _do_recommend(self) -> None:
        """Execute card recommendations using hybrid scoring."""
        if not self._current_deck or not self._db:
            return

        from mtg_core.data.models.responses import CardSummary
        from mtg_core.tools.recommendations import HybridRecommender

        # Initialize recommender lazily
        if self._recommender is None:
            if self._recommender_initializing:
                self.notify("Recommendations loading, please wait...", timeout=2)
                return
            self._recommender_initializing = True
            self.notify("Initializing recommendations (first time may take ~2s)...", timeout=3)
            self._recommender = HybridRecommender()
            init_time = await self._recommender.initialize(self._db)
            self._recommender_initializing = False
            self.notify(
                f"Recommender ready ({init_time:.1f}s, {self._recommender.card_count:,} cards)",
                timeout=2,
            )

        # Convert deck cards to dicts for the hybrid recommender
        deck_card_dicts: list[dict[str, object]] = []
        for dc in self._current_deck.cards:
            if dc.card:
                # Use model_dump to get dict representation
                card_dict = dc.card.model_dump(by_alias=True)
                deck_card_dicts.append(card_dict)

        if not deck_card_dicts:
            self.notify("Could not load card data for recommendations", severity="warning")
            return

        # Get recommendations with hybrid scoring
        try:
            recommendations = self._recommender.recommend_for_deck(
                deck_card_dicts, n=20, explain=True
            )

            # Store recommendations for tooltip/details display
            self._recommendation_details = {r.name: r for r in recommendations}

            # Convert to CardSummary for display
            self._search_results = []
            for rec in recommendations:
                summary = CardSummary(
                    uuid=rec.uuid,
                    name=rec.name,
                    type=rec.type_line,
                    mana_cost=rec.mana_cost,
                    colors=rec.colors or [],
                )
                self._search_results.append(summary)

            # Switch to search view FIRST so container becomes visible
            self.current_view = ViewMode.CARD_SEARCH
            self._active_list = "search"

            # Update display
            self._update_recommendations_display(recommendations)

            # Focus the results list after a brief delay for CSS to apply
            self.call_later(self._focus_search_results)

        except Exception as e:
            self.notify(f"Recommendation error: {e}", severity="error")

    def _focus_search_results(self) -> None:
        """Focus the search results list and select first item."""
        try:
            results_list = self.query_one("#search-results-list", ListView)
            results_list.focus()
            # Select first item if available
            if results_list.children:
                results_list.index = 0
            self._active_list = "search"
        except NoMatches:
            pass

    def _update_recommendations_display(self, recommendations: list[ScoredRecommendation]) -> None:
        """Update search results to show recommendations with synergy reasons."""
        try:
            results_list = self.query_one("#search-results-list", ListView)
            results_header = self.query_one("#search-results-header", Static)
            results_list.clear()

            # Build header with detected themes if available
            header_parts = [f"[{ui_colors.GOLD_DIM}]✨ Recommendations[/]"]
            header_parts.append(f" [{ui_colors.GOLD}]{len(recommendations)}[/]")

            # Show dominant themes if we have deck analysis
            if self._recommender and self._current_deck:
                deck_dicts = [
                    dc.card.model_dump(by_alias=True) for dc in self._current_deck.cards if dc.card
                ]
                if deck_dicts:
                    analysis = self._recommender.analyze_deck(deck_dicts)
                    themes = analysis.get("dominant_themes", [])
                    tribe = analysis.get("dominant_tribe")
                    if themes or tribe:
                        theme_str = ", ".join(themes[:3])
                        if tribe:
                            theme_str = f"{tribe} tribal" + (f", {theme_str}" if theme_str else "")
                        header_parts.append(f" [{ui_colors.GOLD_DIM}]({theme_str})[/]")

            results_header.update("".join(header_parts))

            # Add cards with synergy info in tooltip style
            for card in self._search_results:
                results_list.append(CardResultItem(card))

        except NoMatches:
            pass

    def _get_selected_deck_card(self) -> tuple[DeckCardResultItem | None, bool]:
        """Get selected card from mainboard or sideboard."""
        try:
            if self._active_list == "mainboard":
                mainboard = self.query_one("#mainboard-list", ListView)
                if mainboard.highlighted_child and isinstance(
                    mainboard.highlighted_child, DeckCardResultItem
                ):
                    return mainboard.highlighted_child, False
            elif self._active_list == "sideboard":
                sideboard = self.query_one("#sideboard-list", ListView)
                if sideboard.highlighted_child and isinstance(
                    sideboard.highlighted_child, DeckCardResultItem
                ):
                    return sideboard.highlighted_child, True
        except NoMatches:
            pass
        return None, False

    def action_increase_qty(self) -> None:
        """Increase quantity of selected card."""
        card, is_sideboard = self._get_selected_deck_card()
        if card and self._current_deck:
            self._change_quantity(card.card_name, card.card.quantity + 1, is_sideboard)

    def action_decrease_qty(self) -> None:
        """Decrease quantity of selected card."""
        card, is_sideboard = self._get_selected_deck_card()
        if card and self._current_deck and card.card.quantity > 1:
            self._change_quantity(card.card_name, card.card.quantity - 1, is_sideboard)

    @work
    async def _change_quantity(self, card_name: str, new_qty: int, is_sideboard: bool) -> None:
        """Change card quantity."""
        if not self._current_deck:
            return

        await self._deck_manager.set_quantity(
            self._current_deck.id, card_name, new_qty, is_sideboard
        )
        deck = await self._deck_manager.get_deck(self._current_deck.id)
        self._current_deck = deck
        self._refresh_deck_display()
        location = "sideboard" if is_sideboard else "mainboard"
        self.notify(f"{card_name}: {new_qty}x ({location})", timeout=1)

    def action_remove_card(self) -> None:
        """Remove selected card from deck."""
        card, is_sideboard = self._get_selected_deck_card()
        if card and self._current_deck:
            self._remove_card(card.card_name, is_sideboard)

    @work
    async def _remove_card(self, card_name: str, is_sideboard: bool) -> None:
        """Remove card from deck."""
        if not self._current_deck:
            return

        await self._deck_manager.remove_card(self._current_deck.id, card_name, is_sideboard)
        deck = await self._deck_manager.get_deck(self._current_deck.id)
        self._current_deck = deck
        self._refresh_deck_display()
        self.notify(f"Removed {card_name}", timeout=1)

    def action_toggle_sideboard(self) -> None:
        """Move selected card to/from sideboard."""
        card, is_sideboard = self._get_selected_deck_card()
        if card and self._current_deck:
            self._move_card(card.card_name, not is_sideboard)

    @work
    async def _move_card(self, card_name: str, to_sideboard: bool) -> None:
        """Move card between mainboard and sideboard."""
        if not self._current_deck:
            return

        if to_sideboard:
            await self._deck_manager.move_to_sideboard(self._current_deck.id, card_name)
        else:
            await self._deck_manager.move_to_mainboard(self._current_deck.id, card_name)

        deck = await self._deck_manager.get_deck(self._current_deck.id)
        self._current_deck = deck
        self._refresh_deck_display()
        location = "sideboard" if to_sideboard else "mainboard"
        self.notify(f"Moved {card_name} to {location}", timeout=1)

    def _quick_add(self, quantity: int) -> None:
        """Quick add card from search results."""
        if self.current_view != ViewMode.CARD_SEARCH or not self._current_deck:
            return

        try:
            results_list = self.query_one("#search-results-list", ListView)
            if results_list.highlighted_child and isinstance(
                results_list.highlighted_child, CardResultItem
            ):
                card = results_list.highlighted_child.card
                self._add_card_to_deck(card.name, quantity)
        except NoMatches:
            pass

    @work
    async def _add_card_to_deck(self, card_name: str, quantity: int) -> None:
        """Add a card to the current deck."""
        if not self._current_deck:
            return

        result = await self._deck_manager.add_card(
            self._current_deck.id, card_name, quantity, sideboard=False
        )
        if result.success:
            deck = await self._deck_manager.get_deck(self._current_deck.id)
            self._current_deck = deck
            self._refresh_deck_display()
            self.notify(f"Added {quantity}x {card_name}", timeout=1)
            if self._current_deck:
                self.post_message(CardAddedToDeck(card_name, self._current_deck.name, quantity))
        else:
            self.notify(result.error or "Failed to add", severity="error")

    def action_quick_add_1(self) -> None:
        """Add 1x of selected card."""
        self._quick_add(1)

    def action_quick_add_2(self) -> None:
        """Add 2x of selected card."""
        self._quick_add(2)

    def action_quick_add_3(self) -> None:
        """Add 3x of selected card."""
        self._quick_add(3)

    def action_quick_add_4(self) -> None:
        """Add 4x of selected card."""
        self._quick_add(4)

    # Handle keys not covered by bindings
    def on_key(self, event: events.Key) -> None:
        """Handle keys not covered by bindings."""
        if event.key == "d" and self._active_list == "deck-list":
            self._delete_selected_deck()
            event.stop()
        elif event.key == "enter" and self._active_list == "deck-list":
            # Open selected deck
            try:
                deck_list = self.query_one("#deck-list", ListView)
                if deck_list.highlighted_child and isinstance(
                    deck_list.highlighted_child, DeckListItem
                ):
                    self.current_deck_id = deck_list.highlighted_child.deck.id
                    event.stop()
            except NoMatches:
                pass
        elif event.key == "e" and self._active_list == "search":
            self._expand_current_recommendation()
            event.stop()

    def _expand_current_recommendation(self) -> None:
        """Show detail for the currently highlighted recommendation."""
        if not self._recommendation_details:
            return

        try:
            results_list = self.query_one("#search-results-list", ListView)
            highlighted = results_list.highlighted_child
            if highlighted is None or not isinstance(highlighted, CardResultItem):
                return

            card_name = highlighted.card.name
            rec = self._recommendation_details.get(card_name)
            if rec:
                detail_view = self.query_one("#recommendation-detail", RecommendationDetailView)
                detail_view.show_recommendation(rec)
        except NoMatches:
            pass

    def _delete_selected_deck(self) -> None:
        """Delete the selected deck."""
        try:
            deck_list = self.query_one("#deck-list", ListView)
            if deck_list.highlighted_child and isinstance(
                deck_list.highlighted_child, DeckListItem
            ):
                deck = deck_list.highlighted_child.deck
                self.app.push_screen(
                    ConfirmDeleteModal(deck.id, deck.name),
                    callback=self._on_delete_confirmed,
                )
        except NoMatches:
            pass

    def _on_delete_confirmed(self, deleted: bool | None) -> None:
        """Handle delete confirmation."""
        if deleted:
            if self._current_deck and self.current_deck_id:
                # Clear current deck if it was deleted
                self.current_deck_id = None
            self._load_decks()

    def action_expand_recommendation(self) -> None:
        """Show detailed explanation for selected recommendation."""
        if self.current_view != ViewMode.CARD_SEARCH:
            self.notify("Not in search view", timeout=1)
            return
        if not self._recommendation_details:
            self.notify("No recommendation details available", timeout=1)
            return

        # Get selected card from search results
        try:
            results_list = self.query_one("#search-results-list", ListView)
            highlighted = results_list.highlighted_child
            if highlighted is None:
                self.notify("No item highlighted", timeout=1)
                return
            if not isinstance(highlighted, CardResultItem):
                self.notify(f"Wrong item type: {type(highlighted)}", timeout=1)
                return

            card_name = highlighted.card.name
            rec = self._recommendation_details.get(card_name)
            if rec:
                detail_view = self.query_one("#recommendation-detail", RecommendationDetailView)
                detail_view.show_recommendation(rec)
            else:
                self.notify(f"No details for {card_name}", timeout=1)
        except NoMatches as e:
            self.notify(f"Widget not found: {e}", timeout=1)

    @on(RecommendationDetailCollapse)
    def on_recommendation_detail_collapse(self, _event: RecommendationDetailCollapse) -> None:
        """Handle recommendation detail collapse - refocus the list."""
        try:
            results_list = self.query_one("#search-results-list", ListView)
            results_list.focus()
        except NoMatches:
            pass
