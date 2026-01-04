"""Collection statistics panel with visualizations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from ..ui.theme import ui_colors

if TYPE_CHECKING:
    from ..collection_manager import CollectionCardWithData, CollectionStats


# Mana color display configuration
MANA_COLORS = {
    "W": {"bg": "#F0E68C", "fg": "black", "name": "White", "symbol": "☀"},
    "U": {"bg": "#0E86D4", "fg": "white", "name": "Blue", "symbol": "💧"},
    "B": {"bg": "#6B5B7B", "fg": "white", "name": "Black", "symbol": "💀"},
    "R": {"bg": "#C7253E", "fg": "white", "name": "Red", "symbol": "🔥"},
    "G": {"bg": "#1A5D1A", "fg": "white", "name": "Green", "symbol": "🌲"},
    "C": {"bg": "#95a5a6", "fg": "black", "name": "Colorless", "symbol": "◇"},
}

# Card type configuration
TYPE_ICONS = {
    "Creature": ("⚔", "#7ec850"),
    "Instant": ("⚡", "#4a9fd8"),
    "Sorcery": ("🔮", "#4a9fd8"),
    "Artifact": ("⚙", "#9a9a9a"),
    "Enchantment": ("✨", "#b86fce"),
    "Planeswalker": ("🌟", "#e6c84a"),
    "Land": ("🏔", "#a67c52"),
    "Other": ("?", "#888888"),
}


class CollectionStatsPanel(Vertical):
    """Collection statistics with visualizations.

    Features:
    - Collection overview (unique, total, foils)
    - Color distribution with mana symbols
    - Card type breakdown
    - Mana curve visualization
    - Value estimate (if prices available)
    """

    DEFAULT_CSS = """
    CollectionStatsPanel {
        width: 100%;
        height: auto;
        padding: 0 1;
        background: #1a1a1a;
    }

    .stats-section {
        height: auto;
        margin-bottom: 1;
    }

    .stats-header {
        text-style: bold;
        margin-bottom: 0;
    }

    .stats-content {
        height: auto;
    }
    """

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._stats: CollectionStats | None = None
        self._cards: list[CollectionCardWithData] = []

    def compose(self) -> ComposeResult:
        # Collection Overview
        with Vertical(classes="stats-section"):
            yield Static(
                f"[bold {ui_colors.GOLD_DIM}]📦 Collection Overview[/]",
                classes="stats-header",
            )
            yield Static("[dim]Loading...[/]", id="collection-overview")

        # Collection Value (requires price data)
        with Vertical(classes="stats-section"):
            yield Static(
                f"[bold {ui_colors.GOLD_DIM}]💰 Collection Value[/]",
                classes="stats-header",
            )
            yield Static("[dim]Calculating...[/]", id="collection-value")

        # Color Distribution
        with Vertical(classes="stats-section"):
            yield Static(
                f"[bold {ui_colors.GOLD_DIM}]🎨 Color Distribution[/]",
                classes="stats-header",
            )
            yield Static("", id="collection-colors")

        # Card Types
        with Vertical(classes="stats-section"):
            yield Static(
                f"[bold {ui_colors.GOLD_DIM}]📋 Card Types[/]",
                classes="stats-header",
            )
            yield Static("", id="collection-types")

        # Mana Curve
        with Vertical(classes="stats-section"):
            yield Static(
                f"[bold {ui_colors.GOLD_DIM}]📈 Mana Curve[/]",
                classes="stats-header",
            )
            yield Static("", id="collection-curve")

        # Availability
        with Vertical(classes="stats-section"):
            yield Static(
                f"[bold {ui_colors.GOLD_DIM}]📊 Availability[/]",
                classes="stats-header",
            )
            yield Static("", id="collection-availability")

        # Rarity Breakdown
        with Vertical(classes="stats-section"):
            yield Static(
                f"[bold {ui_colors.GOLD_DIM}]🏆 Rarity Breakdown[/]",
                classes="stats-header",
            )
            yield Static("", id="collection-rarity")

        # Sets Represented
        with Vertical(classes="stats-section"):
            yield Static(
                f"[bold {ui_colors.GOLD_DIM}]📚 Sets Represented[/]",
                classes="stats-header",
            )
            yield Static("", id="collection-sets")

        # Top Keywords
        with Vertical(classes="stats-section"):
            yield Static(
                f"[bold {ui_colors.GOLD_DIM}]🔑 Top Keywords[/]",
                classes="stats-header",
            )
            yield Static("", id="collection-keywords")

        # Legendaries
        with Vertical(classes="stats-section"):
            yield Static(
                f"[bold {ui_colors.GOLD_DIM}]👑 Legendaries[/]",
                classes="stats-header",
            )
            yield Static("", id="collection-legendaries")

        # Top Artists
        with Vertical(classes="stats-section"):
            yield Static(
                f"[bold {ui_colors.GOLD_DIM}]🎨 Top Artists[/]",
                classes="stats-header",
            )
            yield Static("", id="collection-artists")

        # Quick Stats (averages)
        with Vertical(classes="stats-section"):
            yield Static(
                f"[bold {ui_colors.GOLD_DIM}]📊 Quick Stats[/]",
                classes="stats-header",
            )
            yield Static("", id="collection-quick-stats")

    def update_stats(self, stats: CollectionStats, cards: list[CollectionCardWithData]) -> None:
        """Update the stats display with new data."""
        self._stats = stats
        self._cards = cards
        self._refresh_display()

    def _refresh_display(self) -> None:
        """Refresh all stats displays."""
        if self._stats is None:
            return

        self._update_overview()
        self._update_colors()
        self._update_types()
        self._update_curve()
        self._update_availability()
        self._update_rarity()
        self._update_sets()
        self._update_keywords()
        self._update_legendaries()
        self._update_artists()
        self._update_quick_stats()

    def _update_overview(self) -> None:
        """Update the overview section."""
        if self._stats is None:
            return

        stats = self._stats
        overview = self.query_one("#collection-overview", Static)

        # Calculate in-deck usage
        total_in_decks = sum(c.in_deck_count for c in self._cards)
        total_available = sum(c.available for c in self._cards)

        lines = [
            f"[{ui_colors.GOLD}]{stats.unique_cards:,}[/] [dim]unique cards[/]",
            f"[{ui_colors.GOLD}]{stats.total_cards:,}[/] [dim]total copies[/]",
            f"[#b86fce]{stats.total_foils:,}[/] [dim]foils ✨[/]",
            "",
            f"[#7ec850]{total_available:,}[/] [dim]available[/]",
            f"[#e6c84a]{total_in_decks:,}[/] [dim]in decks[/]",
        ]
        overview.update("\n".join(lines))

    def _update_colors(self) -> None:
        """Update the color distribution section."""
        color_counts: dict[str, int] = dict.fromkeys(MANA_COLORS, 0)

        for card_data in self._cards:
            if card_data.card and card_data.card.colors:
                qty = card_data.total_owned
                for color in card_data.card.colors:
                    if color in color_counts:
                        color_counts[color] += qty
            elif card_data.card:
                # Colorless
                color_counts["C"] += card_data.total_owned

        total = sum(color_counts.values()) or 1
        max_count = max(color_counts.values()) or 1

        lines = []
        for color, info in MANA_COLORS.items():
            count = color_counts[color]
            if count == 0:
                continue
            pct = count * 100 // total
            bar_len = count * 15 // max_count
            bar = "█" * bar_len + "░" * (15 - bar_len)
            lines.append(f"{info['symbol']} [{info['bg']}]{bar}[/] {count:>3} ({pct:>2}%)")

        colors_widget = self.query_one("#collection-colors", Static)
        colors_widget.update("\n".join(lines) if lines else "[dim]No cards[/]")

    def _update_types(self) -> None:
        """Update the card types section."""
        type_counts: dict[str, int] = {}

        for card_data in self._cards:
            if card_data.card and card_data.card.type:
                qty = card_data.total_owned
                type_line = card_data.card.type
                # Extract primary type
                primary_type = "Other"
                for t in TYPE_ICONS:
                    if t in type_line:
                        primary_type = t
                        break
                type_counts[primary_type] = type_counts.get(primary_type, 0) + qty

        total = sum(type_counts.values()) or 1

        lines = []
        for type_name, (icon, color) in TYPE_ICONS.items():
            count = type_counts.get(type_name, 0)
            if count == 0:
                continue
            pct = count * 100 // total
            lines.append(f"{icon} [{color}]{type_name:12}[/] {count:>4} ({pct:>2}%)")

        types_widget = self.query_one("#collection-types", Static)
        types_widget.update("\n".join(lines) if lines else "[dim]No cards[/]")

    def _update_curve(self) -> None:
        """Update the mana curve section."""
        cmc_counts: dict[int, int] = {}

        for card_data in self._cards:
            if card_data.card:
                cmc = int(card_data.card.cmc) if card_data.card.cmc else 0
                cmc = min(cmc, 7)  # Cap at 7+
                qty = card_data.total_owned
                cmc_counts[cmc] = cmc_counts.get(cmc, 0) + qty

        if not cmc_counts:
            curve_widget = self.query_one("#collection-curve", Static)
            curve_widget.update("[dim]No cards[/]")
            return

        max_count = max(cmc_counts.values()) or 1

        # Vertical bar chart
        lines = []
        for cmc in range(8):
            count = cmc_counts.get(cmc, 0)
            bar_len = count * 12 // max_count if max_count > 0 else 0
            bar = "█" * bar_len
            label = f"{cmc}+" if cmc == 7 else str(cmc)
            lines.append(f"[dim]{label}[/] [{ui_colors.GOLD}]{bar:12}[/] {count:>3}")

        curve_widget = self.query_one("#collection-curve", Static)
        curve_widget.update("\n".join(lines))

    def _update_availability(self) -> None:
        """Update the availability section."""
        fully_available = 0
        partially_used = 0
        fully_used = 0

        for card_data in self._cards:
            if card_data.available == card_data.total_owned:
                fully_available += 1
            elif card_data.available > 0:
                partially_used += 1
            else:
                fully_used += 1

        total = len(self._cards) or 1

        lines = [
            f"[#7ec850]●[/] Fully available: {fully_available} ({fully_available * 100 // total}%)",
            f"[#e6c84a]○[/] Partially used:  {partially_used} ({partially_used * 100 // total}%)",
            f"[dim]●[/] Fully in decks:  {fully_used} ({fully_used * 100 // total}%)",
        ]

        avail_widget = self.query_one("#collection-availability", Static)
        avail_widget.update("\n".join(lines))

    def _update_rarity(self) -> None:
        """Update the rarity breakdown section."""
        rarity_config = {
            "mythic": {"color": "#ff8c00", "symbol": "★"},
            "rare": {"color": "#e6c84a", "symbol": "◆"},
            "uncommon": {"color": "#c0c0c0", "symbol": "◇"},
            "common": {"color": "#666", "symbol": "●"},
        }
        rarity_counts: dict[str, int] = {}

        for card_data in self._cards:
            if card_data.card and card_data.card.rarity:
                rarity = card_data.card.rarity.lower()
                qty = card_data.total_owned
                rarity_counts[rarity] = rarity_counts.get(rarity, 0) + qty

        total = sum(rarity_counts.values()) or 1

        lines = []
        for rarity, config in rarity_config.items():
            count = rarity_counts.get(rarity, 0)
            if count == 0:
                continue
            pct = count * 100 // total
            lines.append(
                f"[{config['color']}]{config['symbol']}[/] "
                f"{rarity.title():11} [{config['color']}]{count:>4}[/] ({pct:>2}%)"
            )

        rarity_widget = self.query_one("#collection-rarity", Static)
        rarity_widget.update("\n".join(lines) if lines else "[dim]No cards[/]")

    def _update_sets(self) -> None:
        """Update the sets represented section."""
        set_counts: dict[str, int] = {}

        for card_data in self._cards:
            set_code = card_data.set_code or (card_data.card.set_code if card_data.card else None)
            if set_code:
                qty = card_data.total_owned
                set_counts[set_code.upper()] = set_counts.get(set_code.upper(), 0) + qty

        if not set_counts:
            sets_widget = self.query_one("#collection-sets", Static)
            sets_widget.update("[dim]No cards[/]")
            return

        # Sort by count, get top 5
        sorted_sets = sorted(set_counts.items(), key=lambda x: x[1], reverse=True)
        top_sets = sorted_sets[:5]
        unique_count = len(set_counts)
        total_cards = sum(set_counts.values())

        lines = [
            f"[{ui_colors.GOLD}]{unique_count}[/] [dim]unique sets[/]",
            "",
        ]
        for set_code, count in top_sets:
            pct = count * 100 // total_cards
            lines.append(f"  [{ui_colors.TEXT_DIM}]{set_code:5}[/] {count:>4} ({pct:>2}%)")

        sets_widget = self.query_one("#collection-sets", Static)
        sets_widget.update("\n".join(lines))

    def _update_keywords(self) -> None:
        """Update the top keywords section."""
        keyword_counts: dict[str, int] = {}

        for card_data in self._cards:
            if card_data.card and card_data.card.keywords:
                qty = card_data.total_owned
                for kw in card_data.card.keywords:
                    if kw:
                        keyword_counts[kw] = keyword_counts.get(kw, 0) + qty

        if not keyword_counts:
            kw_widget = self.query_one("#collection-keywords", Static)
            kw_widget.update("[dim]No keywords[/]")
            return

        # Sort by count, get top 6
        sorted_kw = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        top_kw = sorted_kw[:6]

        lines = []
        for keyword, count in top_kw:
            # Truncate long keywords
            display_kw = keyword[:12] + "…" if len(keyword) > 13 else keyword
            lines.append(f"  [{ui_colors.TEXT_DIM}]{display_kw:13}[/] {count:>3}")

        kw_widget = self.query_one("#collection-keywords", Static)
        kw_widget.update("\n".join(lines))

    def _update_legendaries(self) -> None:
        """Update the legendaries section."""
        legendary_creatures = 0
        legendary_other = 0
        potential_commanders: list[tuple[str, str]] = []  # (name, colors)

        for card_data in self._cards:
            if not card_data.card:
                continue

            supertypes = card_data.card.supertypes or []
            if "Legendary" not in supertypes:
                continue

            card_type = card_data.card.type or ""
            colors = card_data.card.color_identity or card_data.card.colors or []
            color_str = "".join(colors) if colors else "C"

            if "Creature" in card_type:
                legendary_creatures += card_data.total_owned
                # Track as potential commander
                potential_commanders.append((card_data.card_name, color_str))
            else:
                legendary_other += card_data.total_owned

        total_legendary = legendary_creatures + legendary_other
        widget = self.query_one("#collection-legendaries", Static)

        if total_legendary == 0:
            widget.update("[dim]No legendaries[/]")
            return

        lines = [
            f"[{ui_colors.GOLD}]{total_legendary}[/] [dim]total legendaries[/]",
            f"  [#7ec850]{legendary_creatures}[/] [dim]creatures[/]",
            f"  [#4a9fd8]{legendary_other}[/] [dim]other[/]",
        ]

        # Show potential commanders count
        if potential_commanders:
            lines.append("")
            lines.append(f"[dim]{len(potential_commanders)} potential commanders[/]")

        widget.update("\n".join(lines))

    def _update_artists(self) -> None:
        """Update the top artists section."""
        artist_counts: dict[str, int] = {}

        for card_data in self._cards:
            if card_data.card and card_data.card.artist:
                artist = card_data.card.artist
                qty = card_data.total_owned
                artist_counts[artist] = artist_counts.get(artist, 0) + qty

        if not artist_counts:
            widget = self.query_one("#collection-artists", Static)
            widget.update("[dim]No artist data[/]")
            return

        # Sort by count, get top 5
        sorted_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)
        top_artists = sorted_artists[:5]
        unique_count = len(artist_counts)

        lines = [f"[{ui_colors.GOLD}]{unique_count}[/] [dim]unique artists[/]", ""]

        for artist, count in top_artists:
            # Truncate long names
            display_name = artist[:14] + "…" if len(artist) > 15 else artist
            lines.append(f"  [{ui_colors.TEXT_DIM}]{display_name:15}[/] {count:>3}")

        widget = self.query_one("#collection-artists", Static)
        widget.update("\n".join(lines))

    def _update_quick_stats(self) -> None:
        """Update the quick stats section with averages."""
        if not self._cards:
            widget = self.query_one("#collection-quick-stats", Static)
            widget.update("[dim]No cards[/]")
            return

        # Calculate averages
        total_cmc = 0.0
        cmc_count = 0
        nonland_count = 0

        for card_data in self._cards:
            if not card_data.card:
                continue

            card_type = card_data.card.type or ""

            # Skip lands for CMC average
            if "Land" not in card_type:
                nonland_count += card_data.total_owned
                if card_data.card.cmc is not None:
                    total_cmc += card_data.card.cmc * card_data.total_owned
                    cmc_count += card_data.total_owned

        avg_cmc = total_cmc / cmc_count if cmc_count > 0 else 0

        # Cards per unique
        total_copies = sum(c.total_owned for c in self._cards)
        avg_copies = total_copies / len(self._cards) if self._cards else 0

        lines = [
            f"[dim]Avg CMC:[/]     [{ui_colors.GOLD}]{avg_cmc:.2f}[/]",
            f"[dim]Avg copies:[/]  [{ui_colors.GOLD}]{avg_copies:.1f}[/]x",
            f"[dim]Non-lands:[/]   [{ui_colors.GOLD}]{nonland_count}[/]",
        ]

        widget = self.query_one("#collection-quick-stats", Static)
        widget.update("\n".join(lines))

    @staticmethod
    def _price_key(card_name: str, set_code: str | None, collector_number: str | None) -> str:
        """Generate a unique key for price lookup."""
        if set_code and collector_number:
            return f"{card_name}|{set_code.upper()}|{collector_number}"
        return card_name

    def update_value(
        self,
        price_data: dict[str, tuple[float | None, float | None]],
        cards: list[CollectionCardWithData] | None = None,
    ) -> None:
        """Update collection value with price data.

        Args:
            price_data: Dict mapping price_key to (usd_price, usd_foil_price) in dollars.
            cards: Optional cards list (uses self._cards if not provided).
        """
        cards_to_use = cards if cards is not None else self._cards
        total_value = 0.0
        # Track single card prices for stats
        all_prices: list[float] = []
        # Track (name, price) for most valuable list
        card_prices: list[tuple[str, float]] = []
        # Price tier counts
        tier_bulk = 0  # $0-1
        tier_playable = 0  # $1-10
        tier_chase = 0  # $10-50
        tier_premium = 0  # $50+

        for card_data in cards_to_use:
            key = self._price_key(
                card_data.card_name, card_data.set_code, card_data.collector_number
            )
            prices = price_data.get(key)
            if not prices:
                continue

            usd_price, foil_price = prices
            card_total = 0.0

            # Regular copies
            if usd_price and card_data.quantity > 0:
                card_total += usd_price * card_data.quantity

            # Foil copies
            if card_data.foil_quantity > 0:
                foil = foil_price if foil_price else usd_price
                if foil:
                    card_total += foil * card_data.foil_quantity

            if card_total > 0:
                total_value += card_total
                single_price = usd_price if usd_price else (foil_price or 0.0)
                if single_price > 0:
                    all_prices.append(single_price)
                    card_prices.append((card_data.card_name, single_price))
                    # Categorize into price tiers
                    if single_price >= 50:
                        tier_premium += 1
                    elif single_price >= 10:
                        tier_chase += 1
                    elif single_price >= 1:
                        tier_playable += 1
                    else:
                        tier_bulk += 1

        # Update value display
        value_widget = self.query_one("#collection-value", Static)

        if total_value == 0:
            value_widget.update("[dim]No price data[/]")
            return

        # Calculate median
        all_prices.sort()
        median_price = 0.0
        if all_prices:
            mid = len(all_prices) // 2
            if len(all_prices) % 2 == 0:
                median_price = (all_prices[mid - 1] + all_prices[mid]) / 2
            else:
                median_price = all_prices[mid]

        # Calculate top 5 concentration
        card_prices.sort(key=lambda x: x[1], reverse=True)
        top5_value = sum(p for _, p in card_prices[:5])
        top5_pct = (top5_value / total_value * 100) if total_value > 0 else 0

        # Build display lines
        lines = [
            f"[bold {ui_colors.GOLD}]${total_value:,.2f}[/] [dim]USD[/]",
            f"[dim]Median:[/] [{ui_colors.GOLD}]${median_price:.2f}[/]  "
            f"[dim]Top 5 =[/] [{ui_colors.GOLD}]{top5_pct:.0f}%[/]",
        ]

        # Price tier breakdown
        total_cards = tier_bulk + tier_playable + tier_chase + tier_premium
        if total_cards > 0:
            lines.append("")
            lines.append("[dim]Price Tiers:[/]")
            if tier_premium > 0:
                lines.append(
                    f"  [#ff8c00]★[/] Premium ($50+)    [{ui_colors.GOLD}]{tier_premium:>3}[/]"
                )
            if tier_chase > 0:
                lines.append(
                    f"  [#e6c84a]◆[/] Chase ($10-50)    [{ui_colors.GOLD}]{tier_chase:>3}[/]"
                )
            if tier_playable > 0:
                lines.append(
                    f"  [#c0c0c0]◇[/] Playable ($1-10)  [{ui_colors.GOLD}]{tier_playable:>3}[/]"
                )
            if tier_bulk > 0:
                lines.append(f"  [#666]●[/] Bulk (<$1)        [{ui_colors.GOLD}]{tier_bulk:>3}[/]")

        # Most valuable cards (top 5)
        if card_prices:
            top_cards = card_prices[:5]
            lines.append("")
            lines.append("[dim]Most Valuable:[/]")
            for name, price in top_cards:
                display_name = name[:16] + "…" if len(name) > 17 else name
                lines.append(
                    f"  [{ui_colors.TEXT_DIM}]{display_name:17}[/] [#7ec850]${price:.2f}[/]"
                )

        value_widget.update("\n".join(lines))
