"""Shop-style card display for gallery view with thumbnail."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.css.query import NoMatches
from textual.widgets import Static

from ...ui.theme import get_price_color, get_rarity_style, ui_colors
from . import HAS_IMAGE_SUPPORT, TImage
from .image_loader import load_image_from_url

if TYPE_CHECKING:
    from mtg_core.data.models.responses import PrintingInfo


def _get_small_url(image_url: str | None) -> str | None:
    """Convert normal image URL to small thumbnail URL."""
    if not image_url:
        return None
    # Scryfall URL pattern: /normal/ -> /small/
    return image_url.replace("/normal/", "/small/")


class ShopCard(Vertical, can_focus=True):
    """Card display with thumbnail image and info below."""

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
        self._image_loaded = False

    def compose(self) -> ComposeResult:
        """Build compact filmstrip card: thumbnail + set/rarity + price."""
        p = self.printing

        # Thumbnail image area
        if HAS_IMAGE_SUPPORT:
            yield TImage(id=f"{self.id}-thumb", classes="shop-card-thumb")
        else:
            yield Static("[dim]IMG[/]", classes="shop-card-thumb-placeholder")

        # Set code + rarity icon on same line (e.g., "PIP ★")
        set_code = p.set_code.upper() if p.set_code else "???"
        rarity_icon, rarity_color = get_rarity_style(p.rarity or "common")
        yield Static(
            f"[{ui_colors.GOLD}]{set_code}[/][{rarity_color}]{rarity_icon}[/]",
            classes="shop-card-set",
        )

        # Price
        if p.price_usd is not None:
            price_text = f"${p.price_usd:.2f}"
            price_color = get_price_color(p.price_usd)
            yield Static(
                f"[{price_color}]{price_text}[/]",
                classes="shop-card-price",
            )
        else:
            yield Static("[dim]--[/]", classes="shop-card-price")

    def on_mount(self) -> None:
        """Load thumbnail when mounted."""
        if HAS_IMAGE_SUPPORT and not self._image_loaded:
            self._load_thumbnail()

    @work
    async def _load_thumbnail(self) -> None:
        """Load the thumbnail image."""
        if not HAS_IMAGE_SUPPORT:
            return

        small_url = _get_small_url(self.printing.image)
        if not small_url:
            return

        try:
            thumb_widget = self.query_one(f"#{self.id}-thumb", TImage)
            await load_image_from_url(
                small_url,
                thumb_widget,
                use_large=False,
                max_width=146,  # Scryfall small size
                max_height=204,
            )
            self._image_loaded = True
        except NoMatches:
            pass

    def set_selected(self, selected: bool) -> None:
        """Mark this card as selected."""
        self.selected = selected
        if selected:
            self.add_class("selected")
        else:
            self.remove_class("selected")
