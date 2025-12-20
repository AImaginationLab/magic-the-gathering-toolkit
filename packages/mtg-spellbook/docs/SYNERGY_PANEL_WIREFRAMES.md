# Synergy Panel UX Wireframes

## Before & After Comparison

### Current Design (Cluttered)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Synergies for Lightning Bolt {R}  (120 found)                      │ 3 lines
├─────────────────────────────────────────────────────────────────────┤
│ [All (120)]  [Combos (5)]  [Tribal (20)]  [Keywords (30)]...       │ 3 lines
├─────────────────────────────────────────────────────────────────────┤
│ Sort: Score  |  Filters: Type: Creature  |  Compare: 2             │ 2 lines
├─────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────┬───────────────────────────────┐│
│ │ All (45 results)                │                               ││ 2 lines
│ ├─────────────────────────────────┤                               ││
│ │ [[[[[[[[..] [K] Lightning Gre...│     (Detail View Hidden)      ││
│ │   Keyword - Protects combo pie..│                               ││
│ │                                 │                               ││
│ │ [[[[[[[[..] [T] Goblin Chieft...│                               ││
│ │   Tribal - Anthem effect for...│                               ││
│ │                                 │                               ││
│ │ [[[[[[..] [A] Purphoros, God...│                               ││
│ │   Ability - Triggers on ETB...  │                               ││
│ │                                 │                               ││
│ ├─────────────────────────────────┤                               ││
│ │ Showing 1-25 of 45  Page 1/2    │                               ││ 2 lines
│ └─────────────────────────────────┴───────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────┤
│ Tab: categories | jk: navigate | Enter: view | e: expand | ...     │ 2 lines
└─────────────────────────────────────────────────────────────────────┘

Total chrome: 14 lines before content
```

### Proposed Design (Clean)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Synergies for Lightning Bolt {R}         [Search: ______________ ] │
│ [showing 45 of 120 | Sort: Score | Type: All]                      │ 3 lines
├───┬─────────────────────────────────────────────────────────────────┤
│ A │ [90%] Sol Ring {1}                                              │
│ ↓ │       Combo - Goes infinite with your commander                │
│   │                                                                 │
│ C │ [85%] Lightning Greaves {2}                                     │
│   │       Keyword - Protects your combo pieces                      │
│ K │                                                                 │
│ ↑ │ [80%] Goblin Chieftain {1}{R}{R}                               │
│ T │       Tribal - Anthem effect for your goblins                   │
│   │                                                                 │
│ A │ [75%] Purphoros, God of the Forge {3}{R}                        │
│   │       Ability - Triggers on creature ETB                        │
│ H │                                                                 │
│   │ ... (more results, scrollable)                                  │
│   │                                                                 │
├───┴─────────────────────────────────────────────────────────────────┤
│ A-Z: filter type | s: sort | Enter: detail | /: search | Esc: close│ 2 lines
└─────────────────────────────────────────────────────────────────────┘

Total chrome: 5 lines (65% reduction)
```

## Component Breakdown

### 1. Header with Search (3 lines)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Line 1: Synergies for Lightning Bolt {R}    [Search: __________ ]  │
│ Line 2: [showing 45 of 120 | Sort: Score | Type: All]              │
│ Line 3: (border)                                                    │
└─────────────────────────────────────────────────────────────────────┘

Components:
- Static: Title with source card + mana cost
- Input: Search box (right-aligned, 30 chars wide)
- Static: Info line with current state
```

### 2. Type Index Sidebar (3-4 chars wide)

```
┌───┐
│ A │ ← All (active)
│ C │   Combo
│ K │   Keyword
│ T │   Tribal
│ A │   Ability
│ H │   Theme
└───┘

Styling:
- Active type: bold + highlight color
- Inactive: dim gray
- Single-letter keys for navigation
- Updates counts dynamically: "C (5)"
```

### 3. Synergy List Items (2 lines each)

```
[90%] Sol Ring {1}
      Combo - Goes infinite with your commander

[85%] Lightning Greaves {2}
      Keyword - Protects your combo pieces

Format:
Line 1: [score%] Card Name mana_cost
Line 2:       Type - Reason (indented)

Spacing:
- 1 blank line between items
- Clean visual separation
```

### 4. Status Bar (2 lines)

```
┌─────────────────────────────────────────────────────────────────────┐
│ (border)                                                            │
│ A-Z: filter type | s: sort | Enter: detail | /: search | Esc: close│
└─────────────────────────────────────────────────────────────────────┘

Shows:
- Core navigation hints
- Active filter shortcuts
- No clutter (only essential 5-6 actions)
```

## Interaction Flows

### Flow 1: Browse Synergies

```
Step 1: Panel Opens                Step 2: Filter by Type
┌────────────────────────────┐    ┌────────────────────────────┐
│ Synergies for Card X       │    │ Synergies for Card X       │
│ [showing 120]              │    │ [showing 5 | Type: Combo]  │
├───┬────────────────────────┤    ├───┬────────────────────────┤
│ A │ [90%] Sol Ring         │    │ A │                        │
│ ↓ │ [85%] Greaves          │    │ C │ [90%] Sol Ring         │
│ C │ [80%] Chieftain        │    │ ↓ │ [87%] Thassa's Oracle  │
│   │ [75%] Purphoros        │    │ K │ [85%] Demonic Consult  │
│   │ ...                    │    │   │ [80%] Worldgorger      │
└───┴────────────────────────┘    │   │ [75%] Animate Dead    │
                                  └───┴────────────────────────┘
User presses 'C'                   Only combo synergies shown
```

### Flow 2: Search Within Results

```
Step 1: Type '/' to Search         Step 2: Type "artifact"
┌────────────────────────────┐    ┌────────────────────────────┐
│ Synergies for Card X       │    │ Synergies for Card X       │
│ [Search: ______________ ]  │    │ [Search: artifact______ ]  │
│ [showing 120]              │    │ [showing 15 of 120]        │
├───┬────────────────────────┤    ├───┬────────────────────────┤
│   │ (search focused)       │    │ A │ [90%] Sol Ring         │
│   │                        │    │ ↓ │ [87%] Mana Vault       │
│   │                        │    │   │ [85%] Mana Crypt       │
│   │                        │    │   │ [80%] Chrome Mox       │
│   │                        │    │   │ ...                    │
└───┴────────────────────────┘    └───┴────────────────────────┘
Input focused, ready to type       Results filter in real-time
```

### Flow 3: View Detail

```
Step 1: Select Item               Step 2: Press Enter
┌────────────────────────────┐   ┌────────────────────────────────────────┐
│ Synergies for Card X       │   │ Sol Ring {1}              [90% match]  │
│ [showing 120]              │   │ Artifact                               │
├───┬────────────────────────┤   ├────────────────────────────────────────┤
│ A │→[90%] Sol Ring ←       │   │                                        │
│ ↓ │      Combo - Goes inf..│   │ Why it synergizes:                     │
│ C │                        │   │   Provides explosive mana acceleration │
│   │ [85%] Greaves          │   │   that enables your combo pieces to    │
│   │ [80%] Chieftain        │   │   come down turns earlier.             │
└───┴────────────────────────┘   │                                        │
                                  │ How it works:                          │
Item highlighted                   │   - Ramps you by 2 colorless mana    │
                                  │   - Costs only 1 to cast              │
                                  │   - Synergizes with artifact themes   │
                                  │                                        │
                                  │ Score Breakdown:                       │
                                  │   Base: 50%                            │
                                  │   Combo bonus: +40%                    │
                                  │                                        │
                                  │ [Press Esc to close]                   │
                                  └────────────────────────────────────────┘
                                  Modal overlay (full screen)
```

## Layout Measurements

### Current Panel Space Usage

```
Header:           3 lines  (11%)
Tabs:             3 lines  (11%)
Filter Bar:       2 lines  (7%)
List Header:      2 lines  (7%)
Content:         15 lines  (54%)  ← Actual synergy list
Pagination:       2 lines  (7%)
Status:           1 line   (4%)
─────────────────────────────
Total:           28 lines

Content: 54% of space
Chrome:  46% of space
```

### Proposed Panel Space Usage

```
Header:           3 lines  (11%)
Content:         23 lines  (82%)  ← List + sidebar
Status:           2 lines  (7%)
─────────────────────────────
Total:           28 lines

Content: 82% of space (+28%)
Chrome:  18% of space (-28%)
```

## Type Index States

### Normal View (All Types)

```
┌───┐
│ A │ ← Active (bold, highlighted)
│ C │ (5)
│ K │ (30)
│ T │ (20)
│ A │ (45)
│ H │ (20)
└───┘

Shows counts for each type
User can press letter to filter
```

### Filtered View (Combos Only)

```
┌───┐
│ A │
│ C │ ← Active (bold, highlighted)
│ K │ (5) ← Still shows count
│ T │
│ A │
│ H │
└───┘

Active filter highlighted
Other types dim but still accessible
```

### Search Active View

```
┌───┐
│ A │ (showing 15 of 120)
│ C │ (2)  ← Counts update
│ K │ (5)     based on search
│ T │ (3)
│ A │ (3)
│ H │ (2)
└───┘

Search filters across all types
Type filter still works
Can combine search + type filter
```

## Responsive Behavior

### Narrow Terminal (< 80 cols)

```
┌──────────────────────────────────┐
│ Synergies: Lightning Bolt        │
│ [45 of 120 | Score | All]        │
├───┬──────────────────────────────┤
│ A │ [90%] Sol Ring {1}           │
│ C │   Combo - Goes infinite...   │
│ K │                              │
│ T │ [85%] Lightning Greaves      │
│ A │   Keyword - Protects...      │
│ H │ ...                          │
└───┴──────────────────────────────┘

Adjustments:
- Shorter header text
- Truncate long card names
- Hide search input (use '/' to access)
```

### Wide Terminal (> 120 cols)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Synergies for Lightning Bolt {R}         [Search: ______________ ] │
│ [showing 45 of 120 | Sort: Score | Type: All Synergies]            │
├───┬─────────────────────────────────────────────────────────────────┤
│   │ [90%] Sol Ring {1}                                              │
│ A │       Combo - Goes infinite with your commander enabling turn 3 │
│ ↓ │       wins with proper setup and protection                     │
│   │                                                                 │
│ C │ [85%] Lightning Greaves {2}                                     │
│   │       Keyword - Protects your combo pieces and provides haste   │
└───┴─────────────────────────────────────────────────────────────────┘

Advantages:
- Full card names visible
- Longer reason text (no truncation)
- More items visible per screen
```

## Accessibility Features

### Keyboard Navigation Summary

```
Navigation:
  j/k, ↑/↓    : Move up/down in list
  PageUp/Down : Jump 10 items
  Home/End    : First/last item

Filtering:
  A           : Show all synergies
  C           : Show combos only
  K           : Show keyword synergies
  T           : Show tribal synergies
  A           : Show ability synergies
  H           : Show theme synergies

Search:
  /           : Focus search input
  Esc         : Clear search / close panel

Actions:
  Enter       : View detailed explanation
  s           : Cycle sort (Score/Name/CMC)
  r           : Jump to random synergy

Escape Routes:
  Esc         : Close detail modal
  q, Esc      : Close synergy panel
```

### Visual Indicators

```
Active Selection:
  → [90%] Sol Ring {1} ←
    Background highlight
    Arrow indicators

Active Filter:
  Type: [Combo] ← Bold, colored
  Others gray

Search Active:
  [Search: artifact█_____ ]
          Cursor visible
          Live results

Loading State:
  [Loading synergies...]
  Spinner or progress indicator
```

## CSS Integration

### Key Style Classes Needed

```css
/* Header with search */
.synergy-header {
    height: 3;
    layout: horizontal;
}

.synergy-title {
    width: auto;
}

.synergy-search {
    width: 30;
    margin-left: auto;
}

.synergy-info-bar {
    height: 1;
    background: #151515;
}

/* Type index sidebar */
.type-index-container {
    width: 4;
    height: 100%;
    border-right: solid #3d3d3d;
    padding: 1;
}

.type-index {
    height: auto;
}

.type-letter {
    height: 1;
    padding: 0;
}

.type-letter.active {
    background: #2a2a4e;
    color: #e6c84a;
    text-style: bold;
}

/* Simplified list items */
.synergy-list-item {
    height: 3;  /* 2 lines + spacing */
    padding: 0 1;
}

.synergy-item-line1 {
    height: 1;
}

.synergy-item-line2 {
    height: 1;
    padding-left: 6;  /* Indent reason */
}

/* Detail modal */
.synergy-detail-modal {
    width: 80%;
    height: 80%;
    layer: overlay;
    background: #0d0d0d;
    border: heavy #c9a227;
}
```

## Migration Path

### Phase 1: Layout Simplification

**Before**:
- 5 separate container widgets
- 14 lines of chrome
- Complex nesting

**After**:
- 2 containers (header + content)
- 5 lines of chrome
- Flat hierarchy

### Phase 2: Add Type Index

**Before**:
- Tab widget with 6 tabs
- Horizontal layout
- Complex state management

**After**:
- Sidebar with 6 letters
- Vertical layout
- Simple active index

### Phase 3: Simplify List Items

**Before**:
```
[[[[[[[[..] [K] Lightning Greaves {2}  [85%]
  Keyword - Protects your combo pieces
```

**After**:
```
[85%] Lightning Greaves {2}
      Keyword - Protects your combo pieces
```

### Phase 4: Modal Detail View

**Before**:
- Side panel (40% width)
- Competes with list
- Complex show/hide

**After**:
- Full-screen overlay
- Dedicated focus
- Simple modal pattern

## Summary

The wireframes demonstrate how adopting the Artist Browser pattern results in:

1. **28% more content space** (82% vs 54%)
2. **Cleaner visual hierarchy** (2 levels vs 5 levels)
3. **Faster navigation** (single key vs tab navigation)
4. **Better discoverability** (visual type index)
5. **Responsive search** (prominent input + debouncing)

The design maintains all core functionality while dramatically improving usability.
