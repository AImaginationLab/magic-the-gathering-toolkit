"""Ability pattern matching using 17lands official ability dictionary.

This module provides utilities for categorizing MTG cards by their abilities,
using the official 17lands ability dictionary as the source of truth.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

# Cache directory for downloaded dictionaries
DICT_CACHE_DIR = Path.home() / ".cache" / "mtg-toolkit" / "dictionaries"
ABILITIES_URL = "https://17lands-public.s3.amazonaws.com/analysis_data/cards/abilities.csv"


def _get_abilities_path() -> Path | None:
    """Get path to abilities CSV, downloading if needed."""
    # Check cache first
    cache_path = DICT_CACHE_DIR / "abilities.csv"
    if cache_path.exists():
        return cache_path

    # Try to download
    try:
        import urllib.request

        DICT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(ABILITIES_URL, cache_path)
        return cache_path
    except Exception:
        return None


@dataclass
class Ability:
    """An ability from the 17lands dictionary."""

    id: int
    text: str
    category: str = ""  # Computed category


@dataclass
class AbilityMatch:
    """A matched ability in card text."""

    ability: Ability
    matched_text: str
    start_pos: int
    end_pos: int


# Evergreen keyword IDs from the dictionary (these are simple single-word keywords)
EVERGREEN_IDS = frozenset(
    {1, 2, 3, 6, 7, 8, 9, 10, 12, 13, 14, 15, 104}
)  # Deathtouch through Indestructible

# Category patterns for classification
CATEGORY_PATTERNS = {
    "keyword": re.compile(r"^[A-Z][a-z]+( [a-z]+)?$"),  # Single/two word capitalized
    "activated": re.compile(r"\{[^}]+\}.*:"),  # {cost}: effect
    "triggered_etb": re.compile(r"When .* enters", re.IGNORECASE),
    "triggered_dies": re.compile(r"When .* dies|Whenever .* dies", re.IGNORECASE),
    "triggered_attack": re.compile(r"Whenever .* attacks", re.IGNORECASE),
    "triggered_damage": re.compile(r"Whenever .* deals (combat )?damage", re.IGNORECASE),
    "triggered_cast": re.compile(r"Whenever you cast", re.IGNORECASE),
    "sacrifice": re.compile(r"[Ss]acrifice", re.IGNORECASE),
    "graveyard": re.compile(r"graveyard|dies|return .* from .* graveyard", re.IGNORECASE),
    "counters": re.compile(r"\+1/\+1 counter|\-1/\-1 counter|counter on", re.IGNORECASE),
    "tokens": re.compile(r"create .* token|token creature", re.IGNORECASE),
    "draw": re.compile(r"draw (a |cards?)", re.IGNORECASE),
    "lifegain": re.compile(r"(gain|gains) .* life", re.IGNORECASE),
    "ramp": re.compile(r"search .* library .* land|add .* mana", re.IGNORECASE),
}


@dataclass
class AbilityDictionary:
    """Dictionary of MTG abilities for pattern matching."""

    abilities: dict[int, Ability] = field(default_factory=dict)
    _by_text: dict[str, Ability] = field(default_factory=dict)
    _keywords: list[Ability] = field(default_factory=list)
    _complex_abilities: list[Ability] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path | None = None) -> AbilityDictionary:
        """Load abilities from CSV file (downloads if needed)."""
        if path is None:
            path = _get_abilities_path()
        if path is None or not path.exists():
            return cls()

        instance = cls()
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ability_id = int(row["id"])
                text = row["text"]
                category = cls._categorize(text, ability_id)

                ability = Ability(id=ability_id, text=text, category=category)
                instance.abilities[ability_id] = ability
                instance._by_text[text.lower()] = ability

                # Separate keywords from complex abilities
                if category == "keyword" or ability_id in EVERGREEN_IDS:
                    instance._keywords.append(ability)
                else:
                    instance._complex_abilities.append(ability)

        # Sort keywords by length (longer first for greedy matching)
        instance._keywords.sort(key=lambda a: len(a.text), reverse=True)

        return instance

    @staticmethod
    def _categorize(text: str, ability_id: int) -> str:
        """Categorize an ability based on its text."""
        if ability_id in EVERGREEN_IDS:
            return "keyword"

        # Check each category pattern
        for category, pattern in CATEGORY_PATTERNS.items():
            if pattern.search(text):
                return category

        # Default based on text structure
        if len(text) < 20 and not any(c in text for c in "{}()"):
            return "keyword"

        return "complex"

    def find_keywords(self, card_text: str) -> list[Ability]:
        """Find all keywords present in card text."""
        if not card_text:
            return []

        found = []
        text_lower = card_text.lower()

        for ability in self._keywords:
            # Word boundary match
            pattern = r"\b" + re.escape(ability.text.lower()) + r"\b"
            if re.search(pattern, text_lower):
                found.append(ability)

        return found

    def categorize_card(self, oracle_text: str) -> dict[str, list[str]]:
        """Categorize a card's abilities by theme.

        Returns a dict mapping category -> list of matched ability texts.
        """
        if not oracle_text:
            return {}

        categories: dict[str, list[str]] = {}

        # Check keywords
        keywords = self.find_keywords(oracle_text)
        if keywords:
            categories["keywords"] = [k.text for k in keywords]

        # Check theme patterns directly on oracle text
        for category, pattern in CATEGORY_PATTERNS.items():
            if category == "keyword":
                continue
            matches = pattern.findall(oracle_text)
            if matches or pattern.search(oracle_text):
                if category not in categories:
                    categories[category] = []
                # Store the matched pattern name, not the regex matches
                categories[category].append(category)

        return categories

    def get_synergy_themes(self, oracle_text: str) -> set[str]:
        """Get synergy-relevant themes from card text.

        Returns themes that are useful for synergy detection:
        sacrifice, graveyard, counters, tokens, etc.
        """
        if not oracle_text:
            return set()

        themes = set()
        text_lower = oracle_text.lower()

        # Direct theme detection
        theme_checks = {
            "sacrifice": ["sacrifice", "sacrificed"],
            "graveyard": ["graveyard", "from your graveyard", "dies"],
            "counters": ["+1/+1 counter", "-1/-1 counter", "counter on"],
            "tokens": ["create", "token"],
            "lifegain": ["gain life", "gains life", "lifelink"],
            "draw": ["draw a card", "draw cards", "draws a card"],
            "ramp": ["search your library for", "add {", "mana of any"],
            "etb": ["enters the battlefield", "when ~ enters"],
            "aristocrats": ["whenever a creature dies", "whenever another creature"],
            "spellslinger": ["instant or sorcery", "noncreature spell"],
            "tribal": ["creature type", "each creature you control"],
            "equipment": ["equip", "equipped creature"],
            "enchantments": ["enchantment", "enchanted"],
            "artifacts": ["artifact", "artifacts you control"],
            "flicker": ["exile", "return", "enters the battlefield"],
        }

        for theme, patterns in theme_checks.items():
            for pattern in patterns:
                if pattern in text_lower:
                    themes.add(theme)
                    break

        # Add keyword-based themes
        keywords = self.find_keywords(oracle_text)
        keyword_themes = {
            "Flying": "evasion",
            "Menace": "evasion",
            "Trample": "evasion",
            "Deathtouch": "removal",
            "Lifelink": "lifegain",
            "Haste": "aggro",
            "Vigilance": "aggro",
            "First strike": "combat",
            "Double strike": "combat",
        }
        for kw in keywords:
            if kw.text in keyword_themes:
                themes.add(keyword_themes[kw.text])

        return themes


@lru_cache(maxsize=1)
def get_ability_dictionary() -> AbilityDictionary:
    """Get the singleton ability dictionary."""
    return AbilityDictionary.load()


def categorize_card_abilities(oracle_text: str) -> dict[str, list[str]]:
    """Convenience function to categorize a card's abilities."""
    return get_ability_dictionary().categorize_card(oracle_text)


def get_card_themes(oracle_text: str) -> set[str]:
    """Convenience function to get synergy themes from card text."""
    return get_ability_dictionary().get_synergy_themes(oracle_text)
