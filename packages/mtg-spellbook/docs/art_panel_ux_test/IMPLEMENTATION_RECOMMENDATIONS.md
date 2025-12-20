# Art Panel - Implementation Recommendations
## Based on User Experience Testing

This document provides concrete implementation suggestions for addressing UX issues identified in testing.

---

## P0: Critical Issues (Fix Before Release)

### 1. Add Loading State Indicator

**Issue:** No visual feedback when loading printings into Art tab.

**Files to modify:**
- `/Users/cycorg/repos/magic-the-gathering-toolkit/packages/mtg-spellbook/src/mtg_spellbook/widgets/art_navigator/enhanced.py`
- `/Users/cycorg/repos/magic-the-gathering-toolkit/packages/mtg-spellbook/src/mtg_spellbook/widgets/art_navigator/grid.py`

**Implementation:**

```python
# In enhanced.py - EnhancedArtNavigator
class EnhancedArtNavigator(Vertical, can_focus=True):
    is_loading: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        # ... existing code ...
        yield Static(
            "Loading printings...",
            id=f"{self._id_prefix}-loading",
            classes="loading-message hidden",
        )

    def watch_is_loading(self, loading: bool) -> None:
        """Show/hide loading indicator."""
        try:
            loading_msg = self.query_one(f"#{self._id_prefix}-loading", Static)
            if loading:
                loading_msg.remove_class("hidden")
            else:
                loading_msg.add_class("hidden")
        except LookupError:
            pass

    async def load_printings(self, card_name: str, printings: list[PrintingInfo]) -> None:
        """Load printings into all views."""
        self.is_loading = True
        try:
            # ... existing loading code ...
        finally:
            self.is_loading = False
```

**CSS addition:**
```css
.loading-message {
    height: auto;
    text-align: center;
    padding: 1;
    color: $warning;
}

.loading-message.hidden {
    display: none;
}
```

---

### 2. Add Navigation Boundary Feedback

**Issue:** No indication when reaching first/last printing.

**Files to modify:**
- `/Users/cycorg/repos/magic-the-gathering-toolkit/packages/mtg-spellbook/src/mtg_spellbook/widgets/art_navigator/focus.py`
- `/Users/cycorg/repos/magic-the-gathering-toolkit/packages/mtg-spellbook/src/mtg_spellbook/widgets/art_navigator/grid.py`

**Implementation:**

```python
# In focus.py - FocusView
async def navigate(self, direction: str) -> None:
    """Navigate through printings with boundary feedback."""
    if not self._printings:
        return

    old_index = self._current_index

    if direction == "next":
        self._current_index = (self._current_index + 1) % len(self._printings)
        if self._current_index == 0:
            # Wrapped around
            self.app.notify("Wrapped to first printing", severity="information", timeout=2)
    elif direction == "prev":
        self._current_index = (self._current_index - 1) % len(self._printings)
        if self._current_index == len(self._printings) - 1:
            # Wrapped around
            self.app.notify("Wrapped to last printing", severity="information", timeout=2)

    if old_index != self._current_index:
        await self._update_display()

# In grid.py - PrintingsGrid
def navigate(self, direction: str) -> None:
    """Navigate grid with boundary awareness."""
    if not self._printings:
        return

    old_index = self._selected_index

    # ... existing navigation logic ...

    # After navigation, check boundaries
    if direction in ("left", "right"):
        cols = self._cols
        if self._selected_index % cols == 0 and direction == "left":
            self.app.notify("First column", severity="information", timeout=1)
        elif (self._selected_index + 1) % cols == 0 and direction == "right":
            self.app.notify("Last column", severity="information", timeout=1)
```

---

## P1: Medium Priority (Fix Soon)

### 3. Make Mode Toggle Buttons Clickable

**Issue:** View mode buttons show visual indicators but aren't clickable.

**Files to modify:**
- `/Users/cycorg/repos/magic-the-gathering-toolkit/packages/mtg-spellbook/src/mtg_spellbook/widgets/art_navigator/view_toggle.py`

**Implementation:**

```python
# In view_toggle.py - ViewModeToggle
from textual.message import Message

class ModeSelected(Message):
    """Posted when a mode is clicked."""

    def __init__(self, mode: ViewMode) -> None:
        super().__init__()
        self.mode = mode

def on_mount(self) -> None:
    """Set up click handlers."""
    for mode in ViewMode:
        button = self.query_one(f"#mode-{mode.value}", Static)
        button.can_focus = False  # Prevent focus, just clickable

def on_static_clicked(self, event: events.Click) -> None:
    """Handle mode button clicks."""
    widget_id = event.widget.id
    if widget_id and widget_id.startswith("mode-"):
        mode_name = widget_id.replace("mode-", "")
        try:
            mode = ViewMode(mode_name)
            self.post_message(ModeSelected(mode))
        except ValueError:
            pass

# In enhanced.py - EnhancedArtNavigator
@on(ViewModeToggle.ModeSelected)
def on_mode_selected(self, event: ViewModeToggle.ModeSelected) -> None:
    """Handle mode selection from toggle."""
    self.current_view = event.mode
```

---

### 4. Show Current Sort Order

**Issue:** Pressing `s` cycles sort but no indication of current order.

**Files to modify:**
- `/Users/cycorg/repos/magic-the-gathering-toolkit/packages/mtg-spellbook/src/mtg_spellbook/widgets/art_navigator/grid.py`
- `/Users/cycorg/repos/magic-the-gathering-toolkit/packages/mtg-spellbook/src/mtg_spellbook/widgets/art_navigator/enhanced.py`

**Implementation:**

```python
# In grid.py - PrintingsGrid
class PrintingsGrid(Vertical):
    current_sort: reactive[str] = reactive("release")  # "release", "name", "price"

    SORT_NAMES = {
        "release": "Release Date",
        "name": "Set Name",
        "price": "Price",
    }

    def cycle_sort(self) -> None:
        """Cycle through sort orders."""
        sorts = ["release", "name", "price"]
        current = sorts.index(self.current_sort)
        self.current_sort = sorts[(current + 1) % len(sorts)]

        # Show notification
        sort_name = self.SORT_NAMES[self.current_sort]
        self.app.notify(f"Sort: {sort_name}", severity="information", timeout=2)

        self._sort_and_display()

# In enhanced.py - update statusbar
def compose(self) -> ComposeResult:
    # ... existing code ...
    yield Static(
        "[dim]hjkl/arrows: navigate | s: sort | g: gallery | f: focus | c: compare | Space: add | esc: back[/]",
        id=f"{self._id_prefix}-statusbar",
        classes="art-statusbar",
    )

def watch_current_view(self, new_view: ViewMode) -> None:
    """Update statusbar when view changes."""
    # ... existing code ...
    self._update_statusbar()

def _update_statusbar(self) -> None:
    """Update statusbar with current sort info."""
    try:
        statusbar = self.query_one(f"#{self._id_prefix}-statusbar", Static)

        base_help = "hjkl/arrows: navigate"

        if self.current_view == ViewMode.GALLERY:
            grid = self.query_one(f"#{self._id_prefix}-grid", PrintingsGrid)
            sort_name = PrintingsGrid.SORT_NAMES.get(grid.current_sort, "?")
            help_text = f"{base_help} | s: sort ([cyan]{sort_name}[/]) | g/f/c: views | Space: add | esc: back"
        else:
            help_text = f"{base_help} | g/f/c: views | Space: add | esc: back"

        statusbar.update(f"[dim]{help_text}[/]")
    except LookupError:
        pass
```

---

### 5. Highlight Selected Comparison Slot

**Issue:** Number keys 1-4 select slots but no visual indication.

**Files to modify:**
- `/Users/cycorg/repos/magic-the-gathering-toolkit/packages/mtg-spellbook/src/mtg_spellbook/widgets/art_navigator/compare.py`

**Implementation:**

```python
# In compare.py - CompareView
class CompareView(Vertical):
    selected_slot: reactive[int] = reactive(1)

    def watch_selected_slot(self, new_slot: int) -> None:
        """Update slot highlighting."""
        for slot_num in range(1, 5):
            try:
                slot = self.query_one(f"#compare-slot-{slot_num}")
                if slot_num == new_slot:
                    slot.add_class("slot-selected")
                else:
                    slot.remove_class("slot-selected")
            except LookupError:
                pass

# In enhanced.py - update slot selection actions
def action_select_slot_1(self) -> None:
    """Select comparison slot 1."""
    self._compare_selected_slot = 1
    try:
        compare = self.query_one(f"#{self._id_prefix}-compare", CompareView)
        compare.selected_slot = 1
    except LookupError:
        pass
```

**CSS addition:**
```css
.compare-view .slot-selected {
    border: thick $accent;
    background: $boost;
}
```

---

## P2: Low Priority (Nice to Have)

### 6. Add Printing Counter

**Implementation:**
```python
# In focus.py - FocusView
def compose(self) -> ComposeResult:
    # ... existing code ...
    yield Static(
        "",
        id=f"{self.id}-counter",
        classes="printing-counter",
    )

async def _update_display(self) -> None:
    # ... existing code ...
    counter = self.query_one(f"#{self.id}-counter", Static)
    counter.update(f"[dim]{self._current_index + 1} / {len(self._printings)}[/]")
```

---

### 7. Add to Compare Confirmation

**Implementation:**
```python
# In enhanced.py - action_add_to_compare
def action_add_to_compare(self) -> None:
    """Add current selection to compare list."""
    try:
        compare = self.query_one(f"#{self._id_prefix}-compare", CompareView)
        # ... existing code ...

        # After adding
        slot_count = len(compare.get_printings())  # Assuming this method exists
        self.app.notify(f"Added to Compare ({slot_count}/4)", severity="information", timeout=2)
    except LookupError:
        pass
```

---

## Testing Checklist

After implementing these fixes, verify:

- [ ] Loading indicator appears when switching to Art tab
- [ ] Loading indicator disappears when printings loaded
- [ ] Navigation wrap-around shows notification
- [ ] Mode toggle buttons respond to mouse clicks
- [ ] Current sort order shown in statusbar
- [ ] Sort notification appears when pressing `s`
- [ ] Selected comparison slot highlighted with border
- [ ] Printing counter shows "N/M" format
- [ ] "Added to Compare" notification appears
- [ ] All notifications auto-dismiss after timeout

---

## File Paths Summary

Files requiring modification:

1. `/Users/cycorg/repos/magic-the-gathering-toolkit/packages/mtg-spellbook/src/mtg_spellbook/widgets/art_navigator/enhanced.py`
2. `/Users/cycorg/repos/magic-the-gathering-toolkit/packages/mtg-spellbook/src/mtg_spellbook/widgets/art_navigator/focus.py`
3. `/Users/cycorg/repos/magic-the-gathering-toolkit/packages/mtg-spellbook/src/mtg_spellbook/widgets/art_navigator/grid.py`
4. `/Users/cycorg/repos/magic-the-gathering-toolkit/packages/mtg-spellbook/src/mtg_spellbook/widgets/art_navigator/compare.py`
5. `/Users/cycorg/repos/magic-the-gathering-toolkit/packages/mtg-spellbook/src/mtg_spellbook/widgets/art_navigator/view_toggle.py`
6. `/Users/cycorg/repos/magic-the-gathering-toolkit/packages/mtg-spellbook/src/mtg_spellbook/styles/APP_CSS` (CSS additions)

---

**Next Steps:**
1. Review recommendations with development team
2. Prioritize P0 issues for immediate implementation
3. Create tickets for P1 and P2 enhancements
4. Re-test with updated test script after fixes
