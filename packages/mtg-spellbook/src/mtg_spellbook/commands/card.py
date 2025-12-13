"""Card lookup and search commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual import work

from mtg_core.data.models.inputs import SearchCardsInput
from mtg_core.exceptions import CardNotFoundError
from mtg_core.tools import cards

from ..search import parse_search_query

if TYPE_CHECKING:
    from mtg_core.data.models.responses import CardDetail, CardSummary


class CardCommandsMixin:
    """Mixin providing card lookup and search commands."""

    if TYPE_CHECKING:
        _db: Any
        _scryfall: Any
        _current_results: list[Any]
        _current_card: Any
        _synergy_mode: bool

        def query_one(self, selector: str, expect_type: type[Any] = ...) -> Any: ...
        def _hide_synergy_panel(self) -> None: ...
        def _update_results(self, results: list[Any]) -> None: ...
        def _update_card_panel(self, card: Any) -> None: ...
        def _show_message(self, message: str) -> None: ...

    @work
    async def lookup_card(self, name: str) -> None:
        """Look up a single card by name."""
        if not self._db:
            return

        self._hide_synergy_panel()
        self._synergy_mode = False

        try:
            card = await cards.get_card(self._db, self._scryfall, name=name)
            self._current_results = [card]
            self._current_card = card
            self._update_results([card])
            self._update_card_panel(card)
            await self._load_card_extras(card)
        except CardNotFoundError:
            filters = SearchCardsInput(name=name, page_size=10)
            result = await cards.search_cards(self._db, self._scryfall, filters)
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

        filters = parse_search_query(query)
        result = await cards.search_cards(self._db, self._scryfall, filters)

        if result.cards:
            await self._load_search_results(result.cards)
        else:
            self._show_message(f"[yellow]No cards found for: {query}[/]")

    async def _load_search_results(self, summaries: list[CardSummary]) -> None:
        """Load full card details for search results."""
        if not self._db:
            return
        self._current_results = []

        for summary in summaries[:25]:
            try:
                detail = await cards.get_card(
                    self._db, self._scryfall, name=summary.name
                )
                self._current_results.append(detail)
            except CardNotFoundError:
                pass

        self._update_results(self._current_results)
        if self._current_results:
            self._current_card = self._current_results[0]
            self._update_card_panel(self._current_results[0])
            await self._load_card_extras(self._current_results[0])

    async def _load_card_extras(
        self, card: CardDetail, panel_id: str = "#card-panel"
    ) -> None:
        """Load rulings, legalities, and printings for a card.

        Args:
            card: The card to load extras for
            panel_id: CSS selector for the CardPanel to update
        """
        from ..widgets import CardPanel

        panel = self.query_one(panel_id, CardPanel)

        if self._db:
            await panel.load_rulings(self._db, card.name)
            await panel.load_legalities(self._db, card.name)

        await panel.load_printings(self._scryfall, card.name)

    @work
    async def lookup_random(self) -> None:
        """Get a random card."""
        if not self._db:
            return

        self._hide_synergy_panel()
        self._synergy_mode = False

        card = await cards.get_random_card(self._db, self._scryfall)
        self._current_results = [card]
        self._current_card = card
        self._update_results([card])
        self._update_card_panel(card)
        await self._load_card_extras(card)
