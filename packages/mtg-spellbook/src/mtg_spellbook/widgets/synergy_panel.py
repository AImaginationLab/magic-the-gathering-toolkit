"""Synergy panel widget for displaying source card in synergy mode."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from ..formatting import prettify_mana

if TYPE_CHECKING:
    from mtg_core.data.models.responses import CardDetail, FindSynergiesResult


class SynergyPanel(Vertical):
    """Display source card when viewing synergies."""

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._source_card: CardDetail | None = None

    def compose(self) -> ComposeResult:
        yield Static(
            "[dim]Use 'synergy <card>' to find synergistic cards[/]",
            id="synergy-content",
        )

    def show_source_card(self, card: CardDetail) -> None:
        """Display the source card (single-line compact view)."""
        self._source_card = card
        content = self.query_one("#synergy-content", Static)

        mana = prettify_mana(card.mana_cost) if card.mana_cost else ""

        parts = [f"[bold cyan]🎯 Synergies for:[/] [bold]{card.name}[/]"]
        if mana:
            parts.append(mana)

        type_part = f"[dim]{card.type}[/]"
        if card.power is not None and card.toughness is not None:
            type_part += f" [bold]{card.power}/{card.toughness}[/]"
        elif card.loyalty is not None:
            type_part += f" [bold]Loyalty: {card.loyalty}[/]"
        parts.append(type_part)

        content.update("  ".join(parts))

    def clear_source(self) -> None:
        """Clear the source card display."""
        self._source_card = None
        content = self.query_one("#synergy-content", Static)
        content.update("[dim]Use 'synergy <card>' to find synergistic cards[/]")

    def update_synergies(self, result: FindSynergiesResult) -> None:
        """Update displayed synergies (legacy method for combos display)."""
        content = self.query_one("#synergy-content", Static)

        if not result.synergies:
            content.update(f"[dim]No synergies found for {result.card_name}[/]")
            return

        lines = [
            f"[bold]🔗 Synergies for {result.card_name}[/] ({result.total_found} found)",
            "",
        ]

        type_icons = {
            "keyword": "🔑",
            "tribal": "👥",
            "ability": "✨",
            "theme": "🎯",
            "archetype": "🏛️",
        }

        for syn in result.synergies[:20]:
            icon = type_icons.get(syn.synergy_type, "•")
            mana = f" {prettify_mana(syn.mana_cost)}" if syn.mana_cost else ""
            score_bar = "●" * int(syn.score * 5) + "○" * (5 - int(syn.score * 5))
            lines.append(
                f"  [{self._score_color(syn.score)}]{score_bar}[/] "
                f"{icon} [cyan]{syn.name}[/]{mana}"
            )
            lines.append(f"         [dim]{syn.reason}[/]")

        content.update("\n".join(lines))

    def _score_color(self, score: float) -> str:
        if score >= 0.8:
            return "green"
        elif score >= 0.5:
            return "yellow"
        return "dim"
