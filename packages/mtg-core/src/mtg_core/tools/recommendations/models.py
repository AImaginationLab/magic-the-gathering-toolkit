"""Data models for deck recommendations.

Contains dataclasses for cards, deck suggestions, combos, filters, and matches.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CardData:
    """Minimal card data for deck analysis."""

    name: str
    type_line: str | None = None
    colors: list[str] | None = None
    mana_cost: str | None = None
    text: str | None = None
    color_identity: list[str] | None = None
    keywords: list[str] | None = None
    subtypes: list[str] | None = None
    power: str | None = None
    toughness: str | None = None
    edhrec_rank: int | None = None
    set_code: str | None = None

    # Pre-compiled regex patterns for CMC parsing
    _COLORED_MANA_RE = re.compile(r"\{[WUBRG]\}")
    _HYBRID_MANA_RE = re.compile(r"\{[WUBRG]/[WUBRG]\}")
    _GENERIC_MANA_RE = re.compile(r"\{(\d+)\}")

    # Basic land names for land detection
    _BASIC_LANDS = frozenset(
        {
            "Plains",
            "Island",
            "Swamp",
            "Mountain",
            "Forest",
            "Snow-Covered Plains",
            "Snow-Covered Island",
            "Snow-Covered Swamp",
            "Snow-Covered Mountain",
            "Snow-Covered Forest",
            "Wastes",
        }
    )

    def to_encoder_dict(self) -> dict[str, Any]:
        """Convert to dict format expected by CardEncoder/DeckEncoder."""
        return {
            "name": self.name,
            "type": self.type_line or "",
            "colors": self.colors or [],
            "manaCost": self.mana_cost or "",
            "mana_cost": self.mana_cost or "",
            "text": self.text or "",
            "colorIdentity": self.color_identity or [],
            "color_identity": self.color_identity or [],
            "keywords": self.keywords or [],
            "subtypes": self.subtypes or [],
            "power": self.power or "0",
            "toughness": self.toughness or "0",
            "edhrecRank": self.edhrec_rank,
            "edhrec_rank": self.edhrec_rank,
        }

    def get_color_identity(self) -> list[str]:
        """Get color identity - use explicit identity if set, otherwise derive from colors/mana."""
        if self.color_identity:
            return self.color_identity
        if self.colors:
            return self.colors
        if self.mana_cost:
            identity = [c for c in ["W", "U", "B", "R", "G"] if c in self.mana_cost]
            if identity:
                return identity
        return []

    def get_cmc(self) -> int:
        """Extract converted mana cost from mana_cost string."""
        if not self.mana_cost:
            return 0
        cmc = 0
        cmc += len(self._COLORED_MANA_RE.findall(self.mana_cost))
        cmc += len(self._HYBRID_MANA_RE.findall(self.mana_cost))
        for match in self._GENERIC_MANA_RE.findall(self.mana_cost):
            cmc += int(match)
        return cmc

    def is_land(self) -> bool:
        """Check if this card is a land."""
        if self.name in self._BASIC_LANDS:
            return True
        return bool(self.type_line and "land" in self.type_line.lower())

    def get_card_type(self) -> str:
        """Get primary card type for categorization."""
        if self.is_land():
            return "land"
        if not self.type_line:
            return "other"
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
        return "other"


@dataclass
class DeckFilters:
    """Filters for deck suggestions."""

    colors: list[str] | None = None
    creature_type: str | None = None  # Single tribal type filter
    creature_types: list[str] | None = None  # Multiple tribal types (OR filter)
    theme: str | None = None  # Single theme filter
    themes: list[str] | None = None  # Multiple themes (OR filter)
    keyword: str | None = None
    format: str | None = None
    set_codes: list[str] | None = None  # Filter/prioritize cards from these sets
    owned_only: bool = True


@dataclass
class ComboSummary:
    """Summary of a combo for deck suggestions."""

    id: str
    cards: list[str]
    missing_cards: list[str]
    produces: list[str]
    bracket: str
    score: float
    completion_pct: float

    @property
    def result(self) -> str:
        """Get a human-readable result string."""
        return ", ".join(self.produces) if self.produces else "Unknown result"


@dataclass
class DeckSuggestion:
    """A suggested deck archetype based on collection."""

    name: str
    format: str
    commander: str | None = None
    archetype: str | None = None
    colors: list[str] = field(default_factory=list)
    key_cards_owned: list[str] = field(default_factory=list)
    key_cards_missing: list[str] = field(default_factory=list)
    completion_pct: float = 0.0
    estimated_cost: float = 0.0
    reasons: list[str] = field(default_factory=list)
    # Combo information
    near_combos: list[ComboSummary] = field(default_factory=list)
    complete_combos: list[ComboSummary] = field(default_factory=list)
    combo_score: float = 0.0
    # Limited stats
    limited_bombs: list[str] = field(default_factory=list)
    # Filter match explanations
    filter_reasons: list[str] = field(default_factory=list)
    # Deck quality validation
    curve_warnings: list[str] = field(default_factory=list)
    interaction_count: int = 0
    quality_score: float = 0.0
    # Mana base quality
    mana_base_quality: str = ""
    fixing_land_count: int = 0
    # Win condition validation
    win_condition_types: list[str] = field(default_factory=list)
    tribal_strength: str = ""
    theme_strength: str = ""
    # MTG fundamentals validation
    lord_count: int = 0
    ramp_count: int = 0
    ramp_warnings: list[str] = field(default_factory=list)
    card_advantage_count: int = 0
    card_advantage_breakdown: dict[str, int] = field(default_factory=dict)
    card_advantage_warnings: list[str] = field(default_factory=list)


@dataclass
class FilterResult:
    """Result of pre-filtering cards and commanders."""

    cards: list[CardData]
    commanders: list[CardData]
    tribal_count: int = 0
    theme_count: int = 0
    filter_reasons: list[str] = field(default_factory=list)
    meets_tribal_minimum: bool = True
    meets_theme_minimum: bool = True


@dataclass
class CommanderMatch:
    """A commander candidate with scoring breakdown."""

    name: str
    type_line: str
    color_identity: list[str] = field(default_factory=list)
    oracle_text: str | None = None
    # Scoring components (all 0.0-1.0)
    edhrec_score: float = 0.0
    theme_score: float = 0.0
    combo_score: float = 0.0
    synergy_score: float = 0.0
    limited_score: float = 0.0
    ownership_bonus: float = 0.0
    # Final combined score
    total_score: float = 0.0
    # Metadata
    is_owned: bool = False
    combo_count: int = 0
    synergy_cards: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    edhrec_rank: int | None = None
