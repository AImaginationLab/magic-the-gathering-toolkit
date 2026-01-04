"""Pydantic request models for API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CardDetailsRequest(BaseModel):
    """Request for card details."""

    name: str = Field(..., min_length=1, description="Card name")


class CardRulingsRequest(BaseModel):
    """Request for card rulings."""

    name: str = Field(..., min_length=1, description="Card name")


class CardPrintingsRequest(BaseModel):
    """Request for card printings."""

    name: str = Field(..., min_length=1, description="Card name")


class FindSynergiesRequest(BaseModel):
    """Request for finding card synergies."""

    card_name: str = Field(..., min_length=1, description="Card name to find synergies for")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum results to return")
    format_legal: str | None = Field(default=None, description="Filter by format legality")


class DetectCombosRequest(BaseModel):
    """Request for detecting combos in a list of cards."""

    card_names: list[str] = Field(..., min_length=1, description="List of card names")


class CombosForCardRequest(BaseModel):
    """Request for finding combos involving a specific card."""

    card_name: str = Field(..., min_length=1, description="Card name to find combos for")


class SuggestCardsRequest(BaseModel):
    """Request for card suggestions."""

    deck_cards: list[str] = Field(..., min_length=1, description="Current deck card names")
    format_legal: str | None = Field(default=None, description="Format to filter by")
    budget_max: float | None = Field(default=None, ge=0, description="Maximum price per card")
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum suggestions")
    set_codes: list[str] | None = Field(
        default=None, description="Prioritize cards from these sets"
    )
    themes: list[str] | None = Field(default=None, description="Filter by themes")
    creature_types: list[str] | None = Field(
        default=None, description="Filter by creature types (tribals)"
    )
    owned_only: bool = Field(default=False, description="Only suggest cards from user's collection")


class FindCommandersRequest(BaseModel):
    """Request for finding commanders for a collection."""

    collection_cards: list[str] | None = Field(
        default=None, description="Card names in collection (optional if use_collection=True)"
    )
    use_collection: bool = Field(
        default=False, description="Use entire user collection instead of passing card list"
    )
    colors: list[str] | None = Field(default=None, description="Filter by colors (W, U, B, R, G)")
    creature_type: str | None = Field(default=None, description="Filter by creature type")
    creature_types: list[str] | None = Field(
        default=None, description="Filter by multiple creature types (tribals)"
    )
    theme: str | None = Field(default=None, description="Filter by theme")
    themes: list[str] | None = Field(default=None, description="Filter by multiple themes")
    format: str | None = Field(
        default=None, description="Filter by format (commander, standard, modern, etc.)"
    )
    set_codes: list[str] | None = Field(
        default=None, description="Prioritize cards from these sets"
    )
    limit: int = Field(default=10, ge=1, le=50, description="Maximum commanders to return")


class FindDecksRequest(BaseModel):
    """Request for finding buildable decks."""

    collection_cards: list[str] | None = Field(
        default=None, description="Card names in collection (optional if use_collection=True)"
    )
    use_collection: bool = Field(
        default=False, description="Use entire user collection instead of passing card list"
    )
    colors: list[str] | None = Field(default=None, description="Filter by colors")
    creature_type: str | None = Field(default=None, description="Filter by tribal type")
    creature_types: list[str] | None = Field(
        default=None, description="Filter by multiple creature types (tribals)"
    )
    theme: str | None = Field(default=None, description="Filter by theme")
    themes: list[str] | None = Field(default=None, description="Filter by multiple themes")
    format: str | None = Field(
        default=None, description="Filter by format (commander, standard, modern, etc.)"
    )
    set_codes: list[str] | None = Field(
        default=None, description="Prioritize cards from these sets"
    )
    min_completion: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Minimum deck completion percentage"
    )
    limit: int = Field(default=10, ge=1, le=50, description="Maximum decks to return")


class PreloadCardsRequest(BaseModel):
    """Request for preloading card data into cache."""

    card_names: list[str] = Field(
        ..., min_length=1, max_length=5000, description="Card names to preload"
    )
