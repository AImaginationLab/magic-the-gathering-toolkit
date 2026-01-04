"""Deck analysis API routes."""

from __future__ import annotations

import logging
import re

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from mtg_core.data.models import (
    AnalyzeDeckInput,
    ColorAnalysisResult,
    CompositionResult,
    DeckHealthResult,
    DeckValidationResult,
    ManaCurveResult,
    PriceAnalysisResult,
    ValidateDeckInput,
)
from mtg_core.exceptions import CardNotFoundError, MTGError, ValidationError
from mtg_core.tools import deck as deck_tools
from mtg_core.tools.deck_impact import DeckImpact, calculate_deck_impact


class DeckImpactInput(BaseModel):
    """Input for deck impact calculation."""

    card_name: str
    deck_id: int
    quantity: int = 1


class ImportDeckInput(BaseModel):
    """Input for importing a deck from URL or text."""

    url: str | None = Field(None, description="URL to import deck from")
    text: str | None = Field(None, description="Deck list text to parse")
    name: str | None = Field(None, description="Override deck name")
    format: str | None = Field(None, description="Override format")


class ParsedCard(BaseModel):
    """A parsed card from deck import."""

    name: str
    quantity: int
    is_sideboard: bool = False
    is_maybeboard: bool = False
    is_commander: bool = False
    set_code: str | None = None
    collector_number: str | None = None


class ImportDeckResult(BaseModel):
    """Result of parsing a deck for import."""

    name: str
    format: str | None
    commander: str | None
    cards: list[ParsedCard]
    sideboard: list[ParsedCard]
    maybeboard: list[ParsedCard] = Field(default_factory=list)
    source_url: str | None = None
    errors: list[str] = Field(default_factory=list)


router = APIRouter()


logger = logging.getLogger(__name__)


@router.post("/validate", response_model=DeckValidationResult)
async def validate_deck(
    request: Request,
    body: ValidateDeckInput,
) -> DeckValidationResult:
    """Validate a deck against format rules."""
    db = request.app.state.db_manager.db
    try:
        return await deck_tools.validate_deck(db, body)
    except CardNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except MTGError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in validate_deck")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/analyze/mana-curve", response_model=ManaCurveResult)
async def analyze_mana_curve(
    request: Request,
    body: AnalyzeDeckInput,
) -> ManaCurveResult:
    """Analyze the mana curve of a deck."""
    db = request.app.state.db_manager.db
    return await deck_tools.analyze_mana_curve(db, body)


@router.post("/analyze/colors", response_model=ColorAnalysisResult)
async def analyze_colors(
    request: Request,
    body: AnalyzeDeckInput,
) -> ColorAnalysisResult:
    """Analyze the color distribution of a deck."""
    db = request.app.state.db_manager.db
    return await deck_tools.analyze_colors(db, body)


@router.post("/analyze/composition", response_model=CompositionResult)
async def analyze_composition(
    request: Request,
    body: AnalyzeDeckInput,
) -> CompositionResult:
    """Analyze the card type composition of a deck."""
    db = request.app.state.db_manager.db
    return await deck_tools.analyze_deck_composition(db, body)


@router.post("/analyze/price", response_model=PriceAnalysisResult)
async def analyze_price(
    request: Request,
    body: AnalyzeDeckInput,
) -> PriceAnalysisResult:
    """Analyze the price of a deck."""
    db = request.app.state.db_manager.db
    return await deck_tools.analyze_deck_price(db, body)


@router.post("/analyze/health", response_model=DeckHealthResult)
async def analyze_health(
    request: Request,
    body: AnalyzeDeckInput,
    deck_format: str | None = None,
) -> DeckHealthResult:
    """Comprehensive deck health analysis with score, archetype, and issues."""
    db = request.app.state.db_manager.db
    return await deck_tools.analyze_deck_health(db, body, deck_format)


@router.post("/analyze/impact", response_model=DeckImpact)
async def analyze_impact(
    request: Request,
    body: DeckImpactInput,
) -> DeckImpact:
    """Calculate the impact of adding a card to a deck.

    Shows what changes when adding a card: keywords added, themes strengthened,
    combat stats, type count changes, etc. Similar to WoW item comparison tooltips.
    """
    import time

    start = time.perf_counter()
    db = request.app.state.db_manager.db
    user_db = request.app.state.db_manager.user
    if user_db is None:
        raise HTTPException(status_code=503, detail="User database not available")
    try:
        result = await calculate_deck_impact(
            db,
            user_db,
            card_name=body.card_name,
            deck_id=body.deck_id,
            quantity=body.quantity,
        )
        duration_ms = (time.perf_counter() - start) * 1000
        if duration_ms > 100:
            logger.info(
                "Deck impact for '%s' (deck %d) took %.1fms",
                body.card_name,
                body.deck_id,
                duration_ms,
            )
        return result
    except CardNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except MTGError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in analyze_impact")
        raise HTTPException(status_code=500, detail="Internal server error") from e


def _parse_cardkingdom_form(html: str) -> str:
    """Parse deck from Card Kingdom affiliate form hidden input.

    Many deck sites include a Card Kingdom affiliate form with the deck list
    in a hidden input field with format: "4 Card Name||4 Card Name||..."

    Returns the parsed deck text or empty string if not found.
    """
    # Look for Card Kingdom form with hidden input containing deck list
    ck_input = re.search(
        r'<form[^>]*action="[^"]*cardkingdom\.com[^"]*"[^>]*>.*?'
        r'<input[^>]*name="c"[^>]*value="([^"]+)"',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if ck_input:
        deck_value = ck_input.group(1)
        # Unescape HTML entities
        deck_value = deck_value.replace("&#x27;", "'").replace("&amp;", "&")
        # Split by || delimiter and convert to deck list format
        cards = [c.strip() for c in deck_value.split("||") if c.strip()]
        return "\n".join(cards)
    return ""


def _parse_deck_list_text(
    text: str,
) -> tuple[
    list[ParsedCard],
    list[ParsedCard],
    list[ParsedCard],
    str | None,
    str | None,
    str | None,
]:
    """Parse deck list text in common formats.

    Supports:
    - "4 Card Name"
    - "4x Card Name"
    - "4 Card Name (SET) 123"
    - Section headers: About, Deck, Sideboard, Maybeboard, Commander, Companion
    - About section with Name and Format fields

    Returns: (main_deck, sideboard, maybeboard, commander, deck_name, deck_format)
    """
    lines = text.strip().split("\n")
    main_deck: list[ParsedCard] = []
    sideboard: list[ParsedCard] = []
    maybeboard: list[ParsedCard] = []
    commander: str | None = None
    deck_name: str | None = None
    deck_format: str | None = None

    current_section = "deck"

    # Pattern: quantity + card name + optional (SET) + optional collector number
    card_pattern = re.compile(
        r"^\s*(\d+)x?\s+(.+?)(?:\s+\(([A-Z0-9]+)\)\s*(\d+)?)?\s*$", re.IGNORECASE
    )

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for section headers
        line_lower = line.lower()
        if line_lower in ("about", "about:"):
            current_section = "about"
            continue
        if line_lower in ("deck", "deck:", "main deck", "main deck:", "main:"):
            current_section = "deck"
            continue
        if line_lower in (
            "sideboard",
            "sideboard:",
            "side",
            "side:",
            "sb",
            "sb:",
        ):
            current_section = "sideboard"
            continue
        if line_lower in (
            "maybeboard",
            "maybeboard:",
            "maybe",
            "maybe:",
            "mb",
            "mb:",
            "considering",
            "considering:",
        ):
            current_section = "maybeboard"
            continue
        if line_lower in ("commander", "commander:", "cmdr", "cmdr:"):
            current_section = "commander"
            continue
        if line_lower in ("companion", "companion:"):
            current_section = "companion"
            continue

        # Handle About section fields
        if current_section == "about":
            # Check for "Name <value>" or "Name: <value>" format
            if line_lower.startswith("name"):
                # Extract value after "Name" or "Name:"
                name_value = line[4:].lstrip(": \t")
                if name_value:
                    deck_name = name_value
                continue
            # Check for "Format <value>" or "Format: <value>"
            if line_lower.startswith("format"):
                format_value = line[6:].lstrip(": \t")
                if format_value:
                    deck_format = format_value.lower()
                continue
            # Skip other about section content
            continue

        # Try to parse as a card line
        match = card_pattern.match(line)
        if match:
            quantity = int(match.group(1))
            card_name = match.group(2).strip()
            set_code = match.group(3)
            collector_num = match.group(4)

            card = ParsedCard(
                name=card_name,
                quantity=quantity,
                is_sideboard=current_section == "sideboard",
                is_commander=current_section == "commander",
                set_code=set_code.upper() if set_code else None,
                collector_number=collector_num,
            )

            if current_section == "commander":
                commander = card_name
                card.is_commander = True
                main_deck.append(card)
            elif current_section == "sideboard":
                sideboard.append(card)
            elif current_section == "maybeboard":
                card.is_maybeboard = True
                maybeboard.append(card)
            else:
                main_deck.append(card)

    return main_deck, sideboard, maybeboard, commander, deck_name, deck_format


async def _fetch_deck_from_url(url: str) -> tuple[str, str | None, str | None]:
    """Fetch deck page and extract deck list.

    Returns: (deck_text, deck_name, format)
    """
    # Determine site and fetch strategy
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) MTGSpellbook/1.0",
        "Accept": "text/html,application/xhtml+xml",
    }

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        html = response.text

    deck_name = "Imported Deck"
    deck_format: str | None = None
    deck_text = ""

    # Parse based on site
    if "mtgdecks.net" in url:
        deck_name, deck_format, deck_text = _parse_mtgdecks_net(html, url)
    elif "moxfield.com" in url:
        deck_name, deck_format, deck_text = _parse_moxfield(html, url)
    elif "archidekt.com" in url:
        deck_name, deck_format, deck_text = _parse_archidekt(html, url)
    elif "tappedout.net" in url:
        deck_name, deck_format, deck_text = _parse_tappedout(html, url)
    elif "mtggoldfish.com" in url:
        deck_name, deck_format, deck_text = _parse_mtggoldfish(html, url)
    else:
        # Try generic parsing - look for common deck list patterns
        deck_text = _extract_generic_deck_list(html)

    return deck_text, deck_name, deck_format


def _parse_mtgdecks_net(html: str, url: str) -> tuple[str, str | None, str]:
    """Parse deck from mtgdecks.net."""
    deck_name = "Imported Deck"
    deck_format: str | None = None

    # Extract deck name from title
    title_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html, re.IGNORECASE)
    if title_match:
        deck_name = title_match.group(1).strip()
        # Clean up common suffixes
        deck_name = re.sub(r"\s*deck\s*$", "", deck_name, flags=re.IGNORECASE)
        deck_name = re.sub(r",\s*by\s+\w+$", "", deck_name, flags=re.IGNORECASE)

    # Extract format from URL or page
    url_lower = url.lower()
    for fmt in [
        "commander",
        "standard",
        "modern",
        "legacy",
        "vintage",
        "pioneer",
        "pauper",
        "historic",
    ]:
        if f"/{fmt}/" in url_lower or f"/{fmt}-" in url_lower:
            deck_format = fmt
            break

    deck_text = ""

    # Method 1 (most universal): Card Kingdom affiliate form (common across many deck sites)
    deck_text = _parse_cardkingdom_form(html)

    # Method 2: Look for <textarea id="arena_deck"> with the full deck list
    if not deck_text:
        arena_textarea = re.search(
            r'<textarea[^>]*id="arena_deck"[^>]*>(.*?)</textarea>',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if arena_textarea:
            deck_text = arena_textarea.group(1).strip()
            # Unescape HTML entities
            deck_text = deck_text.replace("&amp;", "&").replace("&#x27;", "'")

    # Method 3: Look for data-clipboard-text attribute on the export button
    if not deck_text:
        clipboard_match = re.search(
            r'data-clipboard-text="([^"]+)"',
            html,
            re.IGNORECASE,
        )
        if clipboard_match:
            deck_text = clipboard_match.group(1).strip()
            # Unescape HTML entities
            deck_text = deck_text.replace("&amp;", "&").replace("&#x27;", "'")

    # Method 4: Find the exportable deck list section (div with arena class)
    if not deck_text:
        arena_section = re.search(
            r'<div[^>]*class="[^"]*arena[^"]*"[^>]*>(.*?)</div>',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if arena_section:
            deck_text = re.sub(r"<[^>]+>", "\n", arena_section.group(1))
            deck_text = deck_text.strip()

    # Method 5: Look for card list with quantities
    if not deck_text:
        # Find all card entries like "4 Card Name" or links with quantities
        card_matches = re.findall(
            r"(\d+)\s*(?:x\s*)?<a[^>]*>([^<]+)</a>",
            html,
            re.IGNORECASE,
        )
        if card_matches:
            deck_lines = [f"{qty} {name.strip()}" for qty, name in card_matches]
            deck_text = "\n".join(deck_lines)

    # Method 6: Plain text extraction from pre/code blocks
    if not deck_text:
        pre_match = re.search(r"<pre[^>]*>(.*?)</pre>", html, re.DOTALL | re.IGNORECASE)
        if pre_match:
            deck_text = re.sub(r"<[^>]+>", "", pre_match.group(1))

    return deck_name, deck_format, deck_text


def _parse_moxfield(html: str, _url: str) -> tuple[str, str | None, str]:
    """Parse deck from moxfield.com - basic extraction."""
    # Moxfield uses React/JS heavily, so HTML parsing is limited
    # Users can export from the site and paste the text
    deck_name = "Moxfield Deck"
    title_match = re.search(r"<title>([^<|]+)", html)
    if title_match:
        deck_name = title_match.group(1).strip()
    return deck_name, None, ""


def _parse_archidekt(html: str, _url: str) -> tuple[str, str | None, str]:
    """Parse deck from archidekt.com - basic extraction."""
    deck_name = "Archidekt Deck"
    title_match = re.search(r"<title>([^<|]+)", html)
    if title_match:
        deck_name = title_match.group(1).strip()
    return deck_name, None, ""


def _parse_tappedout(html: str, _url: str) -> tuple[str, str | None, str]:
    """Parse deck from tappedout.net.

    TappedOut embeds the deck list in a hidden input field with format:
    "1 Card Name||1 Card Name||..."

    Also has data attributes: data-qty, data-board (main/side/maybe), data-name
    """
    deck_name = "TappedOut Deck"
    deck_format: str | None = None

    # Extract deck name from title tag
    title_match = re.search(r"<title>([^<]+?)\s*\(", html)
    if title_match:
        deck_name = title_match.group(1).strip()

    # Look for format in title (e.g., "Commander / EDH")
    format_in_title = re.search(
        r"\((Commander|EDH|Standard|Modern|Legacy|Vintage|Pioneer|Pauper)[^)]*\)",
        html,
        re.IGNORECASE,
    )
    if format_in_title:
        fmt = format_in_title.group(1).lower()
        deck_format = "commander" if fmt == "edh" else fmt

    # Method 1 (preferred): Parse data attributes (data-qty, data-board, data-name)
    # This preserves sideboard/maybeboard info
    # Pattern: data-qty="N" ... data-board="main|side|maybe" ... data-name="Card Name"
    card_entries = re.findall(
        r'data-qty="(\d+)"[^>]*data-board="(main|side|maybe)"[^>]*data-name="([^"]+)"',
        html,
    )
    if card_entries:
        # Aggregate quantities by (name, board) - TappedOut shows multiple entries for different printings
        card_totals: dict[tuple[str, str], int] = {}
        for qty, board, name in card_entries:
            key = (name, board)
            card_totals[key] = card_totals.get(key, 0) + int(qty)

        main_deck: list[str] = []
        sideboard: list[str] = []
        maybeboard: list[str] = []
        for (name, board), total_qty in card_totals.items():
            line = f"{total_qty} {name}"
            if board == "side":
                sideboard.append(line)
            elif board == "maybe":
                maybeboard.append(line)
            else:
                main_deck.append(line)

        deck_text = "\n".join(main_deck)
        if sideboard:
            deck_text += "\n\nSideboard\n" + "\n".join(sideboard)
        if maybeboard:
            deck_text += "\n\nMaybeboard\n" + "\n".join(maybeboard)
        return deck_name, deck_format, deck_text

    # Method 2 (fallback): Hidden input with "||" delimited deck list
    # Note: This doesn't preserve sideboard/maybeboard info
    hidden_input = re.search(r'<input[^>]*name="c"[^>]*value="([^"]+)"', html)
    if hidden_input:
        deck_value = hidden_input.group(1)
        # Decode HTML entities
        deck_value = deck_value.replace("&#x27;", "'").replace("&amp;", "&")
        # Split by || and format as deck list
        cards = deck_value.split("||")
        deck_lines = []
        for card in cards:
            card = card.strip()
            if card:
                deck_lines.append(card)
        if deck_lines:
            return deck_name, deck_format, "\n".join(deck_lines)

    # Fallback to generic extraction
    deck_text = _extract_generic_deck_list(html)
    return deck_name, deck_format, deck_text


def _parse_mtggoldfish(html: str, url: str) -> tuple[str, str | None, str]:
    """Parse deck from mtggoldfish.com."""
    deck_name = "MTGGoldfish Deck"
    deck_format: str | None = None

    title_match = re.search(r"<h1[^>]*class=\"title\"[^>]*>([^<]+)", html)
    if title_match:
        deck_name = title_match.group(1).strip()

    # Format from URL
    for fmt in ["commander", "standard", "modern", "legacy", "vintage", "pioneer", "pauper"]:
        if f"/{fmt}/" in url.lower():
            deck_format = fmt
            break

    deck_text = _extract_generic_deck_list(html)
    return deck_name, deck_format, deck_text


def _extract_generic_deck_list(html: str) -> str:
    """Try to extract deck list from any HTML using common patterns."""
    # Remove script and style tags
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Look for lines that match "N Card Name" pattern
    # First strip HTML tags
    text = re.sub(r"<[^>]+>", "\n", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&#\d+;", "", text)

    lines = text.split("\n")
    deck_lines = []

    card_pattern = re.compile(r"^\s*(\d+)x?\s+([A-Z][^0-9\n]{2,50})\s*$", re.IGNORECASE)

    for line in lines:
        line = line.strip()
        if card_pattern.match(line):
            deck_lines.append(line)

    return "\n".join(deck_lines)


@router.post("/import/parse", response_model=ImportDeckResult)
async def parse_deck_import(
    _request: Request,
    body: ImportDeckInput,
) -> ImportDeckResult:
    """Parse a deck from URL or text for preview before importing.

    Supports multiple deck sites and common text formats.
    """
    errors: list[str] = []
    deck_text = ""
    deck_name = body.name or "Imported Deck"
    deck_format = body.format
    source_url = body.url

    # Get deck text from URL or use provided text
    if body.url:
        try:
            fetched_text, fetched_name, fetched_format = await _fetch_deck_from_url(body.url)
            deck_text = fetched_text
            if not body.name and fetched_name:
                deck_name = fetched_name
            if not body.format and fetched_format:
                deck_format = fetched_format
        except httpx.HTTPStatusError as e:
            errors.append(f"Failed to fetch URL: HTTP {e.response.status_code}")
        except httpx.RequestError as e:
            errors.append(f"Failed to fetch URL: {e!s}")
        except Exception as e:
            logger.exception("Error fetching deck URL")
            errors.append(f"Failed to parse deck: {e!s}")

    if body.text:
        # Prefer provided text over fetched
        deck_text = body.text

    if not deck_text:
        errors.append("No deck list found. Try copying the deck list text directly.")
        return ImportDeckResult(
            name=deck_name,
            format=deck_format,
            commander=None,
            cards=[],
            sideboard=[],
            source_url=source_url,
            errors=errors,
        )

    # Parse the deck text
    main_deck, sideboard, maybeboard, commander, parsed_name, parsed_format = _parse_deck_list_text(
        deck_text
    )

    # Use parsed name/format if not already set from URL or override
    if not body.name and parsed_name:
        deck_name = parsed_name
    if not body.format and parsed_format:
        deck_format = parsed_format

    if not main_deck and not sideboard:
        errors.append("Could not parse any cards from the deck list.")

    return ImportDeckResult(
        name=deck_name,
        format=deck_format,
        commander=commander,
        cards=main_deck,
        maybeboard=maybeboard,
        sideboard=sideboard,
        source_url=source_url,
        errors=errors,
    )
