"""Messages for BlockBrowser widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.message import Message

if TYPE_CHECKING:
    from mtg_core.data.models.responses import BlockSummary, SetSummary


class BlockSelected(Message):
    """Message sent when a block is expanded/selected."""

    def __init__(self, block: BlockSummary) -> None:
        super().__init__()
        self.block = block


class SetFromBlockSelected(Message):
    """Message sent when a set within a block is selected."""

    def __init__(self, set_summary: SetSummary, block_name: str) -> None:
        super().__init__()
        self.set_summary = set_summary
        self.block_name = block_name


class BlockBrowserClosed(Message):
    """Message sent when the block browser is closed."""

    pass
