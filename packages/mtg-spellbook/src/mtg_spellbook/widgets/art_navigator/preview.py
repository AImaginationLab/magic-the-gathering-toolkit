"""Preview panel widget for gallery view - displays card image only."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.css.query import NoMatches
from textual.widgets import Static

from . import HAS_IMAGE_SUPPORT, TImage
from .image_loader import load_image_from_url

if TYPE_CHECKING:
    from mtg_core.data.models.responses import PrintingInfo


class PreviewPanel(Vertical):
    """Enlarged preview panel showing selected card image only."""

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._current_printing: PrintingInfo | None = None
        self._show_art_crop: bool = False

    def compose(self) -> ComposeResult:
        """Build preview panel layout - image only."""
        if HAS_IMAGE_SUPPORT:
            yield TImage(id="preview-image", classes="preview-image")
        else:
            yield Static("[dim]Image support not available[/]", classes="preview-placeholder")

    async def update_printing(self, _card_name: str, printing: PrintingInfo) -> None:
        """Update the preview panel with a new printing."""
        self._current_printing = printing

        if printing.image:
            image_url = printing.image
            # If art crop mode is enabled, use art_crop URL
            if self._show_art_crop and printing.art_crop:
                image_url = printing.art_crop
            self._load_image(image_url)

    def set_art_crop_mode(self, enabled: bool) -> None:
        """Toggle between full card and art crop display."""
        self._show_art_crop = enabled
        if self._current_printing:
            if enabled and self._current_printing.art_crop:
                self._load_image(self._current_printing.art_crop)
            elif self._current_printing.image:
                self._load_image(self._current_printing.image)

    @work
    async def _load_image(self, image_url: str) -> None:
        """Load and display the card image."""
        if not HAS_IMAGE_SUPPORT:
            return

        try:
            img_widget = self.query_one("#preview-image", TImage)
            await load_image_from_url(image_url, img_widget, use_large=True)
        except NoMatches:
            pass

    @property
    def art_crop_enabled(self) -> bool:
        """Check if art crop mode is enabled."""
        return self._show_art_crop
