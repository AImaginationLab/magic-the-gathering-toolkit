"""Widget to display deck impact when hovering over a card."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from ..ui.theme import ui_colors

if TYPE_CHECKING:
    from .impact import DeckImpact


class DeckImpactWidget(Vertical):
    """Displays the impact of adding a card to a deck.

    Shows stat changes like WoW item comparison tooltips:
    - Green for positive changes (+Flying, +3 Power)
    - Red for negative changes (-Haste equivalent)
    - Cyan/teal for info stats
    """

    DEFAULT_CSS = """
    DeckImpactWidget {
        width: 100%;
        height: auto;
        padding: 1;
        background: $surface;
        border: solid #3d3d3d;
    }

    DeckImpactWidget .impact-header {
        text-style: bold;
        color: #FFD700;
        margin-bottom: 1;
    }

    DeckImpactWidget .impact-section {
        margin-bottom: 1;
    }

    DeckImpactWidget .no-impact {
        color: #666;
        text-style: italic;
    }
    """

    def __init__(
        self,
        impact: DeckImpact | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._impact = impact

    def compose(self) -> ComposeResult:
        """Compose the widget."""
        yield Static("", id="impact-content")

    def update_impact(self, impact: DeckImpact | None) -> None:
        """Update the displayed impact."""
        self._impact = impact
        self._render_impact()

    def _render_impact(self) -> None:
        """Render the impact display."""
        try:
            content = self.query_one("#impact-content", Static)
        except Exception:
            return

        if not self._impact or not self._impact.has_impact():
            content.update(
                Text("No significant deck changes", style=f"italic {ui_colors.TEXT_DIM}")
            )
            return

        impact = self._impact
        lines: list[Text] = []

        # Header
        header = Text()
        header.append("If you add this card:\n", style=f"bold {ui_colors.GOLD}")
        lines.append(header)

        # Combat stats for creatures
        if impact.power_added or impact.toughness_added:
            combat = Text()
            combat.append("  Combat: ", style=ui_colors.TEXT_DIM)
            if impact.power_added:
                combat.append(f"+{impact.power_added} Power", style="#00FF00")
            if impact.power_added and impact.toughness_added:
                combat.append(", ", style=ui_colors.TEXT_DIM)
            if impact.toughness_added:
                combat.append(f"+{impact.toughness_added} Toughness", style="#00FF00")
            combat.append("\n")
            lines.append(combat)

        # Keywords added (bright green - these are always positive)
        if impact.keywords_added:
            kw_text = Text()
            kw_text.append("  Keywords: ", style=ui_colors.TEXT_DIM)
            for i, kw in enumerate(impact.keywords_added[:5]):  # Limit to 5
                if i > 0:
                    kw_text.append(", ", style=ui_colors.TEXT_DIM)
                kw_text.append(f"+{kw.capitalize()}", style="#00FF00")
            if len(impact.keywords_added) > 5:
                kw_text.append(
                    f" (+{len(impact.keywords_added) - 5} more)", style=ui_colors.TEXT_DIM
                )
            kw_text.append("\n")
            lines.append(kw_text)

        # Themes strengthened (cyan/teal for synergy info)
        if impact.themes_strengthened:
            theme_text = Text()
            theme_text.append("  Synergies: ", style=ui_colors.TEXT_DIM)
            for i, theme in enumerate(impact.themes_strengthened[:3]):
                if i > 0:
                    theme_text.append(", ", style=ui_colors.TEXT_DIM)
                if "active" in theme.lower():
                    theme_text.append(f"+{theme}", style="#FFD700")  # Gold for activation
                else:
                    theme_text.append(f"+{theme}", style="#00CED1")  # Dark cyan
            theme_text.append("\n")
            lines.append(theme_text)

        # Tribal boost
        if impact.tribal_boost:
            tribal = Text()
            tribal.append("  Tribal: ", style=ui_colors.TEXT_DIM)
            if "active" in impact.tribal_boost.lower():
                tribal.append(impact.tribal_boost, style="#FFD700")
            else:
                tribal.append(impact.tribal_boost, style="#00CED1")
            tribal.append("\n")
            lines.append(tribal)

        # Stat changes (type counts, avg CMC)
        stat_changes = [c for c in impact.changes if c.category in ("stat", "type")]
        if stat_changes:
            stats = Text()
            stats.append("  Stats: ", style=ui_colors.TEXT_DIM)
            for i, change in enumerate(stat_changes[:4]):
                if i > 0:
                    stats.append(", ", style=ui_colors.TEXT_DIM)

                delta_str = change.display_delta
                if change.is_positive is True:
                    color = "#00FF00"  # Green
                elif change.is_positive is False:
                    color = "#FF4444"  # Red
                else:
                    color = "#87CEEB"  # Light blue for neutral

                if delta_str:
                    stats.append(f"{delta_str} {change.name}", style=color)
                else:
                    stats.append(f"{change.name}", style=color)
            stats.append("\n")
            lines.append(stats)

        # Combine all lines
        result = Text()
        for line in lines:
            result.append_text(line)

        content.update(result)


class CompactImpactLine(Static):
    """Single-line compact impact display for list items.

    Shows a condensed version like:
    "+Flying +3/+2 +Tokens"
    """

    DEFAULT_CSS = """
    CompactImpactLine {
        height: 1;
        width: 100%;
        color: #666;
    }
    """

    def __init__(self, impact: DeckImpact | None = None, **kwargs: Any) -> None:
        super().__init__("", **kwargs)
        self._impact = impact
        if impact:
            self._render_content()

    def update_impact(self, impact: DeckImpact | None) -> None:
        """Update with new impact data."""
        self._impact = impact
        self._render_content()

    def _render_content(self) -> None:
        """Render compact impact line."""
        if not self._impact or not self._impact.has_impact():
            self.update("")
            return

        impact = self._impact
        parts: list[Text] = []

        # Keywords (most important)
        for kw in impact.keywords_added[:2]:
            t = Text()
            t.append(f"+{kw.capitalize()}", style="#00FF00")
            parts.append(t)

        # Combat stats
        if impact.power_added or impact.toughness_added:
            t = Text()
            t.append(f"+{impact.power_added}/+{impact.toughness_added}", style="#00FF00")
            parts.append(t)

        # One theme
        if impact.themes_strengthened:
            theme = impact.themes_strengthened[0]
            if "active" in theme.lower():
                t = Text()
                t.append(f"+{theme.split('(')[0].strip()}", style="#FFD700")
                parts.append(t)
            else:
                t = Text()
                t.append(f"+{theme}", style="#00CED1")
                parts.append(t)

        # Tribal
        if impact.tribal_boost and not parts:
            t = Text()
            # Extract just the type name
            tribal_short = impact.tribal_boost.split("(")[0].strip()
            t.append(tribal_short, style="#00CED1")
            parts.append(t)

        # Combine with spaces
        if parts:
            result = Text()
            result.append("  ", style="dim")  # Indent
            for i, part in enumerate(parts[:3]):  # Max 3 items
                if i > 0:
                    result.append(" ", style="dim")
                result.append_text(part)
            self.update(result)
        else:
            self.update("")
