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

    def show_recommendation(self, rec: ScoredRecommendation, in_collection: bool = False) -> None:
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
            # Cap at 100% for display (total_score can exceed 1.0 due to land_score bonuses)
            score_pct = min(int(rec.total_score * 100), 100)
            score_color = self._get_score_color(min(rec.total_score, 1.0))
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
        """Render the full detail content with visual styling."""
        if not self._recommendation:
            return ""

        rec = self._recommendation
        lines: list[str] = []

        # Type line with subtle styling
        if rec.type_line:
            lines.append(f"[dim italic]{rec.type_line}[/]")
            lines.append("")

        # Collection status - styled as a pill badge
        if self._in_collection:
            lines.append("[bold green on #0d2818] ✓ IN COLLECTION [/]")
        else:
            lines.append("[dim]○ Not in collection[/]")
        lines.append("")

        # Score breakdown with visual bars - styled section
        lines.append(f"[bold {ui_colors.GOLD}]┌─ Score Breakdown ─────────────────┐[/]")
        lines.append(self._render_score_breakdown())
        lines.append(f"[{ui_colors.GOLD}]└───────────────────────────────────┘[/]")
        lines.append("")

        # Why this card? (all reasons from recommender)
        if rec.reasons:
            lines.append("[bold #BD93F9]┌─ Why This Card? ──────────────────┐[/]")
            for reason in rec.reasons:
                lines.append(f"[#BD93F9]│[/] [#50FA7B]▸[/] {reason}")
            lines.append("[#BD93F9]└───────────────────────────────────┘[/]")
            lines.append("")

        # Additional insights based on scores
        insights = self._generate_insights()
        if insights:
            lines.append("[bold #8BE9FD]┌─ Insights ────────────────────────┐[/]")
            for insight in insights:
                lines.append(f"[#8BE9FD]│[/] {insight}")
            lines.append("[#8BE9FD]└───────────────────────────────────┘[/]")
            lines.append("")

        # Combos it completes - highlighted section
        if rec.completes_combos:
            combo_count = len(rec.completes_combos)
            lines.append(f"[bold #FF6B6B]┌─ Completes {combo_count} Combo(s) ─────────────┐[/]")
            lines.extend(self._render_combos(rec.completes_combos[:5]))
            if len(rec.completes_combos) > 5:
                remaining = len(rec.completes_combos) - 5
                lines.append(f"[#FF6B6B]│[/] [dim]...and {remaining} more combos[/]")
            lines.append("[#FF6B6B]└───────────────────────────────────┘[/]")
            lines.append("")

        # 17lands data - styled section
        if rec.limited_tier or rec.limited_gih_wr:
            lines.append("[bold #4ECDC4]┌─ Limited Stats ───────────────────┐[/]")
            if rec.limited_tier:
                tier_color = self._get_tier_color(rec.limited_tier)
                tier_desc = self._get_tier_description(rec.limited_tier)
                lines.append(f"[#4ECDC4]│[/] [{tier_color}]★ Tier {rec.limited_tier}[/] [dim]{tier_desc}[/]")
            if rec.limited_gih_wr:
                wr_color = self._get_winrate_color(rec.limited_gih_wr)
                wr_desc = self._get_winrate_description(rec.limited_gih_wr)
                lines.append(f"[#4ECDC4]│[/] [{wr_color}]{rec.limited_gih_wr:.1%}[/] GIH Win Rate")
                lines.append(f"[#4ECDC4]│[/] [dim]{wr_desc}[/]")
            lines.append("[#4ECDC4]└───────────────────────────────────┘[/]")

        return "\n".join(lines)

    def _generate_insights(self) -> list[str]:
        """Generate rich additional insights based on score components."""
        if not self._recommendation:
            return []

        rec = self._recommendation
        insights: list[str] = []

        # Check if this is a basic/simple land (skip text/popularity insights for these)
        is_basic_land = rec.type_line and (
            "Basic Land" in rec.type_line
            or (
                "Land" in rec.type_line
                and rec.tfidf_score < 0.15  # Low text complexity = simple land
            )
        )

        # Text similarity insight with context (skip for basic lands)
        if not is_basic_land:
            if rec.tfidf_score >= 0.5:
                insights.append(
                    f"🎯 [bold]High text match[/] ({int(rec.tfidf_score * 100)}%) - "
                    "shares key abilities with your core cards"
                )
            elif rec.tfidf_score >= 0.3:
                insights.append(
                    f"📝 Text similarity {int(rec.tfidf_score * 100)}% - "
                    "mechanically related to your deck's effects"
                )

        # Synergy insight with specifics
        if rec.synergy_score >= 0.7:
            insights.append(
                "⚡ [bold]Elite synergy[/] - this card amplifies multiple deck strategies"
            )
        elif rec.synergy_score >= 0.5:
            insights.append(
                "🔗 Strong mechanical synergy with your deck's core themes"
            )
        elif rec.synergy_score >= 0.3:
            insights.append(
                "↗ Moderate synergy - supports your overall strategy"
            )

        # Popularity insight with percentile (skip for basic lands)
        if not is_basic_land:
            if rec.popularity_score >= 0.9:
                insights.append(
                    "🏆 [bold]Format staple[/] - top 10% most played in Commander"
                )
            elif rec.popularity_score >= 0.7:
                insights.append(
                    "📈 Very popular - top 30% on EDHRec for similar decks"
                )
            elif rec.popularity_score >= 0.5:
                insights.append(
                    "👍 Commonly played in decks with similar strategies"
                )

        # Enhanced combo insight
        if rec.combo_score >= 0.7:
            combo_count = len(rec.completes_combos)
            if combo_count > 1:
                insights.append(
                    f"💥 [bold]Combo powerhouse[/] - unlocks {combo_count} winning lines!"
                )
            else:
                insights.append(
                    "💥 [bold]Combo piece[/] - completes an infinite or game-winning combo"
                )
        elif rec.combo_score >= 0.3:
            insights.append(
                "🔄 Enables powerful interactions with cards you already run"
            )

        # Mana curve insight with CMC context
        if rec.curve_score >= 0.7:
            cmc = self._get_cmc_from_mana(rec.mana_cost) if rec.mana_cost else None
            if cmc is not None:
                insights.append(
                    f"📊 [bold]Curve filler[/] - your deck needs more {cmc}-drops"
                )
            else:
                insights.append(
                    "📊 [bold]Perfect curve fit[/] - fills a critical gap in your mana curve"
                )
        elif rec.curve_score >= 0.4:
            insights.append(
                "📉 Helps smooth out your mana curve distribution"
            )

        # Enhanced tribal insight
        if rec.tribal_score >= 0.8:
            insights.append(
                "👥 [bold]Tribal all-star[/] - shares creature types with your core tribe"
            )
        elif rec.tribal_score >= 0.5:
            insights.append(
                "🦎 Tribal synergy - benefits from your creature type lords/effects"
            )

        # Enhanced Limited insight with win rate context
        if rec.limited_gih_wr and rec.limited_gih_wr >= 0.58:
            delta = (rec.limited_gih_wr - 0.50) * 100
            insights.append(
                f"🎮 [bold]Limited bomb[/] - {rec.limited_gih_wr:.1%} win rate "
                f"(+{delta:.1f}% above average)"
            )
        elif rec.limited_score >= 0.7:
            insights.append(
                "🎮 Proven Limited performer - reliable in draft/sealed"
            )
        elif rec.limited_tier and rec.limited_tier in ("S", "A"):
            insights.append(
                f"🏅 Tier {rec.limited_tier} in Limited - high pick priority"
            )

        # Card type insights
        if rec.type_line:
            if "Creature" in rec.type_line and "Legendary" in rec.type_line:
                insights.append(
                    "👑 Legendary creature - potential commander or clone target"
                )
            elif "Planeswalker" in rec.type_line:
                insights.append(
                    "⭐ Planeswalker - high value threat that demands answers"
                )
            elif "Artifact" in rec.type_line and "Equipment" in rec.type_line:
                insights.append(
                    "⚔️ Equipment - reusable value that survives creature removal"
                )

        # Land insight
        if rec.land_score > 0:
            if rec.land_score >= 1.0:
                insights.append(
                    "🌍 [bold]Critical mana fix[/] - your deck urgently needs more lands"
                )
            elif rec.land_score >= 0.5:
                insights.append(
                    "🏔 Mana upgrade - improves color consistency"
                )

        # Collection insight
        if rec.in_collection:
            insights.append(
                "✅ [green]Already owned[/] - no acquisition needed!"
            )

        return insights

    def _get_cmc_from_mana(self, mana_cost: str) -> int | None:
        """Extract CMC from mana cost string."""
        if not mana_cost:
            return None
        # Simple CMC calculation - count mana symbols
        import re
        symbols = re.findall(r'\{([^}]+)\}', mana_cost)
        cmc = 0
        for sym in symbols:
            if sym.isdigit():
                cmc += int(sym)
            elif sym not in ('X', 'Y', 'Z'):
                cmc += 1
        return cmc

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
            for i, combo_id in enumerate(combo_ids):
                combo = detector.get_combo(combo_id)
                if combo:
                    # Show card names (truncate if too many)
                    card_names = combo.card_names[:3]
                    cards_str = " [dim]+[/] ".join(
                        f"[#FFB86C]{name}[/]" for name in card_names
                    )
                    if len(combo.card_names) > 3:
                        cards_str += f" [dim]+{len(combo.card_names) - 3} more[/]"

                    # Show what it produces with emphasis
                    produces = combo.produces[:2] if combo.produces else []
                    produces_str = ", ".join(produces) if produces else "Value"

                    lines.append(f"[#FF6B6B]│[/] [#FF6B6B]⚡[/] {cards_str}")
                    lines.append(f"[#FF6B6B]│[/]   [dim]→[/] [italic #50FA7B]{produces_str}[/]")
                    # Add separator between combos (not after last)
                    if i < len(combo_ids) - 1:
                        lines.append("[#FF6B6B]│[/]")
                else:
                    lines.append(f"[#FF6B6B]│[/] [#FF6B6B]⚡[/] Combo {combo_id}")
        except ImportError:
            for combo_id in combo_ids:
                lines.append(f"[#FF6B6B]│[/] [#FF6B6B]⚡[/] {combo_id}")
        return lines

    def _render_score_breakdown(self) -> str:
        """Render visual score breakdown with bars."""
        if not self._recommendation:
            return ""

        rec = self._recommendation
        components: list[tuple[str, float, str]] = []

        # Add non-zero scores with icons
        if rec.tfidf_score > 0:
            components.append(("📝 Text", rec.tfidf_score, ui_colors.GOLD))
        if rec.synergy_score > 0:
            components.append(("🔗 Synergy", rec.synergy_score, ui_colors.SYNERGY_STRONG))
        if rec.tribal_score > 0:
            components.append(("👥 Tribal", rec.tribal_score, "#9370DB"))
        if rec.combo_score > 0:
            components.append(("⚡ Combo", rec.combo_score, "#FF6B6B"))
        if rec.limited_score > 0:
            components.append(("🎮 Gameplay", rec.limited_score, "#4ECDC4"))
        if rec.curve_score > 0:
            components.append(("📊 Curve", rec.curve_score, "#45B7D1"))
        if rec.popularity_score > 0:
            components.append(("📈 Popular", rec.popularity_score, "#96CEB4"))
        if rec.land_score > 0:
            components.append(("🌍 Mana", rec.land_score, "#8BE9FD"))

        if not components:
            return f"[{ui_colors.GOLD}]│[/] [dim]No detailed breakdown available[/]"

        lines = []
        max_label_len = max(len(c[0]) for c in components)

        for label, score, color in components:
            # Create bar (max 12 chars to fit in box)
            # Cap score at 1.0 for display (land_score can exceed 1.0)
            capped_score = min(score, 1.0)
            bar_width = int(capped_score * 12)
            filled = "█" * bar_width
            empty = "░" * (12 - bar_width)
            score_pct = min(int(score * 100), 100)
            padded_label = label.ljust(max_label_len)
            lines.append(
                f"[{ui_colors.GOLD}]│[/] {padded_label} [{color}]{filled}[/][dim]{empty}[/] [{color}]{score_pct:>3}%[/]"
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
