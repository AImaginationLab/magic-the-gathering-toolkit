"""Synergy and strategy tool routes."""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP

from mtg_mcp.context import ToolContext, get_app
from mtg_mcp.data.models import (
    DetectCombosResult,
    FindSynergiesResult,
    Format,
    SuggestCardsResult,
)
from mtg_mcp.tools import synergy


def register(mcp: FastMCP) -> None:
    """Register synergy and strategy tools with the MCP server."""

    @mcp.tool()
    async def find_synergies(
        ctx: ToolContext,
        card_name: Annotated[str, "Card name to find synergies for"],
        max_results: Annotated[int, "Maximum number of results (1-50)"] = 20,
        format_legal: Annotated[Format | None, "Filter by format legality"] = None,
    ) -> FindSynergiesResult:
        """Find cards that synergize with a given card.

        Analyzes the card's keywords, types, subtypes, and abilities to find
        synergistic cards. Results are sorted by synergy score.

        Examples:
        - "Rhystic Study" → finds draw triggers, tax effects
        - "Craterhoof Behemoth" → finds creature token producers, haste enablers
        - "Niv-Mizzet, Parun" → finds draw effects, damage doublers
        """
        app = get_app(ctx)
        return await synergy.find_synergies(
            app.db,
            card_name=card_name,
            max_results=max_results,
            format_legal=format_legal,
        )

    @mcp.tool()
    async def detect_combos(
        ctx: ToolContext,
        card_name: Annotated[str | None, "Find combos involving this card"] = None,
        cards: Annotated[
            list[dict[str, Any]] | None,
            "Deck cards as [{name: str, quantity: int}]",
        ] = None,
    ) -> DetectCombosResult:
        """Detect known combos in a deck or find combos for a specific card.

        Can be used two ways:
        1. Provide card_name to find all known combos involving that card
        2. Provide cards (deck list) to find complete and potential combos

        Potential combos are those where the deck has some pieces but is
        missing 1-2 cards to complete the combo.

        Examples:
        - card_name="Thassa's Oracle" → Thoracle + Demonic Consultation, etc.
        - cards=[{name: "Splinter Twin", quantity: 1}] → suggests Deceiver Exarch
        """
        app = get_app(ctx)

        # Extract card names from deck cards if provided
        deck_card_names: list[str] | None = None
        if cards:
            deck_card_names = [c["name"] for c in cards if "name" in c]

        return await synergy.detect_combos(
            app.db,
            card_name=card_name,
            deck_cards=deck_card_names,
        )

    @mcp.tool()
    async def suggest_cards(
        ctx: ToolContext,
        cards: Annotated[
            list[dict[str, Any]],
            "Current deck cards as [{name: str, quantity: int}]",
        ],
        format_legal: Annotated[Format | None, "Format for suggestions"] = None,
        budget_max: Annotated[float | None, "Maximum price per card (USD)"] = None,
        max_results: Annotated[int, "Maximum number of suggestions (1-25)"] = 10,
    ) -> SuggestCardsResult:
        """Suggest cards to add to a deck based on detected themes and synergies.

        Analyzes the deck to detect themes (tokens, aristocrats, reanimator, etc.)
        and suggests cards that fit those themes. Can optionally filter by budget.

        Returns:
        - suggestions: List of suggested cards with reasons
        - detected_themes: Themes found in the deck
        - deck_colors: Color identity of the deck

        Examples:
        - Deck with sacrifice effects → suggests Blood Artist, Viscera Seer
        - Deck with ETB effects → suggests Panharmonicon, blink effects
        """
        app = get_app(ctx)

        # Extract card names from deck cards
        deck_card_names = [c["name"] for c in cards if "name" in c]

        return await synergy.suggest_cards(
            app.db,
            app.scryfall,
            deck_cards=deck_card_names,
            format_legal=format_legal,
            budget_max=budget_max,
            max_results=max_results,
        )
