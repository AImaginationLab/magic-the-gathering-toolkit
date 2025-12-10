"""Mana cost parsing and color identity utilities."""

import re
from typing import NamedTuple

# Color mappings
COLORS = {
    "W": "White",
    "U": "Blue",
    "B": "Black",
    "R": "Red",
    "G": "Green",
}

COLOR_ORDER = ["W", "U", "B", "R", "G"]

# Mana symbol patterns
MANA_SYMBOL_PATTERN = re.compile(r"\{([^}]+)\}")


class ManaCost(NamedTuple):
    """Parsed mana cost."""

    raw: str
    cmc: int
    colors: list[str]
    color_identity: list[str]
    generic: int
    colored: dict[str, int]  # e.g., {"W": 2, "U": 1}
    hybrid: list[str]  # e.g., ["W/U", "2/W"]
    phyrexian: list[str]  # e.g., ["W/P", "U/P"]
    x_count: int


def parse_mana_cost(mana_cost: str | None) -> ManaCost:
    """
    Parse a mana cost string into its components.

    Args:
        mana_cost: Mana cost string like "{2}{W}{W}" or "{X}{G}{G}"

    Returns:
        ManaCost with parsed components
    """
    if not mana_cost:
        return ManaCost(
            raw="",
            cmc=0,
            colors=[],
            color_identity=[],
            generic=0,
            colored={},
            hybrid=[],
            phyrexian=[],
            x_count=0,
        )

    symbols = MANA_SYMBOL_PATTERN.findall(mana_cost)

    generic = 0
    colored: dict[str, int] = {}
    hybrid: list[str] = []
    phyrexian: list[str] = []
    x_count = 0
    cmc = 0
    colors: set[str] = set()
    color_identity: set[str] = set()

    for symbol in symbols:
        symbol_upper = symbol.upper()

        # X mana
        if symbol_upper == "X":
            x_count += 1
            continue

        # Generic mana (number)
        if symbol_upper.isdigit():
            value = int(symbol_upper)
            generic += value
            cmc += value
            continue

        # Colorless mana symbol
        if symbol_upper == "C":
            cmc += 1
            continue

        # Phyrexian mana (e.g., "W/P" or "P/W")
        if "/P" in symbol_upper or "P/" in symbol_upper:
            phyrexian.append(symbol_upper)
            # Extract color from phyrexian
            color = symbol_upper.replace("/P", "").replace("P/", "")
            if color in COLORS:
                colors.add(color)
                color_identity.add(color)
            cmc += 1
            continue

        # Hybrid mana (e.g., "W/U" or "2/W")
        if "/" in symbol_upper:
            hybrid.append(symbol_upper)
            parts = symbol_upper.split("/")
            for part in parts:
                if part in COLORS:
                    color_identity.add(part)
                    colors.add(part)
            # Hybrid costs count as 1 CMC (or 2 for 2/C hybrids)
            if parts[0].isdigit():
                cmc += int(parts[0])
            else:
                cmc += 1
            continue

        # Single colored mana
        if symbol_upper in COLORS:
            colored[symbol_upper] = colored.get(symbol_upper, 0) + 1
            colors.add(symbol_upper)
            color_identity.add(symbol_upper)
            cmc += 1
            continue

    # Sort colors in WUBRG order
    sorted_colors = [c for c in COLOR_ORDER if c in colors]
    sorted_identity = [c for c in COLOR_ORDER if c in color_identity]

    return ManaCost(
        raw=mana_cost,
        cmc=cmc,
        colors=sorted_colors,
        color_identity=sorted_identity,
        generic=generic,
        colored=colored,
        hybrid=hybrid,
        phyrexian=phyrexian,
        x_count=x_count,
    )


def calculate_color_identity(
    mana_cost: str | None,
    card_text: str | None,
    color_indicator: list[str] | None = None,
) -> list[str]:
    """
    Calculate a card's color identity for Commander format.

    Color identity includes:
    - Colors in mana cost
    - Colors in rules text mana symbols
    - Color indicator (for cards like Ancestral Vision)

    Args:
        mana_cost: The card's mana cost
        card_text: The card's rules text
        color_indicator: Explicit color indicator on the card

    Returns:
        List of colors in WUBRG order
    """
    identity: set[str] = set()

    # From mana cost
    if mana_cost:
        parsed = parse_mana_cost(mana_cost)
        identity.update(parsed.color_identity)

    # From card text (mana symbols in abilities)
    if card_text:
        symbols = MANA_SYMBOL_PATTERN.findall(card_text)
        for symbol in symbols:
            symbol_upper = symbol.upper()
            # Check for colors in hybrid symbols too
            if "/" in symbol_upper:
                parts = symbol_upper.split("/")
                for part in parts:
                    if part in COLORS:
                        identity.add(part)
            elif symbol_upper in COLORS:
                identity.add(symbol_upper)

    # From color indicator
    if color_indicator:
        for color in color_indicator:
            color_upper = color.upper()
            if color_upper in COLORS:
                identity.add(color_upper)
            else:
                # Handle full color names
                for abbrev, name in COLORS.items():
                    if color_upper == name.upper():
                        identity.add(abbrev)
                        break

    # Sort in WUBRG order
    return [c for c in COLOR_ORDER if c in identity]


def format_mana_cost(mana_cost: str | None) -> str:
    """
    Format a mana cost for display.

    Converts {2}{W}{W} to "2WW" for compact display.
    """
    if not mana_cost:
        return ""

    symbols = MANA_SYMBOL_PATTERN.findall(mana_cost)
    return "".join(symbols)


def mana_cost_to_emoji(mana_cost: str | None) -> str:
    """
    Convert mana cost to emoji representation.

    This is just for fun display purposes.
    """
    if not mana_cost:
        return ""

    emoji_map = {
        "W": "⚪",
        "U": "🔵",
        "B": "⚫",
        "R": "🔴",
        "G": "🟢",
        "C": "◇",
    }

    symbols = MANA_SYMBOL_PATTERN.findall(mana_cost)
    result = []

    for symbol in symbols:
        if symbol.upper() in emoji_map:
            result.append(emoji_map[symbol.upper()])
        elif symbol.isdigit():
            result.append(f"({symbol})")
        elif symbol.upper() == "X":
            result.append("(X)")
        else:
            result.append(f"{{{symbol}}}")

    return "".join(result)
