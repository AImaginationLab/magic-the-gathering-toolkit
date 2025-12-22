"""Artist portfolio view widget for displaying all cards by an artist.

Components:
- ArtistPortfolioView: Main 3-column layout (stats | gallery | preview)
- ArtistStatsPanel: Statistics display panel
- ArtistGallery: Scrollable card gallery
- CardPreviewPanel: Selected card preview
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import ListView, Static

from ..formatting import prettify_mana
from ..ui.formatters import CardFormatters
from ..ui.theme import ui_colors
from .card_result_item import CardResultItem

if TYPE_CHECKING:
    from mtg_core.data.models.responses import CardSummary

# Batch size for progressive list loading
GALLERY_BATCH_SIZE = 50


@dataclass
class ArtistStats:
    """Artist statistics data."""

    name: str
    total_cards: int = 0
    sets_featured: list[str] = field(default_factory=list)
    first_card_year: int | None = None
    most_recent_year: int | None = None
    format_distribution: dict[str, int] = field(default_factory=dict)


class CardSelected(Message):
    """Message sent when a card is selected in the gallery."""

    def __init__(self, card: CardSummary) -> None:
        super().__init__()
        self.card = card


class ArtistStatsPanel(Vertical):
    """Statistics panel displaying artist info and metrics."""

    def compose(self) -> ComposeResult:
        yield Static(
            "[dim]No artist loaded[/]",
            id="stats-artist-name",
            classes="stats-artist-name",
        )
        yield Static("", id="stats-card-count", classes="stats-row")
        yield Static("", id="stats-sets-count", classes="stats-row")
        yield Static("", id="stats-first-card", classes="stats-row")
        yield Static("", id="stats-recent-card", classes="stats-row")
        yield Static("", id="stats-formats-header", classes="stats-section-header")
        yield VerticalScroll(
            Static("", id="stats-formats-list", classes="stats-formats"),
            classes="stats-formats-scroll",
        )

    def update_stats(self, stats: ArtistStats) -> None:
        """Update display with artist statistics."""
        # Artist name
        name_widget = self.query_one("#stats-artist-name", Static)
        name_widget.update(f"[bold {ui_colors.GOLD}]{stats.name}[/]")

        # Card count
        card_count = self.query_one("#stats-card-count", Static)
        card_count.update(f"[dim]Cards Illustrated:[/]  [{ui_colors.GOLD}]{stats.total_cards}[/]")

        # Sets count
        sets_count = self.query_one("#stats-sets-count", Static)
        sets_count.update(
            f"[dim]Sets Featured:[/]      [{ui_colors.GOLD}]{len(stats.sets_featured)}[/]"
        )

        # First card
        first_card = self.query_one("#stats-first-card", Static)
        if stats.first_card_year:
            first_card.update(f"[dim]First Card:[/]         {stats.first_card_year}")
        else:
            first_card.update("[dim]First Card:[/]         [dim]Unknown[/]")

        # Most recent card
        recent_card = self.query_one("#stats-recent-card", Static)
        if stats.most_recent_year:
            recent_card.update(f"[dim]Most Recent:[/]        {stats.most_recent_year}")
        else:
            recent_card.update("[dim]Most Recent:[/]        [dim]Unknown[/]")

        # Format distribution header
        formats_header = self.query_one("#stats-formats-header", Static)
        if stats.format_distribution:
            formats_header.update(f"\n[bold {ui_colors.TEXT_DIM}]Top Formats:[/]")
        else:
            formats_header.update("")

        # Format list
        formats_list = self.query_one("#stats-formats-list", Static)
        if stats.format_distribution:
            sorted_formats = sorted(
                stats.format_distribution.items(), key=lambda x: x[1], reverse=True
            )[:5]
            lines = [f"  [dim]{fmt.capitalize()}[/]  ({count})" for fmt, count in sorted_formats]
            formats_list.update("\n".join(lines))
        else:
            formats_list.update("")

    def clear(self) -> None:
        """Clear all statistics."""
        self.query_one("#stats-artist-name", Static).update("[dim]No artist loaded[/]")
        self.query_one("#stats-card-count", Static).update("")
        self.query_one("#stats-sets-count", Static).update("")
        self.query_one("#stats-first-card", Static).update("")
        self.query_one("#stats-recent-card", Static).update("")
        self.query_one("#stats-formats-header", Static).update("")
        self.query_one("#stats-formats-list", Static).update("")


class ArtistGallery(VerticalScroll):
    """Scrollable gallery of artist's cards."""

    selected_index: reactive[int] = reactive(0)

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._cards: list[CardSummary] = []

    def compose(self) -> ComposeResult:
        yield ListView(id="gallery-list", classes="gallery-list")

    async def load_cards(self, cards: list[CardSummary]) -> None:
        """Load and display card gallery with batched loading for responsiveness."""
        self._cards = cards
        self.selected_index = 0

        gallery_list = self.query_one("#gallery-list", ListView)
        await gallery_list.clear()

        batch_count = 0
        for card in cards:
            item = self._create_card_item(card)
            await gallery_list.append(item)
            batch_count += 1

            # Yield to event loop periodically to keep UI responsive
            if batch_count >= GALLERY_BATCH_SIZE:
                batch_count = 0
                await asyncio.sleep(0)

        # Select first item
        if cards and gallery_list.children:
            gallery_list.index = 0

    def _create_card_item(self, card: CardSummary) -> CardResultItem[CardSummary]:
        """Create a list item for a card using unified CardResultItem."""
        return CardResultItem(card)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle card selection from list view."""
        if event.list_view.id == "gallery-list":
            index = event.list_view.index
            if index is not None and 0 <= index < len(self._cards):
                # Only update index; watcher will post the message
                self.selected_index = index

    def watch_selected_index(self, index: int) -> None:
        """Update selection when index changes - posts CardSelected once."""
        if self._cards and 0 <= index < len(self._cards):
            self.post_message(CardSelected(self._cards[index]))

    def get_selected_card(self) -> CardSummary | None:
        """Get currently selected card."""
        if 0 <= self.selected_index < len(self._cards):
            return self._cards[self.selected_index]
        return None

    def select_random(self) -> CardSummary | None:
        """Select a random card."""
        import random

        if self._cards:
            index = random.randint(0, len(self._cards) - 1)
            gallery_list = self.query_one("#gallery-list", ListView)
            gallery_list.index = index
            self.selected_index = index
            return self._cards[index]
        return None

    def clear(self) -> None:
        """Clear the gallery."""
        self._cards = []
        self.selected_index = 0


class CardPreviewPanel(Vertical):
    """Card preview panel showing selected card details."""

    def compose(self) -> ComposeResult:
        yield Static(
            "[dim]Select a card[/]",
            id="preview-card-name",
            classes="preview-card-name",
        )
        yield Static("", id="preview-mana-cost", classes="preview-mana-cost")
        yield Static("", id="preview-type", classes="preview-type")
        yield Static("", id="preview-set-info", classes="preview-set-info")
        yield VerticalScroll(
            Static("", id="preview-keywords", classes="preview-keywords"),
            Static("", id="preview-price", classes="preview-price"),
            classes="preview-details-scroll",
        )
        yield Static(
            "[dim]Tab: View artwork[/]",
            id="preview-hint",
            classes="preview-hint",
        )

    def update_card(self, card: CardSummary) -> None:
        """Update preview with card details."""
        # Card name - show flavor name prominently if available
        name_widget = self.query_one("#preview-card-name", Static)
        if card.flavor_name and card.flavor_name != card.name:
            name_widget.update(f"[bold {ui_colors.GOLD}]{card.flavor_name}[/]\n[dim]{card.name}[/]")
        else:
            name_widget.update(f"[bold {ui_colors.GOLD}]{card.name}[/]")

        # Mana cost
        mana_widget = self.query_one("#preview-mana-cost", Static)
        if card.mana_cost:
            mana_widget.update(f"[dim]Mana:[/] {prettify_mana(card.mana_cost)}")
        else:
            mana_widget.update("")

        # Type line
        type_widget = self.query_one("#preview-type", Static)
        if card.type:
            type_widget.update(f"[dim]Type:[/] {card.type}")
        else:
            type_widget.update("")

        # Set info
        set_widget = self.query_one("#preview-set-info", Static)
        set_parts = []
        if card.set_code:
            set_parts.append(card.set_code.upper())
        if card.rarity:
            rarity_color = CardFormatters.get_rarity_color(card.rarity)
            set_parts.append(f"[{rarity_color}]{card.rarity}[/]")
        set_widget.update(" - ".join(set_parts) if set_parts else "")

        # Keywords
        keywords_widget = self.query_one("#preview-keywords", Static)
        if card.keywords:
            keywords_widget.update(f"\n[dim]Keywords:[/]\n{', '.join(card.keywords)}")
        else:
            keywords_widget.update("")

        # Price
        price_widget = self.query_one("#preview-price", Static)
        if card.price_usd is not None:
            price_widget.update(f"\n[dim]Price:[/] ${card.price_usd:.2f}")
        else:
            price_widget.update("")

    def clear(self) -> None:
        """Clear the preview."""
        self.query_one("#preview-card-name", Static).update("[dim]Select a card[/]")
        self.query_one("#preview-mana-cost", Static).update("")
        self.query_one("#preview-type", Static).update("")
        self.query_one("#preview-set-info", Static).update("")
        self.query_one("#preview-keywords", Static).update("")
        self.query_one("#preview-price", Static).update("")


class ViewArtwork(Message):
    """Message sent when user wants to view artwork for a card."""

    def __init__(self, card: CardSummary) -> None:
        super().__init__()
        self.card = card


class ClosePortfolio(Message):
    """Message sent when user wants to close the portfolio view."""

    pass


class ArtistPortfolioView(Vertical, can_focus=True):
    """Artist portfolio view with stats, gallery, and card preview.

    3-column layout:
    - Left 45%: Gallery Grid (scrollable card list)
    - Center 25%: Card Preview (selected card details)
    - Right 30%: Statistics Panel (card count, sets, timeline, formats)
    """

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape,q", "close", "Close"),
        Binding("up,k", "nav_up", "Up", show=False),
        Binding("down,j", "nav_down", "Down", show=False),
        Binding("enter", "select_card", "Select"),
        Binding("r", "random_card", "Random"),
        Binding("tab", "view_art", "View Art"),
    ]

    artist_name: reactive[str] = reactive("")
    is_loading: reactive[bool] = reactive(False)

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._cards: list[CardSummary] = []
        self._stats: ArtistStats | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(classes="portfolio-main"):
            yield ArtistGallery(id="portfolio-gallery", classes="portfolio-gallery")
            yield CardPreviewPanel(id="portfolio-preview", classes="portfolio-preview")
            yield ArtistStatsPanel(id="portfolio-stats", classes="portfolio-stats")
        yield Static(
            "[dim]j/k: navigate | Enter: select | r: random | Tab: artwork | Esc: close[/]",
            id="portfolio-statusbar",
            classes="portfolio-statusbar",
        )

    def on_card_selected(self, event: CardSelected) -> None:
        """Handle card selection from gallery."""
        preview = self.query_one("#portfolio-preview", CardPreviewPanel)
        preview.update_card(event.card)

    @work
    async def load_artist(
        self,
        artist_name: str,
        cards: list[CardSummary],
        stats: ArtistStats | None = None,
    ) -> None:
        """Load artist data and display portfolio.

        Args:
            artist_name: Name of the artist.
            cards: List of cards by this artist.
            stats: Optional pre-computed stats. If None, stats are computed from cards.
        """
        self.is_loading = True
        self.artist_name = artist_name
        self._cards = cards

        # Compute stats if not provided
        if stats is None:
            stats = self._compute_stats(artist_name, cards)
        self._stats = stats

        try:
            # Update stats panel
            stats_panel = self.query_one("#portfolio-stats", ArtistStatsPanel)
            stats_panel.update_stats(stats)

            # Load gallery
            gallery = self.query_one("#portfolio-gallery", ArtistGallery)
            await gallery.load_cards(cards)

            # Clear preview (first card will be selected automatically)
            preview = self.query_one("#portfolio-preview", CardPreviewPanel)
            if cards:
                preview.update_card(cards[0])
            else:
                preview.clear()

        finally:
            self.is_loading = False

    def _compute_stats(self, artist_name: str, cards: list[CardSummary]) -> ArtistStats:
        """Compute statistics from card list."""
        sets_featured: set[str] = set()
        years: list[int] = []
        format_counts: dict[str, int] = {}

        for card in cards:
            if card.set_code:
                sets_featured.add(card.set_code.upper())

        stats = ArtistStats(
            name=artist_name,
            total_cards=len(cards),
            sets_featured=sorted(sets_featured),
            first_card_year=min(years) if years else None,
            most_recent_year=max(years) if years else None,
            format_distribution=format_counts,
        )

        return stats

    def action_close(self) -> None:
        """Close the portfolio view."""
        self.post_message(ClosePortfolio())

    def action_nav_up(self) -> None:
        """Navigate up in gallery."""
        try:
            gallery = self.query_one("#portfolio-gallery", ArtistGallery)
            gallery_list = gallery.query_one("#gallery-list", ListView)
            if gallery_list.index is not None and gallery_list.index > 0:
                gallery_list.index -= 1
        except NoMatches:
            pass

    def action_nav_down(self) -> None:
        """Navigate down in gallery."""
        try:
            gallery = self.query_one("#portfolio-gallery", ArtistGallery)
            gallery_list = gallery.query_one("#gallery-list", ListView)
            if gallery_list.index is not None:
                gallery_list.index += 1
        except NoMatches:
            pass

    def action_select_card(self) -> None:
        """Select the current card for full view."""
        try:
            gallery = self.query_one("#portfolio-gallery", ArtistGallery)
            card = gallery.get_selected_card()
            if card:
                self.post_message(ViewArtwork(card))
        except NoMatches:
            pass

    def action_random_card(self) -> None:
        """Select a random card from the gallery."""
        try:
            gallery = self.query_one("#portfolio-gallery", ArtistGallery)
            card = gallery.select_random()
            if card:
                self.notify(f"Random: {card.name}", timeout=1.5)
        except NoMatches:
            pass

    def action_view_art(self) -> None:
        """View artwork for the selected card."""
        try:
            gallery = self.query_one("#portfolio-gallery", ArtistGallery)
            card = gallery.get_selected_card()
            if card:
                self.post_message(ViewArtwork(card))
        except NoMatches:
            pass

    def clear(self) -> None:
        """Clear the portfolio view."""
        self._cards = []
        self._stats = None
        self.artist_name = ""

        try:
            stats_panel = self.query_one("#portfolio-stats", ArtistStatsPanel)
            stats_panel.clear()

            gallery = self.query_one("#portfolio-gallery", ArtistGallery)
            gallery.clear()

            preview = self.query_one("#portfolio-preview", CardPreviewPanel)
            preview.clear()
        except NoMatches:
            pass
