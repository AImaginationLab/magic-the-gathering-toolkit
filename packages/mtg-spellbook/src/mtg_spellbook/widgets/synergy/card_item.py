"""Synergy card item widget for displaying individual synergy results."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.widgets import ListItem, Static

from ...formatting import prettify_mana
from ...ui.theme import ui_colors

if TYPE_CHECKING:
    from mtg_core.data.models.responses import SynergyResult


class SynergyCardItem(ListItem):
    """A synergy card item showing score, name, and reason."""

    TYPE_LABELS: ClassVar[dict[str, str]] = {
        "keyword": "Keyword",
        "tribal": "Tribal",
        "ability": "Ability",
        "theme": "Theme",
        "archetype": "Theme",
        "combo": "Combo",
    }

    def __init__(
        self,
        synergy: SynergyResult,
        *,
        in_collection: bool = False,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.synergy = synergy
        self.in_collection = in_collection

    def compose(self) -> ComposeResult:
        yield Static(self._render_item(), classes="synergy-item-content")

    def _render_item(self) -> str:
        """Render a compact single-line item."""
        syn = self.synergy

        # Score with color
        score_pct = int(syn.score * 100)
        score_color = self._get_score_color(syn.score)

        # Mana cost
        mana = prettify_mana(syn.mana_cost) if syn.mana_cost else ""

        # Type label (short)
        type_label = self.TYPE_LABELS.get(syn.synergy_type, syn.synergy_type.title())

        # Collection indicator
        owned_marker = "[green]✓[/] " if self.in_collection else "  "

        # Build single line: ✓ [80%] Card Name {mana} · Type - reason
        parts = [owned_marker + f"[{score_color}]{score_pct:>3}%[/]"]
        parts.append(f"[bold]{syn.name}[/]")
        if mana:
            parts.append(mana)
        parts.append(f"[dim]·[/] [{ui_colors.TEXT_DIM}]{type_label}: {syn.reason}[/]")

        return " ".join(parts)

    def _get_score_color(self, score: float) -> str:
        """Get color based on synergy score."""
        if score >= 0.8:
            return ui_colors.SYNERGY_STRONG
        elif score >= 0.6:
            return ui_colors.SYNERGY_MODERATE
        elif score >= 0.4:
            return ui_colors.SYNERGY_WEAK
        return ui_colors.TEXT_DIM


class SynergyListHeader(Static):
    """Header for synergy list showing count and category."""

    def __init__(
        self,
        category: str,
        count: int,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.category = category
        self.count = count
        self.update(self._render_header())

    def _render_header(self) -> str:
        """Render the header text."""
        return (
            f"[bold {ui_colors.GOLD}]{self.category}[/] "
            f"[{ui_colors.TEXT_DIM}]({self.count} results)[/]"
        )

    def update_count(self, count: int) -> None:
        """Update the displayed count."""
        self.count = count
        self.update(self._render_header())
