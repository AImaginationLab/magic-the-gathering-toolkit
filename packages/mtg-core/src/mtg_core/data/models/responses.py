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

    uuid: str | None = None  # For looking up exact printing
    name: str
    flavor_name: str | None = None  # Alternate name (SpongeBob, Walking Dead, etc.)
    mana_cost: str | None = None
    cmc: float | None = None
    type: str | None = None
    colors: list[str] = Field(default_factory=list)
    color_identity: list[str] = Field(default_factory=list)
    rarity: str | None = None
    set_code: str | None = None
    collector_number: str | None = None  # For preserving exact printing
    keywords: list[str] = Field(default_factory=list)
    power: str | None = None
    toughness: str | None = None

    # Scryfall enrichment (optional)
    image: str | None = None
    image_small: str | None = None
    price_usd: float | None = None
    purchase_link: str | None = None

    # Collection status
    owned: bool | None = None  # True if card is in user's collection


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
    flavor_name: str | None = None  # Alternate name (SpongeBob, Walking Dead, etc.)
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
    """Single printing info with card data for display."""

    uuid: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    image: str | None = None
    art_crop: str | None = None
    price_usd: float | None = None
    price_usd_foil: float | None = None
    price_eur: float | None = None
    artist: str | None = None
    flavor_text: str | None = None
    rarity: str | None = None
    release_date: str | None = None
    illustration_id: str | None = None
    # Card data (same for all printings, included for display convenience)
    mana_cost: str | None = None
    type_line: str | None = None
    oracle_text: str | None = None
    power: str | None = None
    toughness: str | None = None
    loyalty: str | None = None


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


# =============================================================================
# Synergy & Strategy Response Models
# =============================================================================

# Type literals for synergy detection
SynergyType = Literal["keyword", "tribal", "ability", "theme", "archetype", "combo"]
ComboType = Literal["infinite", "value", "lock", "win"]
SuggestionCategory = Literal["synergy", "staple", "upgrade", "budget"]


class SynergyResult(BaseModel):
    """A card that synergizes with the input card."""

    name: str
    synergy_type: SynergyType
    reason: str  # Human-readable explanation
    score: float = Field(ge=0.0, le=1.0)  # Synergy strength
    mana_cost: str | None = None
    type_line: str | None = None
    image_small: str | None = None  # Scryfall small image URL

    # Card properties
    rarity: str | None = None
    keywords: list[str] = Field(default_factory=list)
    price_usd: float | None = None  # Price in dollars
    edhrec_rank: int | None = None  # Commander popularity (lower = more popular)

    # Collection status
    owned: bool | None = None  # True if card is in user's collection

    # 17Lands gameplay data (when available)
    synergy_lift: float | None = None  # % improvement when played together
    win_rate_together: float | None = None  # Win rate when both in hand (0-1)
    sample_size: int | None = None  # Co-occurrence count for confidence
    tier: str | None = None  # S/A/B/C/D/F tier rating
    gih_wr: float | None = None  # Games in Hand Win Rate (0-1)
    iwd: float | None = None  # Improvement When Drawn (late game impact)
    oh_wr: float | None = None  # Opening Hand Win Rate (early game strength)

    # Archetype context (color pairs this card performs best in)
    best_archetypes: list[str] = Field(
        default_factory=list
    )  # e.g., ["UR", "UB"] - top performing color pairs

    # Card classification
    is_bomb: bool | None = None  # Standalone power (Sealed > Draft)
    is_synergy_dependent: bool | None = None  # Needs archetype support (Draft > Sealed)

    # Combo connections (when available from Spellbook)
    combo_count: int | None = None  # Number of known combos involving this card
    combo_preview: str | None = None  # First combo description (teaser)


class FindSynergiesResult(BaseModel):
    """Result of find_synergies tool."""

    card_name: str
    synergies: list[SynergyResult]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_found(self) -> int:
        """Number of synergies found."""
        return len(self.synergies)


class ComboCard(BaseModel):
    """A card in a combo."""

    name: str
    role: str  # What this card does in the combo


class Combo(BaseModel):
    """A known combo."""

    id: str  # Unique identifier
    cards: list[ComboCard]
    description: str  # What the combo does
    combo_type: ComboType
    colors: list[str] = Field(default_factory=list)  # Colors involved


class DetectCombosResult(BaseModel):
    """Result of detect_combos tool."""

    combos: list[Combo] = Field(default_factory=list)  # Found complete combos
    potential_combos: list[Combo] = Field(default_factory=list)  # Missing 1-2 pieces
    missing_cards: dict[str, list[str]] = Field(default_factory=dict)  # combo_id -> missing cards


class SuggestedCard(BaseModel):
    """A suggested card to add."""

    name: str
    reason: str
    category: SuggestionCategory
    mana_cost: str | None = None
    type_line: str | None = None
    price_usd: float | None = None

    # Collection status
    owned: bool | None = None  # True if card is in user's collection

    # Enhanced scoring from data sources
    score: float | None = None  # Overall relevance score (0-100)
    tier: str | None = None  # 17Lands tier (S/A/B/C/D/F)
    edhrec_rank: int | None = None  # EDHREC popularity rank (lower = more popular)
    combo_count: int | None = None  # Number of combos this card enables


class SuggestCardsResult(BaseModel):
    """Result of suggest_cards tool."""

    suggestions: list[SuggestedCard] = Field(default_factory=list)
    detected_themes: list[str] = Field(default_factory=list)
    deck_colors: list[str] = Field(default_factory=list)


# =============================================================================
# Artist Discovery Response Models
# =============================================================================


class ArtistSummary(BaseModel):
    """Summary of an artist for browser views."""

    name: str
    card_count: int
    sets_count: int
    first_card_year: int | None = None
    most_recent_year: int | None = None


class ArtistStats(BaseModel):
    """Detailed artist statistics."""

    name: str
    total_cards: int
    sets_featured: list[str] = Field(default_factory=list)
    first_card_date: str | None = None
    most_recent_date: str | None = None
    format_distribution: dict[str, int] = Field(default_factory=dict)


class ArtistPortfolio(BaseModel):
    """Complete artist portfolio for display."""

    artist: ArtistSummary
    stats: ArtistStats
    cards: list[CardSummary] = Field(default_factory=list)


class ArtistCardsResult(BaseModel):
    """Cached result of artist cards query (for disk cache)."""

    artist_name: str
    cards: list[CardSummary] = Field(default_factory=list)


# =============================================================================
# Set Exploration Response Models
# =============================================================================


class SetStats(BaseModel):
    """Set statistics for display."""

    set_code: str
    total_cards: int
    rarity_distribution: dict[str, int] = Field(default_factory=dict)
    color_distribution: dict[str, int] = Field(default_factory=dict)
    mechanics: list[str] = Field(default_factory=list)
    avg_cmc: float | None = None


class BlockSummary(BaseModel):
    """Summary of a block for browser views."""

    name: str
    set_count: int
    total_cards: int
    first_release: str | None = None
    last_release: str | None = None
    sets: list[SetSummary] = Field(default_factory=list)


# =============================================================================
# Comprehensive Deck Health Analysis
# =============================================================================

# Archetype literals
ArchetypeType = Literal[
    "Aggro",
    "Midrange",
    "Control",
    "Combo",
    "Spellslinger",
    "Creature-heavy",
    "Lands Matter",
    "Balanced",
]

# Grade literals
GradeType = Literal["S", "A", "B", "C", "D", "F"]


class DeckHealthIssue(BaseModel):
    """A health issue or warning for the deck."""

    message: str
    severity: Literal["warning", "error"]  # warning = yellow, error = red


class KeywordCount(BaseModel):
    """Count of a specific keyword in the deck."""

    keyword: str
    count: int


class DeckTheme(BaseModel):
    """A detected deck theme with card count."""

    name: str
    card_count: int
    description: str | None = None


class SynergyPair(BaseModel):
    """A synergy between two cards."""

    card1: str
    card2: str
    reason: str
    category: str  # e.g., "Death triggers", "ETB effects", "Gameplay Data"


class MatchupInfo(BaseModel):
    """Deck matchup information."""

    strong_against: list[str] = Field(default_factory=list)
    weak_against: list[str] = Field(default_factory=list)


class DeckHealthResult(BaseModel):
    """Comprehensive deck health analysis."""

    # Overall score and grade
    score: int = Field(ge=0, le=100)  # 0-100
    grade: GradeType  # S, A, B, C, D, F

    # Archetype detection
    archetype: ArchetypeType
    archetype_confidence: int = Field(ge=0, le=100)  # 0-100%

    # Key metrics
    total_cards: int
    expected_cards: int  # 60 or 99 based on format
    land_count: int
    land_percentage: float
    average_cmc: float
    interaction_count: int
    card_draw_count: int
    ramp_count: int

    # Breakdown counts
    creature_count: int
    instant_count: int
    sorcery_count: int
    artifact_count: int
    enchantment_count: int
    planeswalker_count: int

    # Top keywords
    top_keywords: list[KeywordCount] = Field(default_factory=list)

    # Issues and suggestions
    issues: list[DeckHealthIssue] = Field(default_factory=list)

    # Archetype traits (human-readable explanations)
    archetype_traits: list[str] = Field(default_factory=list)

    # Deck themes (e.g., Tokens, Sacrifice, Lifegain)
    themes: list[DeckTheme] = Field(default_factory=list)

    # Tribal info (if dominant tribe detected)
    dominant_tribe: str | None = None
    tribal_count: int = 0

    # Matchup information
    matchups: MatchupInfo | None = None

    # Synergy pairs between cards in the deck
    synergy_pairs: list[SynergyPair] = Field(default_factory=list)


# =============================================================================
# Preload Response Models
# =============================================================================


class PreloadResult(BaseModel):
    """Result of preloading card data into cache."""

    cards_requested: int
    cards_cached: int
    cards_already_cached: int
    cards_failed: int
    failed_cards: list[str] = Field(default_factory=list)
