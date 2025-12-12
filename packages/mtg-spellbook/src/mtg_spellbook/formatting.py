"""Mana symbols and text formatting utilities."""

from __future__ import annotations

import re

# Rich markup colored mana blocks for display
MANA_SYMBOLS = {
    "W": "[white on white]  [/]",  # White
    "U": "[blue on blue]  [/]",  # Blue
    "B": "[black on black]  [/]",  # Black
    "R": "[red on red]  [/]",  # Red
    "G": "[green on green]  [/]",  # Green
}

# Pretty mana symbol representations using actual MTG-style symbols
# These use Unicode characters that resemble the official mana symbols
# Each symbol includes a trailing space for better readability
MANA_DISPLAY = {
    # Basic mana - using colored circle emoji for visibility
    "{W}": "⚪ ",  # White - white circle (cleaner than sun)
    "{U}": "💧 ",  # Blue - water droplet (blue mana symbol)
    "{B}": "💀 ",  # Black - skull (black mana symbol)
    "{R}": "🔥 ",  # Red - fire (red mana symbol is a fireball)
    "{G}": "🌲 ",  # Green - evergreen tree (closer to MTG tree)
    "{C}": "◇ ",  # Colorless - diamond (cleaner)
    # Tap/Untap - using larger emoji
    "{T}": "🔄 ",  # Tap - counterclockwise arrows (larger)
    "{Q}": "🔃 ",  # Untap - clockwise arrows
    # Special
    "{X}": "Ⓧ ",  # X mana
    "{S}": "❄️ ",  # Snow mana - snowflake
    "{E}": "⚡ ",  # Energy
}

# Generic mana numbers - using circled numbers for better spacing
GENERIC_MANA = {
    0: "⓪ ",
    1: "① ",
    2: "② ",
    3: "③ ",
    4: "④ ",
    5: "⑤ ",
    6: "⑥ ",
    7: "⑦ ",
    8: "⑧ ",
    9: "⑨ ",
    10: "⑩ ",
}

# Flavor quotes for REPL
FLAVOR_QUOTES = [
    '"The spark ignites. The journey begins."',
    '"In the multiverse, every spell tells a story."',
    '"Knowledge is the ultimate power."',
    '"From the chaos of mana, order is forged."',
    '"Every planeswalker was once a beginner."',
]

GOODBYE_QUOTES = [
    '"Until we meet again, planeswalker."',
    '"May your draws be ever in your favor."',
    '"The spell fades, but the magic remains."',
    '"Go forth and conquer the multiverse!"',
    '"Another chapter closes in the Blind Eternities..."',
]


def prettify_mana(text: str) -> str:
    """Convert mana symbols to pretty Unicode representations."""
    result = text

    # IMPORTANT: Process complex symbols BEFORE simple ones to avoid partial replacements

    # Replace hybrid mana like {W/U} with both symbols
    result = re.sub(
        r"\{([WUBRGC])/([WUBRGC])\}",
        lambda m: f"{MANA_DISPLAY.get('{' + m.group(1) + '}', m.group(1))}/{MANA_DISPLAY.get('{' + m.group(2) + '}', m.group(2))}",
        result,
    )

    # Replace Phyrexian mana like {W/P}
    result = re.sub(
        r"\{([WUBRG])/P\}",
        lambda m: f"{MANA_DISPLAY.get('{' + m.group(1) + '}', m.group(1))}ᵖ",
        result,
    )

    # Replace generic mana {1}, {2}, etc with emoji number circles (keycap style)
    def replace_generic(match: re.Match[str]) -> str:
        num = int(match.group(1))
        if num in GENERIC_MANA:
            return GENERIC_MANA[num]
        elif num <= 20:
            # Fall back to circled numbers for 11-20
            return chr(0x2460 + num - 1)
        else:
            return f"({num})"

    result = re.sub(r"\{(\d+)\}", replace_generic, result)

    # Replace specific symbols last (after complex patterns are handled)
    for symbol, pretty in MANA_DISPLAY.items():
        result = result.replace(symbol, pretty)

    return result


def strip_quotes(s: str) -> str:
    """Strip surrounding quotes from a string."""
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s
