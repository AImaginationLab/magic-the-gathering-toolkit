"""Messages for synergy panel components."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.message import Message

if TYPE_CHECKING:
    from mtg_core.data.models.responses import SynergyResult


class SynergySelected(Message):
    """Posted when a synergy card is selected for viewing."""

    def __init__(self, synergy: SynergyResult) -> None:
        super().__init__()
        self.synergy = synergy


class SynergyCompareAdd(Message):
    """Posted when a synergy is added to comparison queue."""

    def __init__(self, synergy: SynergyResult) -> None:
        super().__init__()
        self.synergy = synergy


class SynergyCompareRemove(Message):
    """Posted when a synergy is removed from comparison queue."""

    def __init__(self, synergy: SynergyResult) -> None:
        super().__init__()
        self.synergy = synergy


class SynergyCompareView(Message):
    """Posted to open the comparison view."""

    pass


class SynergyCompareClear(Message):
    """Posted to clear the comparison queue."""

    pass


class SynergyDetailExpand(Message):
    """Posted when synergy detail is expanded."""

    def __init__(self, synergy: SynergyResult) -> None:
        super().__init__()
        self.synergy = synergy


class SynergyDetailCollapse(Message):
    """Posted when synergy detail is collapsed."""

    pass


class SynergyPanelClosed(Message):
    """Posted when the synergy panel is closed."""

    pass


class CategoryChanged(Message):
    """Posted when the active category tab changes."""

    def __init__(self, category: str) -> None:
        super().__init__()
        self.category = category


class FilterApplied(Message):
    """Posted when filters are applied."""

    def __init__(
        self,
        sort_by: str | None = None,
        card_type: str | None = None,
        min_cmc: int | None = None,
        max_cmc: int | None = None,
        color: str | None = None,
    ) -> None:
        super().__init__()
        self.sort_by = sort_by
        self.card_type = card_type
        self.min_cmc = min_cmc
        self.max_cmc = max_cmc
        self.color = color


class FilterCleared(Message):
    """Posted when filters are cleared."""

    pass


class FavoriteSynergy(Message):
    """Posted when a synergy is favorited."""

    def __init__(self, synergy: SynergyResult) -> None:
        super().__init__()
        self.synergy = synergy


class UnfavoriteSynergy(Message):
    """Posted when a synergy is unfavorited."""

    def __init__(self, synergy: SynergyResult) -> None:
        super().__init__()
        self.synergy = synergy
