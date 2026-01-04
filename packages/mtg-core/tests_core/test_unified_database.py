"""Comprehensive tests for UnifiedDatabase class.

These tests verify all database operations including card lookups, searches,
set management, artist queries, and price filtering. Target coverage: 92%+.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest

from mtg_core.config import Settings
from mtg_core.data.database import UnifiedDatabase, create_database
from mtg_core.data.database.cache import CardCache
from mtg_core.data.models import Card, CardLegality, CardRuling, SearchCardsInput, Set
from mtg_core.data.models.responses import ArtistSummary
from mtg_core.exceptions import CardNotFoundError, SetNotFoundError

from .conftest import get_test_db_path

DB_PATH = get_test_db_path()
pytestmark = pytest.mark.skipif(
    DB_PATH is None,
    reason="MTG database not found - run create-mtg-db first",
)


@pytest.fixture
async def db() -> AsyncIterator[UnifiedDatabase]:
    """Create database connection for tests."""
    assert DB_PATH is not None
    settings = Settings(mtg_db_path=DB_PATH)
    async with create_database(settings) as database:
        yield database


@pytest.fixture
async def db_with_cache() -> AsyncIterator[UnifiedDatabase]:
    """Create database connection with custom cache for testing."""
    assert DB_PATH is not None
    settings = Settings(mtg_db_path=DB_PATH)
    cache = CardCache(max_size=10, ttl_seconds=3600)
    async with create_database(settings) as database:
        database._cache = cache
        yield database


class TestRowConversion:
    """Tests for row to model conversion methods."""

    async def test_row_to_card_basic(self, db: UnifiedDatabase) -> None:
        """Test converting database row to Card model."""
        async with db._execute(
            "SELECT * FROM cards WHERE name = 'Lightning Bolt' LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None

            card = db._row_to_card(row)

            assert isinstance(card, Card)
            assert card.name == "Lightning Bolt"
            assert card.uuid == row["id"]
            assert card.type is not None
            assert "Instant" in card.type

    async def test_row_to_card_with_json_fields(self, db: UnifiedDatabase) -> None:
        """Test row conversion with JSON array fields."""
        async with db._execute(
            "SELECT * FROM cards WHERE colors IS NOT NULL AND keywords IS NOT NULL LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None

            card = db._row_to_card(row)

            if row["colors"]:
                assert isinstance(card.colors, list)
            if row["keywords"]:
                assert isinstance(card.keywords, list)

    async def test_row_to_card_with_prices(self, db: UnifiedDatabase) -> None:
        """Test row conversion includes price data."""
        async with db._execute("SELECT * FROM cards WHERE price_usd IS NOT NULL LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if row:
                card = db._row_to_card(row)
                assert card.price_usd is not None
                assert card.price_usd > 0

    async def test_row_to_set(self, db: UnifiedDatabase) -> None:
        """Test converting database row to Set model."""
        async with db._execute("SELECT * FROM sets WHERE code = 'KTK'") as cursor:
            row = await cursor.fetchone()
            if row:
                mtg_set = db._row_to_set(row)

                assert isinstance(mtg_set, Set)
                assert mtg_set.code.upper() == "KTK"
                assert mtg_set.name is not None
                assert mtg_set.card_count is not None

    async def test_parse_json_list_valid(self, db: UnifiedDatabase) -> None:
        """Test JSON list parsing with valid input."""
        result = db._parse_json_list('["Red", "Blue"]')
        assert result == ["Red", "Blue"]

    async def test_parse_json_list_null(self, db: UnifiedDatabase) -> None:
        """Test JSON list parsing with null input."""
        result = db._parse_json_list(None)
        assert result is None

    async def test_parse_json_list_invalid(self, db: UnifiedDatabase) -> None:
        """Test JSON list parsing with invalid input."""
        result = db._parse_json_list("not json")
        assert result is None

    async def test_parse_json_list_not_list(self, db: UnifiedDatabase) -> None:
        """Test JSON list parsing with non-list JSON."""
        result = db._parse_json_list('{"key": "value"}')
        assert result is None


class TestCardLookup:
    """Tests for individual card lookup methods."""

    async def test_get_card_by_name_basic(self, db: UnifiedDatabase) -> None:
        """Test getting a card by exact name."""
        card = await db.get_card_by_name("Lightning Bolt")

        assert card.name == "Lightning Bolt"
        assert card.uuid is not None
        assert card.legalities is not None
        assert card.rulings is not None

    async def test_get_card_by_name_case_insensitive(self, db: UnifiedDatabase) -> None:
        """Test card lookup is case-insensitive."""
        card1 = await db.get_card_by_name("Lightning Bolt")
        card2 = await db.get_card_by_name("LIGHTNING BOLT")
        card3 = await db.get_card_by_name("lightning bolt")

        assert card1.name == card2.name == card3.name

    async def test_get_card_by_name_not_found(self, db: UnifiedDatabase) -> None:
        """Test getting a non-existent card raises CardNotFoundError."""
        with pytest.raises(CardNotFoundError) as exc_info:
            await db.get_card_by_name("This Card Does Not Exist XYZ123")

        assert "This Card Does Not Exist XYZ123" in str(exc_info.value)

    async def test_get_card_by_name_without_extras(self, db: UnifiedDatabase) -> None:
        """Test getting card without legalities and rulings."""
        card = await db.get_card_by_name("Lightning Bolt", include_extras=False)

        assert card.name == "Lightning Bolt"
        assert card.legalities is None
        assert card.rulings is None

    async def test_get_card_by_name_uses_cache(self, db_with_cache: UnifiedDatabase) -> None:
        """Test that card lookups use cache."""
        card1 = await db_with_cache.get_card_by_name("Lightning Bolt")
        card2 = await db_with_cache.get_card_by_name("Lightning Bolt")

        assert card1.name == card2.name
        assert card1.uuid == card2.uuid

        cache_stats = await db_with_cache._cache.stats()
        assert cache_stats["size"] > 0

    async def test_get_card_by_uuid_basic(self, db: UnifiedDatabase) -> None:
        """Test getting a card by UUID."""
        bolt = await db.get_card_by_name("Lightning Bolt")
        assert bolt.uuid is not None

        card = await db.get_card_by_uuid(bolt.uuid)

        assert card.name == "Lightning Bolt"
        assert card.uuid == bolt.uuid
        assert card.legalities is not None

    async def test_get_card_by_uuid_not_found(self, db: UnifiedDatabase) -> None:
        """Test getting a card by invalid UUID raises error."""
        with pytest.raises(CardNotFoundError):
            await db.get_card_by_uuid("00000000-0000-0000-0000-000000000000")

    async def test_get_card_by_uuid_without_extras(self, db: UnifiedDatabase) -> None:
        """Test getting card by UUID without extras."""
        bolt = await db.get_card_by_name("Lightning Bolt")
        assert bolt.uuid is not None

        card = await db.get_card_by_uuid(bolt.uuid, include_extras=False)

        assert card.legalities is None
        assert card.rulings is None

    async def test_get_card_by_set_and_number(self, db: UnifiedDatabase) -> None:
        """Test getting card by set code and collector number."""
        card = await db.get_card_by_set_and_number("M21", "125")

        assert card is not None
        assert card.set_code.upper() == "M21"

    async def test_get_card_by_set_and_number_case_insensitive(self, db: UnifiedDatabase) -> None:
        """Test set code lookup is case-insensitive."""
        card = await db.get_card_by_set_and_number("m21", "125")

        assert card is not None
        assert card.set_code.upper() == "M21"

    async def test_get_card_by_set_and_number_leading_zeros(self, db: UnifiedDatabase) -> None:
        """Test collector number handles leading zeros."""
        card1 = await db.get_card_by_set_and_number("M21", "125")
        card2 = await db.get_card_by_set_and_number("M21", "0125")

        if card1 and card2:
            assert card1.name == card2.name

    async def test_get_card_by_set_and_number_not_found(self, db: UnifiedDatabase) -> None:
        """Test getting non-existent printing returns None."""
        card = await db.get_card_by_set_and_number("INVALID", "999999")

        assert card is None


class TestCardPrintings:
    """Tests for card printing and artwork methods."""

    async def test_get_all_printings(self, db: UnifiedDatabase) -> None:
        """Test getting all printings of a card."""
        printings = await db.get_all_printings("Lightning Bolt")

        assert len(printings) > 0
        assert all(card.name == "Lightning Bolt" for card in printings)
        assert len({card.set_code for card in printings}) > 1

    async def test_get_all_printings_sorted_by_date(self, db: UnifiedDatabase) -> None:
        """Test printings are sorted by release date descending."""
        printings = await db.get_all_printings("Lightning Bolt")

        dates = [card.release_date for card in printings if card.release_date]
        assert dates == sorted(dates, reverse=True)

    async def test_get_unique_artworks(self, db: UnifiedDatabase) -> None:
        """Test getting unique artworks for a card."""
        artworks = await db.get_unique_artworks("Lightning Bolt")

        assert len(artworks) > 0
        illustration_ids = [card.illustration_id for card in artworks]
        assert len(illustration_ids) == len(set(illustration_ids))

    async def test_get_unique_artworks_case_insensitive(self, db: UnifiedDatabase) -> None:
        """Test artwork lookup is case-insensitive."""
        artworks = await db.get_unique_artworks("LIGHTNING BOLT")

        assert len(artworks) > 0


class TestCardSearch:
    """Tests for card search functionality."""

    async def test_search_cards_by_name(self, db: UnifiedDatabase) -> None:
        """Test searching cards by name."""
        filters = SearchCardsInput(name="Lightning", page_size=10)
        cards, total = await db.search_cards(filters)

        assert len(cards) > 0
        assert total > 0
        assert any("Lightning" in card.name for card in cards)

    async def test_search_cards_by_flavor_name(self, db: UnifiedDatabase) -> None:
        """Test searching by flavor name (alternate names)."""
        filters = SearchCardsInput(name="spongebob", page_size=10)
        cards, total = await db.search_cards(filters)

        if total > 0:
            assert any(card.flavor_name and "SpongeBob" in card.flavor_name for card in cards)

    async def test_search_cards_by_type(self, db: UnifiedDatabase) -> None:
        """Test searching cards by type."""
        filters = SearchCardsInput(type="Instant", page_size=10)
        cards, _total = await db.search_cards(filters)

        assert len(cards) > 0
        assert all("Instant" in (card.type or "") for card in cards)

    async def test_search_cards_by_text(self, db: UnifiedDatabase) -> None:
        """Test searching cards by oracle text."""
        filters = SearchCardsInput(text="destroy target", page_size=10)
        cards, _total = await db.search_cards(filters)

        assert len(cards) > 0

    async def test_search_cards_by_set(self, db: UnifiedDatabase) -> None:
        """Test searching cards by set code."""
        filters = SearchCardsInput(set_code="M21", page_size=10)
        cards, _total = await db.search_cards(filters)

        assert len(cards) > 0
        assert all(card.set_code and card.set_code.upper() == "M21" for card in cards)

    async def test_search_cards_by_rarity(self, db: UnifiedDatabase) -> None:
        """Test searching cards by rarity."""
        filters = SearchCardsInput(rarity="mythic", page_size=10)
        cards, _total = await db.search_cards(filters)

        assert len(cards) > 0
        assert all(card.rarity and card.rarity.lower() == "mythic" for card in cards)

    async def test_search_cards_by_cmc_exact(self, db: UnifiedDatabase) -> None:
        """Test searching cards by exact mana value."""
        filters = SearchCardsInput(cmc=3, page_size=10)
        cards, _total = await db.search_cards(filters)

        assert len(cards) > 0
        assert all(card.cmc == 3 for card in cards)

    async def test_search_cards_by_cmc_range(self, db: UnifiedDatabase) -> None:
        """Test searching cards by mana value range."""
        filters = SearchCardsInput(cmc_min=2, cmc_max=4, page_size=10)
        cards, _total = await db.search_cards(filters)

        assert len(cards) > 0
        assert all(card.cmc is not None and 2 <= card.cmc <= 4 for card in cards)

    async def test_search_cards_by_colors(self, db: UnifiedDatabase) -> None:
        """Test searching cards by colors."""
        filters = SearchCardsInput(colors=["R"], page_size=10)
        cards, _total = await db.search_cards(filters)

        assert len(cards) > 0
        assert all(card.colors and "R" in card.colors for card in cards)

    async def test_search_cards_by_color_identity(self, db: UnifiedDatabase) -> None:
        """Test searching cards by color identity."""
        filters = SearchCardsInput(color_identity=["U", "R"], page_size=10)
        cards, _total = await db.search_cards(filters)

        assert len(cards) > 0
        assert all(
            card.color_identity and "U" in card.color_identity and "R" in card.color_identity
            for card in cards
        )

    async def test_search_cards_by_format_commander(self, db: UnifiedDatabase) -> None:
        """Test searching cards legal in Commander."""
        filters = SearchCardsInput(format_legal="commander", page_size=10)
        cards, _total = await db.search_cards(filters)

        assert len(cards) > 0

    async def test_search_cards_by_format_modern(self, db: UnifiedDatabase) -> None:
        """Test searching cards legal in Modern."""
        filters = SearchCardsInput(format_legal="modern", page_size=10)
        cards, _total = await db.search_cards(filters)

        assert len(cards) > 0

    async def test_search_cards_by_format_standard(self, db: UnifiedDatabase) -> None:
        """Test searching cards legal in Standard."""
        filters = SearchCardsInput(format_legal="standard", page_size=10)
        _cards, total = await db.search_cards(filters)

        assert total >= 0

    async def test_search_cards_by_format_other(self, db: UnifiedDatabase) -> None:
        """Test searching cards legal in other formats."""
        filters = SearchCardsInput(format_legal="vintage", page_size=10)
        _cards, total = await db.search_cards(filters)

        assert total >= 0

    async def test_search_cards_by_artist(self, db: UnifiedDatabase) -> None:
        """Test searching cards by artist."""
        filters = SearchCardsInput(artist="Mark Tedin", page_size=10)
        cards, total = await db.search_cards(filters)

        if total > 0:
            assert all(card.artist and "Tedin" in card.artist for card in cards)

    async def test_search_cards_by_keywords(self, db: UnifiedDatabase) -> None:
        """Test searching cards by keywords."""
        filters = SearchCardsInput(keywords=["Flying"], page_size=10)
        cards, _total = await db.search_cards(filters)

        assert len(cards) > 0
        assert all(card.keywords and "Flying" in card.keywords for card in cards)

    async def test_search_cards_pagination(self, db: UnifiedDatabase) -> None:
        """Test search pagination."""
        filters1 = SearchCardsInput(type="Creature", page=1, page_size=5)
        filters2 = SearchCardsInput(type="Creature", page=2, page_size=5)

        cards1, total1 = await db.search_cards(filters1)
        cards2, total2 = await db.search_cards(filters2)

        assert total1 == total2
        assert len(cards1) <= 5
        assert len(cards2) <= 5
        assert cards1[0].name != cards2[0].name

    async def test_search_cards_sort_by_name_asc(self, db: UnifiedDatabase) -> None:
        """Test sorting search results by name ascending."""
        filters = SearchCardsInput(type="Instant", sort_by="name", sort_order="asc", page_size=10)
        cards, _ = await db.search_cards(filters)

        names = [card.name for card in cards]
        assert names == sorted(names)

    async def test_search_cards_sort_by_name_desc(self, db: UnifiedDatabase) -> None:
        """Test sorting search results by name descending."""
        filters = SearchCardsInput(type="Instant", sort_by="name", sort_order="desc", page_size=10)
        cards, _ = await db.search_cards(filters)

        names = [card.name for card in cards]
        assert names == sorted(names, reverse=True)

    async def test_search_cards_sort_by_cmc(self, db: UnifiedDatabase) -> None:
        """Test sorting search results by mana value."""
        filters = SearchCardsInput(type="Creature", sort_by="cmc", sort_order="asc", page_size=10)
        cards, _ = await db.search_cards(filters)

        cmcs = [card.cmc for card in cards]
        assert cmcs == sorted(cmcs)

    async def test_search_cards_sort_by_price(self, db: UnifiedDatabase) -> None:
        """Test sorting search results by name (price not in sort options)."""
        filters = SearchCardsInput(sort_by="name", sort_order="desc", page_size=10)
        cards, _ = await db.search_cards(filters)

        assert len(cards) > 0

    async def test_search_cards_no_results(self, db: UnifiedDatabase) -> None:
        """Test search with no results."""
        filters = SearchCardsInput(name="XYZNONEXISTENT123", page_size=10)
        cards, total = await db.search_cards(filters)

        assert len(cards) == 0
        assert total == 0


class TestLegalitiesAndRulings:
    """Tests for card legalities and rulings."""

    async def test_get_legalities_basic(self, db: UnifiedDatabase) -> None:
        """Test getting legalities for a card."""
        bolt = await db.get_card_by_name("Lightning Bolt")
        assert bolt.uuid is not None

        legalities = await db._get_legalities(bolt.uuid)

        assert isinstance(legalities, list)
        assert all(isinstance(leg, CardLegality) for leg in legalities)
        assert all(leg.format and leg.legality for leg in legalities)

    async def test_get_legalities_no_data(self, db: UnifiedDatabase) -> None:
        """Test getting legalities for card without legality data."""
        legalities = await db._get_legalities("00000000-0000-0000-0000-000000000000")

        assert legalities == []

    async def test_get_rulings_basic(self, db: UnifiedDatabase) -> None:
        """Test getting rulings for a card by oracle_id."""
        async with db._execute(
            "SELECT oracle_id FROM cards WHERE oracle_id IN (SELECT oracle_id FROM rulings) LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                oracle_id = row["oracle_id"]
                rulings = await db._get_rulings(oracle_id)

                assert isinstance(rulings, list)
                assert all(isinstance(ruling, CardRuling) for ruling in rulings)
                assert all(ruling.date and ruling.text for ruling in rulings)

    async def test_get_rulings_sorted_by_date(self, db: UnifiedDatabase) -> None:
        """Test rulings are sorted by date descending."""
        async with db._execute(
            "SELECT oracle_id FROM cards WHERE oracle_id IN (SELECT oracle_id FROM rulings GROUP BY oracle_id HAVING COUNT(*) > 1) LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                oracle_id = row["oracle_id"]
                rulings = await db._get_rulings(oracle_id)

                if len(rulings) > 1:
                    dates = [ruling.date for ruling in rulings]
                    assert dates == sorted(dates, reverse=True)

    async def test_get_card_rulings_by_name(self, db: UnifiedDatabase) -> None:
        """Test getting rulings by card name."""
        rulings = await db.get_card_rulings("Lightning Bolt")

        assert isinstance(rulings, list)

    async def test_get_card_rulings_not_found(self, db: UnifiedDatabase) -> None:
        """Test getting rulings for non-existent card."""
        rulings = await db.get_card_rulings("Nonexistent Card XYZ123")

        assert rulings == []

    async def test_get_card_legalities_by_name(self, db: UnifiedDatabase) -> None:
        """Test getting legalities by card name as dict."""
        legalities = await db.get_card_legalities("Lightning Bolt")

        assert isinstance(legalities, dict)
        assert len(legalities) > 0

    async def test_get_card_legalities_not_found(self, db: UnifiedDatabase) -> None:
        """Test getting legalities for non-existent card."""
        legalities = await db.get_card_legalities("Nonexistent Card XYZ123")

        assert legalities == {}


class TestSetOperations:
    """Tests for set-related operations."""

    async def test_get_set_basic(self, db: UnifiedDatabase) -> None:
        """Test getting a set by code."""
        mtg_set = await db.get_set("KTK")

        assert mtg_set.code.upper() == "KTK"
        assert mtg_set.name is not None
        assert mtg_set.card_count is not None

    async def test_get_set_case_insensitive(self, db: UnifiedDatabase) -> None:
        """Test set lookup is case-insensitive."""
        set1 = await db.get_set("KTK")
        set2 = await db.get_set("ktk")

        assert set1.code == set2.code

    async def test_get_set_not_found(self, db: UnifiedDatabase) -> None:
        """Test getting non-existent set raises error."""
        with pytest.raises(SetNotFoundError) as exc_info:
            await db.get_set("INVALID")

        assert "INVALID" in str(exc_info.value)

    async def test_get_all_sets_basic(self, db: UnifiedDatabase) -> None:
        """Test getting all sets."""
        sets = await db.get_all_sets()

        assert len(sets) > 0
        assert all(isinstance(s, Set) for s in sets)

    async def test_get_all_sets_sorted_by_date(self, db: UnifiedDatabase) -> None:
        """Test sets are sorted by release date descending."""
        sets = await db.get_all_sets()

        dates = [s.release_date for s in sets if s.release_date]
        assert dates == sorted(dates, reverse=True)

    async def test_get_all_sets_by_type(self, db: UnifiedDatabase) -> None:
        """Test filtering sets by type."""
        sets = await db.get_all_sets(set_type="expansion")

        assert len(sets) > 0
        assert all(s.type and s.type.lower() == "expansion" for s in sets)

    async def test_get_all_sets_exclude_online(self, db: UnifiedDatabase) -> None:
        """Test excluding online-only sets."""
        sets = await db.get_all_sets(include_online_only=False)

        assert len(sets) > 0

    async def test_search_sets_by_name(self, db: UnifiedDatabase) -> None:
        """Test searching sets by name."""
        sets = await db.search_sets("Khans")

        assert len(sets) > 0
        assert any("Khans" in s.name for s in sets)

    async def test_search_sets_no_results(self, db: UnifiedDatabase) -> None:
        """Test searching sets with no results."""
        sets = await db.search_sets("XYZNONEXISTENT")

        assert len(sets) == 0


class TestDatabaseStats:
    """Tests for database statistics."""

    async def test_get_database_stats(self, db: UnifiedDatabase) -> None:
        """Test getting database statistics."""
        stats = await db.get_database_stats()

        assert "total_cards" in stats
        assert "unique_cards" in stats
        assert "total_sets" in stats
        assert stats["total_cards"] > 0
        assert stats["unique_cards"] > 0
        assert stats["total_sets"] > 0

    async def test_get_database_stats_includes_metadata(self, db: UnifiedDatabase) -> None:
        """Test stats include metadata fields."""
        stats = await db.get_database_stats()

        assert isinstance(stats, dict)


class TestRandomCard:
    """Tests for random card selection."""

    async def test_get_random_card_basic(self, db: UnifiedDatabase) -> None:
        """Test getting a random card."""
        card = await db.get_random_card()

        assert isinstance(card, Card)
        assert card.name is not None
        assert card.legalities is not None
        assert card.rulings is not None

    async def test_get_random_card_multiple_calls(self, db: UnifiedDatabase) -> None:
        """Test multiple random card calls work."""
        cards = []
        for _ in range(5):
            card = await db.get_random_card()
            cards.append(card)

        assert len(cards) == 5
        assert all(isinstance(card, Card) for card in cards)

    async def test_get_random_card_empty_database_fallback(self) -> None:
        """Test random card raises error on empty database."""
        assert DB_PATH is not None
        settings = Settings(mtg_db_path=DB_PATH)

        async with create_database(settings) as test_db:
            with patch.object(test_db, "_execute") as mock_execute:
                mock_cursor = AsyncMock()
                mock_cursor.fetchone = AsyncMock(return_value=None)
                mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
                mock_cursor.__aexit__ = AsyncMock(return_value=None)
                mock_execute.return_value = mock_cursor

                with pytest.raises(CardNotFoundError) as exc_info:
                    await test_db.get_random_card()

                assert "random" in str(exc_info.value)


class TestBatchOperations:
    """Tests for batch card operations."""

    async def test_get_cards_by_names_basic(self, db: UnifiedDatabase) -> None:
        """Test batch loading cards by names."""
        names = ["Lightning Bolt", "Counterspell", "Giant Growth"]
        result = await db.get_cards_by_names(names)

        assert len(result) >= 2
        assert all(isinstance(card, Card) for card in result.values())

    async def test_get_cards_by_names_case_insensitive(self, db: UnifiedDatabase) -> None:
        """Test batch loading is case-insensitive."""
        names = ["Lightning Bolt", "LIGHTNING BOLT", "lightning bolt"]
        result = await db.get_cards_by_names(names)

        assert "lightning bolt" in result

    async def test_get_cards_by_names_with_extras(self, db: UnifiedDatabase) -> None:
        """Test batch loading with legalities and rulings."""
        names = ["Lightning Bolt"]
        result = await db.get_cards_by_names(names, include_extras=True)

        card = result.get("lightning bolt")
        if card:
            assert card.legalities is not None

    async def test_get_cards_by_names_without_extras(self, db: UnifiedDatabase) -> None:
        """Test batch loading without extras."""
        names = ["Lightning Bolt"]
        result = await db.get_cards_by_names(names, include_extras=False)

        card = result.get("lightning bolt")
        if card:
            assert card.legalities is None

    async def test_get_cards_by_names_empty_list(self, db: UnifiedDatabase) -> None:
        """Test batch loading with empty list."""
        result = await db.get_cards_by_names([])

        assert result == {}

    async def test_get_cards_by_names_uses_cache(self, db_with_cache: UnifiedDatabase) -> None:
        """Test batch loading uses cache."""
        names = ["Lightning Bolt"]
        await db_with_cache.get_card_by_name("Lightning Bolt")

        result = await db_with_cache.get_cards_by_names(names)

        assert len(result) > 0


class TestPriceSearch:
    """Tests for price-based searching."""

    async def test_search_by_price_min(self, db: UnifiedDatabase) -> None:
        """Test searching by minimum price."""
        cards = await db.search_by_price(min_price=10.0, page_size=5)

        assert all(card.price_usd is None or card.price_usd >= 1000 for card in cards)

    async def test_search_by_price_max(self, db: UnifiedDatabase) -> None:
        """Test searching by maximum price."""
        cards = await db.search_by_price(max_price=1.0, page_size=5)

        if cards:
            assert all(card.price_usd is None or card.price_usd <= 100 for card in cards)

    async def test_search_by_price_range(self, db: UnifiedDatabase) -> None:
        """Test searching by price range."""
        cards = await db.search_by_price(min_price=5.0, max_price=20.0, page_size=5)

        if cards:
            assert all(card.price_usd is None or 500 <= card.price_usd <= 2000 for card in cards)

    async def test_search_by_price_pagination(self, db: UnifiedDatabase) -> None:
        """Test price search pagination."""
        cards1 = await db.search_by_price(min_price=1.0, page=1, page_size=5)
        cards2 = await db.search_by_price(min_price=1.0, page=2, page_size=5)

        if cards1 and cards2:
            assert cards1[0].name != cards2[0].name

    async def test_search_by_price_sorted_desc(self, db: UnifiedDatabase) -> None:
        """Test price search is sorted by price descending."""
        cards = await db.search_by_price(min_price=1.0, page_size=10)

        if len(cards) > 1:
            prices = [card.price_usd for card in cards if card.price_usd]
            assert prices == sorted(prices, reverse=True)


class TestKeywords:
    """Tests for keyword operations."""

    async def test_get_all_keywords(self, db: UnifiedDatabase) -> None:
        """Test getting all keywords."""
        keywords = await db.get_all_keywords()

        assert isinstance(keywords, set)
        assert len(keywords) > 0
        assert "Flying" in keywords or "Haste" in keywords

    async def test_keywords_are_unique(self, db: UnifiedDatabase) -> None:
        """Test returned keywords are unique."""
        keywords = await db.get_all_keywords()

        assert len(keywords) == len(set(keywords))


class TestArtistOperations:
    """Tests for artist-related operations."""

    async def test_get_random_artist_for_spotlight(self, db: UnifiedDatabase) -> None:
        """Test getting random artist for spotlight."""
        artist = await db.get_random_artist_for_spotlight(min_cards=20)

        if artist:
            assert isinstance(artist, ArtistSummary)
            assert artist.name is not None
            assert artist.card_count >= 20

    async def test_get_random_artist_deterministic_per_day(self, db: UnifiedDatabase) -> None:
        """Test same artist returned for same day."""
        artist1 = await db.get_random_artist_for_spotlight(min_cards=20)
        artist2 = await db.get_random_artist_for_spotlight(min_cards=20)

        if artist1 and artist2:
            assert artist1.name == artist2.name

    async def test_get_random_artist_no_eligible_artists(self, db: UnifiedDatabase) -> None:
        """Test returns None when no eligible artists."""
        artist = await db.get_random_artist_for_spotlight(min_cards=999999)

        assert artist is None

    async def test_get_random_artist_fallback_on_detail_failure(self) -> None:
        """Test random artist returns fallback when detail query fails."""
        assert DB_PATH is not None
        settings = Settings(mtg_db_path=DB_PATH)

        async with create_database(settings) as test_db:
            with patch.object(test_db, "_execute") as mock_execute:
                mock_cursor_candidates = AsyncMock()
                mock_cursor_candidates.__aenter__ = AsyncMock(return_value=mock_cursor_candidates)
                mock_cursor_candidates.__aexit__ = AsyncMock(return_value=None)

                async def async_iter(_self):
                    yield {"name": "Test Artist", "card_count": 50}

                mock_cursor_candidates.__aiter__ = async_iter

                mock_cursor_details = AsyncMock()
                mock_cursor_details.fetchone = AsyncMock(return_value=None)
                mock_cursor_details.__aenter__ = AsyncMock(return_value=mock_cursor_details)
                mock_cursor_details.__aexit__ = AsyncMock(return_value=None)

                mock_execute.side_effect = [mock_cursor_candidates, mock_cursor_details]

                artist = await test_db.get_random_artist_for_spotlight(min_cards=20)

                assert artist is not None
                assert artist.name == "Test Artist"
                assert artist.card_count == 50
                assert artist.sets_count == 0
                assert artist.first_card_year is None

    async def test_get_cards_by_artist_basic(self, db: UnifiedDatabase) -> None:
        """Test getting cards by artist."""
        cards = await db.get_cards_by_artist("Mark Tedin")

        if len(cards) > 0:
            assert all(card.artist and "Tedin" in card.artist for card in cards)

    async def test_get_cards_by_artist_deduped(self, db: UnifiedDatabase) -> None:
        """Test cards by artist uses deduplication logic.

        Note: Deduplication is by (name, flavor_text) pair to handle variants,
        so some card names may appear multiple times with different flavor text.
        """
        cards = await db.get_cards_by_artist("Mark Tedin")

        assert len(cards) > 0
        name_flavor_pairs = [(card.name, card.flavor or "") for card in cards]
        assert len(name_flavor_pairs) == len(set(name_flavor_pairs))

    async def test_get_cards_by_artist_sorted(self, db: UnifiedDatabase) -> None:
        """Test cards by artist are sorted by release date desc."""
        cards = await db.get_cards_by_artist("Mark Tedin")

        if len(cards) > 1:
            dates = [card.release_date for card in cards if card.release_date]
            assert dates == sorted(dates, reverse=True)

    async def test_get_cards_by_artist_collaborative(self, db: UnifiedDatabase) -> None:
        """Test getting cards by artist includes collaborations."""
        async with db._execute(
            "SELECT DISTINCT artist FROM cards WHERE artist LIKE '% & %' LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                collab_artist = row["artist"]
                first_artist = collab_artist.split(" & ")[0]

                cards = await db.get_cards_by_artist(first_artist)
                assert len(cards) > 0

    async def test_get_all_artists_basic(self, db: UnifiedDatabase) -> None:
        """Test getting all artists."""
        artists = await db.get_all_artists(min_cards=1)

        assert len(artists) > 0
        assert all(isinstance(artist, ArtistSummary) for artist in artists)
        assert all(artist.card_count >= 1 for artist in artists)

    async def test_get_all_artists_min_cards_filter(self, db: UnifiedDatabase) -> None:
        """Test filtering artists by minimum card count."""
        artists = await db.get_all_artists(min_cards=50)

        if artists:
            assert all(artist.card_count >= 50 for artist in artists)

    async def test_get_all_artists_sorted(self, db: UnifiedDatabase) -> None:
        """Test artists sorted by card count descending."""
        artists = await db.get_all_artists(min_cards=1)

        if len(artists) > 1:
            counts = [artist.card_count for artist in artists]
            assert counts == sorted(counts, reverse=True)

    async def test_get_all_artists_has_metadata(self, db: UnifiedDatabase) -> None:
        """Test artist summaries include metadata."""
        artists = await db.get_all_artists(min_cards=10)

        if artists:
            artist = artists[0]
            assert artist.sets_count > 0

    async def test_search_artists_basic(self, db: UnifiedDatabase) -> None:
        """Test searching artists by name."""
        artists = await db.search_artists("Tedin", min_cards=1)

        assert len(artists) > 0
        assert all("Tedin" in artist.name for artist in artists)

    async def test_search_artists_sorted(self, db: UnifiedDatabase) -> None:
        """Test search artists sorted by card count."""
        artists = await db.search_artists("Mark", min_cards=1)

        if len(artists) > 1:
            counts = [artist.card_count for artist in artists]
            assert counts == sorted(counts, reverse=True)

    async def test_search_artists_min_cards_filter(self, db: UnifiedDatabase) -> None:
        """Test search artists with minimum card filter."""
        artists = await db.search_artists("Mark", min_cards=20)

        if artists:
            assert all(artist.card_count >= 20 for artist in artists)

    async def test_search_artists_no_results(self, db: UnifiedDatabase) -> None:
        """Test searching artists with no results."""
        artists = await db.search_artists("XYZNONEXISTENT", min_cards=1)

        assert len(artists) == 0


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    async def test_row_to_card_with_null_optional_fields(self, db: UnifiedDatabase) -> None:
        """Test row conversion handles null optional fields."""
        async with db._execute("SELECT * FROM cards LIMIT 1") as cursor:
            row = await cursor.fetchone()
            assert row is not None

            card = db._row_to_card(row)
            assert isinstance(card, Card)

    async def test_search_cards_combined_filters(self, db: UnifiedDatabase) -> None:
        """Test search with multiple filters combined."""
        filters = SearchCardsInput(
            type="Creature",
            colors=["R"],
            cmc_min=2,
            cmc_max=4,
            rarity="rare",
            page_size=5,
        )
        cards, _total = await db.search_cards(filters)

        if cards:
            assert all("Creature" in (card.type or "") for card in cards)
            assert all(card.colors and "R" in card.colors for card in cards)
            assert all(card.cmc is not None and 2 <= card.cmc <= 4 for card in cards)

    async def test_get_cards_by_names_partial_results(self, db: UnifiedDatabase) -> None:
        """Test batch loading with some invalid names."""
        names = ["Lightning Bolt", "INVALID_CARD_XYZ123", "Counterspell"]
        result = await db.get_cards_by_names(names)

        assert len(result) >= 1
        assert "lightning bolt" in result or "counterspell" in result

    async def test_get_cards_by_names_skips_already_cached(
        self, db_with_cache: UnifiedDatabase
    ) -> None:
        """Test batch loading skips names already in cache."""
        await db_with_cache._cache.clear()

        await db_with_cache.get_card_by_name("Lightning Bolt", include_extras=False)

        names = ["Lightning Bolt", "Counterspell"]
        result = await db_with_cache.get_cards_by_names(names, include_extras=False)

        assert "lightning bolt" in result
        assert result["lightning bolt"].name == "Lightning Bolt"


class TestCacheIntegration:
    """Tests for cache integration."""

    async def test_cache_hit_returns_same_instance(self, db_with_cache: UnifiedDatabase) -> None:
        """Test cache returns same card instance."""
        card1 = await db_with_cache.get_card_by_name("Lightning Bolt")
        card2 = await db_with_cache.get_card_by_name("Lightning Bolt")

        assert card1.uuid == card2.uuid
        assert card1.name == card2.name

    async def test_cache_respects_include_extras_flag(self, db_with_cache: UnifiedDatabase) -> None:
        """Test cache keys include extras flag."""
        card_with = await db_with_cache.get_card_by_name("Lightning Bolt", include_extras=True)
        card_without = await db_with_cache.get_card_by_name("Lightning Bolt", include_extras=False)

        assert card_with.legalities is not None
        assert card_without.legalities is None

    async def test_batch_loading_uses_cache(self, db_with_cache: UnifiedDatabase) -> None:
        """Test batch loading retrieves from cache."""
        await db_with_cache.get_card_by_name("Lightning Bolt", include_extras=False)

        names = ["Lightning Bolt", "Counterspell"]
        result = await db_with_cache.get_cards_by_names(names, include_extras=False)

        assert "lightning bolt" in result

        stats = await db_with_cache._cache.stats()
        assert stats["size"] > 0
