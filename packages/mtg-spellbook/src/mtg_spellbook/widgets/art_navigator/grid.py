"""Filmstrip layout for printings gallery - horizontal scrolling thumbnails."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Horizontal, HorizontalScroll

from .shop_card import ShopCard

if TYPE_CHECKING:
    from collections.abc import Callable

    from mtg_core.data.models.responses import PrintingInfo

SORT_LABELS = {
    "price": "[$] Price",
    "set": "[A] Set",
    "rarity": "[R] Rarity",
}


class PrintingsGrid(HorizontalScroll, can_focus=True):
    """Horizontal filmstrip of card thumbnails for all printings."""

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._printings: list[PrintingInfo] = []
        self._filtered_printings: list[PrintingInfo] = []
        self._cards: list[ShopCard] = []
        self._selected_index: int = 0
        self._on_select: Callable[[int, PrintingInfo], None] | None = None
        self._card_name: str = ""
        self._compare_marked: set[tuple[str, str]] = set()
        self._current_sort: str = "price"
        self._load_generation: int = 0
        self._filter_set: str | None = None
        self._filter_rarity: str | None = None

    def compose(self) -> ComposeResult:
        """Build filmstrip with horizontal card container."""
        yield Horizontal(id="filmstrip-container", classes="filmstrip-container")

    def set_on_select(self, callback: Callable[[int, PrintingInfo], None]) -> None:
        """Set callback for when a printing is selected."""
        self._on_select = callback

    async def load_printings(
        self,
        card_name: str,
        printings: list[PrintingInfo],
        sort_order: str = "price",
        *,
        reset_filters: bool = True,
    ) -> None:
        """Load and display printings in filmstrip."""
        self._load_generation += 1
        current_generation = self._load_generation

        self._card_name = card_name
        self._current_sort = sort_order
        self._printings = printings
        if reset_filters:
            self._filter_set = None
            self._filter_rarity = None

        # Apply sort and filters
        self._filtered_printings = self._apply_filters_and_sort(printings, sort_order)
        self._selected_index = 0

        # Get the container
        container = self.query_one("#filmstrip-container", Horizontal)

        # Remove old cards
        if self._cards:
            await container.query(".shop-card").remove()
            self._cards.clear()

        if current_generation != self._load_generation:
            return

        # Create all shop cards (batch preparation)
        cards_to_mount: list[ShopCard] = []
        for idx, printing in enumerate(self._filtered_printings):
            if printing.uuid:
                unique_id = f"g{current_generation}-{printing.uuid}"
            else:
                unique_id = f"g{current_generation}-{printing.set_code or 'unk'}-{printing.collector_number or idx}"
            card = ShopCard(
                printing,
                id=f"shop-{unique_id}",
                classes="shop-card",
            )
            cards_to_mount.append(card)
            self._cards.append(card)

        if current_generation != self._load_generation:
            self._cards.clear()
            return

        # Batch mount all cards into the container
        if cards_to_mount:
            await container.mount_all(cards_to_mount)

        if current_generation != self._load_generation:
            return

        if self._cards and self._filtered_printings:
            self._cards[0].set_selected(True)
            if self._on_select:
                self._on_select(0, self._filtered_printings[0])

    def _apply_filters_and_sort(
        self, printings: list[PrintingInfo], sort_order: str
    ) -> list[PrintingInfo]:
        """Apply filters and sorting to printings."""
        filtered = list(printings)

        if self._filter_set:
            filtered = [
                p for p in filtered if p.set_code and p.set_code.lower() == self._filter_set.lower()
            ]

        if self._filter_rarity:
            filtered = [
                p for p in filtered if p.rarity and p.rarity.lower() == self._filter_rarity.lower()
            ]

        return self._sort_printings(filtered, sort_order)

    def _sort_printings(self, printings: list[PrintingInfo], sort_order: str) -> list[PrintingInfo]:
        """Sort printings by the specified order."""
        if sort_order == "price":
            return sorted(
                printings,
                key=lambda p: p.price_usd if p.price_usd is not None else -1,
                reverse=True,
            )
        elif sort_order == "set":
            return sorted(printings, key=lambda p: p.set_code or "")
        elif sort_order == "rarity":
            rarity_order = {"mythic": 0, "rare": 1, "uncommon": 2, "common": 3, "special": 4}
            return sorted(
                printings,
                key=lambda p: rarity_order.get((p.rarity or "").lower(), 99),
            )
        return printings

    def get_available_sets(self) -> list[str]:
        """Get list of unique set codes in current printings."""
        sets = {p.set_code.upper() for p in self._printings if p.set_code}
        return sorted(sets)

    def get_available_rarities(self) -> list[str]:
        """Get list of unique rarities in current printings."""
        rarities = {p.rarity.lower() for p in self._printings if p.rarity}
        return sorted(rarities)

    async def set_filter(self, set_code: str | None = None, rarity: str | None = None) -> None:
        """Set filter and reload display."""
        self._filter_set = set_code
        self._filter_rarity = rarity
        await self.load_printings(
            self._card_name, self._printings, self._current_sort, reset_filters=False
        )

    def navigate(self, direction: str) -> bool:
        """Navigate filmstrip left/right. Returns True if moved."""
        if not self._filtered_printings:
            return False

        old_index = self._selected_index
        total = len(self._filtered_printings)

        if direction == "left":
            if old_index == 0:
                self.notify("First printing", severity="warning", timeout=1.5)
                return False
            self._select_index(old_index - 1)
            return True
        elif direction == "right":
            if old_index == total - 1:
                self.notify("Last printing", severity="warning", timeout=1.5)
                return False
            self._select_index(old_index + 1)
            return True
        # Up/down don't apply to filmstrip, but don't show error
        return False

    def _select_index(self, index: int) -> None:
        """Select a card by index."""
        if not (0 <= index < len(self._filtered_printings)):
            return

        if 0 <= self._selected_index < len(self._cards):
            self._cards[self._selected_index].set_selected(False)

        self._selected_index = index
        self._cards[index].set_selected(True)
        self._cards[index].scroll_visible()

        if self._on_select:
            self._on_select(index, self._filtered_printings[index])

    def cycle_sort(self) -> None:
        """Cycle through sort orders: price -> set -> rarity -> price."""
        sort_cycle = {"price": "set", "set": "rarity", "rarity": "price"}
        new_sort = sort_cycle.get(self._current_sort, "price")

        if self._printings:
            self._current_sort = new_sort
            self.run_worker(self.load_printings(self._card_name, self._printings, new_sort))
            self.notify(
                f"Sorted by {SORT_LABELS.get(new_sort, new_sort)}",
                severity="information",
                timeout=1.5,
            )

    def get_current_printing(self) -> PrintingInfo | None:
        """Get the currently selected printing."""
        if 0 <= self._selected_index < len(self._filtered_printings):
            return self._filtered_printings[self._selected_index]
        return None

    def mark_in_compare(self, printing: PrintingInfo) -> None:
        """Mark a printing as added to comparison."""
        key = (printing.set_code or "", printing.collector_number or "")
        self._compare_marked.add(key)

        for i, p in enumerate(self._filtered_printings):
            p_key = (p.set_code or "", p.collector_number or "")
            if p_key == key and i < len(self._cards):
                self._cards[i].add_class("in-compare")

    def clear_compare_marks(self) -> None:
        """Clear all comparison marks."""
        self._compare_marked.clear()
        for card in self._cards:
            card.remove_class("in-compare")

    @property
    def current_index(self) -> int:
        """Get current selected index."""
        return self._selected_index

    @property
    def total_count(self) -> int:
        """Get total number of printings."""
        return len(self._filtered_printings)
