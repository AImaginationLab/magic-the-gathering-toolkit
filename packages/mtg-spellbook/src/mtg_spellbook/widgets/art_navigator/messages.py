"""Message classes for art navigator events."""

from __future__ import annotations

from textual.message import Message


class ArtistSelected(Message):
    """Message sent when user wants to browse cards by an artist."""

    def __init__(self, artist_name: str, card_name: str | None = None) -> None:
        super().__init__()
        self.artist_name = artist_name
        self.card_name = card_name
