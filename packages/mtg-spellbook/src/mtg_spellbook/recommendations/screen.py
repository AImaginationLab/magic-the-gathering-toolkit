"""Full-screen recommendations view with collection integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.events import Key
from textual.widgets import ListView, Static

from ..screens import BaseScreen
from ..ui.theme import ui_colors
from .card_item import RecommendationCardItem
from .detail_panel import RecommendationDetailPanel
from .filter_panel import (
    FilterChanged,
    FilterType,
    RecommendationFilterPanel,
    SortChanged,
    SortOrder,
)
from .messages import AddCardToDeck, RecommendationScreenClosed

if TYPE_CHECKING:
    from mtg_core.tools.recommendations.hybrid import HybridRecommender, ScoredRecommendation

    from ..deck_manager import DeckManager, DeckWithCards


class RecommendationScreen(BaseScreen[None]):
    """Full-screen recommendations view with filtering and sorting.

    Three-pane layout:
    - Left (20%): Filter options
    - Center (50%): Card list
    - Right (30%): Detail view with score breakdown
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape,q", "close_screen", "Close", show=True),
        Binding("tab", "toggle_focus", "Switch Pane", show=False),
        Binding("f", "cycle_filter", "Filter", show=True),
        Binding("s", "cycle_sort", "Sort", show=True),
        Binding("space", "add_one", "Add 1", show=True),
        Binding("1", "add_qty_1", "Add 1", show=False),
        Binding("2", "add_qty_2", "Add 2", show=False),
        Binding("3", "add_qty_3", "Add 3", show=False),
        Binding("4", "add_qty_4", "Add 4", show=False),
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
    RecommendationScreen {
        background: #0d0d0d;
    }

    #rec-header {
        height: 3;
        background: #0a0a14;
        border-bottom: heavy #c9a227;
        padding: 0 2;
        content-align: center middle;
    }

    #rec-main {
        width: 100%;
        height: 1fr;
    }

    #rec-filter-pane {
        width: 20%;
        height: 100%;
        background: #0f0f0f;
        border-right: solid #3d3d3d;
        overflow-y: auto;
    }

    #rec-list-pane {
        width: 50%;
        height: 100%;
        background: #0a0a14;
        border-right: solid #3d3d3d;
    }

    #rec-list-header {
        height: 2;
        padding: 0 1;
        background: #121218;
        border-bottom: solid #2a2a2a;
        content-align: left middle;
    }

    #rec-list {
        height: 1fr;
        scrollbar-color: #c9a227;
        scrollbar-color-hover: #e6c84a;
    }

    #rec-list > ListItem {
        height: auto;
        border-bottom: solid #1a1a1a;
        background: #121212;
    }

    #rec-list > ListItem:hover {
        background: #1a1a2e;
    }

    #rec-list > ListItem.-highlight {
        background: #2a2a4e;
        border-left: heavy #c9a227;
    }

    #rec-detail-pane {
        width: 30%;
        height: 100%;
        background: #0d0d0d;
    }

    #rec-statusbar {
        height: 2;
        padding: 0 1;
        background: #1a1a1a;
        border-top: solid #3d3d3d;
        content-align: left middle;
    }
    """

    def __init__(
        self,
        deck: DeckWithCards,
        recommender: HybridRecommender,
        collection_cards: set[str] | None = None,
        deck_manager: DeckManager | None = None,
    ) -> None:
        super().__init__()
        self._deck = deck
        self._recommender = recommender
        self._collection_cards = collection_cards or set()
        self._deck_manager = deck_manager

        # Recommendation data
        self._all_recommendations: list[ScoredRecommendation] = []
        self._filtered_recommendations: list[ScoredRecommendation] = []
        self._current_recommendation: ScoredRecommendation | None = None

        # State
        self._active_filter = FilterType.ALL
        self._active_sort = SortOrder.SCORE
        self._active_pane = "list"

    def compose_content(self) -> ComposeResult:
        deck_name = self._deck.name if self._deck else "Unknown"
        yield Static(
            f'[bold {ui_colors.GOLD}]{chr(0x2728)} RECOMMENDATIONS FOR[/] "{deck_name}"',
            id="rec-header",
        )

        with Horizontal(id="rec-main"):
            # Filter pane (left)
            with Vertical(id="rec-filter-pane"):
                yield RecommendationFilterPanel(id="rec-filter-panel")

            # List pane (center)
            with Vertical(id="rec-list-pane"):
                yield Static("Loading...", id="rec-list-header")
                yield ListView(id="rec-list")

            # Detail pane (right)
            with Vertical(id="rec-detail-pane"):
                yield RecommendationDetailPanel(id="rec-detail-panel")

        yield Static(self._render_statusbar(), id="rec-statusbar")

    async def on_mount(self) -> None:
        """Load recommendations on mount."""
        self._load_recommendations()

    @work(exclusive=True, group="recommendations")
    async def _load_recommendations(self) -> None:
        """Load recommendations from the hybrid recommender."""
        if not self._recommender.is_initialized:
            self._show_loading_error("Recommender not initialized")
            return

        # Get deck cards
        deck_cards = []
        if self._deck:
            for card in self._deck.mainboard:
                deck_cards.append(
                    {
                        "name": card.card_name,
                        "quantity": card.quantity,
                    }
                )

        # Get recommendations (this is blocking but fast)
        recommendations = self._recommender.recommend_for_deck(deck_cards, n=100, explain=True)

        self._on_recommendations_loaded(recommendations)

    def _on_recommendations_loaded(self, recommendations: list[ScoredRecommendation]) -> None:
        """Handle loaded recommendations."""
        self._all_recommendations = recommendations
        self._apply_filters()
        self._update_filter_counts()
        self._update_list_header()
        self._populate_list()

        # Focus first item
        try:
            list_view = self.query_one("#rec-list", ListView)
            if list_view.children:
                list_view.index = 0
                list_view.focus()
        except NoMatches:
            pass

    def _show_loading_error(self, message: str) -> None:
        """Show loading error."""
        try:
            header = self.query_one("#rec-list-header", Static)
            header.update(f"[red]Error: {message}[/]")
        except NoMatches:
            pass

    def _apply_filters(self) -> None:
        """Apply current filter to recommendations."""
        filtered = self._all_recommendations

        if self._active_filter == FilterType.OWNED:
            filtered = [r for r in filtered if r.name in self._collection_cards]
        elif self._active_filter == FilterType.NEED:
            filtered = [r for r in filtered if r.name not in self._collection_cards]
        elif self._active_filter == FilterType.COMBOS:
            filtered = [r for r in filtered if r.completes_combos]
        elif self._active_filter == FilterType.TOP_TIER:
            filtered = [r for r in filtered if r.total_score >= 0.7 or r.limited_tier in ("S", "A")]

        # Apply sort
        if self._active_sort == SortOrder.SCORE:
            filtered.sort(key=lambda r: -r.total_score)
        elif self._active_sort == SortOrder.OWNED_FIRST:
            filtered.sort(
                key=lambda r: (0 if r.name in self._collection_cards else 1, -r.total_score)
            )
        elif self._active_sort == SortOrder.CMC:
            filtered.sort(key=lambda r: (self._get_cmc(r.mana_cost), r.name))
        elif self._active_sort == SortOrder.NAME:
            filtered.sort(key=lambda r: r.name.lower())

        self._filtered_recommendations = filtered

    def _get_cmc(self, mana_cost: str | None) -> int:
        """Extract CMC from mana cost string."""
        if not mana_cost:
            return 0
        # Count symbols
        count = 0
        in_brace = False
        num = ""
        for c in mana_cost:
            if c == "{":
                in_brace = True
                num = ""
            elif c == "}":
                if num.isdigit():
                    count += int(num)
                elif num and num != "X":
                    count += 1
                in_brace = False
            elif in_brace:
                num += c
        return count

    def _update_filter_counts(self) -> None:
        """Update filter counts in filter panel."""
        try:
            panel = self.query_one("#rec-filter-panel", RecommendationFilterPanel)
            all_count = len(self._all_recommendations)
            owned_count = sum(
                1 for r in self._all_recommendations if r.name in self._collection_cards
            )
            need_count = all_count - owned_count
            combos_count = sum(1 for r in self._all_recommendations if r.completes_combos)
            top_count = sum(
                1
                for r in self._all_recommendations
                if r.total_score >= 0.7 or r.limited_tier in ("S", "A")
            )
            panel.set_counts(all_count, owned_count, need_count, combos_count, top_count)
        except NoMatches:
            pass

    def _update_list_header(self) -> None:
        """Update list header with count."""
        try:
            header = self.query_one("#rec-list-header", Static)
            count = len(self._filtered_recommendations)
            total = len(self._all_recommendations)
            if count == total:
                header.update(f"[{ui_colors.TEXT_DIM}]{count} recommendations[/]")
            else:
                header.update(f"[{ui_colors.TEXT_DIM}]Showing {count} of {total}[/]")
        except NoMatches:
            pass

    def _populate_list(self) -> None:
        """Populate the card list."""
        try:
            list_view = self.query_one("#rec-list", ListView)
            list_view.clear()

            for rec in self._filtered_recommendations:
                in_collection = rec.name in self._collection_cards
                item = RecommendationCardItem(rec, in_collection=in_collection)
                list_view.append(item)

        except NoMatches:
            pass

    def _render_statusbar(self) -> str:
        """Render status bar with shortcuts."""
        parts = [
            f"[{ui_colors.GOLD}]f[/]:Filter",
            f"[{ui_colors.GOLD}]s[/]:Sort",
            f"[{ui_colors.GOLD}]Space[/]:Add",
            f"[{ui_colors.GOLD}]1-4[/]:AddQty",
            f"[{ui_colors.GOLD}]Tab[/]:Pane",
            f"[{ui_colors.GOLD}]Esc[/]:Close",
        ]
        return "  ".join(parts)

    @on(ListView.Highlighted)
    def on_list_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle card highlight in list."""
        if event.item and isinstance(event.item, RecommendationCardItem):
            rec = event.item.recommendation
            self._current_recommendation = rec
            self._update_detail_panel(rec)

    @on(ListView.Selected)
    def on_list_selected(self, event: ListView.Selected) -> None:
        """Handle card selection (Enter key)."""
        if event.item and isinstance(event.item, RecommendationCardItem):
            rec = event.item.recommendation
            self._current_recommendation = rec
            self._update_detail_panel(rec)

    def _update_detail_panel(self, rec: ScoredRecommendation) -> None:
        """Update the detail panel with recommendation info."""
        try:
            panel = self.query_one("#rec-detail-panel", RecommendationDetailPanel)
            in_collection = rec.name in self._collection_cards
            panel.show_recommendation(rec, in_collection=in_collection)
        except NoMatches:
            pass

    @on(FilterChanged)
    def on_filter_changed(self, event: FilterChanged) -> None:
        """Handle filter change from filter panel."""
        self._active_filter = event.filter_type
        self._apply_filters()
        self._update_list_header()
        self._populate_list()

    @on(SortChanged)
    def on_sort_changed(self, event: SortChanged) -> None:
        """Handle sort change from filter panel."""
        self._active_sort = event.sort_order
        self._apply_filters()
        self._populate_list()

    def action_close_screen(self) -> None:
        """Close the recommendations screen."""
        self.post_message(RecommendationScreenClosed())
        self.app.pop_screen()

    def action_toggle_focus(self) -> None:
        """Toggle focus between panes."""
        try:
            if self._active_pane == "list":
                filter_panel = self.query_one("#rec-filter-panel", RecommendationFilterPanel)
                filter_panel.focus()
                self._active_pane = "filter"
            else:
                list_view = self.query_one("#rec-list", ListView)
                list_view.focus()
                self._active_pane = "list"
        except NoMatches:
            pass

    def action_cycle_filter(self) -> None:
        """Cycle filter options."""
        try:
            panel = self.query_one("#rec-filter-panel", RecommendationFilterPanel)
            panel.cycle_filter()
        except NoMatches:
            pass

    def action_cycle_sort(self) -> None:
        """Cycle sort options."""
        try:
            panel = self.query_one("#rec-filter-panel", RecommendationFilterPanel)
            panel.cycle_sort()
        except NoMatches:
            pass

    def _add_to_deck(self, quantity: int) -> None:
        """Add current card to deck."""
        if not self._current_recommendation:
            return
        if not self._deck_manager or not self._deck:
            self.notify("Cannot add: no deck manager", severity="error")
            return

        card_name = self._current_recommendation.name
        self._do_add_to_deck(card_name, quantity)

    @work(exclusive=True, group="deck_add")
    async def _do_add_to_deck(self, card_name: str, quantity: int) -> None:
        """Actually add the card to the deck."""
        if not self._deck_manager or not self._deck:
            return

        result = await self._deck_manager.add_card(self._deck.id, card_name, quantity)
        if result.success:
            self.notify(f"Added {quantity}x {card_name} to deck")
            # Directly refresh the deck screen in the stack
            self._refresh_deck_screen()
            # Also post message for any other listeners
            self.post_message(AddCardToDeck(card_name, quantity))
        else:
            self.notify(f"Failed to add: {result.error}", severity="error")

    def _refresh_deck_screen(self) -> None:
        """Find and refresh the FullDeckScreen in the screen stack."""
        from ..deck import FullDeckScreen

        try:
            for screen in self.app.screen_stack:
                if isinstance(screen, FullDeckScreen) and screen._current_deck:
                    screen._load_deck(screen._current_deck.id)
                    break
        except (LookupError, AttributeError):
            pass  # No app context (e.g., in tests)

    def action_add_one(self) -> None:
        self._add_to_deck(1)

    def action_add_qty_1(self) -> None:
        self._add_to_deck(1)

    def action_add_qty_2(self) -> None:
        self._add_to_deck(2)

    def action_add_qty_3(self) -> None:
        self._add_to_deck(3)

    def action_add_qty_4(self) -> None:
        self._add_to_deck(4)

    def action_nav_up(self) -> None:
        try:
            list_view = self.query_one("#rec-list", ListView)
            list_view.action_cursor_up()
        except NoMatches:
            pass

    def action_nav_down(self) -> None:
        try:
            list_view = self.query_one("#rec-list", ListView)
            list_view.action_cursor_down()
        except NoMatches:
            pass

    def action_page_up(self) -> None:
        try:
            list_view = self.query_one("#rec-list", ListView)
            list_view.action_page_up()
        except NoMatches:
            pass

    def action_page_down(self) -> None:
        try:
            list_view = self.query_one("#rec-list", ListView)
            list_view.action_page_down()
        except NoMatches:
            pass

    def action_first(self) -> None:
        try:
            list_view = self.query_one("#rec-list", ListView)
            if list_view.children:
                list_view.index = 0
        except NoMatches:
            pass

    def action_last_item(self) -> None:
        try:
            list_view = self.query_one("#rec-list", ListView)
            if list_view.children:
                list_view.index = len(list_view.children) - 1
        except NoMatches:
            pass

    def on_key(self, event: Key) -> None:
        """Handle key events."""
        # Let list handle navigation
        if event.key in ("up", "down", "j", "k", "pageup", "pagedown", "home", "end"):
            return
