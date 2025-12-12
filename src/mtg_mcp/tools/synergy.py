"""Synergy and strategy tools for MTG deck building."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from ..data.models.inputs import SearchCardsInput
from ..data.models.responses import (
    Combo,
    ComboCard,
    DetectCombosResult,
    FindSynergiesResult,
    SuggestCardsResult,
    SuggestedCard,
    SynergyResult,
    SynergyType,
)
from ..exceptions import CardNotFoundError

if TYPE_CHECKING:
    from ..data.database import MTGDatabase, ScryfallDatabase
    from ..data.models.card import Card

# Base synergy scores by match type
SYNERGY_BASE_SCORES: dict[SynergyType, float] = {
    "keyword": 0.8,
    "tribal": 0.85,
    "ability": 0.75,
    "theme": 0.7,
    "archetype": 0.65,
}

# Keyword synergies: keyword on source card -> search patterns for synergistic cards
KEYWORD_SYNERGIES: dict[str, list[tuple[str, str]]] = {
    # Combat keywords
    "Flying": [
        ("reach", "Can block flying creatures"),
        ("can block.*flying", "Anti-flying defense"),
    ],
    "Deathtouch": [
        ("first strike", "Strike first with deathtouch"),
        ("double strike", "Strike first with deathtouch"),
        ("fight", "Removal via fighting"),
        ("lure", "Force blocks with deathtouch"),
    ],
    "Lifelink": [
        ("whenever you gain life", "Life gain triggers"),
        ("life.*matters", "Life total payoffs"),
        ("pay.*life", "Offset life payment costs"),
    ],
    "Trample": [
        ("power.*greater", "Power boost synergy"),
        ("double.*power", "Double power for trample damage"),
    ],
    # Counter keywords
    "+1/+1 counter": [
        ("proliferate", "Increase counters"),
        ("Hardened Scales", "Double counters"),
        ("Doubling Season", "Double counters"),
        ("Winding Constrictor", "Extra counters"),
    ],
    "-1/-1 counter": [
        ("proliferate", "Increase counters"),
        ("Hapatra", "Snake tokens from counters"),
        ("Nest of Scarabs", "Insect tokens from counters"),
    ],
    # Evasion
    "Unblockable": [
        ("whenever.*deals combat damage", "Combat damage triggers"),
        ("Curiosity", "Draw on damage"),
        ("Sword of", "Equipment synergy"),
    ],
    "Menace": [
        ("can't block alone", "Stack blocking restrictions"),
    ],
    # Value keywords
    "Flash": [
        ("instant", "Instant speed synergy"),
        ("end step", "End step tricks"),
    ],
    "Haste": [
        ("enters the battlefield", "Immediate ETB + attack"),
        ("attack trigger", "Attack triggers immediately"),
    ],
}

# Ability text patterns: pattern on source card -> synergistic search terms
ABILITY_SYNERGIES: dict[str, list[tuple[str, str]]] = {
    # ETB effects
    "enters the battlefield": [
        ("Panharmonicon", "Double ETB triggers"),
        ("blink", "Repeat ETB effects"),
        ("flicker", "Repeat ETB effects"),
        ("return.*to.*hand", "Bounce for re-ETB"),
        ("Conjurer's Closet", "Free blink each turn"),
        ("Thassa, Deep-Dwelling", "Free blink each turn"),
    ],
    # Death triggers
    "whenever.*dies": [
        ("sacrifice", "Controlled death triggers"),
        ("Blood Artist", "Drain on death"),
        ("Zulaport Cutthroat", "Drain on death"),
        ("aristocrat", "Sacrifice synergy"),
        ("Grave Pact", "Force opponent sacrifice"),
    ],
    "when.*dies": [
        ("sacrifice", "Controlled death triggers"),
        ("reanimate", "Return after death"),
    ],
    # Card draw
    "draw.*card": [
        ("whenever you draw", "Draw triggers"),
        ("Rhystic Study", "More draw triggers"),
        ("Consecrated Sphinx", "Mass card draw"),
        ("Notion Thief", "Steal opponent draws"),
    ],
    # Cast triggers
    "whenever you cast": [
        ("storm", "Storm count builder"),
        ("magecraft", "Copy spells"),
        ("prowess", "Pump on cast"),
        ("cascade", "Free extra casts"),
    ],
    # Discard effects
    "discard": [
        ("madness", "Cast discarded cards"),
        ("Waste Not", "Value from discard"),
        ("whenever you discard", "Discard triggers"),
        ("Anje Falkenrath", "Madness commander"),
    ],
    # Graveyard
    "graveyard": [
        ("reanimate", "Return from graveyard"),
        ("flashback", "Cast from graveyard"),
        ("dredge", "Mill + return"),
        ("Meren", "Recurring graveyard value"),
    ],
    # Tokens
    "create.*token": [
        ("populate", "Copy tokens"),
        ("Doubling Season", "Double tokens"),
        ("Anointed Procession", "Double tokens"),
        ("whenever.*token.*enters", "Token ETB triggers"),
        ("Purphoros", "Damage on token creation"),
    ],
    # Counters (general)
    "counter": [
        ("proliferate", "Add more counters"),
        ("The Ozolith", "Save counters"),
    ],
    # Sacrifice
    "sacrifice": [
        ("whenever.*dies", "Death triggers"),
        ("creature dying", "Death triggers"),
        ("Grave Pact", "Force opponent sacrifice"),
        ("Blood Artist", "Drain on sacrifice"),
    ],
}

# Type-based synergies: card type -> search patterns
TYPE_SYNERGIES: dict[str, list[tuple[str, str]]] = {
    "Artifact": [
        ("artifact.*enters", "Artifact ETB triggers"),
        ("affinity", "Cost reduction"),
        ("metalcraft", "Artifact count matters"),
        ("improvise", "Tap for mana"),
        ("Urza", "Artifact synergy commander"),
    ],
    "Enchantment": [
        ("constellation", "Enchantment ETB triggers"),
        ("enchantress", "Draw on enchantment cast"),
        ("Sythis", "Enchantress value"),
        ("whenever.*enchantment", "Enchantment triggers"),
    ],
    "Instant": [
        ("magecraft", "Spell copy"),
        ("prowess", "Combat boost"),
        ("whenever you cast.*instant", "Instant triggers"),
    ],
    "Sorcery": [
        ("magecraft", "Spell copy"),
        ("prowess", "Combat boost"),
        ("flashback", "Cast again"),
    ],
    "Planeswalker": [
        ("proliferate", "Add loyalty counters"),
        ("Doubling Season", "Double loyalty"),
        ("The Chain Veil", "Extra activations"),
    ],
    "Land": [
        ("landfall", "Land ETB triggers"),
        ("whenever.*land.*enters", "Land triggers"),
        ("Azusa", "Extra land drops"),
    ],
}

KNOWN_COMBOS: list[dict[str, Any]] = [
    # 2-card infinite combos
    {
        "id": "twin",
        "cards": [
            ("Splinter Twin", "Enchant creature, tap to copy"),
            ("Deceiver Exarch", "Untap enchanted creature"),
        ],
        "type": "infinite",
        "desc": "Infinite hasty token copies",
        "colors": ["U", "R"],
    },
    {
        "id": "twin-pestermite",
        "cards": [
            ("Splinter Twin", "Enchant creature, tap to copy"),
            ("Pestermite", "Untap enchanted creature"),
        ],
        "type": "infinite",
        "desc": "Infinite hasty token copies",
        "colors": ["U", "R"],
    },
    {
        "id": "thoracle-consult",
        "cards": [
            ("Thassa's Oracle", "Win with empty library"),
            ("Demonic Consultation", "Exile library"),
        ],
        "type": "win",
        "desc": "Win the game with empty library",
        "colors": ["U", "B"],
    },
    {
        "id": "thoracle-pact",
        "cards": [
            ("Thassa's Oracle", "Win with empty library"),
            ("Tainted Pact", "Exile library"),
        ],
        "type": "win",
        "desc": "Win the game with empty library",
        "colors": ["U", "B"],
    },
    {
        "id": "niv-curiosity",
        "cards": [
            ("Niv-Mizzet, Parun", "Draw trigger deals damage"),
            ("Curiosity", "Damage trigger draws"),
        ],
        "type": "infinite",
        "desc": "Infinite draw and damage loop",
        "colors": ["U", "R"],
    },
    {
        "id": "niv-ophidian",
        "cards": [
            ("Niv-Mizzet, Parun", "Draw trigger deals damage"),
            ("Ophidian Eye", "Damage trigger draws"),
        ],
        "type": "infinite",
        "desc": "Infinite draw and damage loop",
        "colors": ["U", "R"],
    },
    {
        "id": "sanguine-exquisite",
        "cards": [
            ("Sanguine Bond", "Life gain causes life loss"),
            ("Exquisite Blood", "Life loss causes life gain"),
        ],
        "type": "infinite",
        "desc": "Infinite life drain loop",
        "colors": ["B"],
    },
    {
        "id": "kiki-conscripts",
        "cards": [
            ("Kiki-Jiki, Mirror Breaker", "Tap to copy creature"),
            ("Zealous Conscripts", "Untaps Kiki-Jiki"),
        ],
        "type": "infinite",
        "desc": "Infinite hasty tokens",
        "colors": ["R"],
    },
    {
        "id": "kiki-felidar",
        "cards": [
            ("Kiki-Jiki, Mirror Breaker", "Tap to copy creature"),
            ("Felidar Guardian", "Blinks Kiki-Jiki"),
        ],
        "type": "infinite",
        "desc": "Infinite hasty tokens",
        "colors": ["R", "W"],
    },
    {
        "id": "mike-trike",
        "cards": [
            ("Mikaeus, the Unhallowed", "Undying + buff"),
            ("Triskelion", "Damage ping + self-kill"),
        ],
        "type": "infinite",
        "desc": "Infinite damage",
        "colors": ["B"],
    },
    {
        "id": "mike-ballista",
        "cards": [
            ("Mikaeus, the Unhallowed", "Undying + buff"),
            ("Walking Ballista", "Damage ping + self-kill"),
        ],
        "type": "infinite",
        "desc": "Infinite damage",
        "colors": ["B"],
    },
    {
        "id": "dramatic-scepter",
        "cards": [
            ("Dramatic Reversal", "Untap all nonlands"),
            ("Isochron Scepter", "Imprint and repeat"),
        ],
        "type": "infinite",
        "desc": "Infinite mana (with 3+ mana from rocks)",
        "colors": ["U"],
    },
    {
        "id": "heliod-ballista",
        "cards": [
            ("Heliod, Sun-Crowned", "Gives lifelink"),
            ("Walking Ballista", "Damage + gain life"),
        ],
        "type": "infinite",
        "desc": "Infinite damage and life",
        "colors": ["W"],
    },
    {
        "id": "devoted-vizier",
        "cards": [
            ("Devoted Druid", "Untap with -1/-1"),
            ("Vizier of Remedies", "Prevents -1/-1 counters"),
        ],
        "type": "infinite",
        "desc": "Infinite green mana",
        "colors": ["G", "W"],
    },
    {
        "id": "peregrine-deadeye",
        "cards": [
            ("Peregrine Drake", "Untap 5 lands on ETB"),
            ("Deadeye Navigator", "Soulbond blink"),
        ],
        "type": "infinite",
        "desc": "Infinite mana",
        "colors": ["U"],
    },
    {
        "id": "palinchron-high-tide",
        "cards": [
            ("Palinchron", "Untap 7 lands on ETB"),
            ("High Tide", "Islands tap for extra mana"),
        ],
        "type": "infinite",
        "desc": "Infinite mana",
        "colors": ["U"],
    },
    {
        "id": "worldgorger-animate",
        "cards": [
            ("Worldgorger Dragon", "Exile all permanents"),
            ("Animate Dead", "Return and re-exile loop"),
        ],
        "type": "infinite",
        "desc": "Infinite mana and ETB triggers",
        "colors": ["B", "R"],
    },
    {
        "id": "basalt-rings",
        "cards": [
            ("Basalt Monolith", "Tap for 3, untap for 3"),
            ("Rings of Brighthearth", "Copy untap ability"),
        ],
        "type": "infinite",
        "desc": "Infinite colorless mana",
        "colors": [],
    },
    {
        "id": "food-chain-eternal",
        "cards": [
            ("Food Chain", "Exile creature for mana"),
            ("Eternal Scourge", "Cast from exile"),
        ],
        "type": "infinite",
        "desc": "Infinite creature mana",
        "colors": ["G"],
    },
    {
        "id": "food-chain-misthollow",
        "cards": [
            ("Food Chain", "Exile creature for mana"),
            ("Misthollow Griffin", "Cast from exile"),
        ],
        "type": "infinite",
        "desc": "Infinite creature mana",
        "colors": ["G", "U"],
    },
    # 2-card value/lock combos
    {
        "id": "teferi-knowledge",
        "cards": [
            ("Teferi, Time Raveler", "Opponents cast at sorcery only"),
            ("Knowledge Pool", "Exile and swap spells"),
        ],
        "type": "lock",
        "desc": "Opponents can't cast spells",
        "colors": ["W", "U"],
    },
    {
        "id": "drannith-knowledge",
        "cards": [
            ("Drannith Magistrate", "Can't cast from non-hand"),
            ("Knowledge Pool", "Exile and swap spells"),
        ],
        "type": "lock",
        "desc": "Opponents can't cast spells",
        "colors": ["W"],
    },
    {
        "id": "narset-wheels",
        "cards": [
            ("Narset, Parter of Veils", "Opponents draw only 1"),
            ("Windfall", "Everyone discards and draws"),
        ],
        "type": "value",
        "desc": "One-sided hand refill",
        "colors": ["U"],
    },
    {
        "id": "notion-wheels",
        "cards": [
            ("Notion Thief", "Steal opponent draws"),
            ("Windfall", "Everyone draws = you draw all"),
        ],
        "type": "value",
        "desc": "Draw everyone's cards",
        "colors": ["U", "B"],
    },
    {
        "id": "dauthi-thoracle",
        "cards": [
            ("Dauthi Voidwalker", "Exile opponents' cards"),
            ("Opposition Agent", "Steal tutored cards"),
        ],
        "type": "value",
        "desc": "Deny all opponent resources",
        "colors": ["B"],
    },
]

THEME_INDICATORS: dict[str, list[str]] = {
    "tokens": ["create.*token", "populate", "whenever.*enters", "token creature"],
    "aristocrats": ["sacrifice", "whenever.*dies", "blood artist", "zulaport"],
    "reanimator": ["graveyard", "return.*battlefield", "reanimate", "unearth"],
    "spellslinger": ["instant", "sorcery", "magecraft", "prowess", "storm"],
    "voltron": ["equipment", "aura", "attach", "equipped creature"],
    "stax": ["sacrifice.*permanent", "each player", "can't", "opponent.*can't"],
    "landfall": ["land.*enters", "landfall", "play.*additional land"],
    "blink": ["exile.*return", "flicker", "enters the battlefield"],
    "counters": ["+1/+1 counter", "proliferate", "counter.*creature"],
    "tribal": [],  # Detected separately via subtype concentration
    "graveyard": ["mill", "graveyard", "from.*graveyard", "self-mill"],
    "artifacts": ["artifact.*enters", "metalcraft", "affinity", "improvise"],
    "enchantress": ["enchantment", "constellation", "whenever.*enchantment"],
    "control": ["counterspell", "counter target", "destroy.*permanent"],
    "aggro": ["haste", "attack", "combat damage", "first strike"],
}


def _normalize_card_name(name: str) -> str:
    """Normalize card name for comparison."""
    return name.lower().strip()


def _card_has_pattern(card: Card, pattern: str) -> bool:
    """Check if card text matches a pattern (case-insensitive)."""
    if not card.text:
        return False
    try:
        return bool(re.search(pattern, card.text, re.IGNORECASE))
    except re.error:
        # Invalid regex, fall back to substring search
        return pattern.lower() in card.text.lower()


def _calculate_synergy_score(
    card: Card,
    source_card: Card,
    synergy_type: SynergyType,
) -> float:
    """Calculate synergy score with bonuses for color match."""
    base = SYNERGY_BASE_SCORES.get(synergy_type, 0.5)

    # Color identity overlap bonus
    if card.color_identity and source_card.color_identity:
        overlap = set(card.color_identity) & set(source_card.color_identity)
        if overlap:
            base += 0.1 * len(overlap) / max(
                len(source_card.color_identity), 1
            )

    return min(base, 1.0)


async def _search_synergies(
    db: MTGDatabase,
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
        search_terms: List of (search_text, reason) tuples
        synergy_type: Type of synergy for scoring
        seen_names: Set of already-seen card names (will be modified)
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
            normalized = _normalize_card_name(card.name)
            if normalized not in seen_names:
                seen_names.add(normalized)
                score = _calculate_synergy_score(card, source_card, synergy_type)
                results.append(
                    SynergyResult(
                        name=card.name,
                        synergy_type=synergy_type,
                        reason=reason,
                        score=score * score_modifier,
                        mana_cost=card.mana_cost,
                        type_line=card.type,
                    )
                )

    return results


def _combo_to_model(combo_data: dict[str, Any]) -> Combo:
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


def _detect_themes(cards: list[Card]) -> list[str]:
    """Detect deck themes from card texts."""
    theme_scores: dict[str, int] = dict.fromkeys(THEME_INDICATORS, 0)

    # Check each card against theme indicators
    for card in cards:
        if not card.text:
            continue

        card_text_lower = card.text.lower()
        for theme, patterns in THEME_INDICATORS.items():
            for pattern in patterns:
                # Try regex first, fall back to substring
                try:
                    if re.search(pattern, card_text_lower, re.IGNORECASE):
                        theme_scores[theme] += 1
                        break  # Only count each card once per theme
                except re.error:
                    if pattern.lower() in card_text_lower:
                        theme_scores[theme] += 1
                        break

    # Detect tribal theme via subtype concentration
    subtype_counts: dict[str, int] = {}
    for card in cards:
        if card.subtypes:
            for subtype in card.subtypes:
                subtype_counts[subtype] = subtype_counts.get(subtype, 0) + 1

    # If any subtype has 5+ cards, it's tribal
    for _subtype, count in subtype_counts.items():
        if count >= 5:
            theme_scores["tribal"] += count

    # Return themes with 3+ indicators
    return [theme for theme, score in theme_scores.items() if score >= 3]


def _detect_deck_colors(cards: list[Card]) -> list[str]:
    """Detect deck colors from card color identities."""
    colors: set[str] = set()
    for card in cards:
        if card.color_identity:
            colors.update(card.color_identity)

    # Return in WUBRG order
    color_order = ["W", "U", "B", "R", "G"]
    return [c for c in color_order if c in colors]


async def find_synergies(
    db: MTGDatabase,
    card_name: str,
    max_results: int = 20,
    format_legal: str | None = None,
) -> FindSynergiesResult:
    """Find cards that synergize with a given card."""
    source_card = await db.get_card_by_name(card_name)
    if not source_card:
        raise CardNotFoundError(f"Card not found: {card_name}")

    synergies: list[SynergyResult] = []
    seen_names: set[str] = {_normalize_card_name(source_card.name)}
    color_identity = source_card.color_identity or None

    # Pass 1: Keyword synergies
    if source_card.keywords:
        for keyword in source_card.keywords:
            if keyword in KEYWORD_SYNERGIES:
                terms = [(t, f"{keyword}: {r}") for t, r in KEYWORD_SYNERGIES[keyword]]
                synergies.extend(
                    await _search_synergies(
                        db, source_card, terms, "keyword",
                        seen_names, color_identity, format_legal,
                    )
                )

    # Pass 2: Tribal synergies
    skip_subtypes = {"human", "warrior", "wizard", "soldier", "cleric"}
    if source_card.subtypes:
        for subtype in source_card.subtypes:
            if subtype.lower() in skip_subtypes:
                continue
            # Cards mentioning this subtype
            synergies.extend(
                await _search_synergies(
                    db, source_card,
                    [(subtype, f"Synergizes with {subtype}s")],
                    "tribal", seen_names, color_identity, format_legal, page_size=15,
                )
            )
            # Cards of same subtype (lower score)
            cards, _ = await db.search_cards(
                SearchCardsInput(
                    subtype=subtype,
                    color_identity=color_identity,  # type: ignore[arg-type]
                    format_legal=format_legal,  # type: ignore[arg-type]
                    page_size=10,
                )
            )
            for card in cards:
                normalized = _normalize_card_name(card.name)
                if normalized not in seen_names:
                    seen_names.add(normalized)
                    synergies.append(
                        SynergyResult(
                            name=card.name,
                            synergy_type="tribal",
                            reason=f"Fellow {subtype}",
                            score=_calculate_synergy_score(card, source_card, "tribal") * 0.9,
                            mana_cost=card.mana_cost,
                            type_line=card.type,
                        )
                    )

    # Pass 3: Ability text synergies
    if source_card.text:
        for pattern, search_terms in ABILITY_SYNERGIES.items():
            if _card_has_pattern(source_card, pattern):
                synergies.extend(
                    await _search_synergies(
                        db, source_card, search_terms, "ability",
                        seen_names, color_identity, format_legal, page_size=8,
                    )
                )

    # Pass 4: Type synergies
    if source_card.types:
        for card_type in source_card.types:
            if card_type in TYPE_SYNERGIES:
                terms = [(t, f"{card_type}: {r}") for t, r in TYPE_SYNERGIES[card_type]]
                synergies.extend(
                    await _search_synergies(
                        db, source_card, terms, "theme",
                        seen_names, color_identity, format_legal, page_size=8,
                    )
                )

    synergies.sort(key=lambda s: s.score, reverse=True)
    synergies = synergies[:max_results]

    return FindSynergiesResult(
        card_name=source_card.name,
        synergies=synergies,
    )


async def detect_combos(
    db: MTGDatabase,  # noqa: ARG001 - kept for API consistency
    card_name: str | None = None,
    deck_cards: list[str] | None = None,
) -> DetectCombosResult:
    """Detect known combos in a deck or for a specific card.

    If card_name is provided, finds all combos involving that card.
    If deck_cards is provided, finds complete and potential combos in the deck.
    """
    if card_name:
        # Find combos involving this specific card
        card_name_lower = _normalize_card_name(card_name)
        found_combos: list[Combo] = []

        for combo_data in KNOWN_COMBOS:
            combo_card_names = [
                _normalize_card_name(c[0] if isinstance(c, tuple) else c)
                for c in combo_data["cards"]
            ]
            if card_name_lower in combo_card_names:
                found_combos.append(_combo_to_model(combo_data))

        return DetectCombosResult(
            combos=found_combos,
            potential_combos=[],
            missing_cards={},
        )

    if deck_cards:
        # Check deck against known combos
        deck_card_names = {_normalize_card_name(c) for c in deck_cards}
        found_combos = []
        potential_combos = []
        missing_cards: dict[str, list[str]] = {}

        for combo_data in KNOWN_COMBOS:
            combo_card_names = [
                _normalize_card_name(c[0] if isinstance(c, tuple) else c)
                for c in combo_data["cards"]
            ]
            combo_card_originals = [
                c[0] if isinstance(c, tuple) else c for c in combo_data["cards"]
            ]

            present = set(combo_card_names) & deck_card_names
            missing = set(combo_card_names) - deck_card_names

            if not missing:
                # Complete combo found
                found_combos.append(_combo_to_model(combo_data))
            elif len(missing) <= 2 and len(present) >= 1:
                # Potential combo - missing 1-2 pieces
                combo = _combo_to_model(combo_data)
                potential_combos.append(combo)
                # Find original names for missing cards
                missing_originals = [
                    orig
                    for orig, norm in zip(
                        combo_card_originals, combo_card_names, strict=True
                    )
                    if norm in missing
                ]
                missing_cards[combo_data["id"]] = missing_originals

        return DetectCombosResult(
            combos=found_combos,
            potential_combos=potential_combos,
            missing_cards=missing_cards,
        )

    # Neither provided
    return DetectCombosResult(
        combos=[],
        potential_combos=[],
        missing_cards={},
    )


async def suggest_cards(
    db: MTGDatabase,
    scryfall: ScryfallDatabase | None,
    deck_cards: list[str],
    format_legal: str | None = None,
    budget_max: float | None = None,
    max_results: int = 10,
) -> SuggestCardsResult:
    """Suggest cards to add to a deck based on themes and synergies.

    Analyzes the deck to detect themes, then suggests cards that fit.
    """
    # Resolve deck cards to Card objects
    resolved_cards: list[Card] = []
    deck_card_names_lower: set[str] = set()

    for card_name in deck_cards:
        try:
            card = await db.get_card_by_name(card_name)
            if card:
                resolved_cards.append(card)
                deck_card_names_lower.add(_normalize_card_name(card.name))
        except CardNotFoundError:
            continue

    if not resolved_cards:
        return SuggestCardsResult(
            suggestions=[],
            detected_themes=[],
            deck_colors=[],
        )

    # Detect themes and colors
    detected_themes = _detect_themes(resolved_cards)
    deck_colors = _detect_deck_colors(resolved_cards)

    suggestions: list[SuggestedCard] = []
    seen_names: set[str] = deck_card_names_lower.copy()

    # Search for cards matching each detected theme
    for theme in detected_themes[:3]:  # Limit to top 3 themes
        if theme not in THEME_INDICATORS or not THEME_INDICATORS[theme]:
            continue

        # Use first indicator as search term
        search_term = THEME_INDICATORS[theme][0]

        results, _ = await db.search_cards(
            SearchCardsInput(
                text=search_term,
                color_identity=deck_colors if deck_colors else None,  # type: ignore[arg-type]
                format_legal=format_legal,  # type: ignore[arg-type]
                page_size=20,
            )
        )

        for card in results:
            if _normalize_card_name(card.name) in seen_names:
                continue
            seen_names.add(_normalize_card_name(card.name))

            # Get price if Scryfall available
            price_usd: float | None = None
            if scryfall:
                try:
                    image_data = await scryfall.get_card_image(card.name)
                    if image_data:
                        price_usd = image_data.get_price_usd()
                except Exception:
                    pass

            # Apply budget filter
            if (
                budget_max is not None
                and price_usd is not None
                and price_usd > budget_max
            ):
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

            if len(suggestions) >= max_results:
                break

        if len(suggestions) >= max_results:
            break

    # If we don't have enough suggestions, add some staples based on colors
    if len(suggestions) < max_results and deck_colors:
        # Search for popular cards in the deck's colors
        staple_searches = [
            ("draw.*card", "Card advantage staple"),
            ("destroy.*target", "Removal staple"),
            ("add.*mana", "Ramp staple"),
        ]

        for search_term, reason in staple_searches:
            if len(suggestions) >= max_results:
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
                if _normalize_card_name(card.name) in seen_names:
                    continue
                seen_names.add(_normalize_card_name(card.name))

                price_usd = None
                if scryfall:
                    try:
                        image_data = await scryfall.get_card_image(card.name)
                        if image_data:
                            price_usd = image_data.get_price_usd()
                    except Exception:
                        pass

                if (
                    budget_max is not None
                    and price_usd is not None
                    and price_usd > budget_max
                ):
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

                if len(suggestions) >= max_results:
                    break

    return SuggestCardsResult(
        suggestions=suggestions[:max_results],
        detected_themes=detected_themes,
        deck_colors=deck_colors,
    )
