"""Deck analysis tools."""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import TYPE_CHECKING

from ..data.models.card import Card
from ..data.models.responses import (
    CardIssue,
    CardPrice,
    ColorAnalysisResult,
    ColorBreakdown,
    CompositionResult,
    DeckValidationResult,
    ManaCurveResult,
    PriceAnalysisResult,
    TypeCount,
)
from ..exceptions import CardNotFoundError
from ..utils.mana import COLOR_ORDER, COLORS, parse_mana_cost

if TYPE_CHECKING:
    from ..data.database import MTGDatabase, ScryfallDatabase
    from ..data.models.inputs import AnalyzeDeckInput, DeckCardInput, ValidateDeckInput

# Format rules: (min_deck_size, max_sideboard, copy_limit, is_singleton, check_color_identity)
FORMAT_RULES: dict[str, tuple[int, int, int, bool, bool]] = {
    "standard": (60, 15, 4, False, False),
    "modern": (60, 15, 4, False, False),
    "legacy": (60, 15, 4, False, False),
    "vintage": (60, 15, 4, False, False),
    "pioneer": (60, 15, 4, False, False),
    "pauper": (60, 15, 4, False, False),
    "historic": (60, 15, 4, False, False),
    "alchemy": (60, 15, 4, False, False),
    "explorer": (60, 15, 4, False, False),
    "timeless": (60, 15, 4, False, False),
    "commander": (100, 0, 1, True, True),
    "brawl": (60, 0, 1, True, True),
    "oathbreaker": (60, 0, 1, True, True),
    "duel": (100, 0, 1, True, True),  # Duel Commander
}

# Basic lands are exempt from singleton rules
BASIC_LANDS = frozenset({
    "Plains",
    "Island",
    "Swamp",
    "Mountain",
    "Forest",
    "Wastes",
    "Snow-Covered Plains",
    "Snow-Covered Island",
    "Snow-Covered Swamp",
    "Snow-Covered Mountain",
    "Snow-Covered Forest",
})

# Keywords/text patterns for detecting interaction
INTERACTION_PATTERNS = frozenset({
    "destroy",
    "exile",
    "counter target",
    "return target",
    "bounce",
    "sacrifice",
    "-1/-1",
    "deals damage",
})

# Keywords/text patterns for detecting ramp
RAMP_PATTERNS = frozenset({
    "add {",
    "search your library for a basic land",
    "search your library for a land",
    "mana of any",
    "add one mana",
    "add two mana",
})


async def _resolve_deck_cards(
    db: MTGDatabase,
    cards: list[DeckCardInput],
    include_extras: bool = False,
) -> list[tuple[DeckCardInput, Card | None]]:
    """
    Look up all cards in deck.

    Args:
        db: Database connection
        cards: List of deck card inputs
        include_extras: If True, load legalities and rulings (slower)

    Returns list of tuples: (input, Card or None if not found)
    """
    results: list[tuple[DeckCardInput, Card | None]] = []

    for card_input in cards:
        try:
            card = await db.get_card_by_name(card_input.name, include_extras=include_extras)
            results.append((card_input, card))
        except CardNotFoundError:
            results.append((card_input, None))

    return results


async def validate_deck(
    db: MTGDatabase,
    input: ValidateDeckInput,
) -> DeckValidationResult:
    """Validate a deck against format rules."""
    format_name = input.format.lower()
    issues: list[CardIssue] = []
    warnings: list[str] = []

    # Get format rules
    rules = FORMAT_RULES.get(format_name)
    if not rules:
        # Default to standard-like rules for unknown formats
        rules = (60, 15, 4, False, False)
        warnings.append(f"Unknown format '{format_name}', using default rules")

    min_deck_size, max_sideboard, copy_limit, is_singleton, check_identity = rules

    # Resolve all cards (with legalities for validation)
    resolved = await _resolve_deck_cards(db, input.cards, include_extras=input.check_legality)

    # Count cards
    mainboard_cards = [r for r in resolved if not r[0].sideboard]
    sideboard_cards = [r for r in resolved if r[0].sideboard]

    total_mainboard = sum(r[0].quantity for r in mainboard_cards)
    total_sideboard = sum(r[0].quantity for r in sideboard_cards)

    # Get commander card for color identity check
    commander_card: Card | None = None
    commander_identity: set[str] = set()
    if input.commander and (is_singleton or input.check_color_identity):
        try:
            commander_card = await db.get_card_by_name(input.commander)
            commander_identity = set(commander_card.color_identity or [])
        except CardNotFoundError:
            issues.append(CardIssue(
                card_name=input.commander,
                issue="not_found",
                details="Commander card not found in database",
            ))

    # Track card counts for copy limit check
    card_counts: dict[str, int] = defaultdict(int)

    for card_input, card in resolved:
        card_name = card_input.name

        # Card not found
        if card is None:
            issues.append(CardIssue(
                card_name=card_name,
                issue="not_found",
                details="Card not found in database",
            ))
            continue

        # Check legality
        if input.check_legality and card.legalities and not card.is_legal_in(format_name):
            legality = card.get_legality(format_name)
            issues.append(CardIssue(
                card_name=card_name,
                issue="not_legal",
                details=f"Card is {legality or 'not legal'} in {format_name}",
            ))

        # Track copy count
        card_counts[card_name] += card_input.quantity

        # Check color identity (Commander/Brawl)
        if input.check_color_identity and check_identity and commander_card:
            card_identity = set(card.color_identity or [])
            if not card_identity.issubset(commander_identity):
                outside_colors = card_identity - commander_identity
                issues.append(CardIssue(
                    card_name=card_name,
                    issue="outside_color_identity",
                    details=f"Card has colors {list(outside_colors)} outside commander's identity",
                ))

    # Check copy limits
    if input.check_copy_limit:
        for card_name, count in card_counts.items():
            # Basic lands exempt from singleton
            if card_name in BASIC_LANDS:
                continue

            limit = 1 if (is_singleton and input.check_singleton) else copy_limit
            if count > limit:
                issue_type = "over_singleton_limit" if is_singleton else "over_copy_limit"
                issues.append(CardIssue(
                    card_name=card_name,
                    issue=issue_type,
                    details=f"Has {count} copies, limit is {limit}",
                ))

    # Check deck size
    if input.check_deck_size:
        if format_name == "commander" and total_mainboard != 100:
            # Commander requires exactly 100 cards (including commander)
            warnings.append(f"Commander deck should be exactly 100 cards, has {total_mainboard}")
        elif total_mainboard < min_deck_size:
            warnings.append(f"Deck has {total_mainboard} cards, minimum is {min_deck_size}")

        if max_sideboard > 0 and total_sideboard > max_sideboard:
            warnings.append(f"Sideboard has {total_sideboard} cards, maximum is {max_sideboard}")

    is_valid = len(issues) == 0

    return DeckValidationResult(
        format=format_name,
        is_valid=is_valid,
        total_cards=total_mainboard,
        sideboard_count=total_sideboard,
        issues=issues,
        warnings=warnings,
    )


async def analyze_mana_curve(
    db: MTGDatabase,
    input: AnalyzeDeckInput,
) -> ManaCurveResult:
    """Analyze the mana curve of a deck."""
    resolved = await _resolve_deck_cards(db, input.cards)

    curve: dict[int, int] = defaultdict(int)
    cmc_values: list[float] = []
    land_count = 0
    x_spell_count = 0

    for card_input, card in resolved:
        if card is None:
            continue

        quantity = card_input.quantity

        # Check if land
        if card.types and "Land" in card.types:
            land_count += quantity
            continue

        # Get CMC
        cmc = card.cmc or 0

        # Check for X spells
        if card.mana_cost and "X" in card.mana_cost.upper():
            x_spell_count += quantity

        # Add to curve
        cmc_int = int(cmc)
        curve[cmc_int] += quantity

        # Track for average/median
        cmc_values.extend([cmc] * quantity)

    # Calculate stats
    nonland_count = sum(curve.values())
    average_cmc = statistics.mean(cmc_values) if cmc_values else 0.0
    median_cmc = statistics.median(cmc_values) if cmc_values else 0.0

    # Convert defaultdict to regular dict and fill gaps
    max_cmc = max(curve.keys()) if curve else 0
    curve_dict = {i: curve.get(i, 0) for i in range(max_cmc + 1)}

    return ManaCurveResult(
        curve=curve_dict,
        average_cmc=round(average_cmc, 2),
        median_cmc=round(median_cmc, 2),
        land_count=land_count,
        nonland_count=nonland_count,
        x_spell_count=x_spell_count,
    )


async def analyze_colors(
    db: MTGDatabase,
    input: AnalyzeDeckInput,
) -> ColorAnalysisResult:
    """Analyze the color distribution of a deck."""
    resolved = await _resolve_deck_cards(db, input.cards)

    # Track colors and pips
    deck_colors: set[str] = set()
    deck_identity: set[str] = set()
    color_card_counts: dict[str, int] = defaultdict(int)
    mana_pip_totals: dict[str, int] = defaultdict(int)
    multicolor_count = 0
    colorless_count = 0

    for card_input, card in resolved:
        if card is None:
            continue

        quantity = card_input.quantity
        card_colors = card.colors or []
        card_identity = card.color_identity or []

        # Track deck colors
        deck_colors.update(card_colors)
        deck_identity.update(card_identity)

        # Count card by color
        if not card_colors:
            colorless_count += quantity
        elif len(card_colors) > 1:
            multicolor_count += quantity
            for color in card_colors:
                color_card_counts[color] += quantity
        else:
            color_card_counts[card_colors[0]] += quantity

        # Parse mana cost for pip counts
        if card.mana_cost:
            parsed = parse_mana_cost(card.mana_cost)
            for color, count in parsed.colored.items():
                mana_pip_totals[color] += count * quantity

    # Build color breakdown
    breakdown: list[ColorBreakdown] = []
    for color in COLOR_ORDER:
        if color in deck_colors or mana_pip_totals.get(color, 0) > 0:
            breakdown.append(ColorBreakdown(
                color=color,
                color_name=COLORS[color],
                card_count=color_card_counts.get(color, 0),
                mana_symbols=mana_pip_totals.get(color, 0),
            ))

    # Calculate recommended land ratios
    total_pips = sum(mana_pip_totals.values())
    recommended_ratio: dict[str, float] = {}
    if total_pips > 0:
        for color in COLOR_ORDER:
            if color in mana_pip_totals:
                ratio = mana_pip_totals[color] / total_pips
                recommended_ratio[color] = round(ratio, 2)

    # Sort colors in WUBRG order
    sorted_colors = [c for c in COLOR_ORDER if c in deck_colors]
    sorted_identity = [c for c in COLOR_ORDER if c in deck_identity]

    return ColorAnalysisResult(
        colors=sorted_colors,
        color_identity=sorted_identity,
        breakdown=breakdown,
        multicolor_count=multicolor_count,
        colorless_count=colorless_count,
        mana_pip_totals=dict(mana_pip_totals),
        recommended_land_ratio=recommended_ratio,
    )


async def analyze_deck_composition(
    db: MTGDatabase,
    input: AnalyzeDeckInput,
) -> CompositionResult:
    """Analyze the card type composition of a deck."""
    resolved = await _resolve_deck_cards(db, input.cards)

    type_counts: dict[str, int] = defaultdict(int)
    creatures = 0
    lands = 0
    instants = 0
    sorceries = 0
    interaction = 0
    ramp_count = 0
    total_cards = 0

    for card_input, card in resolved:
        if card is None:
            continue

        quantity = card_input.quantity
        total_cards += quantity
        card_types = card.types or []

        # Count by type
        for card_type in card_types:
            type_counts[card_type] += quantity

        # Track specific categories
        if "Creature" in card_types:
            creatures += quantity
        if "Land" in card_types:
            lands += quantity
        if "Instant" in card_types:
            instants += quantity
        if "Sorcery" in card_types:
            sorceries += quantity

        # Detect interaction (heuristic)
        card_text = (card.text or "").lower()
        if any(pattern in card_text for pattern in INTERACTION_PATTERNS):
            interaction += quantity

        # Detect ramp (heuristic)
        if any(pattern in card_text for pattern in RAMP_PATTERNS):
            ramp_count += quantity

    # Build type breakdown with percentages
    type_list: list[TypeCount] = []
    for card_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        percentage = (count / total_cards * 100) if total_cards > 0 else 0
        type_list.append(TypeCount(
            type=card_type,
            count=count,
            percentage=round(percentage, 1),
        ))

    return CompositionResult(
        total_cards=total_cards,
        types=type_list,
        creatures=creatures,
        noncreatures=total_cards - creatures - lands,
        lands=lands,
        spells=instants + sorceries,
        interaction=interaction,
        ramp_count=ramp_count,
    )


async def analyze_deck_price(
    db: MTGDatabase,  # noqa: ARG001 - kept for API consistency with other analyze functions
    scryfall: ScryfallDatabase | None,
    input: AnalyzeDeckInput,
) -> PriceAnalysisResult:
    """Analyze the price of a deck."""
    if scryfall is None:
        return PriceAnalysisResult(
            total_price=None,
            mainboard_price=None,
            sideboard_price=None,
            average_card_price=None,
            most_expensive=[],
            missing_prices=[c.name for c in input.cards],
        )

    card_prices: list[CardPrice] = []
    missing_prices: list[str] = []
    mainboard_total = 0.0
    sideboard_total = 0.0

    for card_input in input.cards:
        try:
            card_image = await scryfall.get_card_image(card_input.name)
            if card_image:
                unit_price = card_image.get_price_usd()
                if unit_price is not None:
                    total_price = unit_price * card_input.quantity
                    card_prices.append(CardPrice(
                        name=card_input.name,
                        quantity=card_input.quantity,
                        unit_price=unit_price,
                        total_price=total_price,
                    ))
                    if card_input.sideboard:
                        sideboard_total += total_price
                    else:
                        mainboard_total += total_price
                else:
                    missing_prices.append(card_input.name)
            else:
                missing_prices.append(card_input.name)
        except Exception:
            missing_prices.append(card_input.name)

    # Sort by total price descending, take top 10
    card_prices.sort(key=lambda x: x.total_price or 0, reverse=True)
    most_expensive = card_prices[:10]

    total_price = mainboard_total + sideboard_total
    cards_with_prices = len(card_prices)
    average_price = total_price / cards_with_prices if cards_with_prices > 0 else None

    return PriceAnalysisResult(
        total_price=round(total_price, 2) if total_price > 0 else None,
        mainboard_price=round(mainboard_total, 2) if mainboard_total > 0 else None,
        sideboard_price=round(sideboard_total, 2) if sideboard_total > 0 else None,
        average_card_price=round(average_price, 2) if average_price else None,
        most_expensive=most_expensive,
        missing_prices=missing_prices,
    )
