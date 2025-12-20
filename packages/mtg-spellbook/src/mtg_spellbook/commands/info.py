"""Card information commands (rulings, legalities, price, art)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual import work

from mtg_core.exceptions import CardNotFoundError
from mtg_core.tools import images


class InfoCommandsMixin:
    """Mixin providing card info commands (rulings, legalities, price, art)."""

    if TYPE_CHECKING:
        _db: Any
        _scryfall: Any

        def query_one(self, selector: str, expect_type: type[Any] = ...) -> Any: ...
        def _show_message(self, message: str) -> None: ...

    @work
    async def load_rulings(self, card_name: str) -> None:
        """Load rulings for a card (integrated in focus view)."""
        if not self._db:
            return

        from ..widgets import CardPanel

        panel = self.query_one("#card-panel", CardPanel)
        await panel.load_rulings(self._db, card_name)

    @work
    async def load_legalities(self, card_name: str) -> None:
        """Load legalities for a card (shown in focus view)."""
        if not self._db:
            return

        from ..widgets import CardPanel

        panel = self.query_one("#card-panel", CardPanel)
        await panel.load_legalities(self._db, card_name)

    @work
    async def show_price(self, card_name: str) -> None:
        """Show price for a card (prices shown in focus view)."""
        if not self._scryfall:
            self._show_message("[red]Scryfall database not available for prices[/]")
            return

        try:
            result = await images.get_card_price(self._scryfall, card_name)

            # Format price info for notification
            lines = []
            if result.prices:
                if result.prices.usd is not None:
                    lines.append(f"${result.prices.usd:.2f}")
                if result.prices.usd_foil is not None:
                    lines.append(f"Foil: ${result.prices.usd_foil:.2f}")

            if lines:
                self._show_message(f"[green]{result.card_name}: {' | '.join(lines)}[/]")
            else:
                self._show_message(f"[dim]No price data for {result.card_name}[/]")

        except CardNotFoundError:
            self._show_message(f"[red]Could not get price for: {card_name}[/]")

    @work
    async def show_art(self, card_name: str) -> None:
        """Show card art with all printings."""
        if not self._scryfall:
            self._show_message("[red]Scryfall database not available for images[/]")
            return

        from ..widgets import CardPanel

        try:
            panel = self.query_one("#card-panel", CardPanel)
            await panel.load_printings(self._scryfall, self._db, card_name)

        except CardNotFoundError:
            self._show_message(f"[red]Card not found: {card_name}[/]")
