# Deck Builder UX Design Proposal
## MTG Spellbook - Comprehensive Deck Building Experience

**Version:** 1.0
**Date:** 2025-12-14
**Status:** Design Proposal

---

## Executive Summary

This document proposes a comprehensive, terminal-native deck building experience for MTG Spellbook that rivals modern web-based deck builders (Moxfield, Archidekt) while embracing the unique strengths of a TUI environment: keyboard-first navigation, instant responsiveness, and efficient workflows.

### Design Philosophy

1. **Keyboard-first, but not keyboard-only** - Optimize for rapid keyboard navigation while supporting mouse interaction
2. **Context-aware interfaces** - Show relevant information at the right time without overwhelming users
3. **Progressive disclosure** - Simple workflows for beginners, powerful shortcuts for experts
4. **Real-time feedback** - Instant visual updates to deck composition, legality, and statistics
5. **Seamless integration** - Deck building feels like a natural extension of card browsing

---

## 1. User Research & Personas

### Primary Personas

#### 1.1 The Casual Builder - "Casey"

**Demographics:**
- Age: 18-35
- Experience: 2-5 years playing MTG
- Deck count: 3-8 decks
- Format preference: Commander, Standard

**Goals:**
- Build decks around favorite cards or themes
- Stay within budget constraints ($50-200)
- Ensure decks are format-legal
- Test deck balance before playing

**Pain Points:**
- Forgetting which cards are already in other decks
- Accidentally creating illegal decks
- Losing track of deck price while building
- Manual card quantity adjustments

**Workflow:**
- Starts with a theme or commander
- Searches for cards that fit the theme
- Adds 1-4 copies at a time
- Checks mana curve and card types periodically
- Validates before finalizing

#### 1.2 The Competitive Player - "Taylor"

**Demographics:**
- Age: 22-40
- Experience: 5+ years competitive play
- Deck count: 10-30 decks
- Format preference: Modern, Pioneer, Legacy

**Goals:**
- Fine-tune meta decks with personal tech choices
- Compare different card options side-by-side
- Track deck versions and iterative changes
- Import/export decklists from tournaments

**Pain Points:**
- Slow iteration when testing card swaps
- No way to compare similar decks
- Manual import/export to other platforms
- Limited filtering when browsing large collections

**Workflow:**
- Imports base decklist or creates from scratch
- Tests multiple card options (4x vs 3x ratios)
- Uses statistics to optimize mana curve
- Exports for tournament submission
- Archives multiple deck versions

#### 1.3 The Collection Manager - "Morgan"

**Demographics:**
- Age: 25-45
- Experience: 10+ years collecting
- Deck count: 50+ decks
- Format preference: All formats

**Goals:**
- Build decks from cards they already own
- Track which decks contain specific cards
- Monitor total collection value
- Organize decks by tags/categories

**Pain Points:**
- Can't see which decks share cards
- No visibility into owned vs needed cards
- Hard to find "that deck with Lightning Bolt"
- No organizational hierarchy

**Workflow:**
- Searches across all decks for specific cards
- Creates new decks tagged by format/theme
- Views deck lists to redistribute cards
- Tracks price changes over time

### User Journey Maps

See Section 2 for detailed journey maps for each persona.

---

## 2. User Journey Mapping

### Journey 1: Building a New Commander Deck (Casey - Casual Builder)

```
SCENARIO: Casey wants to build a dragon tribal deck around Miirym, Sentinel Wyrm

Phase 1: INSPIRATION
├─ Opens MTG Spellbook
├─ Searches for "Miirym, Sentinel Wyrm"
├─ Views card details and rulings
└─ Decides: "I want to build around this!"

Phase 2: DECK CREATION
├─ Presses Ctrl+N (New Deck)
├─ Modal appears: "Create New Deck"
│  ├─ Name: "Miirym Dragon Tribal"
│  ├─ Format: Commander
│  └─ Commander: Miirym, Sentinel Wyrm
├─ Submits → deck created
└─ Deck panel slides in on left side

Phase 3: ADDING CORE CARDS
├─ Still viewing Miirym card panel
├─ Presses Ctrl+E (Add to Deck)
├─ Modal: Add to Deck
│  ├─ Card: Miirym, Sentinel Wyrm
│  ├─ Deck: [Miirym Dragon Tribal]
│  ├─ Quantity: 1 (grayed out for commander)
│  └─ ☑ Set as Commander
├─ Confirms → card added
└─ Notification: "Miirym set as commander"

Phase 4: SEARCHING FOR SYNERGIES
├─ Presses Ctrl+S (Find Synergies)
├─ Results list populates with dragon synergies:
│  ├─ Terror of the Peaks
│  ├─ Dragon Tempest
│  ├─ Dragonspeaker Shaman
│  └─ ...30+ results
├─ Navigates list with arrow keys
├─ For each card:
│  ├─ Presses Enter → views card detail
│  ├─ Presses Ctrl+E → adds to deck
│  └─ Sees live deck count update: "38/100"
└─ Deck panel shows real-time updates

Phase 5: REVIEWING COMPOSITION
├─ Presses Ctrl+D (Toggle Deck Panel)
├─ Deck panel expands to full view
├─ Sees tabs: [Cards] [Stats] [Analysis] [Price]
├─ Switches to Stats tab:
│  ├─ Mana curve visualization
│  ├─ Color distribution (Temur colors)
│  ├─ Card type breakdown
│  └─ Average CMC: 3.8
├─ Switches to Price tab:
│  └─ Total: $147.50 (within budget!)
└─ Satisfied with composition

Phase 6: FILLING MANA BASE
├─ Searches "t:land produces:blue produces:red produces:green"
├─ Adds dual lands, fetches, basics
├─ Watches deck count: "96/100"
└─ Adds 4 more utility cards → "100/100"

Phase 7: VALIDATION
├─ Presses V (Validate Deck)
├─ Analysis modal appears:
│  ├─ ✓ Format: Legal (Commander)
│  ├─ ✓ Card count: 100 (99 + 1 commander)
│  ├─ ✓ Color identity: Temur (matches Miirym)
│  ├─ ✓ No banned cards
│  └─ ✓ Singleton enforced
└─ Notification: "Deck is format-legal!"

OUTCOME: Deck complete in ~25 minutes
SATISFACTION: High (clear workflow, instant feedback, stayed in budget)
```

### Journey 2: Optimizing a Competitive Modern Deck (Taylor - Competitive Player)

```
SCENARIO: Taylor wants to tune a Burn deck by testing 3x vs 4x Eidolon of the Great Revel

Phase 1: IMPORT EXISTING LIST
├─ Presses Ctrl+I (Import Deck)
├─ Modal appears with text area
├─ Pastes MTGO-format decklist
├─ Submits → deck parsed and created
└─ Deck panel shows imported cards

Phase 2: DEDICATED DECK BUILDER MODE
├─ Presses Shift+D (Full Deck Builder)
├─ Screen transitions to split-pane layout:
│  ├─ LEFT (40%): Search & Browse
│  │  ├─ Search bar at top
│  │  ├─ Filter panel (CMC, color, type)
│  │  └─ Results list
│  └─ RIGHT (60%): Deck Editor
│     ├─ Mainboard (sorted by CMC)
│     ├─ Sideboard
│     └─ Stats panel (collapsible)
└─ Full keyboard navigation

Phase 3: TESTING CARD RATIOS
├─ Selects "4 Eidolon of the Great Revel" in deck
├─ Presses - → "3 Eidolon of the Great Revel"
├─ Stats panel updates:
│  ├─ Mana curve shifts (2-CMC: 12 → 11)
│  └─ Deck total: 60 → 59
├─ Searches "c:red cmc:2 t:creature"
├─ Reviews alternatives:
│  ├─ Kari Zev, Skyship Raider
│  ├─ Ash Zealot
│  └─ Earthshaker Khenra
├─ Highlights each → presses Tab to view in detail pane
└─ Decides to keep Eidolon at 3x

Phase 4: SIDE-BY-SIDE COMPARISON
├─ Opens card "Skullcrack" in detail pane
├─ Presses C (Compare Mode)
├─ Searches "Deflecting Palm"
├─ Presses Space (Add to Compare)
├─ Split view shows:
│  ├─ LEFT: Skullcrack - {1}{R} - Instant
│  └─ RIGHT: Deflecting Palm - {R}{W} - Instant
├─ Compares text, CMC, color requirements
└─ Decides: Skullcrack better (mono-red)

Phase 5: SIDEBOARD CONSTRUCTION
├─ Focuses sideboard section (Tab)
├─ Searches "artifact hate c:red"
├─ For each card:
│  ├─ Presses Shift+S (Add to Sideboard)
│  └─ Quantity modal → enters 2-3 copies
├─ Sideboard fills: "14/15"
└─ Adds 1 more flex slot

Phase 6: EXPORT FOR TOURNAMENT
├─ Presses Ctrl+X (Export)
├─ Modal shows export formats:
│  ├─ MTGO
│  ├─ Arena
│  ├─ Text (plain)
│  └─ Moxfield URL
├─ Selects MTGO
└─ Copies to clipboard

OUTCOME: Deck optimized in ~15 minutes
SATISFACTION: Very High (fast iteration, visual comparison, easy export)
```

### Journey 3: Finding Cards Across Collection (Morgan - Collection Manager)

```
SCENARIO: Morgan wants to find all decks containing Fetch Lands to build a new deck

Phase 1: GLOBAL DECK SEARCH
├─ Presses Ctrl+Shift+F (Search All Decks)
├─ Search modal appears
├─ Enters: "t:land o:search"
└─ Results show all decks with fetch lands

Phase 2: DECK ORGANIZATION
├─ Views deck list (50+ decks)
├─ Presses T (Toggle Tags)
├─ Tag filter appears:
│  ├─ #modern (12 decks)
│  ├─ #legacy (8 decks)
│  ├─ #budget (15 decks)
│  └─ #competitive (10 decks)
├─ Clicks #modern
└─ List filters to 12 decks

Phase 3: VIEWING SHARED CARDS
├─ Presses Shift+C (Collection View)
├─ Modal shows "Cards in Multiple Decks":
│  ├─ Lightning Bolt (8 decks)
│  ├─ Polluted Delta (6 decks)
│  ├─ Thoughtseize (4 decks)
│  └─ ...
├─ Clicks "Polluted Delta"
└─ Shows which 6 decks contain it

OUTCOME: Found cards in ~5 minutes
SATISFACTION: High (powerful search, clear organization)
```

---

## 3. Wireframes (ASCII Art)

### 3.1 Full-Screen Deck Builder Mode

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ MTG SPELLBOOK ✦ Deck Builder: "Mono-Red Burn" (Modern) · 60 cards                         [X]  │
├──────────────────────────────────────┬──────────────────────────────────────────────────────────┤
│ SEARCH & BROWSE                      │ DECK EDITOR                                              │
│                                      │                                                          │
│ ┌──────────────────────────────────┐ │ Mainboard (56/60) ───────────────────────────────────── │
│ │ ⚡ Search: c:red cmc<=3          │ │  CMC  Qty  Card Name                Mana   Type         │
│ └──────────────────────────────────┘ │  ─────────────────────────────────────────────────────  │
│                                      │   1    4   Monastery Swiftspear     {R}    Creature     │
│ FILTERS ▼                            │   1    4   Goblin Guide             {R}    Creature     │
│ ┌──────────────────────────────────┐ │   1    4   Lightning Bolt           {R}    Instant      │
│ │ CMC: [0] [1] [2] [3] [ ]         │ │   1    4   Lava Spike              {R}    Sorcery      │
│ │ Type: ☑ Creature ☑ Instant      │ │   2    4   Eidolon of Great Revel  {1}{R} Creature     │
│ │       ☑ Sorcery  ☐ Enchantment  │ │   2    4   Searing Blaze           {R}{R} Instant      │
│ └──────────────────────────────────┘ │   2    4   Skullcrack              {1}{R} Instant      │
│                                      │   3    4   Rift Bolt               {2}{R} Sorcery      │
│ RESULTS (127 cards) ▼                │   4   20   Mountain                {T}    Land         │
│ ┌──────────────────────────────────┐ │  ─────────────────────────────────────────────────────  │
│ │> Lightning Bolt         {R}      │ │                                                          │
│ │  Monastery Swiftspear   {R}      │ │ Sideboard (15/15) ──────────────────────────────────── │
│ │  Goblin Guide           {R}      │ │   2    3   Smash to Smithereens   {1}{R} Instant      │
│ │  Lava Spike            {R}      │ │   2    3   Deflecting Palm        {R}{W} Instant      │
│ │  Eidolon of Great Revel{1}{R}    │ │   2    4   Rampaging Ferocidon    {2}{R} Creature     │
│ │  Chain Lightning       {R}      │ │   3    2   Exquisite Firecraft    {1}{R}{R} Sorcery   │
│ │  Searing Blaze         {R}{R}    │ │   3    3   Roiling Vortex         {1}{R} Enchantment  │
│ │  ...                             │ │  ─────────────────────────────────────────────────────  │
│ └──────────────────────────────────┘ │                                                          │
│                                      │ STATS ▼ ────────────────────────────────────────────── │
│ [Enter] View  [Ctrl+E] Add          │  Curve:  1 ███████████ 16     Creatures:  24 (40%)      │
│ [/] Focus Search                    │          2 ██████ 8           Instants:   16 (27%)      │
│                                      │          3 ██ 4               Sorcery:     8 (13%)      │
│                                      │          4 ████████████ 20    Lands:      20 (33%)      │
│                                      │  Avg CMC: 1.9  ·  Colors: R  ·  Price: $245.00          │
├──────────────────────────────────────┴──────────────────────────────────────────────────────────┤
│ [Ctrl+E] Add · [+/-] Qty · [S] Sideboard · [V] Validate · [Ctrl+X] Export · [Esc] Exit       │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Compact Deck Panel (Sidebar View)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ MTG SPELLBOOK ✦ 33,429 cards · 578 sets                                                        │
├──────────┬──────────────────────────┬───────────────────────────────────────────────────────────┤
│          │ RESULTS (24)             │ CARD DETAILS                                              │
│ MY DECKS │                          │                                                           │
│ ──────── │ > Lightning Bolt         │ ┌─────────────────────────────────────────────────────┐   │
│          │   Chain Lightning        │ │ Lightning Bolt                            {R}       │   │
│ [N] New  │   Lava Spike            │ │ ─────────────────────────────────────────────────── │   │
│          │   Searing Blaze         │ │ Instant                                             │   │
│ > Burn   │   Rift Bolt             │ │                                                     │   │
│ Modern   │   ...                    │ │ Lightning Bolt deals 3 damage to any target.       │   │
│ 60 cards │                          │ │                                                     │   │
│ $245     │                          │ │ "The sparkmage shrieked, calling on the sky.       │   │
│          │                          │ │  The sky listened, and answered."                  │   │
│ Elves    │                          │ └─────────────────────────────────────────────────── │   │
│ Legacy   │                          │                                                           │
│ 60 cards │                          │ [📖 Card] [🖼 Art] [📜 Rulings] [⚖ Legal] [💰 Price]     │
│ $1,240   │                          │                                                           │
│          │                          │ [Ctrl+E] Add to Deck   [Ctrl+S] Find Synergies           │
│ Atraxa   │                          │                                                           │
│ Cmdr     │                          │                                                           │
│ 100 cards│                          │                                                           │
│ $890     │                          │                                                           │
│          │                          │                                                           │
│ ...      │                          │                                                           │
│          │                          │                                                           │
│ [Enter]  │                          │                                                           │
│ Edit     │                          │                                                           │
│          │                          │                                                           │
│ [D]      │                          │                                                           │
│ Delete   │                          │                                                           │
├──────────┴──────────────────────────┴───────────────────────────────────────────────────────────┤
│ [Ctrl+D] Toggle Decks · [Ctrl+E] Add to Deck · [Ctrl+Q] Quit                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Add to Deck Modal (Quick Add)

```
                           ┌─────────────────────────────────────┐
                           │ ADD TO DECK                         │
                           ├─────────────────────────────────────┤
                           │                                     │
                           │ Card: Lightning Bolt                │
                           │                                     │
                           │ Deck:  ┌──────────────────────────┐ │
                           │        │ Mono-Red Burn      ▼     │ │
                           │        ├──────────────────────────┤ │
                           │        │ Mono-Red Burn            │ │
                           │        │ Elves Combo              │ │
                           │        │ Atraxa Superfriends      │ │
                           │        │ ──────────────────────   │ │
                           │        │ + Create New Deck        │ │
                           │        └──────────────────────────┘ │
                           │                                     │
                           │ Quantity: [ 4 ]  [1] [2] [3] [4]   │
                           │                                     │
                           │ ☐ Add to Sideboard                  │
                           │                                     │
                           │  Current: 0x  →  New: 4x            │
                           │  Deck total: 56/60  →  60/60        │
                           │                                     │
                           │      [Add]           [Cancel]       │
                           │                                     │
                           └─────────────────────────────────────┘
```

### 3.4 Deck Analysis Modal

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ DECK ANALYSIS: Mono-Red Burn (Modern)                                                     [X]  │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                 │
│ VALIDATION ─────────────────────────────────────────────────────────────────────────────────── │
│  ✓ Format Legal: Modern                                                                        │
│  ✓ Deck Size: 60/60 mainboard, 15/15 sideboard                                                 │
│  ✓ Max Copies: No card exceeds 4 copies (except basic lands)                                   │
│  ✓ Banned/Restricted: No issues                                                                │
│                                                                                                 │
│ MANA CURVE ────────────────────────────────────────────────────────────────────────────────── │
│   0:                                                                      0 (0%)                │
│   1: ████████████████████████████████████                               16 (40%)               │
│   2: ████████████████                                                     8 (20%)               │
│   3: ████                                                                 4 (10%)               │
│   4:                                                                      0 (0%)                │
│   5+:                                                                     0 (0%)                │
│   Lands: ████████████████████████████████████████                       20 (33%)               │
│                                                                                                 │
│   Average CMC (non-land): 1.57                                  OPTIMAL RANGE: 1.5-2.5         │
│                                                                                                 │
│ COLOR DISTRIBUTION ─────────────────────────────────────────────────────────────────────────── │
│   {R} Red:     ██████████████████████████████████████████████████████ 56 (100% of non-land)   │
│   {W} White:   2 (sideboard only)                                                              │
│   Colorless:   20 (lands)                                                                      │
│                                                                                                 │
│ CARD TYPES ─────────────────────────────────────────────────────────────────────────────────── │
│   Creatures:   ████████████ 12 (30%)                                                           │
│   Instants:    ████████████ 12 (30%)                                                           │
│   Sorceries:   ████ 4 (10%)                                                                    │
│   Lands:       ██████████████████ 20 (33%)                                                     │
│                                                                                                 │
│ PRICE ANALYSIS ─────────────────────────────────────────────────────────────────────────────── │
│   Total Deck Value: $245.00 USD                                                                │
│   Mainboard: $220.00  ·  Sideboard: $25.00                                                     │
│                                                                                                 │
│   Most Expensive Cards:                                                                        │
│     1. Scalding Tarn        $85.00 (4x = $340.00) - NOT IN CURRENT LIST                       │
│     2. Blood Moon (SB)      $18.00 (3x = $54.00)                                               │
│     3. Eidolon of Great R.  $12.00 (3x = $36.00)                                               │
│                                                                                                 │
│ RECOMMENDATIONS ────────────────────────────────────────────────────────────────────────────── │
│   ⚠ Low land count: 20 lands is aggressive for this curve. Consider 21-22.                    │
│   ⚠ No card draw: Deck may run out of gas. Consider: Light Up the Stage, Experimental Frenzy  │
│   ✓ Mana curve: Excellent curve for aggro strategy                                             │
│   ✓ Color consistency: Mono-colored ensures consistent mana                                    │
│                                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [V] Re-validate  ·  [E] Export Report  ·  [Esc] Close                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.5 Card Comparison View (Split Detail)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ COMPARE: Skullcrack vs Deflecting Palm                                                    [X]  │
├──────────────────────────────────────┬──────────────────────────────────────────────────────────┤
│ Skullcrack                    {1}{R} │ Deflecting Palm                   {R}{W}                 │
├──────────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Instant                              │ Instant                                                  │
│                                      │                                                          │
│ Players can't gain life this turn.   │ The next time a source of your choice                    │
│ Damage can't be prevented this turn. │ would deal damage to you this turn,                      │
│                                      │ prevent that damage. If damage is                        │
│ Skullcrack deals 3 damage to target │ prevented this way, Deflecting Palm                       │
│ player or planeswalker.              │ deals that much damage to that source's                  │
│                                      │ controller.                                              │
│ ──────────────────────────────────── │ ──────────────────────────────────────────────────────── │
│ CMC: 2                               │ CMC: 2                                                   │
│ Colors: {R}                          │ Colors: {R}{W}                                           │
│ Type: Instant                        │ Type: Instant                                            │
│ Rarity: Uncommon                     │ Rarity: Rare                                             │
│ Price: $0.50                         │ Price: $1.25                                             │
│                                      │                                                          │
│ PROS:                                │ PROS:                                                    │
│ + Mono-red (fits mana base)          │ + Can redirect large attacks                             │
│ + Deals damage directly              │ + Flexible (works vs burn & combat)                      │
│ + Prevents lifegain hate             │ + Can save life total                                    │
│                                      │                                                          │
│ CONS:                                │ CONS:                                                    │
│ - Fixed 3 damage                     │ - Requires white mana                                    │
│ - Only targets player/PW             │ - Reactive (requires opponent action)                    │
│                                      │ - Doesn't guarantee damage                               │
│                                      │                                                          │
│ FORMAT LEGALITY:                     │ FORMAT LEGALITY:                                         │
│ ✓ Modern  ✓ Pioneer  ✓ Legacy       │ ✓ Modern  ✓ Pioneer  ✓ Legacy                           │
│                                      │                                                          │
├──────────────────────────────────────┴──────────────────────────────────────────────────────────┤
│ [1] Select Skullcrack  ·  [2] Select Deflecting Palm  ·  [A] Add Both  ·  [Esc] Close         │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.6 Import Deck Modal

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ IMPORT DECK                                                                                [X]  │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                 │
│ Paste your decklist below (Arena, MTGO, or plain text format)                                  │
│                                                                                                 │
│ ┌─────────────────────────────────────────────────────────────────────────────────────────────┐ │
│ │ 4 Lightning Bolt                                                                            │ │
│ │ 4 Monastery Swiftspear                                                                      │ │
│ │ 4 Goblin Guide                                                                              │ │
│ │ 3 Eidolon of the Great Revel                                                                │ │
│ │ 4 Lava Spike                                                                                │ │
│ │ 4 Rift Bolt                                                                                 │ │
│ │ 4 Searing Blaze                                                                             │ │
│ │ 4 Skullcrack                                                                                │ │
│ │ 20 Mountain                                                                                 │ │
│ │                                                                                             │ │
│ │ Sideboard                                                                                   │ │
│ │ 3 Smash to Smithereens                                                                      │ │
│ │ 4 Rampaging Ferocidon                                                                       │ │
│ │ ...                                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                                 │
│ Deck Name: [ Mono-Red Burn                    ]                                                │
│                                                                                                 │
│ Format:    [Modern            ▼]                                                               │
│                                                                                                 │
│ ☑ Validate cards (check if they exist)                                                         │
│ ☑ Auto-detect format from card legality                                                        │
│                                                                                                 │
│ Preview: 31 mainboard cards, 7 sideboard cards detected                                        │
│                                                                                                 │
│      [Import]           [Cancel]                                                               │
│                                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Interaction Patterns & Keyboard Shortcuts

### 4.1 Keyboard-First Navigation

#### Global Shortcuts (Work Anywhere)

| Key | Action | Context |
|-----|--------|---------|
| `Ctrl+D` | Toggle deck panel (sidebar) | Always |
| `Ctrl+Shift+D` | Open full deck builder | Always |
| `Ctrl+N` | New deck | Always |
| `Ctrl+E` | Add current card to deck | When viewing card |
| `Ctrl+I` | Import deck from text | Always |
| `Ctrl+X` | Export current deck | When viewing deck |
| `Ctrl+F` | Focus search | Always |
| `Ctrl+Shift+F` | Search across all decks | Always |
| `Esc` | Back / Cancel / Close modal | Context-dependent |

#### Deck List Panel

| Key | Action | Notes |
|-----|--------|-------|
| `↑` / `↓` | Navigate deck list | Vim-style: `k`/`j` also work |
| `Enter` | Open deck in editor | Shows deck details |
| `N` | New deck | Quick access |
| `D` | Delete selected deck | Requires confirmation |
| `E` | Edit deck metadata | Name, format, description |
| `T` | Toggle tag filter | Show/hide tag panel |
| `V` | Validate selected deck | Run format legality check |
| `Space` | Select/deselect (multi-select) | For bulk operations |

#### Deck Editor (Full View)

| Key | Action | Notes |
|-----|--------|-------|
| `Tab` | Switch focus (search ↔ deck) | Cycle through panels |
| `Shift+Tab` | Reverse focus | Backward cycle |
| `/` | Focus search bar | Quick search access |
| `↑` / `↓` | Navigate card list | Current focused panel |
| `←` / `→` | Switch columns (if multi-column) | Layout dependent |
| `Enter` | View card details | Opens detail pane |
| `Space` | Quick-add card (from search) | Adds 1x to mainboard |
| `Ctrl+Space` | Quick-add to sideboard | Adds 1x to sideboard |
| `+` / `=` | Increase quantity | Selected card in deck |
| `-` | Decrease quantity | Selected card in deck |
| `Delete` | Remove card from deck | Confirmation for last copy |
| `Backspace` | Remove 1 copy | Faster than `-` key |
| `S` | Toggle sideboard/mainboard | Move selected card |
| `M` | Move to mainboard | Explicit move |
| `B` | Move to sideboard | Explicit move (sideboard) |
| `C` | Compare selected cards | Opens comparison view |
| `V` | Validate deck | Show analysis modal |
| `A` | Full analysis | Comprehensive stats |
| `P` | Show price breakdown | Price analysis view |
| `G` | Group by category | Toggle grouping mode |
| `O` | Sort options | Cycle: CMC, Name, Type, Color |

#### Card Search Panel (in Deck Builder)

| Key | Action | Notes |
|-----|--------|-------|
| `/` | Focus search input | Start typing immediately |
| `Ctrl+F` | Advanced filter panel | Toggle filter sidebar |
| `Ctrl+K` | Clear search | Reset to empty |
| `↑` / `↓` | Navigate results | Standard navigation |
| `Enter` | View card details | Detail pane updates |
| `Space` | Add to deck (quick) | Default: 1x mainboard |
| `1-4` | Add N copies | Quick quantity shortcuts |
| `Shift+1-4` | Add N to sideboard | Sideboard variants |
| `Tab` | Next filter field | When filters visible |

#### Modals (Add to Deck, Import, Export)

| Key | Action | Notes |
|-----|--------|-------|
| `Enter` | Confirm / Submit | Primary action |
| `Esc` | Cancel / Close | Discard changes |
| `Tab` | Next field | Form navigation |
| `Shift+Tab` | Previous field | Reverse navigation |
| `1-4` | Select quantity preset | In "Add to Deck" modal |
| `↑` / `↓` | Navigate dropdowns | Deck selection |
| `Space` | Toggle checkbox | E.g., "Add to sideboard" |

#### Analysis View

| Key | Action | Notes |
|-----|--------|-------|
| `Tab` | Switch analysis category | Curve → Types → Colors → Price |
| `E` | Export analysis as text | Copy to clipboard |
| `V` | Re-run validation | Refresh data |
| `Esc` | Close analysis | Return to editor |

### 4.2 Mouse Interaction

While keyboard-first, mouse support enhances accessibility:

- **Click** - Select cards, decks, buttons
- **Double-click** - Quick-add card to deck (1x)
- **Right-click** - Context menu (Add to deck, Compare, View rulings)
- **Scroll** - Navigate long lists
- **Drag & drop** - Reorder cards (optional enhancement)

### 4.3 Progressive Disclosure Patterns

#### Beginner Mode (Default)
- Simple add/remove cards
- Basic stats visible (card count, mana curve)
- Clear labels and hints

#### Intermediate Mode (Auto-detected)
- Advanced filters appear after 5+ searches
- Quick-add shortcuts shown in tooltips
- Comparison mode available

#### Expert Mode (Toggleable)
- Vim-style navigation (hjkl)
- All keyboard shortcuts active
- Minimal UI (hidden labels, compact layout)
- Custom keybinding support

### 4.4 Context-Aware Help

Press `?` in any view to show context-specific shortcuts:

```
┌─────────────────────────────────────────┐
│ KEYBOARD SHORTCUTS - Deck Editor        │
├─────────────────────────────────────────┤
│ NAVIGATION                              │
│   ↑/↓ or j/k   Navigate cards           │
│   Tab          Switch panels            │
│   /            Focus search             │
│                                         │
│ EDITING                                 │
│   Space        Add card (1x)            │
│   1-4          Add N copies             │
│   +/-          Adjust quantity          │
│   S            Toggle sideboard         │
│   Delete       Remove card              │
│                                         │
│ ANALYSIS                                │
│   V            Validate deck            │
│   A            Full analysis            │
│   P            Price breakdown          │
│                                         │
│ Press ? to close                        │
└─────────────────────────────────────────┘
```

---

## 5. Component Inventory

### 5.1 Core Widgets (Must Build)

#### DeckListPanel
- **Purpose:** Sidebar showing all user's decks
- **Features:**
  - List of decks with name, format, card count, price
  - Quick actions: New, Edit, Delete, Validate
  - Tag filtering
  - Search across decks
- **Complexity:** Medium (150-200 lines)
- **Dependencies:** `DeckManager`, `ListView`, `Static`

#### DeckEditorPanel
- **Purpose:** In-line deck editor (non-full-screen)
- **Features:**
  - Mainboard/sideboard card lists
  - Live stats sidebar (curve, types, price)
  - Quantity adjustment (+/-)
  - Card removal
- **Complexity:** High (250-300 lines)
- **Dependencies:** `DeckManager`, `ListView`, `Horizontal`, `Vertical`

#### FullDeckBuilder
- **Purpose:** Dedicated full-screen deck building mode
- **Features:**
  - Split pane: Search (left) + Deck (right)
  - Advanced filters
  - Real-time stats
  - Keyboard-optimized navigation
- **Complexity:** Very High (400-500 lines)
- **Dependencies:** All deck components + `CardPanel` integration

#### AddToDeckModal
- **Purpose:** Quick modal for adding current card to a deck
- **Features:**
  - Deck dropdown (with search)
  - Quantity selector (1-4 quick buttons)
  - Sideboard checkbox
  - "Create new deck" option
  - Live preview (before/after counts)
- **Complexity:** Low (100-150 lines)
- **Dependencies:** `ModalScreen`, `Select`, `Input`, `Button`

#### DeckAnalysisModal
- **Purpose:** Comprehensive deck analysis overlay
- **Features:**
  - Validation results
  - Mana curve visualization
  - Color distribution
  - Card type breakdown
  - Price analysis with most expensive cards
  - Recommendations
- **Complexity:** High (300-350 lines)
- **Dependencies:** Deck analysis tools from `mtg-core`

#### ImportDeckModal
- **Purpose:** Parse and import deck from text
- **Features:**
  - Large text area for paste
  - Format detection (Arena, MTGO, plain)
  - Card validation
  - Error reporting
  - Preview before import
- **Complexity:** Medium (200-250 lines)
- **Dependencies:** `DeckManager.import_from_text`, `TextArea`, `Static`

#### ExportDeckModal
- **Purpose:** Export deck to various formats
- **Features:**
  - Format selection (MTGO, Arena, Text, Moxfield URL)
  - Copy to clipboard
  - Save to file option
  - Preview before export
- **Complexity:** Low (100-150 lines)
- **Dependencies:** `DeckManager.export_to_text`, `Select`, `Button`

#### DeckStatsPanel
- **Purpose:** Real-time deck statistics widget
- **Features:**
  - Mana curve bar chart
  - Color distribution pie/bar chart
  - Card type breakdown
  - Average CMC
  - Total price
  - Format legality indicator
- **Complexity:** Medium (200-250 lines)
- **Dependencies:** Rich renderables, deck analysis functions

#### QuickFilterBar
- **Purpose:** Compact filter controls for card search
- **Features:**
  - CMC range slider
  - Color checkboxes (WUBRG)
  - Type toggles (Creature, Instant, etc.)
  - Rarity filter
- **Complexity:** Medium (150-200 lines)
- **Dependencies:** `Horizontal`, `Checkbox`, custom widgets

#### CardComparisonPanel
- **Purpose:** Side-by-side card comparison
- **Features:**
  - Split view (2-4 cards)
  - Highlighted differences
  - Format legality comparison
  - Price comparison
  - "Add both" quick action
- **Complexity:** High (250-300 lines)
- **Dependencies:** `CardPanel` reuse, `Horizontal`, custom diff logic

#### DeckTagEditor
- **Purpose:** Manage deck tags
- **Features:**
  - Add/remove tags
  - Tag autocomplete
  - Color-coded tags
  - Tag-based filtering
- **Complexity:** Low (100-150 lines)
- **Dependencies:** `Input`, `HorizontalList`, database tag operations

### 5.2 Reusable Components (Already Exist)

#### CardPanel
- **Current Use:** Display card details with tabs
- **Deck Builder Use:** Show cards in search results, comparison
- **Modification Needed:** None (already perfect)

#### ResultsList
- **Current Use:** Show search results
- **Deck Builder Use:** Show deck cards, search results
- **Modification Needed:** Add quantity prefix rendering

#### EnhancedArtNavigator
- **Current Use:** Browse card artwork
- **Deck Builder Use:** Preview cards while building
- **Modification Needed:** None

### 5.3 Data Models (mtg-core)

Already implemented:
- `Deck` - Core deck model
- `DeckCard` - Card in deck with quantity
- `DeckManager` - Business logic layer
- `UserDatabase` - SQLite persistence

Need to add:
- `DeckTag` - Tag metadata
- `DeckVersion` - Deck history (future)

---

## 6. Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal:** Basic deck creation and card addition

#### Tasks:
1. **DeckListPanel widget** (150 lines)
   - Display list of decks
   - New deck modal
   - Delete confirmation modal
   - Basic navigation (up/down, enter)

2. **AddToDeckModal** (100 lines)
   - Deck dropdown
   - Quantity input
   - Add to sideboard checkbox
   - Integration with existing card panel

3. **App integration** (50 lines)
   - `Ctrl+D` toggle deck panel
   - `Ctrl+E` add to deck from card view
   - Wire up `DeckManager` to modals

**Deliverable:** Users can create decks and add cards from search results.

**Testing:**
- Create 3 decks with different formats
- Add 10 cards to each deck
- Verify database persistence
- Test keyboard shortcuts

---

### Phase 2: Deck Editing (Week 2)
**Goal:** View and modify deck contents

#### Tasks:
1. **DeckEditorPanel** (250 lines)
   - Mainboard card list with quantities
   - Sideboard card list
   - Quantity adjustment (+/- keys)
   - Card removal (delete key)
   - Sort options (CMC, name, type)

2. **DeckStatsPanel** (200 lines)
   - Mana curve bar chart
   - Card type breakdown
   - Live updates as deck changes
   - Total card count

3. **Navigation flow** (100 lines)
   - Deck list → editor transition
   - Back to list (escape key)
   - Highlight current deck in list

**Deliverable:** Users can view deck contents and adjust quantities.

**Testing:**
- Load deck with 60 cards
- Adjust quantities (increase/decrease)
- Remove cards
- Verify stats update in real-time
- Test with 100-card Commander deck

---

### Phase 3: Full Deck Builder Mode (Week 3)
**Goal:** Dedicated deck building interface

#### Tasks:
1. **FullDeckBuilder screen** (400 lines)
   - Split pane layout (search + deck)
   - Focus management (Tab key)
   - Search results on left
   - Deck editor on right
   - Collapsible stats panel

2. **QuickFilterBar** (150 lines)
   - CMC filter
   - Color checkboxes
   - Type toggles
   - Integration with search

3. **Quick-add shortcuts** (50 lines)
   - Space bar to add 1x
   - Number keys (1-4) to add N copies
   - Shift+Space for sideboard
   - Toast notifications

**Deliverable:** Fast, keyboard-driven deck building workflow.

**Testing:**
- Build a 60-card deck from scratch in < 10 minutes
- Use only keyboard (no mouse)
- Verify filters work correctly
- Test with 500+ search results

---

### Phase 4: Analysis & Validation (Week 4)
**Goal:** Comprehensive deck analysis

#### Tasks:
1. **DeckAnalysisModal** (300 lines)
   - Format validation
   - Mana curve visualization
   - Color distribution
   - Card type composition
   - Price breakdown
   - Recommendations engine

2. **Integration with mtg-core tools** (100 lines)
   - Wire up existing `validate_deck`
   - Wire up existing `analyze_mana_curve`
   - Wire up existing `analyze_colors`
   - Wire up existing `analyze_deck_composition`
   - Wire up existing `analyze_deck_price`

3. **Live validation feedback** (50 lines)
   - Warning badges on deck list
   - Color-coded legality (✓ green, ⚠ yellow, ✗ red)
   - Inline warnings in editor

**Deliverable:** Users get instant feedback on deck legality and composition.

**Testing:**
- Validate legal Modern deck (should pass)
- Create illegal deck (5x Lightning Bolt) - should fail
- Test with Commander deck (100 cards, singleton)
- Verify price calculations match Scryfall

---

### Phase 5: Import/Export (Week 5)
**Goal:** Interoperability with other tools

#### Tasks:
1. **ImportDeckModal** (200 lines)
   - Text area for paste
   - Parser for Arena format ("4 Lightning Bolt")
   - Parser for MTGO format ("4x Lightning Bolt")
   - Card validation
   - Error reporting (missing cards)
   - Preview before import

2. **ExportDeckModal** (100 lines)
   - Format selection dropdown
   - Copy to clipboard button
   - Save to file option
   - Preview before export

3. **Format converters** (150 lines)
   - MTGO format: "4 Lightning Bolt"
   - Arena format: "4 Lightning Bolt (M21) 123"
   - Plain text: "4x Lightning Bolt"
   - Moxfield URL (if API available)

**Deliverable:** Seamless import/export to/from other platforms.

**Testing:**
- Import 10 decklists from different sources
- Export to all formats
- Round-trip test (import → export → import)
- Verify special characters (apostrophes, hyphens)

---

### Phase 6: Advanced Features (Week 6)
**Goal:** Power-user features

#### Tasks:
1. **CardComparisonPanel** (250 lines)
   - Side-by-side card view
   - Highlighted differences
   - Quick-add both cards
   - Compare up to 4 cards

2. **DeckTagEditor** (100 lines)
   - Add/remove tags
   - Tag-based filtering
   - Tag autocomplete
   - Color-coded tags

3. **Search across decks** (100 lines)
   - Global search (Ctrl+Shift+F)
   - Results show deck names
   - Jump to deck from results

4. **Bulk operations** (100 lines)
   - Multi-select cards (Space)
   - Bulk move to sideboard
   - Bulk quantity adjustment
   - Bulk delete

**Deliverable:** Expert-level workflow optimizations.

**Testing:**
- Compare 3 similar cards (e.g., Lightning Bolt vs Chain Lightning vs Lava Spike)
- Tag 20 decks with various tags
- Filter by multiple tags
- Search for "Lightning Bolt" across all decks
- Bulk move 10 cards to sideboard

---

### Phase 7: Polish & Refinement (Week 7)
**Goal:** Production-ready UX

#### Tasks:
1. **Responsive layouts** (100 lines)
   - Handle small terminal sizes (80x24)
   - Collapsible panels
   - Dynamic font scaling

2. **Keyboard shortcut hints** (50 lines)
   - Context-sensitive help (? key)
   - Tooltips on hover (mouse users)
   - Status bar hints

3. **Animations & transitions** (100 lines)
   - Smooth panel slide-in/out
   - Fade effects for modals
   - Loading spinners

4. **Error handling & edge cases** (100 lines)
   - Graceful failure for missing cards
   - Network error handling (price fetch)
   - Empty state messages
   - Maximum deck size warnings

5. **Accessibility** (50 lines)
   - Screen reader labels
   - High contrast mode
   - Reduced motion option

**Deliverable:** Polished, accessible, production-ready deck builder.

**Testing:**
- Test on 80x24 terminal
- Test on 200x60 terminal (ultra-wide)
- Test with screen reader
- Test all error conditions
- User acceptance testing with 5+ users

---

## 7. Recommended Build Order

### Sprint 1 (Week 1): MVP
1. DeckListPanel
2. AddToDeckModal
3. App integration (Ctrl+D, Ctrl+E)

**Milestone:** Can create decks and add cards

---

### Sprint 2 (Week 2): Editing
1. DeckEditorPanel
2. DeckStatsPanel
3. Navigation flow

**Milestone:** Can view and edit deck contents

---

### Sprint 3 (Week 3): Builder Mode
1. FullDeckBuilder screen
2. QuickFilterBar
3. Quick-add shortcuts

**Milestone:** Fast deck building workflow

---

### Sprint 4 (Week 4): Analysis
1. DeckAnalysisModal
2. Integration with mtg-core
3. Live validation

**Milestone:** Deck validation and recommendations

---

### Sprint 5 (Week 5): Interop
1. ImportDeckModal
2. ExportDeckModal
3. Format converters

**Milestone:** Import/export from other platforms

---

### Sprint 6 (Week 6): Power Features
1. CardComparisonPanel
2. DeckTagEditor
3. Global deck search
4. Bulk operations

**Milestone:** Expert workflow optimizations

---

### Sprint 7 (Week 7): Polish
1. Responsive layouts
2. Keyboard hints
3. Animations
4. Error handling
5. Accessibility

**Milestone:** Production release

---

## 8. UX Principles & Best Practices

### 8.1 Immediate Feedback
- **Card count updates** - Every add/remove shows deck total: "56/60 → 60/60"
- **Price updates** - Live price changes as cards are added
- **Validation badges** - Green checkmark or red X on deck list
- **Toast notifications** - "Added 4x Lightning Bolt to Mono-Red Burn"

### 8.2 Contextual Awareness
- **Recent deck memory** - Last used deck becomes default in "Add to Deck"
- **Format detection** - Auto-suggest format based on cards added
- **Smart defaults** - Quantity defaults to 4 for non-legendary, 1 for legendary
- **Related cards** - Suggest synergies after adding tribal/thematic cards

### 8.3 Minimize Cognitive Load
- **Single-purpose modals** - One task at a time (no multi-step wizards)
- **Clear visual hierarchy** - Important info is larger/bolder
- **Consistent patterns** - Same shortcuts work everywhere
- **Progressive complexity** - Advanced features hidden until needed

### 8.4 Error Prevention
- **Quantity limits** - Can't add 5x Lightning Bolt (max 4 + basic lands)
- **Format warnings** - "This card is banned in Modern" before adding
- **Confirm destructive actions** - Delete deck requires Y/N confirmation
- **Auto-save** - Changes saved immediately (no "Save" button needed)

### 8.5 Efficiency for Experts
- **Vim-style navigation** - hjkl works everywhere
- **Compose shortcuts** - Ctrl+E, E, E, E = add 4 copies rapidly
- **Smart search** - "c:r cmc<=2 t:creature" finds exact cards fast
- **Bulk actions** - Select 10 cards, press S = move all to sideboard

### 8.6 Accessibility
- **High contrast mode** - For visually impaired users
- **Screen reader support** - Proper ARIA labels
- **Keyboard-only navigation** - Zero mouse required
- **Clear focus indicators** - Always know where you are
- **Reduced motion option** - Disable animations for sensitive users

---

## 9. Competitive Analysis

### 9.1 Moxfield (Web) - Strengths to Emulate

**What they do well:**
- **Drag-and-drop simplicity** - Cards move between sections effortlessly
  - *TUI equivalent:* Quick keyboard shortcuts (Space, 1-4, S for sideboard)
- **Real-time mana curve** - Updates as you add cards
  - *TUI equivalent:* Live stats panel with bar chart visualization
- **Powerful search engine** - Advanced filters (CMC, color, type)
  - *TUI equivalent:* QuickFilterBar + Scryfall syntax support
- **Playtesting mode** - Goldfish hands and mulligans
  - *Future feature:* Phase 8 (post-MVP)
- **Price integration** - TCGPlayer/Card Kingdom pricing
  - *TUI equivalent:* Already have Scryfall prices in mtg-core
- **Card packages** - Save common card groups (e.g., "Sol Ring + Signets")
  - *Future feature:* Phase 9 (templates/packages)

**What we can improve:**
- **Offline-first** - Moxfield requires internet; we work fully offline
- **Keyboard speed** - Web is mouse-heavy; we're keyboard-first (faster)
- **No ads/tracking** - Privacy-focused, local data only

### 9.2 Archidekt (Web) - Strengths to Emulate

**What they do well:**
- **Visual deck builder** - Card images in stacks (beautiful, tactile)
  - *TUI equivalent:* Art navigator integration (already have this!)
- **Custom categories** - Group cards by "Ramp", "Card Draw", etc.
  - *TUI equivalent:* Tag system + sortable groups
- **Collaboration features** - Real-time multi-user editing
  - *Future feature:* Out of scope (local-first design)
- **Collection tracking** - Mark cards as "owned"
  - *Future feature:* Phase 10 (collection management)

**What we can improve:**
- **Speed** - Archidekt can be slow with large decks; TUI is instant
- **Simplicity** - Archidekt has many features but cluttered UI; we focus on clarity

### 9.3 MTGO (Desktop) - Lessons Learned

**What they do well:**
- **Keyboard shortcuts** - Everything has a hotkey
  - *TUI equivalent:* Core design principle (keyboard-first)
- **Bulk add** - Type "4 Lightning Bolt" in deck editor
  - *TUI equivalent:* Import deck modal supports this format

**What they do poorly:**
- **Dated UI** - Looks like Windows 95
  - *TUI equivalent:* Modern Textual framework with rich colors/styling
- **Slow search** - Laggy card database
  - *TUI equivalent:* SQLite with FTS5 = instant search

### 9.4 Arena (Desktop) - User Experience Wins

**What they do well:**
- **Onboarding** - Clear tutorials and hints
  - *TUI equivalent:* Context-sensitive help (? key)
- **Visual feedback** - Satisfying animations (card flip, glow)
  - *TUI equivalent:* Smooth transitions, loading indicators

**What they do poorly:**
- **Limited deck building** - Can't build decks for formats Arena doesn't support
  - *TUI equivalent:* Support all MTG formats (Legacy, Vintage, Pauper, etc.)
- **No export** - Decks locked in Arena ecosystem
  - *TUI equivalent:* Import/export to any format (MTGO, plain text, etc.)

---

## 10. Success Metrics

### 10.1 Usability Metrics

**Time to Build First Deck (Casey persona):**
- Target: < 30 minutes for 60-card deck
- Measure: Time from app open to deck validation passing

**Time to Import Deck (Taylor persona):**
- Target: < 2 minutes from paste to validated deck
- Measure: Time from Ctrl+I to deck saved

**Search Efficiency (Morgan persona):**
- Target: Find card in deck list in < 10 seconds
- Measure: Time from search query to card selected

**Keyboard Coverage:**
- Target: > 95% of actions available via keyboard
- Measure: % of features with keyboard shortcuts

### 10.2 Feature Adoption

**Deck Builder Usage:**
- Target: 70% of users create at least 1 deck in first week
- Measure: User accounts with deck_count > 0

**Full Deck Builder Mode:**
- Target: 40% of deck edits happen in full-screen mode
- Measure: Sessions using FullDeckBuilder vs DeckEditorPanel

**Import/Export:**
- Target: 30% of decks are imported (not built from scratch)
- Measure: Decks created via ImportDeckModal vs manual creation

### 10.3 Quality Metrics

**Deck Validation Rate:**
- Target: 85% of completed decks are format-legal
- Measure: Decks with card_count = 60/100 that pass validation

**Card Accuracy:**
- Target: < 1% of added cards fail to load (card not found errors)
- Measure: Failed card additions / total card additions

**User Satisfaction:**
- Target: > 4.5 / 5 stars in user survey
- Measure: Post-usage survey (after building 3+ decks)

---

## 11. Future Enhancements (Post-MVP)

### Phase 8: Playtesting & Simulation
- **Goldfish mode** - Draw opening hands, mulligan, play turns
- **Statistics** - Track win rate, mulligan %, card draw frequency
- **Scenarios** - Test specific game situations

### Phase 9: Templates & Packages
- **Mana base templates** - "Modern RG Lands (8 fetch, 4 shock, 8 basic)"
- **Card packages** - "Commander Ramp Suite", "Counterspell Package"
- **Archetype templates** - "Burn (Modern)", "Elves (Legacy)"

### Phase 10: Collection Management
- **Owned cards** - Mark cards in collection
- **Missing cards** - Highlight cards needed to complete deck
- **Trade binders** - Manage cards available for trade
- **Price alerts** - Notify when card prices drop

### Phase 11: Deck Versioning
- **History tracking** - Save deck changes over time
- **Diff view** - Compare two deck versions
- **Revert changes** - Undo deck modifications
- **Branch decks** - Create variants (e.g., "Burn - Budget" vs "Burn - Optimized")

### Phase 12: Community Features (Optional)
- **Share decks** - Export to public URL (requires backend server)
- **Deck voting** - Upvote/downvote decks
- **Comments** - Discuss deck choices
- **Meta snapshots** - Import top tournament decks

### Phase 13: Advanced Analytics
- **Combo detection** - Identify infinite combos in deck
- **Synergy scoring** - AI-powered card recommendations
- **Meta analysis** - Compare deck to current metagame
- **Expected win rate** - Simulate vs popular decks

---

## 12. Accessibility Considerations

### 12.1 WCAG 2.1 AA Compliance

#### Color Contrast
- **Text:** 4.5:1 minimum contrast ratio
- **UI elements:** 3:1 minimum contrast ratio
- **High contrast mode:** User-toggleable theme with 7:1+ ratios

#### Keyboard Navigation
- **All features accessible** - Zero mouse required
- **Focus indicators** - Clear visual border on focused element
- **Tab order** - Logical flow (top-to-bottom, left-to-right)
- **Skip links** - Jump to main content (Ctrl+/)

#### Screen Reader Support
- **ARIA labels** - Descriptive labels for all interactive elements
- **Live regions** - Announce deck updates ("Card added to deck")
- **Semantic HTML** - Proper heading hierarchy (h1, h2, h3)
- **Alt text** - Card images have descriptive alt text

### 12.2 Inclusive Design

#### Visual Impairments
- **Large text mode** - Increase font size (Ctrl++)
- **Color-blind safe palette** - Avoid red/green only distinctions
- **Icons + text** - Never rely on color/icons alone

#### Motor Impairments
- **Sticky keys support** - Don't require simultaneous key presses
- **Adjustable repeat rate** - Customize key repeat for +/- shortcuts
- **Large click targets** - Buttons minimum 44x44 pixels (if using mouse)

#### Cognitive Considerations
- **Clear language** - Avoid jargon (e.g., "CMC" → "Mana Cost")
- **Consistent patterns** - Same action = same shortcut everywhere
- **Error recovery** - Easy undo for mistakes
- **Progressive disclosure** - Don't overwhelm with options

### 12.3 Localization (Future)
- **I18n support** - Externalize all strings
- **RTL layout** - Support right-to-left languages (Arabic, Hebrew)
- **Date/number formats** - Respect locale settings
- **Card translations** - Multi-language card names (via Scryfall)

---

## 13. Technical Constraints & Considerations

### 13.1 Terminal Limitations

**Character-based layout:**
- Can't use pixel-perfect positioning
- Grid-based layout (columns/rows)
- Solution: Embrace it! Terminal UIs are fast and accessible

**Limited colors:**
- Some terminals only support 16 colors
- True color (24-bit) not universally supported
- Solution: Degrade gracefully, test with 16-color palette

**No native drag-and-drop:**
- Mouse events vary by terminal emulator
- Solution: Keyboard-first design makes this irrelevant

**Variable terminal sizes:**
- Users may have 80x24 or 200x60 terminals
- Solution: Responsive layouts with collapsible panels

### 13.2 Performance Targets

**Search latency:**
- Target: < 50ms for search results
- SQLite with FTS5 achieves this easily

**Deck load time:**
- Target: < 100ms for 100-card deck
- Async loading + caching ensures speed

**UI responsiveness:**
- Target: < 16ms per frame (60 FPS)
- Textual's reactive rendering handles this

**Memory footprint:**
- Target: < 200 MB RAM for app + databases
- Python + SQLite are lightweight

### 13.3 Data Integrity

**Database transactions:**
- All deck modifications wrapped in transactions
- Prevent partial saves on crash

**Foreign key constraints:**
- Enforce referential integrity (card names must exist)
- Prevent orphaned deck cards

**Validation before save:**
- Client-side validation before database write
- Prevent invalid states

**Backup on destructive actions:**
- Auto-backup before deck deletion
- Allow recovery from mistakes

---

## 14. Open Questions & Decisions Needed

### 14.1 UX Decisions

**Q1: Should we support drag-and-drop (mouse)?**
- Pro: Intuitive for mouse users, matches web experience
- Con: Complex to implement, not all terminals support it
- **Recommendation:** Phase 9+ (nice-to-have, not essential)

**Q2: How many decks should be visible in sidebar?**
- Option A: Show all (scrollable list)
- Option B: Show recent 10, rest in "More" section
- **Recommendation:** Option A with smart sorting (recently edited first)

**Q3: Should deck builder mode be modal (full-screen) or inline?**
- Option A: Full-screen dedicated mode (like Vim)
- Option B: Expand card panel into deck editor
- **Recommendation:** Both! Ctrl+D for inline, Shift+D for full-screen

**Q4: Support for custom card categories (like Archidekt)?**
- E.g., group cards as "Ramp", "Card Draw", "Removal"
- **Recommendation:** Yes, but Phase 9+ (post-MVP)

### 14.2 Technical Decisions

**Q5: How to handle large decks (200+ card Commander decks)?**
- Virtualized list (only render visible cards)?
- Pagination (show 20 at a time)?
- **Recommendation:** Virtualized list with instant search/filter

**Q6: Cache card images for offline use?**
- Pro: Faster load times, works offline
- Con: Disk space (100 MB+ for popular decks)
- **Recommendation:** Yes, with configurable cache size limit

**Q7: Support for deck "folders" or hierarchical organization?**
- E.g., "Modern > Aggro > Burn"
- **Recommendation:** Yes, via tag system (tags can be hierarchical)

**Q8: Allow editing deck metadata (name, format) after creation?**
- **Recommendation:** Yes, via Edit action (E key) on deck list

---

## 15. Comparative UX Table

| Feature | Moxfield | Archidekt | MTGO | MTG Spellbook (Proposed) |
|---------|----------|-----------|------|--------------------------|
| **Deck Creation** | ✓ | ✓ | ✓ | ✓ |
| **Visual Deck Builder** | ✓ | ✓ | ✗ | ✓ (split-pane mode) |
| **Real-time Mana Curve** | ✓ | ✓ | ✗ | ✓ |
| **Price Integration** | ✓ | ✓ | ✗ | ✓ (Scryfall) |
| **Import/Export** | ✓ | ✓ | ✓ | ✓ |
| **Playtesting** | ✓ | ✓ | ✓ | Phase 8+ |
| **Collection Tracking** | ✓ | ✓ | ✓ | Phase 10+ |
| **Keyboard Shortcuts** | Limited | Limited | ✓ | ✓ (comprehensive) |
| **Offline Mode** | ✗ | ✗ | ✗ | ✓ |
| **Deck Validation** | ✓ | ✓ | ✗ | ✓ |
| **Card Comparison** | ✗ | ✗ | ✗ | ✓ |
| **Tag System** | ✓ | ✓ | ✗ | ✓ |
| **Bulk Operations** | ✗ | ✗ | ✓ | ✓ |
| **Responsive Design** | ✓ | ✓ | ✗ | ✓ (terminal-aware) |
| **Accessibility** | Partial | Partial | Poor | ✓ (WCAG 2.1 AA) |

---

## 16. User Feedback Integration Plan

### 16.1 Beta Testing Program

**Phase 1: Internal Testing (Week 8)**
- Test with 3-5 MTG players on dev team
- Focus on core workflows (create, edit, validate)
- Gather qualitative feedback (interviews)

**Phase 2: Closed Beta (Week 9)**
- Invite 20-30 users from MTG community
- Mix of casual/competitive players
- Use telemetry (opt-in) to track feature usage

**Phase 3: Open Beta (Week 10)**
- Public release to /r/magicTCG community
- Feedback via Discord, GitHub issues
- Iterate based on most-requested features

### 16.2 Feedback Channels

**In-App Feedback:**
- `Ctrl+Shift+F` - Send feedback modal
- Auto-include: OS, terminal, deck count, feature being used

**Community Forums:**
- Discord server: #deck-builder channel
- GitHub Discussions: Q&A, feature requests
- Reddit: Weekly feedback thread

**Analytics (Privacy-First):**
- Opt-in anonymous usage stats
- Track: feature adoption, error rates, session length
- Never track: deck contents, card searches, personal data

### 16.3 Iteration Cadence

**Weekly releases:**
- Bug fixes deployed within 48 hours
- Minor features every Friday
- Major features every 2 weeks

**User surveys:**
- After 1 week of use
- After 1 month of use
- After 50 decks built

**Feature prioritization:**
- Vote on feature requests (GitHub Discussions)
- Top 5 most-voted features added to roadmap

---

## 17. Conclusion & Next Steps

### 17.1 Summary

This proposal outlines a comprehensive, terminal-native deck building experience that:

1. **Matches web-based tools** - Feature parity with Moxfield/Archidekt
2. **Leverages TUI strengths** - Keyboard-first, offline, fast, accessible
3. **Integrates seamlessly** - Feels like natural extension of existing app
4. **Scales with users** - Beginner-friendly, expert-optimized
5. **Follows best practices** - WCAG 2.1 AA, progressive disclosure, immediate feedback

### 17.2 Immediate Next Steps

**Step 1: Review & Approval**
- Review this proposal with stakeholders
- Gather feedback on wireframes, user journeys
- Prioritize must-have vs nice-to-have features

**Step 2: Technical Spike (Week 0)**
- Prototype FullDeckBuilder layout in Textual
- Test split-pane rendering on 80x24 terminal
- Validate database schema with sample decks

**Step 3: Begin Phase 1 (Week 1)**
- Implement DeckListPanel
- Implement AddToDeckModal
- Wire up app integration
- Release MVP to internal testers

### 17.3 Success Criteria

**MVP is complete when:**
- Users can create decks
- Users can add cards from search results
- Users can view deck contents
- Users can validate decks
- Users can import/export decklists

**Product is production-ready when:**
- All 7 implementation phases complete
- WCAG 2.1 AA compliant
- Beta tested with 50+ users
- < 5 critical bugs in issue tracker
- Average user rating > 4.5 / 5

---

## 18. Appendix

### A. Glossary

| Term | Definition |
|------|------------|
| **CMC** | Converted Mana Cost (total mana cost of a card) |
| **Mainboard** | Primary 60/100 cards in deck |
| **Sideboard** | Optional 15 cards swapped between games |
| **Format** | Rules set (Standard, Modern, Commander, etc.) |
| **Singleton** | Deck rule requiring only 1 copy of each card |
| **Mana Curve** | Distribution of cards by CMC |
| **Color Identity** | All colors in card's mana cost + rules text |
| **TUI** | Text/Terminal User Interface |
| **WCAG** | Web Content Accessibility Guidelines |

### B. Card Count Requirements by Format

| Format | Mainboard | Sideboard | Special Rules |
|--------|-----------|-----------|---------------|
| Standard | 60+ | 0-15 | Max 4 copies |
| Modern | 60+ | 0-15 | Max 4 copies |
| Legacy | 60+ | 0-15 | Max 4 copies |
| Vintage | 60+ | 0-15 | Max 4 copies, restricted list |
| Commander | 99 | 0 | Singleton, 1 commander |
| Pauper | 60+ | 0-15 | Commons only, max 4 copies |
| Pioneer | 60+ | 0-15 | Max 4 copies |

### C. File Size Estimates

| Component | Lines of Code | Estimated Dev Time |
|-----------|---------------|-------------------|
| DeckListPanel | 150 | 2 days |
| DeckEditorPanel | 250 | 4 days |
| FullDeckBuilder | 400 | 6 days |
| AddToDeckModal | 100 | 1 day |
| DeckAnalysisModal | 300 | 4 days |
| ImportDeckModal | 200 | 3 days |
| ExportDeckModal | 100 | 1 day |
| DeckStatsPanel | 200 | 3 days |
| QuickFilterBar | 150 | 2 days |
| CardComparisonPanel | 250 | 4 days |
| DeckTagEditor | 100 | 1 day |
| **Total** | **2,200** | **31 days** |

Add 30% for testing, polish, docs = **40 days total**

### D. Resources & References

**Design Inspiration:**
- [Moxfield - MTG Deck Builder](https://moxfield.com/)
- [Archidekt - Visual Deckbuilder](https://archidekt.com/)
- [Draftsim - Best MTG Deck Builder Review](https://draftsim.com/best-mtg-deck-builder/)
- [EDHREC - Collaborating on Archidekt](https://edhrec.com/articles/digital-deckbuilding-collaborating-on-archidekt/)

**TUI Best Practices:**
- [Awesome TUIs - GitHub](https://github.com/rothgar/awesome-tuis)
- [Textual Documentation](https://textual.textualize.io/)
- [7 TUI Libraries for Interactive Terminal Apps](https://blog.logrocket.com/7-tui-libraries-interactive-terminal-apps/)
- [Terminal.Gui - TUI Patterns](https://blog.ironmansoftware.com/tui-powershell/)

**Accessibility Guidelines:**
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Inclusive Design Principles](https://inclusivedesignprinciples.org/)

---

**Document Version:** 1.0
**Last Updated:** 2025-12-14
**Author:** MTG Spellbook UX Team
**Status:** Ready for Review
