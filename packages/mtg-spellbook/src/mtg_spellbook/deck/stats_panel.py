"""Real-time deck statistics display panel with ASCII art visualizations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from ..ui.theme import ui_colors

if TYPE_CHECKING:
    from ..deck_manager import DeckWithCards


# Mana color display configuration
MANA_COLORS = {
    "W": {"bg": "#F0E68C", "fg": "black", "name": "White", "symbol": "☀"},
    "U": {"bg": "#0E86D4", "fg": "white", "name": "Blue", "symbol": "💧"},
    "B": {"bg": "#6B5B7B", "fg": "white", "name": "Black", "symbol": "💀"},
    "R": {"bg": "#C7253E", "fg": "white", "name": "Red", "symbol": "🔥"},
    "G": {"bg": "#1A5D1A", "fg": "white", "name": "Green", "symbol": "🌲"},
    "C": {"bg": "#95a5a6", "fg": "black", "name": "Colorless", "symbol": "◇"},
}

# Card type configuration
TYPE_ICONS = {
    "Creature": ("⚔", "#7ec850"),
    "Instant": ("⚡", "#4a9fd8"),
    "Sorcery": ("🔥", "#4a9fd8"),
    "Artifact": ("⚙", "#9a9a9a"),
    "Enchantment": ("✨", "#b86fce"),
    "Planeswalker": ("🌟", "#e6c84a"),
    "Land": ("🏔", "#a67c52"),
    "Other": ("?", "#888888"),
}


class DeckStatsPanel(Vertical):
    """Real-time deck statistics with ASCII art visualizations.

    Features:
    - Card counts with validation colors
    - Vertical mana curve bar chart
    - Color wheel visualization with mana symbols
    - Deck composition breakdown (creatures/spells/lands)
    - Deck health indicators
    """

    DEFAULT_CSS = """
    DeckStatsPanel {
        width: 100%;
        height: auto;
        padding: 0 1;
        background: #1a1a1a;
    }

    .stats-section {
        height: auto;
        margin-bottom: 1;
    }

    .stats-header {
        text-style: bold;
        margin-bottom: 0;
    }

    .stats-content {
        height: auto;
    }
    """

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._deck: DeckWithCards | None = None

    def compose(self) -> ComposeResult:
        # Deck Overview
        with Vertical(classes="stats-section"):
            yield Static(
                f"[bold {ui_colors.GOLD_DIM}]📊 Deck Overview[/]",
                classes="stats-header",
            )
            yield Static("[dim]No deck loaded[/]", id="stats-overview")

        # Mana Curve - Vertical
        with Vertical(classes="stats-section"):
            yield Static(
                f"[bold {ui_colors.GOLD_DIM}]📈 Mana Curve[/]",
                classes="stats-header",
            )
            yield Static("", id="stats-curve")

        # Color Wheel
        with Vertical(classes="stats-section"):
            yield Static(
                f"[bold {ui_colors.GOLD_DIM}]🎨 Color Distribution[/]",
                classes="stats-header",
            )
            yield Static("", id="stats-colors")

        # Deck Composition
        with Vertical(classes="stats-section"):
            yield Static(
                f"[bold {ui_colors.GOLD_DIM}]🎯 Composition[/]",
                classes="stats-header",
            )
            yield Static("", id="stats-composition")

        # Deck Health
        with Vertical(classes="stats-section"):
            yield Static("", id="stats-health")

    def update_stats(self, deck: DeckWithCards | None) -> None:
        """Update all statistics from deck data."""
        self._deck = deck

        if deck is None:
            self._clear_stats()
            return

        self._update_overview(deck)
        self._update_mana_curve(deck)
        self._update_colors(deck)
        self._update_composition(deck)
        self._update_health(deck)

    def _clear_stats(self) -> None:
        """Clear all stats displays."""
        self.query_one("#stats-overview", Static).update("[dim]No deck loaded[/]")
        self.query_one("#stats-curve", Static).update("")
        self.query_one("#stats-colors", Static).update("")
        self.query_one("#stats-composition", Static).update("")
        self.query_one("#stats-health", Static).update("")

    def _update_overview(self, deck: DeckWithCards) -> None:
        """Update deck overview with card counts and format."""
        # Determine expected size based on format
        expected_main = 60
        format_name = deck.format or "Custom"
        if deck.format and deck.format.lower() == "commander":
            expected_main = 99 if deck.commander else 100
            format_name = "Commander"
        elif deck.format and deck.format.lower() == "standard":
            expected_main = 60
            format_name = "Standard"

        # Card count indicators
        main_count = deck.mainboard_count
        side_count = deck.sideboard_count

        if main_count >= expected_main:
            main_icon = "[green]✓[/]"
            main_color = "green"
        elif main_count >= expected_main * 0.8:
            main_icon = "[yellow]○[/]"
            main_color = "yellow"
        else:
            main_icon = "[red]✗[/]"
            main_color = "red"

        side_icon = "[green]✓[/]" if side_count <= 15 else "[red]![/]"
        side_color = "green" if side_count <= 15 else "red"

        # Build overview box
        lines = [
            f"┌{'─' * 22}┐",
            f"│ [bold]{format_name:^20}[/] │",
            f"├{'─' * 22}┤",
            f"│ {main_icon} Main:  [{main_color}]{main_count:>3}[/]/{expected_main:<3}    │",
            f"│ {side_icon} Side:  [{side_color}]{side_count:>3}[/]/15      │",
            f"└{'─' * 22}┘",
        ]

        self.query_one("#stats-overview", Static).update("\n".join(lines))

    def _update_mana_curve(self, deck: DeckWithCards) -> None:
        """Render vertical ASCII bar chart for mana curve."""
        curve: dict[int, int] = {}
        total_cmc = 0.0
        non_land_count = 0

        for card in deck.mainboard:
            if card.card:
                cmc = int(card.card.cmc or 0)
                is_land = card.card.type and "Land" in card.card.type
                if not is_land:
                    # Bucket 7+ together
                    bucket = min(cmc, 7)
                    curve[bucket] = curve.get(bucket, 0) + card.quantity
                    total_cmc += (card.card.cmc or 0) * card.quantity
                    non_land_count += card.quantity

        if not curve:
            self.query_one("#stats-curve", Static).update("[dim]No non-land cards[/]")
            return

        avg_cmc = total_cmc / non_land_count if non_land_count > 0 else 0
        max_count = max(curve.values()) if curve else 1

        # Vertical bar chart (8 rows tall max)
        max_height = 8
        bar_chars = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

        # Build vertical bars from bottom up
        rows = []

        # Scale factor to fit in max_height
        scale = max_height / max_count if max_count > 0 else 1

        # Top row: counts
        count_row = "    "
        for cmc in range(8):
            count = curve.get(cmc, 0)
            if count > 0:
                count_str = str(count) if count < 100 else "99"
                count_row += f"[dim]{count_str:>2}[/] "
            else:
                count_row += "   "
        rows.append(count_row)

        # Bar rows (from top to bottom)
        for level in range(max_height, 0, -1):
            row = "    "
            for cmc in range(8):
                count = curve.get(cmc, 0)
                bar_height = count * scale
                if bar_height >= level:
                    row += f"[bold {ui_colors.GOLD}]██[/] "
                elif bar_height >= level - 0.5:
                    # Partial fill
                    idx = int((bar_height - level + 1) * len(bar_chars))
                    idx = max(0, min(idx, len(bar_chars) - 1))
                    row += f"[{ui_colors.GOLD}]{bar_chars[idx]}{bar_chars[idx]}[/] "
                else:
                    row += "[dim]░░[/] "
            rows.append(row)

        # CMC labels
        label_row = "    "
        for cmc in range(8):
            label = f"{cmc}+" if cmc == 7 else str(cmc)
            label_row += f"[dim]{label:>2}[/] "
        rows.append(label_row)

        # Average CMC with visual indicator
        avg_indicator = "─" * int(avg_cmc * 3) + "◆"
        rows.append("")
        rows.append(f"  [dim]Avg:[/] [{ui_colors.GOLD}]{avg_cmc:.2f}[/]")
        rows.append(f"  [dim]{avg_indicator}[/]")

        self.query_one("#stats-curve", Static).update("\n".join(rows))

    def _update_colors(self, deck: DeckWithCards) -> None:
        """Update color distribution with visual wheel."""
        colors: dict[str, int] = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "C": 0}

        for card in deck.mainboard:
            if card.card and card.card.mana_cost:
                for color in colors:
                    if color == "C":
                        colors[color] += card.card.mana_cost.count("{C}") * card.quantity
                    else:
                        colors[color] += card.card.mana_cost.count(f"{{{color}}}") * card.quantity

        total_pips = sum(colors.values())
        if total_pips == 0:
            self.query_one("#stats-colors", Static).update("[dim]No colored mana[/]")
            return

        # Build color wheel visualization
        lines = []

        # Calculate percentages and build bars
        bar_width = 16
        for color_code in ["W", "U", "B", "R", "G"]:
            count = colors[color_code]
            if count == 0:
                continue

            cfg = MANA_COLORS[color_code]
            pct = count / total_pips * 100
            bar_len = int((count / total_pips) * bar_width)
            bar_len = max(1, bar_len)  # At least 1 char if present

            symbol = cfg["symbol"]
            bg = cfg["bg"]
            fg = cfg["fg"]

            # Color bar with symbol
            bar = f"[{fg} on {bg}]{symbol} " + "█" * bar_len + "[/]"
            padding = " " * (bar_width - bar_len)
            lines.append(f"{bar}{padding} {count:>2} ({pct:>4.1f}%)")

        # Colorless if present
        if colors["C"] > 0:
            cfg = MANA_COLORS["C"]
            count = colors["C"]
            pct = count / total_pips * 100
            bar_len = max(1, int((count / total_pips) * bar_width))
            lines.append(
                f"[{cfg['fg']} on {cfg['bg']}]{cfg['symbol']} "
                + "█" * bar_len
                + "[/]"
                + " " * (bar_width - bar_len)
                + f" {count:>2} ({pct:>4.1f}%)"
            )

        # Mana pip totals row
        lines.append("")
        pip_row = ""
        for c in ["W", "U", "B", "R", "G"]:
            if colors[c] > 0:
                cfg = MANA_COLORS[c]
                pip_row += f"[{cfg['fg']} on {cfg['bg']}] {c} [/]"
        if pip_row:
            lines.append(f"Pips: {pip_row} = {total_pips}")

        self.query_one("#stats-colors", Static).update("\n".join(lines))

    def _update_composition(self, deck: DeckWithCards) -> None:
        """Update deck composition with visual breakdown."""
        # Count each category
        counts: dict[str, int] = {
            "creatures": 0,
            "instants": 0,
            "sorceries": 0,
            "artifacts": 0,
            "enchantments": 0,
            "planeswalkers": 0,
            "lands": 0,
        }

        for card in deck.mainboard:
            if card.card and card.card.type:
                type_line = card.card.type
                if "Creature" in type_line:
                    counts["creatures"] += card.quantity
                elif "Instant" in type_line:
                    counts["instants"] += card.quantity
                elif "Sorcery" in type_line:
                    counts["sorceries"] += card.quantity
                elif "Artifact" in type_line:
                    counts["artifacts"] += card.quantity
                elif "Enchantment" in type_line:
                    counts["enchantments"] += card.quantity
                elif "Planeswalker" in type_line:
                    counts["planeswalkers"] += card.quantity
                elif "Land" in type_line:
                    counts["lands"] += card.quantity

        total = sum(counts.values())
        if total == 0:
            self.query_one("#stats-composition", Static).update("[dim]No cards[/]")
            return

        # Category display configuration
        display_config = [
            ("creatures", "⚔", "#7ec850", "Creature"),
            ("instants", "⚡", "#4a9fd8", "Instant"),
            ("sorceries", "🔥", "#e86a58", "Sorcery"),
            ("artifacts", "⚙", "#9a9a9a", "Artifact"),
            ("enchantments", "✨", "#b86fce", "Enchant"),
            ("planeswalkers", "🌟", "#e6c84a", "Planesw"),
            ("lands", "🏔", "#a67c52", "Land"),
        ]

        lines = []
        bar_width = 12

        for key, icon, color, label in display_config:
            count = counts[key]
            if count == 0:
                continue

            pct = count / total * 100
            bar_len = max(1, int((count / total) * bar_width))
            bar = f"[{color}]" + "█" * bar_len + "[/]" + "[dim]░[/]" * (bar_width - bar_len)
            lines.append(f"{icon} {label:8} {bar} {count:>2} ({pct:>4.1f}%)")

        # Summary row
        creatures = counts["creatures"]
        spells = counts["instants"] + counts["sorceries"]
        lands = counts["lands"]

        lines.append("")
        lines.append(
            f"[#7ec850]⚔ {creatures}[/] creatures  "
            f"[#4a9fd8]⚡ {spells}[/] spells  "
            f"[#a67c52]🏔 {lands}[/] lands"
        )

        self.query_one("#stats-composition", Static).update("\n".join(lines))

    def _update_health(self, deck: DeckWithCards) -> None:
        """Update deck health indicators."""
        # Calculate deck health metrics
        creatures = 0
        lands = 0
        card_draw = 0
        removal = 0
        ramp = 0

        # Keywords that indicate card draw
        draw_keywords = ["draw", "draws", "scry", "look at the top"]
        removal_keywords = ["destroy", "exile", "damage", "return target", "-X/-X"]
        ramp_keywords = ["add {", "search your library for a", "mana", "untap target land"]

        for card in deck.mainboard:
            if card.card:
                type_line = card.card.type or ""
                text = (card.card.text or "").lower()

                if "Creature" in type_line:
                    creatures += card.quantity
                if "Land" in type_line:
                    lands += card.quantity

                # Heuristic detection
                for kw in draw_keywords:
                    if kw in text:
                        card_draw += card.quantity
                        break
                for kw in removal_keywords:
                    if kw in text:
                        removal += card.quantity
                        break
                for kw in ramp_keywords:
                    if kw in text and "Land" not in type_line:
                        ramp += card.quantity
                        break

        total = deck.mainboard_count
        if total == 0:
            self.query_one("#stats-health", Static).update("")
            return

        # Calculate health scores
        land_ratio = lands / total if total > 0 else 0
        land_health = (
            "green"
            if 0.33 <= land_ratio <= 0.42
            else "yellow"
            if 0.28 <= land_ratio <= 0.48
            else "red"
        )

        lines = []
        lines.append(f"[bold {ui_colors.GOLD_DIM}]🏥 Deck Health[/]")

        # Health indicators as gauges
        draw_color = "green" if card_draw >= 8 else "yellow" if card_draw >= 4 else "dim"
        removal_color = "green" if removal >= 8 else "yellow" if removal >= 4 else "dim"
        ramp_color = "green" if ramp >= 8 else "yellow" if ramp >= 4 else "dim"

        indicators: list[tuple[str, int, str, str]] = [
            ("🏔 Lands", lands, land_health, f"{land_ratio:.0%}"),
            ("📚 Draw", card_draw, draw_color, ""),
            ("💥 Removal", removal, removal_color, ""),
            ("🌱 Ramp", ramp, ramp_color, ""),
        ]

        for label, count, color, extra in indicators:
            gauge = self._make_gauge(count, 15)
            extra_str = f" {extra}" if extra else ""
            lines.append(f"{label}: [{color}]{gauge}[/] {count}{extra_str}")

        self.query_one("#stats-health", Static).update("\n".join(lines))

    def _make_gauge(self, value: int, max_val: int) -> str:
        """Create a small ASCII gauge."""
        bar_len = 6
        filled_chars = int((min(value, max_val) / max_val) * bar_len) if max_val > 0 else 0
        return "█" * filled_chars + "░" * (bar_len - filled_chars)
