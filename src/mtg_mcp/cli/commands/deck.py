"""Deck analysis CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from mtg_mcp.cli.context import DatabaseContext, output_json, run_async
from mtg_mcp.data.models.inputs import AnalyzeDeckInput, DeckCardInput, ValidateDeckInput
from mtg_mcp.tools import deck

console = Console()

deck_app = typer.Typer(help="Deck analysis commands")


def parse_deck_file(deck_file: Path) -> list[DeckCardInput]:
    """Parse a deck file into card list.

    Supports simple format:
        4 Lightning Bolt
        4 Mountain
        SB: 2 Pyroblast
    """
    deck_cards: list[DeckCardInput] = []

    with deck_file.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            sideboard = False
            if line.upper().startswith("SB:"):
                sideboard = True
                line = line[3:].strip()

            parts = line.split(None, 1)
            if len(parts) == 2:
                try:
                    qty = int(parts[0])
                    name = parts[1]
                except ValueError:
                    qty = 1
                    name = line
            else:
                qty = 1
                name = line

            deck_cards.append(DeckCardInput(name=name, quantity=qty, sideboard=sideboard))

    return deck_cards


@deck_app.command("validate")
def validate_deck_cmd(
    deck_file: Annotated[Path, typer.Argument(help="Deck file path")],
    format_name: Annotated[
        str,
        typer.Option("-f", "--format", help="Format to validate against"),
    ],
    commander: Annotated[str | None, typer.Option(help="Commander name")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Validate a deck against format rules."""
    ctx = DatabaseContext()
    deck_cards = parse_deck_file(deck_file)

    async def _run() -> None:
        db = await ctx.get_db()

        input_data = ValidateDeckInput(
            cards=deck_cards,
            format=format_name,  # type: ignore[arg-type]
            commander=commander,
        )
        result = await deck.validate_deck(db, input_data)

        if as_json:
            output_json(result)
        else:
            status = "[green]VALID[/]" if result.is_valid else "[red]INVALID[/]"
            console.print(f"\n[bold]Deck Validation:[/] {status}")
            console.print(f"Format: {result.format}")
            console.print(
                f"Cards: {result.total_cards} mainboard, {result.sideboard_count} sideboard"
            )

            if result.issues:
                console.print("\n[red]Issues:[/]")
                for issue in result.issues:
                    console.print(f"  • {issue.card_name}: {issue.issue}")
                    if issue.details:
                        console.print(f"    [dim]{issue.details}[/dim]")

            if result.warnings:
                console.print("\n[yellow]Warnings:[/]")
                for warning in result.warnings:
                    console.print(f"  • {warning}")

        await ctx.close()

    run_async(_run())


@deck_app.command("curve")
def analyze_curve_cmd(
    deck_file: Annotated[Path, typer.Argument(help="Deck file path")],
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Analyze mana curve of a deck."""
    ctx = DatabaseContext()
    deck_cards = parse_deck_file(deck_file)

    async def _run() -> None:
        db = await ctx.get_db()
        input_data = AnalyzeDeckInput(cards=deck_cards)
        result = await deck.analyze_mana_curve(db, input_data)

        if as_json:
            output_json(result)
        else:
            console.print("\n[bold]Mana Curve Analysis[/]\n")
            console.print(f"Average CMC: [cyan]{result.average_cmc:.2f}[/]")
            console.print(f"Lands: {result.land_count}, Non-lands: {result.nonland_count}")

            if result.curve:
                console.print("\n[bold]Curve:[/]")
                max_count = max(result.curve.values())
                for cmc in sorted(result.curve.keys()):
                    count = result.curve[cmc]
                    bar_len = int(count / max_count * 30) if max_count > 0 else 0
                    bar = "█" * bar_len
                    console.print(f"  {cmc}: [cyan]{bar}[/] {count}")

        await ctx.close()

    run_async(_run())


@deck_app.command("colors")
def analyze_colors_cmd(
    deck_file: Annotated[Path, typer.Argument(help="Deck file path")],
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Analyze color distribution of a deck."""
    ctx = DatabaseContext()
    deck_cards = parse_deck_file(deck_file)

    async def _run() -> None:
        db = await ctx.get_db()
        input_data = AnalyzeDeckInput(cards=deck_cards)
        result = await deck.analyze_colors(db, input_data)

        if as_json:
            output_json(result)
        else:
            console.print("\n[bold]Color Analysis[/]\n")
            colors_str = ", ".join(result.colors) if result.colors else "Colorless"
            console.print(f"Colors: [cyan]{colors_str}[/]")
            console.print(f"Multicolor cards: {result.multicolor_count}")
            console.print(f"Colorless cards: {result.colorless_count}")

            if result.mana_pip_totals:
                console.print("\n[bold]Mana pip totals:[/]")
                color_styles = {"W": "white", "U": "blue", "B": "magenta", "R": "red", "G": "green"}
                for color, count in result.mana_pip_totals.items():
                    style = color_styles.get(color, "white")
                    console.print(f"  [{style}]{color}[/]: {count}")

            if result.recommended_land_ratio:
                console.print("\n[bold]Recommended land ratios:[/]")
                for color, ratio in result.recommended_land_ratio.items():
                    console.print(f"  {color}: {ratio:.1%}")

        await ctx.close()

    run_async(_run())


@deck_app.command("composition")
def analyze_composition_cmd(
    deck_file: Annotated[Path, typer.Argument(help="Deck file path")],
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Analyze card type composition of a deck."""
    ctx = DatabaseContext()
    deck_cards = parse_deck_file(deck_file)

    async def _run() -> None:
        db = await ctx.get_db()
        input_data = AnalyzeDeckInput(cards=deck_cards)
        result = await deck.analyze_deck_composition(db, input_data)

        if as_json:
            output_json(result)
        else:
            console.print("\n[bold]Deck Composition[/]\n")
            console.print(f"Total cards: [cyan]{result.total_cards}[/]")
            console.print(f"Creatures: {result.creatures}")
            console.print(f"Lands: {result.lands}")
            console.print(f"Spells: {result.spells}")

            if result.types:
                table = Table(title="By Type")
                table.add_column("Type")
                table.add_column("Count", justify="right")
                table.add_column("Percentage", justify="right")

                for tc in result.types:
                    table.add_row(tc.type, str(tc.count), f"{tc.percentage:.1f}%")

                console.print(table)

        await ctx.close()

    run_async(_run())


@deck_app.command("price")
def analyze_price_cmd(
    deck_file: Annotated[Path, typer.Argument(help="Deck file path")],
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Analyze total price of a deck."""
    ctx = DatabaseContext()
    deck_cards = parse_deck_file(deck_file)

    async def _run() -> None:
        db = await ctx.get_db()
        scryfall = await ctx.get_scryfall()

        if scryfall is None:
            console.print("[red]Error: Scryfall database not available[/]")
            await ctx.close()
            return

        input_data = AnalyzeDeckInput(cards=deck_cards)
        result = await deck.analyze_deck_price(db, scryfall, input_data)

        if as_json:
            output_json(result)
        else:
            console.print("\n[bold]Deck Price Analysis[/]\n")
            if result.total_price is not None:
                console.print(f"Total: [green]${result.total_price:.2f}[/]")
                if result.mainboard_price is not None:
                    console.print(f"  Mainboard: ${result.mainboard_price:.2f}")
                if result.sideboard_price is not None:
                    console.print(f"  Sideboard: ${result.sideboard_price:.2f}")

            if result.most_expensive:
                table = Table(title="Most Expensive Cards")
                table.add_column("Card")
                table.add_column("Qty", justify="right")
                table.add_column("Total", justify="right")

                for cp in result.most_expensive[:10]:
                    if cp.total_price is not None:
                        table.add_row(cp.name, str(cp.quantity), f"${cp.total_price:.2f}")

                console.print(table)

            if result.missing_prices:
                console.print(
                    f"\n[yellow]Missing prices for:[/] {', '.join(result.missing_prices[:5])}"
                )
                if len(result.missing_prices) > 5:
                    console.print(f"[dim]... and {len(result.missing_prices) - 5} more[/dim]")

        await ctx.close()

    run_async(_run())
