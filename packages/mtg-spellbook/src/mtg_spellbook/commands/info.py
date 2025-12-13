"""Card information commands (rulings, legalities, price, art)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual import work
from textual.widgets import Static, TabbedContent

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
        """Load rulings and switch to rulings tab."""
        if not self._db:
            return

        from ..widgets import CardPanel

        panel = self.query_one("#card-panel", CardPanel)
        await panel.load_rulings(self._db, card_name)

        tabs = panel.query_one(panel.get_child_id("tabs"), TabbedContent)
        tabs.active = panel.get_child_name("tab-rulings")

    @work
    async def load_legalities(self, card_name: str) -> None:
        """Load legalities and switch to legal tab."""
        if not self._db:
            return

        from ..widgets import CardPanel

        panel = self.query_one("#card-panel", CardPanel)
        await panel.load_legalities(self._db, card_name)

        tabs = panel.query_one(panel.get_child_id("tabs"), TabbedContent)
        tabs.active = panel.get_child_name("tab-legal")

    @work
    async def show_price(self, card_name: str) -> None:
        """Show price for a card."""
        if not self._scryfall:
            self._show_message("[red]Scryfall database not available for prices[/]")
            return

        from ..widgets import CardPanel

        try:
            result = await images.get_card_price(self._scryfall, card_name)

            panel = self.query_one("#card-panel", CardPanel)
            price_text = panel.query_one(panel.get_child_id("price-text"), Static)

            lines = [f"[bold]💰 {result.card_name}[/]", ""]
            if result.prices:
                if result.prices.usd:
                    lines.append(f"  USD:  [green]${result.prices.usd:.2f}[/]")
                if result.prices.usd_foil:
                    lines.append(f"  Foil: [yellow]${result.prices.usd_foil:.2f}[/]")
                if result.prices.eur:
                    lines.append(f"  EUR:  [green]€{result.prices.eur:.2f}[/]")
            else:
                lines.append("  [dim]No price data available[/]")

            price_text.update("\n".join(lines))

            tabs = panel.query_one(panel.get_child_id("tabs"), TabbedContent)
            tabs.active = panel.get_child_name("tab-price")

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
            await panel.load_printings(self._scryfall, card_name)

            tabs = panel.query_one(panel.get_child_id("tabs"), TabbedContent)
            tabs.active = panel.get_child_name("tab-art")

        except CardNotFoundError:
            self._show_message(f"[red]Card not found: {card_name}[/]")
