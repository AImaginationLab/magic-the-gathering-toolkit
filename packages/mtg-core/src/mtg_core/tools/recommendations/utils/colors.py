"""Color identity utilities for deck recommendations.

Provides helper functions for color identity comparison and manipulation.
"""

from __future__ import annotations

# Color name mappings
COLOR_NAMES: dict[str, str] = {
    "W": "White",
    "U": "Blue",
    "B": "Black",
    "R": "Red",
    "G": "Green",
}

# All valid color symbols
VALID_COLORS: frozenset[str] = frozenset({"W", "U", "B", "R", "G"})


def get_color_name(color: str) -> str:
    """Get the full name for a color symbol.

    Args:
        color: Single color symbol (W, U, B, R, G)

    Returns:
        Full color name, or the original symbol if not found.
    """
    return COLOR_NAMES.get(color.upper(), color)


def get_color_names(colors: list[str]) -> str:
    """Get formatted color names string.

    Args:
        colors: List of color symbols

    Returns:
        Slash-separated color names (e.g., "Blue/Black")
    """
    return "/".join(get_color_name(c) for c in sorted(colors))


def color_fits_identity(
    card_colors: list[str] | set[str] | None,
    deck_identity: list[str] | set[str],
) -> bool:
    """Check if a card's colors fit within a deck's color identity.

    A card fits if all its colors are within the deck's identity.
    Colorless cards (empty colors) fit any deck.

    Args:
        card_colors: Card's color identity (None or empty means colorless)
        deck_identity: Deck's color identity

    Returns:
        True if the card can be played in the deck.
    """
    if not card_colors:
        return True  # Colorless fits anywhere

    card_set = set(card_colors) if not isinstance(card_colors, set) else card_colors
    deck_set = set(deck_identity) if not isinstance(deck_identity, set) else deck_identity

    return card_set.issubset(deck_set)


def colors_intersect(
    colors1: list[str] | set[str] | None,
    colors2: list[str] | set[str],
) -> bool:
    """Check if two color identities share at least one color.

    Empty/colorless identities are considered to not intersect with anything.

    Args:
        colors1: First color identity
        colors2: Second color identity

    Returns:
        True if there's at least one shared color.
    """
    if not colors1:
        return False

    set1 = set(colors1) if not isinstance(colors1, set) else colors1
    set2 = set(colors2) if not isinstance(colors2, set) else colors2

    return bool(set1.intersection(set2))


def extract_colors_from_mana_cost(mana_cost: str) -> list[str]:
    """Extract color symbols from a mana cost string.

    Args:
        mana_cost: Mana cost string like "{2}{U}{B}"

    Returns:
        List of unique color symbols found (e.g., ["U", "B"])
    """
    colors = []
    for color in VALID_COLORS:
        if color in mana_cost:
            colors.append(color)
    return colors


def normalize_colors(colors: list[str] | None) -> list[str]:
    """Normalize and validate a list of color symbols.

    Args:
        colors: List of color symbols (may contain invalid values)

    Returns:
        Sorted list of valid color symbols only.
    """
    if not colors:
        return []
    return sorted(c.upper() for c in colors if c.upper() in VALID_COLORS)
