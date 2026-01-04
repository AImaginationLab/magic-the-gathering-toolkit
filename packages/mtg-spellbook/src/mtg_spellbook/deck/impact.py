"""Deck impact calculator - shows what changes when adding a card."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mtg_core.tools.recommendations.features import (
    CardEncoder,
    CardFeatures,
    DeckEncoder,
    DeckFeatures,
)

if TYPE_CHECKING:
    from typing import Any


@dataclass
class StatChange:
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


@dataclass
class DeckImpact:
    """Complete impact analysis of adding a card to a deck."""

    card_name: str
    quantity: int = 1

    # Stat changes
    changes: list[StatChange] = field(default_factory=list)

    # Keywords added/removed
    keywords_added: list[str] = field(default_factory=list)
    keywords_removed: list[str] = field(default_factory=list)

    # Themes strengthened/weakened
    themes_strengthened: list[str] = field(default_factory=list)
    themes_weakened: list[str] = field(default_factory=list)

    # Tribal impact
    tribal_boost: str | None = None  # e.g., "+1 Zombie"

    # Combat stats (for creatures)
    power_added: int = 0
    toughness_added: int = 0

    # Card features for display
    card_features: CardFeatures | None = None

    @property
    def positive_changes(self) -> list[StatChange]:
        """Get all positive stat changes."""
        return [c for c in self.changes if c.is_positive is True]

    @property
    def negative_changes(self) -> list[StatChange]:
        """Get all negative stat changes."""
        return [c for c in self.changes if c.is_positive is False]

    @property
    def neutral_changes(self) -> list[StatChange]:
        """Get all neutral stat changes."""
        return [c for c in self.changes if c.is_positive is None]

    def has_impact(self) -> bool:
        """Check if there's any meaningful impact to display."""
        return bool(
            self.changes
            or self.keywords_added
            or self.themes_strengthened
            or self.tribal_boost
            or self.power_added
            or self.toughness_added
        )


class DeckImpactCalculator:
    """Calculates the impact of adding a card to a deck."""

    def __init__(self) -> None:
        self._card_encoder = CardEncoder()
        self._deck_encoder = DeckEncoder()

    def calculate_impact(
        self,
        card: dict[str, Any],
        deck_cards: list[dict[str, Any]],
        quantity: int = 1,
    ) -> DeckImpact:
        """Calculate impact of adding a card to a deck.

        Args:
            card: Card dict to add
            deck_cards: Current deck cards as list of dicts
            quantity: Number of copies to add

        Returns:
            DeckImpact with all changes
        """
        card_name = card.get("name", "Unknown")
        impact = DeckImpact(card_name=card_name, quantity=quantity)

        # Encode the card
        card_features = self._card_encoder.encode(card)
        impact.card_features = card_features

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
            # Higher CMC is generally negative, lower is positive
            is_positive = delta < 0 if current.avg_cmc > 3.0 else None
            impact.changes.append(
                StatChange(
                    name="Avg CMC",
                    old_value=current.avg_cmc,
                    new_value=new.avg_cmc,
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
                        is_positive=True,  # Adding cards is generally positive
                        category="type",
                    )
                )

    def _calculate_keyword_changes(
        self,
        impact: DeckImpact,
        current: DeckFeatures,
        new: DeckFeatures,
        card: CardFeatures,
    ) -> None:
        """Calculate keyword ability changes."""
        # New keywords added to deck
        new_keywords = new.keyword_presence - current.keyword_presence
        impact.keywords_added = sorted(new_keywords)

        # Keywords the card has (even if deck already has them)
        for kw in card.keyword_abilities:
            if kw not in new_keywords:
                # Keyword already in deck, but we're adding more density
                old_density = current.keyword_density.get(kw, 0)
                new_density = new.keyword_density.get(kw, 0)
                if new_density > old_density:
                    impact.changes.append(
                        StatChange(
                            name=kw.capitalize(),
                            old_value=old_density,
                            new_value=new_density,
                            is_positive=True,
                            category="keyword",
                        )
                    )

    def _calculate_theme_changes(
        self,
        impact: DeckImpact,
        current: DeckFeatures,
        new: DeckFeatures,
        card: CardFeatures,
    ) -> None:
        """Calculate synergy theme changes."""
        # Themes strengthened
        for theme in card.synergy_themes:
            old_count = current.synergy_themes.get(theme, 0)
            new_count = new.synergy_themes.get(theme, 0)

            if new_count > old_count:
                # Theme is being strengthened
                theme_display = theme.replace("_", " ").title()

                # Check if this crosses the "dominant theme" threshold (3+)
                if old_count < 3 <= new_count:
                    impact.themes_strengthened.append(f"{theme_display} (now active!)")
                elif new_count >= 3:
                    impact.themes_strengthened.append(theme_display)
                else:
                    # Building toward theme
                    impact.changes.append(
                        StatChange(
                            name=theme_display,
                            old_value=old_count,
                            new_value=new_count,
                            is_positive=True,
                            category="theme",
                        )
                    )

    def _calculate_tribal_impact(
        self,
        impact: DeckImpact,
        current: DeckFeatures,
        new: DeckFeatures,
        card: CardFeatures,
    ) -> None:
        """Calculate tribal synergy impact."""
        if not card.subtypes:
            return

        for subtype in card.subtypes:
            old_count = current.subtype_counts.get(subtype, 0)
            new_count = new.subtype_counts.get(subtype, 0)

            if new_count > old_count:
                # Check if this is a meaningful tribal type
                # Skip basic land types and generic supertypes
                skip_types = {"basic", "snow", "legendary"}
                if subtype.lower() in skip_types:
                    continue

                # Check if this crosses tribal threshold (8+)
                if old_count < 8 <= new_count:
                    impact.tribal_boost = f"+{impact.quantity} {subtype} (Tribal active!)"
                elif new_count >= 5:
                    # Building tribal
                    impact.tribal_boost = f"+{impact.quantity} {subtype} ({new_count} total)"
                elif new_count >= 2:
                    # Just tracking
                    impact.tribal_boost = f"+{impact.quantity} {subtype}"


# Singleton instance
_calculator: DeckImpactCalculator | None = None


def get_impact_calculator() -> DeckImpactCalculator:
    """Get the global deck impact calculator."""
    global _calculator
    if _calculator is None:
        _calculator = DeckImpactCalculator()
    return _calculator
