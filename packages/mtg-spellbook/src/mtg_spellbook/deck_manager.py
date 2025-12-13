"""Deck management with card data integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from mtg_core.data.database import DeckCardRow, DeckSummary, UserDatabase
from mtg_core.data.models import (
    AnalyzeDeckInput,
    Card,
    DeckCardInput,
    Format,
    ValidateDeckInput,
)
from mtg_core.tools import deck as deck_tools

if TYPE_CHECKING:
    from mtg_core.data.database import MTGDatabase, ScryfallDatabase
    from mtg_core.data.models import (
        ColorAnalysisResult,
        CompositionResult,
        DeckValidationResult,
        ManaCurveResult,
        PriceAnalysisResult,
    )


@dataclass
class AddCardResult:
    """Result of adding a card to a deck."""

    success: bool
    card: Card | None = None
    error: str | None = None
    new_quantity: int = 0


@dataclass
class DeckCardWithData:
    """A deck card with full card data."""

    card_name: str
    quantity: int
    is_sideboard: bool
    is_commander: bool
    card: Card | None  # Full card data, may be None if lookup fails


@dataclass
class DeckWithCards:
    """A deck with all card data loaded."""

    id: int
    name: str
    format: str | None
    commander: str | None
    cards: list[DeckCardWithData]

    @property
    def mainboard(self) -> list[DeckCardWithData]:
        """Get mainboard cards."""
        return [c for c in self.cards if not c.is_sideboard]

    @property
    def sideboard(self) -> list[DeckCardWithData]:
        """Get sideboard cards."""
        return [c for c in self.cards if c.is_sideboard]

    @property
    def mainboard_count(self) -> int:
        """Total cards in mainboard."""
        return sum(c.quantity for c in self.mainboard)

    @property
    def sideboard_count(self) -> int:
        """Total cards in sideboard."""
        return sum(c.quantity for c in self.sideboard)


@dataclass
class FullDeckAnalysis:
    """Complete deck analysis results."""

    validation: DeckValidationResult
    mana_curve: ManaCurveResult
    colors: ColorAnalysisResult
    composition: CompositionResult
    price: PriceAnalysisResult | None


class DeckManager:
    """Manages deck operations with full card data."""

    def __init__(
        self,
        user_db: UserDatabase,
        mtg_db: MTGDatabase,
        scryfall: ScryfallDatabase | None = None,
    ):
        self.user = user_db
        self.mtg = mtg_db
        self.scryfall = scryfall

    # ─────────────────────────────────────────────────────────────────────────
    # Deck Operations
    # ─────────────────────────────────────────────────────────────────────────

    async def create_deck(
        self,
        name: str,
        format: str | None = None,
        commander: str | None = None,
        description: str | None = None,
    ) -> int:
        """Create a new deck."""
        return await self.user.create_deck(name, format, commander, description)

    async def list_decks(self) -> list[DeckSummary]:
        """List all decks."""
        return await self.user.list_decks()

    async def get_deck(self, deck_id: int) -> DeckWithCards | None:
        """Get a deck with all card data loaded."""
        deck = await self.user.get_deck(deck_id)
        if deck is None:
            return None

        card_rows = await self.user.get_deck_cards(deck_id)
        cards = await self._load_card_data(card_rows)

        return DeckWithCards(
            id=deck.id,
            name=deck.name,
            format=deck.format,
            commander=deck.commander,
            cards=cards,
        )

    async def delete_deck(self, deck_id: int) -> bool:
        """Delete a deck."""
        return await self.user.delete_deck(deck_id)

    async def update_deck(
        self,
        deck_id: int,
        name: str | None = None,
        format: str | None = None,
        commander: str | None = None,
    ) -> None:
        """Update deck metadata."""
        await self.user.update_deck(deck_id, name=name, format=format, commander=commander)

    # ─────────────────────────────────────────────────────────────────────────
    # Card Operations
    # ─────────────────────────────────────────────────────────────────────────

    async def add_card(
        self,
        deck_id: int,
        card_name: str,
        quantity: int = 1,
        sideboard: bool = False,
    ) -> AddCardResult:
        """Add a card to a deck with validation."""
        # Validate card exists
        card = await self.mtg.get_card_by_name(card_name)
        if card is None:
            return AddCardResult(
                success=False,
                error=f"Card not found: {card_name}",
            )

        # Add to deck (uses canonical name from DB)
        await self.user.add_card(deck_id, card.name, quantity, sideboard)

        # Get new total quantity
        new_qty = await self.user.get_deck_card_count(deck_id, card.name)

        return AddCardResult(
            success=True,
            card=card,
            new_quantity=new_qty,
        )

    async def remove_card(self, deck_id: int, card_name: str, sideboard: bool = False) -> bool:
        """Remove a card from a deck."""
        return await self.user.remove_card(deck_id, card_name, sideboard)

    async def set_quantity(
        self,
        deck_id: int,
        card_name: str,
        quantity: int,
        sideboard: bool = False,
    ) -> None:
        """Set the quantity of a card."""
        await self.user.set_quantity(deck_id, card_name, quantity, sideboard)

    async def move_to_sideboard(self, deck_id: int, card_name: str) -> None:
        """Move a card to sideboard."""
        await self.user.move_to_sideboard(deck_id, card_name)

    async def move_to_mainboard(self, deck_id: int, card_name: str) -> None:
        """Move a card to mainboard."""
        await self.user.move_to_mainboard(deck_id, card_name)

    # ─────────────────────────────────────────────────────────────────────────
    # Analysis
    # ─────────────────────────────────────────────────────────────────────────

    async def validate_deck(self, deck_id: int) -> DeckValidationResult:
        """Validate a deck."""
        deck = await self.user.get_deck(deck_id)
        if deck is None:
            raise ValueError(f"Deck not found: {deck_id}")

        cards = await self.user.get_deck_cards(deck_id)
        deck_cards = self._rows_to_deck_cards(cards)

        input_data = ValidateDeckInput(
            cards=deck_cards,
            format=cast(Format, deck.format or "commander"),
            commander=deck.commander,
        )
        return await deck_tools.validate_deck(self.mtg, input_data)

    async def analyze_mana_curve(self, deck_id: int) -> ManaCurveResult:
        """Analyze deck mana curve."""
        cards = await self.user.get_deck_cards(deck_id)
        deck_cards = self._rows_to_deck_cards(cards)
        input_data = AnalyzeDeckInput(cards=deck_cards)
        return await deck_tools.analyze_mana_curve(self.mtg, input_data)

    async def analyze_colors(self, deck_id: int) -> ColorAnalysisResult:
        """Analyze deck colors."""
        cards = await self.user.get_deck_cards(deck_id)
        deck_cards = self._rows_to_deck_cards(cards)
        input_data = AnalyzeDeckInput(cards=deck_cards)
        return await deck_tools.analyze_colors(self.mtg, input_data)

    async def analyze_composition(self, deck_id: int) -> CompositionResult:
        """Analyze deck composition."""
        cards = await self.user.get_deck_cards(deck_id)
        deck_cards = self._rows_to_deck_cards(cards)
        input_data = AnalyzeDeckInput(cards=deck_cards)
        return await deck_tools.analyze_deck_composition(self.mtg, input_data)

    async def analyze_price(self, deck_id: int) -> PriceAnalysisResult | None:
        """Analyze deck price."""
        if self.scryfall is None:
            return None

        cards = await self.user.get_deck_cards(deck_id)
        deck_cards = self._rows_to_deck_cards(cards)
        input_data = AnalyzeDeckInput(cards=deck_cards)
        return await deck_tools.analyze_deck_price(self.mtg, self.scryfall, input_data)

    async def full_analysis(self, deck_id: int) -> FullDeckAnalysis:
        """Run all analysis tools on a deck."""
        deck = await self.user.get_deck(deck_id)
        if deck is None:
            raise ValueError(f"Deck not found: {deck_id}")

        cards = await self.user.get_deck_cards(deck_id)
        deck_cards = self._rows_to_deck_cards(cards)

        validate_input = ValidateDeckInput(
            cards=deck_cards,
            format=cast(Format, deck.format or "commander"),
            commander=deck.commander,
        )
        analyze_input = AnalyzeDeckInput(cards=deck_cards)

        validation = await deck_tools.validate_deck(self.mtg, validate_input)
        mana_curve = await deck_tools.analyze_mana_curve(self.mtg, analyze_input)
        colors = await deck_tools.analyze_colors(self.mtg, analyze_input)
        composition = await deck_tools.analyze_deck_composition(self.mtg, analyze_input)

        price = None
        if self.scryfall:
            price = await deck_tools.analyze_deck_price(self.mtg, self.scryfall, analyze_input)

        return FullDeckAnalysis(
            validation=validation,
            mana_curve=mana_curve,
            colors=colors,
            composition=composition,
            price=price,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Queries
    # ─────────────────────────────────────────────────────────────────────────

    async def find_decks_with_card(self, card_name: str) -> list[DeckSummary]:
        """Find all decks containing a card."""
        return await self.user.find_decks_with_card(card_name)

    # ─────────────────────────────────────────────────────────────────────────
    # Import/Export
    # ─────────────────────────────────────────────────────────────────────────

    async def import_from_text(
        self,
        text: str,
        deck_name: str,
        format: str | None = None,
    ) -> tuple[int, list[str]]:
        """
        Import a deck from text (Arena/MTGO format).

        Returns (deck_id, list of errors/warnings).
        """
        deck_id = await self.create_deck(deck_name, format)
        errors: list[str] = []
        in_sideboard = False

        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("//") or line.startswith("#"):
                continue

            # Check for sideboard marker
            if line.lower() in ("sideboard", "sideboard:"):
                in_sideboard = True
                continue

            # Parse line: "4 Lightning Bolt" or "4x Lightning Bolt"
            parts = line.split(None, 1)
            if len(parts) < 2:
                errors.append(f"Could not parse: {line}")
                continue

            qty_str = parts[0].rstrip("x")
            try:
                quantity = int(qty_str)
            except ValueError:
                errors.append(f"Invalid quantity: {line}")
                continue

            card_name = parts[1].strip()

            # Remove set code if present: "Lightning Bolt (M21)"
            if "(" in card_name and card_name.endswith(")"):
                card_name = card_name[: card_name.rfind("(")].strip()

            result = await self.add_card(deck_id, card_name, quantity, in_sideboard)
            if not result.success:
                errors.append(result.error or f"Unknown error adding {card_name}")

        return deck_id, errors

    async def export_to_text(self, deck_id: int) -> str:
        """Export a deck to text format."""
        deck = await self.get_deck(deck_id)
        if deck is None:
            raise ValueError(f"Deck not found: {deck_id}")

        lines = []

        # Mainboard
        for card in sorted(deck.mainboard, key=lambda c: c.card_name):
            lines.append(f"{card.quantity} {card.card_name}")

        # Sideboard
        if deck.sideboard:
            lines.append("")
            lines.append("Sideboard")
            for card in sorted(deck.sideboard, key=lambda c: c.card_name):
                lines.append(f"{card.quantity} {card.card_name}")

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    async def _load_card_data(self, rows: list[DeckCardRow]) -> list[DeckCardWithData]:
        """Load full card data for deck cards."""
        from mtg_core.exceptions import CardNotFoundError

        result = []
        for row in rows:
            try:
                card = await self.mtg.get_card_by_name(row.card_name)
            except CardNotFoundError:
                card = None
            result.append(
                DeckCardWithData(
                    card_name=row.card_name,
                    quantity=row.quantity,
                    is_sideboard=row.is_sideboard,
                    is_commander=row.is_commander,
                    card=card,
                )
            )
        return result

    def _rows_to_deck_cards(self, rows: list[DeckCardRow]) -> list[DeckCardInput]:
        """Convert database rows to DeckCardInput models for analysis tools."""
        return [
            DeckCardInput(
                name=row.card_name,
                quantity=row.quantity,
                sideboard=row.is_sideboard,
            )
            for row in rows
        ]
