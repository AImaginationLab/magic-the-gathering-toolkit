"""MCP Prompts - pre-built prompt templates."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register MCP prompts with the server."""

    @mcp.prompt()
    def build_commander_deck(
        commander: Annotated[str, "Commander card name"],
        budget: Annotated[str | None, "Budget constraint (e.g., '$50', '$100')"] = None,
    ) -> str:
        """Help build a Commander/EDH deck around a specific commander."""
        prompt = f"""Help me build a Commander deck with {commander} as the commander.

Please:
1. First, look up {commander} to understand its colors and abilities
2. Suggest a strategy/theme that synergizes with the commander
3. Recommend key cards in these categories:
   - Ramp (10-12 cards)
   - Card draw (10 cards)
   - Removal (8-10 cards)
   - Board wipes (3-4 cards)
   - Win conditions (3-5 cards)
   - Synergy pieces (20-25 cards)
   - Lands (35-38 cards)
"""
        if budget:
            prompt += f"\nBudget constraint: {budget}"
        return prompt

    @mcp.prompt()
    def analyze_card(
        card_name: Annotated[str, "Card name to analyze"],
    ) -> str:
        """Get comprehensive analysis of a Magic card."""
        return f"""Analyze the Magic: The Gathering card "{card_name}".

Please provide:
1. Card details (look up the card first)
2. Strengths and weaknesses
3. Best formats for this card
4. Synergies with other cards
5. Similar cards to consider
6. Current price and value assessment
"""

    @mcp.prompt()
    def find_cards_for_strategy(
        strategy: Annotated[str, "Strategy or theme (e.g., 'graveyard recursion', 'token swarm')"],
        colors: Annotated[str | None, "Color restriction (e.g., 'Golgari', 'WUB')"] = None,
        format_name: Annotated[str | None, "Format (commander, modern, standard)"] = None,
    ) -> str:
        """Find cards that support a specific strategy."""
        prompt = f"""Find Magic cards that support a "{strategy}" strategy.

Search for cards that:
1. Directly enable the strategy
2. Provide synergy with the theme
3. Offer protection or resilience
"""
        if colors:
            prompt += f"\nColor restriction: {colors}"
        if format_name:
            prompt += f"\nFormat: {format_name}"
        return prompt

    @mcp.prompt()
    def compare_cards(
        card1: Annotated[str, "First card name"],
        card2: Annotated[str, "Second card name"],
    ) -> str:
        """Compare two Magic cards."""
        return f"""Compare these two Magic cards: "{card1}" vs "{card2}"

Please:
1. Look up both cards
2. Compare mana cost and efficiency
3. Compare abilities and effects
4. Discuss which is better in different situations
5. Consider format legality
6. Compare prices
"""
