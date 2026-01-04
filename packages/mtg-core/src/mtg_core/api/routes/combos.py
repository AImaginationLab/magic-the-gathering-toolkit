"""Combo API routes.

Uses SpellbookComboDetector which queries the combos.sqlite database
containing 73K+ combos from Commander Spellbook.
"""

from __future__ import annotations

from fastapi import APIRouter

from mtg_core.data.models import DetectCombosResult
from mtg_core.data.models.responses import Combo, ComboCard
from mtg_core.tools.recommendations.spellbook_combos import (
    SpellbookCombo,
    SpellbookComboMatch,
    get_spellbook_detector,
)

from ..models.requests import CombosForCardRequest, DetectCombosRequest

router = APIRouter()


def _spellbook_combo_to_model(combo: SpellbookCombo) -> Combo:
    """Convert SpellbookCombo to API Combo model."""
    return Combo(
        id=combo.id,
        cards=[ComboCard(name=name, role="Combo piece") for name in combo.card_names],
        description=combo.description,
        combo_type="infinite" if "infinite" in combo.description.lower() else "value",
        colors=list(combo.identity) if combo.identity else [],
    )


def _match_to_combo(match: SpellbookComboMatch) -> Combo:
    """Convert SpellbookComboMatch to API Combo model."""
    return _spellbook_combo_to_model(match.combo)


@router.post("/detect", response_model=DetectCombosResult)
async def detect_deck_combos(
    body: DetectCombosRequest,
) -> DetectCombosResult:
    """Detect known combos in a list of cards."""
    detector = await get_spellbook_detector()

    # Find complete combos (max_missing=0) and potential combos (max_missing=2)
    complete_matches = await detector.find_combos(body.card_names, max_missing=0, limit=50)
    potential_matches, _ = await detector.find_missing_pieces(
        body.card_names, max_missing=2, min_present=2
    )

    # Filter out complete combos from potential
    complete_ids = {m.combo.id for m in complete_matches}
    potential_matches = [m for m in potential_matches if m.combo.id not in complete_ids]

    # Build missing cards dict
    missing_cards: dict[str, list[str]] = {}
    for match in potential_matches[:30]:
        if match.missing_cards:
            missing_cards[match.combo.id] = match.missing_cards

    return DetectCombosResult(
        combos=[_match_to_combo(m) for m in complete_matches],
        potential_combos=[_match_to_combo(m) for m in potential_matches[:30]],
        missing_cards=missing_cards,
    )


@router.post("/for-card", response_model=DetectCombosResult)
async def find_combos_for_card(
    body: CombosForCardRequest,
) -> DetectCombosResult:
    """Find all combos involving a specific card."""
    detector = await get_spellbook_detector()
    combos = await detector.find_combos_for_card(body.card_name, limit=50)

    return DetectCombosResult(
        combos=[_spellbook_combo_to_model(c) for c in combos],
        potential_combos=[],
        missing_cards={},
    )
