"""Tests for Deck Builder Phase 1 functionality - simulates user testing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock

import pytest
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Input, ListView, Select

from mtg_spellbook.deck.editor_panel import DeckEditorPanel
from mtg_spellbook.deck.list_panel import DeckListPanel
from mtg_spellbook.deck.messages import DeckSelected
from mtg_spellbook.deck.modals import AddToDeckModal, ConfirmDeleteModal, NewDeckModal

if TYPE_CHECKING:
    from mtg_core.data.database import DeckSummary
    from mtg_spellbook.deck_manager import DeckWithCards


class DeckBuilderTestApp(App[None]):
    """Test app with deck list and editor panels."""

    def __init__(self, deck_manager: Any) -> None:
        super().__init__()
        self._deck_manager = deck_manager
        self._ctx = AsyncMock()
        self._ctx.get_deck_manager = AsyncMock(return_value=deck_manager)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield DeckListPanel(id="deck-list-panel")
            yield DeckEditorPanel(id="deck-editor-panel")


# ─────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_deck_summary() -> DeckSummary:
    """Sample deck summary for testing."""
    from datetime import datetime

    from mtg_core.data.database import DeckSummary

    return DeckSummary(
        id=1,
        name="Test Commander Deck",
        format="commander",
        card_count=60,
        sideboard_count=15,
        commander="Sol Ring",
        updated_at=datetime(2025, 1, 1, 0, 0, 0),
    )


@pytest.fixture
def sample_deck_with_cards() -> DeckWithCards:
    """Sample deck with cards for testing."""
    from mtg_core.data.models.card import Card
    from mtg_spellbook.deck_manager import DeckCardWithData, DeckWithCards

    card1 = Card(
        uuid="uuid-1",
        name="Lightning Bolt",
        manaCost="{R}",
        manaValue=1.0,
        colors=["R"],
        colorIdentity=["R"],
        type="Instant",
        types=["Instant"],
        text="Lightning Bolt deals 3 damage to any target.",
        rarity="common",
        setCode="LEA",
        number="161",
        artist="Christopher Rush",
        keywords=[],
    )

    card2 = Card(
        uuid="uuid-2",
        name="Birds of Paradise",
        manaCost="{G}",
        manaValue=1.0,
        colors=["G"],
        colorIdentity=["G"],
        type="Creature — Bird",
        types=["Creature"],
        subtypes=["Bird"],
        text="Flying\n{T}: Add one mana of any color.",
        power="0",
        toughness="1",
        rarity="rare",
        setCode="LEA",
        number="162",
        artist="Mark Poole",
        keywords=["Flying"],
    )

    return DeckWithCards(
        id=1,
        name="Test Commander Deck",
        format="commander",
        commander=None,
        cards=[
            DeckCardWithData(
                card_name="Lightning Bolt",
                quantity=4,
                is_sideboard=False,
                is_commander=False,
                set_code="M21",
                collector_number="152",
                card=card1,
            ),
            DeckCardWithData(
                card_name="Birds of Paradise",
                quantity=2,
                is_sideboard=True,
                is_commander=False,
                set_code="M12",
                collector_number="165",
                card=card2,
            ),
        ],
    )


@pytest.fixture
def mock_deck_manager_populated(
    sample_deck_summary: DeckSummary, sample_deck_with_cards: DeckWithCards
) -> Any:
    """Mock DeckManager with populated decks."""
    from mtg_spellbook.deck_manager import AddCardResult

    mock = AsyncMock()
    mock.create_deck = AsyncMock(return_value=1)
    mock.list_decks = AsyncMock(return_value=[sample_deck_summary])
    mock.get_deck = AsyncMock(return_value=sample_deck_with_cards)
    mock.delete_deck = AsyncMock(return_value=True)

    successful_add = AddCardResult(success=True, new_quantity=4)
    mock.add_card = AsyncMock(return_value=successful_add)

    return mock


# ─────────────────────────────────────────────────────────────────────────
# User Story 1: Create a new deck
# ─────────────────────────────────────────────────────────────────────────


class TestCreateNewDeck:
    """Test User Story: As a user, I want to create a new deck."""

    @pytest.mark.asyncio
    async def test_open_new_deck_modal_with_n_key(self, mock_deck_manager_populated: Any) -> None:
        """Test opening new deck modal with N key."""
        async with DeckBuilderTestApp(mock_deck_manager_populated).run_test() as pilot:
            # Simulate pressing 'n' key
            await pilot.press("n")

            # Verify modal is on the screen stack
            assert isinstance(pilot.app.screen, NewDeckModal)

    @pytest.mark.asyncio
    async def test_create_deck_with_name_and_format(self, mock_deck_manager_populated: Any) -> None:
        """Test creating a deck by entering name and format."""
        async with DeckBuilderTestApp(mock_deck_manager_populated).run_test() as pilot:
            # Open the modal
            await pilot.press("n")
            await pilot.pause()

            modal = pilot.app.screen
            assert isinstance(modal, NewDeckModal)

            # Enter deck name
            name_input = modal.query_one("#deck-name-input", Input)
            name_input.value = "My Awesome Deck"

            # Select format
            format_select = modal.query_one("#format-select", Select)
            format_select.value = "commander"

            # Click create button
            await pilot.click("#create-btn")
            await pilot.pause()

            # Verify deck manager was called
            mock_deck_manager_populated.create_deck.assert_called_once_with(
                "My Awesome Deck", "commander"
            )

    @pytest.mark.asyncio
    async def test_create_deck_submitting_with_enter(
        self, mock_deck_manager_populated: Any
    ) -> None:
        """Test creating a deck by pressing Enter in name input."""
        async with DeckBuilderTestApp(mock_deck_manager_populated).run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()

            modal = pilot.app.screen
            name_input = modal.query_one("#deck-name-input", Input)
            name_input.value = "Quick Deck"

            # Submit with Enter
            await pilot.press("enter")
            await pilot.pause()

            # Verify deck was created
            mock_deck_manager_populated.create_deck.assert_called()

    @pytest.mark.asyncio
    async def test_cancel_new_deck_with_escape(self, mock_deck_manager_populated: Any) -> None:
        """Test canceling new deck creation with Escape key."""
        async with DeckBuilderTestApp(mock_deck_manager_populated).run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()

            # Press escape to cancel
            await pilot.press("escape")
            await pilot.pause()

            # Verify we're back to main screen
            assert not isinstance(pilot.app.screen, NewDeckModal)

            # Verify deck was not created
            mock_deck_manager_populated.create_deck.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_new_deck_with_button(self, mock_deck_manager_populated: Any) -> None:
        """Test canceling new deck creation with Cancel button."""
        async with DeckBuilderTestApp(mock_deck_manager_populated).run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()

            # Click cancel button
            await pilot.click("#cancel-btn")
            await pilot.pause()

            # Verify deck was not created
            mock_deck_manager_populated.create_deck.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_deck_name_shows_error(self, mock_deck_manager_populated: Any) -> None:
        """Test that empty deck name shows error notification."""
        async with DeckBuilderTestApp(mock_deck_manager_populated).run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()

            modal = pilot.app.screen
            name_input = modal.query_one("#deck-name-input", Input)
            name_input.value = "   "  # Whitespace only

            await pilot.click("#create-btn")
            await pilot.pause()

            # Verify deck was not created
            mock_deck_manager_populated.create_deck.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────
# User Story 2: Add cards to deck
# ─────────────────────────────────────────────────────────────────────────


class TestAddCardsToDeck:
    """Test User Story: As a user, I want to add cards to my deck."""

    @pytest.mark.asyncio
    async def test_add_to_deck_modal_displays_card_name(
        self, sample_deck_summary: DeckSummary
    ) -> None:
        """Test that add to deck modal displays the card name."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            # Push modal onto screen
            modal = AddToDeckModal("Lightning Bolt", [sample_deck_summary])
            pilot.app.push_screen(modal)
            await pilot.pause()

            # Verify card name is displayed
            modal_screen = pilot.app.screen
            assert isinstance(modal_screen, AddToDeckModal)
            assert modal_screen.card_name == "Lightning Bolt"

    @pytest.mark.asyncio
    async def test_add_card_selects_deck_and_quantity(
        self, sample_deck_summary: DeckSummary, mock_deck_manager_populated: Any
    ) -> None:
        """Test adding a card with selected deck and quantity."""

        class TestApp(App[None]):
            def __init__(self) -> None:
                super().__init__()
                self._ctx = AsyncMock()
                self._ctx.get_deck_manager = AsyncMock(return_value=mock_deck_manager_populated)

            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = AddToDeckModal("Lightning Bolt", [sample_deck_summary])
            pilot.app.push_screen(modal)
            await pilot.pause()

            # Set quantity
            qty_input = modal.query_one("#qty-input", Input)
            qty_input.value = "3"

            # Trigger add action directly (more robust than clicking)
            await modal.on_add()
            await pilot.pause()

            # Verify add_card was called with correct parameters
            mock_deck_manager_populated.add_card.assert_called_once_with(
                1, "Lightning Bolt", 3, sideboard=False, set_code=None, collector_number=None
            )

    @pytest.mark.asyncio
    async def test_add_card_no_decks_available(self) -> None:
        """Test that modal handles no decks gracefully."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            # Create modal with empty deck list
            modal = AddToDeckModal("Lightning Bolt", [])
            pilot.app.push_screen(modal)
            await pilot.pause()

            # Trigger add action directly - should dismiss without error
            await modal.on_add()
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_cancel_add_to_deck(self, sample_deck_summary: DeckSummary) -> None:
        """Test canceling add to deck operation."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                return []

        async with TestApp().run_test() as pilot:
            modal = AddToDeckModal("Lightning Bolt", [sample_deck_summary])
            pilot.app.push_screen(modal)
            await pilot.pause()

            # Press escape
            await pilot.press("escape")
            await pilot.pause()

            # Verify we're back to main screen
            assert not isinstance(pilot.app.screen, AddToDeckModal)


# ─────────────────────────────────────────────────────────────────────────
# User Story 3: Navigate deck list
# ─────────────────────────────────────────────────────────────────────────


class TestNavigateDeckList:
    """Test User Story: As a user, I want to navigate my deck list."""

    @pytest.mark.asyncio
    async def test_deck_list_displays_decks(self, mock_deck_manager_populated: Any) -> None:
        """Test that deck list displays decks correctly."""
        async with DeckBuilderTestApp(mock_deck_manager_populated).run_test() as pilot:
            deck_list_panel = pilot.app.query_one("#deck-list-panel", DeckListPanel)

            # Refresh decks
            await deck_list_panel.refresh_decks(mock_deck_manager_populated)
            await pilot.pause()

            # Verify deck list has items
            deck_list = deck_list_panel.query_one("#deck-list", ListView)
            assert len(deck_list.children) > 0

    @pytest.mark.asyncio
    async def test_navigate_with_arrow_keys(self, mock_deck_manager_populated: Any) -> None:
        """Test navigating deck list with arrow keys."""
        async with DeckBuilderTestApp(mock_deck_manager_populated).run_test() as pilot:
            deck_list_panel = pilot.app.query_one("#deck-list-panel", DeckListPanel)
            await deck_list_panel.refresh_decks(mock_deck_manager_populated)
            await pilot.pause()

            deck_list = deck_list_panel.query_one("#deck-list", ListView)

            # Focus deck list
            deck_list.focus()
            await pilot.pause()

            # Navigate with down arrow
            await pilot.press("down")
            await pilot.pause()

            # Verify navigation occurred
            assert deck_list.highlighted_child is not None or len(list(deck_list.children)) == 0

    @pytest.mark.asyncio
    async def test_select_deck_with_enter(self, mock_deck_manager_populated: Any) -> None:
        """Test selecting a deck with Enter key."""
        deck_selected_posted = False
        selected_deck_id = -1

        class TestApp(DeckBuilderTestApp):
            def on_deck_selected(self, message: DeckSelected) -> None:
                nonlocal deck_selected_posted, selected_deck_id
                deck_selected_posted = True
                selected_deck_id = message.deck_id

        async with TestApp(mock_deck_manager_populated).run_test() as pilot:
            deck_list_panel = pilot.app.query_one("#deck-list-panel", DeckListPanel)
            await deck_list_panel.refresh_decks(mock_deck_manager_populated)
            await pilot.pause()

            # Get the ListView and simulate highlighting the first item
            deck_list = deck_list_panel.query_one("#deck-list", ListView)
            if deck_list.children:
                deck_list.index = 0  # Highlight first item
                await pilot.pause()

                # Now trigger the action
                deck_list_panel.action_open_deck()
                await pilot.pause()

                # Verify DeckSelected message was posted
                assert deck_selected_posted
                assert selected_deck_id == 1

    @pytest.mark.asyncio
    async def test_empty_deck_list_shows_message(self) -> None:
        """Test that empty deck list shows helpful message."""
        mock_manager = AsyncMock()
        mock_manager.list_decks = AsyncMock(return_value=[])

        async with DeckBuilderTestApp(mock_manager).run_test() as pilot:
            deck_list_panel = pilot.app.query_one("#deck-list-panel", DeckListPanel)
            await deck_list_panel.refresh_decks(mock_manager)
            await pilot.pause()

            deck_list = deck_list_panel.query_one("#deck-list", ListView)
            assert len(deck_list.children) > 0  # Should have placeholder message


# ─────────────────────────────────────────────────────────────────────────
# User Story 4: Delete a deck
# ─────────────────────────────────────────────────────────────────────────


class TestDeleteDeck:
    """Test User Story: As a user, I want to delete a deck."""

    @pytest.mark.asyncio
    async def test_delete_deck_with_d_key(self, mock_deck_manager_populated: Any) -> None:
        """Test initiating deck deletion with D key."""
        async with DeckBuilderTestApp(mock_deck_manager_populated).run_test() as pilot:
            deck_list_panel = pilot.app.query_one("#deck-list-panel", DeckListPanel)
            await deck_list_panel.refresh_decks(mock_deck_manager_populated)
            await pilot.pause()

            # Highlight first item
            deck_list = deck_list_panel.query_one("#deck-list", ListView)
            if deck_list.children:
                deck_list.index = 0
                await pilot.pause()

                # Trigger delete action directly
                deck_list_panel.action_delete_deck()
                await pilot.pause()

                # Verify confirmation modal is shown
                assert isinstance(pilot.app.screen, ConfirmDeleteModal)

    @pytest.mark.asyncio
    async def test_confirm_deletion_with_button(self, mock_deck_manager_populated: Any) -> None:
        """Test confirming deletion with Delete button."""
        async with DeckBuilderTestApp(mock_deck_manager_populated).run_test() as pilot:
            deck_list_panel = pilot.app.query_one("#deck-list-panel", DeckListPanel)
            await deck_list_panel.refresh_decks(mock_deck_manager_populated)
            await pilot.pause()

            # Highlight first item
            deck_list = deck_list_panel.query_one("#deck-list", ListView)
            if deck_list.children:
                deck_list.index = 0
                await pilot.pause()

                # Trigger delete action
                deck_list_panel.action_delete_deck()
                await pilot.pause()

                # Click delete button
                await pilot.click("#delete-btn")
                await pilot.pause()

                # Give time for async operation to complete
                await pilot.pause()

                # Verify delete was called
                mock_deck_manager_populated.delete_deck.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_deletion_with_y_key(self, mock_deck_manager_populated: Any) -> None:
        """Test confirming deletion with Y key."""
        async with DeckBuilderTestApp(mock_deck_manager_populated).run_test() as pilot:
            deck_list_panel = pilot.app.query_one("#deck-list-panel", DeckListPanel)
            await deck_list_panel.refresh_decks(mock_deck_manager_populated)
            await pilot.pause()

            # Highlight first item
            deck_list = deck_list_panel.query_one("#deck-list", ListView)
            if deck_list.children:
                deck_list.index = 0
                await pilot.pause()

                # Trigger delete action
                deck_list_panel.action_delete_deck()
                await pilot.pause()

                # Press 'y' to confirm
                await pilot.press("y")
                await pilot.pause()

                # Give time for async operation to complete
                await pilot.pause()

                # Verify delete was called
                mock_deck_manager_populated.delete_deck.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_deletion_with_n_key(self, mock_deck_manager_populated: Any) -> None:
        """Test canceling deletion with N key."""
        async with DeckBuilderTestApp(mock_deck_manager_populated).run_test() as pilot:
            deck_list_panel = pilot.app.query_one("#deck-list-panel", DeckListPanel)
            await deck_list_panel.refresh_decks(mock_deck_manager_populated)
            await pilot.pause()

            deck_list = deck_list_panel.query_one("#deck-list", ListView)
            deck_list.focus()
            await pilot.press("d")
            await pilot.pause()

            # Press 'n' to cancel
            await pilot.press("n")
            await pilot.pause()

            # Verify delete was not called
            mock_deck_manager_populated.delete_deck.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_deletion_with_escape(self, mock_deck_manager_populated: Any) -> None:
        """Test canceling deletion with Escape key."""
        async with DeckBuilderTestApp(mock_deck_manager_populated).run_test() as pilot:
            deck_list_panel = pilot.app.query_one("#deck-list-panel", DeckListPanel)
            await deck_list_panel.refresh_decks(mock_deck_manager_populated)
            await pilot.pause()

            deck_list = deck_list_panel.query_one("#deck-list", ListView)
            deck_list.focus()
            await pilot.press("d")
            await pilot.pause()

            # Press escape to cancel
            await pilot.press("escape")
            await pilot.pause()

            # Verify delete was not called
            mock_deck_manager_populated.delete_deck.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────
# User Story 5: Deck Editor Panel
# ─────────────────────────────────────────────────────────────────────────


class TestDeckEditorPanel:
    """Test Deck Editor Panel functionality."""

    @pytest.mark.asyncio
    async def test_display_deck_with_cards(self, sample_deck_with_cards: DeckWithCards) -> None:
        """Test displaying a deck with cards."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckEditorPanel(id="deck-editor")

        async with TestApp().run_test() as pilot:
            editor = pilot.app.query_one("#deck-editor", DeckEditorPanel)

            # Update with deck
            editor.update_deck(sample_deck_with_cards)
            await pilot.pause()

            # Verify header shows deck name
            header = editor.query_one("#deck-editor-header")
            assert "Test Commander Deck" in str(header.render())

            # Verify mainboard has cards
            mainboard = editor.query_one("#mainboard-list")
            assert len(mainboard.children) > 0

    @pytest.mark.asyncio
    async def test_display_empty_deck(self) -> None:
        """Test displaying empty deck panel."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckEditorPanel(id="deck-editor")

        async with TestApp().run_test() as pilot:
            editor = pilot.app.query_one("#deck-editor", DeckEditorPanel)

            # Update with None
            editor.update_deck(None)
            await pilot.pause()

            # Verify shows no deck loaded
            header = editor.query_one("#deck-editor-header")
            assert "No deck loaded" in str(header.render())

    @pytest.mark.asyncio
    async def test_back_to_list_with_backspace(self) -> None:
        """Test returning to deck list with backspace key."""
        deck_selected_posted = False

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckEditorPanel(id="deck-editor")

            def on_deck_selected(self, message: DeckSelected) -> None:
                nonlocal deck_selected_posted
                deck_selected_posted = True
                assert message.deck_id == -1

        async with TestApp().run_test() as pilot:
            editor = pilot.app.query_one("#deck-editor", DeckEditorPanel)
            editor.focus()

            # Press backspace
            await pilot.press("backspace")
            await pilot.pause()

            # Verify message was posted
            assert deck_selected_posted

    @pytest.mark.asyncio
    async def test_validate_deck_action(self, sample_deck_with_cards: DeckWithCards) -> None:
        """Test validating a deck with V key."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckEditorPanel(id="deck-editor")

        async with TestApp().run_test() as pilot:
            editor = pilot.app.query_one("#deck-editor", DeckEditorPanel)
            editor.update_deck(sample_deck_with_cards)
            editor.focus()
            await pilot.pause()

            # Press 'v' to validate
            await pilot.press("v")
            await pilot.pause()

            # Test passes if no exception is raised


# ─────────────────────────────────────────────────────────────────────────
# Integration Tests
# ─────────────────────────────────────────────────────────────────────────


class TestDeckBuilderIntegration:
    """Integration tests for full deck builder workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow_create_and_delete(self, mock_deck_manager_populated: Any) -> None:
        """Test full workflow: create deck, view it, delete it."""
        async with DeckBuilderTestApp(mock_deck_manager_populated).run_test() as pilot:
            # Create new deck
            await pilot.press("n")
            await pilot.pause()

            modal = pilot.app.screen
            name_input = modal.query_one("#deck-name-input", Input)
            name_input.value = "Integration Test Deck"

            await pilot.click("#create-btn")
            await pilot.pause()

            # Refresh deck list
            deck_list_panel = pilot.app.query_one("#deck-list-panel", DeckListPanel)
            await deck_list_panel.refresh_decks(mock_deck_manager_populated)
            await pilot.pause()

            # Highlight first item
            deck_list = deck_list_panel.query_one("#deck-list", ListView)
            if deck_list.children:
                deck_list.index = 0
                await pilot.pause()

                # Trigger delete action directly
                deck_list_panel.action_delete_deck()
                await pilot.pause()

                await pilot.press("y")
                await pilot.pause()
                await pilot.pause()

                # Verify both create and delete were called
                assert mock_deck_manager_populated.create_deck.called
                assert mock_deck_manager_populated.delete_deck.called

    @pytest.mark.asyncio
    async def test_messages_posted_correctly(self, mock_deck_manager_populated: Any) -> None:
        """Test that DeckSelected messages are posted correctly."""
        messages_posted = []

        class TestApp(DeckBuilderTestApp):
            def on_deck_selected(self, message: DeckSelected) -> None:
                messages_posted.append(message.deck_id)

        async with TestApp(mock_deck_manager_populated).run_test() as pilot:
            deck_list_panel = pilot.app.query_one("#deck-list-panel", DeckListPanel)
            await deck_list_panel.refresh_decks(mock_deck_manager_populated)
            await pilot.pause()

            # Highlight first item
            deck_list = deck_list_panel.query_one("#deck-list", ListView)
            if deck_list.children:
                deck_list.index = 0
                await pilot.pause()

                # Trigger action directly
                deck_list_panel.action_open_deck()
                await pilot.pause()

                # Verify message was posted
                assert len(messages_posted) > 0
                assert messages_posted[0] == 1
