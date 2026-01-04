"""Deck impact calculator - shows what changes when adding a card to a deck."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from mtg_core.tools.deck import THEME_MATCHUPS
from mtg_core.tools.recommendations.features import (
    CardEncoder,
    CardFeatures,
    DeckEncoder,
    DeckFeatures,
    get_keyword_abilities,
)

if TYPE_CHECKING:
    from mtg_core.data.database import UnifiedDatabase

logger = logging.getLogger(__name__)


class StatChange(BaseModel):
    """A single stat change when adding a card."""

    name: str
    old_value: float | int | str
    new_value: float | int | str
    is_positive: bool | None = None  # None = neutral
    category: str = "stat"  # stat, keyword, theme, type

    @property
    def delta(self) -> float:
        """Get numeric delta if applicable."""
        if isinstance(self.old_value, (int, float)) and isinstance(self.new_value, (int, float)):
            return self.new_value - self.old_value
        return 0.0

    @property
    def display_delta(self) -> str:
        """Get formatted delta string."""
        if isinstance(self.old_value, (int, float)) and isinstance(self.new_value, (int, float)):
            delta = self.new_value - self.old_value
            if isinstance(delta, float):
                if delta > 0:
                    return f"+{delta:.2f}"
                return f"{delta:.2f}"
            else:
                if delta > 0:
                    return f"+{delta}"
                return str(delta)
        return ""


class DeckImpact(BaseModel):
    """Impact of adding a card to a deck."""

    card_name: str
    quantity: int = 1
    changes: list[StatChange] = []
    keywords_added: list[str] = []
    themes_strengthened: list[str] = []
    tribal_boost: str | None = None
    power_added: int = 0
    toughness_added: int = 0
    matchup_improvements: list[str] = []  # Archetypes this card helps against

    def has_impact(self) -> bool:
        """Check if there's any meaningful impact to display."""
        return bool(
            self.changes
            or self.keywords_added
            or self.themes_strengthened
            or self.tribal_boost
            or self.power_added
            or self.toughness_added
            or self.matchup_improvements
        )


@dataclass
class DeckImpactCalculator:
    """Calculates the impact of adding a card to a deck."""

    _card_encoder: CardEncoder = field(default_factory=CardEncoder)
    _deck_encoder: DeckEncoder = field(default_factory=DeckEncoder)

    def calculate_impact(
        self,
        card: dict[str, Any],
        deck_cards: list[dict[str, Any]],
        quantity: int = 1,
    ) -> DeckImpact:
        """Calculate impact of adding a card to a deck."""
        card_name = card.get("name", "Unknown")
        impact = DeckImpact(card_name=card_name, quantity=quantity)

        # Encode the card
        card_features = self._card_encoder.encode(card)

        # Encode current deck
        current_features = self._deck_encoder.encode(deck_cards)

        # Create deck with card added (quantity times)
        new_deck = deck_cards + [card] * quantity
        new_features = self._deck_encoder.encode(new_deck)

        # Calculate stat changes
        self._calculate_stat_changes(impact, current_features, new_features, card_features)

        # Calculate keyword changes
        self._calculate_keyword_changes(impact, current_features, new_features, card_features)

        # Calculate theme changes
        self._calculate_theme_changes(impact, current_features, new_features, card_features)

        # Calculate tribal impact
        self._calculate_tribal_impact(impact, current_features, new_features, card_features)

        # Calculate matchup improvements based on strengthened themes
        self._calculate_matchup_improvements(impact)

        # Combat stats for creatures
        if card_features.is_creature:
            impact.power_added = int(card_features.power * quantity)
            impact.toughness_added = int(card_features.toughness * quantity)

        return impact

    def _calculate_stat_changes(
        self,
        impact: DeckImpact,
        current: DeckFeatures,
        new: DeckFeatures,
        _card: CardFeatures,
    ) -> None:
        """Calculate basic stat changes."""
        # Average CMC change
        if current.avg_cmc != new.avg_cmc:
            delta = new.avg_cmc - current.avg_cmc
            is_positive = delta < 0 if current.avg_cmc > 3.0 else None
            impact.changes.append(
                StatChange(
                    name="Avg CMC",
                    old_value=round(current.avg_cmc, 2),
                    new_value=round(new.avg_cmc, 2),
                    is_positive=is_positive,
                    category="stat",
                )
            )

        # Type count changes
        type_changes = [
            ("Creatures", current.creature_count, new.creature_count),
            ("Instants", current.instant_count, new.instant_count),
            ("Sorceries", current.sorcery_count, new.sorcery_count),
            ("Artifacts", current.artifact_count, new.artifact_count),
            ("Enchantments", current.enchantment_count, new.enchantment_count),
            ("Planeswalkers", current.planeswalker_count, new.planeswalker_count),
            ("Lands", current.land_count, new.land_count),
        ]

        for name, old, new_val in type_changes:
            if old != new_val:
                impact.changes.append(
                    StatChange(
                        name=name,
                        old_value=old,
                        new_value=new_val,
                        is_positive=True,
                        category="type",
                    )
                )

    def _calculate_keyword_changes(
        self,
        impact: DeckImpact,
        current: DeckFeatures,
        new: DeckFeatures,
        card_features: CardFeatures,
    ) -> None:
        """Calculate keyword ability changes."""
        # keyword_density is a dict[str, int], keyword_presence is a set
        current_density = current.keyword_density
        new_density = new.keyword_density

        for kw in get_keyword_abilities():
            # If card adds this keyword to deck
            current_count = current_density.get(kw, 0)
            new_count = new_density.get(kw, 0)
            if new_count > current_count:
                # First instance is more impactful
                if current_count == 0:
                    impact.keywords_added.append(kw)

    def _calculate_theme_changes(
        self,
        impact: DeckImpact,
        current: DeckFeatures,
        new: DeckFeatures,
        card_features: CardFeatures,
    ) -> None:
        """Calculate synergy theme changes."""
        # Show themes the card brings, even if first card with that theme
        # Use the card's own themes directly for better display
        for theme in card_features.synergy_themes:
            impact.themes_strengthened.append(theme)

    def _calculate_tribal_impact(
        self,
        impact: DeckImpact,
        current: DeckFeatures,
        new: DeckFeatures,
        card_features: CardFeatures,
    ) -> None:
        """Calculate tribal synergy impact."""
        current_subtypes = current.subtype_counts
        new_subtypes = new.subtype_counts

        # Find if card strengthens an existing tribe
        for subtype, new_count in new_subtypes.items():
            current_count = current_subtypes.get(subtype, 0)
            if new_count > current_count and current_count >= 2:
                # Card adds to an existing tribal theme (3+ of same type)
                impact.tribal_boost = subtype
                break

    def _calculate_matchup_improvements(self, impact: DeckImpact) -> None:
        """Calculate matchup improvements based on strengthened themes.

        Uses THEME_MATCHUPS from deck.py to determine what archetypes
        the card helps against based on which themes it strengthens.
        """
        matchups: set[str] = set()

        for theme in impact.themes_strengthened:
            # THEME_MATCHUPS keys are title case, themes_strengthened are lowercase
            theme_key = theme.title()
            if theme_key in THEME_MATCHUPS:
                strong_against, _ = THEME_MATCHUPS[theme_key]
                matchups.update(strong_against[:2])  # Limit to top 2 per theme

        # Limit total matchup improvements to avoid clutter
        impact.matchup_improvements = sorted(matchups)[:3]


# Singleton instance
_calculator: DeckImpactCalculator | None = None


def get_impact_calculator() -> DeckImpactCalculator:
    """Get or create the singleton calculator instance."""
    global _calculator
    if _calculator is None:
        _calculator = DeckImpactCalculator()
    return _calculator


async def calculate_deck_impact(
    db: UnifiedDatabase,
    user_db: Any,  # UserDatabase - using Any to avoid circular import
    card_name: str,
    deck_id: int,
    quantity: int = 1,
) -> DeckImpact:
    """Calculate the impact of adding a card to a deck.

    Args:
        db: Database for card lookups
        user_db: User database for deck access
        card_name: Name of the card to add
        deck_id: ID of the deck to analyze
        quantity: Number of copies to add

    Returns:
        DeckImpact with all changes
    """
    import random

    # Add small jitter to prevent thundering herd when many concurrent requests arrive
    await asyncio.sleep(random.uniform(0, 0.01))

    logger.debug("calculate_deck_impact: starting for %s, deck %d", card_name, deck_id)

    # Get the card data
    card = await db.get_card_by_name(card_name)
    if not card:
        logger.debug("calculate_deck_impact: card not found: %s", card_name)
        return DeckImpact(card_name=card_name, quantity=quantity)

    logger.debug("calculate_deck_impact: got card %s", card.name)

    # Convert card to dict for the calculator
    card_dict = {
        "name": card.name,
        "manaCost": card.mana_cost,
        "manaValue": card.cmc,
        "type": card.type,
        "colors": card.colors or [],
        "colorIdentity": card.color_identity or [],
        "text": card.text,
        "power": card.power,
        "toughness": card.toughness,
        "keywords": card.keywords or [],
        "subtypes": card.subtypes or [],
    }

    # Get deck and cards in a single semaphore acquisition (50% less pressure)
    deck, deck_cards = await user_db.get_deck_with_cards(deck_id)
    if not deck:
        logger.debug("calculate_deck_impact: deck not found: %d", deck_id)
        return DeckImpact(card_name=card_name, quantity=quantity)

    logger.debug("calculate_deck_impact: got deck %s", deck.name)

    if not deck_cards:
        logger.debug("calculate_deck_impact: deck has no cards")
        return DeckImpact(card_name=card_name, quantity=quantity)

    logger.debug("calculate_deck_impact: deck has %d card entries", len(deck_cards))

    # Batch fetch all unique card names from the deck
    unique_names = list({dc.card_name for dc in deck_cards})
    logger.debug("calculate_deck_impact: fetching %d unique cards", len(unique_names))

    # Use batch lookup - get all cards in ONE query (fixes N+1 problem)
    card_map = await db.get_cards_by_names(unique_names, include_extras=False)

    logger.debug("calculate_deck_impact: fetched %d cards from db", len(card_map))

    # Build deck card dicts using the map
    deck_dicts = []
    for dc in deck_cards:
        # card_map keys are lowercase
        deck_card = card_map.get(dc.card_name.lower())
        if deck_card:
            card_entry = {
                "name": deck_card.name,
                "manaCost": deck_card.mana_cost,
                "manaValue": deck_card.cmc,
                "type": deck_card.type,
                "colors": deck_card.colors or [],
                "colorIdentity": deck_card.color_identity or [],
                "text": deck_card.text,
                "power": deck_card.power,
                "toughness": deck_card.toughness,
                "keywords": deck_card.keywords or [],
                "subtypes": deck_card.subtypes or [],
            }
            for _ in range(dc.quantity):
                deck_dicts.append(card_entry)

    logger.debug("calculate_deck_impact: built %d deck card dicts", len(deck_dicts))

    # Calculate impact
    calculator = get_impact_calculator()
    result = calculator.calculate_impact(card_dict, deck_dicts, quantity=quantity)
    logger.debug("calculate_deck_impact: done, has_impact=%s", result.has_impact())
    return result
