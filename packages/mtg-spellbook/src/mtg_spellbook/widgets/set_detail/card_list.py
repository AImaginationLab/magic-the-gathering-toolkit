"""Scrollable card list for set detail view."""

from __future__ import annotations

import random
from collections.abc import Callable
from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import ListItem, ListView, Static

from ...ui.theme import rarity_colors, ui_colors

if TYPE_CHECKING:
    from mtg_core.data.models.responses import CardSummary


class CardListItem(ListItem):
    """A single card item in the set card list."""

    def __init__(self, card: CardSummary, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.card = card

    def compose(self) -> ComposeResult:
        yield Static(self._render_card())

    def _render_card(self) -> str:
        """Render card name with rarity indicator."""
        rarity = (self.card.rarity or "common").lower()
        rarity_indicator = self._get_rarity_indicator(rarity)
        rarity_color = self._get_rarity_color(rarity)

        name = self.card.name
        mana = self.card.mana_cost or ""

        return f"[{rarity_color}]{rarity_indicator}[/] {name} [{ui_colors.TEXT_DIM}]{mana}[/]"

    def _get_rarity_indicator(self, rarity: str) -> str:
        """Get single-letter rarity indicator."""
        indicators = {
            "mythic": "[M]",
            "rare": "[R]",
            "uncommon": "[U]",
            "common": "[C]",
            "special": "[S]",
            "bonus": "[B]",
        }
        return indicators.get(rarity, "[?]")

    def _get_rarity_color(self, rarity: str) -> str:
        """Get color for rarity indicator."""
        colors = {
            "mythic": rarity_colors.MYTHIC,
            "rare": rarity_colors.RARE,
            "uncommon": rarity_colors.UNCOMMON,
            "common": rarity_colors.COMMON,
        }
        return colors.get(rarity, ui_colors.TEXT_DIM)


class SetCardList(VerticalScroll):
    """Scrollable list of cards in a set with filtering."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("up,k", "cursor_up", "Up", show=False),
        Binding("down,j", "cursor_down", "Down", show=False),
        Binding("pageup", "page_up", "Page Up", show=False),
        Binding("pagedown", "page_down", "Page Down", show=False),
        Binding("home", "first", "First", show=False),
        Binding("end", "last", "Last", show=False),
    ]

    selected_index: reactive[int] = reactive(0)
    filter_rarity: reactive[str | None] = reactive(None)
    filter_color: reactive[str | None] = reactive(None)

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._all_cards: list[CardSummary] = []
        self._filtered_cards: list[CardSummary] = []
        self._on_select_callback: Callable[[CardSummary], None] | None = None

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="card-list-scroll"):
            yield Static(
                "[dim]No cards loaded[/]",
                id="card-list-empty",
                classes="card-list-empty",
            )
            yield ListView(id="card-list-view", classes="card-list-view")

    def on_mount(self) -> None:
        """Hide list view initially."""
        try:
            list_view = self.query_one("#card-list-view", ListView)
            list_view.display = False
        except NoMatches:
            pass

    def set_on_select(self, callback: Callable[[CardSummary], None]) -> None:
        """Set callback for card selection."""
        self._on_select_callback = callback

    async def load_cards(self, cards: list[CardSummary]) -> None:
        """Load and display cards."""
        self._all_cards = cards
        self._apply_filters()
        await self._rebuild_list()

        # Select first card if available
        if self._filtered_cards:
            self.selected_index = 0
            self._notify_selection()

    def filter_cards(
        self,
        rarity: str | None = None,
        color: str | None = None,
    ) -> None:
        """Apply filters to card list."""
        self.filter_rarity = rarity
        self.filter_color = color
        self._apply_filters()
        self.run_worker(self._rebuild_list())

        # Reset selection
        if self._filtered_cards:
            self.selected_index = 0
            self._notify_selection()

    def clear_filters(self) -> None:
        """Clear all filters."""
        self.filter_rarity = None
        self.filter_color = None
        self._apply_filters()
        self.run_worker(self._rebuild_list())

    def _apply_filters(self) -> None:
        """Apply current filters to card list."""
        self._filtered_cards = self._all_cards.copy()

        if self.filter_rarity:
            self._filtered_cards = [
                c
                for c in self._filtered_cards
                if (c.rarity or "").lower() == self.filter_rarity.lower()
            ]

        if self.filter_color:
            self._filtered_cards = [
                c for c in self._filtered_cards if self.filter_color.upper() in (c.colors or [])
            ]

    async def _rebuild_list(self) -> None:
        """Rebuild the list view with filtered cards."""
        try:
            empty_msg = self.query_one("#card-list-empty", Static)
            list_view = self.query_one("#card-list-view", ListView)

            if not self._filtered_cards:
                empty_msg.update("[dim]No cards match filters[/]")
                empty_msg.display = True
                list_view.display = False
                return

            empty_msg.display = False
            list_view.display = True

            # Clear and rebuild list
            await list_view.clear()
            for i, card in enumerate(self._filtered_cards):
                item = CardListItem(card, id=f"card-item-{i}")
                await list_view.append(item)

            # Set initial highlight
            if self._filtered_cards:
                list_view.index = 0
        except NoMatches:
            pass

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle list selection."""
        if isinstance(event.item, CardListItem):
            self._notify_selection_for_card(event.item.card)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle list highlight change."""
        if isinstance(event.item, CardListItem):
            self._notify_selection_for_card(event.item.card)

    def _notify_selection(self) -> None:
        """Notify callback of current selection."""
        if 0 <= self.selected_index < len(self._filtered_cards):
            card = self._filtered_cards[self.selected_index]
            self._notify_selection_for_card(card)

    def _notify_selection_for_card(self, card: CardSummary) -> None:
        """Notify callback of a specific card selection."""
        if self._on_select_callback:
            self._on_select_callback(card)

    def get_current_card(self) -> CardSummary | None:
        """Get the currently selected card."""
        try:
            list_view = self.query_one("#card-list-view", ListView)
            if list_view.highlighted_child and isinstance(
                list_view.highlighted_child, CardListItem
            ):
                return list_view.highlighted_child.card
        except NoMatches:
            pass
        return None

    def get_random_card(self) -> CardSummary | None:
        """Get a random card from the filtered list."""
        if not self._filtered_cards:
            return None
        return random.choice(self._filtered_cards)

    def select_random(self) -> None:
        """Select a random card and scroll to it."""
        if not self._filtered_cards:
            return

        index = random.randint(0, len(self._filtered_cards) - 1)
        try:
            list_view = self.query_one("#card-list-view", ListView)
            list_view.index = index
        except NoMatches:
            pass

    def action_cursor_up(self) -> None:
        """Move selection up."""
        try:
            list_view = self.query_one("#card-list-view", ListView)
            list_view.action_cursor_up()
        except NoMatches:
            pass

    def action_cursor_down(self) -> None:
        """Move selection down."""
        try:
            list_view = self.query_one("#card-list-view", ListView)
            list_view.action_cursor_down()
        except NoMatches:
            pass

    def action_page_up(self) -> None:
        """Move selection up by a page."""
        try:
            list_view = self.query_one("#card-list-view", ListView)
            list_view.action_page_up()
        except NoMatches:
            pass

    def action_page_down(self) -> None:
        """Move selection down by a page."""
        try:
            list_view = self.query_one("#card-list-view", ListView)
            list_view.action_page_down()
        except NoMatches:
            pass

    def action_first(self) -> None:
        """Move selection to first item."""
        try:
            list_view = self.query_one("#card-list-view", ListView)
            list_view.index = 0
        except NoMatches:
            pass

    def action_last(self) -> None:
        """Move selection to last item."""
        try:
            list_view = self.query_one("#card-list-view", ListView)
            if self._filtered_cards:
                list_view.index = len(self._filtered_cards) - 1
        except NoMatches:
            pass

    @property
    def card_count(self) -> int:
        """Get total card count (before filtering)."""
        return len(self._all_cards)

    @property
    def filtered_count(self) -> int:
        """Get filtered card count."""
        return len(self._filtered_cards)
