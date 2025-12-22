"""Search bar with autocomplete dropdown for dashboard."""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, ListView

from ..card_result_item import CardResultItem
from .messages import SearchResultSelected, SearchSubmitted

if TYPE_CHECKING:
    from textual.events import Key

    from mtg_core.data.database import UnifiedDatabase
    from mtg_core.data.models.responses import CardSummary

# Debounce delay in milliseconds
SEARCH_DEBOUNCE_MS = 150

# Pattern to detect query language filters (e.g., t:creature, c:R, set:fin)
QUERY_FILTER_PATTERN = re.compile(r"\b(t|c|ci|cmc|f|r|set|text|kw|artist):", re.IGNORECASE)


# Re-export CardResultItem as SearchResultItem for backward compatibility
SearchResultItem = CardResultItem


class SearchBar(Vertical, can_focus=False):
    """Search input with autocomplete dropdown.

    Args:
        name: Unique name for this search bar (used to generate element IDs).
              Defaults to "dashboard" for backward compatibility.
        placeholder: Custom placeholder text for the input.
        id: Widget ID.
    """

    DEFAULT_CSS = """
    SearchBar {
        height: auto;
        width: 100%;
        margin: 2 2;
    }

    SearchBar > Input {
        width: 100%;
        background: #1a1a2e;
        border: tall #3d3d3d;
    }

    SearchBar > Input:focus {
        border: tall #c9a227;
        background: #1e1e32;
    }

    SearchBar > ListView {
        max-height: 30;
        width: 100%;
        background: #151515;
        border: solid #3d3d3d;
        border-top: none;
    }

    SearchBar > ListView.hidden {
        display: none;
    }

    SearchBar > ListView > ListItem {
        padding: 1 2;
        height: auto;
        background: #121212;
    }

    SearchBar > ListView > ListItem:hover {
        background: #1a1a2e;
    }

    SearchBar > ListView > ListItem.-highlight {
        background: #2a2a4e;
    }
    """

    def __init__(
        self,
        *,
        name: str = "dashboard",
        placeholder: str = "type card name or pattern 'search t:type c:colors set:code artist:name'",
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._name = name
        self._placeholder = placeholder
        self._db: UnifiedDatabase | None = None
        self._search_task: asyncio.Task[None] | None = None
        self._results: list[CardSummary] = []
        self._dropdown_visible = False

    @property
    def _input_id(self) -> str:
        return f"{self._name}-search"

    @property
    def _dropdown_id(self) -> str:
        return f"{self._name}-search-dropdown"

    def compose(self) -> ComposeResult:
        """Compose the search bar with input and dropdown."""
        yield Input(
            placeholder=self._placeholder,
            id=self._input_id,
        )
        yield ListView(id=self._dropdown_id, classes="hidden")

    def set_database(self, db: UnifiedDatabase) -> None:
        """Set database connection for search."""
        self._db = db

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes with debouncing."""
        if event.input.id != self._input_id:
            return

        query = event.value.strip()

        # Cancel any existing search task
        if self._search_task is not None:
            self._search_task.cancel()
            self._search_task = None

        # Hide dropdown if query is empty
        if not query:
            self._hide_dropdown()
            return

        # Start debounced search
        self._search_task = asyncio.create_task(self._debounced_search(query))

    async def _debounced_search(self, query: str) -> None:
        """Execute search after debounce delay."""
        try:
            await asyncio.sleep(SEARCH_DEBOUNCE_MS / 1000)
        except asyncio.CancelledError:
            return

        if not self._db:
            return

        try:
            results = await self._search(query)
            self._results = results
            self._populate_dropdown(results)
            if results:
                self._show_dropdown()
            else:
                self._hide_dropdown()
        except asyncio.CancelledError:
            pass

    def _has_query_filters(self, query: str) -> bool:
        """Check if query contains filter syntax like t:creature, set:fin."""
        return bool(QUERY_FILTER_PATTERN.search(query))

    async def _search(self, query: str) -> list[CardSummary]:
        """Search for cards matching query.

        Supports two modes:
        - Typeahead: Simple name FTS search (default)
        - Query language: When filters like t:, c:, set: are detected
        """
        if not self._db:
            return []

        from mtg_core.tools import cards

        try:
            # Detect if query uses filter syntax
            if self._has_query_filters(query):
                # Query language mode - parse filters
                from ...search import parse_search_query

                filters = parse_search_query(query)
                # Override page size for dropdown
                filters_dict = filters.model_dump()
                filters_dict["page_size"] = 8
                from mtg_core.data.models.inputs import SearchCardsInput

                filters = SearchCardsInput(**filters_dict)
                result = await cards.search_cards(self._db, filters)
            else:
                # Typeahead mode - simple FTS name search
                from mtg_core.data.models.inputs import SearchCardsInput

                filters = SearchCardsInput(name=query, page_size=8)
                result = await cards.search_cards(self._db, filters)
            return result.cards
        except Exception:
            return []

    def _populate_dropdown(self, results: list[CardSummary]) -> None:
        """Populate dropdown with search results."""
        dropdown = self.query_one(f"#{self._dropdown_id}", ListView)
        dropdown.clear()

        for card in results:
            dropdown.append(SearchResultItem(card))

    def _show_dropdown(self) -> None:
        """Show the dropdown."""
        if not self._dropdown_visible:
            self._dropdown_visible = True
            dropdown = self.query_one(f"#{self._dropdown_id}", ListView)
            dropdown.remove_class("hidden")

    def _hide_dropdown(self) -> None:
        """Hide the dropdown."""
        if self._dropdown_visible:
            self._dropdown_visible = False
            dropdown = self.query_one(f"#{self._dropdown_id}", ListView)
            dropdown.add_class("hidden")
            dropdown.clear()
            self._results = []

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter in input."""
        if event.input.id != self._input_id:
            return

        query = event.value.strip()
        if not query:
            return

        # If dropdown has highlighted item, select it
        dropdown = self.query_one(f"#{self._dropdown_id}", ListView)
        if self._dropdown_visible and dropdown.highlighted_child:
            item = dropdown.highlighted_child
            if isinstance(item, SearchResultItem):
                self._hide_dropdown()
                event.input.value = ""
                self.post_message(SearchResultSelected(item.card))
                return

        # Otherwise submit as search query
        self._hide_dropdown()
        event.input.value = ""
        self.post_message(SearchSubmitted(query))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle selection from dropdown."""
        if event.list_view.id != self._dropdown_id:
            return

        item = event.item
        if isinstance(item, SearchResultItem):
            self._hide_dropdown()
            search_input = self.query_one(f"#{self._input_id}", Input)
            search_input.value = ""
            self.post_message(SearchResultSelected(item.card))

    def on_key(self, event: Key) -> None:
        """Handle key events for dropdown navigation."""
        search_input = self.query_one(f"#{self._input_id}", Input)
        dropdown = self.query_one(f"#{self._dropdown_id}", ListView)

        # If input is focused
        if search_input.has_focus:
            if event.key == "down" and self._dropdown_visible:
                # Move focus to dropdown
                dropdown.focus()
                if dropdown.index is None and len(dropdown.children) > 0:
                    dropdown.index = 0
                event.stop()
                event.prevent_default()
            elif event.key == "escape":
                self._hide_dropdown()
                event.stop()
                event.prevent_default()

        # If dropdown is focused
        elif dropdown.has_focus:
            if event.key == "escape":
                self._hide_dropdown()
                search_input.focus()
                event.stop()
                event.prevent_default()
            elif event.key == "up" and dropdown.index == 0:
                # Move back to input if at top of list
                search_input.focus()
                event.stop()
                event.prevent_default()

    def clear(self) -> None:
        """Clear the search bar."""
        search_input = self.query_one(f"#{self._input_id}", Input)
        search_input.value = ""
        self._hide_dropdown()

    def focus_search(self) -> None:
        """Focus the search input."""
        search_input = self.query_one(f"#{self._input_id}", Input)
        search_input.focus()
