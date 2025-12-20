# Artist Discovery & Set Exploration Features
## Design Proposal for MTG Spellbook TUI

**Version:** 1.0
**Date:** 2025-12-14
**Status:** Proposal

---

## Executive Summary

This document outlines the design for two major feature expansions in MTG Spellbook:

1. **Artist Discovery & Exploration** - Turn artwork into a discovery pathway
2. **Set Browsing & Exploration** - Make sets first-class citizens in the app

Both features leverage existing database capabilities (2,245 unique artists, 600+ sets) and follow TUI-first design principles emphasizing keyboard navigation, progressive disclosure, and screen real estate optimization.

---

## Table of Contents

1. [Feature Prioritization](#feature-prioritization)
2. [Artist Discovery Features](#artist-discovery-features)
3. [Set Exploration Features](#set-exploration-features)
4. [Integration Points](#integration-points)
5. [Keyboard Shortcuts](#keyboard-shortcuts)
6. [Implementation Phases](#implementation-phases)

---

## Feature Prioritization

### Phase 1: Foundation (MVP - Week 1-2)

**Artist Features:**
- Artist portfolio/gallery view (search cards by artist)
- Artist statistics panel (card count, sets, formats)
- Enhanced "Enter: explore" from art tab

**Set Features:**
- Set browser with visual set symbols
- Set details panel (stats, metadata)
- Browse cards in a set

**Rationale:** Build on existing infrastructure (artist field, set data already in DB). Minimal new database queries needed.

---

### Phase 2: Enhanced Discovery (Week 3-4)

**Artist Features:**
- Artist search/browse functionality
- Random artist exploration
- Artist spotlight mode

**Set Features:**
- Block browsing (group related sets)
- Set timeline/history view
- New releases highlight

**Rationale:** Enhances core features with more sophisticated discovery mechanisms.

---

### Phase 3: Advanced Features (Week 5+)

**Artist Features:**
- Similar artists recommendations (via shared sets, styles)
- Favorite artists list (requires user DB)
- Art style categorization (metadata enhancement)

**Set Features:**
- Set comparison tool
- Set completion tracking (requires user collection DB)
- Format-specific set filtering
- Price analytics by set

**Rationale:** Requires additional database tables, metadata enrichment, or third-party APIs.

---

## Artist Discovery Features

### 1. Artist Portfolio View

**Purpose:** Display all cards illustrated by a specific artist, transforming artwork into a discovery pathway.

**User Flow:**
```
1. User views card in Art tab
2. Artist name displayed: "Artist: Rebecca Guay"
3. User presses ENTER → "Explore artist: Rebecca Guay"
4. App shows artist portfolio view with all Rebecca Guay cards
5. User can browse gallery, filter by set/format, view stats
```

**Wireframe: Artist Portfolio Screen**
```
┌─ MTG SPELLBOOK ─────────────────────────────────────────────────────────────────┐
│ 🎨 Artist: Rebecca Guay                                    [ctrl+f] Filter Sets │
├─────────────────────────────────────────────────────────────────────────────────┤
│ ┌─ Statistics ──────────────┬─ Gallery (24 cards) ──────────────────────────┐  │
│ │                            │                                               │  │
│ │  Cards Illustrated:   47   │  [◆] Path to Exile    [◆] Enchantress's...   │  │
│ │  Sets Featured:       18   │   UMA · Uncommon        ONS · Rare            │  │
│ │  First Card:    1997 (5E)  │                                               │  │
│ │  Most Recent:  2019 (MH1)  │  [◆] Dark Ritual      [◆] Abundance          │  │
│ │                            │   JUD · Common           10E · Rare           │  │
│ │  Top Formats:              │                                               │  │
│ │   • Legacy         (34)    │  [◆] Priest of Titania [◆] Rancor           │  │
│ │   • Vintage        (34)    │   UDS · Common           ULG · Common         │  │
│ │   • Commander      (42)    │                                               │  │
│ │                            │  ▼ Scroll for more (Page 1 of 2)             │  │
│ │  Signature Styles:         │                                               │  │
│ │   • Ethereal               │                                               │  │
│ │   • Watercolor             └───────────────────────────────────────────────┘  │
│ │   • Fairy Tale             ┌─ Card Detail ───────────────────────────────┐  │
│ │                            │                                              │  │
│ └────────────────────────────┤  [Selected card details shown here]          │  │
│                               │                                              │  │
│                               │  → Press TAB to view artwork                 │  │
│                               └──────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ ⚡ :artist search query   [↑↓] Navigate  [Enter] Select  [Esc] Back  [Tab] Art │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Key Components:**
- **Statistics Panel** (left 30%): Artist bio data
  - Total cards illustrated
  - Sets featured in
  - Timeline (first/most recent card)
  - Format breakdown
  - Signature styles (future: metadata-driven)

- **Gallery Grid** (center 45%): Scrollable card thumbnails
  - Compact card representation: `[◆] Name` + set + rarity
  - Pagination for large artist portfolios
  - Sort options: Chronological, Alphabetical, Set, Format

- **Detail Panel** (right 25%): Selected card info
  - Full card details
  - Quick access to Art tab
  - Artist notes/trivia (future)

**Navigation:**
- `↑↓` - Navigate gallery
- `Enter` - Select card (load in detail panel)
- `Tab` - Switch to Art tab for selected card
- `ctrl+f` - Filter by set/format/type
- `r` - Random card by this artist
- `Esc` - Return to previous view

---

### 2. Artist Search & Browse

**Purpose:** Discover new artists without needing a specific card first.

**User Flow:**
```
1. User types: :artists [optional search term]
2. App shows alphabetical artist list (2,245 artists)
3. User can filter/search: :artists rebecca
4. User selects artist → Portfolio view opens
```

**Wireframe: Artist Browser**
```
┌─ MTG SPELLBOOK ─────────────────────────────────────────────────────────────────┐
│ 🎨 Artist Browser (2,245 artists)                        [/] Search  [r] Random │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  A                                                                               │
│  ├─ Aaron Miller (23 cards)                                                     │
│  ├─ Adam Paquette (187 cards)                                                   │
│  ├─ Adam Rex (8 cards)                                                          │
│  ├─ Adrian Smith (42 cards)                                                     │
│  └─ Aleksi Briclot (76 cards)                                                   │
│                                                                                  │
│  B                                                                               │
│  ├─ Ben Thompson (14 cards)                                                     │
│  ├─ Brad Rigney (98 cards)                                                      │
│  └─ Brian Snoddy (156 cards)                                                    │
│                                                                                  │
│  [R]                                                                             │
│  ├─ Randy Gallegos (34 cards)                                                   │
│  ├─ Raymond Swanland (189 cards)                                                │
│  ├─▶ Rebecca Guay (47 cards) ◀─────────────────────────── [Selected]           │
│  └─ Rob Alexander (129 cards)                                                   │
│                                                                                  │
│  ▼ More artists... (showing 15 of 2,245)                                        │
│                                                                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ ⚡ :artists [name]   [↑↓] Navigate  [Enter] View Portfolio  [/] Filter  [r] Rnd│
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Features:**
- Alphabetical grouping with letter headers
- Card count per artist
- Incremental search filter
- Random artist button for discovery
- Fast keyboard navigation (type letter to jump)

---

### 3. Artist Spotlight Mode

**Purpose:** Featured artist showcase for discovery.

**User Flow:**
```
1. User types: :artist-spotlight or presses ctrl+shift+a
2. App randomly selects an artist with 20+ cards
3. Shows curated "spotlight" view with highlights
4. User can browse portfolio or shuffle to new artist
```

**Wireframe: Artist Spotlight**
```
┌─ MTG SPELLBOOK ─────────────────────────────────────────────────────────────────┐
│ ✨ Artist Spotlight                                    [space] Next  [Esc] Exit │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│                           🎨  John Avon                                          │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  Known for stunning landscape artworks and iconic basic lands           │   │
│  │                                                                          │   │
│  │  Career Highlights:                                                     │   │
│  │   • 342 cards illustrated (1996-2024)                                   │   │
│  │   • Featured in 87 different sets                                       │   │
│  │   • Legendary for Unhinged/Unglued full-art basic lands                │   │
│  │   • Notable works: Wrath of God, Damnation, Flooded Strand             │   │
│  │                                                                          │   │
│  │  Signature Style: Photorealistic landscapes, dramatic lighting          │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  Featured Cards:                                                                │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐                 │
│  │ [◆] Wrath    │ [◆] Island   │ [◆] Flooded  │ [◆] Plains   │                 │
│  │   of God     │   (UNH)      │   Strand     │   (ZEN)      │                 │
│  │   10E · Rare │   Basic      │   EXP · Rare │   Basic      │                 │
│  └──────────────┴──────────────┴──────────────┴──────────────┘                 │
│                                                                                  │
│  [Enter] View Full Portfolio  [space] Next Artist  [r] Random  [Esc] Close     │
│                                                                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ ⚡ Discover artists and their incredible MTG artwork                            │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Features:**
- Artist bio/description (curated text or community-sourced)
- Key statistics
- "Featured Cards" carousel (most iconic/popular)
- Shuffle to next artist
- Quick jump to full portfolio

---

### 4. Similar Artists (Phase 3)

**Purpose:** Recommend artists with similar styles or themes.

**Algorithm Ideas:**
- **Shared Sets:** Artists who worked on the same sets
- **Shared Formats:** Artists whose cards appear in same formats
- **Metadata Tags:** Style tags (watercolor, digital, dark fantasy, etc.)
- **Community Data:** Integration with EDHRec or Scryfall artist data

**Implementation:** Requires metadata enrichment or third-party API integration.

---

## Set Exploration Features

### 1. Set Browser

**Purpose:** Browse all MTG sets with filtering and search.

**User Flow:**
```
1. User types: :sets or presses ctrl+shift+s
2. App displays chronological set list
3. User can filter by type, block, year
4. User selects set → Set detail view opens
```

**Wireframe: Set Browser**
```
┌─ MTG SPELLBOOK ─────────────────────────────────────────────────────────────────┐
│ 📚 Set Browser (628 sets)          [t] Type  [b] Block  [y] Year  [/] Search   │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Filter: All Types ▼  │  Sort: Chronological ▼                                  │
├──────────────────────┴──────────────────────────────────────────────────────────┤
│                                                                                  │
│  2024                                                                            │
│  ├─ [MKM] Murders at Karlov Manor         (Feb 9, 2024)  [Expansion] ⚡         │
│  ├─ [OTJ] Outlaws of Thunder Junction     (Apr 19, 2024) [Expansion]           │
│  └─ [MH3] Modern Horizons 3               (Jun 14, 2024) [Masters]             │
│                                                                                  │
│  2023                                                                            │
│  ├─ [LTR] The Lord of the Rings           (Jun 23, 2023) [Expansion]           │
│  ├─ [WOE] Wilds of Eldraine               (Sep 8, 2023)  [Expansion]           │
│  └─ [LCI] The Lost Caverns of Ixalan      (Nov 17, 2023) [Expansion]           │
│                                                                                  │
│  2022                                                                            │
│  ├─ [NEO] Kamigawa: Neon Dynasty          (Feb 18, 2022) [Expansion]           │
│  ├─▶ [SNC] Streets of New Capenna ◀────────────────────── [Selected]           │
│  │    (Apr 29, 2022) [Expansion] - 281 cards                                   │
│  ├─ [DMU] Dominaria United                (Sep 9, 2022)  [Expansion]           │
│  └─ [BRO] The Brothers' War               (Nov 18, 2022) [Expansion]           │
│                                                                                  │
│  ▼ Earlier sets... (showing 12 of 628)                                          │
│                                                                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ ⚡ :sets [name]   [↑↓] Navigate  [Enter] View Set  [t/b/y] Filter  [r] Random  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Features:**
- Chronological display (newest first, configurable)
- Year grouping headers
- Set code, name, date, type
- Visual indicators for special sets (⚡ = Standard legal, 🎭 = Un-set, etc.)
- Filter by:
  - Type: Expansion, Core, Masters, Commander, etc.
  - Block: Innistrad, Ravnica, etc.
  - Year: 2024, 2023, etc.
- Search by name or code
- Random set exploration

---

### 2. Set Detail View

**Purpose:** Comprehensive set information and card browsing.

**User Flow:**
```
1. User selects set from browser
2. App shows set details + card gallery
3. User can browse all cards in set
4. User can filter by rarity, color, type
```

**Wireframe: Set Detail View**
```
┌─ MTG SPELLBOOK ─────────────────────────────────────────────────────────────────┐
│ 📦 Streets of New Capenna (SNC)                      [ctrl+b] Browse Cards      │
├─────────────────────────────────────────────────────────────────────────────────┤
│ ┌─ Set Information ────────────┬─ Cards in Set (281) ──────────────────────┐  │
│ │                               │ Filter: All ▼  Rarity: All ▼  Color: All▼│  │
│ │  Code:         SNC            ├───────────────────────────────────────────┤  │
│ │  Released:     Apr 29, 2022   │                                           │  │
│ │  Type:         Expansion      │  [M] Jetmir, Nexus of Revels (Mythic)    │  │
│ │  Block:        —              │  [M] Ob Nixilis, the Adversary (Mythic)  │  │
│ │  Cards:        281            │  [M] Elspeth Resplendent (Mythic)        │  │
│ │  Format:       Standard ✓     │  [R] Ledger Shredder (Rare)              │  │
│ │                Pioneer ✓      │  [R] Bootleggers' Stash (Rare)           │  │
│ │                Modern ✓       │  [R] Cityscape Leveler (Rare)            │  │
│ │                               │  [U] Brokers Ascendancy (Uncommon)       │  │
│ │  Theme:        Art Deco crime │  [U] Maestros Ascendancy (Uncommon)      │  │
│ │                families, 1920s│  [U] Obscura Ascendancy (Uncommon)       │  │
│ │                gangsters      │  [C] Devilish Valet (Common)             │  │
│ │                               │  [C] Jewel Thief (Common)                │  │
│ │  Mechanics:                   │                                           │  │
│ │   • Alliance                  │  ▼ Scroll for more (Page 1 of 12)        │  │
│ │   • Blitz                     │                                           │  │
│ │   • Casualty                  └───────────────────────────────────────────┘  │
│ │   • Connive                   ┌─ Selected Card ─────────────────────────┐  │
│ │   • Shield Counters           │                                          │  │
│ │                               │  Ledger Shredder  {1}{U}                 │  │
│ └───────────────────────────────┤  Creature - Bird Advisor                 │  │
│                                 │  Rare                                    │  │
│                                 │                                          │  │
│                                 │  Flying                                  │  │
│                                 │  Whenever a player casts their second... │  │
│                                 │                                          │  │
│                                 │  → Press TAB for full details            │  │
│                                 └──────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ ⚡ [↑↓] Navigate  [Enter] View Card  [r] Random  [c] Compare  [Esc] Back       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Features:**
- **Set Metadata Panel** (left 30%):
  - Code, name, release date, type, block
  - Total cards count
  - Format legality indicators
  - Set theme/description
  - Mechanics/keywords introduced
  - Set symbol (ASCII art or Unicode)

- **Card Gallery** (center 45%):
  - All cards in set, sortable/filterable
  - Rarity indicators: [M] [R] [U] [C]
  - Color filtering
  - Type filtering (Creature, Instant, etc.)
  - Search within set

- **Card Preview** (right 25%):
  - Quick preview of selected card
  - Jump to full card view

**Navigation:**
- `↑↓` - Browse cards
- `Enter` - Load full card details
- `r` - Random card from set
- `ctrl+f` - Filter cards
- `c` - Compare with another set (Phase 3)

---

### 3. Block Browser (Phase 2)

**Purpose:** Browse sets grouped by storyline/block.

**Example Blocks:**
- Innistrad (ISD, DKA, AVR, SOI, EMN, MID, VOW)
- Ravnica (RAV, GPT, DIS, RTR, GTC, DGM, GRN, RNA, WAR)
- Phyrexia (DMU, BRO, ONE, MOM)

**Wireframe Concept:**
```
┌─ Block Browser ──────────────────────────────────┐
│                                                   │
│  Innistrad Block (7 sets across 3 visits)        │
│  ├─ Original Innistrad (2011-2012)               │
│  │   ├─ [ISD] Innistrad                          │
│  │   ├─ [DKA] Dark Ascension                     │
│  │   └─ [AVR] Avacyn Restored                    │
│  ├─ Shadows Block (2016)                         │
│  │   ├─ [SOI] Shadows over Innistrad             │
│  │   └─ [EMN] Eldritch Moon                      │
│  └─ Midnight Hunt / Crimson Vow (2021)           │
│      ├─ [MID] Innistrad: Midnight Hunt           │
│      └─ [VOW] Innistrad: Crimson Vow             │
│                                                   │
└───────────────────────────────────────────────────┘
```

---

### 4. Set Timeline (Phase 2)

**Purpose:** Visual chronological set history.

**Features:**
- Horizontal timeline (1993 → Present)
- Zoom in/out by decade
- Highlight major events (first Commander set, first Planeswalker, etc.)
- Filter by set type while maintaining timeline

---

### 5. New Releases Highlight (Phase 2)

**Purpose:** Quickly see latest sets.

**Wireframe Concept:**
```
┌─ New Releases ──────────────────────────────┐
│                                              │
│  🆕 Latest Standard Sets                    │
│  ├─ [MKM] Murders at Karlov Manor (Feb 24)  │
│  ├─ [OTJ] Outlaws Thunder Junction (Apr 24) │
│  └─ [MH3] Modern Horizons 3 (Jun 24)        │
│                                              │
│  📅 Upcoming Releases                        │
│  └─ [FDN] Foundations (Nov 15, 2024)        │
│                                              │
└──────────────────────────────────────────────┘
```

---

### 6. Set Comparison Tool (Phase 3)

**Purpose:** Compare statistics between two sets.

**Comparison Metrics:**
- Card count, rarity distribution
- Average CMC
- Color distribution
- Price range (min/avg/max)
- Shared mechanics
- Power level indicators (EDHRec rank)

---

### 7. Set Completion Tracking (Phase 3)

**Purpose:** Track personal collection progress per set.

**Requirements:**
- User collection database
- Card ownership tracking
- Progress visualization

**Wireframe Concept:**
```
┌─ Set Completion: Streets of New Capenna ────┐
│                                              │
│  Progress: 134 / 281 cards (48%)            │
│  ████████████░░░░░░░░░░░░░                  │
│                                              │
│  By Rarity:                                  │
│   Mythic:      3 / 20  (15%) ███░░░░░░      │
│   Rare:       12 / 60  (20%) ████░░░░░      │
│   Uncommon:   48 / 80  (60%) ████████░      │
│   Common:     71 / 121 (59%) █████████      │
│                                              │
│  Missing High-Value Cards:                   │
│   • Jetmir, Nexus of Revels ($24)           │
│   • Ledger Shredder ($18)                   │
│                                              │
└──────────────────────────────────────────────┘
```

---

## Integration Points

### 1. Existing Features → Artist/Set Discovery

| Current Feature | Integration Point | New Capability |
|----------------|-------------------|----------------|
| **Art Tab** | Artist name display | Press `Enter` → Artist Portfolio |
| **Card Details** | Set code display | Press `s` → Set Detail View |
| **Search Results** | Set filter | Quick jump to Set Browser |
| **Synergy Mode** | Common sets | "Artists who collaborated on this set" |

---

### 2. Database Queries Required

**Artist Features:**
```sql
-- Get all cards by artist
SELECT * FROM cards WHERE artist = ? ORDER BY releaseDate

-- Count cards per artist
SELECT artist, COUNT(*) as card_count
FROM cards
WHERE artist IS NOT NULL
GROUP BY artist
ORDER BY card_count DESC

-- Get artist statistics
SELECT
    artist,
    COUNT(DISTINCT setCode) as sets_count,
    MIN(releaseDate) as first_card,
    MAX(releaseDate) as most_recent
FROM cards
WHERE artist = ?
GROUP BY artist
```

**Set Features:**
```sql
-- Get all cards in a set
SELECT * FROM cards WHERE setCode = ? ORDER BY number

-- Get set rarity distribution
SELECT rarity, COUNT(*) as count
FROM cards
WHERE setCode = ?
GROUP BY rarity

-- Get sets by block
SELECT * FROM sets WHERE block = ? ORDER BY releaseDate
```

**New Database Functions Needed:**
- `MTGDatabase.get_cards_by_artist(artist: str) -> list[Card]`
- `MTGDatabase.get_artist_stats(artist: str) -> ArtistStats`
- `MTGDatabase.get_all_artists() -> list[ArtistSummary]`
- `MTGDatabase.get_cards_in_set(set_code: str) -> list[Card]`
- `MTGDatabase.get_sets_by_block(block: str) -> list[Set]`

---

### 3. New Models Required

```python
# Artist models
class ArtistSummary(BaseModel):
    name: str
    card_count: int
    sets_count: int
    first_card_year: int | None
    most_recent_year: int | None

class ArtistStats(BaseModel):
    name: str
    total_cards: int
    sets_featured: list[str]
    first_card_date: str | None
    most_recent_date: str | None
    format_distribution: dict[str, int]  # {"commander": 42, "modern": 38, ...}
    signature_styles: list[str] = []  # Future: metadata-driven

class ArtistPortfolio(BaseModel):
    artist: ArtistSummary
    stats: ArtistStats
    cards: list[CardSummary]  # All cards by artist

# Set models (extend existing)
class SetStats(BaseModel):
    total_cards: int
    rarity_distribution: dict[str, int]  # {"mythic": 20, "rare": 60, ...}
    color_distribution: dict[str, int]   # {"W": 45, "U": 40, ...}
    mechanics: list[str]
    avg_cmc: float | None

class BlockSummary(BaseModel):
    name: str
    sets: list[SetSummary]
    total_cards: int
    year_range: tuple[int, int]  # (2011, 2012)
```

---

### 4. UI Components

**New Widgets:**
- `ArtistPortfolioView(Vertical)` - Artist portfolio screen
- `ArtistBrowser(Vertical)` - Artist list browser
- `ArtistStatsPanel(Vertical)` - Statistics display
- `SetBrowser(Vertical)` - Set list browser
- `SetDetailView(Vertical)` - Set detail screen
- `BlockBrowser(Vertical)` - Block grouping view
- `SetTimeline(Horizontal)` - Chronological timeline

**Existing Widgets to Extend:**
- `CardPanel` - Add "Press `s` for set details"
- `EnhancedArtNavigator` - Enhance "Explore artist" prompt
- `ResultsList` - Support artist/set list items

---

### 5. Command System Extensions

**New Commands:**
```python
# Artist commands
:artist <name>           # Search for artist, show portfolio
:artists                 # Browse all artists
:artist-spotlight        # Random artist showcase

# Set commands
:set <code>              # Show set details
:sets                    # Browse all sets
:sets type:expansion     # Filter by type
:sets block:innistrad    # Filter by block
:sets year:2024          # Filter by year
:blocks                  # Browse blocks
:timeline                # Set timeline view
```

**Command Mixins:**
```python
class ArtistCommandsMixin:
    @work
    async def show_artist(self, name: str) -> None: ...

    @work
    async def browse_artists(self) -> None: ...

    @work
    async def random_artist(self) -> None: ...

class SetCommandsMixin:  # Extend existing
    @work
    async def browse_sets(self, filters: dict) -> None: ...

    @work
    async def show_set_detail(self, code: str) -> None: ...

    @work
    async def browse_blocks(self) -> None: ...
```

---

## Keyboard Shortcuts

### Global Shortcuts (App Level)

| Key | Action | Context |
|-----|--------|---------|
| `ctrl+shift+a` | Open Artist Browser | Anywhere |
| `ctrl+shift+s` | Open Set Browser | Anywhere |
| `ctrl+shift+b` | Open Block Browser | Anywhere |

### Context-Specific Shortcuts

**In Art Tab:**
| Key | Action |
|-----|--------|
| `Enter` | Explore artist (open portfolio) |
| `a` | Toggle artist info panel |

**In Card Detail:**
| Key | Action |
|-----|--------|
| `s` | View set details |
| `a` | View artist portfolio |

**In Artist Portfolio:**
| Key | Action |
|-----|--------|
| `↑↓` | Navigate card gallery |
| `Enter` | Select card |
| `Tab` | Switch to art view |
| `r` | Random card by artist |
| `ctrl+f` | Filter by set/format |
| `Esc` | Return to previous view |

**In Set Browser:**
| Key | Action |
|-----|--------|
| `↑↓` | Navigate sets |
| `Enter` | Open set details |
| `t` | Filter by type |
| `b` | Filter by block |
| `y` | Filter by year |
| `/` or `ctrl+f` | Search sets |
| `r` | Random set |

**In Set Detail:**
| Key | Action |
|-----|--------|
| `↑↓` | Navigate cards in set |
| `Enter` | View card details |
| `r` | Random card from set |
| `c` | Compare with another set (Phase 3) |
| `ctrl+f` | Filter cards |
| `Esc` | Return to set browser |

---

## Implementation Phases

### Phase 1: Foundation (MVP - 2 weeks)

**Week 1: Database & Models**
- [ ] Add artist database methods to `MTGDatabase`
  - `get_cards_by_artist(artist: str)`
  - `get_artist_stats(artist: str)`
  - `get_all_artists()`
- [ ] Add set database methods
  - `get_cards_in_set(set_code: str)`
  - `get_set_stats(set_code: str)`
- [ ] Create Pydantic models: `ArtistSummary`, `ArtistStats`, `SetStats`
- [ ] Add artist/set tools to `mtg_core/tools/`

**Week 2: UI Components**
- [ ] Build `ArtistPortfolioView` widget
- [ ] Build `SetDetailView` widget
- [ ] Add "Enter: explore artist" to `EnhancedArtNavigator`
- [ ] Add "Press `s` for set details" to `CardPanel`
- [ ] Implement basic artist/set commands
- [ ] Add keyboard shortcuts

**Testing Priorities:**
- Database query performance (artist with 300+ cards)
- Gallery pagination (sets with 250+ cards)
- Keyboard navigation responsiveness

---

### Phase 2: Enhanced Discovery (2 weeks)

**Week 3: Browsers & Search**
- [ ] Build `ArtistBrowser` with alphabetical listing
- [ ] Build `SetBrowser` with filters (type, block, year)
- [ ] Add artist search functionality
- [ ] Add set search/filter UI
- [ ] Implement `BlockBrowser` for grouped sets
- [ ] Add "New Releases" highlight

**Week 4: Advanced Views**
- [ ] Build `ArtistStatsPanel` with detailed analytics
- [ ] Build `SetTimeline` chronological view
- [ ] Add random artist/set exploration
- [ ] Polish filtering and sorting
- [ ] Add artist spotlight mode

---

### Phase 3: Advanced Features (3+ weeks)

**Week 5: Recommendations & Analytics**
- [ ] Similar artists algorithm (shared sets/formats)
- [ ] Set comparison tool (side-by-side stats)
- [ ] Enhanced set statistics (power level, price analytics)
- [ ] Format-specific filtering

**Week 6+: User Personalization**
- [ ] Favorite artists list (requires user DB)
- [ ] Set completion tracking (requires collection DB)
- [ ] Art style categorization (metadata or ML)
- [ ] Community integration (EDHRec, Scryfall API)

---

## Success Metrics

**Artist Features:**
- [ ] Users can discover all 2,245+ artists
- [ ] Average load time < 200ms for artist portfolio
- [ ] Support artists with 1-500+ cards efficiently
- [ ] Keyboard navigation feels instant

**Set Features:**
- [ ] Users can browse all 628+ sets
- [ ] Set detail view loads < 100ms
- [ ] Card filtering within set feels responsive
- [ ] Block/timeline views enhance discovery

**User Experience:**
- [ ] Zero mouse required for all operations
- [ ] Consistent keyboard shortcuts across views
- [ ] Clear visual hierarchy in all screens
- [ ] Progressive disclosure (stats → details → full view)

---

## Technical Considerations

### Performance Optimization

1. **Lazy Loading:** Load card details on demand (summaries first)
2. **Caching:** Cache artist/set queries (60s TTL)
3. **Pagination:** Limit gallery views to 25-50 items per page
4. **Indexing:** Ensure `artist` and `setCode` columns indexed in DB

### Screen Real Estate

- **Artist Portfolio:** 30% stats, 45% gallery, 25% detail
- **Set Detail:** 30% metadata, 45% cards, 25% preview
- **Browsers:** Full-width list with inline search/filter

### Accessibility

- Clear focus indicators in galleries
- Screen reader support for all labels
- High contrast mode for rarity/color indicators
- Keyboard shortcuts documented in help (ctrl+h)

---

## Future Enhancements

### Artist Features
- **Artist Collaboration Network:** Artists who worked on same sets
- **Art Style Tags:** Community-driven or ML-generated style metadata
- **Artist Interviews:** Embedded links to artist interviews/portfolios
- **Favorite Artists:** Personal curated list with notifications for new cards

### Set Features
- **Set Reviews:** Community ratings and reviews
- **Limited Print Run Indicators:** Show which sets are out of print
- **Set Price Tracker:** Track set value over time
- **Draft Simulator:** Simulate drafting from a set
- **Sealed Generator:** Generate sealed pool from set

### Cross-Feature Integration
- **Artist × Set:** "Which artists contributed to this set?"
- **Set × Synergy:** "Best combos from this set"
- **Artist × Deck:** "Build a deck using only Rebecca Guay cards"
- **Timeline × Price:** "Set values over time visualization"

---

## Conclusion

This proposal transforms MTG Spellbook from a card lookup tool into a comprehensive discovery platform. By elevating artists and sets to first-class features, we enable users to explore Magic's rich history through multiple lenses:

- **Artists** become entry points to discover new cards and aesthetics
- **Sets** become curated collections with context and narrative
- **Keyboard-first design** ensures the TUI remains fast and efficient
- **Progressive disclosure** keeps the interface uncluttered while maximizing depth

**Recommended Start:** Phase 1 MVP (Artist Portfolio + Set Detail views) provides immediate value with minimal database changes, leveraging existing infrastructure for maximum impact.

---

**Document Status:** Ready for review
**Next Steps:**
1. Review and approve feature prioritization
2. Begin Phase 1 database method implementation
3. Design widget component architecture
4. Start UI implementation with Artist Portfolio View

---

**Appendix A: Database Schema Considerations**

No schema changes required for Phase 1-2. Existing columns support all queries:
- `cards.artist` (indexed)
- `cards.setCode` (indexed)
- `sets` table (complete metadata)

Phase 3 considerations:
- Add `artist_metadata` table for styles, bios, links
- Add `user_favorites_artists` table
- Add `user_collection` table for set completion tracking

**Appendix B: Command Syntax Examples**

```
# Artist commands
:artist rebecca guay          # Search for artist
:artists                       # Browse all artists
:artist-spotlight              # Random featured artist

# Set commands
:set mkm                       # Show Murders at Karlov Manor
:sets                          # Browse all sets
:sets expansion                # Filter to expansion sets only
:sets innistrad                # Search for Innistrad sets
:sets 2024                     # Filter to 2024 releases
:blocks                        # Browse blocks/storylines
```

**Appendix C: ASCII Art Set Symbols (Future)**

```
[MKM] 🔍  Murders at Karlov Manor
[SNC] 🎩  Streets of New Capenna
[NEO] ⚡  Kamigawa: Neon Dynasty
[MH3] 🌀  Modern Horizons 3
```

Use Unicode symbols or ASCII art to represent iconic set symbols in browser views.
