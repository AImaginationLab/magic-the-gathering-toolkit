"""ArtistBrowser widget for browsing all artists alphabetically."""

from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import Input, ListItem, ListView, Static

from ...ui.theme import ui_colors
from .messages import ArtistBrowserClosed, ArtistSelected

if TYPE_CHECKING:
    from mtg_core.data.models.responses import ArtistSummary

# Debounce delay for search input (milliseconds)
SEARCH_DEBOUNCE_MS = 150
# Batch size for progressive list loading
LIST_BATCH_SIZE = 50
# Maximum items to display at once (performance limit)
MAX_DISPLAY_ITEMS = 50


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


class ArtistBrowser(Vertical, can_focus=True):
    """Simple browser for exploring all artists with search."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape,q", "close", "Close"),
        Binding("up,k", "nav_up", "Up", show=False),
        Binding("down,j", "nav_down", "Down", show=False),
        Binding("pageup", "page_up", "Page Up", show=False),
        Binding("pagedown", "page_down", "Page Down", show=False),
        Binding("home", "first", "First", show=False),
        Binding("end", "last_item", "Last", show=False),
        Binding("enter", "select_artist", "Select"),
        Binding("r", "random_artist", "Random"),
        Binding("/", "focus_search", "Search"),
    ]

    is_loading: reactive[bool] = reactive(False)
    search_query: reactive[str] = reactive("")
    total_count: reactive[int] = reactive(0)
    filtered_count: reactive[int] = reactive(0)

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._artists: list[ArtistSummary] = []
        self._filtered_artists: list[ArtistSummary] = []
        self._search_debounce_task: asyncio.Task[None] | None = None
        self._population_cancelled = False

    def compose(self) -> ComposeResult:
        with Vertical(classes="artist-browser-container"):
            with Horizontal(classes="artist-browser-header"):
                yield Static(
                    self._render_header(),
                    id="artist-browser-title",
                    classes="artist-browser-title",
                )
                yield Input(
                    placeholder="Search artists...",
                    id="artist-search",
                    classes="artist-search",
                )

            yield ListView(id="artist-list", classes="artist-list")

            yield Static(
                self._render_statusbar(),
                id="artist-statusbar",
                classes="artist-statusbar",
            )

    def on_mount(self) -> None:
        """Focus the list on mount."""
        try:
            artist_list = self.query_one("#artist-list", ListView)
            artist_list.focus()
        except NoMatches:
            pass

    def _render_header(self) -> str:
        """Render header text."""
        if self.search_query:
            if self.filtered_count > MAX_DISPLAY_ITEMS:
                return (
                    f"[bold {ui_colors.GOLD}]Artists[/]  "
                    f"[dim]showing first {MAX_DISPLAY_ITEMS} of {self.filtered_count} matches[/]"
                )
            return (
                f"[bold {ui_colors.GOLD}]Artists[/]  "
                f"[dim]showing {self.filtered_count} of {self.total_count}[/]"
            )
        if self.total_count > MAX_DISPLAY_ITEMS:
            return (
                f"[bold {ui_colors.GOLD}]Artists[/]  "
                f"[dim]({self.total_count} total - type to search)[/]"
            )
        return f"[bold {ui_colors.GOLD}]Artists[/]  [dim]({self.total_count} artists)[/]"

    def _render_statusbar(self) -> str:
        """Render status bar."""
        parts = [
            f"[{ui_colors.TEXT_DIM}]jk/arrows: navigate[/]",
            f"[{ui_colors.GOLD}]Enter[/]: view portfolio",
            f"[{ui_colors.GOLD}]r[/]: random",
            f"[{ui_colors.GOLD}]/[/]: search",
            f"[{ui_colors.GOLD}]Esc[/]: close",
        ]
        return "  |  ".join(parts)

    def _update_header(self) -> None:
        """Update header display."""
        try:
            title = self.query_one("#artist-browser-title", Static)
            title.update(self._render_header())
        except NoMatches:
            pass

    async def load_artists(self, artists: list[ArtistSummary]) -> None:
        """Load artists and display in the list."""
        self.is_loading = True
        self._population_cancelled = False
        self._artists = artists
        self._filtered_artists = artists
        self.total_count = len(artists)
        self.filtered_count = len(artists)

        try:
            await self._populate_list_batched(artists)
            if not self._population_cancelled:
                self._update_header()
        finally:
            self.is_loading = False

    async def _populate_list_batched(self, artists: list[ArtistSummary]) -> None:
        """Populate the ListView with artists in batches (limited for performance)."""
        try:
            artist_list = self.query_one("#artist-list", ListView)
            await artist_list.clear()

            if not artists:
                return

            # Limit to MAX_DISPLAY_ITEMS for performance
            display_artists = artists[:MAX_DISPLAY_ITEMS]
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
        if event.input.id == "artist-search":
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
        self.search_query = query
        self._filtered_artists = self._filter_artists(query)
        self.filtered_count = len(self._filtered_artists)

        await self._populate_list_batched(self._filtered_artists)

        if not self._population_cancelled:
            self._update_header()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search submit - focus list."""
        if event.input.id == "artist-search":
            try:
                artist_list = self.query_one("#artist-list", ListView)
                artist_list.focus()
            except NoMatches:
                pass

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle artist selection."""
        if event.list_view.id == "artist-list":
            item = event.item
            if isinstance(item, ArtistListItem):
                self.post_message(ArtistSelected(item.artist))

    def action_close(self) -> None:
        """Close the browser."""
        self.post_message(ArtistBrowserClosed())

    def action_nav_up(self) -> None:
        """Navigate up."""
        try:
            artist_list = self.query_one("#artist-list", ListView)
            if artist_list.index is not None and artist_list.index > 0:
                artist_list.index -= 1
        except NoMatches:
            pass

    def action_nav_down(self) -> None:
        """Navigate down."""
        try:
            artist_list = self.query_one("#artist-list", ListView)
            if artist_list.index is not None:
                max_index = len(artist_list.children) - 1
                if artist_list.index < max_index:
                    artist_list.index += 1
        except NoMatches:
            pass

    def action_page_up(self) -> None:
        """Page up in the list."""
        try:
            artist_list = self.query_one("#artist-list", ListView)
            artist_list.action_page_up()
        except NoMatches:
            pass

    def action_page_down(self) -> None:
        """Page down in the list."""
        try:
            artist_list = self.query_one("#artist-list", ListView)
            artist_list.action_page_down()
        except NoMatches:
            pass

    def action_first(self) -> None:
        """Go to first artist."""
        try:
            artist_list = self.query_one("#artist-list", ListView)
            if artist_list.children:
                artist_list.index = 0
        except NoMatches:
            pass

    def action_last_item(self) -> None:
        """Go to last artist."""
        try:
            artist_list = self.query_one("#artist-list", ListView)
            if artist_list.children:
                artist_list.index = len(artist_list.children) - 1
        except NoMatches:
            pass

    def action_select_artist(self) -> None:
        """Select the current artist."""
        try:
            artist_list = self.query_one("#artist-list", ListView)
            if artist_list.index is not None:
                item = artist_list.children[artist_list.index]
                if isinstance(item, ArtistListItem):
                    self.post_message(ArtistSelected(item.artist))
        except NoMatches:
            pass

    def action_random_artist(self) -> None:
        """Select a random artist."""
        if not self._filtered_artists:
            return

        artist = random.choice(self._filtered_artists)
        self.notify(f"Random: {artist.name}", timeout=1.5)
        self.post_message(ArtistSelected(artist))

    def action_focus_search(self) -> None:
        """Focus the search input."""
        try:
            search = self.query_one("#artist-search", Input)
            search.focus()
        except NoMatches:
            pass

    def get_current_artist(self) -> ArtistSummary | None:
        """Get the currently selected artist."""
        try:
            artist_list = self.query_one("#artist-list", ListView)
            if artist_list.index is not None:
                item = artist_list.children[artist_list.index]
                if isinstance(item, ArtistListItem):
                    return item.artist
        except NoMatches:
            pass
        return None
