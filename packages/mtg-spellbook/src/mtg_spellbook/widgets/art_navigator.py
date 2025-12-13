"""Art navigation widgets for card image display."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING, Any, ClassVar

import httpx
from PIL import Image
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Static

try:
    from textual_image.widget import Image as TImage

    HAS_IMAGE_SUPPORT = True
except ImportError:
    HAS_IMAGE_SUPPORT = False
    TImage = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from .card_panel import CardPanel


class CardImageWidget(Static):
    """Widget to display card image or fallback to text."""

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._image_widget: Any = None

    async def load_image(self, url: str) -> None:
        """Load and display image from URL."""
        self.remove_children()

        if not HAS_IMAGE_SUPPORT:
            self.mount(Static("[dim]Image display not available\n(install textual-image)[/]"))
            return

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                image_data = response.content

            pil_image = Image.open(BytesIO(image_data))
            self._image_widget = TImage(pil_image)
            self.mount(self._image_widget)

        except Exception as e:
            self.mount(Static(f"[red]Failed to load image: {e}[/]"))

    def clear_image(self) -> None:
        """Clear the displayed image."""
        self.remove_children()
        self._image_widget = None


class ArtNavigator(Vertical, can_focus=True):
    """Focusable widget for navigating card art with arrow keys.

    Press down to focus, then left/right to navigate between printings.
    """

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("left", "prev_art", "← Prev", show=False),
        Binding("right", "next_art", "→ Next", show=False),
        Binding("up", "release_focus", "↑ Back", show=False),
    ]

    def __init__(
        self,
        id_prefix: str,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._id_prefix = id_prefix
        self._panel: CardPanel | None = None

    def compose(self) -> ComposeResult:
        yield Static(
            "[dim]Select a card to view art\n\n← → to navigate printings[/]",
            id=f"{self._id_prefix}-art-info",
            classes="-art-info",
        )
        if HAS_IMAGE_SUPPORT:
            yield TImage(id=f"{self._id_prefix}-art-image", classes="-art-image")

    def set_panel(self, panel: CardPanel) -> None:
        """Set the parent panel reference after mount."""
        self._panel = panel

    def action_next_art(self) -> None:
        """Navigate to next artwork."""
        if self._panel:
            self._load_next()

    def action_prev_art(self) -> None:
        """Navigate to previous artwork."""
        if self._panel:
            self._load_prev()

    def action_release_focus(self) -> None:
        """Release focus back to tab panel."""
        if self._panel:
            try:
                from textual.widgets import TabbedContent, Tabs

                tabbed_content = self._panel.query_one(
                    self._panel.get_child_id("tabs"), TabbedContent
                )
                tabs = tabbed_content.query_one(Tabs)
                tabs.focus()
            except Exception:
                pass

    @work
    async def _load_next(self) -> None:
        if self._panel:
            await self._panel.load_next_art()

    @work
    async def _load_prev(self) -> None:
        if self._panel:
            await self._panel.load_prev_art()
