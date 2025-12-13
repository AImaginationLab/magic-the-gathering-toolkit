"""Card tool routes."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP

from mtg_core.data.models import (
    CardDetail,
    Color,
    Format,
    LegalitiesResponse,
    Rarity,
    RulingsResponse,
    SearchCardsInput,
    SearchResult,
    SortField,
    SortOrder,
)
from mtg_core.tools import cards
from mtg_mcp_server.context import ToolContext, get_app


def register(mcp: FastMCP) -> None:
    """Register card tools with the MCP server."""

    @mcp.tool()
    async def search_cards(
        ctx: ToolContext,
        name: Annotated[str | None, "Card name (partial match)"] = None,
        colors: Annotated[list[Color] | None, "Filter by colors (W, U, B, R, G)"] = None,
        color_identity: Annotated[
            list[Color] | None, "Filter by color identity (Commander)"
        ] = None,
        type: Annotated[str | None, "Card type (Creature, Instant, etc.)"] = None,
        subtype: Annotated[str | None, "Subtype (Elf, Dragon, Wizard)"] = None,
        supertype: Annotated[str | None, "Supertype (Legendary, Basic, Snow)"] = None,
        rarity: Annotated[Rarity | None, "Card rarity"] = None,
        set_code: Annotated[str | None, "Set code (DOM, MH2)"] = None,
        cmc: Annotated[float | None, "Exact mana value"] = None,
        cmc_min: Annotated[float | None, "Minimum mana value"] = None,
        cmc_max: Annotated[float | None, "Maximum mana value"] = None,
        power: Annotated[str | None, "Creature power"] = None,
        toughness: Annotated[str | None, "Creature toughness"] = None,
        text: Annotated[str | None, "Search in card text"] = None,
        keywords: Annotated[list[str] | None, "Filter by keywords (Flying, Trample)"] = None,
        format_legal: Annotated[Format | None, "Filter by format legality"] = None,
        sort_by: Annotated[
            SortField | None, "Sort by field (name, cmc, color, rarity, type)"
        ] = None,
        sort_order: Annotated[SortOrder, "Sort order (asc, desc)"] = "asc",
        page: Annotated[int, "Page number"] = 1,
        page_size: Annotated[int, "Results per page (max 100)"] = 25,
    ) -> SearchResult:
        """Search for Magic: The Gathering cards with filters."""
        app = get_app(ctx)
        filters = SearchCardsInput(
            name=name,
            colors=colors,
            color_identity=color_identity,
            type=type,
            subtype=subtype,
            supertype=supertype,
            rarity=rarity,
            set_code=set_code,
            cmc=cmc,
            cmc_min=cmc_min,
            cmc_max=cmc_max,
            power=power,
            toughness=toughness,
            text=text,
            keywords=keywords,
            format_legal=format_legal,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=min(page_size, 100),
        )
        return await cards.search_cards(app.db, app.scryfall, filters)

    @mcp.tool()
    async def get_card(
        ctx: ToolContext,
        name: Annotated[str | None, "Exact card name"] = None,
        uuid: Annotated[str | None, "Card UUID"] = None,
    ) -> CardDetail:
        """Get detailed information about a specific card."""
        app = get_app(ctx)
        return await cards.get_card(app.db, app.scryfall, name, uuid)

    @mcp.tool()
    async def get_card_rulings(
        ctx: ToolContext,
        name: Annotated[str, "Exact card name"],
    ) -> RulingsResponse:
        """Get official rulings for a card."""
        return await cards.get_card_rulings(get_app(ctx).db, name)

    @mcp.tool()
    async def get_card_legalities(
        ctx: ToolContext,
        name: Annotated[str, "Exact card name"],
    ) -> LegalitiesResponse:
        """Get format legalities for a card."""
        return await cards.get_card_legalities(get_app(ctx).db, name)

    @mcp.tool()
    async def get_random_card(ctx: ToolContext) -> CardDetail:
        """Get a random Magic card."""
        app = get_app(ctx)
        return await cards.get_random_card(app.db, app.scryfall)
