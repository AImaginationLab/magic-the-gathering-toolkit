"""MTG MCP Server - Magic: The Gathering MCP server."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP
from mtg_core.config import get_settings
from mtg_core.data.database import DatabaseManager

from .context import AppContext
from .routes import register_all_routes

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


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

# Register all routes (tools, resources, prompts)
register_all_routes(mcp)


def main() -> None:
    """Entry point."""
    mcp.run()


if __name__ == "__main__":
    main()
