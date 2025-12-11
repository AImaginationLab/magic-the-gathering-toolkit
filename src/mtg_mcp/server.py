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
from .routes import register_all_routes
from .tools import cards, sets

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


# Create MCP server instance
mcp = FastMCP("mtg-mcp", lifespan=lifespan)

# Register all tool routes
register_all_routes(mcp)


# =============================================================================
# Helper for context access (used by routes)
# =============================================================================

# Type alias for Context with our AppContext
ToolContext = Context[Any, AppContext, Any]


def get_app(ctx: ToolContext) -> AppContext:
    """Get application context from request context."""
    assert ctx.request_context is not None
    return ctx.request_context.lifespan_context


# =============================================================================
# Resources (browsable data)
# =============================================================================


def _model_to_json(model: BaseModel) -> str:
    """Convert Pydantic model to JSON string."""
    return model.model_dump_json(indent=2)


@mcp.resource("mtg://cards/{name}")
async def card_resource(name: str, ctx: ToolContext) -> str:
    """Get a card as a browsable resource."""
    app = get_app(ctx)
    result = await cards.get_card(app.db, app.scryfall, name=name)
    return _model_to_json(result)


@mcp.resource("mtg://sets/{code}")
async def set_resource(code: str, ctx: ToolContext) -> str:
    """Get a set as a browsable resource."""
    result = await sets.get_set(get_app(ctx).db, code)
    return _model_to_json(result)


@mcp.resource("mtg://rulings/{name}")
async def rulings_resource(name: str, ctx: ToolContext) -> str:
    """Get card rulings as a browsable resource."""
    result = await cards.get_card_rulings(get_app(ctx).db, name)
    return _model_to_json(result)


@mcp.resource("mtg://stats")
async def stats_resource(ctx: ToolContext) -> str:
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
