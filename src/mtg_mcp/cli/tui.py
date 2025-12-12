"""TUI components for MTG CLI - rich terminal interface styling."""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mtg_mcp.cli.formatting import prettify_mana

if TYPE_CHECKING:
    from mtg_mcp.data.models.responses import CardDetail

console = Console()

# Color scheme inspired by MTG
COLORS = {
    "white": "#F8F6F0",
    "blue": "#0E68AB",
    "black": "#150B00",
    "red": "#D3202A",
    "green": "#00733E",
    "gold": "#C9A227",
    "colorless": "#CBC5BF",
    "accent": "#9B4DCA",
    "dim": "#666666",
}


def render_header(card_count: int, set_count: int) -> Panel:
    """Render the app header with stats."""
    title = Text()
    title.append("⚔️  ", style="bold")
    title.append("MTG", style="bold red")
    title.append(" ", style="")
    title.append("SPELLBOOK", style="bold white")
    title.append("  ⚔️", style="bold")

    stats = Text()
    stats.append(f"📚 {card_count:,} cards", style="cyan")
    stats.append("  •  ", style="dim")
    stats.append(f"🎴 {set_count} sets", style="cyan")

    content = Group(title, Text(""), stats)
    return Panel(
        content,
        border_style="bright_blue",
        padding=(0, 2),
    )


def render_menu() -> Panel:
    """Render the command menu bar."""
    menu = Table.grid(padding=(0, 2))
    menu.add_column(style="bold cyan", justify="center")
    menu.add_column(style="dim")
    menu.add_column(style="bold cyan", justify="center")
    menu.add_column(style="dim")
    menu.add_column(style="bold cyan", justify="center")
    menu.add_column(style="dim")

    menu.add_row(
        "[card]", "lookup",
        "[search]", "find cards",
        "[art]", "view art",
    )
    menu.add_row(
        "[synergy]", "find combos",
        "[sets]", "browse sets",
        "[random]", "discover",
    )

    return Panel(
        menu,
        title="[bold]Commands[/]",
        title_align="left",
        border_style="dim",
        padding=(0, 1),
    )


def render_quick_help() -> Panel:
    """Render quick help panel."""
    help_text = Text()
    help_text.append("💡 ", style="yellow")
    help_text.append("Just type a card name to look it up! ", style="")
    help_text.append("Try: ", style="dim")
    help_text.append("Lightning Bolt", style="italic cyan")
    help_text.append(" or ", style="dim")
    help_text.append("search dragon t:creature", style="italic cyan")

    return Panel(
        help_text,
        border_style="yellow",
        padding=(0, 1),
    )


def render_welcome(card_count: int, set_count: int, show_menu: bool = True) -> None:
    """Render the welcome screen with header and menu."""
    console.print()
    console.print(render_header(card_count, set_count))
    if show_menu:
        console.print(render_menu())
        console.print(render_quick_help())
    console.print()


def render_command_bar() -> str:
    """Render an inline command reminder and return the prompt."""
    hints = Text()
    hints.append("  [", style="dim")
    hints.append("?", style="bold yellow")
    hints.append("=help", style="dim")
    hints.append(" ", style="")
    hints.append("q", style="bold yellow")
    hints.append("=quit", style="dim")
    hints.append("]", style="dim")
    console.print(hints)
    return ""


def render_search_filters_help() -> Panel:
    """Render search filters help."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", width=12)
    table.add_column(style="")

    filters = [
        ("t:creature", "Card type"),
        ("c:RG", "Colors (WUBRG)"),
        ("ci:WU", "Color identity"),
        ("cmc:3", "Mana value"),
        ("cmc>:2", "Min mana value"),
        ("cmc<:5", "Max mana value"),
        ("f:modern", "Format legal"),
        ("r:mythic", "Rarity"),
        ("set:MH2", "Set code"),
        ("text:\"draw\"", "Oracle text"),
        ("kw:flying", "Keywords"),
        ("sort:cmc", "Sort by field"),
    ]

    for cmd, desc in filters:
        table.add_row(cmd, desc)

    return Panel(
        table,
        title="[bold]🔍 Search Filters[/]",
        title_align="left",
        border_style="cyan",
        padding=(0, 1),
    )


def render_full_help() -> None:
    """Render full help screen."""
    console.print()

    # Commands section
    cmd_table = Table.grid(padding=(0, 3))
    cmd_table.add_column(style="bold cyan", width=20)
    cmd_table.add_column(style="")

    commands = [
        ("📖 Card Lookup", ""),
        ("<card name>", "Look up any card directly"),
        ("search <query>", "Search with filters"),
        ("art <name>", "View card artwork"),
        ("rulings <name>", "Official rulings"),
        ("legal <name>", "Format legalities"),
        ("price <name>", "Current prices"),
        ("random", "Discover a random card"),
        ("", ""),
        ("🔗 Synergy & Combos", ""),
        ("synergy <name>", "Find synergistic cards"),
        ("combos <name>", "Find known combos"),
        ("", ""),
        ("📚 Sets & Info", ""),
        ("sets", "Browse all sets"),
        ("set <code>", "Set details"),
        ("stats", "Database info"),
        ("quit", "Exit"),
    ]

    for cmd, desc in commands:
        if cmd.startswith(("📖", "🔗", "📚")):
            cmd_table.add_row(f"[bold yellow]{cmd}[/]", "")
        elif cmd:
            cmd_table.add_row(cmd, f"[dim]{desc}[/]")
        else:
            cmd_table.add_row("", "")

    console.print(Panel(
        cmd_table,
        title="[bold]⚔️ Spell Book[/]",
        border_style="bright_blue",
        padding=(1, 2),
    ))

    console.print(render_search_filters_help())

    # Examples
    examples = Text()
    examples.append("search dragon t:creature c:R\n", style="cyan")
    examples.append("search t:instant f:modern cmc<:3\n", style="cyan")
    examples.append("search text:\"draw a card\" c:U\n", style="cyan")
    examples.append("search r:mythic set:MOM sort:cmc", style="cyan")

    console.print(Panel(
        examples,
        title="[bold]💡 Examples[/]",
        border_style="green",
        padding=(0, 1),
    ))
    console.print()


def render_status_bar(message: str, style: str = "dim") -> None:
    """Render a status message."""
    console.print(f"[{style}]{message}[/]")


def render_error(message: str) -> None:
    """Render an error message."""
    console.print(Panel(
        f"[bold red]Error:[/] {message}",
        border_style="red",
        padding=(0, 1),
    ))


def render_card_not_found(name: str, suggestions: list[str] | None = None) -> None:
    """Render card not found message with suggestions."""
    content = Text()
    content.append("No cards found matching ", style="")
    content.append(f"'{name}'", style="yellow")

    if suggestions:
        content.append("\n\n")
        content.append("Did you mean?\n", style="dim")
        for sug in suggestions[:5]:
            content.append(f"  • {sug}\n", style="cyan")

    console.print(Panel(
        content,
        border_style="yellow",
        padding=(0, 1),
    ))


# Border color mapping for MTG card colors
CARD_BORDER_COLORS = {
    "W": "grey93",
    "U": "dodger_blue1",
    "B": "medium_purple",
    "R": "red1",
    "G": "green3",
}

RARITY_ICONS = {"common": "○", "uncommon": "◐", "rare": "●", "mythic": "★"}
RARITY_COLORS = {"common": "white", "uncommon": "cyan", "rare": "yellow", "mythic": "red"}


def get_card_border_style(colors: list[str] | None) -> str:
    """Determine border color based on card colors."""
    if not colors:
        return "grey70"  # Colorless/artifacts
    if len(colors) == 1:
        return CARD_BORDER_COLORS.get(colors[0], "grey70")
    return "gold1"  # Multicolor


def render_card(card: CardDetail, width: int = 60) -> Panel:
    """Render a card with MTG-style formatting.

    Returns a Panel that can be printed or used in layouts.
    """
    text_width = width - 10
    sep_width = width - 6
    sep = f"[dim]{'─' * sep_width}[/]"

    lines: list[str] = []

    # NAME + MANA COST
    mana = prettify_mana(card.mana_cost) if card.mana_cost else ""
    if mana:
        lines.append(f"[bold]{card.name}[/]  {mana}")
    else:
        lines.append(f"[bold]{card.name}[/]")

    lines.append(sep)

    # TYPE LINE
    lines.append(f"[italic]{card.type}[/]")

    # RULES TEXT
    if card.text:
        lines.append(sep)
        pretty_text = prettify_mana(card.text).replace("\\n", "\n")

        for i, para in enumerate(pretty_text.split("\n")):
            if para.strip():
                wrapped = textwrap.fill(para.strip(), width=text_width)
                lines.append(wrapped)
                if i < len(pretty_text.split("\n")) - 1:
                    lines.append("")

    # FLAVOR TEXT
    if card.flavor:
        lines.append(sep)
        flavor = card.flavor.replace("\\n", "\n")
        wrapped_flavor = textwrap.fill(flavor, width=text_width)
        lines.append(f'[dim italic]"{wrapped_flavor}"[/]')

    # P/T or LOYALTY or DEFENSE
    if card.power is not None and card.toughness is not None:
        lines.append(sep)
        lines.append(f"⚔️ [bold]{card.power}/{card.toughness}[/]")
    elif card.loyalty is not None:
        lines.append(sep)
        lines.append(f"🛡️ [bold]{card.loyalty}[/]")
    elif card.defense is not None:
        lines.append(sep)
        lines.append(f"🏰 [bold]{card.defense}[/]")

    # FOOTER: Set + Rarity + Price
    footer_parts = []
    if card.set_code:
        rarity = card.rarity.lower() if card.rarity else "common"
        icon = RARITY_ICONS.get(rarity, "○")
        r_color = RARITY_COLORS.get(rarity, "white")
        footer_parts.append(f"[{r_color}]{icon} {card.set_code.upper()}[/]")

    if card.prices and card.prices.usd:
        footer_parts.append(f"💰 [green]${card.prices.usd:.2f}[/]")

    if footer_parts:
        lines.append(sep)
        lines.append(" · ".join(footer_parts))

    return Panel(
        "\n".join(lines),
        border_style=get_card_border_style(card.colors),
        padding=(1, 2),
        width=width,
    )


def render_card_compact(card: CardDetail) -> Panel:
    """Render a compact card view for search results."""
    mana = prettify_mana(card.mana_cost) if card.mana_cost else ""

    # Build compact info
    info = Text()
    info.append(card.name, style="bold cyan")
    if mana:
        info.append(f"  {mana}")
    info.append("\n")
    info.append(card.type or "", style="dim italic")

    if card.power is not None and card.toughness is not None:
        info.append(f"  [{card.power}/{card.toughness}]", style="bold")

    return Panel(
        info,
        border_style=get_card_border_style(card.colors),
        padding=(0, 1),
    )


def render_search_results_grid(cards: list[CardDetail]) -> None:
    """Render search results in a grid layout."""
    if not cards:
        console.print("[dim]No cards found[/]")
        return

    # Create compact panels for each card
    panels = [render_card_compact(card) for card in cards]

    # Display in columns
    console.print(Columns(panels, equal=True, expand=True))
