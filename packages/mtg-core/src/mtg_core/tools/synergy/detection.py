"""Theme and combo detection logic."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from ...data.models.responses import Combo, ComboCard
from .constants import KNOWN_COMBOS, THEME_INDICATORS
from .scoring import normalize_card_name

if TYPE_CHECKING:
    from ...data.models.card import Card


def detect_themes(cards: list[Card]) -> list[str]:
    """Detect deck themes from card texts."""
    theme_scores: dict[str, int] = dict.fromkeys(THEME_INDICATORS, 0)

    for card in cards:
        if not card.text:
            continue

        card_text_lower = card.text.lower()
        for theme, patterns in THEME_INDICATORS.items():
            for pattern in patterns:
                try:
                    if re.search(pattern, card_text_lower, re.IGNORECASE):
                        theme_scores[theme] += 1
                        break
                except re.error:
                    if pattern.lower() in card_text_lower:
                        theme_scores[theme] += 1
                        break

    subtype_counts: dict[str, int] = {}
    for card in cards:
        if card.subtypes:
            for subtype in card.subtypes:
                subtype_counts[subtype] = subtype_counts.get(subtype, 0) + 1

    for _subtype, count in subtype_counts.items():
        if count >= 5:
            theme_scores["tribal"] += count

    return [theme for theme, score in theme_scores.items() if score >= 3]


def detect_deck_colors(cards: list[Card]) -> list[str]:
    """Detect deck colors from card color identities."""
    colors: set[str] = set()
    for card in cards:
        if card.color_identity:
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
            normalize_card_name(c[0] if isinstance(c, tuple) else c)
            for c in combo_data["cards"]
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
            normalize_card_name(c[0] if isinstance(c, tuple) else c)
            for c in combo_data["cards"]
        ]
        combo_card_originals = [
            c[0] if isinstance(c, tuple) else c for c in combo_data["cards"]
        ]

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
