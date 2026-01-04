"""Recommendation detail view for 'Why this card?' explanations."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from ..formatting import prettify_mana
from ..ui.theme import ui_colors

if TYPE_CHECKING:
    from mtg_core.tools.recommendations.hybrid import ScoredRecommendation


class RecommendationDetailCollapse(Message):
    """Posted when the recommendation detail view is collapsed."""

    pass


class RecommendationDetailView(Vertical, can_focus=False):
    """Expanded detail view for a recommendation showing scoring breakdown."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape,e", "close", "Close", show=False),
    ]

    DEFAULT_CSS = """
    RecommendationDetailView {
        width: 100%;
        height: auto;
        max-height: 24;
        background: #0a0a14;
        border: solid #c9a227;
        padding: 1;
        display: none;
    }

    RecommendationDetailView.visible {
        display: block;
    }

    .rec-detail-header {
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
    }

    .rec-detail-scroll {
        height: 1fr;
        max-height: 18;
    }

    .rec-detail-content {
        height: auto;
        padding: 0 1;
    }

    .rec-detail-hints {
        height: auto;
        padding: 0 1;
        margin-top: 1;
    }
    """

    is_visible: reactive[bool] = reactive(False, toggle_class="visible")

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._recommendation: ScoredRecommendation | None = None

    def compose(self) -> ComposeResult:
        yield Static("", id="rec-detail-header", classes="rec-detail-header")
        with VerticalScroll(id="rec-detail-scroll", classes="rec-detail-scroll"):
            yield Static("", id="rec-detail-content", classes="rec-detail-content")
        yield Static(
            self._render_hints(),
            id="rec-detail-hints",
            classes="rec-detail-hints",
        )

    def _render_hints(self) -> str:
        """Render keyboard hints."""
        return (
            f"[{ui_colors.TEXT_DIM}]Press [/][{ui_colors.GOLD}]e[/] "
            f"[{ui_colors.TEXT_DIM}]or[/] [{ui_colors.GOLD}]Esc[/] "
            f"[{ui_colors.TEXT_DIM}]to close[/]"
        )

    async def show_recommendation(self, rec: ScoredRecommendation) -> None:
        """Display recommendation detail."""
        self._recommendation = rec
        self.is_visible = True
        await self._update_display()
        self.focus()

    async def _update_display(self) -> None:
        """Update the detail display."""
        if not self._recommendation:
            return

        rec = self._recommendation

        # Update header
        try:
            header = self.query_one("#rec-detail-header", Static)
            mana = prettify_mana(rec.mana_cost) if rec.mana_cost else ""
            score_pct = min(100, int(rec.total_score * 100))
            score_color = self._get_score_color(min(rec.total_score, 1.0))
            header.update(
                f"[bold {ui_colors.GOLD}]{rec.name}[/] {mana}  "
                f"[{score_color}]({score_pct}% match)[/]"
            )
        except NoMatches:
            pass

        # Update content
        try:
            content = self.query_one("#rec-detail-content", Static)
            content.update(await self._render_detail_content())
        except NoMatches:
            pass

    async def _render_detail_content(self) -> str:
        """Render the full detail content."""
        if not self._recommendation:
            return ""

        rec = self._recommendation
        lines: list[str] = []

        # Type line
        if rec.type_line:
            lines.append(f"[{ui_colors.TEXT_DIM}]{rec.type_line}[/]")
            lines.append("")

        # Score breakdown with visual bars
        lines.append("[bold]Score Breakdown:[/]")
        lines.append(self._render_score_breakdown())
        lines.append("")

        # Why this card? (all reasons)
        if rec.reasons:
            lines.append("[bold]Why this card?[/]")
            for reason in rec.reasons:
                lines.append(f"  [green]•[/] {reason}")
            lines.append("")

        # Combos it completes
        if rec.completes_combos:
            lines.append("[bold]Completes Combos:[/]")
            lines.extend(await self._render_combos(rec.completes_combos[:5]))
            if len(rec.completes_combos) > 5:
                lines.append(
                    f"  [{ui_colors.TEXT_DIM}]...and {len(rec.completes_combos) - 5} more[/]"
                )
            lines.append("")

        # 17lands data
        if rec.limited_tier or rec.limited_gih_wr:
            lines.append("[bold]Limited Performance:[/]")
            if rec.limited_tier:
                tier_color = self._get_tier_color(rec.limited_tier)
                tier_desc = self._get_tier_description(rec.limited_tier)
                lines.append(f"  Tier: [{tier_color}]{rec.limited_tier}[/] - {tier_desc}")
            if rec.limited_gih_wr:
                wr_color = self._get_winrate_color(rec.limited_gih_wr)
                lines.append(f"  Win Rate (GIH): [{wr_color}]{rec.limited_gih_wr:.1%}[/]")
            lines.append("")

        # Additional insights
        insights = self._generate_insights()
        if insights:
            lines.append("[bold]Additional Insights:[/]")
            for insight in insights:
                lines.append(f"  {insight}")

        return "\n".join(lines)

    def _generate_insights(self) -> list[str]:
        """Generate rich additional insights based on score components."""
        if not self._recommendation:
            return []

        rec = self._recommendation
        insights: list[str] = []

        # Text similarity insight
        if rec.tfidf_score >= 0.5:
            insights.append(f"🎯 [bold]High text match[/] ({int(rec.tfidf_score * 100)}%)")
        elif rec.tfidf_score >= 0.3:
            insights.append(f"📝 Text similarity {int(rec.tfidf_score * 100)}%")

        # Synergy insight
        if rec.synergy_score >= 0.7:
            insights.append("⚡ [bold]Elite synergy[/] with deck themes")
        elif rec.synergy_score >= 0.5:
            insights.append("🔗 Strong mechanical synergy")
        elif rec.synergy_score >= 0.3:
            insights.append("↗ Moderate synergy")

        # Popularity insight
        if rec.popularity_score >= 0.9:
            insights.append("🏆 [bold]Format staple[/] - top 10%")
        elif rec.popularity_score >= 0.7:
            insights.append("📈 Very popular - top 30%")

        # Combo insight
        if rec.combo_score >= 0.7:
            combo_count = len(rec.completes_combos)
            if combo_count > 1:
                insights.append(f"💥 [bold]Combo piece[/] - {combo_count} combos!")
            else:
                insights.append("💥 [bold]Combo enabler[/]")
        elif rec.combo_score >= 0.3:
            insights.append("🔄 Enables powerful interactions")

        # Curve insight
        if rec.curve_score >= 0.7:
            insights.append("📊 [bold]Perfect curve fit[/]")
        elif rec.curve_score >= 0.4:
            insights.append("📉 Smooths mana curve")

        # Tribal insight
        if rec.tribal_score >= 0.8:
            insights.append("👥 [bold]Tribal all-star[/]")
        elif rec.tribal_score >= 0.5:
            insights.append("🦎 Tribal synergy")

        # Limited insight
        if rec.limited_gih_wr and rec.limited_gih_wr >= 0.58:
            delta = (rec.limited_gih_wr - 0.50) * 100
            insights.append(f"🎮 [bold]Limited bomb[/] (+{delta:.0f}% WR)")

        # Card type insights
        if rec.type_line:
            if "Legendary" in rec.type_line and "Creature" in rec.type_line:
                insights.append("👑 Legendary - clone/copy target")
            elif "Planeswalker" in rec.type_line:
                insights.append("⭐ Planeswalker - high threat")

        # Land insight
        if rec.land_score >= 1.0:
            insights.append("🌍 [bold]Critical mana fix[/]")
        elif rec.land_score >= 0.5:
            insights.append("🏔 Improves color consistency")

        # Collection insight
        if rec.in_collection:
            insights.append("✅ [green]Already owned![/]")

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

    async def _render_combos(self, combo_ids: list[str]) -> list[str]:
        """Render combo info with human-readable names."""
        lines: list[str] = []
        try:
            from mtg_core.tools.recommendations.spellbook_combos import (
                get_spellbook_detector,
            )

            detector = await get_spellbook_detector()
            for combo_id in combo_ids:
                combo = await detector.get_combo(combo_id)
                if combo:
                    # Show card names (truncate if too many)
                    card_names = combo.card_names[:3]
                    cards_str = " + ".join(card_names)
                    if len(combo.card_names) > 3:
                        cards_str += f" +{len(combo.card_names) - 3} more"

                    # Show what it produces
                    produces = combo.produces[:2] if combo.produces else []
                    produces_str = ", ".join(produces) if produces else "Value"

                    lines.append(f"  [{ui_colors.GOLD}]⚡[/] {cards_str}")
                    lines.append(f"     [{ui_colors.TEXT_DIM}]→ {produces_str}[/]")
                else:
                    lines.append(f"  [{ui_colors.GOLD}]⚡[/] Combo {combo_id}")
        except ImportError:
            for combo_id in combo_ids:
                lines.append(f"  [{ui_colors.GOLD}]⚡[/] {combo_id}")
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
            components.append(("Tribal", rec.tribal_score, "#9370DB"))  # Purple
        if rec.combo_score > 0:
            components.append(("Combo", rec.combo_score, "#FF6B6B"))  # Red
        if rec.limited_score > 0:
            components.append(("Gameplay", rec.limited_score, "#4ECDC4"))  # Teal
        if rec.curve_score > 0:
            components.append(("Mana Curve", rec.curve_score, "#45B7D1"))  # Blue
        if rec.popularity_score > 0:
            components.append(("Popularity", rec.popularity_score, "#96CEB4"))  # Green

        if not components:
            return f"  [{ui_colors.TEXT_DIM}]No detailed breakdown available[/]"

        lines = []
        max_label_len = max(len(c[0]) for c in components)

        for label, score, color in components:
            # Create bar (max 15 chars, capped at 100%)
            bar_width = min(15, int(score * 15))
            bar = "█" * bar_width + "░" * (15 - bar_width)
            score_pct = min(100, int(score * 100))
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
            "S": "#FFD700",  # Gold
            "A": "#32CD32",  # Green
            "B": "#87CEEB",  # Light blue
            "C": "#FFFFFF",  # White
            "D": "#FFA500",  # Orange
            "F": "#FF4500",  # Red
        }
        return tier_colors.get(tier.upper(), ui_colors.TEXT_DIM)

    def _get_winrate_color(self, wr: float) -> str:
        """Get color for win rate."""
        if wr >= 0.60:
            return "#FFD700"  # Gold (exceptional)
        elif wr >= 0.55:
            return "#32CD32"  # Green (great)
        elif wr >= 0.50:
            return "#FFFFFF"  # White (good)
        elif wr >= 0.45:
            return "#FFA500"  # Orange (below average)
        return "#FF4500"  # Red (poor)

    def action_close(self) -> None:
        """Close the detail view."""
        self.is_visible = False
        self.post_message(RecommendationDetailCollapse())

    def watch_is_visible(self, visible: bool) -> None:
        """Update display state and focus when visibility changes."""
        self.display = visible
        # Prevent capturing focus when hidden
        self.can_focus = visible
