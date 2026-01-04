"""Set analysis tools for extracting insights from MTG sets.

Provides value summaries, mechanic detection, tribal themes, and type distribution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mtg_core.data.database import UnifiedDatabase


@dataclass
class PriceTierBreakdown:
    """Price tier distribution."""

    bulk: int  # $0-1
    playable: int  # $1-10
    chase: int  # $10-50
    premium: int  # $50+


@dataclass
class SetValueSummary:
    """Price/value summary for a set."""

    total_value: float  # Regular prices
    total_value_foil: float  # Best prices (regular or foil)
    average_value: float
    median_value: float
    chase_card_count: int  # Cards > $10
    top_cards: list[tuple[str, float, bool]]  # (name, price, is_foil) sorted by price desc
    top5_concentration: float  # Top 5 cards as % of total value
    price_tiers: PriceTierBreakdown


@dataclass
class MechanicInfo:
    """Information about a mechanic in a set."""

    name: str
    card_count: int
    description: str
    top_cards: list[str]


@dataclass
class TribalTheme:
    """Tribal theme info for a set."""

    creature_type: str
    card_count: int
    percentage: float  # Of total creatures


@dataclass
class TypeDistribution:
    """Card type distribution in a set."""

    creatures: int
    instants: int
    sorceries: int
    enchantments: int
    artifacts: int
    lands: int
    planeswalkers: int
    battles: int
    other: int


@dataclass
class RarityDistribution:
    """Rarity distribution in a set."""

    mythic: int
    rare: int
    uncommon: int
    common: int
    special: int


@dataclass
class LimitedCardStat:
    """Limited stats for a single card."""

    card_name: str
    tier: str  # S/A/B/C/D/F
    gih_wr: float  # Games in Hand Win Rate (0.0-1.0)
    games: int


@dataclass
class LimitedTierSummary:
    """Summary of cards by tier for Limited play."""

    s_tier: list[LimitedCardStat]
    a_tier: list[LimitedCardStat]
    b_tier: list[LimitedCardStat]
    c_tier_count: int
    d_tier_count: int
    f_tier_count: int
    has_data: bool = True


@dataclass
class SetAnalysis:
    """Complete analysis of a set."""

    set_code: str
    set_name: str
    total_cards: int
    value_summary: SetValueSummary
    mechanics: list[MechanicInfo]
    tribal_themes: list[TribalTheme]
    type_distribution: TypeDistribution
    rarity_distribution: RarityDistribution
    limited_stats: LimitedTierSummary | None = None


# Mechanic patterns for detection
# Format: (pattern_regex, display_name, description)
MECHANIC_PATTERNS: list[tuple[str, str, str]] = [
    # Recent set mechanics
    (r"\bOffspring\b", "Offspring", "Pay extra to create a 1/1 token copy"),
    (r"\bGift\b", "Gift", "Give opponent a benefit for a bigger effect"),
    (r"\bForage\b", "Forage", "Exile from graveyard for benefits"),
    (r"\bValiant\b", "Valiant", "Triggers when targeted by your spell"),
    (r"\bPlot\b", "Plot", "Exile and cast later for free"),
    (r"\bSpree\b", "Spree", "Choose modes by paying additional costs"),
    (r"\bSaddle \d+", "Saddle", "Tap creatures to let this attack"),
    (r"\bDisguise\b", "Disguise", "Play face-down with ward 2"),
    (r"\bCloak\b", "Cloak", "Put card face-down as creature"),
    (r"\bCollect evidence \d+", "Collect Evidence", "Exile cards totaling N mana value"),
    (r"\bSuspect\b", "Suspect", "Has menace, can't block"),
    (r"\bDiscover \d+", "Discover", "Exile until CMC ≤ N, cast free or draw"),
    (r"\bExplore\b", "Explore", "Reveal top card: land to hand, else +1/+1"),
    (r"\bCraft with", "Craft", "Transform by exiling materials"),
    (r"\bDescend \d+", "Descend", "Count permanents in graveyard"),
    (r"\bFinality counter", "Finality", "Can't return from graveyard"),
    (r"\bIncubate \d+", "Incubate", "Create Incubator token"),
    (r"\bBackup \d+", "Backup", "Put counters on target, share abilities"),
    (r"\bBattle\b.*\bSiege\b", "Battles", "New card type - attack to flip"),
    (r"\bTransform\b", "Transform", "Double-faced card flip"),
    (r"\bPrototype\b", "Prototype", "Cast cheaper with reduced stats"),
    (r"\bUnearth\b", "Unearth", "Return from graveyard, exile at end"),
    (r"\bPowerstone\b", "Powerstones", "Artifact mana (not for non-artifacts)"),
    (r"\bRavenous\b", "Ravenous", "Enters with X +1/+1 counters, draw if X≥5"),
    (r"\bEnlist\b", "Enlist", "Tap creature to add its power"),
    (r"\bRead ahead\b", "Read Ahead", "Start Saga on any chapter"),
    (r"\bDomain\b", "Domain", "Count basic land types"),
    (r"\bBlitz\b", "Blitz", "Haste, draw when dies, sacrifice at end"),
    (r"\bCasualty \d+", "Casualty", "Sacrifice creature to copy"),
    (r"\bConnive\b", "Connive", "Draw, discard, maybe +1/+1"),
    (r"\bHideaway\b", "Hideaway", "Exile cards face-down to cast later"),
    (r"\bAlliance\b", "Alliance", "Triggers when creature ETBs"),
    # Evergreen and deciduous
    (r"\bFlash\b", "Flash", "Cast any time you could cast an instant"),
    (r"\bFlying\b", "Flying", "Can only be blocked by fliers/reach"),
    (r"\bLifelink\b", "Lifelink", "Damage also gains you life"),
    (r"\bDeathtouch\b", "Deathtouch", "Any damage destroys creature"),
    (r"\bTrample\b", "Trample", "Excess damage goes to player"),
    (r"\bFirst strike\b", "First Strike", "Deals combat damage first"),
    (r"\bDouble strike\b", "Double Strike", "Deals first strike and normal damage"),
    (r"\bVigilance\b", "Vigilance", "Doesn't tap to attack"),
    (r"\bHaste\b", "Haste", "Can attack/tap immediately"),
    (r"\bReach\b", "Reach", "Can block flying creatures"),
    (r"\bMenace\b", "Menace", "Must be blocked by 2+ creatures"),
    (r"\bHexproof\b", "Hexproof", "Can't be targeted by opponents"),
    (r"\bIndestructible\b", "Indestructible", "Can't be destroyed"),
    (r"\bWard\b", "Ward", "Counter spell unless cost paid"),
]


async def analyze_set(db: UnifiedDatabase, set_code: str) -> SetAnalysis | None:
    """Perform complete analysis of a set.

    Returns None if set not found.
    """
    # Get set info
    set_info = await db.get_set(set_code)
    if not set_info:
        return None

    # Get all cards in the set (paginate since page_size max is 100)
    from mtg_core.data.models.inputs import SearchCardsInput

    all_cards: list[Any] = []
    page = 1
    while True:
        filters = SearchCardsInput(set_code=set_code, page_size=100, page=page)
        cards, _total = await db.search_cards(filters)
        if not cards:
            break
        all_cards.extend(cards)
        if len(cards) < 100:
            break
        page += 1

    if not all_cards:
        return None

    cards = all_cards

    # Calculate value summary
    value_summary = _calculate_value_summary(cards)

    # Detect mechanics
    mechanics = _detect_mechanics(cards)

    # Analyze tribal themes
    tribal_themes = _analyze_tribal_themes(cards)

    # Type distribution
    type_dist = _analyze_type_distribution(cards)

    # Rarity distribution
    rarity_dist = _analyze_rarity_distribution(cards)

    # Get limited stats (if available)
    limited_stats = _get_limited_stats(set_code)

    return SetAnalysis(
        set_code=set_code.upper(),
        set_name=set_info.name,
        total_cards=len(cards),
        value_summary=value_summary,
        mechanics=mechanics,
        tribal_themes=tribal_themes,
        type_distribution=type_dist,
        rarity_distribution=rarity_dist,
        limited_stats=limited_stats,
    )


def _calculate_value_summary(cards: list[Any]) -> SetValueSummary:
    """Calculate price/value summary for cards.

    Uses the best price (regular or foil) for top cards display,
    but regular prices for total/average/median calculations.
    """
    regular_prices: list[tuple[str, float]] = []
    best_prices: list[tuple[str, float, bool]] = []  # (name, price, is_foil)

    for card in cards:
        # Get both regular and foil prices
        price = card.get_price_usd() if hasattr(card, "get_price_usd") else None
        foil = card.get_price_usd_foil() if hasattr(card, "get_price_usd_foil") else None

        # Track regular price for totals
        if price and price > 0:
            regular_prices.append((card.name, price))

        # Track best price (regular or foil) for top cards
        if price and foil:
            if foil > price:
                best_prices.append((card.name, foil, True))
            else:
                best_prices.append((card.name, price, False))
        elif foil and foil > 0:
            best_prices.append((card.name, foil, True))
        elif price and price > 0:
            best_prices.append((card.name, price, False))

    if not regular_prices and not best_prices:
        return SetValueSummary(
            total_value=0,
            total_value_foil=0,
            average_value=0,
            median_value=0,
            chase_card_count=0,
            top_cards=[],
            top5_concentration=0,
            price_tiers=PriceTierBreakdown(bulk=0, playable=0, chase=0, premium=0),
        )

    # Sort best prices by price descending for top cards
    best_prices.sort(key=lambda x: x[1], reverse=True)

    # Calculate both totals
    regular_price_values = [p[1] for p in regular_prices]
    best_price_values = [p[1] for p in best_prices]

    total_regular = sum(regular_price_values) if regular_price_values else 0
    total_best = sum(best_price_values) if best_price_values else 0

    # Use regular prices for average/median (base set value)
    avg = total_regular / len(regular_price_values) if regular_price_values else 0

    # Median (regular prices)
    if regular_price_values:
        sorted_prices = sorted(regular_price_values)
        mid = len(sorted_prices) // 2
        if len(sorted_prices) % 2 == 0:
            median = (sorted_prices[mid - 1] + sorted_prices[mid]) / 2
        else:
            median = sorted_prices[mid]
    else:
        median = 0

    # Chase cards (> $10) - based on best price
    chase_count = sum(1 for p in best_price_values if p > 10)

    # Top 5 concentration (best prices as % of best total)
    top5_value = sum(p for _, p, _ in best_prices[:5])
    top5_pct = (top5_value / total_best * 100) if total_best > 0 else 0

    # Price tier breakdown (based on best prices - regular or foil)
    tier_bulk = 0  # $0-1
    tier_playable = 0  # $1-10
    tier_chase = 0  # $10-50
    tier_premium = 0  # $50+

    for p in best_price_values:
        if p < 1:
            tier_bulk += 1
        elif p < 10:
            tier_playable += 1
        elif p < 50:
            tier_chase += 1
        else:
            tier_premium += 1

    return SetValueSummary(
        total_value=total_regular,
        total_value_foil=total_best,
        average_value=avg,
        median_value=median,
        chase_card_count=chase_count,
        top_cards=best_prices[:10],  # Top 10 by best price
        top5_concentration=top5_pct,
        price_tiers=PriceTierBreakdown(
            bulk=tier_bulk,
            playable=tier_playable,
            chase=tier_chase,
            premium=tier_premium,
        ),
    )


def _detect_mechanics(cards: list[Any]) -> list[MechanicInfo]:
    """Detect mechanics present in set."""
    mechanic_cards: dict[str, list[str]] = {}

    for card in cards:
        text = getattr(card, "text", "") or ""
        keywords = getattr(card, "keywords", None)
        if keywords:
            if isinstance(keywords, list):
                text += " " + " ".join(keywords)
            else:
                text += " " + str(keywords)

        for pattern, name, _desc in MECHANIC_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                if name not in mechanic_cards:
                    mechanic_cards[name] = []
                if card.name not in mechanic_cards[name]:
                    mechanic_cards[name].append(card.name)

    # Build result sorted by count
    results = []
    for name, card_names in mechanic_cards.items():
        # Find description
        desc = next(
            (d for p, n, d in MECHANIC_PATTERNS if n == name),
            "",
        )
        results.append(
            MechanicInfo(
                name=name,
                card_count=len(card_names),
                description=desc,
                top_cards=card_names[:5],
            )
        )

    # Sort by count descending, filter to significant (2+ cards for non-evergreen)
    results.sort(key=lambda x: x.card_count, reverse=True)

    # Filter: keep set-specific mechanics (those with 2+ cards) or evergreen with 5+
    evergreen = {
        "Flying",
        "Lifelink",
        "Deathtouch",
        "Trample",
        "First Strike",
        "Double Strike",
        "Vigilance",
        "Haste",
        "Reach",
        "Menace",
        "Hexproof",
        "Indestructible",
        "Flash",
    }

    filtered = []
    for m in results:
        if m.name in evergreen:
            if m.card_count >= 5:
                filtered.append(m)
        elif m.card_count >= 2:
            filtered.append(m)

    return filtered[:15]  # Top 15 mechanics


def _analyze_tribal_themes(cards: list[Any]) -> list[TribalTheme]:
    """Analyze creature type distribution."""
    type_counts: dict[str, int] = {}
    total_creatures = 0

    for card in cards:
        type_line = getattr(card, "type", "") or ""

        if "Creature" not in type_line and "Tribal" not in type_line:
            continue

        total_creatures += 1

        # Extract subtypes (after the dash)
        if "—" in type_line:
            subtypes = type_line.split("—")[1].strip()
            for subtype in subtypes.split():
                # Skip generic types
                if subtype.lower() in ("the", "of", "and"):
                    continue
                type_counts[subtype] = type_counts.get(subtype, 0) + 1
        elif " — " in type_line:
            subtypes = type_line.split(" — ")[1].strip()
            for subtype in subtypes.split():
                if subtype.lower() in ("the", "of", "and"):
                    continue
                type_counts[subtype] = type_counts.get(subtype, 0) + 1

    if total_creatures == 0:
        return []

    # Build results
    results = []
    for creature_type, count in type_counts.items():
        if count >= 2:  # At least 2 cards
            results.append(
                TribalTheme(
                    creature_type=creature_type,
                    card_count=count,
                    percentage=(count / total_creatures) * 100,
                )
            )

    # Sort by count descending
    results.sort(key=lambda x: x.card_count, reverse=True)
    return results[:12]  # Top 12 types


def _analyze_type_distribution(cards: list[Any]) -> TypeDistribution:
    """Analyze card type distribution."""
    counts = {
        "creatures": 0,
        "instants": 0,
        "sorceries": 0,
        "enchantments": 0,
        "artifacts": 0,
        "lands": 0,
        "planeswalkers": 0,
        "battles": 0,
        "other": 0,
    }

    for card in cards:
        type_line = (getattr(card, "type", "") or "").lower()

        if "creature" in type_line:
            counts["creatures"] += 1
        elif "instant" in type_line:
            counts["instants"] += 1
        elif "sorcery" in type_line:
            counts["sorceries"] += 1
        elif "enchantment" in type_line:
            counts["enchantments"] += 1
        elif "artifact" in type_line:
            counts["artifacts"] += 1
        elif "land" in type_line:
            counts["lands"] += 1
        elif "planeswalker" in type_line:
            counts["planeswalkers"] += 1
        elif "battle" in type_line:
            counts["battles"] += 1
        else:
            counts["other"] += 1

    return TypeDistribution(**counts)


def _analyze_rarity_distribution(cards: list[Any]) -> RarityDistribution:
    """Analyze rarity distribution."""
    counts = {
        "mythic": 0,
        "rare": 0,
        "uncommon": 0,
        "common": 0,
        "special": 0,
    }

    for card in cards:
        rarity = (getattr(card, "rarity", "") or "").lower()
        if rarity in counts:
            counts[rarity] += 1
        elif rarity in ("bonus", "special"):
            counts["special"] += 1

    return RarityDistribution(**counts)


def _get_limited_stats(set_code: str) -> LimitedTierSummary | None:
    """Get limited stats for a set from 17Lands data.

    Returns None if no data available.
    """
    try:
        from mtg_core.tools.recommendations.gameplay import get_gameplay_db

        db = get_gameplay_db()
        if not db.is_available:
            return None

        db.connect()

        # Get top cards by tier
        all_stats = db.get_top_cards(set_code=set_code, limit=200)

        if not all_stats:
            db.close()
            return None

        # Organize by tier
        s_tier: list[LimitedCardStat] = []
        a_tier: list[LimitedCardStat] = []
        b_tier: list[LimitedCardStat] = []
        c_count = 0
        d_count = 0
        f_count = 0

        for stat in all_stats:
            card_stat = LimitedCardStat(
                card_name=stat.card_name,
                tier=stat.tier,
                gih_wr=stat.gih_wr or 0.0,
                games=stat.games_in_hand,
            )

            if stat.tier == "S":
                s_tier.append(card_stat)
            elif stat.tier == "A":
                a_tier.append(card_stat)
            elif stat.tier == "B":
                b_tier.append(card_stat)
            elif stat.tier == "C":
                c_count += 1
            elif stat.tier == "D":
                d_count += 1
            elif stat.tier == "F":
                f_count += 1

        db.close()

        # Limit displayed cards (show top 5 for S/A, top 10 for B)
        return LimitedTierSummary(
            s_tier=s_tier[:5],
            a_tier=a_tier[:8],
            b_tier=b_tier[:5],
            c_tier_count=c_count,
            d_tier_count=d_count,
            f_tier_count=f_count,
            has_data=True,
        )

    except Exception:
        return None
