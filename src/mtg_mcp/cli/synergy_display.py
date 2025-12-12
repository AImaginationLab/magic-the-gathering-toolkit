"""Display utilities for synergy results.

Shared between CLI commands and REPL for consistent formatting.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

from mtg_mcp.cli.formatting import prettify_mana
from mtg_mcp.cli.pagination import format_score_bar

if TYPE_CHECKING:
    from mtg_mcp.data.models.responses import (
        DetectCombosResult,
        FindSynergiesResult,
        SuggestCardsResult,
        SynergyResult,
    )

console = Console()


SYNERGY_TYPE_ICONS = {
    "keyword": "🔑",
    "tribal": "👥",
    "ability": "✨",
    "theme": "🎯",
    "archetype": "🏛️",
}

CATEGORY_ICONS = {
    "synergy": "🔗",
    "staple": "⭐",
    "upgrade": "⬆️",
    "budget": "💰",
}

THEME_ICONS = {
    "tokens": "🪙",
    "aristocrats": "💀",
    "reanimator": "⚰️",
    "spellslinger": "📜",
    "voltron": "⚔️",
    "stax": "🔒",
    "landfall": "🏔️",
    "blink": "✨",
    "counters": "➕",  # noqa: RUF001
    "tribal": "👥",
    "graveyard": "🪦",
    "artifacts": "⚙️",
    "enchantress": "🌸",
    "control": "🛡️",
    "aggro": "🗡️",
}

COLOR_NAMES = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}


def render_synergy_item(syn: SynergyResult, index: int) -> None:  # noqa: ARG001
    """Render a single synergy item."""
    mana = f" {prettify_mana(syn.mana_cost)}" if syn.mana_cost else ""
    bar, style = format_score_bar(syn.score)
    icon = SYNERGY_TYPE_ICONS.get(syn.synergy_type, "•")

    console.print(f"  [{style}]{bar}[/] {icon} [cyan]{syn.name}[/]{mana}")
    console.print(f"         [dim]{syn.reason}[/]")


def render_synergy_item_compact(syn: SynergyResult, index: int) -> None:  # noqa: ARG001
    """Render a single synergy item in compact mode."""
    mana = f" {prettify_mana(syn.mana_cost)}" if syn.mana_cost else ""
    bar, style = format_score_bar(syn.score)
    icon = SYNERGY_TYPE_ICONS.get(syn.synergy_type, "•")

    console.print(f"  [{style}]{bar}[/] {icon} [cyan]{syn.name}[/]{mana}")


async def display_synergies_paginated(
    result: FindSynergiesResult,
    page_size: int = 10,
) -> None:
    """Display synergy results with pagination.

    Args:
        result: The FindSynergiesResult from the synergy tool
        page_size: Number of items per page
    """
    from mtg_mcp.cli.pagination import paginate_display

    if not result.synergies:
        console.print(f"\n[bold]Synergies for {result.card_name}[/]")
        console.print("[dim]No synergies found[/]\n")
        return

    # Show score legend once at the start
    console.print("\n[dim]Score: ●●●●● = strong synergy, ○○○○○ = weak[/]")

    await paginate_display(
        items=result.synergies,
        render_item=render_synergy_item,
        title=f"Synergies for {result.card_name}",
        page_size=page_size,
        prompt="synergy",
    )


def display_synergies(result: FindSynergiesResult, compact: bool = False) -> None:
    """Display synergy results (non-paginated, for CLI).

    Args:
        result: The FindSynergiesResult from the synergy tool
        compact: If True, use more compact display
    """
    console.print(f"\n[bold]Synergies for {result.card_name}[/] ({result.total_found} found)")

    if not result.synergies:
        console.print("[dim]No synergies found[/]\n")
        return

    console.print("[dim]Score: ●●●●● = strong synergy[/]\n")

    render_fn = render_synergy_item_compact if compact else render_synergy_item
    for i, syn in enumerate(result.synergies):
        render_fn(syn, i + 1)

    console.print()


def display_combos(result: DetectCombosResult, title: str | None = None) -> None:
    """Display combo detection results.

    Args:
        result: The DetectCombosResult from the combo detection tool
        title: Optional title to display
    """
    if title:
        console.print(f"\n[bold]{title}[/]")

    if result.combos:
        console.print(f"\n[bold green]Complete Combos ({len(result.combos)}):[/]\n")
        for combo in result.combos:
            console.print(f"  [bold cyan]{combo.id}[/] [dim][{combo.combo_type}][/]")
            console.print(f"  {combo.description}")
            for card in combo.cards:
                console.print(f"    • [cyan]{card.name}[/] — {card.role}")
            console.print()

    if result.potential_combos:
        console.print(
            f"[bold yellow]Potential Combos ({len(result.potential_combos)}):[/]\n"
        )
        for combo in result.potential_combos:
            missing = result.missing_cards.get(combo.id, [])
            console.print(f"  [bold cyan]{combo.id}[/] [dim][{combo.combo_type}][/]")
            console.print(f"  {combo.description}")
            if missing:
                console.print(f"  [red]Missing:[/] {', '.join(missing)}")
            console.print()

    if not result.combos and not result.potential_combos:
        console.print("\n[dim]No known combos found for this card.[/]")
        console.print("[dim]The combo database contains ~25 popular EDH/cEDH combos.[/]")
        console.print("[dim]Try: Thassa's Oracle, Splinter Twin, Kiki-Jiki, etc.[/]\n")


def display_suggestions(result: SuggestCardsResult, compact: bool = False) -> None:
    """Display card suggestions.

    Args:
        result: The SuggestCardsResult from the suggest cards tool
        compact: If True, use more compact display (for REPL)
    """
    if result.deck_colors:
        colors_str = "".join(result.deck_colors)
        console.print(f"\n[bold]Deck Colors:[/] [cyan]{colors_str}[/]")

    if result.detected_themes:
        console.print(f"[bold]Detected Themes:[/] {', '.join(result.detected_themes)}")

    if not result.suggestions:
        console.print("\n[dim]No suggestions generated[/]")
        return

    console.print(f"\n[bold]Card Suggestions ({len(result.suggestions)}):[/]\n")

    # Group by category
    from mtg_mcp.data.models.responses import SuggestedCard

    by_category: dict[str, list[SuggestedCard]] = {}
    for sug in result.suggestions:
        cat: str = sug.category
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(sug)

    for category, suggestions in by_category.items():
        icon = CATEGORY_ICONS.get(category, "•")
        console.print(f"[bold cyan]{icon} {category.capitalize()}:[/]")

        for sug in suggestions:
            mana = f" {prettify_mana(sug.mana_cost)}" if sug.mana_cost else ""
            price = f" [green]${sug.price_usd:.2f}[/]" if sug.price_usd else ""

            if compact:
                console.print(f"  [cyan]{sug.name}[/]{mana}{price}")
            else:
                console.print(f"  [cyan]{sug.name}[/]{mana}{price}")
                console.print(f"    [dim]{sug.reason}[/]")

        console.print()


def display_themes(
    deck_colors: list[str],
    detected_themes: list[str],
) -> None:
    """Display detected themes and colors.

    Args:
        deck_colors: List of color codes (W, U, B, R, G)
        detected_themes: List of detected theme names
    """
    if deck_colors:
        colors_display = ", ".join(
            f"[cyan]{COLOR_NAMES.get(c, c)}[/]" for c in deck_colors
        )
        console.print(f"[bold]Colors:[/] {colors_display}")
    else:
        console.print("[bold]Colors:[/] [dim]Colorless[/]")

    if detected_themes:
        console.print("\n[bold]Detected Themes:[/]")
        for theme in detected_themes:
            icon = THEME_ICONS.get(theme, "•")
            console.print(f"  {icon} [cyan]{theme.capitalize()}[/]")
    else:
        console.print("\n[dim]No strong themes detected[/]")

    console.print()
