"""Reusable widgets for the MTG Spellbook TUI."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING, Any

import httpx
from PIL import Image
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import ListView, Static, TabbedContent, TabPane

from mtg_mcp.cli.formatting import prettify_mana
from mtg_mcp.exceptions import CardNotFoundError
from mtg_mcp.tools import cards

# Try to import textual-image for image display
try:
    from textual_image.widget import Image as TImage

    HAS_IMAGE_SUPPORT = True
except ImportError:
    HAS_IMAGE_SUPPORT = False
    TImage = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from mtg_mcp.data.database import MTGDatabase, ScryfallDatabase
    from mtg_mcp.data.models.responses import CardDetail, FindSynergiesResult, PrintingInfo


class CardImageWidget(Static):
    """Widget to display card image or fallback to text."""

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._image_widget: Any = None  # TImage when available

    async def load_image(self, url: str) -> None:
        """Load and display image from URL."""
        self.remove_children()

        if not HAS_IMAGE_SUPPORT:
            self.mount(Static("[dim]Image display not available\n(install textual-image)[/]"))
            return

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                image_data = response.content

            # Load image with PIL
            pil_image = Image.open(BytesIO(image_data))

            # Create textual-image widget
            self._image_widget = TImage(pil_image)
            self.mount(self._image_widget)

        except Exception as e:
            self.mount(Static(f"[red]Failed to load image: {e}[/]"))

    def clear_image(self) -> None:
        """Clear the displayed image."""
        self.remove_children()
        self._image_widget = None


class CardPanel(Vertical):
    """Display card details with tabs for different views."""

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._card: CardDetail | None = None
        self._printings: list[PrintingInfo] = []
        self._current_printing_index: int = 0
        self._card_name_for_art: str = ""

    def compose(self) -> ComposeResult:
        with TabbedContent(id="card-tabs"):
            with TabPane("📖 Card", id="tab-card"):
                yield Static("[dim]Select a card to view details[/]", id="card-text")
            with TabPane("🖼️ Art", id="tab-art"):
                # Yield directly instead of using a custom widget
                yield Static("[dim]Select a card to view art[/]", id="art-info")
                if HAS_IMAGE_SUPPORT:
                    yield TImage(id="art-image")
            with TabPane("📜 Rulings", id="tab-rulings"):
                yield VerticalScroll(Static("[dim]No rulings loaded[/]", id="rulings-text"))
            with TabPane("⚖️ Legal", id="tab-legal"):
                yield Static("[dim]No legality data[/]", id="legal-text")
            with TabPane("💰 Price", id="tab-price"):
                yield Static("[dim]No price data[/]", id="price-text")

    def update_card(self, card: CardDetail | None) -> None:
        """Update the displayed card."""
        self._card = card

        card_text = self.query_one("#card-text", Static)
        if card:
            card_text.update(self._render_card_text(card))
        else:
            card_text.update("[dim]Select a card to view details[/]")

        price_text = self.query_one("#price-text", Static)
        if card and card.prices:
            price_text.update(self._render_prices(card))
        else:
            price_text.update("[dim]No price data available[/]")

    def update_card_with_synergy(
        self, card: CardDetail | None, synergy_info: dict[str, object] | None
    ) -> None:
        """Update the displayed card with synergy information."""
        self._card = card

        card_text = self.query_one("#card-text", Static)
        if card:
            text = self._render_card_text(card)
            # Append synergy info if available
            if synergy_info:
                reason = str(synergy_info.get("reason", ""))
                score_val = synergy_info.get("score", 0)
                score = float(score_val) if isinstance(score_val, (int, float)) else 0.0
                synergy_type = str(synergy_info.get("type", ""))
                score_bar = "●" * int(score * 5) + "○" * (5 - int(score * 5))
                text += f"\n\n[bold cyan]🔗 Synergy:[/] {reason}"
                text += f"\n[dim]Score: [{self._score_color(score)}]{score_bar}[/] · Type: {synergy_type}[/]"
            card_text.update(text)
        else:
            card_text.update("[dim]Select a card to view details[/]")

        price_text = self.query_one("#price-text", Static)
        if card and card.prices:
            price_text.update(self._render_prices(card))
        else:
            price_text.update("[dim]No price data available[/]")

    def _score_color(self, score: float) -> str:
        """Get color for synergy score."""
        if score >= 0.8:
            return "green"
        elif score >= 0.5:
            return "yellow"
        return "dim"

    def _render_card_text(self, card: CardDetail) -> str:
        """Render card as rich text."""
        lines = []

        # Name + mana cost
        mana = prettify_mana(card.mana_cost) if card.mana_cost else ""
        lines.append(f"[bold]{card.name}[/]  {mana}" if mana else f"[bold]{card.name}[/]")
        lines.append(f"[italic dim]{card.type}[/]")
        lines.append("")

        # Rules text
        if card.text:
            text = prettify_mana(card.text).replace("\\n", "\n")
            lines.append(text)
            lines.append("")

        # Flavor text
        if card.flavor:
            flavor = card.flavor.replace("\\n", "\n")
            lines.append(f'[dim italic]"{flavor}"[/]')
            lines.append("")

        # P/T or Loyalty
        if card.power is not None and card.toughness is not None:
            lines.append(f"[bold]{card.power}/{card.toughness}[/]")
        elif card.loyalty is not None:
            lines.append(f"[bold]Loyalty: {card.loyalty}[/]")
        elif card.defense is not None:
            lines.append(f"[bold]Defense: {card.defense}[/]")

        # Footer
        footer_parts = []
        if card.set_code:
            footer_parts.append(f"[cyan]{card.set_code.upper()}[/]")
        if card.rarity:
            rarity_colors = {
                "common": "white",
                "uncommon": "cyan",
                "rare": "yellow",
                "mythic": "red",
            }
            color = rarity_colors.get(card.rarity.lower(), "white")
            footer_parts.append(f"[{color}]{card.rarity.capitalize()}[/]")

        if footer_parts:
            lines.append("")
            lines.append(" · ".join(footer_parts))

        return "\n".join(lines)

    def _render_prices(self, card: CardDetail) -> str:
        """Render price information."""
        lines = [f"[bold]💰 {card.name}[/]", ""]

        if card.prices:
            if card.prices.usd:
                lines.append(f"  USD:      [green]${card.prices.usd:.2f}[/]")
            if card.prices.usd_foil:
                lines.append(f"  Foil:     [yellow]${card.prices.usd_foil:.2f}[/]")
            if card.prices.eur:
                lines.append(f"  EUR:      [green]€{card.prices.eur:.2f}[/]")
        else:
            lines.append("  [dim]No price data available[/]")

        return "\n".join(lines)

    async def load_rulings(self, db: MTGDatabase, card_name: str) -> None:
        """Load and display rulings for a card."""
        rulings_text = self.query_one("#rulings-text", Static)

        try:
            result = await cards.get_card_rulings(db, card_name)
            if result.rulings:
                lines = [f"[bold]📜 {result.count} rulings for {result.card_name}[/]", ""]
                for ruling in result.rulings:
                    lines.append(f"[dim]{ruling.date}[/]")
                    lines.append(f"  {ruling.text}")
                    lines.append("")
                rulings_text.update("\n".join(lines))
            else:
                rulings_text.update(f"[dim]No rulings found for {card_name}[/]")
        except CardNotFoundError:
            rulings_text.update(f"[red]Card not found: {card_name}[/]")

    async def load_legalities(self, db: MTGDatabase, card_name: str) -> None:
        """Load and display format legalities."""
        legal_text = self.query_one("#legal-text", Static)

        try:
            result = await cards.get_card_legalities(db, card_name)
            lines = [f"[bold]⚖️ {result.card_name}[/]", ""]

            formats = [
                "standard",
                "pioneer",
                "modern",
                "legacy",
                "vintage",
                "commander",
                "pauper",
                "brawl",
            ]
            for fmt in formats:
                if fmt in result.legalities:
                    status = result.legalities[fmt]
                    if status == "Legal":
                        icon, style = "✓", "green"
                    elif status == "Banned":
                        icon, style = "✗", "red"
                    else:
                        icon, style = "~", "yellow"
                    lines.append(f"  {icon} [{style}]{fmt.capitalize():12}[/] {status}")

            legal_text.update("\n".join(lines))
        except CardNotFoundError:
            legal_text.update(f"[red]Card not found: {card_name}[/]")

    async def load_printings(
        self, scryfall: ScryfallDatabase | None, card_name: str
    ) -> None:
        """Load all printings for a card into the art tab."""
        from mtg_mcp.tools import images

        art_info = self.query_one("#art-info", Static)

        if not scryfall:
            art_info.update("[yellow]Scryfall database not available[/]")
            return

        try:
            result = await images.get_card_printings(scryfall, card_name)
            if not result.printings:
                art_info.update(f"[yellow]No printings found for {card_name}[/]")
                return

            # Sort by price (highest first)
            self._printings = sorted(
                result.printings,
                key=lambda p: p.price_usd if p.price_usd is not None else -1,
                reverse=True,
            )
            self._current_printing_index = 0
            self._card_name_for_art = card_name
            self._update_art_display()
            await self._load_current_art_image()
        except CardNotFoundError:
            art_info.update(f"[red]Card not found: {card_name}[/]")
        except Exception as e:
            art_info.update(f"[red]Error loading printings: {e}[/]")

    def _update_art_display(self) -> None:
        """Update the art info display for current printing."""
        art_info = self.query_one("#art-info", Static)

        if not self._printings:
            art_info.update("[dim]No printings available[/]")
            return

        printing = self._printings[self._current_printing_index]
        total = len(self._printings)
        idx = self._current_printing_index + 1

        # Build info line
        lines = [f"[bold]{self._card_name_for_art}[/]  [dim]({idx}/{total})[/]"]

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

        art_info.update("\n".join(lines))

    async def _load_current_art_image(self) -> None:
        """Load the image for the current printing."""
        if not HAS_IMAGE_SUPPORT or not self._printings:
            return

        printing = self._printings[self._current_printing_index]
        if not printing.image:
            return

        try:
            img_widget = self.query_one("#art-image", TImage)

            # Use "large" Scryfall image for better quality (if available)
            image_url = printing.image
            # Scryfall URLs: replace "normal" with "large" for higher resolution
            if "normal" in image_url:
                image_url = image_url.replace("normal", "large")

            async with httpx.AsyncClient() as client:
                response = await client.get(image_url, timeout=15.0)
                response.raise_for_status()
                image_data = response.content

            pil_image = Image.open(BytesIO(image_data))

            # Convert to RGB if necessary (some images may be RGBA or palette)
            if pil_image.mode not in ("RGB", "L"):
                pil_image = pil_image.convert("RGB")

            img_widget.image = pil_image

        except Exception:
            pass  # Silently fail for images

    def next_printing(self) -> bool:
        """Move to next printing. Returns True if moved."""
        if not self._printings or self._current_printing_index >= len(self._printings) - 1:
            return False
        self._current_printing_index += 1
        self._update_art_display()
        return True

    def prev_printing(self) -> bool:
        """Move to previous printing. Returns True if moved."""
        if not self._printings or self._current_printing_index <= 0:
            return False
        self._current_printing_index -= 1
        self._update_art_display()
        return True

    async def load_next_art(self) -> None:
        """Navigate to next printing and load image."""
        if self.next_printing():
            await self._load_current_art_image()

    async def load_prev_art(self) -> None:
        """Navigate to previous printing and load image."""
        if self.prev_printing():
            await self._load_current_art_image()


class SynergyPanel(Vertical):
    """Display source card when viewing synergies."""

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._source_card: CardDetail | None = None

    def compose(self) -> ComposeResult:
        yield Static("[dim]Use 'synergy <card>' to find synergistic cards[/]", id="synergy-content")

    def show_source_card(self, card: CardDetail) -> None:
        """Display the source card that synergies are based on."""
        self._source_card = card
        content = self.query_one("#synergy-content", Static)

        lines = [
            "[bold cyan]🎯 Source Card[/]",
            "",
        ]

        # Name + mana cost
        mana = prettify_mana(card.mana_cost) if card.mana_cost else ""
        lines.append(f"[bold]{card.name}[/]  {mana}" if mana else f"[bold]{card.name}[/]")
        lines.append(f"[italic dim]{card.type}[/]")
        lines.append("")

        # Rules text (truncated for panel)
        if card.text:
            text = prettify_mana(card.text).replace("\\n", "\n")
            # Truncate long text
            if len(text) > 300:
                text = text[:297] + "..."
            lines.append(text)
            lines.append("")

        # P/T or Loyalty
        if card.power is not None and card.toughness is not None:
            lines.append(f"[bold]{card.power}/{card.toughness}[/]")
        elif card.loyalty is not None:
            lines.append(f"[bold]Loyalty: {card.loyalty}[/]")
        elif card.defense is not None:
            lines.append(f"[bold]Defense: {card.defense}[/]")

        # Footer
        footer_parts = []
        if card.set_code:
            footer_parts.append(f"[cyan]{card.set_code.upper()}[/]")
        if card.rarity:
            rarity_colors = {
                "common": "white",
                "uncommon": "cyan",
                "rare": "yellow",
                "mythic": "red",
            }
            color = rarity_colors.get(card.rarity.lower(), "white")
            footer_parts.append(f"[{color}]{card.rarity.capitalize()}[/]")

        if footer_parts:
            lines.append("")
            lines.append(" · ".join(footer_parts))

        content.update("\n".join(lines))

    def clear_source(self) -> None:
        """Clear the source card display."""
        self._source_card = None
        content = self.query_one("#synergy-content", Static)
        content.update("[dim]Use 'synergy <card>' to find synergistic cards[/]")

    def update_synergies(self, result: FindSynergiesResult) -> None:
        """Update displayed synergies (legacy method for combos display)."""
        content = self.query_one("#synergy-content", Static)

        if not result.synergies:
            content.update(f"[dim]No synergies found for {result.card_name}[/]")
            return

        lines = [
            f"[bold]🔗 Synergies for {result.card_name}[/] ({result.total_found} found)",
            "",
        ]

        type_icons = {
            "keyword": "🔑",
            "tribal": "👥",
            "ability": "✨",
            "theme": "🎯",
            "archetype": "🏛️",
        }

        for syn in result.synergies[:20]:
            icon = type_icons.get(syn.synergy_type, "•")
            mana = f" {prettify_mana(syn.mana_cost)}" if syn.mana_cost else ""
            score_bar = "●" * int(syn.score * 5) + "○" * (5 - int(syn.score * 5))
            lines.append(
                f"  [{self._score_color(syn.score)}]{score_bar}[/] "
                f"{icon} [cyan]{syn.name}[/]{mana}"
            )
            lines.append(f"         [dim]{syn.reason}[/]")

        content.update("\n".join(lines))

    def _score_color(self, score: float) -> str:
        if score >= 0.8:
            return "green"
        elif score >= 0.5:
            return "yellow"
        return "dim"


class ResultsList(ListView):
    """List of search results with keyboard navigation."""

    pass
