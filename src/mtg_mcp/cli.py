"""MTG CLI - Command-line interface for Magic: The Gathering tools."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import get_settings
from .data.database import DatabaseManager, MTGDatabase, ScryfallDatabase
from .data.models.inputs import AnalyzeDeckInput, DeckCardInput, SearchCardsInput
from .tools import cards, deck, images, sets

console = Console()

# =============================================================================
# Database context manager
# =============================================================================


class DatabaseContext:
    """Lazy database connection manager for CLI."""

    def __init__(self) -> None:
        self._manager: DatabaseManager | None = None
        self._db: MTGDatabase | None = None
        self._scryfall: ScryfallDatabase | None = None

    async def get_db(self) -> MTGDatabase:
        """Get MTGDatabase, connecting if needed."""
        if self._manager is None:
            settings = get_settings()
            self._manager = DatabaseManager(settings)
            await self._manager.start()
            self._db = self._manager.db
            self._scryfall = self._manager.scryfall
        assert self._db is not None
        return self._db

    async def get_scryfall(self) -> ScryfallDatabase | None:
        """Get ScryfallDatabase, connecting if needed."""
        await self.get_db()
        return self._scryfall

    async def close(self) -> None:
        """Close database connections."""
        if self._manager is not None:
            await self._manager.stop()
            self._manager = None


def run_async(coro: Any) -> Any:
    """Run async coroutine in sync context."""
    return asyncio.run(coro)


def output_json(data: Any) -> None:
    """Output data as JSON."""
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    rprint(json.dumps(data, indent=2, default=str))


# =============================================================================
# Main CLI app
# =============================================================================

cli = typer.Typer(
    name="mtg",
    help="MTG CLI - Magic: The Gathering card lookup and deck analysis tools.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

card_app = typer.Typer(help="Card lookup commands")
set_app = typer.Typer(help="Set lookup commands")
deck_app = typer.Typer(help="Deck analysis commands")

cli.add_typer(card_app, name="card")
cli.add_typer(set_app, name="set")
cli.add_typer(deck_app, name="deck")


# =============================================================================
# Server command
# =============================================================================


@cli.command()
def serve() -> None:
    """Start the MCP server."""
    from .server import main

    main()


# =============================================================================
# Card commands
# =============================================================================


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
    ctx = DatabaseContext()

    async def _run() -> None:
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

        await ctx.close()

    run_async(_run())


@card_app.command("get")
def get_card_cmd(
    name: Annotated[str, typer.Argument(help="Card name")],
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Get detailed card information."""
    ctx = DatabaseContext()

    async def _run() -> None:
        db = await ctx.get_db()
        scryfall = await ctx.get_scryfall()

        result = await cards.get_card(db, scryfall, name=name)

        if as_json:
            output_json(result)
        else:
            # Build card panel
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

        await ctx.close()

    run_async(_run())


@card_app.command("rulings")
def get_rulings_cmd(
    name: Annotated[str, typer.Argument(help="Card name")],
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Get official rulings for a card."""
    ctx = DatabaseContext()

    async def _run() -> None:
        db = await ctx.get_db()
        result = await cards.get_card_rulings(db, name)

        if as_json:
            output_json(result)
        else:
            console.print(f"\n[bold]Rulings for {result.card_name}[/] ({result.count} rulings)\n")
            for ruling in result.rulings:
                console.print(f"[dim]{ruling.date}[/]")
                console.print(f"  {ruling.text}\n")

        await ctx.close()

    run_async(_run())


@card_app.command("legality")
def get_legality_cmd(
    name: Annotated[str, typer.Argument(help="Card name")],
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Get format legalities for a card."""
    ctx = DatabaseContext()

    async def _run() -> None:
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

        await ctx.close()

    run_async(_run())


@card_app.command("price")
def get_price_cmd(
    name: Annotated[str, typer.Argument(help="Card name")],
    set_code: Annotated[str | None, typer.Option("--set", help="Set code")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Get current prices for a card."""
    ctx = DatabaseContext()

    async def _run() -> None:
        scryfall = await ctx.get_scryfall()
        if scryfall is None:
            console.print("[red]Error: Scryfall database not available[/]")
            await ctx.close()
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

        await ctx.close()

    run_async(_run())


@card_app.command("random")
def random_card_cmd(
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Get a random card."""
    ctx = DatabaseContext()

    async def _run() -> None:
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

        await ctx.close()

    run_async(_run())


# =============================================================================
# Set commands
# =============================================================================


@set_app.command("list")
def list_sets_cmd(
    name: Annotated[str | None, typer.Option("-n", "--name", help="Filter by name")] = None,
    set_type: Annotated[str | None, typer.Option("-t", "--type", help="Filter by type")] = None,
    include_online: Annotated[bool, typer.Option(help="Include online-only")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """List Magic sets."""
    ctx = DatabaseContext()

    async def _run() -> None:
        db = await ctx.get_db()
        result = await sets.get_sets(db, name, set_type, include_online)

        if as_json:
            output_json(result)
        else:
            table = Table(title=f"Found {result.count} sets")
            table.add_column("Code", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("Released", style="dim")
            table.add_column("Type", style="green")

            for s in result.sets[:50]:
                table.add_row(s.code, s.name, s.release_date or "????", s.type or "")

            console.print(table)
            if result.count > 50:
                console.print(f"[dim]... and {result.count - 50} more[/dim]")

        await ctx.close()

    run_async(_run())


@set_app.command("get")
def get_set_cmd(
    code: Annotated[str, typer.Argument(help="Set code")],
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Get details for a specific set."""
    ctx = DatabaseContext()

    async def _run() -> None:
        db = await ctx.get_db()
        result = await sets.get_set(db, code)

        if as_json:
            output_json(result)
        else:
            lines = [
                f"[bold]Type:[/] {result.type}",
                f"[bold]Released:[/] {result.release_date or 'Unknown'}",
                f"[bold]Cards:[/] {result.total_set_size or 'Unknown'}",
            ]
            console.print(
                Panel("\n".join(lines), title=f"[bold cyan]{result.name}[/] [{result.code}]")
            )

        await ctx.close()

    run_async(_run())


# =============================================================================
# Deck commands
# =============================================================================


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
        from .data.models.inputs import ValidateDeckInput

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


# =============================================================================
# Stats command
# =============================================================================


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


# =============================================================================
# REPL command
# =============================================================================


MANA_SYMBOLS = {
    "W": "[white on white]  [/]",  # White
    "U": "[blue on blue]  [/]",  # Blue
    "B": "[black on black]  [/]",  # Black
    "R": "[red on red]  [/]",  # Red
    "G": "[green on green]  [/]",  # Green
}

# Pretty mana symbol representations
MANA_DISPLAY = {
    "{W}": "⚪",  # White
    "{U}": "🔵",  # Blue
    "{B}": "⚫",  # Black
    "{R}": "🔴",  # Red
    "{G}": "🟢",  # Green
    "{C}": "◇",  # Colorless
    "{T}": "↩️",  # Tap
    "{Q}": "↪️",  # Untap
    "{X}": "Ⓧ",  # X
    "{S}": "❄️",  # Snow
    "{E}": "⚡",  # Energy
}


async def fetch_card_image(url: str) -> bytes | None:
    """Fetch card image from URL."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            if response.status_code == 200:
                return response.content
    except Exception:
        pass
    return None


def display_image_iterm2(image_data: bytes) -> bool:
    """Display image using iTerm2's imgcat protocol (high fidelity)."""
    import base64
    import os
    import sys

    # Check if we're in iTerm2 or a compatible terminal
    term_program = os.environ.get("TERM_PROGRAM", "")
    if term_program not in ("iTerm.app", "WezTerm", "mintty"):
        # Check for other iTerm2-compatible terminals
        lc_terminal = os.environ.get("LC_TERMINAL", "")
        if lc_terminal != "iTerm2":
            return False

    try:
        # iTerm2 inline images protocol
        # Format: ESC ] 1337 ; File = [arguments] : base64data ^G
        encoded = base64.b64encode(image_data).decode("ascii")

        # Width=auto fits to terminal, preserveAspectRatio keeps card shape
        sys.stdout.write(f"\033]1337;File=inline=1;width=30;preserveAspectRatio=1:{encoded}\a")
        sys.stdout.write("\n")
        sys.stdout.flush()
        return True
    except Exception:
        return False


def display_image_kitty(image_data: bytes) -> bool:
    """Display image using Kitty graphics protocol (high fidelity)."""
    import base64
    import os
    import sys

    # Check if we're in Kitty terminal
    if os.environ.get("TERM", "") != "xterm-kitty":
        return False

    try:
        encoded = base64.b64encode(image_data).decode("ascii")

        # Kitty graphics protocol - send in chunks
        # a=T means transmit, f=100 means PNG format auto-detect
        chunk_size = 4096
        first_chunk = True

        for i in range(0, len(encoded), chunk_size):
            chunk = encoded[i : i + chunk_size]
            is_last = i + chunk_size >= len(encoded)

            if first_chunk:
                # First chunk: a=T (transmit), f=100 (auto format), m=1 if more chunks
                m = 0 if is_last else 1
                sys.stdout.write(f"\033_Ga=T,f=100,m={m};{chunk}\033\\")
                first_chunk = False
            else:
                # Continuation chunks
                m = 0 if is_last else 1
                sys.stdout.write(f"\033_Gm={m};{chunk}\033\\")

        sys.stdout.write("\n")
        sys.stdout.flush()
        return True
    except Exception:
        return False


def display_image_sixel(image_data: bytes, width: int = 25) -> bool:
    """Display image using Sixel graphics (for compatible terminals)."""
    import os

    # Sixel support check - very few terminals support this
    # Known: xterm with +sixel, mlterm, some others
    term = os.environ.get("TERM", "")
    if "sixel" not in term.lower():
        return False

    try:
        from io import BytesIO

        from PIL import Image

        img = Image.open(BytesIO(image_data))

        # Resize for display (sixel has ~6 pixels per character height)
        aspect_ratio = img.height / img.width
        px_width = width * 10  # ~10 pixels per character width
        px_height = int(px_width * aspect_ratio)

        resized = img.resize((px_width, px_height), Image.Resampling.LANCZOS)
        resized.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)

        # This would require a sixel encoder - skip for now
        return False
    except Exception:
        return False


def display_image_in_terminal(image_data: bytes, width: int = 25) -> bool:
    """Display image in terminal. Tries high-fidelity protocols first, falls back to ANSI."""

    # Try high-fidelity protocols first
    if display_image_iterm2(image_data):
        return True
    if display_image_kitty(image_data):
        return True

    # Fall back to ANSI half-block rendering
    try:
        from io import BytesIO
        from typing import cast

        from PIL import Image

        img = Image.open(BytesIO(image_data))

        # Calculate height maintaining aspect ratio (cards are ~745x1040)
        aspect_ratio = img.height / img.width
        height = int(width * aspect_ratio * 0.5)  # Terminal chars are ~2:1

        # Resize - use higher internal resolution for better quality
        # Sample at 2x width and height, then each character represents 2x2 pixels
        resized = img.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
        rgb_img = resized.convert("RGB")

        lines: list[str] = []

        for y in range(0, rgb_img.height, 2):
            line = ""
            for x in range(rgb_img.width):
                # Get top and bottom pixels
                r1, g1, b1 = cast("tuple[int, int, int]", rgb_img.getpixel((x, y)))
                if y + 1 < rgb_img.height:
                    r2, g2, b2 = cast("tuple[int, int, int]", rgb_img.getpixel((x, y + 1)))
                else:
                    r2, g2, b2 = 0, 0, 0

                # Use half-block character with fg=top, bg=bottom
                line += f"\033[38;2;{r1};{g1};{b1}m\033[48;2;{r2};{g2};{b2}m▀"

            line += "\033[0m"  # Reset colors
            lines.append(line)

        # Print the image
        for line in lines:
            print(line)

        return True
    except Exception:
        return False


def prettify_mana(text: str) -> str:
    """Convert mana symbols to pretty Unicode representations."""
    import re

    result = text

    # Replace specific symbols
    for symbol, pretty in MANA_DISPLAY.items():
        result = result.replace(symbol, pretty)

    # Replace generic mana {1}, {2}, etc with circled numbers
    def replace_generic(match: re.Match[str]) -> str:
        num = int(match.group(1))
        if num == 0:
            return "⓪"
        elif num <= 20:
            # Circled numbers ① through ⑳
            return chr(0x2460 + num - 1)
        else:
            return f"({num})"

    result = re.sub(r"\{(\d+)\}", replace_generic, result)

    # Replace hybrid mana like {W/U} with both symbols
    result = re.sub(
        r"\{([WUBRGC])/([WUBRGC])\}",
        lambda m: f"{MANA_DISPLAY.get('{' + m.group(1) + '}', m.group(1))}/{MANA_DISPLAY.get('{' + m.group(2) + '}', m.group(2))}",
        result,
    )

    # Replace Phyrexian mana like {W/P}
    result = re.sub(
        r"\{([WUBRG])/P\}",
        lambda m: f"{MANA_DISPLAY.get('{' + m.group(1) + '}', m.group(1))}ᵖ",
        result,
    )

    return result


FLAVOR_QUOTES = [
    '"The spark ignites. The journey begins."',
    '"In the multiverse, every spell tells a story."',
    '"Knowledge is the ultimate power."',
    '"From the chaos of mana, order is forged."',
    '"Every planeswalker was once a beginner."',
]

GOODBYE_QUOTES = [
    '"Until we meet again, planeswalker."',
    '"May your draws be ever in your favor."',
    '"The spell fades, but the magic remains."',
    '"Go forth and conquer the multiverse!"',
    '"Another chapter closes in the Blind Eternities..."',
]


def strip_quotes(s: str) -> str:
    """Strip surrounding quotes from a string."""
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


@cli.command()
def repl() -> None:
    """Start interactive REPL mode."""
    import random

    ctx = DatabaseContext()

    # Cool ASCII art banner
    banner = """
[bold red]    ╔╦╗╔═╗╔═╗╦╔═╗[/]  [bold white]┌┬┐┬ ┬┌─┐[/]
[bold red]    ║║║╠═╣║ ╦║║  [/]  [bold white] │ ├─┤├┤ [/]
[bold red]    ╩ ╩╩ ╩╚═╝╩╚═╝[/]  [bold white] ┴ ┴ ┴└─┘[/]
[bold blue]  ╔═╗╔═╗╔╦╗╦ ╦╔═╗╦═╗╦╔╗╔╔═╗[/]
[bold blue]  ║ ╦╠═╣ ║ ╠═╣║╣ ╠╦╝║║║║║ ╦[/]
[bold blue]  ╚═╝╩ ╩ ╩ ╩ ╩╚═╝╩╚═╩╝╚╝╚═╝[/]
"""
    console.print(banner)
    console.print(f"[dim italic]{random.choice(FLAVOR_QUOTES)}[/]\n")

    async def run_repl() -> None:
        console.print("[dim]Tapping mana sources...[/]")
        db = await ctx.get_db()
        scryfall = await ctx.get_scryfall()
        db_stats = await db.get_database_stats()

        mana_bar = "".join(MANA_SYMBOLS.values())
        console.print(f"\n{mana_bar}")
        console.print(
            f"[bold green]Library loaded![/] {db_stats.get('unique_cards', '?'):,} cards across {db_stats.get('total_sets', '?')} sets"
        )
        console.print("[dim]Type a card name to look it up, or [cyan]?[/] for help[/]\n")

        async def _show_card(db: MTGDatabase, scryfall: ScryfallDatabase | None, name: str) -> None:
            """Display a card with MTG card-like formatting."""
            import textwrap

            card_result = await cards.get_card(db, scryfall, name=name)

            # Determine border color based on card colors
            # Using colors that work on both light and dark backgrounds
            border_style = "grey70"  # Default gray for colorless/artifacts
            if card_result.colors:
                color_map = {
                    "W": "grey93",  # White - light gray (visible on dark bg)
                    "U": "dodger_blue1",  # Blue
                    "B": "medium_purple",  # Black - purple so it's visible
                    "R": "red1",  # Red
                    "G": "green3",  # Green
                }
                if len(card_result.colors) == 1:
                    border_style = color_map.get(card_result.colors[0], "grey70")
                elif len(card_result.colors) >= 2:
                    border_style = "gold1"  # Gold for multicolor

            # Card dimensions
            panel_width = 50
            text_width = 40  # Width for text wrapping
            sep_width = panel_width - 6  # Account for border (2) + padding (4)
            sep = f"[dim]{'─' * sep_width}[/]"

            # Build card content
            lines: list[str] = []

            # ═══ NAME + MANA COST ═══
            mana = prettify_mana(card_result.mana_cost) if card_result.mana_cost else ""
            if mana:
                lines.append(f"[bold]{card_result.name}[/]  {mana}")
            else:
                lines.append(f"[bold]{card_result.name}[/]")

            lines.append(sep)

            # ═══ TYPE LINE ═══
            lines.append(f"[italic]{card_result.type}[/]")

            # ═══ RULES TEXT ═══
            if card_result.text:
                lines.append(sep)
                pretty_text = prettify_mana(card_result.text)
                pretty_text = pretty_text.replace("\\n", "\n")

                paragraphs = pretty_text.split("\n")
                for i, para in enumerate(paragraphs):
                    if para.strip():
                        wrapped = textwrap.fill(para.strip(), width=text_width)
                        lines.append(wrapped)
                        if i < len(paragraphs) - 1:
                            lines.append("")

            # ═══ FLAVOR TEXT ═══
            if card_result.flavor:
                lines.append(sep)
                flavor = card_result.flavor.replace("\\n", "\n")
                wrapped_flavor = textwrap.fill(flavor, width=text_width)
                lines.append(f'[dim italic]"{wrapped_flavor}"[/]')

            # ═══ P/T or LOYALTY ═══
            # Note: emoji + space to help with terminal width alignment
            if card_result.power is not None and card_result.toughness is not None:
                lines.append(sep)
                lines.append(f"⚔️ [bold]{card_result.power}/{card_result.toughness}[/]")
            elif card_result.loyalty is not None:
                lines.append(sep)
                lines.append(f"🛡️ [bold]{card_result.loyalty}[/]")

            # ═══ FOOTER ═══
            footer_parts = []
            if card_result.set_code:
                rarity_icons = {"common": "○", "uncommon": "◐", "rare": "●", "mythic": "★"}
                rarity_colors = {
                    "common": "white",
                    "uncommon": "cyan",
                    "rare": "yellow",
                    "mythic": "red",
                }
                icon = (
                    rarity_icons.get(card_result.rarity.lower(), "○") if card_result.rarity else "○"
                )
                r_color = (
                    rarity_colors.get(card_result.rarity.lower(), "white")
                    if card_result.rarity
                    else "white"
                )
                footer_parts.append(f"[{r_color}]{icon} {card_result.set_code.upper()}[/]")
            if card_result.prices and card_result.prices.usd:
                footer_parts.append(f"💰 [green]${card_result.prices.usd:.2f}[/]")

            if footer_parts:
                lines.append(sep)
                lines.append(" · ".join(footer_parts))

            console.print(
                Panel(
                    "\n".join(lines),
                    border_style=border_style,
                    padding=(1, 2),
                    width=panel_width,
                )
            )

        while True:
            try:
                line = console.input("[bold magenta]⚡[/] ").strip()
            except (EOFError, KeyboardInterrupt):
                import random as r

                console.print(f"\n[dim italic]{r.choice(GOODBYE_QUOTES)}[/]")
                break

            if not line:
                continue

            # Strip quotes from the entire input first for single-word inputs
            line = strip_quotes(line)

            parts = line.split(None, 1)
            cmd = parts[0].lower()
            args = strip_quotes(parts[1]) if len(parts) > 1 else ""

            try:
                if cmd in ("quit", "exit", "q"):
                    import random as r

                    console.print(f"\n[dim italic]{r.choice(GOODBYE_QUOTES)}[/]")
                    break

                elif cmd in ("help", "?"):
                    console.print("\n[bold]⚔️  Spell Book[/]\n")
                    console.print("  [bold cyan]Just type a card name[/] to look it up!")
                    console.print("")
                    console.print("  [cyan]search[/] <text>    Search cards by name")
                    console.print(
                        "  [cyan]art[/] <name>       Browse & display card art (pick from variants)"
                    )
                    console.print("  [cyan]rulings[/] <name>   Official card rulings")
                    console.print("  [cyan]legal[/] <name>     Format legalities")
                    console.print("  [cyan]price[/] <name>     Current prices")
                    console.print("  [cyan]random[/]           Discover a random card")
                    console.print(
                        "  [cyan]sets[/]             Browse all sets (paginated, searchable)"
                    )
                    console.print("  [cyan]set[/] <name>       Set details (by code or name)")
                    console.print("  [cyan]stats[/]            Database info")
                    console.print("  [cyan]quit[/]             Exit")
                    console.print()

                elif cmd == "search":
                    if not args:
                        console.print("[yellow]Usage: search <card name>[/]")
                        continue
                    filters = SearchCardsInput(name=args, page_size=10)
                    search_result = await cards.search_cards(db, scryfall, filters)
                    console.print(f"\n[bold]Found {search_result.count} cards:[/]")
                    for c in search_result.cards:
                        mana = f" [yellow]{c.mana_cost}[/]" if c.mana_cost else ""
                        console.print(f"  [cyan]{c.name}[/]{mana}")
                    console.print()

                elif cmd in ("card", "c"):
                    if not args:
                        console.print("[yellow]Usage: card <card name>[/]")
                        continue
                    await _show_card(db, scryfall, args)

                elif cmd in ("art", "img", "image", "pic"):
                    if not args:
                        console.print("[yellow]Usage: art <card name>[/]")
                        continue
                    if scryfall is None:
                        console.print("[red]Scryfall database not available for images[/]")
                        continue

                    try:
                        # Get all unique artworks
                        artworks = await scryfall.get_unique_artworks(args)
                        if not artworks:
                            console.print(f"[yellow]No artwork found for '{args}'[/]")
                            continue

                        # Helper to describe artwork
                        def describe_art(art: Any) -> str:
                            """Create a short description of an artwork variant."""
                            import json as json_mod

                            tags = []
                            if art.border_color == "borderless":
                                tags.append("[magenta]borderless[/]")
                            if art.full_art:
                                tags.append("[cyan]full-art[/]")
                            if art.finishes:
                                try:
                                    finishes = json_mod.loads(art.finishes)
                                    if "foil" in finishes:
                                        tags.append("[yellow]foil[/]")
                                    if "etched" in finishes:
                                        tags.append("[blue]etched[/]")
                                except Exception:
                                    pass
                            frame_names = {
                                "1993": "Alpha",
                                "1997": "Classic",
                                "2003": "Modern",
                                "2015": "M15",
                                "future": "Future",
                            }
                            frame_desc = frame_names.get(art.frame, art.frame) if art.frame else ""
                            set_info = f"[dim]{art.set_code.upper()}[/]" if art.set_code else ""
                            tags_str = " ".join(tags)
                            return f"{set_info} {frame_desc} {tags_str}".strip()

                        # If only one artwork, display it directly
                        if len(artworks) == 1:
                            art = artworks[0]
                            if art.image_normal:
                                console.print("[dim]Fetching image...[/]")
                                image_data = await fetch_card_image(art.image_normal)
                                if image_data:
                                    console.print(f"\n[bold]{art.name}[/] {describe_art(art)}\n")
                                    if not display_image_in_terminal(image_data):
                                        console.print(
                                            "[yellow]Could not display image in terminal[/]"
                                        )
                                        console.print(f"[dim]View online: {art.image_normal}[/]")
                                else:
                                    console.print("[red]Failed to download image[/]")
                        else:
                            # Show artwork choices
                            console.print(
                                f"\n[bold]🎨 {len(artworks)} unique artworks for {artworks[0].name}:[/]\n"
                            )
                            for i, art in enumerate(artworks[:15], 1):
                                desc = describe_art(art)
                                price_str = (
                                    f"[green]${art.get_price_usd():.2f}[/]"
                                    if art.get_price_usd()
                                    else ""
                                )
                                console.print(f"  [cyan]{i:2}[/]) {desc} {price_str}")

                            if len(artworks) > 15:
                                console.print(f"  [dim]... and {len(artworks) - 15} more[/]")

                            console.print(
                                "\n[dim]Enter a number to view, or press Enter to skip:[/]"
                            )
                            try:
                                choice = console.input("[bold magenta]#[/] ").strip()
                                if choice and choice.isdigit():
                                    idx = int(choice) - 1
                                    if 0 <= idx < len(artworks):
                                        art = artworks[idx]
                                        if art.image_normal:
                                            console.print("[dim]Fetching image...[/]")
                                            image_data = await fetch_card_image(art.image_normal)
                                            if image_data:
                                                console.print(
                                                    f"\n[bold]{art.name}[/] {describe_art(art)}\n"
                                                )
                                                if not display_image_in_terminal(image_data):
                                                    console.print(
                                                        "[yellow]Could not display image in terminal[/]"
                                                    )
                                                    console.print(
                                                        f"[dim]View online: {art.image_normal}[/]"
                                                    )
                                            else:
                                                console.print("[red]Failed to download image[/]")
                                    else:
                                        console.print("[yellow]Invalid selection[/]")
                            except (EOFError, KeyboardInterrupt):
                                pass

                    except Exception as e:
                        console.print(f"[red]Error: {e}[/]")
                    console.print()

                elif cmd in ("rulings", "r"):
                    if not args:
                        console.print("[yellow]Usage: rulings <card name>[/]")
                        continue
                    rulings_result = await cards.get_card_rulings(db, args)
                    console.print(
                        f"\n[bold]📜 {rulings_result.count} rulings for {rulings_result.card_name}:[/]"
                    )
                    for ruling in rulings_result.rulings[:5]:
                        console.print(f"  [dim]{ruling.date}[/] {ruling.text}")
                    if rulings_result.count > 5:
                        console.print(f"  [dim]... and {rulings_result.count - 5} more[/dim]")
                    console.print()

                elif cmd in ("legality", "legal", "l"):
                    if not args:
                        console.print("[yellow]Usage: legal <card name>[/]")
                        continue
                    legality_result = await cards.get_card_legalities(db, args)
                    console.print(f"\n[bold]⚖️  {legality_result.card_name}[/]")
                    for fmt in [
                        "standard",
                        "pioneer",
                        "modern",
                        "legacy",
                        "vintage",
                        "commander",
                        "pauper",
                    ]:
                        if fmt in legality_result.legalities:
                            status = legality_result.legalities[fmt]
                            icon = "✓" if status == "Legal" else "✗" if status == "Banned" else "~"
                            style = (
                                "green"
                                if status == "Legal"
                                else "red"
                                if status == "Banned"
                                else "yellow"
                            )
                            console.print(f"  {icon} [{style}]{fmt.capitalize():12}[/] {status}")
                    console.print()

                elif cmd in ("price", "p"):
                    if not args:
                        console.print("[yellow]Usage: price <card name>[/]")
                        continue
                    if scryfall is None:
                        console.print("[red]💰 Scryfall database not available for prices[/]")
                        continue
                    price_result = await images.get_card_price(scryfall, args)
                    console.print(f"\n[bold]💰 {price_result.card_name}[/]")
                    if price_result.prices:
                        if price_result.prices.usd:
                            console.print(f"  USD: [green]${price_result.prices.usd:.2f}[/]")
                        if price_result.prices.usd_foil:
                            console.print(f"  Foil: [yellow]${price_result.prices.usd_foil:.2f}[/]")
                    else:
                        console.print("  [dim]No price data available[/]")
                    console.print()

                elif cmd == "random":
                    random_result = await cards.get_random_card(db, scryfall)
                    console.print("\n[bold]🎲 Random card:[/]")
                    await _show_card(db, scryfall, random_result.name)

                elif cmd == "sets":
                    sets_result = await sets.get_sets(db, name=args if args else None)
                    all_sets = sets_result.sets
                    page_size = 15
                    page = 0
                    filter_text = args or ""

                    while True:
                        # Filter sets if there's a filter
                        if filter_text:
                            filtered = [
                                s for s in all_sets if filter_text.lower() in s.name.lower()
                            ]
                        else:
                            filtered = all_sets

                        total = len(filtered)
                        start = page * page_size
                        end = min(start + page_size, total)
                        page_sets = filtered[start:end]

                        # Display current page
                        if filter_text:
                            console.print(f"\n[bold]📚 {total} sets matching '{filter_text}':[/]")
                        else:
                            console.print(f"\n[bold]📚 {total} sets:[/]")

                        for i, s in enumerate(page_sets, start + 1):
                            console.print(
                                f"  [dim]{i:3})[/] [cyan]{s.code.upper():6}[/] {s.name} [dim]({s.release_date or '?'})[/]"
                            )

                        # Show navigation hints
                        hints = []
                        if end < total:
                            hints.append("[cyan]Enter[/]=more")
                        if page > 0:
                            hints.append("[cyan]b[/]=back")
                        hints.append("[cyan]/<text>[/]=filter")
                        hints.append("[cyan]q[/]=done")

                        if end < total:
                            console.print(
                                f"\n[dim]Showing {start + 1}-{end} of {total}. {' | '.join(hints)}[/]"
                            )
                        else:
                            console.print(f"\n[dim]{' | '.join(hints)}[/]")

                        try:
                            nav = console.input("[bold magenta]sets>[/] ").strip()
                            if nav == "" and end < total:
                                page += 1
                            elif nav.lower() == "b" and page > 0:
                                page -= 1
                            elif nav.lower() == "q" or nav.lower() == "quit":
                                break
                            elif nav.startswith("/"):
                                filter_text = nav[1:].strip()
                                page = 0  # Reset to first page when filtering
                            elif nav == "" and end >= total:
                                break  # No more pages, exit
                            else:
                                # Maybe they entered a number to select
                                if nav.isdigit():
                                    idx = int(nav) - 1
                                    if 0 <= idx < total:
                                        selected = filtered[idx]
                                        full_set = await sets.get_set(db, selected.code)
                                        console.print(
                                            Panel(
                                                f"[bold]Type:[/] {full_set.type}\n"
                                                f"[bold]Released:[/] {full_set.release_date or 'Unknown'}\n"
                                                f"[bold]Cards:[/] {full_set.total_set_size or 'Unknown'}",
                                                title=f"[cyan]{full_set.name}[/] [{full_set.code.upper()}]",
                                            )
                                        )
                                else:
                                    # Treat as new filter
                                    filter_text = nav
                                    page = 0
                        except (EOFError, KeyboardInterrupt):
                            break
                    console.print()

                elif cmd == "set":
                    if not args:
                        console.print("[yellow]Usage: set <set code or name>[/]")
                        continue

                    # Helper to display a set (expects SetDetail with total_set_size)
                    def _display_set_detail(s: Any) -> None:
                        console.print(
                            Panel(
                                f"[bold]Type:[/] {s.type}\n"
                                f"[bold]Released:[/] {s.release_date or 'Unknown'}\n"
                                f"[bold]Cards:[/] {s.total_set_size or 'Unknown'}",
                                title=f"[cyan]{s.name}[/] [{s.code.upper()}]",
                            )
                        )

                    # First try exact code match
                    try:
                        set_result = await sets.get_set(db, args)
                        _display_set_detail(set_result)
                    except Exception:
                        # Not found by code - search by name
                        sets_result = await sets.get_sets(db, name=args)
                        if sets_result.count == 0:
                            console.print(f"[yellow]No sets found matching '{args}'[/]")
                        elif sets_result.count == 1:
                            # Fetch full details for single match
                            full_set = await sets.get_set(db, sets_result.sets[0].code)
                            _display_set_detail(full_set)
                        else:
                            # Multiple matches - let user pick
                            console.print(
                                f"\n[bold]📚 {sets_result.count} sets matching '{args}':[/]\n"
                            )
                            for i, s in enumerate(sets_result.sets[:15], 1):
                                console.print(
                                    f"  [cyan]{i:2}[/]) [{s.code.upper():5}] {s.name} [dim]({s.release_date or '?'})[/]"
                                )
                            if sets_result.count > 15:
                                console.print(f"  [dim]... and {sets_result.count - 15} more[/]")
                            console.print(
                                "\n[dim]Enter a number to view, or press Enter to skip:[/]"
                            )
                            try:
                                choice = console.input("[bold magenta]#[/] ").strip()
                                if choice and choice.isdigit():
                                    idx = int(choice) - 1
                                    if 0 <= idx < len(sets_result.sets):
                                        # Fetch full details for selected set
                                        full_set = await sets.get_set(
                                            db, sets_result.sets[idx].code
                                        )
                                        _display_set_detail(full_set)
                                    else:
                                        console.print("[yellow]Invalid selection[/]")
                            except (EOFError, KeyboardInterrupt):
                                pass

                elif cmd == "stats":
                    stats_data = await db.get_database_stats()
                    console.print("\n[bold]📊 Database Stats[/]")
                    console.print(f"  Cards:   [cyan]{stats_data.get('unique_cards', '?'):,}[/]")
                    console.print(f"  Sets:    [cyan]{stats_data.get('total_sets', '?'):,}[/]")
                    console.print(
                        f"  Version: [dim]{stats_data.get('data_version', 'unknown')}[/]\n"
                    )

                else:
                    # Not a known command - treat the whole line as a card name!
                    card_name = line  # Use the full original line
                    try:
                        await _show_card(db, scryfall, card_name)
                    except Exception:
                        # If exact match fails, try searching
                        filters = SearchCardsInput(name=card_name, page_size=5)
                        search_result = await cards.search_cards(db, scryfall, filters)
                        if search_result.count == 0:
                            console.print(
                                f"[dim]No cards found matching '[/][yellow]{card_name}[/][dim]'[/]"
                            )
                        elif search_result.count == 1:
                            # Single match - show it
                            await _show_card(db, scryfall, search_result.cards[0].name)
                        else:
                            console.print("\n[dim]Did you mean one of these?[/]")
                            for c in search_result.cards:
                                mana = f" [yellow]{c.mana_cost}[/]" if c.mana_cost else ""
                                console.print(f"  [cyan]{c.name}[/]{mana}")
                            console.print()

            except Exception as e:
                console.print(f"[red]Error: {e}[/]")

        await ctx.close()

    run_async(run_repl())


if __name__ == "__main__":
    cli()
