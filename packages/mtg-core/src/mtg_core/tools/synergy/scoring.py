"""Synergy scoring and helper functions."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ...data.models.responses import SynergyResult, SynergyType
from .constants import SYNERGY_BASE_SCORES

if TYPE_CHECKING:
    from ...data.models.card import Card


def normalize_card_name(name: str) -> str:
    """Normalize card name for comparison."""
    return name.lower().strip()


def card_has_pattern(card: Card, pattern: str) -> bool:
    """Check if card text matches a pattern (case-insensitive)."""
    if not card.text:
        return False
    try:
        return bool(re.search(pattern, card.text, re.IGNORECASE))
    except re.error:
        return pattern.lower() in card.text.lower()


def calculate_synergy_score(
    card: Card,
    source_card: Card,
    synergy_type: SynergyType,
) -> float:
    """Calculate synergy score with bonuses for color match."""
    base = SYNERGY_BASE_SCORES.get(synergy_type, 0.5)

    if card.color_identity and source_card.color_identity:
        overlap = set(card.color_identity) & set(source_card.color_identity)
        if overlap:
            base += 0.1 * len(overlap) / max(len(source_card.color_identity), 1)

    return min(base, 1.0)


def create_synergy_result(
    card: Card,
    source_card: Card,
    synergy_type: SynergyType,
    reason: str,
    score_modifier: float = 1.0,
) -> SynergyResult:
    """Create a SynergyResult from card data."""
    score = calculate_synergy_score(card, source_card, synergy_type)
    return SynergyResult(
        name=card.name,
        synergy_type=synergy_type,
        reason=reason,
        score=score * score_modifier,
        mana_cost=card.mana_cost,
        type_line=card.type,
    )
