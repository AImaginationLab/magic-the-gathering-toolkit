"""Main SetDetailView widget for set exploration."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import Static

from ...ui.theme import ui_colors
from .card_list import SetCardList
from .card_preview import SetCardPreviewPanel
from .info_panel import SetInfoPanel, SetStats
from .messages import SetCardSelected, SetDetailClosed

if TYPE_CHECKING:
    from mtg_core.data.models import Set
    from mtg_core.data.models.responses import CardSummary


class SetDetailView(Vertical, can_focus=True):
    """Set detail view with info panel, card list, and preview."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape,q", "close", "Close"),
        Binding("up,k", "nav_up", "Up", show=False),
        Binding("down,j", "nav_down", "Down", show=False),
        Binding("pageup", "page_up", "Page Up", show=False),
        Binding("pagedown", "page_down", "Page Down", show=False),
        Binding("home", "first", "First", show=False),
        Binding("end", "last", "Last", show=False),
        Binding("enter", "select_card", "Select"),
        Binding("r", "random_card", "Random"),
        Binding("f", "toggle_filter", "Filter"),
        Binding("c", "clear_filters", "Clear Filters", show=False),
    ]

    is_loading: reactive[bool] = reactive(False)
    current_filter: reactive[str | None] = reactive(None)

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._set_data: Set | None = None
        self._set_code: str = ""
        self._cards: list[CardSummary] = []
        self._filter_index: int = 0
        self._rarity_filters = [None, "mythic", "rare", "uncommon", "common"]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="set-detail-main"):
            yield SetInfoPanel(
                id="set-info-panel",
                classes="set-info-panel",
            )
            yield SetCardList(
                id="set-card-list",
                classes="set-card-list",
            )
            yield SetCardPreviewPanel(
                id="set-card-preview",
                classes="set-card-preview",
            )

        yield Static(
            self._render_statusbar(),
            id="set-statusbar",
            classes="set-statusbar",
        )

    def on_mount(self) -> None:
        """Set up card selection callback."""
        try:
            card_list = self.query_one("#set-card-list", SetCardList)
            card_list.set_on_select(self._on_card_selected)
        except NoMatches:
            pass

    def _render_statusbar(self) -> str:
        """Render the status bar text."""
        parts = [
            f"[{ui_colors.TEXT_DIM}]jk/arrows: navigate[/]",
            f"[{ui_colors.GOLD}]Enter[/]: select",
            f"[{ui_colors.GOLD}]r[/]: random",
            f"[{ui_colors.GOLD}]f[/]: filter",
            f"[{ui_colors.GOLD}]Esc[/]: close",
        ]

        # Add filter indicator if active
        if self.current_filter:
            parts.insert(0, f"[bold cyan]Filter: {self.current_filter.title()}[/]")

        return "  |  ".join(parts)

    def _update_statusbar(self) -> None:
        """Update the status bar."""
        try:
            statusbar = self.query_one("#set-statusbar", Static)
            statusbar.update(self._render_statusbar())
        except NoMatches:
            pass

    async def load_set(
        self,
        set_data: Set,
        cards: list[CardSummary],
        stats: SetStats | None = None,
        format_legality: dict[str, bool] | None = None,
    ) -> None:
        """Load set data and display."""
        self.is_loading = True
        self._set_data = set_data
        self._set_code = set_data.code
        self._cards = cards

        try:
            # Update info panel
            info_panel = self.query_one("#set-info-panel", SetInfoPanel)
            info_panel.update_info(set_data, stats, format_legality)

            # Load cards into list
            card_list = self.query_one("#set-card-list", SetCardList)
            await card_list.load_cards(cards)

            # Focus the card list
            card_list.focus()
        finally:
            self.is_loading = False

    def _on_card_selected(self, card: CardSummary) -> None:
        """Handle card selection from list."""
        try:
            preview = self.query_one("#set-card-preview", SetCardPreviewPanel)
            preview.update_card(card)
        except NoMatches:
            pass

    def watch_current_filter(self, _filter_value: str | None) -> None:
        """Update display when filter changes."""
        self._update_statusbar()

    def action_close(self) -> None:
        """Close the set detail view."""
        self.post_message(SetDetailClosed(self._set_code))

    def action_nav_up(self) -> None:
        """Navigate up in card list."""
        try:
            card_list = self.query_one("#set-card-list", SetCardList)
            card_list.action_cursor_up()
        except NoMatches:
            pass

    def action_nav_down(self) -> None:
        """Navigate down in card list."""
        try:
            card_list = self.query_one("#set-card-list", SetCardList)
            card_list.action_cursor_down()
        except NoMatches:
            pass

    def action_page_up(self) -> None:
        """Page up in card list."""
        try:
            card_list = self.query_one("#set-card-list", SetCardList)
            card_list.action_page_up()
        except NoMatches:
            pass

    def action_page_down(self) -> None:
        """Page down in card list."""
        try:
            card_list = self.query_one("#set-card-list", SetCardList)
            card_list.action_page_down()
        except NoMatches:
            pass

    def action_first(self) -> None:
        """Go to first card."""
        try:
            card_list = self.query_one("#set-card-list", SetCardList)
            card_list.action_first()
        except NoMatches:
            pass

    def action_last(self) -> None:
        """Go to last card."""
        try:
            card_list = self.query_one("#set-card-list", SetCardList)
            card_list.action_last()
        except NoMatches:
            pass

    def action_select_card(self) -> None:
        """Select the current card and post message."""
        try:
            card_list = self.query_one("#set-card-list", SetCardList)
            card = card_list.get_current_card()
            if card:
                self.post_message(SetCardSelected(card))
        except NoMatches:
            pass

    def action_random_card(self) -> None:
        """Select a random card from the set."""
        try:
            card_list = self.query_one("#set-card-list", SetCardList)
            card_list.select_random()
        except NoMatches:
            pass

    def action_toggle_filter(self) -> None:
        """Cycle through rarity filters."""
        self._filter_index = (self._filter_index + 1) % len(self._rarity_filters)
        rarity = self._rarity_filters[self._filter_index]
        self.current_filter = rarity

        try:
            card_list = self.query_one("#set-card-list", SetCardList)
            card_list.filter_cards(rarity=rarity)
        except NoMatches:
            pass

    def action_clear_filters(self) -> None:
        """Clear all filters."""
        self._filter_index = 0
        self.current_filter = None

        try:
            card_list = self.query_one("#set-card-list", SetCardList)
            card_list.clear_filters()
        except NoMatches:
            pass

    def get_current_card(self) -> CardSummary | None:
        """Get the currently selected card."""
        try:
            card_list = self.query_one("#set-card-list", SetCardList)
            return card_list.get_current_card()
        except NoMatches:
            return None

    @property
    def set_code(self) -> str:
        """Get the current set code."""
        return self._set_code

    @property
    def card_count(self) -> int:
        """Get total card count."""
        try:
            card_list = self.query_one("#set-card-list", SetCardList)
            return card_list.card_count
        except NoMatches:
            return 0
