"""Filter panel for the recommendations screen."""

from __future__ import annotations

from enum import Enum
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from ..ui.theme import ui_colors


class FilterType(Enum):
    """Filter options for recommendations."""

    ALL = "all"
    OWNED = "owned"
    NEED = "need"
    COMBOS = "combos"
    TOP_TIER = "top"


class SortOrder(Enum):
    """Sort options for recommendations."""

    SCORE = "score"
    OWNED_FIRST = "owned"
    CMC = "cmc"
    NAME = "name"


class FilterChanged(Message):
    """Posted when filter changes."""

    def __init__(self, filter_type: FilterType) -> None:
        super().__init__()
        self.filter_type = filter_type


class SortChanged(Message):
    """Posted when sort order changes."""

    def __init__(self, sort_order: SortOrder) -> None:
        super().__init__()
        self.sort_order = sort_order


class RecommendationFilterPanel(Vertical):
    """Left pane filter panel with filter and sort options."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("1", "filter_all", "All", show=False),
        Binding("2", "filter_owned", "Owned", show=False),
        Binding("3", "filter_need", "Need", show=False),
        Binding("4", "filter_combos", "Combos", show=False),
        Binding("5", "filter_top", "Top", show=False),
    ]

    DEFAULT_CSS = """
    RecommendationFilterPanel {
        width: 100%;
        height: auto;
        padding: 1;
    }

    .rec-filter-section {
        height: auto;
        padding: 0;
        margin-bottom: 1;
    }

    .rec-filter-header {
        text-style: bold;
        padding: 0 0 1 0;
    }

    .rec-filter-option {
        height: auto;
        padding: 0 1;
    }

    .rec-filter-option.active {
        background: #2a2a4e;
    }
    """

    active_filter: reactive[FilterType] = reactive(FilterType.ALL)
    active_sort: reactive[SortOrder] = reactive(SortOrder.SCORE)

    # Filter counts
    all_count: reactive[int] = reactive(0)
    owned_count: reactive[int] = reactive(0)
    need_count: reactive[int] = reactive(0)
    combos_count: reactive[int] = reactive(0)
    top_count: reactive[int] = reactive(0)

    def __init__(
        self,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)

    def compose(self) -> ComposeResult:
        # Filter section
        with Vertical(classes="rec-filter-section"):
            yield Static(f"[{ui_colors.GOLD}]FILTER[/]", classes="rec-filter-header")
            yield Static(id="rec-filter-all", classes="rec-filter-option active")
            yield Static(id="rec-filter-owned", classes="rec-filter-option")
            yield Static(id="rec-filter-need", classes="rec-filter-option")
            yield Static(id="rec-filter-combos", classes="rec-filter-option")
            yield Static(id="rec-filter-top", classes="rec-filter-option")

        # Sort section
        with Vertical(classes="rec-filter-section"):
            yield Static(f"[{ui_colors.GOLD}]SORT BY[/]", classes="rec-filter-header")
            yield Static(id="rec-sort-score", classes="rec-filter-option active")
            yield Static(id="rec-sort-owned", classes="rec-filter-option")
            yield Static(id="rec-sort-cmc", classes="rec-filter-option")
            yield Static(id="rec-sort-name", classes="rec-filter-option")

    def on_mount(self) -> None:
        """Update display on mount."""
        self._update_filter_display()
        self._update_sort_display()

    def _update_filter_display(self) -> None:
        """Update filter options display."""
        filters = [
            ("rec-filter-all", FilterType.ALL, "All", self.all_count),
            ("rec-filter-owned", FilterType.OWNED, "Owned", self.owned_count),
            ("rec-filter-need", FilterType.NEED, "Need", self.need_count),
            ("rec-filter-combos", FilterType.COMBOS, "Combos", self.combos_count),
            ("rec-filter-top", FilterType.TOP_TIER, "Top Tier", self.top_count),
        ]

        for widget_id, filter_type, label, count in filters:
            try:
                widget = self.query_one(f"#{widget_id}", Static)
                is_active = self.active_filter == filter_type
                bullet = chr(0x25CF) if is_active else chr(0x25CB)
                color = ui_colors.GOLD if is_active else ui_colors.TEXT_DIM

                widget.update(f"[{color}]{bullet}[/] {label} ({count})")
                widget.set_class(is_active, "active")
            except Exception:
                pass

    def _update_sort_display(self) -> None:
        """Update sort options display."""
        sorts = [
            ("rec-sort-score", SortOrder.SCORE, "Score"),
            ("rec-sort-owned", SortOrder.OWNED_FIRST, "Owned First"),
            ("rec-sort-cmc", SortOrder.CMC, "CMC"),
            ("rec-sort-name", SortOrder.NAME, "Name"),
        ]

        for widget_id, sort_type, label in sorts:
            try:
                widget = self.query_one(f"#{widget_id}", Static)
                is_active = self.active_sort == sort_type
                bullet = chr(0x25CF) if is_active else chr(0x25CB)
                color = ui_colors.GOLD if is_active else ui_colors.TEXT_DIM

                widget.update(f"[{color}]{bullet}[/] {label}")
                widget.set_class(is_active, "active")
            except Exception:
                pass

    def watch_active_filter(self, filter_type: FilterType) -> None:
        """React to filter changes."""
        self._update_filter_display()
        self.post_message(FilterChanged(filter_type))

    def watch_active_sort(self, sort_order: SortOrder) -> None:
        """React to sort changes."""
        self._update_sort_display()
        self.post_message(SortChanged(sort_order))

    def set_counts(
        self,
        all_count: int,
        owned_count: int,
        need_count: int,
        combos_count: int,
        top_count: int,
    ) -> None:
        """Update filter counts."""
        self.all_count = all_count
        self.owned_count = owned_count
        self.need_count = need_count
        self.combos_count = combos_count
        self.top_count = top_count
        self._update_filter_display()

    def cycle_filter(self) -> None:
        """Cycle to next filter option."""
        filters = list(FilterType)
        current_idx = filters.index(self.active_filter)
        self.active_filter = filters[(current_idx + 1) % len(filters)]

    def cycle_sort(self) -> None:
        """Cycle to next sort option."""
        sorts = list(SortOrder)
        current_idx = sorts.index(self.active_sort)
        self.active_sort = sorts[(current_idx + 1) % len(sorts)]

    def action_filter_all(self) -> None:
        self.active_filter = FilterType.ALL

    def action_filter_owned(self) -> None:
        self.active_filter = FilterType.OWNED

    def action_filter_need(self) -> None:
        self.active_filter = FilterType.NEED

    def action_filter_combos(self) -> None:
        self.active_filter = FilterType.COMBOS

    def action_filter_top(self) -> None:
        self.active_filter = FilterType.TOP_TIER
