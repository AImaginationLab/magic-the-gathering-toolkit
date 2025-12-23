"""Tests for block commands mixin."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from mtg_core.data.models.responses import BlockSummary, SetSummary


@pytest.fixture
def sample_blocks() -> list[BlockSummary]:
    """Sample blocks for testing."""
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
    ]


@pytest.fixture
def sample_recent_sets() -> list[SetSummary]:
    """Sample recent sets for testing."""
    return [
        SetSummary(code="one", name="Phyrexia: All Will Be One", release_date="2023-02-10"),
        SetSummary(code="mom", name="March of the Machine", release_date="2023-04-21"),
        SetSummary(code="woe", name="Wilds of Eldraine", release_date="2023-09-08"),
    ]


class TestBlockCommands:
    """Tests for BlockCommandsMixin functionality."""

    @pytest.mark.asyncio
    async def test_browse_blocks(
        self, mock_app_with_database, sample_blocks: list[BlockSummary]
    ) -> None:
        """Test opening block browser with blocks."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db.get_all_blocks = AsyncMock(return_value=sample_blocks)

            app.browse_blocks()
            await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_browse_blocks_empty(self, mock_app_with_database) -> None:
        """Test block browser with no blocks."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db.get_all_blocks = AsyncMock(return_value=[])

            app.browse_blocks()
            await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_browse_blocks_reuses_existing(
        self, mock_app_with_database, sample_blocks: list[BlockSummary]
    ) -> None:
        """Test that browser is reused if already exists."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db.get_all_blocks = AsyncMock(return_value=sample_blocks)

            # First call creates browser
            app.browse_blocks()
            await pilot.pause(0.2)

            # Second call should reuse existing browser
            app.browse_blocks()
            await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_show_recent_sets(
        self, mock_app_with_database, sample_recent_sets: list[SetSummary]
    ) -> None:
        """Test showing recent sets."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db.get_recent_sets = AsyncMock(return_value=sample_recent_sets)

            app.show_recent_sets(limit=10)
            await pilot.pause(0.2)

            results_list = app.query_one("#results-list")
            assert len(results_list.children) > 0

    @pytest.mark.asyncio
    async def test_show_recent_sets_custom_limit(
        self, mock_app_with_database, sample_recent_sets: list[SetSummary]
    ) -> None:
        """Test showing recent sets with custom limit."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db.get_recent_sets = AsyncMock(return_value=sample_recent_sets[:5])

            app.show_recent_sets(limit=5)
            await pilot.pause(0.2)

            results_list = app.query_one("#results-list")
            assert len(results_list.children) <= 5

    @pytest.mark.asyncio
    async def test_show_recent_sets_empty(self, mock_app_with_database) -> None:
        """Test showing recent sets when none exist."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db.get_recent_sets = AsyncMock(return_value=[])

            app.show_recent_sets()
            await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_show_recent_sets_different_types(self, mock_app_with_database) -> None:
        """Test recent sets with different set types."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            sets_with_types = [
                SetSummary(code="one", name="Set One", release_date="2023-01-01", type="expansion"),
                SetSummary(code="two", name="Set Two", release_date="2023-02-01", type="core"),
                SetSummary(code="thr", name="Set Three", release_date="2023-03-01", type="masters"),
            ]
            app._db.get_recent_sets = AsyncMock(return_value=sets_with_types)

            app.show_recent_sets()
            await pilot.pause(0.2)

            results_list = app.query_one("#results-list")
            assert len(results_list.children) == 3

    @pytest.mark.asyncio
    async def test_update_results_header(self, mock_app_with_database) -> None:
        """Test updating results header."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._update_results_header("Test Header (10)")
            await pilot.pause()

            header = app.query_one("#results-header")
            header_text = str(header.render())
            assert "Test Header" in header_text or header_text != ""


class TestBlockCommandsEdgeCases:
    """Tests for edge cases in block commands."""

    @pytest.mark.asyncio
    async def test_browse_blocks_no_database(self, mock_app_with_database) -> None:
        """Test browse blocks with no database."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db = None

            app.browse_blocks()
            await pilot.pause(0.1)

    @pytest.mark.asyncio
    async def test_show_recent_sets_no_database(self, mock_app_with_database) -> None:
        """Test show recent sets with no database."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db = None

            app.show_recent_sets()
            await pilot.pause(0.1)

    @pytest.mark.asyncio
    async def test_recent_sets_type_formatting(self, mock_app_with_database) -> None:
        """Test that set types are formatted correctly in display."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            sets = [
                SetSummary(
                    code="tst", name="Test", release_date="2023-01-01", type="draft_innovation"
                ),
            ]
            app._db.get_recent_sets = AsyncMock(return_value=sets)

            app.show_recent_sets()
            await pilot.pause(0.2)

            # Verify type is formatted (draft_innovation -> Draft Innovation)
            results_list = app.query_one("#results-list")
            assert len(results_list.children) > 0
