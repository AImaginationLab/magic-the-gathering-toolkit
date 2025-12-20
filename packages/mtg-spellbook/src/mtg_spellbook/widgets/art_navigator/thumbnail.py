"""Thumbnail card widget for gallery view."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

if TYPE_CHECKING:
    from mtg_core.data.models.responses import PrintingInfo


class ThumbnailCard(Vertical, can_focus=True):
    """Individual printing thumbnail for gallery grid."""

    def __init__(
        self,
        printing: PrintingInfo,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.printing = printing
        self.selected = False

    def compose(self) -> ComposeResult:
        """Build thumbnail layout."""
        set_code = self.printing.set_code.upper() if self.printing.set_code else "???"

        yield Static(
            f"[dim]{set_code}[/]",
            classes="thumbnail-set",
        )

        if self.printing.price_usd is not None:
            price_text = f"${self.printing.price_usd:.2f}"
            price_class = self._get_price_class(self.printing.price_usd)
            yield Static(
                f"[{price_class}]{price_text}[/]",
                classes="thumbnail-price",
            )
        else:
            yield Static(
                "[dim]--[/]",
                classes="thumbnail-price",
            )

    def _get_price_class(self, price: float) -> str:
        """Get CSS class for price based on value."""
        if price >= 100:
            return "price-high"
        elif price >= 20:
            return "price-medium-high"
        elif price >= 5:
            return "price-medium"
        else:
            return "price-low"

    def set_selected(self, selected: bool) -> None:
        """Mark this thumbnail as selected."""
        self.selected = selected
        if selected:
            self.add_class("selected")
        else:
            self.remove_class("selected")
