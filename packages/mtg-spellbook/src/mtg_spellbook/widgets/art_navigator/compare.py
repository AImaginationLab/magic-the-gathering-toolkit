"""Compare view component for side-by-side printing comparison."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.widgets import Static

from ...ui.theme import get_price_color, rarity_colors, ui_colors
from . import HAS_IMAGE_SUPPORT, TImage
from .image_loader import load_image_from_url

if TYPE_CHECKING:
    from mtg_core.data.models.responses import PrintingInfo


class CompareSlot(Vertical):
    """Individual comparison slot showing one printing."""

    def __init__(
        self,
        slot_number: int,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.slot_number = slot_number
        self._printing: PrintingInfo | None = None
        self._card_name: str = ""

    def compose(self) -> ComposeResult:
        """Build comparison slot layout."""
        if HAS_IMAGE_SUPPORT:
            yield TImage(
                id=f"compare-image-{self.slot_number}",
                classes="compare-image",
            )
        else:
            yield Static(
                "[dim]Image not available[/]",
                classes="compare-no-image",
            )

        yield Static(
            f"[dim][ {self.slot_number} ] Empty[/]",
            id=f"compare-info-{self.slot_number}",
            classes="compare-metadata",
        )

    async def load_printing(
        self,
        card_name: str,
        printing: PrintingInfo,
        first_artwork_id: str | None = None,
    ) -> None:
        """Load a printing into this slot."""
        self._card_name = card_name
        self._printing = printing

        # Build compact single-line info
        parts = [f"[{ui_colors.GOLD}][ {self.slot_number} ][/]"]

        if printing.set_code:
            parts.append(printing.set_code.upper())

        if printing.price_usd is not None:
            price_color = get_price_color(printing.price_usd)
            parts.append(f"[{price_color}]${printing.price_usd:.2f}[/]")

        badge_text = self._get_artwork_badge(printing, first_artwork_id)
        if badge_text:
            parts.append(badge_text)

        info_widget = self.query_one(f"#compare-info-{self.slot_number}", Static)
        info_widget.update(" • ".join(parts))

        if printing.image:
            self._load_image(printing.image)

    def clear_slot(self) -> None:
        """Clear this slot's content."""
        self._printing = None
        self._card_name = ""

        info_widget = self.query_one(f"#compare-info-{self.slot_number}", Static)
        info_widget.update(f"[dim][ {self.slot_number} ] Empty[/]")

    def _get_artwork_badge(
        self,
        printing: PrintingInfo,
        first_artwork_id: str | None,
    ) -> str:
        """Get badge text for artwork uniqueness."""
        current_id = printing.illustration_id

        if not first_artwork_id:
            return f"[{rarity_colors.MYTHIC}]★ Original Art[/]"

        if current_id and current_id != first_artwork_id:
            return f"[{rarity_colors.MYTHIC}]★ Alternate Art[/]"

        if printing.artist and first_artwork_id:
            return "[dim]Classic Reprint[/]"

        return ""

    @work
    async def _load_image(self, image_url: str) -> None:
        """Load and display the card image."""
        if not HAS_IMAGE_SUPPORT:
            return

        try:
            img_widget = self.query_one(f"#compare-image-{self.slot_number}", TImage)
            await load_image_from_url(image_url, img_widget, use_large=True)
        except NoMatches:
            pass


class SummaryBar(Static):
    """Summary bar showing comparison statistics."""

    def update_summary(self, printings: list[PrintingInfo]) -> None:
        """Update summary with current printings."""
        if not printings:
            self.update("[dim]No printings selected for comparison[/]")
            return

        prices = [p.price_usd for p in printings if p.price_usd is not None]

        if not prices:
            self.update("[dim]No price data available[/]")
            return

        cheapest_price = min(prices)
        most_expensive_price = max(prices)

        cheapest_printing = next(p for p in printings if p.price_usd == cheapest_price)
        expensive_printing = next(p for p in printings if p.price_usd == most_expensive_price)

        cheapest_set = cheapest_printing.set_code.upper() if cheapest_printing.set_code else "???"
        expensive_set = (
            expensive_printing.set_code.upper() if expensive_printing.set_code else "???"
        )

        artwork_ids = set()
        for p in printings:
            if p.illustration_id:
                artwork_ids.add(p.illustration_id)

        unique_arts = (
            len(artwork_ids) if artwork_ids else len({p.artist for p in printings if p.artist})
        )

        summary_parts = [
            f"[green]Cheapest:[/] {cheapest_set} (${cheapest_price:.2f})",
            f"[{ui_colors.TEXT_ERROR}]Most Expensive:[/] {expensive_set} (${most_expensive_price:.2f})",
            f"[{ui_colors.GOLD}]{unique_arts} unique artwork{'s' if unique_arts != 1 else ''}[/]",
        ]

        self.update("    ".join(summary_parts))


class CompareView(Vertical):
    """Side-by-side comparison view for multiple printings."""

    MAX_SLOTS = 4

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._printings: list[PrintingInfo] = []
        self._card_name: str = ""
        self._selected_slot: int = 1

    def compose(self) -> ComposeResult:
        """Build compare view layout."""
        yield Static(
            "[bold]Comparing Printings[/]",
            id="compare-header",
            classes="compare-header",
        )

        with Horizontal(classes="compare-slots-container", id="compare-slots"):
            for i in range(1, self.MAX_SLOTS + 1):
                yield CompareSlot(i, classes="compare-slot")

        yield SummaryBar(
            "[dim]Add printings to compare[/]",
            classes="compare-summary",
            id="compare-summary",
        )
        # Status bar is now handled by parent EnhancedArtNavigator (QW1)

    async def load_printings(self, card_name: str, printings: list[PrintingInfo]) -> None:
        """Load printings into comparison view."""
        self._card_name = card_name
        self._printings = printings[: self.MAX_SLOTS]

        header = self.query_one("#compare-header", Static)
        count = len(self._printings)
        header.update(
            f"[bold {ui_colors.GOLD}]Comparing {count} Printing{'s' if count != 1 else ''}[/]"
        )

        first_artwork_id = None
        if self._printings:
            first = self._printings[0]
            first_artwork_id = first.illustration_id

        slots = self.query(CompareSlot)
        for i, slot in enumerate(slots):
            if i < len(self._printings):
                await slot.load_printing(card_name, self._printings[i], first_artwork_id)
            else:
                slot.clear_slot()

        summary = self.query_one("#compare-summary", SummaryBar)
        summary.update_summary(self._printings)

    async def add_printing(self, printing: PrintingInfo) -> bool:
        """Add a printing to the comparison. Returns True if added successfully."""
        if len(self._printings) >= self.MAX_SLOTS:
            return False

        if any(
            p.set_code == printing.set_code and p.collector_number == printing.collector_number
            for p in self._printings
        ):
            return False

        self._printings.append(printing)
        await self.load_printings(self._card_name, self._printings)
        return True

    async def remove_printing(self, slot_number: int) -> None:
        """Remove a printing from the specified slot."""
        if 1 <= slot_number <= len(self._printings):
            self._printings.pop(slot_number - 1)
            await self.load_printings(self._card_name, self._printings)

    async def clear_all(self) -> None:
        """Clear all comparison slots."""
        self._printings.clear()
        await self.load_printings(self._card_name, self._printings)

    def get_printings(self) -> list[PrintingInfo]:
        """Get current printings in comparison."""
        return self._printings.copy()

    def select_slot(self, slot_number: int) -> None:
        """Select a comparison slot and update visual highlight."""
        if not 1 <= slot_number <= self.MAX_SLOTS:
            return

        self._selected_slot = slot_number

        # Update slot highlighting
        try:
            slots = list(self.query(CompareSlot))
            for i, slot in enumerate(slots):
                if i + 1 == slot_number:
                    slot.add_class("selected")
                else:
                    slot.remove_class("selected")

            # Notify user of selection
            has_content = slot_number <= len(self._printings)
            if has_content:
                printing = self._printings[slot_number - 1]
                set_code = printing.set_code.upper() if printing.set_code else "???"
                self.notify(f"Selected slot {slot_number}: {set_code}", timeout=1.5)
            else:
                self.notify(f"Selected slot {slot_number} (empty)", timeout=1.5)
        except NoMatches:
            pass

    def get_selected_slot(self) -> int:
        """Get the currently selected slot number."""
        return self._selected_slot
