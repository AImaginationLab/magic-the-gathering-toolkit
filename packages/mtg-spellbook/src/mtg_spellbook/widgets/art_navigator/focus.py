"""Focus view component for immersive single-card artwork display."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import Static

from ...formatting import prettify_mana
from ...ui.theme import card_type_colors, get_price_color, rarity_colors, ui_colors
from . import HAS_IMAGE_SUPPORT, TImage
from .image_loader import load_image_from_url
from .messages import ArtistSelected

if TYPE_CHECKING:
    from mtg_core.data.models.responses import PrintingInfo


class FocusView(Vertical, can_focus=True):
    """Immersive single-card view with maximized image and rich metadata."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("e", "browse_artist", "Explore Artist", show=True),
    ]

    show_art_crop: reactive[bool] = reactive(False)

    # Keywords data cache (class-level, loaded once)
    _keywords_data: ClassVar[list[dict[str, Any]] | None] = None

    def __init__(
        self,
        card_name: str,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._card_name = card_name
        self._flavor_name: str | None = None
        self._printings: list[PrintingInfo] = []
        self._current_index: int = 0
        self._legalities: dict[str, str] = {}
        self._load_keywords_data()

    def compose(self) -> ComposeResult:
        """Build focus view layout."""
        with Horizontal(classes="focus-main-container"):
            with Vertical(classes="focus-image-container"):
                if HAS_IMAGE_SUPPORT:
                    yield TImage(id="focus-image", classes="focus-image")
                else:
                    yield Static(
                        "[dim]Image display not available[/]",
                        classes="focus-no-image",
                    )

            with VerticalScroll(classes="focus-metadata", id="focus-metadata"):
                yield Static("", id="focus-card-name", classes="focus-card-name")
                yield Static("", id="focus-mana-cost", classes="focus-mana-cost")
                yield Static("", id="focus-type-line", classes="focus-type-line")
                yield Static("", id="focus-set-info", classes="focus-set-info")
                yield Static("", id="focus-artist", classes="focus-artist")
                yield Static("", id="focus-oracle-text", classes="focus-oracle-text")
                yield Static("", id="focus-flavor", classes="focus-flavor")
                yield Static("", id="focus-keywords", classes="focus-keywords")
                yield Static("", id="focus-limited-stats", classes="focus-limited-stats")
                yield Static("", id="focus-legalities", classes="focus-legalities")
                yield Static("", id="focus-prices", classes="focus-prices")
                yield Static("", id="focus-nav-counter", classes="focus-nav-counter")

        # Status bar is now handled by parent EnhancedArtNavigator (QW1)

    async def load_printings(
        self,
        card_name: str,
        printings: list[PrintingInfo],
        flavor_name: str | None = None,
        start_index: int = 0,
    ) -> None:
        """Load printings into focus view."""
        self._card_name = card_name
        self._flavor_name = flavor_name
        self._printings = printings
        self._current_index = min(start_index, len(printings) - 1) if printings else 0

        if printings:
            await self._update_display()

    def set_legalities(self, legalities: dict[str, str]) -> None:
        """Set legalities data for display."""
        self._legalities = legalities
        # Update display if we have printings loaded
        if self._printings:
            self._update_legalities_display()

    async def sync_to_index(self, index: int) -> None:
        """Sync focus view to a specific printing index."""
        if 0 <= index < len(self._printings):
            self._current_index = index
            await self._update_display()

    async def navigate(self, direction: str) -> None:
        """Navigate to prev/next printing."""
        if not self._printings:
            return

        if direction == "prev":
            if self._current_index > 0:
                self._current_index -= 1
                await self._update_display()
            else:
                self.notify("First printing", severity="warning", timeout=1.5)
        elif direction == "next":
            if self._current_index < len(self._printings) - 1:
                self._current_index += 1
                await self._update_display()
            else:
                self.notify("Last printing", severity="warning", timeout=1.5)

    def get_current_printing(self) -> PrintingInfo | None:
        """Get the currently displayed printing."""
        if 0 <= self._current_index < len(self._printings):
            return self._printings[self._current_index]
        return None

    def watch_show_art_crop(self) -> None:
        """Reload image when art crop mode changes."""
        if self._printings:
            self.run_worker(self._update_display())

    async def _update_display(self) -> None:
        """Update all display elements for current printing."""
        if not self._printings:
            return

        printing = self._printings[self._current_index]
        total = len(self._printings)
        index = self._current_index

        # Update card name - show flavor name as primary if present
        name_widget = self.query_one("#focus-card-name", Static)
        if self._flavor_name:
            name_widget.update(
                f"[bold {ui_colors.GOLD}]{self._flavor_name}[/]\n[dim]{self._card_name}[/]"
            )
        else:
            name_widget.update(f"[bold {ui_colors.GOLD}]{self._card_name}[/]")

        # Update mana cost (prettified)
        mana_widget = self.query_one("#focus-mana-cost", Static)
        if printing.mana_cost:
            pretty_mana = prettify_mana(printing.mana_cost)
            mana_widget.update(pretty_mana)
        else:
            mana_widget.update("")

        # Update type line with color and stats
        self._update_type_display(printing)

        # Update set info
        self._update_set_info(printing)

        # Update artist
        artist_widget = self.query_one("#focus-artist", Static)
        if printing.artist:
            artist_widget.update(f"🎨 [italic underline {ui_colors.GOLD}]{printing.artist}[/]")
        else:
            artist_widget.update("")

        # Update oracle text (prettified mana symbols)
        oracle_widget = self.query_one("#focus-oracle-text", Static)
        if printing.oracle_text and not self.show_art_crop:
            pretty_text = prettify_mana(printing.oracle_text).replace("\\n", "\n")
            oracle_widget.update(pretty_text)
        else:
            oracle_widget.update("")

        # Update flavor text
        flavor_widget = self.query_one("#focus-flavor", Static)
        if printing.flavor_text and not self.show_art_crop:
            flavor_widget.update(f'[dim italic]"{printing.flavor_text}"[/]')
        else:
            flavor_widget.update("")

        # Update keyword explanations (always shown)
        self._update_keywords_display(printing)

        # Update gameplay stats (limited data)
        self._update_limited_stats(printing)

        # Update legalities
        self._update_legalities_display()

        # Update prices
        self._update_prices(printing)

        # Update navigation counter
        counter_widget = self.query_one("#focus-nav-counter", Static)
        counter_widget.update(f"[dim]Printing {index + 1} of {total}[/]")

        # Load image
        image_url = printing.art_crop if self.show_art_crop else printing.image
        if image_url:
            self._load_image(image_url)

    def _update_type_display(self, printing: PrintingInfo) -> None:
        """Update type line with color coding and stats."""
        type_widget = self.query_one("#focus-type-line", Static)

        if not printing.type_line:
            type_widget.update("")
            return

        type_color = self._get_type_color(printing.type_line)
        type_text = f"[{type_color}]{printing.type_line}[/]"

        # Add stats if present
        if printing.power and printing.toughness:
            type_text += f"  [{ui_colors.GOLD_DIM}]⚔ {printing.power}/{printing.toughness}[/]"
        elif printing.loyalty:
            type_text += f"  [{ui_colors.GOLD_DIM}]✦ {printing.loyalty}[/]"

        type_widget.update(type_text)

    def _update_set_info(self, printing: PrintingInfo) -> None:
        """Update set information display."""
        set_info_widget = self.query_one("#focus-set-info", Static)
        set_parts = []

        if printing.set_code:
            set_parts.append(f"[cyan]📦 {printing.set_code.upper()}[/]")
        if printing.collector_number:
            set_parts.append(f"[dim]#{printing.collector_number}[/]")
        if printing.release_date:
            year = printing.release_date[:4] if len(printing.release_date) >= 4 else ""
            if year:
                set_parts.append(f"[dim]{year}[/]")
        if printing.rarity:
            rarity_icon, rarity_color = self._get_rarity_style(printing.rarity)
            set_parts.append(f"[{rarity_color}]{rarity_icon} {printing.rarity.capitalize()}[/]")

        set_info_widget.update(" · ".join(set_parts) if set_parts else "[dim]Unknown set[/]")

    def _update_legalities_display(self) -> None:
        """Update legalities section."""
        legalities_widget = self.query_one("#focus-legalities", Static)

        if not self._legalities:
            legalities_widget.update("")
            return

        # Key formats to show
        key_formats = [
            ("commander", "CMD"),
            ("standard", "STD"),
            ("modern", "MOD"),
            ("legacy", "LEG"),
            ("pioneer", "PIO"),
        ]

        parts = []
        for fmt, abbrev in key_formats:
            if fmt in self._legalities:
                status = self._legalities[fmt].lower()
                if status == "legal":
                    parts.append(f"[green]✓{abbrev}[/]")
                elif status == "banned":
                    parts.append(f"[red]✗{abbrev}[/]")
                elif status == "restricted":
                    parts.append(f"[yellow]⚠{abbrev}[/]")
                else:
                    parts.append(f"[dim]○{abbrev}[/]")

        if parts:
            legalities_widget.update("  ".join(parts))
        else:
            legalities_widget.update("")

    def _update_prices(self, printing: PrintingInfo) -> None:
        """Update prices display."""
        prices_widget = self.query_one("#focus-prices", Static)
        price_parts = []

        if printing.price_usd is not None:
            price_color = get_price_color(printing.price_usd)
            price_parts.append(f"[{price_color}]${printing.price_usd:.2f}[/]")
        if printing.price_usd_foil is not None:
            price_parts.append(f"[yellow]${printing.price_usd_foil:.2f} ✨[/]")
        if printing.price_eur is not None:
            price_parts.append(f"[dim]€{printing.price_eur:.2f}[/]")

        if price_parts:
            prices_widget.update("💰 " + "  ".join(price_parts))
        else:
            prices_widget.update("[dim]No price data[/]")

    def _update_limited_stats(self, printing: PrintingInfo) -> None:
        """Update 17Lands limited stats display."""
        stats_widget = self.query_one("#focus-limited-stats", Static)

        try:
            from mtg_core.tools.recommendations.gameplay import GameplayDB

            db = GameplayDB()
            if not db.is_available:
                stats_widget.update("")
                return

            # Try to get stats for specific set, fallback to any set
            stats = db.get_card_stats(self._card_name, printing.set_code)
            if not stats:
                stats = db.get_card_stats(self._card_name)

            if not stats:
                stats_widget.update("")
                return

            # Build the display
            lines = []

            # Header with tier badge
            tier = stats.tier.upper() if stats.tier else "?"
            tier_colors = {
                "S": "#FFD700",  # Gold
                "A": "#50FA7B",  # Green
                "B": "#8BE9FD",  # Cyan
                "C": "#F1FA8C",  # Yellow
                "D": "#FFB86C",  # Orange
                "F": "#FF5555",  # Red
            }
            tier_color = tier_colors.get(tier, "#888")

            # Tier badge with visual styling
            lines.append(f"[bold]📊 GAMEPLAY DATA[/]  [{tier_color} on #1a1a1a] {tier}-TIER [/]")

            # Stats row with visual bars
            stat_parts = []

            # GIH Win Rate (most important stat)
            if stats.gih_wr is not None:
                wr_pct = stats.gih_wr * 100
                # Color based on win rate (50% is baseline)
                if wr_pct >= 60:
                    wr_color = "#50FA7B"  # Green - excellent
                elif wr_pct >= 55:
                    wr_color = "#8BE9FD"  # Cyan - good
                elif wr_pct >= 50:
                    wr_color = "#F1FA8C"  # Yellow - average
                else:
                    wr_color = "#FF5555"  # Red - below average

                # Visual bar (10 chars = 20 percentage points, centered on 50%)
                bar_len = 10
                filled = max(0, min(bar_len, int((wr_pct - 40) / 2)))
                bar = f"[{wr_color}]{'█' * filled}[/][dim]{'░' * (bar_len - filled)}[/]"

                stat_parts.append(f"GIH WR: [{wr_color}]{wr_pct:.1f}%[/] {bar}")

            # IWD (Improvement When Drawn)
            if stats.iwd is not None:
                iwd_pct = stats.iwd * 100
                if iwd_pct >= 5:
                    iwd_color = "#50FA7B"
                    iwd_icon = "▲"
                elif iwd_pct >= 0:
                    iwd_color = "#F1FA8C"
                    iwd_icon = "▲"
                else:
                    iwd_color = "#FF5555"
                    iwd_icon = "▼"
                stat_parts.append(f"IWD: [{iwd_color}]{iwd_icon}{abs(iwd_pct):.1f}pp[/]")

            # Opening Hand Win Rate
            if stats.oh_wr is not None:
                oh_pct = stats.oh_wr * 100
                if oh_pct >= 60:
                    oh_color = "#50FA7B"
                elif oh_pct >= 55:
                    oh_color = "#8BE9FD"
                elif oh_pct >= 50:
                    oh_color = "#F1FA8C"
                else:
                    oh_color = "#FF5555"
                stat_parts.append(f"OH WR: [{oh_color}]{oh_pct:.1f}%[/]")

            # Games sample size
            if stats.games_in_hand:
                games_str = (
                    f"{stats.games_in_hand:,}"
                    if stats.games_in_hand >= 1000
                    else str(stats.games_in_hand)
                )
                stat_parts.append(f"[dim]({games_str} games)[/]")

            if stat_parts:
                lines.append("  ".join(stat_parts[:2]))  # First row: GIH WR
                if len(stat_parts) > 2:
                    lines.append("  ".join(stat_parts[2:]))  # Second row: IWD, OH WR, games

            stats_widget.update("\n".join(lines))

        except Exception:
            stats_widget.update("")

    def _get_type_color(self, type_line: str) -> str:
        """Get color based on card type."""
        type_lower = type_line.lower()
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

    def _get_rarity_style(self, rarity: str) -> tuple[str, str]:
        """Get icon and color for rarity."""
        rarity_styles = {
            "common": ("●", rarity_colors.COMMON),
            "uncommon": ("◆", rarity_colors.UNCOMMON),
            "rare": ("♦", rarity_colors.RARE),
            "mythic": ("★", rarity_colors.MYTHIC),
        }
        return rarity_styles.get(rarity.lower(), ("○", rarity_colors.DEFAULT))

    @work
    async def _load_image(self, image_url: str) -> None:
        """Load and display the card image."""
        if not HAS_IMAGE_SUPPORT:
            return

        try:
            img_widget = self.query_one("#focus-image", TImage)
            use_large = not self.show_art_crop
            await load_image_from_url(image_url, img_widget, use_large=use_large)
        except NoMatches:
            pass

    def action_browse_artist(self) -> None:
        """Browse other cards by the current artist."""
        printing = self.get_current_printing()
        if printing and printing.artist:
            self.post_message(ArtistSelected(printing.artist, self._card_name))
        else:
            self.notify("No artist information available", severity="warning", timeout=2)

    @classmethod
    def _load_keywords_data(cls) -> None:
        """Load keywords data from JSON file (cached at class level)."""
        if cls._keywords_data is not None:
            return

        keywords_path = Path(__file__).parent.parent.parent / "data" / "keywords.json"
        if keywords_path.exists():
            try:
                data = json.loads(keywords_path.read_text())
                cls._keywords_data = data.get("keywords", [])
            except Exception:
                cls._keywords_data = []
        else:
            cls._keywords_data = []

    def _find_keywords_in_text(self, text: str) -> list[dict[str, Any]]:
        """Find keywords present in the card text."""
        if not self._keywords_data or not text:
            return []

        found = []
        text_lower = text.lower()

        for kw in self._keywords_data:
            kw_name = kw.get("name", "").lower()
            if not kw_name:
                continue

            # Check for keyword in text (whole word match)
            pattern = r"\b" + re.escape(kw_name) + r"\b"
            if re.search(pattern, text_lower):
                found.append(kw)

        return found

    def _update_keywords_display(self, printing: PrintingInfo) -> None:
        """Update the keywords explanation section."""
        try:
            keywords_widget = self.query_one("#focus-keywords", Static)
        except NoMatches:
            return

        if not printing.oracle_text:
            keywords_widget.update("")
            return

        # Find keywords in oracle text and type line
        found = self._find_keywords_in_text(printing.oracle_text)
        if printing.type_line:
            type_keywords = self._find_keywords_in_text(printing.type_line)
            # Deduplicate
            found_names = {k["name"] for k in found}
            for kw in type_keywords:
                if kw["name"] not in found_names:
                    found.append(kw)

        if not found:
            keywords_widget.update("")
            return

        # Build formatted output - compact style (text will wrap naturally)
        lines = [f"[bold {ui_colors.GOLD}]📖 Keywords[/]"]
        for kw in found:
            name = kw.get("name", "")
            summary = kw.get("summary", "")
            if summary:
                lines.append(f"  [yellow]{name}[/]: {summary}")
            else:
                lines.append(f"  [yellow]{name}[/]")

        keywords_widget.update("\n".join(lines))
