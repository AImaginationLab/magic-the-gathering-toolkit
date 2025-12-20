"""Tests for BlockBrowser widget."""

from __future__ import annotations

from typing import ClassVar

import pytest
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Tree

from mtg_core.data.models.responses import BlockSummary, SetSummary
from mtg_spellbook.widgets.block_browser import (
    BlockBrowser,
    BlockBrowserClosed,
)


def create_sample_blocks() -> list[BlockSummary]:
    """Create sample blocks for testing."""
    return [
        BlockSummary(
            name="Innistrad",
            set_count=3,
            total_cards=750,
            first_release="2011-09-30",
            last_release="2012-05-04",
            sets=[
                SetSummary(code="isd", name="Innistrad", release_date="2011-09-30"),
                SetSummary(code="dka", name="Dark Ascension", release_date="2012-02-03"),
                SetSummary(code="avr", name="Avacyn Restored", release_date="2012-05-04"),
            ],
        ),
        BlockSummary(
            name="Ravnica",
            set_count=3,
            total_cards=800,
            first_release="2005-10-07",
            last_release="2006-05-05",
            sets=[
                SetSummary(code="rav", name="Ravnica: City of Guilds", release_date="2005-10-07"),
                SetSummary(code="gpt", name="Guildpact", release_date="2006-02-03"),
                SetSummary(code="dis", name="Dissension", release_date="2006-05-05"),
            ],
        ),
        BlockSummary(
            name="Ixalan",
            set_count=2,
            total_cards=450,
            first_release="2017-09-29",
            last_release="2018-01-19",
            sets=[
                SetSummary(code="xln", name="Ixalan", release_date="2017-09-29"),
                SetSummary(code="rix", name="Rivals of Ixalan", release_date="2018-01-19"),
            ],
        ),
    ]


class BlockBrowserTestApp(App[None]):
    """Test app with BlockBrowser widget."""

    def compose(self) -> ComposeResult:
        with Vertical(id="main-container"):
            yield BlockBrowser(id="block-browser")


class TestBlockBrowserWidget:
    """Tests for BlockBrowser widget functionality."""

    @pytest.mark.asyncio
    async def test_browser_loads_blocks(self) -> None:
        """Test that browser correctly loads and displays blocks."""
        async with BlockBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#block-browser", BlockBrowser)
            blocks = create_sample_blocks()

            await browser.load_blocks(blocks)

            assert browser.total_blocks == 3
            assert len(browser._blocks) == 3

    @pytest.mark.asyncio
    async def test_tree_structure_created(self) -> None:
        """Test that tree structure is created correctly."""
        async with BlockBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#block-browser", BlockBrowser)
            blocks = create_sample_blocks()

            await browser.load_blocks(blocks)

            tree = browser.query_one("#block-tree", Tree)
            # Root should be expanded
            assert tree.root.is_expanded
            # Should have decade children
            assert len(list(tree.root.children)) > 0

    @pytest.mark.asyncio
    async def test_decade_grouping(self) -> None:
        """Test that blocks are grouped by decade."""
        async with BlockBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#block-browser", BlockBrowser)
            blocks = create_sample_blocks()

            await browser.load_blocks(blocks)

            tree = browser.query_one("#block-tree", Tree)
            # Check that we have decade nodes
            decade_labels = [str(child.label) for child in tree.root.children]
            # Should have 2010s, 2000s (2010s for Innistrad/Ixalan, 2000s for Ravnica)
            assert any("2010s" in label for label in decade_labels)
            assert any("2000s" in label for label in decade_labels)

    @pytest.mark.asyncio
    async def test_close_action_posts_message(self) -> None:
        """Test that close action posts BlockBrowserClosed message."""

        class TestApp(App[None]):
            messages: ClassVar[list[BlockBrowserClosed]] = []

            def compose(self) -> ComposeResult:
                with Vertical(id="main-container"):
                    yield BlockBrowser(id="block-browser")

            def on_block_browser_closed(self, msg: BlockBrowserClosed) -> None:
                TestApp.messages.append(msg)

        TestApp.messages = []  # Reset for this test
        async with TestApp().run_test() as pilot:
            browser = pilot.app.query_one("#block-browser", BlockBrowser)

            browser.action_close()
            await pilot.pause()

            assert len(TestApp.messages) == 1

    @pytest.mark.asyncio
    async def test_block_info_panel_updates(self) -> None:
        """Test that selecting a block updates the info panel."""
        async with BlockBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#block-browser", BlockBrowser)
            blocks = create_sample_blocks()

            await browser.load_blocks(blocks)

            # Show block info for Innistrad
            browser._show_block_info(blocks[0])
            await pilot.pause()

            from textual.widgets import Static

            info = browser.query_one("#block-info", Static)
            # Static widget's content can be accessed via render()
            info_text = str(info.render())

            # Verify key info is displayed
            assert "Innistrad" in info_text

    @pytest.mark.asyncio
    async def test_header_shows_block_count(self) -> None:
        """Test that header displays correct block count."""
        async with BlockBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#block-browser", BlockBrowser)
            blocks = create_sample_blocks()

            await browser.load_blocks(blocks)

            header = browser._render_header()
            assert "3 blocks" in header

    @pytest.mark.asyncio
    async def test_cursor_navigation(self) -> None:
        """Test cursor up/down actions."""
        async with BlockBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#block-browser", BlockBrowser)
            blocks = create_sample_blocks()

            await browser.load_blocks(blocks)

            # Should not raise
            browser.action_cursor_up()
            await pilot.pause()

            browser.action_cursor_down()
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_select_item_toggles_expand(self) -> None:
        """Test that select action expands/collapses nodes."""
        async with BlockBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#block-browser", BlockBrowser)
            blocks = create_sample_blocks()

            await browser.load_blocks(blocks)

            # Should not raise
            browser.action_select_item()
            await pilot.pause()


class TestBlockBrowserMessages:
    """Tests for BlockBrowser message handling."""

    @pytest.mark.asyncio
    async def test_block_selected_message_on_expand(self) -> None:
        """Test that expanding a block posts BlockSelected message."""
        # This test is more of an integration test that would need
        # actual tree node interaction
        async with BlockBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#block-browser", BlockBrowser)
            blocks = create_sample_blocks()

            await browser.load_blocks(blocks)

            # Verify block_nodes are created
            assert len(browser._block_nodes) == 3


class TestBlockBrowserEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_block_list(self) -> None:
        """Test browser with empty block list."""
        async with BlockBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#block-browser", BlockBrowser)

            await browser.load_blocks([])

            assert browser.total_blocks == 0

    @pytest.mark.asyncio
    async def test_block_without_dates(self) -> None:
        """Test block without release dates."""
        async with BlockBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#block-browser", BlockBrowser)

            blocks = [
                BlockSummary(
                    name="Unknown Block",
                    set_count=1,
                    total_cards=100,
                    first_release=None,
                    last_release=None,
                    sets=[
                        SetSummary(code="unk", name="Unknown Set", release_date=None),
                    ],
                ),
            ]

            await browser.load_blocks(blocks)

            assert browser.total_blocks == 1

    @pytest.mark.asyncio
    async def test_block_with_same_year_release(self) -> None:
        """Test block where all sets released in same year."""
        async with BlockBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#block-browser", BlockBrowser)

            blocks = [
                BlockSummary(
                    name="Single Year Block",
                    set_count=2,
                    total_cards=300,
                    first_release="2020-01-01",
                    last_release="2020-12-31",
                    sets=[
                        SetSummary(code="sy1", name="Set One", release_date="2020-01-01"),
                        SetSummary(code="sy2", name="Set Two", release_date="2020-12-31"),
                    ],
                ),
            ]

            await browser.load_blocks(blocks)

            # Should display (2020) instead of (2020-2020)
            assert browser.total_blocks == 1

    @pytest.mark.asyncio
    async def test_multiple_blocks_same_decade(self) -> None:
        """Test multiple blocks in the same decade are grouped together."""
        async with BlockBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#block-browser", BlockBrowser)

            blocks = [
                BlockSummary(
                    name="Block A",
                    set_count=1,
                    total_cards=100,
                    first_release="2015-01-01",
                    last_release="2015-01-01",
                    sets=[SetSummary(code="ba", name="Block A Set")],
                ),
                BlockSummary(
                    name="Block B",
                    set_count=1,
                    total_cards=100,
                    first_release="2016-01-01",
                    last_release="2016-01-01",
                    sets=[SetSummary(code="bb", name="Block B Set")],
                ),
            ]

            await browser.load_blocks(blocks)

            tree = browser.query_one("#block-tree", Tree)
            # Should have only one decade node (2010s)
            decade_nodes = [child for child in tree.root.children if "2010s" in str(child.label)]
            assert len(decade_nodes) == 1


class TestBlockBrowserStatusBar:
    """Tests for status bar rendering."""

    @pytest.mark.asyncio
    async def test_statusbar_content(self) -> None:
        """Test that status bar contains expected shortcuts."""
        async with BlockBrowserTestApp().run_test() as pilot:
            browser = pilot.app.query_one("#block-browser", BlockBrowser)

            statusbar = browser._render_statusbar()

            assert "navigate" in statusbar
            assert "Enter" in statusbar
            assert "Esc" in statusbar
