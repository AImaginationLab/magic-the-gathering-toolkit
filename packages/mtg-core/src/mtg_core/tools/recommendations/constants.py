"""Constants for deck recommendations.

Contains deck targets, thresholds, patterns, theme keywords, and tribal types.
"""

from __future__ import annotations

# Color-fixing requirements by color count
COLOR_FIXING_REQUIREMENTS: dict[int, int] = {
    1: 0,  # Mono-color needs no fixing
    2: 6,  # 2 colors: 6+ dual lands
    3: 12,  # 3 colors: 12+ non-basics
    4: 18,  # 4 colors: 18+ non-basics
    5: 22,  # 5 colors: 22+ non-basics
}

# Patterns to detect color-fixing lands
DUAL_LAND_PATTERNS: list[str] = [
    r"add \{[WUBRG]\} or \{[WUBRG]\}",  # Dual lands
    r"add \{[WUBRG]\}, \{[WUBRG]\}, or \{[WUBRG]\}",  # Triomes
    r"add one mana of any color",  # Any color
    r"add .* mana of any type",  # Any type
    r"search your library for .* land",  # Fetch lands
]

# Basic land names for distribution
BASIC_LAND_NAMES: dict[str, str] = {
    "W": "Plains",
    "U": "Island",
    "B": "Swamp",
    "R": "Mountain",
    "G": "Forest",
}

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
        "other": (0, 5),  # Limit misc card types
    },
    "standard": {
        "total": 60,
        "creature": (20, 28),
        "spell": (8, 16),
        "artifact": (0, 6),
        "enchantment": (0, 6),
        "land": (22, 26),
        "planeswalker": (0, 3),
        "other": (0, 4),  # Limit misc card types
    },
}

# Deck quality validation thresholds
CURVE_THRESHOLDS: dict[str, dict[str, float]] = {
    "commander": {"avg_cmc_max": 3.5, "low_cmc_ratio_min": 0.25},  # 25%+ at CMC 1-2
    "standard_aggro": {"avg_cmc_max": 2.5, "low_cmc_ratio_min": 0.50},
    "standard_midrange": {"avg_cmc_max": 3.5, "low_cmc_ratio_min": 0.30},
    "standard_control": {"avg_cmc_max": 4.0, "low_cmc_ratio_min": 0.20},
}

INTERACTION_MINIMUMS: dict[str, int] = {
    "commander": 10,  # 10+ removal/interaction spells
    "standard": 6,
}

# Archetype-specific quality scoring weights
# Each archetype emphasizes different aspects of deck building
# Weights: curve, interaction, mana_base, win_conditions (must sum to ~1.0)
ARCHETYPE_WEIGHTS: dict[str, dict[str, float]] = {
    "Aggro": {"curve": 0.40, "interaction": 0.15, "mana_base": 0.25, "win_con": 0.20},
    "Control": {"curve": 0.15, "interaction": 0.40, "mana_base": 0.25, "win_con": 0.20},
    "Combo": {"curve": 0.15, "interaction": 0.20, "mana_base": 0.25, "win_con": 0.40},
    "Midrange": {"curve": 0.25, "interaction": 0.25, "mana_base": 0.25, "win_con": 0.25},
    "Tokens": {"curve": 0.25, "interaction": 0.20, "mana_base": 0.25, "win_con": 0.30},
    "Graveyard": {"curve": 0.20, "interaction": 0.20, "mana_base": 0.25, "win_con": 0.35},
    "Sacrifice": {"curve": 0.20, "interaction": 0.20, "mana_base": 0.25, "win_con": 0.35},
    "Artifacts": {"curve": 0.25, "interaction": 0.20, "mana_base": 0.30, "win_con": 0.25},
    "Enchantments": {"curve": 0.20, "interaction": 0.20, "mana_base": 0.30, "win_con": 0.30},
    "Spellslinger": {"curve": 0.30, "interaction": 0.25, "mana_base": 0.20, "win_con": 0.25},
    "Reanimator": {"curve": 0.15, "interaction": 0.20, "mana_base": 0.25, "win_con": 0.40},
    "Voltron": {"curve": 0.30, "interaction": 0.20, "mana_base": 0.25, "win_con": 0.25},
    "Stax": {"curve": 0.20, "interaction": 0.35, "mana_base": 0.25, "win_con": 0.20},
    "Blink": {"curve": 0.25, "interaction": 0.20, "mana_base": 0.25, "win_con": 0.30},
    "Landfall": {"curve": 0.20, "interaction": 0.20, "mana_base": 0.35, "win_con": 0.25},
    # Default for tribal and unknown archetypes
    "_default": {"curve": 0.25, "interaction": 0.25, "mana_base": 0.25, "win_con": 0.25},
}

# Keywords indicating interaction (removal, counterspells, etc.)
INTERACTION_PATTERNS: list[str] = [
    r"destroy target",
    r"exile target",
    r"deals? \d+ damage to",
    r"counter target",
    r"-\d+/-\d+ until",
    r"return target .* to",
    r"tap target",
    r"can't attack",
    r"can't block",
]

# Win condition detection patterns
WIN_CONDITION_PATTERNS: dict[str, list[str]] = {
    "evasion": [
        r"flying",
        r"can't be blocked",
        r"unblockable",
        r"menace",
        r"trample",
        r"shadow",
    ],
    "finisher": [r"win the game", r"lose the game", r"infect", r"commander damage"],
    "burn": [
        r"deals? \d+ damage to .* player",
        r"each opponent loses",
        r"deals damage equal to",
    ],
    "value_engine": [r"draw .* card", r"create .* token", r"search your library"],
}

WIN_CONDITION_THRESHOLDS: dict[str, dict[str, int]] = {
    "commander": {
        "combo_min": 1,  # At least 1 complete combo OR
        "evasion_min": 6,  # 6+ evasive creatures OR
        "finisher_min": 2,  # 2+ finishers
    },
    "standard_aggro": {"evasion_min": 8, "burn_min": 4},
    "standard_control": {"finisher_min": 3, "value_engine_min": 8},
}

# Improved synergy thresholds
TRIBAL_THRESHOLD_STRONG = 25  # 25+ creatures = strong tribal
TRIBAL_THRESHOLD_VIABLE = 15  # 15+ = viable tribal
TRIBAL_THRESHOLD_WEAK = 8  # 8+ = weak tribal (current)

THEME_THRESHOLD_STRONG = 15  # 15+ supporting cards = strong theme
THEME_THRESHOLD_VIABLE = 10  # 10+ = viable theme
THEME_THRESHOLD_WEAK = 5  # 5+ = weak theme

# Tribal lord detection patterns - these cards buff other creatures of a type
# but may not be that creature type themselves
LORD_PATTERNS: list[str] = [
    r"other .+ creatures? (you control )?get \+\d+/\+\d+",  # "Other Zombie creatures get +1/+1"
    r"other .+ creatures? (you control )?have",  # "Other Goblins have haste"
    r"creatures? you control get \+\d+/\+\d+ for each",  # Anthem effects
    r"whenever (a|another) .+ (enters|dies|attacks)",  # Tribal payoffs
    r"choose a creature type",  # Changeling lords
]

# Ramp detection patterns
RAMP_PATTERNS: list[str] = [
    r"add \{[WUBRGC]\}",  # Mana dorks: "add {G}"
    r"add .+ mana",  # "add two mana of any color"
    r"search your library for .* (basic )?land",  # Land ramp
    r"put .* land .* onto the battlefield",  # Land ramp
    r"mana rocks?",  # Type line check
    r"whenever .* tap .* for mana",  # Mana doublers
]

# Card advantage detection patterns
CARD_ADVANTAGE_PATTERNS: dict[str, list[str]] = {
    "draw": [
        r"draw (a|two|three|\d+) cards?",
        r"draws? .* cards?",
        r"whenever .* draw",
    ],
    "selection": [
        r"scry \d+",
        r"look at the top .* cards?",
        r"surveil \d+",
        r"search your library",
    ],
    "recursion": [
        r"return .* from .* graveyard",
        r"cast .* from .* graveyard",
        r"flashback",
    ],
}

# Ramp thresholds by average CMC
RAMP_THRESHOLDS: dict[str, dict[str, int]] = {
    "commander": {
        "high_cmc": 8,  # 8+ ramp for avg CMC > 3.5
        "medium_cmc": 5,  # 5+ ramp for avg CMC 3.0-3.5
        "low_cmc": 3,  # 3+ ramp for avg CMC < 3.0
    },
    "standard": {
        "high_cmc": 6,
        "medium_cmc": 4,
        "low_cmc": 2,
    },
}

# Card advantage minimums by archetype style
CARD_ADVANTAGE_MINIMUMS: dict[str, int] = {
    "commander_control": 12,  # Control needs lots of draw
    "commander_midrange": 8,  # Midrange needs refill
    "commander_aggro": 4,  # Aggro needs some gas
    "commander_combo": 10,  # Combo needs to find pieces
    "standard_control": 8,
    "standard_midrange": 5,
    "standard_aggro": 2,
}

# Theme keywords to detect deck archetypes (alphabetically sorted for UI)
THEME_KEYWORDS: dict[str, list[str]] = {
    "Aggro": ["haste", "attack", "combat", "first strike"],
    "Artifacts": ["artifact", "equipment", "vehicle", "metalcraft"],
    "Blink": ["exile", "return", "enters", "leaves"],
    "Burn": ["damage to", "deal damage", "lightning", "fire"],
    "Clones": ["copy", "clone", "becomes a copy"],
    "Control": ["counter", "destroy", "exile", "return to hand"],
    "Counters": ["+1/+1 counter", "proliferate", "counter on"],
    "Discard": ["discard", "hand", "madness"],
    "Draw": ["draw", "card", "scry"],
    "Enchantments": ["enchantment", "constellation", "aura"],
    "Energy": ["energy", "{e}"],
    "Graveyard": ["graveyard", "dies", "sacrifice", "reanimate", "return from"],
    "Landfall": ["land enters", "landfall", "play a land"],
    "Lands": ["land", "forest", "island", "mountain", "plains", "swamp"],
    "Lifegain": ["gain life", "lifelink", "whenever you gain life"],
    "Mill": ["mill", "library into", "graveyard from library"],
    "Ramp": ["add {", "mana", "search your library for a land"],
    "Reanimator": ["graveyard to the battlefield", "return.*creature", "reanimate"],
    "Sacrifice": ["sacrifice", "dies", "death trigger"],
    "Spellslinger": ["instant", "sorcery", "prowess", "magecraft"],
    "Stax": ["can't", "each player", "sacrifice a", "opponents can't"],
    "Superfriends": ["planeswalker", "loyalty"],
    "Tokens": ["create", "token", "populate", "convoke"],
    "Voltron": ["equipment", "aura", "attach", "equipped creature"],
}

# Common tribal types to detect (alphabetically sorted for UI)
TRIBAL_TYPES: list[str] = [
    "Angel",
    "Artifact",
    "Beast",
    "Bird",
    "Cat",
    "Cleric",
    "Demon",
    "Dinosaur",
    "Dog",
    "Dragon",
    "Elemental",
    "Elf",
    "Faerie",
    "Fungus",
    "Giant",
    "Goblin",
    "Horror",
    "Human",
    "Hydra",
    "Knight",
    "Merfolk",
    "Ninja",
    "Pirate",
    "Rat",
    "Rogue",
    "Shaman",
    "Skeleton",
    "Sliver",
    "Snake",
    "Soldier",
    "Spider",
    "Spirit",
    "Treefolk",
    "Vampire",
    "Warrior",
    "Wizard",
    "Wolf",
    "Zombie",
]

# Minimum card counts for filtered suggestions
TRIBAL_FILTER_MINIMUM = 5  # Need 5+ creatures of type when user filters by tribal
THEME_FILTER_MINIMUM = 3  # Need 3+ cards when user filters by theme
