"""Messages for ArtistBrowser widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.message import Message

if TYPE_CHECKING:
    from mtg_core.data.models.responses import ArtistSummary


class ArtistSelected(Message):
    """Message sent when an artist is selected for viewing."""

    def __init__(self, artist: ArtistSummary) -> None:
        super().__init__()
        self.artist = artist


class ArtistBrowserClosed(Message):
    """Message sent when the artist browser is closed."""

    pass
