"""Set API routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from mtg_core.data.models import (
    CardSummary,
    SearchCardsInput,
    SetDetail,
    SetsResponse,
)
from mtg_core.exceptions import SetNotFoundError
from mtg_core.tools import sets as sets_tools
from mtg_core.tools.set_analysis import (
    MechanicInfo,
    PriceTierBreakdown,
    RarityDistribution,
    SetValueSummary,
    TribalTheme,
    TypeDistribution,
    analyze_set,
)

if TYPE_CHECKING:
    from mtg_core.data.database import UnifiedDatabase

router = APIRouter()


def _get_db(request: Request) -> UnifiedDatabase:
    """Get database from app state."""
    db: UnifiedDatabase = request.app.state.db_manager.db
    return db


class SetCardsResponse(BaseModel):
    """Response for cards in a set."""

    set_code: str
    set_name: str
    cards: list[CardSummary]
    page: int
    page_size: int
    total_count: int


class PriceTierBreakdownResponse(BaseModel):
    """Price tier distribution for API response."""

    bulk: int = Field(description="Cards $0-1")
    playable: int = Field(description="Cards $1-10")
    chase: int = Field(description="Cards $10-50")
    premium: int = Field(description="Cards $50+")


class SetValueSummaryResponse(BaseModel):
    """Price/value summary for API response."""

    total_value: float
    total_value_foil: float
    average_value: float
    median_value: float
    chase_card_count: int
    top_cards: list[tuple[str, float, bool]]
    top5_concentration: float
    price_tiers: PriceTierBreakdownResponse


class MechanicInfoResponse(BaseModel):
    """Mechanic information for API response."""

    name: str
    card_count: int
    description: str
    top_cards: list[str]


class TribalThemeResponse(BaseModel):
    """Tribal theme for API response."""

    creature_type: str
    card_count: int
    percentage: float


class TypeDistributionResponse(BaseModel):
    """Card type distribution for API response."""

    creatures: int
    instants: int
    sorceries: int
    enchantments: int
    artifacts: int
    lands: int
    planeswalkers: int
    battles: int
    other: int


class RarityDistributionResponse(BaseModel):
    """Rarity distribution for API response."""

    mythic: int
    rare: int
    uncommon: int
    common: int
    special: int


class SetAnalysisResponse(BaseModel):
    """Complete set analysis response."""

    set_code: str
    set_name: str
    total_cards: int
    value_summary: SetValueSummaryResponse
    mechanics: list[MechanicInfoResponse]
    tribal_themes: list[TribalThemeResponse]
    type_distribution: TypeDistributionResponse
    rarity_distribution: RarityDistributionResponse


def _convert_price_tiers(tiers: PriceTierBreakdown) -> PriceTierBreakdownResponse:
    """Convert dataclass to Pydantic model."""
    return PriceTierBreakdownResponse(
        bulk=tiers.bulk,
        playable=tiers.playable,
        chase=tiers.chase,
        premium=tiers.premium,
    )


def _convert_value_summary(summary: SetValueSummary) -> SetValueSummaryResponse:
    """Convert dataclass to Pydantic model."""
    return SetValueSummaryResponse(
        total_value=summary.total_value,
        total_value_foil=summary.total_value_foil,
        average_value=summary.average_value,
        median_value=summary.median_value,
        chase_card_count=summary.chase_card_count,
        top_cards=summary.top_cards,
        top5_concentration=summary.top5_concentration,
        price_tiers=_convert_price_tiers(summary.price_tiers),
    )


def _convert_mechanic(mechanic: MechanicInfo) -> MechanicInfoResponse:
    """Convert dataclass to Pydantic model."""
    return MechanicInfoResponse(
        name=mechanic.name,
        card_count=mechanic.card_count,
        description=mechanic.description,
        top_cards=mechanic.top_cards,
    )


def _convert_tribal(tribal: TribalTheme) -> TribalThemeResponse:
    """Convert dataclass to Pydantic model."""
    return TribalThemeResponse(
        creature_type=tribal.creature_type,
        card_count=tribal.card_count,
        percentage=tribal.percentage,
    )


def _convert_type_distribution(dist: TypeDistribution) -> TypeDistributionResponse:
    """Convert dataclass to Pydantic model."""
    return TypeDistributionResponse(
        creatures=dist.creatures,
        instants=dist.instants,
        sorceries=dist.sorceries,
        enchantments=dist.enchantments,
        artifacts=dist.artifacts,
        lands=dist.lands,
        planeswalkers=dist.planeswalkers,
        battles=dist.battles,
        other=dist.other,
    )


def _convert_rarity_distribution(dist: RarityDistribution) -> RarityDistributionResponse:
    """Convert dataclass to Pydantic model."""
    return RarityDistributionResponse(
        mythic=dist.mythic,
        rare=dist.rare,
        uncommon=dist.uncommon,
        common=dist.common,
        special=dist.special,
    )


@router.get("", response_model=SetsResponse)
async def list_sets(
    request: Request,
    name: str | None = Query(default=None, description="Filter by set name"),
    set_type: str | None = Query(default=None, description="Filter by set type"),
    include_online_only: bool = Query(default=True, description="Include online-only sets"),
) -> SetsResponse:
    """List all sets with optional filters."""
    db = _get_db(request)
    return await sets_tools.get_sets(
        db,
        name=name,
        set_type=set_type,
        include_online_only=include_online_only,
    )


@router.get("/{code}", response_model=SetDetail)
async def get_set(
    request: Request,
    code: str,
) -> SetDetail:
    """Get detailed information about a specific set."""
    db = _get_db(request)
    try:
        return await sets_tools.get_set(db, code)
    except SetNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/{code}/cards", response_model=SetCardsResponse)
async def get_set_cards(
    request: Request,
    code: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=25, ge=1, le=100, description="Cards per page"),
) -> SetCardsResponse:
    """Get cards in a set with pagination."""
    db = _get_db(request)

    # Verify set exists first
    try:
        mtg_set = await db.get_set(code)
    except SetNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    # Search for cards in this set
    filters = SearchCardsInput(set_code=code, page=page, page_size=page_size)
    cards, total_count = await db.search_cards(filters)

    # Convert to CardSummary
    card_summaries = [
        CardSummary(
            uuid=card.uuid,
            name=card.name,
            flavor_name=card.flavor_name,
            mana_cost=card.mana_cost,
            cmc=card.cmc,
            type=card.type,
            colors=card.colors or [],
            color_identity=card.color_identity or [],
            rarity=card.rarity,
            set_code=card.set_code,
            collector_number=card.number,
            keywords=card.keywords or [],
            power=card.power,
            toughness=card.toughness,
            image=card.image_normal,
            image_small=card.image_small,
            price_usd=card.get_price_usd() if hasattr(card, "get_price_usd") else None,
            purchase_link=card.purchase_tcgplayer,
        )
        for card in cards
    ]

    return SetCardsResponse(
        set_code=mtg_set.code,
        set_name=mtg_set.name,
        cards=card_summaries,
        page=page,
        page_size=page_size,
        total_count=total_count,
    )


@router.get("/{code}/analysis", response_model=SetAnalysisResponse)
async def get_set_analysis(
    request: Request,
    code: str,
) -> SetAnalysisResponse:
    """Get complete analysis of a set including value, mechanics, tribal themes, and composition."""
    db = _get_db(request)

    analysis = await analyze_set(db, code)
    if analysis is None:
        raise HTTPException(status_code=404, detail=f"Set not found: {code}")

    return SetAnalysisResponse(
        set_code=analysis.set_code,
        set_name=analysis.set_name,
        total_cards=analysis.total_cards,
        value_summary=_convert_value_summary(analysis.value_summary),
        mechanics=[_convert_mechanic(m) for m in analysis.mechanics],
        tribal_themes=[_convert_tribal(t) for t in analysis.tribal_themes],
        type_distribution=_convert_type_distribution(analysis.type_distribution),
        rarity_distribution=_convert_rarity_distribution(analysis.rarity_distribution),
    )
