"""Card panel widget for displaying card details."""

from __future__ import annotations

import contextlib
import re
from io import BytesIO
from typing import TYPE_CHECKING

import httpx
from PIL import Image
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.events import Key
from textual.widgets import Static, TabbedContent, TabPane

from mtg_core.exceptions import CardNotFoundError
from mtg_core.tools import cards

from ..formatting import prettify_mana
from .art_navigator import HAS_IMAGE_SUPPORT, ArtNavigator

if HAS_IMAGE_SUPPORT:
    from textual_image.widget import Image as TImage

if TYPE_CHECKING:
    from mtg_core.data.database import MTGDatabase, ScryfallDatabase
    from mtg_core.data.models.responses import CardDetail, PrintingInfo


class CardPanel(Vertical):
    """Display card details with tabs for different views."""

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._card: CardDetail | None = None
        self._printings: list[PrintingInfo] = []
        self._current_printing_index: int = 0
        self._card_name_for_art: str = ""
        self._id_prefix = id or "card-panel"

    def _child_id(self, name: str) -> str:
        """Generate a unique child widget ID based on panel's ID."""
        return f"{self._id_prefix}-{name}"

    def get_child_name(self, name: str) -> str:
        """Get the child widget ID without selector (for setting active tabs, etc.)."""
        return self._child_id(name)

    def get_child_id(self, name: str) -> str:
        """Get the full CSS selector for a child widget (for queries)."""
        return f"#{self._child_id(name)}"

    def compose(self) -> ComposeResult:
        with TabbedContent(id=self._child_id("tabs")):
            with TabPane("📖 Card", id=self._child_id("tab-card"), classes="-tab-card"):
                yield Static(
                    "[dim]Select a card to view details[/]",
                    id=self._child_id("card-text"),
                    classes="-card-text",
                )
            with TabPane("🖼️ Art", id=self._child_id("tab-art"), classes="-tab-art"):
                yield ArtNavigator(
                    self._id_prefix,
                    id=self._child_id("art-navigator"),
                    classes="-art-navigator",
                )
            with TabPane("📜 Rulings", id=self._child_id("tab-rulings"), classes="-tab-rulings"):
                yield VerticalScroll(
                    Static(
                        "[dim]No rulings loaded[/]",
                        id=self._child_id("rulings-text"),
                        classes="-rulings-text",
                    )
                )
            with TabPane("⚖️ Legal", id=self._child_id("tab-legal"), classes="-tab-legal"):
                yield Static(
                    "[dim]No legality data[/]",
                    id=self._child_id("legal-text"),
                    classes="-legal-text",
                )
            with TabPane("💰 Price", id=self._child_id("tab-price"), classes="-tab-price"):
                yield Static(
                    "[dim]No price data[/]",
                    id=self._child_id("price-text"),
                    classes="-price-text",
                )

    def on_mount(self) -> None:
        """Set up panel reference in ArtNavigator after mount."""
        try:
            art_nav = self.query_one(f"#{self._child_id('art-navigator')}", ArtNavigator)
            art_nav.set_panel(self)
        except Exception:
            pass

    def on_key(self, event: Key) -> None:
        """Handle key events - down arrow focuses art navigator when on art tab."""
        if event.key == "down" and self.focus_art_navigator():
            event.stop()

    def focus_art_navigator(self) -> bool:
        """Focus the art navigator if on the art tab. Returns True if focused."""
        try:
            tabs = self.query_one(f"#{self._child_id('tabs')}", TabbedContent)
            if tabs.active == self._child_id("tab-art"):
                art_nav = self.query_one(f"#{self._child_id('art-navigator')}", ArtNavigator)
                art_nav.focus()
                return True
        except Exception:
            pass
        return False

    def show_loading(self, message: str = "Loading card details...") -> None:
        """Show loading indicator on card panel."""
        card_text = self.query_one(f"#{self._child_id('card-text')}", Static)
        card_text.update(f"[dim #c9a227]✦ {message}[/]")

    def show_art_loading(self) -> None:
        """Show art loading indicator."""
        try:
            art_info = self.query_one(f"#{self._child_id('art-info')}", Static)
            art_info.update("[dim #c9a227]🎨 Loading artwork...[/]")
        except Exception:
            pass

    def update_card(self, card: CardDetail | None) -> None:
        """Update the displayed card."""
        self._card = card

        card_text = self.query_one(f"#{self._child_id('card-text')}", Static)
        if card:
            card_text.update(self._render_card_text(card))
            # Update panel border based on rarity
            self._update_rarity_border(card)
        else:
            card_text.update("[dim]Select a card to view details[/]")
            self._reset_border()

        price_text = self.query_one(f"#{self._child_id('price-text')}", Static)
        if card and card.prices:
            price_text.update(self._render_prices(card))
        else:
            price_text.update("[dim]No price data available[/]")

    def update_card_with_synergy(
        self, card: CardDetail | None, synergy_info: dict[str, object] | None
    ) -> None:
        """Update the displayed card with synergy information."""
        self._card = card

        card_text = self.query_one(f"#{self._child_id('card-text')}", Static)
        if card:
            text = self._render_card_text(card)
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

        price_text = self.query_one(f"#{self._child_id('price-text')}", Static)
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
        """Render card as rich text with enhanced typography."""
        lines = []

        # TITLE with enhanced color
        mana = prettify_mana(card.mana_cost) if card.mana_cost else ""
        if mana:
            lines.append(f"[bold #e6c84a]{card.name}[/]  {mana}")
        else:
            lines.append(f"[bold #e6c84a]{card.name}[/]")

        # TYPE with color coding
        type_color = self._get_type_color(card.type or "")
        lines.append(f"[italic {type_color}]{card.type}[/]")

        # Visual separator
        lines.append("[dim]" + "─" * 50 + "[/]")
        lines.append("")

        # CARD TEXT with keyword highlighting
        if card.text:
            text = prettify_mana(card.text).replace("\\n", "\n")
            text = self._highlight_keywords(text)
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
            lines.append(f"[bold #c9a227]⚔  {card.power} / {card.toughness}[/]")
        elif card.loyalty is not None:
            lines.append(f"[bold #c9a227]✦ Loyalty: {card.loyalty}[/]")
        elif card.defense is not None:
            lines.append(f"[bold #c9a227]🛡 Defense: {card.defense}[/]")

        # FOOTER with rarity icon
        footer_parts = []
        if card.set_code:
            footer_parts.append(f"[cyan]📦 {card.set_code.upper()}[/]")
        if card.rarity:
            rarity_icon, color = self._get_rarity_style(card.rarity)
            footer_parts.append(f"[{color}]{rarity_icon} {card.rarity.capitalize()}[/]")

        if footer_parts:
            lines.append("")
            lines.append(" · ".join(footer_parts))

        return "\n".join(lines)

    def _get_type_color(self, card_type: str) -> str:
        """Get color based on card type."""
        type_lower = card_type.lower()
        if "creature" in type_lower:
            return "#7ec850"  # Green
        elif "instant" in type_lower or "sorcery" in type_lower:
            return "#4a9fd8"  # Blue
        elif "artifact" in type_lower:
            return "#9a9a9a"  # Gray
        elif "enchantment" in type_lower:
            return "#b86fce"  # Purple
        elif "planeswalker" in type_lower:
            return "#e6c84a"  # Gold
        elif "land" in type_lower:
            return "#a67c52"  # Brown
        return "#888"

    def _get_rarity_style(self, rarity: str) -> tuple[str, str]:
        """Get icon and color for rarity."""
        rarity_styles = {
            "common": ("●", "#888"),
            "uncommon": ("◆", "#c0c0c0"),
            "rare": ("♦", "#c9a227"),
            "mythic": ("★", "#e65c00"),
        }
        return rarity_styles.get(rarity.lower(), ("○", "#666"))

    def _update_rarity_border(self, card: CardDetail) -> None:
        """Update panel border color based on card rarity."""
        from textual.css.types import EdgeType

        if not card.rarity:
            return

        rarity_lower = card.rarity.lower()
        border_colors = {
            "mythic": "#e65c00",  # Orange for mythics
            "rare": "#c9a227",  # Gold for rares
            "uncommon": "#c0c0c0",  # Silver for uncommons
            "common": "#3d3d3d",  # Default gray
        }

        color = border_colors.get(rarity_lower, "#3d3d3d")
        border_type: EdgeType = "heavy" if rarity_lower in ("mythic", "rare") else "round"

        with contextlib.suppress(Exception):
            self.styles.border = (border_type, color)

    def _reset_border(self) -> None:
        """Reset panel border to default."""
        with contextlib.suppress(Exception):
            self.styles.border = ("round", "#3d3d3d")

    def _highlight_keywords(self, text: str) -> str:
        """Highlight keyword abilities."""
        keywords = [
            "Flying",
            "First strike",
            "Double strike",
            "Deathtouch",
            "Haste",
            "Hexproof",
            "Indestructible",
            "Lifelink",
            "Menace",
            "Reach",
            "Trample",
            "Vigilance",
            "Ward",
            "Flash",
            "Defender",
            "Prowess",
            "Protection",
            "Shroud",
            "Fear",
            "Intimidate",
            "Landwalk",
            "Regenerate",
            "Banding",
            "Flanking",
            "Phasing",
            "Cumulative upkeep",
            "Echo",
            "Fading",
            "Kicker",
            "Flashback",
            "Madness",
            "Morph",
            "Storm",
            "Affinity",
            "Entwine",
            "Splice",
            "Offering",
            "Ninjutsu",
            "Epic",
            "Convoke",
            "Dredge",
            "Transmute",
            "Bloodthirst",
            "Haunt",
            "Replicate",
            "Forecast",
            "Graft",
            "Recover",
            "Ripple",
            "Split second",
            "Suspend",
            "Vanishing",
            "Absorb",
            "Aura swap",
            "Delve",
            "Fortify",
            "Frenzy",
            "Gravestorm",
            "Poisonous",
            "Transfigure",
            "Champion",
            "Changeling",
            "Evoke",
            "Hideaway",
            "Prowl",
            "Reinforce",
            "Conspire",
            "Persist",
            "Wither",
            "Retrace",
            "Devour",
            "Exalted",
            "Unearth",
            "Cascade",
            "Annihilator",
            "Level up",
            "Rebound",
            "Infect",
            "Battle cry",
            "Living weapon",
            "Undying",
            "Miracle",
            "Soulbond",
            "Overload",
            "Scavenge",
            "Unleash",
            "Cipher",
            "Evolve",
            "Extort",
            "Fuse",
            "Bestow",
            "Tribute",
            "Dethrone",
            "Hidden agenda",
            "Outlast",
            "Prowess",
            "Dash",
            "Exploit",
            "Menace",
            "Renown",
            "Awaken",
            "Devoid",
            "Ingest",
            "Myriad",
            "Surge",
            "Skulk",
            "Emerge",
            "Escalate",
            "Melee",
            "Crew",
            "Fabricate",
            "Partner",
            "Undaunted",
            "Improvise",
            "Aftermath",
            "Embalm",
            "Eternalize",
            "Afflict",
            "Ascend",
            "Assist",
            "Jump-start",
            "Mentor",
            "Afterlife",
            "Riot",
            "Spectacle",
            "Escape",
            "Companion",
            "Mutate",
            "Cycling",
            "Equip",
        ]
        for keyword in keywords:
            # Case-insensitive replacement that preserves the original case
            pattern = re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE)
            text = pattern.sub(f"[bold #e6c84a]{keyword}[/]", text)
        return text

    def _render_prices(self, card: CardDetail) -> str:
        """Render price information with enhanced styling."""
        lines = [f"[bold #e6c84a]💰 {card.name}[/]"]
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

    async def load_rulings(self, db: MTGDatabase, card_name: str) -> None:
        """Load and display rulings for a card with enhanced styling."""
        rulings_text = self.query_one(f"#{self._child_id('rulings-text')}", Static)

        try:
            result = await cards.get_card_rulings(db, card_name)
            if result.rulings:
                lines = [
                    f"[bold #e6c84a]📜 {result.card_name}[/]",
                    f"[dim]{result.count} official rulings[/]",
                    "[dim]" + "─" * 50 + "[/]",
                    "",
                ]
                for i, ruling in enumerate(result.rulings, 1):
                    # Date with icon
                    lines.append(f"[#c9a227]#{i}[/] [dim italic]{ruling.date}[/]")
                    # Ruling text with highlighting
                    ruling_text = self._highlight_keywords(ruling.text)
                    lines.append(f"   {ruling_text}")
                    lines.append("")
                rulings_text.update("\n".join(lines))
            else:
                rulings_text.update(f"[dim]No rulings found for {card_name}[/]")
        except CardNotFoundError:
            rulings_text.update(f"[red]Card not found: {card_name}[/]")

    async def load_legalities(self, db: MTGDatabase, card_name: str) -> None:
        """Load and display format legalities with enhanced styling."""
        legal_text = self.query_one(f"#{self._child_id('legal-text')}", Static)

        try:
            result = await cards.get_card_legalities(db, card_name)
            lines = [f"[bold #e6c84a]⚖️ {result.card_name}[/]"]
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

                    lines.append(
                        f"  [{style}]{icon}[/] [dim]{display_name:12}[/] [{style}]{status}[/]"
                    )

            legal_text.update("\n".join(lines))
        except CardNotFoundError:
            legal_text.update(f"[red]Card not found: {card_name}[/]")

    async def load_printings(self, scryfall: ScryfallDatabase | None, card_name: str) -> None:
        """Load all printings for a card into the art tab."""
        from mtg_core.tools import images

        art_info = self.query_one(f"#{self._child_id('art-info')}", Static)

        if not scryfall:
            art_info.update("[yellow]Scryfall database not available[/]")
            return

        try:
            result = await images.get_card_printings(scryfall, card_name)
            if not result.printings:
                art_info.update(f"[yellow]No printings found for {card_name}[/]")
                return

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
        art_info = self.query_one(f"#{self._child_id('art-info')}", Static)

        if not self._printings:
            art_info.update("[dim]No printings available[/]")
            return

        printing = self._printings[self._current_printing_index]
        total = len(self._printings)
        idx = self._current_printing_index + 1

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
        art_info = self.query_one(f"#{self._child_id('art-info')}", Static)

        if not HAS_IMAGE_SUPPORT:
            return

        if not self._printings:
            return

        printing = self._printings[self._current_printing_index]
        if not printing.image:
            return

        try:
            try:
                img_widget = self.query_one(f"#{self._child_id('art-image')}", TImage)
            except Exception:
                return

            image_url = printing.image
            if "normal" in image_url:
                image_url = image_url.replace("normal", "large")

            async with httpx.AsyncClient() as client:
                response = await client.get(image_url, timeout=15.0)
                response.raise_for_status()
                image_data = response.content

            pil_image = Image.open(BytesIO(image_data))

            if pil_image.mode not in ("RGB", "L"):
                pil_image = pil_image.convert("RGB")  # type: ignore[assignment]

            img_widget.image = pil_image

        except Exception as e:
            current_text = art_info.renderable  # type: ignore[attr-defined]
            art_info.update(f"{current_text}\n[red dim]Image error: {e}[/]")

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
