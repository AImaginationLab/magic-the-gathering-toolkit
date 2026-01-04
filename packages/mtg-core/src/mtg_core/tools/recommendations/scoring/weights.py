"""Scoring weights and constants for deck recommendations.

Centralizes all magic numbers and scoring weights to make tuning easier.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LimitedTierWeights:
    """Weights for 17Lands Limited tier scoring."""

    S: float = 1.5  # Elite bombs
    A: float = 1.0  # Very strong
    B: float = 0.5  # Above average
    C: float = 0.0  # Average (no bonus)
    D: float = -0.25  # Below average (slight penalty)
    F: float = -0.5  # Weak (penalty)
    BOMB_BONUS: float = 0.3  # Extra for bomb cards

    def get(self, tier: str, default: float = 0.0) -> float:
        """Get weight for a tier."""
        return getattr(self, tier, default)


@dataclass(frozen=True)
class LimitedTierScores:
    """Score mapping for Limited tier (0-1 range)."""

    S: float = 1.0
    A: float = 0.85
    B: float = 0.7
    C: float = 0.55
    D: float = 0.4
    F: float = 0.25
    UNKNOWN: float = 0.5

    def get(self, tier: str | None) -> float:
        """Get score for a tier."""
        if tier is None:
            return self.UNKNOWN
        return getattr(self, tier, self.UNKNOWN)


@dataclass(frozen=True)
class CardScoringWeights:
    """Weights for individual card scoring."""

    SYNERGY_SCALE: float = 5.0  # Scale synergy score (0-1) to larger range
    ARCHETYPE_BONUS: float = 1.0  # Bonus when card text matches archetype
    EDHREC_DIVISOR: float = 30000.0  # EDHREC rank divisor for normalization
    EDHREC_POPULARITY_THRESHOLD: float = 0.7  # Threshold for "Popular" label


@dataclass(frozen=True)
class ComboBracketWeights:
    """Weights for combo bracket quality."""

    R: float = 0.4  # Restricted/powerful
    S: float = 0.3  # Strong
    P: float = 0.2  # Playable
    C: float = 0.1  # Casual
    DEFAULT: float = 0.1

    BRACKET_WEIGHT: float = 0.3  # Weight of bracket in combo score
    OWNERSHIP_WEIGHT: float = 0.7  # Weight of ownership ratio in combo score
    NORMALIZE_DIVISOR: float = 10.0  # Normalize combo score

    def get(self, bracket: str) -> float:
        """Get weight for a bracket tag."""
        return getattr(self, bracket, self.DEFAULT)


@dataclass(frozen=True)
class ThemeMatchWeights:
    """Weights for theme/tribal matching."""

    TRIBE_TEXT_MATCH: float = 0.5  # Tribe mentioned in text
    TRIBE_LORD_PATTERN: float = 0.3  # "other [tribe]" pattern
    TRIBE_CONTROL_PATTERN: float = 0.2  # "[tribe]s you control" pattern
    ARCHETYPE_KEYWORD_BONUS: float = 0.15  # Per matching keyword
    ARCHETYPE_MAX_BONUS: float = 0.6  # Maximum archetype bonus


@dataclass(frozen=True)
class SynergyWeights:
    """Weights for synergy scoring."""

    THEME_OVERLAP: float = 0.3  # Per overlapping theme
    SUBTYPE_OVERLAP: float = 0.2  # Per overlapping subtype
    SYNERGY_NORMALIZE_DIVISOR: float = 20.0  # Points for max synergy score


@dataclass(frozen=True)
class CommanderWeights:
    """Weights for commander total score calculation."""

    EDHREC: float = 0.25  # Popularity/proven power
    THEME: float = 0.20  # Matches requested strategy
    COMBO: float = 0.15  # Combo potential
    SYNERGY: float = 0.25  # Synergy with owned cards
    LIMITED: float = 0.05  # 17Lands performance
    OWNERSHIP: float = 0.10  # Bonus for owning the commander


@dataclass(frozen=True)
class EDHRECRankThresholds:
    """Thresholds for EDHREC rank categorization."""

    TOP_COMMANDER: int = 1000  # "Top EDHREC commander"
    POPULAR_COMMANDER: int = 5000  # "Popular commander"
    UNKNOWN_SCORE: float = 0.3  # Score for unknown commanders


@dataclass(frozen=True)
class ScoringConfig:
    """Master configuration for all scoring weights."""

    limited_tier_weights: LimitedTierWeights = field(default_factory=LimitedTierWeights)
    limited_tier_scores: LimitedTierScores = field(default_factory=LimitedTierScores)
    card_scoring: CardScoringWeights = field(default_factory=CardScoringWeights)
    combo_bracket: ComboBracketWeights = field(default_factory=ComboBracketWeights)
    theme_match: ThemeMatchWeights = field(default_factory=ThemeMatchWeights)
    synergy: SynergyWeights = field(default_factory=SynergyWeights)
    commander: CommanderWeights = field(default_factory=CommanderWeights)
    edhrec_thresholds: EDHRECRankThresholds = field(default_factory=EDHRECRankThresholds)


# Global default config
DEFAULT_SCORING_CONFIG = ScoringConfig()
