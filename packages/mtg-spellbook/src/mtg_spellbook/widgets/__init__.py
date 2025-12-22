"""Reusable widgets for the MTG Spellbook TUI.

This package provides the UI components:
- CardPanel: Main card display with tabs for details, art, rulings, etc.
- Dashboard: Discovery-first landing page with artist spotlight
- EnhancedArtNavigator: Gallery view art navigation with grid and preview
- SynergyPanel: Source card display for synergy mode (legacy)
- EnhancedSynergyPanel: Categorized synergy discovery with tabs and comparison
- ResultsList: Search results list with keyboard navigation
- PaginationHeader: Pagination info and controls display
- GoToPageModal: Modal dialog for jumping to a specific page
- ArtistPortfolioView: Artist portfolio with stats, gallery, and preview
- ArtistBrowser: Browse all artists alphabetically with search
- BlockBrowser: Browse MTG blocks and storylines with tree view
- SetDetailView: Set exploration with info, card list, and preview
"""

from .art_navigator import HAS_IMAGE_SUPPORT, EnhancedArtNavigator
from .artist_browser import ArtistBrowser, ArtistBrowserClosed, ArtistSelected
from .artist_portfolio import (
    ArtistGallery,
    ArtistPortfolioView,
    ArtistStats,
    ArtistStatsPanel,
    CardPreviewPanel,
    CardSelected,
    ClosePortfolio,
    ViewArtwork,
)
from .block_browser import (
    BlockBrowser,
    BlockBrowserClosed,
    BlockSelected,
    SetFromBlockSelected,
)
from .card_panel import CardPanel
from .card_result_item import CardResultItem
from .dashboard import (
    ArtistClicked,
    CardClicked,
    Dashboard,
    DashboardAction,
    RefreshDashboard,
    SetClicked,
)
from .goto_page_modal import GoToPageModal
from .menu import MenuActionRequested, MenuBar, MenuToggled
from .pagination_header import PaginationHeader
from .results_list import ResultsList
from .set_detail import (
    SetCardList,
    SetCardPreviewPanel,
    SetCardSelected,
    SetDetailClosed,
    SetDetailView,
    SetInfoPanel,
    SetStats,
)
from .synergy import (
    EnhancedSynergyPanel,
    SortOrder,
    SynergyCardItem,
    SynergyPanelClosed,
    SynergySelected,
    TypeIndex,
)
from .synergy_panel import SynergyPanel

__all__ = [
    "HAS_IMAGE_SUPPORT",
    "ArtistBrowser",
    "ArtistBrowserClosed",
    "ArtistClicked",
    "ArtistGallery",
    "ArtistPortfolioView",
    "ArtistSelected",
    "ArtistStats",
    "ArtistStatsPanel",
    "BlockBrowser",
    "BlockBrowserClosed",
    "BlockSelected",
    "CardClicked",
    "CardPanel",
    "CardPreviewPanel",
    "CardResultItem",
    "CardSelected",
    "ClosePortfolio",
    "Dashboard",
    "DashboardAction",
    "EnhancedArtNavigator",
    "EnhancedSynergyPanel",
    "GoToPageModal",
    "MenuActionRequested",
    "MenuBar",
    "MenuToggled",
    "PaginationHeader",
    "RefreshDashboard",
    "ResultsList",
    "SetCardList",
    "SetCardPreviewPanel",
    "SetCardSelected",
    "SetClicked",
    "SetDetailClosed",
    "SetDetailView",
    "SetFromBlockSelected",
    "SetInfoPanel",
    "SetStats",
    "SortOrder",
    "SynergyCardItem",
    "SynergyPanel",
    "SynergyPanelClosed",
    "SynergySelected",
    "TypeIndex",
    "ViewArtwork",
]
