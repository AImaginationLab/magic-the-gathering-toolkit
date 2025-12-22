"""Comprehensive deck analysis panel with combos, themes, and stats."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static

from ..ui.theme import ui_colors

if TYPE_CHECKING:
    from mtg_core.tools.recommendations.spellbook_combos import SpellbookComboMatch

    from ..deck_manager import DeckWithCards


# Mana colors
MANA = {
    "W": "#F8E7B9",
    "U": "#0E86D4",
    "B": "#9B7BB8",
    "R": "#E86A58",
    "G": "#7EC850",
    "C": "#95A5A6",
}


@dataclass
class DeckAnalysis:
    """Complete deck analysis results."""

    # Basic stats
    card_count: int
    land_count: int
    avg_cmc: float
    colors: dict[str, int]  # color -> pip count

    # Type breakdown
    creatures: int
    instants: int
    sorceries: int
    artifacts: int
    enchantments: int
    planeswalkers: int
    lands: int

    # Deck health
    interaction_count: int
    draw_count: int
    ramp_count: int

    # Theme detection
    archetype: str
    archetype_confidence: int
    dominant_themes: list[str]
    dominant_tribe: str | None
    keywords: list[tuple[str, int]]  # keyword -> count

    # Combos
    combos: list[SpellbookComboMatch]

    # 17Lands tiers
    tier_counts: dict[str, int]  # S/A/B/C/D/F -> count
    top_cards: list[tuple[str, str, float | None]]  # name, tier, gih_wr

    # Collection
    owned_count: int
    needed_count: int

    # Price
    total_price: float
    expensive_cards: list[tuple[str, float]]


class DeckAnalysisPanel(VerticalScroll):
    """Full deck analysis panel showing combos, themes, stats.

    This panel provides comprehensive deck insights:
    - Overview with archetype detection
    - Mana curve and color distribution
    - Detected combos from Commander Spellbook
    - 17Lands card ratings
    - Collection coverage
    - Deck health metrics
    """

    DEFAULT_CSS = """
    DeckAnalysisPanel {
        width: 100%;
        height: 100%;
        background: #0d0d0d;
        scrollbar-color: #c9a227;
    }

    DeckAnalysisPanel .section-header {
        width: 100%;
        height: 2;
        background: #151520;
        padding: 0 1;
        text-style: bold;
        border-bottom: solid #2a2a4e;
    }

    DeckAnalysisPanel .section-content {
        padding: 1;
        height: auto;
    }

    DeckAnalysisPanel .stat-row {
        height: auto;
    }

    DeckAnalysisPanel #analysis-empty {
        width: 100%;
        height: 100%;
        content-align: center middle;
    }
    """

    TIER_COLORS: ClassVar[dict[str, str]] = {
        "S": "#FFD700",  # Gold
        "A": "#7EC850",  # Green
        "B": "#4A9FD8",  # Blue
        "C": "#A0A0A0",  # Gray
        "D": "#E86A58",  # Red
        "F": "#9B4D4D",  # Dark red
    }

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._analysis: DeckAnalysis | None = None
        self._deck: DeckWithCards | None = None

    def compose(self) -> ComposeResult:
        yield Static(
            "[dim]Select a deck to view analysis[/]",
            id="analysis-empty",
        )

    def update_analysis(
        self,
        deck: DeckWithCards | None,
        collection_cards: set[str] | None = None,
        prices: dict[str, float] | None = None,
    ) -> None:
        """Analyze deck and update display."""
        self._deck = deck

        if deck is None or deck.mainboard_count == 0:
            self._show_empty()
            return

        # Perform analysis
        self._analysis = self._analyze_deck(deck, collection_cards, prices)

        # Rebuild display
        self._rebuild_display()

    def _show_empty(self) -> None:
        """Show empty state."""
        # Check if already showing empty state
        try:
            self.query_one("#analysis-empty", Static)
            # Already showing empty state
            return
        except Exception:
            pass

        # Remove any existing children and show empty state
        self.remove_children()
        self.mount(
            Static(
                "[dim]Select a deck to view analysis[/]",
                id="analysis-empty",
            )
        )

    def _analyze_deck(
        self,
        deck: DeckWithCards,
        collection_cards: set[str] | None = None,
        prices: dict[str, float] | None = None,
    ) -> DeckAnalysis:
        """Perform complete deck analysis."""
        prices = prices or {}
        collection_cards = collection_cards or set()

        # Basic stats
        card_count = deck.mainboard_count
        colors = self._calc_colors(deck)
        avg_cmc = self._calc_avg_cmc(deck)

        # Type counts
        types = self._calc_types(deck)
        creatures = types.get("Creature", 0)
        instants = types.get("Instant", 0)
        sorceries = types.get("Sorcery", 0)
        artifacts = types.get("Artifact", 0)
        enchantments = types.get("Enchantment", 0)
        planeswalkers = types.get("Planeswalker", 0)
        lands = types.get("Land", 0)

        # Deck health
        interaction = self._count_interaction(deck)
        draw = self._count_draw(deck)
        ramp = self._count_ramp(deck)

        # Theme detection
        archetype, conf = self._detect_archetype(deck, types, avg_cmc, interaction, draw)
        themes = self._detect_themes(deck)
        tribe = self._detect_tribe(deck)
        keywords = self._count_keywords(deck)

        # Combo detection
        combos = self._detect_combos(deck)

        # 17Lands tiers
        tier_counts, top_cards = self._get_17lands_stats(deck)

        # Collection coverage
        owned_count = sum(1 for c in deck.mainboard if c.card_name in collection_cards)
        needed_count = card_count - owned_count if collection_cards else 0

        # Price
        total_price = 0.0
        expensive: list[tuple[str, float]] = []
        for card in deck.mainboard:
            price = prices.get(card.card_name, 0.0)
            card_total = price * card.quantity
            total_price += card_total
            if price > 1.0:
                expensive.append((card.card_name, price))
        expensive.sort(key=lambda x: -x[1])

        return DeckAnalysis(
            card_count=card_count,
            land_count=lands,
            avg_cmc=avg_cmc,
            colors=colors,
            creatures=creatures,
            instants=instants,
            sorceries=sorceries,
            artifacts=artifacts,
            enchantments=enchantments,
            planeswalkers=planeswalkers,
            lands=lands,
            interaction_count=interaction,
            draw_count=draw,
            ramp_count=ramp,
            archetype=archetype,
            archetype_confidence=conf,
            dominant_themes=themes,
            dominant_tribe=tribe,
            keywords=keywords,
            combos=combos,
            tier_counts=tier_counts,
            top_cards=top_cards,
            owned_count=owned_count,
            needed_count=needed_count,
            total_price=total_price,
            expensive_cards=expensive[:5],
        )

    def _rebuild_display(self) -> None:
        """Rebuild the analysis display."""
        self.remove_children()

        if not self._analysis or not self._deck:
            self._show_empty()
            return

        a = self._analysis
        deck = self._deck

        # Overview section
        self.mount(self._build_overview_section(a, deck))

        # Mana curve section
        self.mount(self._build_curve_section(a, deck))

        # Colors section
        self.mount(self._build_colors_section(a))

        # Combos section (if any found)
        if a.combos:
            self.mount(self._build_combos_section(a))

        # 17Lands section (if data available)
        if a.tier_counts:
            self.mount(self._build_17lands_section(a))

        # Themes section
        if a.dominant_themes or a.dominant_tribe:
            self.mount(self._build_themes_section(a))

        # Health metrics
        self.mount(self._build_health_section(a, deck))

        # Collection section (if relevant)
        if a.needed_count > 0 or a.owned_count > 0:
            self.mount(self._build_collection_section(a))

        # Price section
        if a.total_price > 0:
            self.mount(self._build_price_section(a))

    def _build_overview_section(self, a: DeckAnalysis, deck: DeckWithCards) -> Vertical:
        """Build overview section."""
        # Deck score
        score = self._calc_score(a, deck)
        score_color = "#7ec850" if score >= 80 else "#e6c84a" if score >= 60 else "#e86a58"
        grade = (
            "S"
            if score >= 90
            else "A"
            if score >= 80
            else "B"
            if score >= 65
            else "C"
            if score >= 50
            else "D"
        )

        # Format check
        fmt = deck.format or "casual"
        expected = 99 if fmt.lower() == "commander" else 60
        count_ok = a.card_count >= expected

        # Commander
        commander_line = ""
        if deck.commander:
            commander_line = f"\n[dim]Commander:[/] [{ui_colors.GOLD}]{deck.commander}[/]"

        content = f"""[bold {ui_colors.GOLD}]{deck.name}[/]{commander_line}
[{a.archetype}] [{ui_colors.GOLD_DIM}]{a.archetype_confidence}% conf[/]

[{score_color}]{grade}[/] [{score_color}]{score}[/]/100 {"[green]✓[/]" if count_ok else "[red]✗[/]"} {a.card_count}/{expected} cards"""

        section = Vertical()
        section.compose_add_child(
            Static(f"[{ui_colors.GOLD}]OVERVIEW[/]", classes="section-header")
        )
        section.compose_add_child(Static(content, classes="section-content"))
        return section

    def _build_curve_section(self, a: DeckAnalysis, deck: DeckWithCards) -> Vertical:
        """Build mana curve section with visual bars."""
        curve = self._calc_curve(deck)
        max_count = max(curve.values()) if curve else 1
        total_spells = a.card_count - a.lands

        # Sparkline
        blocks = " ▁▂▃▄▅▆▇█"
        sparkline = ""
        for cmc in range(8):
            count = curve.get(cmc, 0)
            level = int((count / max_count) * 8) if max_count > 0 else 0
            char = blocks[level]
            if level > 0:
                sparkline += f"[{ui_colors.GOLD}]{char}[/]"
            else:
                sparkline += f"[dim]{char}[/]"

        # Average CMC color coding
        cmc_color = "#7ec850" if a.avg_cmc <= 2.5 else "#e6c84a" if a.avg_cmc <= 3.5 else "#e86a58"

        # Detailed breakdown
        counts = " ".join(f"{curve.get(i, 0):>2}" for i in range(8))

        content = f"""{sparkline}
[dim]0  1  2  3  4  5  6 7+[/]
{counts}

[dim]Average:[/] [{cmc_color}]{a.avg_cmc:.2f}[/] CMC
[dim]Spells:[/] {total_spells} non-land"""

        section = Vertical()
        section.compose_add_child(
            Static(f"[{ui_colors.GOLD}]MANA CURVE[/]", classes="section-header")
        )
        section.compose_add_child(Static(content, classes="section-content"))
        return section

    def _build_colors_section(self, a: DeckAnalysis) -> Vertical:
        """Build color distribution section."""
        total = sum(a.colors.values()) if a.colors else 1
        lines = []

        for c in ["W", "U", "B", "R", "G"]:
            count = a.colors.get(c, 0)
            if count == 0:
                continue
            pct = int((count / total) * 100) if total > 0 else 0
            bar_len = max(1, min(8, int((count / total) * 8))) if total > 0 else 0
            bar = f"[{MANA[c]}]{'█' * bar_len}[/][dim]{'░' * (8 - bar_len)}[/]"
            lines.append(f"[{MANA[c]}]{c}[/] {bar} {pct:>2}% ({count})")

        if not lines:
            lines.append("[dim]Colorless deck[/]")

        # Color identity display
        identity = "".join(c for c in "WUBRG" if a.colors.get(c, 0) > 0) or "C"
        id_display = " ".join(f"[{MANA.get(c, '#888')}]●[/]" for c in identity)
        lines.append(f"\n[dim]Identity:[/] {id_display}")

        section = Vertical()
        section.compose_add_child(Static(f"[{ui_colors.GOLD}]COLORS[/]", classes="section-header"))
        section.compose_add_child(Static("\n".join(lines), classes="section-content"))
        return section

    def _build_combos_section(self, a: DeckAnalysis) -> Vertical:
        """Build combos section showing detected combos."""
        lines = []

        # Count by completeness
        complete = [c for c in a.combos if c.is_complete]
        partial = [c for c in a.combos if not c.is_complete]

        if complete:
            lines.append(f"[green]✓ {len(complete)} COMPLETE[/]")
            for match in complete[:3]:
                combo = match.combo
                # What it produces
                produces = ", ".join(combo.produces[:2]) if combo.produces else "combo"
                lines.append(f"  [bold]{combo.card_names[0]}[/] +{len(combo.card_names) - 1}")
                lines.append(f"  [dim]→ {produces}[/]")

        if partial:
            lines.append(f"\n[yellow]⚠ {len(partial)} NEAR-COMPLETE[/]")
            for match in partial[:3]:
                combo = match.combo
                missing = ", ".join(match.missing_cards[:2])
                pct = int(match.completion_ratio * 100)
                lines.append(
                    f"  [{ui_colors.GOLD_DIM}]{pct}%[/] {combo.card_names[0]} +{len(combo.card_names) - 1}"
                )
                lines.append(f"  [dim]Need: {missing}[/]")

        section = Vertical()
        section.compose_add_child(
            Static(f"[{ui_colors.GOLD}]⚡ COMBOS ({len(a.combos)})[/]", classes="section-header")
        )
        section.compose_add_child(Static("\n".join(lines), classes="section-content"))
        return section

    def _build_17lands_section(self, a: DeckAnalysis) -> Vertical:
        """Build 17lands tier ratings section."""
        lines = []

        # Tier summary
        tier_order = ["S", "A", "B", "C", "D", "F"]
        tier_summary = []
        for tier in tier_order:
            count = a.tier_counts.get(tier, 0)
            if count > 0:
                color = self.TIER_COLORS.get(tier, "#888")
                tier_summary.append(f"[{color}]{tier}:{count}[/]")

        if tier_summary:
            lines.append("  ".join(tier_summary))
            lines.append("")

        # Top cards by tier
        lines.append("[dim]Top performers:[/]")
        for name, tier, gih_wr in a.top_cards[:5]:
            color = self.TIER_COLORS.get(tier, "#888")
            short_name = name[:18] if len(name) > 18 else name
            wr_str = f"{gih_wr:.0%}" if gih_wr else "N/A"
            lines.append(f"[{color}]★ {tier}[/] {short_name} [{ui_colors.GOLD_DIM}]{wr_str}[/]")

        section = Vertical()
        section.compose_add_child(
            Static(f"[{ui_colors.GOLD}]📊 17LANDS DATA[/]", classes="section-header")
        )
        section.compose_add_child(Static("\n".join(lines), classes="section-content"))
        return section

    def _build_themes_section(self, a: DeckAnalysis) -> Vertical:
        """Build themes and synergies section."""
        lines = []

        if a.dominant_tribe:
            lines.append(f"[bold]Tribal:[/] [{ui_colors.GOLD}]{a.dominant_tribe}[/]")

        if a.dominant_themes:
            lines.append(f"[bold]Themes:[/] {', '.join(a.dominant_themes[:4])}")

        if a.keywords:
            lines.append("\n[dim]Keywords:[/]")
            for kw, count in a.keywords[:6]:
                lines.append(f"  {kw}: {count}")

        section = Vertical()
        section.compose_add_child(
            Static(f"[{ui_colors.GOLD}]SYNERGIES[/]", classes="section-header")
        )
        section.compose_add_child(Static("\n".join(lines), classes="section-content"))
        return section

    def _build_health_section(self, a: DeckAnalysis, deck: DeckWithCards) -> Vertical:  # noqa: ARG002
        """Build deck health metrics section."""
        # Land ratio
        total = a.card_count
        land_pct = int((a.lands / total) * 100) if total > 0 else 0
        land_ok = 35 <= land_pct <= 42
        land_color = "#7ec850" if land_ok else "#e6c84a"

        # Type breakdown (compact)
        type_parts = []
        if a.creatures:
            type_parts.append(f"[#7ec850]⚔{a.creatures}[/]")
        if a.instants:
            type_parts.append(f"[#4a9fd8]⚡{a.instants}[/]")
        if a.sorceries:
            type_parts.append(f"[#a855f7]✦{a.sorceries}[/]")
        if a.artifacts:
            type_parts.append(f"[#9a9a9a]⚙{a.artifacts}[/]")
        if a.enchantments:
            type_parts.append(f"[#b86fce]✧{a.enchantments}[/]")
        if a.planeswalkers:
            type_parts.append(f"[#e6c84a]★{a.planeswalkers}[/]")

        # Health checks
        checks = []
        if a.interaction_count >= 10:
            checks.append(f"[green]✓[/] Interaction: {a.interaction_count}")
        elif a.interaction_count >= 6:
            checks.append(f"[yellow]~[/] Interaction: {a.interaction_count}")
        else:
            checks.append(f"[red]✗[/] Interaction: {a.interaction_count} (low)")

        if a.draw_count >= 8:
            checks.append(f"[green]✓[/] Card draw: {a.draw_count}")
        elif a.draw_count >= 4:
            checks.append(f"[yellow]~[/] Card draw: {a.draw_count}")
        else:
            checks.append(f"[red]✗[/] Card draw: {a.draw_count} (low)")

        if a.ramp_count >= 8:
            checks.append(f"[green]✓[/] Ramp: {a.ramp_count}")
        elif a.ramp_count >= 4:
            checks.append(f"[yellow]~[/] Ramp: {a.ramp_count}")
        else:
            checks.append(f"[red]✗[/] Ramp: {a.ramp_count} (low)")

        content = f"""[dim]Types:[/] {" ".join(type_parts)}
[{land_color}]◆ {a.lands}[/] lands ({land_pct}%)

{chr(10).join(checks)}"""

        section = Vertical()
        section.compose_add_child(
            Static(f"[{ui_colors.GOLD}]DECK HEALTH[/]", classes="section-header")
        )
        section.compose_add_child(Static(content, classes="section-content"))
        return section

    def _build_collection_section(self, a: DeckAnalysis) -> Vertical:
        """Build collection coverage section."""
        total = a.owned_count + a.needed_count
        owned_pct = int((a.owned_count / total) * 100) if total > 0 else 0

        # Progress bar
        bar_len = 20
        filled = int((a.owned_count / total) * bar_len) if total > 0 else 0
        bar = f"[green]{'█' * filled}[/][dim]{'░' * (bar_len - filled)}[/]"

        if a.needed_count == 0:
            status = "[green]✓ Complete![/]"
        else:
            status = f"[yellow]⚠ {a.needed_count} cards needed[/]"

        content = f"""{bar}
[green]✓ {a.owned_count}[/] owned ({owned_pct}%)
{status}"""

        section = Vertical()
        section.compose_add_child(
            Static(f"[{ui_colors.GOLD}]COLLECTION[/]", classes="section-header")
        )
        section.compose_add_child(Static(content, classes="section-content"))
        return section

    def _build_price_section(self, a: DeckAnalysis) -> Vertical:
        """Build price analysis section."""
        price_color = (
            "#7ec850" if a.total_price < 50 else "#e6c84a" if a.total_price < 200 else "#e86a58"
        )

        lines = [f"[{price_color}]${a.total_price:.0f}[/] total"]

        if a.expensive_cards:
            lines.append("\n[dim]Most expensive:[/]")
            for name, price in a.expensive_cards[:4]:
                short = name[:16] if len(name) > 16 else name
                lines.append(f"  {short} [dim]${price:.0f}[/]")

        section = Vertical()
        section.compose_add_child(Static(f"[{ui_colors.GOLD}]PRICE[/]", classes="section-header"))
        section.compose_add_child(Static("\n".join(lines), classes="section-content"))
        return section

    # ===== Analysis helpers =====

    def _calc_curve(self, deck: DeckWithCards) -> dict[int, int]:
        """Calculate mana curve (non-land spells)."""
        curve: dict[int, int] = {}
        for card in deck.mainboard:
            if card.card and card.card.type and "Land" not in card.card.type:
                cmc = min(7, int(card.card.cmc or 0))
                curve[cmc] = curve.get(cmc, 0) + card.quantity
        return curve

    def _calc_avg_cmc(self, deck: DeckWithCards) -> float:
        """Calculate average CMC of non-land cards."""
        total, count = 0.0, 0
        for card in deck.mainboard:
            if card.card and card.card.type and "Land" not in card.card.type:
                total += (card.card.cmc or 0) * card.quantity
                count += card.quantity
        return total / count if count > 0 else 0

    def _calc_colors(self, deck: DeckWithCards) -> dict[str, int]:
        """Calculate color pip distribution from mana costs."""
        colors: dict[str, int] = {}
        for card in deck.mainboard:
            if card.card and card.card.mana_cost:
                for c in "WUBRG":
                    colors[c] = (
                        colors.get(c, 0) + card.card.mana_cost.count(f"{{{c}}}") * card.quantity
                    )
        return colors

    def _calc_types(self, deck: DeckWithCards) -> dict[str, int]:
        """Calculate type distribution."""
        types: dict[str, int] = {}
        priority = [
            "Creature",
            "Instant",
            "Sorcery",
            "Artifact",
            "Enchantment",
            "Planeswalker",
            "Land",
        ]
        for card in deck.mainboard:
            if card.card and card.card.type:
                for t in priority:
                    if t in card.card.type:
                        types[t] = types.get(t, 0) + card.quantity
                        break
        return types

    def _count_keywords(self, deck: DeckWithCards) -> list[tuple[str, int]]:
        """Count keywords across all cards."""
        keywords: dict[str, int] = {}
        for card in deck.mainboard:
            if card.card and card.card.keywords:
                for kw in card.card.keywords:
                    keywords[kw] = keywords.get(kw, 0) + card.quantity

        return sorted(keywords.items(), key=lambda x: -x[1])

    def _count_interaction(self, deck: DeckWithCards) -> int:
        """Count removal and interaction spells."""
        patterns = ["destroy", "exile", "counter target", "return target", r"deals.*damage to"]
        count = 0
        for card in deck.mainboard:
            if card.card and card.card.text:
                text = card.card.text.lower()
                if any(re.search(p, text) for p in patterns):
                    count += card.quantity
        return count

    def _count_draw(self, deck: DeckWithCards) -> int:
        """Count card draw effects."""
        patterns = ["draw a card", "draw cards", "draws a card", "draw two", "draw three"]
        count = 0
        for card in deck.mainboard:
            if card.card and card.card.text:
                text = card.card.text.lower()
                if any(p in text for p in patterns):
                    count += card.quantity
        return count

    def _count_ramp(self, deck: DeckWithCards) -> int:
        """Count mana ramp effects."""
        patterns = [
            r"add \{",
            "add one mana",
            "add two mana",
            "search your library for a basic land",
            "search your library for a land",
            r"put.*land.*onto the battlefield",
        ]
        count = 0
        for card in deck.mainboard:
            if card.card and card.card.type and "Land" not in card.card.type and card.card.text:
                text = card.card.text.lower()
                if any(re.search(p, text) for p in patterns):
                    count += card.quantity
        return count

    def _detect_archetype(
        self,
        deck: DeckWithCards,
        types: dict[str, int],
        avg_cmc: float,
        interaction: int,
        draw: int,
    ) -> tuple[str, int]:
        """Detect deck archetype based on card composition."""
        creatures = types.get("Creature", 0)
        instants = types.get("Instant", 0)
        sorceries = types.get("Sorcery", 0)
        lands = types.get("Land", 0)

        total_nonland = deck.mainboard_count - lands
        creature_pct = (creatures / total_nonland * 100) if total_nonland > 0 else 0
        spell_pct = ((instants + sorceries) / total_nonland * 100) if total_nonland > 0 else 0

        if creature_pct > 60 and avg_cmc < 2.5:
            return "Aggro", 85
        elif creature_pct > 60 and avg_cmc >= 2.5:
            return "Creature-Heavy", 75
        elif interaction > 12 and creatures < 15:
            return "Control", 80
        elif spell_pct > 50:
            return "Spellslinger", 75
        elif draw > 10 and interaction > 8:
            return "Draw-Go", 70
        elif avg_cmc > 3.5 and creatures > 15:
            return "Midrange", 70
        elif avg_cmc < 2.5:
            return "Low Curve", 65
        else:
            return "Balanced", 50

    def _detect_themes(self, deck: DeckWithCards) -> list[str]:
        """Detect dominant themes in the deck."""
        themes: Counter[str] = Counter()

        theme_patterns = {
            "Landfall": ["landfall", "land enters", "whenever a land"],
            "+1/+1 Counters": ["+1/+1 counter", "put a counter", "proliferate"],
            "Tokens": ["create a", "token", "populate"],
            "Sacrifice": ["sacrifice a", "when.*dies", "death trigger"],
            "Graveyard": ["graveyard", "return from", "mill", "flashback"],
            "Lifegain": ["gain life", "lifelink", "whenever you gain"],
            "Artifacts": ["artifact", "metalcraft", "affinity"],
            "Enchantments": ["enchantment", "constellation", "aura"],
            "Spellslinger": ["instant or sorcery", "magecraft", "whenever you cast"],
            "Tribal": ["creature type", "creatures you control"],
        }

        for card in deck.mainboard:
            if card.card and card.card.text:
                text = card.card.text.lower()
                for theme, patterns in theme_patterns.items():
                    if any(p in text for p in patterns):
                        themes[theme] += card.quantity

        # Return top themes
        return [t for t, _ in themes.most_common(4) if themes[t] >= 3]

    def _detect_tribe(self, deck: DeckWithCards) -> str | None:
        """Detect dominant creature type."""
        subtypes: Counter[str] = Counter()

        for card in deck.mainboard:
            if (
                card.card
                and card.card.type
                and "Creature" in card.card.type
                and " — " in card.card.type
            ):
                # Extract subtypes (after the dash)
                subtype_part = card.card.type.split(" — ")[1]
                for subtype in subtype_part.split():
                    if subtype not in ["Creature", "Legendary", "Basic"]:
                        subtypes[subtype] += card.quantity

        if subtypes:
            top, count = subtypes.most_common(1)[0]
            if count >= 5:  # At least 5 creatures of the type
                return top

        return None

    def _detect_combos(self, deck: DeckWithCards) -> list[SpellbookComboMatch]:
        """Detect combos in the deck using Commander Spellbook."""
        try:
            from mtg_core.tools.recommendations.spellbook_combos import get_spellbook_detector

            detector = get_spellbook_detector()
            if not detector.is_available:
                return []

            card_names = [c.card_name for c in deck.mainboard]
            # find_missing_pieces returns (matches, missing_card_to_combos)
            # We want combos with >= 60% completion (max_missing varies by combo size)
            matches, _ = detector.find_missing_pieces(card_names, max_missing=3, min_present=2)

            # Filter to min 60% completion and sort by completion ratio
            filtered = [m for m in matches if m.completion_ratio >= 0.6]
            return sorted(filtered, key=lambda m: (-int(m.is_complete), -m.completion_ratio))[:10]

        except Exception:
            return []

    def _get_17lands_stats(
        self, deck: DeckWithCards
    ) -> tuple[dict[str, int], list[tuple[str, str, float | None]]]:
        """Get 17Lands tier data for cards in deck."""
        tier_counts: dict[str, int] = {}
        top_cards: list[tuple[str, str, float | None]] = []

        try:
            from mtg_core.tools.recommendations.limited_stats import get_limited_stats_db

            db = get_limited_stats_db()
            if not db.is_available:
                return tier_counts, top_cards

            cards_with_stats: list[tuple[str, str, float | None]] = []

            for card in deck.mainboard:
                stats = db.get_card_stats(card.card_name)
                if stats:
                    tier_counts[stats.tier] = tier_counts.get(stats.tier, 0) + 1
                    cards_with_stats.append((card.card_name, stats.tier, stats.gih_wr))

            # Sort by tier (S > A > B...) then by win rate
            tier_order = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4, "F": 5}
            cards_with_stats.sort(key=lambda x: (tier_order.get(x[1], 99), -(x[2] or 0)))
            top_cards = cards_with_stats[:8]

        except Exception:
            pass

        return tier_counts, top_cards

    def _calc_score(self, a: DeckAnalysis, deck: DeckWithCards) -> int:
        """Calculate deck health score (0-100)."""
        score = 100
        total = a.card_count
        expected = 99 if (deck.format or "").lower() == "commander" else 60

        # Card count penalty
        if total < expected:
            score -= min(30, (expected - total) * 2)

        # Land ratio check
        ratio = a.lands / total if total > 0 else 0
        if ratio < 0.33 or ratio > 0.45:
            score -= 15
        elif ratio < 0.35 or ratio > 0.42:
            score -= 5

        # CMC check
        if a.avg_cmc > 4.0:
            score -= 15
        elif a.avg_cmc > 3.5:
            score -= 5

        # Interaction check
        if a.interaction_count < 6:
            score -= 10
        elif a.interaction_count < 10:
            score -= 5

        # Draw check
        if a.draw_count < 4:
            score -= 10
        elif a.draw_count < 8:
            score -= 5

        return max(0, min(100, score))
