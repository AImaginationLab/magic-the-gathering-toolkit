"""Artist discovery commands."""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING, Any

from textual import work

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mtg_core.data.models.responses import ArtistSummary, CardDetail

    from ..pagination import PaginationState


ARTIST_PAGE_SIZE = 50


class ArtistCommandsMixin:
    """Mixin providing artist discovery commands."""

    if TYPE_CHECKING:
        _db: Any
        _current_results: list[CardDetail]
        _current_card: CardDetail | None
        _pagination: PaginationState | None
        _artist_mode: bool
        _artist_name: str
        _synergy_mode: bool

        def query_one(self, selector: str, expect_type: type[Any] = ...) -> Any: ...
        def _show_message(self, message: str) -> None: ...
        def _update_pagination_header(self) -> None: ...
        def _update_card_panel(self, card: Any) -> None: ...
        def notify(
            self, message: str, *, severity: str = "information", timeout: float = 3
        ) -> None: ...

        async def _load_card_extras(self, card: Any, panel_id: str = "#card-panel") -> None: ...

    @work
    async def show_artist(self, artist_name: str, select_card: str | None = None) -> None:
        """Show artist's cards in the results list with pagination.

        Args:
            artist_name: Name of the artist to browse.
            select_card: Optional card name to auto-select.
        """
        if not self._db:
            return

        from mtg_core.tools import artists as artist_tools
        from mtg_core.tools import cards as card_tools

        from ..pagination import PaginationState
        from ..widgets import ResultsList

        # Load artist data from cache or database
        result = await artist_tools.get_artist_cards(self._db, artist_name)
        summaries = result.cards

        if not summaries:
            self._show_message(f"[yellow]No cards found for artist: {artist_name}[/]")
            return

        # Show results container, hide dashboard
        # Use _hide_dashboard from main app to properly track state
        if hasattr(self, "_hide_dashboard"):
            self._hide_dashboard()
        else:
            self._show_results_view()

        # Set artist mode
        self._artist_mode = True
        self._artist_name = artist_name
        self._synergy_mode = False

        # Store UUID mapping so we fetch the correct printing (by this artist)
        # Key is index in the summaries list, value is UUID
        self._artist_card_uuids: dict[int, str] = {}

        select_page = 1
        select_index_on_page = 0

        for i, card in enumerate(summaries):
            # Store UUID for later lookup
            if card.uuid:
                self._artist_card_uuids[i] = card.uuid

            # Track which page and index the selected card is on
            if select_card and card.name.lower() == select_card.lower():
                select_page = (i // ARTIST_PAGE_SIZE) + 1
                select_index_on_page = i % ARTIST_PAGE_SIZE

        # Create pagination state
        self._pagination = PaginationState.from_summaries(
            summaries,
            source_type="artist",
            source_query=artist_name,
            page_size=ARTIST_PAGE_SIZE,
        )

        # Go to the page with the selected card
        if select_page > 1:
            self._pagination.go_to_page(select_page)

        # Load card details for current page using UUIDs (to get correct artist's version)
        self._current_results = []
        page_start = (self._pagination.current_page - 1) * ARTIST_PAGE_SIZE
        for i, summary in enumerate(self._pagination.current_page_items):
            global_idx = page_start + i
            try:
                uuid = self._artist_card_uuids.get(global_idx)
                if uuid:
                    # Use UUID to get the exact printing by this artist
                    detail = await card_tools.get_card(self._db, uuid=uuid)
                else:
                    # Fallback to name lookup
                    detail = await card_tools.get_card(self._db, name=summary.name)
                self._current_results.append(detail)
            except Exception:
                logger.debug("Failed to load card detail for %s", summary.name, exc_info=True)

        # Cache first page
        self._pagination.cache_details(self._pagination.current_page, self._current_results)

        if not self._current_results:
            self._show_message(f"[yellow]Could not load cards for artist: {artist_name}[/]")
            return

        # Display results
        self._display_artist_results()

        # Select the target card
        results_list = self.query_one("#results-list", ResultsList)
        if select_index_on_page < len(self._current_results):
            results_list.index = select_index_on_page
            self._current_card = self._current_results[select_index_on_page]
        else:
            self._current_card = self._current_results[0]

        # Update menu card state if available
        if hasattr(self, "_update_menu_card_state"):
            self._update_menu_card_state()

        self._update_card_panel(self._current_card)
        await self._load_card_extras(self._current_card)

    def _display_artist_results(self) -> None:
        """Display artist results for current page using unified CardResultItem."""
        from ..widgets import ResultsList
        from ..widgets.card_result_item import CardResultItem

        results_list = self.query_one("#results-list", ResultsList)
        results_list.clear()

        for card in self._current_results:
            # Use unified CardResultItem for consistent formatting
            results_list.append(CardResultItem(card))

        self._update_pagination_header()

        if self._current_results:
            results_list.focus()
            results_list.index = 0

    def _show_results_view(self) -> None:
        """Show results container and hide dashboard."""
        from textual.css.query import NoMatches

        try:
            dashboard = self.query_one("#dashboard")
            dashboard.add_class("hidden")
        except NoMatches:
            pass

        try:
            results_container = self.query_one("#results-container")
            results_container.remove_class("hidden")
        except NoMatches:
            pass

        try:
            detail_container = self.query_one("#detail-container")
            detail_container.remove_class("hidden")
        except NoMatches:
            pass

    @work
    async def browse_artists(self, search_query: str = "") -> None:
        """Open artist browser widget with full alphabetical listing."""
        if not self._db:
            return

        from textual.css.query import NoMatches

        from ..widgets import ArtistBrowser

        # Get all artists (or search results)
        if search_query:
            artists: list[ArtistSummary] = await self._db.search_artists(search_query, min_cards=1)
        else:
            artists = await self._db.get_all_artists(min_cards=1)

        if not artists:
            self._show_message("[yellow]No artists found[/]")
            return

        # Check if browser already exists
        try:
            existing = self.query_one("#artist-browser", ArtistBrowser)
            await existing.load_artists(artists)
            existing.remove_class("hidden")
            return
        except NoMatches:
            pass

        # Create and mount new artist browser
        browser = ArtistBrowser(id="artist-browser", classes="artist-browser-overlay")

        try:
            main_container = self.query_one("#main-container")
            main_container.mount(browser)
            await browser.load_artists(artists)
        except NoMatches:
            self._show_message("[red]Could not display artist browser[/]")

    @work
    async def random_artist(self) -> None:
        """Show random artist with significant portfolio."""
        if not self._db:
            return

        # Get artists with at least 20 cards
        artists: list[ArtistSummary] = await self._db.get_all_artists(min_cards=20)

        if not artists:
            self._show_message("[yellow]No artists found[/]")
            return

        # Pick a random artist
        artist = random.choice(artists)
        self.notify(f"Random artist: {artist.name}", timeout=2)
        self.show_artist(artist.name)
