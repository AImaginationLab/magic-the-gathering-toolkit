"""Card lookup and search commands."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from textual import work

from mtg_core.data.models.inputs import SearchCardsInput
from mtg_core.exceptions import CardNotFoundError
from mtg_core.tools import cards

from ..pagination import PaginationState
from ..search import parse_search_query

if TYPE_CHECKING:
    from mtg_core.data.models.responses import CardDetail, CardSummary


class CardCommandsMixin:
    """Mixin providing card lookup and search commands."""

    if TYPE_CHECKING:
        _db: Any
        _current_results: list[Any]
        _current_card: Any
        _synergy_mode: bool
        _artist_mode: bool
        _pagination: PaginationState | None

        def query_one(self, selector: str, expect_type: type[Any] = ...) -> Any: ...
        def _hide_synergy_panel(self) -> None: ...
        def _update_results(self, results: list[Any]) -> None: ...
        def _update_card_panel(self, card: Any) -> None: ...
        def _update_pagination_header(self) -> None: ...
        def _show_message(self, message: str) -> None: ...

    @work
    async def lookup_card(
        self,
        name: str,
        uuid: str | None = None,
        target_set: str | None = None,
        target_number: str | None = None,
    ) -> None:
        """Look up a single card by name or uuid.

        Args:
            name: Card name to search for
            uuid: Optional uuid for exact printing lookup
            target_set: Optional set code for selecting the specific printing in gallery
            target_number: Optional collector number for selecting the specific printing
        """
        if not self._db:
            return

        self._hide_synergy_panel()
        self._synergy_mode = False
        self._artist_mode = False

        try:
            card = None

            # If target_set and target_number are provided, try to load that exact printing
            if target_set and target_number:
                db_card = await self._db.get_card_by_set_and_number(target_set, target_number)
                if db_card:
                    # Convert db Card to CardDetail using the cards tool
                    card = await cards.get_card(self._db, uuid=db_card.uuid)

            # Fall back to uuid or name lookup if no target printing or not found
            if card is None:
                card = await cards.get_card(self._db, name=name, uuid=uuid)

            self._current_results = [card]
            self._current_card = card
            self._update_results([card])
            self._update_card_panel(card)
            # Pass target set/number if provided, otherwise use card's own set/number
            # QW2: Auto-focus art navigator for single card lookup
            await self._load_card_extras(
                card,
                target_set=target_set or card.set_code,
                target_number=target_number or card.number,
                auto_focus_art=True,
            )
        except CardNotFoundError:
            filters = SearchCardsInput(name=name, page_size=10)
            result = await cards.search_cards(self._db, filters)
            if result.cards:
                await self._load_search_results(result.cards)
            else:
                self._show_message(f"[yellow]No cards found matching '{name}'[/]")

    @work
    async def search_cards(self, query: str) -> None:
        """Search for cards."""
        if not self._db:
            return

        self._hide_synergy_panel()
        self._synergy_mode = False
        self._artist_mode = False

        # Use max allowed page size to get more results for pagination
        filters = parse_search_query(query)
        filters_dict = filters.model_dump()
        filters_dict["page_size"] = 100  # Max allowed by SearchCardsInput
        search_filters = SearchCardsInput(**filters_dict)

        result = await cards.search_cards(self._db, search_filters)

        if result.cards:
            await self._load_search_results(result.cards, query)
        else:
            self._pagination = None
            self._update_pagination_header()
            self._show_message(f"[yellow]No cards found for: {query}[/]")

    async def _load_search_results(self, summaries: list[CardSummary], query: str = "") -> None:
        """Load full card details for search results with pagination."""
        if not self._db:
            return

        # Create pagination state
        self._pagination = PaginationState.from_summaries(
            summaries=summaries,
            source_type="search",
            source_query=query,
            page_size=25,
        )

        # Load first page
        self._current_results = []
        for summary in self._pagination.current_page_items:
            try:
                # Use uuid if available for exact printing, otherwise fall back to name
                if summary.uuid:
                    detail = await cards.get_card(self._db, uuid=summary.uuid)
                else:
                    detail = await cards.get_card(self._db, name=summary.name)
                self._current_results.append(detail)
            except CardNotFoundError:
                pass

        # Cache first page
        self._pagination.cache_details(1, self._current_results)

        self._update_results(self._current_results)
        self._update_pagination_header()

        if self._current_results:
            self._current_card = self._current_results[0]
            self._update_card_panel(self._current_results[0])
            await self._load_card_extras(self._current_results[0])

    async def _load_card_extras(
        self,
        card: CardDetail,
        panel_id: str = "#card-panel",
        target_set: str | None = None,
        target_number: str | None = None,
        auto_focus_art: bool = False,
    ) -> None:
        """Load rulings, legalities, and printings for a card.

        Args:
            card: The card to load extras for
            panel_id: CSS selector for the CardPanel to update
            target_set: Optional set code to select in the gallery (defaults to card.set_code)
            target_number: Optional collector number to select (defaults to card.number)
            auto_focus_art: If True, auto-focus the art navigator after loading (QW2)
        """
        from ..widgets import CardPanel

        panel = self.query_one(panel_id, CardPanel)

        tasks = [
            panel.load_printings(
                self._db,
                card.name,
                flavor_name=card.flavor_name,
                target_set=target_set or card.set_code,
                target_number=target_number or card.number,
            )
        ]
        if self._db:
            tasks.append(panel.load_legalities(self._db, card.name))

        await asyncio.gather(*tasks, return_exceptions=True)

        # QW2: Auto-focus art navigator for single card results
        if auto_focus_art:
            panel.focus_art_navigator()

    @work
    async def lookup_random(self) -> None:
        """Get a random card."""
        if not self._db:
            return

        self._hide_synergy_panel()
        self._synergy_mode = False
        self._artist_mode = False

        card = await cards.get_random_card(self._db)
        self._current_results = [card]
        self._current_card = card
        self._update_results([card])
        self._update_card_panel(card)
        # QW2: Auto-focus art navigator for random card
        await self._load_card_extras(card, auto_focus_art=True)
