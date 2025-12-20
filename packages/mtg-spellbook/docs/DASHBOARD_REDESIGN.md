# MTG Spellbook Dashboard Redesign Proposal
## Analysis and Simplified UX Redesign

**Version:** 1.0
**Date:** 2025-12-15
**Status:** Design Proposal
**Priority:** High - Current implementation unusable

---

## Executive Summary

The current dashboard implementation has critical UX and stability issues that render it "broken with one click." This proposal identifies the root causes and proposes a simplified, more stable redesign that:

1. Eliminates competing focus/key binding conflicts
2. Simplifies the interaction model
3. Keeps the Artist Spotlight concept (user likes this)
4. Maintains the search bar as primary interaction
5. Reduces complexity to improve stability

**Key Finding:** The dashboard has **too many overlapping key bindings** across nested focusable widgets, creating unpredictable behavior and focus traps.

---

## Table of Contents

1. [Problem Analysis](#problem-analysis)
2. [Root Causes](#root-causes)
3. [User Experience Issues](#user-experience-issues)
4. [Proposed Redesign](#proposed-redesign)
5. [Wireframes](#wireframes)
6. [Implementation Strategy](#implementation-strategy)
7. [What to Keep, Change, Remove](#what-to-keep-change-remove)

---

## Problem Analysis

### Current Architecture Issues

#### 1. Key Binding Conflicts (Critical Issue)

The dashboard has **multiple layers of focusable widgets** with **overlapping bindings**:

```
Dashboard (can_focus=True)
├── BINDINGS: a, s, d, r, 1-4, 5-7, 9, enter
├── ArtistSpotlight (can_focus=True)
│   ├── BINDINGS: enter, right, space, 1-4
│   └── FeaturedCard (can_focus=True) × 4
│       └── BINDINGS: enter, space
├── NewSets (can_focus=True)
│   ├── BINDINGS: enter, up, down, j, k, 5-7
│   └── ListView (focusable) with ListItems (focusable)
├── RandomDiscoveries (can_focus=True)
│   └── BINDINGS: enter, space, 9
└── QuickActions (can_focus=True)
    └── BINDINGS: a, s, d, r
```

**Problem:** When user presses `1`, which widget handles it?
- Dashboard.action_card_1?
- ArtistSpotlight.action_select_card_1?
- FeaturedCard focus and activation?

**Result:** Unpredictable behavior, focus traps, broken navigation.

#### 2. Focus Management Complexity

The dashboard has **7+ focusable widgets** in a single view:
1. Dashboard container
2. ArtistSpotlight section
3. FeaturedCard tiles (4x)
4. NewSets section + ListView
5. RandomDiscoveries section
6. QuickActions bar
7. Search input (at bottom)

**Problem:** User tabs through widgets → gets lost → can't escape → "broken."

#### 3. Duplicate Bindings Across Widgets

Multiple widgets define the same keys:

| Key | Dashboard | ArtistSpotlight | NewSets | RandomDiscoveries | QuickActions |
|-----|-----------|-----------------|---------|-------------------|--------------|
| `1` | card_1    | select_card_1   | -       | -                 | -            |
| `5` | set_1     | -               | select_set_1 | -            | -            |
| `enter` | activate_section | view_portfolio | select_set | view_card | -   |
| `a` | artists   | -               | -       | -                 | artists      |

**Result:** Key presses handled by wrong widget depending on focus state.

#### 4. Nested Reactive State

The dashboard loads content asynchronously and updates multiple reactive attributes:
- `Dashboard.is_loading`
- `ArtistSpotlight.artist`, `.featured_cards`, `.is_loading`
- `NewSets.sets`, `.is_loading`
- `RandomDiscoveries.card`, `.is_loading`

**Problem:** Race conditions during loading → widgets in inconsistent states → crashes on interaction.

### What Happens "With One Click"

**Scenario 1: User presses `1` immediately after launch**
```
1. Dashboard is loading (is_loading=True)
2. User presses `1` → Dashboard.action_card_1() fires
3. Calls spotlight._select_card_at(0)
4. spotlight._cards is still empty (loading not done)
5. IndexError or silent failure
6. Dashboard appears "broken" (nothing happens)
```

**Scenario 2: User tabs to explore sections**
```
1. User presses Tab → focus moves to ArtistSpotlight
2. Presses Tab again → focus to FeaturedCard #1
3. Presses Tab → FeaturedCard #2
4. Presses Tab → FeaturedCard #3
5. Presses Tab → FeaturedCard #4
6. Presses Tab → NewSets ListView
7. Presses Tab → ListItem #1
8. Presses Tab → ListItem #2
9. User is now 9 tabs deep, lost, can't remember how to get back
10. Presses Escape → Nothing (no binding)
11. User feels stuck → "broken"
```

**Scenario 3: User tries to use quick actions**
```
1. User presses `A` for artists
2. Focus is on FeaturedCard → binding doesn't fire
3. Nothing happens
4. User presses `A` again → still nothing
5. User gives up → "broken"
```

---

## Root Causes

### 1. Over-Engineering for V1

The dashboard tries to do too much on launch:
- Artist spotlight with 4 clickable cards
- 3 clickable sets in a scrollable list
- Random card of the day
- Quick action bar
- Number key shortcuts (1-9)
- Navigation between sections
- Loading 4+ database queries in parallel

**Analysis:** This is Phase 3 complexity for a Phase 1 feature. Too ambitious.

### 2. Textual Focus Model Mismatch

Textual's focus model is designed for **single-focused-widget** at a time. The dashboard tries to create a **multi-section interactive experience** with:
- Multiple focusable sections
- Overlapping key bindings
- Nested focusable children

**This doesn't match how Textual wants to work.**

### 3. Missing Guard Rails

The code lacks defensive checks:
- No `if self._cards:` before `self._cards[index]`
- No `if not self.is_loading:` before user actions
- No disabled state during loading
- No bounds checking on index access

**Result:** Crashes or silent failures when user acts too fast.

### 4. Confusing Mental Model

User sees dashboard and thinks:
- "I can click these cards" (but how?)
- "I see numbers [1-4] but what are they for?"
- "There's a search bar at the bottom but I'm in this dashboard"
- "How do I get back to searching?"

**The dashboard creates cognitive load instead of reducing it.**

---

## User Experience Issues

### Issue 1: No Clear Primary Action

**Problem:** User sees the dashboard and doesn't know what to do first.
- Should I press a number?
- Should I tab to a section?
- Should I just start typing?
- Should I press a quick action key?

**Result:** Analysis paralysis → user does nothing or random action.

### Issue 2: Focus Traps

**Problem:** Tab navigation goes through 7+ widgets before returning to input.
- User tabs through 4 featured cards (why?)
- User tabs through ListView items (gets lost)
- No visual indicator of focus hierarchy
- No escape hatch (Escape key doesn't reset focus)

**Result:** User feels stuck, can't navigate out.

### Issue 3: Invisible Number Shortcuts

**Problem:** Dashboard shows `[1] Path to Exile` but:
- No clear indication these are keyboard shortcuts
- Doesn't work if focus isn't on Dashboard
- User presses `1` → nothing happens → confusion

**Result:** Features appear broken.

### Issue 4: Competing Interaction Models

**Problem:** Dashboard supports 3 different interaction models simultaneously:
1. **Keyboard numbers** (1-9): Jump to specific items
2. **Keyboard letters** (A/S/D/R): Quick actions
3. **Tab + Enter**: Navigate and select
4. **Mouse clicks**: Click on items (in theory)

**Result:** User doesn't know which to use, tries multiple, gets confused.

### Issue 5: Unclear Escape Path

**Problem:** User sees dashboard but wants to search.
- No clear "skip dashboard" hint
- Search bar at bottom isn't obvious
- Escape key doesn't do anything
- Ctrl+F hint isn't shown

**Result:** User stuck on dashboard, feels forced to engage.

---

## Proposed Redesign

### Design Principles

1. **Simplicity First**: One primary interaction model, not four
2. **Search is Primary**: Dashboard enhances search, doesn't replace it
3. **Read-Only Discovery**: Dashboard shows content, doesn't require interaction
4. **Clear Escape**: Always obvious how to "skip" and search
5. **No Focus Traps**: Minimal focusable widgets, clear tab order
6. **Fast Loading**: Content appears instantly, not gradually
7. **Artist Spotlight**: Keep this (user likes it), but simplify

### Key Changes

#### 1. Make Dashboard Read-Only (Non-Focusable)

**Current:** Dashboard and all sections are `can_focus=True`
**Proposed:** Dashboard is informational only, not interactive

```python
class Dashboard(Vertical, can_focus=False):  # Non-focusable
    """Read-only discovery panel shown on launch."""
```

**Benefits:**
- No focus traps
- No key binding conflicts
- Clearer mental model: "This is info, search bar is action"

#### 2. Eliminate Number Key Shortcuts

**Current:** `1-4` for cards, `5-7` for sets, `9` for card of day
**Proposed:** Remove all number shortcuts

**Why:** They're invisible, confusing, and conflict with text input when user starts typing card names (e.g., "10th Edition").

**Alternative:** Show clickable items but use **letter shortcuts only** for major actions.

#### 3. Simplify to 3 Sections (Not 5)

**Current:**
1. Artist Spotlight (interactive)
2. Featured Cards grid (4x focusable)
3. New Sets (scrollable list)
4. Random Discoveries (card of day)
5. Quick Actions (4 buttons)

**Proposed:**
1. **Artist Spotlight** (read-only, no featured cards grid)
2. **Recent Sets** (read-only, 3 sets listed)
3. **Quick Actions Bar** (4 letter shortcuts only)

**Removed:**
- Featured cards grid (too complex, causes focus issues)
- Card of the Day (redundant with Random Card shortcut)

#### 4. Single Row of Letter Shortcuts Only

**Current:** A/S/D/R in a QuickActions bar that's also focusable
**Proposed:** A/S/D/R shown as hint text, handled at app level

```
Quick Actions: [A] Artists · [S] Sets · [D] Decks · [R] Random · [/] Search
```

Handled by app-level bindings, not widget bindings.

#### 5. Clear Search Prompt Always Visible

**Current:** Search input at bottom, no hint that it's primary
**Proposed:** Prominent hint at top of dashboard

```
┌─ Welcome to MTG Spellbook ─────────────────────────────┐
│ Type to search for cards (or press A/S/D/R for quick)  │
│                                                         │
│ ⚡ Search: _                                            │
└─────────────────────────────────────────────────────────┘
```

#### 6. Auto-Hide Dashboard After First Action

**Current:** Dashboard hides when search is submitted
**Proposed:** Dashboard hides on ANY user action (A/S/D/R/search)

Once user engages with the app, they don't need the dashboard anymore.

---

## Wireframes

### Wireframe 1: Simplified Dashboard (Default View)

```
┌─ MTG SPELLBOOK ─────────────────────────────────────────────────────────────┐
│ ✦ 33,429 cards · 842 sets · 2,245 artists                [?] Help [Ctrl+Q] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Welcome! Type to search, or use quick actions below.                      │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  ✨ ARTIST SPOTLIGHT                                                       │
│                                                                             │
│     Rebecca Guay                                                            │
│     Known for ethereal watercolor artwork with fairy tale aesthetics.      │
│     47 cards · 18 sets · 1997-2019                                         │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  📚 RECENT SETS                    🎲 QUICK ACTIONS                        │
│                                                                             │
│   Murders at Karlov Manor           [A] Browse All Artists                 │
│   Feb 2024 · 286 cards              [S] Browse All Sets                    │
│                                      [D] My Decks                           │
│   Outlaws Thunder Junction          [R] Random Card                        │
│   Apr 2024 · 276 cards                                                     │
│                                      Type / or Ctrl+F to search            │
│   Modern Horizons 3                                                        │
│   Jun 2024 · 303 cards                                                     │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  [A] Artists · [S] Sets · [D] Decks · [R] Random                          │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  ⚡  _                                                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- **No focusable sections** - entire dashboard is static/read-only
- **No number shortcuts** - only A/S/D/R letter shortcuts
- **Clear search prompt** - "Type to search" message
- **Simplified artist spotlight** - just name and description, no card grid
- **Compact set list** - 3 sets, no scrollable ListView
- **Prominent quick actions** - clear letter shortcuts shown twice

### Wireframe 2: After User Types (Dashboard Hidden)

```
┌─ MTG SPELLBOOK ─────────────────────────────────────────────────────────────┐
│ ✦ 33,429 cards · 842 sets · 2,245 artists                [?] Help [Ctrl+Q] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Search Results                  │  Lightning Bolt                         │
│  ────────────────                │  ───────────────────────                │
│                                   │                                         │
│  > Lightning Bolt                 │  Instant                    {R}        │
│    Lava Spike                     │  Deal 3 damage to any                  │
│    Shock                          │  target.                               │
│    ...                            │                                         │
│                                   │  ┌─────────────────┐                   │
│                                   │  │    Art: 2BBR    │                   │
│                                   │  └─────────────────┘                   │
│                                   │                                         │
│                                   │  [Ctrl+S] Synergy                      │
│                                   │  [Ctrl+A] Art                          │
│                                   │                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  ⚡  lightning bolt_                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Dashboard is completely hidden after first search. User in familiar results view.

---

## Implementation Strategy

### Phase 1: Stabilization (Week 1)

**Goal:** Fix critical bugs in current dashboard

1. **Add loading guards**: Disable all actions while `is_loading=True`
2. **Add bounds checking**: Check array length before indexing
3. **Remove nested focusables**: Make FeaturedCard non-focusable
4. **Add escape binding**: `Escape` → focus search input

```python
class Dashboard(Vertical, can_focus=True):
    def action_card_1(self) -> None:
        if self.is_loading:
            return  # Guard: Don't act while loading
        spotlight = self.query_one("#artist-spotlight", ArtistSpotlight)
        if spotlight._cards and len(spotlight._cards) > 0:  # Bounds check
            spotlight._select_card_at(0)
```

**Outcome:** Dashboard still complex but doesn't crash.

### Phase 2: Simplification (Week 2)

**Goal:** Implement simplified read-only design

1. **Remove focus from Dashboard**: `can_focus=False`
2. **Remove FeaturedCard grid**: Just show artist name/bio
3. **Replace NewSets ListView** with static list (no focus)
4. **Remove number key bindings**: Keep only A/S/D/R
5. **Add prominent search hint**: Welcome message at top

```python
class Dashboard(Vertical, can_focus=False):  # No longer focusable
    """Read-only discovery panel."""

    BINDINGS = [
        # All bindings removed - handled at app level
    ]
```

**Outcome:** Simpler, more stable dashboard.

### Phase 3: Polish (Week 3)

**Goal:** Enhance with better styling and hints

1. **Add loading skeleton**: Show placeholders while loading
2. **Add click handlers**: Allow mouse clicks on artist name (even if not focusable)
3. **Add animation**: Fade-in effect when dashboard loads
4. **Add rotation**: Different artist each day (already implemented)

---

## What to Keep, Change, Remove

### ✅ Keep (User Likes These)

1. **Artist Spotlight concept** - User loves MTG artists
   - Keep the daily featured artist
   - Keep artist name, bio, stats
   - Keep the aesthetic (gold colors, nice formatting)

2. **Quick Actions (A/S/D/R)** - Fast shortcuts are good
   - Keep the letter shortcuts
   - Keep the clear labeling

3. **Auto-hide on search** - Good behavior
   - Keep hiding dashboard after user engages

4. **Search bar as primary** - Core interaction
   - Keep search input always visible at bottom
   - Keep it as primary interaction

### 🔄 Change (Needs Simplification)

1. **Artist Spotlight section** → Simplify
   - **Remove:** 4-card grid with individual focus
   - **Keep:** Artist name, description, stats
   - **Change:** Make clicking artist name open portfolio (simple message)

2. **New Sets section** → Simplify
   - **Remove:** Scrollable ListView with navigation
   - **Keep:** 3 recent sets
   - **Change:** Simple static text list, no interaction

3. **Quick Actions section** → Simplify
   - **Remove:** Focusable QuickActions widget
   - **Keep:** A/S/D/R shortcuts
   - **Change:** Show as hint text, handle at app level

4. **Number shortcuts** → Remove entirely
   - **Remove:** 1-9 bindings (too confusing)
   - **Replace:** Letter shortcuts only (A/S/D/R)

### ❌ Remove (Causing Problems)

1. **FeaturedCard widget** - Adds complexity, causes focus traps
   - Entire widget can be removed
   - Artist spotlight can be text-only

2. **Card of the Day section** - Redundant
   - Random card shortcut (R) does the same thing
   - Removes one section = simpler layout

3. **Nested focusable widgets** - Root cause of focus traps
   - Dashboard should be non-focusable OR children non-focusable
   - Can't have both without issues

4. **Loading state complexity** - Race conditions
   - Simplify to: show placeholder → load → replace
   - No partial loading states

---

## Technical Implementation Notes

### Focus Model

**Current Problem:**
```python
Dashboard (can_focus=True)
├── ArtistSpotlight (can_focus=True)
│   └── FeaturedCard (can_focus=True) × 4  # Focus trap!
└── NewSets (can_focus=True)
    └── ListView (focusable) → ListItem (focusable) × 3  # Another trap!
```

**Proposed Solution:**
```python
Dashboard (can_focus=False)  # Not focusable
├── ArtistSpotlight (Static)  # Just displays text
├── RecentSets (Static)       # Just displays text
└── QuickActionsHint (Static) # Just displays text
```

All interactions handled at app level via global bindings.

### Key Binding Architecture

**Current Problem:** Bindings scattered across 5 widgets
**Proposed Solution:** All shortcuts at app level

```python
# In app.py
class MTGSpellbook(App):
    BINDINGS = [
        # Global shortcuts (work anywhere, including dashboard)
        Binding("a", "browse_artists", "Artists"),
        Binding("s", "browse_sets", "Sets"),
        Binding("d", "toggle_decks", "Decks"),
        Binding("r", "random_card", "Random"),
        Binding("/", "focus_input", "Search"),
        # ... other bindings
    ]

    def action_browse_artists(self) -> None:
        """Browse artists - works from dashboard or anywhere."""
        self._hide_dashboard()
        self.browse_artists()
```

**Benefits:**
- Shortcuts work everywhere, not just when focused on right widget
- No key binding conflicts
- Predictable behavior

### Loading State

**Current Problem:** Multiple reactive loading states
**Proposed Solution:** Single loading state with skeleton

```python
class Dashboard(Vertical):
    is_loading: reactive[bool] = reactive(True)

    def compose(self) -> ComposeResult:
        if self.is_loading:
            yield Static("[dim]Loading...[/]", id="loading-skeleton")
        else:
            yield Static(f"Artist: {self.artist_name}", id="artist-info")
            # ... other content
```

### Message Flow

**Keep this simple:**

```
User presses 'A' → App.action_browse_artists()
                  → self._hide_dashboard()
                  → self.browse_artists()
```

No dashboard messages needed for basic navigation.

---

## Migration Path

### For Users

**Before (Current):**
1. App launches → dashboard loads gradually
2. User sees sections appear one by one
3. User tries to interact → things break
4. User confused, gives up

**After (Redesigned):**
1. App launches → dashboard appears instantly (placeholder if needed)
2. User sees "Type to search or press A/S/D/R"
3. User presses 'R' → random card appears, dashboard hidden
4. User searches → results appear, dashboard hidden
5. Clear, predictable behavior

### For Developers

**Migration steps:**

1. Create new `dashboard_v2/` directory
2. Implement simplified widgets (no focus, no bindings)
3. Move A/S/D/R bindings to app level
4. Test thoroughly (no focus traps, no crashes)
5. Replace old dashboard with new one
6. Remove old `dashboard/` directory

**No breaking changes** - dashboard is internal widget, not exposed API.

---

## Success Criteria

After redesign, dashboard should:

1. ✅ **Never crash** - No IndexError, no race conditions
2. ✅ **No focus traps** - Tab navigation predictable and escapable
3. ✅ **Shortcuts work reliably** - A/S/D/R work from anywhere
4. ✅ **Clear mental model** - Users understand what to do
5. ✅ **Fast loading** - Appears in <500ms, even on slow systems
6. ✅ **Keep artist spotlight** - User's favorite feature preserved
7. ✅ **Search remains primary** - Dashboard enhances, doesn't replace

---

## Appendix A: Key Binding Conflicts (Detailed)

### Current Conflicts

| Key | Widget 1 | Widget 2 | Widget 3 | Result |
|-----|----------|----------|----------|--------|
| `1` | Dashboard.action_card_1 | ArtistSpotlight.action_select_card_1 | - | Depends on focus |
| `2` | Dashboard.action_card_2 | ArtistSpotlight.action_select_card_2 | - | Depends on focus |
| `3` | Dashboard.action_card_3 | ArtistSpotlight.action_select_card_3 | - | Depends on focus |
| `4` | Dashboard.action_card_4 | ArtistSpotlight.action_select_card_4 | - | Depends on focus |
| `5` | Dashboard.action_set_1 | NewSets.action_select_set_1 | - | Depends on focus |
| `6` | Dashboard.action_set_2 | NewSets.action_select_set_2 | - | Depends on focus |
| `7` | Dashboard.action_set_3 | NewSets.action_select_set_3 | - | Depends on focus |
| `9` | Dashboard.action_card_of_day | RandomDiscoveries.action_view_card | - | Depends on focus |
| `enter` | Dashboard.action_activate_section | ArtistSpotlight.action_view_portfolio | NewSets.action_select_set | RandomDiscoveries.action_view_card |
| `a` | Dashboard.action_artists | QuickActions.action_artists | - | Depends on focus |
| `s` | Dashboard.action_sets | QuickActions.action_sets | - | Depends on focus |
| `d` | Dashboard.action_decks | QuickActions.action_decks | - | Depends on focus |
| `r` | Dashboard.action_random | QuickActions.action_random | - | Depends on focus |

**Total conflicts: 17 key bindings with ambiguous behavior**

### After Redesign (No Conflicts)

| Key | Handler | Scope | Result |
|-----|---------|-------|--------|
| `a` | App.action_browse_artists | Global | Always works |
| `s` | App.action_browse_sets | Global | Always works |
| `d` | App.action_toggle_decks | Global | Always works |
| `r` | App.action_random_card | Global | Always works |
| `/` | App.action_focus_input | Global | Always works |

**Total conflicts: 0**

---

## Appendix B: Loading Performance Analysis

### Current Loading Sequence

```python
async def load_dashboard(self) -> None:
    # 4 parallel database queries
    artist_task = self._db.get_random_artist_for_spotlight(min_cards=20)
    sets_task = self._db.get_latest_sets(limit=3)
    card_task = self._db.get_random_card_of_day()

    results = await asyncio.gather(artist_task, sets_task, card_task)

    # Then loads 4 more cards for artist
    featured = await self._db.get_featured_cards_for_artist(artist, limit=4)
```

**Total:** 5 database queries on launch
**Time:** ~200-500ms depending on system
**Issue:** Dashboard shows "Loading..." → sections appear gradually → user can interact before ready

### Proposed Loading Sequence

```python
async def load_dashboard(self) -> None:
    # Show placeholder immediately
    self.update_placeholder()

    # 2 parallel queries (removed card of day, removed featured cards)
    artist_task = self._db.get_random_artist_for_spotlight(min_cards=20)
    sets_task = self._db.get_latest_sets(limit=3)

    results = await asyncio.gather(artist_task, sets_task)

    # Update dashboard (all at once, not gradually)
    self.update_content(artist, sets)
```

**Total:** 2 database queries on launch
**Time:** ~100-200ms
**Improvement:** 60% faster, simpler, no gradual loading

---

## Conclusion

The current dashboard has fundamental architecture issues:

1. **Too many focusable widgets** → focus traps
2. **Overlapping key bindings** → unpredictable behavior
3. **Complex loading states** → race conditions
4. **Confusing interaction model** → cognitive overload

**Recommendation:** Implement the simplified read-only dashboard design.

**Why this will work:**
- Eliminates all focus-related bugs (non-focusable)
- Eliminates all key binding conflicts (handled at app level)
- Eliminates loading race conditions (simpler state)
- Maintains artist spotlight (user's favorite feature)
- Keeps search as primary (user's main workflow)

**Estimated effort:** 2-3 days to implement Phase 2 (simplified design)

**Risk:** Low - smaller surface area = fewer bugs

**User impact:** High - transforms "broken with one click" into stable, predictable experience.
