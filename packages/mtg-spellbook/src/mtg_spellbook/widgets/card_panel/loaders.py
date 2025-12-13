"""Data loading utilities for card panel."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

import httpx
from PIL import Image

from mtg_core.exceptions import CardNotFoundError
from mtg_core.tools import cards, images

from ...ui.theme import ui_colors
from .formatters import highlight_keywords

if TYPE_CHECKING:
    from mtg_core.data.database import MTGDatabase, ScryfallDatabase
    from mtg_core.data.models.responses import PrintingInfo


async def load_rulings(db: MTGDatabase, card_name: str, keywords: set[str]) -> tuple[str, bool]:
    """Load and display rulings for a card with enhanced styling.

    Returns:
        Tuple of (formatted text, success flag)
    """
    try:
        result = await cards.get_card_rulings(db, card_name)
        if result.rulings:
            lines = [
                f"[bold {ui_colors.GOLD}]📜 {result.card_name}[/]",
                f"[dim]{result.count} official rulings[/]",
                "[dim]" + "─" * 50 + "[/]",
                "",
            ]
            for i, ruling in enumerate(result.rulings, 1):
                # Date with icon
                lines.append(f"[{ui_colors.GOLD_DIM}]#{i}[/] [dim italic]{ruling.date}[/]")
                # Ruling text with highlighting
                ruling_text = highlight_keywords(ruling.text, keywords)
                lines.append(f"   {ruling_text}")
                lines.append("")
            return "\n".join(lines), True
        else:
            return f"[dim]No rulings found for {card_name}[/]", True
    except CardNotFoundError:
        return f"[red]Card not found: {card_name}[/]", False


async def load_legalities(db: MTGDatabase, card_name: str) -> tuple[str, bool]:
    """Load and display format legalities with enhanced styling.

    Returns:
        Tuple of (formatted text, success flag)
    """
    try:
        result = await cards.get_card_legalities(db, card_name)
        lines = [f"[bold {ui_colors.GOLD}]⚖️ {result.card_name}[/]"]
        lines.append("[dim]" + "─" * 40 + "[/]")
        lines.append("")

        formats = [
            ("standard", "Standard"),
            ("pioneer", "Pioneer"),
            ("modern", "Modern"),
            ("legacy", "Legacy"),
            ("vintage", "Vintage"),
            ("commander", "Commander"),
            ("pauper", "Pauper"),
            ("brawl", "Brawl"),
        ]

        for fmt, display_name in formats:
            if fmt in result.legalities:
                status = result.legalities[fmt]
                if status == "Legal":
                    icon, style = "✓", "green bold"
                elif status == "Banned":
                    icon, style = "✗", "red bold"
                elif status == "Restricted":
                    icon, style = "⚠", "yellow bold"
                else:
                    icon, style = "○", "dim"

                lines.append(f"  [{style}]{icon}[/] [dim]{display_name:12}[/] [{style}]{status}[/]")

        return "\n".join(lines), True
    except CardNotFoundError:
        return f"[red]Card not found: {card_name}[/]", False


async def load_printings(
    scryfall: ScryfallDatabase | None, card_name: str
) -> tuple[list[PrintingInfo], str | None]:
    """Load all printings for a card.

    Returns:
        Tuple of (printings list, error message if any)
    """
    if not scryfall:
        return [], "[yellow]Scryfall database not available[/]"

    try:
        result = await images.get_card_printings(scryfall, card_name)
        if not result.printings:
            return [], f"[yellow]No printings found for {card_name}[/]"

        # Sort by price, highest first
        printings = sorted(
            result.printings,
            key=lambda p: p.price_usd if p.price_usd is not None else -1,
            reverse=True,
        )
        return printings, None
    except CardNotFoundError:
        return [], f"[red]Card not found: {card_name}[/]"
    except Exception as e:
        return [], f"[red]Error loading printings: {e}[/]"


def format_art_display(card_name: str, printing: PrintingInfo, index: int, total: int) -> str:
    """Format the art info display for a printing."""
    lines = [f"[bold]{card_name}[/]  [dim]({index + 1}/{total})[/]"]

    set_info = printing.set_code.upper() if printing.set_code else "Unknown"
    if printing.collector_number:
        set_info += f" #{printing.collector_number}"
    lines.append(f"[cyan]{set_info}[/]")

    if printing.price_usd is not None:
        lines.append(f"[green]${printing.price_usd:.2f}[/]")
    else:
        lines.append("[dim]No price[/]")

    lines.append("")
    lines.append("[dim]← → to navigate[/]")

    return "\n".join(lines)


async def load_art_image(image_url: str) -> tuple[Image.Image | None, str | None]:
    """Load a card image from URL.

    Returns:
        Tuple of (PIL Image if successful, error message if failed)
    """
    try:
        # Prefer larger image
        if "normal" in image_url:
            image_url = image_url.replace("normal", "large")

        async with httpx.AsyncClient() as client:
            response = await client.get(image_url, timeout=15.0)
            response.raise_for_status()
            image_data = response.content

        pil_image = Image.open(BytesIO(image_data))

        if pil_image.mode not in ("RGB", "L"):
            pil_image = pil_image.convert("RGB")  # type: ignore[assignment]

        return pil_image, None
    except Exception as e:
        return None, f"[red dim]Image error: {e}[/]"
