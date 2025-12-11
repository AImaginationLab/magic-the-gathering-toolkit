"""Set tool routes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from mcp.server.fastmcp import Context, FastMCP

from ..data.models import SetDetail, SetsResponse
from ..tools import sets

if TYPE_CHECKING:
    from ..server import AppContext

# Type alias for Context with our AppContext
ToolContext = Context[Any, "AppContext", Any]


def _get_app(ctx: ToolContext) -> AppContext:
    """Get application context from request context."""
    assert ctx.request_context is not None
    return ctx.request_context.lifespan_context


def register(mcp: FastMCP) -> None:
    """Register set tools with the MCP server."""

    @mcp.tool()
    async def get_sets(
        ctx: ToolContext,
        name: Annotated[str | None, "Filter by set name (partial match)"] = None,
        set_type: Annotated[
            str | None, "Filter by type (expansion, core, masters)"
        ] = None,
        include_online_only: Annotated[bool, "Include online-only sets"] = True,
    ) -> SetsResponse:
        """Get Magic: The Gathering sets."""
        return await sets.get_sets(_get_app(ctx).db, name, set_type, include_online_only)

    @mcp.tool()
    async def get_set(
        ctx: ToolContext,
        code: Annotated[str, "Set code (DOM, MH2, LEA)"],
    ) -> SetDetail:
        """Get detailed information about a specific set."""
        return await sets.get_set(_get_app(ctx).db, code)

    @mcp.tool()
    async def get_database_stats(ctx: ToolContext) -> dict[str, Any]:
        """Get database statistics (card count, set count, version)."""
        return await _get_app(ctx).db.get_database_stats()
