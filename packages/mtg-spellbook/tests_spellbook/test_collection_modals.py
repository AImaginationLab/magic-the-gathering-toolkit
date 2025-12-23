"""Tests for collection modal dialogs."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Checkbox, Input

from mtg_spellbook.collection.modals import (
    AddToCollectionModal,
    AddToCollectionResult,
    CollectionCardInfo,
    ConfirmDeleteModal,
    CreateDeckResult,
    DeckSuggestionsModal,
    ExportCollectionModal,
    ImportCollectionModal,
    PrintingSelectionModal,
)


class TestAddToCollectionModal:
    """Tests for AddToCollectionModal."""

    @pytest.mark.asyncio
    async def test_modal_initializes_with_card_name(self) -> None:
        """Test modal initializes with pre-filled card name."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = AddToCollectionModal("Lightning Bolt")
            pilot.app.push_screen(modal)
            await pilot.pause()

            # Verify card name is pre-filled
            card_input = modal.query_one("#card-name-input", Input)
            assert card_input.value == "Lightning Bolt"

    @pytest.mark.asyncio
    async def test_modal_initializes_empty(self) -> None:
        """Test modal initializes with empty card name."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = AddToCollectionModal()
            pilot.app.push_screen(modal)
            await pilot.pause()

            card_input = modal.query_one("#card-name-input", Input)
            assert card_input.value == ""

    @pytest.mark.asyncio
    async def test_on_mount_focuses_card_input_when_empty(self) -> None:
        """Test that card name input gets focus when empty."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = AddToCollectionModal()
            pilot.app.push_screen(modal)
            await pilot.pause()

            # Focus should be on card name input
            assert pilot.app.focused == modal.query_one("#card-name-input", Input)

    @pytest.mark.asyncio
    async def test_on_mount_focuses_qty_input_when_prefilled(self) -> None:
        """Test that quantity input gets focus when card name is pre-filled."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = AddToCollectionModal("Lightning Bolt")
            pilot.app.push_screen(modal)
            await pilot.pause()

            # Focus should be on quantity input
            assert pilot.app.focused == modal.query_one("#qty-input", Input)

    @pytest.mark.asyncio
    async def test_quantity_buttons_select_quantity(self) -> None:
        """Test that clicking quantity buttons updates input."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = AddToCollectionModal()
            pilot.app.push_screen(modal)
            await pilot.pause()

            # Click qty-3 button
            await pilot.click("#qty-3")
            await pilot.pause()

            qty_input = modal.query_one("#qty-input", Input)
            assert qty_input.value == "3"

    @pytest.mark.asyncio
    async def test_number_key_quick_select(self) -> None:
        """Test that number keys 1-4 quick-select quantity."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = AddToCollectionModal()
            pilot.app.push_screen(modal)
            await pilot.pause()

            # Focus quantity input
            qty_input = modal.query_one("#qty-input", Input)
            qty_input.focus()

            # Press 4
            await pilot.press("4")
            await pilot.pause()

            assert qty_input.value == "4"

    @pytest.mark.asyncio
    async def test_cancel_with_escape(self) -> None:
        """Test canceling with Escape key."""
        result = None

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = AddToCollectionModal()

            def handle_result(r: AddToCollectionResult | None) -> None:
                nonlocal result
                result = r

            pilot.app.push_screen(modal, handle_result)
            await pilot.pause()

            # Press escape
            await pilot.press("escape")
            await pilot.pause()

            # Should dismiss with None
            assert result is None

    @pytest.mark.asyncio
    async def test_add_card_with_button(self) -> None:
        """Test adding card with Add button."""
        result = None

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = AddToCollectionModal()

            def handle_result(r: AddToCollectionResult | None) -> None:
                nonlocal result
                result = r

            pilot.app.push_screen(modal, handle_result)
            await pilot.pause()

            # Fill in card name
            card_input = modal.query_one("#card-name-input", Input)
            card_input.value = "Sol Ring"

            # Click add
            await pilot.click("#add-btn")
            await pilot.pause()

            # Should return result
            assert result is not None
            assert result.card_name == "Sol Ring"
            assert result.quantity == 1

    @pytest.mark.asyncio
    async def test_add_foil_card(self) -> None:
        """Test adding foil card with checkbox."""
        result = None

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = AddToCollectionModal()

            def handle_result(r: AddToCollectionResult | None) -> None:
                nonlocal result
                result = r

            pilot.app.push_screen(modal, handle_result)
            await pilot.pause()

            # Fill in card name
            card_input = modal.query_one("#card-name-input", Input)
            card_input.value = "Black Lotus"

            # Check foil
            foil_cb = modal.query_one("#foil-checkbox", Checkbox)
            foil_cb.value = True

            await pilot.click("#add-btn")
            await pilot.pause()

            assert result is not None
            assert result.foil is True

    @pytest.mark.asyncio
    async def test_empty_card_name_shows_error(self) -> None:
        """Test that empty card name prevents submission."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = AddToCollectionModal()
            pilot.app.push_screen(modal)
            await pilot.pause()

            # Leave card name empty, click add
            await pilot.click("#add-btn")
            await pilot.pause()

            # Should still be on modal
            assert pilot.app.screen == modal


class TestImportCollectionModal:
    """Tests for ImportCollectionModal."""

    @pytest.mark.asyncio
    async def test_modal_initializes(self) -> None:
        """Test modal initializes correctly."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = ImportCollectionModal()
            pilot.app.push_screen(modal)
            await pilot.pause()

            # Should have text area
            from textual.widgets import TextArea

            text_area = modal.query_one("#import-text-area", TextArea)
            assert text_area is not None

    @pytest.mark.asyncio
    async def test_import_with_text(self) -> None:
        """Test importing with text."""
        result = None

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test(size=(100, 40)) as pilot:
            modal = ImportCollectionModal()

            def handle_result(r: str | None) -> None:
                nonlocal result
                result = r

            pilot.app.push_screen(modal, handle_result)
            await pilot.pause()

            # Add text
            from textual.widgets import TextArea

            text_area = modal.query_one("#import-text-area", TextArea)
            text_area.text = "4 Lightning Bolt\n2 Counterspell"

            await pilot.click("#import-btn")
            await pilot.pause()

            assert result is not None
            assert "Lightning Bolt" in result

    @pytest.mark.asyncio
    async def test_cancel_import(self) -> None:
        """Test canceling import."""
        result = "should-be-none"

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = ImportCollectionModal()

            def handle_result(r: str | None) -> None:
                nonlocal result
                result = r

            pilot.app.push_screen(modal, handle_result)
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

            assert result is None


class TestExportCollectionModal:
    """Tests for ExportCollectionModal."""

    @pytest.mark.asyncio
    async def test_modal_displays_export_text(self) -> None:
        """Test modal displays export text."""
        export_text = "4 Lightning Bolt\n2 Counterspell"

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = ExportCollectionModal(export_text)
            pilot.app.push_screen(modal)
            await pilot.pause()

            from textual.widgets import TextArea

            text_area = modal.query_one("#export-text-area", TextArea)
            assert text_area.text == export_text

    @pytest.mark.asyncio
    async def test_close_modal(self) -> None:
        """Test closing modal."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = ExportCollectionModal("test")
            pilot.app.push_screen(modal)
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

            # Should be dismissed
            assert pilot.app.screen != modal


class TestConfirmDeleteModal:
    """Tests for ConfirmDeleteModal."""

    @pytest.mark.asyncio
    async def test_modal_shows_card_info(self) -> None:
        """Test modal shows card information."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = ConfirmDeleteModal("Lightning Bolt", quantity=4, foil_quantity=1)
            pilot.app.push_screen(modal)
            await pilot.pause()

            # Should have the correct card name
            assert modal._card_name == "Lightning Bolt"
            assert modal._quantity == 4
            assert modal._foil_quantity == 1

    @pytest.mark.asyncio
    async def test_confirm_deletion_with_button(self) -> None:
        """Test confirming deletion with button."""
        result = False

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = ConfirmDeleteModal("Sol Ring")

            def handle_result(r: bool) -> None:
                nonlocal result
                result = r

            pilot.app.push_screen(modal, handle_result)
            await pilot.pause()

            await pilot.click("#delete-btn")
            await pilot.pause()

            assert result is True

    @pytest.mark.asyncio
    async def test_confirm_deletion_with_y_key(self) -> None:
        """Test confirming deletion with Y key."""
        result = False

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = ConfirmDeleteModal("Sol Ring")

            def handle_result(r: bool) -> None:
                nonlocal result
                result = r

            pilot.app.push_screen(modal, handle_result)
            await pilot.pause()

            await pilot.press("y")
            await pilot.pause()

            assert result is True

    @pytest.mark.asyncio
    async def test_cancel_deletion_with_n_key(self) -> None:
        """Test canceling deletion with N key."""
        result = True

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = ConfirmDeleteModal("Sol Ring")

            def handle_result(r: bool) -> None:
                nonlocal result
                result = r

            pilot.app.push_screen(modal, handle_result)
            await pilot.pause()

            await pilot.press("n")
            await pilot.pause()

            assert result is False


class TestPrintingSelectionModal:
    """Tests for PrintingSelectionModal."""

    @pytest.mark.asyncio
    async def test_modal_initializes_with_cards(self) -> None:
        """Test modal initializes with card list."""
        cards = [
            ("Lightning Bolt", 5),
            ("Counterspell", 3),
        ]

        mock_db = AsyncMock()
        mock_db.get_all_printings = AsyncMock(return_value=[])

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = PrintingSelectionModal(cards, mock_db)
            pilot.app.push_screen(modal)
            await pilot.pause()

            # Should have both cards in the card list
            assert len(modal._cards) == 2
            assert modal._cards[0][0] == "Lightning Bolt"
            assert modal._cards[1][0] == "Counterspell"

    @pytest.mark.asyncio
    async def test_skip_printing_selection(self) -> None:
        """Test skipping printing selection."""
        result = "should-be-none"

        mock_db = AsyncMock()
        mock_db.get_all_printings = AsyncMock(return_value=[])

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = PrintingSelectionModal([("Sol Ring", 2)], mock_db)

            def handle_result(r: dict[str, tuple[str, str]] | None) -> None:
                nonlocal result
                result = r

            pilot.app.push_screen(modal, handle_result)
            await pilot.pause()

            await pilot.click("#skip-btn")
            await pilot.pause()

            assert result is None


class TestDeckSuggestionsModal:
    """Tests for DeckSuggestionsModal."""

    @pytest.mark.asyncio
    async def test_modal_initializes_with_cards(self) -> None:
        """Test modal initializes with card list."""
        cards = [
            CollectionCardInfo(name="Lightning Bolt", type_line="Instant", colors=["R"]),
            CollectionCardInfo(name="Counterspell", type_line="Instant", colors=["U"]),
        ]

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = DeckSuggestionsModal(cards)
            pilot.app.push_screen(modal)
            await pilot.pause()

            # Should have both cards
            assert len(modal._card_info_list) == 2

    @pytest.mark.asyncio
    async def test_switch_format_to_standard(self) -> None:
        """Test switching to standard format."""
        cards = [
            CollectionCardInfo(name="Lightning Bolt"),
        ]

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = DeckSuggestionsModal(cards)
            pilot.app.push_screen(modal)
            await pilot.pause()

            # Click standard button
            await pilot.click("#btn-standard")
            await pilot.pause()

            assert modal._current_format == "standard"

    @pytest.mark.asyncio
    async def test_close_modal(self) -> None:
        """Test closing modal."""
        result = "should-be-none"

        cards = [CollectionCardInfo(name="Sol Ring")]

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = DeckSuggestionsModal(cards)

            def handle_result(r: CreateDeckResult | None) -> None:
                nonlocal result
                result = r

            pilot.app.push_screen(modal, handle_result)
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

            assert result is None

    @pytest.mark.asyncio
    async def test_create_deck_without_selection_shows_warning(self) -> None:
        """Test creating deck without selection shows warning."""
        cards = [CollectionCardInfo(name="Sol Ring")]

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = DeckSuggestionsModal(cards)
            modal._selected_suggestion = None
            pilot.app.push_screen(modal)
            await pilot.pause()

            # Try to create deck
            await pilot.click("#create-btn")
            await pilot.pause()

            # Should still be on modal
            assert pilot.app.screen == modal


class TestCollectionCardInfo:
    """Tests for CollectionCardInfo dataclass."""

    def test_creates_with_minimal_info(self) -> None:
        """Test creating with just name."""
        info = CollectionCardInfo(name="Lightning Bolt")
        assert info.name == "Lightning Bolt"
        assert info.type_line is None

    def test_creates_with_full_info(self) -> None:
        """Test creating with all fields."""
        info = CollectionCardInfo(
            name="Lightning Bolt",
            type_line="Instant",
            colors=["R"],
            mana_cost="{R}",
            text="Lightning Bolt deals 3 damage to any target.",
        )
        assert info.name == "Lightning Bolt"
        assert info.type_line == "Instant"
        assert info.colors == ["R"]


class TestCreateDeckResult:
    """Tests for CreateDeckResult dataclass."""

    def test_creates_with_minimal_info(self) -> None:
        """Test creating with minimal fields."""
        result = CreateDeckResult(
            deck_name="My Deck",
            card_names=["Sol Ring", "Lightning Bolt"],
        )
        assert result.deck_name == "My Deck"
        assert result.commander is None
        assert result.format_type == "commander"

    def test_creates_with_commander(self) -> None:
        """Test creating with commander."""
        result = CreateDeckResult(
            deck_name="Commander Deck",
            card_names=["Sol Ring"],
            commander="Atraxa",
            format_type="commander",
        )
        assert result.commander == "Atraxa"
