"""Simplified synergy panel widgets for card synergy discovery.

This package provides the simplified synergy panel components:
- EnhancedSynergyPanel: Main container with search, filtering, and type index
- SynergyCardItem: Individual synergy result display
- TypeIndex: Sidebar for filtering by synergy type

Synergy Types:
- All: View all synergies
- Combo: Infinite and win combos
- Tribal: Creature type synergies
- Keyword: Keyword ability synergies
- Ability: Triggered/activated ability synergies
- Theme: Theme and archetype synergies
"""

from __future__ import annotations

from .card_item import SynergyCardItem, SynergyListHeader
from .messages import SynergyPanelClosed, SynergySelected
from .panel import EnhancedSynergyPanel, SortOrder, TypeIndex

__all__ = [
    "EnhancedSynergyPanel",
    "SortOrder",
    "SynergyCardItem",
    "SynergyListHeader",
    "SynergyPanelClosed",
    "SynergySelected",
    "TypeIndex",
]
