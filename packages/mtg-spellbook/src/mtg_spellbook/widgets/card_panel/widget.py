"""Main CardPanel widget for displaying card details."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.events import Key
from textual.widgets import Static, TabbedContent, TabPane

from ...ui.theme import rarity_colors, ui_colors
from ..art_navigator import HAS_IMAGE_SUPPORT, ArtNavigator
from . import formatters, loaders

if HAS_IMAGE_SUPPORT:
    from textual_image.widget import Image as TImage

if TYPE_CHECKING:
    from mtg_core.data.database import MTGDatabase, ScryfallDatabase
    from mtg_core.data.models.responses import CardDetail, PrintingInfo


class CardPanel(Vertical):
    """Display card details with tabs for different views."""

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._card: CardDetail | None = None
        self._printings: list[PrintingInfo] = []
        self._current_printing_index: int = 0
        self._card_name_for_art: str = ""
        self._id_prefix = id or "card-panel"
        self._keywords: set[str] = set()

    def set_keywords(self, keywords: set[str]) -> None:
        """Set the keywords to highlight in card text."""
        self._keywords = keywords

    def _child_id(self, name: str) -> str:
        """Generate a unique child widget ID based on panel's ID."""
        return f"{self._id_prefix}-{name}"

    def get_child_name(self, name: str) -> str:
        """Get the child widget ID without selector (for setting active tabs, etc.)."""
        return self._child_id(name)

    def get_child_id(self, name: str) -> str:
        """Get the full CSS selector for a child widget (for queries)."""
        return f"#{self._child_id(name)}"

    def compose(self) -> ComposeResult:
        with TabbedContent(id=self._child_id("tabs")):
            with TabPane("📖 Card", id=self._child_id("tab-card"), classes="-tab-card"):
                yield Static(
                    "[dim]Select a card to view details[/]",
                    id=self._child_id("card-text"),
                    classes="-card-text",
                )
            with TabPane("🖼️ Art", id=self._child_id("tab-art"), classes="-tab-art"):
                yield ArtNavigator(
                    self._id_prefix,
                    id=self._child_id("art-navigator"),
                    classes="-art-navigator",
                )
            with TabPane("📜 Rulings", id=self._child_id("tab-rulings"), classes="-tab-rulings"):
                yield VerticalScroll(
                    Static(
                        "[dim]No rulings loaded[/]",
                        id=self._child_id("rulings-text"),
                        classes="-rulings-text",
                    )
                )
            with TabPane("⚖️ Legal", id=self._child_id("tab-legal"), classes="-tab-legal"):
                yield Static(
                    "[dim]No legality data[/]",
                    id=self._child_id("legal-text"),
                    classes="-legal-text",
                )
            with TabPane("💰 Price", id=self._child_id("tab-price"), classes="-tab-price"):
                yield Static(
                    "[dim]No price data[/]",
                    id=self._child_id("price-text"),
                    classes="-price-text",
                )

    def on_mount(self) -> None:
        """Set up panel reference in ArtNavigator after mount."""
        try:
            art_nav = self.query_one(f"#{self._child_id('art-navigator')}", ArtNavigator)
            art_nav.set_panel(self)
        except LookupError:
            pass

    def on_key(self, event: Key) -> None:
        """Handle key events - down arrow focuses art navigator when on art tab."""
        if event.key == "down" and self.focus_art_navigator():
            event.stop()

    def focus_art_navigator(self) -> bool:
        """Focus the art navigator if on the art tab. Returns True if focused."""
        try:
            tabs = self.query_one(f"#{self._child_id('tabs')}", TabbedContent)
            if tabs.active == self._child_id("tab-art"):
                art_nav = self.query_one(f"#{self._child_id('art-navigator')}", ArtNavigator)
                art_nav.focus()
                return True
        except LookupError:
            pass
        return False

    def show_loading(self, message: str = "Loading card details...") -> None:
        """Show loading indicator on card panel."""
        card_text = self.query_one(f"#{self._child_id('card-text')}", Static)
        card_text.update(f"[dim {ui_colors.GOLD_DIM}]✦ {message}[/]")

    def show_art_loading(self) -> None:
        """Show art loading indicator."""
        try:
            art_info = self.query_one(f"#{self._child_id('art-info')}", Static)
            art_info.update(f"[dim {ui_colors.GOLD_DIM}]🎨 Loading artwork...[/]")
        except LookupError:
            pass

    def update_card(self, card: CardDetail | None) -> None:
        """Update the displayed card."""
        self._card = card

        card_text = self.query_one(f"#{self._child_id('card-text')}", Static)
        if card:
            card_text.update(formatters.render_card_text(card, self._keywords))
            self._update_rarity_border(card)
        else:
            card_text.update("[dim]Select a card to view details[/]")
            self._reset_border()

        price_text = self.query_one(f"#{self._child_id('price-text')}", Static)
        if card and card.prices:
            price_text.update(formatters.render_prices(card))
        else:
            price_text.update("[dim]No price data available[/]")

    def update_card_with_synergy(
        self, card: CardDetail | None, synergy_info: dict[str, object] | None
    ) -> None:
        """Update the displayed card with synergy information."""
        self._card = card

        card_text = self.query_one(f"#{self._child_id('card-text')}", Static)
        if card:
            if synergy_info:
                text = formatters.render_card_with_synergy(card, self._keywords, synergy_info)
            else:
                text = formatters.render_card_text(card, self._keywords)
            card_text.update(text)
        else:
            card_text.update("[dim]Select a card to view details[/]")

        price_text = self.query_one(f"#{self._child_id('price-text')}", Static)
        if card and card.prices:
            price_text.update(formatters.render_prices(card))
        else:
            price_text.update("[dim]No price data available[/]")

    def _update_rarity_border(self, card: CardDetail) -> None:
        """Update panel border color based on card rarity."""
        from textual.css.types import EdgeType

        if not card.rarity:
            return

        rarity_lower = card.rarity.lower()
        border_colors = {
            "mythic": rarity_colors.MYTHIC,
            "rare": rarity_colors.RARE,
            "uncommon": rarity_colors.UNCOMMON,
            "common": ui_colors.BORDER_DEFAULT,
        }

        color = border_colors.get(rarity_lower, ui_colors.BORDER_DEFAULT)
        border_type: EdgeType = "heavy" if rarity_lower in ("mythic", "rare") else "round"

        with contextlib.suppress(Exception):
            self.styles.border = (border_type, color)

    def _reset_border(self) -> None:
        """Reset panel border to default."""
        with contextlib.suppress(Exception):
            self.styles.border = ("round", "#3d3d3d")

    async def load_rulings(self, db: MTGDatabase, card_name: str) -> None:
        """Load and display rulings for a card with enhanced styling."""
        rulings_text = self.query_one(f"#{self._child_id('rulings-text')}", Static)
        text, _ = await loaders.load_rulings(db, card_name, self._keywords)
        rulings_text.update(text)

    async def load_legalities(self, db: MTGDatabase, card_name: str) -> None:
        """Load and display format legalities with enhanced styling."""
        legal_text = self.query_one(f"#{self._child_id('legal-text')}", Static)
        text, _ = await loaders.load_legalities(db, card_name)
        legal_text.update(text)

    async def load_printings(self, scryfall: ScryfallDatabase | None, card_name: str) -> None:
        """Load all printings for a card into the art tab."""
        art_info = self.query_one(f"#{self._child_id('art-info')}", Static)

        printings, error = await loaders.load_printings(scryfall, card_name)
        if error:
            art_info.update(error)
            return

        self._printings = printings
        self._current_printing_index = 0
        self._card_name_for_art = card_name
        self._update_art_display()
        await self._load_current_art_image()

    def _update_art_display(self) -> None:
        """Update the art info display for current printing."""
        art_info = self.query_one(f"#{self._child_id('art-info')}", Static)

        if not self._printings:
            art_info.update("[dim]No printings available[/]")
            return

        printing = self._printings[self._current_printing_index]
        text = loaders.format_art_display(
            self._card_name_for_art, printing, self._current_printing_index, len(self._printings)
        )
        art_info.update(text)

    async def _load_current_art_image(self) -> None:
        """Load the image for the current printing."""
        art_info = self.query_one(f"#{self._child_id('art-info')}", Static)

        if not HAS_IMAGE_SUPPORT:
            return

        if not self._printings:
            return

        printing = self._printings[self._current_printing_index]
        if not printing.image:
            return

        try:
            img_widget = self.query_one(f"#{self._child_id('art-image')}", TImage)
        except LookupError:
            return

        pil_image, error = await loaders.load_art_image(printing.image)
        if pil_image:
            img_widget.image = pil_image
        elif error:
            current_text = art_info.renderable  # type: ignore[attr-defined]
            art_info.update(f"{current_text}\n{error}")

    def next_printing(self) -> bool:
        """Move to next printing. Returns True if moved."""
        if not self._printings or self._current_printing_index >= len(self._printings) - 1:
            return False
        self._current_printing_index += 1
        self._update_art_display()
        return True

    def prev_printing(self) -> bool:
        """Move to previous printing. Returns True if moved."""
        if not self._printings or self._current_printing_index <= 0:
            return False
        self._current_printing_index -= 1
        self._update_art_display()
        return True

    async def load_next_art(self) -> None:
        """Navigate to next printing and load image."""
        if self.next_printing():
            await self._load_current_art_image()

    async def load_prev_art(self) -> None:
        """Navigate to previous printing and load image."""
        if self.prev_printing():
            await self._load_current_art_image()
