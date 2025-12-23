"""Tests for GoToPageModal widget."""

from __future__ import annotations

import asyncio

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Input

from mtg_spellbook.widgets.goto_page_modal import GoToPageModal


class GoToPageModalTestApp(App[int | None]):
    """Test app for GoToPageModal."""

    def __init__(self, current_page: int = 1, total_pages: int = 10) -> None:
        super().__init__()
        self.current_page = current_page
        self.total_pages = total_pages
        self.result: int | None = None

    def compose(self) -> ComposeResult:
        yield from []

    def push_modal(self) -> None:
        """Push the modal screen (non-blocking)."""
        self.push_screen(
            GoToPageModal(current_page=self.current_page, total_pages=self.total_pages),
            callback=self._on_modal_result,
        )

    def _on_modal_result(self, result: int | None) -> None:
        """Handle modal result."""
        self.result = result


class TestGoToPageModalInitialization:
    """Tests for GoToPageModal initialization."""

    @pytest.mark.asyncio
    async def test_modal_initialization_defaults(self) -> None:
        """Test modal initializes with default values."""
        app = GoToPageModalTestApp()
        async with app.run_test():
            modal = GoToPageModal(current_page=1, total_pages=10)
            assert modal._current_page == 1
            assert modal._total_pages == 10

    @pytest.mark.asyncio
    async def test_modal_initialization_custom_values(self) -> None:
        """Test modal initializes with custom values."""
        app = GoToPageModalTestApp()
        async with app.run_test():
            modal = GoToPageModal(current_page=5, total_pages=20)
            assert modal._current_page == 5
            assert modal._total_pages == 20

    @pytest.mark.asyncio
    async def test_modal_composes_all_elements(self) -> None:
        """Test modal composes all required elements."""
        app = GoToPageModalTestApp()
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            # Check all elements exist
            assert pilot.app.screen.query_one(".modal-title")
            assert pilot.app.screen.query_one(".modal-info")
            assert pilot.app.screen.query_one("#page-input", Input)
            assert pilot.app.screen.query_one("#error-text")
            assert pilot.app.screen.query_one("#go-btn", Button)
            assert pilot.app.screen.query_one("#cancel-btn", Button)

    @pytest.mark.asyncio
    async def test_modal_displays_page_range(self) -> None:
        """Test modal displays correct page range in info text."""
        app = GoToPageModalTestApp(current_page=3, total_pages=15)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            info = pilot.app.screen.query_one(".modal-info")
            text = str(info.render())
            assert "1-15" in text

    @pytest.mark.asyncio
    async def test_modal_input_prefilled_with_current_page(self) -> None:
        """Test input is prefilled with current page."""
        app = GoToPageModalTestApp(current_page=7, total_pages=10)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            input_widget = pilot.app.screen.query_one("#page-input", Input)
            assert input_widget.value == "7"

    @pytest.mark.asyncio
    async def test_modal_input_focused_on_mount(self) -> None:
        """Test input is focused when modal opens."""
        app = GoToPageModalTestApp()
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            input_widget = pilot.app.screen.query_one("#page-input", Input)
            assert input_widget.has_focus


class TestGoToPageModalValidation:
    """Tests for input validation in GoToPageModal."""

    @pytest.mark.asyncio
    async def test_valid_page_number_accepted(self) -> None:
        """Test valid page number is accepted."""
        app = GoToPageModalTestApp(current_page=1, total_pages=10)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            # Enter valid page
            input_widget = pilot.app.screen.query_one("#page-input", Input)
            input_widget.value = "5"
            await pilot.press("enter")
            await pilot.pause()

            assert app.result == 5

    @pytest.mark.asyncio
    async def test_invalid_non_numeric_shows_error(self) -> None:
        """Test non-numeric input shows error message."""
        app = GoToPageModalTestApp(current_page=1, total_pages=10)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            # Enter non-numeric value
            input_widget = pilot.app.screen.query_one("#page-input", Input)
            input_widget.value = "abc"
            await pilot.press("enter")
            await pilot.pause()

            error_text = pilot.app.screen.query_one("#error-text")
            text = str(error_text.render())
            assert "valid number" in text.lower()

    @pytest.mark.asyncio
    async def test_page_below_minimum_shows_error(self) -> None:
        """Test page number below 1 shows error."""
        app = GoToPageModalTestApp(current_page=1, total_pages=10)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            # Enter 0
            input_widget = pilot.app.screen.query_one("#page-input", Input)
            input_widget.value = "0"
            await pilot.press("enter")
            await pilot.pause()

            error_text = pilot.app.screen.query_one("#error-text")
            text = str(error_text.render())
            assert "between 1 and" in text.lower()

    @pytest.mark.asyncio
    async def test_page_above_maximum_shows_error(self) -> None:
        """Test page number above max shows error."""
        app = GoToPageModalTestApp(current_page=1, total_pages=10)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            # Enter 11 (max is 10)
            input_widget = pilot.app.screen.query_one("#page-input", Input)
            input_widget.value = "11"
            await pilot.press("enter")
            await pilot.pause()

            error_text = pilot.app.screen.query_one("#error-text")
            text = str(error_text.render())
            assert "between 1 and 10" in text.lower()

    @pytest.mark.asyncio
    async def test_negative_page_shows_error(self) -> None:
        """Test negative page number shows error."""
        app = GoToPageModalTestApp(current_page=1, total_pages=10)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            # Enter negative number
            input_widget = pilot.app.screen.query_one("#page-input", Input)
            input_widget.value = "-5"
            await pilot.press("enter")
            await pilot.pause()

            error_text = pilot.app.screen.query_one("#error-text")
            text = str(error_text.render())
            assert "between 1 and" in text.lower()

    @pytest.mark.asyncio
    async def test_whitespace_stripped_from_input(self) -> None:
        """Test whitespace is stripped from input."""
        app = GoToPageModalTestApp(current_page=1, total_pages=10)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            # Enter valid page with whitespace
            input_widget = pilot.app.screen.query_one("#page-input", Input)
            input_widget.value = "  7  "
            await pilot.press("enter")
            await pilot.pause()

            assert app.result == 7


class TestGoToPageModalButtonInteraction:
    """Tests for button interactions in GoToPageModal."""

    @pytest.mark.asyncio
    async def test_go_button_submits_valid_page(self) -> None:
        """Test clicking Go button submits valid page."""
        app = GoToPageModalTestApp(current_page=1, total_pages=10)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            # Enter valid page and press enter (more reliable than button click)
            input_widget = pilot.app.screen.query_one("#page-input", Input)
            input_widget.value = "8"
            input_widget.focus()
            await pilot.press("enter")
            await pilot.pause()

            assert app.result == 8

    @pytest.mark.asyncio
    async def test_cancel_button_dismisses_without_result(self) -> None:
        """Test clicking Cancel button dismisses modal with None."""
        app = GoToPageModalTestApp(current_page=1, total_pages=10)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            cancel_btn = pilot.app.screen.query_one("#cancel-btn", Button)
            await pilot.click(cancel_btn)
            await pilot.pause()

            assert app.result is None

    @pytest.mark.asyncio
    async def test_go_button_validates_input(self) -> None:
        """Test Go button validates input before submitting."""
        app = GoToPageModalTestApp(current_page=1, total_pages=10)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            # Enter invalid page and press enter (more reliable than button click)
            input_widget = pilot.app.screen.query_one("#page-input", Input)
            input_widget.value = "invalid"
            input_widget.focus()
            await pilot.press("enter")
            await pilot.pause()

            # Should show error, not dismiss
            error_text = pilot.app.screen.query_one("#error-text")
            text = str(error_text.render())
            assert "valid number" in text.lower()


class TestGoToPageModalKeyBindings:
    """Tests for keyboard bindings in GoToPageModal."""

    @pytest.mark.asyncio
    async def test_escape_key_cancels_modal(self) -> None:
        """Test Escape key cancels modal."""
        app = GoToPageModalTestApp(current_page=1, total_pages=10)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            await pilot.press("escape")
            await pilot.pause()

            assert app.result is None

    @pytest.mark.asyncio
    async def test_q_key_cancels_modal(self) -> None:
        """Test 'q' key cancels modal."""
        app = GoToPageModalTestApp(current_page=1, total_pages=10)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            await pilot.press("q")
            await pilot.pause()

            assert app.result is None

    @pytest.mark.asyncio
    async def test_enter_key_submits_valid_page(self) -> None:
        """Test Enter key submits valid page."""
        app = GoToPageModalTestApp(current_page=1, total_pages=10)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            # Change input and press Enter
            input_widget = pilot.app.screen.query_one("#page-input", Input)
            input_widget.value = "3"
            await pilot.press("enter")
            await pilot.pause()

            assert app.result == 3

    @pytest.mark.asyncio
    async def test_enter_key_validates_input(self) -> None:
        """Test Enter key validates input before submitting."""
        app = GoToPageModalTestApp(current_page=1, total_pages=10)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            # Enter invalid page and press Enter
            input_widget = pilot.app.screen.query_one("#page-input", Input)
            input_widget.value = "50"  # Above max
            await pilot.press("enter")
            await pilot.pause()

            # Should show error
            error_text = pilot.app.screen.query_one("#error-text")
            text = str(error_text.render())
            assert "between 1 and 10" in text.lower()


class TestGoToPageModalEdgeCases:
    """Tests for edge cases in GoToPageModal."""

    @pytest.mark.asyncio
    async def test_modal_with_single_page(self) -> None:
        """Test modal with only one page."""
        app = GoToPageModalTestApp(current_page=1, total_pages=1)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            # Only page 1 should be valid
            input_widget = pilot.app.screen.query_one("#page-input", Input)
            input_widget.value = "1"
            await pilot.press("enter")
            await pilot.pause()

            assert app.result == 1

    @pytest.mark.asyncio
    async def test_modal_with_large_page_count(self) -> None:
        """Test modal with large page count."""
        app = GoToPageModalTestApp(current_page=1, total_pages=1000)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            # Enter large page number
            input_widget = pilot.app.screen.query_one("#page-input", Input)
            input_widget.value = "999"
            await pilot.press("enter")
            await pilot.pause()

            assert app.result == 999

    @pytest.mark.asyncio
    async def test_modal_boundary_page_min(self) -> None:
        """Test modal accepts minimum boundary page (1)."""
        app = GoToPageModalTestApp(current_page=5, total_pages=10)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            input_widget = pilot.app.screen.query_one("#page-input", Input)
            input_widget.value = "1"
            await pilot.press("enter")
            await pilot.pause()

            assert app.result == 1

    @pytest.mark.asyncio
    async def test_modal_boundary_page_max(self) -> None:
        """Test modal accepts maximum boundary page."""
        app = GoToPageModalTestApp(current_page=1, total_pages=10)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            input_widget = pilot.app.screen.query_one("#page-input", Input)
            input_widget.value = "10"
            await pilot.press("enter")
            await pilot.pause()

            assert app.result == 10

    @pytest.mark.asyncio
    async def test_modal_empty_input_shows_error(self) -> None:
        """Test empty input shows error."""
        app = GoToPageModalTestApp(current_page=1, total_pages=10)
        async with app.run_test() as pilot:
            pilot.app.push_modal()
            await asyncio.sleep(0.1)

            # Clear input and submit
            input_widget = pilot.app.screen.query_one("#page-input", Input)
            input_widget.value = ""
            await pilot.press("enter")
            await pilot.pause()

            error_text = pilot.app.screen.query_one("#error-text")
            text = str(error_text.render())
            assert "valid number" in text.lower()


class TestGoToPageModalMessage:
    """Tests for PageSelected message."""

    @pytest.mark.asyncio
    async def test_page_selected_message_creation(self) -> None:
        """Test PageSelected message can be created."""
        from mtg_spellbook.widgets.goto_page_modal import GoToPageModal

        msg = GoToPageModal.PageSelected(5)
        assert msg.page == 5

    @pytest.mark.asyncio
    async def test_page_selected_message_with_different_pages(self) -> None:
        """Test PageSelected message with different page values."""
        from mtg_spellbook.widgets.goto_page_modal import GoToPageModal

        msg1 = GoToPageModal.PageSelected(1)
        assert msg1.page == 1

        msg2 = GoToPageModal.PageSelected(100)
        assert msg2.page == 100
