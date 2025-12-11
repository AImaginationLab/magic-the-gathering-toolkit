"""Card lookup CLI commands."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mtg_mcp.cli.context import DatabaseContext, output_json, run_async
from mtg_mcp.data.models.inputs import SearchCardsInput
from mtg_mcp.tools import cards, images

console = Console()

card_app = typer.Typer(help="Card lookup commands")


@card_app.command("search")
def search_cards_cmd(
    name: Annotated[str | None, typer.Option("-n", "--name", help="Card name")] = None,
    card_type: Annotated[str | None, typer.Option("-t", "--type", help="Card type")] = None,
    subtype: Annotated[str | None, typer.Option("-s", "--subtype", help="Subtype")] = None,
    colors: Annotated[str | None, typer.Option("-c", "--colors", help="Colors (W,U,B,R,G)")] = None,
    cmc: Annotated[float | None, typer.Option(help="Exact mana value")] = None,
    cmc_min: Annotated[float | None, typer.Option(help="Min mana value")] = None,
    cmc_max: Annotated[float | None, typer.Option(help="Max mana value")] = None,
    format_legal: Annotated[str | None, typer.Option("-f", "--format", help="Format")] = None,
    text: Annotated[str | None, typer.Option(help="Rules text")] = None,
    rarity: Annotated[str | None, typer.Option(help="Rarity")] = None,
    set_code: Annotated[str | None, typer.Option("--set", help="Set code")] = None,
    page: Annotated[int, typer.Option(help="Page number")] = 1,
    page_size: Annotated[int, typer.Option(help="Results per page")] = 25,
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Search for cards with filters."""

    async def _run() -> None:
        async with DatabaseContext() as ctx:
            db = await ctx.get_db()
            scryfall = await ctx.get_scryfall()

            color_list = [c.strip().upper() for c in colors.split(",")] if colors else None

            filters = SearchCardsInput(
                name=name,
                type=card_type,
                subtype=subtype,
                colors=color_list,  # type: ignore[arg-type]
                cmc=cmc,
                cmc_min=cmc_min,
                cmc_max=cmc_max,
                format_legal=format_legal,  # type: ignore[arg-type]
                text=text,
                rarity=rarity,  # type: ignore[arg-type]
                set_code=set_code,
                page=page,
                page_size=page_size,
            )

            result = await cards.search_cards(db, scryfall, filters)

            if as_json:
                output_json(result)
            else:
                table = Table(title=f"Found {result.count} cards (page {result.page})")
                table.add_column("Name", style="cyan")
                table.add_column("Mana", style="yellow")
                table.add_column("Type", style="green")

                for card in result.cards:
                    table.add_row(
                        card.name,
                        card.mana_cost or "",
                        (card.type or "")[:40],
                    )

                console.print(table)
                if result.count > page * page_size:
                    console.print(f"[dim]... and {result.count - page * page_size} more[/dim]")

    run_async(_run())


@card_app.command("get")
def get_card_cmd(
    name: Annotated[str, typer.Argument(help="Card name")],
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Get detailed card information."""

    async def _run() -> None:
        async with DatabaseContext() as ctx:
            db = await ctx.get_db()
            scryfall = await ctx.get_scryfall()

            result = await cards.get_card(db, scryfall, name=name)

            if as_json:
                output_json(result)
            else:
                lines = []
                if result.mana_cost:
                    lines.append(f"[yellow]{result.mana_cost}[/] (CMC {result.cmc})")
                lines.append(f"[green]{result.type}[/]")
                if result.text:
                    lines.append("")
                    lines.append(result.text)
                if result.power is not None:
                    lines.append(f"\n[bold]{result.power}/{result.toughness}[/bold]")
                if result.prices and result.prices.usd:
                    lines.append(f"\n[dim]${result.prices.usd:.2f}[/dim]")

                console.print(Panel("\n".join(lines), title=f"[bold cyan]{result.name}[/]"))

    run_async(_run())


@card_app.command("rulings")
def get_rulings_cmd(
    name: Annotated[str, typer.Argument(help="Card name")],
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Get official rulings for a card."""

    async def _run() -> None:
        async with DatabaseContext() as ctx:
            db = await ctx.get_db()
            result = await cards.get_card_rulings(db, name)

            if as_json:
                output_json(result)
            else:
                console.print(f"\n[bold]Rulings for {result.card_name}[/] ({result.count} rulings)\n")
                for ruling in result.rulings:
                    console.print(f"[dim]{ruling.date}[/]")
                    console.print(f"  {ruling.text}\n")

    run_async(_run())


@card_app.command("legality")
def get_legality_cmd(
    name: Annotated[str, typer.Argument(help="Card name")],
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Get format legalities for a card."""

    async def _run() -> None:
        async with DatabaseContext() as ctx:
            db = await ctx.get_db()
            result = await cards.get_card_legalities(db, name)

            if as_json:
                output_json(result)
            else:
                table = Table(title=f"Legalities for {result.card_name}")
                table.add_column("Format", style="cyan")
                table.add_column("Status")

                for fmt, status in sorted(result.legalities.items()):
                    style = "green" if status == "Legal" else "red" if status == "Banned" else "yellow"
                    table.add_row(fmt, f"[{style}]{status}[/]")

                console.print(table)

    run_async(_run())


@card_app.command("price")
def get_price_cmd(
    name: Annotated[str, typer.Argument(help="Card name")],
    set_code: Annotated[str | None, typer.Option("--set", help="Set code")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Get current prices for a card."""

    async def _run() -> None:
        async with DatabaseContext() as ctx:
            scryfall = await ctx.get_scryfall()
            if scryfall is None:
                console.print("[red]Error: Scryfall database not available[/]")
                return

            result = await images.get_card_price(scryfall, name, set_code)

            if as_json:
                output_json(result)
            else:
                table = Table(title=f"Prices for {result.card_name}")
                table.add_column("Currency")
                table.add_column("Regular", justify="right")
                table.add_column("Foil", justify="right")

                if result.prices:
                    usd = f"${result.prices.usd:.2f}" if result.prices.usd else "-"
                    usd_foil = f"${result.prices.usd_foil:.2f}" if result.prices.usd_foil else "-"
                    eur = f"€{result.prices.eur:.2f}" if result.prices.eur else "-"
                    eur_foil = f"€{result.prices.eur_foil:.2f}" if result.prices.eur_foil else "-"

                    table.add_row("USD", usd, usd_foil)
                    table.add_row("EUR", eur, eur_foil)

                console.print(table)

    run_async(_run())


@card_app.command("random")
def random_card_cmd(
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Get a random card."""

    async def _run() -> None:
        async with DatabaseContext() as ctx:
            db = await ctx.get_db()
            scryfall = await ctx.get_scryfall()

            result = await cards.get_random_card(db, scryfall)

            if as_json:
                output_json(result)
            else:
                lines = []
                if result.mana_cost:
                    lines.append(f"[yellow]{result.mana_cost}[/]")
                lines.append(f"[green]{result.type}[/]")
                if result.text:
                    lines.append(f"\n{result.text}")

                console.print(Panel("\n".join(lines), title=f"[bold cyan]{result.name}[/]"))

    run_async(_run())
