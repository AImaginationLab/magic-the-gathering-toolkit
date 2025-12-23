"""Tests for RecommendationScreen add-to-deck functionality.

These tests verify that the _do_add_to_deck method correctly calls the deck manager
and handles success/failure cases. The bug was that _add_to_deck only posted a message
that never reached DeckFullScreen. The fix was to actually call deck_manager.add_card.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def mock_deck() -> Any:
    """Create a mock deck."""
    deck = Mock()
    deck.id = 1
    deck.name = "Test Deck"
    return deck


@pytest.fixture
def mock_deck_manager_success() -> Any:
    """Create a mock deck manager that returns success."""
    manager = AsyncMock()
    result = Mock()
    result.success = True
    result.error = None
    manager.add_card = AsyncMock(return_value=result)
    return manager


@pytest.fixture
def mock_deck_manager_failure() -> Any:
    """Create a mock deck manager that returns failure."""
    manager = AsyncMock()
    result = Mock()
    result.success = False
    result.error = "Card not found"
    manager.add_card = AsyncMock(return_value=result)
    return manager


class TestDoAddToDeck:
    """Tests for the _do_add_to_deck async method.

    This tests the core add-to-deck logic without requiring the full
    RecommendationScreen UI which has many side effects on mount.
    """

    @pytest.mark.asyncio
    async def test_add_card_calls_deck_manager(
        self,
        mock_deck: Any,
        mock_deck_manager_success: Any,
    ) -> None:
        """Test that _do_add_to_deck calls the deck manager with correct args."""
        # Import here to avoid issues with textual app context
        from mtg_spellbook.recommendations.screen import RecommendationScreen

        # Create a minimal screen instance without running in app context
        # We'll just test the async method directly
        screen = object.__new__(RecommendationScreen)
        screen._deck = mock_deck
        screen._deck_manager = mock_deck_manager_success
        screen.notify = Mock()
        screen.post_message = Mock()

        # Call the core async method directly (bypass the @work decorator)
        await RecommendationScreen._do_add_to_deck.__wrapped__(screen, "Lightning Bolt", 1)

        # Verify deck_manager.add_card was called
        mock_deck_manager_success.add_card.assert_called_once_with(1, "Lightning Bolt", 1)
        # Verify success notification was shown
        screen.notify.assert_called()
        assert "Added 1x Lightning Bolt" in str(screen.notify.call_args)

    @pytest.mark.asyncio
    async def test_add_card_with_quantity(
        self,
        mock_deck: Any,
        mock_deck_manager_success: Any,
    ) -> None:
        """Test adding multiple copies of a card."""
        from mtg_spellbook.recommendations.screen import RecommendationScreen

        screen = object.__new__(RecommendationScreen)
        screen._deck = mock_deck
        screen._deck_manager = mock_deck_manager_success
        screen.notify = Mock()
        screen.post_message = Mock()

        await RecommendationScreen._do_add_to_deck.__wrapped__(screen, "Lightning Bolt", 4)

        mock_deck_manager_success.add_card.assert_called_once_with(1, "Lightning Bolt", 4)
        assert "Added 4x Lightning Bolt" in str(screen.notify.call_args)

    @pytest.mark.asyncio
    async def test_add_card_handles_failure(
        self,
        mock_deck: Any,
        mock_deck_manager_failure: Any,
    ) -> None:
        """Test that failure shows error notification."""
        from mtg_spellbook.recommendations.screen import RecommendationScreen

        screen = object.__new__(RecommendationScreen)
        screen._deck = mock_deck
        screen._deck_manager = mock_deck_manager_failure
        screen.notify = Mock()
        screen.post_message = Mock()

        await RecommendationScreen._do_add_to_deck.__wrapped__(screen, "Lightning Bolt", 1)

        # Verify error notification was shown
        screen.notify.assert_called_once()
        call_args = screen.notify.call_args
        assert "Failed" in call_args[0][0]
        assert call_args[1]["severity"] == "error"

    @pytest.mark.asyncio
    async def test_add_card_without_deck_returns_early(
        self,
        mock_deck_manager_success: Any,
    ) -> None:
        """Test that missing deck causes early return."""
        from mtg_spellbook.recommendations.screen import RecommendationScreen

        screen = object.__new__(RecommendationScreen)
        screen._deck = None  # No deck
        screen._deck_manager = mock_deck_manager_success
        screen.notify = Mock()
        screen.post_message = Mock()

        await RecommendationScreen._do_add_to_deck.__wrapped__(screen, "Lightning Bolt", 1)

        # Should not call deck_manager
        mock_deck_manager_success.add_card.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_card_without_deck_manager_returns_early(
        self,
        mock_deck: Any,
    ) -> None:
        """Test that missing deck manager causes early return."""
        from mtg_spellbook.recommendations.screen import RecommendationScreen

        screen = object.__new__(RecommendationScreen)
        screen._deck = mock_deck
        screen._deck_manager = None  # No deck manager
        screen.notify = Mock()
        screen.post_message = Mock()

        await RecommendationScreen._do_add_to_deck.__wrapped__(screen, "Lightning Bolt", 1)

        # Should not crash, just return early
        screen.notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_card_posts_message_on_success(
        self,
        mock_deck: Any,
        mock_deck_manager_success: Any,
    ) -> None:
        """Test that success posts AddCardToDeck message."""
        from mtg_spellbook.recommendations.messages import AddCardToDeck
        from mtg_spellbook.recommendations.screen import RecommendationScreen

        screen = object.__new__(RecommendationScreen)
        screen._deck = mock_deck
        screen._deck_manager = mock_deck_manager_success
        screen.notify = Mock()
        screen.post_message = Mock()

        await RecommendationScreen._do_add_to_deck.__wrapped__(screen, "Lightning Bolt", 2)

        # Should post message for DeckFullScreen to refresh
        screen.post_message.assert_called_once()
        msg = screen.post_message.call_args[0][0]
        assert isinstance(msg, AddCardToDeck)
        assert msg.card_name == "Lightning Bolt"
        assert msg.quantity == 2


class TestAddToDeckValidation:
    """Tests for _add_to_deck input validation."""

    def test_add_to_deck_without_recommendation_does_nothing(self) -> None:
        """Test that _add_to_deck does nothing without a selected recommendation."""
        from mtg_spellbook.recommendations.screen import RecommendationScreen

        screen = object.__new__(RecommendationScreen)
        screen._current_recommendation = None
        screen._deck = Mock()
        screen._deck_manager = AsyncMock()
        screen.notify = Mock()

        # Should return early without error
        screen._add_to_deck(1)

        # Nothing should happen
        screen.notify.assert_not_called()

    def test_add_to_deck_without_deck_manager_shows_error(self) -> None:
        """Test that _add_to_deck shows error without deck manager."""
        from mtg_spellbook.recommendations.screen import RecommendationScreen

        screen = object.__new__(RecommendationScreen)
        rec = Mock()
        rec.name = "Lightning Bolt"
        screen._current_recommendation = rec
        screen._deck = Mock()
        screen._deck_manager = None
        screen.notify = Mock()

        screen._add_to_deck(1)

        # Should show error notification
        screen.notify.assert_called_once()
        assert "Cannot add" in screen.notify.call_args[0][0]


class TestActionMethods:
    """Tests for action methods that call _add_to_deck."""

    def test_action_add_one_calls_add_to_deck_with_1(self) -> None:
        """Test action_add_one passes quantity 1."""
        from mtg_spellbook.recommendations.screen import RecommendationScreen

        screen = object.__new__(RecommendationScreen)
        screen._add_to_deck = Mock()
        screen._current_recommendation = Mock()

        screen.action_add_one()

        screen._add_to_deck.assert_called_once_with(1)

    def test_action_add_qty_methods(self) -> None:
        """Test all action_add_qty_* methods pass correct quantities."""
        from mtg_spellbook.recommendations.screen import RecommendationScreen

        screen = object.__new__(RecommendationScreen)
        screen._add_to_deck = Mock()
        screen._current_recommendation = Mock()

        screen.action_add_qty_1()
        screen._add_to_deck.assert_called_with(1)

        screen.action_add_qty_2()
        screen._add_to_deck.assert_called_with(2)

        screen.action_add_qty_3()
        screen._add_to_deck.assert_called_with(3)

        screen.action_add_qty_4()
        screen._add_to_deck.assert_called_with(4)
