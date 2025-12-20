"""Card slot widget for carousel display."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.css.query import NoMatches
from textual.widgets import Static

from ...ui.theme import get_price_color, rarity_colors, ui_colors
from . import HAS_IMAGE_SUPPORT, TImage

if TYPE_CHECKING:
    from mtg_core.data.models.responses import PrintingInfo


class CardSlot(Vertical):
    """Single card slot in carousel with image and label."""

    DEFAULT_CSS = """
    CardSlot {
        width: 1fr;
        height: 100%;
        margin: 0 1;
        align: center middle;
    }

    CardSlot.current {
        border: heavy #c9a227;
    }

    CardSlot.faded {
        opacity: 0.7;
    }

    CardSlot .slot-image-container {
        width: 100%;
        height: 1fr;
        align: center middle;
    }

    CardSlot .slot-label {
        width: 100%;
        height: 3;
        text-align: center;
        padding: 0 1;
    }

    CardSlot .slot-empty {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: #444;
    }
    """

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._printing: PrintingInfo | None = None
        self._owned: bool = False
        self._image_widget: Any = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="slot-image-container"):
            if HAS_IMAGE_SUPPORT:
                self._image_widget = TImage(id="slot-image")
                yield self._image_widget
            else:
                yield Static("[dim]No image support[/]", classes="slot-empty")
        yield Static("", id="slot-label", classes="slot-label")

    def set_printing(
        self,
        printing: PrintingInfo | None,
        *,
        owned: bool = False,
    ) -> None:
        """Set the printing to display in this slot."""
        self._printing = printing
        self._owned = owned
        self._update_label()

    def _update_label(self) -> None:
        """Update the label with printing info."""
        try:
            label = self.query_one("#slot-label", Static)
        except NoMatches:
            return

        if self._printing is None:
            label.update("")
            return

        p = self._printing
        parts = []

        # Set code and collector number
        set_info = p.set_code.upper() if p.set_code else "???"
        if p.collector_number:
            set_info += f" #{p.collector_number}"
        parts.append(f"[{ui_colors.GOLD}]{set_info}[/]")

        # Price with color coding
        if p.price_usd is not None:
            price_color = get_price_color(p.price_usd)
            parts.append(f"[{price_color}]${p.price_usd:.2f}[/]")
        else:
            parts.append("[dim]N/A[/]")

        # Owned indicator
        if self._owned:
            parts.append("[green bold]✓[/]")

        label.update(" · ".join(parts))

    @property
    def printing(self) -> PrintingInfo | None:
        """Get the current printing."""
        return self._printing

    @property
    def image_widget(self) -> Any:
        """Get the image widget for external loading."""
        return self._image_widget

    def get_rarity_color(self) -> str:
        """Get color based on rarity."""
        if not self._printing or not self._printing.rarity:
            return rarity_colors.DEFAULT
        rarity = self._printing.rarity.lower()
        return getattr(rarity_colors, rarity.upper(), rarity_colors.DEFAULT)
