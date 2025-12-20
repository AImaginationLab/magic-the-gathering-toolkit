# Art Panel Bug Report - User Testing Session

**Date**: 2025-12-14
**Tester**: User Tester Agent
**Component**: Art Navigator (Gallery/Focus/Compare Views)

## Summary

- **Total Bugs Found**: 27
- **Critical**: 5
- **Major**: 12
- **Minor**: 7
- **Cosmetic**: 3
- **UX Score**: 4/10

## Critical Bugs (P0)

### C1: Compare View Never Stores Card Name
**Location**: `compare.py` - `CompareSlot`
**Issue**: When adding a card to compare, the `_card_name` is never set, so slots show empty card names.
**Expected**: Slot should display card name alongside set code and price.

### C2: Focus View Doesn't Sync with Gallery Selection
**Location**: `focus.py` / `enhanced.py`
**Issue**: Switching from Gallery to Focus view doesn't show the currently selected printing - shows blank or stale data.
**Expected**: Focus should immediately display the gallery's selected printing.

### C3: Compare Slots Don't Accept New Cards After First Add
**Location**: `compare.py`
**Issue**: After adding first card to compare, subsequent Space presses don't add to remaining slots.
**Expected**: Should fill slots 1-4 sequentially.

### C4: View Mode State Lost on Card Change
**Location**: `enhanced.py`
**Issue**: Loading a new card resets view mode to GALLERY even if user was in FOCUS.
**Expected**: Preserve user's view mode preference.

### C5: No Loading State During Image Fetch
**Location**: `focus.py`, `preview.py`
**Issue**: Image panels show blank/stale content while images load.
**Expected**: Show loading indicator during fetch.

## Major Bugs (P1)

### M1: Escape Key Doesn't Exit Focus/Compare to Gallery
**Location**: `enhanced.py`
**Issue**: Pressing Escape in Focus or Compare view does nothing.
**Expected**: Return to Gallery view.

### M2: Slot Selection Not Visible
**Location**: `compare.py`
**Issue**: No visual indicator for which compare slot is selected for next add.
**Expected**: Highlight the target slot.

### M3: Image Load Failures Not Handled
**Location**: `image_loader.py`
**Issue**: When image URL returns 404 or times out, no error shown.
**Expected**: Show placeholder with error message.

### M4: Grid Navigation Wraps Incorrectly
**Location**: `grid.py`
**Issue**: Pressing right on last item of row doesn't move to next row.
**Expected**: Should wrap to first item of next row, or stay put with feedback.

### M5: Sort Indicator Shows Wrong State After Reload
**Location**: `grid.py`
**Issue**: After changing sort and reloading printings, indicator resets but sort persists.
**Expected**: Indicator should match actual sort state.

### M6: Preview Panel Doesn't Update on Fast Navigation
**Location**: `preview.py`, `enhanced.py`
**Issue**: Rapid arrow key navigation causes preview to lag or skip updates.
**Expected**: Debounce or always show final selection.

### M7: Compare Summary Bar Math Wrong
**Location**: `compare.py` - `SummaryBar`
**Issue**: Total price calculation incorrect when some slots have no price data.
**Expected**: Sum only valid prices, show "N/A" appropriately.

### M8: Art Crop Toggle Doesn't Persist
**Location**: `focus.py`
**Issue**: Toggling art crop mode resets when changing printings.
**Expected**: Maintain user's art crop preference.

### M9: Keyboard Focus Lost After View Switch
**Location**: `enhanced.py`
**Issue**: Switching views with g/f/c leaves focus in limbo.
**Expected**: Focus appropriate widget for new view.

### M10: No Visual Feedback for 's' Sort Toggle
**Location**: `grid.py`
**Issue**: Pressing 's' changes sort but no immediate visual confirmation.
**Expected**: Brief notification or highlight of sort indicator.

### M11: Compare View Doesn't Show Help for Keybindings
**Location**: `compare.py`
**Issue**: Users don't know how to use compare (Space to add, 1-4 to select slot).
**Expected**: Show help text or footer hints.

### M12: Thumbnail Selection Border Too Subtle
**Location**: `thumbnail.py` CSS
**Issue**: Selected thumbnail border is barely visible, especially on bright cards.
**Expected**: More prominent selection indicator.

## Minor Bugs (P2)

### m1: Release date not formatted consistently
**Location**: `preview.py`, `focus.py`
**Issue**: Some dates show full ISO, others show partial.

### m2: Price shows too many decimal places
**Location**: `theme.py` - `get_price_color`
**Issue**: Prices like "$12.3456" instead of "$12.35".

### m3: Empty artist field shows "Unknown" twice
**Location**: `focus.py`
**Issue**: If artist is None, shows "Artist: Unknown" but also "Unknown Artist" elsewhere.

### m4: Grid header count updates before grid loads
**Location**: `grid.py`
**Issue**: Header says "All Printings (50)" while grid still shows old thumbnails.

### m5: Compare slot "Empty" text misaligned
**Location**: `compare.py`
**Issue**: "Press Space to add" text not vertically centered.

### m6: Focus view doesn't show collector number
**Location**: `focus.py`
**Issue**: Metadata shows set but not collector number.

### m7: View toggle buttons not keyboard-accessible
**Location**: `view_toggle.py`
**Issue**: Can't tab to view mode buttons.

## Cosmetic Issues (P3)

### c1: Inconsistent padding in compare slots
### c2: Preview panel border doesn't match theme
### c3: Loading message uses different gold shade than headers

---

## Reproduction Steps

### Compare View Flow:
1. Search for a card with multiple printings (e.g., "Lightning Bolt")
2. Press 'c' to enter Compare view
3. Select a printing and press Space - observe if it adds
4. Check if card name appears in slot
5. Try pressing 1-4 to select different slots

### Focus View Sync:
1. In Gallery view, navigate to printing #3
2. Press 'f' to switch to Focus
3. Observe if Focus shows printing #3 or something else

---

## Recommended Fix Priority

1. **C2 + C1**: Fix Focus/Compare data flow (blocks basic usage)
2. **C3**: Fix compare slot sequential adds
3. **M1**: Implement Escape key handling
4. **M9**: Fix focus management on view switch
5. **C5 + M3**: Add loading states and error handling
6. **M2 + M11**: Add visual feedback and help text
7. **Remaining Major bugs**
8. **Minor + Cosmetic**
