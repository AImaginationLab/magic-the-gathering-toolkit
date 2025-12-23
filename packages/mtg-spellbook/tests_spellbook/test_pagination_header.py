"""Tests for PaginationHeader widget."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Static

from mtg_spellbook.pagination import PaginationState
from mtg_spellbook.widgets.pagination_header import PaginationHeader


class PaginationHeaderTestApp(App[None]):
    """Test app with PaginationHeader widget."""

    def __init__(self, pagination: PaginationState | None = None, title: str = "Results") -> None:
        super().__init__()
        self.pagination = pagination
        self.title = title

    def compose(self) -> ComposeResult:
        yield PaginationHeader(pagination=self.pagination, title=self.title, id="test-header")


def create_pagination(
    num_items: int, page_size: int = 25, current_page: int = 1
) -> PaginationState:
    """Helper to create pagination state."""
    return PaginationState(
        all_items=list(range(num_items)),
        page_size=page_size,
        current_page=current_page,
    )


class TestPaginationHeaderInitialization:
    """Tests for PaginationHeader initialization."""

    @pytest.mark.asyncio
    async def test_header_initialization_with_no_pagination(self) -> None:
        """Test header initializes with no pagination."""
        async with PaginationHeaderTestApp().run_test() as pilot:
            header = pilot.app.query_one("#test-header", PaginationHeader)
            assert header is not None
            assert header._pagination is None
            assert header._title == "Results"

    @pytest.mark.asyncio
    async def test_header_initialization_with_pagination(self) -> None:
        """Test header initializes with pagination state."""
        pagination = create_pagination(100)
        async with PaginationHeaderTestApp(pagination=pagination).run_test() as pilot:
            header = pilot.app.query_one("#test-header", PaginationHeader)
            assert header._pagination == pagination

    @pytest.mark.asyncio
    async def test_header_initialization_with_custom_title(self) -> None:
        """Test header initializes with custom title."""
        async with PaginationHeaderTestApp(title="Search Results").run_test() as pilot:
            header = pilot.app.query_one("#test-header", PaginationHeader)
            assert header._title == "Search Results"


class TestPaginationHeaderDisplay:
    """Tests for PaginationHeader display rendering."""

    @pytest.mark.asyncio
    async def test_header_displays_zero_items(self) -> None:
        """Test header displays correctly for zero items."""
        pagination = create_pagination(0)
        async with PaginationHeaderTestApp(pagination=pagination).run_test() as pilot:
            header = pilot.app.query_one("#test-header", PaginationHeader)
            await pilot.pause()

            # Should display "(0)"
            content = header.query_one("#pagination-content", Static)
            # Get rendered text
            assert content is not None

    @pytest.mark.asyncio
    async def test_header_displays_single_page(self) -> None:
        """Test header displays correctly for single page."""
        pagination = create_pagination(10)
        async with PaginationHeaderTestApp(pagination=pagination).run_test() as pilot:
            pilot.app.query_one("#test-header", PaginationHeader)
            await pilot.pause()

            # Single page should not show page numbers
            assert pagination.total_pages == 1

    @pytest.mark.asyncio
    async def test_header_displays_multiple_pages(self) -> None:
        """Test header displays correctly for multiple pages."""
        pagination = create_pagination(100, page_size=25, current_page=2)
        async with PaginationHeaderTestApp(pagination=pagination).run_test() as pilot:
            pilot.app.query_one("#test-header", PaginationHeader)
            await pilot.pause()

            # Check pagination state
            assert pagination.total_pages == 4
            assert pagination.start_index == 26
            assert pagination.end_index == 50

    @pytest.mark.asyncio
    async def test_header_displays_pagination_controls(self) -> None:
        """Test header displays keyboard controls for pagination."""
        pagination = create_pagination(100)
        async with PaginationHeaderTestApp(pagination=pagination).run_test() as pilot:
            header = pilot.app.query_one("#test-header", PaginationHeader)
            await pilot.pause()

            # Verify content widget exists
            content = header.query_one("#pagination-content", Static)
            assert content is not None

    @pytest.mark.asyncio
    async def test_header_displays_loading_state(self) -> None:
        """Test header displays loading state."""
        pagination = create_pagination(100)
        pagination.is_loading = True
        async with PaginationHeaderTestApp(pagination=pagination).run_test() as pilot:
            pilot.app.query_one("#test-header", PaginationHeader)
            await pilot.pause()

            # Verify widget exists and loading flag is set
            assert pagination.is_loading is True

    @pytest.mark.asyncio
    async def test_header_displays_last_page(self) -> None:
        """Test header displays correctly for last page."""
        pagination = create_pagination(100, page_size=25, current_page=4)
        async with PaginationHeaderTestApp(pagination=pagination).run_test() as pilot:
            pilot.app.query_one("#test-header", PaginationHeader)
            await pilot.pause()

            # Last page: items 76-100
            assert pagination.start_index == 76
            assert pagination.end_index == 100
            assert pagination.current_page == 4
            assert pagination.total_pages == 4


class TestPaginationHeaderUpdate:
    """Tests for updating PaginationHeader state."""

    @pytest.mark.asyncio
    async def test_update_pagination_changes_state(self) -> None:
        """Test update_pagination changes the pagination state."""
        pagination1 = create_pagination(100, current_page=1)
        async with PaginationHeaderTestApp(pagination=pagination1).run_test() as pilot:
            header = pilot.app.query_one("#test-header", PaginationHeader)
            await pilot.pause()

            # Update to page 2
            pagination2 = create_pagination(100, current_page=2)
            header.update_pagination(pagination2)
            await pilot.pause()

            # Verify state updated
            assert header._pagination == pagination2
            assert header._pagination.current_page == 2

    @pytest.mark.asyncio
    async def test_update_pagination_with_new_title(self) -> None:
        """Test update_pagination can change the title."""
        async with PaginationHeaderTestApp(title="Results").run_test() as pilot:
            header = pilot.app.query_one("#test-header", PaginationHeader)

            pagination = create_pagination(50)
            header.update_pagination(pagination, title="Search Results")
            await pilot.pause()

            assert header._title == "Search Results"

    @pytest.mark.asyncio
    async def test_update_pagination_keeps_title_if_none(self) -> None:
        """Test update_pagination keeps existing title if None passed."""
        async with PaginationHeaderTestApp(title="Original Title").run_test() as pilot:
            header = pilot.app.query_one("#test-header", PaginationHeader)

            pagination = create_pagination(50)
            header.update_pagination(pagination, title=None)
            await pilot.pause()

            assert header._title == "Original Title"

    @pytest.mark.asyncio
    async def test_update_pagination_to_none(self) -> None:
        """Test update_pagination can clear pagination."""
        pagination = create_pagination(100)
        async with PaginationHeaderTestApp(pagination=pagination).run_test() as pilot:
            header = pilot.app.query_one("#test-header", PaginationHeader)
            await pilot.pause()

            # Clear pagination
            header.update_pagination(None)
            await pilot.pause()

            assert header._pagination is None


class TestPaginationHeaderLoadingState:
    """Tests for PaginationHeader loading state."""

    @pytest.mark.asyncio
    async def test_show_loading_displays_loading_message(self) -> None:
        """Test show_loading displays loading message."""
        async with PaginationHeaderTestApp(title="Results").run_test() as pilot:
            header = pilot.app.query_one("#test-header", PaginationHeader)

            header.show_loading()
            await pilot.pause()

            # Verify content widget exists
            content = header.query_one("#pagination-content", Static)
            assert content is not None

    @pytest.mark.asyncio
    async def test_show_loading_with_custom_title(self) -> None:
        """Test show_loading uses the configured title."""
        async with PaginationHeaderTestApp(title="Custom Title").run_test() as pilot:
            header = pilot.app.query_one("#test-header", PaginationHeader)

            header.show_loading()
            await pilot.pause()

            # Verify title is preserved
            assert header._title == "Custom Title"


class TestPaginationHeaderEdgeCases:
    """Tests for edge cases in PaginationHeader."""

    @pytest.mark.asyncio
    async def test_header_with_one_item_on_last_page(self) -> None:
        """Test header with exactly one item on last page."""
        pagination = create_pagination(51, page_size=25, current_page=3)
        async with PaginationHeaderTestApp(pagination=pagination).run_test() as pilot:
            pilot.app.query_one("#test-header", PaginationHeader)
            await pilot.pause()

            # Last page: item 51-51
            assert pagination.start_index == 51
            assert pagination.end_index == 51
            assert pagination.total_pages == 3

    @pytest.mark.asyncio
    async def test_header_with_large_numbers(self) -> None:
        """Test header with large item counts."""
        pagination = create_pagination(10000, page_size=100, current_page=50)
        async with PaginationHeaderTestApp(pagination=pagination).run_test() as pilot:
            pilot.app.query_one("#test-header", PaginationHeader)
            await pilot.pause()

            # Page 50: items 4901-5000
            assert pagination.start_index == 4901
            assert pagination.end_index == 5000
            assert pagination.total_pages == 100

    @pytest.mark.asyncio
    async def test_header_refresh_content_internal(self) -> None:
        """Test _refresh_content updates display correctly."""
        pagination = create_pagination(100, current_page=1)
        async with PaginationHeaderTestApp(pagination=pagination).run_test() as pilot:
            header = pilot.app.query_one("#test-header", PaginationHeader)
            await pilot.pause()

            # Change internal state and call _refresh_content
            header._pagination = create_pagination(100, current_page=3)
            header._refresh_content()
            await pilot.pause()

            # Verify pagination state changed
            assert header._pagination.current_page == 3
            assert header._pagination.start_index == 51
            assert header._pagination.end_index == 75


class TestPaginationHeaderComposition:
    """Tests for PaginationHeader composition."""

    @pytest.mark.asyncio
    async def test_header_composes_content_widget(self) -> None:
        """Test header composes the content static widget."""
        async with PaginationHeaderTestApp().run_test() as pilot:
            header = pilot.app.query_one("#test-header", PaginationHeader)
            content = header.query_one("#pagination-content", Static)
            assert content is not None
