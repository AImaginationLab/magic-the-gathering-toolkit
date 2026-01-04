"""Structured feature encoders for cards and decks."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

# Keywords that indicate mechanical synergies (not just abilities)
SYNERGY_KEYWORDS = {
    # Sacrifice themes
    "sacrifice": ["sacrifice", "sacrificed", "sac "],
    "death_trigger": ["when .* dies", "whenever .* dies", "dying"],
    "aristocrats": ["blood artist", "whenever a creature dies", "lose life"],
    # ETB themes
    "etb": ["enters the battlefield", "enters under your control", "etb", "when .* enters"],
    "blink": ["exile .* return", "flicker", "blink"],
    # Graveyard themes
    "graveyard": ["from your graveyard", "graveyard to", "reanimate"],
    "self_mill": ["mill", "put .* into your graveyard"],
    # Token themes
    "tokens": ["create .* token", "token creature", "populate", "creates .* token"],
    "go_wide": ["all creatures you control", "each creature you control"],
    # +1/+1 counter themes
    "counters": ["\\+1/\\+1 counter", "proliferate", "counter on"],
    # Draw/card advantage
    "draw": ["draw .* card", "draws a card"],
    "impulse_draw": ["exile .* you may play", "exile .* you may cast"],
    # Ramp/mana
    "ramp": ["add .* mana", "search .* land", "mana dork"],
    "cost_reduction": ["cost .* less", "costs .* less"],
    # Control
    "counterspell": ["counter target", "counter that spell"],
    "removal": ["destroy target", "exile target", "deals .* damage to"],
    "board_wipe": ["destroy all", "exile all", "all creatures get -"],
    # Combat
    "evasion": ["flying", "menace", "unblockable", "can't be blocked"],
    "combat_trigger": ["whenever .* attacks", "whenever .* deals combat damage"],
    "equipment": ["equip", "equipped creature"],
    # Spell themes
    "spellslinger": ["instant or sorcery", "whenever you cast .* instant", "magecraft"],
    "storm": ["storm", "copy .* spell"],
    # Tribal
    "tribal_lord": ["other .* get \\+", "creatures you control get"],
    "tribal_synergy": ["share a creature type", "choose a creature type"],
    # Exile themes
    "exile": ["exile .* card", "exiled card", "exile target", "from exile"],
    # Hand disruption
    "hand_reveal": ["reveals .* hand", "reveal .* hand", "look at .* hand"],
    "discard": ["discard .* card", "discards a card", "each opponent discards"],
    # Life manipulation
    "lifegain": ["gain .* life", "gains .* life", "lifelink"],
    "life_payment": ["pay .* life", "lose .* life"],
    # Set mechanics (regex patterns for oracle text references)
    "suspect": ["suspect", "suspected"],
    "investigate": ["investigate", "clue token"],
    "surveil": ["surveil"],
    "explore": ["explore"],
    "amass": ["amass"],
    "incubate": ["incubate"],
    "adapt": ["adapt \\d"],
    "proliferate": ["proliferate"],
    "populate": ["populate"],
    "energy": ["\\{e\\}", "energy counter"],
    "food": ["food token", "create .* food"],
    "treasure": ["treasure token", "create .* treasure"],
    "blood": ["blood token", "create .* blood"],
    "clue": ["clue token", "create .* clue"],
    "landfall": ["landfall", "whenever a land enters"],
    "magecraft": ["magecraft", "whenever you cast or copy an instant or sorcery"],
    "constellation": ["constellation", "whenever .* enchantment enters"],
    "raid": ["raid", "if you attacked"],
    "revolt": ["revolt", "if a permanent you controlled left"],
    "delirium": ["delirium", "four or more card types"],
    "threshold": ["threshold", "seven or more cards in your graveyard"],
    "metalcraft": ["metalcraft", "three or more artifacts"],
    "morbid": ["morbid", "if a creature died"],
    "formidable": ["formidable", "creatures .* total power 8"],
    "ferocious": ["ferocious", "creature with power 4 or greater"],
}

# Fallback keyword abilities (used if database unavailable)
_FALLBACK_KEYWORD_ABILITIES = [
    "flying",
    "first strike",
    "double strike",
    "deathtouch",
    "hexproof",
    "indestructible",
    "lifelink",
    "menace",
    "reach",
    "trample",
    "vigilance",
    "flash",
    "haste",
    "defender",
    "ward",
    "protection",
]


@lru_cache(maxsize=1)
def _load_keyword_abilities_from_db() -> list[str]:
    """Load keyword abilities from gameplay.sqlite database."""
    from mtg_core.config import get_settings

    settings = get_settings()
    db_path: Path = settings.gameplay_sqlite_path

    if not db_path.exists():
        return _FALLBACK_KEYWORD_ABILITIES

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT DISTINCT text FROM abilities WHERE category = 'keyword' ORDER BY text"
        )
        keywords = []
        for (text,) in cursor.fetchall():
            # Normalize: lowercase, strip numbers/punctuation for matching
            kw = text.lower().strip()
            # Skip compound abilities like "Amass Orcs 2" - just keep base keyword
            if " " in kw:
                base = kw.split()[0]
                if base not in keywords:
                    keywords.append(base)
            elif kw and kw not in keywords:
                keywords.append(kw)
        conn.close()
        return keywords if keywords else _FALLBACK_KEYWORD_ABILITIES
    except Exception:
        return _FALLBACK_KEYWORD_ABILITIES


def get_keyword_abilities() -> list[str]:
    """Get list of keyword abilities from database (cached)."""
    return _load_keyword_abilities_from_db()


# For backwards compatibility - this is now a function call
KEYWORD_ABILITIES = _FALLBACK_KEYWORD_ABILITIES  # Initial value, updated at runtime


@dataclass
class CardFeatures:
    """Structured feature vector for a single card."""

    name: str

    # Mana features
    cmc: float = 0.0
    color_pips: dict[str, int] = field(default_factory=dict)  # W, U, B, R, G counts
    color_identity: set[str] = field(default_factory=set)  # Full color identity (for lands)
    is_colorless: bool = False
    is_multicolor: bool = False

    # Type features
    is_creature: bool = False
    is_instant: bool = False
    is_sorcery: bool = False
    is_artifact: bool = False
    is_enchantment: bool = False
    is_planeswalker: bool = False
    is_land: bool = False
    is_legendary: bool = False

    # Subtypes (for tribal)
    subtypes: list[str] = field(default_factory=list)

    # Combat stats
    power: float = 0.0
    toughness: float = 0.0

    # Keyword abilities (standard MTG keywords)
    keyword_abilities: set[str] = field(default_factory=set)

    # Synergy themes (detected from oracle text)
    synergy_themes: set[str] = field(default_factory=set)

    # Popularity
    edhrec_rank: int | None = None

    def to_vector(self) -> NDArray[np.float64]:
        """Convert to numerical vector for ML."""
        vec: list[float] = []

        # CMC (normalized 0-10)
        vec.append(min(self.cmc / 10.0, 1.0))

        # Color pips (5 dims)
        for color in "WUBRG":
            vec.append(min(self.color_pips.get(color, 0) / 3.0, 1.0))

        # Color identity flags (5 dims) - includes lands/text colors
        for color in "WUBRG":
            vec.append(1.0 if color in self.color_identity else 0.0)

        # Color flags
        vec.append(1.0 if self.is_colorless else 0.0)
        vec.append(1.0 if self.is_multicolor else 0.0)

        # Type flags (7 dims)
        vec.append(1.0 if self.is_creature else 0.0)
        vec.append(1.0 if self.is_instant else 0.0)
        vec.append(1.0 if self.is_sorcery else 0.0)
        vec.append(1.0 if self.is_artifact else 0.0)
        vec.append(1.0 if self.is_enchantment else 0.0)
        vec.append(1.0 if self.is_planeswalker else 0.0)
        vec.append(1.0 if self.is_land else 0.0)
        vec.append(1.0 if self.is_legendary else 0.0)

        # Combat stats (normalized)
        vec.append(min(self.power / 10.0, 1.0))
        vec.append(min(self.toughness / 10.0, 1.0))

        # Keyword abilities (dynamic dims based on database)
        for kw in get_keyword_abilities():
            vec.append(1.0 if kw in self.keyword_abilities else 0.0)

        # Synergy themes (len(SYNERGY_KEYWORDS) dims)
        for theme in SYNERGY_KEYWORDS:
            vec.append(1.0 if theme in self.synergy_themes else 0.0)

        # EDHRec rank (normalized, lower = better)
        if self.edhrec_rank is not None:
            vec.append(max(0, 1.0 - (self.edhrec_rank / 30000.0)))
        else:
            vec.append(0.5)  # Unknown

        return np.array(vec, dtype=np.float64)


@dataclass
class DeckFeatures:
    """Aggregated features for an entire deck."""

    # Size
    card_count: int = 0

    # Mana curve
    avg_cmc: float = 0.0
    cmc_distribution: list[float] = field(default_factory=lambda: [0.0] * 7)  # 0,1,2,3,4,5,6+

    # Color profile
    color_intensity: dict[str, float] = field(default_factory=dict)  # Total pips per color
    color_identity: set[str] = field(default_factory=set)  # Combined color identity of all cards
    color_count: int = 0

    # Type distribution
    creature_count: int = 0
    instant_count: int = 0
    sorcery_count: int = 0
    artifact_count: int = 0
    enchantment_count: int = 0
    planeswalker_count: int = 0
    land_count: int = 0

    # Keyword presence (which keywords appear in deck)
    keyword_presence: set[str] = field(default_factory=set)
    keyword_density: dict[str, int] = field(default_factory=dict)  # Count per keyword

    # Synergy themes present in deck
    synergy_themes: dict[str, int] = field(default_factory=dict)  # Theme -> count

    # Subtypes (for tribal detection)
    subtype_counts: dict[str, int] = field(default_factory=dict)

    @property
    def creature_ratio(self) -> float:
        return self.creature_count / max(self.card_count, 1)

    @property
    def spell_ratio(self) -> float:
        return (self.instant_count + self.sorcery_count) / max(self.card_count, 1)

    @property
    def dominant_tribe(self) -> str | None:
        """Get the most common creature type if tribal."""
        if not self.subtype_counts:
            return None
        top = max(self.subtype_counts.items(), key=lambda x: x[1])
        # Need at least 8 of a type to be "tribal"
        return top[0] if top[1] >= 8 else None

    @property
    def dominant_themes(self) -> list[str]:
        """Get themes with 3+ cards supporting them."""
        return [theme for theme, count in self.synergy_themes.items() if count >= 3]

    def curve_gap_at(self, cmc: int) -> float:
        """How much the deck needs cards at this CMC (0-1)."""
        idx = 6 if cmc >= 6 else cmc

        # Ideal curve (rough approximation)
        ideal = [0.05, 0.15, 0.25, 0.20, 0.15, 0.10, 0.10]
        actual = self.cmc_distribution[idx]

        # Positive = we need more at this CMC
        return max(0, ideal[idx] - actual)


class CardEncoder:
    """Encodes cards into structured feature vectors."""

    def __init__(self, use_precomputed_themes: bool = True) -> None:
        """Initialize encoder.

        Args:
            use_precomputed_themes: If True, try to load themes from database
                instead of detecting via regex. Falls back to regex if unavailable.
        """
        self._use_precomputed = use_precomputed_themes
        self._themes_cache: dict[str, set[str]] = {}
        self._themes_loaded = False

    def _load_themes_cache(self) -> None:
        """Load all card themes from database into memory cache."""
        if self._themes_loaded:
            return

        self._themes_loaded = True

        try:
            from mtg_core.config import get_settings

            settings = get_settings()
            db_path = settings.gameplay_sqlite_path

            if not db_path.exists():
                return

            import sqlite3

            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute("SELECT card_name, theme FROM card_themes")
            for card_name, theme in cursor.fetchall():
                if card_name not in self._themes_cache:
                    self._themes_cache[card_name] = set()
                self._themes_cache[card_name].add(theme)
            conn.close()
        except Exception:
            pass  # Fall back to regex detection

    def _get_precomputed_themes(self, card_name: str) -> set[str] | None:
        """Get pre-computed themes for a card, or None if unavailable."""
        if not self._use_precomputed:
            return None

        self._load_themes_cache()

        if card_name in self._themes_cache:
            return self._themes_cache[card_name]

        return None

    def encode(self, card: dict[str, Any]) -> CardFeatures:
        """Encode a card dict into CardFeatures."""
        features = CardFeatures(name=card.get("name", "Unknown"))

        # CMC
        features.cmc = float(card.get("manaValue") or card.get("cmc") or 0)

        # Parse mana cost for color pips
        mana_cost = card.get("manaCost") or card.get("mana_cost") or ""
        features.color_pips = self._parse_color_pips(mana_cost)

        # Color flags
        colors = card.get("colors") or []
        if isinstance(colors, str):
            colors = [c.strip() for c in colors.split(",") if c.strip()]
        features.is_colorless = len(colors) == 0 and features.cmc > 0
        features.is_multicolor = len(colors) > 1

        # Color identity (distinct from colors - includes lands, activated abilities)
        color_identity = card.get("colorIdentity") or card.get("color_identity") or []
        if isinstance(color_identity, str):
            color_identity = [c.strip() for c in color_identity.split(",") if c.strip()]
        features.color_identity = set(color_identity)

        # Parse type line
        type_line = card.get("type") or ""
        features.is_creature = "Creature" in type_line
        features.is_instant = "Instant" in type_line
        features.is_sorcery = "Sorcery" in type_line
        features.is_artifact = "Artifact" in type_line
        features.is_enchantment = "Enchantment" in type_line
        features.is_planeswalker = "Planeswalker" in type_line
        features.is_land = "Land" in type_line
        features.is_legendary = "Legendary" in type_line

        # Subtypes
        subtypes = card.get("subtypes") or []
        if isinstance(subtypes, str):
            subtypes = [s.strip() for s in subtypes.split(",") if s.strip()]
        features.subtypes = subtypes

        # Combat stats
        power = card.get("power") or "0"
        toughness = card.get("toughness") or "0"
        features.power = self._parse_pt(power)
        features.toughness = self._parse_pt(toughness)

        # Keywords
        keywords = card.get("keywords") or []
        if isinstance(keywords, str):
            keywords = [k.strip().lower() for k in keywords.split(",") if k.strip()]
        else:
            keywords = [k.lower() for k in keywords]
        features.keyword_abilities = set(keywords) & set(get_keyword_abilities())

        # Synergy themes - try pre-computed first, fall back to regex
        card_name = card.get("name", "")
        precomputed = self._get_precomputed_themes(card_name)
        if precomputed is not None:
            features.synergy_themes = precomputed
        else:
            oracle_text = (card.get("text") or "").lower()
            features.synergy_themes = self._detect_synergy_themes(oracle_text)

        # EDHRec rank
        features.edhrec_rank = card.get("edhrecRank") or card.get("edhrec_rank")

        return features

    def _parse_color_pips(self, mana_cost: str) -> dict[str, int]:
        """Count color pips in mana cost."""
        pips: dict[str, int] = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0}
        for color in pips:
            pips[color] = mana_cost.count(color)
        return pips

    def _parse_pt(self, value: str) -> float:
        """Parse power/toughness, handling * and X."""
        if not value:
            return 0.0
        try:
            return float(value)
        except ValueError:
            # Handle *, X, 1+*, etc.
            if "*" in value or "X" in value:
                return 0.0
            # Try to extract any number
            match = re.search(r"(\d+)", value)
            return float(match.group(1)) if match else 0.0

    def _detect_synergy_themes(self, oracle_text: str) -> set[str]:
        """Detect synergy themes from oracle text."""
        themes: set[str] = set()
        for theme, patterns in SYNERGY_KEYWORDS.items():
            for pattern in patterns:
                if re.search(pattern, oracle_text, re.IGNORECASE):
                    themes.add(theme)
                    break
        return themes


class DeckEncoder:
    """Encodes a deck (list of cards) into aggregated features."""

    def __init__(self) -> None:
        self.card_encoder = CardEncoder()

    def encode(self, cards: list[dict[str, Any]]) -> DeckFeatures:
        """Encode a list of card dicts into DeckFeatures."""
        features = DeckFeatures()
        features.card_count = len(cards)

        if not cards:
            return features

        # Encode all cards
        encoded_cards = [self.card_encoder.encode(c) for c in cards]

        # Aggregate CMC
        cmcs = [c.cmc for c in encoded_cards if not c.is_land]
        features.avg_cmc = sum(cmcs) / len(cmcs) if cmcs else 0.0

        # CMC distribution
        cmc_counts = [0] * 7
        for cmc in cmcs:
            idx = min(int(cmc), 6)
            cmc_counts[idx] += 1
        total_nonland = len(cmcs)
        features.cmc_distribution = [c / max(total_nonland, 1) for c in cmc_counts]

        # Color intensity and color identity
        color_totals: dict[str, float] = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0}
        deck_color_identity: set[str] = set()
        for card in encoded_cards:
            for color, count in card.color_pips.items():
                color_totals[color] += count
            deck_color_identity.update(card.color_identity)
        features.color_intensity = color_totals
        features.color_identity = deck_color_identity
        features.color_count = sum(1 for v in color_totals.values() if v > 0)

        # Type counts
        for card in encoded_cards:
            if card.is_creature:
                features.creature_count += 1
            if card.is_instant:
                features.instant_count += 1
            if card.is_sorcery:
                features.sorcery_count += 1
            if card.is_artifact:
                features.artifact_count += 1
            if card.is_enchantment:
                features.enchantment_count += 1
            if card.is_planeswalker:
                features.planeswalker_count += 1
            if card.is_land:
                features.land_count += 1

        # Keyword aggregation
        for card in encoded_cards:
            features.keyword_presence.update(card.keyword_abilities)
            for kw in card.keyword_abilities:
                features.keyword_density[kw] = features.keyword_density.get(kw, 0) + 1

        # Synergy theme aggregation
        for card in encoded_cards:
            for theme in card.synergy_themes:
                features.synergy_themes[theme] = features.synergy_themes.get(theme, 0) + 1

        # Subtype aggregation
        for card in encoded_cards:
            for subtype in card.subtypes:
                features.subtype_counts[subtype] = features.subtype_counts.get(subtype, 0) + 1

        return features
