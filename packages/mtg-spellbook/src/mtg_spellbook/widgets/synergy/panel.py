"""Simplified synergy panel following Artist Browser pattern."""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.events import Key
from textual.reactive import reactive
from textual.widgets import Input, ListItem, ListView, Static

from ...formatting import prettify_mana
from ...ui.theme import ui_colors
from .card_item import SynergyCardItem
from .messages import SynergyPanelClosed, SynergySelected

if TYPE_CHECKING:
    from mtg_core.data.models.responses import CardDetail, FindSynergiesResult, SynergyResult

# Debounce delay for search input (milliseconds)
SEARCH_DEBOUNCE_MS = 150
# Batch size for progressive list loading
LIST_BATCH_SIZE = 100


class SortOrder(Enum):
    """Sort order options."""

    OWNED_FIRST = "owned"
    SCORE_DESC = "score"
    CMC_ASC = "cmc"
    NAME_ASC = "name"


class TypeIndex(Static):
    """Type filter pills shown horizontally."""

    # Keyboard shortcuts for each type
    TYPE_KEYS: ClassVar[dict[str, str]] = {
        "all": "a",
        "combo": "c",
        "keyword": "k",
        "tribal": "t",
        "ability": "b",
        "theme": "h",
    }

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._type_counts: dict[str, int] = {}
        self._active_type: str = "all"

    def update_counts(self, counts: dict[str, int], active: str = "all") -> None:
        """Update type counts and active filter."""
        self._type_counts = counts
        self._active_type = active
        self.update(self._render_index())

    def _render_index(self) -> str:
        """Render horizontal filter pills."""
        types = [
            ("all", "All"),
            ("combo", "Combo"),
            ("keyword", "Keyword"),
            ("tribal", "Tribal"),
            ("ability", "Ability"),
            ("theme", "Theme"),
        ]

        pills = []
        for type_key, label in types:
            count = self._type_counts.get(type_key, 0)
            key = self.TYPE_KEYS.get(type_key, "")
            if type_key == self._active_type:
                pills.append(f"[bold {ui_colors.GOLD} on #333]〈{key}〉{label}({count})[/]")
            elif count > 0:
                pills.append(f"[{ui_colors.TEXT_DIM}]〈{key}〉{label}({count})[/]")
            else:
                pills.append(f"[dim]〈{key}〉{label}(0)[/]")

        return "  ".join(pills)


class EnhancedSynergyPanel(Vertical, can_focus=True):
    """Simplified synergy panel with filterable list and sidebar index."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape,q", "close", "Close"),
        Binding("up,k", "nav_up", "Up", show=False),
        Binding("down,j", "nav_down", "Down", show=False),
        Binding("pageup", "page_up", "Page Up", show=False),
        Binding("pagedown", "page_down", "Page Down", show=False),
        Binding("home", "first", "First", show=False),
        Binding("end", "last_item", "Last", show=False),
        Binding("enter", "select_synergy", "View"),
        Binding("s", "cycle_sort", "Sort"),
        Binding("/", "focus_search", "Search"),
    ]

    is_loading: reactive[bool] = reactive(False)
    search_query: reactive[str] = reactive("")
    total_count: reactive[int] = reactive(0)
    filtered_count: reactive[int] = reactive(0)
    current_sort: reactive[SortOrder] = reactive(SortOrder.SCORE_DESC)

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._source_card: CardDetail | None = None
        self._all_synergies: list[SynergyResult] = []
        self._filtered_synergies: list[SynergyResult] = []
        self._type_counts: dict[str, int] = {}
        self._active_type: str = "all"
        self._search_debounce_task: asyncio.Task[None] | None = None
        self._population_cancelled = False
        self._collection_cards: set[str] = set()  # Card names in user's collection

    def compose(self) -> ComposeResult:
        with Vertical(classes="synergy-panel-container"):
            # Header row 1: Title and search
            with Horizontal(classes="synergy-panel-header"):
                yield Static(
                    self._render_header(),
                    id="synergy-panel-title",
                    classes="synergy-panel-title",
                )
                yield Input(
                    placeholder="Search synergies...",
                    id="synergy-search",
                    classes="synergy-search",
                )

            # Header row 2: Type filter pills
            yield TypeIndex(id="type-index", classes="type-index-pills")

            # Synergy list (full width now)
            yield ListView(id="synergy-list", classes="synergy-list")

            # Status bar
            yield Static(
                self._render_statusbar(),
                id="synergy-statusbar",
                classes="synergy-statusbar",
            )

    def on_mount(self) -> None:
        """Focus the list on mount."""
        try:
            synergy_list = self.query_one("#synergy-list", ListView)
            synergy_list.focus()
        except NoMatches:
            pass

    def _render_header(self) -> str:
        """Render header text."""
        if not self._source_card:
            return f"[bold {ui_colors.GOLD}]Synergies[/]"

        card = self._source_card
        mana = prettify_mana(card.mana_cost) if card.mana_cost else ""

        if self.search_query or self._active_type != "all":
            return (
                f"[bold {ui_colors.GOLD}]Synergies for {card.name}[/] {mana}  "
                f"[dim]showing {self.filtered_count} of {self.total_count}[/]"
            )

        return (
            f"[bold {ui_colors.GOLD}]Synergies for {card.name}[/] {mana}  "
            f"[dim]({self.total_count} found)[/]"
        )

    def _render_statusbar(self) -> str:
        """Render status bar."""
        sort_labels = {
            SortOrder.OWNED_FIRST: "Owned",
            SortOrder.SCORE_DESC: "Score",
            SortOrder.CMC_ASC: "CMC",
            SortOrder.NAME_ASC: "Name",
        }
        sort_label = sort_labels[self.current_sort]

        parts = [
            f"[{ui_colors.TEXT_DIM}]Sort: [{ui_colors.GOLD}]{sort_label}[/][/]",
            f"[{ui_colors.TEXT_DIM}]jk/arrows: navigate[/]",
            f"[{ui_colors.GOLD}]a/c/k/t/b/h[/]: filter type",
            f"[{ui_colors.GOLD}]s[/]: sort",
            f"[{ui_colors.GOLD}]/[/]: search",
            f"[{ui_colors.GOLD}]Enter[/]: view",
            f"[{ui_colors.GOLD}]Esc[/]: close",
        ]
        return "  |  ".join(parts)

    def _update_header(self) -> None:
        """Update header display."""
        try:
            title = self.query_one("#synergy-panel-title", Static)
            title.update(self._render_header())
        except NoMatches:
            pass

    def _update_statusbar(self) -> None:
        """Update status bar."""
        try:
            statusbar = self.query_one("#synergy-statusbar", Static)
            statusbar.update(self._render_statusbar())
        except NoMatches:
            pass

    def _update_type_index(self) -> None:
        """Update type index display."""
        try:
            index = self.query_one("#type-index", TypeIndex)
            index.update_counts(self._type_counts, self._active_type)
        except NoMatches:
            pass

    async def load_synergies(
        self,
        result: FindSynergiesResult,
        source_card: CardDetail | None = None,
        collection_cards: set[str] | None = None,
    ) -> None:
        """Load synergy results and display."""
        self.is_loading = True
        self._population_cancelled = False
        self._source_card = source_card
        self._collection_cards = collection_cards or set()
        self._all_synergies = list(result.synergies)
        self.total_count = len(self._all_synergies)

        # Calculate type counts
        self._calculate_type_counts()

        # Reset filters
        self._active_type = "all"
        self.search_query = ""

        # Apply initial filtering (just all items, sorted)
        self._filter_synergies()

        try:
            await self._populate_list_batched(self._filtered_synergies)
            if not self._population_cancelled:
                self._update_header()
                self._update_type_index()
                self._update_statusbar()
        finally:
            self.is_loading = False

    def _calculate_type_counts(self) -> None:
        """Calculate synergy counts by type."""
        self._type_counts = {
            "all": len(self._all_synergies),
            "combo": 0,
            "keyword": 0,
            "tribal": 0,
            "ability": 0,
            "theme": 0,
        }

        for syn in self._all_synergies:
            syn_type = syn.synergy_type
            if syn_type in self._type_counts:
                self._type_counts[syn_type] += 1
            elif syn_type == "archetype":
                self._type_counts["theme"] += 1

    def _filter_synergies(self) -> None:
        """Filter synergies by type and search query."""
        # Start with all synergies
        filtered = self._all_synergies

        # Apply type filter
        if self._active_type != "all":
            filtered = [
                s
                for s in filtered
                if s.synergy_type == self._active_type
                or (self._active_type == "theme" and s.synergy_type == "archetype")
            ]

        # Apply search filter
        if self.search_query:
            query_lower = self.search_query.lower()
            filtered = [
                s
                for s in filtered
                if query_lower in s.name.lower() or query_lower in s.reason.lower()
            ]

        self._filtered_synergies = filtered
        self.filtered_count = len(filtered)

        # Apply sorting
        self._sort_synergies()

    def _sort_synergies(self) -> None:
        """Sort filtered synergies based on current sort order."""
        if self.current_sort == SortOrder.OWNED_FIRST:
            # Sort by owned first (0 for owned, 1 for not owned), then by score descending
            self._filtered_synergies.sort(
                key=lambda s: (0 if s.name in self._collection_cards else 1, -s.score)
            )
        elif self.current_sort == SortOrder.SCORE_DESC:
            self._filtered_synergies.sort(key=lambda s: s.score, reverse=True)
        elif self.current_sort == SortOrder.CMC_ASC:
            # Sort by estimated CMC (count mana symbols)
            def estimate_cmc(syn: SynergyResult) -> float:
                if not syn.mana_cost:
                    return 999.0
                import re

                cmc = 0.0
                generic = re.findall(r"\{(\d+)\}", syn.mana_cost)
                for g in generic:
                    cmc += int(g)
                colored = re.findall(r"\{[WUBRG]\}", syn.mana_cost)
                cmc += len(colored)
                return cmc

            self._filtered_synergies.sort(key=estimate_cmc)
        elif self.current_sort == SortOrder.NAME_ASC:
            self._filtered_synergies.sort(key=lambda s: s.name.lower())

    async def _populate_list_batched(self, synergies: list[SynergyResult]) -> None:
        """Populate the ListView with synergies in batches to avoid UI blocking."""
        try:
            synergy_list = self.query_one("#synergy-list", ListView)
            await synergy_list.clear()

            if not synergies:
                # Show empty state
                empty_item = ListItem(Static(f"[{ui_colors.TEXT_DIM}]No synergies found[/]"))
                await synergy_list.append(empty_item)
                return

            batch_count = 0

            for i, synergy in enumerate(synergies):
                # Check if population was cancelled (e.g., new search started)
                if self._population_cancelled:
                    return

                # Add synergy item with collection indicator
                in_collection = synergy.name in self._collection_cards
                item = SynergyCardItem(
                    synergy,
                    in_collection=in_collection,
                    id=f"synergy-item-{i}",
                    classes="synergy-item",
                )
                await synergy_list.append(item)
                batch_count += 1

                # Yield to event loop periodically to keep UI responsive
                if batch_count >= LIST_BATCH_SIZE:
                    batch_count = 0
                    await asyncio.sleep(0)  # Yield to event loop

            # Select first item
            if synergy_list.children:
                synergy_list.index = 0

        except NoMatches:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes with debouncing."""
        if event.input.id == "synergy-search":
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

        # Reset cancellation flag for new population
        self._population_cancelled = False

        self.search_query = query
        self._filter_synergies()

        await self._populate_list_batched(self._filtered_synergies)

        if not self._population_cancelled:
            self._update_header()
            self._update_statusbar()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search submit - focus list."""
        if event.input.id == "synergy-search":
            try:
                synergy_list = self.query_one("#synergy-list", ListView)
                synergy_list.focus()
            except NoMatches:
                pass

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle synergy selection (Enter key)."""
        if event.list_view.id == "synergy-list":
            item = event.item
            if isinstance(item, SynergyCardItem):
                self.post_message(SynergySelected(item.synergy))

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle synergy highlight change - auto-update card display."""
        if (
            event.list_view.id == "synergy-list"
            and event.item
            and isinstance(event.item, SynergyCardItem)
        ):
            self.post_message(SynergySelected(event.item.synergy))

    def _set_type_filter(self, type_filter: str) -> None:
        """Set the active type filter."""
        if type_filter == self._active_type:
            return

        self._active_type = type_filter
        self._population_cancelled = True
        self._filter_synergies()
        self.run_worker(self._repopulate_list())

    async def _repopulate_list(self) -> None:
        """Repopulate list after filter change."""
        self._population_cancelled = False
        await self._populate_list_batched(self._filtered_synergies)

        if not self._population_cancelled:
            self._update_header()
            self._update_type_index()
            self._update_statusbar()

    def on_key(self, event: Key) -> None:
        """Handle key presses for type filtering."""
        # Check if search input is focused - don't intercept letter keys
        try:
            search = self.query_one("#synergy-search", Input)
            if search.has_focus:
                return
        except NoMatches:
            pass

        # Type filter keys
        type_map = {
            "a": "all",
            "c": "combo",
            "k": "keyword",
            "t": "tribal",
            "b": "ability",  # 'b' for ability (a is taken by all)
            "h": "theme",  # 'h' for theme
        }

        key = event.key.lower()
        if key in type_map:
            self._set_type_filter(type_map[key])
            type_label = type_map[key].title()
            self.notify(f"Filter: {type_label}", timeout=1)
            event.stop()

    # Actions

    def action_close(self) -> None:
        """Close the synergy panel."""
        self.post_message(SynergyPanelClosed())

    def action_nav_up(self) -> None:
        """Navigate up in list."""
        try:
            synergy_list = self.query_one("#synergy-list", ListView)
            synergy_list.action_cursor_up()
        except NoMatches:
            pass

    def action_nav_down(self) -> None:
        """Navigate down in list."""
        try:
            synergy_list = self.query_one("#synergy-list", ListView)
            synergy_list.action_cursor_down()
        except NoMatches:
            pass

    def action_page_up(self) -> None:
        """Page up in the list."""
        try:
            synergy_list = self.query_one("#synergy-list", ListView)
            synergy_list.action_page_up()
        except NoMatches:
            pass

    def action_page_down(self) -> None:
        """Page down in the list."""
        try:
            synergy_list = self.query_one("#synergy-list", ListView)
            synergy_list.action_page_down()
        except NoMatches:
            pass

    def action_first(self) -> None:
        """Go to first synergy."""
        try:
            synergy_list = self.query_one("#synergy-list", ListView)
            if synergy_list.children:
                synergy_list.index = 0
        except NoMatches:
            pass

    def action_last_item(self) -> None:
        """Go to last synergy."""
        try:
            synergy_list = self.query_one("#synergy-list", ListView)
            if synergy_list.children:
                synergy_list.index = len(synergy_list.children) - 1
        except NoMatches:
            pass

    def action_select_synergy(self) -> None:
        """Select current synergy for full view."""
        try:
            synergy_list = self.query_one("#synergy-list", ListView)
            if synergy_list.index is not None:
                item = synergy_list.children[synergy_list.index]
                if isinstance(item, SynergyCardItem):
                    self.post_message(SynergySelected(item.synergy))
        except NoMatches:
            pass

    def action_cycle_sort(self) -> None:
        """Cycle through sort options."""
        orders = list(SortOrder)
        current_idx = orders.index(self.current_sort)
        self.current_sort = orders[(current_idx + 1) % len(orders)]

        # Re-sort and repopulate
        self._sort_synergies()
        self.run_worker(self._repopulate_list())

    def action_focus_search(self) -> None:
        """Focus the search input."""
        try:
            search = self.query_one("#synergy-search", Input)
            search.focus()
        except NoMatches:
            pass

    @property
    def source_card(self) -> CardDetail | None:
        """Get the source card."""
        return self._source_card

    @property
    def synergy_count(self) -> int:
        """Get total synergy count."""
        return len(self._all_synergies)
