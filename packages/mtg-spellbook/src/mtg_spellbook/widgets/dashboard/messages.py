"""Messages for dashboard interactions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from textual.message import Message

if TYPE_CHECKING:
    from mtg_core.data.models import Card, Set
    from mtg_core.data.models.responses import ArtistSummary, CardSummary


# Active messages for dashboard V4 (interactive dashboard)
QuickLinkAction = Literal["artists", "sets", "decks", "collection", "random"]


class QuickLinkActivated(Message):
    """Posted when a quick link button is activated."""

    def __init__(self, action: QuickLinkAction) -> None:
        super().__init__()
        self.action = action


class SearchResultSelected(Message):
    """Posted when a search result is selected from dropdown."""

    def __init__(self, card: CardSummary) -> None:
        super().__init__()
        self.card = card


class SearchSubmitted(Message):
    """Posted when search is submitted without dropdown selection."""

    def __init__(self, query: str) -> None:
        super().__init__()
        self.query = query


# Legacy messages (kept for backward compatibility)
class DashboardAction(Message):
    """Legacy - use QuickLinkActivated instead."""

    def __init__(self, action: Literal["artists", "sets", "decks", "random"]) -> None:
        super().__init__()
        self.action = action


class ArtistClicked(Message):
    """Legacy - dashboard artist click."""

    def __init__(self, artist: ArtistSummary) -> None:
        super().__init__()
        self.artist = artist


class CardClicked(Message):
    """Legacy - dashboard card click."""

    def __init__(self, card: Card) -> None:
        super().__init__()
        self.card = card


class SetClicked(Message):
    """Legacy - dashboard set click."""

    def __init__(self, set_info: Set) -> None:
        super().__init__()
        self.set_info = set_info


class RefreshDashboard(Message):
    """Legacy - refresh dashboard."""

    pass
