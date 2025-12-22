"""Main synergy tool implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...cache import get_cached, set_cached
from ...data.models.inputs import SearchCardsInput
from ...data.models.responses import (
    DetectCombosResult,
    FindSynergiesResult,
    SuggestCardsResult,
    SuggestedCard,
    SynergyResult,
)
from ...exceptions import CardNotFoundError
from .constants import (
    ABILITY_SYNERGIES,
    KEYWORD_SYNERGIES,
    THEME_INDICATORS,
    TYPE_SYNERGIES,
)
from .detection import (
    detect_deck_colors,
    detect_themes,
    find_combos_for_card,
    find_combos_for_card_db,
    find_combos_in_deck,
    find_combos_in_deck_db,
)
from .scoring import (
    calculate_synergy_score,
    card_has_pattern,
    normalize_card_name,
)
from .search import search_synergies

if TYPE_CHECKING:
    from ...data.database import ComboDatabase, UnifiedDatabase
    from ...data.models.card import Card

# Cache namespace and TTL for synergies
_SYNERGIES_CACHE_NS = "synergies"
_SYNERGIES_TTL_DAYS = 14


def _synergy_cache_key(card_name: str, max_results: int, format_legal: str | None) -> str:
    """Generate cache key for synergy results."""
    return f"{card_name.lower()}|{max_results}|{format_legal or 'any'}"


async def find_synergies(
    db: UnifiedDatabase,
    card_name: str,
    max_results: int = 20,
    format_legal: str | None = None,
    *,
    use_cache: bool = True,
) -> FindSynergiesResult:
    """Find cards that synergize with a given card."""
    # Check cache first
    cache_key = _synergy_cache_key(card_name, max_results, format_legal)
    if use_cache:
        cached = get_cached(
            _SYNERGIES_CACHE_NS, cache_key, FindSynergiesResult, _SYNERGIES_TTL_DAYS
        )
        if cached is not None:
            return cached

    source_card = await db.get_card_by_name(card_name)
    if not source_card:
        raise CardNotFoundError(f"Card not found: {card_name}")

    synergies: list[SynergyResult] = []
    seen_names: set[str] = {normalize_card_name(source_card.name)}
    color_identity = source_card.color_identity or None

    # Pass 1: Keyword synergies
    if source_card.keywords:
        for keyword in source_card.keywords:
            if keyword in KEYWORD_SYNERGIES:
                terms = [(t, f"{keyword}: {r}") for t, r in KEYWORD_SYNERGIES[keyword]]
                synergies.extend(
                    await search_synergies(
                        db,
                        source_card,
                        terms,
                        "keyword",
                        seen_names,
                        color_identity,
                        format_legal,
                    )
                )

    # Pass 2: Tribal synergies
    skip_subtypes = {"human", "warrior", "wizard", "soldier", "cleric"}
    if source_card.subtypes:
        for subtype in source_card.subtypes:
            if subtype.lower() in skip_subtypes:
                continue
            synergies.extend(
                await search_synergies(
                    db,
                    source_card,
                    [(subtype, f"Synergizes with {subtype}s")],
                    "tribal",
                    seen_names,
                    color_identity,
                    format_legal,
                    page_size=15,
                )
            )
            # Cards of same subtype
            await _add_tribal_matches(
                db, source_card, subtype, synergies, seen_names, color_identity, format_legal
            )

    # Pass 3: Ability text synergies
    if source_card.text:
        for pattern, search_terms in ABILITY_SYNERGIES.items():
            if card_has_pattern(source_card, pattern):
                synergies.extend(
                    await search_synergies(
                        db,
                        source_card,
                        search_terms,
                        "ability",
                        seen_names,
                        color_identity,
                        format_legal,
                        page_size=8,
                    )
                )

    # Pass 4: Type synergies
    if source_card.types:
        for card_type in source_card.types:
            if card_type in TYPE_SYNERGIES:
                terms = [(t, f"{card_type}: {r}") for t, r in TYPE_SYNERGIES[card_type]]
                synergies.extend(
                    await search_synergies(
                        db,
                        source_card,
                        terms,
                        "theme",
                        seen_names,
                        color_identity,
                        format_legal,
                        page_size=8,
                    )
                )

    synergies.sort(key=lambda s: s.score, reverse=True)
    synergies = synergies[:max_results]

    result = FindSynergiesResult(
        card_name=source_card.name,
        synergies=synergies,
    )

    # Cache result for future use
    if use_cache:
        set_cached(_SYNERGIES_CACHE_NS, cache_key, result)

    return result


async def _add_tribal_matches(
    db: UnifiedDatabase,
    source_card: Card,
    subtype: str,
    synergies: list[SynergyResult],
    seen_names: set[str],
    color_identity: list[str] | None,
    format_legal: str | None,
) -> None:
    """Add cards of the same subtype as tribal synergies."""
    cards, _ = await db.search_cards(
        SearchCardsInput(
            subtype=subtype,
            color_identity=color_identity,  # type: ignore[arg-type]
            format_legal=format_legal,  # type: ignore[arg-type]
            page_size=10,
        )
    )
    for card in cards:
        normalized = normalize_card_name(card.name)
        if normalized not in seen_names:
            seen_names.add(normalized)
            synergies.append(
                SynergyResult(
                    name=card.name,
                    synergy_type="tribal",
                    reason=f"Fellow {subtype}",
                    score=calculate_synergy_score(card, source_card, "tribal") * 0.9,
                    mana_cost=card.mana_cost,
                    type_line=card.type,
                )
            )


async def detect_combos(
    db: UnifiedDatabase,  # noqa: ARG001
    card_name: str | None = None,
    deck_cards: list[str] | None = None,
    combo_db: ComboDatabase | None = None,
) -> DetectCombosResult:
    """Detect known combos in a deck or for a specific card.

    If combo_db is provided, uses the database for combo detection.
    Otherwise falls back to the hardcoded KNOWN_COMBOS list.
    """
    if card_name:
        if combo_db:
            found_combos = await find_combos_for_card_db(combo_db, card_name)
        else:
            found_combos = find_combos_for_card(card_name)
        return DetectCombosResult(
            combos=found_combos,
            potential_combos=[],
            missing_cards={},
        )

    if deck_cards:
        if combo_db:
            found, potential, missing = await find_combos_in_deck_db(combo_db, deck_cards)
        else:
            found, potential, missing = find_combos_in_deck(deck_cards)
        return DetectCombosResult(
            combos=found,
            potential_combos=potential,
            missing_cards=missing,
        )

    return DetectCombosResult(
        combos=[],
        potential_combos=[],
        missing_cards={},
    )


async def suggest_cards(
    db: UnifiedDatabase,
    deck_cards: list[str],
    format_legal: str | None = None,
    budget_max: float | None = None,
    max_results: int = 10,
) -> SuggestCardsResult:
    """Suggest cards to add to a deck based on themes and synergies."""
    resolved_cards: list[Card] = []
    deck_card_names_lower: set[str] = set()

    for card_name in deck_cards:
        try:
            card = await db.get_card_by_name(card_name)
            if card:
                resolved_cards.append(card)
                deck_card_names_lower.add(normalize_card_name(card.name))
        except CardNotFoundError:
            continue

    if not resolved_cards:
        return SuggestCardsResult(
            suggestions=[],
            detected_themes=[],
            deck_colors=[],
        )

    detected_themes = detect_themes(resolved_cards)
    deck_colors = detect_deck_colors(resolved_cards)

    suggestions: list[SuggestedCard] = []
    seen_names: set[str] = deck_card_names_lower.copy()

    # Search for cards matching detected themes
    for theme in detected_themes[:3]:
        if theme not in THEME_INDICATORS or not THEME_INDICATORS[theme]:
            continue

        search_term = THEME_INDICATORS[theme][0]
        suggestions.extend(
            await _search_theme_suggestions(
                db,
                search_term,
                theme,
                deck_colors,
                format_legal,
                budget_max,
                seen_names,
                max_results - len(suggestions),
            )
        )
        if len(suggestions) >= max_results:
            break

    # Add staples if we don't have enough suggestions
    if len(suggestions) < max_results and deck_colors:
        suggestions.extend(
            await _search_staple_suggestions(
                db,
                deck_colors,
                format_legal,
                budget_max,
                seen_names,
                max_results - len(suggestions),
            )
        )

    return SuggestCardsResult(
        suggestions=suggestions[:max_results],
        detected_themes=detected_themes,
        deck_colors=deck_colors,
    )


async def _search_theme_suggestions(
    db: UnifiedDatabase,
    search_term: str,
    theme: str,
    deck_colors: list[str],
    format_legal: str | None,
    budget_max: float | None,
    seen_names: set[str],
    limit: int,
) -> list[SuggestedCard]:
    """Search for cards matching a theme."""
    suggestions: list[SuggestedCard] = []

    results, _ = await db.search_cards(
        SearchCardsInput(
            text=search_term,
            color_identity=deck_colors if deck_colors else None,  # type: ignore[arg-type]
            format_legal=format_legal,  # type: ignore[arg-type]
            page_size=20,
        )
    )

    for card in results:
        if normalize_card_name(card.name) in seen_names:
            continue
        seen_names.add(normalize_card_name(card.name))

        price_usd = await _get_card_price(db, card.name)

        if budget_max is not None and price_usd is not None and price_usd > budget_max:
            continue

        suggestions.append(
            SuggestedCard(
                name=card.name,
                reason=f"Fits {theme} theme",
                category="synergy",
                mana_cost=card.mana_cost,
                type_line=card.type,
                price_usd=price_usd,
            )
        )

        if len(suggestions) >= limit:
            break

    return suggestions


async def _search_staple_suggestions(
    db: UnifiedDatabase,
    deck_colors: list[str],
    format_legal: str | None,
    budget_max: float | None,
    seen_names: set[str],
    limit: int,
) -> list[SuggestedCard]:
    """Search for staple cards in deck colors."""
    suggestions: list[SuggestedCard] = []
    staple_searches = [
        ("draw.*card", "Card advantage staple"),
        ("destroy.*target", "Removal staple"),
        ("add.*mana", "Ramp staple"),
    ]

    for search_term, reason in staple_searches:
        if len(suggestions) >= limit:
            break

        results, _ = await db.search_cards(
            SearchCardsInput(
                text=search_term,
                color_identity=deck_colors,  # type: ignore[arg-type]
                format_legal=format_legal,  # type: ignore[arg-type]
                page_size=10,
            )
        )

        for card in results:
            if normalize_card_name(card.name) in seen_names:
                continue
            seen_names.add(normalize_card_name(card.name))

            price_usd = await _get_card_price(db, card.name)

            if budget_max is not None and price_usd is not None and price_usd > budget_max:
                continue

            suggestions.append(
                SuggestedCard(
                    name=card.name,
                    reason=reason,
                    category="staple",
                    mana_cost=card.mana_cost,
                    type_line=card.type,
                    price_usd=price_usd,
                )
            )

            if len(suggestions) >= limit:
                break

    return suggestions


async def _get_card_price(db: UnifiedDatabase, card_name: str) -> float | None:
    """Get card price from unified database."""
    try:
        card = await db.get_card_by_name(card_name, include_extras=False)
        return card.get_price_usd()
    except (OSError, CardNotFoundError):
        pass
    return None
