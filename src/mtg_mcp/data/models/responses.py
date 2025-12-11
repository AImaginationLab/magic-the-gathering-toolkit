"""Response models for API outputs."""

from typing import Literal

from pydantic import BaseModel, Field, computed_field

# Issue types for deck validation
IssueType = Literal[
    "not_found",
    "not_legal",
    "over_copy_limit",
    "over_singleton_limit",
    "outside_color_identity",
]


class CardSummary(BaseModel):
    """Card summary for search results."""

    name: str
    mana_cost: str | None = None
    cmc: float | None = None
    type: str | None = None
    colors: list[str] = Field(default_factory=list)
    color_identity: list[str] = Field(default_factory=list)
    rarity: str | None = None
    set_code: str | None = None
    keywords: list[str] = Field(default_factory=list)
    power: str | None = None
    toughness: str | None = None

    # Scryfall enrichment (optional)
    image: str | None = None
    image_small: str | None = None
    price_usd: float | None = None
    purchase_link: str | None = None


class ImageUrls(BaseModel):
    """Card image URLs in various sizes."""

    small: str | None = None
    normal: str | None = None
    large: str | None = None
    png: str | None = None
    art_crop: str | None = None


class Prices(BaseModel):
    """Card prices."""

    usd: float | None = None
    usd_foil: float | None = None
    eur: float | None = None
    eur_foil: float | None = None


class PurchaseLinks(BaseModel):
    """Purchase links for a card."""

    tcgplayer: str | None = None
    cardmarket: str | None = None
    cardhoarder: str | None = None


class RelatedLinks(BaseModel):
    """Related links for a card."""

    edhrec: str | None = None
    gatherer: str | None = None


class CardDetail(BaseModel):
    """Detailed card information."""

    name: str
    uuid: str | None = None
    mana_cost: str | None = None
    cmc: float | None = None
    colors: list[str] = Field(default_factory=list)
    color_identity: list[str] = Field(default_factory=list)
    type: str | None = None
    supertypes: list[str] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)
    subtypes: list[str] = Field(default_factory=list)
    text: str | None = None
    flavor: str | None = None
    rarity: str | None = None
    set_code: str | None = None
    number: str | None = None
    artist: str | None = None
    layout: str | None = None
    keywords: list[str] = Field(default_factory=list)

    # Creature stats
    power: str | None = None
    toughness: str | None = None
    loyalty: str | None = None
    defense: str | None = None

    # Metadata
    edhrec_rank: int | None = None
    legalities: dict[str, str] | None = None
    rulings_count: int | None = None

    # Scryfall enrichment
    images: ImageUrls | None = None
    prices: Prices | None = None
    purchase_links: PurchaseLinks | None = None
    related_links: RelatedLinks | None = None


class SearchResult(BaseModel):
    """Search results with pagination."""

    cards: list[CardSummary]
    page: int
    page_size: int
    total_count: int | None = None  # Total matching cards (for pagination)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def count(self) -> int:
        """Number of cards on this page."""
        return len(self.cards)


class RulingEntry(BaseModel):
    """A single ruling."""

    date: str
    text: str


class RulingsResponse(BaseModel):
    """Card rulings response."""

    card_name: str
    rulings: list[RulingEntry]
    note: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def count(self) -> int:
        return len(self.rulings)


class LegalitiesResponse(BaseModel):
    """Card legalities response."""

    card_name: str
    legalities: dict[str, str]
    note: str | None = None


class SetSummary(BaseModel):
    """Set summary for list results."""

    code: str
    name: str
    type: str | None = None
    release_date: str | None = None


class SetDetail(BaseModel):
    """Detailed set information."""

    code: str
    name: str
    type: str | None = None
    release_date: str | None = None
    block: str | None = None
    base_set_size: int | None = None
    total_set_size: int | None = None
    is_online_only: bool | None = None
    is_foil_only: bool | None = None
    keyrune_code: str | None = None


class SetsResponse(BaseModel):
    """Sets list response."""

    sets: list[SetSummary]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def count(self) -> int:
        return len(self.sets)


class DatabaseStats(BaseModel):
    """Database statistics."""

    unique_cards: int
    total_printings: int
    total_sets: int
    data_version: str | None = None
    data_date: str | None = None


class CardImageResponse(BaseModel):
    """Card image response."""

    card_name: str
    set_code: str | None = None
    images: ImageUrls
    prices: Prices
    purchase_links: PurchaseLinks
    related_links: RelatedLinks
    highres_image: bool = False
    full_art: bool = False


class PrintingInfo(BaseModel):
    """Single printing info."""

    set_code: str | None = None
    collector_number: str | None = None
    image: str | None = None
    price_usd: float | None = None


class PrintingsResponse(BaseModel):
    """All printings of a card."""

    card_name: str
    printings: list[PrintingInfo]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def count(self) -> int:
        return len(self.printings)


class PriceResponse(BaseModel):
    """Card price response."""

    card_name: str
    set_code: str | None = None
    prices: Prices
    purchase_links: PurchaseLinks


class PriceSearchResult(BaseModel):
    """Card in price search results."""

    name: str
    set_code: str | None = None
    price_usd: float | None = None
    image: str | None = None


class PriceSearchResponse(BaseModel):
    """Price search results."""

    cards: list[PriceSearchResult]
    page: int
    page_size: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def count(self) -> int:
        return len(self.cards)


# =============================================================================
# Deck Analysis Response Models
# =============================================================================


class CardIssue(BaseModel):
    """An issue with a card in deck validation."""

    card_name: str
    issue: IssueType
    details: str | None = None


class DeckValidationResult(BaseModel):
    """Deck validation result."""

    format: str
    is_valid: bool
    total_cards: int
    sideboard_count: int
    issues: list[CardIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ManaCurveResult(BaseModel):
    """Mana curve analysis result."""

    curve: dict[int, int]  # {0: 5, 1: 12, 2: 15, 3: 10, ...}
    average_cmc: float
    median_cmc: float
    land_count: int
    nonland_count: int
    x_spell_count: int


class ColorBreakdown(BaseModel):
    """Color breakdown for a single color."""

    color: str  # "W", "U", "B", "R", "G"
    color_name: str  # "White", "Blue", etc.
    card_count: int
    mana_symbols: int  # Total colored pips needed


class ColorAnalysisResult(BaseModel):
    """Color analysis result."""

    colors: list[str]  # Deck's colors in WUBRG order
    color_identity: list[str]  # Full color identity
    breakdown: list[ColorBreakdown]
    multicolor_count: int
    colorless_count: int
    mana_pip_totals: dict[str, int]  # {"W": 15, "U": 8, ...}
    recommended_land_ratio: dict[str, float]  # {"W": 0.4, "U": 0.2, ...}


class TypeCount(BaseModel):
    """Card type count."""

    type: str
    count: int
    percentage: float


class CompositionResult(BaseModel):
    """Deck composition analysis result."""

    total_cards: int
    types: list[TypeCount]
    creatures: int
    noncreatures: int
    lands: int
    spells: int  # Instants + Sorceries
    interaction: int  # Removal, counterspells (heuristic)
    ramp_count: int  # Detected ramp cards (heuristic)


class CardPrice(BaseModel):
    """Price info for a card in deck."""

    name: str
    quantity: int
    unit_price: float | None
    total_price: float | None


class PriceAnalysisResult(BaseModel):
    """Deck price analysis result."""

    total_price: float | None
    mainboard_price: float | None
    sideboard_price: float | None
    average_card_price: float | None
    most_expensive: list[CardPrice]  # Top 10
    missing_prices: list[str]  # Cards with no price data

    @computed_field  # type: ignore[prop-decorator]
    @property
    def most_expensive_count(self) -> int:
        """Number of cards in the most_expensive list (up to 10)."""
        return len(self.most_expensive)
