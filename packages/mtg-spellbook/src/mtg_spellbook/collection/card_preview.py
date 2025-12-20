"""Compact card preview for collection view with ownership info."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.widgets import Static

from ..formatting import prettify_mana
from ..ui.theme import get_price_color, rarity_colors, ui_colors
from ..widgets.art_navigator import HAS_IMAGE_SUPPORT, TImage
from ..widgets.art_navigator.image_loader import load_image_from_url

if TYPE_CHECKING:
    from mtg_core.data.database import MTGDatabase, ScryfallDatabase
    from mtg_core.data.models.responses import PrintingInfo

    from ..collection_manager import CollectionCardWithData


class CollectionCardPreview(Vertical):
    """Compact card preview optimized for collection view.

    Features:
    - Side-by-side layout: image left, info right
    - Ownership details prominently displayed
    - Deck usage information
    - Price and set info
    """

    DEFAULT_CSS = """
    CollectionCardPreview {
        width: 100%;
        height: 100%;
        background: #0d0d0d;
    }

    #ccp-main {
        width: 100%;
        height: auto;
        min-height: 32;
    }

    #ccp-image-container {
        width: 50%;
        height: auto;
        min-height: 30;
        padding: 1;
        align: center middle;
    }

    #ccp-image {
        width: 100%;
        height: auto;
        min-height: 28;
    }

    #ccp-info-container {
        width: 50%;
        height: auto;
        padding: 1;
    }

    #ccp-card-name {
        text-style: bold;
        margin-bottom: 1;
    }

    #ccp-type-line {
        margin-bottom: 1;
    }

    #ccp-set-info {
        margin-bottom: 1;
    }

    #ccp-ownership {
        background: #1a1a2e;
        border: solid #3d3d3d;
        padding: 1;
        margin-top: 1;
        height: auto;
    }

    #ccp-prices {
        margin-top: 1;
    }

    #ccp-artist {
        margin-top: 1;
    }

    #ccp-deck-usage {
        background: #151520;
        border-top: solid #3d3d3d;
        padding: 1;
        height: auto;
        min-height: 4;
        max-height: 10;
    }

    #ccp-quick-actions {
        background: #1a1a1a;
        border-top: solid #3d3d3d;
        padding: 0 1;
        height: 3;
        content-align: center middle;
    }

    #ccp-scroll {
        height: 1fr;
    }

    #ccp-no-card {
        width: 100%;
        height: 100%;
        content-align: center middle;
    }
    """

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._card_data: CollectionCardWithData | None = None
        self._printing: PrintingInfo | None = None
        self._deck_usage: list[tuple[str, int]] = []

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="ccp-scroll"):
            # Main content - image and info side by side
            with Horizontal(id="ccp-main"):
                with Vertical(id="ccp-image-container"):
                    if HAS_IMAGE_SUPPORT:
                        yield TImage(id="ccp-image")
                    else:
                        yield Static("[dim]Image not available[/]", id="ccp-image-placeholder")

                with Vertical(id="ccp-info-container"):
                    yield Static("", id="ccp-card-name")
                    yield Static("", id="ccp-mana-cost")
                    yield Static("", id="ccp-type-line")
                    yield Static("", id="ccp-set-info")
                    yield Static("", id="ccp-prices")
                    yield Static("", id="ccp-artist")

                    # Ownership box
                    with Vertical(id="ccp-ownership"):
                        yield Static(
                            f"[bold {ui_colors.GOLD_DIM}]📊 OWNERSHIP[/]",
                            id="ccp-ownership-header",
                        )
                        yield Static("", id="ccp-ownership-details")

            # Deck usage section
            with Vertical(id="ccp-deck-usage"):
                yield Static(
                    f"[bold {ui_colors.GOLD_DIM}]🗂 DECK USAGE[/]",
                    id="ccp-deck-header",
                )
                yield Static("[dim]Not used in any decks[/]", id="ccp-deck-list")

        # Quick actions bar
        yield Static(
            "[dim]e: Add to deck | g: Gallery | esc: back[/]",
            id="ccp-quick-actions",
        )

    def update_card(
        self,
        card_data: CollectionCardWithData | None,
        deck_usage: list[tuple[str, int]] | None = None,
    ) -> None:
        """Update the preview with card data."""
        self._card_data = card_data
        self._deck_usage = deck_usage or []
        self._refresh_display()

    def _refresh_display(self) -> None:
        """Refresh all display elements."""
        if self._card_data is None:
            self._show_empty()
            return

        card_data = self._card_data
        card = card_data.card

        # Card name
        name_widget = self.query_one("#ccp-card-name", Static)
        rarity = card.rarity if card else None
        name_color = self._get_rarity_color(rarity)
        name_widget.update(f"[bold {name_color}]{card_data.card_name}[/]")

        # Mana cost
        mana_widget = self.query_one("#ccp-mana-cost", Static)
        if card and card.mana_cost:
            mana_widget.update(prettify_mana(card.mana_cost))
        else:
            mana_widget.update("")

        # Type line
        type_widget = self.query_one("#ccp-type-line", Static)
        if card and card.type:
            type_color = self._get_type_color(card.type)
            type_widget.update(f"[{type_color}]{card.type}[/]")
        else:
            type_widget.update("")

        # Set info
        set_widget = self.query_one("#ccp-set-info", Static)
        set_parts = []
        set_code = card_data.set_code or (card.set_code if card else None)
        if set_code:
            set_parts.append(f"[cyan]📦 {set_code.upper()}[/]")
        if card_data.collector_number:
            set_parts.append(f"[dim]#{card_data.collector_number}[/]")
        if rarity:
            icon, color = self._get_rarity_icon(rarity)
            set_parts.append(f"[{color}]{icon} {rarity.title()}[/]")
        set_widget.update(" · ".join(set_parts) if set_parts else "")

        # Prices (from printing if available)
        self._update_prices()

        # Artist
        artist_widget = self.query_one("#ccp-artist", Static)
        if card and card.artist:
            artist_widget.update(
                f"[dim]🎨[/] [{ui_colors.GOLD}]{card.artist}[/] [dim](Enter to explore)[/]"
            )
        else:
            artist_widget.update("")

        # Ownership details
        self._update_ownership()

        # Deck usage
        self._update_deck_usage()

    def _update_ownership(self) -> None:
        """Update ownership section."""
        details_widget = self.query_one("#ccp-ownership-details", Static)

        if not self._card_data:
            details_widget.update("[dim]No card selected[/]")
            return

        card_data = self._card_data
        total = card_data.total_owned
        regular = card_data.quantity
        foil = card_data.foil_quantity
        available = card_data.available
        in_decks = card_data.in_deck_count

        lines = []

        # Total owned
        lines.append(f"[{ui_colors.GOLD}]{total}x[/] owned")

        # Breakdown
        parts = []
        if regular > 0:
            parts.append(f"{regular} regular")
        if foil > 0:
            parts.append(f"[#b86fce]{foil} foil ✨[/]")
        if parts:
            lines.append(f"  [dim]{' + '.join(parts)}[/]")

        lines.append("")

        # Availability
        if available == total:
            lines.append(f"[#7ec850]✓ All {available} available[/]")
        elif available > 0:
            lines.append(f"[#e6c84a]○ {available}/{total} available[/]")
        else:
            lines.append("[dim]● All in decks[/]")

        if in_decks > 0:
            lines.append(f"[dim]  {in_decks} used in decks[/]")

        details_widget.update("\n".join(lines))

    def _update_deck_usage(self) -> None:
        """Update deck usage section."""
        deck_list = self.query_one("#ccp-deck-list", Static)

        if not self._deck_usage:
            deck_list.update("[dim]Not used in any decks[/]")
            return

        lines = []
        for deck_name, count in self._deck_usage[:5]:  # Show top 5
            lines.append(f"  [{ui_colors.GOLD}]{count}x[/] [dim]in[/] {deck_name}")

        if len(self._deck_usage) > 5:
            lines.append(f"  [dim]... and {len(self._deck_usage) - 5} more[/]")

        deck_list.update("\n".join(lines))

    def _update_prices(self) -> None:
        """Update price display."""
        prices_widget = self.query_one("#ccp-prices", Static)

        if self._printing:
            parts = []
            if self._printing.price_usd is not None:
                color = get_price_color(self._printing.price_usd)
                parts.append(f"[{color}]${self._printing.price_usd:.2f}[/]")
            if self._printing.price_eur is not None:
                parts.append(f"[dim]€{self._printing.price_eur:.2f}[/]")

            if parts:
                prices_widget.update("💰 " + "  ".join(parts))
            else:
                prices_widget.update("[dim]No price data[/]")
        else:
            prices_widget.update("")

    def _show_empty(self) -> None:
        """Show empty state."""
        for widget_id in [
            "#ccp-card-name",
            "#ccp-mana-cost",
            "#ccp-type-line",
            "#ccp-set-info",
            "#ccp-prices",
            "#ccp-artist",
        ]:
            try:
                widget = self.query_one(widget_id, Static)
                widget.update("")
            except NoMatches:
                pass

        try:
            details = self.query_one("#ccp-ownership-details", Static)
            details.update("[dim]Select a card[/]")
            deck_list = self.query_one("#ccp-deck-list", Static)
            deck_list.update("[dim]No card selected[/]")
        except NoMatches:
            pass

    async def load_printing(
        self,
        scryfall: ScryfallDatabase | None,
        db: MTGDatabase | None,
        card_name: str,
        set_code: str | None = None,
        collector_number: str | None = None,
    ) -> None:
        """Load printing info and image for a card.

        Args:
            scryfall: Scryfall database for image/price data
            db: MTG database for card data
            card_name: The card name to look up
            set_code: Optional set code for exact printing
            collector_number: Optional collector number for exact printing
        """
        if not scryfall or not card_name:
            return

        try:
            from mtg_core.data.models.responses import PrintingInfo

            # First try to get exact printing if set_code and collector_number provided
            if set_code and collector_number:
                image = await scryfall.get_card_image(card_name, set_code, collector_number)
                if image:
                    self._printing = PrintingInfo(
                        uuid=None,
                        set_code=image.set_code,
                        collector_number=image.collector_number,
                        rarity=None,
                        image=image.image_normal,
                        art_crop=image.image_art_crop,
                        price_usd=image.price_usd / 100 if image.price_usd else None,
                        price_eur=image.price_eur / 100 if image.price_eur else None,
                        artist=None,
                        illustration_id=image.illustration_id,
                    )
                    self._update_prices()
                    if self._printing.image:
                        self._load_image(self._printing.image)
                    return

            # Fall back to getting all printings and selecting first
            from mtg_core.tools import images

            printings = await images.get_card_printings(scryfall, db, card_name)
            if printings and printings.printings:
                # Try to find matching set_code if provided
                if set_code:
                    for p in printings.printings:
                        if p.set_code and p.set_code.lower() == set_code.lower():
                            self._printing = p
                            break
                    else:
                        self._printing = printings.printings[0]
                else:
                    self._printing = printings.printings[0]

                self._update_prices()
                if self._printing.image:
                    self._load_image(self._printing.image)
        except Exception:
            pass

    @work
    async def _load_image(self, image_url: str) -> None:
        """Load and display the card image."""
        if not HAS_IMAGE_SUPPORT:
            return

        try:
            img_widget = self.query_one("#ccp-image", TImage)
            await load_image_from_url(image_url, img_widget, use_large=True)
        except NoMatches:
            pass

    def _get_rarity_color(self, rarity: str | None) -> str:
        """Get color for rarity."""
        if not rarity:
            return ui_colors.WHITE
        rarity_lower = rarity.lower()
        if rarity_lower == "mythic":
            return rarity_colors.MYTHIC
        elif rarity_lower == "rare":
            return rarity_colors.RARE
        return ui_colors.WHITE

    def _get_rarity_icon(self, rarity: str) -> tuple[str, str]:
        """Get icon and color for rarity."""
        rarity_styles = {
            "common": ("●", rarity_colors.COMMON),
            "uncommon": ("◆", rarity_colors.UNCOMMON),
            "rare": ("♦", rarity_colors.RARE),
            "mythic": ("★", rarity_colors.MYTHIC),
        }
        return rarity_styles.get(rarity.lower(), ("○", rarity_colors.DEFAULT))

    def _get_type_color(self, type_line: str) -> str:
        """Get color based on card type."""
        type_lower = type_line.lower()
        if "creature" in type_lower:
            return "#7ec850"
        elif "instant" in type_lower or "sorcery" in type_lower:
            return "#4a9fd8"
        elif "artifact" in type_lower:
            return "#9a9a9a"
        elif "enchantment" in type_lower:
            return "#b86fce"
        elif "planeswalker" in type_lower:
            return "#e6c84a"
        elif "land" in type_lower:
            return "#a67c52"
        return "#888"
