"""Image and price tool routes."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP

from mtg_core.data.models import (
    CardImageResponse,
    PriceResponse,
    PriceSearchResponse,
    PrintingsResponse,
)
from mtg_core.tools import images
from mtg_mcp_server.context import ToolContext, get_app


def register(mcp: FastMCP) -> None:
    """Register image and price tools with the MCP server."""

    @mcp.tool()
    async def get_card_image(
        ctx: ToolContext,
        name: Annotated[str, "Exact card name"],
        set_code: Annotated[str | None, "Set code for specific printing"] = None,
    ) -> CardImageResponse:
        """Get card images in multiple sizes with pricing."""
        return await images.get_card_image(get_app(ctx).db, name, set_code)

    @mcp.tool()
    async def get_card_printings(
        ctx: ToolContext,
        name: Annotated[str, "Exact card name"],
    ) -> PrintingsResponse:
        """Get all printings of a card with images and prices."""
        app = get_app(ctx)
        return await images.get_card_printings(app.db, name)

    @mcp.tool()
    async def get_card_price(
        ctx: ToolContext,
        name: Annotated[str, "Exact card name"],
        set_code: Annotated[str | None, "Set code for specific printing"] = None,
    ) -> PriceResponse:
        """Get current prices for a card (USD/EUR, regular/foil)."""
        return await images.get_card_price(get_app(ctx).db, name, set_code)

    @mcp.tool()
    async def search_by_price(
        ctx: ToolContext,
        min_price: Annotated[float | None, "Minimum price in USD"] = None,
        max_price: Annotated[float | None, "Maximum price in USD"] = None,
        page: Annotated[int, "Page number"] = 1,
        page_size: Annotated[int, "Results per page (max 100)"] = 25,
    ) -> PriceSearchResponse:
        """Search for cards by price range."""
        return await images.search_by_price(
            get_app(ctx).db,
            min_price,
            max_price,
            page,
            min(page_size, 100),
        )
