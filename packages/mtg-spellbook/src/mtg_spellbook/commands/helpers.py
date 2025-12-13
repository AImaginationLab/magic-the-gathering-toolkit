"""Helper methods for command handlers (results display, panels, etc.)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.widgets import Label, ListItem, Static

from ..formatting import prettify_mana
from ..ui.formatters import CardFormatters
from ..ui.theme import card_type_colors, rarity_colors, ui_colors

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
            label = self._format_result_line(card)
            results_list.append(ListItem(Label(label)))

        self._update_results_header(f"🔍 Results ({len(results)})")

        if results:
            results_list.focus()
            results_list.index = 0

    def _format_result_line(self, card: CardDetail) -> str:
        """Format a search result line with enhanced typography."""
        # Name color based on rarity
        rarity_lower = (card.rarity or "").lower()
        if rarity_lower == "mythic":
            name_color = rarity_colors.MYTHIC
        elif rarity_lower == "rare":
            name_color = rarity_colors.RARE
        else:
            name_color = ui_colors.WHITE

        # Mana cost
        mana = prettify_mana(card.mana_cost) if card.mana_cost else ""

        # Type icon
        type_icon = CardFormatters.get_type_icon(card.type or "")

        # Build line
        parts = [f"[bold {name_color}]{card.name}[/]"]
        if mana:
            parts.append(f"{mana}")
        if type_icon:
            parts.append(f"[dim]{type_icon}[/]")

        return " ".join(parts)

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
        """Show help in card panel with enhanced styling."""
        from ..widgets import CardPanel

        self._hide_synergy_panel()

        panel = self.query_one("#card-panel", CardPanel)
        card_text = panel.query_one(panel.get_child_id("card-text"), Static)

        help_text = f"""[bold {ui_colors.GOLD}]✦ MTG Spellbook Help ✦[/]
[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]

[bold {ui_colors.GOLD_DIM}]📖 Card Lookup[/]
  [{ui_colors.GOLD}]<card name>[/]     Look up a card directly
  [{ui_colors.GOLD}]search <query>[/]  Search with filters
  [{ui_colors.GOLD}]random[/]          Get a random card
  [{ui_colors.GOLD}]art <name>[/]      View card artwork

[bold {ui_colors.GOLD_DIM}]📋 Card Info[/]
  [{ui_colors.GOLD}]rulings <name>[/]  Official card rulings
  [{ui_colors.GOLD}]legal <name>[/]    Format legalities
  [{ui_colors.GOLD}]price <name>[/]    Current prices

[bold {ui_colors.GOLD_DIM}]🔗 Synergy[/]
  [{ui_colors.GOLD}]synergy <name>[/]  Find synergistic cards
  [{ui_colors.GOLD}]combos <name>[/]   Find known combos

[bold {ui_colors.GOLD_DIM}]📚 Browse[/]
  [{ui_colors.GOLD}]sets[/]            Browse all sets
  [{ui_colors.GOLD}]set <code>[/]      Set details
  [{ui_colors.GOLD}]stats[/]           Database statistics

[bold {ui_colors.GOLD_DIM}]🔍 Search Filters[/]
  [{card_type_colors.CREATURE}]t:[/]type   [{card_type_colors.INSTANT}]c:[/]colors   [{card_type_colors.ENCHANTMENT}]ci:[/]identity
  [{card_type_colors.ARTIFACT}]cmc:[/]N    [{ui_colors.GOLD}]f:[/]format   [{ui_colors.GOLD_DIM}]r:[/]rarity
  [cyan]set:[/]CODE [{rarity_colors.MYTHIC}]kw:[/]keyword [dim]text:[/]"..."

[bold {ui_colors.GOLD_DIM}]⚡ Quick Actions[/]
  [bold {ui_colors.GOLD}]Ctrl+S[/]  [dim]→[/]  Synergies for current card
  [bold {ui_colors.GOLD}]Ctrl+O[/]  [dim]→[/]  Combos for current card
  [bold {ui_colors.GOLD}]Ctrl+A[/]  [dim]→[/]  Art gallery
  [bold {ui_colors.GOLD}]Ctrl+P[/]  [dim]→[/]  Price info
  [bold {ui_colors.GOLD}]Ctrl+R[/]  [dim]→[/]  Random card
  [bold {ui_colors.GOLD}]Ctrl+D[/]  [dim]→[/]  Toggle deck panel
  [bold {ui_colors.GOLD}]Ctrl+E[/]  [dim]→[/]  Add card to deck

[bold {ui_colors.GOLD_DIM}]🎮 Navigation[/]
  [bold {ui_colors.GOLD}]↑↓[/]      [dim]→[/]  Navigate results
  [bold {ui_colors.GOLD}]Tab[/]     [dim]→[/]  Switch tabs
  [bold {ui_colors.GOLD}]←→[/]      [dim]→[/]  Navigate art printings
  [bold {ui_colors.GOLD}]Esc[/]     [dim]→[/]  Focus input
  [bold {ui_colors.GOLD}]Ctrl+L[/]  [dim]→[/]  Clear display
  [bold {ui_colors.GOLD}]Ctrl+C[/]  [dim]→[/]  Quit

[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]
[dim italic]Type 'help' anytime to see this screen[/]
"""
        card_text.update(help_text)
