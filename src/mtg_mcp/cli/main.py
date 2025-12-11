"""MTG CLI - Command-line interface for Magic: The Gathering tools."""

from __future__ import annotations

from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from mtg_mcp.cli.commands import card_app, deck_app, set_app
from mtg_mcp.cli.context import DatabaseContext, output_json, run_async
from mtg_mcp.cli.repl import start_repl

console = Console()

# =============================================================================
# Main CLI app
# =============================================================================

cli = typer.Typer(
    name="mtg",
    help="MTG CLI - Magic: The Gathering card lookup and deck analysis tools.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

cli.add_typer(card_app, name="card")
cli.add_typer(set_app, name="set")
cli.add_typer(deck_app, name="deck")


# =============================================================================
# Top-level commands
# =============================================================================


@cli.command()
def serve() -> None:
    """Start the MCP server."""
    from mtg_mcp.server import main

    main()


@cli.command()
def stats(
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Show database statistics."""
    ctx = DatabaseContext()

    async def _run() -> None:
        db = await ctx.get_db()
        scryfall = await ctx.get_scryfall()

        db_stats = await db.get_database_stats()

        if as_json:
            data: dict[str, Any] = {"mtg_database": db_stats}
            if scryfall:
                data["scryfall_database"] = await scryfall.get_database_stats()
            output_json(data)
        else:
            table = Table(title="Database Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right")

            table.add_row("Unique cards", str(db_stats.get("unique_cards", "?")))
            table.add_row("Total printings", str(db_stats.get("total_cards", "?")))
            table.add_row("Sets", str(db_stats.get("total_sets", "?")))
            table.add_row("Data version", db_stats.get("data_version", "unknown"))

            if scryfall:
                sf_stats = await scryfall.get_database_stats()
                table.add_row("", "")  # Separator
                table.add_row("Scryfall cards", str(sf_stats.get("total_cards", "?")))

            console.print(table)

        await ctx.close()

    run_async(_run())


@cli.command()
def repl() -> None:
    """Start interactive REPL mode."""
    start_repl()


if __name__ == "__main__":
    cli()
