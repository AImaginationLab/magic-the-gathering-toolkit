"""Shared test fixtures and utilities for MTG Spellbook tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    from mtg_core.data.database import MTGDatabase, ScryfallDatabase
    from mtg_spellbook.deck_manager import DeckManager


@pytest.fixture
def sample_card_detail() -> Any:
    """Sample CardDetail for testing."""
    from mtg_core.data.models.responses import CardDetail, Prices

    return CardDetail(
        name="Lightning Bolt",
        mana_cost="{R}",
        type="Instant",
        text="Lightning Bolt deals 3 damage to any target.",
        power=None,
        toughness=None,
        colors=["R"],
        color_identity=["R"],
        keywords=[],
        cmc=1.0,
        rarity="common",
        set_code="LEA",
        number="161",
        artist="Christopher Rush",
        flavor=None,
        loyalty=None,
        uuid="test-uuid-123",
        legalities={
            "standard": "not_legal",
            "modern": "legal",
            "legacy": "legal",
            "vintage": "legal",
            "commander": "legal",
        },
        prices=Prices(usd=2.50),
        edhrec_rank=None,
    )


@pytest.fixture
def sample_creature_card() -> Any:
    """Sample creature CardDetail for testing."""
    from mtg_core.data.models.responses import CardDetail, Prices

    return CardDetail(
        name="Birds of Paradise",
        mana_cost="{G}",
        type="Creature — Bird",
        text="Flying\n{T}: Add one mana of any color.",
        power="0",
        toughness="1",
        colors=["G"],
        color_identity=["G"],
        keywords=["Flying"],
        cmc=1.0,
        rarity="rare",
        set_code="LEA",
        number="162",
        artist="Mark Poole",
        flavor=None,
        loyalty=None,
        uuid="test-uuid-456",
        legalities={
            "standard": "not_legal",
            "modern": "not_legal",
            "legacy": "legal",
            "vintage": "legal",
            "commander": "legal",
        },
        prices=Prices(usd=8.50),
        edhrec_rank=100,
    )


@pytest.fixture
def sample_search_results(sample_card_detail: Any, sample_creature_card: Any) -> list[Any]:
    """Sample search results for testing."""
    return [sample_card_detail, sample_creature_card]


@pytest.fixture
def mock_mtg_database(sample_card_detail: Any, sample_search_results: list[Any]) -> MTGDatabase:
    """Mock MTGDatabase with common operations."""
    mock_db = AsyncMock()

    mock_db.get_card_by_name = AsyncMock(return_value=sample_card_detail)
    mock_db.get_card_by_uuid = AsyncMock(return_value=sample_card_detail)
    mock_db.search_cards = AsyncMock(
        return_value=(sample_search_results, len(sample_search_results))
    )
    mock_db.get_random_card = AsyncMock(return_value=sample_card_detail)
    mock_db.get_database_stats = AsyncMock(return_value={"unique_cards": 25000, "total_sets": 500})
    mock_db.get_keywords = AsyncMock(return_value=["Flying", "First Strike", "Trample", "Haste"])
    mock_db.get_all_sets = AsyncMock(return_value=[])
    mock_db.close = AsyncMock()

    return mock_db


@pytest.fixture
def mock_scryfall_database() -> ScryfallDatabase:
    """Mock ScryfallDatabase with common operations."""
    mock_db = AsyncMock()

    mock_db.get_card_images = AsyncMock(return_value=None)
    mock_db.get_card_prices = AsyncMock(return_value=None)
    mock_db.close = AsyncMock()

    return mock_db


@pytest.fixture
def mock_deck_manager() -> DeckManager:
    """Mock DeckManager for testing deck operations."""
    mock_manager = AsyncMock()

    mock_manager.create_deck = AsyncMock(return_value=1)
    mock_manager.list_decks = AsyncMock(return_value=[])
    mock_manager.get_deck = AsyncMock(return_value=None)
    mock_manager.add_card = AsyncMock()
    mock_manager.remove_card = AsyncMock()
    mock_manager.delete_deck = AsyncMock()

    return mock_manager


@pytest.fixture
def mock_database_context(
    mock_mtg_database: MTGDatabase,
    mock_scryfall_database: ScryfallDatabase,
    mock_deck_manager: DeckManager,
) -> MagicMock:
    """Mock DatabaseContext for testing."""
    mock_ctx = MagicMock()

    mock_ctx.get_db = AsyncMock(return_value=mock_mtg_database)
    mock_ctx.get_scryfall = AsyncMock(return_value=mock_scryfall_database)
    mock_ctx.get_deck_manager = AsyncMock(return_value=mock_deck_manager)
    mock_ctx.get_keywords = AsyncMock(return_value=["Flying", "First Strike", "Trample", "Haste"])
    mock_ctx.close = AsyncMock()

    return mock_ctx


class AsyncContextManagerMock:
    """Helper for mocking async context managers."""

    def __init__(self, return_value: Any) -> None:
        self.return_value = return_value

    async def __aenter__(self) -> Any:
        return self.return_value

    async def __aexit__(self, *args: Any) -> None:
        pass


@pytest.fixture
def async_context_manager_factory() -> type[AsyncContextManagerMock]:
    """Factory for creating async context manager mocks."""
    return AsyncContextManagerMock


@pytest.fixture
def mock_app_with_database(
    mock_mtg_database: MTGDatabase,
    mock_scryfall_database: ScryfallDatabase,
    mock_deck_manager: DeckManager,
) -> Any:
    """Factory for creating MTGSpellbook with mocked database dependencies."""

    def create_app() -> Any:
        from mtg_spellbook.app import MTGSpellbook

        app = MTGSpellbook()
        app._db = mock_mtg_database
        app._scryfall = mock_scryfall_database
        app._deck_manager = mock_deck_manager
        return app

    return create_app


@pytest.fixture
def sample_search_result(sample_card_detail: Any) -> Any:
    """Sample SearchResult for testing."""
    from mtg_core.data.models.responses import CardSummary, SearchResult

    summary = CardSummary(
        name=sample_card_detail.name,
        mana_cost=sample_card_detail.mana_cost,
        type=sample_card_detail.type,
        power=sample_card_detail.power,
        toughness=sample_card_detail.toughness,
        colors=sample_card_detail.colors,
        cmc=sample_card_detail.cmc,
        rarity=sample_card_detail.rarity,
        set_code=sample_card_detail.set_code,
    )

    return SearchResult(cards=[summary], page=1, page_size=25, total_count=1)
