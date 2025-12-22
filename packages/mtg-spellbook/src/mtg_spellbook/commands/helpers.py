"""Helper methods for command handlers (results display, panels, etc.)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.widgets import Static

from ..ui.theme import ui_colors
from ..widgets.card_result_item import CardResultItem

if TYPE_CHECKING:
    from mtg_core.data.models.responses import CardDetail


class CommandHelpersMixin:
    """Mixin providing helper methods for command handlers."""

    if TYPE_CHECKING:
        _synergy_mode: bool
        _synergy_info: dict[str, Any]

        def query_one(self, selector: str, expect_type: type[Any] = ...) -> Any: ...

    def _update_results(self, results: list[CardDetail]) -> None:
        """Update the results list with enhanced formatting."""
        from ..widgets import ResultsList

        results_list = self.query_one("#results-list", ResultsList)
        results_list.clear()

        for card in results:
            # Use unified CardResultItem for consistent formatting
            results_list.append(CardResultItem(card))

        self._update_results_header(f"Results ({len(results)})")

        # Set index to 0 so first item is highlighted when user navigates
        # Don't auto-focus results list - let user stay in search input
        if results:
            results_list.index = 0

    def _update_results_header(self, text: str) -> None:
        """Update results header text with enhanced styling."""
        header = self.query_one("#results-header", Static)
        header.update(f"[bold {ui_colors.GOLD}]{text}[/]")

    def _update_card_panel(self, card: CardDetail | None) -> None:
        """Update the card panel."""
        from ..widgets import CardPanel

        panel = self.query_one("#card-panel", CardPanel)
        panel.update_card(card)

    def _show_synergy_panel(self) -> None:
        """Show side-by-side comparison mode (for synergies/combos)."""
        self.query_one("#source-card-panel").add_class("visible")
        self.query_one("#card-panel").add_class("synergy-mode")

    def _hide_synergy_panel(self) -> None:
        """Hide comparison mode, show card panel at full width."""
        from ..widgets import CardPanel

        self.query_one("#source-card-panel").remove_class("visible")
        self.query_one("#card-panel").remove_class("synergy-mode")
        source_panel = self.query_one("#source-card-panel", CardPanel)
        source_panel.update_card(None)

    def show_help(self) -> None:
        """Show help - use Menu (F10) for navigation options."""
        from typing import Any, cast

        app = cast(Any, self)
        app.notify("Press F10 or Ctrl+M to open the Menu for navigation options", timeout=5)
