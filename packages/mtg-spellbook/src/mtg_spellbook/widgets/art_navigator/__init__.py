"""Art navigation widgets for card image display.

This package provides multi-mode artwork viewing:
- EnhancedArtNavigator: Multi-mode navigator (gallery, focus, compare)
- ViewModeToggle: Mode selection toggle
- FocusView: Immersive single-card view
- CompareView: Side-by-side printing comparison
- PrintingsGrid: Shop-style grid layout (4 cards per row)
- ShopCard: Shop-style card display with set/rarity/price
- PreviewPanel: Enlarged preview with metadata
"""

from __future__ import annotations

try:
    from textual_image.widget import Image as TImage

    HAS_IMAGE_SUPPORT = True
except ImportError:
    HAS_IMAGE_SUPPORT = False
    TImage = None  # type: ignore[assignment]

from .compare import CompareView
from .enhanced import EnhancedArtNavigator
from .focus import FocusView
from .grid import PrintingsGrid
from .messages import ArtistSelected
from .preview import PreviewPanel
from .shop_card import ShopCard
from .thumbnail import ThumbnailCard
from .view_toggle import ViewMode, ViewModeToggle

__all__ = [
    "HAS_IMAGE_SUPPORT",
    "ArtistSelected",
    "CompareView",
    "EnhancedArtNavigator",
    "FocusView",
    "PreviewPanel",
    "PrintingsGrid",
    "ShopCard",
    "TImage",
    "ThumbnailCard",
    "ViewMode",
    "ViewModeToggle",
]
