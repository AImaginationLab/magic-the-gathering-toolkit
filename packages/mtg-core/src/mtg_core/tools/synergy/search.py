"""Synergy search functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...data.models.inputs import SearchCardsInput
from ...data.models.responses import SynergyResult, SynergyType
from .scoring import create_synergy_result, normalize_card_name

if TYPE_CHECKING:
    from ...data.database import UnifiedDatabase
    from ...data.models.card import Card


async def search_synergies(
    db: UnifiedDatabase,
    source_card: Card,
    search_terms: list[tuple[str, str]],
    synergy_type: SynergyType,
    seen_names: set[str],
    color_identity: list[str] | None,
    format_legal: str | None,
    page_size: int = 10,
    score_modifier: float = 1.0,
) -> list[SynergyResult]:
    """Search for synergistic cards given search terms.

    Args:
        db: Database connection
        source_card: Card to find synergies for
        search_terms: List of (search_text, reason) tuples
        synergy_type: Type of synergy for scoring
        seen_names: Set of already-seen card names (will be modified)
        color_identity: Color identity filter
        format_legal: Format legality filter
        page_size: Max results per search term
        score_modifier: Multiply score by this value
    """
    results: list[SynergyResult] = []

    for search_term, reason in search_terms:
        cards, _ = await db.search_cards(
            SearchCardsInput(
                text=search_term,
                color_identity=color_identity,  # type: ignore[arg-type]
                format_legal=format_legal,  # type: ignore[arg-type]
                page_size=page_size,
            )
        )
        for card in cards:
            normalized = normalize_card_name(card.name)
            if normalized not in seen_names:
                seen_names.add(normalized)
                results.append(
                    create_synergy_result(card, source_card, synergy_type, reason, score_modifier)
                )

    return results
