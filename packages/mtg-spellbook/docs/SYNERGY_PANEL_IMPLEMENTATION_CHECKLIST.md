# Synergy Panel Redesign - Implementation Checklist

## Pre-Implementation

- [ ] Review design documents with team
- [ ] Create feature branch: `feature/synergy-panel-redesign`
- [ ] Back up current implementation
- [ ] Set up snapshot tests for baseline

## Phase 1: Simplify Layout (2-3 hours)

### Remove Complex Widgets

**File**: `/packages/mtg-spellbook/src/mtg_spellbook/widgets/synergy/panel.py`

- [ ] Remove `CategoryTabs` import and usage
- [ ] Remove `synergy-tabs` from compose()
- [ ] Delete `action_next_category()`, `action_prev_category()`, `action_select_category()`
- [ ] Remove `on_category_changed()` handler
- [ ] Remove `active_category` reactive

**File**: `/packages/mtg-spellbook/src/mtg_spellbook/widgets/synergy/tabs.py`

- [ ] Delete entire file (will recreate as type_index.py)

### Consolidate Header

**File**: `/packages/mtg-spellbook/src/mtg_spellbook/widgets/synergy/panel.py`

- [ ] Update `compose()` to use Horizontal header layout
- [ ] Add search Input widget to header (id="synergy-search")
- [ ] Consolidate info into single info bar (results count, sort, filter)
- [ ] Remove separate filter bar widget
- [ ] Update `_render_header()` to be simpler

```python
def compose(self) -> ComposeResult:
    # Header with search
    with Horizontal(id="synergy-header", classes="synergy-header"):
        yield Static(
            self._render_title(),
            id="synergy-title",
            classes="synergy-title",
        )
        yield Input(
            placeholder="Search synergies...",
            id="synergy-search",
            classes="synergy-search",
        )

    # Info bar
    yield Static(
        self._render_info_bar(),
        id="synergy-info-bar",
        classes="synergy-info-bar",
    )

    # Main content area
    with Horizontal(id="synergy-content", classes="synergy-content"):
        # Type index (Phase 2)
        # List view
        # ...
```

### Update CSS

**File**: `/packages/mtg-spellbook/src/mtg_spellbook/styles.py`

- [ ] Remove `.synergy-tabs` styles
- [ ] Remove `.synergy-filter-bar` styles (consolidating to info bar)
- [ ] Add `.synergy-header` horizontal layout
- [ ] Add `.synergy-title` and `.synergy-search` styles
- [ ] Add `.synergy-info-bar` styles

```css
/* Synergy header with search */
.synergy-header {
    height: 3;
    background: #1a1a2e;
    border-bottom: solid #c9a227;
    padding: 0 2;
    layout: horizontal;
    align: left middle;
}

.synergy-title {
    width: auto;
    content-align: left middle;
}

.synergy-search {
    width: 30;
    margin-left: auto;
    background: #151515;
    border: tall #3d3d3d;
}

.synergy-search:focus {
    border: tall #c9a227;
    background: #1e1e32;
}

.synergy-info-bar {
    height: 1;
    background: #151515;
    padding: 0 2;
    color: #888;
}
```

### Update Pagination

**File**: `/packages/mtg-spellbook/src/mtg_spellbook/widgets/synergy/panel.py`

- [ ] Remove separate pagination widget from compose()
- [ ] Move pagination info to info bar
- [ ] Update `_render_info_bar()` to include count/pagination

```python
def _render_info_bar(self) -> str:
    """Render consolidated info bar."""
    parts = []

    # Results count
    total = len(self._all_synergies)
    filtered = len(self._filtered_synergies)
    if filtered < total:
        parts.append(f"[showing {filtered} of {total}]")
    else:
        parts.append(f"[showing {total}]")

    # Sort order
    sort_labels = {
        SortOrder.SCORE_DESC: "Score",
        SortOrder.CMC_ASC: "CMC",
        SortOrder.NAME_ASC: "Name",
    }
    parts.append(f"Sort: {sort_labels[self.current_sort]}")

    # Active filter (Phase 2)
    parts.append("Type: All")

    return " | ".join(parts)
```

### Test Phase 1

- [ ] Run app and verify synergy panel opens
- [ ] Check that header displays correctly
- [ ] Verify search input is visible and functional
- [ ] Confirm info bar shows correct counts
- [ ] Test with ruff: `uv run ruff check packages/mtg-spellbook`
- [ ] Test with mypy: `uv run mypy packages/mtg-spellbook`

## Phase 2: Type Index Sidebar (1-2 hours)

### Create TypeIndex Widget

**File**: `/packages/mtg-spellbook/src/mtg_spellbook/widgets/synergy/type_index.py` (new)

```python
"""Type filter index sidebar for synergy panel."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.events import Key
from textual.reactive import reactive
from textual.widgets import Static

from ...ui.theme import ui_colors

if TYPE_CHECKING:
    from mtg_core.data.models.responses import SynergyResult

# Type definitions
TYPE_INFO: dict[str, tuple[str, str]] = {
    "all": ("A", "All synergies"),
    "combo": ("C", "Combo synergies"),
    "keyword": ("K", "Keyword synergies"),
    "tribal": ("T", "Tribal synergies"),
    "ability": ("A", "Ability synergies"),
    "theme": ("H", "Theme synergies"),
}

TYPE_ORDER = ["all", "combo", "keyword", "tribal", "ability", "theme"]


class TypeIndex(Vertical, can_focus=True):
    """Sidebar showing synergy type filters."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("a", "filter_all", "All", show=False),
        Binding("c", "filter_combo", "Combo", show=False),
        Binding("k", "filter_keyword", "Keyword", show=False),
        Binding("t", "filter_tribal", "Tribal", show=False),
        Binding("shift+a", "filter_ability", "Ability", show=False),
        Binding("h", "filter_theme", "Theme", show=False),
    ]

    active_type: reactive[str] = reactive("all")

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._counts: dict[str, int] = dict.fromkeys(TYPE_ORDER, 0)

    def compose(self) -> ComposeResult:
        yield Static(
            self._render_index(),
            id="type-index-content",
            classes="type-index-content",
        )

    def _render_index(self) -> str:
        """Render the type index."""
        lines = []
        for type_key in TYPE_ORDER:
            letter, _ = TYPE_INFO[type_key]
            count = self._counts.get(type_key, 0)

            if type_key == self.active_type:
                # Active type - bold and highlighted
                lines.append(f"[bold {ui_colors.GOLD}]{letter}[/] [dim]({count})[/]")
            else:
                # Inactive type - dim
                lines.append(f"[dim]{letter} ({count})[/]")

        return "\n".join(lines)

    def update_counts(self, synergies: list[SynergyResult]) -> None:
        """Update type counts from synergies."""
        self._counts = dict.fromkeys(TYPE_ORDER, 0)
        self._counts["all"] = len(synergies)

        for syn in synergies:
            syn_type = syn.synergy_type
            if syn_type in TYPE_ORDER:
                self._counts[syn_type] += 1

        self._update_display()

    def _update_display(self) -> None:
        """Update the display."""
        try:
            content = self.query_one("#type-index-content", Static)
            content.update(self._render_index())
        except Exception:
            pass

    def watch_active_type(self, _type: str) -> None:
        """Handle active type change."""
        self._update_display()
        # Post message for parent to handle filtering
        from .messages import TypeFilterChanged
        self.post_message(TypeFilterChanged(_type))

    # Actions for key bindings
    def action_filter_all(self) -> None:
        self.active_type = "all"

    def action_filter_combo(self) -> None:
        self.active_type = "combo"

    def action_filter_keyword(self) -> None:
        self.active_type = "keyword"

    def action_filter_tribal(self) -> None:
        self.active_type = "tribal"

    def action_filter_ability(self) -> None:
        self.active_type = "ability"

    def action_filter_theme(self) -> None:
        self.active_type = "theme"
```

### Create TypeFilterChanged Message

**File**: `/packages/mtg-spellbook/src/mtg_spellbook/widgets/synergy/messages.py`

- [ ] Add `TypeFilterChanged` message class

```python
@dataclass
class TypeFilterChanged(Message):
    """Posted when type filter changes."""
    type_key: str
```

### Integrate TypeIndex into Panel

**File**: `/packages/mtg-spellbook/src/mtg_spellbook/widgets/synergy/panel.py`

- [ ] Import TypeIndex
- [ ] Add to compose() layout
- [ ] Add `on_type_filter_changed()` handler
- [ ] Update filtering logic to use active type

```python
def compose(self) -> ComposeResult:
    # ... header ...

    # Main content with type index
    with Horizontal(id="synergy-content", classes="synergy-content"):
        yield TypeIndex(
            id="type-index",
            classes="type-index",
        )

        # List container
        with Vertical(id="synergy-list-container", classes="synergy-list-container"):
            # ... list ...
```

### Update CSS for Sidebar

**File**: `/packages/mtg-spellbook/src/mtg_spellbook/styles.py`

- [ ] Add type index container styles
- [ ] Set width to 4-5 chars
- [ ] Add border and padding

```css
.type-index {
    width: 5;
    height: 100%;
    background: #151515;
    border-right: solid #3d3d3d;
    padding: 1;
}

.type-index-content {
    height: auto;
}
```

### Test Phase 2

- [ ] Verify type index appears in sidebar
- [ ] Test single-key filtering (A, C, K, T, A, H)
- [ ] Confirm counts update correctly
- [ ] Check active type highlighting
- [ ] Verify filtered results display correctly

## Phase 3: Simplify List Items (1 hour)

### Update SynergyCardItem

**File**: `/packages/mtg-spellbook/src/mtg_spellbook/widgets/synergy/card_item.py`

- [ ] Remove visual score bar (keep percentage only)
- [ ] Remove type icon (now in sidebar)
- [ ] Simplify to 2-line format
- [ ] Improve spacing

```python
def compose(self) -> ComposeResult:
    with Vertical(classes="synergy-item-container"):
        # Line 1: Score + name + mana
        yield Static(
            self._render_line1(),
            classes="synergy-item-line1",
        )
        # Line 2: Type + reason (indented)
        yield Static(
            self._render_line2(),
            classes="synergy-item-line2",
        )

def _render_line1(self) -> str:
    """Render first line: [score%] Name {mana}."""
    score = int(self.synergy.score * 100)
    color = self._get_score_color(self.synergy.score)

    name = self.synergy.name
    if self.is_in_compare:
        name = f"[bold]{name}[/]"

    mana = ""
    if self.synergy.mana_cost:
        mana = f" {prettify_mana(self.synergy.mana_cost)}"

    return f"[{color}][{score}%][/] {name}{mana}"

def _render_line2(self) -> str:
    """Render second line: Type - Reason (indented)."""
    type_display = self.synergy.synergy_type.title()
    return f"      [{ui_colors.TEXT_DIM}]{type_display} - {self.synergy.reason}[/]"
```

### Update CSS

**File**: `/packages/mtg-spellbook/src/mtg_spellbook/styles.py`

- [ ] Simplify item styles
- [ ] Add proper spacing between items
- [ ] Remove old component styles

```css
.synergy-item-container {
    height: 3;  /* 2 lines + 1 spacing */
    padding: 0;
}

.synergy-item-line1 {
    height: 1;
    padding: 0 1;
}

.synergy-item-line2 {
    height: 1;
    padding: 0 1;
}
```

### Test Phase 3

- [ ] Verify items display cleanly
- [ ] Check spacing between items
- [ ] Confirm score colors work
- [ ] Test mana symbol rendering
- [ ] Verify list is scannable

## Phase 4: Modal Detail View (2 hours)

### Convert SynergyDetailView to Modal

**File**: `/packages/mtg-spellbook/src/mtg_spellbook/widgets/synergy/detail_view.py`

- [ ] Change to full-screen overlay (not side panel)
- [ ] Add modal styling
- [ ] Update bindings
- [ ] Center content

```python
class SynergyDetailModal(Vertical, can_focus=True):
    """Full-screen modal for synergy detail."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape,q", "close", "Close"),
    ]

    is_visible: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        with Vertical(id="detail-modal-container", classes="detail-modal-container"):
            yield Static("", id="detail-header", classes="detail-header")
            with VerticalScroll(classes="detail-scroll"):
                yield Static("", id="detail-content", classes="detail-content")
            yield Static(
                "[dim]Press Esc to close[/]",
                classes="detail-hint",
            )

    def watch_is_visible(self, visible: bool) -> None:
        """Show/hide modal."""
        if visible:
            self.add_class("visible")
            self.focus()
        else:
            self.remove_class("visible")
```

### Update Panel Integration

**File**: `/packages/mtg-spellbook/src/mtg_spellbook/widgets/synergy/panel.py`

- [ ] Change detail view from side panel to overlay
- [ ] Update action_expand_detail() to show modal
- [ ] Remove detail view from horizontal layout

```python
def compose(self) -> ComposeResult:
    # ... header, content ...

    # Detail modal (overlay)
    yield SynergyDetailModal(
        id="synergy-detail-modal",
        classes="synergy-detail-modal",
    )

    # ... status bar ...
```

### Update CSS

**File**: `/packages/mtg-spellbook/src/mtg_spellbook/styles.py`

- [ ] Add modal overlay styles
- [ ] Center modal
- [ ] Add backdrop

```css
.synergy-detail-modal {
    display: none;
}

.synergy-detail-modal.visible {
    display: block;
    layer: overlay;
    width: 80%;
    height: 80%;
    border: heavy #c9a227;
    background: #0d0d0d;
    align: center middle;
}

.detail-modal-container {
    width: 100%;
    height: 100%;
}

.detail-header {
    height: 3;
    background: #1a1a2e;
    border-bottom: solid #c9a227;
    padding: 0 2;
}

.detail-scroll {
    height: 1fr;
    padding: 1 2;
}

.detail-hint {
    height: 2;
    background: #1a1a1a;
    border-top: solid #3d3d3d;
    text-align: center;
    padding: 0;
}
```

### Test Phase 4

- [ ] Verify modal opens on Enter
- [ ] Check modal is centered
- [ ] Test Esc to close
- [ ] Confirm backdrop/overlay works
- [ ] Verify content scrolls properly

## Phase 5: Search Integration (2 hours)

### Add Search Handler

**File**: `/packages/mtg-spellbook/src/mtg_spellbook/widgets/synergy/panel.py`

- [ ] Add search input handler
- [ ] Implement debounced search (150ms)
- [ ] Update filtering to include search query
- [ ] Add search cancellation

```python
from asyncio import Task, create_task, sleep

SEARCH_DEBOUNCE_MS = 150

def __init__(self, ...):
    super().__init__(...)
    self._search_task: Task[None] | None = None
    self._search_query: str = ""

def on_input_changed(self, event: Input.Changed) -> None:
    """Handle search input with debouncing."""
    if event.input.id == "synergy-search":
        # Cancel pending search
        if self._search_task:
            self._search_task.cancel()

        # Schedule debounced search
        self._search_task = create_task(
            self._debounced_search(event.value)
        )

async def _debounced_search(self, query: str) -> None:
    """Execute search after debounce delay."""
    try:
        await sleep(SEARCH_DEBOUNCE_MS / 1000)
    except asyncio.CancelledError:
        return

    self._search_query = query.lower()
    self._apply_filters()
    await self._rebuild_list()
```

### Update Filtering Logic

**File**: `/packages/mtg-spellbook/src/mtg_spellbook/widgets/synergy/panel.py`

- [ ] Add search filter to `_apply_filters()`
- [ ] Filter by card name and reason text
- [ ] Update counts in real-time

```python
def _apply_filters(self) -> None:
    """Apply type filter and search query."""
    # Start with all synergies
    self._filtered_synergies = list(self._all_synergies)

    # Apply type filter
    if self._active_type != "all":
        self._filtered_synergies = [
            s for s in self._filtered_synergies
            if s.synergy_type == self._active_type
        ]

    # Apply search filter
    if self._search_query:
        query = self._search_query.lower()
        self._filtered_synergies = [
            s for s in self._filtered_synergies
            if query in s.name.lower() or query in s.reason.lower()
        ]

    # Apply sorting
    self._sort_synergies()
```

### Add Batched Loading

**File**: `/packages/mtg-spellbook/src/mtg_spellbook/widgets/synergy/panel.py`

- [ ] Implement batched list population
- [ ] Add yield points for UI responsiveness
- [ ] Show loading indicator if needed

```python
LIST_BATCH_SIZE = 100

async def _rebuild_list(self) -> None:
    """Rebuild list with batched loading."""
    if not self.is_mounted:
        return

    try:
        list_view = self.query_one("#synergy-list", ListView)
        await list_view.clear()

        if not self._filtered_synergies:
            # Empty state
            empty = ListItem(Static("[dim]No matching synergies[/]"))
            await list_view.append(empty)
            return

        # Add items in batches
        batch_count = 0
        for i, syn in enumerate(self._filtered_synergies):
            item = SynergyCardItem(syn, id=f"synergy-item-{i}")
            await list_view.append(item)
            batch_count += 1

            # Yield periodically
            if batch_count >= LIST_BATCH_SIZE:
                batch_count = 0
                await asyncio.sleep(0)

        # Update counts
        self._update_info_bar()

    except Exception:
        pass
```

### Test Phase 5

- [ ] Test search input responsiveness
- [ ] Verify debouncing works (150ms delay)
- [ ] Check search filters results correctly
- [ ] Test combined type + search filtering
- [ ] Verify counts update in real-time
- [ ] Test with 100+ results (batching)

## Final Testing & Cleanup

### Integration Testing

- [ ] Full workflow: open panel → filter → search → view detail → close
- [ ] Test all key bindings work correctly
- [ ] Verify no memory leaks (open/close multiple times)
- [ ] Test with various synergy counts (0, 10, 100, 500+)
- [ ] Check responsive layout at different terminal sizes

### Code Quality

- [ ] Run ruff check: `uv run ruff check packages/mtg-spellbook`
- [ ] Run ruff format: `uv run ruff format packages/mtg-spellbook`
- [ ] Run mypy: `uv run mypy packages/mtg-spellbook`
- [ ] Add docstrings to new components
- [ ] Remove unused imports

### Snapshot Tests

**File**: `/packages/mtg-spellbook/tests/test_synergy_panel.py`

- [ ] Update snapshot tests for new layout
- [ ] Add tests for type filtering
- [ ] Add tests for search functionality
- [ ] Add tests for modal detail view
- [ ] Run: `uv run pytest packages/mtg-spellbook/tests/test_synergy_panel.py`

### Documentation

- [ ] Update keyboard shortcuts in user docs
- [ ] Add comments to complex filtering logic
- [ ] Document new TypeIndex component
- [ ] Update CHANGELOG with redesign notes

### Cleanup

- [ ] Remove old tab widget files
- [ ] Remove unused CSS classes
- [ ] Remove old comparison view code (if deferring)
- [ ] Clean up unused imports and variables

## Post-Implementation

### Review

- [ ] Code review with team
- [ ] UX review - does it match wireframes?
- [ ] Performance check - smooth with 500+ synergies?
- [ ] Accessibility check - keyboard nav works?

### Deployment

- [ ] Merge feature branch to main
- [ ] Tag release with redesign notes
- [ ] Update user documentation
- [ ] Announce improvement in release notes

### Follow-up

- [ ] Gather user feedback
- [ ] Monitor for issues/bugs
- [ ] Consider follow-up improvements:
  - [ ] Restore comparison view (improved)
  - [ ] Add advanced filters
  - [ ] Add export/share features

---

## Quick Reference: Key Changes

| Component | Before | After |
|-----------|--------|-------|
| **Chrome** | 14 lines (46%) | 5 lines (18%) |
| **Key bindings** | 20+ | 9 |
| **Type filter** | 6 tabs | 6-letter sidebar |
| **Search** | Hidden/absent | Prominent in header |
| **Detail view** | Side panel (40%) | Full-screen modal |
| **List items** | 5 components | 2 lines |
| **Pagination** | Separate widget | In header |

## Estimated Time

- **Phase 1**: 2-3 hours
- **Phase 2**: 1-2 hours
- **Phase 3**: 1 hour
- **Phase 4**: 2 hours
- **Phase 5**: 2 hours
- **Testing/Cleanup**: 2-3 hours

**Total**: 10-13 hours (~1.5-2 days)
