"""Pagination commands for navigating through results."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual import work
from textual.widgets import Label, ListItem, Static

from mtg_core.exceptions import CardNotFoundError
from mtg_core.tools import cards

from ..formatting import prettify_mana
from ..pagination import PaginationState
from ..ui.formatters import CardFormatters
from ..ui.theme import rarity_colors, ui_colors

if TYPE_CHECKING:
    from mtg_core.data.models.responses import CardDetail


class PaginationCommandsMixin:
    """Mixin providing pagination commands."""

    if TYPE_CHECKING:
        _db: Any
        _scryfall: Any
        _pagination: PaginationState | None
        _current_results: list[Any]
        _current_card: Any
        _synergy_mode: bool
        _synergy_info: dict[str, Any]

        def query_one(self, selector: str, expect_type: type[Any] = ...) -> Any: ...
        def _update_card_panel(self, card: Any) -> None: ...
        def _update_card_panel_with_synergy(self, card: Any) -> None: ...
        def _show_message(self, message: str) -> None: ...
        def push_screen(self, screen: Any, callback: Any = None) -> Any: ...

        async def _load_card_extras(self, card: Any, panel_id: str = "#card-panel") -> None: ...

    def action_next_page(self) -> None:
        """Go to next page of results."""
        if self._pagination and self._pagination.has_next_page and self._pagination.next_page():
            self._load_current_page()

    def action_prev_page(self) -> None:
        """Go to previous page of results."""
        if self._pagination and self._pagination.has_prev_page and self._pagination.prev_page():
            self._load_current_page()

    def action_first_page(self) -> None:
        """Go to first page of results."""
        if (
            self._pagination
            and self._pagination.current_page != 1
            and self._pagination.first_page()
        ):
            self._load_current_page()

    def action_last_page(self) -> None:
        """Go to last page of results."""
        if (
            self._pagination
            and self._pagination.current_page != self._pagination.total_pages
            and self._pagination.last_page()
        ):
            self._load_current_page()

    def action_goto_page(self) -> None:
        """Show go to page dialog."""
        if not self._pagination or self._pagination.total_pages <= 1:
            return

        from ..widgets import GoToPageModal

        def handle_result(page: int | None) -> None:
            if page is not None and self._pagination and self._pagination.go_to_page(page):
                self._load_current_page()

        self.push_screen(
            GoToPageModal(
                current_page=self._pagination.current_page,
                total_pages=self._pagination.total_pages,
            ),
            handle_result,
        )

    @work
    async def _load_current_page(self) -> None:
        """Load the current page of results."""
        if not self._pagination or not self._db:
            return

        # Update header to show loading
        self._pagination.is_loading = True
        self._update_pagination_header()

        # Check cache first
        cached = self._pagination.get_cached_details(self._pagination.current_page)
        if cached:
            self._current_results = cached
            self._pagination.is_loading = False
            self._display_current_page_results()
            # Prefetch next page in background
            self._prefetch_next_page()
            return

        # Load card details for current page
        current_items = self._pagination.current_page_items
        details: list[CardDetail] = []

        for item in current_items:
            try:
                # item could be CardSummary or a synergy result
                name = item.name if hasattr(item, "name") else str(item)
                detail = await cards.get_card(self._db, self._scryfall, name=name)
                details.append(detail)
            except CardNotFoundError:
                pass

        # Cache and display
        self._pagination.cache_details(self._pagination.current_page, details)
        self._current_results = details
        self._pagination.is_loading = False
        self._display_current_page_results()

        # Prefetch next page in background
        self._prefetch_next_page()

    def _display_current_page_results(self) -> None:
        """Display the current page results in the list."""
        if self._synergy_mode:
            self._display_synergy_results()
        else:
            self._display_search_results()

        # Select first result
        if self._current_results:
            self._current_card = self._current_results[0]
            if self._synergy_mode:
                self._update_card_panel_with_synergy(self._current_results[0])
            else:
                self._update_card_panel(self._current_results[0])

    def _display_search_results(self) -> None:
        """Display search results for current page."""
        from ..widgets import ResultsList

        results_list = self.query_one("#results-list", ResultsList)
        results_list.clear()

        for card in self._current_results:
            label = self._format_result_line(card)
            results_list.append(ListItem(Label(label)))

        self._update_pagination_header()

        if self._current_results:
            results_list.focus()
            results_list.index = 0

    def _display_synergy_results(self) -> None:
        """Display synergy results for current page with 10-segment score bar."""
        from ..widgets import ResultsList

        results_list = self.query_one("#results-list", ResultsList)
        results_list.clear()

        type_icons = {
            "keyword": "\U0001f511",
            "tribal": "\U0001f465",
            "ability": "\u2728",
            "theme": "\U0001f3af",
            "archetype": "\U0001f3db\ufe0f",
        }

        for card in self._current_results:
            info = self._synergy_info.get(card.name, {})
            score = info.get("score", 0)
            synergy_type = info.get("type", "")
            reason = info.get("reason", "")
            icon = type_icons.get(synergy_type, "\u2022")

            # 10-segment score bar
            score_color = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "dim"
            filled = int(score * 10)
            score_bar = "\u2588" * filled + "\u2591" * (10 - filled)

            # Card name with rarity color
            rarity_lower = (card.rarity or "").lower()
            if rarity_lower == "mythic":
                name_color = rarity_colors.MYTHIC
            elif rarity_lower == "rare":
                name_color = rarity_colors.RARE
            else:
                name_color = ui_colors.WHITE

            mana = prettify_mana(card.mana_cost) if card.mana_cost else ""
            type_icon = CardFormatters.get_type_icon(card.type or "")
            short_type = CardFormatters.get_short_type(card.type or "")

            # Build first line: score bar, synergy icon, name, mana, type
            parts = [f"[{score_color}]{score_bar}[/]", icon, f"[bold {name_color}]{card.name}[/]"]
            if mana:
                parts.append(mana)
            if type_icon:
                parts.append(f"[dim]{type_icon} {short_type}[/]")

            # Add stats (P/T or loyalty)
            stats = self._get_card_stats(card)
            if stats:
                parts.append(f"[dim]{stats}[/]")

            # Add price
            price = self._get_card_price(card)
            if price:
                parts.append(f"[dim]{price}[/]")

            lines = ["  ".join(parts)]
            if reason:
                lines.append(f"    [dim italic]{reason}[/]")

            results_list.append(ListItem(Label("\n".join(lines))))

        self._update_pagination_header()

        if self._current_results:
            results_list.focus()
            results_list.index = 0

    def _update_pagination_header(self) -> None:
        """Update the pagination header display."""
        header = self.query_one("#results-header", Static)

        if not self._pagination or self._pagination.total_items == 0:
            title = "🔍 Synergies" if self._synergy_mode else "🔍 Results"
            header.update(f"[bold {ui_colors.GOLD}]{title} (0)[/]")
            return

        p = self._pagination
        icon = "🔗" if self._synergy_mode else "🔍"

        if p.total_pages <= 1:
            # Single page: show full title with source query
            title = f"Synergies for {p.source_query}" if self._synergy_mode else "Results"
            header.update(f"[bold {ui_colors.GOLD}]{icon} {title} ({p.total_items})[/]")
        else:
            # Multiple pages: use short title to fit controls
            title = "Synergies" if self._synergy_mode else "Results"
            info = f"{p.start_index}-{p.end_index} of {p.total_items}"
            position = f"Page {p.current_page}/{p.total_pages}"
            controls = "n:Next p:Prev g:GoTo"

            if p.is_loading:
                position = "[yellow]Loading...[/]"
                controls = ""

            text = f"[bold {ui_colors.GOLD}]{icon} {title}: {info}[/]  [{ui_colors.GRAY_LIGHT}]{position}[/]"
            if controls:
                text += f"  [dim]{controls}[/]"
            header.update(text)

    @work
    async def _prefetch_next_page(self) -> None:
        """Prefetch the next page in background for faster navigation."""
        if not self._pagination or not self._db:
            return

        next_page = self._pagination.current_page + 1
        if next_page > self._pagination.total_pages:
            return

        # Already cached?
        if self._pagination.get_cached_details(next_page) is not None:
            return

        # Get items for next page
        start = (next_page - 1) * self._pagination.page_size
        end = start + self._pagination.page_size
        next_items = self._pagination.all_items[start:end]

        details: list[CardDetail] = []
        for item in next_items:
            try:
                name = item.name if hasattr(item, "name") else str(item)
                detail = await cards.get_card(self._db, self._scryfall, name=name)
                details.append(detail)
            except CardNotFoundError:
                pass

        self._pagination.cache_details(next_page, details)

    def _format_result_line(self, card: Any) -> str:
        """Format a search result line with enhanced typography.

        Format: [Name]  [Mana]  [Icon Type]  [#Rank]  [Stats]  [Price]
        """
        rarity_lower = (card.rarity or "").lower()
        if rarity_lower == "mythic":
            name_color = rarity_colors.MYTHIC
        elif rarity_lower == "rare":
            name_color = rarity_colors.RARE
        else:
            name_color = ui_colors.WHITE

        mana = prettify_mana(card.mana_cost) if card.mana_cost else ""
        type_icon = CardFormatters.get_type_icon(card.type or "")

        parts = [f"[bold {name_color}]{card.name}[/]"]
        if mana:
            parts.append(f"{mana}")
        if type_icon:
            parts.append(f"[dim]{type_icon} {CardFormatters.get_short_type(card.type or '')}[/]")

        # EDHREC rank
        if hasattr(card, "edhrec_rank") and card.edhrec_rank is not None:
            parts.append(f"[dim]#{card.edhrec_rank} \u2605[/]")

        # Stats: P/T for creatures, loyalty for planeswalkers
        stats = self._get_card_stats(card)
        if stats:
            parts.append(f"[dim]{stats}[/]")

        # Price
        price = self._get_card_price(card)
        if price:
            parts.append(f"[dim]{price}[/]")

        return "  ".join(parts)

    def _get_card_stats(self, card: Any) -> str:
        """Get power/toughness or loyalty for card."""
        type_lower = (card.type or "").lower()
        if "creature" in type_lower:
            power = getattr(card, "power", None)
            toughness = getattr(card, "toughness", None)
            if power is not None and toughness is not None:
                return f"{power}/{toughness}"
        elif "planeswalker" in type_lower:
            loyalty = getattr(card, "loyalty", None)
            if loyalty is not None:
                return f"\u2726{loyalty}"
        return ""

    def _get_card_price(self, card: Any) -> str:
        """Get USD price for card."""
        prices = getattr(card, "prices", None)
        if prices is not None:
            usd = getattr(prices, "usd", None)
            if usd is not None:
                return f"${usd:.2f}"
        return ""
