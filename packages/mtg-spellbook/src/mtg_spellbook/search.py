"""Search query parsing for the TUI."""

from __future__ import annotations

import shlex

from mtg_core.data.models.inputs import SearchCardsInput


def parse_search_query(query: str) -> SearchCardsInput:
    """Parse search query with filters.

    Supports filters like:
        t:creature - card type
        c:RG - colors
        ci:WU - color identity
        cmc:3 - mana value
        f:modern - format
        r:mythic - rarity
        set:MH2 - set code
        text:"draw a card" - oracle text (quoted for spaces)
        kw:flying - keyword
        artist:"Michal Ivan" - artist name (quoted for spaces)
    """
    filters: dict[str, str | list[str] | int | None] = {"page_size": 25}
    name_parts = []

    # Use shlex to properly handle quoted strings
    try:
        tokens = shlex.split(query)
    except ValueError:
        # Fall back to simple split if quotes are unbalanced
        tokens = query.split()

    for token in tokens:
        if ":" in token:
            key, value = token.split(":", 1)
            key = key.lower()
            if key == "t":
                filters["type"] = value
            elif key == "c":
                filters["colors"] = list(value.upper())
            elif key == "ci":
                filters["color_identity"] = list(value.upper())
            elif key == "cmc" and value.isdigit():
                filters["cmc"] = int(value)
            elif key == "f":
                filters["format_legal"] = value
            elif key == "r":
                filters["rarity"] = value
            elif key == "set":
                filters["set_code"] = value
            elif key == "text":
                filters["text"] = value
            elif key == "kw":
                filters["keywords"] = [value]
            elif key == "artist":
                filters["artist"] = value
            else:
                # Unknown filter key, treat as part of name
                name_parts.append(token)
        else:
            name_parts.append(token)

    if name_parts:
        filters["name"] = " ".join(name_parts)

    return SearchCardsInput(**filters)  # type: ignore[arg-type]
