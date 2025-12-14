# Artwork Pane Redesign - Research Summary

**Project:** MTG Spellbook
**Date:** December 14, 2025
**Status:** Research & Design Complete - Ready for Review

---

## Deliverables Created

All files are in `/tmp/` (not added to repo as requested):

| File | Description |
|------|-------------|
| `artwork-pane-redesign-proposal.md` | Comprehensive design specification |
| `artwork-pane-wireframes.txt` | Detailed ASCII wireframes for all views |
| `artwork-pane-research-summary.md` | This summary document |

---

## Executive Summary

Based on extensive user research on MTG card browsing experiences (Scryfall, EDHREC, Moxfield, Archidekt) and UI/UX best practices for image galleries and TUI applications, we recommend a **three-mode artwork pane** redesign:

### Proposed View Modes

1. **Gallery View** (Default)
   - Thumbnail grid showing ALL printings at once
   - Preview panel with enlarged selected card
   - Sort/filter capabilities
   - Price visible on each thumbnail

2. **Focus View**
   - Maximized single-card display
   - Rich metadata footer (artist, set, year, price)
   - Art crop mode toggle
   - Prev/next navigation with price hints

3. **Compare View**
   - Side-by-side comparison of 2-4 printings
   - Unified metadata display
   - Highlights different artwork versions
   - Price comparison summary

---

## Key Research Findings

### User Research (MTG Community)

1. **Hover-to-zoom is fundamental** - Users expect instant card details on selection
2. **Multiple printings comparison** is highly requested across all platforms
3. **Artist attribution** matters deeply - 400+ artists over 30 years
4. **Flavor text** is "quietly important" - core to MTG identity
5. **High resolution** is essential for artwork appreciation

### UI/UX Best Practices

1. **Thumbnails are critical** - 100% of desktop sites use them for navigation
2. **Progressive disclosure** - Layer information (visible → hover → click)
3. **Keyboard-first** - Vim-style navigation (hjkl) for TUI apps
4. **Multi-panel layouts** work well for master-detail views
5. **Study lazygit** - Excellent model for TUI UX patterns

### TUI-Specific Opportunities

1. **Modern graphics protocols** (Kitty, iTerm2, Sixel) enable quality images
2. **Textual framework** supports complex layouts and async image loading
3. **Keyboard efficiency** is a TUI strength - embrace it
4. **File manager patterns** (ranger, nnn, Yazi) demonstrate gallery navigation

---

## Recommended Features (Priority Order)

### P0 - Must Have
- [ ] Thumbnail grid showing all printings
- [ ] Preview panel with card metadata
- [ ] Artist name display
- [ ] Vim-style keyboard navigation (hjkl)

### P1 - Should Have
- [ ] Focus view with maximized image
- [ ] Flavor text display
- [ ] Sort by price/date/set
- [ ] Art crop mode toggle

### P2 - Nice to Have
- [ ] Compare view (side-by-side)
- [ ] Filter by frame type/finish
- [ ] Random printing button
- [ ] Favorites system

### P3 - Future Enhancement
- [ ] Artist info lookup
- [ ] Price trend visualization
- [ ] Collection integration

---

## Comparison: Current vs Proposed

| Feature | Current | Proposed |
|---------|---------|----------|
| View all printings | ❌ One at a time | ✅ Grid view |
| Artist info | ❌ | ✅ |
| Flavor text | ❌ | ✅ |
| Art crop mode | ❌ | ✅ |
| Side-by-side compare | ❌ | ✅ |
| Sort/filter | ❌ | ✅ |
| Keyboard nav | ✅ Basic (←→) | ✅ Vim-style |
| Random art | ❌ | ✅ |

---

## Implementation Approach

### Phase 1: Gallery View Foundation
- Refactor `ArtNavigator` to support multiple view modes
- Implement thumbnail grid layout
- Add preview sidebar panel
- Create basic grid navigation

### Phase 2: Focus View Enhancement
- Maximize image display area
- Add rich metadata footer
- Implement art crop mode
- Add prev/next hints with prices

### Phase 3: Compare Mode
- Multi-select in gallery
- Side-by-side layout (2-4 cards)
- Slot management
- Summary bar

### Phase 4: Polish
- Filter/search overlay
- Artist info panel
- Help overlay
- Random/favorites features

---

## Technical Notes

### Current Implementation
- **Framework:** Textual (Python TUI)
- **Image display:** textual-image (PIL-based)
- **Data source:** Scryfall API
- **Key files:**
  - `widgets/art_navigator.py` - Main art widget
  - `widgets/card_panel/widget.py` - Container panel
  - `widgets/card_panel/loaders.py` - Image loading

### Proposed Changes
- Replace single-image `ArtNavigator` with multi-mode `EnhancedArtNavigator`
- Add thumbnail caching for grid performance
- Implement view mode state machine
- Add sorting/filtering logic
- Create overlay components (help, search, artist info)

---

## Next Steps

1. **Review this proposal** with stakeholders
2. **Prioritize features** based on effort vs impact
3. **Create technical spec** for chosen features
4. **Implement in phases** starting with Gallery View

---

## Files for Review

```
/tmp/
├── artwork-pane-redesign-proposal.md   # Full design spec (837 lines)
├── artwork-pane-wireframes.txt         # ASCII mockups (425 lines)
└── artwork-pane-research-summary.md    # This file
```

To view the files:
```bash
cat /tmp/artwork-pane-redesign-proposal.md
cat /tmp/artwork-pane-wireframes.txt
```

---

*Research conducted using MTG community resources, Scryfall documentation, and UI/UX best practices from industry sources.*
