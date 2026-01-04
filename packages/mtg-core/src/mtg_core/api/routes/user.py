"""User data API routes (decks, collections)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from mtg_core.data.models import (
    AnalyzeDeckInput,
    ColorAnalysisResult,
    DeckCardInput,
    DeckHealthResult,
    ManaCurveResult,
    PriceAnalysisResult,
)
from mtg_core.tools import deck as deck_tools

if TYPE_CHECKING:
    from mtg_core.data.database import UnifiedDatabase, UserDatabase

router = APIRouter()


class CreateDeckRequest(BaseModel):
    """Request to create a new deck."""

    name: str
    format: str | None = None
    commander: str | None = None
    description: str | None = None


class UpdateDeckRequest(BaseModel):
    """Request to update deck metadata."""

    name: str | None = None
    format: str | None = None
    commander: str | None = None
    description: str | None = None


class AddCardRequest(BaseModel):
    """Request to add a card to a deck."""

    card_name: str
    quantity: int = 1
    is_sideboard: bool = False
    is_maybeboard: bool = False
    is_commander: bool = False
    set_code: str | None = None
    collector_number: str | None = None


class UpdateCardQuantityRequest(BaseModel):
    """Request to update card quantity in a deck."""

    quantity: int


class DeckSummaryResponse(BaseModel):
    """Summary of a deck for listing."""

    id: int
    name: str
    format: str | None
    card_count: int
    sideboard_count: int
    maybeboard_count: int
    commander: str | None
    updated_at: str | None


class DeckCardResponse(BaseModel):
    """A card in a deck with enriched card data."""

    card_name: str
    quantity: int
    is_sideboard: bool
    is_maybeboard: bool
    is_commander: bool
    set_code: str | None
    collector_number: str | None
    # Enriched card data from MTG database
    mana_cost: str | None = None
    cmc: float | None = None
    type_line: str | None = None
    rarity: str | None = None
    flavor_name: str | None = None
    colors: list[str] | None = None
    image_small: str | None = None


class DeckResponse(BaseModel):
    """Full deck with cards."""

    id: int
    name: str
    format: str | None
    commander: str | None
    description: str | None
    card_count: int
    sideboard_count: int
    maybeboard_count: int
    updated_at: str | None
    cards: list[DeckCardResponse]


class CreateDeckResponse(BaseModel):
    """Response after creating a deck."""

    id: int


class DeleteDeckResponse(BaseModel):
    """Response after deleting a deck."""

    deleted: bool


class AddCardResponse(BaseModel):
    """Response after adding a card."""

    success: bool


class RemoveCardResponse(BaseModel):
    """Response after removing a card."""

    removed: bool


class UpdateCardResponse(BaseModel):
    """Response after updating card quantity."""

    success: bool


def _get_user_db(request: Request) -> UserDatabase:
    """Get user database from app state."""
    user_db: UserDatabase | None = request.app.state.db_manager.user
    if user_db is None:
        raise HTTPException(status_code=503, detail="User database not available")
    return user_db


def _get_mtg_db(request: Request) -> UnifiedDatabase:
    """Get MTG database from app state."""
    db: UnifiedDatabase = request.app.state.db_manager.db
    return db


@router.get("/decks", response_model=list[DeckSummaryResponse])
async def list_decks(request: Request) -> list[DeckSummaryResponse]:
    """List all decks."""
    user_db = _get_user_db(request)
    decks = await user_db.list_decks()
    return [
        DeckSummaryResponse(
            id=deck.id,
            name=deck.name,
            format=deck.format,
            card_count=deck.card_count,
            sideboard_count=deck.sideboard_count,
            maybeboard_count=deck.maybeboard_count,
            commander=deck.commander,
            updated_at=deck.updated_at.isoformat() if deck.updated_at else None,
        )
        for deck in decks
    ]


@router.post("/decks", response_model=CreateDeckResponse)
async def create_deck(request: Request, body: CreateDeckRequest) -> CreateDeckResponse:
    """Create a new deck."""
    user_db = _get_user_db(request)
    deck_id = await user_db.create_deck(
        name=body.name,
        format=body.format,
        commander=body.commander,
        description=body.description,
    )

    # If a commander was specified, add it as a card with is_commander=True
    if body.commander:
        await user_db.add_card(
            deck_id=deck_id,
            card_name=body.commander,
            quantity=1,
            sideboard=False,
            is_commander=True,
        )

    return CreateDeckResponse(id=deck_id)


@router.get("/decks/{deck_id}", response_model=DeckResponse)
async def get_deck(request: Request, deck_id: int) -> DeckResponse:
    """Get a deck with all its cards, enriched with card data."""
    user_db = _get_user_db(request)
    mtg_db = _get_mtg_db(request)

    deck = await user_db.get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

    cards = await user_db.get_deck_cards(deck_id)

    # Batch-load card data from MTG database
    card_names = [c.card_name for c in cards]
    cards_by_name = await mtg_db.get_cards_by_names(card_names) if card_names else {}

    card_count = sum(c.quantity for c in cards if not c.is_sideboard and not c.is_maybeboard)
    sideboard_count = sum(c.quantity for c in cards if c.is_sideboard)
    maybeboard_count = sum(c.quantity for c in cards if c.is_maybeboard)

    # Build enriched card responses
    enriched_cards: list[DeckCardResponse] = []
    for card in cards:
        # Lookup uses lowercase key
        card_data = cards_by_name.get(card.card_name.lower())

        enriched_cards.append(
            DeckCardResponse(
                card_name=card.card_name,
                quantity=card.quantity,
                is_sideboard=card.is_sideboard,
                is_maybeboard=card.is_maybeboard,
                is_commander=card.is_commander,
                set_code=card.set_code,
                collector_number=card.collector_number,
                # Enriched data from MTG database
                mana_cost=card_data.mana_cost if card_data else None,
                cmc=card_data.cmc if card_data else None,
                type_line=card_data.type if card_data else None,
                rarity=card_data.rarity if card_data else None,
                flavor_name=card_data.flavor_name if card_data else None,
                colors=card_data.colors if card_data else None,
                image_small=card_data.image_small if card_data else None,
            )
        )

    return DeckResponse(
        id=deck.id,
        name=deck.name,
        format=deck.format,
        commander=deck.commander,
        description=deck.description,
        card_count=card_count,
        sideboard_count=sideboard_count,
        maybeboard_count=maybeboard_count,
        updated_at=deck.updated_at.isoformat() if deck.updated_at else None,
        cards=enriched_cards,
    )


@router.put("/decks/{deck_id}", response_model=dict)
async def update_deck(request: Request, deck_id: int, body: UpdateDeckRequest) -> dict[str, bool]:
    """Update deck metadata."""
    user_db = _get_user_db(request)

    deck = await user_db.get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

    await user_db.update_deck(
        deck_id=deck_id,
        name=body.name,
        format=body.format,
        commander=body.commander,
        description=body.description,
    )
    return {"success": True}


@router.delete("/decks/{deck_id}", response_model=DeleteDeckResponse)
async def delete_deck(request: Request, deck_id: int) -> DeleteDeckResponse:
    """Delete a deck."""
    user_db = _get_user_db(request)
    deleted = await user_db.delete_deck(deck_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")
    return DeleteDeckResponse(deleted=True)


@router.post("/decks/{deck_id}/cards", response_model=AddCardResponse)
async def add_card_to_deck(request: Request, deck_id: int, body: AddCardRequest) -> AddCardResponse:
    """Add a card to a deck."""
    user_db = _get_user_db(request)

    deck = await user_db.get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

    await user_db.add_card(
        deck_id=deck_id,
        card_name=body.card_name,
        quantity=body.quantity,
        sideboard=body.is_sideboard,
        maybeboard=body.is_maybeboard,
        is_commander=body.is_commander,
        set_code=body.set_code,
        collector_number=body.collector_number,
    )
    return AddCardResponse(success=True)


@router.delete("/decks/{deck_id}/cards/{card_name}", response_model=RemoveCardResponse)
async def remove_card_from_deck(
    request: Request,
    deck_id: int,
    card_name: str,
    sideboard: bool = False,
    maybeboard: bool = False,
) -> RemoveCardResponse:
    """Remove a card from a deck."""
    user_db = _get_user_db(request)

    deck = await user_db.get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

    removed = await user_db.remove_card(deck_id, card_name, sideboard, maybeboard)
    return RemoveCardResponse(removed=removed)


@router.put("/decks/{deck_id}/cards/{card_name}", response_model=UpdateCardResponse)
async def update_card_quantity(
    request: Request,
    deck_id: int,
    card_name: str,
    body: UpdateCardQuantityRequest,
    sideboard: bool = False,
    maybeboard: bool = False,
) -> UpdateCardResponse:
    """Update card quantity in a deck."""
    user_db = _get_user_db(request)

    deck = await user_db.get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

    await user_db.set_quantity(deck_id, card_name, body.quantity, sideboard, maybeboard)
    return UpdateCardResponse(success=True)


class MoveCardRequest(BaseModel):
    """Request to move a card between mainboard/sideboard/maybeboard."""

    from_sideboard: bool = False
    from_maybeboard: bool = False
    to_sideboard: bool = False
    to_maybeboard: bool = False


class MoveCardResponse(BaseModel):
    """Response after moving a card."""

    success: bool


@router.post("/decks/{deck_id}/cards/{card_name}/move", response_model=MoveCardResponse)
async def move_card_in_deck(
    request: Request, deck_id: int, card_name: str, body: MoveCardRequest
) -> MoveCardResponse:
    """Move a card between mainboard, sideboard, and maybeboard."""
    user_db = _get_user_db(request)

    deck = await user_db.get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

    await user_db.move_card(
        deck_id=deck_id,
        card_name=card_name,
        from_sideboard=body.from_sideboard,
        from_maybeboard=body.from_maybeboard,
        to_sideboard=body.to_sideboard,
        to_maybeboard=body.to_maybeboard,
    )
    return MoveCardResponse(success=True)


@router.get("/decks/{deck_id}/analyze/health", response_model=DeckHealthResult)
async def analyze_deck_health_by_id(request: Request, deck_id: int) -> DeckHealthResult:
    """Analyze deck health by deck ID - fetches cards directly from database."""
    user_db = _get_user_db(request)
    mtg_db = _get_mtg_db(request)

    deck = await user_db.get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

    cards = await user_db.get_deck_cards(deck_id)

    # Convert to deck analysis input format
    deck_input = AnalyzeDeckInput(
        cards=[
            DeckCardInput(name=c.card_name, quantity=c.quantity, sideboard=c.is_sideboard)
            for c in cards
        ]
    )

    return await deck_tools.analyze_deck_health(mtg_db, deck_input, deck.format)


@router.get("/decks/{deck_id}/analyze/mana-curve", response_model=ManaCurveResult)
async def analyze_deck_mana_curve_by_id(request: Request, deck_id: int) -> ManaCurveResult:
    """Analyze deck mana curve by deck ID."""
    user_db = _get_user_db(request)
    mtg_db = _get_mtg_db(request)

    deck = await user_db.get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

    cards = await user_db.get_deck_cards(deck_id)

    deck_input = AnalyzeDeckInput(
        cards=[
            DeckCardInput(name=c.card_name, quantity=c.quantity, sideboard=c.is_sideboard)
            for c in cards
        ]
    )

    return await deck_tools.analyze_mana_curve(mtg_db, deck_input)


@router.get("/decks/{deck_id}/analyze/colors", response_model=ColorAnalysisResult)
async def analyze_deck_colors_by_id(request: Request, deck_id: int) -> ColorAnalysisResult:
    """Analyze deck colors by deck ID."""
    user_db = _get_user_db(request)
    mtg_db = _get_mtg_db(request)

    deck = await user_db.get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

    cards = await user_db.get_deck_cards(deck_id)

    deck_input = AnalyzeDeckInput(
        cards=[
            DeckCardInput(name=c.card_name, quantity=c.quantity, sideboard=c.is_sideboard)
            for c in cards
        ]
    )

    return await deck_tools.analyze_colors(mtg_db, deck_input)


@router.get("/decks/{deck_id}/analyze/price", response_model=PriceAnalysisResult)
async def analyze_deck_price_by_id(request: Request, deck_id: int) -> PriceAnalysisResult:
    """Analyze deck price by deck ID."""
    user_db = _get_user_db(request)
    mtg_db = _get_mtg_db(request)

    deck = await user_db.get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

    cards = await user_db.get_deck_cards(deck_id)

    deck_input = AnalyzeDeckInput(
        cards=[
            DeckCardInput(name=c.card_name, quantity=c.quantity, sideboard=c.is_sideboard)
            for c in cards
        ]
    )

    return await deck_tools.analyze_deck_price(mtg_db, deck_input)
