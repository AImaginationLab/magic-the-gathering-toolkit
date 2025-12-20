# Deck Builder UX Proposal - Executive Summary

## Overview

A comprehensive deck building experience for MTG Spellbook that rivals modern web-based tools (Moxfield, Archidekt) while embracing terminal UI strengths: keyboard-first navigation, instant responsiveness, and offline capabilities.

## Key Design Decisions

### 1. Dual-Mode Interface

**Sidebar Mode (Ctrl+D):**
- Deck list visible alongside card browsing
- Quick add/remove operations
- Minimal screen real estate

**Full Builder Mode (Shift+D):**
- Dedicated split-pane interface
- Search/browse on left (40%)
- Deck editor on right (60%)
- Optimized for building from scratch

### 2. Three User Personas

1. **Casual Builder (Casey)** - Builds 3-8 thematic decks, budget-conscious
2. **Competitive Player (Taylor)** - Fine-tunes meta decks, imports/exports frequently
3. **Collection Manager (Morgan)** - Manages 50+ decks, needs powerful search

### 3. Keyboard-First Philosophy

All features accessible via keyboard with progressive shortcuts:
- **Beginner:** Basic arrows, Enter, Escape
- **Intermediate:** Ctrl+E (add to deck), +/- (quantity), V (validate)
- **Expert:** Vim-style (hjkl), number keys (1-4 for quick-add), bulk operations

## Core User Journeys

### Journey 1: Building a New Deck (25 minutes)
1. Search for commander/theme card
2. Press Ctrl+N → Create new deck
3. Press Ctrl+E → Add card to deck
4. Press Ctrl+S → Find synergies
5. Navigate results, add cards with Ctrl+E
6. Press V → Validate deck
7. Complete!

### Journey 2: Optimizing Existing Deck (15 minutes)
1. Press Ctrl+I → Import deck from MTGO
2. Press Shift+D → Open full deck builder
3. Search for alternatives in left pane
4. Press +/- to adjust quantities
5. Press C → Compare cards side-by-side
6. Press V → Validate changes
7. Press Ctrl+X → Export for tournament

### Journey 3: Finding Cards Across Decks (5 minutes)
1. Press Ctrl+Shift+F → Search all decks
2. Enter card name
3. See all decks containing card
4. Click deck to view/edit

## Key Features

### Phase 1-2 (MVP - Weeks 1-2)
- Create/delete decks
- Add cards from search results
- View deck contents with quantities
- Basic stats (card count, mana curve)
- Adjust quantities (+/-)

### Phase 3-4 (Core Experience - Weeks 3-4)
- Full-screen deck builder mode
- Advanced filters (CMC, color, type)
- Quick-add shortcuts (Space, 1-4 keys)
- Comprehensive analysis (validation, curve, colors, composition, price)
- Live validation feedback

### Phase 5-6 (Power Features - Weeks 5-6)
- Import/export (MTGO, Arena, plain text)
- Side-by-side card comparison
- Tag-based organization
- Search across all decks
- Bulk operations

### Phase 7 (Polish - Week 7)
- Responsive layouts (80x24 to 200x60)
- Context-sensitive keyboard hints (? key)
- Smooth transitions/animations
- WCAG 2.1 AA accessibility compliance

## Wireframes Highlights

### Full-Screen Deck Builder
```
┌─────────────────────────────────────────────────────────────┐
│ SEARCH & BROWSE          │ DECK EDITOR                      │
│ ┌─────────────────────┐  │ Mainboard (56/60)                │
│ │ ⚡ Search: c:red    │  │  4x Lightning Bolt      {R}      │
│ └─────────────────────┘  │  4x Monastery Swiftspear{R}      │
│ FILTERS ▼                │  4x Goblin Guide        {R}      │
│ CMC: [1] [2] [3]         │  ...                             │
│ Type: ☑ Creature        │ STATS ▼                          │
│                          │  Curve: 1 ███████ 16             │
│ RESULTS (127)            │         2 ████ 8                 │
│ > Lightning Bolt {R}     │  Avg CMC: 1.9 · Price: $245      │
│   Chain Lightning{R}     │                                  │
└─────────────────────────────────────────────────────────────┘
```

### Add to Deck Modal
```
┌──────────────────────────┐
│ ADD TO DECK              │
│ Card: Lightning Bolt     │
│ Deck: [Mono-Red ▼]      │
│ Quantity: [4]            │
│ ☐ Add to Sideboard      │
│  [Add]      [Cancel]     │
└──────────────────────────┘
```

## Competitive Advantages

### vs Moxfield/Archidekt
- **Offline-first:** Works without internet
- **Keyboard speed:** 3-5x faster card addition with shortcuts
- **Privacy:** Local data only, no tracking
- **Terminal-native:** Integrates with developer workflows

### vs MTGO
- **Modern UI:** Rich colors, smooth layouts (not Windows 95)
- **Instant search:** SQLite FTS5 vs laggy MTGO database
- **All formats:** Legacy, Vintage, Pauper (MTGO limited to online formats)

### vs Arena
- **Flexible formats:** Build decks for any format, not just Standard/Historic
- **Full export:** Share decks anywhere (Arena locks you in)
- **Advanced analysis:** Mana curve, composition, price breakdown

## Implementation Timeline

**7-week roadmap:**
- Week 1: Deck list + Add to Deck modal (MVP)
- Week 2: Deck editor + Stats panel
- Week 3: Full builder mode + Quick filters
- Week 4: Analysis + Validation
- Week 5: Import/Export
- Week 6: Power features (comparison, tags, bulk ops)
- Week 7: Polish + Accessibility

**Total effort:** 40 days (including testing/polish)

## Success Metrics

- **Time to build first deck:** < 30 minutes (casual user)
- **Time to import deck:** < 2 minutes
- **Keyboard coverage:** > 95% of actions
- **Deck validation rate:** 85% of decks are format-legal
- **User satisfaction:** > 4.5 / 5 stars

## Accessibility Highlights

- **WCAG 2.1 AA compliant**
- **Keyboard-only navigation** (zero mouse required)
- **Screen reader support** (ARIA labels, live regions)
- **High contrast mode** (7:1+ contrast ratio)
- **Reduced motion option** (for sensitive users)

## Next Steps

1. **Review this proposal** with stakeholders
2. **Technical spike** - Prototype split-pane layout (1 week)
3. **Begin Phase 1** - DeckListPanel + AddToDeckModal (1 week)
4. **Internal testing** - Test with 3-5 MTG players
5. **Iterate** based on feedback

## Files to Create

| Component | Est. Lines | Priority |
|-----------|-----------|----------|
| DeckListPanel | 150 | P0 (MVP) |
| AddToDeckModal | 100 | P0 (MVP) |
| DeckEditorPanel | 250 | P0 (MVP) |
| FullDeckBuilder | 400 | P1 |
| DeckAnalysisModal | 300 | P1 |
| ImportDeckModal | 200 | P2 |
| ExportDeckModal | 100 | P2 |
| CardComparisonPanel | 250 | P2 |

**Total: ~2,200 lines of production code**

## References

- Full proposal: `/packages/mtg-spellbook/docs/DECK_BUILDER_UX_PROPOSAL.md`
- Implementation plan: `/docs/DECK_MANAGEMENT_PLAN.md` (technical architecture)
- User research: See "User Personas" section in full proposal
- Wireframes: See "Wireframes (ASCII Art)" section in full proposal

---

**Ready to build the best terminal-based deck builder in MTG!** 🎯
