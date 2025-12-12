"""Command handlers for the MTG Spellbook TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from textual import work
from textual.widgets import Static, TabbedContent

from mtg_mcp.cli.formatting import prettify_mana
from mtg_mcp.data.models.inputs import SearchCardsInput
from mtg_mcp.exceptions import CardNotFoundError
from mtg_mcp.tools import cards, images, sets, synergy

from .search import parse_search_query
from .widgets import CardPanel

if TYPE_CHECKING:
    from mtg_mcp.data.database import MTGDatabase, ScryfallDatabase
    from mtg_mcp.data.models.responses import CardDetail, CardSummary


class AppProtocol(Protocol):
    """Protocol for the App class that this mixin expects."""

    _db: MTGDatabase | None
    _scryfall: ScryfallDatabase | None
    _current_results: list[CardDetail]
    _current_card: CardDetail | None

    def exit(self) -> None: ...
    def query_one(self, selector: str, expect_type: type[Any] = ...) -> Any: ...


class CommandHandlersMixin:
    """Mixin providing command handler methods for the TUI app.

    This mixin expects the class to satisfy AppProtocol.
    """

    # Type hints for mixin - these will be provided by the App class
    # Using Any to avoid conflicts with base class definitions
    _db: Any  # MTGDatabase | None
    _scryfall: Any  # ScryfallDatabase | None
    _current_results: list[Any]  # list[CardDetail]
    _current_card: Any  # CardDetail | None
    _synergy_mode: bool  # Whether we're in synergy view mode
    _synergy_info: dict[str, Any]  # Maps card name -> synergy reason/score

    def handle_command(self, query: str) -> None:
        """Parse and route a command."""
        parts = query.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd in ("quit", "q", "exit"):
            self.exit()
        elif cmd == "random":
            self.lookup_random()
        elif cmd == "search":
            if args:
                self.search_cards(args)
            else:
                self._show_message("[yellow]Usage: search <query>[/]")
        elif cmd in ("synergy", "syn"):
            if args:
                self.find_synergies(args)
            else:
                self._show_message("[yellow]Usage: synergy <card name>[/]")
        elif cmd in ("combos", "combo"):
            if args:
                self.find_combos(args)
            else:
                self._show_message("[yellow]Usage: combos <card name>[/]")
        elif cmd == "sets":
            self.browse_sets(args)
        elif cmd == "set":
            if args:
                self.show_set(args)
            else:
                self._show_message("[yellow]Usage: set <code>[/]")
        elif cmd == "stats":
            self.show_stats()
        elif cmd in ("rulings", "r"):
            if args:
                self.load_rulings(args)
            else:
                self._show_message("[yellow]Usage: rulings <card name>[/]")
        elif cmd in ("legal", "l", "legality"):
            if args:
                self.load_legalities(args)
            else:
                self._show_message("[yellow]Usage: legal <card name>[/]")
        elif cmd in ("price", "p"):
            if args:
                self.show_price(args)
            else:
                self._show_message("[yellow]Usage: price <card name>[/]")
        elif cmd in ("art", "img", "image"):
            if args:
                self.show_art(args)
            else:
                self._show_message("[yellow]Usage: art <card name>[/]")
        elif cmd in ("help", "?"):
            self.show_help()
        elif cmd in ("card", "c"):
            if args:
                self.lookup_card(args)
            else:
                self._show_message("[yellow]Usage: card <name>[/]")
        else:
            # Treat as card name
            self.lookup_card(query)

    @work
    async def lookup_card(self, name: str) -> None:
        """Look up a single card by name."""
        if not self._db:
            return

        self._hide_synergy_panel()
        self._synergy_mode = False

        try:
            card = await cards.get_card(
                self._db, self._scryfall, name=name
            )
            self._current_results = [card]
            self._current_card = card
            self._update_results([card])
            self._update_card_panel(card)
            await self._load_card_extras(card)
        except CardNotFoundError:
            # Try search
            filters = SearchCardsInput(name=name, page_size=10)
            result = await cards.search_cards(
                self._db, self._scryfall, filters
            )
            if result.cards:
                await self._load_search_results(result.cards)
            else:
                self._show_message(f"[yellow]No cards found matching '{name}'[/]")

    @work
    async def search_cards(self, query: str) -> None:
        """Search for cards."""
        if not self._db:
            return

        self._hide_synergy_panel()
        self._synergy_mode = False

        filters = parse_search_query(query)
        result = await cards.search_cards(
            self._db, self._scryfall, filters
        )

        if result.cards:
            await self._load_search_results(result.cards)
        else:
            self._show_message(f"[yellow]No cards found for: {query}[/]")

    async def _load_search_results(self, summaries: list[CardSummary]) -> None:
        """Load full card details for search results."""
        if not self._db:
            return
        self._current_results = []

        for summary in summaries[:25]:
            try:
                detail = await cards.get_card(
                    self._db, self._scryfall, name=summary.name
                )
                self._current_results.append(detail)
            except CardNotFoundError:
                pass

        self._update_results(self._current_results)
        if self._current_results:
            self._current_card = self._current_results[0]
            self._update_card_panel(self._current_results[0])
            await self._load_card_extras(self._current_results[0])

    async def _load_card_extras(self, card: CardDetail) -> None:
        """Load rulings, legalities, and printings for a card."""
        panel = self.query_one("#card-panel", CardPanel)

        if self._db:
            await panel.load_rulings(self._db, card.name)
            await panel.load_legalities(self._db, card.name)

        # Load all printings for the art gallery
        await panel.load_printings(self._scryfall, card.name)

    @work
    async def lookup_random(self) -> None:
        """Get a random card."""
        if not self._db:
            return

        self._hide_synergy_panel()
        self._synergy_mode = False

        card = await cards.get_random_card(
            self._db, self._scryfall
        )
        self._current_results = [card]
        self._current_card = card
        self._update_results([card])
        self._update_card_panel(card)
        await self._load_card_extras(card)

    @work
    async def find_synergies(self, card_name: str) -> None:
        """Find synergistic cards and show in results list."""
        if not self._db:
            return

        self._synergy_mode = True
        self._synergy_info = {}

        # First, get the source card to display
        try:
            source_card = await cards.get_card(self._db, self._scryfall, name=card_name)
        except CardNotFoundError:
            self._show_message(f"[red]Card not found: {card_name}[/]")
            self._synergy_mode = False
            return

        result = await synergy.find_synergies(
            self._db, card_name=card_name, max_results=50
        )

        if not result.synergies:
            self._show_message(f"[yellow]No synergies found for {card_name}[/]")
            self._synergy_mode = False
            return

        # Store synergy info for each card
        for syn in result.synergies:
            self._synergy_info[syn.name] = {
                "type": syn.synergy_type,
                "reason": syn.reason,
                "score": syn.score,
            }

        # Load full card details for synergy cards
        self._current_results = []
        for syn in result.synergies[:25]:
            try:
                detail = await cards.get_card(self._db, self._scryfall, name=syn.name)
                self._current_results.append(detail)
            except CardNotFoundError:
                pass

        # Update results list with synergy info
        self._update_synergy_results(self._current_results, card_name, len(result.synergies))

        # Show source card in synergy panel (bottom right)
        self._show_source_card(source_card)

        if self._current_results:
            self._current_card = self._current_results[0]
            self._update_card_panel_with_synergy(self._current_results[0])
            await self._load_card_extras(self._current_results[0])

    def _update_synergy_results(
        self, results: list[Any], source_card: str, total_found: int
    ) -> None:
        """Update results list with synergy cards and detailed info."""
        from textual.widgets import Label, ListItem

        from .widgets import ResultsList

        results_list = self.query_one("#results-list", ResultsList)
        results_list.clear()

        type_icons = {
            "keyword": "🔑",
            "tribal": "👥",
            "ability": "✨",
            "theme": "🎯",
            "archetype": "🏛️",
        }

        for card in results:
            info = self._synergy_info.get(card.name, {})
            score = info.get("score", 0)
            synergy_type = info.get("type", "")
            reason = info.get("reason", "")
            icon = type_icons.get(synergy_type, "•")

            # Score indicator with color
            score_color = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "dim"
            score_bar = "●" * int(score * 5) + "○" * (5 - int(score * 5))
            mana = prettify_mana(card.mana_cost) if card.mana_cost else ""

            # Multi-line format with reason
            lines = []
            # Line 1: score | icon | name | mana
            line1 = f"[{score_color}]{score_bar}[/] {icon} [bold]{card.name}[/]"
            if mana:
                line1 += f"  {mana}"
            lines.append(line1)
            # Line 2: synergy reason (indented)
            if reason:
                lines.append(f"    [dim italic]{reason}[/]")

            results_list.append(ListItem(Label("\n".join(lines))))

        self._update_results_header(f"Synergies for {source_card} ({total_found})")

        if results:
            results_list.focus()
            results_list.index = 0

    def _update_card_panel_with_synergy(self, card: Any) -> None:
        """Update card panel and show synergy reason."""
        panel = self.query_one("#card-panel", CardPanel)
        panel.update_card_with_synergy(card, self._synergy_info.get(card.name))

    @work
    async def find_combos(self, card_name: str) -> None:
        """Find combos for a card."""
        if not self._db:
            return

        self._show_synergy_panel()

        result = await synergy.detect_combos(
            self._db, card_name=card_name
        )

        content = self.query_one("#synergy-content", Static)

        lines = [f"[bold]🔗 Combos involving {card_name}[/]", ""]

        if result.combos:
            lines.append(f"[bold green]Complete Combos ({len(result.combos)}):[/]")
            for combo in result.combos:
                lines.append(f"  [bold cyan]{combo.id}[/] [{combo.combo_type}]")
                lines.append(f"    {combo.description}")
                for card in combo.cards:
                    lines.append(f"      • [cyan]{card.name}[/] — {card.role}")
                lines.append("")

        if result.potential_combos:
            lines.append(f"[bold yellow]Potential Combos ({len(result.potential_combos)}):[/]")
            for combo in result.potential_combos:
                missing = result.missing_cards.get(combo.id, [])
                lines.append(f"  [bold cyan]{combo.id}[/] [{combo.combo_type}]")
                lines.append(f"    {combo.description}")
                if missing:
                    lines.append(f"    [red]Missing:[/] {', '.join(missing)}")
                lines.append("")

        if not result.combos and not result.potential_combos:
            lines.append("[dim]No known combos found for this card.[/]")

        content.update("\n".join(lines))

    @work
    async def browse_sets(self, query: str = "") -> None:
        """Browse available sets."""
        if not self._db:
            return

        self._hide_synergy_panel()

        result = await sets.get_sets(
            self._db, name=query if query else None
        )

        from textual.widgets import Label, ListItem

        from .widgets import ResultsList

        results_list = self.query_one("#results-list", ResultsList)
        results_list.clear()

        for s in result.sets[:50]:
            label = f"[cyan]{s.code.upper()}[/] {s.name} [dim]({s.release_date or '?'})[/]"
            results_list.append(ListItem(Label(label)))

        self._update_results_header(f"Sets ({len(result.sets)})")

    @work
    async def show_set(self, code: str) -> None:
        """Show set details."""
        if not self._db:
            return

        self._hide_synergy_panel()

        try:
            result = await sets.get_set(self._db, code)

            panel = self.query_one("#card-panel", CardPanel)
            card_text = panel.query_one("#card-text", Static)

            lines = [
                f"[bold]{result.name}[/] [{result.code.upper()}]",
                "",
                f"[bold]Type:[/] {result.type}",
                f"[bold]Released:[/] {result.release_date or 'Unknown'}",
                f"[bold]Cards:[/] {result.total_set_size or 'Unknown'}",
            ]
            card_text.update("\n".join(lines))

        except Exception:
            self._show_message(f"[red]Set not found: {code}[/]")

    @work
    async def show_stats(self) -> None:
        """Show database statistics."""
        if not self._db:
            return

        stats = await self._db.get_database_stats()

        panel = self.query_one("#card-panel", CardPanel)
        card_text = panel.query_one("#card-text", Static)

        lines = [
            "[bold]📊 Database Statistics[/]",
            "",
            f"  [bold]Cards:[/]   [cyan]{stats.get('unique_cards', '?'):,}[/]",
            f"  [bold]Sets:[/]    [cyan]{stats.get('total_sets', '?'):,}[/]",
            f"  [bold]Version:[/] [dim]{stats.get('data_version', 'unknown')}[/]",
        ]
        card_text.update("\n".join(lines))

    @work
    async def load_rulings(self, card_name: str) -> None:
        """Load rulings and switch to rulings tab."""
        if not self._db:
            return

        panel = self.query_one("#card-panel", CardPanel)
        await panel.load_rulings(self._db, card_name)

        tabs = panel.query_one("#card-tabs", TabbedContent)
        tabs.active = "tab-rulings"

    @work
    async def load_legalities(self, card_name: str) -> None:
        """Load legalities and switch to legal tab."""
        if not self._db:
            return

        panel = self.query_one("#card-panel", CardPanel)
        await panel.load_legalities(self._db, card_name)

        tabs = panel.query_one("#card-tabs", TabbedContent)
        tabs.active = "tab-legal"

    @work
    async def show_price(self, card_name: str) -> None:
        """Show price for a card."""
        if not self._scryfall:
            self._show_message("[red]Scryfall database not available for prices[/]")
            return

        try:
            result = await images.get_card_price(
                self._scryfall, card_name
            )

            panel = self.query_one("#card-panel", CardPanel)
            price_text = panel.query_one("#price-text", Static)

            lines = [f"[bold]💰 {result.card_name}[/]", ""]
            if result.prices:
                if result.prices.usd:
                    lines.append(f"  USD:  [green]${result.prices.usd:.2f}[/]")
                if result.prices.usd_foil:
                    lines.append(f"  Foil: [yellow]${result.prices.usd_foil:.2f}[/]")
                if result.prices.eur:
                    lines.append(f"  EUR:  [green]€{result.prices.eur:.2f}[/]")
            else:
                lines.append("  [dim]No price data available[/]")

            price_text.update("\n".join(lines))

            tabs = panel.query_one("#card-tabs", TabbedContent)
            tabs.active = "tab-price"

        except Exception:
            self._show_message(f"[red]Could not get price for: {card_name}[/]")

    @work
    async def show_art(self, card_name: str) -> None:
        """Show card art with all printings."""
        if not self._scryfall:
            self._show_message("[red]Scryfall database not available for images[/]")
            return

        try:
            panel = self.query_one("#card-panel", CardPanel)
            await panel.load_printings(self._scryfall, card_name)

            tabs = panel.query_one("#card-tabs", TabbedContent)
            tabs.active = "tab-art"

        except CardNotFoundError:
            self._show_message(f"[red]Card not found: {card_name}[/]")

    def show_help(self) -> None:
        """Show help in card panel."""
        self._hide_synergy_panel()

        panel = self.query_one("#card-panel", CardPanel)
        card_text = panel.query_one("#card-text", Static)

        help_text = """[bold yellow]⚔️ MTG Spellbook Help[/]

[bold cyan]Card Lookup:[/]
  [cyan]<card name>[/]     Look up a card directly
  [cyan]search <query>[/]  Search with filters
  [cyan]random[/]          Get a random card
  [cyan]art <name>[/]      View card artwork

[bold cyan]Card Info:[/]
  [cyan]rulings <name>[/]  Official card rulings
  [cyan]legal <name>[/]    Format legalities
  [cyan]price <name>[/]    Current prices

[bold cyan]Synergy:[/]
  [cyan]synergy <name>[/]  Find synergistic cards
  [cyan]combos <name>[/]   Find known combos

[bold cyan]Browse:[/]
  [cyan]sets[/]            Browse all sets
  [cyan]set <code>[/]      Set details
  [cyan]stats[/]           Database statistics

[bold cyan]Search Filters:[/]
  [cyan]t:[/]type   [cyan]c:[/]colors   [cyan]ci:[/]identity
  [cyan]cmc:[/]N    [cyan]f:[/]format   [cyan]r:[/]rarity
  [cyan]set:[/]CODE [cyan]kw:[/]keyword [cyan]text:[/]"..."

[bold cyan]Keys:[/]
  [yellow]↑↓[/]        Navigate results
  [yellow]Tab[/]       Switch tabs
  [yellow]Enter[/]     Select
  [yellow]Esc[/]       Focus input
  [yellow]Ctrl+L[/]    Clear
  [yellow]Ctrl+C[/]    Quit
"""
        card_text.update(help_text)

    def _update_results(self, results: list[CardDetail]) -> None:
        """Update the results list."""
        from textual.widgets import Label, ListItem

        from .widgets import ResultsList

        results_list = self.query_one("#results-list", ResultsList)
        results_list.clear()

        for card in results:
            mana = prettify_mana(card.mana_cost) if card.mana_cost else ""
            label = f"[bold]{card.name}[/]  {mana}" if mana else f"[bold]{card.name}[/]"
            results_list.append(ListItem(Label(label)))

        self._update_results_header(f"Results ({len(results)})")

        if results:
            results_list.focus()
            results_list.index = 0

    def _update_results_header(self, text: str) -> None:
        """Update results header text."""
        header = self.query_one("#results-header", Static)
        header.update(f"[bold]{text}[/]")

    def _update_card_panel(self, card: CardDetail | None) -> None:
        """Update the card panel."""
        panel = self.query_one("#card-panel", CardPanel)
        panel.update_card(card)

    def _show_synergy_panel(self) -> None:
        """Show synergy panel (for combos), hide card panel."""
        self.query_one("#card-panel").styles.display = "none"
        self.query_one("#synergy-panel").styles.display = "block"
        self.query_one("#synergy-panel").add_class("visible")

    def _hide_synergy_panel(self) -> None:
        """Hide synergy panel, show card panel at full height."""
        from .widgets import SynergyPanel

        self.query_one("#synergy-panel").styles.display = "none"
        self.query_one("#synergy-panel").remove_class("visible")
        self.query_one("#card-panel").styles.display = "block"
        self.query_one("#card-panel").remove_class("synergy-mode")
        # Clear source card when hiding
        synergy_panel = self.query_one("#synergy-panel", SynergyPanel)
        synergy_panel.clear_source()

    def _show_source_card(self, card: Any) -> None:
        """Show source card in synergy panel below card panel."""
        from .widgets import SynergyPanel

        synergy_panel = self.query_one("#synergy-panel", SynergyPanel)
        synergy_panel.show_source_card(card)
        # Show both panels - card panel shrinks, synergy panel appears below
        self.query_one("#card-panel").styles.display = "block"
        self.query_one("#card-panel").add_class("synergy-mode")
        self.query_one("#synergy-panel").styles.display = "block"
        self.query_one("#synergy-panel").add_class("visible")
