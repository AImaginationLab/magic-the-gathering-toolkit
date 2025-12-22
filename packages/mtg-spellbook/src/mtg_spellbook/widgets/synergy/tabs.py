"""Category tabs widget for synergy panel."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import Static

from ...ui.theme import ui_colors
from .messages import CategoryChanged

if TYPE_CHECKING:
    from mtg_core.data.models.responses import SynergyResult

# Category definitions with display names
CATEGORY_INFO: dict[str, tuple[str, str]] = {
    "all": ("All", "View all synergies"),
    "combo": ("Combos", "Infinite and win combos"),
    "tribal": ("Tribal", "Creature type synergies"),
    "keyword": ("Keywords", "Keyword ability synergies"),
    "ability": ("Abilities", "Triggered/activated ability synergies"),
    "theme": ("Themes", "Theme and archetype synergies"),
}

CATEGORY_ORDER = ["all", "combo", "tribal", "keyword", "ability", "theme"]


class CategoryTab(Static, can_focus=True):
    """A single category tab."""

    is_active: reactive[bool] = reactive(False)

    def __init__(
        self,
        category: str,
        count: int = 0,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.category = category
        self.count = count
        self._label = CATEGORY_INFO.get(category, (category.title(), ""))[0]

    def compose(self) -> ComposeResult:
        return []

    def on_mount(self) -> None:
        """Initialize the tab content."""
        self.update(self._render_tab())

    def _render_tab(self) -> str:
        """Render the tab label with count."""
        if self.is_active:
            return f"[bold {ui_colors.GOLD}][ {self._label} ({self.count}) ][/]"
        else:
            return f"[{ui_colors.TEXT_DIM}]  {self._label} ({self.count})  [/]"

    def watch_is_active(self, _active: bool) -> None:
        """Update display when active state changes."""
        self.update(self._render_tab())

    def update_count(self, count: int) -> None:
        """Update the count and re-render."""
        self.count = count
        self.update(self._render_tab())


class CategoryTabs(Horizontal, can_focus=True):
    """Horizontal tab bar for category navigation."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("tab", "next_tab", "Next Tab", show=False),
        Binding("shift+tab", "prev_tab", "Prev Tab", show=False),
        Binding("1", "select_tab(0)", "All", show=False),
        Binding("2", "select_tab(1)", "Combos", show=False),
        Binding("3", "select_tab(2)", "Tribal", show=False),
        Binding("4", "select_tab(3)", "Keywords", show=False),
        Binding("5", "select_tab(4)", "Abilities", show=False),
        Binding("6", "select_tab(5)", "Themes", show=False),
    ]

    active_index: reactive[int] = reactive(0)

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._category_counts: dict[str, int] = dict.fromkeys(CATEGORY_ORDER, 0)

    def compose(self) -> ComposeResult:
        for i, category in enumerate(CATEGORY_ORDER):
            tab = CategoryTab(
                category,
                count=self._category_counts.get(category, 0),
                id=f"synergy-tab-{category}",
                classes="synergy-category-tab",
            )
            if i == 0:
                tab.is_active = True
            yield tab

    def update_counts(self, synergies: list[SynergyResult]) -> None:
        """Update category counts from synergies."""
        self._category_counts = dict.fromkeys(CATEGORY_ORDER, 0)
        self._category_counts["all"] = len(synergies)

        for syn in synergies:
            syn_type = syn.synergy_type
            # Map synergy types to categories
            if syn_type == "tribal":
                self._category_counts["tribal"] += 1
            elif syn_type == "keyword":
                self._category_counts["keyword"] += 1
            elif syn_type == "ability":
                self._category_counts["ability"] += 1
            elif syn_type in ("theme", "archetype"):
                self._category_counts["theme"] += 1
            # Check if it's a combo (would need combo detection)
            # For now, we'll rely on the synergy_type

        # Update tab widgets
        for category in CATEGORY_ORDER:
            try:
                tab = self.query_one(f"#synergy-tab-{category}", CategoryTab)
                tab.update_count(self._category_counts[category])
            except NoMatches:
                pass

    def set_combo_count(self, count: int) -> None:
        """Set the combo count explicitly (for combo detection results)."""
        self._category_counts["combo"] = count
        try:
            tab = self.query_one("#synergy-tab-combo", CategoryTab)
            tab.update_count(count)
        except NoMatches:
            pass

    def watch_active_index(self, index: int) -> None:
        """Update tab active states when index changes."""
        for i, category in enumerate(CATEGORY_ORDER):
            try:
                tab = self.query_one(f"#synergy-tab-{category}", CategoryTab)
                tab.is_active = i == index
            except NoMatches:
                pass

        # Post message about category change
        category = CATEGORY_ORDER[index] if 0 <= index < len(CATEGORY_ORDER) else "all"
        self.post_message(CategoryChanged(category))

    def action_next_tab(self) -> None:
        """Move to next tab."""
        self.active_index = (self.active_index + 1) % len(CATEGORY_ORDER)

    def action_prev_tab(self) -> None:
        """Move to previous tab."""
        self.active_index = (self.active_index - 1) % len(CATEGORY_ORDER)

    def action_select_tab(self, index: int) -> None:
        """Select tab by index."""
        if 0 <= index < len(CATEGORY_ORDER):
            self.active_index = index

    @property
    def active_category(self) -> str:
        """Get the currently active category."""
        return CATEGORY_ORDER[self.active_index]

    def get_count(self, category: str) -> int:
        """Get count for a category."""
        return self._category_counts.get(category, 0)
