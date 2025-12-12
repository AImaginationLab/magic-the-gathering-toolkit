"""Input validation models for MCP tools."""

from typing import Literal

from pydantic import BaseModel, Field

from .types import Color, Format, Rarity

SortField = Literal["name", "cmc", "color", "rarity", "type"]
SortOrder = Literal["asc", "desc"]


class SearchCardsInput(BaseModel):
    """Input parameters for search_cards tool."""

    name: str | None = Field(default=None, description="Card name (partial match)")
    colors: list[Color] | None = Field(default=None, description="Filter by colors")
    color_identity: list[Color] | None = Field(default=None, description="Filter by color identity")
    type: str | None = Field(default=None, description="Card type")
    subtype: str | None = Field(default=None, description="Subtype")
    supertype: str | None = Field(default=None, description="Supertype")
    rarity: Rarity | None = Field(default=None, description="Card rarity")
    set_code: str | None = Field(default=None, description="Set code")
    cmc: float | None = Field(default=None, ge=0, description="Exact mana value")
    cmc_min: float | None = Field(default=None, ge=0, description="Minimum mana value")
    cmc_max: float | None = Field(default=None, ge=0, description="Maximum mana value")
    power: str | None = Field(default=None, description="Creature power")
    toughness: str | None = Field(default=None, description="Creature toughness")
    text: str | None = Field(default=None, description="Search in card text")
    keywords: list[str] | None = Field(default=None, description="Filter by keywords")
    format_legal: Format | None = Field(default=None, description="Filter by format legality")
    sort_by: SortField | None = Field(default=None, description="Sort by field (name, cmc, color, rarity, type)")
    sort_order: SortOrder = Field(default="asc", description="Sort order (asc, desc)")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=25, ge=1, le=100, description="Results per page")


class GetCardInput(BaseModel):
    """Input parameters for get_card tool."""

    name: str | None = Field(default=None, description="Exact card name")
    uuid: str | None = Field(default=None, description="Card UUID")


class GetCardRulingsInput(BaseModel):
    """Input parameters for get_card_rulings tool."""

    name: str = Field(..., min_length=1, description="Exact card name")


class GetCardLegalitiesInput(BaseModel):
    """Input parameters for get_card_legalities tool."""

    name: str = Field(..., min_length=1, description="Exact card name")


class GetCardImageInput(BaseModel):
    """Input parameters for get_card_image tool."""

    name: str = Field(..., min_length=1, description="Exact card name")
    set_code: str | None = Field(default=None, description="Set code for specific printing")


class GetCardPrintingsInput(BaseModel):
    """Input parameters for get_card_printings tool."""

    name: str = Field(..., min_length=1, description="Exact card name")


class GetCardPriceInput(BaseModel):
    """Input parameters for get_card_price tool."""

    name: str = Field(..., min_length=1, description="Exact card name")
    set_code: str | None = Field(default=None, description="Set code for specific printing")


class SearchByPriceInput(BaseModel):
    """Input parameters for search_by_price tool."""

    min_price: float | None = Field(default=None, ge=0, description="Minimum price in USD")
    max_price: float | None = Field(default=None, ge=0, description="Maximum price in USD")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=25, ge=1, le=100, description="Results per page")


class GetSetsInput(BaseModel):
    """Input parameters for get_sets tool."""

    name: str | None = Field(default=None, description="Filter by set name")
    set_type: str | None = Field(default=None, description="Filter by set type")
    include_online_only: bool = Field(default=True, description="Include online-only sets")


class GetSetInput(BaseModel):
    """Input parameters for get_set tool."""

    code: str = Field(..., min_length=1, description="Set code")


# =============================================================================
# Deck Analysis Input Models
# =============================================================================


class DeckCardInput(BaseModel):
    """A card entry in a deck."""

    name: str = Field(..., min_length=1, description="Card name")
    quantity: int = Field(default=1, ge=1, le=99, description="Number of copies")
    sideboard: bool = Field(default=False, description="Is in sideboard")


class ValidateDeckInput(BaseModel):
    """Input parameters for validate_deck tool."""

    cards: list[DeckCardInput] = Field(..., description="Deck cards")
    format: Format = Field(..., description="Format to validate against")
    commander: str | None = Field(default=None, description="Commander card name")
    # Configurable rules
    check_legality: bool = Field(default=True, description="Check card legality")
    check_deck_size: bool = Field(default=True, description="Check deck size requirements")
    check_copy_limit: bool = Field(default=True, description="Check copy limit (4 or singleton)")
    check_singleton: bool = Field(default=True, description="Check singleton rule (Commander)")
    check_color_identity: bool = Field(default=True, description="Check color identity (Commander)")


class AnalyzeDeckInput(BaseModel):
    """Input parameters for deck analysis tools."""

    cards: list[DeckCardInput] = Field(..., description="Deck cards")
    format: Format | None = Field(default=None, description="Format (optional)")
    commander: str | None = Field(default=None, description="Commander card name")
