"""Set insights panel showing value, mechanics, tribal themes, and type distribution."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widgets import Static

from ..ui.styled_sections import (
    divider,
    icons,
    key_value_padded,
    numbered_item,
    percentage_display,
    price_display,
    progress_bar,
    section_header,
    stat_row,
    tier_badge,
    two_column_stats,
)
from ..ui.theme import ui_colors

if TYPE_CHECKING:
    from mtg_core.tools.set_analysis import SetAnalysis


class SetInsightsPanel(ScrollableContainer):
    """Scrollable panel showing set analysis insights.

    Displays:
    - Set value summary (total, top cards)
    - Featured mechanics with descriptions
    - Tribal/creature type themes
    - Type and rarity distribution
    """

    DEFAULT_CSS = """
    SetInsightsPanel {
        width: 100%;
        height: 100%;
        background: #0d0d0d;
        padding: 1;
        scrollbar-color: #c9a227;
        scrollbar-color-hover: #e6c84a;
    }

    .insights-content {
        width: 100%;
        height: auto;
    }

    .insight-section {
        width: 100%;
        height: auto;
        margin-bottom: 1;
        padding: 0 1;
    }

    .section-header {
        height: auto;
        margin-bottom: 1;
    }

    .section-content {
        height: auto;
    }

    .insight-empty {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: #666;
    }
    """

    analysis: reactive[SetAnalysis | None] = reactive(None)

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._expanded_sections: set[str] = {"value", "mechanics", "tribal"}

    def compose(self) -> ComposeResult:
        yield Static(
            f"[{ui_colors.TEXT_DIM}]Select a set to view insights[/]",
            id="insights-empty",
            classes="insight-empty",
        )

    def update_analysis(self, analysis: SetAnalysis | None) -> None:
        """Update the panel with new analysis data."""
        self.analysis = analysis
        self._refresh_display()

    def _refresh_display(self) -> None:
        """Refresh the display with current analysis."""
        # Clear existing content
        for child in list(self.children):
            child.remove()

        if not self.analysis:
            self.mount(
                Static(
                    f"[{ui_colors.TEXT_DIM}]Select a set to view insights[/]",
                    id="insights-empty",
                    classes="insight-empty",
                )
            )
            return

        # Build content
        content = Vertical(classes="insights-content")
        self.mount(content)

        # Add sections
        content.mount(self._build_value_section())
        content.mount(self._build_limited_section())
        content.mount(self._build_mechanics_section())
        content.mount(self._build_tribal_section())
        content.mount(self._build_composition_section())

    def _build_value_section(self) -> Static:
        """Build the set value section."""
        if not self.analysis:
            return Static("")

        vs = self.analysis.value_summary
        lines = [
            section_header("Set Value", icons.VALUE),
            "",
        ]

        # Summary stats - show both regular and foil totals
        lines.append(key_value_padded("Regular", f"${vs.total_value:,.2f}", 16))
        lines.append(key_value_padded("With Foils", f"${vs.total_value_foil:,.2f} ✦", 16))
        lines.append(key_value_padded("Average Card", f"${vs.average_value:.2f}", 16))
        lines.append(key_value_padded("Median Card", f"${vs.median_value:.2f}", 16))
        lines.append(key_value_padded("Top 5", f"= {vs.top5_concentration:.0f}% of value", 16))
        lines.append("")

        # Price tier breakdown
        pt = vs.price_tiers
        total_cards = pt.bulk + pt.playable + pt.chase + pt.premium
        if total_cards > 0:
            lines.append("[bold]Price Tiers:[/]")
            lines.append(
                f"  [{ui_colors.TEXT_DIM}]Bulk     <$1[/]    {pt.bulk:>3}  "
                f"[dim]│[/]  [{ui_colors.GOLD}]Chase  $10-50[/]  {pt.chase:>3}"
            )
            lines.append(
                f"  [{ui_colors.TEXT_DIM}]Playable $1-10[/] {pt.playable:>3}  "
                f"[dim]│[/]  [bold {ui_colors.GOLD}]Premium  $50+[/]   {pt.premium:>3}"
            )
            lines.append("")

        # Top 5 valuable cards (shows best price - regular or foil)
        if vs.top_cards:
            lines.append("[bold]Top Valuable Cards:[/]")
            for i, (name, price, is_foil) in enumerate(vs.top_cards[:5], 1):
                foil_mark = f" [{ui_colors.GOLD}]✦[/]" if is_foil else ""
                lines.append(numbered_item(i, f"{name} {price_display(price)}{foil_mark}"))
            lines.append("")

        lines.append(divider(38))

        return Static("\n".join(lines), classes="insight-section")

    def _build_limited_section(self) -> Static:
        """Build the Limited tier list section."""
        if not self.analysis or not self.analysis.limited_stats:
            return Static("")

        ls = self.analysis.limited_stats
        if not ls.has_data:
            return Static("")

        lines = [
            section_header("Limited Tier List", icons.LIMITED),
            "",
        ]

        # S Tier
        if ls.s_tier:
            lines.append(f"{tier_badge('S')} [bold]Tier (60%+ WR)[/]")
            for card in ls.s_tier[:5]:
                lines.append(
                    f"  [{ui_colors.TIER_S}]★[/] {card.card_name[:24].ljust(24)} "
                    f"{percentage_display(card.gih_wr)}"
                )
            lines.append("")

        # A Tier
        if ls.a_tier:
            lines.append(f"{tier_badge('A')} [bold]Tier (57-60% WR)[/]")
            for card in ls.a_tier[:5]:
                lines.append(
                    f"  [{ui_colors.TIER_A}]◆[/] {card.card_name[:24].ljust(24)} "
                    f"{percentage_display(card.gih_wr)}"
                )
            if len(ls.a_tier) > 5:
                lines.append(f"  [{ui_colors.TEXT_DIM}]+{len(ls.a_tier) - 5} more[/]")
            lines.append("")

        # Summary of lower tiers
        tier_summary = []
        if ls.b_tier:
            tier_summary.append(f"B: {len(ls.b_tier)}")
        if ls.c_tier_count > 0:
            tier_summary.append(f"C: {ls.c_tier_count}")
        if ls.d_tier_count > 0:
            tier_summary.append(f"D: {ls.d_tier_count}")
        if ls.f_tier_count > 0:
            tier_summary.append(f"F: {ls.f_tier_count}")

        if tier_summary:
            lines.append(f"[{ui_colors.TEXT_DIM}]Lower tiers: {' | '.join(tier_summary)}[/]")
            lines.append("")

        lines.append(divider(38))

        return Static("\n".join(lines), classes="insight-section")

    def _build_mechanics_section(self) -> Static:
        """Build the mechanics section."""
        if not self.analysis:
            return Static("")

        mechanics = self.analysis.mechanics
        lines = [
            section_header("Featured Mechanics", icons.MECHANICS, len(mechanics)),
            "",
        ]

        if not mechanics:
            lines.append(f"[{ui_colors.TEXT_DIM}]No notable mechanics detected[/]")
        else:
            # Show top mechanics with descriptions
            for mech in mechanics[:8]:
                # Header with count
                lines.append(
                    f"[bold {ui_colors.GOLD}]{mech.name}[/] "
                    f"[{ui_colors.TEXT_DIM}]({mech.card_count} cards)[/]"
                )
                # Description
                lines.append(f"  [{ui_colors.TEXT_DIM}]{mech.description}[/]")
                # Top card example
                if mech.top_cards:
                    lines.append(f"  [dim]Example:[/] [{ui_colors.GOLD_DIM}]{mech.top_cards[0]}[/]")
                lines.append("")

        lines.append(divider(38))

        return Static("\n".join(lines), classes="insight-section")

    def _build_tribal_section(self) -> Static:
        """Build the tribal themes section."""
        if not self.analysis:
            return Static("")

        tribes = self.analysis.tribal_themes
        lines = [
            section_header("Tribal Themes", icons.TRIBAL, len(tribes)),
            "",
        ]

        if not tribes:
            lines.append(f"[{ui_colors.TEXT_DIM}]No significant tribal themes[/]")
        else:
            # Show top tribes with visual bars
            max_count = tribes[0].card_count if tribes else 1
            for tribe in tribes[:8]:
                pct = tribe.card_count / max_count
                bar = progress_bar(pct, 12, ui_colors.GOLD_DIM)
                lines.append(
                    f"  {tribe.creature_type.ljust(12)} {bar} "
                    f"[{ui_colors.TEXT_DIM}]{tribe.card_count} ({tribe.percentage:.0f}%)[/]"
                )

            if len(tribes) > 8:
                lines.append(f"  [{ui_colors.TEXT_DIM}]...and {len(tribes) - 8} more types[/]")

        lines.append("")
        lines.append(divider(38))

        return Static("\n".join(lines), classes="insight-section")

    def _build_composition_section(self) -> Static:
        """Build the type/rarity composition section."""
        if not self.analysis:
            return Static("")

        td = self.analysis.type_distribution
        rd = self.analysis.rarity_distribution

        lines = [
            section_header("Set Composition", icons.TYPES),
            "",
        ]

        # Two-column layout for types and rarities
        lines.append("[bold]Card Types[/]")
        lines.append(two_column_stats(("Creature", td.creatures), ("Instant", td.instants)))
        lines.append(two_column_stats(("Sorcery", td.sorceries), ("Enchant", td.enchantments)))
        lines.append(two_column_stats(("Artifact", td.artifacts), ("Land", td.lands)))
        if td.planeswalkers > 0 or td.battles > 0:
            lines.append(
                two_column_stats(("Planeswalker", td.planeswalkers), ("Battle", td.battles))
            )
        lines.append("")

        lines.append("[bold]Rarities[/]")
        lines.append(two_column_stats(("Mythic", rd.mythic), ("Rare", rd.rare)))
        lines.append(two_column_stats(("Uncommon", rd.uncommon), ("Common", rd.common)))
        if rd.special > 0:
            lines.append(stat_row("Special", rd.special))

        return Static("\n".join(lines), classes="insight-section")
