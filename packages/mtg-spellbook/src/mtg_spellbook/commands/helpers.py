"""Helper methods for command handlers (results display, panels, etc.)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.widgets import Label, ListItem, Static

from ..formatting import prettify_mana

if TYPE_CHECKING:
    from mtg_core.data.models.responses import CardDetail


class CommandHelpersMixin:
    """Mixin providing helper methods for command handlers."""

    _synergy_mode: bool
    _synergy_info: dict[str, Any]

    def query_one(self, selector: str, expect_type: type[Any] = ...) -> Any: ...

    def _update_results(self, results: list[CardDetail]) -> None:
        """Update the results list."""
        from ..widgets import ResultsList

        results_list = self.query_one("#results-list", ResultsList)
        results_list.clear()

        for card in results:
            mana = prettify_mana(card.mana_cost) if card.mana_cost else ""
            label = (
                f"[bold]{card.name}[/]  {mana}" if mana else f"[bold]{card.name}[/]"
            )
            results_list.append(ListItem(Label(label)))

        self._update_results_header(f"Results ({len(results)})")

        if results:
            results_list.focus()
            results_list.index = 0

    def _update_results_header(self, text: str) -> None:
        """Update results header text."""
        header = self.query_one("#results-header", Static)
        header.update(f"[bold]{text}[/]")

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
        """Show help in card panel."""
        from ..widgets import CardPanel

        self._hide_synergy_panel()

        panel = self.query_one("#card-panel", CardPanel)
        card_text = panel.query_one(panel.get_child_id("card-text"), Static)

        help_text = """[bold yellow]⚔️ MTG Spellbook Help[/]

[bold cyan]Card Lookup:[/]
  [cyan]<card name>[/]     Look up a card directly
  [cyan]search <query>[/]  Search with filters
  [cyan]random[/]          Get a random card
  [cyan]art <name>[/]      View card artwork

[bold cyan]Card Info:[/]
  [cyan]rulings <name>[/]  Official card rulings
  [cyan]legal <name>[/]    Format legalities
  [cyan]price <name>[/]    Current prices

[bold cyan]Synergy:[/]
  [cyan]synergy <name>[/]  Find synergistic cards
  [cyan]combos <name>[/]   Find known combos

[bold cyan]Browse:[/]
  [cyan]sets[/]            Browse all sets
  [cyan]set <code>[/]      Set details
  [cyan]stats[/]           Database statistics

[bold cyan]Search Filters:[/]
  [cyan]t:[/]type   [cyan]c:[/]colors   [cyan]ci:[/]identity
  [cyan]cmc:[/]N    [cyan]f:[/]format   [cyan]r:[/]rarity
  [cyan]set:[/]CODE [cyan]kw:[/]keyword [cyan]text:[/]"..."

[bold cyan]Quick Actions:[/]
  [yellow]Ctrl+S[/]    Synergies for current card
  [yellow]Ctrl+O[/]    Combos for current card
  [yellow]Ctrl+A[/]    Art gallery
  [yellow]Ctrl+P[/]    Price info
  [yellow]Ctrl+R[/]    Random card

[bold cyan]Navigation:[/]
  [yellow]↑↓[/]        Navigate results
  [yellow]Tab[/]       Switch tabs
  [yellow]←→[/]        Navigate art printings (on Art tab)
  [yellow]Esc[/]       Focus input
  [yellow]Ctrl+L[/]    Clear
  [yellow]Ctrl+C[/]    Quit
"""
        card_text.update(help_text)
