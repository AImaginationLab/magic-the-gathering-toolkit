"""Deck analysis tool routes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from mcp.server.fastmcp import Context, FastMCP

from ..data.models import (
    AnalyzeDeckInput,
    ColorAnalysisResult,
    CompositionResult,
    DeckCardInput,
    DeckValidationResult,
    Format,
    ManaCurveResult,
    PriceAnalysisResult,
    ValidateDeckInput,
)
from ..tools import deck

if TYPE_CHECKING:
    from ..server import AppContext

# Type alias for Context with our AppContext
ToolContext = Context[Any, "AppContext", Any]


def _get_app(ctx: ToolContext) -> AppContext:
    """Get application context from request context."""
    assert ctx.request_context is not None
    return ctx.request_context.lifespan_context


def _parse_deck_cards(cards_data: list[dict[str, Any]]) -> list[DeckCardInput]:
    """Parse raw card data into DeckCardInput list."""
    return [
        DeckCardInput(
            name=c.get("name", ""),
            quantity=c.get("quantity", 1),
            sideboard=c.get("sideboard", False),
        )
        for c in cards_data
    ]


def register(mcp: FastMCP) -> None:
    """Register deck analysis tools with the MCP server."""

    @mcp.tool()
    async def validate_deck(
        ctx: ToolContext,
        cards: Annotated[list[dict[str, Any]], "Deck cards [{name, quantity, sideboard?}]"],
        format: Annotated[Format, "Format to validate against"],
        commander: Annotated[
            str | None, "Commander card name (for Commander format)"
        ] = None,
        check_legality: Annotated[bool, "Check card legality in format"] = True,
        check_deck_size: Annotated[bool, "Check minimum deck size"] = True,
        check_copy_limit: Annotated[bool, "Check 4-copy limit (or singleton)"] = True,
        check_singleton: Annotated[bool, "Check singleton rule (Commander)"] = True,
        check_color_identity: Annotated[
            bool, "Check color identity (Commander)"
        ] = True,
    ) -> DeckValidationResult:
        """Validate a deck against format rules."""
        app = _get_app(ctx)
        input_data = ValidateDeckInput(
            cards=_parse_deck_cards(cards),
            format=format,
            commander=commander,
            check_legality=check_legality,
            check_deck_size=check_deck_size,
            check_copy_limit=check_copy_limit,
            check_singleton=check_singleton,
            check_color_identity=check_color_identity,
        )
        return await deck.validate_deck(app.db, input_data)

    @mcp.tool()
    async def analyze_mana_curve(
        ctx: ToolContext,
        cards: Annotated[list[dict[str, Any]], "Deck cards [{name, quantity, sideboard?}]"],
        format: Annotated[Format | None, "Format (optional)"] = None,
        commander: Annotated[str | None, "Commander card name"] = None,
    ) -> ManaCurveResult:
        """Analyze the mana curve of a deck."""
        app = _get_app(ctx)
        input_data = AnalyzeDeckInput(
            cards=_parse_deck_cards(cards),
            format=format,
            commander=commander,
        )
        return await deck.analyze_mana_curve(app.db, input_data)

    @mcp.tool()
    async def analyze_colors(
        ctx: ToolContext,
        cards: Annotated[list[dict[str, Any]], "Deck cards [{name, quantity, sideboard?}]"],
        format: Annotated[Format | None, "Format (optional)"] = None,
        commander: Annotated[str | None, "Commander card name"] = None,
    ) -> ColorAnalysisResult:
        """Analyze the color distribution of a deck."""
        app = _get_app(ctx)
        input_data = AnalyzeDeckInput(
            cards=_parse_deck_cards(cards),
            format=format,
            commander=commander,
        )
        return await deck.analyze_colors(app.db, input_data)

    @mcp.tool()
    async def analyze_deck_composition(
        ctx: ToolContext,
        cards: Annotated[list[dict[str, Any]], "Deck cards [{name, quantity, sideboard?}]"],
        format: Annotated[Format | None, "Format (optional)"] = None,
        commander: Annotated[str | None, "Commander card name"] = None,
    ) -> CompositionResult:
        """Analyze the card type composition of a deck."""
        app = _get_app(ctx)
        input_data = AnalyzeDeckInput(
            cards=_parse_deck_cards(cards),
            format=format,
            commander=commander,
        )
        return await deck.analyze_deck_composition(app.db, input_data)

    @mcp.tool()
    async def analyze_deck_price(
        ctx: ToolContext,
        cards: Annotated[list[dict[str, Any]], "Deck cards [{name, quantity, sideboard?}]"],
        format: Annotated[Format | None, "Format (optional)"] = None,
        commander: Annotated[str | None, "Commander card name"] = None,
    ) -> PriceAnalysisResult:
        """Analyze the total price of a deck."""
        app = _get_app(ctx)
        input_data = AnalyzeDeckInput(
            cards=_parse_deck_cards(cards),
            format=format,
            commander=commander,
        )
        return await deck.analyze_deck_price(app.db, app.scryfall, input_data)
