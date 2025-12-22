"""Recommendation card item widget with owned indicator and score display."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.widgets import ListItem, Static

from ..formatting import prettify_mana
from ..ui.theme import ui_colors

if TYPE_CHECKING:
    from mtg_core.tools.recommendations.hybrid import ScoredRecommendation


class RecommendationCardItem(ListItem):
    """A recommendation card in the list.

    Displays:
    - Owned indicator (checkmark if in collection)
    - Card name with mana cost
    - Type line
    - Score bar with percentage
    - Primary reason (first reason from recommendation)
    """

    DEFAULT_CSS = """
    RecommendationCardItem {
        height: auto;
        min-height: 4;
        padding: 0 1;
    }

    RecommendationCardItem Static {
        width: 100%;
    }

    RecommendationCardItem.-highlight {
        background: #2a2a4e;
        border-left: heavy #c9a227;
    }

    RecommendationCardItem:hover {
        background: #1a1a2e;
    }
    """

    def __init__(
        self,
        rec: ScoredRecommendation,
        in_collection: bool = False,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.recommendation = rec
        self.in_collection = in_collection

    def compose(self) -> ComposeResult:
        yield Static(self._format_card())

    def _format_card(self) -> str:
        """Format the recommendation card display."""
        rec = self.recommendation
        lines: list[str] = []

        # Line 1: Owned indicator + Name + Mana cost
        owned_icon = "[green]\u2713[/]" if self.in_collection else "[dim]\u25cb[/]"
        mana = prettify_mana(rec.mana_cost) if rec.mana_cost else ""
        name_line = f"{owned_icon} [{ui_colors.GOLD}]{rec.name}[/] {mana}"
        lines.append(name_line)

        # Line 2: Type line
        if rec.type_line:
            lines.append(f"   [{ui_colors.TEXT_DIM}]{rec.type_line}[/]")

        # Line 3: Score bar + percentage
        score_pct = int(rec.total_score * 100)
        score_color = self._get_score_color(rec.total_score)
        bar_width = int(rec.total_score * 10)
        bar = "\u2588" * bar_width + "\u2591" * (10 - bar_width)
        lines.append(f"   [{score_color}]{bar}[/] [{score_color}]{score_pct}%[/]")

        # Line 4: Primary reason
        if rec.reasons:
            reason = rec.reasons[0]
            # Truncate long reasons
            if len(reason) > 50:
                reason = reason[:47] + "..."
            lines.append(f"   [{ui_colors.TEXT_DIM}]\u2192 {reason}[/]")

        return "\n".join(lines)

    def _get_score_color(self, score: float) -> str:
        """Get color based on score."""
        if score >= 0.7:
            return ui_colors.SYNERGY_STRONG
        elif score >= 0.5:
            return ui_colors.SYNERGY_MODERATE
        elif score >= 0.3:
            return ui_colors.SYNERGY_WEAK
        return ui_colors.TEXT_DIM
