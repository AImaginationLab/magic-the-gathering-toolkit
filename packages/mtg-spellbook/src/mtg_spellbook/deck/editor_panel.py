"""Deck editor panel widget."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import ListItem, ListView, Static

from ..formatting import prettify_mana
from .messages import DeckSelected

if TYPE_CHECKING:
    from ..deck_manager import DeckWithCards


class DeckCardItem(ListItem):
    """A single card in the deck editor."""

    def __init__(
        self, card_name: str, quantity: int, mana_cost: str | None = None
    ) -> None:
        super().__init__()
        self.card_name = card_name
        self.quantity = quantity
        self.mana_cost = mana_cost

    def compose(self) -> ComposeResult:
        mana = prettify_mana(self.mana_cost) if self.mana_cost else ""
        yield Static(f"{self.quantity}x {self.card_name}  {mana}")


class DeckEditorPanel(Vertical):
    """Panel for editing a deck."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("plus", "increase_qty", "+1"),
        Binding("equal", "increase_qty", "+1"),
        Binding("minus", "decrease_qty", "-1"),
        Binding("s", "toggle_sideboard", "Sideboard"),
        Binding("delete", "remove_card", "Remove"),
        Binding("backspace", "back_to_list", "Back"),
        Binding("v", "validate", "Validate"),
    ]

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._deck: DeckWithCards | None = None

    def compose(self) -> ComposeResult:
        yield Static("[bold]No deck loaded[/]", id="deck-editor-header")
        with Horizontal(id="deck-editor-content"):
            with Vertical(id="deck-cards-container"):
                yield Static("[#c9a227]Mainboard[/]", id="mainboard-header")
                yield ListView(id="mainboard-list")
                yield Static("[#c9a227]Sideboard[/]", id="sideboard-header")
                yield ListView(id="sideboard-list")
            with Vertical(id="deck-stats-container"):
                yield Static("[dim]Stats[/]", id="deck-stats")
        yield Static(
            "[dim][+/-] Qty · [S] Sideboard · [Del] Remove · [V] Validate · [Backspace] Back[/]",
            id="deck-editor-footer",
        )

    def update_deck(self, deck: DeckWithCards | None) -> None:
        """Update the displayed deck."""
        self._deck = deck

        header = self.query_one("#deck-editor-header", Static)
        mainboard = self.query_one("#mainboard-list", ListView)
        sideboard = self.query_one("#sideboard-list", ListView)
        stats = self.query_one("#deck-stats", Static)

        mainboard.clear()
        sideboard.clear()

        if deck is None:
            header.update("[bold]No deck loaded[/]")
            stats.update("[dim]No stats[/]")
            return

        format_str = f" ({deck.format})" if deck.format else ""
        header.update(f"[bold #c9a227]{deck.name}[/]{format_str}")

        for card in sorted(deck.mainboard, key=lambda c: c.card_name):
            mana_cost = card.card.mana_cost if card.card else None
            mainboard.append(DeckCardItem(card.card_name, card.quantity, mana_cost))

        for card in sorted(deck.sideboard, key=lambda c: c.card_name):
            mana_cost = card.card.mana_cost if card.card else None
            sideboard.append(DeckCardItem(card.card_name, card.quantity, mana_cost))

        stats.update(self._render_stats(deck))

    def _render_stats(self, deck: DeckWithCards) -> str:
        """Render deck stats."""
        lines = [
            f"[bold]Cards:[/] {deck.mainboard_count}/60",
            f"[bold]Sideboard:[/] {deck.sideboard_count}/15",
            "",
        ]

        curve: dict[int, int] = {}
        for card in deck.mainboard:
            if card.card:
                cmc = int(card.card.mana_value or 0)
                curve[cmc] = curve.get(cmc, 0) + card.quantity

        if curve:
            lines.append("[bold]Mana Curve:[/]")
            max_count = max(curve.values()) if curve else 1
            for cmc in range(min(curve.keys() or [0]), max(curve.keys() or [0]) + 1):
                count = curve.get(cmc, 0)
                bar_len = int((count / max_count) * 8) if max_count > 0 else 0
                bar = "█" * bar_len
                lines.append(f"[dim]{cmc}:[/] {bar} {count}")

        return "\n".join(lines)

    def action_back_to_list(self) -> None:
        """Go back to deck list."""
        self.post_message(DeckSelected(-1))

    def action_validate(self) -> None:
        """Validate the deck."""
        if self._deck:
            self.app.notify(f"Validating {self._deck.name}...")
