"""Horizontal deck statistics bar with dense visualizations."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from ..ui.theme import ui_colors

if TYPE_CHECKING:
    from ..deck_manager import DeckWithCards

# Mana colors with improved contrast
MANA = {
    "W": "#F8E7B9",
    "U": "#0E86D4",
    "B": "#9B7BB8",
    "R": "#E86A58",
    "G": "#7EC850",
    "C": "#95A5A6",
}


class DeckStatsBar(Vertical):
    """Wide horizontal stats bar with graphs and analysis.

    Layout:
    ┌─Curve──────┬─Colors─────┬─Types──────┬─Keywords────┬─Analysis──────────┬─Price──┐
    │ ▁▂▅▇▅▃▂▁  │ W ████ 25% │ ⚔ Crea 24 │ Flying: 8   │ Archetype: Aggro  │ $245   │
    │ 0123456+   │ U ██   12% │ ⚡ Inst 12 │ Trample: 4  │ Grade: A (82/100) │ Top:   │
    │ Avg: 2.4   │ B ████ 25% │ 🔮 Sorc  8 │ Lifelink: 3 │ Lands: 24 (40%)   │ Sol.. $│
    └────────────┴────────────┴────────────┴─────────────┴───────────────────┴────────┘
    """

    DEFAULT_CSS = """
    DeckStatsBar {
        width: 100%;
        height: auto;
        min-height: 10;
        max-height: 12;
        background: #0a0a14;
        border-top: heavy #c9a227;
    }

    #stats-bar-header {
        width: 100%;
        height: 1;
        background: #151520;
        padding: 0 1;
    }

    #stats-bar-content {
        width: 100%;
        height: 1fr;
        padding: 0;
    }

    .stats-column {
        height: 100%;
        padding: 0 1;
        border-right: solid #2a2a3e;
    }

    .stats-column:last-child {
        border-right: none;
    }

    #stats-curve {
        width: 18;
        min-width: 16;
    }

    #stats-colors {
        width: 20;
        min-width: 18;
    }

    #stats-types {
        width: 16;
        min-width: 14;
    }

    #stats-keywords {
        width: 18;
        min-width: 16;
    }

    #stats-analysis {
        width: 1fr;
        min-width: 24;
    }

    #stats-price {
        width: 16;
        min-width: 14;
    }

    .stats-label {
        height: 1;
        color: #c9a227;
        text-style: bold;
    }

    .stats-value {
        height: auto;
    }

    #stats-empty-bar {
        width: 100%;
        height: 100%;
        content-align: center middle;
    }
    """

    can_focus = True

    def __init__(
        self,
        *,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._deck: DeckWithCards | None = None
        self._prices: dict[str, float] = {}  # card_name -> price_usd

    def compose(self) -> ComposeResult:
        yield Static(
            f"[bold {ui_colors.GOLD}]━━━ DECK ANALYSIS ━━━[/]",
            id="stats-bar-header",
        )
        with Horizontal(id="stats-bar-content"):
            yield Static("[dim]Select a deck to view statistics[/]", id="stats-empty-bar")

    def update_stats(
        self,
        deck: DeckWithCards | None,
        prices: dict[str, float] | None = None,
    ) -> None:
        """Update statistics display.

        Args:
            deck: The deck to analyze
            prices: Optional dict of card_name -> price_usd
        """
        self._deck = deck
        if prices:
            self._prices = prices

        try:
            content = self.query_one("#stats-bar-content", Horizontal)
            content.remove_children()

            if deck is None or deck.mainboard_count == 0:
                content.mount(
                    Static("[dim]Select a deck to view statistics[/]", id="stats-empty-bar")
                )
                return

            # Build all stat columns
            content.mount(self._build_curve_column(deck))
            content.mount(self._build_colors_column(deck))
            content.mount(self._build_types_column(deck))
            content.mount(self._build_keywords_column(deck))
            content.mount(self._build_analysis_column(deck))
            content.mount(self._build_price_column(deck))

        except Exception:
            # Silently skip stats on error - UI will just show empty
            pass

    def _build_curve_column(self, deck: DeckWithCards) -> Vertical:
        """Build mana curve visualization with sparkline bars."""
        curve = self._calc_curve(deck)
        max_count = max(curve.values()) if curve else 1
        total = sum(curve.values())
        avg = self._calc_avg_cmc(deck)

        lines = []

        # Sparkline using block characters (3 rows high for compactness)
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
        lines.append(sparkline)

        # CMC labels
        lines.append("[dim]0123456+[/]")

        # Counts per CMC (compact)
        counts = ""
        for c in range(8):
            val = curve.get(c, 0)
            counts += str(val) if val < 10 else "+"
        lines.append(f"[dim]{counts}[/]")

        # Average with color coding
        cmc_color = "#7ec850" if avg <= 2.5 else "#e6c84a" if avg <= 3.5 else "#e86a58"
        lines.append(f"[dim]avg[/] [{cmc_color}]{avg:.2f}[/]")

        # Total non-land cards
        lines.append(f"[dim]{total} spells[/]")

        col = Vertical(classes="stats-column", id="stats-curve")
        col.compose_add_child(Static(f"[{ui_colors.GOLD}]CURVE[/]", classes="stats-label"))
        col.compose_add_child(Static("\n".join(lines), classes="stats-value"))
        return col

    def _build_colors_column(self, deck: DeckWithCards) -> Vertical:
        """Build color distribution with pip counts."""
        colors = self._calc_colors(deck)
        total = sum(colors.values())

        lines = []
        for c in ["W", "U", "B", "R", "G"]:
            count = colors.get(c, 0)
            if count == 0:
                continue
            pct = int((count / total) * 100) if total > 0 else 0
            bar_len = max(1, min(6, int((count / total) * 6))) if total > 0 else 0
            bar = f"[{MANA[c]}]{'█' * bar_len}[/][dim]{'░' * (6 - bar_len)}[/]"
            lines.append(f"[{MANA[c]}]{c}[/]{bar}{pct:>2}%")

        if not lines:
            lines.append("[dim]Colorless[/]")

        # Color identity display
        identity = "".join(c for c in "WUBRG" if colors.get(c, 0) > 0) or "C"
        id_display = "".join(f"[{MANA.get(c, '#888')}]●[/]" for c in identity)
        lines.append(f"[dim]ID:[/] {id_display}")

        col = Vertical(classes="stats-column", id="stats-colors")
        col.compose_add_child(Static(f"[{ui_colors.GOLD}]COLORS[/]", classes="stats-label"))
        col.compose_add_child(Static("\n".join(lines), classes="stats-value"))
        return col

    def _build_types_column(self, deck: DeckWithCards) -> Vertical:
        """Build card type breakdown."""
        types = self._calc_types(deck)

        type_info = [
            ("Creature", "⚔", "#7ec850"),
            ("Instant", "⚡", "#4a9fd8"),
            ("Sorcery", "✦", "#a855f7"),
            ("Artifact", "⚙", "#9a9a9a"),
            ("Enchantment", "✧", "#b86fce"),
            ("Planeswalker", "★", "#e6c84a"),
            ("Land", "◆", "#a67c52"),
        ]

        lines = []
        for type_name, icon, color in type_info:
            count = types.get(type_name, 0)
            if count == 0:
                continue
            short_name = type_name[:4]
            lines.append(f"{icon}[{color}]{short_name:>4}[/] {count:>2}")

        col = Vertical(classes="stats-column", id="stats-types")
        col.compose_add_child(Static(f"[{ui_colors.GOLD}]TYPES[/]", classes="stats-label"))
        col.compose_add_child(Static("\n".join(lines), classes="stats-value"))
        return col

    def _build_keywords_column(self, deck: DeckWithCards) -> Vertical:
        """Build keyword/mechanic summary."""
        keywords = self._count_keywords(deck)

        # Get top 5 keywords
        sorted_kw = sorted(keywords.items(), key=lambda x: -x[1])[:5]

        lines = []
        for kw, count in sorted_kw:
            # Truncate long keywords
            display = kw[:8] if len(kw) > 8 else kw
            lines.append(f"[dim]{display}[/] {count}")

        if not lines:
            lines.append("[dim]No keywords[/]")

        col = Vertical(classes="stats-column", id="stats-keywords")
        col.compose_add_child(Static(f"[{ui_colors.GOLD}]KEYWORDS[/]", classes="stats-label"))
        col.compose_add_child(Static("\n".join(lines), classes="stats-value"))
        return col

    def _build_analysis_column(self, deck: DeckWithCards) -> Vertical:
        """Build deck analysis with archetype and health metrics."""
        total = deck.mainboard_count
        lands = self._count_type(deck, "Land")
        interaction = self._count_interaction(deck)
        draw = self._count_draw(deck)
        ramp = self._count_ramp(deck)

        # Archetype detection
        archetype, conf = self._detect_archetype(deck)

        # Deck score
        score = self._calc_score(deck)
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

        # Land ratio
        land_pct = int((lands / total) * 100) if total > 0 else 0
        land_ok = 35 <= land_pct <= 42
        land_color = "#7ec850" if land_ok else "#e6c84a"

        # Format check
        fmt = deck.format or "casual"
        expected = 99 if fmt.lower() == "commander" else 60
        count_ok = total >= expected

        lines = [
            f"[bold]{archetype}[/] [{ui_colors.GOLD_DIM}]{conf}%[/]",
            f"[{score_color}]{grade}[/] [{score_color}]{score}[/]/100",
            f"[{land_color}]{lands}[/] lands ({land_pct}%)",
            f"⚔{interaction} [dim]int[/] ✎{draw} [dim]draw[/] ⬆{ramp} [dim]ramp[/]",
            f"{'[#7ec850]✓[/]' if count_ok else '[#e86a58]✗[/]'} {total}/{expected} {fmt}",
        ]

        col = Vertical(classes="stats-column", id="stats-analysis")
        col.compose_add_child(Static(f"[{ui_colors.GOLD}]ANALYSIS[/]", classes="stats-label"))
        col.compose_add_child(Static("\n".join(lines), classes="stats-value"))
        return col

    def _build_price_column(self, deck: DeckWithCards) -> Vertical:
        """Build price analysis using cached prices."""
        total_price = 0.0
        expensive_cards: list[tuple[str, float]] = []

        for card in deck.mainboard + deck.sideboard:
            price = self._prices.get(card.card_name, 0.0)
            card_total = price * card.quantity
            total_price += card_total
            if price > 1.0:
                expensive_cards.append((card.card_name, price))

        expensive_cards.sort(key=lambda x: -x[1])

        lines = []
        if total_price > 0:
            price_color = (
                "#7ec850" if total_price < 50 else "#e6c84a" if total_price < 200 else "#e86a58"
            )
            lines.append(f"[{price_color}]${total_price:.0f}[/] total")
            lines.append("[dim]Top cards:[/]")
            for name, price in expensive_cards[:3]:
                short_name = name[:9] if len(name) > 9 else name
                lines.append(f"[dim]{short_name}[/] ${price:.0f}")
        else:
            lines.append("[dim]Price data[/]")
            lines.append("[dim]loading...[/]")

        col = Vertical(classes="stats-column", id="stats-price")
        col.compose_add_child(Static(f"[{ui_colors.GOLD}]PRICE[/]", classes="stats-label"))
        col.compose_add_child(Static("\n".join(lines), classes="stats-value"))
        return col

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

    def _count_keywords(self, deck: DeckWithCards) -> dict[str, int]:
        """Count keywords across all cards."""
        keywords: dict[str, int] = {}
        for card in deck.mainboard:
            if card.card and card.card.keywords:
                for kw in card.card.keywords:
                    keywords[kw] = keywords.get(kw, 0) + card.quantity
        return keywords

    def _count_type(self, deck: DeckWithCards, type_name: str) -> int:
        """Count cards of a specific type."""
        count = 0
        for card in deck.mainboard:
            if card.card and card.card.type and type_name in card.card.type:
                count += card.quantity
        return count

    def _count_interaction(self, deck: DeckWithCards) -> int:
        """Count removal and interaction spells."""
        literal_patterns = ["destroy", "exile", "counter target", "return target"]
        regex_patterns = [re.compile(r"deals\s+\d+\s+damage\s+to")]
        count = 0
        for card in deck.mainboard:
            if card.card and card.card.text:
                text = card.card.text.lower()
                if any(p in text for p in literal_patterns) or any(
                    r.search(text) for r in regex_patterns
                ):
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
        literal_patterns = [
            "add {",
            "add one mana",
            "add two mana",
            "search your library for a basic land",
            "search your library for a land",
        ]
        regex_patterns = [re.compile(r"put\s+.+\s+land.+onto the battlefield")]
        count = 0
        for card in deck.mainboard:
            if card.card and card.card.type and "Land" not in card.card.type and card.card.text:
                text = card.card.text.lower()
                if any(p in text for p in literal_patterns) or any(
                    r.search(text) for r in regex_patterns
                ):
                    count += card.quantity
        return count

    def _detect_archetype(self, deck: DeckWithCards) -> tuple[str, int]:
        """Detect deck archetype based on card composition."""
        creatures = self._count_type(deck, "Creature")
        instants = self._count_type(deck, "Instant")
        sorceries = self._count_type(deck, "Sorcery")
        avg = self._calc_avg_cmc(deck)
        interaction = self._count_interaction(deck)
        draw = self._count_draw(deck)

        total_nonland = deck.mainboard_count - self._count_type(deck, "Land")
        creature_pct = (creatures / total_nonland * 100) if total_nonland > 0 else 0
        spell_pct = ((instants + sorceries) / total_nonland * 100) if total_nonland > 0 else 0

        # Archetype detection with confidence
        if creature_pct > 60 and avg < 2.5:
            return "Aggro", 85
        elif creature_pct > 60 and avg >= 2.5:
            return "Creature-heavy", 75
        elif interaction > 12 and creatures < 15:
            return "Control", 80
        elif spell_pct > 50:
            return "Spellslinger", 75
        elif draw > 10 and interaction > 8:
            return "Draw-Go", 70
        elif avg > 3.5 and creatures > 15:
            return "Midrange", 70
        elif avg < 2.5:
            return "Low Curve", 65
        else:
            return "Balanced", 50

    def _calc_score(self, deck: DeckWithCards) -> int:
        """Calculate deck health score (0-100)."""
        score = 100
        total = deck.mainboard_count
        expected = 99 if (deck.format or "").lower() == "commander" else 60

        # Card count penalty
        if total < expected:
            score -= min(30, (expected - total) * 2)

        # Land ratio check
        lands = self._count_type(deck, "Land")
        ratio = lands / total if total > 0 else 0
        if ratio < 0.33 or ratio > 0.45:
            score -= 15
        elif ratio < 0.35 or ratio > 0.42:
            score -= 5

        # CMC check
        avg = self._calc_avg_cmc(deck)
        if avg > 4.0:
            score -= 15
        elif avg > 3.5:
            score -= 5

        # Interaction check
        if self._count_interaction(deck) < 6:
            score -= 10
        elif self._count_interaction(deck) < 10:
            score -= 5

        # Draw check
        if self._count_draw(deck) < 4:
            score -= 10
        elif self._count_draw(deck) < 8:
            score -= 5

        return max(0, min(100, score))
