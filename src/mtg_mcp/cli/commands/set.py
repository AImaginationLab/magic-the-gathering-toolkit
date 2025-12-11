"""Set lookup CLI commands."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mtg_mcp.cli.context import DatabaseContext, output_json, run_async
from mtg_mcp.tools import sets

console = Console()

set_app = typer.Typer(help="Set lookup commands")


@set_app.command("list")
def list_sets_cmd(
    name: Annotated[str | None, typer.Option("-n", "--name", help="Filter by name")] = None,
    set_type: Annotated[str | None, typer.Option("-t", "--type", help="Filter by type")] = None,
    include_online: Annotated[bool, typer.Option(help="Include online-only")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """List Magic sets."""

    async def _run() -> None:
        async with DatabaseContext() as ctx:
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

    run_async(_run())


@set_app.command("get")
def get_set_cmd(
    code: Annotated[str, typer.Argument(help="Set code")],
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Get details for a specific set."""

    async def _run() -> None:
        async with DatabaseContext() as ctx:
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

    run_async(_run())
