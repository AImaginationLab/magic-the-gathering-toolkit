"""Collection management with card data integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mtg_core.data.database import UserDatabase
from mtg_core.data.models import Card
from mtg_core.exceptions import CardNotFoundError

if TYPE_CHECKING:
    from mtg_core.data.database import MTGDatabase, ScryfallDatabase


@dataclass
class AddToCollectionResult:
    """Result of adding a card to the collection."""

    success: bool
    card: Card | None = None
    error: str | None = None
    new_quantity: int = 0
    new_foil_quantity: int = 0


@dataclass
class CollectionCardWithData:
    """A collection card with full card data and usage info."""

    card_name: str
    quantity: int
    foil_quantity: int
    set_code: str | None
    collector_number: str | None
    card: Card | None
    in_deck_count: int
    deck_usage: list[tuple[str, int]]

    @property
    def total_owned(self) -> int:
        """Total cards owned (regular + foil)."""
        return self.quantity + self.foil_quantity

    @property
    def available(self) -> int:
        """Cards available (not in any deck)."""
        return max(0, self.total_owned - self.in_deck_count)


@dataclass
class CollectionStats:
    """Summary statistics for the collection."""

    unique_cards: int
    total_cards: int
    total_foils: int


@dataclass
class ImportedCard:
    """A card imported with info about available printings."""

    card_name: str
    quantity: int
    foil: bool
    printings_count: int
    current_set_code: str | None = None
    current_collector_number: str | None = None


@dataclass
class ImportResult:
    """Result of importing cards from text."""

    added_count: int
    errors: list[str]
    cards_with_printings: list[ImportedCard]  # Cards that have multiple printings


class CollectionManager:
    """Manages collection operations with full card data."""

    def __init__(
        self,
        user_db: UserDatabase,
        mtg_db: MTGDatabase,
        scryfall: ScryfallDatabase | None = None,
    ):
        self.user = user_db
        self.mtg = mtg_db
        self.scryfall = scryfall

    async def add_card(
        self,
        card_name: str | None = None,
        quantity: int = 1,
        foil: bool = False,
        set_code: str | None = None,
        collector_number: str | None = None,
    ) -> AddToCollectionResult:
        """Add a card to the collection with validation.

        Card can be identified by:
        - card_name: Look up by name
        - set_code + collector_number: Look up by set and collector number

        Supports regular cards, tokens, and art series cards.
        """
        card: Card | None = None

        # If set_code and collector_number provided, look up by those first
        if set_code and collector_number:
            # Try regular cards first
            card = await self.mtg.get_card_by_set_and_number(set_code, collector_number)
            # Fall back to tokens table (includes art series)
            if card is None:
                card = await self.mtg.get_token_by_set_and_number(set_code, collector_number)
            if card is None:
                return AddToCollectionResult(
                    success=False,
                    error=f"Card not found: {set_code.upper()} #{collector_number}",
                )
        elif card_name:
            # Look up by name
            try:
                card = await self.mtg.get_card_by_name(card_name)
            except CardNotFoundError:
                # Fall back to token lookup
                card = await self.mtg.get_token_by_name(card_name)
                if card is None:
                    return AddToCollectionResult(
                        success=False,
                        error=f"Card not found: {card_name}",
                    )
        else:
            return AddToCollectionResult(
                success=False,
                error="Must provide card_name or set_code + collector_number",
            )

        # Add to collection (uses canonical name from DB)
        foil_qty = quantity if foil else 0
        regular_qty = 0 if foil else quantity

        await self.user.add_to_collection(
            card.name,
            quantity=regular_qty,
            foil_quantity=foil_qty,
            set_code=set_code,
            collector_number=collector_number,
        )

        # Get updated quantities
        collection_card = await self.user.get_collection_card(card.name)
        new_qty = collection_card.quantity if collection_card else 0
        new_foil = collection_card.foil_quantity if collection_card else 0

        return AddToCollectionResult(
            success=True,
            card=card,
            new_quantity=new_qty,
            new_foil_quantity=new_foil,
        )

    async def remove_card(self, card_name: str) -> bool:
        """Remove a card entirely from the collection."""
        result: bool = await self.user.remove_from_collection(card_name)
        return result

    async def set_quantity(
        self,
        card_name: str,
        quantity: int,
        foil_quantity: int = 0,
    ) -> None:
        """Set the quantity of a card in the collection."""
        await self.user.set_collection_quantity(card_name, quantity, foil_quantity)

    async def update_printing(
        self,
        card_name: str,
        set_code: str,
        collector_number: str,
    ) -> bool:
        """Update the printing (set/number) for a card in the collection."""
        return await self.user.update_collection_printing(card_name, set_code, collector_number)

    async def apply_printing_selections(
        self,
        selections: dict[str, tuple[str, str]],
    ) -> int:
        """Apply printing selections to collection cards.

        Args:
            selections: Dict mapping card_name -> (set_code, collector_number)

        Returns:
            Number of cards updated
        """
        updated = 0
        for card_name, (set_code, collector_number) in selections.items():
            if await self.update_printing(card_name, set_code, collector_number):
                updated += 1
        return updated

    async def get_card(self, card_name: str) -> CollectionCardWithData | None:
        """Get a single card from the collection with full data."""
        row = await self.user.get_collection_card(card_name)
        if row is None:
            return None

        card = await self.mtg.get_card_by_name(card_name)
        deck_usage = await self.user.get_card_deck_usage(card_name)
        in_deck_count = sum(qty for _, qty in deck_usage)

        return CollectionCardWithData(
            card_name=row.card_name,
            quantity=row.quantity,
            foil_quantity=row.foil_quantity,
            set_code=row.set_code,
            collector_number=row.collector_number,
            card=card,
            in_deck_count=in_deck_count,
            deck_usage=deck_usage,
        )

    async def get_collection(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[CollectionCardWithData], int]:
        """Get paginated collection with card data.

        Returns (cards, total_count).
        """
        offset = (page - 1) * page_size
        rows = await self.user.get_collection_cards(limit=page_size, offset=offset)
        total = await self.user.get_collection_count()

        if not rows:
            return [], total

        # Batch load card data
        card_names = [row.card_name for row in rows]
        cards_by_name = await self.mtg.get_cards_by_names(card_names)

        # Batch load deck usage (single query instead of N+1)
        deck_usage_by_card = await self.user.get_cards_deck_usage_batch(card_names)

        # Build result with usage data
        result = []
        for row in rows:
            card = cards_by_name.get(row.card_name.lower())
            deck_usage = deck_usage_by_card.get(row.card_name, [])
            in_deck_count = sum(qty for _, qty in deck_usage)

            result.append(
                CollectionCardWithData(
                    card_name=row.card_name,
                    quantity=row.quantity,
                    foil_quantity=row.foil_quantity,
                    set_code=row.set_code,
                    collector_number=row.collector_number,
                    card=card,
                    in_deck_count=in_deck_count,
                    deck_usage=deck_usage,
                )
            )

        return result, total

    async def get_stats(self) -> CollectionStats:
        """Get collection statistics."""
        unique = await self.user.get_collection_count()
        total = await self.user.get_collection_total_cards()
        total_foils = await self.user.get_collection_foil_total()

        return CollectionStats(
            unique_cards=unique,
            total_cards=total,
            total_foils=total_foils,
        )

    async def get_card_availability(self, card_name: str) -> tuple[int, int, list[tuple[str, int]]]:
        """Get availability info for a card.

        Returns (owned_qty, in_deck_qty, [(deck_name, qty), ...])
        """
        collection_card = await self.user.get_collection_card(card_name)
        owned = 0
        if collection_card:
            owned = collection_card.quantity + collection_card.foil_quantity

        deck_usage = await self.user.get_card_deck_usage(card_name)
        in_decks = sum(qty for _, qty in deck_usage)

        return owned, in_decks, deck_usage

    async def import_from_text(self, text: str) -> ImportResult:
        """Import cards from text format (one card per line).

        Supported formats:
        - "4 Lightning Bolt" or "4x Lightning Bolt"
        - "4 Lightning Bolt [M21]" or "4 Lightning Bolt (M21)" - with set code
        - "4 Lightning Bolt [M21 #123]" - with set and collector number
        - "4 Lightning Bolt *F*" or "4 Lightning Bolt (foil)" - foil marker
        - "4 FIN 0012" or "4 FIN 12 foil" - set code + collector number lookup
        - "fca 27" or "2 fca 27" - set code + collector number (quantity optional)

        Returns ImportResult with added count, errors, and cards needing printing selection.
        """
        from .collection.parser import parse_card_input

        added = 0
        errors: list[str] = []
        cards_with_printings: list[ImportedCard] = []

        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("//") or line.startswith("#"):
                continue

            # Parse the line using shared parser
            parsed = parse_card_input(line)

            # If SET NUMBER format, look up the card
            card_name = parsed.card_name
            if parsed.set_code and parsed.collector_number and not card_name:
                # Try regular cards first
                looked_up_card = await self.mtg.get_card_by_set_and_number(
                    parsed.set_code, parsed.collector_number
                )
                # Fall back to tokens table (includes art series)
                if not looked_up_card:
                    looked_up_card = await self.mtg.get_token_by_set_and_number(
                        parsed.set_code, parsed.collector_number
                    )
                if looked_up_card:
                    card_name = looked_up_card.name
                else:
                    errors.append(
                        f"Card not found: {parsed.set_code.upper()} #{parsed.collector_number}"
                    )
                    continue

            if not card_name:
                errors.append(f"Could not parse: {line}")
                continue

            result = await self.add_card(
                card_name,
                parsed.quantity,
                foil=parsed.foil,
                set_code=parsed.set_code,
                collector_number=parsed.collector_number,
            )
            if result.success and result.card:
                added += 1
                # Only check for multiple printings if user didn't specify a printing
                if not parsed.set_code:
                    try:
                        printings = await self.mtg.get_all_printings(result.card.name)
                        if len(printings) > 1:
                            cards_with_printings.append(
                                ImportedCard(
                                    card_name=result.card.name,
                                    quantity=parsed.quantity,
                                    foil=parsed.foil,
                                    printings_count=len(printings),
                                )
                            )
                    except Exception:
                        pass  # If we can't get printings, skip the selection step
            elif not result.success:
                errors.append(result.error or f"Unknown error adding {card_name}")

        return ImportResult(
            added_count=added,
            errors=errors,
            cards_with_printings=cards_with_printings,
        )

    async def get_collection_card_names(self) -> set[str]:
        """Get all card names in the collection (efficient set lookup)."""
        return await self.user.get_collection_card_names()

    async def export_to_text(self) -> str:
        """Export collection to text format.

        Format: "4 Card Name [SET #123] *F*"
        - Set code and collector number included if available
        - Foils are marked with *F* suffix
        """
        rows = await self.user.get_collection_cards(limit=10000, offset=0)

        lines = []
        for row in rows:
            # Build the printing suffix if we have set/number info
            printing_suffix = ""
            if row.set_code:
                if row.collector_number:
                    printing_suffix = f" [{row.set_code.upper()} #{row.collector_number}]"
                else:
                    printing_suffix = f" [{row.set_code.upper()}]"

            # Export regular and foil copies separately if both exist
            if row.quantity > 0:
                lines.append(f"{row.quantity} {row.card_name}{printing_suffix}")
            if row.foil_quantity > 0:
                lines.append(f"{row.foil_quantity} {row.card_name}{printing_suffix} *F*")

        return "\n".join(sorted(lines))
