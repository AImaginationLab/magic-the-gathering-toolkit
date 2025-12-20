# Synergy Panel UX Improvements

## Executive Summary

The current synergy panel has layout and usability issues. This proposal recommends adopting the successful UX pattern from the Artist Browser widget, which provides excellent usability through a clean filterable-list-with-preview architecture.

## Current Issues Identified

### 1. **Cluttered Layout**
- **Problem**: Synergy panel tries to display too much information at once
  - Header (3 lines)
  - Category tabs (3 lines)
  - Filter bar (2 lines)
  - List container with header (2 lines)
  - Pagination (2 lines)
  - Status bar (2 lines)
  - **Total: ~14 lines of chrome** before content even starts
- **Impact**: Users see minimal actual content in the viewport

### 2. **Overly Complex Navigation**
- **Current bindings**: 20+ key bindings across multiple widgets
  - Tab navigation (tab, shift+tab, 1-6)
  - List navigation (up/down, page up/down, home/end)
  - Sort/filter (s, f, r)
  - Actions (enter, e, c, C)
- **Problem**: Cognitive overload - too many ways to do things
- **Comparison**: Artist Browser has ~8 core bindings and feels intuitive

### 3. **Inconsistent Information Hierarchy**
```
Current Structure:
├── Panel Header (source card info)
├── Category Tabs (horizontal tabs widget)
├── Filter Bar (sort + active filters)
├── Content Area
│   ├── List Container (60% width)
│   │   ├── List Header (category name + count)
│   │   ├── Scrollable List
│   │   └── Pagination Footer
│   └── Detail View (40% width, hidden by default)
└── Status Bar
```

**Issues**:
- Multiple competing headers (panel header, list header)
- Pagination info separated from list
- Detail view competes for space instead of replacing list view
- Filter bar shows info that could be in header

### 4. **List Items Are Too Dense**
Each synergy item shows:
- Visual score bar (10 chars)
- Type icon ([K], [T], etc.)
- Card name
- Mana cost
- Score badge (percentage)
- Reason text (full line below)

**Problem**: Too much information per item makes scanning difficult
**Artist Browser approach**: Clean, scannable items with just essential info

### 5. **Unused/Incomplete Features**
- **Comparison view**: Overlay that blocks entire UI
- **Detail view**: Side panel that shrinks list
- **Filter system**: Currently just cycles through card types
- **Result**: Features that seem half-implemented

## Artist Browser Success Patterns

The Artist Browser demonstrates excellent UX through:

### 1. **Clean, Focused Layout**
```
Artist Browser Structure:
├── Header (4 lines) - Title + Search Input
├── Content Area (horizontal split)
│   ├── Letter Index (8 chars wide, minimal)
│   └── Main List (scrollable)
└── Status Bar (2 lines)

Total chrome: 6 lines (vs synergy's 14 lines)
```

### 2. **Smart Progressive Loading**
- Batches items (100 at a time) to prevent UI blocking
- Uses debounced search (150ms) for responsive filtering
- Letter-based indexing for quick navigation

### 3. **Intuitive Key Bindings**
Core actions:
- `jk` / arrows: navigate
- `A-Z`: jump to letter
- `Enter`: select
- `r`: random
- `/`: search
- `Esc`: close

**Pattern**: Single-purpose keys, no modifier confusion

### 4. **Clean List Items**
```
[bold]Artist Name[/]
[cyan]123[/] cards  [dim]45 sets[/]  [dim](1995-2024)[/]
```

**Features**:
- Scannable name (bold, on its own line conceptually)
- Key stats in visual hierarchy (color-coded)
- Minimal vertical space per item

### 5. **Effective Search Integration**
- Prominent search input in header
- Real-time filtering with debouncing
- Shows "X of Y" when filtering
- Letter index updates dynamically

## Proposed Synergy Panel Redesign

### Design Philosophy
**Adopt the "Gallery Browser" pattern** - filterable list with detail panel, not competing simultaneous views.

### Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│ Synergies for [Card Name] {mana}    [Search: ________ ] │ 3 lines
│ [showing 45 of 120]                                     │
├─────────────────────────────────────────────────────────┤
│ ┌───┬────────────────────────────────────────────────┐ │
│ │ A │ [90%] Sol Ring {1}                             │ │
│ │ C │       Combo - Goes infinite with your commander│ │
│ │   │                                                 │ │
│ │ K │ [85%] Lightning Greaves {2}                    │ │
│ │   │       Keyword - Protects your combo pieces     │ │
│ │   │                                                 │ │
│ │ T │ [80%] Goblin Chieftain {1}{R}{R}               │ │
│ │   │       Tribal - Anthem effect for your goblins  │ │
│ │   │                                                 │ │
│ │ ... (scrollable)                                    │ │
│ └───┴────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│ A-Z: filter type  s: sort  Enter: detail  /: search   │ 2 lines
└─────────────────────────────────────────────────────────┘
```

### Key Changes

#### 1. **Simplified Header** (3 lines instead of 8)
```
Synergies for [Card Name] {mana}    [Search: _________ ]
[showing 45 of 120 | Sort: Score | Type: All]
```

**Consolidates**:
- Source card info
- Search input (like artist browser)
- Current filter/sort state
- Result count

#### 2. **Type Index Sidebar** (like letter index)
```
┌───┐
│ A │  All
│ C │  Combo
│ K │  Keyword
│ T │  Tribal
│ A │  Ability
│ H │  Theme
└───┘
```

**Benefits**:
- Single-key navigation (A/C/K/T/A/H)
- Visual indicator of current filter
- Minimal space (3-4 chars wide)
- Consistent with Artist Browser pattern

#### 3. **Cleaner List Items**
```
[90%] Sol Ring {1}
      Combo - Goes infinite with your commander
```

**Changes**:
- Remove redundant score bar (keep percentage)
- Remove type icon (now in sidebar)
- Reason on second line with type prefix
- More breathing room between items

#### 4. **Detail View as Modal Overlay**
When user presses `Enter`, show full-screen detail:
```
┌──────────────────────────────────────────────────────┐
│ Sol Ring {1}                            [90% match]  │
│ Artifact                                             │
├──────────────────────────────────────────────────────┤
│                                                      │
│ Why it synergizes:                                   │
│   [detailed explanation...]                          │
│                                                      │
│ How it works:                                        │
│   - Point 1                                          │
│   - Point 2                                          │
│                                                      │
│ [Press Esc to close]                                 │
└──────────────────────────────────────────────────────┘
```

**Benefits**:
- Full screen for detailed info
- Doesn't compete for space with list
- Clearer entry/exit (like artist portfolio view)

#### 5. **Remove/Defer Complex Features**
- **Remove**: Comparison view (overlay complexity)
- **Remove**: Tab-based navigation (use sidebar filter instead)
- **Remove**: Expand-in-place detail (use modal instead)
- **Simplify**: Filtering to just type + search
- **Defer**: Advanced filters (CMC, color) to future iteration

### Simplified Key Bindings

**Navigation** (6 bindings):
- `jk` / `↑↓`: Navigate list
- `Enter`: View detail
- `/`: Focus search
- `A/C/K/T/H`: Filter by type (All/Combo/Keyword/Tribal/Ability/tHeme)
- `Esc/q`: Close panel

**Actions** (3 bindings):
- `s`: Cycle sort (Score/Name/CMC)
- `r`: Random synergy
- `c`: Copy to clipboard (if needed)

**Total: 9 core bindings** (vs current 20+)

## Component Reuse Opportunities

### From Artist Browser

#### 1. **Batched List Loading Pattern**
```python
# Reuse from artist_browser/widget.py:201-254
async def _populate_list_batched(self, synergies: list[SynergyResult]) -> None:
    """Populate with batches to avoid UI blocking."""
    # Same pattern - batch of 100, yield with asyncio.sleep(0)
```

#### 2. **Debounced Search**
```python
# Reuse from artist_browser/widget.py:277-310
SEARCH_DEBOUNCE_MS = 150

async def _debounced_search(self, query: str) -> None:
    await asyncio.sleep(SEARCH_DEBOUNCE_MS / 1000)
    # Apply search filter
```

#### 3. **Header Layout**
```python
# Similar pattern from artist_browser/widget.py:96-107
with Horizontal(classes="synergy-header"):
    yield Static(title, id="synergy-title")
    yield Input(placeholder="Search synergies...", id="synergy-search")
```

#### 4. **Index Sidebar**
```python
# Adapt from artist_browser's letter index
# artist_browser/widget.py:110-113
with VerticalScroll(classes="type-index-container"):
    yield Static("", id="type-index", classes="type-index")
```

### New Components Needed

#### 1. **SynergyListItem** (simplified)
```python
class SynergyListItem(ListItem):
    """Simplified synergy item - just score, name, type tag."""

    def compose(self) -> ComposeResult:
        # Line 1: [90%] Card Name {mana}
        # Line 2:       Type - Reason
        yield Static(self._render_item())
```

#### 2. **SynergyDetailModal** (full-screen overlay)
```python
class SynergyDetailModal(Vertical):
    """Full-screen synergy detail view."""
    # Replace SynergyDetailView side panel
    # Use layer: overlay in CSS
```

#### 3. **TypeIndex** (minimal sidebar)
```python
class TypeIndex(Vertical):
    """Type filter index sidebar (A/C/K/T/A/H)."""
    # Similar to letter index in artist browser
    # Highlight current type
```

## Implementation Phases

### Phase 1: Simplify Layout (2-3 hours)
- Remove category tabs widget
- Add search input to header
- Remove filter bar (consolidate to header)
- Remove pagination widget (show in header)
- Simplify status bar

**Result**: Clean layout with 6 lines of chrome instead of 14

### Phase 2: Add Type Index Sidebar (1-2 hours)
- Create TypeIndex widget
- Add single-key navigation (A/C/K/T/A/H)
- Update CSS for sidebar layout

**Result**: Quick filtering without tab complexity

### Phase 3: Simplify List Items (1 hour)
- Remove score bar (keep percentage)
- Remove type icon (now in sidebar)
- Improve spacing and readability

**Result**: Scannable list like artist browser

### Phase 4: Refactor Detail View (2 hours)
- Convert side panel to full-screen modal
- Use overlay layer
- Add proper entry/exit animations

**Result**: Detail view that doesn't compete for space

### Phase 5: Integrate Search + Batching (2 hours)
- Reuse batched loading from artist browser
- Add debounced search
- Update header with live counts

**Result**: Responsive filtering without UI blocking

**Total estimated effort**: 8-10 hours

## Success Metrics

### Usability Improvements
- **Chrome reduction**: 14 lines → 6 lines (57% less overhead)
- **Key binding reduction**: 20+ → 9 (55% simpler)
- **Time to scan results**: Estimated 30-40% faster due to cleaner items
- **Time to filter**: Instant with sidebar (vs multi-step tab navigation)

### Code Quality
- **Reuse existing patterns**: 60-70% of logic from artist browser
- **Remove complexity**: Delete ~200 lines of tab/pagination/comparison code
- **Maintainability**: Single consistent pattern across browsers

### User Experience
- **Cognitive load**: Significantly reduced (fewer competing UI elements)
- **Discoverability**: Type index makes filtering obvious
- **Search**: Prominent, responsive (like artist browser)
- **Detail view**: Clear modal pattern (vs confusing side panel)

## Recommendation

**Adopt the Artist Browser pattern for the Synergy Panel.** The gallery-style filterable list with sidebar index is proven, intuitive, and significantly simpler than the current multi-tab, multi-panel approach.

**Priority**: High - Current synergy panel has usability issues that affect core feature value.

**Risk**: Low - Pattern is already proven in the codebase, reuses existing components.

**Timeline**: 1-2 days of focused development for full implementation.
