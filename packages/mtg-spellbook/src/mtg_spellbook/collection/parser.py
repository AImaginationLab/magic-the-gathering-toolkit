"""Collection card input parsing utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ParsedCardInput:
    """Result of parsing a card input string."""

    card_name: str | None  # None if set_code/collector_number identify a specific printing
    quantity: int
    foil: bool
    set_code: str | None
    collector_number: str | None


# Pattern for "N? SET NUMBER" format: e.g., "2 fca 27" or "fca 27" or "M21 123"
# Optional quantity (with optional x suffix), 2-5 char set code, collector number
SET_NUMBER_PATTERN = re.compile(
    r"^(?:(\d+)x?\s+)?([A-Za-z0-9]{2,5})\s+#?(\d+[a-z]?)$", re.IGNORECASE
)

# Pattern for quantity prefix: "4" or "4x"
QUANTITY_PREFIX_PATTERN = re.compile(r"^(\d+)x?\s+(.+)$")

# Pattern for bracket/paren set info: [M21], [M21 #123], (M21), (M21 #123)
BRACKET_SET_PATTERN = re.compile(r"\[([A-Za-z0-9]+)(?:\s*#?\s*(\d+[a-z]?))?\]\s*$")
PAREN_SET_PATTERN = re.compile(r"\(([A-Za-z0-9]+)(?:\s*#?\s*(\d+[a-z]?))?\)\s*$")

# Foil markers to check (ordered longest first)
FOIL_MARKERS = ["*foil*", "(foil)", "*f*", "foil"]


def parse_card_input(raw_input: str, default_quantity: int = 1) -> ParsedCardInput:
    """Parse a card input string into structured data.

    Supports multiple formats:
    - "Lightning Bolt" - card name only
    - "4 Lightning Bolt" or "4x Lightning Bolt" - quantity + card name
    - "fca 27" - set code + collector number
    - "2 fca 27" or "2x fca 27" - quantity + set code + collector number
    - "Lightning Bolt [M21]" - card name + set code
    - "Lightning Bolt [M21 #123]" - card name + set + collector number
    - "Lightning Bolt *F*" or "Lightning Bolt foil" - foil markers

    Args:
        raw_input: The raw input string from user
        default_quantity: Default quantity if not specified in input

    Returns:
        ParsedCardInput with extracted fields
    """
    text = raw_input.strip()
    quantity = default_quantity
    foil = False
    set_code: str | None = None
    collector_number: str | None = None

    # Check for foil markers at the end (before other parsing)
    text_lower = text.lower()
    for marker in FOIL_MARKERS:
        if text_lower.endswith(marker):
            foil = True
            text = text[: -len(marker)].strip()
            text_lower = text.lower()
            break

    # Also check for trailing asterisk (e.g., "Lightning Bolt *")
    if text.endswith("*"):
        foil = True
        text = text[:-1].strip()
        text_lower = text.lower()

    # Check for standalone "f" as foil marker (e.g., "fca 27 f")
    if text_lower.endswith(" f"):
        foil = True
        text = text[:-2].strip()

    # Check for "N? SET NUMBER" format (e.g., "fca 27" or "2 fca 27")
    set_number_match = SET_NUMBER_PATTERN.match(text)
    if set_number_match:
        if set_number_match.group(1):
            quantity = int(set_number_match.group(1))
        set_code = set_number_match.group(2).lower()
        collector_number = set_number_match.group(3)
        return ParsedCardInput(
            card_name=None,
            quantity=quantity,
            foil=foil,
            set_code=set_code,
            collector_number=collector_number,
        )

    # Check for quantity prefix (e.g., "4 Lightning Bolt" or "4x Lightning Bolt")
    qty_match = QUANTITY_PREFIX_PATTERN.match(text)
    if qty_match:
        quantity = int(qty_match.group(1))
        text = qty_match.group(2).strip()

    # Check for bracket/paren set info (e.g., "[M21]" or "[M21 #123]")
    bracket_match = BRACKET_SET_PATTERN.search(text)
    paren_match = PAREN_SET_PATTERN.search(text)
    set_match = bracket_match or paren_match
    if set_match:
        set_code = set_match.group(1).lower()
        if set_match.group(2):
            collector_number = set_match.group(2)
        # Remove the matched part from card name
        text = text[: set_match.start()].strip()

    # Remaining text is the card name
    return ParsedCardInput(
        card_name=text if text else None,
        quantity=quantity,
        foil=foil,
        set_code=set_code,
        collector_number=collector_number,
    )
