"""Full-screen collection browser with stats, filtering, and card details."""

from __future__ import annotations

import asyncio
import contextlib
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.events import Key
from textual.reactive import reactive
from textual.widgets import Input, ListItem, ListView, Static

from ..deck.messages import AddToDeckRequested
from ..screens import BaseScreen
from ..ui.theme import ui_colors
from .card_preview import CollectionCardPreview
from .deck_suggestions_screen import (
    CollectionCardInfo,
    CreateDeckResult,
    DeckSuggestionsScreen,
)
from .filter_bar import CollectionColorIndex, CollectionTypeIndex
from .modals import (
    AddToCollectionModal,
    AddToCollectionResult,
    ConfirmDeleteModal,
    ExportCollectionModal,
    ImportCollectionModal,
    PrintingSelectionModal,
)
from .stats_panel import CollectionStatsPanel

if TYPE_CHECKING:
    from mtg_core.data.database import UnifiedDatabase

    from ..collection_manager import CollectionCardWithData, CollectionManager

# Debounce delay for search input (milliseconds)
SEARCH_DEBOUNCE_MS = 150


class SortOrder(Enum):
    """Sort order options for collection."""

    NAME_ASC = "name"
    CMC_ASC = "cmc"
    TYPE_ASC = "type"
    QTY_DESC = "qty"
    PRICE_DESC = "price"


class CollectionCardAdapter:
    """Adapter to make CollectionCardWithData compatible with CardLike protocol.

    Uses attributes (not properties) to satisfy Protocol requirements.
    """

    name: str
    mana_cost: str | None
    type: str | None
    rarity: str | None
    set_code: str | None
    flavor_name: str | None

    def __init__(self, card_data: CollectionCardWithData) -> None:
        card = card_data.card
        self.name = card_data.card_name
        self.mana_cost = card.mana_cost if card else None
        self.type = card.type if card else None
        self.rarity = card.rarity if card else None
        self.set_code = card_data.set_code or (card.set_code if card else None)
        self.flavor_name = card.flavor_name if card else None


class CollectionCardItem(ListItem):
    """A card in the collection list.

    Uses shared CardResultFormatter for consistent styling with search results,
    with collection-specific availability info appended.
    """

    DEFAULT_CSS = """
    CollectionCardItem {
        height: auto;
        min-height: 4;
    }

    CollectionCardItem Static {
        width: 100%;
    }
    """

    def __init__(self, card: CollectionCardWithData, id: str | None = None) -> None:
        super().__init__(id=id)
        self.card_data = card

    def compose(self) -> ComposeResult:
        yield Static(self._format_card())

    def _format_card(self) -> str:
        """Format the card using shared formatter + availability info."""
        from ..widgets.card_result_item import CardResultFormatter

        card = self.card_data
        total = card.total_owned
        avail = card.available

        # Use shared formatter for base card display
        adapter = CollectionCardAdapter(card)
        base_format = CardResultFormatter.format(adapter)

        # Availability styling
        if avail == total:
            avail_color = "#7ec850"
            avail_icon = "✓"
        elif avail > 0:
            avail_color = "#e6c84a"
            avail_icon = "○"
        else:
            avail_color = "#666"
            avail_icon = "●"

        # Append availability line
        avail_line = f"   [{avail_color}]{avail_icon}[/] [{ui_colors.GOLD}]{total}x[/] [dim]({avail} avail)[/]"

        return f"{base_format}\n{avail_line}"


class FullCollectionScreen(BaseScreen[None]):
    """Full-screen collection browser with filtering and sorting.

    Features:
    - Type filtering (creatures, instants, etc.)
    - Color filtering
    - Availability filtering (all, available, in decks)
    - Multiple sort options
    - Debounced search
    - Keyboard shortcuts for quick navigation
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape,q", "exit_collection", "Exit", show=True),
        Binding("tab", "toggle_focus", "Switch Pane", show=False),
        Binding("slash", "focus_search", "Search", show=True),
        Binding("plus", "add_card", "Add", show=True),
        Binding("ctrl+e", "add_to_deck", "To Deck", show=True),
        Binding("ctrl+o", "import_cards", "Import"),
        Binding("ctrl+x", "export_cards", "Export"),
        Binding("delete,backspace", "remove_card", "Remove"),
        Binding("f", "cycle_sort", "Sort"),
        Binding("y", "show_synergies", "Synergy", show=True),
        Binding("ctrl+d", "show_deck_suggestions", "Suggest Decks", show=True),
        # Navigation
        Binding("up,k", "nav_up", "Up", show=False),
        Binding("down,j", "nav_down", "Down", show=False),
        Binding("pageup", "page_up", "Page Up", show=False),
        Binding("pagedown", "page_down", "Page Down", show=False),
        Binding("home", "first", "First", show=False),
        Binding("end", "last_item", "Last", show=False),
    ]

    # Don't show footer - this screen has its own status bar
    show_footer: ClassVar[bool] = False

    CSS = """
    FullCollectionScreen {
        background: #0d0d0d;
    }

    /* Override screen-content to use grid for proper height distribution */
    FullCollectionScreen #screen-content {
        layout: grid;
        grid-size: 1;
        grid-rows: 4 1fr;
    }

    #collection-header {
        background: #0a0a14;
        border-bottom: heavy #c9a227;
        padding: 0 2;
        content-align: center middle;
    }

    #collection-main {
        width: 100%;
    }

    #collection-stats-pane {
        width: 22%;
        height: 100%;
        background: #0f0f0f;
        border-right: solid #3d3d3d;
        overflow-y: auto;
    }

    #collection-list-pane {
        width: 38%;
        height: 100%;
        background: #0a0a14;
        border-right: solid #3d3d3d;
        /* Grid layout so child ListView can use 1fr */
        layout: grid;
        grid-size: 1;
        grid-rows: auto auto 1fr auto;
    }

    #collection-filter-row {
        height: auto;
        padding: 0 1;
        background: #121218;
        border-bottom: solid #2a2a2a;
    }

    #collection-type-index {
        height: auto;
        padding: 1 0 0 0;
    }

    #collection-color-index {
        height: auto;
        padding: 0 0 1 0;
    }

    #collection-search-container {
        height: 3;
        padding: 0 1;
        background: #151515;
        border-bottom: solid #2a2a2a;
    }

    #collection-search-input {
        width: 100%;
        background: #1a1a2e;
        border: tall #3d3d3d;
    }

    #collection-search-input:focus {
        border: tall #c9a227;
        background: #1e1e32;
    }

    #collection-list {
        height: 1fr;
        scrollbar-color: #c9a227;
        scrollbar-color-hover: #e6c84a;
    }

    #collection-list > ListItem {
        padding: 0 1;
        height: auto;
        border-bottom: solid #1a1a1a;
        background: #121212;
    }

    #collection-list > ListItem:hover {
        background: #1a1a2e;
        border-left: solid #5a5a6e;
    }

    #collection-list > ListItem.-highlight {
        background: #2a2a4e;
        border-left: heavy #c9a227;
    }

    #collection-statusbar {
        height: 2;
        padding: 0 1;
        background: #1a1a1a;
        border-top: solid #3d3d3d;
        content-align: left middle;
    }

    #collection-preview-pane {
        width: 40%;
        height: 100%;
        background: #0d0d0d;
    }

    #collection-card-preview {
        height: 100%;
    }
    """

    # Reactive state
    search_query: reactive[str] = reactive("")
    current_sort: reactive[SortOrder] = reactive(SortOrder.NAME_ASC)
    active_type: reactive[str] = reactive("all")
    active_color: reactive[str] = reactive("all")
    active_avail: reactive[str] = reactive("all")
    total_count: reactive[int] = reactive(0)
    filtered_count: reactive[int] = reactive(0)

    def __init__(
        self,
        manager: CollectionManager,
        db: UnifiedDatabase,
    ) -> None:
        super().__init__()
        self._manager = manager
        self._db = db
        self._cards: list[CollectionCardWithData] = []
        self._filtered_cards: list[CollectionCardWithData] = []
        self._current_card: CollectionCardWithData | None = None
        self._type_counts: dict[str, int] = {}
        self._color_counts: dict[str, int] = {}
        self._avail_counts: dict[str, int] = {}
        self._search_debounce_task: asyncio.Task[None] | None = None
        self._population_cancelled = False
        self._prices: dict[str, tuple[float | None, float | None]] = {}

    def compose_content(self) -> ComposeResult:
        # Header
        yield Static(
            f"[bold {ui_colors.GOLD}]📦 MY COLLECTION[/]",
            id="collection-header",
        )

        with Horizontal(id="collection-main"):
            # Stats pane
            with Vertical(id="collection-stats-pane"):
                yield CollectionStatsPanel(id="collection-stats")

            # Card list pane
            with Vertical(id="collection-list-pane"):
                # Filter row with type and color pills
                with Vertical(id="collection-filter-row"):
                    yield CollectionTypeIndex(id="collection-type-index")
                    yield CollectionColorIndex(id="collection-color-index")

                # Search
                with Horizontal(id="collection-search-container"):
                    yield Input(
                        placeholder="Search collection...",
                        id="collection-search-input",
                    )

                # Card list
                yield ListView(id="collection-list")

                # Status bar
                yield Static(
                    self._render_statusbar(),
                    id="collection-statusbar",
                )

            # Preview pane - compact card preview
            with Vertical(id="collection-preview-pane"):
                yield CollectionCardPreview(id="collection-card-preview")

    def _render_statusbar(self) -> str:
        """Render status bar with current state and shortcuts."""
        sort_labels = {
            SortOrder.NAME_ASC: "Name",
            SortOrder.CMC_ASC: "CMC",
            SortOrder.TYPE_ASC: "Type",
            SortOrder.QTY_DESC: "Qty",
            SortOrder.PRICE_DESC: "Price",
        }
        sort_label = sort_labels[self.current_sort]

        parts = [
            f"[{ui_colors.GOLD}]^d[/]:Suggest Decks",
            f"[{ui_colors.GOLD}]f[/]:Sort({sort_label})",
            f"[{ui_colors.GOLD}]/[/]:Search",
            f"[{ui_colors.GOLD}]+[/]:Add",
            f"[{ui_colors.GOLD}]^e[/]:To Deck",
            f"[{ui_colors.GOLD}]Del[/]:Remove",
        ]
        return "  ".join(parts)

    def _update_statusbar(self) -> None:
        """Update the status bar."""
        try:
            statusbar = self.query_one("#collection-statusbar", Static)
            statusbar.update(self._render_statusbar())
        except NoMatches:
            pass

    def _update_header(self) -> None:
        """Update header with current count."""
        try:
            header = self.query_one("#collection-header", Static)
            is_filtered = (
                self.search_query
                or self.active_type != "all"
                or self.active_color != "all"
                or self.active_avail != "all"
            )
            if is_filtered:
                header.update(
                    f"[bold {ui_colors.GOLD}]📦 MY COLLECTION[/]  "
                    f"[dim]showing {self.filtered_count} of {self.total_count}[/]"
                )
            else:
                header.update(
                    f"[bold {ui_colors.GOLD}]📦 MY COLLECTION[/]  "
                    f"[dim]({self.total_count} cards)[/]"
                )
        except NoMatches:
            pass

    def _update_type_index(self) -> None:
        """Update the type filter index."""
        try:
            type_index = self.query_one("#collection-type-index", CollectionTypeIndex)
            type_index.update_counts(self._type_counts, self.active_type)
        except NoMatches:
            pass

    def _update_color_index(self) -> None:
        """Update the color filter index."""
        try:
            color_index = self.query_one("#collection-color-index", CollectionColorIndex)
            color_index.update_counts(self._color_counts, self.active_color)
        except NoMatches:
            pass

    async def on_mount(self) -> None:
        """Load collection data on mount."""
        # Focus the list
        try:
            list_view = self.query_one("#collection-list", ListView)
            list_view.focus()
        except NoMatches:
            pass

        # Load collection
        self._load_collection()

    @work
    async def _load_collection(self, *, reload_prices: bool = True) -> None:
        """Load all collection cards.

        Args:
            reload_prices: If False, reuse existing price data instead of re-fetching.
                          Use False for quantity changes and removals where prices don't change.
        """
        self._population_cancelled = False

        # Get all cards
        self._cards, _ = await self._manager.get_collection(page=1, page_size=10000)
        self.total_count = len(self._cards)

        # Calculate type counts
        self._calculate_counts()

        # Update stats panel
        stats = await self._manager.get_stats()
        try:
            stats_panel = self.query_one("#collection-stats", CollectionStatsPanel)
            stats_panel.update_stats(stats, self._cards)

            if reload_prices:
                # Load price data fresh (in background to not block UI)
                self._load_price_data()
            elif self._prices:
                # Reuse existing prices, just recalculate total value
                stats_panel.update_value(self._prices, self._cards)
        except NoMatches:
            pass

        # Apply filtering
        self._filter_cards()

        # Populate list
        await self._populate_list()

        # Update UI
        self._update_header()
        self._update_type_index()
        self._update_color_index()
        self._update_statusbar()

    @staticmethod
    def _price_key(card_name: str, set_code: str | None, collector_number: str | None) -> str:
        """Generate a unique key for price lookup.

        Uses set_code/collector_number when available for specific printing prices.
        """
        if set_code and collector_number:
            return f"{card_name}|{set_code.upper()}|{collector_number}"
        return card_name

    @work(exclusive=True, group="price_data")
    async def _load_price_data(self) -> None:
        """Load price data for all collection cards.

        Uses optimized price-only queries that fetch just 4 columns instead of 40+.
        Cards with specific printings use get_prices_by_set_and_numbers(),
        cards without use get_prices_by_names().

        Prices are cached in the CollectionManager for 5 minutes to avoid
        repeated database queries when reopening the collection screen.
        """
        if not self._cards:
            return

        # Check for cached prices first
        cached = self._manager.get_cached_prices()
        if cached:
            self._prices = cached
            # Update stats panel with cached prices
            try:
                stats_panel = self.query_one("#collection-stats", CollectionStatsPanel)
                stats_panel.update_value(cached, self._cards)
            except NoMatches:
                pass
            return

        # Build price dict: price_key -> (usd_price, usd_foil_price)
        price_data: dict[str, tuple[float | None, float | None]] = {}

        # Separate cards with specific printings from those without
        printings_to_fetch: list[tuple[str, str]] = []
        cards_with_printing: list[CollectionCardWithData] = []
        cards_without_printing: list[CollectionCardWithData] = []

        for card_data in self._cards:
            if card_data.set_code and card_data.collector_number:
                cards_with_printing.append(card_data)
                printings_to_fetch.append((card_data.set_code, card_data.collector_number))
            else:
                cards_without_printing.append(card_data)

        # Fetch prices only (not full card objects) - much faster
        if printings_to_fetch:
            prices_by_printing = await self._db.get_prices_by_set_and_numbers(printings_to_fetch)

            for card_data in cards_with_printing:
                assert card_data.set_code is not None
                assert card_data.collector_number is not None
                lookup_key = (card_data.set_code.upper(), card_data.collector_number)
                price_tuple = prices_by_printing.get(lookup_key)
                if price_tuple:
                    key = self._price_key(
                        card_data.card_name, card_data.set_code, card_data.collector_number
                    )
                    price_usd = price_tuple[0] / 100.0 if price_tuple[0] else None
                    price_usd_foil = price_tuple[1] / 100.0 if price_tuple[1] else None
                    price_data[key] = (price_usd, price_usd_foil)

        # Fetch prices by name for cards without specific printings
        if cards_without_printing:
            card_names = [c.card_name for c in cards_without_printing]
            prices_by_name = await self._db.get_prices_by_names(card_names)

            for card_data in cards_without_printing:
                price_tuple = prices_by_name.get(card_data.card_name.lower())
                if price_tuple:
                    key = self._price_key(
                        card_data.card_name, card_data.set_code, card_data.collector_number
                    )
                    price_usd = price_tuple[0] / 100.0 if price_tuple[0] else None
                    price_usd_foil = price_tuple[1] / 100.0 if price_tuple[1] else None
                    price_data[key] = (price_usd, price_usd_foil)

        # Store prices for sorting and cache for future opens
        self._prices = price_data
        self._manager.set_cached_prices(price_data)

        # Update stats panel
        try:
            stats_panel = self.query_one("#collection-stats", CollectionStatsPanel)
            stats_panel.update_value(price_data, self._cards)
        except NoMatches:
            pass

    def _calculate_counts(self) -> None:
        """Calculate type, color, and availability counts."""
        self._type_counts = {
            "all": len(self._cards),
            "creature": 0,
            "instant": 0,
            "sorcery": 0,
            "artifact": 0,
            "enchantment": 0,
            "planeswalker": 0,
            "land": 0,
        }
        self._color_counts = {
            "all": len(self._cards),
            "W": 0,
            "U": 0,
            "B": 0,
            "R": 0,
            "G": 0,
            "C": 0,
            "M": 0,
        }
        self._avail_counts = {
            "all": len(self._cards),
            "available": 0,
            "in_decks": 0,
        }

        for card in self._cards:
            # Type counting
            if card.card and card.card.type:
                type_lower = card.card.type.lower()
                if "creature" in type_lower:
                    self._type_counts["creature"] += 1
                elif "instant" in type_lower:
                    self._type_counts["instant"] += 1
                elif "sorcery" in type_lower:
                    self._type_counts["sorcery"] += 1
                elif "artifact" in type_lower:
                    self._type_counts["artifact"] += 1
                elif "enchantment" in type_lower:
                    self._type_counts["enchantment"] += 1
                elif "planeswalker" in type_lower:
                    self._type_counts["planeswalker"] += 1
                elif "land" in type_lower:
                    self._type_counts["land"] += 1

            # Color counting
            if card.card:
                colors = card.card.colors or []
                if len(colors) > 1:
                    self._color_counts["M"] += 1
                elif len(colors) == 1:
                    color = colors[0]
                    if color in self._color_counts:
                        self._color_counts[color] += 1
                else:
                    self._color_counts["C"] += 1

            # Availability counting
            if card.available > 0:
                self._avail_counts["available"] += 1
            if card.in_deck_count > 0:
                self._avail_counts["in_decks"] += 1

    def _filter_cards(self) -> None:
        """Filter cards by type, color, availability, and search query."""
        filtered = self._cards

        # Apply type filter
        if self.active_type != "all":
            filtered = [
                c
                for c in filtered
                if c.card and c.card.type and self.active_type in c.card.type.lower()
            ]

        # Apply color filter
        if self.active_color != "all":
            filtered = [c for c in filtered if self._card_matches_color(c)]

        # Apply availability filter
        if self.active_avail == "available":
            filtered = [c for c in filtered if c.available > 0]
        elif self.active_avail == "in_decks":
            filtered = [c for c in filtered if c.in_deck_count > 0]

        # Apply search filter
        if self.search_query:
            query_lower = self.search_query.lower()
            filtered = [
                c
                for c in filtered
                if query_lower in c.card_name.lower()
                or (c.card and c.card.type and query_lower in c.card.type.lower())
            ]

        self._filtered_cards = filtered
        self.filtered_count = len(filtered)

        # Apply sorting
        self._sort_cards()

    def _card_matches_color(self, card_data: CollectionCardWithData) -> bool:
        """Check if a card matches the active color filter."""
        if not card_data.card:
            return False

        colors = card_data.card.colors or []
        color_filter = self.active_color

        if color_filter == "M":
            return len(colors) > 1
        elif color_filter == "C":
            return len(colors) == 0
        else:
            return color_filter in colors

    def _sort_cards(self) -> None:
        """Sort filtered cards based on current sort order."""
        if self.current_sort == SortOrder.NAME_ASC:
            self._filtered_cards.sort(key=lambda c: c.card_name.lower())
        elif self.current_sort == SortOrder.CMC_ASC:

            def get_cmc(c: CollectionCardWithData) -> float:
                if c.card and c.card.cmc is not None:
                    return float(c.card.cmc)
                return 999.0

            self._filtered_cards.sort(key=get_cmc)
        elif self.current_sort == SortOrder.TYPE_ASC:

            def get_type(c: CollectionCardWithData) -> str:
                if c.card and c.card.type:
                    return str(c.card.type).lower()
                return "zzz"

            self._filtered_cards.sort(key=get_type)
        elif self.current_sort == SortOrder.QTY_DESC:
            self._filtered_cards.sort(key=lambda c: c.total_owned, reverse=True)
        elif self.current_sort == SortOrder.PRICE_DESC:

            def get_price(c: CollectionCardWithData) -> float:
                key = self._price_key(c.card_name, c.set_code, c.collector_number)
                price_tuple = self._prices.get(key)
                if price_tuple and price_tuple[0]:
                    return price_tuple[0]
                return 0.0

            self._filtered_cards.sort(key=get_price, reverse=True)

    async def _populate_list(self) -> None:
        """Populate the ListView with cards."""
        try:
            list_view = self.query_one("#collection-list", ListView)
            await list_view.clear()

            if not self._filtered_cards:
                empty_item = ListItem(Static(f"[{ui_colors.TEXT_DIM}]No cards match filters[/]"))
                await list_view.append(empty_item)
                return

            # Add cards in batches to keep UI responsive
            batch_size = 50
            batch_count = 0

            for i, card in enumerate(self._filtered_cards):
                if self._population_cancelled:
                    return

                item = CollectionCardItem(card, id=f"card-item-{i}")
                await list_view.append(item)
                batch_count += 1

                if batch_count >= batch_size:
                    batch_count = 0
                    await asyncio.sleep(0)

            # Select first item
            if list_view.children:
                list_view.index = 0
                # Show first card preview
                if self._filtered_cards:
                    self._current_card = self._filtered_cards[0]
                    self._show_card_preview(self._filtered_cards[0])

        except NoMatches:
            pass

    @on(Input.Changed, "#collection-search-input")
    def on_search_changed(self, event: Input.Changed) -> None:
        """Handle search input changes with debouncing."""
        # Cancel any pending debounce task
        if self._search_debounce_task is not None:
            self._search_debounce_task.cancel()
            self._search_debounce_task = None

        # Cancel any ongoing population
        self._population_cancelled = True

        # Schedule debounced search
        self._search_debounce_task = asyncio.create_task(self._debounced_search(event.value))

    async def _debounced_search(self, query: str) -> None:
        """Execute search after debounce delay."""
        try:
            await asyncio.sleep(SEARCH_DEBOUNCE_MS / 1000)
        except asyncio.CancelledError:
            return

        self._population_cancelled = False
        self.search_query = query.strip()
        self._filter_cards()
        await self._populate_list()

        if not self._population_cancelled:
            self._update_header()

    @on(Input.Submitted, "#collection-search-input")
    def on_search_submitted(self, _event: Input.Submitted) -> None:
        """Focus list after search submit."""
        try:
            list_view = self.query_one("#collection-list", ListView)
            list_view.focus()
        except NoMatches:
            pass

    @on(ListView.Highlighted, "#collection-list")
    def on_card_highlighted(self, event: ListView.Highlighted) -> None:
        """Update preview when card is highlighted."""
        if event.item and isinstance(event.item, CollectionCardItem):
            self._current_card = event.item.card_data
            self._show_card_preview(event.item.card_data)

    @work
    async def _show_card_preview(self, card_data: CollectionCardWithData) -> None:
        """Show card in the preview panel."""
        if not card_data.card:
            return

        try:
            preview = self.query_one("#collection-card-preview", CollectionCardPreview)
            # Update card data with deck usage info
            deck_usage = card_data.deck_usage if card_data.deck_usage else []
            preview.update_card(card_data, deck_usage)
            # Load printing info and image (pass stored set_code/collector_number for exact printing)
            await preview.load_printing(
                self._db,
                card_data.card_name,
                card_data.set_code,
                card_data.collector_number,
            )
        except Exception:
            pass

    def _set_type_filter(self, type_filter: str) -> None:
        """Set the active type filter."""
        if type_filter == self.active_type:
            return

        self.active_type = type_filter
        self._population_cancelled = True
        self._filter_cards()
        self._repopulate_list()

    def _set_color_filter(self, color_filter: str) -> None:
        """Set the active color filter."""
        if color_filter == self.active_color:
            return

        self.active_color = color_filter
        self._population_cancelled = True
        self._filter_cards()
        self._repopulate_list()

    def _set_avail_filter(self, avail_filter: str) -> None:
        """Set the active availability filter."""
        if avail_filter == self.active_avail:
            return

        self.active_avail = avail_filter
        self._population_cancelled = True
        self._filter_cards()
        self._repopulate_list()

    @work(exclusive=True, group="populate_list")
    async def _repopulate_list(self) -> None:
        """Repopulate list after filter change."""
        self._population_cancelled = False
        await self._populate_list()

        if not self._population_cancelled:
            self._update_header()
            self._update_type_index()
            self._update_color_index()
            self._update_statusbar()

    def on_key(self, event: Key) -> None:
        """Handle key presses for type, color, and availability filtering."""
        # Check if search input is focused - don't intercept letter keys
        try:
            search = self.query_one("#collection-search-input", Input)
            if search.has_focus:
                return
        except NoMatches:
            pass

        # Type filter keys (unique letters)
        type_map = {
            "a": "all",  # All types
            "c": "creature",  # Creature
            "i": "instant",  # Instant
            "s": "sorcery",  # Sorcery
            "t": "artifact",  # arTifact (t to avoid conflict with 'r' for red)
            "e": "enchantment",  # Enchantment
            "p": "planeswalker",  # Planeswalker
            "l": "land",  # Land
        }

        # Color filter keys (WUBRG + colorless/multi)
        color_map = {
            "asterisk": "all",
            "w": "W",  # White
            "u": "U",  # Blue
            "b": "B",  # Black (conflicts with nothing important)
            "r": "R",  # Red
            "g": "G",  # Green
            "0": "C",  # Colorless
            "m": "M",  # Multicolor
        }

        # Availability filter keys
        avail_map = {
            "1": "all",
            "2": "available",
            "3": "in_decks",
        }

        key = event.key.lower()
        # Check for color keys first (WUBRG standard MTG color letters)
        if key in color_map:
            color = color_map[key]
            self._set_color_filter(color)
            color_labels = {
                "all": "All Colors",
                "W": "White ☀",
                "U": "Blue 💧",
                "B": "Black 💀",
                "R": "Red 🔥",
                "G": "Green 🌲",
                "C": "Colorless ◇",
                "M": "Multicolor 🌈",
            }
            self.notify(f"Color: {color_labels.get(color, color)}", timeout=1)
            event.stop()
        elif key in type_map:
            self._set_type_filter(type_map[key])
            type_label = type_map[key].title()
            self.notify(f"Type: {type_label}", timeout=1)
            event.stop()
        elif key in avail_map:
            self._set_avail_filter(avail_map[key])
            avail_labels = {"all": "All", "available": "Available", "in_decks": "In Decks"}
            self.notify(f"Showing: {avail_labels[avail_map[key]]}", timeout=1)
            event.stop()

    # Actions

    def action_exit_collection(self) -> None:
        """Exit the collection screen."""
        self.app.pop_screen()

    def action_show_synergies(self) -> None:
        """Show synergies for the currently selected card."""
        if not self._current_card:
            self.notify("Select a card first", severity="warning", timeout=2)
            return

        card_name = self._current_card.card_name
        # Exit collection and show synergies in main app
        self.app.pop_screen()
        # Call find_synergies on the app (it's a method from SynergyCommandsMixin)
        if hasattr(self.app, "find_synergies"):
            self.app.find_synergies(card_name)

    def action_show_deck_suggestions(self) -> None:
        """Show deck archetypes that can be built from collection."""
        if not self._cards:
            self.notify("Add cards to your collection first", severity="warning", timeout=2)
            return

        # Build card info list with type/color/text data for analysis
        card_info_list: list[CollectionCardInfo] = []
        for card_data in self._cards:
            card = card_data.card
            if card:
                card_info_list.append(
                    CollectionCardInfo(
                        name=card_data.card_name,
                        type_line=card.type,
                        colors=card.colors,
                        mana_cost=card.mana_cost,
                        text=card.text,
                        color_identity=card.color_identity,
                    )
                )
            else:
                # Card without full data - include name only
                card_info_list.append(CollectionCardInfo(name=card_data.card_name))

        self.app.push_screen(
            DeckSuggestionsScreen(card_info_list),
            callback=self._on_deck_suggestion_result,
        )

    def _on_deck_suggestion_result(self, result: CreateDeckResult | None) -> None:
        """Handle deck suggestion modal result."""
        if result is not None:
            missing_count = len(result.cards_missing) if result.cards_missing else 0
            self.notify(
                f"Creating '{result.deck_name}': {len(result.card_names)} owned, {missing_count} needed",
                timeout=5,
            )
            self._create_deck_from_suggestion(result)

    @work
    async def _create_deck_from_suggestion(self, result: CreateDeckResult) -> None:
        """Create a new deck from the suggestion."""
        # Access deck manager from app (private attribute)
        deck_manager = getattr(self.app, "_deck_manager", None)
        if deck_manager is None:
            self.notify("Deck manager not available", severity="error")
            return

        # Create the deck
        try:
            deck_id = await deck_manager.create_deck(
                name=result.deck_name,
                format=result.format_type,
                commander=result.commander,
            )

            if not deck_id:
                self.notify("Failed to create deck", severity="error")
                return

            # Add owned cards to the deck
            added_count = 0
            for card_name in result.card_names:
                try:
                    add_result = await deck_manager.add_card(
                        deck_id=deck_id,
                        card_name=card_name,
                        quantity=1,
                        sideboard=False,
                    )
                    if add_result.success:
                        added_count += 1
                except Exception:
                    pass  # Skip cards that fail to add

            # Add missing cards (basic lands, etc.) with counts
            missing_count = 0
            if result.cards_missing:
                # Count duplicates in missing cards
                from collections import Counter

                missing_counts = Counter(result.cards_missing)
                for card_name, qty in missing_counts.items():
                    try:
                        add_result = await deck_manager.add_card(
                            deck_id=deck_id,
                            card_name=card_name,
                            quantity=qty,
                            sideboard=False,
                        )
                        if add_result.success:
                            missing_count += qty
                    except Exception:
                        pass

            total_added = added_count + missing_count
            msg = f"Created '{result.deck_name}' with {total_added} cards!"
            if missing_count > 0:
                msg += f" (includes {missing_count} basic lands)"
            self.notify(msg, severity="information", timeout=4)

            # Close collection screen and open the new deck
            self.app.pop_screen()

            # Open the deck screen if possible
            if hasattr(self.app, "open_deck"):
                self.app.open_deck(deck_id)

        except Exception as e:
            self.notify(f"Error creating deck: {e}", severity="error")

    def action_focus_search(self) -> None:
        """Focus the search input."""
        with contextlib.suppress(NoMatches):
            self.query_one("#collection-search-input", Input).focus()

    def action_toggle_focus(self) -> None:
        """Toggle focus between search and list."""
        try:
            search_input = self.query_one("#collection-search-input", Input)
            list_view = self.query_one("#collection-list", ListView)

            if search_input.has_focus:
                list_view.focus()
            else:
                search_input.focus()
        except NoMatches:
            pass

    def action_cycle_sort(self) -> None:
        """Cycle through sort options."""
        orders = list(SortOrder)
        current_idx = orders.index(self.current_sort)
        self.current_sort = orders[(current_idx + 1) % len(orders)]

        sort_labels = {
            SortOrder.NAME_ASC: "Name",
            SortOrder.CMC_ASC: "CMC",
            SortOrder.TYPE_ASC: "Type",
            SortOrder.QTY_DESC: "Quantity",
            SortOrder.PRICE_DESC: "Price",
        }
        self.notify(f"Sort: {sort_labels[self.current_sort]}", timeout=1)

        self._sort_cards()
        self._repopulate_list()

    def action_nav_up(self) -> None:
        """Navigate up in list."""
        try:
            list_view = self.query_one("#collection-list", ListView)
            list_view.action_cursor_up()
        except NoMatches:
            pass

    def action_nav_down(self) -> None:
        """Navigate down in list."""
        try:
            list_view = self.query_one("#collection-list", ListView)
            list_view.action_cursor_down()
        except NoMatches:
            pass

    def action_page_up(self) -> None:
        """Page up in the list."""
        try:
            list_view = self.query_one("#collection-list", ListView)
            list_view.action_page_up()
        except NoMatches:
            pass

    def action_page_down(self) -> None:
        """Page down in the list."""
        try:
            list_view = self.query_one("#collection-list", ListView)
            list_view.action_page_down()
        except NoMatches:
            pass

    def action_first(self) -> None:
        """Go to first card."""
        try:
            list_view = self.query_one("#collection-list", ListView)
            if list_view.children:
                list_view.index = 0
        except NoMatches:
            pass

    def action_last_item(self) -> None:
        """Go to last card."""
        try:
            list_view = self.query_one("#collection-list", ListView)
            if list_view.children:
                list_view.index = len(list_view.children) - 1
        except NoMatches:
            pass

    def action_add_card(self) -> None:
        """Open add card modal."""
        self.app.push_screen(
            AddToCollectionModal(),
            callback=self._on_add_result,
        )

    def action_add_to_deck(self) -> None:
        """Add the selected card to a deck."""
        if not self._current_card:
            self.notify("Select a card first", severity="warning")
            return

        # Post message to app - it handles showing the AddToDeckModal
        self.post_message(
            AddToDeckRequested(
                card_name=self._current_card.card_name,
                set_code=self._current_card.set_code,
                collector_number=self._current_card.collector_number,
            )
        )

    def _on_add_result(self, result: AddToCollectionResult | None) -> None:
        """Handle add modal result."""
        if result is not None:
            self._do_add_card(result)

    @work
    async def _do_add_card(self, data: AddToCollectionResult) -> None:
        """Add a card to the collection."""
        result = await self._manager.add_card(
            card_name=data.card_name,
            quantity=data.quantity,
            foil=data.foil,
            set_code=data.set_code,
            collector_number=data.collector_number,
        )
        if result.success and result.card:
            # Invalidate price cache since we added a new card
            self._manager.invalidate_price_cache()
            # Show appropriate message based on input type
            if data.set_code and data.collector_number:
                msg = f"Added {data.quantity}x {result.card.name} ({data.set_code.upper()} #{data.collector_number})"
            else:
                msg = f"Added {data.quantity}x {result.card.name}"
            self.notify(msg)
            self._load_collection()
        else:
            self.notify(result.error or "Failed to add card", severity="error")

    def action_import_cards(self) -> None:
        """Open import modal."""
        self.app.push_screen(
            ImportCollectionModal(),
            callback=self._on_import_result,
        )

    def _on_import_result(self, text: str | None) -> None:
        """Handle import modal result."""
        if text:
            self._do_import(text)

    @work
    async def _do_import(self, text: str) -> None:
        """Import cards from text."""
        result = await self._manager.import_from_text(text)
        added = result.added_count
        errors = result.errors

        if added > 0:
            # Invalidate price cache since we added new cards
            self._manager.invalidate_price_cache()
            msg = f"Imported {added} card{'s' if added != 1 else ''}"
            if errors:
                msg += f" ({len(errors)} not found)"
            self.notify(msg, severity="information" if not errors else "warning")
            self._load_collection()

            if result.cards_with_printings:
                cards_for_modal = [
                    (c.card_name, c.printings_count) for c in result.cards_with_printings
                ]
                self.app.push_screen(
                    PrintingSelectionModal(cards_for_modal, self._db),
                    callback=self._on_printing_selection,
                )
        elif errors:
            self.notify("No cards imported", severity="error")

        if errors:
            for error in errors[:3]:
                self.notify(error, severity="warning", timeout=6)
            if len(errors) > 3:
                self.notify(f"...and {len(errors) - 3} more not found", timeout=5)

    def _on_printing_selection(self, selections: dict[str, tuple[str, str]] | None) -> None:
        """Handle printing selection modal result."""
        if selections:
            self._apply_printing_selections(selections)

    @work
    async def _apply_printing_selections(self, selections: dict[str, tuple[str, str]]) -> None:
        """Apply the selected printings to collection cards."""
        updated = await self._manager.apply_printing_selections(selections)
        if updated > 0:
            # Invalidate price cache since different printings have different prices
            self._manager.invalidate_price_cache()
            self.notify(f"Updated printings for {updated} card{'s' if updated != 1 else ''}")
            self._load_collection()

    def action_export_cards(self) -> None:
        """Open export modal."""
        self._do_export()

    @work
    async def _do_export(self) -> None:
        """Export collection to text format."""
        export_text = await self._manager.export_to_text()
        if export_text:
            self.app.push_screen(ExportCollectionModal(export_text))
        else:
            self.notify("Collection is empty", severity="warning")

    def action_remove_card(self) -> None:
        """Remove the selected card with confirmation."""
        if self._current_card:
            # Show confirmation modal
            modal = ConfirmDeleteModal(
                self._current_card.card_name,
                self._current_card.quantity,
                self._current_card.foil_quantity,
            )
            self.app.push_screen(modal, self._on_delete_confirmed)

    def _on_delete_confirmed(self, confirmed: bool | None) -> None:
        """Handle delete confirmation result."""
        if confirmed is True and self._current_card:
            self._do_remove_card(self._current_card.card_name)

    @work
    async def _do_remove_card(self, card_name: str) -> None:
        """Remove a card from the collection."""
        removed = await self._manager.remove_card(card_name)
        if removed:
            self.notify(f"Removed {card_name}")
            # Prices don't change on removal, just recalculate total
            self._load_collection(reload_prices=False)
