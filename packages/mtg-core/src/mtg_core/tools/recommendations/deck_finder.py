"""Deck recommendations based on user's collection.

Analyzes a user's collection to suggest deck archetypes they can build
for Commander and Standard formats.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_core.data.database import MTGDatabase

logger = logging.getLogger(__name__)


@dataclass
class CardData:
    """Minimal card data for deck analysis."""

    name: str
    type_line: str | None = None
    colors: list[str] | None = None
    mana_cost: str | None = None
    text: str | None = None
    color_identity: list[str] | None = None  # For lands and cards with colored mana in text

    def get_color_identity(self) -> list[str]:
        """Get color identity - use explicit identity if set, otherwise derive from colors/mana."""
        if self.color_identity:
            return self.color_identity
        if self.colors:
            return self.colors
        # Try to derive from mana cost
        if self.mana_cost:
            identity = []
            for color in ["W", "U", "B", "R", "G"]:
                if color in self.mana_cost:
                    identity.append(color)
            if identity:
                return identity
        return []  # Truly colorless

    def get_cmc(self) -> int:
        """Extract converted mana cost from mana_cost string."""
        if not self.mana_cost:
            return 0
        cmc = 0
        import re
        # Count colored symbols
        cmc += len(re.findall(r"\{[WUBRG]\}", self.mana_cost))
        # Count hybrid (each counts as 1)
        cmc += len(re.findall(r"\{[WUBRG]/[WUBRG]\}", self.mana_cost))
        # Count generic mana
        for match in re.findall(r"\{(\d+)\}", self.mana_cost):
            cmc += int(match)
        return cmc

    def get_card_type(self) -> str:
        """Get primary card type for categorization."""
        # Fallback for basic lands without type_line data
        if not self.type_line:
            basic_lands = {"Plains", "Island", "Swamp", "Mountain", "Forest",
                          "Snow-Covered Plains", "Snow-Covered Island",
                          "Snow-Covered Swamp", "Snow-Covered Mountain",
                          "Snow-Covered Forest", "Wastes"}
            if self.name in basic_lands:
                return "land"
            return "unknown"
        type_lower = self.type_line.lower()
        if "creature" in type_lower:
            return "creature"
        elif "instant" in type_lower or "sorcery" in type_lower:
            return "spell"
        elif "artifact" in type_lower:
            return "artifact"
        elif "enchantment" in type_lower:
            return "enchantment"
        elif "planeswalker" in type_lower:
            return "planeswalker"
        elif "land" in type_lower:
            return "land"
        return "other"


# Target deck composition for balanced decks
DECK_TARGETS: dict[str, dict[str, int | tuple[int, int]]] = {
    "commander": {
        "total": 99,  # 99 + commander
        "creature": (25, 35),  # min, max
        "spell": (10, 20),
        "artifact": (8, 15),
        "enchantment": (5, 12),
        "land": (35, 38),
        "planeswalker": (0, 3),
    },
    "standard": {
        "total": 60,
        "creature": (20, 28),
        "spell": (8, 16),
        "artifact": (0, 6),
        "enchantment": (0, 6),
        "land": (22, 26),
        "planeswalker": (0, 3),
    },
}


@dataclass
class DeckSuggestion:
    """A suggested deck archetype based on collection."""

    name: str
    format: str  # "commander" or "standard"
    commander: str | None = None  # For commander format
    archetype: str | None = None  # e.g., "Aggro", "Control", "Combo"
    colors: list[str] = field(default_factory=list)
    key_cards_owned: list[str] = field(default_factory=list)
    key_cards_missing: list[str] = field(default_factory=list)
    completion_pct: float = 0.0
    estimated_cost: float = 0.0  # Cost to complete in USD
    reasons: list[str] = field(default_factory=list)


# Theme keywords to detect deck archetypes
THEME_KEYWORDS: dict[str, list[str]] = {
    "Tokens": ["create", "token", "populate", "convoke"],
    "Counters": ["+1/+1 counter", "proliferate", "counter on"],
    "Graveyard": ["graveyard", "dies", "sacrifice", "reanimate", "return from"],
    "Artifacts": ["artifact", "equipment", "vehicle", "metalcraft"],
    "Enchantments": ["enchantment", "constellation", "aura"],
    "Spellslinger": ["instant", "sorcery", "prowess", "magecraft"],
    "Lifegain": ["gain life", "lifelink", "whenever you gain life"],
    "Mill": ["mill", "library into", "graveyard from library"],
    "Voltron": ["equipment", "aura", "attach", "equipped creature"],
    "Stax": ["can't", "each player", "sacrifice a", "opponents can't"],
}

# Common tribal types to detect
TRIBAL_TYPES: list[str] = [
    "Goblin",
    "Elf",
    "Zombie",
    "Vampire",
    "Dragon",
    "Angel",
    "Demon",
    "Wizard",
    "Warrior",
    "Soldier",
    "Knight",
    "Merfolk",
    "Human",
    "Beast",
    "Dinosaur",
    "Pirate",
    "Cat",
    "Dog",
    "Bird",
    "Elemental",
    "Spirit",
    "Sliver",
    "Fungus",
    "Rat",
    "Snake",
    "Spider",
    "Treefolk",
]


class DeckFinder:
    """Recommend deck archetypes based on collection."""

    def __init__(self, db: MTGDatabase | None = None) -> None:
        self._db = db
        self._initialized = False

    async def initialize(self, db: MTGDatabase) -> None:
        """Initialize with card data from database."""
        self._db = db
        self._initialized = True

    def _score_card_for_deck(
        self,
        card: CardData,
        archetype: str | None,
        _commander_text: str | None,
        theme_keywords: list[str],
    ) -> float:
        """Score a card's fit for a specific deck.

        Higher scores = better fit.
        """
        score = 1.0  # Base score

        card_text = (card.text or "").lower()
        card_type = card.get_card_type()

        # Synergy with archetype keywords
        if archetype:
            archetype_lower = archetype.lower()
            # Check if card supports the archetype
            if archetype_lower in card_text:
                score += 2.0

        # Synergy with theme keywords from commander
        for keyword in theme_keywords:
            if keyword.lower() in card_text:
                score += 1.5

        # Bonus for removal/interaction
        removal_keywords = ["destroy", "exile", "counter target", "deal.*damage"]
        import re
        for keyword in removal_keywords:
            if re.search(keyword, card_text):
                score += 1.0
                break

        # Bonus for card advantage
        if "draw" in card_text and "card" in card_text:
            score += 1.0

        # Bonus for ramp
        if "add" in card_text and any(c in card_text for c in ["{w}", "{u}", "{b}", "{r}", "{g}", "mana"]):
            score += 0.8

        # Legendary creatures get a small boost (potential sub-commanders)
        if card.type_line and "legendary" in card.type_line.lower():
            score += 0.5

        # Planeswalkers are generally valuable
        if card_type == "planeswalker":
            score += 1.0

        return score

    def _select_best_cards(
        self,
        cards: list[CardData],
        deck_format: str,
        archetype: str | None = None,
        commander: CardData | None = None,
    ) -> tuple[list[str], list[str]]:
        """Select the best cards for a deck, respecting type balance and deck size."""
        targets = DECK_TARGETS.get(deck_format, DECK_TARGETS["commander"])
        total = targets["total"]
        max_cards = total if isinstance(total, int) else 99

        # Extract theme keywords from commander
        theme_keywords: list[str] = []
        commander_text = None
        if commander and commander.text:
            commander_text = commander.text.lower()
            # Extract relevant keywords
            for _theme, keywords in THEME_KEYWORDS.items():
                for kw in keywords:
                    if kw.lower() in commander_text:
                        theme_keywords.append(kw)

        # Score all cards
        scored_cards: list[tuple[float, CardData]] = []
        for card in cards:
            score = self._score_card_for_deck(card, archetype, commander_text, theme_keywords)
            scored_cards.append((score, card))

        # Sort by score descending
        scored_cards.sort(key=lambda x: -x[0])

        # Get commander's color identity for filtering
        commander_identity = set(commander.get_color_identity()) if commander else set()

        # Filter cards by color identity first
        valid_cards: list[tuple[float, CardData]] = []
        for score, card in scored_cards:
            if commander_identity:
                card_identity = set(card.get_color_identity())
                if card_identity and not card_identity.issubset(commander_identity):
                    continue
            valid_cards.append((score, card))

        # Two-pass selection: first ensure minimums, then fill with best cards
        type_counts: Counter[str] = Counter()
        owned_cards: list[str] = []
        missing_cards: list[str] = []  # Cards we need to add (like basic lands)
        selected_names: set[str] = set()

        # Pass 1: Ensure minimum lands (critical for playable decks)
        land_min = 22 if deck_format == "standard" else 35
        land_cards = [(s, c) for s, c in valid_cards if c.get_card_type() == "land"]

        # Add owned lands first
        for _score, card in land_cards[:land_min]:
            if card.name not in selected_names:
                owned_cards.append(card.name)
                selected_names.add(card.name)
                type_counts["land"] += 1

        # If we don't have enough lands, add basic lands (always available)
        if type_counts["land"] < land_min:
            # Get deck colors from commander or from card color identities
            deck_colors: set[str] = set()
            if commander_identity:
                deck_colors = commander_identity
            else:
                # Derive from non-land cards in the deck
                for _score, card in valid_cards:
                    if card.get_card_type() != "land":
                        deck_colors.update(card.get_color_identity())

            # Map colors to basic lands
            color_to_basic = {
                "W": "Plains", "U": "Island", "B": "Swamp",
                "R": "Mountain", "G": "Forest"
            }

            # Add basic lands evenly distributed across colors
            colors_list = [c for c in deck_colors if c in color_to_basic]
            if not colors_list:
                colors_list = ["R"]  # Default to Mountain for colorless

            lands_needed = land_min - type_counts["land"]
            lands_per_color = max(1, lands_needed // len(colors_list))

            for color in colors_list:
                basic_name = color_to_basic[color]
                for _ in range(lands_per_color):
                    if type_counts["land"] >= land_min:
                        break
                    missing_cards.append(basic_name)
                    type_counts["land"] += 1

            # Fill remaining with first color's basic
            while type_counts["land"] < land_min:
                missing_cards.append(color_to_basic[colors_list[0]])
                type_counts["land"] += 1

        # Pass 2: Fill remaining slots with highest-scoring cards
        total_selected = len(owned_cards) + len(missing_cards)
        for _score, card in valid_cards:
            if total_selected >= max_cards:
                break
            if card.name in selected_names:
                continue

            card_type = card.get_card_type()
            type_limit = targets.get(card_type, (0, 999))
            max_of_type = type_limit[1] if isinstance(type_limit, tuple) else 999

            if type_counts[card_type] < max_of_type:
                owned_cards.append(card.name)
                selected_names.add(card.name)
                type_counts[card_type] += 1
                total_selected += 1

        return (owned_cards, missing_cards)

    def find_commander_decks(
        self,
        _collection_cards: set[str],
        card_data: list[CardData] | None = None,
        min_completion: float = 0.0,
        limit: int = 10,
    ) -> list[DeckSuggestion]:
        """Find Commander decks the user can build.

        Args:
            collection_cards: Set of card names the user owns
            card_data: Optional list of CardData for deeper analysis
            min_completion: Minimum completion percentage to include
            limit: Maximum suggestions to return

        Returns:
            List of deck suggestions sorted by relevance
        """
        suggestions: list[DeckSuggestion] = []

        if not card_data:
            # Without card data, we can't do much analysis
            return suggestions

        # Find potential commanders (legendary creatures)
        potential_commanders: list[CardData] = []
        for card in card_data:
            if card.type_line and self._is_valid_commander(card.type_line):
                potential_commanders.append(card)

        if not potential_commanders:
            # No legendary creatures found
            return suggestions

        # Analyze collection for tribal themes
        tribal_counts = self._count_tribal_types(card_data)

        # Analyze collection for mechanic themes
        theme_counts = self._count_themes(card_data)

        # Analyze colors in collection
        color_counts = self._count_colors(card_data)

        # Generate suggestions for each potential commander
        for commander in potential_commanders:
            suggestion = self._create_commander_suggestion(
                commander,
                card_data,
                tribal_counts,
                theme_counts,
                color_counts,
            )
            if suggestion and suggestion.completion_pct >= min_completion:
                suggestions.append(suggestion)

        # Also add tribal-based suggestions if strong tribal presence
        tribal_suggestions = self._create_tribal_suggestions(
            potential_commanders, card_data, tribal_counts, color_counts
        )
        suggestions.extend(tribal_suggestions)

        # Also add theme-based suggestions
        theme_suggestions = self._create_theme_suggestions(
            potential_commanders, card_data, theme_counts, color_counts
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

    def _create_commander_suggestion(
        self,
        commander: CardData,
        all_cards: list[CardData],
        tribal_counts: Counter[str],
        theme_counts: Counter[str],
        _color_counts: Counter[str],
    ) -> DeckSuggestion | None:
        """Create a deck suggestion around a specific commander."""
        commander_colors = self._get_commander_colors(commander)

        # Get cards that fit this commander's colors (as CardData objects)
        fitting_card_data: list[CardData] = []
        for card in all_cards:
            # Skip the commander itself
            if card.name == commander.name:
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

        reasons: list[str] = []
        reasons.append("You own this legendary creature")
        reasons.append(f"{len(fitting_card_data)} cards in these colors")

        if archetype:
            reasons.append(f"Potential strategy: {archetype}")

        if missing_cards:
            reasons.append(f"Need {len(missing_cards)} basic lands")

        return DeckSuggestion(
            name=f"{commander.name} Commander",
            format="commander",
            commander=commander.name,
            archetype=archetype,
            colors=commander_colors,
            key_cards_owned=owned_cards,
            key_cards_missing=missing_cards,
            completion_pct=completion,
            reasons=reasons,
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
    ) -> list[DeckSuggestion]:
        """Create suggestions based on tribal themes in collection."""
        suggestions: list[DeckSuggestion] = []

        # Only suggest tribal decks if there's a significant tribal presence
        for tribal_type, count in tribal_counts.most_common(5):
            if count < 8:  # Need at least 8 creatures of the type
                continue

            # Find a commander that matches this tribe
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

            # Get cards of this tribe
            tribal_cards = [
                c.name
                for c in all_cards
                if c.type_line and tribal_type.lower() in c.type_line.lower()
            ]

            completion = min(count / 30, 1.0)  # 30 tribal creatures is solid

            suggestions.append(
                DeckSuggestion(
                    name=f"{tribal_type} Tribal",
                    format="commander",
                    commander=matching_commander.name,
                    archetype=f"{tribal_type} Tribal",
                    colors=self._get_commander_colors(matching_commander),
                    key_cards_owned=tribal_cards,
                    key_cards_missing=[],
                    completion_pct=completion,
                    reasons=[
                        f"You have {count} {tribal_type}s in your collection",
                        f"Commander: {matching_commander.name}",
                    ],
                )
            )

        return suggestions

    def _create_theme_suggestions(
        self,
        commanders: list[CardData],
        all_cards: list[CardData],
        theme_counts: Counter[str],
        _color_counts: Counter[str],
    ) -> list[DeckSuggestion]:
        """Create suggestions based on mechanical themes."""
        suggestions: list[DeckSuggestion] = []

        for theme, count in theme_counts.most_common(3):
            if count < 10:  # Need at least 10 cards with this theme
                continue

            # Find a commander that matches this theme
            matching_commander: CardData | None = None
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

            # Get themed cards
            themed_cards: list[str] = []
            for card in all_cards:
                card_text = (card.text or "").lower()
                for keyword in keywords:
                    if keyword.lower() in card_text:
                        themed_cards.append(card.name)
                        break

            completion = min(count / 40, 1.0)

            suggestions.append(
                DeckSuggestion(
                    name=f"{theme} Strategy",
                    format="commander",
                    commander=matching_commander.name,
                    archetype=theme,
                    colors=self._get_commander_colors(matching_commander),
                    key_cards_owned=themed_cards,
                    key_cards_missing=[],
                    completion_pct=completion,
                    reasons=[
                        f"You have {count} cards supporting {theme}",
                        f"Commander: {matching_commander.name}",
                    ],
                )
            )

        return suggestions

    def find_standard_decks(
        self,
        _collection_cards: set[str],
        card_data: list[CardData] | None = None,
        min_completion: float = 0.0,
        limit: int = 10,
    ) -> list[DeckSuggestion]:
        """Find Standard decks the user can build."""
        suggestions: list[DeckSuggestion] = []

        if not card_data:
            return suggestions

        # Count colors
        color_counts = self._count_colors(card_data)

        # Generate color-based suggestions
        color_combos = [
            (["R"], "Mono-Red Aggro", "Aggro"),
            (["W"], "Mono-White Aggro", "Aggro"),
            (["B"], "Mono-Black Midrange", "Midrange"),
            (["G"], "Mono-Green Stompy", "Aggro"),
            (["U"], "Mono-Blue Tempo", "Tempo"),
            (["W", "U"], "Azorius Control", "Control"),
            (["U", "B"], "Dimir Control", "Control"),
            (["B", "R"], "Rakdos Aggro", "Aggro"),
            (["R", "G"], "Gruul Aggro", "Aggro"),
            (["G", "W"], "Selesnya Tokens", "Midrange"),
            (["W", "B"], "Orzhov Midrange", "Midrange"),
            (["U", "R"], "Izzet Spells", "Tempo"),
            (["B", "G"], "Golgari Midrange", "Midrange"),
            (["R", "W"], "Boros Aggro", "Aggro"),
            (["G", "U"], "Simic Ramp", "Ramp"),
        ]

        for colors, name, archetype in color_combos:
            # Check if user has enough cards in these colors
            card_count = sum(color_counts.get(c, 0) for c in colors)

            # For mono-color, need 20+ cards; for two-color, need 30+
            min_cards = 20 if len(colors) == 1 else 30
            if card_count < min_cards:
                continue

            # Get cards that fit (as CardData) - use color identity for lands
            fitting_card_data: list[CardData] = []
            for card in card_data:
                card_identity = card.get_color_identity()
                # Card fits if colorless or its identity is subset of deck colors
                if not card_identity or set(card_identity).issubset(set(colors)):
                    fitting_card_data.append(card)

            # Select best cards for a 60-card Standard deck
            owned_cards, missing_cards = self._select_best_cards(
                fitting_card_data,
                deck_format="standard",
                archetype=archetype,
            )

            total_cards = len(owned_cards) + len(missing_cards)
            completion = min(total_cards / 60, 1.0)

            if completion >= min_completion:
                reasons = [
                    f"{len(fitting_card_data)} cards in these colors",
                    f"Strategy: {archetype}",
                ]
                if missing_cards:
                    reasons.append(f"Need {len(missing_cards)} basic lands")

                suggestions.append(
                    DeckSuggestion(
                        name=name,
                        format="standard",
                        commander=None,
                        archetype=archetype,
                        colors=colors,
                        key_cards_owned=owned_cards,
                        key_cards_missing=missing_cards,
                        completion_pct=completion,
                        reasons=reasons,
                    )
                )

        suggestions.sort(key=lambda s: -s.completion_pct)
        return suggestions[:limit]

    def find_buildable_decks(
        self,
        collection_cards: set[str],
        format: str = "commander",
        card_data: list[CardData] | None = None,
        min_completion: float = 0.0,
        limit: int = 10,
    ) -> list[DeckSuggestion]:
        """Find decks the user can build in the specified format."""
        if format.lower() == "commander":
            return self.find_commander_decks(
                collection_cards,
                card_data=card_data,
                min_completion=min_completion,
                limit=limit,
            )
        elif format.lower() == "standard":
            return self.find_standard_decks(
                collection_cards,
                card_data=card_data,
                min_completion=min_completion,
                limit=limit,
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
