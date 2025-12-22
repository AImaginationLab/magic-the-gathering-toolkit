"""Full-screen artist browser with search and preview."""

from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING, ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import Input, ListItem, ListView, Static

from ..ui.theme import ui_colors
from .base import BaseScreen

if TYPE_CHECKING:
    from mtg_core.data.database import UnifiedDatabase
    from mtg_core.data.models.responses import ArtistSummary

# Debounce delay for search input (milliseconds)
SEARCH_DEBOUNCE_MS = 150
# Maximum items to display at once (performance limit)
MAX_DISPLAY_ITEMS = 50
# Batch size for progressive list loading
LIST_BATCH_SIZE = 50


class ArtistListItem(ListItem):
    """List item representing an artist."""

    def __init__(
        self,
        artist: ArtistSummary,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.artist = artist

    def compose(self) -> ComposeResult:
        years = ""
        if self.artist.first_card_year and self.artist.most_recent_year:
            if self.artist.first_card_year == self.artist.most_recent_year:
                years = f"({self.artist.first_card_year})"
            else:
                years = f"({self.artist.first_card_year}-{self.artist.most_recent_year})"
        elif self.artist.first_card_year:
            years = f"(since {self.artist.first_card_year})"

        content = (
            f"[bold]{self.artist.name}[/]  "
            f"[cyan]{self.artist.card_count}[/] cards  "
            f"[dim]{self.artist.sets_count} sets[/]  "
            f"[dim]{years}[/]"
        )
        yield Static(content, classes="artist-item-content")


class ArtistsScreen(BaseScreen[None]):
    """Full-screen artist browser with search and preview.

    Features:
    - Searchable list of all artists
    - Keyboard navigation
    - Random artist selection
    - Opens artist portfolio on selection
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape,q", "exit", "Exit", show=True),
        Binding("enter", "select_artist", "Select"),
        Binding("r", "random_artist", "Random"),
        Binding("slash", "focus_search", "Search"),
        # Navigation
        Binding("up,k", "nav_up", "Up", show=False),
        Binding("down,j", "nav_down", "Down", show=False),
        Binding("pageup", "page_up", "Page Up", show=False),
        Binding("pagedown", "page_down", "Page Down", show=False),
        Binding("home", "first", "First", show=False),
        Binding("end", "last_item", "Last", show=False),
    ]

    # Don't show footer - this screen has its own status bar
    show_footer: ClassVar[bool] = False

    CSS = """
    ArtistsScreen {
        background: #0d0d0d;
    }

    /* Override screen-content to use grid for proper height distribution.
       Only 2 rows: header (4 lines) and main (fills remaining). Statusbar goes inside main. */
    ArtistsScreen #screen-content {
        width: 100%;
        height: 100%;
        layout: grid;
        grid-size: 1;
        grid-rows: 4 1fr;
    }

    #artists-header {
        background: #0a0a14;
        border-bottom: heavy #c9a227;
        padding: 0 2;
        content-align: center middle;
    }

    /* Grid child must use 1fr to fill its row properly */
    #artists-main {
        width: 100%;
        height: 1fr;
    }

    #artists-list-pane {
        width: 100%;
        height: 100%;
        background: #0a0a14;
        /* Grid layout: search (3 lines), list (fills), statusbar (2 lines) */
        layout: grid;
        grid-size: 1;
        grid-rows: auto 1fr auto;
    }

    #artists-search-container {
        height: 3;
        padding: 0 1;
        background: #151515;
        border-bottom: solid #2a2a2a;
    }

    #artists-search-input {
        width: 100%;
        background: #1a1a2e;
        border: tall #3d3d3d;
    }

    #artists-search-input:focus {
        border: tall #c9a227;
        background: #1e1e32;
    }

    #artists-list {
        height: 1fr;
        scrollbar-color: #c9a227;
        scrollbar-color-hover: #e6c84a;
    }

    #artists-list > ListItem {
        padding: 0 1;
        height: auto;
        border-bottom: solid #1a1a1a;
        background: #121212;
    }

    #artists-list > ListItem:hover {
        background: #1a1a2e;
        border-left: solid #5a5a6e;
    }

    #artists-list > ListItem.-highlight {
        background: #2a2a4e;
        border-left: heavy #c9a227;
    }

    #artists-statusbar {
        height: 2;
        padding: 0 1;
        background: #1a1a1a;
        border-top: solid #3d3d3d;
        content-align: left middle;
    }
    """

    # Reactive state
    search_query: reactive[str] = reactive("")
    total_count: reactive[int] = reactive(0)
    filtered_count: reactive[int] = reactive(0)

    def __init__(self, db: UnifiedDatabase | None = None) -> None:
        super().__init__()
        self._db = db
        self._artists: list[ArtistSummary] = []
        self._filtered_artists: list[ArtistSummary] = []
        self._search_debounce_task: asyncio.Task[None] | None = None
        self._population_cancelled = False

    def compose_content(self) -> ComposeResult:
        # Header
        yield Static(
            self._render_header(),
            id="artists-header",
        )

        # Main content - statusbar is inside the list pane, not a separate grid row
        with Horizontal(id="artists-main"), Vertical(id="artists-list-pane"):
            # Search
            with Horizontal(id="artists-search-container"):
                yield Input(
                    placeholder="Search artists...",
                    id="artists-search-input",
                )

            # Artist list
            yield ListView(id="artists-list")

            # Status bar (inside list pane to avoid grid issues)
            yield Static(
                self._render_statusbar(),
                id="artists-statusbar",
            )

    def _render_header(self) -> str:
        """Render header text."""
        if self.search_query:
            if self.filtered_count > MAX_DISPLAY_ITEMS:
                return (
                    f"[bold {ui_colors.GOLD}]ARTISTS[/]  "
                    f"[dim]showing first {MAX_DISPLAY_ITEMS} of {self.filtered_count} matches[/]"
                )
            return (
                f"[bold {ui_colors.GOLD}]ARTISTS[/]  "
                f"[dim]showing {self.filtered_count} of {self.total_count}[/]"
            )
        if self.total_count > MAX_DISPLAY_ITEMS:
            return (
                f"[bold {ui_colors.GOLD}]ARTISTS[/]  "
                f"[dim]({self.total_count} total - type to search)[/]"
            )
        return f"[bold {ui_colors.GOLD}]ARTISTS[/]  [dim]({self.total_count} artists)[/]"

    def _render_statusbar(self) -> str:
        """Render status bar."""
        parts = [
            f"[{ui_colors.TEXT_DIM}]jk/arrows: navigate[/]",
            f"[{ui_colors.GOLD}]Enter[/]: view portfolio",
            f"[{ui_colors.GOLD}]r[/]: random",
            f"[{ui_colors.GOLD}]/[/]: search",
            f"[{ui_colors.GOLD}]Esc[/]: exit",
        ]
        return "  |  ".join(parts)

    def _update_header(self) -> None:
        """Update header display."""
        try:
            header = self.query_one("#artists-header", Static)
            header.update(self._render_header())
        except NoMatches:
            pass

    async def on_mount(self) -> None:
        """Load artists on mount."""
        # Focus the list
        try:
            artist_list = self.query_one("#artists-list", ListView)
            artist_list.focus()
        except NoMatches:
            pass

        # Load artists
        self._load_artists()

    @work
    async def _load_artists(self) -> None:
        """Load all artists from database."""
        if not self._db:
            return

        self._population_cancelled = False

        # Get all artists
        self._artists = await self._db.get_all_artists()
        self._filtered_artists = self._artists
        self.total_count = len(self._artists)
        self.filtered_count = len(self._artists)

        # Populate list
        await self._populate_list()

        # Update UI
        self._update_header()

    async def _populate_list(self) -> None:
        """Populate the ListView with artists."""
        try:
            artist_list = self.query_one("#artists-list", ListView)
            await artist_list.clear()

            if not self._filtered_artists:
                return

            # Limit to MAX_DISPLAY_ITEMS for performance
            display_artists = self._filtered_artists[:MAX_DISPLAY_ITEMS]
            batch_count = 0

            for artist in display_artists:
                if self._population_cancelled:
                    return

                item = ArtistListItem(artist, classes="artist-item")
                await artist_list.append(item)
                batch_count += 1

                # Yield to event loop periodically
                if batch_count >= LIST_BATCH_SIZE:
                    batch_count = 0
                    await asyncio.sleep(0)

            # Select first item
            if artist_list.children:
                artist_list.index = 0

        except NoMatches:
            pass

    def _filter_artists(self, query: str) -> list[ArtistSummary]:
        """Filter artists by search query."""
        if not query:
            return self._artists

        query_lower = query.lower()
        return [a for a in self._artists if query_lower in a.name.lower()]

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes with debouncing."""
        if event.input.id == "artists-search-input":
            if self._search_debounce_task is not None:
                self._search_debounce_task.cancel()
                self._search_debounce_task = None

            self._population_cancelled = True
            self._search_debounce_task = asyncio.create_task(self._debounced_search(event.value))

    async def _debounced_search(self, query: str) -> None:
        """Execute search after debounce delay."""
        try:
            await asyncio.sleep(SEARCH_DEBOUNCE_MS / 1000)
        except asyncio.CancelledError:
            return

        self._population_cancelled = False
        stripped_query = query.strip()
        self.search_query = stripped_query
        self._filtered_artists = self._filter_artists(stripped_query)
        self.filtered_count = len(self._filtered_artists)

        await self._populate_list()

        if not self._population_cancelled:
            self._update_header()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Focus list after search submit."""
        if event.input.id == "artists-search-input":
            try:
                artist_list = self.query_one("#artists-list", ListView)
                artist_list.focus()
            except NoMatches:
                pass

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle artist selection."""
        if event.list_view.id == "artists-list":
            item = event.item
            if isinstance(item, ArtistListItem):
                self._open_artist_portfolio(item.artist)

    def _open_artist_portfolio(self, artist: ArtistSummary) -> None:
        """Open artist portfolio and exit screen."""
        # Capture app reference before dismissing
        app = self.app
        # Pop all screens to return to home before showing artist
        while len(app.screen_stack) > 1:
            app.pop_screen()
        # Use app's _open_artist_portfolio if available (it shows search view first)
        # Otherwise fall back to showing search view then loading artist
        if hasattr(app, "_open_artist_portfolio"):
            app._open_artist_portfolio(artist.name)
        else:
            # Show search view to make results visible (fixes bug where results don't render
            # when going to Artists page without visiting Search first)
            if hasattr(app, "_show_search_view"):
                app._show_search_view()
            app.notify(f"Loading cards by {artist.name}...", timeout=2)
            if hasattr(app, "show_artist"):
                app.show_artist(artist.name)

    # Actions

    def action_exit(self) -> None:
        """Exit the artists screen."""
        self.dismiss()

    def action_select_artist(self) -> None:
        """Select the current artist."""
        try:
            artist_list = self.query_one("#artists-list", ListView)
            if artist_list.index is not None:
                item = artist_list.children[artist_list.index]
                if isinstance(item, ArtistListItem):
                    self._open_artist_portfolio(item.artist)
        except NoMatches:
            pass

    def action_random_artist(self) -> None:
        """Select a random artist."""
        if not self._filtered_artists:
            return

        artist = random.choice(self._filtered_artists)
        self.notify(f"Random: {artist.name}", timeout=1.5)
        self._open_artist_portfolio(artist)

    def action_focus_search(self) -> None:
        """Focus the search input."""
        try:
            search = self.query_one("#artists-search-input", Input)
            search.focus()
        except NoMatches:
            pass

    def action_nav_up(self) -> None:
        """Navigate up in list."""
        try:
            artist_list = self.query_one("#artists-list", ListView)
            artist_list.action_cursor_up()
        except NoMatches:
            pass

    def action_nav_down(self) -> None:
        """Navigate down in list."""
        try:
            artist_list = self.query_one("#artists-list", ListView)
            artist_list.action_cursor_down()
        except NoMatches:
            pass

    def action_page_up(self) -> None:
        """Page up in the list."""
        try:
            artist_list = self.query_one("#artists-list", ListView)
            artist_list.action_page_up()
        except NoMatches:
            pass

    def action_page_down(self) -> None:
        """Page down in the list."""
        try:
            artist_list = self.query_one("#artists-list", ListView)
            artist_list.action_page_down()
        except NoMatches:
            pass

    def action_first(self) -> None:
        """Go to first artist."""
        try:
            artist_list = self.query_one("#artists-list", ListView)
            if artist_list.children:
                artist_list.index = 0
        except NoMatches:
            pass

    def action_last_item(self) -> None:
        """Go to last artist."""
        try:
            artist_list = self.query_one("#artists-list", ListView)
            if artist_list.children:
                artist_list.index = len(artist_list.children) - 1
        except NoMatches:
            pass

    def get_current_artist(self) -> ArtistSummary | None:
        """Get the currently selected artist."""
        try:
            artist_list = self.query_one("#artists-list", ListView)
            if artist_list.index is not None:
                item = artist_list.children[artist_list.index]
                if isinstance(item, ArtistListItem):
                    return item.artist
        except NoMatches:
            pass
        return None
