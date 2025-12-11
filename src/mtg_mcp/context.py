"""Shared context utilities for MCP routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import Context

if TYPE_CHECKING:
    from .data.database import MTGDatabase, ScryfallDatabase


@dataclass
class AppContext:
    """Application context with database connections."""

    db: MTGDatabase
    scryfall: ScryfallDatabase | None


# Type alias for Context with our AppContext
ToolContext = Context[Any, AppContext, Any]


def get_app(ctx: ToolContext) -> AppContext:
    """Get application context from request context."""
    if ctx.request_context is None:
        raise RuntimeError("Request context is not available")
    return ctx.request_context.lifespan_context
