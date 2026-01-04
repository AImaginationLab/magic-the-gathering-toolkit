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

    # Pass 1: Keyword synergies - find cards that "care about" each keyword
    if source_card.keywords:
        for keyword in source_card.keywords:
            # Dynamic DB lookup: find cards that reference this keyword in their text
            caring_cards = await db.find_cards_that_care_about(
                keyword,
                color_identity=color_identity,
                format_legal=format_legal,
                limit=10,
            )
            for card in caring_cards:
                normalized = normalize_card_name(card.name)
                if normalized not in seen_names:
                    seen_names.add(normalized)
                    price_usd = card.price_usd / 100.0 if card.price_usd else None
                    synergies.append(
                        SynergyResult(
                            name=card.name,
                            synergy_type="keyword",
                            reason=f"Synergizes with {keyword}",
                            score=calculate_synergy_score(card, source_card, "keyword"),
                            mana_cost=card.mana_cost,
                            type_line=card.type,
                            image_small=card.image_small,
                            rarity=card.rarity,
                            keywords=card.keywords or [],
                            price_usd=price_usd,
                            edhrec_rank=card.edhrec_rank,
                        )
                    )

            # Also check hardcoded synergies for specific keyword interactions
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

    # Pass 5: Combo synergies - find cards that combo with source card
    synergies = await _add_combo_synergies(
        db, source_card, synergies, seen_names, color_identity, format_legal
    )

    synergies.sort(key=lambda s: s.score, reverse=True)
    synergies = synergies[:max_results]

    # Enrich with 17Lands gameplay data if available
    synergies = await _enrich_with_gameplay_data(source_card.name, source_card.set_code, synergies)

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
            price_usd = card.price_usd / 100.0 if card.price_usd else None
            synergies.append(
                SynergyResult(
                    name=card.name,
                    synergy_type="tribal",
                    reason=f"Fellow {subtype}",
                    score=calculate_synergy_score(card, source_card, "tribal") * 0.9,
                    mana_cost=card.mana_cost,
                    type_line=card.type,
                    image_small=card.image_small,
                    rarity=card.rarity,
                    keywords=card.keywords or [],
                    price_usd=price_usd,
                    edhrec_rank=card.edhrec_rank,
                )
            )


async def _add_combo_synergies(
    db: UnifiedDatabase,
    source_card: Card,
    synergies: list[SynergyResult],
    seen_names: set[str],
    color_identity: list[str] | None,
    format_legal: str | None,  # noqa: ARG001
) -> list[SynergyResult]:
    """Add combo partners as synergy results.

    Looks up combos containing the source card and adds other combo pieces
    as synergy results with type "combo".
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        from ...tools.recommendations.spellbook_combos import get_spellbook_detector

        spellbook = await get_spellbook_detector()
        if not spellbook.is_available:
            logger.debug("Spellbook not available for combo synergies")
            return synergies
    except Exception as e:
        logger.warning("Failed to initialize spellbook for combo synergies: %s", e)
        return synergies

    try:
        # Find combos containing the source card
        combos = await spellbook.find_combos_for_card(source_card.name, limit=30)
        if not combos:
            return synergies

        # Track combo partners and their best combo descriptions
        partner_combos: dict[str, tuple[str, int]] = {}  # card_name -> (description, popularity)

        for combo in combos:
            for card_name in combo.card_names:
                normalized = card_name.lower()
                # Skip source card
                if normalized == source_card.name.lower():
                    continue
                # Track best combo for this partner (highest popularity)
                if (
                    normalized not in partner_combos
                    or combo.popularity > partner_combos[normalized][1]
                ):
                    # Build a reason from the combo's produces
                    if combo.produces:
                        reason = ", ".join(combo.produces[:2])
                    else:
                        reason = (
                            combo.description[:60] + "..."
                            if len(combo.description) > 60
                            else combo.description
                        )
                    partner_combos[normalized] = (reason, combo.popularity)

        # Look up card details and add as synergy results
        added_count = 0
        for card_name_lower, (reason, popularity) in partner_combos.items():
            # Skip if already in synergies
            if card_name_lower in seen_names:
                continue

            # Try to get card details from database
            try:
                card = await db.get_card_by_name(card_name_lower)
                if not card:
                    continue

                # Check color identity filter
                if (
                    color_identity
                    and card.color_identity
                    and not all(c in color_identity for c in card.color_identity)
                ):
                    continue

                seen_names.add(card_name_lower)
                price_usd = card.price_usd / 100.0 if card.price_usd else None

                # Score based on popularity (normalized to 0-1)
                score = min(1.0, popularity / 1000.0) * 0.9 + 0.1

                synergies.append(
                    SynergyResult(
                        name=card.name,
                        synergy_type="combo",
                        reason=f"Combo: {reason}",
                        score=score,
                        mana_cost=card.mana_cost,
                        type_line=card.type,
                        image_small=card.image_small,
                        rarity=card.rarity,
                        keywords=card.keywords or [],
                        price_usd=price_usd,
                        edhrec_rank=card.edhrec_rank,
                    )
                )
                added_count += 1
            except Exception:
                # Skip cards we can't look up
                continue

        logger.debug("Added %d combo synergies for %s", added_count, source_card.name)
        return synergies
    except Exception as e:
        logger.warning("Error finding combo synergies: %s", e)
        return synergies


async def _enrich_with_gameplay_data(
    source_card_name: str,
    source_set_code: str | None,
    synergies: list[SynergyResult],
) -> list[SynergyResult]:
    """Enrich synergy results with 17Lands gameplay data and combo info.

    Adds synergy_lift, win_rate_together, sample_size, tier, gih_wr, iwd, oh_wr,
    best_archetypes, is_bomb, is_synergy_dependent, combo_count, and combo_preview
    when data is available.
    """
    try:
        from ...tools.recommendations.gameplay import GameplayDB
    except ImportError:
        return synergies

    gameplay_db = GameplayDB()
    if not gameplay_db.is_available:
        return synergies

    # Get spellbook combo detector (uses existing combos.sqlite)
    spellbook = None
    try:
        from ...tools.recommendations.spellbook_combos import get_spellbook_detector

        spellbook = await get_spellbook_detector()
        if not spellbook.is_available:
            spellbook = None
    except (ImportError, Exception):
        pass

    try:
        gameplay_db.connect()

        # Get synergy pairs for source card
        synergy_pairs = gameplay_db.get_synergy_pairs(
            source_card_name,
            set_code=source_set_code,
            min_games=30,  # Lower threshold for more data
            min_lift=-1.0,  # Include negative lift too
        )

        # Build lookup map: card_b name -> synergy pair data
        pair_map = {p.card_b.lower(): p for p in synergy_pairs}

        # Enrich each synergy result
        enriched = []
        for syn in synergies:
            updates: dict[str, object] = {}

            # Check for synergy pair data
            pair = pair_map.get(syn.name.lower())
            if pair:
                updates["synergy_lift"] = pair.synergy_lift
                updates["win_rate_together"] = pair.win_rate_together
                updates["sample_size"] = pair.co_occurrence_count

            # Get individual card stats (without set filter - get any available data)
            card_stats = gameplay_db.get_card_stats(syn.name)
            if card_stats:
                updates["tier"] = card_stats.tier
                updates["gih_wr"] = card_stats.gih_wr
                updates["iwd"] = card_stats.iwd
                updates["oh_wr"] = card_stats.oh_wr

            # Check bomb / synergy-dependent status (without set filter)
            is_bomb = gameplay_db.is_bomb(syn.name)
            is_synergy_dep = gameplay_db.is_synergy_dependent(syn.name)
            if is_bomb:
                updates["is_bomb"] = True
            if is_synergy_dep:
                updates["is_synergy_dependent"] = True

            # Get best archetypes for this card (without set filter)
            best_archetypes = _get_best_archetypes(gameplay_db, syn.name, None)
            if best_archetypes:
                updates["best_archetypes"] = best_archetypes

            # Get combo info if available
            if spellbook:
                combo_count, combo_preview = await _get_combo_info(spellbook, syn.name)
                if combo_count > 0:
                    updates["combo_count"] = combo_count
                    updates["combo_preview"] = combo_preview

            if updates:
                syn = syn.model_copy(update=updates)

            enriched.append(syn)

        return enriched
    except Exception:
        # Silently fail - gameplay data is optional
        return synergies
    finally:
        gameplay_db.close()


def _get_best_archetypes(
    gameplay_db: object, card_name: str, set_code: str | None, limit: int = 3
) -> list[str]:
    """Get the top performing archetypes for a card.

    Returns up to `limit` color pairs where this card performs above average.
    """
    from ...tools.recommendations.gameplay import GameplayDB

    if not isinstance(gameplay_db, GameplayDB):
        return []

    # Color pairs in standard order
    all_archetypes = ["WU", "UB", "BR", "RG", "GW", "WB", "UR", "BG", "RW", "GU"]
    arch_scores: list[tuple[str, float]] = []

    for arch in all_archetypes:
        cards = gameplay_db.get_archetype_cards(arch, set_code, min_games=30, limit=100)
        for card in cards:
            if card.card_name.lower() == card_name.lower() and card.gih_wr is not None:
                # Only include if above average (56%)
                if card.gih_wr > 0.56:
                    arch_scores.append((arch, card.gih_wr))
                break

    # Sort by performance and return top archetypes
    arch_scores.sort(key=lambda x: x[1], reverse=True)
    return [arch for arch, _ in arch_scores[:limit]]


async def _get_combo_info(spellbook: object, card_name: str) -> tuple[int, str | None]:
    """Get combo count and preview for a card.

    Returns (combo_count, first_combo_description).
    """
    from ...tools.recommendations.spellbook_combos import SpellbookComboDetector

    if not isinstance(spellbook, SpellbookComboDetector):
        return 0, None

    try:
        combos = await spellbook.find_combos_for_card(card_name, limit=50)
        if not combos:
            return 0, None

        count = len(combos)
        # Get first combo description (truncate if long)
        preview = combos[0].description if combos else None
        if preview and len(preview) > 200:
            preview = preview[:197] + "..."

        return count, preview
    except Exception:
        return 0, None


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
    """Suggest cards to add to a deck based on themes, synergies, and data.

    Enhanced algorithm using multiple data sources:
    - 17Lands: Card tier ratings (S/A/B/C/D/F) and synergy pairs
    - Commander Spellbook: Combo detection (73K+ combos)
    - EDHREC: Popularity ranking for staple filtering
    - Theme detection: Pattern matching on card text
    """
    from ..recommendations.gameplay import get_gameplay_db
    from ..recommendations.spellbook_combos import get_spellbook_detector

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

    # Initialize data sources
    gameplay_db = get_gameplay_db()
    combo_detector = await get_spellbook_detector()

    # Collect candidate cards from multiple sources
    candidates: dict[str, _SuggestionCandidate] = {}
    seen_names: set[str] = deck_card_names_lower.copy()

    # Source 1: Theme-based suggestions
    for theme in detected_themes[:3]:
        if theme not in THEME_INDICATORS or not THEME_INDICATORS[theme]:
            continue
        search_term = THEME_INDICATORS[theme][0]
        await _add_theme_candidates(
            db, candidates, search_term, theme, deck_colors, format_legal, budget_max, seen_names
        )

    # Source 2: Keyword/ability synergy suggestions (reuse find_synergies logic)
    await _add_synergy_candidates_from_deck(
        db, candidates, resolved_cards, deck_colors, format_legal, budget_max, seen_names
    )

    # Source 3: Staple cards (EDHREC-filtered)
    await _add_staple_candidates(db, candidates, deck_colors, format_legal, budget_max, seen_names)

    # Source 4: 17Lands synergy pairs - find cards that synergize with deck cards
    if gameplay_db.is_available:
        await _add_synergy_pair_candidates(
            db,
            gameplay_db,
            candidates,
            resolved_cards,
            deck_colors,
            format_legal,
            budget_max,
            seen_names,
        )

    # Source 4: Combo piece suggestions
    if combo_detector and combo_detector.is_available:
        await _add_combo_candidates(
            db,
            combo_detector,
            candidates,
            deck_cards,
            deck_colors,
            format_legal,
            budget_max,
            seen_names,
        )

    # Score and rank all candidates
    scored_suggestions = await _score_and_rank_candidates(candidates, gameplay_db)

    return SuggestCardsResult(
        suggestions=scored_suggestions[:max_results],
        detected_themes=detected_themes,
        deck_colors=deck_colors,
    )


class _SuggestionCandidate:
    """Internal candidate for suggestion scoring."""

    __slots__ = (
        "categories",
        "cmc",
        "combo_ids",
        "edhrec_rank",
        "mana_cost",
        "name",
        "price_usd",
        "reasons",
        "synergy_lift",
        "type_line",
    )

    def __init__(self, name: str) -> None:
        self.name = name
        self.reasons: list[str] = []
        self.categories: set[str] = set()
        self.mana_cost: str | None = None
        self.type_line: str | None = None
        self.price_usd: float | None = None
        self.edhrec_rank: int | None = None
        self.synergy_lift: float = 0.0
        self.combo_ids: list[str] = []
        self.cmc: float = 0.0


async def _add_theme_candidates(
    db: UnifiedDatabase,
    candidates: dict[str, _SuggestionCandidate],
    search_term: str,
    theme: str,
    deck_colors: list[str],
    format_legal: str | None,
    budget_max: float | None,
    seen_names: set[str],
) -> None:
    """Add theme-based candidates."""
    results, _ = await db.search_cards(
        SearchCardsInput(
            text=search_term,
            color_identity=deck_colors if deck_colors else None,  # type: ignore[arg-type]
            format_legal=format_legal,  # type: ignore[arg-type]
            page_size=30,
        )
    )

    for card in results:
        name_lower = normalize_card_name(card.name)
        if name_lower in seen_names:
            continue
        seen_names.add(name_lower)

        price_usd = await _get_card_price(db, card.name)
        if budget_max is not None and price_usd is not None and price_usd > budget_max:
            continue

        if card.name not in candidates:
            candidates[card.name] = _SuggestionCandidate(card.name)

        cand = candidates[card.name]
        cand.reasons.append(f"Fits {theme} theme")
        cand.categories.add("synergy")
        cand.mana_cost = card.mana_cost
        cand.type_line = card.type
        cand.price_usd = price_usd
        cand.edhrec_rank = card.edhrec_rank
        cand.cmc = card.cmc or 0.0


async def _add_synergy_candidates_from_deck(
    db: UnifiedDatabase,
    candidates: dict[str, _SuggestionCandidate],
    resolved_cards: list[Card],
    deck_colors: list[str],
    format_legal: str | None,
    budget_max: float | None,
    seen_names: set[str],
) -> None:
    """Add candidates by finding synergies for key deck cards.

    Reuses the existing find_synergies logic which handles:
    - Keyword synergies (flying -> cards that care about flying)
    - Tribal synergies (elf -> elf lords)
    - Ability synergies (ETB -> blink effects)
    """
    # Pick key cards to find synergies for (limit to avoid slowdown)
    # Prioritize cards with keywords/abilities that have synergy potential
    key_cards = [c for c in resolved_cards if c.keywords or (c.text and len(c.text) > 50)][:5]

    for card in key_cards:
        try:
            result = await find_synergies(
                db, card.name, max_results=30, format_legal=format_legal, use_cache=True
            )

            for syn in result.synergies:
                name_lower = normalize_card_name(syn.name)
                if name_lower in seen_names:
                    continue

                # Check color identity
                # Need to look up the card to get full details
                try:
                    syn_card = await db.get_card_by_name(syn.name)
                    if not syn_card:
                        continue

                    if (
                        deck_colors
                        and syn_card.color_identity
                        and not set(syn_card.color_identity).issubset(set(deck_colors))
                    ):
                        continue

                    # Check budget
                    if (
                        budget_max is not None
                        and syn.price_usd is not None
                        and syn.price_usd > budget_max
                    ):
                        continue

                    seen_names.add(name_lower)

                    if syn.name not in candidates:
                        candidates[syn.name] = _SuggestionCandidate(syn.name)

                    cand = candidates[syn.name]
                    cand.reasons.append(f"{syn.reason} ({card.name})")
                    cand.categories.add("synergy")
                    cand.mana_cost = syn.mana_cost
                    cand.type_line = syn.type_line
                    cand.price_usd = syn.price_usd
                    cand.edhrec_rank = syn.edhrec_rank
                    cand.cmc = syn_card.cmc or 0.0

                except CardNotFoundError:
                    continue

        except CardNotFoundError:
            continue


async def _add_staple_candidates(
    db: UnifiedDatabase,
    candidates: dict[str, _SuggestionCandidate],
    deck_colors: list[str],
    format_legal: str | None,
    budget_max: float | None,
    seen_names: set[str],
) -> None:
    """Add staple card candidates filtered by EDHREC rank."""
    # Use simple text patterns (LIKE %text%) not regex
    staple_searches = [
        ("draw a card", "Card advantage staple"),
        ("draw cards", "Card advantage staple"),
        ("destroy target", "Removal staple"),
        ("exile target", "Removal staple"),
        ("add {", "Ramp staple"),
        ("counter target spell", "Counterspell staple"),
        ("return target", "Recursion staple"),
    ]

    for search_term, reason in staple_searches:
        results, _ = await db.search_cards(
            SearchCardsInput(
                text=search_term,
                color_identity=deck_colors if deck_colors else None,  # type: ignore[arg-type]
                format_legal=format_legal,  # type: ignore[arg-type]
                page_size=20,
            )
        )

        for card in results:
            name_lower = normalize_card_name(card.name)
            if name_lower in seen_names:
                continue

            # EDHREC filter: only include popular staples (rank < 5000)
            if card.edhrec_rank is not None and card.edhrec_rank > 5000:
                continue

            seen_names.add(name_lower)

            price_usd = await _get_card_price(db, card.name)
            if budget_max is not None and price_usd is not None and price_usd > budget_max:
                continue

            if card.name not in candidates:
                candidates[card.name] = _SuggestionCandidate(card.name)

            cand = candidates[card.name]
            cand.reasons.append(reason)
            cand.categories.add("staple")
            cand.mana_cost = card.mana_cost
            cand.type_line = card.type
            cand.price_usd = price_usd
            cand.edhrec_rank = card.edhrec_rank
            cand.cmc = card.cmc or 0.0


async def _add_synergy_pair_candidates(
    db: UnifiedDatabase,
    gameplay_db: object,
    candidates: dict[str, _SuggestionCandidate],
    resolved_cards: list[Card],
    deck_colors: list[str],
    format_legal: str | None,
    budget_max: float | None,
    seen_names: set[str],
) -> None:
    """Add candidates from 17Lands synergy pairs."""
    from ..recommendations.gameplay import GameplayDB

    if not isinstance(gameplay_db, GameplayDB) or not gameplay_db.is_available:
        return

    gameplay_db.connect()

    # Find synergy pairs for key deck cards (limit to avoid slowdown)
    for card in resolved_cards[:10]:
        pairs = gameplay_db.get_synergy_pairs(card.name, min_games=100, min_lift=0.02)

        for pair in pairs[:5]:  # Top 5 synergies per card
            partner_name = pair.card_b
            name_lower = normalize_card_name(partner_name)

            if name_lower in seen_names:
                # Update synergy lift if already a candidate
                if partner_name in candidates:
                    candidates[partner_name].synergy_lift = max(
                        candidates[partner_name].synergy_lift, pair.synergy_lift or 0.0
                    )
                continue

            # Verify card exists and matches color identity
            try:
                partner_card = await db.get_card_by_name(partner_name)
                if not partner_card:
                    continue

                # Check color identity
                if (
                    deck_colors
                    and partner_card.color_identity
                    and not set(partner_card.color_identity).issubset(set(deck_colors))
                ):
                    continue

                # Check format legality
                if format_legal and not _is_format_legal(partner_card, format_legal):
                    continue

                seen_names.add(name_lower)

                price_usd = await _get_card_price(db, partner_name)
                if budget_max is not None and price_usd is not None and price_usd > budget_max:
                    continue

                if partner_name not in candidates:
                    candidates[partner_name] = _SuggestionCandidate(partner_name)

                cand = candidates[partner_name]
                lift_pct = int((pair.synergy_lift or 0) * 100)
                cand.reasons.append(f"+{lift_pct}% win rate with {card.name}")
                cand.categories.add("synergy")
                cand.mana_cost = partner_card.mana_cost
                cand.type_line = partner_card.type
                cand.price_usd = price_usd
                cand.edhrec_rank = partner_card.edhrec_rank
                cand.synergy_lift = max(cand.synergy_lift, pair.synergy_lift or 0.0)
                cand.cmc = partner_card.cmc or 0.0

            except CardNotFoundError:
                continue


def _is_format_legal(card: Card, format_name: str) -> bool:
    """Check if a card is legal in the given format."""
    # Card model has is_legal_in method that handles list of CardLegality
    return card.is_legal_in(format_name)


async def _add_combo_candidates(
    db: UnifiedDatabase,
    combo_detector: object,  # SpellbookComboDetector
    candidates: dict[str, _SuggestionCandidate],
    deck_cards: list[str],
    deck_colors: list[str],
    format_legal: str | None,
    budget_max: float | None,
    seen_names: set[str],
) -> None:
    """Add missing combo piece candidates."""
    from ..recommendations.spellbook_combos import SpellbookComboDetector

    if not isinstance(combo_detector, SpellbookComboDetector):
        return

    # Find combos we're close to completing (missing 1-2 pieces)
    _, missing_to_combos = await combo_detector.find_missing_pieces(
        deck_cards,
        max_missing=2,
        min_present=2,
    )

    # Get the most impactful missing pieces
    for missing_card, combo_ids in list(missing_to_combos.items())[:15]:
        name_lower = normalize_card_name(missing_card)
        if name_lower in seen_names:
            # Update combo IDs if already a candidate
            if missing_card in candidates:
                candidates[missing_card].combo_ids.extend(combo_ids)
            continue

        # Verify card exists and matches constraints
        try:
            card = await db.get_card_by_name(missing_card)
            if not card:
                continue

            # Check color identity
            if (
                deck_colors
                and card.color_identity
                and not set(card.color_identity).issubset(set(deck_colors))
            ):
                continue

            # Check format legality
            if format_legal and not _is_format_legal(card, format_legal):
                continue

            seen_names.add(name_lower)

            price_usd = await _get_card_price(db, missing_card)
            if budget_max is not None and price_usd is not None and price_usd > budget_max:
                continue

            if missing_card not in candidates:
                candidates[missing_card] = _SuggestionCandidate(missing_card)

            cand = candidates[missing_card]
            combo_count = len(combo_ids)
            cand.reasons.append(f"Enables {combo_count} combo{'s' if combo_count > 1 else ''}")
            cand.categories.add("synergy")
            cand.mana_cost = card.mana_cost
            cand.type_line = card.type
            cand.price_usd = price_usd
            cand.edhrec_rank = card.edhrec_rank
            cand.combo_ids = combo_ids
            cand.cmc = card.cmc or 0.0

        except CardNotFoundError:
            continue


async def _score_and_rank_candidates(
    candidates: dict[str, _SuggestionCandidate],
    gameplay_db: object,
) -> list[SuggestedCard]:
    """Score candidates and return sorted suggestions with balanced representation."""
    from ..recommendations.gameplay import GameplayDB

    # Track suggestions by category for balanced output
    by_category: dict[str, list[tuple[float, SuggestedCard]]] = {
        "synergy": [],
        "staple": [],
        "combo": [],
        "gameplay": [],  # Cards with 17Lands data
    }

    for cand in candidates.values():
        # Calculate composite score (0-100)
        score = 0.0

        # 1. EDHREC popularity (0-30 points)
        # Lower rank = more popular = higher score
        if cand.edhrec_rank is not None:
            if cand.edhrec_rank <= 100:
                score += 30
            elif cand.edhrec_rank <= 500:
                score += 25
            elif cand.edhrec_rank <= 1000:
                score += 20
            elif cand.edhrec_rank <= 2500:
                score += 15
            elif cand.edhrec_rank <= 5000:
                score += 10
            else:
                score += 5

        # 2. 17Lands tier (0-25 points)
        tier: str | None = None
        has_gameplay_data = False
        if isinstance(gameplay_db, GameplayDB) and gameplay_db.is_available:
            tier = gameplay_db.get_tier(cand.name)
            if tier:
                has_gameplay_data = True
            tier_scores = {"S": 25, "A": 20, "B": 15, "C": 10, "D": 5, "F": 0}
            score += tier_scores.get(tier or "", 10)  # Default 10 if no data
        else:
            score += 10  # Neutral if no 17Lands data

        # 3. Synergy lift from 17Lands (0-20 points)
        if cand.synergy_lift > 0:
            has_gameplay_data = True
            # 5% lift = 10 points, 10% lift = 20 points
            synergy_points = min(cand.synergy_lift * 200, 20)
            score += synergy_points

        # 4. Combo potential (0-15 points)
        combo_count = len(cand.combo_ids)
        if combo_count > 0:
            # 1 combo = 5 points, 3+ combos = 15 points
            combo_points = min(5 + (combo_count - 1) * 5, 15)
            score += combo_points

        # 5. Multiple reasons bonus (0-10 points)
        reason_bonus = min(len(cand.reasons) * 3, 10)
        score += reason_bonus

        # 6. Mana efficiency bonus (0-5 points)
        # Slight preference for efficient cards, but don't exclude expensive ones
        # Lands (CMC 0) and cheap spells get a small bonus
        if cand.cmc <= 1:
            score += 5
        elif cand.cmc <= 2:
            score += 4
        elif cand.cmc <= 3:
            score += 3
        elif cand.cmc <= 4:
            score += 2
        elif cand.cmc <= 5:
            score += 1
        # 6+ CMC cards get no bonus but aren't penalized

        # Determine primary category for balancing
        if combo_count > 0:
            primary_category = "combo"
        elif "staple" in cand.categories:
            primary_category = "staple"
        elif has_gameplay_data:
            primary_category = "gameplay"
        else:
            primary_category = "synergy"

        # Build reason string
        reason = cand.reasons[0] if cand.reasons else "Recommended"
        if len(cand.reasons) > 1:
            reason += f" (+{len(cand.reasons) - 1} more)"

        # Use "synergy" or "staple" for the public category field
        public_category = "staple" if "staple" in cand.categories else "synergy"

        suggestion = SuggestedCard(
            name=cand.name,
            reason=reason,
            category=public_category,  # type: ignore[arg-type]
            mana_cost=cand.mana_cost,
            type_line=cand.type_line,
            price_usd=cand.price_usd,
            score=round(score, 1),
            tier=tier,
            edhrec_rank=cand.edhrec_rank,
            combo_count=combo_count if combo_count > 0 else None,
        )

        by_category[primary_category].append((score, suggestion))

    # Sort each category by score
    for cat_list in by_category.values():
        cat_list.sort(key=lambda x: -x[0])

    # Build balanced output: round-robin from each category that has candidates
    # This ensures no single type dominates the suggestions
    result: list[SuggestedCard] = []
    seen_names: set[str] = set()
    category_indices: dict[str, int] = dict.fromkeys(by_category, 0)

    # Categories in priority order for picking
    category_order = ["synergy", "combo", "staple", "gameplay"]

    # Round-robin until we have enough or run out of candidates
    max_iterations = sum(len(v) for v in by_category.values())
    iteration = 0

    while len(result) < 100 and iteration < max_iterations:
        added_this_round = False
        for cat in category_order:
            idx = category_indices[cat]
            cat_list = by_category[cat]

            # Find next unseen card in this category
            while idx < len(cat_list):
                _, suggestion = cat_list[idx]
                idx += 1
                if suggestion.name not in seen_names:
                    result.append(suggestion)
                    seen_names.add(suggestion.name)
                    added_this_round = True
                    break

            category_indices[cat] = idx

        if not added_this_round:
            break
        iteration += 1

    return result


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
    # Use simple text patterns (LIKE %text%) not regex
    staple_searches = [
        ("draw a card", "Card advantage staple"),
        ("destroy target", "Removal staple"),
        ("add {", "Ramp staple"),
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
