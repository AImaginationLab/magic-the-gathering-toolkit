"""Set information panel displaying set metadata and statistics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.widgets import Static

from ...ui.theme import rarity_colors, ui_colors

if TYPE_CHECKING:
    from mtg_core.data.models import Set


class SetStats:
    """Statistics about a set's card composition."""

    def __init__(
        self,
        total_cards: int = 0,
        rarity_distribution: dict[str, int] | None = None,
        color_distribution: dict[str, int] | None = None,
        mechanics: list[str] | None = None,
        avg_cmc: float | None = None,
    ) -> None:
        self.total_cards = total_cards
        self.rarity_distribution = rarity_distribution or {}
        self.color_distribution = color_distribution or {}
        self.mechanics = mechanics or []
        self.avg_cmc = avg_cmc


class SetInfoPanel(VerticalScroll):
    """Display set metadata and statistics."""

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._set_data: Set | None = None
        self._stats: SetStats | None = None
        self._format_legality: dict[str, bool] = {}

    def compose(self) -> ComposeResult:
        with Vertical(classes="set-info-content"):
            yield Static(
                "[dim]No set loaded[/]",
                id="set-info-text",
                classes="set-info-text",
            )

    def update_info(
        self,
        set_data: Set,
        stats: SetStats | None = None,
        format_legality: dict[str, bool] | None = None,
    ) -> None:
        """Update display with set info."""
        self._set_data = set_data
        self._stats = stats or SetStats()
        self._format_legality = format_legality or {}

        text = self._render_set_info()
        try:
            info_text = self.query_one("#set-info-text", Static)
            info_text.update(text)
        except NoMatches:
            pass

    def _render_set_info(self) -> str:
        """Render set information as rich text."""
        if not self._set_data:
            return "[dim]No set loaded[/]"

        s = self._set_data
        lines: list[str] = []

        # Set name and code header
        lines.append(f"[bold {ui_colors.GOLD}]{s.name}[/]")
        lines.append(f"[dim]({s.code.upper()})[/]")
        lines.append("")

        # Basic info
        if s.release_date:
            lines.append(f"[{ui_colors.TEXT_DIM}]Released:[/] {s.release_date}")

        if s.type:
            type_display = s.type.replace("_", " ").title()
            lines.append(f"[{ui_colors.TEXT_DIM}]Type:[/] {type_display}")

        if s.block:
            lines.append(f"[{ui_colors.TEXT_DIM}]Block:[/] {s.block}")

        # Card counts
        if s.base_set_size:
            lines.append(f"[{ui_colors.TEXT_DIM}]Base Size:[/] {s.base_set_size} cards")

        if s.total_set_size:
            lines.append(f"[{ui_colors.TEXT_DIM}]Total Size:[/] {s.total_set_size} cards")

        lines.append("")

        # Format legality
        if self._format_legality:
            lines.append(f"[bold {ui_colors.GOLD_DIM}]Format Legality[/]")
            for fmt, is_legal in sorted(self._format_legality.items()):
                if is_legal:
                    lines.append(f"  [green]{fmt.title()}[/] [dim]legal[/]")
                else:
                    lines.append(f"  [dim]{fmt.title()}[/] [red]not legal[/]")
            lines.append("")

        # Rarity distribution
        if self._stats and self._stats.rarity_distribution:
            lines.append(f"[bold {ui_colors.GOLD_DIM}]Rarity Distribution[/]")
            rarity_order = ["mythic", "rare", "uncommon", "common"]
            rarity_colors_map = {
                "mythic": rarity_colors.MYTHIC,
                "rare": rarity_colors.RARE,
                "uncommon": rarity_colors.UNCOMMON,
                "common": rarity_colors.COMMON,
            }
            for rarity in rarity_order:
                count = self._stats.rarity_distribution.get(rarity, 0)
                if count > 0:
                    color = rarity_colors_map.get(rarity, ui_colors.TEXT_DIM)
                    lines.append(f"  [{color}]{rarity.title()}:[/] {count}")
            lines.append("")

        # Mechanics
        if self._stats and self._stats.mechanics:
            lines.append(f"[bold {ui_colors.GOLD_DIM}]Mechanics[/]")
            for mechanic in self._stats.mechanics[:10]:  # Limit to 10
                lines.append(f"  [cyan]{mechanic}[/]")
            if len(self._stats.mechanics) > 10:
                lines.append(f"  [dim]...and {len(self._stats.mechanics) - 10} more[/]")
            lines.append("")

        # Online/foil only flags
        flags: list[str] = []
        if s.is_online_only:
            flags.append("[yellow]Online Only[/]")
        if s.is_foil_only:
            flags.append("[magenta]Foil Only[/]")

        if flags:
            lines.append(" | ".join(flags))

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear the info panel."""
        self._set_data = None
        self._stats = None
        self._format_legality = {}
        try:
            info_text = self.query_one("#set-info-text", Static)
            info_text.update("[dim]No set loaded[/]")
        except NoMatches:
            pass
