"""Messages for menu widget communication."""

from __future__ import annotations

from textual.message import Message


class MenuActionRequested(Message):
    """Posted when a menu item is selected.

    The action string corresponds to an action_* method on the app.
    For example, action="browse_artists" maps to action_browse_artists().
    """

    def __init__(self, action: str) -> None:
        super().__init__()
        self.action = action


class MenuToggled(Message):
    """Posted when the menu expands or collapses."""

    def __init__(self, *, expanded: bool) -> None:
        super().__init__()
        self.expanded = expanded
