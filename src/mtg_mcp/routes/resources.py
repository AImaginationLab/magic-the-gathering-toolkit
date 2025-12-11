"""MCP Resources - browsable data endpoints."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from mtg_mcp.context import ToolContext, get_app
from mtg_mcp.tools import cards, sets

if TYPE_CHECKING:
    from pydantic import BaseModel


def _model_to_json(model: BaseModel) -> str:
    """Convert Pydantic model to JSON string."""
    return model.model_dump_json(indent=2)


def register(mcp: FastMCP) -> None:
    """Register MCP resources with the server."""

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
