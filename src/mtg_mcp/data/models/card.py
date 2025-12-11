"""Card-related models."""

from pydantic import BaseModel, ConfigDict, Field


class CardRuling(BaseModel):
    """A ruling for a card."""

    date: str
    text: str


class CardLegality(BaseModel):
    """Format legality for a card."""

    format: str
    legality: str  # Legal, Banned, Restricted, Not Legal


class Card(BaseModel):
    """A Magic: The Gathering card."""

    model_config = ConfigDict(populate_by_name=True)

    # Core identifiers
    uuid: str | None = None
    name: str

    # Card characteristics
    layout: str | None = None
    mana_cost: str | None = Field(default=None, alias="manaCost")
    cmc: float | None = Field(default=None, alias="manaValue", ge=0)
    colors: list[str] | None = None
    color_identity: list[str] | None = Field(default=None, alias="colorIdentity")
    type: str | None = None  # Full type line
    supertypes: list[str] | None = None
    types: list[str] | None = None
    subtypes: list[str] | None = None

    # Card text
    text: str | None = None
    flavor: str | None = Field(default=None, alias="flavorText")

    # Stats (for creatures/planeswalkers/battles)
    power: str | None = None
    toughness: str | None = None
    loyalty: str | None = None
    defense: str | None = None  # For Battle cards

    # Set info
    set_code: str | None = Field(default=None, alias="setCode")
    set_name: str | None = Field(default=None, alias="setName")
    rarity: str | None = None
    number: str | None = None

    # Art
    artist: str | None = None

    # Keywords (for synergy detection)
    keywords: list[str] | None = None

    # EDHRec popularity rank (lower = more popular)
    edhrec_rank: int | None = Field(default=None, alias="edhrecRank", ge=0)

    # Rules (populated on detailed lookups)
    rulings: list[CardRuling] | None = None
    legalities: list[CardLegality] | None = None

    def to_summary(self) -> str:
        """Return a concise summary of the card."""
        parts = [f"**{self.name}**"]
        if self.mana_cost:
            parts.append(f" {self.mana_cost}")
        parts.append(f"\n{self.type}")
        if self.power and self.toughness:
            parts.append(f" ({self.power}/{self.toughness})")
        if self.loyalty:
            parts.append(f" (Loyalty: {self.loyalty})")
        if self.defense:
            parts.append(f" (Defense: {self.defense})")
        if self.text:
            parts.append(f"\n\n{self.text}")
        if self.set_code:
            rarity_str = f" - {self.rarity}" if self.rarity else ""
            parts.append(f"\n\n*{self.set_code}{rarity_str}*")
        return "".join(parts)

    def get_legality(self, format_name: str) -> str | None:
        """Get legality for a specific format."""
        if not self.legalities:
            return None
        for leg in self.legalities:
            if leg.format.lower() == format_name.lower():
                return leg.legality
        return None

    def is_legal_in(self, format_name: str) -> bool:
        """Check if card is legal (or restricted) in a format."""
        legality = self.get_legality(format_name)
        return legality in ("Legal", "Restricted")


class CardImage(BaseModel):
    """Image and pricing data from Scryfall."""

    scryfall_id: str
    oracle_id: str | None = None
    name: str
    set_code: str | None = None
    collector_number: str | None = None

    # Image URLs (various sizes)
    image_small: str | None = None
    image_normal: str | None = None
    image_large: str | None = None
    image_png: str | None = None
    image_art_crop: str | None = None
    image_border_crop: str | None = None

    # Prices (in USD cents, None if unavailable)
    price_usd: int | None = Field(default=None, ge=0)
    price_usd_foil: int | None = Field(default=None, ge=0)
    price_eur: int | None = Field(default=None, ge=0)
    price_eur_foil: int | None = Field(default=None, ge=0)

    # Purchase links
    purchase_tcgplayer: str | None = None
    purchase_cardmarket: str | None = None
    purchase_cardhoarder: str | None = None

    # Related links
    link_edhrec: str | None = None
    link_gatherer: str | None = None

    # Visual properties
    highres_image: bool = False
    full_art: bool = False
    border_color: str | None = None
    illustration_id: str | None = None
    frame: str | None = None
    finishes: str | None = None  # JSON array string like '["nonfoil", "foil"]'

    def get_price_usd(self) -> float | None:
        """Get USD price as float dollars."""
        if self.price_usd is not None:
            return self.price_usd / 100
        return None

    def get_price_usd_foil(self) -> float | None:
        """Get USD foil price as float dollars."""
        if self.price_usd_foil is not None:
            return self.price_usd_foil / 100
        return None
