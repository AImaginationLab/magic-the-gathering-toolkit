"""Synergy panel widget for displaying source card in synergy mode."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from ..formatting import prettify_mana
from ..ui.formatters import CardFormatters
from ..ui.theme import ui_colors

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
        """Display the source card (single-line compact view) with enhanced styling."""
        self._source_card = card
        content = self.query_one("#synergy-content", Static)

        mana = prettify_mana(card.mana_cost) if card.mana_cost else ""

        type_icon = CardFormatters.get_type_icon(card.type or "")

        parts = [
            f"[bold {ui_colors.GOLD}]🎯 Synergies for:[/] [bold {ui_colors.GOLD}]{card.name}[/]"
        ]
        if mana:
            parts.append(mana)

        type_color = CardFormatters.get_type_color(card.type or "")
        type_part = f"[{type_color}]{type_icon} {card.type}[/]"
        if card.power is not None and card.toughness is not None:
            type_part += f" [bold {ui_colors.GOLD_DIM}]⚔ {card.power}/{card.toughness}[/]"
        elif card.loyalty is not None:
            type_part += f" [bold {ui_colors.GOLD_DIM}]✦ {card.loyalty}[/]"
        parts.append(type_part)

        content.update("  ".join(parts))

    def clear_source(self) -> None:
        """Clear the source card display."""
        self._source_card = None
        content = self.query_one("#synergy-content", Static)
        content.update("[dim]Use 'synergy <card>' to find synergistic cards[/]")

    def update_synergies(self, result: FindSynergiesResult) -> None:
        """Update displayed synergies with enhanced visual presentation."""
        content = self.query_one("#synergy-content", Static)

        if not result.synergies:
            content.update(f"[dim]No synergies found for {result.card_name}[/]")
            return

        lines = [
            f"[bold {ui_colors.GOLD}]🔗 Synergies for {result.card_name}[/] [dim]({result.total_found} found)[/]",
            "[dim]" + "─" * 50 + "[/]",
            "",
        ]

        type_icons = {
            "keyword": "🔑",
            "tribal": "👥",
            "ability": "✨",
            "theme": "🎯",
            "archetype": "🏛️",
            "mechanic": "⚙",
            "combo": "💫",
        }

        for syn in result.synergies[:20]:
            icon = type_icons.get(syn.synergy_type, "•")
            mana = f" {prettify_mana(syn.mana_cost)}" if syn.mana_cost else ""

            # Enhanced score bar with gradient effect
            score_bar = self._render_score_bar(syn.score)
            score_color = self._score_color(syn.score)

            lines.append(f"  [{score_color}]{score_bar}[/] {icon} [bold]{syn.name}[/]{mana}")
            lines.append(f"       [dim italic]{syn.reason}[/]")
            lines.append("")

        content.update("\n".join(lines))

    def _render_score_bar(self, score: float) -> str:
        """Render a visual score bar."""
        filled = int(score * 10)
        return "█" * filled + "░" * (10 - filled)

    def _score_color(self, score: float) -> str:
        """Get color for synergy score."""
        if score >= 0.8:
            return ui_colors.SYNERGY_STRONG
        elif score >= 0.6:
            return ui_colors.SYNERGY_MODERATE
        elif score >= 0.4:
            return ui_colors.SYNERGY_WEAK
        return "#666"
