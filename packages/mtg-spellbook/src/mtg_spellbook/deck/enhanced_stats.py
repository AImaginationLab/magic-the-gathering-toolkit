"""Enhanced deck statistics with beautiful visualizations and deep analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from ..ui.theme import ui_colors

if TYPE_CHECKING:
    from ..deck_manager import DeckWithCards


# Mana symbols and colors
MANA_CONFIG = {
    "W": {"symbol": "{W}", "color": "#F8E7B9", "name": "White", "icon": "W"},
    "U": {"symbol": "{U}", "color": "#0E86D4", "name": "Blue", "icon": "U"},
    "B": {"symbol": "{B}", "color": "#9B7BB8", "name": "Black", "icon": "B"},
    "R": {"symbol": "{R}", "color": "#E86A58", "name": "Red", "icon": "R"},
    "G": {"symbol": "{G}", "color": "#7EC850", "name": "Green", "icon": "G"},
    "C": {"symbol": "{C}", "color": "#95A5A6", "name": "Colorless", "icon": "C"},
}


class EnhancedDeckStats(Vertical):
    """Beautiful, comprehensive deck statistics panel.

    Features:
    - Visual mana curve with sparkline
    - Color pie chart (ASCII)
    - Card type distribution
    - Deck archetype detection
    - Mana base analysis
    - Key metrics dashboard
    - Deck health score
    """

    DEFAULT_CSS = """
    EnhancedDeckStats {
        width: 100%;
        height: 100%;
        background: #0d0d0d;
        padding: 1;
        overflow-y: auto;
    }

    .stat-card {
        width: 100%;
        height: auto;
        background: #151520;
        border: solid #2a2a3e;
        padding: 1;
        margin-bottom: 1;
    }

    .stat-card-header {
        width: 100%;
        height: 1;
        margin-bottom: 1;
    }

    .stat-card-content {
        width: 100%;
        height: auto;
    }

    .metric-row {
        width: 100%;
        height: auto;
    }

    .stat-score-card {
        background: #1a1a2e;
        border: heavy #c9a227;
    }

    #stats-empty {
        width: 100%;
        height: 100%;
        content-align: center middle;
    }
    """

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._deck: DeckWithCards | None = None

    def compose(self) -> ComposeResult:
        yield Static(
            "[dim]Select a deck to view statistics[/]",
            id="stats-empty",
        )

    def update_stats(self, deck: DeckWithCards | None) -> None:
        """Update all statistics from deck data."""
        self._deck = deck

        # Remove old content and rebuild
        self.remove_children()

        if deck is None or deck.mainboard_count == 0:
            self.mount(
                Static("[dim]Select a deck to view statistics[/]")
            )
            return

        # Build all stat cards
        self._build_stats(deck)

    def _build_stats(self, deck: DeckWithCards) -> None:
        """Build all statistics widgets."""
        # Score card (top)
        self.mount(self._build_score_card(deck))

        # Key metrics row
        self.mount(self._build_metrics_card(deck))

        # Mana curve
        self.mount(self._build_curve_card(deck))

        # Color distribution
        self.mount(self._build_color_card(deck))

        # Card types
        self.mount(self._build_types_card(deck))

        # Mana base analysis
        self.mount(self._build_manabase_card(deck))

        # Deck archetype
        self.mount(self._build_archetype_card(deck))

    def _build_score_card(self, deck: DeckWithCards) -> Vertical:
        """Build deck health score card."""
        score, _grade, issues = self._calculate_deck_score(deck)

        # Color based on score
        if score >= 85:
            score_color = "#7ec850"
            grade_emoji = "S"
        elif score >= 70:
            score_color = "#4a9fd8"
            grade_emoji = "A"
        elif score >= 55:
            score_color = "#e6c84a"
            grade_emoji = "B"
        elif score >= 40:
            score_color = "#e89b5a"
            grade_emoji = "C"
        else:
            score_color = "#e86a58"
            grade_emoji = "D"

        # Build score visualization
        bar_width = 20
        filled = int((score / 100) * bar_width)
        bar = f"[{score_color}]{'█' * filled}[/][dim]{'░' * (bar_width - filled)}[/]"

        content_lines = [
            f"[bold {score_color}]{grade_emoji}[/]  {bar}  [{score_color}]{score}[/]/100",
            "",
        ]

        # Add issues or praise
        if issues:
            for issue in issues[:3]:
                content_lines.append(f"  [dim]•[/] {issue}")
        else:
            content_lines.append(f"  [{score_color}]✓[/] Deck looks well-balanced!")

        card = Vertical(classes="stat-card stat-score-card")
        card.compose_add_child(
            Static(f"[bold {ui_colors.GOLD}]DECK SCORE[/]", classes="stat-card-header")
        )
        card.compose_add_child(Static("\n".join(content_lines), classes="stat-card-content"))
        return card

    def _build_metrics_card(self, deck: DeckWithCards) -> Vertical:
        """Build key metrics dashboard."""
        # Calculate metrics
        total_cards = deck.mainboard_count
        avg_cmc = self._calculate_avg_cmc(deck)
        land_count = self._count_type(deck, "Land")
        creature_count = self._count_type(deck, "Creature")
        _ = total_cards - land_count - creature_count  # spell_count for reference

        # Mana sources (lands + mana dorks/rocks)
        mana_sources = land_count + self._count_mana_sources(deck)

        # Calculate expected format
        format_name = deck.format or "60-card"
        expected = 99 if format_name.lower() == "commander" else 60

        # Build metrics grid
        metrics = [
            ("Cards", f"{total_cards}/{expected}", "#7ec850" if total_cards >= expected else "#e6c84a"),
            ("Avg CMC", f"{avg_cmc:.2f}", self._cmc_color(avg_cmc)),
            ("Lands", f"{land_count}", self._land_color(land_count, total_cards)),
            ("Mana", f"{mana_sources}", "#7ec850" if mana_sources >= land_count else "#e6c84a"),
        ]

        # Two rows of metrics
        row1 = "  ".join(
            f"[dim]{name}:[/] [{color}]{value}[/]" for name, value, color in metrics[:2]
        )
        row2 = "  ".join(
            f"[dim]{name}:[/] [{color}]{value}[/]" for name, value, color in metrics[2:]
        )

        card = Vertical(classes="stat-card")
        card.compose_add_child(
            Static(f"[bold {ui_colors.GOLD}]KEY METRICS[/]", classes="stat-card-header")
        )
        card.compose_add_child(Static(f"{row1}\n{row2}", classes="stat-card-content"))
        return card

    def _build_curve_card(self, deck: DeckWithCards) -> Vertical:
        """Build mana curve visualization."""
        curve = self._calculate_curve(deck)
        if not curve:
            card = Vertical(classes="stat-card")
            card.compose_add_child(
                Static(f"[bold {ui_colors.GOLD}]MANA CURVE[/]", classes="stat-card-header")
            )
            card.compose_add_child(Static("[dim]No non-land cards[/]", classes="stat-card-content"))
            return card

        max_count = max(curve.values()) if curve else 1
        total = sum(curve.values())
        avg_cmc = self._calculate_avg_cmc(deck)

        # Build vertical bar chart
        lines = []
        bar_height = 6

        # Build bars from top to bottom
        for level in range(bar_height, 0, -1):
            row = ""
            for cmc in range(8):
                count = curve.get(cmc, 0)
                threshold = (count / max_count) * bar_height if max_count > 0 else 0
                if threshold >= level:
                    row += f"[{ui_colors.GOLD}]██[/] "
                elif threshold >= level - 0.5:
                    row += f"[{ui_colors.GOLD_DIM}]▄▄[/] "
                else:
                    row += "[dim]░░[/] "
            lines.append(row)

        # CMC labels
        label_row = " ".join(f"{cmc if cmc < 7 else '7+':>2}" for cmc in range(8))
        lines.append(f"[dim]{label_row}[/]")

        # Counts row
        count_row = " ".join(f"{curve.get(cmc, 0):>2}" for cmc in range(8))
        lines.append(f"[dim]{count_row}[/]")

        # Average indicator
        lines.append("")
        lines.append(f"[dim]Average:[/] [{ui_colors.GOLD}]{avg_cmc:.2f}[/]  [dim]Total:[/] {total}")

        card = Vertical(classes="stat-card")
        card.compose_add_child(
            Static(f"[bold {ui_colors.GOLD}]MANA CURVE[/]", classes="stat-card-header")
        )
        card.compose_add_child(Static("\n".join(lines), classes="stat-card-content"))
        return card

    def _build_color_card(self, deck: DeckWithCards) -> Vertical:
        """Build color distribution with visual representation."""
        colors = self._calculate_colors(deck)
        total_pips = sum(colors.values())

        if total_pips == 0:
            card = Vertical(classes="stat-card")
            card.compose_add_child(
                Static(f"[bold {ui_colors.GOLD}]COLORS[/]", classes="stat-card-header")
            )
            card.compose_add_child(Static("[dim]No colored mana costs[/]", classes="stat-card-content"))
            return card

        lines = []

        # Color identity summary
        identity = "".join(c for c in ["W", "U", "B", "R", "G"] if colors.get(c, 0) > 0)
        identity_display = " ".join(
            f"[{MANA_CONFIG[c]['color']}]{{{c}}}[/]" for c in identity
        ) or "[dim]Colorless[/]"
        lines.append(f"Identity: {identity_display}")
        lines.append("")

        # Color bars
        bar_width = 16
        for color in ["W", "U", "B", "R", "G"]:
            count = colors.get(color, 0)
            if count == 0:
                continue

            cfg = MANA_CONFIG[color]
            pct = (count / total_pips) * 100
            bar_len = max(1, int((count / total_pips) * bar_width))

            bar = f"[{cfg['color']}]{'█' * bar_len}[/][dim]{'░' * (bar_width - bar_len)}[/]"
            lines.append(f"[{cfg['color']}]{{{color}}}[/] {bar} {count:>2} ({pct:>4.1f}%)")

        # Colorless if present
        if colors.get("C", 0) > 0:
            count = colors["C"]
            pct = (count / total_pips) * 100
            bar_len = max(1, int((count / total_pips) * bar_width))
            bar = f"[#95a5a6]{'█' * bar_len}[/][dim]{'░' * (bar_width - bar_len)}[/]"
            lines.append(f"[#95a5a6]{{C}}[/] {bar} {count:>2} ({pct:>4.1f}%)")

        lines.append("")
        lines.append(f"[dim]Total pips:[/] {total_pips}")

        card = Vertical(classes="stat-card")
        card.compose_add_child(
            Static(f"[bold {ui_colors.GOLD}]COLORS[/]", classes="stat-card-header")
        )
        card.compose_add_child(Static("\n".join(lines), classes="stat-card-content"))
        return card

    def _build_types_card(self, deck: DeckWithCards) -> Vertical:
        """Build card type breakdown."""
        types = self._calculate_types(deck)
        total = sum(types.values())

        if total == 0:
            card = Vertical(classes="stat-card")
            card.compose_add_child(
                Static(f"[bold {ui_colors.GOLD}]CARD TYPES[/]", classes="stat-card-header")
            )
            card.compose_add_child(Static("[dim]No cards[/]", classes="stat-card-content"))
            return card

        type_config = {
            "Creature": ("⚔", "#7ec850"),
            "Instant": ("⚡", "#4a9fd8"),
            "Sorcery": ("🔮", "#4a9fd8"),
            "Artifact": ("⚙", "#9a9a9a"),
            "Enchantment": ("✨", "#b86fce"),
            "Planeswalker": ("🌟", "#e6c84a"),
            "Land": ("🏔", "#a67c52"),
            "Other": ("?", "#888"),
        }

        lines = []
        bar_width = 12

        for type_name, (icon, color) in type_config.items():
            count = types.get(type_name, 0)
            if count == 0:
                continue

            pct = (count / total) * 100
            bar_len = max(1, int((count / total) * bar_width))
            bar = f"[{color}]{'█' * bar_len}[/][dim]{'░' * (bar_width - bar_len)}[/]"
            lines.append(f"{icon} [{color}]{type_name:11}[/] {bar} {count:>2} ({pct:>4.1f}%)")

        card = Vertical(classes="stat-card")
        card.compose_add_child(
            Static(f"[bold {ui_colors.GOLD}]CARD TYPES[/]", classes="stat-card-header")
        )
        card.compose_add_child(Static("\n".join(lines), classes="stat-card-content"))
        return card

    def _build_manabase_card(self, deck: DeckWithCards) -> Vertical:
        """Build mana base analysis."""
        land_types = self._analyze_lands(deck)
        total_lands = sum(land_types.values())

        lines = []

        if total_lands == 0:
            lines.append("[dim]No lands in deck[/]")
        else:
            # Land type breakdown
            land_config = [
                ("Basic", "#a67c52"),
                ("Dual", "#b86fce"),
                ("Fetch", "#4a9fd8"),
                ("Shock", "#e86a58"),
                ("Check", "#7ec850"),
                ("Utility", "#e6c84a"),
                ("Other", "#888"),
            ]

            for land_type, color in land_config:
                count = land_types.get(land_type, 0)
                if count == 0:
                    continue
                pct = (count / total_lands) * 100
                lines.append(f"[{color}]{land_type:8}[/] {count:>2} ({pct:>4.1f}%)")

            lines.append("")

            # Mana production analysis
            colors_produced = self._calculate_land_colors(deck)
            if colors_produced:
                production = " ".join(
                    f"[{MANA_CONFIG[c]['color']}]{{{c}}}[/]x{count}"
                    for c, count in sorted(colors_produced.items())
                    if count > 0
                )
                lines.append(f"[dim]Produces:[/] {production}")

        card = Vertical(classes="stat-card")
        card.compose_add_child(
            Static(f"[bold {ui_colors.GOLD}]MANA BASE[/]", classes="stat-card-header")
        )
        card.compose_add_child(Static("\n".join(lines), classes="stat-card-content"))
        return card

    def _build_archetype_card(self, deck: DeckWithCards) -> Vertical:
        """Detect and display deck archetype."""
        archetype, confidence, traits = self._detect_archetype(deck)

        lines = [
            f"[bold {ui_colors.GOLD}]{archetype}[/]  [dim]({confidence}% confidence)[/]",
            "",
        ]

        for trait in traits[:4]:
            lines.append(f"  [dim]•[/] {trait}")

        card = Vertical(classes="stat-card")
        card.compose_add_child(
            Static(f"[bold {ui_colors.GOLD}]ARCHETYPE[/]", classes="stat-card-header")
        )
        card.compose_add_child(Static("\n".join(lines), classes="stat-card-content"))
        return card

    # ===== Calculation helpers =====

    def _calculate_deck_score(self, deck: DeckWithCards) -> tuple[int, str, list[str]]:
        """Calculate overall deck health score."""
        score = 100
        issues: list[str] = []

        total = deck.mainboard_count
        expected = 99 if (deck.format or "").lower() == "commander" else 60

        # Card count penalty
        if total < expected:
            penalty = min(30, (expected - total) * 2)
            score -= penalty
            issues.append(f"Need {expected - total} more cards")

        # Land ratio check
        lands = self._count_type(deck, "Land")
        land_ratio = lands / total if total > 0 else 0
        if land_ratio < 0.33:
            score -= 15
            issues.append(f"Low land count ({lands}, need ~{int(total * 0.38)})")
        elif land_ratio > 0.45:
            score -= 10
            issues.append(f"High land count ({lands})")

        # Mana curve check
        avg_cmc = self._calculate_avg_cmc(deck)
        if avg_cmc > 4.0:
            score -= 15
            issues.append(f"High average CMC ({avg_cmc:.1f})")
        elif avg_cmc > 3.5:
            score -= 5
            issues.append(f"Consider lowering curve ({avg_cmc:.1f})")

        # Interaction check
        removal = self._count_interaction(deck)
        if removal < 6:
            score -= 10
            issues.append(f"Low interaction ({removal} cards)")

        # Card draw check
        draw = self._count_card_draw(deck)
        if draw < 5:
            score -= 10
            issues.append(f"Limited card draw ({draw} cards)")

        # Clamp score
        score = max(0, min(100, score))

        # Determine grade
        if score >= 85:
            grade = "Excellent"
        elif score >= 70:
            grade = "Good"
        elif score >= 55:
            grade = "Needs Work"
        elif score >= 40:
            grade = "Weak"
        else:
            grade = "Incomplete"

        return score, grade, issues

    def _calculate_avg_cmc(self, deck: DeckWithCards) -> float:
        """Calculate average CMC of non-land cards."""
        total_cmc = 0.0
        count = 0
        for card in deck.mainboard:
            if card.card and card.card.type and "Land" not in card.card.type:
                total_cmc += (card.card.cmc or 0) * card.quantity
                count += card.quantity
        return total_cmc / count if count > 0 else 0

    def _calculate_curve(self, deck: DeckWithCards) -> dict[int, int]:
        """Calculate mana curve distribution."""
        curve: dict[int, int] = {}
        for card in deck.mainboard:
            if card.card and card.card.type and "Land" not in card.card.type:
                cmc = min(7, int(card.card.cmc or 0))
                curve[cmc] = curve.get(cmc, 0) + card.quantity
        return curve

    def _calculate_colors(self, deck: DeckWithCards) -> dict[str, int]:
        """Calculate color distribution from mana costs."""
        colors: dict[str, int] = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "C": 0}
        for card in deck.mainboard:
            if card.card and card.card.mana_cost:
                mana = card.card.mana_cost
                for color in colors:
                    count = mana.count(f"{{{color}}}")
                    colors[color] += count * card.quantity
        return colors

    def _calculate_types(self, deck: DeckWithCards) -> dict[str, int]:
        """Calculate card type distribution."""
        types: dict[str, int] = {}
        type_priority = ["Creature", "Instant", "Sorcery", "Artifact", "Enchantment", "Planeswalker", "Land"]

        for card in deck.mainboard:
            if card.card and card.card.type:
                card_type = "Other"
                for t in type_priority:
                    if t in card.card.type:
                        card_type = t
                        break
                types[card_type] = types.get(card_type, 0) + card.quantity

        return types

    def _count_type(self, deck: DeckWithCards, type_name: str) -> int:
        """Count cards of a specific type."""
        count = 0
        for card in deck.mainboard:
            if card.card and card.card.type and type_name in card.card.type:
                count += card.quantity
        return count

    def _count_mana_sources(self, deck: DeckWithCards) -> int:
        """Count non-land mana sources."""
        count = 0
        mana_keywords = ["add {", "add one mana", "for mana"]
        for card in deck.mainboard:
            if card.card and card.card.text and card.card.type:
                if "Land" in card.card.type:
                    continue
                text = card.card.text.lower()
                if any(kw in text for kw in mana_keywords):
                    count += card.quantity
        return count

    def _count_interaction(self, deck: DeckWithCards) -> int:
        """Count removal and interaction."""
        count = 0
        keywords = ["destroy", "exile", "counter", "return target", "damage to"]
        for card in deck.mainboard:
            if card.card and card.card.text:
                text = card.card.text.lower()
                if any(kw in text for kw in keywords):
                    count += card.quantity
        return count

    def _count_card_draw(self, deck: DeckWithCards) -> int:
        """Count card draw effects."""
        count = 0
        keywords = ["draw a card", "draw cards", "draws a card", "draw two", "draw three"]
        for card in deck.mainboard:
            if card.card and card.card.text:
                text = card.card.text.lower()
                if any(kw in text for kw in keywords):
                    count += card.quantity
        return count

    def _analyze_lands(self, deck: DeckWithCards) -> dict[str, int]:
        """Analyze land types in deck."""
        land_types: dict[str, int] = {}
        basics = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}

        for card in deck.mainboard:
            if not card.card or not card.card.type or "Land" not in card.card.type:
                continue

            name = card.card_name
            text = (card.card.text or "").lower()
            type_line = card.card.type or ""

            if name in basics or "Basic" in type_line:
                category = "Basic"
            elif "search your library" in text and "land" in text:
                category = "Fetch"
            elif "pay 2 life" in text or "deals 2 damage" in text:
                category = "Shock"
            elif "enters tapped unless" in text:
                category = "Check"
            elif len([c for c in ["W", "U", "B", "R", "G"] if f"{{{c}}}" in text or c in type_line]) >= 2:
                category = "Dual"
            elif "{T}:" in (card.card.text or "") and "add" not in text:
                category = "Utility"
            else:
                category = "Other"

            land_types[category] = land_types.get(category, 0) + card.quantity

        return land_types

    def _calculate_land_colors(self, deck: DeckWithCards) -> dict[str, int]:
        """Calculate which colors lands can produce."""
        colors: dict[str, int] = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0}

        for card in deck.mainboard:
            if not card.card or not card.card.type or "Land" not in card.card.type:
                continue

            text = (card.card.text or "")
            for color in colors:
                if f"{{{color}}}" in text:
                    colors[color] += card.quantity

        return colors

    def _detect_archetype(self, deck: DeckWithCards) -> tuple[str, int, list[str]]:
        """Detect deck archetype based on card composition."""
        traits: list[str] = []

        creatures = self._count_type(deck, "Creature")
        instants = self._count_type(deck, "Instant")
        sorceries = self._count_type(deck, "Sorcery")
        lands = self._count_type(deck, "Land")

        spells = instants + sorceries
        avg_cmc = self._calculate_avg_cmc(deck)
        removal = self._count_interaction(deck)
        draw = self._count_card_draw(deck)

        # Archetype detection logic
        if creatures > 25 and avg_cmc < 2.5:
            archetype = "Aggro"
            confidence = 85
            traits = [
                f"High creature count ({creatures})",
                f"Low curve ({avg_cmc:.1f} avg)",
                "Fast clock potential",
            ]
        elif removal > 12 and draw > 6 and creatures < 15:
            archetype = "Control"
            confidence = 80
            traits = [
                f"Heavy interaction ({removal} cards)",
                f"Card advantage ({draw} draw)",
                f"Few threats ({creatures} creatures)",
            ]
        elif spells > 20 and creatures < 10:
            archetype = "Spellslinger"
            confidence = 75
            traits = [
                f"Spell-heavy ({spells} instants/sorceries)",
                f"Few creatures ({creatures})",
                "Likely combo or storm",
            ]
        elif avg_cmc > 3.5 and creatures > 15:
            archetype = "Midrange"
            confidence = 70
            traits = [
                f"Balanced curve ({avg_cmc:.1f} avg)",
                f"Solid creature base ({creatures})",
                "Value-oriented",
            ]
        elif lands > 35:
            archetype = "Lands Matter"
            confidence = 65
            traits = [
                f"Heavy land base ({lands})",
                "Land synergies likely",
            ]
        else:
            archetype = "Balanced"
            confidence = 50
            traits = [
                f"{creatures} creatures, {spells} spells",
                f"Average CMC: {avg_cmc:.1f}",
            ]

        return archetype, confidence, traits

    def _cmc_color(self, cmc: float) -> str:
        """Get color for CMC display."""
        if cmc <= 2.5:
            return "#7ec850"
        elif cmc <= 3.5:
            return "#e6c84a"
        else:
            return "#e86a58"

    def _land_color(self, lands: int, total: int) -> str:
        """Get color for land count display."""
        if total == 0:
            return "#888"
        ratio = lands / total
        if 0.33 <= ratio <= 0.42:
            return "#7ec850"
        elif 0.28 <= ratio <= 0.48:
            return "#e6c84a"
        else:
            return "#e86a58"
