"""Deck analysis tools."""

from __future__ import annotations

import re
import statistics
from collections import Counter, defaultdict
from typing import TYPE_CHECKING

from ..data.models.card import Card
from ..data.models.responses import (
    ArchetypeType,
    CardIssue,
    CardPrice,
    ColorAnalysisResult,
    ColorBreakdown,
    CompositionResult,
    DeckHealthIssue,
    DeckHealthResult,
    DeckTheme,
    DeckValidationResult,
    GradeType,
    KeywordCount,
    ManaCurveResult,
    MatchupInfo,
    PriceAnalysisResult,
    SynergyPair,
    TypeCount,
)
from ..exceptions import CardNotFoundError
from ..utils.mana import COLOR_ORDER, COLORS, parse_mana_cost

if TYPE_CHECKING:
    from ..data.database import UnifiedDatabase
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
BASIC_LANDS = frozenset(
    {
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
    }
)

# Keywords/text patterns for detecting interaction (removal/counterspells)
# Match TUI patterns for consistency
INTERACTION_PATTERNS = frozenset(
    {
        "destroy target",
        "destroy all",
        "exile target",
        "counter target",
        "-1/-1",
        "-x/-x",
        "deals damage to any target",
        "deals damage to target",
        "fight",
    }
)

# Keywords/text patterns for detecting ramp (mana acceleration)
# Match TUI patterns for consistency
RAMP_PATTERNS = frozenset(
    {
        "add {",
        "add one mana",
        "search your library for a",
        "mana of any",
    }
)

# Keywords/text patterns for detecting card draw
# Match TUI patterns for consistency
CARD_DRAW_PATTERNS = frozenset(
    {
        "draw",
        "scry",
        "look at the top",
    }
)

# Theme detection patterns (theme_name -> list of regex patterns)
# Expanded theme list for better deck categorization
THEME_PATTERNS: dict[str, list[str]] = {
    # Core archetypes
    "Aggro": [r"haste", r"attack.*trigger", r"combat.*damage", r"first strike"],
    "Control": [r"counter target", r"destroy target", r"exile target", r"return.*to.*hand"],
    "Midrange": [r"value", r"etb.*draw", r"enters.*battlefield.*effect"],
    # Synergy themes
    "Tokens": [r"create.*token", r"token.*creature", r"populate", r"convoke"],
    "Sacrifice": [r"sacrifice", r"when.*dies", r"whenever.*dies", r"aristocrat", r"death trigger"],
    "Graveyard": [r"graveyard", r"return.*from.*graveyard", r"mill", r"flashback", r"unearth"],
    "Counters": [r"\+1/\+1 counter", r"proliferate", r"counter.*on.*creature"],
    "Lifegain": [r"gain.*life", r"lifelink", r"whenever you gain life"],
    "Artifacts": [r"artifact.*enters", r"for each artifact", r"metalcraft", r"affinity"],
    "Enchantments": [r"enchantment.*enters", r"constellation", r"whenever.*enchantment", r"aura"],
    "Spellslinger": [
        r"whenever you cast.*instant",
        r"whenever you cast.*sorcery",
        r"prowess",
        r"magecraft",
    ],
    "Blink": [r"exile.*return", r"flicker", r"enters the battlefield"],
    "Landfall": [r"land.*enters", r"landfall", r"play.*additional land"],
    "Reanimator": [r"return.*graveyard.*battlefield", r"reanimate", r"unearth"],
    "Voltron": [r"equipment", r"attach", r"equipped creature", r"enchanted creature"],
    # Additional themes
    "Burn": [r"deals? \d+ damage to", r"damage to any target", r"lightning"],
    "Mill": [r"mill \d+", r"library into.*graveyard", r"cards? from.*library"],
    "Ramp": [r"add \{[WUBRGC]\}", r"search.*library.*land", r"land.*onto.*battlefield"],
    "Draw": [r"draw.*card", r"whenever.*draw", r"scry \d+"],
    "Discard": [r"discard", r"opponent.*discard", r"madness"],
    "Stax": [r"can't cast", r"can't attack", r"opponents can't", r"each player sacrifices"],
    "Superfriends": [r"planeswalker", r"loyalty counter", r"each planeswalker"],
    "Clones": [r"copy of", r"becomes? a copy", r"clone"],
    "Energy": [r"energy counter", r"\{E\}"],
    "Infect": [r"infect", r"poison counter", r"proliferate.*poison"],
    "Storm": [r"storm", r"cast.*instant.*sorcery.*turn"],
    "Treasure": [r"treasure token", r"create.*treasure", r"sacrifice.*treasure"],
    "Food": [r"food token", r"create.*food", r"sacrifice.*food"],
    "Vehicles": [r"vehicle", r"crew \d+", r"crewed"],
}

# Theme descriptions for UI display
THEME_DESCRIPTIONS: dict[str, str] = {
    # Core archetypes
    "Aggro": "Fast creatures, haste, combat tricks - win quickly",
    "Control": "Counterspells, removal, card draw - answer everything",
    "Midrange": "Value creatures, flexible answers, grind out wins",
    # Synergy themes
    "Tokens": "Go wide with creature tokens, trigger on ETB/death",
    "Sacrifice": "Sacrifice outlets with death triggers for value",
    "Graveyard": "Use the graveyard as a second hand",
    "Counters": "+1/+1 counters with proliferate payoffs",
    "Lifegain": "Lifegain triggers, use life as a resource",
    "Artifacts": "Artifact synergies, metalcraft, affinity",
    "Enchantments": "Enchantress draws, constellation triggers",
    "Spellslinger": "Prowess, magecraft, storm synergies",
    "Blink": "Flicker effects for repeated ETB triggers",
    "Landfall": "Land ETB triggers for incremental value",
    "Reanimator": "Cheat big creatures from graveyard to battlefield",
    "Voltron": "Suit up one creature and swing for lethal",
    "Tribal": "Creature type synergies and lord effects",
    # Additional themes
    "Burn": "Direct damage to face and creatures",
    "Mill": "Empty opponent's library to win",
    "Ramp": "Accelerate mana for big spells early",
    "Draw": "Card advantage through drawing",
    "Discard": "Attack opponent's hand, madness synergies",
    "Stax": "Tax and restrict opponent's actions",
    "Superfriends": "Multiple planeswalkers working together",
    "Clones": "Copy your best creatures and spells",
    "Energy": "Build and spend energy counters",
    "Infect": "Poison counters for alternate win",
    "Storm": "Chain spells for massive storm count",
    "Treasure": "Generate treasure for mana and triggers",
    "Food": "Food tokens for life and sacrifice",
    "Vehicles": "Crew vehicles for evasive threats",
}

# Matchup advantages: theme -> (strong_against, weak_against)
THEME_MATCHUPS: dict[str, tuple[list[str], list[str]]] = {
    "Tokens": (["Control", "Voltron"], ["Sacrifice", "Board wipes"]),
    "Graveyard": (["Control", "Aggro"], ["Graveyard hate", "Exile effects"]),
    "Counters": (["Midrange", "Control"], ["Mass removal", "Infect"]),
    "Sacrifice": (["Tokens", "Midrange"], ["Graveyard hate", "Fast aggro"]),
    "Lifegain": (["Aggro", "Burn"], ["Combo", "Infect"]),
    "Artifacts": (["Control", "Midrange"], ["Artifact hate", "Stax"]),
    "Enchantments": (["Midrange", "Control"], ["Enchantment hate"]),
    "Spellslinger": (["Midrange", "Tokens"], ["Fast aggro", "Counterspells"]),
    "Tribal": (["Midrange", "Control"], ["Board wipes", "Mass removal"]),
    "Blink": (["Removal-heavy", "Control"], ["Fast combo", "Aggro"]),
    "Landfall": (["Control", "Midrange"], ["Land destruction", "Fast aggro"]),
    "Reanimator": (["Control", "Midrange"], ["Graveyard hate", "Exile"]),
    "Voltron": (["Control", "Combo"], ["Sacrifice", "Go-wide"]),
    # Archetype matchups
    "Aggro": (["Control", "Combo"], ["Lifegain", "Board wipes"]),
    "Control": (["Midrange", "Combo"], ["Fast aggro", "Go-wide"]),
    "Midrange": (["Aggro", "Control"], ["Combo", "Big mana"]),
}


async def _get_card_price(db: UnifiedDatabase, card_name: str) -> float | None:
    """Get USD price for a card, or None if unavailable."""
    try:
        card = await db.get_card_by_name(card_name, include_extras=False)
        return card.get_price_usd()
    except CardNotFoundError:
        return None


async def _resolve_deck_cards(
    db: UnifiedDatabase,
    cards: list[DeckCardInput],
    include_extras: bool = False,
) -> list[tuple[DeckCardInput, Card | None]]:
    """
    Look up all cards in deck using batch loading.

    Args:
        db: Database connection
        cards: List of deck card inputs
        include_extras: If True, load legalities and rulings (slower)

    Returns list of tuples: (input, Card or None if not found)
    """
    if not cards:
        return []

    # Batch load all cards in a single query
    unique_names = list({card_input.name for card_input in cards})
    cards_by_name = await db.get_cards_by_names(unique_names, include_extras=include_extras)

    # Map results back to inputs
    results: list[tuple[DeckCardInput, Card | None]] = []
    for card_input in cards:
        card = cards_by_name.get(card_input.name.lower())
        results.append((card_input, card))

    return results


async def validate_deck(
    db: UnifiedDatabase,
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
            issues.append(
                CardIssue(
                    card_name=input.commander,
                    issue="not_found",
                    details="Commander card not found in database",
                )
            )

    # Track card counts for copy limit check
    card_counts: dict[str, int] = defaultdict(int)

    for card_input, card in resolved:
        card_name = card_input.name

        # Card not found
        if card is None:
            issues.append(
                CardIssue(
                    card_name=card_name,
                    issue="not_found",
                    details="Card not found in database",
                )
            )
            continue

        # Check legality
        if input.check_legality and card.legalities and not card.is_legal_in(format_name):
            legality = card.get_legality(format_name)
            issues.append(
                CardIssue(
                    card_name=card_name,
                    issue="not_legal",
                    details=f"Card is {legality or 'not legal'} in {format_name}",
                )
            )

        # Track copy count
        card_counts[card_name] += card_input.quantity

        # Check color identity (Commander/Brawl)
        if input.check_color_identity and check_identity and commander_card:
            card_identity = set(card.color_identity or [])
            if not card_identity.issubset(commander_identity):
                outside_colors = card_identity - commander_identity
                issues.append(
                    CardIssue(
                        card_name=card_name,
                        issue="outside_color_identity",
                        details=f"Card has colors {list(outside_colors)} outside commander's identity",
                    )
                )

    # Check copy limits
    if input.check_copy_limit:
        for card_name, count in card_counts.items():
            # Basic lands exempt from singleton
            if card_name in BASIC_LANDS:
                continue

            limit = 1 if (is_singleton and input.check_singleton) else copy_limit
            if count > limit:
                if is_singleton:
                    issues.append(
                        CardIssue(
                            card_name=card_name,
                            issue="over_singleton_limit",
                            details=f"Has {count} copies, limit is {limit}",
                        )
                    )
                else:
                    issues.append(
                        CardIssue(
                            card_name=card_name,
                            issue="over_copy_limit",
                            details=f"Has {count} copies, limit is {limit}",
                        )
                    )

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
    db: UnifiedDatabase,
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
    db: UnifiedDatabase,
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
            breakdown.append(
                ColorBreakdown(
                    color=color,
                    color_name=COLORS[color],
                    card_count=color_card_counts.get(color, 0),
                    mana_symbols=mana_pip_totals.get(color, 0),
                )
            )

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
    db: UnifiedDatabase,
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
        type_list.append(
            TypeCount(
                type=card_type,
                count=count,
                percentage=round(percentage, 1),
            )
        )

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
    db: UnifiedDatabase,
    input: AnalyzeDeckInput,
) -> PriceAnalysisResult:
    """Analyze the price of a deck."""
    card_prices: list[CardPrice] = []
    missing_prices: list[str] = []
    mainboard_total = 0.0
    sideboard_total = 0.0

    for card_input in input.cards:
        price_info = await _get_card_price(db, card_input.name)
        if price_info is None:
            missing_prices.append(card_input.name)
            continue

        total_price = price_info * card_input.quantity
        card_prices.append(
            CardPrice(
                name=card_input.name,
                quantity=card_input.quantity,
                unit_price=price_info,
                total_price=total_price,
            )
        )
        if card_input.sideboard:
            sideboard_total += total_price
        else:
            mainboard_total += total_price

    # Sort by total price descending, take top 10
    card_prices.sort(key=lambda x: x.total_price or 0, reverse=True)
    most_expensive = card_prices[:10]

    total_price = mainboard_total + sideboard_total
    # Calculate average per card, accounting for quantities
    total_cards_with_prices = sum(cp.quantity for cp in card_prices)
    average_price = total_price / total_cards_with_prices if total_cards_with_prices > 0 else None

    return PriceAnalysisResult(
        total_price=round(total_price, 2) if total_price > 0 else None,
        mainboard_price=round(mainboard_total, 2) if mainboard_total > 0 else None,
        sideboard_price=round(sideboard_total, 2) if sideboard_total > 0 else None,
        average_card_price=round(average_price, 2) if average_price else None,
        most_expensive=most_expensive,
        missing_prices=missing_prices,
    )


async def analyze_deck_health(
    db: UnifiedDatabase,
    input: AnalyzeDeckInput,
    deck_format: str | None = None,
) -> DeckHealthResult:
    """Comprehensive deck health analysis with score, archetype, and issues."""
    resolved = await _resolve_deck_cards(db, input.cards)

    # Count by type
    type_counts: dict[str, int] = defaultdict(int)
    keyword_counts: dict[str, int] = defaultdict(int)
    total_cards = 0
    cmc_values: list[float] = []

    # Metrics
    creatures = 0
    lands = 0
    instants = 0
    sorceries = 0
    artifacts = 0
    enchantments = 0
    planeswalkers = 0
    interaction = 0
    card_draw = 0
    ramp_count = 0

    # Theme and synergy tracking
    theme_counts: Counter[str] = Counter()
    tribe_counts: Counter[str] = Counter()
    card_texts: dict[str, str] = {}  # card_name -> text for synergy detection
    card_keywords: dict[str, list[str]] = {}  # card_name -> keywords

    for card_input, card in resolved:
        if card is None:
            continue

        quantity = card_input.quantity
        total_cards += quantity
        card_types = card.types or []
        card_text = (card.text or "").lower()
        card_name = card_input.name

        # Store for synergy detection
        if card_text:
            card_texts[card_name] = card_text
        if card.keywords:
            card_keywords[card_name] = card.keywords

        # Count by type
        for card_type in card_types:
            type_counts[card_type] += quantity

        # Track specific categories
        if "Creature" in card_types:
            creatures += quantity
            # Extract creature subtypes for tribal detection
            if card.subtypes:
                for subtype in card.subtypes:
                    tribe_counts[subtype] += quantity
        if "Land" in card_types:
            lands += quantity
        else:
            # Track CMC for non-lands
            cmc_values.extend([card.cmc or 0] * quantity)
        if "Instant" in card_types:
            instants += quantity
        if "Sorcery" in card_types:
            sorceries += quantity
        if "Artifact" in card_types:
            artifacts += quantity
        if "Enchantment" in card_types:
            enchantments += quantity
        if "Planeswalker" in card_types:
            planeswalkers += quantity

        # Detect interaction
        if any(pattern in card_text for pattern in INTERACTION_PATTERNS):
            interaction += quantity

        # Detect card draw
        if any(pattern in card_text for pattern in CARD_DRAW_PATTERNS):
            card_draw += quantity

        # Detect ramp (non-lands only)
        if "Land" not in card_types and any(pattern in card_text for pattern in RAMP_PATTERNS):
            ramp_count += quantity

        # Count keywords
        if card.keywords:
            for kw in card.keywords:
                keyword_counts[kw] += quantity

        # Detect themes from card text
        for theme, patterns in THEME_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, card_text, re.IGNORECASE):
                    theme_counts[theme] += quantity
                    break  # Only count once per theme per card

    # Calculate average CMC
    avg_cmc = statistics.mean(cmc_values) if cmc_values else 0.0

    # Determine expected card count based on format
    format_lower = (deck_format or "standard").lower()
    expected_cards = 99 if format_lower == "commander" else 60

    # Calculate land percentage
    land_pct = (lands / total_cards * 100) if total_cards > 0 else 0

    # Calculate score and detect issues
    score = 100
    issues: list[DeckHealthIssue] = []

    # Card count check
    if total_cards < expected_cards:
        missing = expected_cards - total_cards
        penalty = min(30, missing * 2)
        score -= penalty
        issues.append(
            DeckHealthIssue(
                message=f"Need {missing} more cards ({total_cards}/{expected_cards})",
                severity="error" if missing > 10 else "warning",
            )
        )

    # Land ratio check (target: 35-42% for most formats)
    if land_pct < 33:
        score -= 15
        target = int(total_cards * 0.38)
        issues.append(
            DeckHealthIssue(
                message=f"Low land count ({lands}, recommend ~{target})",
                severity="warning",
            )
        )
    elif land_pct > 45:
        score -= 10
        issues.append(
            DeckHealthIssue(
                message=f"High land count ({lands}, {land_pct:.0f}%)",
                severity="warning",
            )
        )

    # CMC check
    if avg_cmc > 4.0:
        score -= 15
        issues.append(
            DeckHealthIssue(
                message=f"Very high average CMC ({avg_cmc:.1f})",
                severity="warning",
            )
        )
    elif avg_cmc > 3.5:
        score -= 5
        issues.append(
            DeckHealthIssue(
                message=f"High average CMC ({avg_cmc:.1f})",
                severity="warning",
            )
        )

    # Interaction check
    if interaction < 6:
        score -= 10
        issues.append(
            DeckHealthIssue(
                message=f"Low interaction ({interaction} cards)",
                severity="warning",
            )
        )

    # Card draw check
    if card_draw < 5:
        score -= 10
        issues.append(
            DeckHealthIssue(
                message=f"Limited card draw ({card_draw} cards)",
                severity="warning",
            )
        )

    # Clamp score
    score = max(0, min(100, score))

    # Determine grade
    grade: GradeType
    if score >= 90:
        grade = "S"
    elif score >= 80:
        grade = "A"
    elif score >= 65:
        grade = "B"
    elif score >= 50:
        grade = "C"
    elif score >= 35:
        grade = "D"
    else:
        grade = "F"

    # Detect archetype
    archetype, confidence, traits = _detect_archetype(
        creatures=creatures,
        instants=instants,
        sorceries=sorceries,
        lands=lands,
        total_cards=total_cards,
        avg_cmc=avg_cmc,
        interaction=interaction,
        card_draw=card_draw,
    )

    # Get top keywords
    sorted_keywords = sorted(keyword_counts.items(), key=lambda x: -x[1])
    top_keywords = [KeywordCount(keyword=kw, count=count) for kw, count in sorted_keywords[:8]]

    # Build themes list (themes with at least 4 cards)
    themes: list[DeckTheme] = []
    for theme, count in theme_counts.most_common(5):
        if count >= 4:
            themes.append(
                DeckTheme(
                    name=theme,
                    card_count=count,
                    description=THEME_DESCRIPTIONS.get(theme),
                )
            )

    # Detect dominant tribe (if 4+ creatures of same type, or 20%+ of creatures)
    dominant_tribe: str | None = None
    tribal_count = 0
    if tribe_counts and creatures > 0:
        top_tribe, top_count = tribe_counts.most_common(1)[0]
        tribe_ratio = top_count / creatures
        if top_count >= 4 and tribe_ratio >= 0.4:  # At least 4 and 40% of creatures
            dominant_tribe = top_tribe
            tribal_count = top_count
            # Add tribal theme if not already present
            if not any(t.name == "Tribal" for t in themes):
                themes.insert(
                    0,
                    DeckTheme(
                        name="Tribal",
                        card_count=top_count,
                        description=f"{top_tribe} tribal - creature type synergies and lord effects",
                    ),
                )

    # Calculate matchups based on themes and archetype
    matchups = _calculate_matchups(archetype, [t.name for t in themes])

    # Detect synergy pairs between cards
    synergy_pairs = _detect_synergy_pairs(card_texts, card_keywords)

    return DeckHealthResult(
        score=score,
        grade=grade,
        archetype=archetype,
        archetype_confidence=confidence,
        total_cards=total_cards,
        expected_cards=expected_cards,
        land_count=lands,
        land_percentage=round(land_pct, 1),
        average_cmc=round(avg_cmc, 2),
        interaction_count=interaction,
        card_draw_count=card_draw,
        ramp_count=ramp_count,
        creature_count=creatures,
        instant_count=instants,
        sorcery_count=sorceries,
        artifact_count=artifacts,
        enchantment_count=enchantments,
        planeswalker_count=planeswalkers,
        top_keywords=top_keywords,
        issues=issues,
        archetype_traits=traits,
        themes=themes,
        dominant_tribe=dominant_tribe,
        tribal_count=tribal_count,
        matchups=matchups,
        synergy_pairs=synergy_pairs,
    )


def _detect_archetype(
    creatures: int,
    instants: int,
    sorceries: int,
    lands: int,
    total_cards: int,
    avg_cmc: float,
    interaction: int,
    card_draw: int,
) -> tuple[ArchetypeType, int, list[str]]:
    """Detect deck archetype based on composition."""
    spells = instants + sorceries
    nonland = total_cards - lands

    if nonland == 0:
        return "Balanced", 50, ["No non-land cards detected"]

    creature_pct = (creatures / nonland) * 100
    spell_pct = (spells / nonland) * 100

    # Aggro: High creature count, low curve
    if creature_pct > 60 and avg_cmc < 2.5:
        return (
            "Aggro",
            85,
            [
                f"High creature count ({creatures})",
                f"Low mana curve ({avg_cmc:.1f} avg)",
                "Fast clock potential",
            ],
        )

    # Creature-heavy: Lots of creatures but higher curve
    if creature_pct > 60 and avg_cmc >= 2.5:
        return (
            "Creature-heavy",
            75,
            [
                f"High creature count ({creatures})",
                f"Higher curve ({avg_cmc:.1f} avg)",
                "Value-oriented creatures",
            ],
        )

    # Control: Heavy interaction, few creatures
    if interaction > 12 and creatures < 15:
        return (
            "Control",
            80,
            [
                f"Heavy interaction ({interaction} cards)",
                f"Card advantage ({card_draw} draw)",
                f"Few threats ({creatures} creatures)",
            ],
        )

    # Spellslinger: Spell-heavy
    if spell_pct > 50:
        return (
            "Spellslinger",
            75,
            [
                f"Spell-heavy ({spells} instants/sorceries)",
                f"Few creatures ({creatures})",
                "Likely combo or storm",
            ],
        )

    # Midrange: Balanced with higher curve
    if avg_cmc > 3.0 and creatures > 15:
        return (
            "Midrange",
            70,
            [
                f"Balanced curve ({avg_cmc:.1f} avg)",
                f"Solid creature base ({creatures})",
                "Value-oriented",
            ],
        )

    # Lands Matter: Heavy land base
    if lands > 35:
        return (
            "Lands Matter",
            65,
            [
                f"Heavy land base ({lands})",
                "Land synergies likely",
            ],
        )

    # Default: Balanced
    return (
        "Balanced",
        50,
        [
            f"{creatures} creatures, {spells} spells",
            f"Average CMC: {avg_cmc:.1f}",
        ],
    )


def _calculate_matchups(
    archetype: ArchetypeType,
    theme_names: list[str],
) -> MatchupInfo:
    """Calculate deck matchups based on archetype and themes."""
    strong_against: set[str] = set()
    weak_against: set[str] = set()

    # Add archetype matchups
    if archetype in THEME_MATCHUPS:
        good, bad = THEME_MATCHUPS[archetype]
        strong_against.update(good[:2])
        weak_against.update(bad[:2])

    # Add theme matchups
    for theme in theme_names[:3]:
        if theme in THEME_MATCHUPS:
            good, bad = THEME_MATCHUPS[theme]
            strong_against.update(good[:2])
            weak_against.update(bad[:2])

    return MatchupInfo(
        strong_against=sorted(strong_against)[:4],
        weak_against=sorted(weak_against)[:4],
    )


# Synergy pattern pairs: (pattern1, pattern2, reason, category)
SYNERGY_PATTERNS: list[tuple[str, str, str, str]] = [
    # Death trigger synergies
    (r"whenever.*dies", r"sacrifice", "Death trigger + sac outlet", "Death triggers"),
    (r"when.*dies", r"sacrifice", "Death trigger + sac outlet", "Death triggers"),
    (r"whenever.*dies", r"create.*token", "Death trigger + token maker", "Death triggers"),
    # ETB synergies
    (
        r"enters the battlefield",
        r"flicker|blink|exile.*return",
        "ETB + blink effect",
        "ETB effects",
    ),
    (r"enters the battlefield", r"return.*to.*hand", "ETB + bounce for re-trigger", "ETB effects"),
    # Counter synergies
    (r"\+1/\+1 counter", r"proliferate", "Counters + proliferate", "Counters"),
    (r"\+1/\+1 counter", r"double.*counter", "Counters + doubling", "Counters"),
    # Token synergies
    (r"create.*token", r"populate", "Token maker + populate", "Tokens"),
    (r"create.*token", r"whenever.*creature.*enters", "Token maker + ETB trigger", "Tokens"),
    (r"create.*token", r"sacrifice", "Token maker + sac outlet", "Tokens"),
    # Lifegain synergies
    (r"lifelink|gain.*life", r"whenever you gain life", "Lifegain + trigger", "Lifegain"),
    (r"lifelink", r"double strike|first strike", "Lifelink + extra damage", "Lifegain"),
    # Graveyard synergies
    (r"mill|put.*graveyard", r"flashback|unearth|escape", "Self-mill + recursion", "Graveyard"),
    (r"mill|put.*graveyard", r"return.*graveyard", "Mill + reanimate", "Graveyard"),
    # Card draw synergies
    (r"draw.*card", r"whenever you draw", "Draw + draw trigger", "Card advantage"),
    (r"draw.*card", r"no maximum hand size", "Draw + no hand limit", "Card advantage"),
    # Combat synergies
    (r"flying", r"whenever.*deals combat damage", "Flying + damage trigger", "Combat"),
    (
        r"unblockable|can't be blocked",
        r"whenever.*deals combat damage",
        "Evasion + damage trigger",
        "Combat",
    ),
    (r"deathtouch", r"first strike|double strike", "Deathtouch + first strike", "Combat"),
    (r"trample", r"double.*power", "Trample + power boost", "Combat"),
]


def _detect_synergy_pairs(
    card_texts: dict[str, str],
    card_keywords: dict[str, list[str]],
) -> list[SynergyPair]:
    """Detect synergy pairs between cards in the deck."""
    synergies: list[SynergyPair] = []
    seen_pairs: set[tuple[str, str]] = set()

    def add_pair(card1: str, card2: str, reason: str, category: str) -> None:
        """Add a synergy pair if not already seen."""
        pair = (min(card1, card2), max(card1, card2))
        if pair not in seen_pairs and card1 != card2:
            seen_pairs.add(pair)
            synergies.append(
                SynergyPair(card1=card1, card2=card2, reason=reason, category=category)
            )

    card_names = list(card_texts.keys())

    # Check each pair of cards for synergy patterns
    for i, card1 in enumerate(card_names):
        text1 = card_texts[card1]
        kws1 = card_keywords.get(card1, [])
        kws1_lower = [k.lower() for k in kws1]

        for card2 in card_names[i + 1 :]:
            text2 = card_texts[card2]
            kws2 = card_keywords.get(card2, [])
            kws2_lower = [k.lower() for k in kws2]

            # Check synergy patterns
            for pattern1, pattern2, reason, category in SYNERGY_PATTERNS:
                # Check both directions (card1 has pattern1 + card2 has pattern2, or vice versa)
                match_forward = re.search(pattern1, text1, re.IGNORECASE) and re.search(
                    pattern2, text2, re.IGNORECASE
                )
                match_reverse = re.search(pattern1, text2, re.IGNORECASE) and re.search(
                    pattern2, text1, re.IGNORECASE
                )
                if match_forward or match_reverse:
                    add_pair(card1, card2, reason, category)

            # Keyword-based synergies
            if "Flying" in kws1 and any(
                re.search(r"deals combat damage", text2, re.IGNORECASE) for _ in [1]
            ):
                add_pair(card1, card2, "Flying enables combat damage", "Combat")
            if "Flying" in kws2 and any(
                re.search(r"deals combat damage", text1, re.IGNORECASE) for _ in [1]
            ):
                add_pair(card1, card2, "Flying enables combat damage", "Combat")

            # Lifelink + lifegain triggers
            if "lifelink" in kws1_lower and re.search(
                r"whenever you gain life", text2, re.IGNORECASE
            ):
                add_pair(card1, card2, "Lifelink triggers lifegain payoff", "Lifegain")
            if "lifelink" in kws2_lower and re.search(
                r"whenever you gain life", text1, re.IGNORECASE
            ):
                add_pair(card1, card2, "Lifelink triggers lifegain payoff", "Lifegain")

    # Limit to top 12 synergies
    return synergies[:12]
