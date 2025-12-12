"""Interactive REPL for MTG CLI."""

from __future__ import annotations

import random
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel

from mtg_mcp.cli.context import DatabaseContext, run_async
from mtg_mcp.cli.display import display_image_in_terminal, fetch_card_image
from mtg_mcp.cli.formatting import (
    GOODBYE_QUOTES,
    prettify_mana,
    strip_quotes,
)
from mtg_mcp.cli.synergy_display import (
    display_combos,
    display_synergies_paginated,
)
from mtg_mcp.cli.tui import (
    console as tui_console,
    render_card,
    render_card_not_found,
    render_error,
    render_full_help,
    render_welcome,
)
from mtg_mcp.data.models.inputs import SearchCardsInput
from mtg_mcp.exceptions import CardNotFoundError, MTGError, SetNotFoundError
from mtg_mcp.tools import cards, images, sets, synergy

if TYPE_CHECKING:
    from mtg_mcp.data.database import MTGDatabase, ScryfallDatabase

console = Console()

# Filter aliases for REPL search
FILTER_ALIASES: dict[str, str] = {
    # Type filters
    "t": "type",
    "type": "type",
    "s": "subtype",
    "sub": "subtype",
    "subtype": "subtype",
    # Color filters
    "c": "colors",
    "color": "colors",
    "colors": "colors",
    "ci": "color_identity",
    "identity": "color_identity",
    # Mana value filters
    "cmc": "cmc",
    "mv": "cmc",
    "mana": "cmc",
    "cmc<": "cmc_max",
    "cmc>": "cmc_min",
    "mv<": "cmc_max",
    "mv>": "cmc_min",
    # Format filter
    "f": "format",
    "format": "format",
    "legal": "format",
    # Other filters
    "r": "rarity",
    "rarity": "rarity",
    "set": "set",
    "e": "set",
    "edition": "set",
    "text": "text",
    "o": "text",
    "oracle": "text",
    # Keywords
    "kw": "keywords",
    "keyword": "keywords",
    "keywords": "keywords",
    # Power/Toughness
    "pow": "power",
    "power": "power",
    "tou": "toughness",
    "toughness": "toughness",
    # Sorting
    "sort": "sort_by",
    "order": "sort_order",
}


def parse_search_filters(args: str) -> tuple[str | None, SearchCardsInput]:
    """Parse search string with filters.

    Syntax: search [name] [filter:value] ...

    Examples:
        search dragon
        search dragon t:creature c:R
        search t:instant c:U,W cmc:2
        search bolt f:modern
        search text:"draw a card" c:U

    Returns:
        Tuple of (name_query, SearchCardsInput)
    """
    # Pattern to match filter:value pairs (handles quoted values)
    filter_pattern = re.compile(r'(\w+[<>]?):(?:"([^"]+)"|(\S+))')

    filters: dict[str, Any] = {}

    # Valid color values
    valid_colors = frozenset({"W", "U", "B", "R", "G"})
    # Valid rarity values
    valid_rarities = frozenset({"common", "uncommon", "rare", "mythic"})
    # Valid sort fields
    valid_sort_fields = frozenset({"name", "cmc", "color", "rarity", "type"})
    # Valid sort orders
    valid_sort_orders = frozenset({"asc", "desc"})

    # Find all filter:value matches
    filter_matches = list(filter_pattern.finditer(args))

    # Extract filters with validation
    for match in filter_matches:
        key = match.group(1).lower()
        value = match.group(2) or match.group(3)  # Quoted or unquoted

        canonical = FILTER_ALIASES.get(key)
        if canonical:
            # Validate specific filter values
            if canonical in ("colors", "color_identity"):
                # Validate each color character
                clean_value = value.upper().replace(",", "")
                invalid_colors = set(clean_value) - valid_colors
                if invalid_colors:
                    # Skip invalid colors but continue
                    clean_value = "".join(c for c in clean_value if c in valid_colors)
                    if not clean_value:
                        continue
                value = clean_value
            elif canonical == "rarity":
                if value.lower() not in valid_rarities:
                    continue  # Skip invalid rarity
                value = value.lower()
            elif canonical == "sort_by":
                if value.lower() not in valid_sort_fields:
                    continue  # Skip invalid sort field
                value = value.lower()
            elif canonical == "sort_order":
                if value.lower() not in valid_sort_orders:
                    continue  # Skip invalid sort order
                value = value.lower()
            filters[canonical] = value

    # Everything not part of a filter is the name query
    remaining = args
    for match in reversed(filter_matches):
        remaining = remaining[: match.start()] + remaining[match.end() :]
    name_query = remaining.strip() or None

    # Build SearchCardsInput
    colors = None
    if "colors" in filters:
        # Parse colors like "R,G" or "RG" or "R G"
        color_str = filters["colors"].upper().replace(",", "").replace(" ", "")
        colors = [c for c in color_str if c in "WUBRG"]

    color_identity = None
    if "color_identity" in filters:
        ci_str = filters["color_identity"].upper().replace(",", "").replace(" ", "")
        color_identity = [c for c in ci_str if c in "WUBRG"]

    keywords = None
    if "keywords" in filters:
        keywords = [k.strip() for k in filters["keywords"].split(",")]

    # Parse CMC values with user-visible warnings on invalid input
    cmc = None
    cmc_min = None
    cmc_max = None
    if "cmc" in filters:
        try:
            cmc = float(filters["cmc"])
        except ValueError:
            console.print(f"[yellow]Warning: Invalid cmc value '{filters['cmc']}', ignoring[/]")
    if "cmc_min" in filters:
        try:
            cmc_min = float(filters["cmc_min"])
        except ValueError:
            console.print(
                f"[yellow]Warning: Invalid cmc_min value '{filters['cmc_min']}', ignoring[/]"
            )
    if "cmc_max" in filters:
        try:
            cmc_max = float(filters["cmc_max"])
        except ValueError:
            console.print(
                f"[yellow]Warning: Invalid cmc_max value '{filters['cmc_max']}', ignoring[/]"
            )

    search_input = SearchCardsInput(
        name=name_query,
        type=filters.get("type"),
        subtype=filters.get("subtype"),
        colors=colors,
        color_identity=color_identity,
        cmc=cmc,
        cmc_min=cmc_min,
        cmc_max=cmc_max,
        power=filters.get("power"),
        toughness=filters.get("toughness"),
        rarity=filters.get("rarity"),
        set_code=filters.get("set"),
        format_legal=filters.get("format"),
        text=filters.get("text"),
        keywords=keywords,
        sort_by=filters.get("sort_by"),
        sort_order=filters.get("sort_order", "asc"),
        page_size=15,
    )

    return name_query, search_input


async def show_card(db: MTGDatabase, scryfall: ScryfallDatabase | None, name: str) -> None:
    """Display a card with MTG card-like formatting."""
    card_result = await cards.get_card(db, scryfall, name=name)
    tui_console.print(render_card(card_result))


def describe_art(art: Any) -> str:
    """Create a short description of an artwork variant."""
    tags = []
    if art.border_color == "borderless":
        tags.append("[magenta]borderless[/]")
    if art.full_art:
        tags.append("[cyan]full-art[/]")
    if art.finishes:
        if "foil" in art.finishes:
            tags.append("[yellow]foil[/]")
        if "etched" in art.finishes:
            tags.append("[blue]etched[/]")
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


def display_set_detail(s: Any) -> None:
    """Display set details in a panel."""
    console.print(
        Panel(
            f"[bold]Type:[/] {s.type}\n"
            f"[bold]Released:[/] {s.release_date or 'Unknown'}\n"
            f"[bold]Cards:[/] {s.total_set_size or 'Unknown'}",
            title=f"[cyan]{s.name}[/] [{s.code.upper()}]",
        )
    )


async def handle_search_command(
    db: MTGDatabase, scryfall: ScryfallDatabase | None, args: str
) -> None:
    """Handle the search command with pagination support."""
    _, base_filters = parse_search_filters(args)

    # Build filter description for display
    filter_desc = []
    if base_filters.type:
        filter_desc.append(f"type:{base_filters.type}")
    if base_filters.colors:
        filter_desc.append(f"colors:{''.join(base_filters.colors)}")
    if base_filters.cmc is not None:
        filter_desc.append(f"cmc:{base_filters.cmc}")
    if base_filters.cmc_min is not None:
        filter_desc.append(f"cmc>{base_filters.cmc_min}")
    if base_filters.cmc_max is not None:
        filter_desc.append(f"cmc<{base_filters.cmc_max}")
    if base_filters.format_legal:
        filter_desc.append(f"format:{base_filters.format_legal}")
    if base_filters.rarity:
        filter_desc.append(f"rarity:{base_filters.rarity}")
    if base_filters.set_code:
        filter_desc.append(f"set:{base_filters.set_code}")
    if base_filters.text:
        filter_desc.append(f'text:"{base_filters.text}"')
    if base_filters.sort_by:
        filter_desc.append(f"sort:{base_filters.sort_by} {base_filters.sort_order}")

    page_size = 20
    page = 1

    def make_filters(p: int) -> SearchCardsInput:
        return base_filters.model_copy(update={"page": p, "page_size": page_size})

    while True:
        search_result = await cards.search_cards(db, scryfall, make_filters(page))

        if search_result.count == 0:
            console.print("[yellow]No cards found matching your criteria[/]")
            return

        # Calculate pagination info
        total = search_result.total_count or search_result.count
        start = (page - 1) * page_size + 1
        end = min(page * page_size, total)
        total_pages = (total + page_size - 1) // page_size

        # Display header
        header = f"Found {total} cards"
        if filter_desc:
            header += f" [dim]({' '.join(filter_desc)})[/]"
        console.print(f"\n[bold]{header}:[/]")

        # Display cards
        for i, c in enumerate(search_result.cards, start=start):
            mana = f" {prettify_mana(c.mana_cost)}" if c.mana_cost else ""
            type_info = f" [dim]{c.type}[/]" if c.type else ""
            price = f" [green]${c.price_usd:.2f}[/]" if c.price_usd else ""
            console.print(f"  [dim]{i:3}.[/] [cyan]{c.name}[/]{mana}{type_info}{price}")

        # If only one page of results, exit immediately
        if total <= page_size:
            console.print()
            return

        # Show pagination info and prompt
        console.print(
            f"\n[dim]Showing {start}-{end} of {total} (page {page}/{total_pages})[/]"
        )

        hints = []
        if page < total_pages:
            hints.append("Enter=more")
        if page > 1:
            hints.append("b=back")
        hints.append("#=view card")
        hints.append("q=done")
        console.print(f"[dim]{' | '.join(hints)}[/]")

        try:
            nav = console.input("[bold magenta]search>[/] ").strip()
            if nav == "" and page < total_pages:
                page += 1
            elif nav.lower() == "b" and page > 1:
                page -= 1
            elif nav.lower() in ("q", "quit", ""):
                break
            elif nav.isdigit():
                idx = int(nav)
                if 1 <= idx <= total:
                    card_idx = idx - 1
                    card_page = card_idx // page_size + 1
                    # Use cached result if same page, otherwise fetch
                    result = search_result
                    if card_page != page:
                        result = await cards.search_cards(db, scryfall, make_filters(card_page))
                    card_in_page = card_idx % page_size
                    if card_in_page < len(result.cards):
                        await show_card(db, scryfall, result.cards[card_in_page].name)
                else:
                    console.print(f"[yellow]Invalid selection (1-{total})[/]")
        except (EOFError, KeyboardInterrupt):
            break
    console.print()


async def handle_art_command(scryfall: ScryfallDatabase, args: str) -> None:
    """Handle the art/image command."""
    try:
        artworks = await scryfall.get_unique_artworks(args)
        if not artworks:
            console.print(f"[yellow]No artwork found for '{args}'[/]")
            return

        if len(artworks) == 1:
            art = artworks[0]
            if art.image_normal:
                console.print("[dim]Fetching image...[/]")
                image_data = await fetch_card_image(art.image_normal)
                if image_data:
                    console.print(f"\n[bold]{art.name}[/] {describe_art(art)}\n")
                    if not display_image_in_terminal(image_data):
                        console.print("[yellow]Could not display image in terminal[/]")
                        console.print(f"[dim]View online: {art.image_normal}[/]")
                else:
                    console.print("[red]Failed to download image[/]")
        else:
            console.print(
                f"\n[bold]🎨 {len(artworks)} unique artworks for {artworks[0].name}:[/]\n"
            )
            for i, art in enumerate(artworks[:15], 1):
                desc = describe_art(art)
                price_str = f"[green]${art.get_price_usd():.2f}[/]" if art.get_price_usd() else ""
                console.print(f"  [cyan]{i:2}[/]) {desc} {price_str}")

            if len(artworks) > 15:
                console.print(f"  [dim]... and {len(artworks) - 15} more[/]")

            console.print("\n[dim]Enter a number to view, or press Enter to skip:[/]")
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
                                console.print(f"\n[bold]{art.name}[/] {describe_art(art)}\n")
                                if not display_image_in_terminal(image_data):
                                    console.print("[yellow]Could not display image in terminal[/]")
                                    console.print(f"[dim]View online: {art.image_normal}[/]")
                            else:
                                console.print("[red]Failed to download image[/]")
                    else:
                        console.print("[yellow]Invalid selection[/]")
            except (EOFError, KeyboardInterrupt):
                pass

    except CardNotFoundError:
        console.print(f"[yellow]No artwork found for '{args}'[/]")
    except MTGError as e:
        console.print(f"[red]Error: {e.message}[/]")
    console.print()


async def handle_sets_command(db: MTGDatabase, args: str) -> None:
    """Handle the sets browsing command."""
    sets_result = await sets.get_sets(db, name=args if args else None)
    all_sets = sets_result.sets
    page_size = 15
    page = 0
    filter_text = args or ""

    while True:
        if filter_text:
            filtered = [s for s in all_sets if filter_text.lower() in s.name.lower()]
        else:
            filtered = all_sets

        total = len(filtered)
        start = page * page_size
        end = min(start + page_size, total)
        page_sets = filtered[start:end]

        if filter_text:
            console.print(f"\n[bold]📚 {total} sets matching '{filter_text}':[/]")
        else:
            console.print(f"\n[bold]📚 {total} sets:[/]")

        for i, s in enumerate(page_sets, start + 1):
            console.print(
                f"  [dim]{i:3})[/] [cyan]{s.code.upper():6}[/] {s.name} [dim]({s.release_date or '?'})[/]"
            )

        hints = []
        if end < total:
            hints.append("[cyan]Enter[/]=more")
        if page > 0:
            hints.append("[cyan]b[/]=back")
        hints.append("[cyan]/<text>[/]=filter")
        hints.append("[cyan]q[/]=done")

        if end < total:
            console.print(f"\n[dim]Showing {start + 1}-{end} of {total}. {' | '.join(hints)}[/]")
        else:
            console.print(f"\n[dim]{' | '.join(hints)}[/]")

        try:
            nav = console.input("[bold magenta]sets>[/] ").strip()
            if nav == "" and end < total:
                page += 1
            elif nav.lower() == "b" and page > 0:
                page -= 1
            elif nav.lower() in ("q", "quit"):
                break
            elif nav.startswith("/"):
                filter_text = nav[1:].strip()
                page = 0
            elif nav == "" and end >= total:
                break
            elif nav.isdigit():
                idx = int(nav) - 1
                if 0 <= idx < total:
                    selected = filtered[idx]
                    full_set = await sets.get_set(db, selected.code)
                    display_set_detail(full_set)
            else:
                filter_text = nav
                page = 0
        except (EOFError, KeyboardInterrupt):
            break
    console.print()


async def handle_set_command(db: MTGDatabase, args: str) -> None:
    """Handle the set lookup command."""
    try:
        set_result = await sets.get_set(db, args)
        display_set_detail(set_result)
    except SetNotFoundError:
        sets_result = await sets.get_sets(db, name=args)
        if sets_result.count == 0:
            console.print(f"[yellow]No sets found matching '{args}'[/]")
        elif sets_result.count == 1:
            full_set = await sets.get_set(db, sets_result.sets[0].code)
            display_set_detail(full_set)
        else:
            console.print(f"\n[bold]📚 {sets_result.count} sets matching '{args}':[/]\n")
            for i, s in enumerate(sets_result.sets[:15], 1):
                console.print(
                    f"  [cyan]{i:2}[/]) [{s.code.upper():5}] {s.name} [dim]({s.release_date or '?'})[/]"
                )
            if sets_result.count > 15:
                console.print(f"  [dim]... and {sets_result.count - 15} more[/]")
            console.print("\n[dim]Enter a number to view, or press Enter to skip:[/]")
            try:
                choice = console.input("[bold magenta]#[/] ").strip()
                if choice and choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(sets_result.sets):
                        full_set = await sets.get_set(db, sets_result.sets[idx].code)
                        display_set_detail(full_set)
                    else:
                        console.print("[yellow]Invalid selection[/]")
            except (EOFError, KeyboardInterrupt):
                pass


def setup_readline() -> None:
    """Set up readline for command history."""
    try:
        import atexit
        import contextlib
        import readline

        history_file = Path.home() / ".mtg_repl_history"
        with contextlib.suppress(FileNotFoundError):
            readline.read_history_file(history_file)
        readline.set_history_length(500)
        atexit.register(readline.write_history_file, history_file)
    except ImportError:
        pass  # readline not available on some platforms


def start_repl() -> None:
    """Start the interactive REPL."""
    ctx = DatabaseContext()

    async def run_repl() -> None:
        setup_readline()

        console.print("\n[dim]Tapping mana sources...[/]")
        db = await ctx.get_db()
        scryfall = await ctx.get_scryfall()
        db_stats = await db.get_database_stats()

        card_count = db_stats.get("unique_cards", 0)
        set_count = db_stats.get("total_sets", 0)
        render_welcome(card_count, set_count)

        while True:
            try:
                line = console.input("[bold magenta]⚡[/] ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print(f"\n[dim italic]{random.choice(GOODBYE_QUOTES)}[/]")
                break

            if not line:
                continue

            line = strip_quotes(line)
            parts = line.split(None, 1)
            cmd = parts[0].lower()
            args = strip_quotes(parts[1]) if len(parts) > 1 else ""

            try:
                if cmd in ("quit", "exit", "q"):
                    console.print(f"\n[dim italic]{random.choice(GOODBYE_QUOTES)}[/]")
                    break

                elif cmd in ("help", "?"):
                    render_full_help()

                elif cmd == "search":
                    if not args:
                        console.print("[yellow]Usage: search <name> [filters][/]")
                        console.print(
                            '[dim]  Filters: t:type c:colors cmc:N f:format r:rarity set:CODE text:"..." sort:field order:asc|desc[/]'
                        )
                        console.print("[dim]  Example: search dragon t:creature c:R sort:cmc order:desc[/]")
                        continue
                    await handle_search_command(db, scryfall, args)

                elif cmd in ("card", "c"):
                    if not args:
                        console.print("[yellow]Usage: card <card name>[/]")
                        continue
                    await show_card(db, scryfall, args)

                elif cmd in ("art", "img", "image", "pic"):
                    if not args:
                        console.print("[yellow]Usage: art <card name>[/]")
                        continue
                    if scryfall is None:
                        console.print("[red]Scryfall database not available for images[/]")
                        continue
                    await handle_art_command(scryfall, args)

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
                    await show_card(db, scryfall, random_result.name)

                elif cmd == "sets":
                    await handle_sets_command(db, args)

                elif cmd == "set":
                    if not args:
                        console.print("[yellow]Usage: set <set code or name>[/]")
                        continue
                    await handle_set_command(db, args)

                elif cmd == "stats":
                    stats_data = await db.get_database_stats()
                    console.print("\n[bold]📊 Database Stats[/]")
                    console.print(f"  Cards:   [cyan]{stats_data.get('unique_cards', '?'):,}[/]")
                    console.print(f"  Sets:    [cyan]{stats_data.get('total_sets', '?'):,}[/]")
                    console.print(
                        f"  Version: [dim]{stats_data.get('data_version', 'unknown')}[/]\n"
                    )

                elif cmd in ("synergy", "syn"):
                    if not args:
                        console.print("[yellow]Usage: synergy <card name>[/]")
                        console.print("[dim]  Find cards that synergize with a given card[/]")
                        continue
                    synergy_result = await synergy.find_synergies(
                        db, card_name=args, max_results=50
                    )
                    await display_synergies_paginated(synergy_result, page_size=10)

                elif cmd in ("combos", "combo"):
                    if not args:
                        console.print("[yellow]Usage: combos <card name>[/]")
                        console.print("[dim]  Find known combos involving a card[/]")
                        continue
                    combos_result = await synergy.detect_combos(db, card_name=args)
                    display_combos(combos_result, title=f"Combos involving {args}")

                elif cmd == "suggest":
                    console.print("[yellow]The 'suggest' command requires a deck file.[/]")
                    console.print("[dim]  Use: mtg synergy suggest deck.txt[/]")
                    console.print("[dim]  Or in REPL: analyze your deck with 'combos' for individual cards[/]")

                else:
                    # Not a known command - treat as card name
                    card_name = line
                    try:
                        await show_card(db, scryfall, card_name)
                    except CardNotFoundError:
                        filters = SearchCardsInput(name=card_name, page_size=5)
                        search_result = await cards.search_cards(db, scryfall, filters)
                        if search_result.count == 0:
                            render_card_not_found(card_name)
                        elif search_result.count == 1:
                            await show_card(db, scryfall, search_result.cards[0].name)
                        else:
                            suggestions = [c.name for c in search_result.cards]
                            render_card_not_found(card_name, suggestions)

            except MTGError as e:
                render_error(e.message)

        await ctx.close()

    run_async(run_repl())
