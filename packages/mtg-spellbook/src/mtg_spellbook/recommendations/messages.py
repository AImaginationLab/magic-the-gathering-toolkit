"""Messages for the recommendations screen."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.message import Message

if TYPE_CHECKING:
    from mtg_core.tools.recommendations.hybrid import ScoredRecommendation


class RecommendationSelected(Message):
    """Posted when a recommendation card is selected for viewing."""

    def __init__(self, rec: ScoredRecommendation) -> None:
        super().__init__()
        self.recommendation = rec


class AddCardToDeck(Message):
    """Posted when user wants to add a recommendation to their deck."""

    def __init__(self, card_name: str, quantity: int = 1) -> None:
        super().__init__()
        self.card_name = card_name
        self.quantity = quantity


class RecommendationScreenClosed(Message):
    """Posted when the recommendation screen is closed."""

    pass
