"""Deck recommendations based on user's collection.

Analyzes a user's collection to suggest deck archetypes they can build
for Commander and Standard formats.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import TYPE_CHECKING, Any

from .constants import (
    ARCHETYPE_WEIGHTS,
    BASIC_LAND_NAMES,
    COLOR_FIXING_REQUIREMENTS,
    DECK_TARGETS,
    THEME_FILTER_MINIMUM,
    THEME_KEYWORDS,
    TRIBAL_FILTER_MINIMUM,
    TRIBAL_TYPES,
)
from .excluded_sets import is_excluded_set
from .features import CardEncoder, DeckEncoder, DeckFeatures
from .gameplay import GameplayDB, get_gameplay_db
from .hybrid import SynergyScorer
from .models import (
    CardData,
    ComboSummary,
    CommanderMatch,
    DeckFilters,
    DeckSuggestion,
    FilterResult,
)
from .scoring import (
    calculate_commander_total_score,
    generate_commander_reasons,
    score_card_for_deck,
    score_commander_combos,
    score_commander_synergy,
    score_edhrec_rank,
    score_limited_for_commander,
    score_limited_stats,
    score_theme_match,
)
from .smart_suggestions import SmartSuggestionEngine, get_smart_engine
from .validators import (
    assess_theme_strength,
    assess_tribal_strength,
    count_card_advantage,
    count_color_sources,
    count_fixing_lands,
    count_interaction,
    count_ramp_sources,
    count_tribal_lords,
    detect_win_conditions,
    validate_card_advantage,
    validate_interaction_density,
    validate_mana_base,
    validate_mana_curve,
    validate_ramp_sufficiency,
    validate_win_conditions,
)

if TYPE_CHECKING:
    from mtg_core.data.database import UnifiedDatabase

logger = logging.getLogger(__name__)


def _pre_filter_cards(
    cards: list[CardData],
    commanders: list[CardData],
    filters: DeckFilters | None,
) -> FilterResult:
    """Centralized pre-filtering of cards at start of suggestion generation.

    Applies all active filters and generates filter_reasons for matching suggestions.
    Enforces minimums: 5+ creatures for tribal, 3+ cards for theme.
    """
    result = FilterResult(cards=list(cards), commanders=list(commanders))

    if not filters:
        return result

    # === COLOR FILTER ===
    if filters.colors:
        filter_color_set = set(filters.colors)

        # Filter commanders: identity must INTERSECT with filter colors
        result.commanders = [
            cmd
            for cmd in result.commanders
            if not cmd.get_color_identity()
            or set(cmd.get_color_identity()).intersection(filter_color_set)
        ]

        # Filter cards: identity must be SUBSET of filter colors
        result.cards = [
            card
            for card in result.cards
            if not card.get_color_identity()
            or set(card.get_color_identity()).issubset(filter_color_set)
        ]

        color_names = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}
        color_str = "/".join(color_names.get(c, c) for c in sorted(filters.colors))
        result.filter_reasons.append(f"Matches {color_str} colors")

    # === TRIBAL FILTER ===
    if filters.creature_type:
        tribal_lower = filters.creature_type.lower()

        # Count creatures of this type
        tribal_creatures = [
            card
            for card in result.cards
            if card.type_line
            and "creature" in card.type_line.lower()
            and (
                tribal_lower in card.type_line.lower()
                or (card.subtypes and any(tribal_lower == s.lower() for s in card.subtypes))
            )
        ]
        result.tribal_count = len(tribal_creatures)

        if result.tribal_count < TRIBAL_FILTER_MINIMUM:
            result.meets_tribal_minimum = False
        else:
            result.filter_reasons.append(
                f"Has {result.tribal_count} {filters.creature_type} creatures"
            )

    # === THEME FILTER ===
    if filters.theme and filters.theme in THEME_KEYWORDS:
        theme_keywords = THEME_KEYWORDS[filters.theme]

        # Count cards supporting this theme
        theme_cards = [
            card
            for card in result.cards
            if card.text and any(kw.lower() in card.text.lower() for kw in theme_keywords)
        ]
        result.theme_count = len(theme_cards)

        if result.theme_count < THEME_FILTER_MINIMUM:
            result.meets_theme_minimum = False
        else:
            result.filter_reasons.append(
                f"Has {result.theme_count} cards supporting {filters.theme}"
            )

    # === KEYWORD FILTER ===
    if filters.keyword:
        keyword_lower = filters.keyword.lower()

        result.cards = [
            card
            for card in result.cards
            if (card.text and keyword_lower in card.text.lower())
            or (card.type_line and keyword_lower in card.type_line.lower())
        ]

        result.filter_reasons.append(f"Contains '{filters.keyword}'")

    # === SET FILTER ===
    if filters.set_codes:
        set_codes_upper = {code.upper() for code in filters.set_codes}

        # Filter cards to only those from specified sets
        result.cards = [
            card
            for card in result.cards
            if card.set_code and card.set_code.upper() in set_codes_upper
        ]

        # Filter commanders to only those from specified sets
        result.commanders = [
            cmd
            for cmd in result.commanders
            if cmd.set_code and cmd.set_code.upper() in set_codes_upper
        ]

        set_list = ", ".join(sorted(filters.set_codes)[:5])
        if len(filters.set_codes) > 5:
            set_list += f" (+{len(filters.set_codes) - 5} more)"
        result.filter_reasons.append(f"Filtered to sets: {set_list}")

    return result


# Name templates for deck suggestions - more variety and flavor
_COMMANDER_NAME_TEMPLATES = [
    "{commander}'s Domain",
    "{commander}'s Legion",
    "{commander}'s Crusade",
    "The {commander} Conquest",
    "{commander}'s Vengeance",
    "{commander}'s Dominion",
]

_TRIBAL_NAME_TEMPLATES = [
    "Rise of the {tribal}s",
    "{tribal} Dominion",
    "The {tribal} Horde",
    "{tribal} Uprising",
    "March of {tribal}s",
    "Wrath of {tribal}s",
]

_THEME_NAME_TEMPLATES = [
    "Path of {theme}",
    "{theme} Mastery",
    "The {theme} Engine",
    "{theme} Dominance",
    "Art of {theme}",
    "{theme} Ascendancy",
]

_SET_FLAVOR_NAMES: dict[str, str] = {
    # Recent/popular sets with thematic names
    "fin": "Final Fantasy",
    "fic": "Final Fantasy",
    "fca": "Final Fantasy",
    "mh3": "Modern Horizons",
    "mh2": "Modern Horizons",
    "lci": "Ixalan",
    "one": "Phyrexian",
    "mom": "Multiverse",
    "dmu": "Dominaria",
    "neo": "Kamigawa",
    "vow": "Crimson Vow",
    "mid": "Midnight Hunt",
    "afr": "Forgotten Realms",
    "stx": "Strixhaven",
    "khm": "Kaldheim",
    "znr": "Zendikar",
    "eld": "Eldraine",
    "thb": "Theros",
    "iko": "Ikoria",
    "war": "Ravnica",
    "dsk": "Duskmourn",
    "blb": "Bloomburrow",
    "otj": "Thunder Junction",
    "mkm": "Murders at Karlov",
    "woe": "Wilds of Eldraine",
    "ltr": "Lord of the Rings",
    "pip": "Fallout",
    "who": "Doctor Who",
    "acr": "Assassin's Creed",
    "40k": "Warhammer 40K",
}


def _generate_deck_name(
    commander: str | None = None,
    tribal: str | None = None,
    theme: str | None = None,
    set_codes: list[str] | None = None,
    archetype: str | None = None,
    seed: int = 0,
) -> str:
    """Generate a creative deck name based on filters and context.

    Uses seed for deterministic but varied name selection.
    Priority: set flavor > tribal > theme > commander > archetype
    """
    import hashlib

    # Create a hash for deterministic randomness
    hash_input = f"{commander or ''}{tribal or ''}{theme or ''}{archetype or ''}{seed}"
    hash_val = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)

    # Check if we have a set with flavor
    set_flavor = None
    if set_codes:
        for code in set_codes:
            code_lower = code.lower()
            if code_lower in _SET_FLAVOR_NAMES:
                set_flavor = _SET_FLAVOR_NAMES[code_lower]
                break

    # Build the name with priority
    if tribal:
        templates = _TRIBAL_NAME_TEMPLATES
        template = templates[hash_val % len(templates)]
        base_name = template.format(tribal=tribal)
        if set_flavor:
            return f"{set_flavor}: {base_name}"
        return base_name

    if theme:
        templates = _THEME_NAME_TEMPLATES
        template = templates[hash_val % len(templates)]
        base_name = template.format(theme=theme)
        if set_flavor:
            return f"{set_flavor}: {base_name}"
        return base_name

    if commander:
        # Extract just the first name for cleaner titles
        cmd_short = commander.split(",")[0].strip()
        templates = _COMMANDER_NAME_TEMPLATES
        template = templates[hash_val % len(templates)]
        base_name = template.format(commander=cmd_short)
        if set_flavor:
            return f"{set_flavor}: {base_name}"
        return base_name

    if archetype:
        if set_flavor:
            return f"{set_flavor}: {archetype}"
        return archetype

    return "Custom Deck"


class DeckFinder:
    """Recommend deck archetypes based on collection."""

    def __init__(self, db: UnifiedDatabase | None = None) -> None:
        self._db = db
        self._initialized = False
        self._smart_engine: SmartSuggestionEngine | None = None
        # Synergy scoring infrastructure
        self._synergy_scorer = SynergyScorer()
        self._card_encoder = CardEncoder()
        self._deck_encoder = DeckEncoder()
        # 17Lands gameplay data for Limited stats
        self._gameplay_db: GameplayDB | None = None

    async def initialize(self, db: UnifiedDatabase) -> None:
        """Initialize with card data from database."""
        self._db = db
        self._smart_engine = get_smart_engine()
        self._smart_engine.initialize(db)
        # Initialize 17Lands gameplay database
        self._gameplay_db = get_gameplay_db()
        if self._gameplay_db.is_available:
            self._gameplay_db.connect()
        self._initialized = True

    def _get_smart_engine(self) -> SmartSuggestionEngine:
        """Get or create smart engine."""
        if self._smart_engine is None:
            self._smart_engine = get_smart_engine()
            if self._db:
                self._smart_engine.initialize(self._db)
        return self._smart_engine

    def _get_gameplay_db(self) -> GameplayDB:
        """Get or create gameplay database."""
        if self._gameplay_db is None:
            self._gameplay_db = get_gameplay_db()
            if self._gameplay_db.is_available:
                self._gameplay_db.connect()
        return self._gameplay_db

    def _score_limited_stats(
        self,
        card_name: str,
        set_code: str | None = None,
    ) -> tuple[float, str | None, bool]:
        """Score a card based on 17Lands Limited performance data."""
        return score_limited_stats(card_name, self._get_gameplay_db(), set_code)

    def _validate_mana_curve(
        self,
        cards: list[CardData],
        format_type: str,
        archetype: str | None = None,
    ) -> tuple[bool, list[str], float]:
        """Validate mana curve is healthy for the format/archetype."""
        return validate_mana_curve(cards, format_type, archetype)

    def _count_interaction(self, cards: list[CardData]) -> tuple[int, list[str]]:
        """Count interaction spells (removal, counterspells, etc)."""
        return count_interaction(cards)

    def _validate_interaction_density(
        self,
        cards: list[CardData],
        format_type: str,
    ) -> tuple[bool, list[str], float]:
        """Validate deck has enough interaction (removal/counterspells)."""
        return validate_interaction_density(cards, format_type)

    def _detect_win_conditions(
        self, cards: list[CardData], _combo_count: int = 0
    ) -> dict[str, list[str]]:
        """Detect win conditions in the deck."""
        return detect_win_conditions(cards, _combo_count)

    def _validate_win_conditions(
        self,
        cards: list[CardData],
        format_type: str,
        archetype: str | None,
        combo_count: int,
    ) -> tuple[bool, list[str], float, list[str]]:
        """Validate deck has viable win conditions."""
        return validate_win_conditions(cards, format_type, archetype, combo_count)

    def _assess_tribal_strength(
        self, creature_type: str, count: int, lord_count: int = 0
    ) -> tuple[str, float]:
        """Assess tribal theme strength."""
        return assess_tribal_strength(creature_type, count, lord_count)

    def _assess_theme_strength(self, theme: str, supporting_cards: int) -> tuple[str, float]:
        """Assess theme strength."""
        return assess_theme_strength(theme, supporting_cards)

    def _count_tribal_lords(
        self, cards: list[CardData], creature_type: str
    ) -> tuple[int, list[str]]:
        """Count tribal lords that buff a specific creature type."""
        return count_tribal_lords(cards, creature_type)

    def _count_ramp_sources(self, cards: list[CardData]) -> tuple[int, list[str]]:
        """Count mana ramp sources in the deck."""
        return count_ramp_sources(cards)

    def _count_card_advantage(self, cards: list[CardData]) -> tuple[int, dict[str, int]]:
        """Count card advantage sources by type."""
        return count_card_advantage(cards)

    def _validate_ramp_sufficiency(
        self,
        cards: list[CardData],
        avg_cmc: float,
        format_type: str = "commander",
    ) -> tuple[bool, list[str], float]:
        """Validate that the deck has sufficient ramp for its mana curve."""
        return validate_ramp_sufficiency(cards, avg_cmc, format_type)

    def _validate_card_advantage(
        self,
        cards: list[CardData],
        archetype: str | None,
        format_type: str = "commander",
    ) -> tuple[bool, list[str], float]:
        """Validate card advantage sources by archetype."""
        return validate_card_advantage(cards, archetype, format_type)

    def _score_card_for_deck(
        self,
        card: CardData,
        deck_features: DeckFeatures,
        archetype: str | None = None,
    ) -> tuple[float, list[str]]:
        """Score a card's fit for a specific deck using SynergyScorer."""
        return score_card_for_deck(
            card,
            deck_features,
            self._synergy_scorer,
            self._card_encoder,
            self._get_gameplay_db(),
            archetype,
        )

    async def _score_combo_potential(
        self,
        deck_cards: list[str],
        commander_identity: list[str],
    ) -> tuple[list[ComboSummary], list[ComboSummary], float]:
        """Find combos enabled by this deck.

        Args:
            deck_cards: Card names in the deck
            commander_identity: Commander's color identity

        Returns:
            Tuple of (complete_combos, near_combos, combo_score)
        """
        from .spellbook_combos import get_spellbook_detector

        detector = await get_spellbook_detector()
        if not detector.is_available:
            return [], [], 0.0

        await detector.initialize()

        # Find combos 0-2 pieces away
        matches, _ = await detector.find_missing_pieces(
            deck_cards,
            max_missing=2,
            min_present=2,
        )

        complete: list[ComboSummary] = []
        near: list[ComboSummary] = []

        # Color identity filter
        identity_set = {c.upper() for c in commander_identity} if commander_identity else set()

        for match in matches[:30]:  # Cap at 30 to avoid performance issues
            combo = match.combo

            # Filter by color identity (combo must fit within commander colors)
            if identity_set:
                combo_identity = set(combo.identity.upper()) if combo.identity else set()
                if combo_identity and not combo_identity.issubset(identity_set):
                    continue

            summary = ComboSummary(
                id=combo.id,
                cards=combo.card_names,
                missing_cards=match.missing_cards,
                produces=combo.produces,
                bracket=combo.bracket_tag,
                score=detector.get_combo_score(combo),
                completion_pct=match.completion_ratio,
            )

            if match.is_complete:
                complete.append(summary)
            else:
                near.append(summary)

        # Sort by score descending
        complete.sort(key=lambda x: -x.score)
        near.sort(key=lambda x: -x.score)

        # Calculate combo_score (0-1)
        # Weight by bracket: R > S > P > C
        bracket_weights = {"R": 1.0, "S": 0.8, "P": 0.6, "PA": 0.5, "C": 0.4, "O": 0.3}

        score = 0.0
        for c_combo in complete[:5]:  # Top 5 complete combos
            weight = bracket_weights.get(c_combo.bracket, 0.4)
            score += weight * 0.2  # Each complete combo adds up to 0.2
        for n_combo in near[:10]:  # Top 10 near combos
            weight = bracket_weights.get(n_combo.bracket, 0.4)
            completion_bonus = n_combo.completion_pct * 0.5  # Higher completion = more valuable
            score += weight * completion_bonus * 0.05  # Near combos worth less

        return complete[:5], near[:10], min(score, 1.0)

    def _select_best_cards(
        self,
        cards: list[CardData],
        deck_format: str,
        archetype: str | None = None,
        commander: CardData | None = None,
        all_lands: list[CardData] | None = None,
    ) -> tuple[list[str], list[str]]:
        """Select the best cards for a deck, respecting type balance and deck size.

        Args:
            cards: Cards to select from (may be filtered by set)
            deck_format: Format like "standard" or "commander"
            archetype: Deck archetype for scoring
            commander: Commander card if applicable
            all_lands: Optional full list of lands from collection (not filtered by set).
                      Used to fill land slots when set filter limits available lands.
        """
        targets = DECK_TARGETS.get(deck_format, DECK_TARGETS["commander"])
        total = targets["total"]
        max_cards = total if isinstance(total, int) else 99

        # Encode deck to get DeckFeatures for synergy scoring
        # Include commander in deck analysis if present
        deck_card_dicts = [c.to_encoder_dict() for c in cards]
        if commander:
            deck_card_dicts.append(commander.to_encoder_dict())
        deck_features = self._deck_encoder.encode(deck_card_dicts)

        # Score all cards using SynergyScorer
        scored_cards: list[tuple[float, CardData, list[str]]] = []
        for card in cards:
            score, reasons = self._score_card_for_deck(card, deck_features, archetype)
            scored_cards.append((score, card, reasons))

        # Sort by score descending
        scored_cards.sort(key=lambda x: -x[0])

        # Get commander's color identity for filtering
        commander_identity = set(commander.get_color_identity()) if commander else set()

        # Filter cards by color identity first
        valid_cards: list[tuple[float, CardData, list[str]]] = []
        for score, card, reasons in scored_cards:
            if commander_identity:
                card_identity = set(card.get_color_identity())
                if card_identity and not card_identity.issubset(commander_identity):
                    continue
            valid_cards.append((score, card, reasons))

        # Two-pass selection: first ensure minimums, then fill with best cards
        type_counts: Counter[str] = Counter()
        owned_cards: list[str] = []
        missing_cards: list[str] = []  # Cards we need to add (like basic lands)
        selected_names: set[str] = set()

        # Pass 1: Ensure minimum lands (critical for playable decks)
        land_min = 22 if deck_format == "standard" else 35
        land_cards = [(s, c, r) for s, c, r in valid_cards if c.get_card_type() == "land"]

        # Add owned lands from the filtered set first
        for _score, card, _reasons in land_cards[:land_min]:
            if card.name not in selected_names:
                owned_cards.append(card.name)
                selected_names.add(card.name)
                type_counts["land"] += 1

        # Get deck colors for land selection
        deck_colors: set[str] = set()
        if commander_identity:
            deck_colors = commander_identity
        else:
            # Derive from non-land cards in the deck
            for _score, card, _reasons in valid_cards:
                if card.get_card_type() != "land":
                    deck_colors.update(card.get_color_identity())

        colors_list = [c for c in deck_colors if c in BASIC_LAND_NAMES]
        if not colors_list:
            colors_list = ["R"]  # Default to Mountain for colorless

        # If we don't have enough lands, try to fill from full collection first
        if type_counts["land"] < land_min and all_lands:
            # Score and sort lands from full collection by fit
            extra_land_candidates: list[tuple[float, CardData]] = []
            for land in all_lands:
                if land.name in selected_names:
                    continue
                # Check color identity compatibility
                land_identity = set(land.get_color_identity())
                if land_identity and not land_identity.issubset(set(colors_list)):
                    continue
                # Score lands: dual lands > utility lands > basics
                score = 0.0
                land_text = (land.text or "").lower()
                land_type = (land.type_line or "").lower()
                # Dual lands that tap for multiple colors
                produces_colors = sum(1 for c in colors_list if c.lower() in land_text)
                if produces_colors >= 2:
                    score += 3.0  # High priority for dual lands
                elif produces_colors == 1:
                    score += 1.0
                # Utility lands (draw, ramp, etc.)
                if any(kw in land_text for kw in ["draw", "scry", "create", "counter"]):
                    score += 0.5
                # Fetch lands, shock lands, check lands
                if "search" in land_text and "land" in land_text:
                    score += 2.5  # Fetch lands
                if "pay 2 life" in land_text:
                    score += 2.0  # Shock lands
                # Basic land types for better synergy
                if any(t in land_type for t in ["plains", "island", "swamp", "mountain", "forest"]):
                    score += 0.3
                extra_land_candidates.append((score, land))

            # Sort by score descending
            extra_land_candidates.sort(key=lambda x: -x[0])

            # Add lands from full collection
            for _score, land in extra_land_candidates:
                if type_counts["land"] >= land_min:
                    break
                if land.name not in selected_names:
                    owned_cards.append(land.name)
                    selected_names.add(land.name)
                    type_counts["land"] += 1

        # If still not enough lands, add basic lands (always available)
        if type_counts["land"] < land_min:
            lands_needed = land_min - type_counts["land"]

            # Use pip-based distribution for optimal basic land allocation
            # Get non-land cards for pip counting
            owned_card_data = [c for _, c, _ in valid_cards if not c.is_land()]
            distribution = self._calculate_optimal_basic_distribution(
                owned_card_data, colors_list, lands_needed
            )

            # Add basic lands according to optimal distribution
            for color, count in distribution.items():
                basic_name = BASIC_LAND_NAMES.get(color)
                if basic_name:
                    for _ in range(count):
                        missing_cards.append(basic_name)
                        type_counts["land"] += 1

            # Fill any remaining with highest-pip color's basic (rounding errors)
            while type_counts["land"] < land_min:
                missing_cards.append(BASIC_LAND_NAMES[colors_list[0]])
                type_counts["land"] += 1

        # Pass 2: Fill remaining slots with highest-scoring NON-LAND cards
        # Lands are fully handled in Pass 1 - we don't want any more lands
        non_land_cards = [(s, c, r) for s, c, r in valid_cards if not c.is_land()]

        total_selected = len(owned_cards) + len(missing_cards)
        for _score, card, _reasons in non_land_cards:
            if total_selected >= max_cards:
                break
            if card.name in selected_names:
                continue

            card_type = card.get_card_type()
            type_limit = targets.get(card_type, (0, 10))  # Default max of 10 for unknown types
            max_of_type = type_limit[1] if isinstance(type_limit, tuple) else 10

            if type_counts[card_type] < max_of_type:
                owned_cards.append(card.name)
                selected_names.add(card.name)
                type_counts[card_type] += 1
                total_selected += 1

        return (owned_cards, missing_cards)

    async def find_commander_decks(
        self,
        _collection_cards: set[str],
        card_data: list[CardData] | None = None,
        min_completion: float = 0.0,
        limit: int = 10,
        filters: DeckFilters | None = None,
    ) -> list[DeckSuggestion]:
        """Find Commander decks the user can build.

        Args:
            collection_cards: Set of card names the user owns
            card_data: Optional list of CardData for deeper analysis
            min_completion: Minimum completion percentage to include
            limit: Maximum suggestions to return
            filters: Optional filters for colors, tribal, theme, keyword

        Returns:
            List of deck suggestions sorted by relevance
        """
        suggestions: list[DeckSuggestion] = []

        if not card_data:
            return suggestions

        # Filter out art series, token sets, and other excluded sets
        card_data = [c for c in card_data if not is_excluded_set(c.set_code)]

        # Find potential commanders (legendary creatures) before filtering
        all_commanders = [
            card
            for card in card_data
            if card.type_line and self._is_valid_commander(card.type_line)
        ]

        # === CENTRALIZED PRE-FILTERING ===
        filter_result = _pre_filter_cards(card_data, all_commanders, filters)

        # Early exit if filter minimums not met
        if filters:
            if filters.creature_type and not filter_result.meets_tribal_minimum:
                return suggestions  # Not enough creatures of requested type
            if filters.theme and not filter_result.meets_theme_minimum:
                return suggestions  # Not enough cards supporting theme

        # Use filtered data
        card_data = filter_result.cards
        potential_commanders = filter_result.commanders
        base_filter_reasons = filter_result.filter_reasons

        if not potential_commanders:
            return suggestions

        # Analyze collection for tribal themes
        tribal_counts = self._count_tribal_types(card_data)

        # Analyze collection for mechanic themes
        theme_counts = self._count_themes(card_data)

        # Analyze colors in collection
        color_counts = self._count_colors(card_data)

        # Generate suggestions for each potential commander
        for commander in potential_commanders:
            suggestion = await self._create_commander_suggestion(
                commander,
                card_data,
                tribal_counts,
                theme_counts,
                color_counts,
                filters=filters,
                filter_reasons=base_filter_reasons,
            )
            if suggestion and suggestion.completion_pct >= min_completion:
                suggestions.append(suggestion)

        # Also add tribal-based suggestions if strong tribal presence
        # (only if no specific tribal filter, or if it matches)
        if not filters or not filters.creature_type:
            tribal_suggestions = self._create_tribal_suggestions(
                potential_commanders,
                card_data,
                tribal_counts,
                color_counts,
                filters=filters,
                filter_reasons=base_filter_reasons,
            )
            suggestions.extend(tribal_suggestions)
        elif filters and filters.creature_type:
            # Filter tribal suggestions to specific type
            tribal_suggestions = self._create_tribal_suggestions(
                potential_commanders,
                card_data,
                tribal_counts,
                color_counts,
                creature_type_filter=filters.creature_type,
                filters=filters,
                filter_reasons=base_filter_reasons,
            )
            suggestions.extend(tribal_suggestions)

        # Also add theme-based suggestions
        # (only if no specific theme filter, or if it matches)
        if not filters or not filters.theme:
            theme_suggestions = self._create_theme_suggestions(
                potential_commanders,
                card_data,
                theme_counts,
                color_counts,
                filters=filters,
                filter_reasons=base_filter_reasons,
            )
            suggestions.extend(theme_suggestions)
        elif filters and filters.theme:
            # Filter theme suggestions to specific theme
            theme_suggestions = self._create_theme_suggestions(
                potential_commanders,
                card_data,
                theme_counts,
                color_counts,
                theme_filter=filters.theme,
                filters=filters,
                filter_reasons=base_filter_reasons,
            )
            suggestions.extend(theme_suggestions)

        # Sort by completion/relevance and deduplicate
        suggestions.sort(key=lambda s: (-s.completion_pct, s.name))

        # Remove duplicates (same commander)
        seen_commanders: set[str] = set()
        unique_suggestions: list[DeckSuggestion] = []
        for s in suggestions:
            if s.commander and s.commander not in seen_commanders:
                seen_commanders.add(s.commander)
                unique_suggestions.append(s)
            elif not s.commander:
                unique_suggestions.append(s)

        return unique_suggestions[:limit]

    def _is_valid_commander(self, type_line: str) -> bool:
        """Check if a card can be a commander."""
        type_lower = type_line.lower()
        # Legendary Creature, or has "can be your commander"
        if "legendary" in type_lower and "creature" in type_lower:
            return True
        # Some planeswalkers can be commanders
        return "legendary" in type_lower and "planeswalker" in type_lower

    def _count_tribal_types(self, cards: list[CardData]) -> Counter[str]:
        """Count creature types in collection."""
        type_counts: Counter[str] = Counter()
        for card in cards:
            if not card.type_line:
                continue
            type_lower = card.type_line.lower()
            for tribal_type in TRIBAL_TYPES:
                if tribal_type.lower() in type_lower:
                    type_counts[tribal_type] += 1
        return type_counts

    def _count_themes(self, cards: list[CardData]) -> Counter[str]:
        """Count theme occurrences in collection."""
        theme_counts: Counter[str] = Counter()
        for card in cards:
            text = (card.text or "").lower()
            type_line = (card.type_line or "").lower()
            combined = f"{text} {type_line}"

            for theme, keywords in THEME_KEYWORDS.items():
                for keyword in keywords:
                    if keyword.lower() in combined:
                        theme_counts[theme] += 1
                        break  # Only count each theme once per card

        return theme_counts

    def _count_colors(self, cards: list[CardData]) -> Counter[str]:
        """Count color presence in collection."""
        color_counts: Counter[str] = Counter()
        for card in cards:
            if card.colors:
                for color in card.colors:
                    color_counts[color] += 1
            elif card.mana_cost:
                # Extract colors from mana cost
                for color in ["W", "U", "B", "R", "G"]:
                    if color in card.mana_cost:
                        color_counts[color] += 1
        return color_counts

    def _get_commander_colors(self, commander: CardData) -> list[str]:
        """Get color identity of a commander."""
        # Use the get_color_identity() method which properly handles
        # the color_identity field (preferred) with fallback to colors/mana
        return commander.get_color_identity()

    def _count_color_sources(self, cards: list[CardData], colors: list[str]) -> dict[str, int]:
        """Count mana sources for each color."""
        return count_color_sources(cards, colors)

    def _count_fixing_lands(self, cards: list[CardData]) -> int:
        """Count lands that provide color fixing."""
        return count_fixing_lands(cards)

    def _validate_mana_base(
        self,
        cards: list[CardData],
        colors: list[str],
        format_type: str,
    ) -> tuple[bool, list[str], float]:
        """Validate mana base has adequate color fixing."""
        return validate_mana_base(cards, colors, format_type)

    def _calculate_optimal_basic_distribution(
        self,
        cards: list[CardData],
        colors: list[str],
        total_basics_needed: int,
    ) -> dict[str, int]:
        """Calculate optimal basic land distribution based on color pip requirements.

        Returns:
            Dict mapping color to number of basic lands.
        """
        # Count pips of each color in mana costs
        pip_counts: dict[str, int] = dict.fromkeys(colors, 0)

        for card in cards:
            if not card.mana_cost:
                continue
            for color in colors:
                # Count occurrences of the color symbol
                pip_counts[color] += card.mana_cost.count(color)

        total_pips = sum(pip_counts.values())
        if total_pips == 0:
            # Even distribution if no pips found
            per_color = total_basics_needed // len(colors)
            return dict.fromkeys(colors, per_color)

        # Distribute proportionally to pip count
        distribution: dict[str, int] = {}
        remaining = total_basics_needed

        for color in colors:
            ratio = pip_counts[color] / total_pips
            count = int(total_basics_needed * ratio)
            distribution[color] = count
            remaining -= count

        # Distribute remainder to highest pip colors
        if remaining > 0:
            sorted_colors = sorted(colors, key=lambda c: pip_counts[c], reverse=True)
            for i in range(remaining):
                distribution[sorted_colors[i % len(sorted_colors)]] += 1

        return distribution

    async def _create_commander_suggestion(
        self,
        commander: CardData,
        all_cards: list[CardData],
        tribal_counts: Counter[str],
        theme_counts: Counter[str],
        _color_counts: Counter[str],
        filters: DeckFilters | None = None,
        filter_reasons: list[str] | None = None,
    ) -> DeckSuggestion | None:
        """Create a deck suggestion around a specific commander."""
        commander_colors = self._get_commander_colors(commander)

        # Check if commander matches filters
        if filters:
            # Check creature type filter
            if filters.creature_type:
                type_lower = filters.creature_type.lower()
                cmd_type = (commander.type_line or "").lower()
                cmd_text = (commander.text or "").lower()
                if type_lower not in cmd_type and type_lower not in cmd_text:
                    return None  # Commander doesn't match tribal filter

            # Check theme filter
            if filters.theme and filters.theme in THEME_KEYWORDS:
                theme_keywords = THEME_KEYWORDS[filters.theme]
                cmd_text = (commander.text or "").lower()
                if not any(kw.lower() in cmd_text for kw in theme_keywords):
                    return None  # Commander doesn't match theme filter

        # Get cards that fit this commander's colors (as CardData objects)
        fitting_card_data: list[CardData] = []
        tribal_filter_lower = (
            filters.creature_type.lower() if filters and filters.creature_type else None
        )

        for card in all_cards:
            # Skip the commander itself
            if card.name == commander.name:
                continue

            # Apply tribal filter - only include creatures of the specified type
            # (lands and support cards are still included)
            if tribal_filter_lower:
                card_type = (card.type_line or "").lower()
                card_text = (card.text or "").lower()
                is_creature = "creature" in card_type
                is_tribal_creature = (
                    tribal_filter_lower in card_type or tribal_filter_lower in card_text
                )
                # Skip non-tribal creatures, but keep lands and non-creatures
                if is_creature and not is_tribal_creature:
                    continue

            # Use color identity for proper filtering (important for lands!)
            card_identity = card.get_color_identity()
            # If commander has no color identity data, accept all cards
            # Otherwise check color identity matching
            if not commander_colors:
                fitting_card_data.append(card)
            elif not card_identity:
                # Truly colorless cards fit any commander
                fitting_card_data.append(card)
            elif all(c in commander_colors for c in card_identity):
                fitting_card_data.append(card)

        # Need at least some cards to make a suggestion
        if len(fitting_card_data) < 10:
            return None

        # Detect archetype based on commander's text and type
        archetype = self._detect_commander_archetype(commander, tribal_counts, theme_counts)

        # Select the best cards using scoring
        owned_cards, missing_cards = self._select_best_cards(
            fitting_card_data,
            deck_format="commander",
            archetype=archetype,
            commander=commander,
        )

        # Calculate completion based on how close to 99 cards we got
        total_cards = len(owned_cards) + len(missing_cards)
        completion = min(total_cards / 99, 1.0)

        # Analyze combo potential
        complete_combos, near_combos, combo_score = await self._score_combo_potential(
            deck_cards=[*owned_cards, commander.name],
            commander_identity=commander_colors,
        )

        # Identify limited bombs (S/A tier cards from 17Lands)
        limited_bombs: list[str] = []
        for card_name in owned_cards:
            _, tier, is_bomb = self._score_limited_stats(card_name)
            if tier in ("S", "A") or is_bomb:
                limited_bombs.append(card_name)

        reasons: list[str] = []
        reasons.append("You own this legendary creature")
        reasons.append(f"{len(fitting_card_data)} cards in these colors")

        if archetype:
            reasons.append(f"Potential strategy: {archetype}")

        if missing_cards:
            reasons.append(f"Need {len(missing_cards)} basic lands")

        # Add combo-based reasons
        if complete_combos:
            top_combo = complete_combos[0]
            produces = top_combo.produces[0] if top_combo.produces else "combo"
            reasons.append(f"Complete combo: {produces}")
        if near_combos:
            reasons.append(f"{len(near_combos)} combos 1-2 cards away")

        # Add 17Lands-based reasons
        if limited_bombs:
            reasons.append(f"{len(limited_bombs)} Limited bombs (S/A tier)")

        # Validate deck quality
        deck_card_data = [c for c in fitting_card_data if c.name in owned_cards]
        _curve_valid, curve_warnings, curve_adj = self._validate_mana_curve(
            deck_card_data,
            "commander",
            archetype,
        )
        _interaction_valid, interaction_warnings, interaction_adj = (
            self._validate_interaction_density(
                deck_card_data,
                "commander",
            )
        )
        interaction_count, _ = self._count_interaction(deck_card_data)

        # Add quality warnings to reasons
        if curve_warnings:
            reasons.extend([f"Warning: {w}" for w in curve_warnings])
        if interaction_warnings:
            reasons.extend([f"Warning: {w}" for w in interaction_warnings])

        # Validate mana base for multi-color decks
        mana_base_quality = ""
        fixing_land_count = 0
        mana_adj = 0.0

        if len(commander_colors) >= 2:
            _mana_valid, mana_warnings, mana_adj = self._validate_mana_base(
                deck_card_data,
                commander_colors,
                "commander",
            )
            if mana_warnings:
                reasons.extend([f"Warning: {w}" for w in mana_warnings])

            # Rate mana base quality
            fixing_land_count = self._count_fixing_lands(deck_card_data)
            required = COLOR_FIXING_REQUIREMENTS.get(len(commander_colors), 12)
            if fixing_land_count >= int(required * 1.2):
                mana_base_quality = "excellent"
            elif fixing_land_count >= required:
                mana_base_quality = "good"
            else:
                mana_base_quality = "poor"

        # Validate win conditions
        complete_combo_count = len(complete_combos) if complete_combos else 0
        _win_valid, win_warnings, win_adj, win_con_types = self._validate_win_conditions(
            deck_card_data,
            "commander",
            archetype,
            complete_combo_count,
        )
        if win_warnings:
            reasons.extend([f"Warning: {w}" for w in win_warnings])

        # Assess tribal/theme strength if applicable
        tribal_strength = ""
        theme_strength = ""
        lord_count = 0

        if archetype and "Tribal" in archetype:
            tribal_type = archetype.replace(" Tribal", "")
            tribal_count = sum(
                1
                for c in deck_card_data
                if c.type_line and tribal_type.lower() in c.type_line.lower()
            )
            # Count tribal lords (cards that buff the tribe)
            lord_count, _lord_names = self._count_tribal_lords(deck_card_data, tribal_type)
            tribal_strength, tribal_adj = self._assess_tribal_strength(
                tribal_type, tribal_count, lord_count
            )
            win_adj += tribal_adj
            if tribal_strength == "strong":
                lord_info = f", {lord_count} lords" if lord_count > 0 else ""
                reasons.append(f"Strong {tribal_type} tribal ({tribal_count} creatures{lord_info})")
            elif tribal_strength == "viable":
                lord_info = f", {lord_count} lords" if lord_count > 0 else ""
                reasons.append(f"Viable {tribal_type} tribal ({tribal_count} creatures{lord_info})")

        # Assess theme strength if archetype detected
        if archetype and archetype in THEME_KEYWORDS:
            keywords = THEME_KEYWORDS[archetype]
            theme_count = sum(
                1
                for c in deck_card_data
                if c.text and any(kw.lower() in c.text.lower() for kw in keywords)
            )
            theme_strength, theme_adj = self._assess_theme_strength(archetype, theme_count)
            win_adj += theme_adj
            if theme_strength == "strong":
                reasons.append(f"Strong {archetype} theme ({theme_count} cards)")
            elif theme_strength == "viable":
                reasons.append(f"Viable {archetype} theme ({theme_count} cards)")

        # Validate ramp sufficiency (Power User suggestion)
        # Calculate average CMC for ramp validation
        non_land_cards = [c for c in deck_card_data if c.type_line and "Land" not in c.type_line]
        avg_cmc = sum(c.get_cmc() for c in non_land_cards) / max(len(non_land_cards), 1)

        ramp_count, _ramp_names = self._count_ramp_sources(deck_card_data)
        ramp_valid, ramp_warnings, ramp_adj = self._validate_ramp_sufficiency(
            deck_card_data, avg_cmc, "commander"
        )
        if not ramp_valid:
            reasons.extend([f"Warning: {w}" for w in ramp_warnings])
            win_adj += ramp_adj

        # Validate card advantage (Power User suggestion)
        card_advantage_count, card_advantage_breakdown = self._count_card_advantage(deck_card_data)
        ca_valid, ca_warnings, ca_adj = self._validate_card_advantage(
            deck_card_data, archetype, "commander"
        )
        if not ca_valid:
            reasons.extend([f"Warning: {w}" for w in ca_warnings])
            win_adj += ca_adj

        # Get archetype-specific weights for quality scoring
        # For tribal archetypes like "Zombie Tribal", check base archetype first
        arch_key = archetype.split()[0] if archetype else "_default"
        if arch_key.endswith("Tribal") or arch_key not in ARCHETYPE_WEIGHTS:
            arch_key = "_default"
        weights = ARCHETYPE_WEIGHTS.get(arch_key, ARCHETYPE_WEIGHTS["_default"])

        # Calculate weighted quality score based on archetype priorities
        # Each adjustment is scaled by its importance to this archetype
        # Adjustments are negative penalties or positive bonuses
        weighted_adj = (
            curve_adj * (weights["curve"] * 4)
            + interaction_adj * (weights["interaction"] * 4)
            + mana_adj * (weights["mana_base"] * 4)
            + win_adj * (weights["win_con"] * 4)
        )
        quality_score = max(0.0, min(1.0, 1.0 + weighted_adj))

        # Generate creative name using filters context
        deck_name = _generate_deck_name(
            commander=commander.name,
            tribal=filters.creature_type if filters else None,
            theme=filters.theme if filters else None,
            set_codes=filters.set_codes if filters else None,
            archetype=archetype,
            seed=hash(commander.name),
        )

        return DeckSuggestion(
            name=deck_name,
            format="commander",
            commander=commander.name,
            archetype=archetype,
            colors=commander_colors,
            key_cards_owned=owned_cards,
            key_cards_missing=missing_cards,
            completion_pct=completion,
            reasons=reasons,
            filter_reasons=filter_reasons or [],
            near_combos=near_combos,
            complete_combos=complete_combos,
            combo_score=combo_score,
            limited_bombs=limited_bombs,
            curve_warnings=curve_warnings,
            interaction_count=interaction_count,
            quality_score=quality_score,
            mana_base_quality=mana_base_quality,
            fixing_land_count=fixing_land_count,
            win_condition_types=win_con_types,
            tribal_strength=tribal_strength,
            theme_strength=theme_strength,
            lord_count=lord_count,
            ramp_count=ramp_count,
            ramp_warnings=ramp_warnings if not ramp_valid else [],
            card_advantage_count=card_advantage_count,
            card_advantage_breakdown=card_advantage_breakdown,
            card_advantage_warnings=ca_warnings if not ca_valid else [],
        )

    def _detect_commander_archetype(
        self,
        commander: CardData,
        tribal_counts: Counter[str],
        _theme_counts: Counter[str],
    ) -> str | None:
        """Detect the likely archetype for a commander."""
        text = (commander.text or "").lower()
        type_line = (commander.type_line or "").lower()

        # Check for tribal synergy
        for tribal_type in TRIBAL_TYPES:
            tribal_lower = tribal_type.lower()
            if (tribal_lower in type_line or tribal_lower in text) and tribal_counts.get(
                tribal_type, 0
            ) >= 5:
                return f"{tribal_type} Tribal"

        # Check for theme synergy
        for theme, keywords in THEME_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    return theme

        # Generic detection
        if "sacrifice" in text or "dies" in text:
            return "Aristocrats"
        if "+1/+1" in text or "counter" in text:
            return "Counters"
        if "token" in text or "create" in text:
            return "Tokens"
        if "draw" in text and "card" in text:
            return "Card Advantage"
        if "damage" in text and "each" in text:
            return "Group Slug"

        return None

    def _create_tribal_suggestions(
        self,
        commanders: list[CardData],
        all_cards: list[CardData],
        tribal_counts: Counter[str],
        _color_counts: Counter[str],
        creature_type_filter: str | None = None,
        filters: DeckFilters | None = None,
        filter_reasons: list[str] | None = None,
    ) -> list[DeckSuggestion]:
        """Create suggestions based on tribal themes in collection.

        Uses smart engine for database queries when a specific tribal filter is set.
        Falls back to collection-only analysis when browsing top tribes.
        """
        suggestions: list[DeckSuggestion] = []
        smart_engine = self._get_smart_engine()
        owned_only = filters.owned_only if filters else True
        color_filter = filters.colors if filters else None

        # Build collection card set for filtering
        collection_cards = {c.name for c in all_cards}

        # If filtering by specific creature type, use smart engine for better results
        if creature_type_filter:
            # Find commanders that synergize with this tribal type
            tribal_commanders = smart_engine.find_tribal_commanders(
                creature_type_filter,
                colors=color_filter,
                limit=10,
            )

            # Filter to owned commanders if owned_only
            if owned_only:
                tribal_commanders = [
                    cmd for cmd in tribal_commanders if cmd["name"] in collection_cards
                ]

            # Find tribal creatures
            _tribal_creatures = smart_engine.find_tribal_creatures(
                creature_type_filter,
                colors=color_filter,
                collection_cards=collection_cards if owned_only else None,
                limit=50,
            )

            if not tribal_commanders:
                # No commander found, check if user has one in collection
                for cmd in commanders:
                    type_lower = (cmd.type_line or "").lower()
                    text_lower = (cmd.text or "").lower()
                    filter_lower = creature_type_filter.lower()
                    if filter_lower in type_lower or filter_lower in text_lower:
                        tribal_commanders = [{"name": cmd.name, "type_line": cmd.type_line}]
                        break

            if tribal_commanders:
                cmd_dict = tribal_commanders[0]
                cmd_name = str(cmd_dict["name"])

                # Get commander colors from our CardData if available
                cmd_card = next((c for c in commanders if c.name == cmd_name), None)
                cmd_colors = self._get_commander_colors(cmd_card) if cmd_card else []

                # Get tribal cards from collection as CardData for proper selection
                tribal_filter_lower = creature_type_filter.lower()
                tribal_card_data = [
                    c
                    for c in all_cards
                    if (c.type_line and tribal_filter_lower in c.type_line.lower())
                    or (c.text and tribal_filter_lower in c.text.lower())
                ]

                # Use _select_best_cards for proper deck building (99 card limit, balanced)
                owned_cards, missing_cards = self._select_best_cards(
                    tribal_card_data,
                    deck_format="commander",
                    archetype=f"{creature_type_filter} Tribal",
                    commander=cmd_card,
                )

                total_cards = len(owned_cards) + len(missing_cards)
                completion = min(total_cards / 99, 1.0)

                reasons = [
                    f"You have {len(tribal_card_data)} {creature_type_filter}s in collection"
                ]
                if cmd_name in collection_cards:
                    reasons.append(f"You own the commander: {cmd_name}")
                else:
                    reasons.append(f"Suggested commander: {cmd_name}")
                if missing_cards:
                    reasons.append(f"Need {len(missing_cards)} basic lands")

                deck_name = _generate_deck_name(
                    commander=cmd_name,
                    tribal=creature_type_filter,
                    set_codes=filters.set_codes if filters else None,
                    seed=hash(cmd_name),
                )

                suggestions.append(
                    DeckSuggestion(
                        name=deck_name,
                        format="commander",
                        commander=cmd_name,
                        archetype=f"{creature_type_filter} Tribal",
                        colors=cmd_colors,
                        key_cards_owned=owned_cards,
                        key_cards_missing=missing_cards
                        if cmd_name in collection_cards
                        else [cmd_name, *missing_cards],
                        completion_pct=completion,
                        reasons=reasons,
                        filter_reasons=filter_reasons or [],
                    )
                )

            return suggestions

        # No specific filter - analyze collection for top tribal types
        types_to_check = tribal_counts.most_common(5)

        for tribal_type, count in types_to_check:
            if count < 8:  # Need at least 8 creatures of the type
                continue

            # Find a commander that matches this tribe (from collection)
            matching_commander: CardData | None = None
            for cmd in commanders:
                if cmd.type_line and tribal_type.lower() in cmd.type_line.lower():
                    matching_commander = cmd
                    break
                if cmd.text and tribal_type.lower() in cmd.text.lower():
                    matching_commander = cmd
                    break

            if not matching_commander:
                continue

            # Get cards of this tribe from collection as CardData
            tribal_type_lower = tribal_type.lower()
            tribal_card_data = [
                c
                for c in all_cards
                if (c.type_line and tribal_type_lower in c.type_line.lower())
                or (c.text and tribal_type_lower in c.text.lower())
            ]

            # Use _select_best_cards for proper deck building
            owned_cards, missing_cards = self._select_best_cards(
                tribal_card_data,
                deck_format="commander",
                archetype=f"{tribal_type} Tribal",
                commander=matching_commander,
            )

            total_cards = len(owned_cards) + len(missing_cards)
            completion = min(total_cards / 99, 1.0)

            reasons = [
                f"You have {count} {tribal_type}s in your collection",
                f"Commander: {matching_commander.name}",
            ]
            if missing_cards:
                reasons.append(f"Need {len(missing_cards)} basic lands")

            deck_name = _generate_deck_name(
                commander=matching_commander.name,
                tribal=tribal_type,
                set_codes=filters.set_codes if filters else None,
                seed=hash(matching_commander.name + tribal_type),
            )

            suggestions.append(
                DeckSuggestion(
                    name=deck_name,
                    format="commander",
                    commander=matching_commander.name,
                    archetype=f"{tribal_type} Tribal",
                    colors=self._get_commander_colors(matching_commander),
                    key_cards_owned=owned_cards,
                    key_cards_missing=missing_cards,
                    completion_pct=completion,
                    reasons=reasons,
                    filter_reasons=filter_reasons or [],
                )
            )

        return suggestions

    def _create_theme_suggestions(
        self,
        commanders: list[CardData],
        all_cards: list[CardData],
        theme_counts: Counter[str],
        _color_counts: Counter[str],
        theme_filter: str | None = None,
        filters: DeckFilters | None = None,
        filter_reasons: list[str] | None = None,
    ) -> list[DeckSuggestion]:
        """Create suggestions based on mechanical themes.

        Uses smart engine for database queries when a specific theme filter is set.
        Falls back to collection-only analysis when browsing top themes.
        """
        suggestions: list[DeckSuggestion] = []
        smart_engine = self._get_smart_engine()
        owned_only = filters.owned_only if filters else True
        color_filter = filters.colors if filters else None
        collection_cards = {c.name for c in all_cards}

        # If filtering by specific theme, use smart engine
        if theme_filter:
            _theme_cards = smart_engine.find_theme_cards(
                theme_filter,
                colors=color_filter,
                collection_cards=collection_cards if owned_only else None,
                limit=50,
            )

            # Find a commander for this theme from collection
            keywords = THEME_KEYWORDS.get(theme_filter, [theme_filter.lower()])
            matching_commander: CardData | None = None

            for cmd in commanders:
                cmd_text = (cmd.text or "").lower()
                for keyword in keywords:
                    if keyword.lower() in cmd_text:
                        matching_commander = cmd
                        break
                if matching_commander:
                    break

            if matching_commander:
                # Get themed cards from collection as CardData for proper selection
                themed_card_data = [
                    c
                    for c in all_cards
                    if any(kw.lower() in (c.text or "").lower() for kw in keywords)
                ]

                # Use _select_best_cards for proper deck building
                owned_cards, missing_cards = self._select_best_cards(
                    themed_card_data,
                    deck_format="commander",
                    archetype=theme_filter,
                    commander=matching_commander,
                )

                total_cards = len(owned_cards) + len(missing_cards)
                completion = min(total_cards / 99, 1.0)

                reasons = [
                    f"You have {len(themed_card_data)} cards supporting {theme_filter}",
                    f"Commander: {matching_commander.name}",
                ]
                if missing_cards:
                    reasons.append(f"Need {len(missing_cards)} basic lands")

                deck_name = _generate_deck_name(
                    commander=matching_commander.name,
                    theme=theme_filter,
                    set_codes=filters.set_codes if filters else None,
                    seed=hash(matching_commander.name + theme_filter),
                )

                suggestions.append(
                    DeckSuggestion(
                        name=deck_name,
                        format="commander",
                        commander=matching_commander.name,
                        archetype=theme_filter,
                        colors=self._get_commander_colors(matching_commander),
                        key_cards_owned=owned_cards,
                        key_cards_missing=missing_cards,
                        completion_pct=completion,
                        reasons=reasons,
                        filter_reasons=filter_reasons or [],
                    )
                )

            return suggestions

        # No specific filter - analyze collection for top themes
        themes_to_check = theme_counts.most_common(3)

        for theme, count in themes_to_check:
            if count < 10:  # Need at least 10 cards with this theme
                continue

            # Find a commander that matches this theme
            matching_commander = None
            keywords = THEME_KEYWORDS.get(theme, [])

            for cmd in commanders:
                cmd_text = (cmd.text or "").lower()
                for keyword in keywords:
                    if keyword.lower() in cmd_text:
                        matching_commander = cmd
                        break
                if matching_commander:
                    break

            if not matching_commander:
                continue

            # Get themed cards from collection as CardData
            themed_card_data = [
                card
                for card in all_cards
                if any(kw.lower() in (card.text or "").lower() for kw in keywords)
            ]

            # Use _select_best_cards for proper deck building
            owned_cards, missing_cards = self._select_best_cards(
                themed_card_data,
                deck_format="commander",
                archetype=theme,
                commander=matching_commander,
            )

            total_cards = len(owned_cards) + len(missing_cards)
            completion = min(total_cards / 99, 1.0)

            reasons = [
                f"You have {count} cards supporting {theme}",
                f"Commander: {matching_commander.name}",
            ]
            if missing_cards:
                reasons.append(f"Need {len(missing_cards)} basic lands")

            deck_name = _generate_deck_name(
                commander=matching_commander.name,
                theme=theme,
                set_codes=filters.set_codes if filters else None,
                seed=hash(matching_commander.name + theme),
            )

            suggestions.append(
                DeckSuggestion(
                    name=deck_name,
                    format="commander",
                    commander=matching_commander.name,
                    archetype=theme,
                    colors=self._get_commander_colors(matching_commander),
                    key_cards_owned=owned_cards,
                    key_cards_missing=missing_cards,
                    completion_pct=completion,
                    reasons=reasons,
                    filter_reasons=filter_reasons or [],
                )
            )

        return suggestions

    async def find_standard_decks(
        self,
        _collection_cards: set[str],
        card_data: list[CardData] | None = None,
        min_completion: float = 0.0,
        limit: int = 10,
        filters: DeckFilters | None = None,
    ) -> list[DeckSuggestion]:
        """Find Standard decks the user can build."""
        suggestions: list[DeckSuggestion] = []

        if not card_data:
            return suggestions

        # Filter out art series, token sets, and other excluded sets
        card_data = [c for c in card_data if not is_excluded_set(c.set_code)]

        # Save all lands from full collection BEFORE applying set filter
        # These can be used to fill land slots even when filtering by set
        all_collection_lands: list[CardData] | None = None
        if filters and filters.set_codes:
            all_collection_lands = [c for c in card_data if c.get_card_type() == "land"]

        # Apply set filter FIRST if specified - this is strict filtering
        if filters and filters.set_codes:
            set_codes_upper = {code.upper() for code in filters.set_codes}
            card_data = [
                c for c in card_data if c.set_code and c.set_code.upper() in set_codes_upper
            ]

        # Pre-filter card data by keyword if specified
        if filters and filters.keyword:
            keyword_lower = filters.keyword.lower()
            card_data = [
                c
                for c in card_data
                if (c.text and keyword_lower in c.text.lower())
                or (c.type_line and keyword_lower in c.type_line.lower())
            ]

        # Count colors
        color_counts = self._count_colors(card_data)

        # Generate color-based suggestions with flavorful names
        color_combos = [
            (["R"], "Flame & Fury", "Aggro"),
            (["W"], "Dawn's Legion", "Aggro"),
            (["B"], "Shadow's Grasp", "Midrange"),
            (["G"], "Primal Might", "Aggro"),
            (["U"], "Mind's Dominion", "Tempo"),
            (["W", "U"], "Azorius Authority", "Control"),
            (["U", "B"], "Whispers in the Dark", "Control"),
            (["B", "R"], "Blood & Fire", "Aggro"),
            (["R", "G"], "Wild Rampage", "Aggro"),
            (["G", "W"], "Nature's Conclave", "Midrange"),
            (["W", "B"], "Twilight Syndicate", "Midrange"),
            (["U", "R"], "Arcane Tempest", "Tempo"),
            (["B", "G"], "Rot & Renewal", "Midrange"),
            (["R", "W"], "Righteous Flames", "Aggro"),
            (["G", "U"], "Evolving Tides", "Ramp"),
        ]

        for colors, base_name, archetype in color_combos:
            # Apply color filter - skip if colors don't match filter
            if filters and filters.colors:
                filter_set = set(filters.colors)
                deck_set = set(colors)
                # Deck colors must be subset of or equal to filter colors
                if not deck_set.issubset(filter_set):
                    continue

            # Check if user has enough cards in these colors
            card_count = sum(color_counts.get(c, 0) for c in colors)

            # For mono-color, need 20+ cards; for two-color, need 30+
            min_cards = 20 if len(colors) == 1 else 30
            if card_count < min_cards:
                continue

            # Get cards that fit (as CardData) - use color identity for lands
            fitting_card_data: list[CardData] = []
            tribal_filter_lower = (
                filters.creature_type.lower() if filters and filters.creature_type else None
            )

            for card in card_data:
                # Apply tribal filter if active
                if tribal_filter_lower:
                    card_type = (card.type_line or "").lower()
                    card_text = (card.text or "").lower()
                    is_creature = "creature" in card_type
                    is_tribal_creature = (
                        tribal_filter_lower in card_type or tribal_filter_lower in card_text
                    )
                    # Skip non-tribal creatures, keep lands and non-creatures
                    if is_creature and not is_tribal_creature:
                        continue

                card_identity = card.get_color_identity()
                # Card fits if colorless or its identity is subset of deck colors
                if not card_identity or set(card_identity).issubset(set(colors)):
                    fitting_card_data.append(card)

            # Select best cards for a 60-card Standard deck
            # Pass all_lands from full collection to fill land slots when set-filtered
            owned_cards, missing_cards = self._select_best_cards(
                fitting_card_data,
                deck_format="standard",
                archetype=archetype,
                all_lands=all_collection_lands,
            )

            total_cards = len(owned_cards) + len(missing_cards)
            completion = min(total_cards / 60, 1.0)

            if completion >= min_completion:
                # Count lands added from outside the set filter
                set_land_names = {
                    fc.name for fc in fitting_card_data if fc.get_card_type() == "land"
                }
                lands_from_collection = sum(
                    1
                    for c in owned_cards
                    if any(land.name == c for land in (all_collection_lands or []))
                    and c not in set_land_names
                )

                reasons = [
                    f"{len(fitting_card_data)} cards in these colors",
                    f"Strategy: {archetype}",
                ]
                if lands_from_collection > 0:
                    reasons.append(f"Using {lands_from_collection} lands from your collection")
                if missing_cards:
                    reasons.append(f"Need {len(missing_cards)} basic lands")

                # Generate filter_reasons
                filter_reasons: list[str] = []
                if filters:
                    if filters.colors:
                        color_names = {
                            "W": "White",
                            "U": "Blue",
                            "B": "Black",
                            "R": "Red",
                            "G": "Green",
                        }
                        color_str = "/".join(color_names.get(c, c) for c in sorted(filters.colors))
                        filter_reasons.append(f"Matches {color_str} colors")
                    if filters.creature_type:
                        tribal_count = sum(
                            1
                            for c in fitting_card_data
                            if c.type_line and filters.creature_type.lower() in c.type_line.lower()
                        )
                        if tribal_count > 0:
                            filter_reasons.append(
                                f"Has {tribal_count} {filters.creature_type} creatures"
                            )
                    if filters.set_codes:
                        set_list = ", ".join(sorted(filters.set_codes)[:5])
                        if len(filters.set_codes) > 5:
                            set_list += f" (+{len(filters.set_codes) - 5} more)"
                        filter_reasons.append(f"Cards from: {set_list}")

                # Analyze combo potential
                complete_combos, near_combos, combo_score = await self._score_combo_potential(
                    deck_cards=owned_cards,
                    commander_identity=colors,
                )

                # Identify limited bombs (S/A tier cards from 17Lands)
                limited_bombs: list[str] = []
                for card_name in owned_cards:
                    _, tier, is_bomb = self._score_limited_stats(card_name)
                    if tier in ("S", "A") or is_bomb:
                        limited_bombs.append(card_name)

                # Add combo/bomb reasons
                if complete_combos:
                    reasons.append(f"{len(complete_combos)} complete combo(s)")
                if limited_bombs:
                    reasons.append(f"{len(limited_bombs)} Limited bombs (S/A tier)")

                # Generate creative deck name with set flavor
                deck_name = _generate_deck_name(
                    tribal=filters.creature_type if filters else None,
                    theme=archetype,
                    set_codes=filters.set_codes if filters else None,
                    archetype=base_name,
                    seed=hash(tuple(colors)),
                )

                suggestions.append(
                    DeckSuggestion(
                        name=deck_name,
                        format="standard",
                        commander=None,
                        archetype=archetype,
                        colors=colors,
                        key_cards_owned=owned_cards,
                        key_cards_missing=missing_cards,
                        completion_pct=completion,
                        reasons=reasons,
                        filter_reasons=filter_reasons,
                        near_combos=near_combos,
                        complete_combos=complete_combos,
                        combo_score=combo_score,
                        limited_bombs=limited_bombs,
                    )
                )

        suggestions.sort(key=lambda s: -s.completion_pct)
        return suggestions[:limit]

    async def find_best_commanders(
        self,
        archetype: str | None = None,
        tribe: str | None = None,
        collection: list[CardData] | None = None,
        filters: DeckFilters | None = None,
        limit: int = 10,
    ) -> list[CommanderMatch]:
        """Find optimal commanders for a strategy.

        Scores commanders by:
        - EDHREC rank (popularity/proven power)
        - Text matching theme keywords
        - Combo potential (via SpellbookComboDetector)
        - Synergy with owned cards (via SynergyScorer)
        - 17Lands data if available

        Args:
            archetype: Strategy like "Tokens", "Graveyard", "Counters"
            tribe: Creature type like "Zombie", "Elf", "Dragon"
            collection: User's card collection for synergy scoring
            filters: Color and other filters
            limit: Maximum commanders to return

        Returns:
            List of CommanderMatch sorted by total_score descending
        """
        from .spellbook_combos import get_spellbook_detector

        smart_engine = self._get_smart_engine()
        collection_names = {c.name for c in collection} if collection else set()

        # Step 1: Query potential commanders
        potential_commanders: list[dict[str, Any]] = []
        if tribe:
            # Use tribal commander search
            potential_commanders = smart_engine.find_tribal_commanders(
                tribe,
                colors=filters.colors if filters else None,
                limit=limit * 3,  # Get more candidates for scoring
            )
        elif archetype and archetype in THEME_KEYWORDS:
            # Query commanders matching archetype keywords
            potential_commanders = self._query_archetype_commanders(
                archetype,
                colors=filters.colors if filters else None,
                limit=limit * 3,
            )
        else:
            # Generic: get top EDHREC commanders with color filter
            potential_commanders = self._query_top_commanders(
                colors=filters.colors if filters else None,
                limit=limit * 3,
            )

        if not potential_commanders:
            return []

        # Step 2: Get combo detector
        combo_detector = await get_spellbook_detector()
        if combo_detector.is_available:
            await combo_detector.initialize()

        # Step 3: Score each commander
        matches: list[CommanderMatch] = []
        for cmd_data in potential_commanders:
            # Extract fields with proper types
            name = str(cmd_data.get("name", ""))
            type_line = str(cmd_data.get("type_line", ""))
            color_identity_raw = cmd_data.get("color_identity")
            if isinstance(color_identity_raw, list):
                color_identity = [str(c) for c in color_identity_raw]
            else:
                color_identity = []
            oracle_text = cmd_data.get("oracle_text")
            edhrec_rank = cmd_data.get("edhrec_rank")

            match = CommanderMatch(
                name=name,
                type_line=type_line,
                color_identity=color_identity,
                oracle_text=str(oracle_text) if oracle_text else None,
                edhrec_rank=int(edhrec_rank) if edhrec_rank else None,
            )

            # Score components
            match.edhrec_score = self._score_edhrec_rank(match.edhrec_rank)
            match.theme_score = self._score_theme_match(
                match.oracle_text or "",
                archetype=archetype,
                tribe=tribe,
            )
            match.combo_score, match.combo_count = self._score_commander_combos(
                match.name,
                collection_names,
                combo_detector,
            )
            match.synergy_score, match.synergy_cards = self._score_commander_synergy(
                cmd_data,
                collection,
                filters,
            )
            match.limited_score = self._score_limited_for_commander(match.name)

            # Ownership bonus
            match.is_owned = match.name in collection_names
            match.ownership_bonus = 0.3 if match.is_owned else 0.0

            # Calculate total score
            match.total_score = self._calculate_commander_total_score(match)
            match.reasons = self._generate_commander_reasons(match, archetype, tribe)

            matches.append(match)

        # Step 4: Sort and return
        matches.sort(key=lambda x: -x.total_score)
        return matches[:limit]

    def _score_edhrec_rank(self, rank: int | None) -> float:
        """Convert EDHREC rank to 0-1 score (lower rank = higher score)."""
        return score_edhrec_rank(rank)

    def _score_theme_match(
        self,
        oracle_text: str,
        archetype: str | None = None,
        tribe: str | None = None,
    ) -> float:
        """Score how well commander matches the requested theme."""
        return score_theme_match(oracle_text, archetype, tribe)

    def _score_commander_combos(
        self,
        commander_name: str,
        collection_names: set[str],
        combo_detector: Any,
    ) -> tuple[float, int]:
        """Score combo potential using SpellbookComboDetector."""
        return score_commander_combos(commander_name, collection_names, combo_detector)

    def _score_commander_synergy(
        self,
        commander_data: dict[str, Any],
        collection: list[CardData] | None,
        _filters: DeckFilters | None,
    ) -> tuple[float, list[str]]:
        """Score synergy between commander and user's collection."""
        return score_commander_synergy(commander_data, collection, self._card_encoder)

    def _score_limited_for_commander(self, commander_name: str) -> float:
        """Get 17Lands-based score for commander (if data exists)."""
        return score_limited_for_commander(commander_name, self._get_gameplay_db())

    def _calculate_commander_total_score(self, match: CommanderMatch) -> float:
        """Calculate weighted total score for commander."""
        return calculate_commander_total_score(match)

    def _generate_commander_reasons(
        self,
        match: CommanderMatch,
        archetype: str | None,
        tribe: str | None,
    ) -> list[str]:
        """Generate human-readable reasons for commander score."""
        return generate_commander_reasons(match, archetype, tribe)

    def _query_archetype_commanders(
        self,
        archetype: str,
        colors: list[str] | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """Find commanders matching an archetype's keywords."""
        import json
        import sqlite3

        from mtg_core.config import get_settings

        settings = get_settings()
        db_path = settings.mtg_db_path

        if not db_path.exists():
            return []

        # Get theme keywords
        keywords = THEME_KEYWORDS.get(archetype, [archetype.lower()])

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Build OR conditions for keywords
        keyword_conditions = " OR ".join(["LOWER(oracle_text) LIKE ?" for _ in keywords])

        query = f"""
            SELECT DISTINCT
                name,
                type_line,
                oracle_text,
                color_identity,
                edhrec_rank
            FROM cards
            WHERE LOWER(type_line) LIKE '%legendary%'
              AND LOWER(type_line) LIKE '%creature%'
              AND legal_commander = 1
              AND (is_token = 0 OR is_token IS NULL)
              AND ({keyword_conditions})
            ORDER BY edhrec_rank ASC NULLS LAST
            LIMIT ?
        """

        params = [f"%{kw.lower()}%" for kw in keywords] + [limit]
        cursor = conn.execute(query, params)

        results = []
        for row in cursor:
            # Apply color filter
            if colors:
                card_identity = json.loads(row["color_identity"] or "[]")
                if card_identity and not set(card_identity).issubset(set(colors)):
                    continue

            results.append(
                {
                    "name": row["name"],
                    "type_line": row["type_line"],
                    "oracle_text": row["oracle_text"],
                    "color_identity": json.loads(row["color_identity"] or "[]"),
                    "edhrec_rank": row["edhrec_rank"],
                }
            )

        conn.close()
        return results

    def _query_top_commanders(
        self,
        colors: list[str] | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """Get top commanders by EDHREC rank with optional color filter."""
        import json
        import sqlite3

        from mtg_core.config import get_settings

        settings = get_settings()
        db_path = settings.mtg_db_path

        if not db_path.exists():
            return []

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        query = """
            SELECT DISTINCT
                name,
                type_line,
                oracle_text,
                color_identity,
                edhrec_rank
            FROM cards
            WHERE LOWER(type_line) LIKE '%legendary%'
              AND LOWER(type_line) LIKE '%creature%'
              AND legal_commander = 1
              AND (is_token = 0 OR is_token IS NULL)
              AND edhrec_rank IS NOT NULL
            ORDER BY edhrec_rank ASC
            LIMIT ?
        """

        cursor = conn.execute(query, [limit])

        results = []
        for row in cursor:
            # Apply color filter
            if colors:
                card_identity = json.loads(row["color_identity"] or "[]")
                if card_identity and not set(card_identity).issubset(set(colors)):
                    continue

            results.append(
                {
                    "name": row["name"],
                    "type_line": row["type_line"],
                    "oracle_text": row["oracle_text"],
                    "color_identity": json.loads(row["color_identity"] or "[]"),
                    "edhrec_rank": row["edhrec_rank"],
                }
            )

        conn.close()
        return results

    async def find_buildable_decks(
        self,
        collection_cards: set[str],
        format: str = "commander",
        card_data: list[CardData] | None = None,
        min_completion: float = 0.0,
        limit: int = 10,
        filters: DeckFilters | None = None,
    ) -> list[DeckSuggestion]:
        """Find decks the user can build in the specified format.

        Args:
            collection_cards: Set of card names the user owns
            format: "commander" or "standard"
            card_data: Optional list of CardData for deeper analysis
            min_completion: Minimum completion percentage to include
            limit: Maximum suggestions to return
            filters: Optional filters for colors, tribal, theme, keyword
        """
        if format.lower() == "commander":
            return await self.find_commander_decks(
                collection_cards,
                card_data=card_data,
                min_completion=min_completion,
                limit=limit,
                filters=filters,
            )
        elif format.lower() == "standard":
            return await self.find_standard_decks(
                collection_cards,
                card_data=card_data,
                min_completion=min_completion,
                limit=limit,
                filters=filters,
            )
        else:
            logger.warning(f"Unsupported format: {format}")
            return []


# Global singleton
_deck_finder: DeckFinder | None = None


def get_deck_finder() -> DeckFinder:
    """Get or create the global deck finder."""
    global _deck_finder
    if _deck_finder is None:
        _deck_finder = DeckFinder()
    return _deck_finder
