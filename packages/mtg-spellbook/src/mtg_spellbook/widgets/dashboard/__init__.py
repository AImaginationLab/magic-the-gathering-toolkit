"""Dashboard widget for MTG Spellbook.

V4 redesign: Interactive dashboard with Quick Links, Search Bar, and Artist Spotlight.

Layout:
- TOP: Quick Links bar (focusable buttons for Artists/Sets/Decks/Collection/Random)
- MIDDLE: Search bar with autocomplete dropdown
- BOTTOM: Artist spotlight

Tab navigation flows through all sections.
"""

from .messages import (
    # Legacy messages
    ArtistClicked,
    CardClicked,
    DashboardAction,
    # Active messages
    QuickLinkActivated,
    RefreshDashboard,
    SearchResultSelected,
    SearchSubmitted,
    SetClicked,
)
from .quick_links import QuickLinkButton, QuickLinksBar
from .search_bar import SearchBar, SearchResultItem
from .widget import Dashboard

__all__ = [
    # Legacy messages
    "ArtistClicked",
    "CardClicked",
    # Main widget
    "Dashboard",
    "DashboardAction",
    # Active messages
    "QuickLinkActivated",
    "QuickLinkButton",
    # Quick links
    "QuickLinksBar",
    "RefreshDashboard",
    # Search bar
    "SearchBar",
    "SearchResultItem",
    "SearchResultSelected",
    "SearchSubmitted",
    "SetClicked",
]
