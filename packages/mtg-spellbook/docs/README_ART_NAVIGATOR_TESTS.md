# Art Navigator Test Suite

## Quick Start

Run the art_navigator tests:

```bash
uv run python -m pytest packages/mtg-spellbook/tests/test_art_navigator.py -v
```

## Test Coverage

This test suite provides comprehensive coverage for the art_navigator package, which implements the 3-mode artwork viewing system:

- **Gallery View**: Thumbnail grid + preview panel
- **Focus View**: Maximized single card with art crop mode
- **Compare View**: Side-by-side comparison of up to 4 printings

## Test Statistics

- **Total Tests**: 40
- **Test Classes**: 10
- **Execution Time**: ~1.3 seconds
- **Status**: All passing ✅

## What's Tested

### 1. Data Model (PrintingInfo)
- Field existence validation
- Type checking
- Optional field handling (None values)

### 2. ThumbnailCard Widget
- Set code display (uppercased)
- Price formatting ($XX.XX)
- Selection state toggling
- Price color classes (low/medium/medium-high/high)
- Price boundary conditions

### 3. PrintingsGrid Widget
- Thumbnail creation and unique IDs
- Left/right/up/down navigation
- Price sorting (high to low)
- Set code sorting (alphabetical)
- Sort mode cycling
- Selection callbacks

### 4. PreviewPanel Widget
- Card name display
- Set code and collector number
- Price formatting
- Missing optional field handling

### 5. FocusView Widget
- Art crop mode toggling
- Prev/next navigation
- Metadata display (artist, rarity, price, etc.)
- Missing flavor text handling

### 6. CompareView Widget
- Adding up to 4 printings
- MAX_SLOTS enforcement (4 max)
- Slot removal
- Clear all functionality
- Unique artwork detection (via illustration_id)
- Cheapest/most expensive analysis

### 7. ViewModeToggle Widget
- Mode switching (GALLERY/FOCUS/COMPARE)
- Active mode highlighting

### 8. EnhancedArtNavigator Integration
- View mode switching
- Keyboard bindings in each mode
- State sharing between views

### 9. CompareSlot Widget
- Loading printings
- Clearing slots

### 10. SummaryBar Widget
- Empty state handling
- Missing price handling
- Unique artwork counting

## Key Test Patterns

### Fixtures

Three reusable fixtures provide test data:

- `sample_printing` - Single printing with all fields
- `sample_printings` - 4 printings with varying data
- `minimal_printing` - Printing with null optional fields

### Async Testing

Tests use pytest-asyncio and Textual's testing utilities:

```python
@pytest.mark.asyncio
async def test_example():
    async with App().run_test() as pilot:
        await pilot.app.mount(widget)
        # Test async operations
        await pilot.pause()  # Wait for async completion
```

### Boundary Testing

Tests verify edge cases:
- Navigation at grid boundaries
- Price class thresholds ($5, $20, $100)
- Maximum comparison slots (4)
- Empty/null data handling

## Bugs Prevented

These tests prevent regressions in:

1. **Duplicate ID bugs** - Ensures unique thumbnail IDs
2. **Navigation bugs** - Validates correct index updates and boundary checks
3. **Sorting bugs** - Verifies price (high→low) and set (A→Z) ordering
4. **State bugs** - Confirms selection and view mode consistency
5. **Display bugs** - Tests price formatting, set code uppercasing, metadata rendering
6. **Null safety bugs** - Validates graceful handling of missing fields
7. **Comparison bugs** - Enforces max slots, duplicate prevention, artwork uniqueness
8. **Price analysis bugs** - Tests cheapest/most expensive calculation

## Test Organization

Tests are organized by component:

```
test_art_navigator.py
├── TestPrintingInfoModel        # Data model tests
├── TestThumbnailCard            # Thumbnail widget tests
├── TestPrintingsGrid            # Grid navigation and sorting
├── TestPreviewPanel             # Preview display tests
├── TestFocusView                # Focus mode tests
├── TestCompareView              # Comparison mode tests
├── TestViewModeToggle           # Mode switching tests
├── TestEnhancedArtNavigator     # Integration tests
├── TestCompareSlot              # Individual slot tests
└── TestSummaryBar               # Statistics tests
```

## Running Specific Tests

```bash
# Run all art_navigator tests
uv run python -m pytest packages/mtg-spellbook/tests/test_art_navigator.py -v

# Run a specific test class
uv run python -m pytest packages/mtg-spellbook/tests/test_art_navigator.py::TestPrintingsGrid -v

# Run a specific test
uv run python -m pytest packages/mtg-spellbook/tests/test_art_navigator.py::TestPrintingsGrid::test_navigation_left_right_moves_selection -v

# Run with coverage
uv run python -m pytest packages/mtg-spellbook/tests/test_art_navigator.py --cov=mtg_spellbook.widgets.art_navigator --cov-report=html
```

## CI Integration

These tests run automatically in CI/CD:

```bash
# All functional tests (excluding screenshots)
uv run python -m pytest packages/mtg-spellbook/tests/test_widgets.py packages/mtg-spellbook/tests/test_art_navigator.py -v
```

**Note**: Screenshot tests (`test_screenshots.py`) are separate visual snapshot tests that may need updating when UI changes.

## Maintenance

When adding new features to art_navigator:

1. **Add tests first** (TDD approach)
2. **Use existing fixtures** where possible
3. **Test edge cases** (null values, boundaries, limits)
4. **Test async operations** with `await pilot.pause()`
5. **Verify state consistency** across view modes
6. **Update this README** with new test coverage

## Related Documentation

- Main test file: `/packages/mtg-spellbook/tests/test_art_navigator.py`
- Test summary: `/packages/mtg-spellbook/TEST_SUMMARY.md`
- Widget code: `/packages/mtg-spellbook/src/mtg_spellbook/widgets/art_navigator/`
