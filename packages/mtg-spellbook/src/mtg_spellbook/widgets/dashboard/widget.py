"""Interactive dashboard widget (V4)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static

from .quick_links import QuickLinksBar
from .search_bar import SearchBar

if TYPE_CHECKING:
    from mtg_core.data.database import MTGDatabase, ScryfallDatabase
    from mtg_core.data.models.responses import ArtistSummary


class ArtistSpotlight(Static, can_focus=True):
    """Focusable artist spotlight section."""

    DEFAULT_CSS = """
    ArtistSpotlight {
        height: auto;
        min-height: 10;
        background: #151515;
        border: round #3d3d3d;
        padding: 1 2;
        margin: 2 0 1 0;
    }

    ArtistSpotlight:focus {
        border: heavy #c9a227;
    }
    """


class Dashboard(Vertical, can_focus=False):
    """Interactive discovery dashboard shown on launch.

    V4 Design:
    - TOP: Quick Links bar (focusable buttons)
    - MIDDLE: Search bar with autocomplete dropdown
    - BOTTOM: Artist spotlight (focusable)

    Tab navigation flows through all sections.
    """

    DEFAULT_CSS = """
    Dashboard {
        width: 100%;
        height: 100%;
        background: #0d0d0d;
        padding: 1 2;
        overflow-y: auto;
    }
    """

    is_loading: reactive[bool] = reactive(True)

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._db: MTGDatabase | None = None
        self._scryfall: ScryfallDatabase | None = None
        self._artist: ArtistSummary | None = None

    def compose(self) -> ComposeResult:
        # TOP: Quick links (auto-focused on load)
        yield QuickLinksBar(id="quick-links-bar")

        # MIDDLE: Search bar with dropdown
        yield SearchBar(id="dashboard-search-bar")

        # BOTTOM: Artist Spotlight (focusable)
        yield ArtistSpotlight(
            "[dim]Loading artist spotlight...[/]",
            id="artist-spotlight-content",
        )

    def on_mount(self) -> None:
        """Focus search input on mount."""
        self.call_after_refresh(self.focus_search)

    def set_database(self, db: MTGDatabase) -> None:
        """Set database connection."""
        self._db = db
        # Also set on search bar
        search_bar = self.query_one("#dashboard-search-bar", SearchBar)
        search_bar.set_databases(db, self._scryfall)

    def set_scryfall(self, scryfall: ScryfallDatabase | None) -> None:
        """Set scryfall database connection."""
        self._scryfall = scryfall
        # Also set on search bar if db is already set
        if self._db:
            search_bar = self.query_one("#dashboard-search-bar", SearchBar)
            search_bar.set_databases(self._db, scryfall)

    @work
    async def load_dashboard(self) -> None:
        """Load dashboard content from database."""
        if not self._db:
            return

        self.is_loading = True

        try:
            # Load artist spotlight
            artist = await self._db.get_random_artist_for_spotlight(min_cards=20)
            if artist:
                self._artist = artist
                self._update_artist_spotlight(artist)

        finally:
            self.is_loading = False

    def _update_artist_spotlight(self, artist: ArtistSummary) -> None:
        """Update artist spotlight with content."""
        from ...ui.theme import ui_colors

        year_range = ""
        if artist.first_card_year and artist.most_recent_year:
            if artist.first_card_year == artist.most_recent_year:
                year_range = f" · {artist.first_card_year}"
            else:
                year_range = f" · {artist.first_card_year}-{artist.most_recent_year}"

        # Build multi-line content
        content = (
            f"\n[bold {ui_colors.GOLD}]✨ ARTIST SPOTLIGHT[/]\n\n"
            f"   [bold {ui_colors.GOLD}]{artist.name}[/]\n\n"
        )

        # Add description if available
        if hasattr(artist, "bio") and artist.bio:
            bio_lines = artist.bio.split(". ")[:2]
            bio_text = ". ".join(bio_lines) + "."
            content += f"   [dim]{bio_text}[/]\n\n"
        else:
            content += "   [dim]Notable MTG artist with distinctive style[/]\n\n"

        # Add stats
        content += (
            f"   [dim]{artist.card_count} cards illustrated · "
            f"{artist.sets_count} sets{year_range}[/]\n\n"
        )

        # Add CTA
        content += (
            f"   [dim]Type[/] [bold {ui_colors.GOLD}]artist {artist.name}[/] "
            f"[dim]to view full portfolio[/]\n"
        )

        spotlight = self.query_one("#artist-spotlight-content", ArtistSpotlight)
        spotlight.update(content)

    def clear(self) -> None:
        """Clear dashboard content."""
        self.is_loading = True
        self._artist = None
        # Clear search bar
        search_bar = self.query_one("#dashboard-search-bar", SearchBar)
        search_bar.clear()

    def focus_search(self) -> None:
        """Focus the search input."""
        search_bar = self.query_one("#dashboard-search-bar", SearchBar)
        search_bar.focus_search()
