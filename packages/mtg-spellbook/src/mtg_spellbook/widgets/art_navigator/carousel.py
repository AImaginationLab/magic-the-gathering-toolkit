"""Printings carousel widget for browsing card printings."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Static

from ...ui.theme import rarity_colors, ui_colors
from .card_slot import CardSlot
from .image_loader import load_image_from_url
from .messages import ArtistSelected

if TYPE_CHECKING:
    from mtg_core.data.models.responses import PrintingInfo


class PrintingsCarousel(Vertical, can_focus=True):
    """Horizontal carousel showing 3 printings at once."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("h,left", "prev", "Previous", show=False),
        Binding("l,right", "next", "Next", show=False),
        Binding("enter", "browse_artist", "Artist"),
    ]

    DEFAULT_CSS = """
    PrintingsCarousel {
        width: 100%;
        height: 100%;
    }

    PrintingsCarousel .carousel-header {
        height: 2;
        background: #1a1a2e;
        border-bottom: solid #3d3d3d;
        padding: 0 2;
        content-align: center middle;
    }

    PrintingsCarousel .carousel-container {
        height: 1fr;
        align: center middle;
        padding: 1 2;
    }

    PrintingsCarousel .carousel-metadata {
        height: 5;
        padding: 0 2;
        border-top: solid #3d3d3d;
        background: #151515;
    }

    PrintingsCarousel .carousel-nav {
        height: 1;
        dock: bottom;
        background: #1a1a2e;
        padding: 0 2;
        content-align: center middle;
    }
    """

    current_index: reactive[int] = reactive(0)

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._printings: list[PrintingInfo] = []
        self._filtered_printings: list[PrintingInfo] = []
        self._card_name: str = ""
        self._owned_printings: set[tuple[str, str]] = set()  # (set_code, collector_number)
        self._load_generation: int = 0

    def compose(self) -> ComposeResult:
        yield Static("", id="carousel-header", classes="carousel-header")

        with Horizontal(classes="carousel-container"):
            yield CardSlot(id="slot-prev", classes="faded")
            yield CardSlot(id="slot-current", classes="current")
            yield CardSlot(id="slot-next", classes="faded")

        yield Static("", id="carousel-metadata", classes="carousel-metadata")
        yield Static("", id="carousel-nav", classes="carousel-nav")

    def on_mount(self) -> None:
        """Initialize display on mount."""
        self._update_nav()

    def load_printings(
        self,
        printings: list[PrintingInfo],
        card_name: str,
        owned_printings: set[tuple[str, str]] | None = None,
    ) -> None:
        """Load printings into the carousel."""
        self._load_generation += 1
        self._printings = list(printings)
        self._filtered_printings = list(printings)
        self._card_name = card_name
        self._owned_printings = owned_printings or set()
        self.current_index = 0
        self._update_header()
        self._update_display()

    def set_filter(
        self,
        set_code: str | None = None,
        artist: str | None = None,
        rarity: str | None = None,
    ) -> None:
        """Filter printings by criteria."""
        filtered = self._printings

        if set_code:
            filtered = [
                p for p in filtered if p.set_code and p.set_code.lower() == set_code.lower()
            ]
        if artist:
            filtered = [p for p in filtered if p.artist and artist.lower() in p.artist.lower()]
        if rarity:
            filtered = [p for p in filtered if p.rarity and p.rarity.lower() == rarity.lower()]

        self._filtered_printings = filtered
        self.current_index = 0
        self._update_header()
        self._update_display()

    def clear_filter(self) -> None:
        """Clear all filters."""
        self._filtered_printings = list(self._printings)
        self.current_index = 0
        self._update_header()
        self._update_display()

    def _update_header(self) -> None:
        """Update the header with count info."""
        try:
            header = self.query_one("#carousel-header", Static)
        except Exception:
            return

        total = len(self._printings)
        filtered = len(self._filtered_printings)

        if filtered == total:
            header.update(
                f"[bold {ui_colors.GOLD}]{total} Printings[/] of [bold]{self._card_name}[/]"
            )
        else:
            header.update(
                f"[bold {ui_colors.GOLD}]{filtered} of {total} Printings[/] of "
                f"[bold]{self._card_name}[/] [dim](filtered)[/]"
            )

    def _update_display(self) -> None:
        """Update all slots and metadata."""
        if not self._filtered_printings:
            self._clear_display()
            return

        # Get prev, current, next printings
        idx = self.current_index
        prev_printing = self._filtered_printings[idx - 1] if idx > 0 else None
        current_printing = self._filtered_printings[idx]
        next_printing = (
            self._filtered_printings[idx + 1] if idx < len(self._filtered_printings) - 1 else None
        )

        # Update slots
        self._update_slot("slot-prev", prev_printing)
        self._update_slot("slot-current", current_printing)
        self._update_slot("slot-next", next_printing)

        # Update metadata for current
        self._update_metadata(current_printing)
        self._update_nav()

        # Load images asynchronously
        self._load_images()

    def _update_slot(self, slot_id: str, printing: PrintingInfo | None) -> None:
        """Update a single card slot."""
        try:
            slot = self.query_one(f"#{slot_id}", CardSlot)
        except Exception:
            return

        if printing:
            owned = self._is_owned(printing)
            slot.set_printing(printing, owned=owned)
        else:
            slot.set_printing(None)

    def _is_owned(self, printing: PrintingInfo) -> bool:
        """Check if a printing is owned."""
        if not printing.set_code or not printing.collector_number:
            return False
        return (printing.set_code.lower(), printing.collector_number) in self._owned_printings

    def _update_metadata(self, printing: PrintingInfo) -> None:
        """Update the metadata panel for current printing."""
        try:
            meta = self.query_one("#carousel-metadata", Static)
        except Exception:
            return

        lines = []

        # Line 1: Set name, collector number, rarity
        set_info = printing.set_code.upper() if printing.set_code else "Unknown"
        if printing.collector_number:
            set_info += f" · #{printing.collector_number}"

        rarity = printing.rarity or "Unknown"
        rarity_color = getattr(rarity_colors, rarity.upper(), rarity_colors.DEFAULT)

        lines.append(f"[{ui_colors.GOLD}]{set_info}[/] · [{rarity_color}]{rarity.title()}[/]")

        # Line 2: Artist
        artist = printing.artist or "Unknown Artist"
        lines.append(f"[dim]Artist:[/] [{ui_colors.GOLD}]{artist}[/] [dim](Enter to browse)[/]")

        # Line 3: Prices
        price_parts = []
        if printing.price_usd is not None:
            price_parts.append(f"[green]USD ${printing.price_usd:.2f}[/]")
        if printing.price_eur is not None:
            price_parts.append(f"[cyan]EUR €{printing.price_eur:.2f}[/]")
        if not price_parts:
            price_parts.append("[dim]No price data[/]")

        lines.append(" · ".join(price_parts))

        # Line 4: Owned status
        if self._is_owned(printing):
            lines.append("[green bold]✓ In your collection[/]")
        else:
            lines.append("[dim]Not in collection · Press [bold]a[/] to add[/]")

        meta.update("\n".join(lines))

    def _update_nav(self) -> None:
        """Update the navigation bar."""
        try:
            nav = self.query_one("#carousel-nav", Static)
        except Exception:
            return

        if not self._filtered_printings:
            nav.update("[dim]No printings[/]")
            return

        idx = self.current_index + 1
        total = len(self._filtered_printings)

        nav.update(
            f"[dim]←[/] [{ui_colors.GOLD}]{idx} of {total}[/] [dim]→[/]   "
            f"[{ui_colors.GOLD}]h/l[/]: navigate   "
            f"[{ui_colors.GOLD}]a[/]: add   "
            f"[{ui_colors.GOLD}]f[/]: filter   "
            f"[{ui_colors.GOLD}]Esc[/]: close"
        )

    def _clear_display(self) -> None:
        """Clear all slots when no printings."""
        for slot_id in ("slot-prev", "slot-current", "slot-next"):
            self._update_slot(slot_id, None)

        try:
            meta = self.query_one("#carousel-metadata", Static)
            meta.update("[dim]No printings to display[/]")
        except Exception:
            pass

        self._update_nav()

    @work
    async def _load_images(self) -> None:
        """Load images for visible slots."""
        generation = self._load_generation

        for slot_id in ("slot-prev", "slot-current", "slot-next"):
            if self._load_generation != generation:
                return  # Cancelled

            try:
                slot = self.query_one(f"#{slot_id}", CardSlot)
                if slot.printing and slot.printing.image and slot.image_widget:
                    await load_image_from_url(slot.printing.image, slot.image_widget)
            except Exception:
                pass

    def action_prev(self) -> None:
        """Navigate to previous printing."""
        if self.current_index > 0:
            self.current_index -= 1
            self._update_display()
        else:
            self.notify("First printing", timeout=1)

    def action_next(self) -> None:
        """Navigate to next printing."""
        if self.current_index < len(self._filtered_printings) - 1:
            self.current_index += 1
            self._update_display()
        else:
            self.notify("Last printing", timeout=1)

    def action_browse_artist(self) -> None:
        """Browse cards by the current artist."""
        if not self._filtered_printings:
            return

        current = self._filtered_printings[self.current_index]
        if current.artist:
            self.post_message(ArtistSelected(current.artist, self._card_name))

    @property
    def current_printing(self) -> PrintingInfo | None:
        """Get the currently displayed printing."""
        if not self._filtered_printings:
            return None
        return self._filtered_printings[self.current_index]

    @property
    def card_name(self) -> str:
        """Get the card name."""
        return self._card_name

    def get_unique_sets(self) -> list[str]:
        """Get unique set codes from printings."""
        sets = {p.set_code.lower() for p in self._printings if p.set_code}
        return sorted(sets)

    def get_unique_artists(self) -> list[str]:
        """Get unique artists from printings."""
        artists = {p.artist for p in self._printings if p.artist}
        return sorted(artists)

    def get_unique_rarities(self) -> list[str]:
        """Get unique rarities from printings."""
        rarities = {p.rarity.lower() for p in self._printings if p.rarity}
        return sorted(rarities)
