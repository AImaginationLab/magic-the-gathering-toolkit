"""Recommendations module - full-screen recommendations view."""

from .card_item import RecommendationCardItem
from .detail_panel import RecommendationDetailPanel
from .filter_panel import (
    FilterChanged,
    FilterType,
    RecommendationFilterPanel,
    SortChanged,
    SortOrder,
)
from .messages import AddCardToDeck, RecommendationScreenClosed, RecommendationSelected
from .screen import RecommendationScreen

__all__ = [
    "AddCardToDeck",
    "FilterChanged",
    "FilterType",
    "RecommendationCardItem",
    "RecommendationDetailPanel",
    "RecommendationFilterPanel",
    "RecommendationScreen",
    "RecommendationScreenClosed",
    "RecommendationSelected",
    "SortChanged",
    "SortOrder",
]
