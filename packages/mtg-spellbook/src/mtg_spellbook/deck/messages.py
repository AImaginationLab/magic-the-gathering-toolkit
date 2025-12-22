"""Message classes for deck-related events."""

from __future__ import annotations

from textual.message import Message


class DeckSelected(Message):
    """Message sent when a deck is selected."""

    def __init__(self, deck_id: int) -> None:
        super().__init__()
        self.deck_id = deck_id


class DeckCreated(Message):
    """Message sent when a new deck is created."""

    def __init__(self, deck_id: int, name: str) -> None:
        super().__init__()
        self.deck_id = deck_id
        self.name = name


class AddToDeckRequested(Message):
    """Message sent when user wants to add a card to a deck."""

    def __init__(
        self,
        card_name: str,
        set_code: str | None = None,
        collector_number: str | None = None,
    ) -> None:
        super().__init__()
        self.card_name = card_name
        self.set_code = set_code
        self.collector_number = collector_number


class CardAddedToDeck(Message):
    """Message sent when a card is added to a deck."""

    def __init__(self, card_name: str, deck_name: str, quantity: int) -> None:
        super().__init__()
        self.card_name = card_name
        self.deck_name = deck_name
        self.quantity = quantity
