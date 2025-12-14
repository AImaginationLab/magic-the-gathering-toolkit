# MTG Spellbook: Artwork Pane Redesign Proposal

**Date:** December 14, 2025
**Document Type:** UI/UX Design Specification
**Status:** Ready for Review

---

## Executive Summary

The current artwork pane in MTG Spellbook displays a single card image at a time with left/right navigation between printings. Based on comprehensive user research on MTG card browsing experiences and UI/UX best practices for image galleries, this document proposes a significant redesign to make the artwork pane more engaging and better utilize available space.

### Key Recommendations

1. **Multi-Card Gallery View** - Display multiple printings simultaneously in a grid
2. **Enhanced Metadata Panel** - Rich sidebar with artist info, flavor text, and pricing
3. **View Mode Toggle** - Switch between Gallery, Focus, and Compare modes
4. **Better Navigation** - Vim-style keybindings with visual indicators
5. **Discovery Features** - Random art, favorites, and art-crop mode

---

## Current State Analysis

### What We Have Now

```
┌─ Art Tab (Current) ────────────────────────────────────────┐
│  ┌─ Art Info (Static) ───────────────────────────────────┐ │
│  │ Lightning Bolt (3/47)                                 │ │
│  │ [M10] #146                                            │ │
│  │ $2.50                                                 │ │
│  │ ← → to navigate printings                             │ │
│  └───────────────────────────────────────────────────────┘ │
│  ┌─ Image Display ───────────────────────────────────────┐ │
│  │                                                       │ │
│  │                 [Single Card Image]                   │ │
│  │                                                       │ │
│  │                                                       │ │
│  │                                                       │ │
│  └───────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

### Current Limitations

1. **Single Image Display** - Can only view one printing at a time
2. **Wasted Space** - Large empty areas around the card image
3. **Limited Metadata** - Only shows set code, collector number, and price
4. **No Artist Info** - Artist attribution is missing (critical for MTG)
5. **No Flavor Text** - Important element of the MTG experience
6. **Linear Navigation** - Must cycle through 47 printings one at a time
7. **No Visual Overview** - Can't see all available printings at a glance

---

## Proposed Designs

We propose **three view modes** that users can toggle between:

### Design Option A: Gallery View (Default)

**Purpose:** Browse all printings at a glance with rich visual thumbnails

```
┌─ Art Tab ─────────────────────────────────────────────────────────────────────┐
│ [Gallery] [Focus] [Compare]                            🎲 Random  ★ Favorite │
├───────────────────────────────────────────────────────┬───────────────────────┤
│  ┌─ Printings (47) ────────── Sort: [Price ▼] ───────┐│ ┌─ Selected ────────┐│
│  │                                                   ││ │                   ││
│  │  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐     ││ │  ╔═══════════╗    ││
│  │  │ ALF │  │ M10 │  │ M11 │  │ MM  │  │ JMP │     ││ │  ║           ║    ││
│  │  │     │  │     │  │     │  │     │  │     │     ││ │  ║  [LARGE]  ║    ││
│  │  │$500 │  │$2.50│  │$1.99│  │$3.00│  │$0.50│     ││ │  ║  [IMAGE]  ║    ││
│  │  └─────┘  └─────┘  └─────┘  └─────┘  └─────┘     ││ │  ║           ║    ││
│  │     ▲                                            ││ │  ╚═══════════╝    ││
│  │  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐     ││ │                   ││
│  │  │ STA │  │ 2XM │  │ TSR │  │ SLD │  │ CLB │     ││ │ Lightning Bolt    ││
│  │  │     │  │     │  │     │  │     │  │     │     ││ │ ──────────────────││
│  │  │$4.00│  │$2.25│  │$2.00│  │$15  │  │$0.75│     ││ │ M10 • #146        ││
│  │  └─────┘  └─────┘  └─────┘  └─────┘  └─────┘     ││ │ Christopher Rush  ││
│  │                                                   ││ │                   ││
│  │  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐     ││ │ $2.50 USD         ││
│  │  │ A25 │  │ IMA │  │ E02 │  │ MH2 │  │ DMR │     ││ │ $3.10 EUR         ││
│  │  │     │  │     │  │     │  │     │  │     │     ││ │                   ││
│  │  │$1.50│  │$1.25│  │$1.00│  │$5.00│  │$1.75│     ││ │ ┌─ Flavor ──────┐ ││
│  │  └─────┘  └─────┘  └─────┘  └─────┘  └─────┘     ││ │ │ "The spark    │ ││
│  │                                                   ││ │ │  ignites..."  │ ││
│  └───────────────────────────────────────────────────┘│ │ └───────────────┘ ││
│  [hjkl/arrows: navigate] [Enter: focus] [/: filter]   │ └───────────────────┘│
└───────────────────────────────────────────────────────┴───────────────────────┘
```

**Key Features:**
- **Thumbnail Grid**: 5-column layout showing all printings with set codes and prices
- **Preview Panel**: Right sidebar shows enlarged selected card with metadata
- **Quick Info**: Set code, price visible on each thumbnail
- **Visual Selection**: Arrow indicator shows currently selected printing
- **Filtering**: Sort by price, release date, set, or artist
- **Random Button**: Discover a random printing
- **Favorites**: Mark preferred printings

**Navigation:**
- `h/j/k/l` or arrow keys: Navigate grid
- `Enter`: Switch to Focus mode for selected card
- `/`: Open filter/search
- `Tab`: Move between grid and preview panel
- `r`: Random printing
- `f`: Toggle favorite

---

### Design Option B: Focus View

**Purpose:** Immersive single-card view for artwork appreciation

```
┌─ Art Tab ─────────────────────────────────────────────────────────────────────┐
│ [Gallery] [Focus] [Compare]                            🎲 Random  ★ Favorite │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│                          ╔═══════════════════════════╗                        │
│                          ║                           ║                        │
│                          ║                           ║                        │
│                          ║                           ║                        │
│                          ║      [FULL CARD IMAGE]    ║                        │
│                          ║                           ║                        │
│                          ║     Lightning Bolt        ║                        │
│                          ║                           ║                        │
│                          ║                           ║                        │
│                          ║                           ║                        │
│                          ╚═══════════════════════════╝                        │
│                                                                               │
│  ╭─────────────────────────────────────────────────────────────────────────╮  │
│  │ Lightning Bolt            M10 • #146                  Christopher Rush  │  │
│  │ Instant • R               2010                        $2.50 USD         │  │
│  │                                                                         │  │
│  │ "The spark mages have harnessed the fury of the storm."                 │  │
│  ╰─────────────────────────────────────────────────────────────────────────╯  │
│                                                                               │
│  ◀ [M11] $1.99                              (3/47)              [MM] $3.00 ▶  │
│  [←/→: prev/next] [g: gallery] [a: art crop] [c: compare] [Esc: back]        │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- **Maximized Image**: Card image fills most of available space
- **Rich Footer**: Card name, set, artist, year, price in elegant bar
- **Flavor Text**: Prominently displayed below card
- **Prev/Next Hints**: Shows adjacent printings with prices
- **Art Crop Mode**: Toggle to show just the artwork (no card frame)

**Art Crop Sub-Mode:**
```
┌─ Art Tab (Art Crop Mode) ─────────────────────────────────────────────────────┐
│                                                                               │
│     ╔═════════════════════════════════════════════════════════════════╗       │
│     ║                                                                 ║       │
│     ║                                                                 ║       │
│     ║                    [ART CROP - NO FRAME]                        ║       │
│     ║                                                                 ║       │
│     ║                    Full artwork appreciation                    ║       │
│     ║                                                                 ║       │
│     ║                                                                 ║       │
│     ╚═════════════════════════════════════════════════════════════════╝       │
│                                                                               │
│  ╭────────────────────────────────────────────────────────────────────────╮   │
│  │ Art by Christopher Rush                                   M10 (2010)  │   │
│  ╰────────────────────────────────────────────────────────────────────────╯   │
│  [a: toggle card view] [←/→: prev/next]                                       │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

### Design Option C: Compare View

**Purpose:** Side-by-side comparison of multiple printings

```
┌─ Art Tab ─────────────────────────────────────────────────────────────────────┐
│ [Gallery] [Focus] [Compare]                       Clear Selection  Add More  │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ╔═══════════════════╗    ╔═══════════════════╗    ╔═══════════════════╗     │
│  ║                   ║    ║                   ║    ║                   ║     │
│  ║                   ║    ║                   ║    ║                   ║     │
│  ║  [CARD IMAGE 1]   ║    ║  [CARD IMAGE 2]   ║    ║  [CARD IMAGE 3]   ║     │
│  ║                   ║    ║                   ║    ║                   ║     │
│  ║                   ║    ║                   ║    ║                   ║     │
│  ╚═══════════════════╝    ╚═══════════════════╝    ╚═══════════════════╝     │
│                                                                               │
│  ┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐     │
│  │ Alpha (1993)      │    │ M10 (2010)        │    │ Secret Lair       │     │
│  │ Christopher Rush  │    │ Christopher Rush  │    │ New Artist        │     │
│  │ $500.00           │    │ $2.50             │    │ $15.00            │     │
│  │ ★ Original Art    │    │ Classic Reprint   │    │ ★ Alternate Art   │     │
│  └───────────────────┘    └───────────────────┘    └───────────────────┘     │
│        [1]                      [2]                      [3]                  │
│                                                                               │
│  [1-9: select slot] [Space: add to compare] [x: remove] [g: gallery]         │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- **2-4 Card Display**: Compare multiple printings side by side
- **Unified Metadata**: Consistent info bar under each card
- **Art Difference Highlighting**: Visual indicator for different artwork
- **Price Comparison**: Easy price comparison across printings
- **Slot Selection**: Keyboard numbers to select comparison slots

---

## Enhanced Metadata Display

### Artist Information Panel

Research shows artist attribution is highly valued by MTG players. Proposed enhancement:

```
┌─ Artist Info ────────────────────────┐
│ Christopher Rush (1965-2016)         │
│ ────────────────────────────────────│
│ Notable Works:                       │
│ • Lightning Bolt (Alpha-M11)         │
│ • Black Lotus                        │
│ • Ancestral Recall                   │
│                                      │
│ Total Cards: 87                      │
│ View all cards by this artist →      │
└──────────────────────────────────────┘
```

### Price History Sparkline

```
┌─ Price Trend ────────────────────────┐
│ $2.50 USD (TCGPlayer Mid)            │
│                                      │
│     ▁▂▃▅▇█▇▅▃▂▁▂▃▄▅▆▇               │
│     └── 30 days ──────┘              │
│                                      │
│ High: $3.25  Low: $1.99  Avg: $2.40  │
└──────────────────────────────────────┘
```

### Flavor Text Display

```
┌─ Flavor ─────────────────────────────┐
│                                      │
│  "The spark mages have harnessed     │
│   the fury of the storm."            │
│                                      │
│               —Erta, Ghitu shaman   │
│                                      │
└──────────────────────────────────────┘
```

---

## Navigation & Keybindings

### Vim-Style Navigation (Following lazygit patterns)

| Key | Action | Context |
|-----|--------|---------|
| `h/j/k/l` | Navigate | All views |
| `←/→` | Prev/Next printing | Focus view |
| `↑/↓` | Navigate grid | Gallery view |
| `Enter` | Select / Focus | Gallery → Focus |
| `Esc` / `q` | Back / Close | All views |
| `g` | Gallery view | From any view |
| `f` | Focus view | From any view |
| `c` | Compare view | From any view |
| `a` | Toggle art crop | Focus view |
| `r` | Random printing | All views |
| `s` | Cycle sort | Gallery view |
| `/` | Filter/search | Gallery view |
| `Space` | Add to compare | Gallery view |
| `1-9` | Select slot | Compare view |
| `?` | Show help | All views |

### Visual Focus Indicators

```
Gallery View - Selected Card:
  ┌─────┐      ╔═════╗      ┌─────┐
  │ ALF │      ║ M10 ║      │ M11 │
  │     │      ║     ║      │     │
  │$500 │      ║$2.50║      │$1.99│
  └─────┘      ╚═════╝      └─────┘
               ▲▲▲▲▲
              Selected
```

---

## Implementation Recommendations

### Phase 1: Gallery View Foundation
1. Implement thumbnail grid layout in ArtNavigator
2. Add sidebar preview panel
3. Create basic grid navigation with keyboard support
4. Add sorting functionality (price, date, set)

### Phase 2: Focus View Enhancement
1. Maximize card image display
2. Add rich metadata footer
3. Implement art crop mode toggle
4. Add prev/next printing hints with prices

### Phase 3: Compare Mode
1. Multi-select functionality in gallery
2. Side-by-side comparison layout
3. Slot management (add/remove)
4. Synchronized navigation option

### Phase 4: Engagement Features
1. Random printing button
2. Favorites system (persisted)
3. Artist information lookup
4. Price trend visualization (if data available)

---

## Technical Considerations

### Textual Framework Capabilities

The existing Textual framework supports:
- Complex layouts with CSS Grid-like system
- Widget composition and nesting
- Focus management and keyboard events
- Image display via textual-image
- Dynamic content updates

### Image Loading Strategy

```python
# Proposed caching strategy
class ArtworkCache:
    """Cache thumbnails and full images separately"""

    thumbnail_cache: dict[str, Image]  # Small versions for grid
    full_cache: dict[str, Image]       # Full resolution for focus

    async def get_thumbnail(self, printing: PrintingInfo) -> Image:
        """Load small version for grid display"""
        # Use Scryfall 'small' image size

    async def get_full(self, printing: PrintingInfo) -> Image:
        """Load large version for focus view"""
        # Use Scryfall 'large' or 'png' size
```

### Layout Structure

```python
# Proposed widget hierarchy
class EnhancedArtNavigator(Vertical):
    """Main artwork viewing widget with multiple modes"""

    def compose(self):
        yield ViewModeToggle()  # [Gallery] [Focus] [Compare]
        yield ActionBar()       # Random, Favorite buttons

        with Horizontal():
            yield PrintingsGrid()   # Thumbnail grid (left)
            yield PreviewPanel()    # Selected card preview (right)

        yield StatusBar()  # Navigation hints
```

---

## Accessibility Considerations

1. **Keyboard-Only Navigation**: All features accessible without mouse
2. **Screen Reader Support**: Meaningful alt text for images
3. **High Contrast Mode**: Optional high-contrast theme
4. **Focus Indicators**: Clear visual focus states
5. **Reduced Motion**: Option to disable transitions

---

## Success Metrics

To evaluate the redesign success, track:

1. **Time to Find Specific Printing**: Should decrease with gallery view
2. **Artwork Tab Usage**: Monitor if users spend more time in art tab
3. **Navigation Efficiency**: Keypresses to reach desired printing
4. **User Feedback**: Qualitative feedback on new features

---

## Appendix A: Additional Mockup - Compact Gallery

For smaller terminals or when space is limited:

```
┌─ Art (47 printings) ──────────────────────────────────────┐
│                                                           │
│  ALF $500 │ M10 $2.5│ M11 $2.0│ MM  $3.0│ JMP $0.5       │
│  ═══════  │         │         │         │                 │
│  STA $4.0 │ 2XM $2.2│ TSR $2.0│ SLD $15 │ CLB $0.8       │
│           │         │         │         │                 │
│                                                           │
│  Selected: M10 Core Set 2010 • Christopher Rush • $2.50   │
│  "The spark mages have harnessed the fury of the storm."  │
│                                                           │
│  [hjkl: nav] [Enter: focus] [a: art crop] [?: help]      │
└───────────────────────────────────────────────────────────┘
```

---

## Appendix B: Color Scheme Reference

Using the existing MTG Spellbook theme:

```
Rarity Colors (from theme.py):
- Mythic:    #FF6B35 (orange)
- Rare:      #FFD700 (gold)
- Uncommon:  #C0C0C0 (silver)
- Common:    #3d3d3d (gray)

UI Colors:
- Background:     #0a0a0a
- Panel BG:       #151515
- Border:         #2a2a2a
- Selected:       #FFD700 (gold highlight)
- Accent:         #4a9eff (blue)
```

---

## Appendix C: Comparison with Industry Tools

| Feature | Scryfall | Current | Proposed |
|---------|----------|---------|----------|
| Multiple printings view | ✅ Grid | ❌ One at a time | ✅ Gallery grid |
| Art crop mode | ✅ | ❌ | ✅ |
| Artist info | ✅ | ❌ | ✅ |
| Flavor text | ✅ | ❌ | ✅ |
| Side-by-side compare | ❌ | ❌ | ✅ |
| Price display | ✅ | ✅ Basic | ✅ Enhanced |
| Keyboard navigation | ❌ Web-based | ✅ Basic | ✅ Vim-style |
| Random art | ✅ | ❌ | ✅ |
| Favorites | ❌ | ❌ | ✅ |

---

**End of Design Proposal**

*This document was prepared based on comprehensive user research on MTG card browsing experiences and UI/UX best practices for image galleries and terminal user interfaces.*
