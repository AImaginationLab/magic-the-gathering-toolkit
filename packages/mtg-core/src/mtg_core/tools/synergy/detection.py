"""Theme and combo detection logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...data.database.combos import ComboCardRow, ComboDatabase, ComboRow
from ...data.models.responses import Combo, ComboCard
from ...tools.recommendations.constants import THEME_KEYWORDS
from .constants import KNOWN_COMBOS
from .scoring import normalize_card_name

if TYPE_CHECKING:
    from ...data.models.card import Card


def detect_themes(cards: list[Card]) -> list[str]:
    """Detect deck themes from card texts and keywords.

    Uses THEME_KEYWORDS from recommendations/constants.py which provides
    a comprehensive mapping of theme names to detection patterns.

    Detection sources:
    - Card oracle text (pattern matching)
    - Card keywords (exact match)
    - Card subtypes (for tribal detection)
    """
    theme_scores: dict[str, int] = dict.fromkeys(THEME_KEYWORDS, 0)

    for card in cards:
        card_text_lower = (card.text or "").lower()
        card_keywords_lower = {k.lower() for k in (card.keywords or [])}

        for theme, patterns in THEME_KEYWORDS.items():
            for pattern in patterns:
                pattern_lower = pattern.lower()

                # Check keywords first (exact match is faster)
                if pattern_lower in card_keywords_lower:
                    theme_scores[theme] += 1
                    break

                # Then check oracle text
                if pattern_lower in card_text_lower:
                    theme_scores[theme] += 1
                    break

    # Detect tribal themes from subtypes
    subtype_counts: dict[str, int] = {}
    for card in cards:
        if card.subtypes:
            for subtype in card.subtypes:
                subtype_counts[subtype] = subtype_counts.get(subtype, 0) + 1

    # Add tribal as a theme if any subtype has 5+ cards
    for _subtype, count in subtype_counts.items():
        if count >= 5:
            if "Tribal" not in theme_scores:
                theme_scores["Tribal"] = 0
            theme_scores["Tribal"] += count

    # Return themes with score >= 3, sorted by score descending
    detected = [(theme, score) for theme, score in theme_scores.items() if score >= 3]
    detected.sort(key=lambda x: -x[1])
    return [theme for theme, _ in detected]


def detect_deck_colors(cards: list[Card]) -> list[str]:
    """Detect deck colors from card color identities.

    Excludes basic and dual lands from color detection since lands can have
    color identities that don't represent the deck's actual spell colors.
    For example, a Jeskai deck might have Temple Garden for mana fixing
    but doesn't actually play green spells.
    """
    colors: set[str] = set()

    for card in cards:
        if not card.color_identity:
            continue

        # Skip lands - they shouldn't determine deck colors
        # A deck with Temple Garden isn't necessarily a green deck
        if card.types and "Land" in card.types:
            continue

        colors.update(card.color_identity)

    color_order = ["W", "U", "B", "R", "G"]
    return [c for c in color_order if c in colors]


def combo_to_model(combo_data: dict[str, Any]) -> Combo:
    """Convert combo dict to Combo model."""
    cards = []
    for card_info in combo_data["cards"]:
        if isinstance(card_info, tuple):
            name, role = card_info
        else:
            name, role = card_info, "Combo piece"
        cards.append(ComboCard(name=name, role=role))

    return Combo(
        id=combo_data["id"],
        cards=cards,
        description=combo_data["desc"],
        combo_type=combo_data["type"],
        colors=combo_data.get("colors", []),
    )


def find_combos_for_card(card_name: str) -> list[Combo]:
    """Find all combos involving a specific card."""
    card_name_lower = normalize_card_name(card_name)
    found_combos: list[Combo] = []

    for combo_data in KNOWN_COMBOS:
        combo_card_names = [
            normalize_card_name(c[0] if isinstance(c, tuple) else c) for c in combo_data["cards"]
        ]
        if card_name_lower in combo_card_names:
            found_combos.append(combo_to_model(combo_data))

    return found_combos


def find_combos_in_deck(
    deck_cards: list[str],
) -> tuple[list[Combo], list[Combo], dict[str, list[str]]]:
    """Find complete and potential combos in a deck.

    Returns:
        Tuple of (complete_combos, potential_combos, missing_cards_by_combo_id)
    """
    deck_card_names = {normalize_card_name(c) for c in deck_cards}
    found_combos: list[Combo] = []
    potential_combos: list[Combo] = []
    missing_cards: dict[str, list[str]] = {}

    for combo_data in KNOWN_COMBOS:
        combo_card_names = [
            normalize_card_name(c[0] if isinstance(c, tuple) else c) for c in combo_data["cards"]
        ]
        combo_card_originals = [c[0] if isinstance(c, tuple) else c for c in combo_data["cards"]]

        present = set(combo_card_names) & deck_card_names
        missing = set(combo_card_names) - deck_card_names

        if not missing:
            found_combos.append(combo_to_model(combo_data))
        elif len(missing) <= 2 and len(present) >= 1:
            combo = combo_to_model(combo_data)
            potential_combos.append(combo)
            missing_originals = [
                orig
                for orig, norm in zip(combo_card_originals, combo_card_names, strict=True)
                if norm in missing
            ]
            missing_cards[combo_data["id"]] = missing_originals

    return found_combos, potential_combos, missing_cards


def _combo_row_to_model(combo: ComboRow, cards: list[ComboCardRow]) -> Combo:
    """Convert database combo row to Combo model."""
    return Combo(
        id=combo.id,
        cards=[ComboCard(name=c.card_name, role=c.role) for c in cards],
        description=combo.description,
        combo_type=combo.combo_type,  # type: ignore[arg-type]
        colors=combo.colors,
    )


async def find_combos_for_card_db(combo_db: ComboDatabase, card_name: str) -> list[Combo]:
    """Find all combos involving a specific card using the database."""
    results = await combo_db.find_combos_by_card(card_name)
    return [_combo_row_to_model(combo, cards) for combo, cards in results]


async def find_combos_in_deck_db(
    combo_db: ComboDatabase, deck_cards: list[str]
) -> tuple[list[Combo], list[Combo], dict[str, list[str]]]:
    """Find complete and potential combos in a deck using the database.

    Returns:
        Tuple of (complete_combos, potential_combos, missing_cards_by_combo_id)
    """
    complete, potential = await combo_db.find_combos_in_deck(deck_cards)

    complete_combos = [_combo_row_to_model(combo, cards) for combo, cards in complete]
    potential_combos = []
    missing_cards: dict[str, list[str]] = {}

    for combo, cards, missing in potential:
        potential_combos.append(_combo_row_to_model(combo, cards))
        missing_cards[combo.id] = missing

    return complete_combos, potential_combos, missing_cards
