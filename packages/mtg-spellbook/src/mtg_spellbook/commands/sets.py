"""Set browsing and statistics commands."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from textual import work
from textual.widgets import Label, ListItem, Static

from mtg_core.exceptions import SetNotFoundError
from mtg_core.tools import cards as card_tools
from mtg_core.tools import sets

if TYPE_CHECKING:
    from mtg_core.data.models import Set
    from mtg_core.data.models.responses import CardDetail, CardSummary

    from ..pagination import PaginationState
    from ..widgets.set_detail import SetStats

logger = logging.getLogger(__name__)

SET_PAGE_SIZE = 50


class SetCommandsMixin:
    """Mixin providing set browsing and statistics commands."""

    if TYPE_CHECKING:
        _db: Any
        _current_results: list[CardDetail]
        _current_card: CardDetail | None
        _pagination: PaginationState | None
        _set_mode: bool
        _set_code: str
        _synergy_mode: bool
        _artist_mode: bool

        def query_one(self, selector: str, expect_type: type[Any] = ...) -> Any: ...
        def _hide_synergy_panel(self) -> None: ...
        def _update_results_header(self, text: str) -> None: ...
        def _update_pagination_header(self) -> None: ...
        def _update_card_panel(self, card: Any) -> None: ...
        def _show_message(self, message: str) -> None: ...
        def notify(
            self, message: str, *, severity: str = "information", timeout: float = 3
        ) -> None: ...
        def run_worker(self, coro: Any) -> Any: ...

        async def _load_card_extras(self, card: Any, panel_id: str = "#card-panel") -> None: ...

    @work
    async def browse_sets(self, query: str = "") -> None:
        """Browse available sets."""
        if not self._db:
            return

        self._hide_synergy_panel()

        result = await sets.get_sets(self._db, name=query if query else None)

        from ..widgets import ResultsList

        results_list = self.query_one("#results-list", ResultsList)
        results_list.clear()

        for s in result.sets[:50]:
            label = f"[cyan]{s.code.upper()}[/] {s.name} [dim]({s.release_date or '?'})[/]"
            results_list.append(ListItem(Label(label)))

        self._update_results_header(f"Sets ({len(result.sets)})")

    @work
    async def explore_set(self, set_code: str) -> None:
        """Load all cards from a set into the results list with pagination.

        Similar to show_artist but for sets - allows browsing cards from a set
        in the main results view.

        Args:
            set_code: The set code (e.g., 'AFIN', 'LEB').
        """
        if not self._db:
            return

        from mtg_core.data.models.inputs import SearchCardsInput

        from ..pagination import PaginationState

        self._hide_synergy_panel()

        # Get set info for display
        try:
            set_data = await self._db.get_set(set_code)
            set_name = set_data.name if set_data else set_code.upper()
        except Exception:
            set_name = set_code.upper()

        self.notify(f"Loading cards from {set_name}...", timeout=2)

        # Search for first batch of cards in this set
        filters = SearchCardsInput(set_code=set_code, page_size=100)
        cards, total = await self._db.search_cards(filters)

        if not cards:
            self._show_message(f"[yellow]No cards found in set: {set_code.upper()}[/]")
            return

        # Convert to CardSummary format for pagination
        from mtg_core.data.models.responses import CardSummary

        summaries: list[CardSummary] = []
        for card in cards:
            summaries.append(
                CardSummary(
                    uuid=card.uuid,
                    name=card.name,
                    mana_cost=card.mana_cost,
                    type=card.type,
                    colors=card.colors or [],
                    rarity=card.rarity,
                    set_code=card.set_code,
                    collector_number=card.number,
                )
            )

        # Show results container, hide dashboard
        if hasattr(self, "_show_search_view"):
            self._show_search_view()
        elif hasattr(self, "_hide_dashboard"):
            self._hide_dashboard()
            self._show_results_view()
        else:
            self._show_results_view()

        # Set mode flags
        self._set_mode = True
        self._set_code = set_code.upper()
        self._synergy_mode = False
        self._artist_mode = False

        # Create pagination state with total override for lazy loading
        self._pagination = PaginationState.from_summaries(
            summaries,
            source_type="set",
            source_query=set_code.upper(),
            page_size=SET_PAGE_SIZE,
        )
        # Set total override so pagination shows correct total count
        self._pagination.total_override = total

        # Load card details for current page
        self._current_results = []
        for summary in self._pagination.current_page_items:
            try:
                if summary.uuid:
                    detail = await card_tools.get_card(self._db, uuid=summary.uuid)
                else:
                    detail = await card_tools.get_card(self._db, name=summary.name)
                self._current_results.append(detail)
            except Exception:
                logger.debug("Failed to load card detail for %s", summary.name, exc_info=True)

        # Cache first page
        self._pagination.cache_details(self._pagination.current_page, self._current_results)

        if not self._current_results:
            self._show_message(f"[yellow]Could not load cards for set: {set_code.upper()}[/]")
            return

        # Display results
        self._display_set_results()

        # Select first card
        self._current_card = self._current_results[0]

        # Update menu card state if available
        if hasattr(self, "_update_menu_card_state"):
            self._update_menu_card_state()

        self._update_card_panel(self._current_card)
        await self._load_card_extras(self._current_card)

    def _display_set_results(self) -> None:
        """Display set results for current page."""
        from ..widgets import ResultsList
        from ..widgets.card_result_item import CardResultItem

        results_list = self.query_one("#results-list", ResultsList)
        results_list.clear()

        for card in self._current_results:
            results_list.append(CardResultItem(card))

        self._update_pagination_header()

        if self._current_results:
            results_list.focus()
            results_list.index = 0

    async def _load_more_set_cards_async(self, _target_page: int) -> None:
        """Load more cards for set browsing when paginating beyond loaded items.

        This is the async version called from within _load_current_page.
        """
        if not self._db or not self._pagination or not self._set_mode:
            return

        from mtg_core.data.models.inputs import SearchCardsInput
        from mtg_core.data.models.responses import CardSummary

        # Calculate which DB page we need (DB uses page_size=100)
        db_page_size = 100
        loaded_count = self._pagination.loaded_items_count
        db_page = (loaded_count // db_page_size) + 1

        # Load next batch from DB
        filters = SearchCardsInput(
            set_code=self._set_code,
            page_size=db_page_size,
            page=db_page,
        )
        cards, _ = await self._db.search_cards(filters)

        if not cards:
            return

        # Convert to CardSummary and extend pagination
        summaries: list[CardSummary] = []
        for card in cards:
            summaries.append(
                CardSummary(
                    uuid=card.uuid,
                    name=card.name,
                    mana_cost=card.mana_cost,
                    type=card.type,
                    colors=card.colors or [],
                    rarity=card.rarity,
                    set_code=card.set_code,
                    collector_number=card.number,
                )
            )

        self._pagination.extend_items(summaries)

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
    async def show_set(self, code: str) -> None:
        """Show set details."""
        if not self._db:
            return

        self._hide_synergy_panel()

        try:
            result = await sets.get_set(self._db, code)

            from ..widgets import ResultsList

            results_list = self.query_one("#results-list", ResultsList)
            results_list.clear()

            lines = [
                f"[bold]{result.name}[/] [{result.code.upper()}]",
                "",
                f"[bold]Type:[/] {result.type}",
                f"[bold]Released:[/] {result.release_date or 'Unknown'}",
                f"[bold]Cards:[/] {result.total_set_size or 'Unknown'}",
            ]
            from textual.widgets import ListItem

            results_list.append(ListItem(Static("\n".join(lines))))

        except SetNotFoundError:
            self._show_message(f"[red]Set not found: {code}[/]")

    @work
    async def show_stats(self) -> None:
        """Show database statistics."""
        if not self._db:
            return

        stats = await self._db.get_database_stats()

        from ..widgets import ResultsList

        results_list = self.query_one("#results-list", ResultsList)
        results_list.clear()

        lines = [
            "[bold]📊 Database Statistics[/]",
            "",
            f"  [bold]Cards:[/]   [cyan]{stats.get('unique_cards', '?'):,}[/]",
            f"  [bold]Sets:[/]    [cyan]{stats.get('total_sets', '?'):,}[/]",
            f"  [bold]Version:[/] [dim]{stats.get('data_version', 'unknown')}[/]",
        ]
        from textual.widgets import ListItem

        results_list.append(ListItem(Static("\n".join(lines))))

    @work
    async def show_set_detail(self, set_code: str) -> None:
        """Show detailed set view with all cards."""
        if not self._db:
            return

        from ..widgets.set_detail import SetStats as SetStatsClass

        try:
            # Get set info - returns a SetDetail response, need to get the Set model
            set_data = await self._db.get_set(set_code)

            # Get all cards in set
            cards = await self._db.get_cards_in_set(set_code)

            if not cards:
                self._show_message(f"[yellow]No cards found in set: {set_code.upper()}[/]")
                return

            # Convert Card objects to CardSummary
            summaries: list[CardSummary] = []
            for card in cards:
                from mtg_core.data.models.responses import CardSummary

                summaries.append(
                    CardSummary(
                        name=card.name,
                        mana_cost=card.mana_cost,
                        cmc=card.cmc,
                        type=card.type,
                        colors=card.colors or [],
                        color_identity=card.color_identity or [],
                        rarity=card.rarity,
                        set_code=card.set_code,
                        keywords=card.keywords or [],
                        power=card.power,
                        toughness=card.toughness,
                    )
                )

            # Get set statistics
            db_stats = await self._db.get_set_stats(set_code)

            # Convert to widget's SetStats class
            stats = SetStatsClass(
                total_cards=db_stats.total_cards,
                rarity_distribution=db_stats.rarity_distribution,
                color_distribution=db_stats.color_distribution,
                mechanics=db_stats.mechanics,
                avg_cmc=db_stats.avg_cmc,
            )

            # Mount and show the set detail view
            self._show_set_detail_view(set_data, summaries, stats)

        except SetNotFoundError:
            self._show_message(f"[red]Set not found: {set_code}[/]")

    def _show_set_detail_view(
        self,
        set_data: Set,
        cards: list[CardSummary],
        stats: SetStats,
    ) -> None:
        """Mount and display the set detail view."""
        from textual.css.query import NoMatches

        from ..widgets import SetDetailView

        # Check if set detail view already exists
        try:
            existing = self.query_one("#set-detail", SetDetailView)
            # Update existing view - use run_worker to handle the coroutine
            self.run_worker(existing.load_set(set_data, cards, stats))
            existing.remove_class("hidden")
            return
        except NoMatches:
            pass

        # Create and mount new set detail view as overlay
        set_view = SetDetailView(id="set-detail", classes="set-detail-overlay")

        # Mount to the main container
        try:
            main_container = self.query_one("#main-container")
            main_container.mount(set_view)
            self.run_worker(set_view.load_set(set_data, cards, stats))
        except NoMatches:
            self._show_message("[red]Could not display set details[/]")
