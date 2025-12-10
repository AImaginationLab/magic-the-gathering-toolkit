"""MTG MCP Server - Magic: The Gathering MCP server."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any

from mcp.server.fastmcp import Context, FastMCP

from .config import get_settings
from .data.database import DatabaseManager, MTGDatabase, ScryfallDatabase
from .data.models import (
    CardDetail,
    CardImageResponse,
    Color,
    Format,
    LegalitiesResponse,
    PriceResponse,
    PriceSearchResponse,
    PrintingsResponse,
    Rarity,
    RulingsResponse,
    SearchCardsInput,
    SearchResult,
    SetDetail,
    SetsResponse,
)
from .tools import cards, images, sets

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """Application context with database connections."""

    db: MTGDatabase
    scryfall: ScryfallDatabase | None


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage database connections."""
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(levelname)s:%(name)s:%(message)s",
    )

    logger.info("Starting MTG MCP Server...")

    db_manager = DatabaseManager(settings)
    await db_manager.start()

    stats = await db_manager.db.get_database_stats()
    logger.info(
        "Database: %d cards, %d sets (v%s)",
        stats["unique_cards"],
        stats["total_sets"],
        stats.get("data_version", "?"),
    )

    if db_manager.scryfall:
        scryfall_stats = await db_manager.scryfall.get_database_stats()
        logger.info("Scryfall: %d cards with images/prices", scryfall_stats["total_cards"])
    else:
        logger.warning("Scryfall database not found - image/price tools unavailable")

    try:
        yield AppContext(db=db_manager.db, scryfall=db_manager.scryfall)
    finally:
        await db_manager.stop()
        logger.info("MTG MCP Server stopped.")


mcp = FastMCP("mtg-mcp", lifespan=lifespan)


def get_app(ctx: Context) -> AppContext:
    """Get application context from request context."""
    return ctx.request_context.lifespan_context  # type: ignore[return-value]


# =============================================================================
# Card Tools
# =============================================================================


@mcp.tool()
async def search_cards(
    ctx: Context,
    name: Annotated[str | None, "Card name (partial match)"] = None,
    colors: Annotated[list[Color] | None, "Filter by colors (W, U, B, R, G)"] = None,
    color_identity: Annotated[list[Color] | None, "Filter by color identity (Commander)"] = None,
    type: Annotated[str | None, "Card type (Creature, Instant, etc.)"] = None,
    subtype: Annotated[str | None, "Subtype (Elf, Dragon, Wizard)"] = None,
    supertype: Annotated[str | None, "Supertype (Legendary, Basic, Snow)"] = None,
    rarity: Annotated[Rarity | None, "Card rarity"] = None,
    set_code: Annotated[str | None, "Set code (DOM, MH2)"] = None,
    cmc: Annotated[float | None, "Exact mana value"] = None,
    cmc_min: Annotated[float | None, "Minimum mana value"] = None,
    cmc_max: Annotated[float | None, "Maximum mana value"] = None,
    power: Annotated[str | None, "Creature power"] = None,
    toughness: Annotated[str | None, "Creature toughness"] = None,
    text: Annotated[str | None, "Search in card text"] = None,
    keywords: Annotated[list[str] | None, "Filter by keywords (Flying, Trample)"] = None,
    format_legal: Annotated[Format | None, "Filter by format legality"] = None,
    page: Annotated[int, "Page number"] = 1,
    page_size: Annotated[int, "Results per page (max 100)"] = 25,
) -> SearchResult:
    """Search for Magic: The Gathering cards with filters."""
    app = get_app(ctx)
    filters = SearchCardsInput(
        name=name,
        colors=colors,
        color_identity=color_identity,
        type=type,
        subtype=subtype,
        supertype=supertype,
        rarity=rarity,
        set_code=set_code,
        cmc=cmc,
        cmc_min=cmc_min,
        cmc_max=cmc_max,
        power=power,
        toughness=toughness,
        text=text,
        keywords=keywords,
        format_legal=format_legal,
        page=page,
        page_size=min(page_size, 100),
    )
    return await cards.search_cards(app.db, app.scryfall, filters)


@mcp.tool()
async def get_card(
    ctx: Context,
    name: Annotated[str | None, "Exact card name"] = None,
    uuid: Annotated[str | None, "Card UUID"] = None,
) -> CardDetail:
    """Get detailed information about a specific card."""
    app = get_app(ctx)
    return await cards.get_card(app.db, app.scryfall, name, uuid)


@mcp.tool()
async def get_card_rulings(
    ctx: Context,
    name: Annotated[str, "Exact card name"],
) -> RulingsResponse:
    """Get official rulings for a card."""
    return await cards.get_card_rulings(get_app(ctx).db, name)


@mcp.tool()
async def get_card_legalities(
    ctx: Context,
    name: Annotated[str, "Exact card name"],
) -> LegalitiesResponse:
    """Get format legalities for a card."""
    return await cards.get_card_legalities(get_app(ctx).db, name)


@mcp.tool()
async def get_random_card(ctx: Context) -> CardDetail:
    """Get a random Magic card."""
    app = get_app(ctx)
    return await cards.get_random_card(app.db, app.scryfall)


# =============================================================================
# Set Tools
# =============================================================================


@mcp.tool()
async def get_sets(
    ctx: Context,
    name: Annotated[str | None, "Filter by set name (partial match)"] = None,
    set_type: Annotated[str | None, "Filter by type (expansion, core, masters)"] = None,
    include_online_only: Annotated[bool, "Include online-only sets"] = True,
) -> SetsResponse:
    """Get Magic: The Gathering sets."""
    return await sets.get_sets(get_app(ctx).db, name, set_type, include_online_only)


@mcp.tool()
async def get_set(
    ctx: Context,
    code: Annotated[str, "Set code (DOM, MH2, LEA)"],
) -> SetDetail:
    """Get detailed information about a specific set."""
    return await sets.get_set(get_app(ctx).db, code)


@mcp.tool()
async def get_database_stats(ctx: Context) -> dict[str, Any]:
    """Get database statistics (card count, set count, version)."""
    return await get_app(ctx).db.get_database_stats()


# =============================================================================
# Image/Price Tools
# =============================================================================


@mcp.tool()
async def get_card_image(
    ctx: Context,
    name: Annotated[str, "Exact card name"],
    set_code: Annotated[str | None, "Set code for specific printing"] = None,
) -> CardImageResponse:
    """Get card images in multiple sizes with pricing."""
    return await images.get_card_image(get_app(ctx).scryfall, name, set_code)


@mcp.tool()
async def get_card_printings(
    ctx: Context,
    name: Annotated[str, "Exact card name"],
) -> PrintingsResponse:
    """Get all printings of a card with images and prices."""
    return await images.get_card_printings(get_app(ctx).scryfall, name)


@mcp.tool()
async def get_card_price(
    ctx: Context,
    name: Annotated[str, "Exact card name"],
    set_code: Annotated[str | None, "Set code for specific printing"] = None,
) -> PriceResponse:
    """Get current prices for a card (USD/EUR, regular/foil)."""
    return await images.get_card_price(get_app(ctx).scryfall, name, set_code)


@mcp.tool()
async def search_by_price(
    ctx: Context,
    min_price: Annotated[float | None, "Minimum price in USD"] = None,
    max_price: Annotated[float | None, "Maximum price in USD"] = None,
    page: Annotated[int, "Page number"] = 1,
    page_size: Annotated[int, "Results per page (max 100)"] = 25,
) -> PriceSearchResponse:
    """Search for cards by price range."""
    return await images.search_by_price(
        get_app(ctx).scryfall,
        min_price,
        max_price,
        page,
        min(page_size, 100),
    )


# =============================================================================
# Resources (browsable data)
# =============================================================================


def _model_to_json(model: BaseModel) -> str:
    """Convert Pydantic model to JSON string."""
    return model.model_dump_json(indent=2)


@mcp.resource("mtg://cards/{name}")
async def card_resource(name: str, ctx: Context) -> str:
    """Get a card as a browsable resource."""
    app = get_app(ctx)
    result = await cards.get_card(app.db, app.scryfall, name=name)
    return _model_to_json(result)


@mcp.resource("mtg://sets/{code}")
async def set_resource(code: str, ctx: Context) -> str:
    """Get a set as a browsable resource."""
    result = await sets.get_set(get_app(ctx).db, code)
    return _model_to_json(result)


@mcp.resource("mtg://rulings/{name}")
async def rulings_resource(name: str, ctx: Context) -> str:
    """Get card rulings as a browsable resource."""
    result = await cards.get_card_rulings(get_app(ctx).db, name)
    return _model_to_json(result)


@mcp.resource("mtg://stats")
async def stats_resource(ctx: Context) -> str:
    """Database statistics resource."""
    stats = await get_app(ctx).db.get_database_stats()
    return json.dumps(stats, indent=2)


# =============================================================================
# Prompts (pre-built templates)
# =============================================================================


@mcp.prompt()
def build_commander_deck(
    commander: Annotated[str, "Commander card name"],
    budget: Annotated[str | None, "Budget constraint (e.g., '$50', '$100')"] = None,
) -> str:
    """Help build a Commander/EDH deck around a specific commander."""
    prompt = f"""Help me build a Commander deck with {commander} as the commander.

Please:
1. First, look up {commander} to understand its colors and abilities
2. Suggest a strategy/theme that synergizes with the commander
3. Recommend key cards in these categories:
   - Ramp (10-12 cards)
   - Card draw (10 cards)
   - Removal (8-10 cards)
   - Board wipes (3-4 cards)
   - Win conditions (3-5 cards)
   - Synergy pieces (20-25 cards)
   - Lands (35-38 cards)
"""
    if budget:
        prompt += f"\nBudget constraint: {budget}"
    return prompt


@mcp.prompt()
def analyze_card(
    card_name: Annotated[str, "Card name to analyze"],
) -> str:
    """Get comprehensive analysis of a Magic card."""
    return f"""Analyze the Magic: The Gathering card "{card_name}".

Please provide:
1. Card details (look up the card first)
2. Strengths and weaknesses
3. Best formats for this card
4. Synergies with other cards
5. Similar cards to consider
6. Current price and value assessment
"""


@mcp.prompt()
def find_cards_for_strategy(
    strategy: Annotated[str, "Strategy or theme (e.g., 'graveyard recursion', 'token swarm')"],
    colors: Annotated[str | None, "Color restriction (e.g., 'Golgari', 'WUB')"] = None,
    format_name: Annotated[str | None, "Format (commander, modern, standard)"] = None,
) -> str:
    """Find cards that support a specific strategy."""
    prompt = f"""Find Magic cards that support a "{strategy}" strategy.

Search for cards that:
1. Directly enable the strategy
2. Provide synergy with the theme
3. Offer protection or resilience
"""
    if colors:
        prompt += f"\nColor restriction: {colors}"
    if format_name:
        prompt += f"\nFormat: {format_name}"
    return prompt


@mcp.prompt()
def compare_cards(
    card1: Annotated[str, "First card name"],
    card2: Annotated[str, "Second card name"],
) -> str:
    """Compare two Magic cards."""
    return f"""Compare these two Magic cards: "{card1}" vs "{card2}"

Please:
1. Look up both cards
2. Compare mana cost and efficiency
3. Compare abilities and effects
4. Discuss which is better in different situations
5. Consider format legality
6. Compare prices
"""


def main() -> None:
    """Entry point."""
    mcp.run()


if __name__ == "__main__":
    main()
