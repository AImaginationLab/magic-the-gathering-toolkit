"""Route modules for MCP tool registration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register_all_routes(mcp: FastMCP) -> None:
    """Register all tool routes with the MCP server."""
    # Import here to avoid circular imports
    from . import cards, deck, images, prompts, resources, sets

    # Tools
    cards.register(mcp)
    sets.register(mcp)
    images.register(mcp)
    deck.register(mcp)

    # Resources and prompts
    resources.register(mcp)
    prompts.register(mcp)
