"""Messages for set detail view components."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.message import Message

if TYPE_CHECKING:
    from mtg_core.data.models.responses import CardSummary


class SetCardSelected(Message):
    """Posted when a card is selected in the set card list."""

    def __init__(self, card: CardSummary) -> None:
        super().__init__()
        self.card = card


class SetDetailClosed(Message):
    """Posted when the set detail view is closed."""

    def __init__(self, set_code: str) -> None:
        super().__init__()
        self.set_code = set_code
