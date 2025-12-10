"""Deck-related models."""

from pydantic import BaseModel, Field

from .card import Card


class DeckCard(BaseModel):
    """A card in a deck with quantity."""

    name: str
    quantity: int = Field(default=1, ge=1)
    sideboard: bool = False
    card: Card | None = None  # Populated when deck is analyzed


class Deck(BaseModel):
    """A Magic: The Gathering deck."""

    name: str
    format: str  # standard, modern, commander, etc.
    cards: list[DeckCard] = Field(default_factory=list)
    commander: str | None = None  # For Commander format

    @property
    def mainboard(self) -> list[DeckCard]:
        """Get mainboard cards."""
        return [c for c in self.cards if not c.sideboard]

    @property
    def sideboard_cards(self) -> list[DeckCard]:
        """Get sideboard cards."""
        return [c for c in self.cards if c.sideboard]

    @property
    def total_cards(self) -> int:
        """Total cards in mainboard."""
        return sum(c.quantity for c in self.mainboard)

    @property
    def sideboard_total(self) -> int:
        """Total cards in sideboard."""
        return sum(c.quantity for c in self.sideboard_cards)
