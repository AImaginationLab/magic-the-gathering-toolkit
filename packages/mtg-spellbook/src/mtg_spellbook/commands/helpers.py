"""Helper methods for command handlers (results display, panels, etc.)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.widgets import Label, ListItem, Static

from ..formatting import prettify_mana

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
            name_color = "#e65c00"
        elif rarity_lower == "rare":
            name_color = "#e6c84a"
        else:
            name_color = "#ffffff"

        # Mana cost
        mana = prettify_mana(card.mana_cost) if card.mana_cost else ""

        # Type icon
        type_icon = self._get_type_icon(card.type)

        # Build line
        parts = [f"[bold {name_color}]{card.name}[/]"]
        if mana:
            parts.append(f"{mana}")
        if type_icon:
            parts.append(f"[dim]{type_icon}[/]")

        return " ".join(parts)

    def _get_type_icon(self, card_type: str) -> str:
        """Get icon for card type."""
        type_lower = card_type.lower()
        if "creature" in type_lower:
            return "⚔"
        elif "instant" in type_lower:
            return "⚡"
        elif "sorcery" in type_lower:
            return "📜"
        elif "artifact" in type_lower:
            return "⚙"
        elif "enchantment" in type_lower:
            return "✨"
        elif "planeswalker" in type_lower:
            return "👤"
        elif "land" in type_lower:
            return "🌍"
        return ""

    def _update_results_header(self, text: str) -> None:
        """Update results header text with enhanced styling."""
        header = self.query_one("#results-header", Static)
        header.update(f"[bold #e6c84a]{text}[/]")

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

        help_text = """[bold #e6c84a]✦ MTG Spellbook Help ✦[/]
[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]

[bold #c9a227]📖 Card Lookup[/]
  [#e6c84a]<card name>[/]     Look up a card directly
  [#e6c84a]search <query>[/]  Search with filters
  [#e6c84a]random[/]          Get a random card
  [#e6c84a]art <name>[/]      View card artwork

[bold #c9a227]📋 Card Info[/]
  [#e6c84a]rulings <name>[/]  Official card rulings
  [#e6c84a]legal <name>[/]    Format legalities
  [#e6c84a]price <name>[/]    Current prices

[bold #c9a227]🔗 Synergy[/]
  [#e6c84a]synergy <name>[/]  Find synergistic cards
  [#e6c84a]combos <name>[/]   Find known combos

[bold #c9a227]📚 Browse[/]
  [#e6c84a]sets[/]            Browse all sets
  [#e6c84a]set <code>[/]      Set details
  [#e6c84a]stats[/]           Database statistics

[bold #c9a227]🔍 Search Filters[/]
  [#7ec850]t:[/]type   [#4a9fd8]c:[/]colors   [#b86fce]ci:[/]identity
  [#9a9a9a]cmc:[/]N    [#e6c84a]f:[/]format   [#c9a227]r:[/]rarity
  [cyan]set:[/]CODE [#e65c00]kw:[/]keyword [dim]text:[/]"..."

[bold #c9a227]⚡ Quick Actions[/]
  [bold #e6c84a]Ctrl+S[/]  [dim]→[/]  Synergies for current card
  [bold #e6c84a]Ctrl+O[/]  [dim]→[/]  Combos for current card
  [bold #e6c84a]Ctrl+A[/]  [dim]→[/]  Art gallery
  [bold #e6c84a]Ctrl+P[/]  [dim]→[/]  Price info
  [bold #e6c84a]Ctrl+R[/]  [dim]→[/]  Random card
  [bold #e6c84a]Ctrl+D[/]  [dim]→[/]  Toggle deck panel
  [bold #e6c84a]Ctrl+E[/]  [dim]→[/]  Add card to deck

[bold #c9a227]🎮 Navigation[/]
  [bold #e6c84a]↑↓[/]      [dim]→[/]  Navigate results
  [bold #e6c84a]Tab[/]     [dim]→[/]  Switch tabs
  [bold #e6c84a]←→[/]      [dim]→[/]  Navigate art printings
  [bold #e6c84a]Esc[/]     [dim]→[/]  Focus input
  [bold #e6c84a]Ctrl+L[/]  [dim]→[/]  Clear display
  [bold #e6c84a]Ctrl+C[/]  [dim]→[/]  Quit

[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]
[dim italic]Type 'help' anytime to see this screen[/]
"""
        card_text.update(help_text)
