"""Detail panel for showing recommendation explanations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static

from ..formatting import prettify_mana
from ..ui.theme import ui_colors

if TYPE_CHECKING:
    from mtg_core.tools.recommendations.hybrid import ScoredRecommendation


class RecommendationDetailPanel(Vertical):
    """Right pane detail panel showing 'Why this card?' breakdown.

    Displays:
    - Card name, mana cost, type line
    - Overall match percentage
    - Score breakdown with visual bars
    - All reasons for recommendation
    - Combos completed
    - 17lands data if available
    - Collection status
    """

    DEFAULT_CSS = """
    RecommendationDetailPanel {
        width: 100%;
        height: 100%;
        background: #0a0a14;
        padding: 1;
    }

    #rec-detail-header {
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
    }

    #rec-detail-scroll {
        height: 1fr;
    }

    #rec-detail-content {
        height: auto;
        padding: 0 1;
    }

    #rec-detail-empty {
        height: 100%;
        content-align: center middle;
    }
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._recommendation: ScoredRecommendation | None = None
        self._in_collection: bool = False

    def compose(self) -> ComposeResult:
        yield Static("", id="rec-detail-header")
        with VerticalScroll(id="rec-detail-scroll"):
            yield Static("", id="rec-detail-content")
        yield Static(
            f"[{ui_colors.TEXT_DIM}]Select a card to see details[/]",
            id="rec-detail-empty",
        )

    def show_recommendation(
        self, rec: ScoredRecommendation, in_collection: bool = False
    ) -> None:
        """Display recommendation detail."""
        self._recommendation = rec
        self._in_collection = in_collection
        self._update_display()

    def clear(self) -> None:
        """Clear the detail panel."""
        self._recommendation = None
        self._in_collection = False
        try:
            header = self.query_one("#rec-detail-header", Static)
            header.update("")
            content = self.query_one("#rec-detail-content", Static)
            content.update("")
            empty = self.query_one("#rec-detail-empty", Static)
            empty.display = True
        except Exception:
            pass

    def _update_display(self) -> None:
        """Update the detail display."""
        if not self._recommendation:
            return

        rec = self._recommendation

        # Hide empty message
        try:
            empty = self.query_one("#rec-detail-empty", Static)
            empty.display = False
        except Exception:
            pass

        # Update header
        try:
            header = self.query_one("#rec-detail-header", Static)
            mana = prettify_mana(rec.mana_cost) if rec.mana_cost else ""
            score_pct = int(rec.total_score * 100)
            score_color = self._get_score_color(rec.total_score)
            header.update(
                f"[bold {ui_colors.GOLD}]{rec.name}[/] {mana}\n"
                f"[{score_color}]({score_pct}% match)[/]"
            )
        except Exception:
            pass

        # Update content
        try:
            content = self.query_one("#rec-detail-content", Static)
            content.update(self._render_detail_content())
        except Exception:
            pass

    def _render_detail_content(self) -> str:
        """Render the full detail content."""
        if not self._recommendation:
            return ""

        rec = self._recommendation
        lines: list[str] = []

        # Type line
        if rec.type_line:
            lines.append(f"[{ui_colors.TEXT_DIM}]{rec.type_line}[/]")
            lines.append("")

        # Collection status
        if self._in_collection:
            lines.append("[green]\u2713 In your collection[/]")
        else:
            lines.append(f"[{ui_colors.TEXT_DIM}]\u2717 Not in collection[/]")
        lines.append("")

        # Score breakdown with visual bars
        lines.append("[bold]Score Breakdown:[/]")
        lines.append(self._render_score_breakdown())
        lines.append("")

        # Why this card? (all reasons from recommender)
        if rec.reasons:
            lines.append("[bold]Why this card?[/]")
            for reason in rec.reasons:
                lines.append(f"  [green]\u2022[/] {reason}")
            lines.append("")

        # Additional insights based on scores
        insights = self._generate_insights()
        if insights:
            lines.append("[bold]Additional Insights:[/]")
            for insight in insights:
                lines.append(f"  [{ui_colors.TEXT_DIM}]\u25B8[/] {insight}")
            lines.append("")

        # Combos it completes
        if rec.completes_combos:
            lines.append("[bold]Completes Combos:[/]")
            lines.extend(self._render_combos(rec.completes_combos[:5]))
            if len(rec.completes_combos) > 5:
                remaining = len(rec.completes_combos) - 5
                lines.append(f"  [{ui_colors.TEXT_DIM}]...and {remaining} more[/]")
            lines.append("")

        # 17lands data
        if rec.limited_tier or rec.limited_gih_wr:
            lines.append("[bold]Limited Performance (17lands):[/]")
            if rec.limited_tier:
                tier_color = self._get_tier_color(rec.limited_tier)
                tier_desc = self._get_tier_description(rec.limited_tier)
                lines.append(f"  Tier: [{tier_color}]{rec.limited_tier}[/] - {tier_desc}")
            if rec.limited_gih_wr:
                wr_color = self._get_winrate_color(rec.limited_gih_wr)
                wr_desc = self._get_winrate_description(rec.limited_gih_wr)
                lines.append(f"  Win Rate (GIH): [{wr_color}]{rec.limited_gih_wr:.1%}[/]")
                lines.append(f"  [{ui_colors.TEXT_DIM}]{wr_desc}[/]")

        return "\n".join(lines)

    def _generate_insights(self) -> list[str]:
        """Generate additional insights based on score components."""
        if not self._recommendation:
            return []

        rec = self._recommendation
        insights: list[str] = []

        # Text similarity insight
        if rec.tfidf_score >= 0.3:
            insights.append(
                f"Card text is {int(rec.tfidf_score * 100)}% similar to your deck's cards"
            )
        elif rec.tfidf_score >= 0.1:
            insights.append("Some text overlap with cards in your deck")

        # Synergy insight
        if rec.synergy_score >= 0.5:
            insights.append("Strong mechanical synergy with your deck's themes")
        elif rec.synergy_score >= 0.2:
            insights.append("Moderate synergy with your deck's strategy")

        # Popularity insight
        if rec.popularity_score >= 0.8:
            insights.append("Very popular in EDHRec (top 20% of cards)")
        elif rec.popularity_score >= 0.5:
            insights.append("Commonly played in similar decks")

        # Combo insight
        if rec.combo_score >= 0.5:
            combo_count = len(rec.completes_combos)
            if combo_count > 1:
                insights.append(f"Key combo piece - enables {combo_count} combos!")
            else:
                insights.append("Combo enabler - completes a powerful interaction")

        # Curve insight
        if rec.curve_score >= 0.5:
            insights.append("Fills a gap in your mana curve")

        # Tribal insight
        if rec.tribal_score >= 0.5:
            insights.append("Matches your deck's creature types")

        # Limited insight (if high)
        if rec.limited_score >= 0.7:
            insights.append("Proven performer in Limited formats")

        return insights

    def _get_tier_description(self, tier: str) -> str:
        """Get description for 17lands tier."""
        descriptions = {
            "S": "Best in format",
            "A": "Excellent pick",
            "B": "Good playable",
            "C": "Average card",
            "D": "Below average",
            "F": "Avoid if possible",
        }
        return descriptions.get(tier.upper(), "Unknown tier")

    def _get_winrate_description(self, wr: float) -> str:
        """Get description for win rate."""
        if wr >= 0.60:
            return "Exceptional - top tier card"
        elif wr >= 0.55:
            return "Great - above average performer"
        elif wr >= 0.52:
            return "Good - solid playable"
        elif wr >= 0.48:
            return "Average - acceptable"
        elif wr >= 0.45:
            return "Below average - situational"
        return "Poor - consider cutting"

    def _render_combos(self, combo_ids: list[str]) -> list[str]:
        """Render combo info with human-readable names."""
        lines: list[str] = []
        try:
            from mtg_core.tools.recommendations.spellbook_combos import (
                get_spellbook_detector,
            )

            detector = get_spellbook_detector()
            for combo_id in combo_ids:
                combo = detector.get_combo(combo_id)
                if combo:
                    # Show card names (truncate if too many)
                    card_names = combo.card_names[:3]
                    cards_str = " + ".join(card_names)
                    if len(combo.card_names) > 3:
                        cards_str += f" +{len(combo.card_names) - 3} more"

                    # Show what it produces
                    produces = combo.produces[:2] if combo.produces else []
                    produces_str = ", ".join(produces) if produces else "Value"

                    lines.append(f"  [{ui_colors.GOLD}]\u26A1[/] {cards_str}")
                    lines.append(f"     [{ui_colors.TEXT_DIM}]\u2192 {produces_str}[/]")
                else:
                    lines.append(f"  [{ui_colors.GOLD}]\u26A1[/] Combo {combo_id}")
        except ImportError:
            for combo_id in combo_ids:
                lines.append(f"  [{ui_colors.GOLD}]\u26A1[/] {combo_id}")
        return lines

    def _render_score_breakdown(self) -> str:
        """Render visual score breakdown with bars."""
        if not self._recommendation:
            return ""

        rec = self._recommendation
        components: list[tuple[str, float, str]] = []

        # Add non-zero scores
        if rec.tfidf_score > 0:
            components.append(("Text Similarity", rec.tfidf_score, ui_colors.GOLD))
        if rec.synergy_score > 0:
            components.append(("Synergy", rec.synergy_score, ui_colors.SYNERGY_STRONG))
        if rec.tribal_score > 0:
            components.append(("Tribal", rec.tribal_score, "#9370DB"))
        if rec.combo_score > 0:
            components.append(("Combo", rec.combo_score, "#FF6B6B"))
        if rec.limited_score > 0:
            components.append(("17lands", rec.limited_score, "#4ECDC4"))
        if rec.curve_score > 0:
            components.append(("Mana Curve", rec.curve_score, "#45B7D1"))
        if rec.popularity_score > 0:
            components.append(("Popularity", rec.popularity_score, "#96CEB4"))

        if not components:
            return f"  [{ui_colors.TEXT_DIM}]No detailed breakdown available[/]"

        lines = []
        max_label_len = max(len(c[0]) for c in components)

        for label, score, color in components:
            # Create bar (max 15 chars)
            bar_width = int(score * 15)
            bar = "\u2588" * bar_width + "\u2591" * (15 - bar_width)
            score_pct = int(score * 100)
            padded_label = label.ljust(max_label_len)
            lines.append(
                f"  {padded_label} [{color}]{bar}[/] [{ui_colors.TEXT_DIM}]{score_pct}%[/]"
            )

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

    def _get_tier_color(self, tier: str) -> str:
        """Get color for 17lands tier."""
        tier_colors = {
            "S": "#FFD700",
            "A": "#32CD32",
            "B": "#87CEEB",
            "C": "#FFFFFF",
            "D": "#FFA500",
            "F": "#FF4500",
        }
        return tier_colors.get(tier.upper(), ui_colors.TEXT_DIM)

    def _get_winrate_color(self, wr: float) -> str:
        """Get color for win rate."""
        if wr >= 0.60:
            return "#FFD700"
        elif wr >= 0.55:
            return "#32CD32"
        elif wr >= 0.50:
            return "#FFFFFF"
        elif wr >= 0.45:
            return "#FFA500"
        return "#FF4500"
