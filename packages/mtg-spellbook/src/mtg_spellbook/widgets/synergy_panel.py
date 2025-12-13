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
        """Display the source card (single-line compact view) with enhanced styling."""
        self._source_card = card
        content = self.query_one("#synergy-content", Static)

        mana = prettify_mana(card.mana_cost) if card.mana_cost else ""

        # Get type icon
        type_icon = self._get_type_icon(card.type or "")

        parts = [f"[bold #e6c84a]🎯 Synergies for:[/] [bold #e6c84a]{card.name}[/]"]
        if mana:
            parts.append(mana)

        type_color = self._get_type_color(card.type or "")
        type_part = f"[{type_color}]{type_icon} {card.type}[/]"
        if card.power is not None and card.toughness is not None:
            type_part += f" [bold #c9a227]⚔ {card.power}/{card.toughness}[/]"
        elif card.loyalty is not None:
            type_part += f" [bold #c9a227]✦ {card.loyalty}[/]"
        parts.append(type_part)

        content.update("  ".join(parts))

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

    def _get_type_color(self, card_type: str) -> str:
        """Get color based on card type."""
        type_lower = card_type.lower()
        if "creature" in type_lower:
            return "#7ec850"
        elif "instant" in type_lower or "sorcery" in type_lower:
            return "#4a9fd8"
        elif "artifact" in type_lower:
            return "#9a9a9a"
        elif "enchantment" in type_lower:
            return "#b86fce"
        elif "planeswalker" in type_lower:
            return "#e6c84a"
        elif "land" in type_lower:
            return "#a67c52"
        return "#888"

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
            f"[bold #e6c84a]🔗 Synergies for {result.card_name}[/] [dim]({result.total_found} found)[/]",
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
            return "#00ff00"  # Bright green
        elif score >= 0.6:
            return "#c9a227"  # Gold
        elif score >= 0.4:
            return "#e6c84a"  # Light gold
        return "#666"  # Gray
