# Focus View Test Suite

Comprehensive test coverage for the FocusView component - an immersive single-card artwork display.

## Test File Location
`/Users/cycorg/repos/magic-the-gathering-toolkit/packages/mtg-spellbook/tests/test_focus_view.py`

## Test Summary

**Total Tests:** 34 tests across 8 test classes
**Status:** All passing

## Test Coverage

### 1. TestFocusViewInitialization (3 tests)
Tests basic initialization and widget composition:
- `test_initialization_with_card_name` - Verifies initial state is set correctly
- `test_composition_creates_all_widgets` - Ensures all metadata and navigation widgets exist
- `test_composition_with_image_support` - Tests image widget creation when support is available

### 2. TestFocusViewPrintingLoading (3 tests)
Tests loading printings into the view:
- `test_load_printings_updates_state` - Verifies internal state updates correctly
- `test_load_printings_updates_display` - Ensures UI elements reflect loaded data
- `test_load_empty_printings` - Handles empty printings list gracefully

### 3. TestFocusViewNavigation (5 tests)
Tests navigation between card printings:
- `test_navigate_next_increments_index` - Next navigation increments correctly
- `test_navigate_prev_decrements_index` - Previous navigation decrements correctly
- `test_navigate_next_at_end_shows_notification` - Boundary check at last printing
- `test_navigate_prev_at_start_shows_notification` - Boundary check at first printing
- `test_navigate_with_no_printings` - Handles navigation with no data

### 4. TestFocusViewSyncToIndex (4 tests)
Tests jumping to specific printings:
- `test_sync_to_valid_index` - Jump to any valid index
- `test_sync_to_index_zero` - Jump to first printing
- `test_sync_to_invalid_index_negative` - Ignores negative indices
- `test_sync_to_invalid_index_too_large` - Ignores out-of-bounds indices

### 5. TestFocusViewGetCurrentPrinting (3 tests)
Tests retrieving the current printing:
- `test_get_current_printing_returns_correct_printing` - Returns correct printing object
- `test_get_current_printing_after_navigation` - Updates after navigation
- `test_get_current_printing_with_no_printings` - Returns None when empty

### 6. TestFocusViewMetadataDisplay (4 tests)
Tests metadata rendering and formatting:
- `test_display_full_metadata` - All metadata fields display correctly
- `test_display_minimal_metadata` - Handles missing optional fields
- `test_rarity_color_formatting` - Rarity displays with proper colors
- `test_flavor_text_hidden_in_art_crop_mode` - Flavor text hidden in art crop mode

### 7. TestFocusViewNavigationHints (3 tests)
Tests navigation hint display:
- `test_navigation_hints_at_middle` - Shows both prev/next hints when in middle
- `test_navigation_hints_at_start` - Hides prev hint at first printing
- `test_navigation_hints_at_end` - Hides next hint at last printing

### 8. TestFocusViewArtCropToggle (2 tests)
Tests art crop mode toggling:
- `test_watch_show_art_crop_triggers_update` - Toggling triggers image reload
- `test_art_crop_changes_image_url` - Uses art_crop URL vs regular image URL

### 9. TestImageLoading (7 tests)
Tests image loading functionality:
- `test_load_image_with_valid_url` - Successfully loads valid images
- `test_load_image_with_404_error` - Gracefully handles 404 errors
- `test_load_image_with_timeout` - Handles network timeouts
- `test_load_image_sets_loading_state` - Loading state is properly managed
- `test_load_image_converts_rgba_to_rgb` - Converts RGBA images to RGB
- `test_load_image_replaces_normal_with_large` - URL transformation for large images
- `test_load_image_does_not_replace_when_use_large_false` - Respects use_large flag

## Key Testing Techniques

### Mocking Strategies
1. **Textual App Testing** - Uses Textual's `run_test()` async context manager
2. **httpx Async Client Mocking** - Custom async context manager class for network requests
3. **Widget Patching** - Patches `_load_image` to isolate UI logic from network calls

### Fixtures
- `sample_printing` - Single printing with full metadata
- `sample_printings` - Three printings for navigation testing
- `minimal_printing` - Printing with minimal/missing fields
- `mock_image` - PIL Image for testing image processing

### Assertion Patterns
- Uses `widget.render()` to get rendered text content
- Converts Rich markup to strings for assertions
- Checks for visible text rather than styled markup (e.g., prices vs set codes)

## Running the Tests

```bash
# Run all Focus view tests
uv run python -m pytest packages/mtg-spellbook/tests/test_focus_view.py -v

# Run specific test class
uv run python -m pytest packages/mtg-spellbook/tests/test_focus_view.py::TestFocusViewNavigation -v

# Run single test
uv run python -m pytest packages/mtg-spellbook/tests/test_focus_view.py::TestImageLoading::test_load_image_with_valid_url -v

# Run with coverage
uv run python -m pytest packages/mtg-spellbook/tests/test_focus_view.py --cov=mtg_spellbook.widgets.art_navigator.focus
```

## Dependencies Tested

### Components
- `/Users/cycorg/repos/magic-the-gathering-toolkit/packages/mtg-spellbook/src/mtg_spellbook/widgets/art_navigator/focus.py` - Main FocusView component
- `/Users/cycorg/repos/magic-the-gathering-toolkit/packages/mtg-spellbook/src/mtg_spellbook/widgets/art_navigator/image_loader.py` - Image loading utilities

### Data Models
- `PrintingInfo` from `mtg_core.data.models.responses` - Card printing data structure

### External Libraries
- `httpx` - HTTP client for image fetching
- `PIL.Image` - Image processing
- `textual` - TUI framework
- `pytest` - Testing framework

## Notes

### Rich Markup Handling
Set codes are rendered as Rich markup styles (e.g., `[LEA]`), which don't appear in plain text output. Tests verify prices and navigation arrows instead, which are visible in rendered content.

### Image Support Detection
Tests use `HAS_IMAGE_SUPPORT` flag to conditionally skip image tests when `textual-image` is not available.

### Async Testing
All tests are async and use Textual's test framework with `pilot.pause()` to allow async operations to complete before assertions.

## Test Quality

- **Code Coverage:** Comprehensive coverage of FocusView functionality
- **Linting:** Passes `ruff check` and `ruff format --check`
- **Type Safety:** Uses proper type hints throughout
- **Documentation:** Clear docstrings for all test methods
- **Isolation:** Tests are independent and can run in any order
