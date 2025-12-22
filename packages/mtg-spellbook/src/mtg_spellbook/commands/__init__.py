"""Command handlers for the MTG Spellbook TUI.

This package provides modular command handling through composable mixins:
- CommandRouterMixin: Routes commands to appropriate handlers
- CardCommandsMixin: Card lookup and search
- SynergyCommandsMixin: Synergy and combo discovery
- InfoCommandsMixin: Rulings, legalities, price, art
- SetCommandsMixin: Set browsing and statistics
- ArtistCommandsMixin: Artist discovery and portfolio
- BlockCommandsMixin: Block browsing and recent releases
- CommandHelpersMixin: Shared helper methods
- PaginationCommandsMixin: Pagination navigation

The CommandHandlersMixin combines all mixins for backwards compatibility.
"""

from .artist import ArtistCommandsMixin
from .base import AppProtocol, CommandRouterMixin
from .blocks import BlockCommandsMixin
from .card import CardCommandsMixin
from .helpers import CommandHelpersMixin
from .info import InfoCommandsMixin
from .pagination import PaginationCommandsMixin
from .sets import SetCommandsMixin
from .synergy import SynergyCommandsMixin


class CommandHandlersMixin(  # type: ignore[misc]  # Mixin stubs vs @work-decorated implementations
    CommandRouterMixin,
    CardCommandsMixin,
    SynergyCommandsMixin,
    InfoCommandsMixin,
    SetCommandsMixin,
    ArtistCommandsMixin,
    BlockCommandsMixin,
    CommandHelpersMixin,
    PaginationCommandsMixin,
):
    """Combined mixin providing all command handling functionality.

    This mixin combines all command-related mixins for use with the App class.
    It maintains backwards compatibility with the original single-class design.
    """

    pass


__all__ = [
    "AppProtocol",
    "ArtistCommandsMixin",
    "BlockCommandsMixin",
    "CardCommandsMixin",
    "CommandHandlersMixin",
    "CommandHelpersMixin",
    "CommandRouterMixin",
    "InfoCommandsMixin",
    "PaginationCommandsMixin",
    "SetCommandsMixin",
    "SynergyCommandsMixin",
]
