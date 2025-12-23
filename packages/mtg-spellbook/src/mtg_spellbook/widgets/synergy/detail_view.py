"""Synergy detail view widget for expanded synergy explanations."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import Static

from ...formatting import prettify_mana
from ...ui.theme import ui_colors
from .messages import SynergyDetailCollapse

if TYPE_CHECKING:
    from mtg_core.data.models.responses import CardDetail, SynergyResult


class SynergyDetailView(Vertical, can_focus=True):
    """Expanded detail view for a synergy showing full explanation."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape,e", "close", "Close", show=False),
    ]

    is_visible: reactive[bool] = reactive(False, toggle_class="visible")

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._synergy: SynergyResult | None = None
        self._source_card: CardDetail | None = None

    def compose(self) -> ComposeResult:
        yield Static(
            "",
            id="detail-header",
            classes="synergy-detail-header",
        )
        with VerticalScroll(id="detail-scroll", classes="synergy-detail-scroll"):
            yield Static(
                "",
                id="detail-content",
                classes="synergy-detail-content",
            )
        yield Static(
            self._render_hints(),
            id="detail-hints",
            classes="synergy-detail-hints",
        )

    def _render_hints(self) -> str:
        """Render keyboard hints."""
        return f"[{ui_colors.TEXT_DIM}]Press [/][{ui_colors.GOLD}]e[/] [{ui_colors.TEXT_DIM}]or[/] [{ui_colors.GOLD}]Esc[/] [{ui_colors.TEXT_DIM}]to close[/]"

    def show_synergy(
        self,
        synergy: SynergyResult,
        source_card: CardDetail | None = None,
    ) -> None:
        """Display synergy detail."""
        self._synergy = synergy
        self._source_card = source_card
        self.is_visible = True
        self._update_display()
        self.focus()

    def _update_display(self) -> None:
        """Update the detail display."""
        if not self._synergy:
            return

        syn = self._synergy

        # Update header
        try:
            header = self.query_one("#detail-header", Static)
            mana = prettify_mana(syn.mana_cost) if syn.mana_cost else ""
            score_pct = min(100, int(syn.score * 100))
            score_color = self._get_score_color(min(syn.score, 1.0))
            header.update(
                f"[bold {ui_colors.GOLD}]{syn.name}[/] {mana}  "
                f"[{score_color}]({score_pct}% match)[/]"
            )
        except NoMatches:
            pass

        # Update content
        try:
            content = self.query_one("#detail-content", Static)
            content.update(self._render_detail_content())
        except NoMatches:
            pass

    def _render_detail_content(self) -> str:
        """Render the full detail content."""
        if not self._synergy:
            return ""

        syn = self._synergy
        lines: list[str] = []

        # Type and reason
        type_display = syn.synergy_type.title()
        lines.append(f"[bold]Synergy Type:[/] [{ui_colors.GOLD}]{type_display}[/]")
        lines.append("")

        # Main reason
        lines.append("[bold]Why it synergizes:[/]")
        lines.append(f"  {syn.reason}")
        lines.append("")

        # Type line if available
        if syn.type_line:
            lines.append(f"[bold]Card Type:[/] [{ui_colors.TEXT_DIM}]{syn.type_line}[/]")
            lines.append("")

        # Explanation based on synergy type
        explanation = self._generate_explanation()
        if explanation:
            lines.append("[bold]How it works:[/]")
            for point in explanation:
                lines.append(f"  - {point}")
            lines.append("")

        # Score breakdown
        lines.append("[bold]Score Breakdown:[/]")
        lines.append(self._render_score_breakdown())
        lines.append("")

        # Source card interaction (if available)
        if self._source_card:
            interaction = self._analyze_interaction()
            if interaction:
                lines.append("[bold]Interaction Analysis:[/]")
                for point in interaction:
                    lines.append(f"  {point}")

        return "\n".join(lines)

    def _generate_explanation(self) -> list[str]:
        """Generate explanation points based on synergy type."""
        if not self._synergy:
            return []

        syn = self._synergy
        points: list[str] = []

        # Generate type-specific explanations
        if syn.synergy_type == "tribal":
            points.append("Both cards share a creature type, enabling tribal synergies")
            points.append("Tribal lords and type-matters effects work with both cards")

        elif syn.synergy_type == "keyword":
            points.append("These cards share or interact with the same keyword ability")
            points.append("Keyword synergies often create multiplicative value")

        elif syn.synergy_type == "ability":
            points.append("The abilities on these cards interact in powerful ways")
            points.append("Look for triggers that chain together for value")

        elif syn.synergy_type == "theme":
            points.append("These cards fit the same strategic theme")
            points.append("Building around this theme creates consistent synergies")

        elif syn.synergy_type == "archetype":
            points.append("Classic archetype pairing found in competitive decks")
            points.append("This synergy has proven effective in gameplay")

        elif syn.synergy_type == "combo":
            points.append("These cards combine to create a powerful effect")
            points.append("Look for win conditions or game-ending loops")

        return points

    def _render_score_breakdown(self) -> str:
        """Render the score breakdown."""
        if not self._synergy:
            return ""

        syn = self._synergy
        score = syn.score

        # Create visual breakdown
        match_bonus = score - 0.5

        # Adjust based on synergy type
        type_bonuses = {
            "tribal": 0.35,
            "keyword": 0.30,
            "ability": 0.25,
            "combo": 0.40,
            "theme": 0.20,
            "archetype": 0.15,
        }
        type_bonus = type_bonuses.get(syn.synergy_type, 0.15)

        lines = [
            f"  Base Score:     [{ui_colors.TEXT_DIM}]50%[/]",
            f"  Type Bonus:     [{ui_colors.SYNERGY_MODERATE}]+{int(type_bonus * 100)}%[/] ({syn.synergy_type})",
            f"  Match Quality:  [{ui_colors.SYNERGY_STRONG}]+{int(match_bonus * 100)}%[/]",
            f"  [bold]Total:[/]         [{self._get_score_color(score)}]{int(score * 100)}%[/]",
        ]

        return "\n".join(lines)

    def _analyze_interaction(self) -> list[str]:
        """Analyze specific interaction between source and synergy card."""
        if not self._synergy or not self._source_card:
            return []

        points: list[str] = []
        source = self._source_card

        # Basic interaction analysis
        if source.text and "enters the battlefield" in source.text.lower():
            points.append("Source card has ETB effect that may be enhanced")

        if source.text and "create" in source.text.lower() and "token" in source.text.lower():
            points.append("Token creation synergies are possible")

        if source.keywords:
            for kw in source.keywords[:3]:
                points.append(f"'{kw}' keyword may interact with synergy card")

        return points

    def _get_score_color(self, score: float) -> str:
        """Get color for score display."""
        if score >= 0.8:
            return ui_colors.SYNERGY_STRONG
        elif score >= 0.6:
            return ui_colors.SYNERGY_MODERATE
        elif score >= 0.4:
            return ui_colors.SYNERGY_WEAK
        return ui_colors.TEXT_DIM

    def action_close(self) -> None:
        """Close the detail view."""
        self.is_visible = False
        self.post_message(SynergyDetailCollapse())

    def watch_is_visible(self, visible: bool) -> None:
        """Update display state when visibility changes."""
        self.display = visible
