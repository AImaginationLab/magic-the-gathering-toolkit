"""Image and price tool routes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from mcp.server.fastmcp import Context, FastMCP

from ..data.models import (
    CardImageResponse,
    PriceResponse,
    PriceSearchResponse,
    PrintingsResponse,
)
from ..tools import images

if TYPE_CHECKING:
    from ..server import AppContext

# Type alias for Context with our AppContext
ToolContext = Context[Any, "AppContext", Any]


def _get_app(ctx: ToolContext) -> AppContext:
    """Get application context from request context."""
    assert ctx.request_context is not None
    return ctx.request_context.lifespan_context


def register(mcp: FastMCP) -> None:
    """Register image and price tools with the MCP server."""

    @mcp.tool()
    async def get_card_image(
        ctx: ToolContext,
        name: Annotated[str, "Exact card name"],
        set_code: Annotated[str | None, "Set code for specific printing"] = None,
    ) -> CardImageResponse:
        """Get card images in multiple sizes with pricing."""
        return await images.get_card_image(_get_app(ctx).scryfall, name, set_code)

    @mcp.tool()
    async def get_card_printings(
        ctx: ToolContext,
        name: Annotated[str, "Exact card name"],
    ) -> PrintingsResponse:
        """Get all printings of a card with images and prices."""
        return await images.get_card_printings(_get_app(ctx).scryfall, name)

    @mcp.tool()
    async def get_card_price(
        ctx: ToolContext,
        name: Annotated[str, "Exact card name"],
        set_code: Annotated[str | None, "Set code for specific printing"] = None,
    ) -> PriceResponse:
        """Get current prices for a card (USD/EUR, regular/foil)."""
        return await images.get_card_price(_get_app(ctx).scryfall, name, set_code)

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
            _get_app(ctx).scryfall,
            min_price,
            max_price,
            page,
            min(page_size, 100),
        )
