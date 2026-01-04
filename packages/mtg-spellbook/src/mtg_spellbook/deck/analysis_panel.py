"""Comprehensive deck analysis panel with combos, themes, and stats."""

from __future__ import annotations

import contextlib
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from textual import work
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from ..ui.theme import rarity_colors, ui_colors

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
    dominant_themes: list[tuple[str, int]]  # theme name, card count
    dominant_tribe: str | None
    keywords: list[tuple[str, int]]  # keyword -> count

    # Card synergies: (card1, card2, synergy_type)
    synergy_pairs: list[tuple[str, str, str]]

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

    # Card rarities for display (card_name -> rarity)
    card_rarities: dict[str, str]

    # Deck quality validation (Phase 12)
    curve_warnings: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    mana_base_quality: str = ""
    fixing_land_count: int = 0
    win_condition_types: list[str] = field(default_factory=list)
    tribal_strength: str = ""
    theme_strength: str = ""


# Theme descriptions - short and practical
THEME_DESCRIPTIONS: dict[str, str] = {
    "Tokens": "Go wide, trigger on creature ETB/death",
    "Graveyard": "Use graveyard as second hand",
    "Counters": "+1/+1 counters, proliferate payoffs",
    "Sacrifice": "Sac outlets + death triggers",
    "Lifegain": "Lifegain triggers, life as resource",
    "Artifacts": "Artifact synergies, metalcraft",
    "Enchantments": "Enchantress draws, constellation",
    "Spellslinger": "Prowess, magecraft, storm",
    "Tribal": "Creature type synergies",
    "Blink": "Flicker for repeated ETBs",
    "Landfall": "Land ETB triggers",
    "Control": "Answers and card advantage",
    "Aggro": "Fast clock, low curve",
    "Reanimator": "Cheat big creatures into play",
    "Voltron": "Suit up one creature, swing big",
    "Stax": "Resource denial, tax effects",
}

# Matchup advantages: theme -> (good against, weak against)
THEME_MATCHUPS: dict[str, tuple[list[str], list[str]]] = {
    "Tokens": (["Control", "Voltron"], ["Sacrifice", "Board wipes"]),
    "Graveyard": (["Control", "Aggro"], ["Graveyard hate", "Exile effects"]),
    "Counters": (["Midrange", "Control"], ["Mass removal", "Infect"]),
    "Sacrifice": (["Tokens", "Midrange"], ["Graveyard hate", "Fast aggro"]),
    "Lifegain": (["Aggro", "Burn"], ["Combo", "Infect"]),
    "Artifacts": (["Control", "Midrange"], ["Artifact hate", "Stax"]),
    "Enchantments": (["Midrange", "Control"], ["Enchantment hate"]),
    "Spellslinger": (["Midrange", "Tokens"], ["Fast aggro", "Counterspells"]),
    "Tribal": (["Midrange", "Control"], ["Board wipes", "Mass removal"]),
    "Blink": (["Removal-heavy", "Control"], ["Fast combo", "Aggro"]),
    "Landfall": (["Control", "Midrange"], ["Land destruction", "Fast aggro"]),
    "Control": (["Midrange", "Combo"], ["Fast aggro", "Go-wide"]),
    "Aggro": (["Control", "Combo"], ["Lifegain", "Board wipes"]),
    "Reanimator": (["Control", "Midrange"], ["Graveyard hate", "Exile"]),
    "Voltron": (["Control", "Combo"], ["Sacrifice", "Go-wide"]),
    "Stax": (["Combo", "Ramp"], ["Fast aggro", "Already-established boards"]),
}


class DeckAnalysisPanel(VerticalScroll):
    """Full deck analysis panel showing combos, themes, stats.

    Uses a simple single-Static approach for reliable rendering.
    """

    DEFAULT_CSS = """
    DeckAnalysisPanel {
        width: 100%;
        height: 100%;
        background: #0d0d0d;
        scrollbar-color: #c9a227;
        padding: 1 2;
    }

    DeckAnalysisPanel #analysis-content {
        width: 100%;
        height: auto;
        padding: 0;
    }

    DeckAnalysisPanel #analysis-empty {
        width: 100%;
        height: 100%;
        content-align: center middle;
    }
    """

    TIER_COLORS: ClassVar[dict[str, str]] = {
        "S": "#FFD700",
        "A": "#7EC850",
        "B": "#4A9FD8",
        "C": "#A0A0A0",
        "D": "#E86A58",
        "F": "#9B4D4D",
    }

    GRADE_COLORS: ClassVar[dict[str, str]] = {
        "S": "#FFD700",
        "A": "#50FA7B",
        "B": "#8BE9FD",
        "C": "#F1FA8C",
        "D": "#FFB86C",
        "F": "#FF5555",
    }

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._analysis: DeckAnalysis | None = None
        self._deck: DeckWithCards | None = None

    def compose(self) -> ComposeResult:
        # Create both widgets upfront - show/hide as needed
        yield Static("", id="analysis-content")
        yield Static(
            "[dim]Select a deck to view analysis[/]",
            id="analysis-empty",
        )

    def on_mount(self) -> None:
        """Hide content initially."""
        with contextlib.suppress(Exception):
            self.query_one("#analysis-content", Static).display = False

    def update_analysis(
        self,
        deck: DeckWithCards | None,
        collection_cards: set[str] | None = None,
        prices: dict[str, float] | None = None,
    ) -> None:
        """Analyze deck and update display (non-blocking)."""
        self._deck = deck

        if deck is None or deck.mainboard_count == 0:
            self._show_empty()
            return

        # Show loading state immediately
        self._show_loading()

        # Run analysis in background
        self._run_analysis(deck, collection_cards, prices)

    def _show_loading(self) -> None:
        """Show loading state while analysis runs."""
        try:
            content = self.query_one("#analysis-content", Static)
            empty = self.query_one("#analysis-empty", Static)
            empty.display = False
            content.display = True
            content.update(
                f"[bold {ui_colors.GOLD}]━━━ ⏳ Analyzing ━━━[/]\n\n"
                f"[dim]Loading deck analysis...[/]\n\n"
                f"[dim italic]Detecting combos, synergies, themes...[/]"
            )
        except Exception:
            pass

    @work(exclusive=True, group="deck_analysis")
    async def _run_analysis(
        self,
        deck: DeckWithCards,
        collection_cards: set[str] | None,
        prices: dict[str, float] | None,
    ) -> None:
        """Run deck analysis in background."""
        # Perform analysis
        self._analysis = await self._analyze_deck(deck, collection_cards, prices)

        # Update UI
        self._update_content()

    def _show_empty(self) -> None:
        """Show empty state."""
        try:
            self.query_one("#analysis-content", Static).display = False
            self.query_one("#analysis-empty", Static).display = True
        except Exception:
            pass

    def _update_content(self) -> None:
        """Update the content Static with all analysis text."""
        if not self._analysis or not self._deck:
            return

        try:
            content = self.query_one("#analysis-content", Static)
            empty = self.query_one("#analysis-empty", Static)

            # Hide empty, show content
            empty.display = False
            content.display = True

            # Build the full text content
            text = self._build_all_content()
            content.update(text)
        except Exception:
            pass

    def _build_all_content(self) -> str:
        """Build all analysis content as a single text block."""
        if not self._analysis or not self._deck:
            return ""

        a = self._analysis
        deck = self._deck
        lines: list[str] = []

        # OVERVIEW - first for context
        lines.append(self._build_overview_text(a, deck))
        lines.append("")

        # DECK SCORE
        lines.append(self._build_score_text(a, deck))
        lines.append("")

        # MANA CURVE
        lines.append(self._build_curve_text(a, deck))
        lines.append("")

        # KEYWORDS (if present)
        if a.keywords:
            lines.append(self._build_keywords_text(a))
            lines.append("")

        # DECK THEMES (if present)
        if a.dominant_themes or a.dominant_tribe:
            lines.append(self._build_deck_themes_text(a))
            lines.append("")

        # MATCHUPS (if themes detected)
        if a.dominant_themes or a.archetype in THEME_MATCHUPS:
            lines.append(self._build_matchups_text(a))
            lines.append("")

        # COMBOS (if present)
        if a.combos:
            lines.append(self._build_combos_text(a))
            lines.append("")

        # SYNERGIES (if present)
        if a.synergy_pairs:
            lines.append(self._build_synergies_text(a))
            lines.append("")

        # 17LANDS DATA (if present)
        if a.tier_counts:
            lines.append(self._build_17lands_text(a))
            lines.append("")

        # DECK HEALTH
        lines.append(self._build_health_text(a))
        lines.append("")

        # DECK QUALITY (if quality data present)
        quality_text = self._build_quality_text(a)
        if quality_text:
            lines.append(quality_text)
            lines.append("")

        # COLOR IDENTITY
        lines.append(self._build_colors_text(a))
        lines.append("")

        # KEY METRICS
        lines.append(self._build_metrics_text(a))
        lines.append("")

        # COLLECTION (if relevant)
        if a.needed_count > 0 or a.owned_count > 0:
            lines.append(self._build_collection_text(a))
            lines.append("")

        # PRICE (if available)
        if a.total_price > 0:
            lines.append(self._build_price_text(a))

        return "\n".join(lines)

    def _build_score_text(self, a: DeckAnalysis, deck: DeckWithCards) -> str:
        """Build deck score section text with compact grade display."""
        score = self._calculate_score(a, deck)
        grade = self._get_grade(score)
        grade_color = self.GRADE_COLORS.get(grade, ui_colors.TEXT_DIM)

        # Score bar
        bar_len = 20
        filled = int((score / 100) * bar_len)
        bar = f"[{grade_color}]{'█' * filled}[/][dim]{'░' * (bar_len - filled)}[/]"

        # Expected deck size based on format
        expected = 60
        if deck.format and deck.format.lower() == "commander":
            expected = 99 if deck.commander else 100

        return f"""[bold {ui_colors.GOLD}]━━━ ⚔ Deck Score ━━━[/]

[bold {grade_color}]{grade}[/]  [bold {grade_color}]{score}[/][dim]/100[/]  {bar}

📊 {a.card_count}/{expected} cards"""

    def _build_overview_text(self, a: DeckAnalysis, deck: DeckWithCards) -> str:
        """Build overview section with deck identity."""
        lines = [f"[bold {ui_colors.GOLD}]━━━ 📋 Overview ━━━[/]", ""]
        lines.append(f"[bold {ui_colors.WHITE}]{deck.name}[/]")
        lines.append("")

        # Archetype with confidence bar
        conf_len = 5
        conf_filled = int((a.archetype_confidence / 100) * conf_len)
        conf_bar = (
            f"[{ui_colors.GOLD}]{'●' * conf_filled}[/][dim]{'○' * (conf_len - conf_filled)}[/]"
        )
        lines.append(f"🎯 [{ui_colors.GOLD}]{a.archetype}[/] {conf_bar} {a.archetype_confidence}%")

        # Format
        format_name = (deck.format or "Custom").title()
        lines.append(f"📖 Format: {format_name}")

        # Commander if present
        if deck.commander:
            lines.append(f"👑 Commander: [{ui_colors.GOLD}]{deck.commander}[/]")

        return "\n".join(lines)

    def _build_colors_text(self, a: DeckAnalysis) -> str:
        """Build color identity section with mana symbols."""
        # Mana symbols and display colors
        mana_symbols = {
            "W": ("☀", "#F8E7B9", "white"),
            "U": ("💧", "#0E86D4", "blue"),
            "B": ("💀", "#9B7BB8", "black"),
            "R": ("🔥", "#E86A58", "red"),
            "G": ("🌲", "#7EC850", "green"),
        }

        lines = [f"[bold {ui_colors.GOLD}]━━━ 🎨 Color Identity ━━━[/]", ""]

        total_pips = sum(a.colors.values()) or 1

        for color in ["W", "U", "B", "R", "G"]:
            count = a.colors.get(color, 0)
            if count > 0:
                symbol, hex_color, _name = mana_symbols[color]
                pct = int((count / total_pips) * 100)
                bar_len = 12
                filled = max(1, int((count / total_pips) * bar_len))
                bar = f"[{hex_color}]{'█' * filled}[/][dim]{'░' * (bar_len - filled)}[/]"
                lines.append(f"{symbol} {color} {bar} {pct:>3}% ({count})")

        # Color identity wheel visualization
        identity_symbols = []
        for c in ["W", "U", "B", "R", "G"]:
            if a.colors.get(c, 0) > 0:
                symbol, hex_color, _ = mana_symbols[c]
                identity_symbols.append(f"[{hex_color}]●[/]")

        if identity_symbols:
            lines.append("")
            lines.append(
                f"Identity: {' '.join(identity_symbols)}  [{ui_colors.TEXT_DIM}]{total_pips} pips[/]"
            )

        return "\n".join(lines)

    def _build_metrics_text(self, a: DeckAnalysis) -> str:
        """Build key metrics section with visual bars and icons."""
        # Type icons and colors
        types = [
            ("⚔", "Creatures", a.creatures, "#7EC850"),
            ("⚡", "Instants", a.instants, "#4A9FD8"),
            ("🔥", "Sorceries", a.sorceries, "#E86A58"),
            ("⚙", "Artifacts", a.artifacts, "#9A9A9A"),
            ("✨", "Enchants", a.enchantments, "#B86FCE"),
            ("🌟", "Planeswlk", a.planeswalkers, "#E6C84A"),
            ("🏔", "Lands", a.lands, "#A67C52"),
        ]

        lines = [f"[bold {ui_colors.GOLD}]━━━ 📊 Key Metrics ━━━[/]", ""]

        # Calculate max for bar scaling
        total = sum(t[2] for t in types) or 1
        max_count = max(t[2] for t in types) or 1
        bar_width = 10

        for icon, name, count, color in types:
            if count > 0:
                bar_len = max(1, int((count / max_count) * bar_width))
                bar = f"[{color}]{'█' * bar_len}[/][dim]{'░' * (bar_width - bar_len)}[/]"
                pct = int((count / total) * 100)
                lines.append(f"{icon} {name:9} {bar} {count:>2} ({pct:>2}%)")
            else:
                lines.append(f"[dim]{icon} {name:9} {'░' * bar_width}  0[/]")

        return "\n".join(lines)

    def _build_combos_text(self, a: DeckAnalysis) -> str:
        """Build combos section showing complete and near-complete combos."""
        lines = [f"[bold {ui_colors.GOLD}]━━━ ⚡ Combos ({len(a.combos)}) ━━━[/]", ""]

        def get_rarity_color(card_name: str) -> str:
            """Get rarity color for a card name."""
            rarity = a.card_rarities.get(card_name, "").lower()
            return getattr(rarity_colors, rarity.upper(), rarity_colors.DEFAULT)

        for i, match in enumerate(a.combos[:5]):
            combo = match.combo
            score = getattr(match, "_score", 0)

            # Score color based on value
            if score >= 70:
                score_color = "#50FA7B"  # Green - excellent
            elif score >= 50:
                score_color = "#F1FA8C"  # Yellow - good
            elif score >= 30:
                score_color = "#FFB86C"  # Orange - okay
            else:
                score_color = "#6272A4"  # Dim - weak

            # Show completion status with score
            if match.is_complete:
                status = "[bold green]✓ COMPLETE[/]"
            elif match.missing_count == 1:
                status = "[yellow]1 away[/]"
            else:
                status = f"[dim]{match.missing_count} away[/]"

            lines.append(f"[bold]#{i + 1}[/] {status}  [{score_color}]{score:.0f}[/][dim]/100[/]")

            # Show cards you have (green checkmark) with rarity colors
            present_str = ", ".join(
                f"[{get_rarity_color(name)}]{name}[/]" for name in match.present_cards[:3]
            )
            if len(match.present_cards) > 3:
                present_str += f" [dim]+{len(match.present_cards) - 3}[/]"
            lines.append(f"   [green]✓[/] {present_str}")

            # Show missing cards (red X) with rarity colors
            if match.missing_cards:
                missing_str = ", ".join(
                    f"[{get_rarity_color(name)}]{name}[/]" for name in match.missing_cards[:2]
                )
                if len(match.missing_cards) > 2:
                    missing_str += f" [dim]+{len(match.missing_cards) - 2}[/]"
                lines.append(f"   [red]✗[/] {missing_str}")

            # Result
            produces = ", ".join(combo.produces[:2]) if combo.produces else "Value"
            lines.append(f"   [dim]→[/] [italic #7EC850]{produces}[/]")
            lines.append("")

        if len(a.combos) > 5:
            lines.append(f"[dim]...and {len(a.combos) - 5} more combos[/]")

        return "\n".join(lines)

    def _build_17lands_text(self, a: DeckAnalysis) -> str:
        """Build 17lands data section with tier distribution."""
        lines = [f"[bold {ui_colors.GOLD}]━━━ 📊 Gameplay Data ━━━[/]", ""]

        # Tier distribution with visual boxes
        tier_line = "  "
        for tier in ["S", "A", "B", "C", "D", "F"]:
            count = a.tier_counts.get(tier, 0)
            color = self.TIER_COLORS.get(tier, "#888")
            if count > 0:
                tier_line += f"[{color} on #1a1a1a] {tier}:{count:>2} [/] "
            else:
                tier_line += f"[dim] {tier}:·  [/] "
        lines.append(tier_line)
        lines.append("")

        # Top performers with stars
        if a.top_cards:
            lines.append("[dim]★ Top performers:[/]")
            for name, tier, wr in a.top_cards[:4]:
                tier_color = self.TIER_COLORS.get(tier, "#888")
                wr_str = f" [{ui_colors.GOLD}]{wr:.0%}[/]" if wr else ""
                short_name = name[:18] if len(name) > 18 else name
                lines.append(f"  [{tier_color}]★{tier}[/] {short_name}{wr_str}")

        return "\n".join(lines)

    def _build_deck_themes_text(self, a: DeckAnalysis) -> str:
        """Build deck themes section."""
        lines = [f"[bold {ui_colors.GOLD}]━━━ 🎭 Deck Themes ━━━[/]", ""]

        # Tribal
        if a.dominant_tribe:
            lines.append(f"👥 Tribal: [{ui_colors.GOLD}]{a.dominant_tribe}[/]")
            tribe_desc = THEME_DESCRIPTIONS.get("Tribal", "")
            if tribe_desc:
                lines.append(f"   [italic dim]{tribe_desc}[/]")
            lines.append("")

        # Themes with engaging descriptions and counts
        if a.dominant_themes:
            for theme, count in a.dominant_themes[:4]:
                desc = THEME_DESCRIPTIONS.get(theme, "")
                lines.append(f"  [{ui_colors.GOLD}]{theme}[/] [dim]({count} cards)[/]")
                if desc:
                    lines.append(f"    [italic dim]{desc}[/]")

        return "\n".join(lines)

    def _build_matchups_text(self, a: DeckAnalysis) -> str:
        """Build matchups section based on themes and archetype."""
        lines = [f"[bold {ui_colors.GOLD}]━━━ ⚔ Matchups ━━━[/]", ""]

        strengths: set[str] = set()
        weaknesses: set[str] = set()

        # Add archetype matchups
        if a.archetype in THEME_MATCHUPS:
            good, bad = THEME_MATCHUPS[a.archetype]
            strengths.update(good[:2])
            weaknesses.update(bad[:2])

        # Add theme matchups
        for theme, _ in a.dominant_themes[:3]:
            if theme in THEME_MATCHUPS:
                good, bad = THEME_MATCHUPS[theme]
                strengths.update(good[:2])
                weaknesses.update(bad[:2])

        if strengths:
            strength_str = ", ".join(sorted(strengths)[:4])
            lines.append(f"  [green]✓ Strong vs:[/] {strength_str}")
        if weaknesses:
            weak_str = ", ".join(sorted(weaknesses)[:4])
            lines.append(f"  [red]✗ Weak to:[/] {weak_str}")

        if not strengths and not weaknesses:
            lines.append(f"  [{ui_colors.TEXT_DIM}]No specific matchup data[/]")

        return "\n".join(lines)

    def _build_synergies_text(self, a: DeckAnalysis) -> str:
        """Build synergies section with grouped card synergies and keywords."""
        lines = [f"[bold {ui_colors.GOLD}]━━━ 🔗 Synergies ━━━[/]", ""]

        # Group synergies by type for cleaner display
        if a.synergy_pairs:
            # Categorize synergies
            synergy_icons = {
                "Gameplay Data": ("📊", "#50FA7B"),  # Data-driven - green
                "death": ("💀", "#9B7BB8"),
                "Flying": ("🕊", "#8BE9FD"),
                "Lifelink": ("❤", "#FF79C6"),
                "ETB": ("✨", "#F1FA8C"),
                "sacrifice": ("🩸", "#FF5555"),
                "token": ("👥", "#FFB86C"),
                "counter": ("⬆", "#50FA7B"),
                "draw": ("📚", "#8BE9FD"),
            }

            # Group by normalized reason
            grouped: dict[str, list[tuple[str, str]]] = {}
            for card1, card2, reason in a.synergy_pairs:
                # Normalize reason to category
                reason_lower = reason.lower()
                if "gameplay" in reason_lower or "wr together" in reason_lower:
                    category = "Gameplay Data"
                elif "death" in reason_lower or "dies" in reason_lower:
                    category = "Death triggers"
                elif "flying" in reason_lower:
                    category = "Flying"
                elif "lifelink" in reason_lower or "life gain" in reason_lower:
                    category = "Lifegain"
                elif "etb" in reason_lower or "enters" in reason_lower:
                    category = "ETB effects"
                elif "sacrifice" in reason_lower:
                    category = "Sacrifice"
                elif "token" in reason_lower:
                    category = "Tokens"
                elif "counter" in reason_lower:
                    category = "Counters"
                else:
                    category = reason.split(":")[0] if ":" in reason else "Other"

                if category not in grouped:
                    grouped[category] = []
                # Avoid duplicate pairs
                pair = (min(card1, card2), max(card1, card2))
                if pair not in [(min(c1, c2), max(c1, c2)) for c1, c2 in grouped[category]]:
                    grouped[category].append((card1, card2))

            # Display grouped synergies - sorted by pair count descending
            sorted_groups = sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True)
            for category, pairs in sorted_groups[:6]:
                # Get icon and color for category
                icon, color = "⚡", ui_colors.SYNERGY_STRONG
                for key, (i, c) in synergy_icons.items():
                    if key.lower() in category.lower():
                        icon, color = i, c
                        break

                lines.append(f"{icon} [{color}]{category}[/] [dim]({len(pairs)} pairs)[/]")
                for card1, card2 in pairs[:3]:  # Show max 3 pairs per category
                    c1 = card1[:16] + "…" if len(card1) > 17 else card1
                    c2 = card2[:16] + "…" if len(card2) > 17 else card2
                    lines.append(f"   [{ui_colors.TEXT_DIM}]{c1} + {c2}[/]")
                if len(pairs) > 3:
                    lines.append(f"   [dim]...+{len(pairs) - 3} more[/]")
            lines.append("")

        return "\n".join(lines)

    def _build_keywords_text(self, a: DeckAnalysis) -> str:
        """Build keywords section."""
        lines = [f"[bold {ui_colors.GOLD}]━━━ 🔑 Keywords ━━━[/]", ""]

        for kw, count in a.keywords[:8]:
            bar_len = min(8, count)
            bar = f"[{ui_colors.GOLD}]{'▪' * bar_len}[/]"
            lines.append(f"  {kw:14} {bar} {count}")

        return "\n".join(lines)

    def _build_curve_text(self, a: DeckAnalysis, deck: DeckWithCards) -> str:
        """Build mana curve with visual vertical bar chart."""
        lines = [f"[bold {ui_colors.GOLD}]━━━ 📈 Mana Curve ━━━[/]", ""]

        # Calculate curve
        curve: dict[int, int] = dict.fromkeys(range(8), 0)
        for card in deck.mainboard:
            if card.card and "Land" not in (card.card.type or ""):
                cmc = min(int(card.card.cmc or 0), 7)
                curve[cmc] += card.quantity

        max_count = max(curve.values()) if curve.values() else 1
        bar_height = 6

        # Count row at top
        count_row = "  "
        for cmc in range(8):
            count = curve[cmc]
            if count > 0:
                count_row += f"[{ui_colors.GOLD}]{count:>2}[/] "
            else:
                count_row += "[dim] ·[/] "
        lines.append(count_row)

        # Build visual bars from top to bottom
        for level in range(bar_height, 0, -1):
            row = "  "
            for cmc in range(8):
                count = curve[cmc]
                fill_level = (count / max_count) * bar_height if max_count > 0 else 0
                if fill_level >= level:
                    row += f"[bold {ui_colors.GOLD}]██[/] "
                elif fill_level >= level - 0.5 and count > 0:
                    row += f"[{ui_colors.GOLD}]▄▄[/] "
                else:
                    row += "[dim]░░[/] "
            lines.append(row)

        # X-axis labels
        lines.append("  0  1  2  3  4  5  6  7+")

        # Average CMC with visual indicator
        lines.append("")
        avg_bar_pos = int(min(a.avg_cmc, 7) * 3) + 2
        avg_indicator = " " * avg_bar_pos + f"[{ui_colors.GOLD}]▲[/]"
        lines.append(avg_indicator)
        lines.append(f"  Average: [{ui_colors.GOLD}]{a.avg_cmc:.2f}[/] CMC")

        # Spell count
        spell_count = sum(curve.values())
        lines.append(f"  Spells: {spell_count}")

        return "\n".join(lines)

    def _build_health_text(self, a: DeckAnalysis) -> str:
        """Build deck health section with visual gauges."""
        lines = [f"[bold {ui_colors.GOLD}]━━━ 🏥 Deck Health ━━━[/]", ""]

        total = a.card_count
        land_pct = int((a.lands / total) * 100) if total > 0 else 0

        # Health metrics with gauges
        metrics = [
            ("🏔 Lands", a.lands, 24, land_pct, 35 <= land_pct <= 42, 30 <= land_pct <= 45),
            (
                "💥 Interaction",
                a.interaction_count,
                15,
                None,
                a.interaction_count >= 10,
                a.interaction_count >= 6,
            ),
            ("📚 Card Draw", a.draw_count, 12, None, a.draw_count >= 8, a.draw_count >= 4),
            ("🌱 Ramp", a.ramp_count, 12, None, a.ramp_count >= 8, a.ramp_count >= 4),
        ]

        for label, count, max_val, pct_val, is_good, is_ok in metrics:
            # Gauge bar
            gauge_len = 8
            filled = min(gauge_len, int((count / max_val) * gauge_len)) if max_val > 0 else 0

            if is_good:
                icon = "[green]✓[/]"
                bar_color = "green"
                status = ""
            elif is_ok:
                icon = "[yellow]~[/]"
                bar_color = "yellow"
                status = ""
            else:
                icon = "[red]✗[/]"
                bar_color = "red"
                status = " [dim](low)[/]"

            bar = f"[{bar_color}]{'█' * filled}[/][dim]{'░' * (gauge_len - filled)}[/]"
            pct_str = f" ({pct_val}%)" if pct_val is not None else ""
            lines.append(f"{icon} {label:12} {bar} {count:>2}{pct_str}{status}")

        return "\n".join(lines)

    def _build_quality_text(self, a: DeckAnalysis) -> str:
        """Build deck quality section with validation results."""
        lines = [f"[bold {ui_colors.GOLD}]--- Deck Quality ---[/]", ""]

        # Quality grade
        if a.quality_score > 0:
            grade, color = self._get_quality_grade(a.quality_score)
            lines.append(f"Grade: [{color}]{grade}[/] ({a.quality_score:.0%})")

        # Mana base quality
        if a.mana_base_quality:
            if a.mana_base_quality == "excellent":
                mana_color = "green"
            elif a.mana_base_quality == "good":
                mana_color = "yellow"
            else:
                mana_color = "red"
            mana_str = f"Mana Base: [{mana_color}]{a.mana_base_quality.title()}[/]"
            if a.fixing_land_count > 0:
                mana_str += f" ({a.fixing_land_count} fixing lands)"
            lines.append(mana_str)

        # Win conditions
        if a.win_condition_types:
            lines.append(f"Win Conditions: {', '.join(a.win_condition_types)}")

        # Synergy strengths
        if a.tribal_strength and a.tribal_strength != "minimal":
            lines.append(f"Tribal: {a.tribal_strength.title()}")
        if a.theme_strength and a.theme_strength != "minimal":
            lines.append(f"Theme: {a.theme_strength.title()}")

        # Curve warnings
        if a.curve_warnings:
            lines.append("")
            lines.append("[red]Warnings:[/]")
            for warning in a.curve_warnings[:3]:
                lines.append(f"  - {warning}")

        return "\n".join(lines) if len(lines) > 2 else ""

    def _build_collection_text(self, a: DeckAnalysis) -> str:
        """Build collection section with progress visualization."""
        lines = [f"[bold {ui_colors.GOLD}]--- Collection ---[/]", ""]

        total = a.owned_count + a.needed_count
        owned_pct = int((a.owned_count / total) * 100) if total > 0 else 0

        # Large progress bar
        bar_len = 24
        filled = int((a.owned_count / total) * bar_len) if total > 0 else 0

        # Color based on completion
        if owned_pct >= 90:
            bar_color = "green"
        elif owned_pct >= 50:
            bar_color = "yellow"
        else:
            bar_color = "red"

        bar = f"[{bar_color}]{'█' * filled}[/][dim]{'░' * (bar_len - filled)}[/]"
        lines.append(f"  {bar} {owned_pct}%")
        lines.append("")

        lines.append(f"  [green]✓[/] {a.owned_count} owned")

        if a.needed_count == 0:
            lines.append("  [bold green]🎉 Complete![/]")
        else:
            lines.append(f"  [yellow]⚠[/] {a.needed_count} cards needed")

        return "\n".join(lines)

    def _build_price_text(self, a: DeckAnalysis) -> str:
        """Build price section with cost breakdown."""
        lines = [f"[bold {ui_colors.GOLD}]━━━ 💰 Price ━━━[/]", ""]

        # Price tier colors
        if a.total_price < 50:
            price_color = "#7EC850"
            tier = "Budget"
        elif a.total_price < 150:
            price_color = "#E6C84A"
            tier = "Moderate"
        elif a.total_price < 500:
            price_color = "#FFB86C"
            tier = "Expensive"
        else:
            price_color = "#FF5555"
            tier = "Premium"

        lines.append(f"  [bold {price_color}]${a.total_price:.0f}[/] [dim]({tier})[/]")
        lines.append("")

        if a.expensive_cards:
            lines.append("[dim]💎 Most expensive:[/]")
            for name, price in a.expensive_cards[:4]:
                short = name[:18] if len(name) > 18 else name
                lines.append(f"  ${price:>6.0f}  {short}")

        return "\n".join(lines)

    def _calculate_score(self, a: DeckAnalysis, _deck: DeckWithCards) -> int:
        """Calculate overall deck score 0-100."""
        score = 0

        # Card count (max 20 points)
        if a.card_count >= 60:
            score += 20
        else:
            score += int((a.card_count / 60) * 20)

        # Land ratio (max 15 points)
        land_ratio = a.lands / a.card_count if a.card_count > 0 else 0
        if 0.35 <= land_ratio <= 0.42:
            score += 15
        elif 0.30 <= land_ratio <= 0.45:
            score += 10
        else:
            score += 5

        # Mana curve (max 15 points)
        if a.avg_cmc <= 3.5:
            score += 15
        elif a.avg_cmc <= 4.0:
            score += 10
        else:
            score += 5

        # Interaction (max 15 points)
        if a.interaction_count >= 10:
            score += 15
        elif a.interaction_count >= 6:
            score += 10
        else:
            score += int((a.interaction_count / 10) * 15)

        # Draw (max 10 points)
        if a.draw_count >= 8:
            score += 10
        else:
            score += int((a.draw_count / 8) * 10)

        # Ramp (max 10 points)
        if a.ramp_count >= 8:
            score += 10
        else:
            score += int((a.ramp_count / 8) * 10)

        # Combos (max 10 points)
        if a.combos:
            score += min(10, len(a.combos) * 3)

        # 17Lands quality (max 5 points)
        high_tier = a.tier_counts.get("S", 0) + a.tier_counts.get("A", 0)
        if high_tier >= 10:
            score += 5
        elif high_tier >= 5:
            score += 3

        return min(100, score)

    def _get_grade(self, score: int) -> str:
        """Convert score to letter grade."""
        if score >= 90:
            return "S"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        return "F"

    def _get_quality_grade(self, quality_score: float) -> tuple[str, str]:
        """Get letter grade and color for quality score."""
        if quality_score >= 0.9:
            return "A+", "green"
        elif quality_score >= 0.8:
            return "A", "green"
        elif quality_score >= 0.7:
            return "B+", "cyan"
        elif quality_score >= 0.6:
            return "B", "cyan"
        elif quality_score >= 0.5:
            return "C+", "yellow"
        elif quality_score >= 0.4:
            return "C", "yellow"
        elif quality_score >= 0.3:
            return "D", "orange1"
        else:
            return "F", "red"

    async def _analyze_deck(
        self,
        deck: DeckWithCards,
        collection_cards: set[str] | None = None,
        prices: dict[str, float] | None = None,
    ) -> DeckAnalysis:
        """Perform complete deck analysis."""
        prices = prices or {}
        collection_cards = collection_cards or set()

        # Basic counts
        card_count = deck.mainboard_count
        land_count = 0
        total_cmc: float = 0.0
        spell_count = 0

        # Type counts
        creatures = 0
        instants = 0
        sorceries = 0
        artifacts = 0
        enchantments = 0
        planeswalkers = 0
        lands = 0

        # Color counts
        colors: dict[str, int] = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0}

        # Health metrics
        interaction_count = 0
        draw_count = 0
        ramp_count = 0

        # Keywords
        keyword_counter: Counter[str] = Counter()

        # Tribe detection
        tribe_counter: Counter[str] = Counter()

        # Collection tracking
        owned_count = 0
        needed_count = 0

        # Price tracking
        total_price = 0.0
        card_prices: list[tuple[str, float]] = []

        # Process each card
        for card_data in deck.mainboard:
            card = card_data.card
            qty = card_data.quantity

            if not card:
                continue

            card_type = card.type or ""

            # Type classification
            if "Land" in card_type:
                lands += qty
                land_count += qty
            else:
                if card.cmc is not None:
                    total_cmc += card.cmc * qty
                    spell_count += qty

            if "Creature" in card_type:
                creatures += qty
            if "Instant" in card_type:
                instants += qty
            if "Sorcery" in card_type:
                sorceries += qty
            if "Artifact" in card_type:
                artifacts += qty
            if "Enchantment" in card_type:
                enchantments += qty
            if "Planeswalker" in card_type:
                planeswalkers += qty

            # Color pips
            if card.mana_cost:
                for color in "WUBRG":
                    colors[color] += card.mana_cost.count(f"{{{color}}}") * qty

            # Keywords
            if card.keywords:
                for kw in card.keywords:
                    keyword_counter[kw] += qty

            # Tribe detection
            if "Creature" in card_type and card.type and "—" in card.type:
                subtypes = card.type.split("—")[1].strip().split()
                for subtype in subtypes:
                    if subtype not in ("Legendary", "Token", "Basic"):
                        tribe_counter[subtype] += qty

            # Health detection
            text = (card.text or "").lower()

            # Interaction
            if any(
                word in text
                for word in [
                    "destroy",
                    "exile",
                    "counter",
                    "damage",
                    "return",
                    "-1/-1",
                    "sacrifice",
                ]
            ):
                interaction_count += qty

            # Draw
            if any(word in text for word in ["draw", "scry", "look at"]):
                draw_count += qty

            # Ramp
            if any(
                word in text
                for word in [
                    "add {",
                    "add one mana",
                    "search your library for a",
                    "mana of any",
                ]
            ):
                ramp_count += qty

            # Collection status
            if card_data.card_name in collection_cards:
                owned_count += qty
            else:
                needed_count += qty

            # Price
            price = prices.get(card_data.card_name, 0)
            if price > 0:
                total_price += price * qty
                card_prices.append((card_data.card_name, price))

        # Calculate averages
        avg_cmc = total_cmc / spell_count if spell_count > 0 else 0

        # Archetype detection
        archetype, confidence = self._detect_archetype(
            creatures, instants, sorceries, lands, avg_cmc, card_count
        )

        # Theme detection
        themes = self._detect_themes(deck)

        # Card synergy detection
        synergy_pairs = self._detect_synergies(deck)

        # Dominant tribe
        dominant_tribe = tribe_counter.most_common(1)[0][0] if tribe_counter else None
        if dominant_tribe and tribe_counter[dominant_tribe] < 8:
            dominant_tribe = None

        # Top keywords
        top_keywords = keyword_counter.most_common(10)

        # Build card rarities dict from deck cards
        card_rarities: dict[str, str] = {}
        for card_data in deck.mainboard:
            if card_data.card and card_data.card.rarity:
                card_rarities[card_data.card_name] = card_data.card.rarity

        # Get combos
        combos = await self._detect_combos(deck)

        # Look up rarities for any missing combo cards not in the deck
        self._fill_missing_rarities(combos, card_rarities)

        # 17Lands data
        tier_counts, top_cards = self._get_17lands_data(deck)

        # Most expensive cards
        card_prices.sort(key=lambda x: -x[1])
        expensive_cards = card_prices[:5]

        # Deck quality validation (Phase 12)
        curve_warnings: list[str] = []
        quality_score = 0.0
        mana_base_quality = ""
        fixing_land_count = 0
        win_condition_types: list[str] = []
        tribal_strength = ""
        theme_strength = ""

        # Calculate quality metrics
        quality_score, curve_warnings, mana_base_quality, fixing_land_count = (
            self._calculate_quality_metrics(deck, avg_cmc, colors, lands, card_count, archetype)
        )

        # Detect win conditions
        win_condition_types = self._detect_win_conditions(deck)

        # Assess tribal strength if dominant tribe present
        if dominant_tribe and tribe_counter:
            tribal_count = tribe_counter[dominant_tribe]
            tribal_strength = self._assess_tribal_strength(tribal_count)

        # Assess theme strength based on dominant themes
        if themes:
            _top_theme_name, top_theme_count = themes[0]
            theme_strength = self._assess_theme_strength(top_theme_count)

        return DeckAnalysis(
            card_count=card_count,
            land_count=land_count,
            avg_cmc=avg_cmc,
            colors={c: v for c, v in colors.items() if v > 0},
            creatures=creatures,
            instants=instants,
            sorceries=sorceries,
            artifacts=artifacts,
            enchantments=enchantments,
            planeswalkers=planeswalkers,
            lands=lands,
            interaction_count=interaction_count,
            draw_count=draw_count,
            ramp_count=ramp_count,
            archetype=archetype,
            archetype_confidence=confidence,
            dominant_themes=themes,
            dominant_tribe=dominant_tribe,
            keywords=top_keywords,
            synergy_pairs=synergy_pairs,
            combos=combos,
            tier_counts=tier_counts,
            top_cards=top_cards,
            owned_count=owned_count,
            needed_count=needed_count,
            total_price=total_price,
            expensive_cards=expensive_cards,
            card_rarities=card_rarities,
            curve_warnings=curve_warnings,
            quality_score=quality_score,
            mana_base_quality=mana_base_quality,
            fixing_land_count=fixing_land_count,
            win_condition_types=win_condition_types,
            tribal_strength=tribal_strength,
            theme_strength=theme_strength,
        )

    def _detect_archetype(
        self,
        creatures: int,
        instants: int,
        sorceries: int,
        _lands: int,
        avg_cmc: float,
        total: int,
    ) -> tuple[str, int]:
        """Detect deck archetype."""
        if total == 0:
            return "Unknown", 0

        creature_ratio = creatures / total
        spell_ratio = (instants + sorceries) / total

        if creature_ratio > 0.4 and avg_cmc < 2.5:
            return "Aggro", 85
        elif creature_ratio > 0.35 and avg_cmc < 3.0:
            return "Low Curve", 65
        elif spell_ratio > 0.4:
            return "Control", 70
        elif creature_ratio > 0.3 and spell_ratio > 0.25:
            return "Midrange", 60
        elif avg_cmc > 4.0:
            return "Ramp", 55
        else:
            return "Mixed", 40

    def _detect_themes(self, deck: DeckWithCards) -> list[tuple[str, int]]:
        """Detect deck themes from card text, returning theme and card count."""
        themes: Counter[str] = Counter()
        theme_patterns = {
            "Tokens": r"create.*token|token.*creature|populate",
            "Graveyard": r"graveyard|return.*from.*graveyard|mill|flashback|unearth",
            "Counters": r"\+1/\+1 counter|proliferate|counter.*creature",
            "Sacrifice": r"sacrifice|when.*dies|whenever.*dies|aristocrat",
            "Lifegain": r"gain.*life|lifelink|whenever you gain life",
            "Artifacts": r"artifact.*enters|for each artifact|metalcraft|affinity",
            "Enchantments": r"enchantment.*enters|constellation|whenever.*enchantment",
            "Spellslinger": r"whenever you cast.*instant|whenever you cast.*sorcery|prowess|magecraft",
            "Blink": r"exile.*return|flicker|enters the battlefield",
            "Landfall": r"land.*enters|landfall|play.*additional land",
            "Reanimator": r"return.*graveyard.*battlefield|reanimate|unearth",
            "Voltron": r"equipment|aura|attach|equipped creature|enchanted creature",
        }

        for card_data in deck.mainboard:
            if not card_data.card or not card_data.card.text:
                continue
            text = card_data.card.text.lower()
            for theme, pattern in theme_patterns.items():
                if re.search(pattern, text, re.IGNORECASE):
                    themes[theme] += card_data.quantity

        # Return themes with at least 4 cards, as (theme, count) tuples
        return [(theme, count) for theme, count in themes.most_common(4) if count >= 4]

    def _detect_synergies(self, deck: DeckWithCards) -> list[tuple[str, str, str]]:
        """Detect card-to-card synergies using mtg_core and 17Lands data."""
        synergies: list[tuple[str, str, str]] = []
        seen_pairs: set[tuple[str, str]] = set()

        def add_pair(card1: str, card2: str, reason: str) -> None:
            """Add a synergy pair if not already seen."""
            pair = (min(card1, card2), max(card1, card2))
            if pair not in seen_pairs and card1 != card2:
                seen_pairs.add(pair)
                synergies.append((card1, card2, reason))

        # 1. Check 17Lands synergy data first (data-driven synergies)
        try:
            from mtg_core.tools.recommendations.gameplay import GameplayDB

            db = GameplayDB()
            if db.is_available:
                card_names = {c.card_name for c in deck.mainboard}

                # Query synergy pairs that have both cards in the deck
                for card_data in deck.mainboard:
                    pairs = db.get_synergy_pairs(card_data.card_name)
                    for pair in pairs:
                        if (
                            pair.card_b in card_names
                            and pair.synergy_lift
                            and pair.synergy_lift > 0.02
                        ):
                            lift_pct = int(pair.synergy_lift * 100)
                            add_pair(
                                pair.card_a,
                                pair.card_b,
                                f"Gameplay: +{lift_pct}% WR together",
                            )
        except (ImportError, AttributeError, Exception):
            pass  # get_synergy_pairs may not exist yet

        # 2. Pattern-based synergies from mtg_core
        try:
            from mtg_core.tools.synergy import ABILITY_SYNERGIES, KEYWORD_SYNERGIES
        except ImportError:
            return synergies[:12]

        # Build card index: card_name -> text_lower
        card_index: dict[str, str] = {}
        for card_data in deck.mainboard:
            if card_data.card and card_data.card.text:
                card_index[card_data.card_name] = card_data.card.text.lower()

        # Check each card for ability synergies
        for card_data in deck.mainboard:
            if not card_data.card or not card_data.card.text:
                continue

            card_name = card_data.card_name
            card_text = card_data.card.text.lower()

            # Check ability patterns
            for pattern, search_terms in ABILITY_SYNERGIES.items():
                if re.search(pattern, card_text, re.IGNORECASE):
                    for search_term, reason in search_terms:
                        for other_name, other_text in card_index.items():
                            if other_name != card_name and re.search(
                                search_term, other_text, re.IGNORECASE
                            ):
                                add_pair(card_name, other_name, reason)

            # Check keyword synergies
            if card_data.card.keywords:
                for keyword in card_data.card.keywords:
                    if keyword in KEYWORD_SYNERGIES:
                        for search_term, reason in KEYWORD_SYNERGIES[keyword]:
                            for other_name, other_text in card_index.items():
                                if other_name != card_name and re.search(
                                    search_term, other_text, re.IGNORECASE
                                ):
                                    add_pair(card_name, other_name, f"{keyword}: {reason}")

        return synergies[:12]

    async def _detect_combos(self, deck: DeckWithCards) -> list[SpellbookComboMatch]:
        """Detect complete and near-complete combos in the deck.

        Shows combos the user has or is close to completing (missing 1-2 cards).
        This helps with deck building by suggesting what cards to add.
        """
        try:
            from mtg_core.tools.recommendations.spellbook_combos import (
                get_spellbook_detector,
            )

            detector = await get_spellbook_detector()
            card_names = [c.card_name for c in deck.mainboard]

            # Include commander if present
            if deck.commander:
                card_names.append(deck.commander)

            # Find combos missing 0-2 pieces (complete + near-complete)
            # min_present=1 so 2-card combos show when you have 1 piece
            matches, _ = await detector.find_missing_pieces(
                card_names,
                max_missing=2,  # Show combos missing up to 2 cards
                min_present=1,  # Include 2-card combos where you have 1 piece
            )

            # Score each combo and sort by: missing_count first, then score
            # This way complete combos come first, but within each tier
            # the best combos (by score) are shown
            for match in matches:
                match._score = detector.get_combo_score(match.combo)  # type: ignore[attr-defined]

            matches.sort(key=lambda m: (m.missing_count, -getattr(m, "_score", 0)))

            return matches[:10]  # Return top 10
        except (ImportError, Exception):
            return []

    def _fill_missing_rarities(
        self, matches: list[SpellbookComboMatch], card_rarities: dict[str, str]
    ) -> None:
        """Look up rarities for missing combo cards from the card database."""
        import sqlite3

        from mtg_core.config import get_settings

        # Collect all missing card names that we don't have rarity for
        missing_names: set[str] = set()
        for match in matches:
            for card_name in match.missing_cards:
                if card_name not in card_rarities:
                    missing_names.add(card_name)

        if not missing_names:
            return

        # Query the database for these cards
        try:
            db_path = get_settings().mtg_db_path
            if not db_path.exists():
                return

            conn = sqlite3.connect(db_path)
            placeholders = ",".join("?" * len(missing_names))
            query = f"""
                SELECT name, rarity
                FROM cards
                WHERE name IN ({placeholders})
                AND rarity IS NOT NULL
                GROUP BY name
            """
            cursor = conn.execute(query, list(missing_names))
            for name, rarity in cursor:
                card_rarities[name] = rarity
            conn.close()
        except Exception:
            pass  # Fail silently, cards will just use default color

    def _get_17lands_data(
        self, deck: DeckWithCards
    ) -> tuple[dict[str, int], list[tuple[str, str, float | None]]]:
        """Get 17Lands tier data for deck cards."""
        tier_counts: dict[str, int] = {}
        top_cards: list[tuple[str, str, float | None]] = []

        try:
            from mtg_core.tools.recommendations.gameplay import GameplayDB

            db = GameplayDB()
            for card_data in deck.mainboard:
                stats = db.get_card_stats(card_data.card_name)
                if stats and stats.tier:
                    tier = stats.tier.upper()
                    tier_counts[tier] = tier_counts.get(tier, 0) + card_data.quantity
                    if tier in ("S", "A") and len(top_cards) < 5:
                        top_cards.append((card_data.card_name, tier, stats.gih_wr))
        except (ImportError, Exception):
            pass

        return tier_counts, top_cards

    def _calculate_quality_metrics(
        self,
        deck: DeckWithCards,
        avg_cmc: float,
        colors: dict[str, int],
        lands: int,
        card_count: int,
        archetype: str,
    ) -> tuple[float, list[str], str, int]:
        """Calculate deck quality metrics based on deck_finder validation patterns.

        Returns:
            (quality_score, curve_warnings, mana_base_quality, fixing_land_count)
        """
        curve_warnings: list[str] = []
        quality_score = 1.0
        mana_base_quality = ""
        fixing_land_count = 0

        # Curve thresholds by archetype
        curve_thresholds = {
            "Aggro": {"avg_cmc_max": 2.5, "low_cmc_ratio_min": 0.50},
            "Low Curve": {"avg_cmc_max": 3.0, "low_cmc_ratio_min": 0.40},
            "Control": {"avg_cmc_max": 4.0, "low_cmc_ratio_min": 0.20},
            "Midrange": {"avg_cmc_max": 3.5, "low_cmc_ratio_min": 0.30},
            "Ramp": {"avg_cmc_max": 4.5, "low_cmc_ratio_min": 0.15},
            "_default": {"avg_cmc_max": 3.5, "low_cmc_ratio_min": 0.25},
        }

        # Get thresholds for this archetype
        thresholds = curve_thresholds.get(archetype, curve_thresholds["_default"])

        # Calculate low CMC ratio
        non_land_count = 0
        low_cmc_count = 0
        for card_data in deck.mainboard:
            card = card_data.card
            if card and "Land" not in (card.type or ""):
                non_land_count += card_data.quantity
                if card.cmc is not None and card.cmc <= 2:
                    low_cmc_count += card_data.quantity

        low_cmc_ratio = low_cmc_count / non_land_count if non_land_count > 0 else 0

        # Validate curve
        if avg_cmc > thresholds["avg_cmc_max"]:
            curve_warnings.append(f"High avg CMC ({avg_cmc:.1f} > {thresholds['avg_cmc_max']})")
            quality_score -= 0.15

        if low_cmc_ratio < thresholds["low_cmc_ratio_min"]:
            curve_warnings.append(
                f"Low early game ({low_cmc_ratio:.0%} < "
                f"{thresholds['low_cmc_ratio_min']:.0%} at CMC 1-2)"
            )
            quality_score -= 0.1

        # Validate mana base for multi-color decks
        num_colors = len([c for c, v in colors.items() if v > 0])
        if num_colors >= 2:
            # Count fixing lands (dual lands, fetch lands, etc.)
            fixing_land_count = self._count_fixing_lands(deck)

            # Color fixing requirements by number of colors
            color_fixing_reqs = {1: 0, 2: 6, 3: 12, 4: 18, 5: 22}
            required = color_fixing_reqs.get(num_colors, 12)

            if fixing_land_count >= int(required * 1.2):
                mana_base_quality = "excellent"
                quality_score += 0.05
            elif fixing_land_count >= required:
                mana_base_quality = "good"
            elif fixing_land_count >= int(required * 0.5):
                mana_base_quality = "poor"
                quality_score -= 0.1
            else:
                mana_base_quality = "critical"
                curve_warnings.append(
                    f"Low color fixing ({fixing_land_count} dual lands, "
                    f"need {required}+ for {num_colors} colors)"
                )
                quality_score -= 0.2

        # Validate land ratio
        if card_count > 0:
            land_ratio = lands / card_count
            if land_ratio < 0.30:
                curve_warnings.append(f"Low land count ({lands}, {land_ratio:.0%})")
                quality_score -= 0.1
            elif land_ratio > 0.45:
                curve_warnings.append(f"High land count ({lands}, {land_ratio:.0%})")
                quality_score -= 0.05

        # Clamp quality score
        quality_score = max(0.0, min(1.0, quality_score))

        return quality_score, curve_warnings, mana_base_quality, fixing_land_count

    def _count_fixing_lands(self, deck: DeckWithCards) -> int:
        """Count lands that provide color fixing (dual lands, fetch lands, etc.)."""
        fixing_count = 0
        dual_patterns = [
            r"add \{[WUBRG]\} or \{[WUBRG]\}",
            r"add \{[WUBRG]\}, \{[WUBRG]\}, or \{[WUBRG]\}",
            r"add one mana of any color",
            r"add .* mana of any type",
            r"search your library for .* land",
        ]

        for card_data in deck.mainboard:
            card = card_data.card
            if card and "Land" in (card.type or ""):
                text = (card.text or "").lower()
                for pattern in dual_patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        fixing_count += card_data.quantity
                        break

        return fixing_count

    def _detect_win_conditions(self, deck: DeckWithCards) -> list[str]:
        """Detect win condition types present in the deck."""
        win_condition_patterns = {
            "Evasion": [
                r"flying",
                r"can't be blocked",
                r"unblockable",
                r"menace",
                r"trample",
            ],
            "Finisher": [r"win the game", r"lose the game", r"infect"],
            "Burn": [
                r"deals? \d+ damage to .* player",
                r"each opponent loses",
                r"deals damage equal to",
            ],
            "Value": [r"draw .* card", r"create .* token", r"search your library"],
        }

        detected: dict[str, int] = {}

        for card_data in deck.mainboard:
            card = card_data.card
            if not card:
                continue

            text = (card.text or "").lower()
            type_line = (card.type or "").lower()

            for win_type, patterns in win_condition_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, text) or re.search(pattern, type_line):
                        detected[win_type] = detected.get(win_type, 0) + card_data.quantity
                        break

        # Return win condition types that have meaningful presence (3+ cards)
        return [wc for wc, count in detected.items() if count >= 3]

    def _assess_tribal_strength(self, creature_count: int) -> str:
        """Assess tribal theme strength based on creature count."""
        if creature_count >= 25:
            return "strong"
        elif creature_count >= 15:
            return "viable"
        elif creature_count >= 8:
            return "weak"
        return "minimal"

    def _assess_theme_strength(self, supporting_card_count: int) -> str:
        """Assess theme strength based on supporting card count."""
        if supporting_card_count >= 15:
            return "strong"
        elif supporting_card_count >= 10:
            return "viable"
        elif supporting_card_count >= 5:
            return "weak"
        return "minimal"
