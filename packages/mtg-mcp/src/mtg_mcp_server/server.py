"""MTG MCP Server - Magic: The Gathering MCP server."""

from __future__ import annotations

import argparse
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

DEFAULT_SSE_PORT = 3179  # MTG on phone keypad


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

    try:
        yield AppContext(db=db_manager.db, user=db_manager.user)
    finally:
        await db_manager.stop()
        logger.info("MTG MCP Server stopped.")


def create_server(port: int = DEFAULT_SSE_PORT) -> FastMCP:
    """Create and configure MCP server instance."""
    server = FastMCP("mtg-mcp", lifespan=lifespan, port=port)
    register_all_routes(server)
    return server


# Default instance for stdio mode (used by Claude Desktop)
mcp = create_server()


def main() -> None:
    """Entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(description="MTG MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport mode: stdio (default) or sse (HTTP)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_SSE_PORT,
        help=f"Port for SSE transport (default: {DEFAULT_SSE_PORT})",
    )
    args = parser.parse_args()

    if args.transport == "sse":
        # Create new instance with configured port
        server = create_server(port=args.port)
        print(f"Starting MCP server on http://127.0.0.1:{args.port}/sse")
        server.run(transport="sse")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
