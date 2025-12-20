"""User experience test for the redesigned Art Panel in MTG Spellbook.

This test simulates real user behavior to evaluate:
- Visual layout and design
- Navigation responsiveness
- Feature discoverability
- Data display quality
- Overall UX quality
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from mtg_spellbook.app import MTGSpellbook


async def test_art_panel_user_experience() -> None:
    """Simulate user testing the art panel with comprehensive scenarios."""
    app = MTGSpellbook()

    # Create output directory for screenshots
    output_dir = Path(__file__).parent / "art_panel_ux_test"
    output_dir.mkdir(exist_ok=True)

    print("Starting Art Panel UX Test...")
    print(f"Screenshots will be saved to: {output_dir}")

    async with app.run_test(size=(140, 50)) as pilot:
        # ===================================================================
        # SCENARIO 1: Card with many printings (Lightning Bolt)
        # ===================================================================
        print("\n[Scenario 1] Testing card with many printings (Lightning Bolt)...")

        # 1.1: Search for Lightning Bolt
        await pilot.press("tab")  # Ensure search input focused
        await pilot.press(*list("lightning bolt"))
        await pilot.press("enter")
        await pilot.pause()  # Wait for all pending events
        await asyncio.sleep(3.0)  # Wait for search results to load (async operation)

        # 1.2: Highlight and view first result
        await pilot.press("down")  # Highlight first result (triggers ListView.Highlighted)
        await pilot.pause()  # Wait for highlight event to process
        print("  Waiting for printings to load...")
        await asyncio.sleep(10.0)  # Wait for card panel to update AND printings to load (bg task)
        app.save_screenshot(str(output_dir / "01_focus_view_initial.svg"))

        # 1.3: Now in Focus View (default) - test navigation
        print("  Testing Focus View navigation...")
        await pilot.press("tab")  # Move focus to art area
        await asyncio.sleep(0.5)

        await pilot.press("l")  # Next printing
        await asyncio.sleep(0.6)
        await pilot.press("l")  # Next printing
        await asyncio.sleep(0.6)
        app.save_screenshot(str(output_dir / "02_focus_navigate.svg"))

        # 1.4: Test art crop mode
        print("  Testing art crop mode...")
        await pilot.press("a")  # Toggle art crop
        await asyncio.sleep(0.8)
        app.save_screenshot(str(output_dir / "03_focus_art_crop_on.svg"))

        await pilot.press("a")  # Toggle back
        await asyncio.sleep(0.8)
        app.save_screenshot(str(output_dir / "04_focus_art_crop_off.svg"))

        # 1.5: Switch to Gallery View
        print("  Testing Gallery View...")
        await pilot.press("g")  # Switch to gallery
        await asyncio.sleep(1.0)
        app.save_screenshot(str(output_dir / "05_gallery_view.svg"))

        # 1.6: Test Gallery navigation with hjkl
        print("  Testing gallery navigation...")
        await pilot.press("l")  # Move right
        await asyncio.sleep(0.6)
        await pilot.press("l")  # Move right again
        await asyncio.sleep(0.6)
        app.save_screenshot(str(output_dir / "06_gallery_navigate_right.svg"))

        await pilot.press("j")  # Move down
        await asyncio.sleep(0.6)
        app.save_screenshot(str(output_dir / "07_gallery_navigate_down.svg"))

        # 1.7: Test sorting
        print("  Testing sort functionality...")
        await pilot.press("s")  # Cycle sort
        await asyncio.sleep(0.8)
        app.save_screenshot(str(output_dir / "08_gallery_sorted_1.svg"))

        await pilot.press("s")  # Cycle sort again
        await asyncio.sleep(0.8)
        app.save_screenshot(str(output_dir / "09_gallery_sorted_2.svg"))

        # 1.8: Test Compare mode
        print("  Testing Compare mode...")
        await pilot.press("space")  # Add to compare
        await asyncio.sleep(0.5)
        await pilot.press("l")  # Move right
        await asyncio.sleep(0.5)
        await pilot.press("space")  # Add another
        await asyncio.sleep(0.5)
        await pilot.press("c")  # Switch to compare view
        await asyncio.sleep(1.0)
        app.save_screenshot(str(output_dir / "10_compare_view.svg"))

        # 1.9: Return to Focus mode
        await pilot.press("f")  # Switch back to focus
        await asyncio.sleep(0.8)
        app.save_screenshot(str(output_dir / "11_back_to_focus.svg"))

        # ===================================================================
        # SCENARIO 2: Escape to return to results
        # ===================================================================
        print("\n[Scenario 2] Testing escape navigation...")
        await pilot.press("escape")  # Return to gallery
        await asyncio.sleep(0.5)
        await pilot.press("escape")  # Return to results
        await asyncio.sleep(0.5)
        app.save_screenshot(str(output_dir / "12_back_to_results.svg"))

        print("\nArt Panel UX Test Complete!")
        print(f"Screenshots saved to: {output_dir}")
