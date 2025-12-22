"""Filter bar widget for printings carousel."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, Select, Static

from ...ui.theme import ui_colors


class FilterChanged(Message):
    """Message sent when filter changes."""

    def __init__(
        self,
        set_code: str | None,
        artist: str | None,
        rarity: str | None,
    ) -> None:
        super().__init__()
        self.set_code = set_code
        self.artist = artist
        self.rarity = rarity


class FilterCleared(Message):
    """Message sent when filters are cleared."""

    pass


class FilterBar(Horizontal):
    """Filter bar with dropdown filters for printings."""

    DEFAULT_CSS = """
    FilterBar {
        height: 3;
        background: #1a1a2e;
        border-bottom: solid #3d3d3d;
        padding: 0 2;
        align: left middle;
    }

    FilterBar.hidden {
        display: none;
    }

    FilterBar .filter-label {
        width: auto;
        padding: 0 1;
        color: #888;
    }

    FilterBar Select {
        width: 20;
        margin: 0 1;
    }

    FilterBar #filter-clear {
        margin-left: 2;
    }

    FilterBar #filter-count {
        width: auto;
        margin-right: 2;
    }
    """

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._sets: list[str] = []
        self._artists: list[str] = []
        self._rarities: list[str] = []
        self._active_filters: dict[str, str | None] = {
            "set": None,
            "artist": None,
            "rarity": None,
        }

    def compose(self) -> ComposeResult:
        yield Static("", id="filter-count", classes="filter-label")

        yield Static("Set:", classes="filter-label")
        yield Select(
            [(("All", None))] + [(s.upper(), s) for s in self._sets],
            id="filter-set",
            allow_blank=False,
            value=None,
        )

        yield Static("Artist:", classes="filter-label")
        yield Select(
            [(("All", None))] + [(a, a) for a in self._artists],
            id="filter-artist",
            allow_blank=False,
            value=None,
        )

        yield Static("Rarity:", classes="filter-label")
        yield Select(
            [(("All", None))] + [(r.title(), r) for r in self._rarities],
            id="filter-rarity",
            allow_blank=False,
            value=None,
        )

        yield Button("Clear", id="filter-clear", variant="default")

    def populate_options(
        self,
        sets: list[str],
        artists: list[str],
        rarities: list[str],
        total_count: int,
    ) -> None:
        """Populate filter dropdowns with options."""
        self._sets = sets
        self._artists = artists
        self._rarities = rarities

        # Update count label
        try:
            count_label = self.query_one("#filter-count", Static)
            count_label.update(f"[{ui_colors.GOLD}]{total_count}[/] printings")
        except Exception:
            pass

        # Update select options
        self._update_select("filter-set", [(("All", None))] + [(s.upper(), s) for s in sets])
        self._update_select("filter-artist", [(("All", None))] + [(a, a) for a in artists])
        self._update_select("filter-rarity", [(("All", None))] + [(r.title(), r) for r in rarities])

    def _update_select(self, select_id: str, options: list[tuple[str, str | None]]) -> None:
        """Update options for a select widget."""
        try:
            select = self.query_one(f"#{select_id}", Select)
            select.set_options(options)
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select change events."""
        select_id = event.select.id
        # Value is str | None for our selects (None means "All")
        value = event.value if isinstance(event.value, str) else None

        if select_id == "filter-set":
            self._active_filters["set"] = value
        elif select_id == "filter-artist":
            self._active_filters["artist"] = value
        elif select_id == "filter-rarity":
            self._active_filters["rarity"] = value

        self.post_message(
            FilterChanged(
                set_code=self._active_filters["set"],
                artist=self._active_filters["artist"],
                rarity=self._active_filters["rarity"],
            )
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle clear button press."""
        if event.button.id == "filter-clear":
            self._clear_filters()
            self.post_message(FilterCleared())

    def _clear_filters(self) -> None:
        """Reset all filters to default."""
        self._active_filters = {"set": None, "artist": None, "rarity": None}

        # Reset select widgets
        for select_id in ("filter-set", "filter-artist", "filter-rarity"):
            try:
                select = self.query_one(f"#{select_id}", Select)
                select.value = None
            except Exception:
                pass

    def update_count(self, filtered_count: int, total_count: int) -> None:
        """Update the count display."""
        try:
            count_label = self.query_one("#filter-count", Static)
            if filtered_count == total_count:
                count_label.update(f"[{ui_colors.GOLD}]{total_count}[/] printings")
            else:
                count_label.update(
                    f"[{ui_colors.GOLD}]{filtered_count}[/] of {total_count} printings"
                )
        except Exception:
            pass

    @property
    def has_active_filters(self) -> bool:
        """Check if any filters are active."""
        return any(v is not None for v in self._active_filters.values())
