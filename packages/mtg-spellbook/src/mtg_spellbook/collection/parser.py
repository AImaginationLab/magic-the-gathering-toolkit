"""Collection card input parsing utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


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

# Pattern for set context line: "FIN:" or "mkm:" (sets context for following lines)
SET_CONTEXT_PATTERN = re.compile(r"^([A-Za-z0-9]{2,5}):$", re.IGNORECASE)

# Pattern for standalone collector number (when in set context): "345", "123a", "2 345", "3x 123"
COLLECTOR_ONLY_PATTERN = re.compile(
    r"^(?:(\d+)x?\s+)?#?(\d+[a-z]?)(?:\s+\*?f(?:oil)?\*?)?$", re.IGNORECASE
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


def parse_card_list(text: str, default_quantity: int = 1) -> list[ParsedCardInput]:
    """Parse a multi-line card list with set context support.

    Supports set context lines that apply to subsequent entries:
        fin:
        345
        239
        2x 421 *f*
        mkm:
        123
        4 Sol Ring

    Lines following a set context (e.g., "fin:") will use that set code
    if they contain only collector numbers. Regular card entries (names,
    full set+number, etc.) are parsed normally and don't use the context.

    Args:
        text: Multi-line text containing card entries
        default_quantity: Default quantity for entries without a count

    Returns:
        List of ParsedCardInput for all valid entries
    """
    results: list[ParsedCardInput] = []
    current_set_context: str | None = None

    for line in text.splitlines():
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#") or line.startswith("//"):
            continue

        # Check for set context line (e.g., "fin:" or "MKM:")
        context_match = SET_CONTEXT_PATTERN.match(line)
        if context_match:
            current_set_context = context_match.group(1).lower()
            continue

        # If we have a set context, check for collector-number-only lines
        if current_set_context:
            collector_match = COLLECTOR_ONLY_PATTERN.match(line)
            if collector_match:
                quantity = (
                    int(collector_match.group(1)) if collector_match.group(1) else default_quantity
                )
                collector_number = collector_match.group(2)
                # Check for foil marker in the line
                foil = bool(re.search(r"\*?f(?:oil)?\*?", line, re.IGNORECASE))
                results.append(
                    ParsedCardInput(
                        card_name=None,
                        quantity=quantity,
                        foil=foil,
                        set_code=current_set_context,
                        collector_number=collector_number,
                    )
                )
                continue

        # Fall back to standard parsing
        parsed = parse_card_input(line, default_quantity)
        if parsed.card_name or parsed.collector_number:
            results.append(parsed)

    return results


def load_card_list_from_file(file_path: Path | str) -> list[ParsedCardInput]:
    """Load and parse a card list from a file.

    Supports .txt and .yaml/.yml files.

    Args:
        file_path: Path to the card list file

    Returns:
        List of ParsedCardInput for all valid entries
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Card list file not found: {path}")

    content = path.read_text(encoding="utf-8")

    if path.suffix.lower() in (".yaml", ".yml"):
        return _parse_yaml_card_list(content)

    return parse_card_list(content)


def _parse_yaml_card_list(content: str) -> list[ParsedCardInput]:
    """Parse a YAML-formatted card list.

    Expected format:
        cards:
          fin:
            - 345
            - 239
            - "421 *f*"
          mkm:
            - 123
            - "4x 456"
          names:
            - "4 Sol Ring"
            - "Lightning Bolt [M21]"

    Or simple list format:
        - fin 345
        - fin 239
        - "4 Sol Ring"
    """
    import yaml

    data = yaml.safe_load(content)

    if data is None:
        return []

    results: list[ParsedCardInput] = []

    # Handle dict format with set groupings
    if isinstance(data, dict):
        cards_section = data.get("cards", data)
        if isinstance(cards_section, dict):
            for set_or_key, entries in cards_section.items():
                if not isinstance(entries, list):
                    continue

                for entry in entries:
                    entry_str = str(entry).strip()
                    if not entry_str:
                        continue

                    # "names" key means parse as full card entries
                    if set_or_key.lower() == "names":
                        parsed = parse_card_input(entry_str)
                    else:
                        # Use set_or_key as set context
                        collector_match = COLLECTOR_ONLY_PATTERN.match(entry_str)
                        if collector_match:
                            quantity = (
                                int(collector_match.group(1)) if collector_match.group(1) else 1
                            )
                            collector_number = collector_match.group(2)
                            foil = bool(re.search(r"\*?f(?:oil)?\*?", entry_str, re.IGNORECASE))
                            parsed = ParsedCardInput(
                                card_name=None,
                                quantity=quantity,
                                foil=foil,
                                set_code=set_or_key.lower(),
                                collector_number=collector_number,
                            )
                        else:
                            parsed = parse_card_input(entry_str)

                    if parsed.card_name or parsed.collector_number:
                        results.append(parsed)

    # Handle simple list format
    elif isinstance(data, list):
        for entry in data:
            entry_str = str(entry).strip()
            if entry_str:
                parsed = parse_card_input(entry_str)
                if parsed.card_name or parsed.collector_number:
                    results.append(parsed)

    return results
