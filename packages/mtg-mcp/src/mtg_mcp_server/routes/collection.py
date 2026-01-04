"""Collection tool routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP

from mtg_mcp_server.context import ToolContext, get_app


@dataclass
class CollectionCard:
    """Collection card data for API response."""

    card_name: str
    quantity: int
    foil_quantity: int
    set_code: str | None
    collector_number: str | None
    added_at: str


@dataclass
class CollectionStats:
    """Collection statistics."""

    unique_cards: int
    total_cards: int
    total_foils: int


@dataclass
class CollectionWithStats:
    """Collection cards with statistics."""

    cards: list[CollectionCard]
    stats: CollectionStats
    total: int
    page: int
    page_size: int


@dataclass
class CollectionStatsDetailed:
    """Detailed collection statistics for visualization."""

    unique_cards: int
    total_cards: int
    total_foils: int
    color_distribution: dict[str, int]
    type_distribution: dict[str, int]
    rarity_distribution: dict[str, int]
    mana_curve: dict[int, int]
    top_sets: list[tuple[str, int]]
    average_cmc: float


def register(mcp: FastMCP) -> None:
    """Register collection tools with the MCP server."""

    @mcp.tool()
    async def get_collection(
        ctx: ToolContext,
        page: Annotated[int, "Page number"] = 1,
        page_size: Annotated[int, "Results per page (max 100)"] = 50,
    ) -> CollectionWithStats:
        """Get collection cards with pagination and statistics."""
        app = get_app(ctx)

        if app.user is None:
            return CollectionWithStats(
                cards=[],
                stats=CollectionStats(unique_cards=0, total_cards=0, total_foils=0),
                total=0,
                page=page,
                page_size=page_size,
            )

        offset = (page - 1) * page_size
        rows = await app.user.get_collection_cards(limit=page_size, offset=offset)

        cards = [
            CollectionCard(
                card_name=row.card_name,
                quantity=row.quantity,
                foil_quantity=row.foil_quantity,
                set_code=row.set_code,
                collector_number=row.collector_number,
                added_at=row.added_at.isoformat(),
            )
            for row in rows
        ]

        unique = await app.user.get_collection_count()
        total = await app.user.get_collection_total_cards()
        foils = await app.user.get_collection_foil_total()

        return CollectionWithStats(
            cards=cards,
            stats=CollectionStats(unique_cards=unique, total_cards=total, total_foils=foils),
            total=unique,
            page=page,
            page_size=page_size,
        )

    @mcp.tool()
    async def get_collection_stats(ctx: ToolContext) -> CollectionStatsDetailed:
        """Get detailed collection statistics for visualization."""
        app = get_app(ctx)

        if app.user is None:
            return CollectionStatsDetailed(
                unique_cards=0,
                total_cards=0,
                total_foils=0,
                color_distribution={},
                type_distribution={},
                rarity_distribution={},
                mana_curve={},
                top_sets=[],
                average_cmc=0.0,
            )

        # Get basic stats
        unique = await app.user.get_collection_count()
        total = await app.user.get_collection_total_cards()
        foils = await app.user.get_collection_foil_total()

        # Get all collection card names
        card_names = await app.user.get_collection_card_names()

        # Get card data from main database for statistics
        color_dist: dict[str, int] = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "C": 0}
        type_dist: dict[str, int] = {}
        rarity_dist: dict[str, int] = {}
        mana_curve: dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
        set_counts: dict[str, int] = {}
        total_cmc = 0.0
        non_land_count = 0

        # Get collection rows to know quantities
        all_rows = await app.user.get_collection_cards(limit=10000, offset=0)
        name_to_qty: dict[str, int] = {}
        for row in all_rows:
            name_to_qty[row.card_name] = row.quantity + row.foil_quantity
            if row.set_code:
                set_counts[row.set_code] = set_counts.get(row.set_code, 0) + 1

        # Batch query card data
        if card_names:
            for card_name in card_names:
                card = await app.db.get_card_by_name(card_name)
                if card is None:
                    continue

                qty = name_to_qty.get(card_name, 1)

                # Colors
                if card.colors:
                    for color in card.colors:
                        if color in color_dist:
                            color_dist[color] += qty
                else:
                    color_dist["C"] += qty

                # Card type
                card_type = "Other"
                type_line = card.type.lower() if card.type else ""
                for t in [
                    "creature",
                    "instant",
                    "sorcery",
                    "artifact",
                    "enchantment",
                    "planeswalker",
                    "land",
                ]:
                    if t in type_line:
                        card_type = t.capitalize()
                        break
                type_dist[card_type] = type_dist.get(card_type, 0) + qty

                # Rarity
                rarity = card.rarity.capitalize() if card.rarity else "Common"
                rarity_dist[rarity] = rarity_dist.get(rarity, 0) + qty

                # Mana curve (skip lands)
                if "land" not in type_line:
                    cmc_val = int(card.cmc) if card.cmc else 0
                    cmc_key = min(cmc_val, 7)
                    mana_curve[cmc_key] = mana_curve.get(cmc_key, 0) + qty
                    total_cmc += (card.cmc or 0) * qty
                    non_land_count += qty

        # Top sets
        top_sets = sorted(set_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        avg_cmc = total_cmc / non_land_count if non_land_count > 0 else 0.0

        return CollectionStatsDetailed(
            unique_cards=unique,
            total_cards=total,
            total_foils=foils,
            color_distribution=color_dist,
            type_distribution=type_dist,
            rarity_distribution=rarity_dist,
            mana_curve=mana_curve,
            top_sets=top_sets,
            average_cmc=round(avg_cmc, 2),
        )

    @mcp.tool()
    async def add_to_collection(
        ctx: ToolContext,
        card_name: Annotated[str, "Card name"],
        quantity: Annotated[int, "Number of copies"] = 1,
        foil_quantity: Annotated[int, "Number of foil copies"] = 0,
        set_code: Annotated[str | None, "Set code"] = None,
        collector_number: Annotated[str | None, "Collector number"] = None,
    ) -> dict[str, Any]:
        """Add a card to the collection."""
        app = get_app(ctx)

        if app.user is None:
            return {"success": False, "error": "User database not available"}

        await app.user.add_to_collection(
            card_name=card_name,
            quantity=quantity,
            foil_quantity=foil_quantity,
            set_code=set_code,
            collector_number=collector_number,
        )

        return {"success": True, "card_name": card_name}

    @mcp.tool()
    async def remove_from_collection(
        ctx: ToolContext,
        card_name: Annotated[str, "Card name"],
    ) -> dict[str, Any]:
        """Remove a card from the collection."""
        app = get_app(ctx)

        if app.user is None:
            return {"success": False, "error": "User database not available"}

        success = await app.user.remove_from_collection(card_name)
        return {"success": success, "card_name": card_name}

    @mcp.tool()
    async def update_collection_quantity(
        ctx: ToolContext,
        card_name: Annotated[str, "Card name"],
        quantity: Annotated[int, "New quantity"],
        foil_quantity: Annotated[int | None, "New foil quantity"] = None,
    ) -> dict[str, Any]:
        """Update the quantity of a card in the collection."""
        app = get_app(ctx)

        if app.user is None:
            return {"success": False, "error": "User database not available"}

        await app.user.set_collection_quantity(
            card_name=card_name,
            quantity=quantity,
            foil_quantity=foil_quantity if foil_quantity is not None else 0,
        )
        return {"success": True, "card_name": card_name}
