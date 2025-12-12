"""Synergy and strategy CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from mtg_mcp.cli.commands.deck import parse_deck_file
from mtg_mcp.cli.context import DatabaseContext, output_json, run_async
from mtg_mcp.cli.synergy_display import (
    display_combos,
    display_suggestions,
    display_synergies,
    display_themes,
)
from mtg_mcp.tools import synergy

console = Console()

synergy_app = typer.Typer(help="Synergy and strategy commands")


# =============================================================================
# CLI Commands
# =============================================================================


@synergy_app.command("find")
def find_synergies_cmd(
    card_name: Annotated[str, typer.Argument(help="Card name to find synergies for")],
    max_results: Annotated[int, typer.Option("--max", "-m", help="Max results")] = 20,
    format_legal: Annotated[
        str | None, typer.Option("-f", "--format", help="Filter by format")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Find cards that synergize with a given card.

    Analyzes keywords, types, subtypes, and abilities to find synergistic cards.
    Results are sorted by synergy score.

    Examples:
        mtg synergy find "Rhystic Study"
        mtg synergy find "Craterhoof Behemoth" -f commander
    """

    async def _run() -> None:
        async with DatabaseContext() as ctx:
            db = await ctx.get_db()

            result = await synergy.find_synergies(
                db,
                card_name=card_name,
                max_results=max_results,
                format_legal=format_legal,
            )

            if as_json:
                output_json(result)
            else:
                display_synergies(result)

    run_async(_run())


@synergy_app.command("combos")
def detect_combos_cmd(
    card_name: Annotated[
        str | None, typer.Option("-c", "--card", help="Find combos for this card")
    ] = None,
    deck_file: Annotated[
        Path | None, typer.Option("-d", "--deck", help="Deck file to analyze")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Detect known combos for a card or in a deck.

    Provide either a card name (-c) or a deck file (-d).

    For deck analysis, shows:
    - Complete combos present in the deck
    - Potential combos (missing 1-2 pieces)

    Examples:
        mtg synergy combos -c "Thassa's Oracle"
        mtg synergy combos -d my_deck.txt
    """
    if not card_name and not deck_file:
        console.print("[red]Error: Provide either --card or --deck[/]")
        raise typer.Exit(1)

    deck_cards: list[str] | None = None
    if deck_file:
        parsed = parse_deck_file(deck_file)
        deck_cards = [c.name for c in parsed]

    async def _run() -> None:
        async with DatabaseContext() as ctx:
            db = await ctx.get_db()

            result = await synergy.detect_combos(
                db,
                card_name=card_name,
                deck_cards=deck_cards,
            )

            if as_json:
                output_json(result)
            else:
                title = f"Combos involving {card_name}" if card_name else "Deck Combo Analysis"
                display_combos(result, title=title)

    run_async(_run())


@synergy_app.command("suggest")
def suggest_cards_cmd(
    deck_file: Annotated[Path, typer.Argument(help="Deck file to analyze")],
    max_results: Annotated[int, typer.Option("--max", "-m", help="Max suggestions")] = 10,
    format_legal: Annotated[
        str | None, typer.Option("-f", "--format", help="Filter by format")
    ] = None,
    budget_max: Annotated[
        float | None, typer.Option("-b", "--budget", help="Max price per card (USD)")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Suggest cards to add to a deck based on detected themes.

    Analyzes the deck to detect themes (tokens, aristocrats, reanimator, etc.)
    and suggests cards that fit those themes.

    Examples:
        mtg synergy suggest my_deck.txt
        mtg synergy suggest my_deck.txt -f commander -b 5.00
    """
    deck_cards_input = parse_deck_file(deck_file)
    deck_card_names = [c.name for c in deck_cards_input]

    async def _run() -> None:
        async with DatabaseContext() as ctx:
            db = await ctx.get_db()
            scryfall = await ctx.get_scryfall()

            result = await synergy.suggest_cards(
                db,
                scryfall,
                deck_cards=deck_card_names,
                format_legal=format_legal,
                budget_max=budget_max,
                max_results=max_results,
            )

            if as_json:
                output_json(result)
            else:
                console.print(f"\n[bold]Suggestions for {deck_file.name}:[/]")
                display_suggestions(result, compact=False)

    run_async(_run())


@synergy_app.command("themes")
def detect_themes_cmd(
    deck_file: Annotated[Path, typer.Argument(help="Deck file to analyze")],
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Detect themes and color identity in a deck.

    Quick analysis to show what themes and colors are detected
    without generating suggestions.

    Examples:
        mtg synergy themes my_deck.txt
    """
    deck_cards_input = parse_deck_file(deck_file)
    deck_card_names = [c.name for c in deck_cards_input]

    async def _run() -> None:
        async with DatabaseContext() as ctx:
            db = await ctx.get_db()

            # Use suggest_cards with 0 results to just get theme detection
            result = await synergy.suggest_cards(
                db,
                scryfall=None,
                deck_cards=deck_card_names,
                max_results=0,
            )

            if as_json:
                output_json(
                    {
                        "deck_colors": result.deck_colors,
                        "detected_themes": result.detected_themes,
                    }
                )
            else:
                console.print(f"\n[bold]Theme Analysis for {deck_file.name}:[/]\n")
                display_themes(result.deck_colors, result.detected_themes)

    run_async(_run())
