"""Card preview panel for set detail view."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.css.query import NoMatches
from textual.widgets import Static

from ...ui.theme import rarity_colors, ui_colors

if TYPE_CHECKING:
    from mtg_core.data.models.responses import CardSummary


class SetCardPreviewPanel(VerticalScroll):
    """Display a preview of the selected card."""

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._card: CardSummary | None = None

    def compose(self) -> ComposeResult:
        yield Static(
            "[dim]Select a card to preview[/]",
            id="card-preview-text",
            classes="card-preview-text",
        )

    def update_card(self, card: CardSummary | None) -> None:
        """Update the preview with a card."""
        self._card = card
        text = self._render_preview()
        try:
            preview_text = self.query_one("#card-preview-text", Static)
            preview_text.update(text)
        except NoMatches:
            pass

    def _render_preview(self) -> str:
        """Render card preview as rich text."""
        if not self._card:
            return "[dim]Select a card to preview[/]"

        c = self._card
        lines: list[str] = []

        # Card name
        lines.append(f"[bold {ui_colors.GOLD}]{c.name}[/]")

        # Mana cost
        if c.mana_cost:
            lines.append(f"[{ui_colors.TEXT_DIM}]{c.mana_cost}[/]")

        lines.append("")

        # Type line
        if c.type:
            lines.append(f"[italic]{c.type}[/]")
            lines.append("")

        # Rarity
        if c.rarity:
            rarity_lower = c.rarity.lower()
            rarity_color = self._get_rarity_color(rarity_lower)
            lines.append(f"[{rarity_color}]{c.rarity.title()}[/]")

        # Set code
        if c.set_code:
            lines.append(f"[{ui_colors.TEXT_DIM}]Set: {c.set_code.upper()}[/]")

        lines.append("")

        # Power/toughness for creatures
        if c.power is not None and c.toughness is not None:
            lines.append(f"[bold]{c.power}/{c.toughness}[/]")

        # CMC
        if c.cmc is not None:
            cmc_display = int(c.cmc) if c.cmc == int(c.cmc) else c.cmc
            lines.append(f"[{ui_colors.TEXT_DIM}]CMC:[/] {cmc_display}")

        # Colors
        if c.colors:
            color_display = self._format_colors(c.colors)
            lines.append(f"[{ui_colors.TEXT_DIM}]Colors:[/] {color_display}")

        # Keywords
        if c.keywords:
            lines.append("")
            lines.append(f"[{ui_colors.TEXT_DIM}]Keywords:[/]")
            for kw in c.keywords[:5]:  # Limit to 5
                lines.append(f"  [cyan]{kw}[/]")
            if len(c.keywords) > 5:
                lines.append(f"  [dim]...and {len(c.keywords) - 5} more[/]")

        # Price
        if c.price_usd is not None:
            lines.append("")
            price_color = self._get_price_color(c.price_usd)
            lines.append(f"[{price_color}]${c.price_usd:.2f}[/]")

        lines.append("")
        lines.append("[dim]Press Enter to view full details[/]")

        return "\n".join(lines)

    def _get_rarity_color(self, rarity: str) -> str:
        """Get color for rarity."""
        colors = {
            "mythic": rarity_colors.MYTHIC,
            "rare": rarity_colors.RARE,
            "uncommon": rarity_colors.UNCOMMON,
            "common": rarity_colors.COMMON,
        }
        return colors.get(rarity, ui_colors.TEXT_DIM)

    def _format_colors(self, colors: list[str]) -> str:
        """Format color list with color codes."""
        color_map = {
            "W": "[#F0E68C]W[/]",
            "U": "[#0E86D4]U[/]",
            "B": "[#2C3639]B[/]",
            "R": "[#C7253E]R[/]",
            "G": "[#1A5D1A]G[/]",
        }
        return "".join(color_map.get(c, c) for c in colors)

    def _get_price_color(self, price: float) -> str:
        """Get color based on price tier."""
        if price >= 100:
            return ui_colors.TEXT_ERROR
        elif price >= 20:
            return "orange"
        elif price >= 5:
            return "yellow"
        return "green"

    def clear(self) -> None:
        """Clear the preview panel."""
        self._card = None
        try:
            preview_text = self.query_one("#card-preview-text", Static)
            preview_text.update("[dim]Select a card to preview[/]")
        except NoMatches:
            pass
