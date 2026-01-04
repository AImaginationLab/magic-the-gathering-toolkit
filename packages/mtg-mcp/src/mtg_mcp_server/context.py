"""Shared context utilities for MCP routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import Context

if TYPE_CHECKING:
    from mtg_core.data.database import UnifiedDatabase, UserDatabase


@dataclass
class AppContext:
    """Application context with database connection."""

    db: UnifiedDatabase
    user: UserDatabase | None = None


# Type alias for Context with our AppContext
ToolContext = Context[Any, AppContext, Any]


def get_app(ctx: ToolContext) -> AppContext:
    """Get application context from request context."""
    if ctx.request_context is None:
        raise RuntimeError("Request context is not available")
    lifespan_ctx = ctx.request_context.lifespan_context
    if not isinstance(lifespan_ctx, AppContext):
        raise TypeError(
            f"Expected AppContext but got {type(lifespan_ctx).__name__}. "
            "Server lifespan may be misconfigured."
        )
    return lifespan_ctx
