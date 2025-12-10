"""Response models for API outputs."""

from pydantic import BaseModel, Field, computed_field


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

    @computed_field
    @property
    def count(self) -> int:
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

    @computed_field
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

    @computed_field
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

    @computed_field
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

    @computed_field
    @property
    def count(self) -> int:
        return len(self.cards)
