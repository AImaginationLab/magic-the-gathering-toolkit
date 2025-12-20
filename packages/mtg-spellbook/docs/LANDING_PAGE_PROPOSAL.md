# MTG Spellbook Landing Page & Initial Experience Design
## Proposal for First-Run and Dashboard Experience

**Version:** 1.0
**Date:** 2025-12-14
**Status:** Design Proposal

---

## Executive Summary

This document proposes a comprehensive landing page and initial experience for MTG Spellbook that transforms the app from a blank search interface into a discovery-driven, artist-centric dashboard. The design leverages our strongest assets (2,245 artists, 842 sets, 33k+ cards) and the user's stated preference: **"artists are my favorite part of MTG."**

### Design Philosophy

1. **Discovery over blank slates** - Users see interesting content immediately
2. **Artist-first experience** - Leverage the user's passion for MTG artwork
3. **Progressive engagement** - Multiple entry points for different user goals
4. **Terminal-native design** - Fast, keyboard-driven, visually rich
5. **Smart defaults** - Learn from user behavior to personalize the experience

---

## Table of Contents

1. [Research Findings](#research-findings)
2. [User Goals & Scenarios](#user-goals--scenarios)
3. [Design Options](#design-options)
4. [Recommended Approach](#recommended-approach)
5. [Wireframes](#wireframes)
6. [Keyboard Navigation](#keyboard-navigation)
7. [Implementation Phases](#implementation-phases)
8. [Success Metrics](#success-metrics)
9. [Technical Considerations](#technical-considerations)

---

## Research Findings

### TUI Dashboard Best Practices (2025)

Based on research from modern TUI design systems, dashboard design principles, and terminal application onboarding:

#### Key Insights from Web Search

**1. Dashboard Design Principles** ([Medium - Dashboard UI/UX 2025](https://medium.com/@allclonescript/20-best-dashboard-ui-ux-design-principles-you-need-in-2025-30b661f2f795))
- Users expect **real-time interactivity and personalization** as standard features, not nice-to-haves
- Great dashboard design starts with **knowing your audience's intent** - why they visit the dashboard
- **Microinteractions** (hover states, tooltips, loading animations) make dashboards feel polished
- Dashboards should be treated as **living products that grow with users**, not one-time designs

**2. TUI-Specific Patterns** ([Polimetro - What is a TUI](https://www.polimetro.com/en/what-is-a-tui/))
- TUIs allow users to **perform complex tasks quickly** once they master shortcuts
- Design clear menus, logical shortcuts, and **informative messages** for usability
- TUIs require **less processing power** than GUIs, making them ideal for resource-constrained environments
- **Don't forget screen cleaning and error checking** - messy TUIs are frustrating

**3. Textual Framework Capabilities** ([Real Python - Textual](https://realpython.com/python-textual/))
- Textual offers **rich widget library** (buttons, inputs, checkboxes, tables, trees)
- **CSS-like styling** for customizing appearance and behavior
- **Reactive attributes** enable dynamic interfaces that respond to state changes
- **Flexible layout management** with docking and grid systems for complex interfaces

**4. Onboarding Best Practices** ([UserGuiding - Onboarding Screens](https://userguiding.com/blog/onboarding-screens))
- Best onboarding screens in 2025 are **clean, interactive, and personalization-focused**
- Use **progress indicators and contextual tooltips** to guide users without overwhelming
- Welcome screens should be **simple, visually appealing, and value-focused**
- Allow users to **skip or customize the experience** - don't force long tutorials

**5. Notable TUI Examples** ([GitHub - Awesome TUIs](https://github.com/rothgar/awesome-tuis))
- **WTF** - "Personal information dashboard for your terminal" - shows widgets for different data sources
- **GoAccess** - Real-time web log analyzer with rich terminal dashboard
- **Ratatui** (Rust) - Provides built-in widgets for dashboards: blocks, tables, gauges, charts, sparklines

### Competitive Analysis: Moxfield & Archidekt Landing Pages

**Moxfield Landing Experience:**
- Jumps straight to **deck list** (assumes returning users)
- **Search bar** prominently featured at top
- **Featured decks** or recent activity for discovery
- User must know what they want to do

**Archidekt Landing Experience:**
- **Visual deck builder** as centerpiece (beautiful card images)
- **Collaboration features** highlighted (real-time editing)
- **Custom categories** for organizing cards
- Strong focus on **collection tracking**

**Key Takeaway:** Web deck builders assume you already have a goal (build/edit deck). TUI should be more **exploratory and educational** - show users interesting content they didn't know they wanted.

### Discovery vs Task-Oriented Workflows

From [Pencil & Paper - Dashboard UX Patterns](https://www.pencilandpaper.io/articles/ux-pattern-analysis-data-dashboards):

**Discovery-focused dashboards:**
- Give users **flexible means to find new insights**
- Focus on **exploring data and drilling into details**
- Highly interactive with drag-and-drop manipulation
- **Change often based on user needs**

**Task-oriented dashboards:**
- Organize interfaces **by tasks users must complete**
- Place features **right where they apply** (not grouped by category)
- **Streamline user journeys** and eliminate unnecessary steps
- Focus on **getting stuff done efficiently**

**Our Approach:** **Hybrid model** - Discovery-first landing page, then task-oriented workflows once user engages.

---

## User Goals & Scenarios

### Scenario 1: First-Time User (Discovery Mode)

**User:** Alex, new MTG Spellbook user, loves MTG art
**Goal:** Explore the app without a specific card/deck in mind

**Current Experience (Blank Search):**
```
Opens app → sees empty search box → thinks "What should I search for?"
→ Searches random card → browses a bit → quits
```

**Proposed Experience (Dashboard):**
```
Opens app → sees "Artist Spotlight: Rebecca Guay" with featured artwork
→ Clicks to view gallery → discovers Path to Exile version they didn't know existed
→ Explores similar artists → finds 3 new favorite artists
→ Saves artists to favorites → returns daily to see new spotlights
```

**Outcome:** User engages for 15+ minutes vs 2 minutes. Discovers features organically.

### Scenario 2: Returning User with Clear Goal (Task Mode)

**User:** Taylor, building a Modern Burn deck
**Goal:** Search for specific cards quickly

**Current Experience:**
```
Opens app → types :card lightning bolt → views card → done
```

**Proposed Experience (Dashboard with Quick Actions):**
```
Opens app → sees recent searches ("Lightning Bolt", "Eidolon")
→ Clicks "Lightning Bolt" from recent → views card → done
OR
→ Presses Ctrl+F to skip dashboard and jump to search → same workflow as before
```

**Outcome:** Dashboard doesn't slow down power users (Ctrl+F escape hatch), but offers shortcuts for common tasks.

### Scenario 3: Casual Browser (Inspiration Mode)

**User:** Morgan, collection manager, wants inspiration
**Goal:** Find interesting cards to build around

**Current Experience:**
```
Opens app → not sure what to do → maybe searches "dragon" → browses → quits
```

**Proposed Experience (Dashboard with "Featured Content"):**
```
Opens app → sees "New Set: Murders at Karlov Manor (24 cards)"
→ Browses set preview → finds Judith, Carnage Connoisseur
→ Clicks "Find Synergies" → discovers aristocrats theme
→ Starts building deck around card they just discovered
```

**Outcome:** App becomes daily habit (check for new sets, new artists, random cards).

---

## Design Options

### Option 1: Minimalist Dashboard (Low Friction)

**Philosophy:** Show minimal content, get out of the way fast.

**Layout:**
```
┌─ MTG SPELLBOOK ────────────────────────────────────────────────┐
│                                                                 │
│            Welcome to MTG Spellbook                             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ⚡ Search cards, artists, or sets                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Quick Actions:                                                │
│  [C] Card Search    [A] Artists    [S] Sets    [D] Decks      │
│                                                                 │
│  Recent:                                                        │
│  > Lightning Bolt (searched 2 min ago)                         │
│    Rebecca Guay (viewed 1 hour ago)                            │
│    Streets of New Capenna (viewed yesterday)                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Pros:**
- Fast to load (no database queries)
- Doesn't overwhelm new users
- Clear call-to-action (search bar)

**Cons:**
- Boring - doesn't showcase app capabilities
- Missed opportunity to engage users
- Doesn't leverage our best assets (artists, artwork)

**Verdict:** ❌ Too conservative. Users can get this anywhere.

---

### Option 2: Rich Dashboard (Discovery-First)

**Philosophy:** Show users interesting content immediately. Make discovery the default.

**Layout:**
```
┌─ MTG SPELLBOOK ─────────────────────────────────────────────────────────────────┐
│ ⚡ :search query   [Ctrl+A] Artists · [Ctrl+S] Sets · [Ctrl+D] Decks          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ ✨ ARTIST SPOTLIGHT ────────────────────────────────────────────────────────── │
│                                                                                 │
│  🎨 Rebecca Guay                                    [Enter] Explore · [Space] Next │
│                                                                                 │
│  Known for ethereal watercolor artwork and fairy tale aesthetics.              │
│  47 cards illustrated across 18 sets (1997-2019)                               │
│                                                                                 │
│  Featured Cards:  [◆] Path to Exile  [◆] Enchantress's Presence  [◆] Rancor  │
│                   UMA · Uncommon      ONS · Rare                  ULG · Common │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ 📚 NEW SETS ──────────────────   🎲 RANDOM DISCOVERIES ──────────────────────  │
│                                                                                 │
│  [MKM] Murders at Karlov Manor     > Teferi, Time Raveler                     │
│        Feb 9, 2024 · 24 cards        "One of MTG's most powerful planeswalkers │
│        [Enter] Explore set            appearing in 4 different sets"           │
│                                      [Enter] View Card                         │
│  [OTJ] Outlaws Thunder Junction                                                │
│        Apr 19, 2024 · 28 cards      > Cabal Coffers                            │
│        [Enter] Explore set            "Legendary land that doubles black mana" │
│                                      [Enter] View Card                         │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│ [C] Card Search · [A] Artists · [S] Sets · [D] Decks · [?] Help               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Pros:**
- Showcases app's best features (artists!)
- Immediate value - users see interesting content
- Multiple entry points (artist, sets, random cards)
- Encourages daily usage ("What's the artist spotlight today?")

**Cons:**
- Slower initial load (requires database queries)
- May overwhelm users who just want to search
- Need "skip to search" escape hatch

**Verdict:** ✅ Strong contender. Balances discovery with functionality.

---

### Option 3: Personalized Dashboard (Adaptive)

**Philosophy:** Learn from user behavior and show relevant content.

**Layout (First-Time User):**
```
┌─ MTG SPELLBOOK ─────────────────────────────────────────────────────────────────┐
│ Welcome! Let's get you started.                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ What brings you here today?                                                    │
│                                                                                 │
│  [1] 🔍 Search for a specific card                                             │
│  [2] 🎨 Discover artists and artwork                                           │
│  [3] 📚 Explore Magic sets                                                     │
│  [4] 🃏 Build or manage decks                                                  │
│                                                                                 │
│  Or just start typing to search...                                             │
│  ⚡ _                                                                           │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Layout (Returning User - Artist Explorer):**
```
┌─ MTG SPELLBOOK ─────────────────────────────────────────────────────────────────┐
│ ⚡ Search   [Ctrl+A] Artists · [Ctrl+S] Sets · [Ctrl+D] Decks                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ 🎨 YOUR FAVORITE ARTISTS ────────────────────────────────────────────────────  │
│  > Rebecca Guay (15 cards viewed) · John Avon (8) · Terese Nielsen (12)       │
│                                                                                 │
│ ✨ DISCOVER MORE ARTISTS ────────────────────────────────────────────────────  │
│  Raymond Swanland · 189 cards · Known for dramatic sci-fi/fantasy scenes      │
│  [Enter] Explore                                                               │
│                                                                                 │
│ 📚 RECENTLY VIEWED SETS ──────────────────────────────────────────────────────  │
│  [NEO] Kamigawa: Neon Dynasty · [SNC] Streets of New Capenna                  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Layout (Returning User - Deck Builder):**
```
┌─ MTG SPELLBOOK ─────────────────────────────────────────────────────────────────┐
│ ⚡ Search   [Ctrl+A] Artists · [Ctrl+S] Sets · [Ctrl+D] Decks                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ 🃏 YOUR DECKS ───────────────────────────────────────────────────────────────  │
│  > Mono-Red Burn (Modern) · 60/60 · Last edited 2 hours ago                   │
│  > Atraxa Superfriends (Commander) · 100/100 · Last edited yesterday          │
│  [Ctrl+N] New Deck                                                             │
│                                                                                 │
│ 💡 DECK IDEAS ───────────────────────────────────────────────────────────────  │
│  Based on your recent searches (Lightning Bolt, Eidolon):                      │
│  > Mono-Red Prowess (Modern) · Import popular archetype                       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Pros:**
- Maximally relevant to each user
- Grows with user behavior
- Reduces friction for common workflows

**Cons:**
- Most complex to implement
- Requires user tracking/preferences
- Empty state for new users
- May feel "creepy" if too personalized

**Verdict:** 🔶 Best long-term, but Phase 2+. Start simpler.

---

## Recommended Approach

### Phase 1: Rich Discovery Dashboard (Option 2)

Start with **Option 2** (Rich Dashboard) as the foundation, with these key elements:

1. **Artist Spotlight** - Hero section showcasing a random artist daily
2. **New Sets** - Latest 2-3 sets for discovery
3. **Random Discoveries** - 2-3 interesting cards to browse
4. **Quick Actions** - Fast keyboard shortcuts to bypass dashboard
5. **Recent Activity** - Last 3-5 searched cards/artists (if any)

### Why This Approach?

**1. Aligns with User's Passion**
- User said "artists are my favorite part" → Artist Spotlight as hero section
- Showcases our strongest asset (2,245 artists, beautiful artwork)
- Creates daily habit ("What artist is featured today?")

**2. Balances Discovery and Task Workflows**
- Discovery: Artist spotlight, new sets, random cards
- Task: Search bar, quick action shortcuts (Ctrl+F, Ctrl+A)
- Progressive: Shows features without forcing tutorials

**3. Terminal-Native Design**
- Keyboard shortcuts for all sections (numbers 1-4, Ctrl+X)
- Fast loading (pre-cached random content)
- Visually rich but not overwhelming (ASCII art, colors)

**4. Natural Progression Path**
- Phase 1: Static dashboard (random artist, latest sets)
- Phase 2: Personalized content (favorite artists, recent decks)
- Phase 3: AI recommendations (deck ideas, similar artists)

---

## Wireframes

### Wireframe 1: Full Dashboard (Default Landing Page)

```
┌─ MTG SPELLBOOK ──────────────────────────────────────────────────────────────────────┐
│ Database: 33,429 cards · 842 sets · 2,245 artists          [?] Help  [Ctrl+Q] Quit │
├──────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│ ⚡ :search for cards, artists, or sets                                              │
│ ┌──────────────────────────────────────────────────────────────────────────────┐   │
│ │ _                                                                             │   │
│ └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│ ═══════════════════════════════════════════════════════════════════════════════════ │
│                                                                                      │
│ ✨ ARTIST SPOTLIGHT ─────────────────────────────────────────────────────────────── │
│                                                                                      │
│   🎨 Rebecca Guay                                [Enter] View Portfolio · [→] Next │
│                                                                                      │
│   Known for ethereal watercolor artwork with fairy tale aesthetics.                │
│   Career: 47 cards across 18 sets (1997-2019)                                      │
│                                                                                      │
│   Featured Cards:                                                                   │
│   ┌──────────────────┬──────────────────┬──────────────────┬──────────────────┐    │
│   │ [◆] Path to      │ [◆] Enchantress's│ [◆] Dark Ritual  │ [◆] Rancor       │    │
│   │     Exile        │     Presence     │                  │                  │    │
│   │ UMA · Uncommon   │ ONS · Rare       │ JUD · Common     │ ULG · Common     │    │
│   └──────────────────┴──────────────────┴──────────────────┴──────────────────┘    │
│                                                                                      │
│   [1] Path to Exile  [2] Enchantress's Presence  [3] Dark Ritual  [4] Rancor       │
│                                                                                      │
│ ═══════════════════════════════════════════════════════════════════════════════════ │
│                                                                                      │
│ 📚 NEW SETS ───────────────────────  🎲 RANDOM DISCOVERIES ───────────────────────  │
│                                                                                      │
│  [MKM] Murders at Karlov Manor      Card of the Day:                               │
│         Feb 9, 2024                  ┌────────────────────────────────────┐         │
│         24 cards · Expansion         │ Teferi, Time Raveler    {1}{W}{U} │         │
│         [5] Explore set             │ Legendary Planeswalker - Teferi    │         │
│                                      │                                    │         │
│  [OTJ] Outlaws Thunder Junction     │ "One of Modern's most powerful     │         │
│         Apr 19, 2024                 │  planeswalkers, appearing in 4     │         │
│         28 cards · Expansion         │  different printings."             │         │
│         [6] Explore set             │                                    │         │
│                                      │ [7] View Full Card                 │         │
│  [MH3] Modern Horizons 3            └────────────────────────────────────┘         │
│         Jun 14, 2024                                                                 │
│         42 cards · Masters           Set of the Week:                               │
│         [8] Explore set             [NEO] Kamigawa: Neon Dynasty                   │
│                                      "Cyberpunk meets feudal Japan"                 │
│                                      [9] Explore set                                 │
│                                                                                      │
│ ═══════════════════════════════════════════════════════════════════════════════════ │
│                                                                                      │
│ 🚀 QUICK ACTIONS ──────────────────────────────────────────────────────────────────  │
│                                                                                      │
│  [A] Browse Artists (2,245)  [S] Browse Sets (842)  [D] My Decks  [R] Random Card  │
│                                                                                      │
│  Recent Activity:                                                                   │
│  > Lightning Bolt (2 min ago) · Rebecca Guay (1 hour ago) · Streets of New Capenna │
│                                                                                      │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ [1-9] Quick Jump · [A/S/D/R] Actions · [Enter] Select · [?] Help · [Ctrl+Q] Quit  │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe 2: Compact Dashboard (Small Terminal - 80x24)

```
┌─ MTG SPELLBOOK ───────────────────────────────────────────────────────┐
│ ⚡ :search _                                              [?] Help    │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ ✨ ARTIST SPOTLIGHT                          [Enter] View · [→] Next│
│   🎨 Rebecca Guay · 47 cards · Ethereal watercolor artwork           │
│   Featured: Path to Exile (UMA) · Enchantress's Presence (ONS)       │
│                                                                       │
│ ─────────────────────────────────────────────────────────────────────│
│                                                                       │
│ 📚 NEW SETS            🎲 RANDOM              🚀 QUICK ACTIONS        │
│  [MKM] Murders (24)    Teferi, Time Raveler   [A] Artists           │
│  [OTJ] Outlaws (28)    "Modern staple"         [S] Sets             │
│  [MH3] Horizons (42)   [View Card]            [D] Decks             │
│                                                [R] Random            │
│                                                                       │
│ Recent: Lightning Bolt · Rebecca Guay · Streets of New Capenna       │
│                                                                       │
├───────────────────────────────────────────────────────────────────────┤
│ [1-9] Jump · [A/S/D/R] Actions · [?] Help · [Ctrl+Q] Quit           │
└───────────────────────────────────────────────────────────────────────┘
```

### Wireframe 3: First-Time User (Empty Recent Activity)

```
┌─ MTG SPELLBOOK ──────────────────────────────────────────────────────────────────────┐
│ Welcome to MTG Spellbook!                               [?] Help  [Ctrl+Q] Quit     │
├──────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│ ⚡ Start typing to search for cards, artists, or sets:                              │
│ ┌──────────────────────────────────────────────────────────────────────────────┐   │
│ │ _                                                                             │   │
│ └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│ Or discover something new:                                                          │
│                                                                                      │
│ ═══════════════════════════════════════════════════════════════════════════════════ │
│                                                                                      │
│ ✨ ARTIST SPOTLIGHT ─────────────────────────────────────────────────────────────── │
│                                                                                      │
│   🎨 John Avon                                  [Enter] View Portfolio · [→] Next  │
│                                                                                      │
│   Known for stunning photorealistic landscapes and iconic basic lands.             │
│   Career: 342 cards across 87 sets (1996-2024)                                     │
│                                                                                      │
│   Featured Cards:                                                                   │
│   ┌──────────────────┬──────────────────┬──────────────────┬──────────────────┐    │
│   │ [◆] Wrath of God │ [◆] Island (UNH) │ [◆] Flooded      │ [◆] Plains (ZEN) │    │
│   │ 10E · Rare       │ Basic Land       │     Strand       │ Basic Land       │    │
│   │                  │                  │ EXP · Rare       │                  │    │
│   └──────────────────┴──────────────────┴──────────────────┴──────────────────┘    │
│                                                                                      │
│ ═══════════════════════════════════════════════════════════════════════════════════ │
│                                                                                      │
│ 💡 NEW USER TIPS ──────────────────────────────────────────────────────────────────  │
│                                                                                      │
│  • Press [A] to browse all 2,245 artists                                           │
│  • Press [S] to explore 842 Magic sets                                             │
│  • Press [R] for a random card discovery                                           │
│  • Type :card name to search for specific cards                                    │
│  • Press [?] anytime for help                                                      │
│                                                                                      │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ [Enter] Start Exploring · [?] Help · [Ctrl+Q] Quit                                 │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe 4: Power User Mode (Skip Dashboard)

For users who want to bypass the dashboard and jump straight to search:

**Config Setting:**
```toml
[spellbook]
landing_page = "dashboard"  # Options: "dashboard", "search", "last_view"
show_tips = true
artist_spotlight = true
```

**Keyboard Shortcut:**
- `Ctrl+F` from dashboard → Jump directly to search (focus search bar)
- `Esc` from any view → Return to dashboard
- `:` → Enter command mode (bypass dashboard entirely)

---

## Keyboard Navigation

### Dashboard Shortcuts

| Key | Action | Description |
|-----|--------|-------------|
| `1-9` | Quick jump | Jump to numbered item (Featured cards, sets) |
| `A` | Artists | Browse all artists |
| `S` | Sets | Browse all sets |
| `D` | Decks | View my decks |
| `R` | Random | Random card discovery |
| `Enter` | View spotlight | View full artist portfolio |
| `→` / `Space` | Next spotlight | Cycle to next artist |
| `←` | Previous spotlight | Cycle to previous artist |
| `Ctrl+F` | Focus search | Jump to search bar |
| `:` | Command mode | Enter command (bypass dashboard) |
| `?` | Help | Show keyboard shortcuts |
| `Esc` | Clear/Back | Clear search or return to dashboard |

### Search Bar (From Dashboard)

| Key | Action | Description |
|-----|--------|-------------|
| Type text | Search | Live search as you type |
| `Enter` | Execute search | Show search results |
| `↓` | Navigate results | Move focus to results list |
| `Esc` | Clear | Clear search, return to dashboard |

### Featured Content Navigation

**Artist Spotlight:**
- `Enter` → View full artist portfolio
- `1-4` → Quick view featured card (number keys)
- `→` / `Space` → Next artist
- `Tab` → Focus next section

**New Sets:**
- `5-8` → Quick view set (number keys)
- `Enter` → Explore set details
- `↓` → Navigate set list

**Random Discoveries:**
- `9` → View card of the day
- `0` → View set of the week
- `r` → Shuffle (new random content)

### First-Time User Tips

**For new users, show contextual hints:**
- After 5 seconds of inactivity: "💡 Press [A] to browse artists"
- After spotlight viewed: "💡 Press [→] for another artist"
- After search typed: "💡 Press [↓] to navigate results"

---

## Implementation Phases

### Phase 1: Static Dashboard (Week 1)

**Goal:** Display static dashboard with random content on app launch.

#### Tasks:
1. **Dashboard Widget** (200 lines)
   - Main container layout (3 sections: Spotlight, New Sets, Random)
   - Static artist spotlight (random from DB)
   - Latest 3 sets (by release date)
   - Random card of the day

2. **Database Queries** (50 lines)
   - `get_random_artist_with_cards()` → Returns artist + 4 sample cards
   - `get_latest_sets(limit=3)` → Returns newest sets
   - `get_random_card()` → Returns random interesting card
   - Add to `mtg_core/tools/`

3. **App Integration** (50 lines)
   - Show dashboard on launch
   - Add keyboard shortcuts (1-9, A/S/D/R)
   - Add search bar with live search
   - Add "skip dashboard" config option

**Testing:**
- Load dashboard in < 200ms
- Verify random artist changes each launch
- Test all keyboard shortcuts
- Test on 80x24 and 120x40 terminals

**Deliverable:** Users see rich dashboard on every launch.

---

### Phase 2: Recent Activity & Favorites (Week 2)

**Goal:** Track user activity and show personalized content.

#### Tasks:
1. **Activity Tracking** (100 lines)
   - Track last 10 viewed cards
   - Track last 10 viewed artists
   - Track last 10 viewed sets
   - Store in user preferences DB

2. **Recent Activity Section** (50 lines)
   - Show recent cards/artists/sets at bottom of dashboard
   - Click to re-open
   - Clear recent activity button

3. **Favorite Artists** (100 lines)
   - "Star" button on artist portfolio
   - Save to user preferences
   - Show favorite artists on dashboard (if any)

**Testing:**
- Verify recent activity persists across sessions
- Test with 0, 5, and 50 recent items
- Test favorite artists list

**Deliverable:** Dashboard adapts to user behavior.

---

### Phase 3: Dynamic Content & Recommendations (Week 3)

**Goal:** Smarter recommendations based on usage patterns.

#### Tasks:
1. **Smart Recommendations** (150 lines)
   - If user searches lots of red cards → Feature red-focused artists
   - If user builds Commander decks → Feature Commander staples
   - If user explores sets → Feature latest Standard sets

2. **Deck Ideas Section** (100 lines)
   - Based on recent searches, suggest deck archetypes
   - "You searched Eidolon + Lightning Bolt → Try Mono-Red Burn"
   - Link to import popular decklists (Phase 5+)

3. **Artist of the Day** (50 lines)
   - Rotate featured artist daily (not random)
   - Cache artist selection in config
   - Reset at midnight

**Testing:**
- Verify artist changes daily
- Test recommendations with different user profiles
- Ensure no duplicate recommendations

**Deliverable:** Intelligent dashboard that learns user preferences.

---

### Phase 4: Onboarding Flow (Week 4)

**Goal:** Guide first-time users through features.

#### Tasks:
1. **First-Run Detection** (50 lines)
   - Detect first app launch
   - Show welcome message
   - Offer quick tour (optional)

2. **Welcome Modal** (100 lines)
   - Welcome screen with app overview
   - "What brings you here?" options
   - Skip button (don't force onboarding)

3. **Contextual Tips** (100 lines)
   - Show tips based on user inactivity
   - Dismiss tips permanently (per-tip basis)
   - "Did you know?" random facts

**Testing:**
- Test first-run experience
- Verify tips don't annoy power users
- Test skip/dismiss functionality

**Deliverable:** New users feel guided, not overwhelmed.

---

## Success Metrics

### Engagement Metrics

**1. Dashboard Engagement Rate**
- **Target:** 70% of sessions interact with dashboard content
- **Measure:** % of app launches where user clicks featured content (not just searches)

**2. Artist Discovery Rate**
- **Target:** 40% of users explore at least 1 artist from spotlight
- **Measure:** % of users who click "View Portfolio" from spotlight

**3. Time to First Action**
- **Target:** < 10 seconds from app launch to user action
- **Measure:** Average time from dashboard shown to first click/search

**4. Feature Discovery**
- **Target:** 60% of users discover artist/set features via dashboard
- **Measure:** % of users who use artist/set features without manual search

### Usability Metrics

**5. Dashboard Load Time**
- **Target:** < 200ms to render dashboard
- **Measure:** Time from app launch to dashboard fully rendered

**6. Skip Dashboard Usage**
- **Target:** < 15% of power users skip dashboard (config setting)
- **Measure:** % of users with `landing_page = "search"` config

**7. Search Bar Usage**
- **Target:** 50% of searches start from dashboard search bar
- **Measure:** % of searches typed in dashboard vs command mode

### Content Metrics

**8. Random Content Freshness**
- **Target:** Artist spotlight changes daily
- **Measure:** Verify artist selection rotates every 24 hours

**9. Set Timeliness**
- **Target:** New sets appear within 1 week of release
- **Measure:** Days between set release date and appearance on dashboard

**10. User Satisfaction**
- **Target:** > 4.0 / 5 stars for dashboard feature
- **Measure:** Post-session survey (optional opt-in)

---

## Technical Considerations

### Performance Optimization

**1. Pre-Caching**
- Cache artist spotlight selection for 24 hours
- Pre-load featured card images in background
- Cache latest sets list (updates weekly)

**2. Lazy Loading**
- Load dashboard sections progressively:
  1. Search bar (instant)
  2. Artist spotlight (50ms)
  3. New sets (100ms)
  4. Random content (150ms)
- User can start typing search while content loads

**3. Database Queries**
```sql
-- Random artist with cards (optimized)
SELECT a.name, a.card_count, c.name, c.setCode, c.rarity
FROM (
  SELECT artist AS name, COUNT(*) as card_count
  FROM cards
  WHERE artist IS NOT NULL
  GROUP BY artist
  ORDER BY RANDOM()
  LIMIT 1
) a
JOIN cards c ON c.artist = a.name
ORDER BY RANDOM()
LIMIT 4;

-- Latest sets
SELECT * FROM sets
ORDER BY releaseDate DESC
LIMIT 3;

-- Random interesting card (not basic land)
SELECT * FROM cards
WHERE type NOT LIKE '%Basic%'
  AND rarity IN ('rare', 'mythic')
ORDER BY RANDOM()
LIMIT 1;
```

**4. Memory Management**
- Limit recent activity to 10 items
- Lazy-load artist portfolio (don't load all 47 cards for Rebecca Guay)
- Clear image cache after 100 MB

### Responsive Layout

**Terminal Size Breakpoints:**

**Tiny (80x24):**
- Compact dashboard (see Wireframe 2)
- Stack sections vertically
- Fewer featured cards (2 instead of 4)

**Small (100x30):**
- 2-column layout (Sets + Random)
- Full artist spotlight

**Medium (120x40):**
- 3-column layout (default)
- All sections visible

**Large (150x50+):**
- Same as medium, but more whitespace
- Larger featured card previews

**Implementation:**
```python
from textual.reactive import reactive

class Dashboard(Vertical):
    terminal_width = reactive(120)

    def watch_terminal_width(self, width: int) -> None:
        if width < 90:
            self.layout = "compact"
        elif width < 120:
            self.layout = "small"
        else:
            self.layout = "default"
```

### Configuration Options

**User Preferences (`.config/mtg-spellbook/config.toml`):**

```toml
[spellbook.dashboard]
# Landing page: "dashboard", "search", "last_view"
landing_page = "dashboard"

# Show artist spotlight
artist_spotlight = true

# Show new sets section
new_sets = true

# Show random discoveries
random_content = true

# Show recent activity
recent_activity = true

# Show tips for new users
show_tips = true

# Maximum recent items to track
max_recent_items = 10

# Artist spotlight rotation (hours)
spotlight_rotation_hours = 24
```

**Escape Hatches for Power Users:**
- `Ctrl+F` → Skip dashboard, jump to search
- `:` → Enter command mode (bypass dashboard)
- `landing_page = "search"` → Never show dashboard

---

## Accessibility Considerations

### Screen Reader Support

**Semantic Labels:**
```python
@property
def aria_label(self) -> str:
    return f"Dashboard with artist spotlight: {self.current_artist}"
```

**Live Regions:**
```python
# Announce when artist spotlight changes
self.notify(f"Artist spotlight now featuring {artist_name}", severity="information")
```

### Keyboard-Only Navigation

- All content accessible via keyboard (no mouse required)
- Tab order follows visual hierarchy (top to bottom)
- Clear focus indicators on all interactive elements
- Skip links: "Press Ctrl+F to skip to search"

### High Contrast Mode

- Respect terminal color scheme
- Use semantic colors (success = green, info = blue)
- Don't rely on color alone (use icons + text)

### Reduced Motion

- Detect `REDUCE_MOTION` environment variable
- Disable transitions if set
- Instant content swaps (no fade effects)

---

## Open Questions & Decisions

### Q1: How often should artist spotlight rotate?

**Options:**
- A) Every app launch (fully random)
- B) Daily (same artist all day)
- C) Weekly (longer spotlight duration)

**Recommendation:** **Option B (Daily)** - Creates daily habit ("What artist is featured today?"), but not so fast that users miss it.

---

### Q2: Should we show user's deck count on dashboard?

**Pros:**
- Quick access to decks
- Shows deck-building progress

**Cons:**
- Not relevant if user doesn't build decks
- Takes screen space

**Recommendation:** **Yes, but only if user has decks.** Hide section if deck_count = 0.

---

### Q3: Should recent activity be public/shareable?

**Pros:**
- Social features (share favorite artists)
- Community building

**Cons:**
- Privacy concerns
- Requires backend server

**Recommendation:** **No for Phase 1-4.** Keep local-only. Revisit for Phase 5+.

---

### Q4: Should dashboard be dismissible/collapsible?

**Pros:**
- Power users can hide it
- More screen space for content

**Cons:**
- Defeats purpose of discovery
- Users may forget it exists

**Recommendation:** **No dismiss, but add Ctrl+F skip shortcut.** Users can configure `landing_page = "search"` if they want.

---

### Q5: What happens when database is offline/missing?

**Fallback Experience:**
```
┌─ MTG SPELLBOOK ─────────────────────────────────────┐
│ ⚠ Database not available                           │
│                                                     │
│ Some features are limited without database access. │
│                                                     │
│ What you can do:                                   │
│  • View cached recent activity                     │
│  • Browse previously viewed cards                  │
│  • Access help documentation                       │
│                                                     │
│ [?] Help  [Ctrl+Q] Quit                           │
└─────────────────────────────────────────────────────┘
```

**Recommendation:** Show degraded dashboard with offline message.

---

## Conclusion

### Summary

This proposal transforms MTG Spellbook from a blank search tool into a **discovery-first, artist-centric dashboard** that:

1. **Showcases our best assets** - 2,245 artists, 842 sets, beautiful artwork
2. **Aligns with user passion** - Artists as hero content (user's stated preference)
3. **Balances workflows** - Discovery for browsers, speed for searchers
4. **Grows with users** - Personalizes based on behavior (Phases 2-3)
5. **Respects power users** - Skip shortcuts (Ctrl+F, config options)

### Recommended Start: Phase 1 MVP

**Immediate next steps (Week 1):**
1. Build `Dashboard` widget with 3 sections (Spotlight, Sets, Random)
2. Add database queries for random content
3. Integrate keyboard shortcuts (1-9, A/S/D/R, Ctrl+F)
4. Test on multiple terminal sizes

**Success criteria:**
- Dashboard loads in < 200ms
- Users engage with featured content (not just search)
- Keyboard navigation feels instant
- New users discover artist/set features organically

---

## Appendix A: Artist Spotlight Rotation Logic

**Daily Rotation Algorithm:**

```python
import hashlib
from datetime import date

def get_artist_of_day(db: MTGDatabase) -> str:
    """Get consistent artist for current day."""
    today = date.today().isoformat()  # "2025-12-14"
    seed = int(hashlib.md5(today.encode()).hexdigest()[:8], 16)

    # Use seed to deterministically pick artist
    artists = db.get_all_artists()  # 2,245 artists
    index = seed % len(artists)
    return artists[index]
```

**Benefits:**
- Same artist shown to all users on same day (creates shared experience)
- Deterministic (no random state issues)
- No database writes needed (purely computed)

---

## Appendix B: Featured Card Selection Criteria

**For Artist Spotlight, prioritize:**
1. **Iconic cards** - High EDHRec rank or tournament play
2. **Visual diversity** - Different colors, card types
3. **Chronological range** - Show early and recent work
4. **Rarity mix** - Mythic/rare/uncommon (not all commons)

**Example query:**
```sql
SELECT * FROM cards
WHERE artist = 'Rebecca Guay'
  AND rarity IN ('rare', 'mythic', 'uncommon')
ORDER BY
  CASE
    WHEN name IN ('Path to Exile', 'Enchantress''s Presence') THEN 1
    ELSE 2
  END,
  RANDOM()
LIMIT 4;
```

---

## Appendix C: New Set Detection Logic

**How to identify "new" sets:**

1. **Release date** - Sets released within last 6 months
2. **Manual curation** - Manually featured sets (for major releases)
3. **Standard-legal** - Currently legal in Standard format

**Database query:**
```sql
SELECT * FROM sets
WHERE releaseDate >= date('now', '-6 months')
  AND type = 'expansion'
ORDER BY releaseDate DESC
LIMIT 3;
```

---

## Sources

- [Medium - Dashboard UI/UX Design Principles 2025](https://medium.com/@allclonescript/20-best-dashboard-ui-ux-design-principles-you-need-in-2025-30b661f2f795)
- [Polimetro - What is a TUI?](https://www.polimetro.com/en/what-is-a-tui/)
- [Real Python - Python Textual](https://realpython.com/python-textual/)
- [UserGuiding - Onboarding Screens Best Practices](https://userguiding.com/blog/onboarding-screens)
- [GitHub - Awesome TUIs](https://github.com/rothgar/awesome-tuis)
- [Textual - Home](https://textual.textualize.io/)
- [Pencil & Paper - Dashboard UX Patterns](https://www.pencilandpaper.io/articles/ux-pattern-analysis-data-dashboards)
- [Moxfield - MTG Deck Builder](https://moxfield.com/)
- [Archidekt - Visual Deckbuilder](https://archidekt.com/)
- [Draftsim - Best MTG Deck Builder Review](https://draftsim.com/best-mtg-deck-builder/)

---

**Document Status:** Ready for Review
**Next Steps:**
1. Review and approve recommended approach (Rich Discovery Dashboard)
2. Prototype artist spotlight component (2 days)
3. Test on multiple terminal sizes
4. Gather feedback from user
5. Begin Phase 1 implementation (Week 1)

---

**This proposal delivers on the user's #1 request: "artists are my favorite part of MTG!" 🎨**
