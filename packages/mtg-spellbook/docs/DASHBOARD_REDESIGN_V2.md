# MTG Spellbook Dashboard Redesign V2
## Simplified, Stable Dashboard Design

**Version:** 2.0
**Date:** 2025-12-15
**Status:** Design Proposal (Final)
**Priority:** Critical - Current implementation is buggy/unusable

---

## Executive Summary

The current dashboard implementation is **buggy and unusable** - "one click and it's basically broken." This V2 redesign proposes a **radically simplified approach** that eliminates all stability issues while keeping the core Artist Spotlight concept the user loves.

### Key Changes from V1 Design

**V1 Analysis (DASHBOARD_REDESIGN.md)** correctly identified all the problems:
- 17+ key binding conflicts across nested focusable widgets
- Focus traps (7+ focusable components)
- Race conditions in loading states
- Confusing interaction model (4 different paradigms)

**V2 Proposal:** Implement the **read-only dashboard** solution from V1's Phase 2, but **go even simpler**.

### The Core Problem: "One Click Breaks It"

After analyzing the code, the breakage happens because:

1. **User clicks during loading** → Featured cards array is empty → IndexError
2. **User tabs through sections** → Gets trapped in nested focusable widgets → Can't escape
3. **User presses number key** → Wrong widget handles it (focus-dependent) → Nothing happens
4. **User tries to interact** → Multiple handlers fire (message bubbling) → Unpredictable behavior

**Root Cause:** The dashboard is **over-designed**. It tries to be interactive when it should just be informational.

---

## Proposed Solution: Read-Only Dashboard

### Design Philosophy

1. **Dashboard is informational only** - Shows what's available, doesn't require interaction
2. **Search bar is the only input** - Everything happens through search
3. **Quick action shortcuts at app level** - A/S/D/R work everywhere
4. **Auto-hide on any action** - Dashboard disappears after user does anything
5. **Artist Spotlight stays** - User loves this, just make it simpler

### What This Means

**Remove:**
- All focusable sections (Dashboard, ArtistSpotlight, NewSets, etc.)
- All widget-level key bindings (1-9, enter, space, etc.)
- All nested interactive components (FeaturedCard, ListView, etc.)
- RandomDiscoveries section (redundant with "R" shortcut)
- QuickActions widget (becomes hint text)

**Keep:**
- Artist Spotlight (text-only, no card grid)
- New Sets list (static text, 3 sets)
- Clear visual styling (gold colors, nice formatting)

**Add:**
- Prominent search hint at top
- App-level shortcuts (A/S/D/R)
- Click-to-search on artist name
- Simple, stable architecture

---

## Wireframes

### Wireframe 1: Simplified Dashboard (Read-Only)

```
┌─ MTG SPELLBOOK ─────────────────────────────────────────────────────────────┐
│ ✦  33,429 cards · 842 sets                          [?] Help    [Ctrl+Q]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Welcome! Type to search cards, or use quick actions below.                │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  ✨ ARTIST SPOTLIGHT                                                       │
│                                                                             │
│     Rebecca Guay                                                            │
│                                                                             │
│     Known for ethereal watercolor artwork with fairy tale aesthetics.      │
│     47 cards illustrated · 18 sets · 1997-2019                             │
│                                                                             │
│     Click artist name or type ':artist rebecca guay' to view portfolio     │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  📚 RECENT SETS                                                             │
│                                                                             │
│     Murders at Karlov Manor         Feb 2024 · 286 cards · Expansion       │
│     Outlaws Thunder Junction        Apr 2024 · 276 cards · Expansion       │
│     Modern Horizons 3                Jun 2024 · 303 cards · Masters        │
│                                                                             │
│     Type ':set mkm' to explore sets                                        │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  🚀 QUICK ACTIONS                                                           │
│                                                                             │
│     [A] Browse Artists (2,245)                                              │
│     [S] Browse Sets (842)                                                   │
│     [D] My Decks                                                            │
│     [R] Random Card                                                         │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  ⚡  _                                                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
    Type to search · [A] Artists · [S] Sets · [D] Decks · [R] Random
```

**Key Features:**
- **No focusable sections** - everything is static text
- **No number shortcuts** - no [1-4] or [5-7] confusion
- **Clear call-to-action** - "Type to search" message
- **Simple artist spotlight** - just name and bio, no card grid
- **Static set list** - plain text, no ListView navigation
- **Hints for actions** - "Click artist name" or "Type :artist"

### Wireframe 2: Compact Version (80x24 Terminal)

```
┌─ MTG SPELLBOOK ───────────────────────────────────────────────────────┐
│ ✦ 33k cards · 842 sets                            [?] [Ctrl+Q]       │
├───────────────────────────────────────────────────────────────────────┤
│ Type to search, or use quick actions:                                │
│                                                                       │
│ ✨ ARTIST SPOTLIGHT                                                  │
│   Rebecca Guay · 47 cards · Ethereal watercolor artwork              │
│                                                                       │
│ 📚 RECENT SETS                                                        │
│   Murders at Karlov Manor (MKM) · Feb 2024 · 286 cards               │
│   Outlaws Thunder Junction (OTJ) · Apr 2024 · 276 cards              │
│   Modern Horizons 3 (MH3) · Jun 2024 · 303 cards                     │
│                                                                       │
│ 🚀 [A] Artists  [S] Sets  [D] Decks  [R] Random                      │
│                                                                       │
├───────────────────────────────────────────────────────────────────────┤
│ ⚡ _                                                                  │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### Before (Current - Broken)

```python
Dashboard (can_focus=True, 17+ bindings)
├── ArtistSpotlight (can_focus=True, 7 bindings)
│   ├── FeaturedCard (can_focus=True, 2 bindings) × 4  # FOCUS TRAP
│   └── Horizontal grid (complex layout)
├── NewSets (can_focus=True, 6 bindings)
│   └── ListView (focusable)
│       └── ListItem (focusable) × 3  # FOCUS TRAP
├── RandomDiscoveries (can_focus=True, 2 bindings)
│   └── Static card display
└── QuickActions (can_focus=True, 4 bindings)
    └── Action buttons × 4
```

**Issues:**
- 7+ focusable widgets → tab navigation nightmare
- 17+ key binding conflicts → unpredictable behavior
- Complex reactive state → race conditions
- Too many messages → event bubbling chaos

### After (Proposed - Stable)

```python
Dashboard (can_focus=False, NO bindings)
├── Static (welcome message)
├── Static (artist spotlight text)
├── Static (recent sets text)
└── Static (quick actions hints)
```

**Benefits:**
- 0 focusable widgets → no focus traps
- 0 key binding conflicts → all handled at app level
- Simple reactive state → just loading flag
- No messages → no bubbling issues

---

## Technical Implementation

### 1. Simplified Dashboard Widget

```python
# dashboard/widget.py

from __future__ import annotations
from typing import TYPE_CHECKING
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static

if TYPE_CHECKING:
    from mtg_core.data.database import MTGDatabase
    from mtg_core.data.models.responses import ArtistSummary
    from mtg_core.data.models import Set

class Dashboard(Vertical, can_focus=False):  # NOT FOCUSABLE
    """Read-only discovery dashboard shown on launch.

    Shows artist spotlight, recent sets, and quick action hints.
    All interactions happen through app-level shortcuts or search.
    """

    is_loading: reactive[bool] = reactive(True)

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._db: MTGDatabase | None = None
        self._artist: ArtistSummary | None = None
        self._sets: list[Set] = []

    def compose(self) -> ComposeResult:
        # Welcome message
        yield Static(
            "[dim]Welcome! Type to search cards, or use quick actions below.[/]",
            classes="dashboard-welcome",
        )

        # Artist Spotlight (static text only)
        yield Static(
            "[dim]Loading artist spotlight...[/]",
            id="artist-spotlight-content",
            classes="artist-spotlight-static",
        )

        # Recent Sets (static text only)
        yield Static(
            "[dim]Loading recent sets...[/]",
            id="recent-sets-content",
            classes="recent-sets-static",
        )

        # Quick Actions (hint text only)
        yield Static(
            "[dim][A] Artists · [S] Sets · [D] Decks · [R] Random[/]",
            classes="quick-actions-hint",
        )

    def set_database(self, db: MTGDatabase) -> None:
        """Set database connection."""
        self._db = db

    async def load_dashboard(self) -> None:
        """Load dashboard content from database."""
        import asyncio

        if not self._db:
            return

        self.is_loading = True

        try:
            # Simple parallel queries (removed featured cards query)
            artist_task = asyncio.create_task(
                self._db.get_random_artist_for_spotlight(min_cards=20)
            )
            sets_task = asyncio.create_task(
                self._db.get_latest_sets(limit=3)
            )

            results = await asyncio.gather(
                artist_task, sets_task, return_exceptions=True
            )

            artist_result, sets_result = results

            # Update artist spotlight (text only)
            if not isinstance(artist_result, BaseException) and artist_result:
                self._artist = artist_result
                self._update_artist_spotlight(artist_result)

            # Update sets list (text only)
            if not isinstance(sets_result, BaseException):
                self._sets = sets_result
                self._update_sets_list(sets_result)

        finally:
            self.is_loading = False

    def _update_artist_spotlight(self, artist: ArtistSummary) -> None:
        """Update artist spotlight with static text."""
        from ...ui.theme import ui_colors

        year_range = ""
        if artist.first_card_year and artist.most_recent_year:
            if artist.first_card_year == artist.most_recent_year:
                year_range = f" · {artist.first_card_year}"
            else:
                year_range = f" · {artist.first_card_year}-{artist.most_recent_year}"

        content = (
            f"\n[bold {ui_colors.GOLD}]✨ ARTIST SPOTLIGHT[/]\n\n"
            f"   [bold {ui_colors.GOLD}]{artist.name}[/]\n\n"
            f"   [dim]{artist.card_count} cards illustrated · "
            f"{artist.sets_count} sets{year_range}[/]\n\n"
            f"   [dim]Type[/] [bold]:artist {artist.name.lower()}[/] "
            f"[dim]to view portfolio[/]\n"
        )

        spotlight_widget = self.query_one("#artist-spotlight-content", Static)
        spotlight_widget.update(content)

    def _update_sets_list(self, sets: list[Set]) -> None:
        """Update sets list with static text."""
        from ...ui.theme import ui_colors

        content = f"\n[bold {ui_colors.GOLD}]📚 RECENT SETS[/]\n\n"

        for set_info in sets[:3]:
            release = set_info.release_date or "Unknown"
            card_count = set_info.total_set_size or set_info.base_set_size or 0
            set_type = (set_info.type or "expansion").replace("_", " ").title()

            content += (
                f"   {set_info.name} ({set_info.code.upper()})\n"
                f"   [dim]{release} · {card_count} cards · {set_type}[/]\n\n"
            )

        content += f"   [dim]Type[/] [bold]:sets[/] [dim]to browse all sets[/]\n"

        sets_widget = self.query_one("#recent-sets-content", Static)
        sets_widget.update(content)

    def clear(self) -> None:
        """Clear dashboard content."""
        self.is_loading = True
        self._artist = None
        self._sets = []
```

### 2. Remove All Subwidgets

**Delete these files:**
- `dashboard/artist_spotlight.py` - No longer needed (static text only)
- `dashboard/new_sets.py` - No longer needed (static text only)
- `dashboard/random_discoveries.py` - No longer needed (use "R" shortcut)
- `dashboard/quick_actions.py` - No longer needed (hint text only)

**Keep only:**
- `dashboard/widget.py` - Main dashboard (simplified)
- `dashboard/messages.py` - Empty (dashboard posts no messages)
- `dashboard/__init__.py` - Minimal exports

### 3. App-Level Shortcuts (No Conflicts)

```python
# app.py

class MTGSpellbook(App):
    BINDINGS = [
        # ... existing bindings ...

        # Quick actions (work from anywhere, including dashboard)
        Binding("a", "browse_artists", "Artists", show=True),
        Binding("s", "browse_sets", "Sets", show=True),
        Binding("d", "toggle_decks", "Decks", show=True),
        Binding("r", "random_card", "Random", show=True),
    ]

    def action_browse_artists(self) -> None:
        """Browse all artists - hides dashboard automatically."""
        self._hide_dashboard()
        self.browse_artists()

    def action_browse_sets(self) -> None:
        """Browse all sets - hides dashboard automatically."""
        self._hide_dashboard()
        self.browse_sets("")

    def action_random_card(self) -> None:
        """Show random card - hides dashboard automatically."""
        self._hide_dashboard()
        self.lookup_random()
```

**No widget-level bindings** = **No conflicts** = **Predictable behavior**

### 4. Remove Dashboard Messages

```python
# dashboard/messages.py

"""Messages for dashboard - DEPRECATED.

Dashboard is now read-only and posts no messages.
All interactions handled at app level.
"""

# Keep these for backward compatibility with app.py handlers
from __future__ import annotations
from typing import TYPE_CHECKING
from textual.message import Message

if TYPE_CHECKING:
    from mtg_core.data.models import Card, Set
    from mtg_core.data.models.responses import ArtistSummary

# These are no longer posted by dashboard, but app.py may still handle them
class DashboardAction(Message):
    """Deprecated - use app-level bindings instead."""
    pass

class ArtistClicked(Message):
    """Deprecated - dashboard is read-only."""
    pass

class CardClicked(Message):
    """Deprecated - dashboard is read-only."""
    pass

class SetClicked(Message):
    """Deprecated - dashboard is read-only."""
    pass

class RefreshDashboard(Message):
    """Deprecated - no interactive refresh needed."""
    pass
```

### 5. Simplified CSS

```css
/* dashboard-view.css (additions to styles.py) */

/* Dashboard container - non-focusable, static content only */
#dashboard {
    width: 100%;
    height: 100%;
    background: #0d0d0d;
    padding: 1 2;
}

#dashboard.hidden {
    display: none;
}

.dashboard-welcome {
    height: 2;
    text-align: center;
    padding: 0 0 1 0;
    color: #888;
}

/* Artist Spotlight - static text only */
.artist-spotlight-static {
    height: auto;
    min-height: 8;
    background: #151515;
    border: round #3d3d3d;
    padding: 0;
    margin-bottom: 1;
}

/* Recent Sets - static text only */
.recent-sets-static {
    height: auto;
    min-height: 10;
    background: #151515;
    border: round #3d3d3d;
    padding: 0;
    margin-bottom: 1;
}

/* Quick Actions - hint text only */
.quick-actions-hint {
    height: 3;
    text-align: center;
    padding: 1;
    background: #1a1a2e;
    border-top: solid #3d3d3d;
    color: #888;
}
```

---

## What Changed from V1 Design

### Implemented from V1 Recommendations

✅ **Dashboard is non-focusable** (Phase 2 recommendation)
✅ **Removed number key shortcuts** (1-9 eliminated)
✅ **Removed nested focusable widgets** (FeaturedCard, ListView)
✅ **App-level shortcuts only** (A/S/D/R at top level)
✅ **Simplified artist spotlight** (text only, no card grid)
✅ **Reduced database queries** (2 instead of 5)

### Additional Simplifications in V2

🆕 **Removed RandomDiscoveries section** (redundant with "R" shortcut)
🆕 **Removed QuickActions widget** (now just hint text)
🆕 **No messages at all** (dashboard posts nothing)
🆕 **No reactive artist/sets** (just loading flag)
🆕 **Even simpler layout** (4 static widgets total)

### What We Kept (User Loves This)

❤️ **Artist Spotlight** - Still the hero section, just simpler
❤️ **Recent Sets** - Still shows latest 3 sets
❤️ **Quick Actions** - A/S/D/R shortcuts still work
❤️ **Auto-hide on search** - Dashboard disappears when user types
❤️ **Visual styling** - Gold colors, nice formatting

---

## Focus Model Comparison

### Before: 7+ Focusable Widgets (BROKEN)

```
Tab Order:
1. Dashboard
2. ArtistSpotlight
3. FeaturedCard #1
4. FeaturedCard #2
5. FeaturedCard #3
6. FeaturedCard #4
7. NewSets
8. ListView
9. ListItem #1
10. ListItem #2
11. ListItem #3
12. RandomDiscoveries
13. QuickActions
14. Search Input

User presses Tab 14 times to get back to search → LOST
```

### After: 0 Focusable Widgets (FIXED)

```
Tab Order:
1. Search Input
2. (nothing else on dashboard)

User presses Tab once → still on search input → CLEAR
```

**Result:** No focus traps, no confusion, no "broken" feeling.

---

## Key Binding Comparison

### Before: 17+ Conflicts (BROKEN)

| Key | Dashboard | ArtistSpotlight | NewSets | RandomDiscoveries | QuickActions | Result |
|-----|-----------|-----------------|---------|-------------------|--------------|--------|
| `1` | action_card_1 | action_select_card_1 | - | - | - | Depends on focus |
| `a` | action_artists | - | - | - | action_artists | Depends on focus |
| `enter` | action_activate_section | action_view_portfolio | action_select_set | action_view_card | - | Depends on focus |

**17 total conflicts** → Unpredictable behavior

### After: 0 Conflicts (FIXED)

| Key | Handler | Scope | Result |
|-----|---------|-------|--------|
| `a` | App.action_browse_artists | Global | Always works |
| `s` | App.action_browse_sets | Global | Always works |
| `d` | App.action_toggle_decks | Global | Always works |
| `r` | App.action_random_card | Global | Always works |

**0 conflicts** → Predictable behavior

---

## Loading Performance

### Before: 5 Database Queries

```python
# 4 parallel queries
artist = await db.get_random_artist_for_spotlight(min_cards=20)
sets = await db.get_latest_sets(limit=3)
card = await db.get_random_card_of_day()

# Then 1 more query (depends on artist)
featured = await db.get_featured_cards_for_artist(artist.name, limit=4)
```

**Total time:** ~200-500ms (5 queries)
**Issue:** Dashboard shows "Loading..." → sections appear gradually → user can interact before ready

### After: 2 Database Queries

```python
# 2 parallel queries only
artist = await db.get_random_artist_for_spotlight(min_cards=20)
sets = await db.get_latest_sets(limit=3)
```

**Total time:** ~100-200ms (2 queries)
**Improvement:** 60% faster, simpler, no gradual loading
**Benefit:** Dashboard appears fully formed or not at all (no partial states)

---

## Migration Path

### Step 1: Create Simplified Widget (1 hour)

1. Backup current dashboard: `mv dashboard/ dashboard_old/`
2. Create new `dashboard/widget.py` with simplified code (above)
3. Create minimal `dashboard/__init__.py`
4. Update `dashboard/messages.py` with deprecation notices

### Step 2: Update App Integration (30 min)

1. Move A/S/D/R bindings to app level
2. Remove dashboard message handlers (no longer posted)
3. Keep `_hide_dashboard()` logic (still works)
4. Test keyboard shortcuts work from anywhere

### Step 3: Update CSS (15 min)

1. Add new dashboard CSS classes (simplified)
2. Remove old classes (featured-card-tile, sets-list, etc.)
3. Test visual styling

### Step 4: Test & Verify (1 hour)

1. ✅ Dashboard loads without errors
2. ✅ A/S/D/R shortcuts work
3. ✅ No focus traps (can't get stuck)
4. ✅ Typing in search hides dashboard
5. ✅ No "one click breaks it" issues

**Total effort:** ~3 hours

---

## Success Criteria

After redesign, dashboard must:

1. ✅ **Never crash** - No IndexError, no race conditions, no exceptions
2. ✅ **No focus traps** - Can't get stuck (nothing to focus on)
3. ✅ **Shortcuts work reliably** - A/S/D/R work from anywhere, always
4. ✅ **Clear mental model** - "Read the dashboard, then search or press A/S/D/R"
5. ✅ **Fast loading** - Appears in <200ms (2 queries, not 5)
6. ✅ **Keep artist spotlight** - User's favorite feature (simplified but present)
7. ✅ **Search remains primary** - Typing immediately hides dashboard and searches

**No "one click breaks it" issues** = Success

---

## What the User Will Experience

### Before (Current - Broken)

```
Opens app → dashboard loads gradually
→ User sees artist spotlight with [1] [2] [3] [4] cards
→ User presses "1" → Nothing happens (loading not done)
→ User tabs to explore → Gets stuck in FeaturedCard #2
→ User presses Tab 5 more times trying to escape
→ User frustrated: "It's broken"
```

### After (Redesigned - Stable)

```
Opens app → dashboard appears instantly (or shows skeleton)
→ User sees artist spotlight: "Rebecca Guay"
→ User thinks "Cool artist!" and types: artist rebecca guay
→ Dashboard hides, artist portfolio appears
→ User explores portfolio, finds cards they love
OR
→ User presses "A" → Dashboard hides, artist browser appears
→ User explores 2,245 artists
OR
→ User just types: lightning bolt
→ Dashboard hides, search results appear
→ Everything works as expected
```

**Result:** Clear, predictable, stable experience.

---

## Risk Assessment

### Risks

1. **User might miss artist spotlight** - If dashboard is too static, users may overlook it
   - **Mitigation:** Use prominent styling (gold colors, large text), auto-show on launch

2. **Loss of "featured cards" grid** - Users can't quick-view cards anymore
   - **Mitigation:** Artist portfolio is just one command away (`:artist name`)

3. **Fewer interactive elements** - Dashboard may feel "less impressive"
   - **Mitigation:** Stability > flashiness. Users prefer working features.

### Benefits Far Outweigh Risks

✅ **No crashes** - Massive UX improvement
✅ **No confusion** - Clear mental model
✅ **Faster loading** - Better first impression
✅ **Easier to maintain** - 75% less code
✅ **Easier to extend** - Simple foundation for future features

---

## Future Enhancements (Post-V2)

Once the stable foundation is in place, we can add:

**Phase 3: Optional Enhancements**
- Click-to-search on artist name (on_click handler → search)
- Daily rotation of artist spotlight (same artist all day)
- Recent activity section (last 3 searches)
- Favorite artists (if user preferences exist)

**Phase 4: Personalization**
- Learn from user behavior (artist explorer vs deck builder)
- Show relevant content based on history
- Recommendations ("You might like...")

**But first:** Get V2 stable and shipped.

---

## Conclusion

### The Problem

Current dashboard is **over-engineered** with:
- 7+ focusable widgets → focus traps
- 17+ key binding conflicts → unpredictable behavior
- 5 database queries → slow loading + race conditions
- 4 interaction paradigms → cognitive overload

**Result:** "One click and it's broken"

### The Solution

Simplified read-only dashboard with:
- 0 focusable widgets → no focus traps
- 0 key binding conflicts → predictable behavior
- 2 database queries → fast loading
- 1 interaction paradigm → clear mental model

**Result:** Stable, fast, predictable experience

### Recommendation

**Implement this V2 design immediately.** It's simpler, more stable, and still keeps the artist spotlight the user loves.

**Estimated effort:** 3 hours
**Risk:** Very low (removing complexity = fewer bugs)
**Impact:** High (transforms unusable feature into stable experience)

---

## Appendix A: Code Diff Summary

### Files to Delete

```bash
rm dashboard/artist_spotlight.py
rm dashboard/new_sets.py
rm dashboard/random_discoveries.py
rm dashboard/quick_actions.py
```

### Files to Modify

**dashboard/widget.py** - Simplified to 150 lines (from 250 lines)
- Remove all `can_focus=True`
- Remove all `BINDINGS`
- Remove all message posting
- Keep only: load, update text, clear

**dashboard/messages.py** - Deprecated (keep for compatibility)
- Add deprecation notices
- No longer posted by dashboard

**dashboard/__init__.py** - Minimal exports
- Export only: `Dashboard` widget

**app.py** - Move bindings to app level
- Add A/S/D/R bindings at app level
- Remove dashboard message handlers
- Keep `_hide_dashboard()` logic

**styles.py** - Simplify CSS
- Remove interactive widget styles
- Add static text styles
- Keep visual styling (colors, borders)

### Files to Create

None! Simplified design needs less code, not more.

---

## Appendix B: ASCII Wireframe (Full)

```
┌─ MTG SPELLBOOK ─────────────────────────────────────────────────────────────┐
│ ✦ Magic: The Gathering Card Database                                       │
│ ✦ 33,429 cards · 842 sets                          [?] Help    [Ctrl+Q]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Welcome! Type to search for cards, or use quick actions below.            │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  ✨ ARTIST SPOTLIGHT                                                       │
│                                                                             │
│     Rebecca Guay                                                            │
│                                                                             │
│     Known for ethereal watercolor artwork with fairy tale aesthetics.      │
│     Signature style: delicate linework, muted color palettes, dreamy       │
│     compositions inspired by Art Nouveau and fairy tales.                  │
│                                                                             │
│     47 cards illustrated · 18 sets · 1997-2019                             │
│                                                                             │
│     Type ':artist rebecca guay' to view full portfolio                     │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  📚 RECENT SETS                                                             │
│                                                                             │
│     Murders at Karlov Manor (MKM)                                          │
│     Feb 9, 2024 · 286 cards · Expansion                                    │
│     Return to Ravnica for a murder mystery                                 │
│                                                                             │
│     Outlaws Thunder Junction (OTJ)                                          │
│     Apr 19, 2024 · 276 cards · Expansion                                   │
│     Wild West themed plane with outlaws and gunslingers                    │
│                                                                             │
│     Modern Horizons 3 (MH3)                                                │
│     Jun 14, 2024 · 303 cards · Masters                                     │
│     Powerful reprints and new cards for Modern format                      │
│                                                                             │
│     Type ':sets' to browse all sets                                        │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  🚀 QUICK ACTIONS                                                           │
│                                                                             │
│     [A] Browse All Artists (2,245)                                          │
│     [S] Browse All Sets (842)                                               │
│     [D] My Decks                                                            │
│     [R] Random Card Discovery                                               │
│                                                                             │
│     Just start typing to search for cards by name, type, or text.          │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  ⚡  _                                                                      │
│     Card name, 'search t:creature c:red', or 'help'                        │
└─────────────────────────────────────────────────────────────────────────────┘
  [A] Artists · [S] Sets · [D] Decks · [R] Random · Type to search
```

**This is what stability looks like: Simple, clear, reliable.**
