"""Reusable styled section components for consistent UI formatting.

These helpers produce rich-text formatted strings following the app's design language.
Use these when building detail panels, insights views, and information displays.
"""

from __future__ import annotations

from dataclasses import dataclass

from .theme import ui_colors


@dataclass(frozen=True)
class SectionIcons:
    """Standard icons for section types."""

    VALUE: str = "💰"
    MECHANICS: str = "⚙️"
    TRIBAL: str = "👥"
    TYPES: str = "📋"
    LIMITED: str = "🎮"
    COMBOS: str = "⚡"
    COMMANDER: str = "👑"
    ARCHETYPES: str = "🎯"
    INFO: str = "[i]"
    TIP: str = "💡"
    WARNING: str = "⚠️"
    CHECK: str = "✓"
    BULLET: str = "•"
    ARROW: str = "→"
    STAR: str = "★"


icons = SectionIcons()


def section_header(title: str, icon: str = "", count: int | None = None) -> str:
    """Create a styled section header.

    Example output: "💰 SET VALUE (42 cards)"
    """
    icon_part = f"{icon} " if icon else ""
    count_part = f" [dim]({count})[/]" if count is not None else ""
    return f"[bold {ui_colors.GOLD}]{icon_part}{title.upper()}[/]{count_part}"


def subsection_header(title: str, color: str = ui_colors.GOLD_DIM) -> str:
    """Create a styled subsection header.

    Example output: "■ Overview"
    """
    return f"[{color} bold]■ {title}[/]"


def divider(width: int = 40) -> str:
    """Create a horizontal divider line."""
    return f"[dim]{'─' * width}[/]"


def key_value(key: str, value: str, key_color: str = ui_colors.TEXT_DIM) -> str:
    """Format a key-value pair.

    Example output: "Total Value:      $2,978.95"
    """
    return f"[{key_color}]{key}:[/] [bold]{value}[/]"


def key_value_padded(
    key: str, value: str, pad_width: int = 20, key_color: str = ui_colors.TEXT_DIM
) -> str:
    """Format a key-value pair with padding for alignment.

    Example output: "Total Value:        $2,978.95"
    """
    padded_key = f"{key}:".ljust(pad_width)
    return f"[{key_color}]{padded_key}[/] [bold]{value}[/]"


def bullet_item(text: str, indent: int = 2, bullet: str = icons.BULLET) -> str:
    """Format a bullet point item.

    Example output: "  • Lightning Bolt"
    """
    spaces = " " * indent
    return f"{spaces}[{ui_colors.GOLD_DIM}]{bullet}[/] {text}"


def numbered_item(number: int, text: str, indent: int = 2) -> str:
    """Format a numbered list item.

    Example output: "  1. Lightning Bolt - $45.00"
    """
    spaces = " " * indent
    return f"{spaces}[{ui_colors.GOLD}]{number}.[/] {text}"


def arrow_item(text: str, indent: int = 4) -> str:
    """Format an arrow-prefixed item (for sub-items).

    Example output: "    → Creates infinite mana"
    """
    spaces = " " * indent
    return f"{spaces}[{ui_colors.TEXT_DIM}]{icons.ARROW}[/] {text}"


def progress_bar(value: float, max_width: int = 15, color: str = ui_colors.GOLD) -> str:
    """Create a visual progress bar.

    Example output: "████████░░░░░░░ 53%"
    """
    clamped = max(0.0, min(1.0, value))
    filled = int(clamped * max_width)
    empty = max_width - filled
    pct = int(clamped * 100)
    return f"[{color}]{'█' * filled}[/][dim]{'░' * empty}[/] [{ui_colors.TEXT_DIM}]{pct}%[/]"


def labeled_bar(
    label: str,
    value: float,
    label_width: int = 16,
    bar_width: int = 15,
    color: str = ui_colors.GOLD,
) -> str:
    """Create a labeled progress bar for score breakdowns.

    Example output: "Text Similarity  ████████░░░░░░░ 53%"
    """
    padded_label = label.ljust(label_width)
    bar = progress_bar(value, bar_width, color)
    return f"  {padded_label} {bar}"


def stat_row(
    label: str,
    value: str | int | float,
    label_width: int = 12,
    value_color: str = ui_colors.WHITE,
) -> str:
    """Format a stat row with aligned label and value.

    Example output: "Mythic:      15"
    """
    padded = f"{label}:".ljust(label_width)
    return f"[{ui_colors.TEXT_DIM}]{padded}[/][{value_color}]{value}[/]"


def two_column_stats(
    left: tuple[str, str | int],
    right: tuple[str, str | int],
    col_width: int = 14,
) -> str:
    """Format two stats side by side.

    Example output: "Mythic:  15 │ Creature: 142"
    """
    left_str = f"{left[0]}:".ljust(col_width - 4)
    right_str = f"{right[0]}:".ljust(col_width - 4)
    return (
        f"[{ui_colors.TEXT_DIM}]{left_str}[/][bold]{left[1]}[/] "
        f"[dim]│[/] "
        f"[{ui_colors.TEXT_DIM}]{right_str}[/][bold]{right[1]}[/]"
    )


def tag(text: str, color: str = ui_colors.GOLD, bg: str = "") -> str:
    """Create a colored tag/badge.

    Example output: "[MYTHIC]" with styling
    """
    if bg:
        return f"[{color} on {bg}] {text} [/]"
    return f"[{color}][{text}][/]"


def category_badge(category: str, is_active: bool = False) -> str:
    """Create a category filter badge.

    Example output: "[All]" or styled active version
    """
    if is_active:
        return f"[{ui_colors.GOLD} on {ui_colors.BACKGROUND_SELECTED}] {category} [/]"
    return f"[{ui_colors.TEXT_DIM}][{category}][/]"


def price_display(price: float | None, currency: str = "$") -> str:
    """Format a price with appropriate color.

    Example output: "$45.00" in appropriate color
    """
    if price is None:
        return f"[{ui_colors.TEXT_DIM}]N/A[/]"

    from .theme import get_price_color

    color = get_price_color(price)
    return f"[{color}]{currency}{price:.2f}[/]"


def rank_display(rank: int, suffix: str = "") -> str:
    """Format a rank number.

    Example output: "#42 overall"
    """
    return f"[{ui_colors.GOLD}]#{rank}[/][dim]{suffix}[/]"


def percentage_display(value: float, decimal_places: int = 1) -> str:
    """Format a percentage with color based on value.

    Example output: "63.2%" in green for high values
    """
    pct = value * 100
    if pct >= 60:
        color = ui_colors.TIER_S
    elif pct >= 55:
        color = ui_colors.TIER_A
    elif pct >= 50:
        color = ui_colors.TIER_B
    elif pct >= 45:
        color = ui_colors.TIER_C
    else:
        color = ui_colors.TIER_D
    return f"[{color}]{pct:.{decimal_places}f}%[/]"


def tier_badge(tier: str) -> str:
    """Format a tier letter with appropriate color.

    Example output: "S" in gold for S-tier
    """
    tier_colors = {
        "S": ui_colors.TIER_S,
        "A": ui_colors.TIER_A,
        "B": ui_colors.TIER_B,
        "C": ui_colors.TIER_C,
        "D": ui_colors.TIER_D,
        "F": ui_colors.TIER_F,
    }
    color = tier_colors.get(tier.upper(), ui_colors.TEXT_DIM)
    return f"[bold {color}]{tier.upper()}[/]"


def card_name(name: str, rarity: str | None = None) -> str:
    """Format a card name with rarity-based coloring."""
    from .theme import get_name_color_for_rarity

    color = get_name_color_for_rarity(rarity)
    return f"[{color}]{name}[/]"


def hint_text(text: str) -> str:
    """Format hint/help text."""
    return f"[{ui_colors.TEXT_DIM}]{text}[/]"


def error_text(text: str) -> str:
    """Format error text."""
    return f"[{ui_colors.ERROR}]{text}[/]"


def success_text(text: str) -> str:
    """Format success text."""
    return f"[{ui_colors.SUCCESS}]{text}[/]"


def warning_text(text: str) -> str:
    """Format warning text."""
    return f"[{ui_colors.WARNING}]{text}[/]"


def collapsible_header(title: str, is_expanded: bool, summary: str = "", icon: str = "") -> str:
    """Format a collapsible section header.

    Example output: "▼ Set Value ($2,978.95)" or "▶ Tribal Themes (6 types)"
    """
    arrow = "▼" if is_expanded else "▶"
    icon_part = f"{icon} " if icon else ""
    summary_part = f" [{ui_colors.TEXT_DIM}]({summary})[/]" if summary else ""
    return f"[bold {ui_colors.GOLD}]{arrow} {icon_part}{title}[/]{summary_part}"


def build_section(
    title: str,
    content_lines: list[str],
    icon: str = "",
    count: int | None = None,
) -> str:
    """Build a complete styled section with header and content.

    Returns a multi-line string ready for display.
    """
    lines = [section_header(title, icon, count), ""]
    lines.extend(content_lines)
    lines.append("")
    return "\n".join(lines)
