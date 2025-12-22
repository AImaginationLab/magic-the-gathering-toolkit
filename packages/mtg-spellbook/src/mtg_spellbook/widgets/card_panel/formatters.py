"""Card text rendering and styling utilities."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ...formatting import prettify_mana
from ...ui.theme import card_type_colors, get_rarity_style, ui_colors

if TYPE_CHECKING:
    from mtg_core.data.models.responses import CardDetail


def render_card_text(card: CardDetail, keywords: set[str]) -> str:
    """Render card as rich text with enhanced typography."""
    lines = []

    # TITLE with enhanced color
    mana = prettify_mana(card.mana_cost) if card.mana_cost else ""
    if mana:
        lines.append(f"[bold {ui_colors.GOLD}]{card.name}[/]  {mana}")
    else:
        lines.append(f"[bold {ui_colors.GOLD}]{card.name}[/]")

    # TYPE with color coding
    type_color = get_type_color(card.type or "")
    lines.append(f"[italic {type_color}]{card.type}[/]")

    # Visual separator
    lines.append("[dim]" + "─" * 50 + "[/]")
    lines.append("")

    # CARD TEXT with keyword highlighting
    if card.text:
        text = prettify_mana(card.text).replace("\\n", "\n")
        text = highlight_keywords(text, keywords)
        lines.append(text)
        lines.append("")

    # FLAVOR TEXT with enhanced styling
    if card.flavor:
        flavor = card.flavor.replace("\\n", "\n")
        lines.append("[dim]" + "─" * 50 + "[/]")
        lines.append(f'[dim italic #999]"{flavor}"[/]')
        lines.append("")

    # STATS with icons
    if card.power is not None and card.toughness is not None:
        lines.append(f"[bold {ui_colors.GOLD_DIM}]⚔  {card.power} / {card.toughness}[/]")
    elif card.loyalty is not None:
        lines.append(f"[bold {ui_colors.GOLD_DIM}]✦ Loyalty: {card.loyalty}[/]")
    elif card.defense is not None:
        lines.append(f"[bold {ui_colors.GOLD_DIM}]🛡 Defense: {card.defense}[/]")

    # FOOTER with rarity icon
    footer_parts = []
    if card.set_code:
        footer_parts.append(f"[cyan]📦 {card.set_code.upper()}[/]")
    if card.rarity:
        rarity_icon, color = get_rarity_style(card.rarity)
        footer_parts.append(f"[{color}]{rarity_icon} {card.rarity.capitalize()}[/]")

    if footer_parts:
        lines.append("")
        lines.append(" · ".join(footer_parts))

    # PRICES
    if card.prices:
        price_parts = []
        if card.prices.usd:
            price_parts.append(f"[green]${card.prices.usd:.2f}[/]")
        if card.prices.usd_foil:
            price_parts.append(f"[yellow]${card.prices.usd_foil:.2f} ✨[/]")
        if price_parts:
            lines.append("[dim]💰[/] " + " · ".join(price_parts))

    return "\n".join(lines)


def render_card_with_synergy(
    card: CardDetail, keywords: set[str], synergy_info: dict[str, object]
) -> str:
    """Render card text with synergy information appended."""
    text = render_card_text(card, keywords)

    reason = str(synergy_info.get("reason", ""))
    score_val = synergy_info.get("score", 0)
    score = float(score_val) if isinstance(score_val, (int, float)) else 0.0
    synergy_type = str(synergy_info.get("type", ""))
    score_bar = "●" * int(score * 5) + "○" * (5 - int(score * 5))
    text += f"\n\n[bold cyan]🔗 Synergy:[/] {reason}"
    text += f"\n[dim]Score: [{get_score_color(score)}]{score_bar}[/] · Type: {synergy_type}[/]"

    return text


def render_prices(card: CardDetail) -> str:
    """Render price information with enhanced styling."""
    lines = [f"[bold {ui_colors.GOLD}]💰 {card.name}[/]"]
    lines.append("[dim]" + "─" * 40 + "[/]")
    lines.append("")

    if card.prices:
        if card.prices.usd:
            lines.append(f"  [dim]USD:[/]      [green bold]${card.prices.usd:.2f}[/]")
        if card.prices.usd_foil:
            lines.append(f"  [dim]Foil:[/]     [yellow bold]${card.prices.usd_foil:.2f}[/] ✨")
        if card.prices.eur:
            lines.append(f"  [dim]EUR:[/]      [green bold]€{card.prices.eur:.2f}[/]")

        lines.append("")
        lines.append("[dim italic]Prices from Scryfall[/]")
    else:
        lines.append("  [dim]No price data available[/]")

    return "\n".join(lines)


def get_type_color(card_type: str) -> str:
    """Get color based on card type."""
    type_lower = card_type.lower()
    if "creature" in type_lower:
        return card_type_colors.CREATURE
    elif "instant" in type_lower or "sorcery" in type_lower:
        return card_type_colors.INSTANT
    elif "artifact" in type_lower:
        return card_type_colors.ARTIFACT
    elif "enchantment" in type_lower:
        return card_type_colors.ENCHANTMENT
    elif "planeswalker" in type_lower:
        return card_type_colors.PLANESWALKER
    elif "land" in type_lower:
        return card_type_colors.LAND
    return card_type_colors.DEFAULT


def get_score_color(score: float) -> str:
    """Get color for synergy score."""
    if score >= 0.8:
        return "green"
    elif score >= 0.5:
        return "yellow"
    return "dim"


def highlight_keywords(text: str, keywords: set[str]) -> str:
    """Highlight keyword abilities using keywords loaded from database."""
    if not keywords:
        return text
    for keyword in keywords:
        # Case-insensitive replacement that preserves the original case
        pattern = re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE)
        text = pattern.sub(f"[bold {ui_colors.GOLD}]{keyword}[/]", text)
    return text
