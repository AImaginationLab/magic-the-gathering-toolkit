"""Full-screen set browser with list, detail, and card preview."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import Input, ListItem, ListView, Static

from mtg_core.tools import sets
from mtg_core.tools.set_analysis import analyze_set

from ..ui.theme import ui_colors
from ..widgets.set_detail import SetCardList, SetStats
from ..widgets.set_insights import SetInsightsPanel
from .base import BaseScreen

if TYPE_CHECKING:
    from mtg_core.data.database import UnifiedDatabase
    from mtg_core.data.models import Set
    from mtg_core.data.models.responses import CardSummary, SetSummary

# Debounce delay for search input (milliseconds)
SEARCH_DEBOUNCE_MS = 150


class SetListItem(ListItem):
    """List item representing a set."""

    def __init__(
        self,
        set_data: SetSummary,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.set_data = set_data

    def compose(self) -> ComposeResult:
        date_str = self.set_data.release_date or "?"
        content = (
            f"[cyan]{self.set_data.code.upper()}[/]  "
            f"[bold]{self.set_data.name}[/]  "
            f"[dim]({date_str})[/]"
        )
        yield Static(content, classes="set-item-content")


class SetsScreen(BaseScreen[None]):
    """Full-screen set browser with list, detail, and card preview.

    Features:
    - Searchable list of all sets
    - Set detail panel with cards
    - Keyboard navigation
    - Rarity filtering
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "back_or_exit", "Back/Exit", show=True),
        Binding("q", "exit", "Exit", show=False),
        Binding("enter", "select", "Select"),
        Binding("e", "explore_set", "Explore"),
        Binding("a", "filter_artist_series", "Art Series"),
        Binding("slash", "focus_search", "Search"),
        Binding("f", "toggle_filter", "Filter"),
        Binding("r", "random_card", "Random"),
        # Navigation
        Binding("up,k", "nav_up", "Up", show=False),
        Binding("down,j", "nav_down", "Down", show=False),
        Binding("pageup", "page_up", "Page Up", show=False),
        Binding("pagedown", "page_down", "Page Down", show=False),
        Binding("home", "first", "First", show=False),
        Binding("end", "last_item", "Last", show=False),
        # Pane switching
        Binding("tab", "toggle_pane", "Switch Pane", show=False),
    ]

    # Don't show footer - this screen has its own status bar
    show_footer: ClassVar[bool] = False

    CSS = """
    SetsScreen {
        background: #0d0d0d;
    }

    /* Override screen-content to use grid for proper height distribution.
       Only 2 rows: header (4 lines) and main (fills remaining). Statusbar goes inside panes. */
    SetsScreen #screen-content {
        width: 100%;
        height: 100%;
        layout: grid;
        grid-size: 1;
        grid-rows: 4 1fr;
    }

    #sets-header {
        background: #0a0a14;
        border-bottom: heavy #c9a227;
        padding: 0 2;
        content-align: center middle;
    }

    /* Grid child must use 1fr to fill its row properly */
    #sets-main {
        width: 100%;
        height: 1fr;
    }

    /* Left pane - set list */
    #sets-list-pane {
        width: 20%;
        height: 100%;
        background: #0f0f0f;
        border-right: solid #3d3d3d;
        /* Grid layout: search (auto), list (fills), statusbar (auto) */
        layout: grid;
        grid-size: 1;
        grid-rows: auto 1fr auto;
    }

    #sets-search-container {
        height: 3;
        padding: 0 1;
        background: #151515;
        border-bottom: solid #2a2a2a;
    }

    #sets-search-input {
        width: 100%;
        background: #1a1a2e;
        border: tall #3d3d3d;
    }

    #sets-search-input:focus {
        border: tall #c9a227;
        background: #1e1e32;
    }

    #sets-list {
        height: 1fr;
        scrollbar-color: #c9a227;
        scrollbar-color-hover: #e6c84a;
    }

    #sets-list > ListItem {
        padding: 0 1;
        height: auto;
        border-bottom: solid #1a1a1a;
        background: #121212;
    }

    #sets-list > ListItem:hover {
        background: #1a1a2e;
        border-left: solid #5a5a6e;
    }

    #sets-list > ListItem.-highlight {
        background: #2a2a4e;
        border-left: heavy #c9a227;
    }

    /* Right pane - set detail (80% of screen) */
    #sets-detail-pane {
        width: 80%;
        height: 100%;
        background: #0a0a14;
    }

    /* Card list on left of detail pane - 44% of detail (35% of screen) */
    #set-card-list {
        width: 44%;
        height: 100%;
        background: #0a0a14;
        border-right: solid #3d3d3d;
    }

    /* Insights panel on right - 56% of detail (45% of screen) */
    #set-insights-panel {
        width: 56%;
        height: 100%;
        background: #0d0d0d;
        overflow-y: auto;
        padding: 0;
    }

    #sets-empty-detail {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: #666;
    }

    #sets-statusbar {
        height: 2;
        padding: 0 1;
        background: #1a1a1a;
        border-top: solid #3d3d3d;
        content-align: left middle;
    }
    """

    # Reactive state
    search_query: reactive[str] = reactive("")
    total_count: reactive[int] = reactive(0)
    filtered_count: reactive[int] = reactive(0)
    current_set_code: reactive[str | None] = reactive(None)
    current_filter: reactive[str | None] = reactive(None)
    active_pane: reactive[str] = reactive("set-list")
    show_artist_series_only: reactive[bool] = reactive(False)

    def __init__(self, db: UnifiedDatabase | None = None) -> None:
        super().__init__()
        self._db = db
        self._sets: list[SetSummary] = []
        self._filtered_sets: list[SetSummary] = []
        self._search_debounce_task: asyncio.Task[None] | None = None
        self._refresh_task: asyncio.Task[None] | None = None
        self._population_cancelled = False
        self._filter_index: int = 0
        self._rarity_filters = [None, "mythic", "rare", "uncommon", "common"]

    def compose_content(self) -> ComposeResult:
        # Header
        yield Static(
            self._render_header(),
            id="sets-header",
        )

        # Main content - statusbar is inside list pane to avoid grid issues
        with Horizontal(id="sets-main"):
            # Left pane - set list
            with Vertical(id="sets-list-pane"):
                with Horizontal(id="sets-search-container"):
                    yield Input(
                        placeholder="Search sets...",
                        id="sets-search-input",
                    )
                yield ListView(id="sets-list")

                # Status bar (inside list pane)
                yield Static(
                    self._render_statusbar(),
                    id="sets-statusbar",
                )

            # Right pane - set detail (initially empty)
            with Horizontal(id="sets-detail-pane"):
                yield Static(
                    "[dim]Select a set from the list[/]",
                    id="sets-empty-detail",
                )

    def _render_header(self) -> str:
        """Render header text."""
        art_badge = "[cyan][Art Series][/]  " if self.show_artist_series_only else ""
        if self.current_set_code:
            filter_text = ""
            if self.current_filter:
                filter_text = f"  [cyan]Filter: {self.current_filter.title()}[/]"
            return f"[bold {ui_colors.GOLD}]SETS[/]  {art_badge}[dim]viewing {self.current_set_code.upper()}[/]{filter_text}"
        if self.search_query or self.show_artist_series_only:
            return (
                f"[bold {ui_colors.GOLD}]SETS[/]  {art_badge}"
                f"[dim]showing {self.filtered_count} of {self.total_count}[/]"
            )
        return f"[bold {ui_colors.GOLD}]SETS[/]  [dim]({self.total_count} sets)[/]"

    def _render_statusbar(self) -> str:
        """Render status bar."""
        if self.active_pane == "set-list":
            art_hint = "[dim]on[/]" if self.show_artist_series_only else "off"
            parts = [
                f"[{ui_colors.TEXT_DIM}]jk/arrows: navigate[/]",
                f"[{ui_colors.GOLD}]Enter[/]: view set",
                f"[{ui_colors.GOLD}]e[/]: explore",
                f"[{ui_colors.GOLD}]a[/]: art series ({art_hint})",
                f"[{ui_colors.GOLD}]/[/]: search",
                f"[{ui_colors.GOLD}]Esc[/]: exit",
            ]
        else:
            parts = [
                f"[{ui_colors.TEXT_DIM}]jk/arrows: navigate cards[/]",
                f"[{ui_colors.GOLD}]e[/]: explore",
                f"[{ui_colors.GOLD}]f[/]: filter rarity",
                f"[{ui_colors.GOLD}]r[/]: random card",
                f"[{ui_colors.GOLD}]Tab[/]: switch pane",
                f"[{ui_colors.GOLD}]Esc[/]: back",
            ]
        return "  |  ".join(parts)

    def _update_header(self) -> None:
        """Update header display."""
        try:
            header = self.query_one("#sets-header", Static)
            header.update(self._render_header())
        except NoMatches:
            pass

    def _update_statusbar(self) -> None:
        """Update status bar display."""
        try:
            statusbar = self.query_one("#sets-statusbar", Static)
            statusbar.update(self._render_statusbar())
        except NoMatches:
            pass

    async def on_mount(self) -> None:
        """Load sets on mount."""
        # Focus the list
        try:
            set_list = self.query_one("#sets-list", ListView)
            set_list.focus()
        except NoMatches:
            pass

        # Load sets
        self._load_sets()

    @work
    async def _load_sets(self) -> None:
        """Load all sets from database."""
        if not self._db:
            return

        self._population_cancelled = False

        # Get all sets
        result = await sets.get_sets(self._db, name=None)
        self._sets = result.sets
        self._filtered_sets = self._sets
        self.total_count = len(self._sets)
        self.filtered_count = len(self._sets)

        # Populate list
        await self._populate_list()

        # Update UI
        self._update_header()

    async def _populate_list(self) -> None:
        """Populate the ListView with sets."""
        try:
            set_list = self.query_one("#sets-list", ListView)
            await set_list.clear()

            if not self._filtered_sets:
                return

            batch_count = 0
            for set_data in self._filtered_sets[:100]:  # Limit to 100 for performance
                if self._population_cancelled:
                    return

                item = SetListItem(set_data, classes="set-item")
                await set_list.append(item)
                batch_count += 1

                if batch_count >= 50:
                    batch_count = 0
                    await asyncio.sleep(0)

            # Select first item
            if set_list.children:
                set_list.index = 0

        except NoMatches:
            pass

    def _filter_sets(self, query: str) -> list[SetSummary]:
        """Filter sets by search query and artist series toggle."""
        sets = self._sets

        # Filter to artist series if enabled (sets starting with 'A')
        if self.show_artist_series_only:
            sets = [s for s in sets if s.code.upper().startswith("A")]

        # Then apply search query
        if query:
            query_lower = query.lower()
            sets = [
                s for s in sets if query_lower in s.name.lower() or query_lower in s.code.lower()
            ]

        return sets

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes with debouncing."""
        if event.input.id == "sets-search-input":
            if self._search_debounce_task is not None:
                self._search_debounce_task.cancel()
                self._search_debounce_task = None

            self._population_cancelled = True
            self._search_debounce_task = asyncio.create_task(self._debounced_search(event.value))

    async def _debounced_search(self, query: str) -> None:
        """Execute search after debounce delay."""
        try:
            await asyncio.sleep(SEARCH_DEBOUNCE_MS / 1000)
        except asyncio.CancelledError:
            return

        self._population_cancelled = False
        self.search_query = query.strip()
        self._filtered_sets = self._filter_sets(query)
        self.filtered_count = len(self._filtered_sets)

        await self._populate_list()

        if not self._population_cancelled:
            self._update_header()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Focus list after search submit."""
        if event.input.id == "sets-search-input":
            try:
                set_list = self.query_one("#sets-list", ListView)
                set_list.focus()
            except NoMatches:
                pass

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle set selection."""
        if event.list_view.id == "sets-list":
            item = event.item
            if isinstance(item, SetListItem):
                self._load_set_detail(item.set_data.code)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Track active pane."""
        if event.list_view.id == "sets-list":
            self.active_pane = "set-list"
            self._update_statusbar()
        elif event.list_view.id == "set-card-list":
            self.active_pane = "set-detail"
            self._update_statusbar()

    @work(exclusive=True, group="set_detail")
    async def _load_set_detail(self, set_code: str) -> None:
        """Load and display set detail."""
        if not self._db:
            return

        self.current_set_code = set_code
        self.current_filter = None
        self._filter_index = 0

        # Get set data
        set_data = await self._db.get_set(set_code)

        if not set_data:
            self.notify(f"Could not load set: {set_code}", severity="warning")
            return

        # Get cards via search_cards with set_code filter
        from mtg_core.data.models.inputs import SearchCardsInput
        from mtg_core.data.models.responses import CardSummary

        filters = SearchCardsInput(set_code=set_code)
        cards, _total = await self._db.search_cards(filters)

        if not cards:
            self.notify(f"No cards found in set: {set_code}", severity="warning")
            return

        # Convert to CardSummary
        summaries: list[CardSummary] = []
        for card in cards:
            summary = CardSummary(
                uuid=card.uuid,
                name=card.name,
                mana_cost=card.mana_cost,
                type=card.type,
                colors=card.colors or [],
                rarity=card.rarity,
                set_code=card.set_code,
                collector_number=card.number,  # Card model uses 'number' not 'collector_number'
            )
            summaries.append(summary)

        # Calculate stats
        rarity_counts = {"mythic": 0, "rare": 0, "uncommon": 0, "common": 0}
        type_counts: dict[str, int] = {}

        for card in cards:
            if card.rarity:
                rarity = card.rarity.lower()
                if rarity in rarity_counts:
                    rarity_counts[rarity] += 1
            if card.type:
                main_type = card.type.split()[0]
                type_counts[main_type] = type_counts.get(main_type, 0) + 1

        stats = SetStats(
            total_cards=len(cards),
            rarity_distribution=rarity_counts,
            color_distribution={},
        )

        # Update detail pane
        await self._show_set_detail(set_data, summaries, stats)
        self._update_header()

    async def _show_set_detail(
        self, set_data: Set, cards: list[CardSummary], _stats: SetStats
    ) -> None:
        """Show the set detail panel with insights."""
        try:
            detail_pane = self.query_one("#sets-detail-pane", Horizontal)

            # Remove empty placeholder
            try:
                empty = self.query_one("#sets-empty-detail", Static)
                await empty.remove()
            except NoMatches:
                pass

            # Check if detail widgets already exist
            try:
                self.query_one("#set-insights-panel", SetInsightsPanel)
                # Update existing widgets
                card_list = self.query_one("#set-card-list", SetCardList)
                await card_list.load_cards(cards)
                card_list.focus()

                # Load analysis asynchronously
                self._load_set_analysis(set_data.code)

            except NoMatches:
                # Create new detail widgets - card list and insights only (per design)
                card_list = SetCardList(id="set-card-list")
                insights_panel = SetInsightsPanel(id="set-insights-panel")

                await detail_pane.mount(card_list)
                await detail_pane.mount(insights_panel)

                await card_list.load_cards(cards)
                card_list.focus()

                # Load analysis asynchronously
                self._load_set_analysis(set_data.code)

            self.active_pane = "set-detail"
            self._update_statusbar()

        except NoMatches:
            pass

    @work(exclusive=True, group="set_analysis")
    async def _load_set_analysis(self, set_code: str) -> None:
        """Load set analysis data asynchronously."""
        if not self._db:
            return

        analysis = await analyze_set(self._db, set_code)

        try:
            insights_panel = self.query_one("#set-insights-panel", SetInsightsPanel)
            insights_panel.update_analysis(analysis)
        except NoMatches:
            pass

    # Actions

    def action_back_or_exit(self) -> None:
        """Go back to set list or exit."""
        if self.current_set_code and self.active_pane == "set-detail":
            # Go back to set list
            self.active_pane = "set-list"
            self._update_statusbar()
            try:
                set_list = self.query_one("#sets-list", ListView)
                set_list.focus()
            except NoMatches:
                pass
        else:
            # Exit screen
            self.dismiss()

    def action_exit(self) -> None:
        """Exit the sets screen."""
        self.dismiss()

    def action_select(self) -> None:
        """Select the current item."""
        if self.active_pane == "set-list":
            try:
                set_list = self.query_one("#sets-list", ListView)
                if set_list.index is not None and set_list.children:
                    item = set_list.children[set_list.index]
                    if isinstance(item, SetListItem):
                        self._load_set_detail(item.set_data.code)
            except NoMatches:
                pass
        else:
            # Select card from set detail
            try:
                card_list = self.query_one("#set-card-list", SetCardList)
                card = card_list.get_current_card()
                if card:
                    # Pop all screens to return to home before showing card
                    app = self.app
                    while len(app.screen_stack) > 1:
                        app.pop_screen()
                    if hasattr(app, "lookup_card"):
                        app.lookup_card(
                            card.name,
                            target_set=card.set_code,
                            target_number=card.collector_number,
                        )
            except NoMatches:
                pass

    def action_focus_search(self) -> None:
        """Focus the search input."""
        try:
            search = self.query_one("#sets-search-input", Input)
            search.focus()
        except NoMatches:
            pass

    def action_toggle_pane(self) -> None:
        """Toggle between set list and detail panes."""
        if self.active_pane == "set-list" and self.current_set_code:
            try:
                card_list = self.query_one("#set-card-list", SetCardList)
                card_list.focus()
                self.active_pane = "set-detail"
            except NoMatches:
                pass
        else:
            try:
                set_list = self.query_one("#sets-list", ListView)
                set_list.focus()
                self.active_pane = "set-list"
            except NoMatches:
                pass
        self._update_statusbar()

    def action_toggle_filter(self) -> None:
        """Cycle through rarity filters (only in detail view)."""
        if self.active_pane != "set-detail":
            return

        self._filter_index = (self._filter_index + 1) % len(self._rarity_filters)
        rarity = self._rarity_filters[self._filter_index]
        self.current_filter = rarity

        try:
            card_list = self.query_one("#set-card-list", SetCardList)
            card_list.filter_cards(rarity=rarity)
        except NoMatches:
            pass

        self._update_header()

    def action_random_card(self) -> None:
        """Select a random card from the set (only in detail view)."""
        if self.active_pane != "set-detail":
            return

        try:
            card_list = self.query_one("#set-card-list", SetCardList)
            card_list.select_random()
        except NoMatches:
            pass

    def action_explore_set(self) -> None:
        """Load set cards into main results and return to home."""
        # Get set code from either current detail view or selected list item
        set_code: str | None = None

        if self.current_set_code:
            set_code = self.current_set_code
        elif self.active_pane == "set-list":
            try:
                set_list = self.query_one("#sets-list", ListView)
                if set_list.index is not None and set_list.children:
                    item = set_list.children[set_list.index]
                    if isinstance(item, SetListItem):
                        set_code = item.set_data.code
            except NoMatches:
                pass

        if not set_code:
            return

        app = self.app

        # Pop all screens to return to home
        while len(app.screen_stack) > 1:
            app.pop_screen()

        # Show search view first (before loading cards)
        if hasattr(app, "_show_search_view"):
            app._show_search_view()
            app.notify(f"Loading cards from {set_code.upper()}...", timeout=2)

        # Load cards from this set into results
        if hasattr(app, "explore_set"):
            app.explore_set(set_code)

    def action_filter_artist_series(self) -> None:
        """Toggle filter to show only artist series sets."""
        self.show_artist_series_only = not self.show_artist_series_only
        self._filtered_sets = self._filter_sets(self.search_query)
        self.filtered_count = len(self._filtered_sets)
        self._apply_filters()

    def _apply_filters(self) -> None:
        """Apply current filters and refresh the list."""
        self._population_cancelled = True
        self._refresh_task = asyncio.create_task(self._refresh_list())

    async def _refresh_list(self) -> None:
        """Refresh the list with current filters."""
        self._population_cancelled = False
        await self._populate_list()
        if not self._population_cancelled:
            self._update_header()
            self._update_statusbar()

    def action_nav_up(self) -> None:
        """Navigate up in active list."""
        if self.active_pane == "set-list":
            try:
                set_list = self.query_one("#sets-list", ListView)
                set_list.action_cursor_up()
            except NoMatches:
                pass
        else:
            try:
                card_list = self.query_one("#set-card-list", SetCardList)
                card_list.action_cursor_up()
            except NoMatches:
                pass

    def action_nav_down(self) -> None:
        """Navigate down in active list."""
        if self.active_pane == "set-list":
            try:
                set_list = self.query_one("#sets-list", ListView)
                set_list.action_cursor_down()
            except NoMatches:
                pass
        else:
            try:
                card_list = self.query_one("#set-card-list", SetCardList)
                card_list.action_cursor_down()
            except NoMatches:
                pass

    def action_page_up(self) -> None:
        """Page up in active list."""
        if self.active_pane == "set-list":
            try:
                set_list = self.query_one("#sets-list", ListView)
                set_list.action_page_up()
            except NoMatches:
                pass
        else:
            try:
                card_list = self.query_one("#set-card-list", SetCardList)
                card_list.action_page_up()
            except NoMatches:
                pass

    def action_page_down(self) -> None:
        """Page down in active list."""
        if self.active_pane == "set-list":
            try:
                set_list = self.query_one("#sets-list", ListView)
                set_list.action_page_down()
            except NoMatches:
                pass
        else:
            try:
                card_list = self.query_one("#set-card-list", SetCardList)
                card_list.action_page_down()
            except NoMatches:
                pass

    def action_first(self) -> None:
        """Go to first item in active list."""
        if self.active_pane == "set-list":
            try:
                set_list = self.query_one("#sets-list", ListView)
                if set_list.children:
                    set_list.index = 0
            except NoMatches:
                pass
        else:
            try:
                card_list = self.query_one("#set-card-list", SetCardList)
                card_list.action_first()
            except NoMatches:
                pass

    def action_last_item(self) -> None:
        """Go to last item in active list."""
        if self.active_pane == "set-list":
            try:
                set_list = self.query_one("#sets-list", ListView)
                if set_list.children:
                    set_list.index = len(set_list.children) - 1
            except NoMatches:
                pass
        else:
            try:
                card_list = self.query_one("#set-card-list", SetCardList)
                card_list.action_last()
            except NoMatches:
                pass
