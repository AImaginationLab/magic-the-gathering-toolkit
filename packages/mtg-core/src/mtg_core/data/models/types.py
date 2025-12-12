"""Type definitions for MTG data."""

from typing import Literal

Color = Literal["W", "U", "B", "R", "G"]

Format = Literal[
    "standard",
    "modern",
    "legacy",
    "vintage",
    "commander",
    "pioneer",
    "pauper",
    "historic",
    "brawl",
    "alchemy",
    "explorer",
    "timeless",
    "oathbreaker",
    "penny",
    "duel",
]

Rarity = Literal["common", "uncommon", "rare", "mythic"]
