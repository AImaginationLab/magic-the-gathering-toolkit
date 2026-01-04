"""Collection import/export API routes."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from mtg_core.config import get_settings
from mtg_core.data.database import UnifiedDatabase, UserDatabase
from mtg_core.data.models.inputs import CollectionSortField, SortOrder
from mtg_core.tools.collection import ParsedCardInput, parse_card_list, price_collection

router = APIRouter()


def _get_db(request: Request) -> UnifiedDatabase:
    """Get database from app state."""
    db: UnifiedDatabase = request.app.state.db_manager.db
    return db


def _get_user_db(request: Request) -> UserDatabase:
    """Get user database from app state."""
    user_db: UserDatabase | None = request.app.state.db_manager.user
    if user_db is None:
        raise HTTPException(status_code=503, detail="User database not available")
    return user_db


class ParsedCard(BaseModel):
    """A parsed card entry."""

    card_name: str | None = Field(None, description="Card name if specified")
    quantity: int = Field(1, description="Number of copies")
    foil: bool = Field(False, description="Whether the card is foil")
    set_code: str | None = Field(None, description="Set code if specified")
    collector_number: str | None = Field(None, description="Collector number if specified")


class ParseCollectionRequest(BaseModel):
    """Request to parse a collection text."""

    text: str = Field(..., description="Collection text to parse (multi-line)")
    default_quantity: int = Field(1, description="Default quantity for entries without count")


class ParseCollectionResponse(BaseModel):
    """Response from parsing a collection."""

    cards: list[ParsedCard] = Field(default_factory=list, description="Parsed card entries")
    total_cards: int = Field(0, description="Total number of cards (sum of quantities)")
    unique_entries: int = Field(0, description="Number of unique entries")


class PricedCard(BaseModel):
    """A card with pricing information."""

    card_name: str | None = Field(None, description="Card name")
    quantity: int = Field(1, description="Number of copies")
    foil: bool = Field(False, description="Whether the card is foil")
    set_code: str | None = Field(None, description="Set code")
    collector_number: str | None = Field(None, description="Collector number")
    price_usd: float | None = Field(None, description="Price in USD (per card)")
    price_usd_foil: float | None = Field(None, description="Foil price in USD (per card)")
    total_value: float = Field(0.0, description="Total value for this entry (price * quantity)")


class PriceCollectionRequest(BaseModel):
    """Request to price a collection."""

    cards: list[ParsedCard] = Field(..., description="Cards to price")


class TopCard(BaseModel):
    """A top-valued card."""

    name: str = Field(..., description="Card name")
    price: float = Field(..., description="Price in USD")


class PriceCollectionResponse(BaseModel):
    """Response with priced collection."""

    cards: list[PricedCard] = Field(default_factory=list, description="Priced card entries")
    total_value: float = Field(0.0, description="Total collection value in USD")
    total_value_foil: float = Field(0.0, description="Total value if all foils in USD")
    cards_with_prices: int = Field(0, description="Number of cards with price data")
    cards_without_prices: int = Field(0, description="Number of cards without price data")
    median_price: float = Field(0.0, description="Median card price in USD")
    top_cards: list[TopCard] = Field(default_factory=list, description="Top 5 most valuable cards")


def _to_parsed_card(p: ParsedCardInput) -> ParsedCard:
    """Convert internal ParsedCardInput to API model."""
    return ParsedCard(
        card_name=p.card_name,
        quantity=p.quantity,
        foil=p.foil,
        set_code=p.set_code,
        collector_number=p.collector_number,
    )


@router.post("/parse", response_model=ParseCollectionResponse)
async def parse_collection(request: ParseCollectionRequest) -> ParseCollectionResponse:
    """Parse a collection text into structured card entries.

    Supports multiple formats:
    - Simple: "4 Lightning Bolt"
    - Set+Number: "fca 27" or "2 fca 27"
    - With set info: "Lightning Bolt [M21]"
    - Foil markers: "Lightning Bolt *F*" or "fca 27 f"
    - Set context blocks:
        fin:
          345
          2 239
          421 f
    """
    parsed = parse_card_list(request.text, request.default_quantity)
    cards = [_to_parsed_card(p) for p in parsed]
    total = sum(c.quantity for c in cards)

    return ParseCollectionResponse(
        cards=cards,
        total_cards=total,
        unique_entries=len(cards),
    )


@router.post("/price", response_model=PriceCollectionResponse)
async def price_collection_endpoint(
    request: Request,
    body: PriceCollectionRequest,
) -> PriceCollectionResponse:
    """Price a collection of cards.

    Takes a list of parsed cards and returns pricing information for each,
    along with collection totals and statistics.

    Uses Scryfall price data from the database. Cards with specific printings
    (set_code + collector_number) get exact printing prices. Cards without
    get the first available price for that card name.
    """
    db = _get_db(request)

    # Convert API models to internal format
    parsed_cards = [
        ParsedCardInput(
            card_name=c.card_name,
            quantity=c.quantity,
            foil=c.foil,
            set_code=c.set_code,
            collector_number=c.collector_number,
        )
        for c in body.cards
    ]

    result = await price_collection(db, parsed_cards)

    # Convert to API response
    priced_cards = [
        PricedCard(
            card_name=c.card_name,
            quantity=c.quantity,
            foil=c.foil,
            set_code=c.set_code,
            collector_number=c.collector_number,
            price_usd=c.price_usd,
            price_usd_foil=c.price_usd_foil,
            total_value=c.total_value,
        )
        for c in result.cards
    ]

    top_cards = [TopCard(name=name, price=price) for name, price in result.top_cards]

    return PriceCollectionResponse(
        cards=priced_cards,
        total_value=result.total_value,
        total_value_foil=result.total_value_foil,
        cards_with_prices=result.cards_with_prices,
        cards_without_prices=result.cards_without_prices,
        median_price=result.median_price,
        top_cards=top_cards,
    )


class CollectionCardResponse(BaseModel):
    """A card in the user's collection with enriched metadata."""

    id: int
    card_name: str
    quantity: int
    foil_quantity: int
    set_code: str | None
    collector_number: str | None
    added_at: str
    updated_at: str
    # Card metadata (from mtg.sqlite)
    rarity: str | None = None
    cmc: float | None = None
    type_line: str | None = None
    colors: list[str] | None = None
    price_usd: float | None = None
    # Gameplay stats (from gameplay.duckdb)
    win_rate: float | None = None
    tier: str | None = None
    draft_pick: float | None = None


class ListCollectionResponse(BaseModel):
    """Response for listing collection cards with pagination."""

    cards: list[CollectionCardResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


def _fetch_card_metadata(
    card_names: list[str], mtg_db_path: Path | None
) -> dict[str, dict[str, Any]]:
    """Fetch card metadata from mtg.sqlite."""
    import json
    import sqlite3

    if not mtg_db_path or not mtg_db_path.exists() or not card_names:
        return {}

    metadata: dict[str, dict[str, Any]] = {}
    try:
        conn = sqlite3.connect(str(mtg_db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        placeholders = ", ".join(["?"] * len(card_names))
        cursor.execute(
            f"""
            SELECT name, rarity, cmc, type_line, colors, price_usd
            FROM cards
            WHERE name IN ({placeholders})
            """,
            card_names,
        )

        for row in cursor.fetchall():
            key = row["name"].lower()
            if key not in metadata:
                colors_raw = row["colors"]
                colors = json.loads(colors_raw) if colors_raw else []
                metadata[key] = {
                    "rarity": row["rarity"],
                    "cmc": row["cmc"],
                    "type_line": row["type_line"],
                    "colors": colors,
                    "price_usd": row["price_usd"],
                }
        conn.close()
    except Exception:
        pass
    return metadata


def _fetch_gameplay_stats(
    card_names: list[str], gameplay_db_path: Path | None
) -> dict[str, dict[str, Any]]:
    """Fetch gameplay stats from gameplay.duckdb."""
    if not gameplay_db_path or not gameplay_db_path.exists() or not card_names:
        return {}

    stats: dict[str, dict[str, Any]] = {}
    try:
        import duckdb

        conn = duckdb.connect(str(gameplay_db_path), read_only=True)
        placeholders = ", ".join(["?"] * len(card_names))
        # Join card_stats with draft_stats to get ATA data
        result = conn.execute(
            f"""
            SELECT cs.card_name, cs.gih_wr, cs.tier, ds.ata
            FROM card_stats cs
            LEFT JOIN draft_stats ds ON cs.card_name = ds.card_name AND cs.set_code = ds.set_code
            WHERE cs.card_name IN ({placeholders})
            """,
            card_names,
        ).fetchall()

        for row in result:
            name, gih_wr, tier, ata = row
            key = name.lower()
            # Prefer rows with ATA data
            if key not in stats or (ata is not None and stats[key].get("draft_pick") is None):
                stats[key] = {
                    "win_rate": gih_wr,
                    "tier": tier,
                    "draft_pick": ata,
                }
        conn.close()
    except Exception:
        pass
    return stats


@router.get("/list", response_model=ListCollectionResponse)
async def list_collection(
    request: Request,
    sort_by: CollectionSortField = Query("name", description="Field to sort by"),
    sort_order: SortOrder = Query("asc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=10000, description="Results per page"),
) -> ListCollectionResponse:
    """List collection cards with sorting and pagination.

    Sort fields:
    - Fast (collection-only): name, dateAdded, quantity, setCode
    - Metadata (requires card data): price, rarity, cmc, type, color
    - Gameplay (requires gameplay data): winRate, tier, draftPick
    """
    user_db = _get_user_db(request)
    settings = get_settings()

    # Calculate offset
    offset = (page - 1) * page_size

    # Get total count for pagination
    total = await user_db.get_collection_count()

    # Get sorted cards
    cards = await user_db.get_collection_cards(
        limit=page_size,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
        mtg_db_path=settings.mtg_db_path,
        gameplay_db_path=settings.gameplay_db_path,
    )

    # Fetch metadata for all cards
    card_names = list({c.card_name for c in cards})
    metadata = _fetch_card_metadata(card_names, settings.mtg_db_path)
    gameplay = _fetch_gameplay_stats(card_names, settings.gameplay_db_path)

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Build enriched response
    enriched_cards = []
    for card in cards:
        key = card.card_name.lower()
        meta = metadata.get(key, {})
        game = gameplay.get(key, {})
        enriched_cards.append(
            CollectionCardResponse(
                id=card.id,
                card_name=card.card_name,
                quantity=card.quantity,
                foil_quantity=card.foil_quantity,
                set_code=card.set_code,
                collector_number=card.collector_number,
                added_at=card.added_at.isoformat(),
                updated_at=card.updated_at.isoformat(),
                rarity=meta.get("rarity"),
                cmc=meta.get("cmc"),
                type_line=meta.get("type_line"),
                colors=meta.get("colors"),
                price_usd=meta.get("price_usd"),
                win_rate=game.get("win_rate"),
                tier=game.get("tier"),
                draft_pick=game.get("draft_pick"),
            )
        )

    return ListCollectionResponse(
        cards=enriched_cards,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


class ImportCollectionRequest(BaseModel):
    """Request to import cards from text."""

    text: str = Field(..., description="Raw text containing card list (multi-line)")
    mode: str = Field("add", description="Import mode: 'add' to merge, 'replace' to clear first")


class ImportedCardInfo(BaseModel):
    """Info about a card that was imported with multiple printings available."""

    card_name: str = Field(..., description="Card name")
    quantity: int = Field(1, description="Quantity imported")
    foil: bool = Field(False, description="Whether foil")
    printings_count: int = Field(0, description="Number of available printings")


class ImportCollectionResponse(BaseModel):
    """Response from importing cards."""

    added_count: int = Field(0, description="Number of unique cards added")
    total_cards: int = Field(0, description="Total cards processed (sum of quantities)")
    errors: list[str] = Field(default_factory=list, description="Errors encountered")
    cards_with_printings: list[ImportedCardInfo] = Field(
        default_factory=list,
        description="Cards that have multiple printings (user may want to select specific printing)",
    )


@router.post("/import", response_model=ImportCollectionResponse)
async def import_collection(
    request: Request,
    body: ImportCollectionRequest,
) -> ImportCollectionResponse:
    """Import cards from raw text into the user's collection.

    Parses the text server-side and batch-inserts all cards efficiently.

    Supported text formats:
    - "4 Lightning Bolt" or "4x Lightning Bolt"
    - "fca 27" or "2 fca 27" (set code + collector number)
    - "Lightning Bolt [M21 #123]" (with specific printing)
    - "Lightning Bolt *F*" or "fca 27 f" (foil markers)
    - Set context blocks:
        fin:
        345
        2 239
        421 f

    Modes:
    - 'add': Merge with existing collection (increases quantities for duplicates)
    - 'replace': Clear collection first, then add all cards
    """
    db = _get_db(request)
    user_db = _get_user_db(request)

    # Parse the text server-side
    parsed_cards = parse_card_list(body.text)

    if not parsed_cards:
        return ImportCollectionResponse(
            added_count=0,
            total_cards=0,
            errors=["No valid card entries found in text"],
            cards_with_printings=[],
        )

    # If replace mode, clear the collection first
    if body.mode == "replace":
        await user_db.clear_collection()

    errors: list[str] = []
    cards_with_printings: list[ImportedCardInfo] = []

    # Build batch of cards to insert
    # Format: (card_name, quantity, foil_quantity, set_code, collector_number)
    batch: list[tuple[str, int, int, str | None, str | None]] = []

    # First pass: resolve card names and build batch
    # Track names that need printing counts (those without set_code)
    names_needing_printings: list[str] = []
    resolved_cards: list[tuple[str, int, bool, str | None, str | None]] = []

    for parsed in parsed_cards:
        card_name = parsed.card_name

        # If no card name but we have set_code and collector_number, look it up
        if not card_name and parsed.set_code and parsed.collector_number:
            looked_up = await db.get_card_by_set_and_number(
                parsed.set_code, parsed.collector_number
            )
            if looked_up:
                card_name = looked_up.name
            else:
                errors.append(
                    f"Card not found: {parsed.set_code.upper()} #{parsed.collector_number}"
                )
                continue

        if not card_name:
            continue

        # Determine quantities
        quantity = parsed.quantity if not parsed.foil else 0
        foil_quantity = parsed.quantity if parsed.foil else 0

        batch.append(
            (
                card_name,
                quantity,
                foil_quantity,
                parsed.set_code,
                parsed.collector_number,
            )
        )

        # Track for printing count lookup (only cards without specific printing)
        if not parsed.set_code:
            names_needing_printings.append(card_name)
            resolved_cards.append(
                (card_name, parsed.quantity, parsed.foil, parsed.set_code, parsed.collector_number)
            )

    # Batch lookup printing counts (fixes N+1 query)
    printings_counts: dict[str, int] = {}
    if names_needing_printings:
        with contextlib.suppress(Exception):
            printings_counts = await db.get_printings_count_batch(names_needing_printings)

    # Build cards_with_printings from batch result
    for card_name, quantity, foil, _set_code, _collector_number in resolved_cards:
        count = printings_counts.get(card_name.lower(), 0)
        if count > 1:
            cards_with_printings.append(
                ImportedCardInfo(
                    card_name=card_name,
                    quantity=quantity,
                    foil=foil,
                    printings_count=count,
                )
            )

    # Batch insert all cards
    added_count = await user_db.add_to_collection_batch(batch)
    total_cards = sum(
        parsed.quantity
        for parsed in parsed_cards
        if parsed.card_name or (parsed.set_code and parsed.collector_number)
    )

    return ImportCollectionResponse(
        added_count=added_count,
        total_cards=total_cards,
        errors=errors,
        cards_with_printings=cards_with_printings,
    )


@router.get("/value", response_model=PriceCollectionResponse)
async def get_collection_value(request: Request) -> PriceCollectionResponse:
    """Get pricing for the entire user collection.

    Reads all cards from user_data.sqlite and prices them using the card database.
    This is more efficient than passing cards through the API since it reads
    directly from the user's collection with set_code and collector_number
    for accurate printing-specific prices.
    """
    db = _get_db(request)
    user_db = _get_user_db(request)

    # Get all collection cards (no limit)
    collection_cards = await user_db.get_collection_cards(limit=100000, offset=0)

    if not collection_cards:
        return PriceCollectionResponse(
            cards=[],
            total_value=0.0,
            total_value_foil=0.0,
            cards_with_prices=0,
            cards_without_prices=0,
            median_price=0.0,
            top_cards=[],
        )

    # Convert to ParsedCardInput format for pricing
    # Create separate entries for regular and foil quantities to price them correctly
    parsed_cards: list[ParsedCardInput] = []
    for card in collection_cards:
        # Add regular copies (non-foil)
        if card.quantity > 0:
            parsed_cards.append(
                ParsedCardInput(
                    card_name=card.card_name,
                    quantity=card.quantity,
                    foil=False,
                    set_code=card.set_code,
                    collector_number=card.collector_number,
                )
            )
        # Add foil copies separately
        if card.foil_quantity > 0:
            parsed_cards.append(
                ParsedCardInput(
                    card_name=card.card_name,
                    quantity=card.foil_quantity,
                    foil=True,
                    set_code=card.set_code,
                    collector_number=card.collector_number,
                )
            )

    # Price the collection
    result = await price_collection(db, parsed_cards)

    # Convert to API response
    priced_cards = [
        PricedCard(
            card_name=c.card_name,
            quantity=c.quantity,
            foil=c.foil,
            set_code=c.set_code,
            collector_number=c.collector_number,
            price_usd=c.price_usd,
            price_usd_foil=c.price_usd_foil,
            total_value=c.total_value,
        )
        for c in result.cards
    ]

    top_cards = [TopCard(name=name, price=price) for name, price in result.top_cards]

    return PriceCollectionResponse(
        cards=priced_cards,
        total_value=result.total_value,
        total_value_foil=result.total_value_foil,
        cards_with_prices=result.cards_with_prices,
        cards_without_prices=result.cards_without_prices,
        median_price=result.median_price,
        top_cards=top_cards,
    )
