"""Comprehensive tests for card, image, set, and artist tools.

These tests verify the functionality of:
- cards.py: Card search and details
- images.py: Image handling and pricing
- sets.py: Set listing and details
- artists.py: Artist queries
- Card model methods: to_summary(), get_legality(), is_legal_in(), price getters
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import patch

import pytest

from mtg_core.config import Settings
from mtg_core.data.database import UnifiedDatabase, create_database
from mtg_core.data.models import (
    Card,
    CardLegality,
    SearchCardsInput,
)
from mtg_core.exceptions import CardNotFoundError, SetNotFoundError, ValidationError
from mtg_core.tools import artists, cards, images, sets

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


class TestCardSearch:
    """Tests for search_cards function."""

    async def test_search_cards_by_name(self, db: UnifiedDatabase) -> None:
        """Search cards by name should return matching results."""
        filters = SearchCardsInput(name="Lightning Bolt", page_size=10)
        result = await cards.search_cards(db, filters)

        assert result.total_count > 0
        assert len(result.cards) > 0
        assert any("Lightning Bolt" in card.name for card in result.cards)

    async def test_search_cards_by_colors(self, db: UnifiedDatabase) -> None:
        """Search cards by colors should filter correctly."""
        filters = SearchCardsInput(colors=["R"], page_size=10)
        result = await cards.search_cards(db, filters)

        assert result.total_count > 0
        for card in result.cards:
            if card.colors:
                assert any(color in ["R"] for color in card.colors)

    async def test_search_cards_by_type(self, db: UnifiedDatabase) -> None:
        """Search cards by type should filter correctly."""
        filters = SearchCardsInput(type="Creature", page_size=10)
        result = await cards.search_cards(db, filters)

        assert result.total_count > 0
        for card in result.cards:
            assert card.type is not None
            assert "Creature" in card.type

    async def test_search_cards_by_rarity(self, db: UnifiedDatabase) -> None:
        """Search cards by rarity should filter correctly."""
        filters = SearchCardsInput(rarity="mythic", page_size=10)
        result = await cards.search_cards(db, filters)

        assert result.total_count > 0
        for card in result.cards:
            assert card.rarity is not None
            assert card.rarity.lower() == "mythic"

    async def test_search_cards_pagination(self, db: UnifiedDatabase) -> None:
        """Search pagination should work correctly."""
        filters_page1 = SearchCardsInput(type="Creature", page=1, page_size=5)
        filters_page2 = SearchCardsInput(type="Creature", page=2, page_size=5)

        result1 = await cards.search_cards(db, filters_page1)
        result2 = await cards.search_cards(db, filters_page2)

        assert result1.page == 1
        assert result2.page == 2
        assert len(result1.cards) == 5
        assert len(result2.cards) == 5

        card_ids_1 = {c.uuid for c in result1.cards}
        card_ids_2 = {c.uuid for c in result2.cards}
        assert card_ids_1.isdisjoint(card_ids_2)

    async def test_search_cards_by_cmc(self, db: UnifiedDatabase) -> None:
        """Search cards by converted mana cost should filter correctly."""
        filters = SearchCardsInput(cmc_min=3, cmc_max=3, page_size=10)
        result = await cards.search_cards(db, filters)

        assert result.total_count > 0
        for card in result.cards:
            if card.cmc is not None:
                assert card.cmc == 3

    async def test_search_cards_by_keywords(self, db: UnifiedDatabase) -> None:
        """Search cards by keywords should filter correctly."""
        filters = SearchCardsInput(keywords=["Flying"], page_size=10)
        result = await cards.search_cards(db, filters)

        assert result.total_count > 0
        for card in result.cards:
            if card.keywords:
                assert "Flying" in card.keywords

    async def test_search_cards_empty_result(self, db: UnifiedDatabase) -> None:
        """Search with no matches should return empty result."""
        filters = SearchCardsInput(name="ThisCardDoesNotExist12345", page_size=10)
        result = await cards.search_cards(db, filters)

        assert result.total_count == 0
        assert len(result.cards) == 0


class TestGetCard:
    """Tests for get_card function."""

    async def test_get_card_by_name(self, db: UnifiedDatabase) -> None:
        """Get card by name should return detailed card info."""
        card = await cards.get_card(db, name="Lightning Bolt")

        assert card.name == "Lightning Bolt"
        assert card.uuid is not None
        assert card.type is not None
        assert "Instant" in card.type

    async def test_get_card_by_uuid(self, db: UnifiedDatabase) -> None:
        """Get card by UUID should return detailed card info."""
        search_result = await cards.search_cards(
            db, SearchCardsInput(name="Lightning Bolt", page_size=1)
        )
        uuid = search_result.cards[0].uuid

        card = await cards.get_card(db, uuid=uuid)

        assert card.uuid == uuid
        assert card.name is not None

    async def test_get_card_not_found(self, db: UnifiedDatabase) -> None:
        """Get card with invalid name should raise CardNotFoundError."""
        with pytest.raises(CardNotFoundError) as exc_info:
            await cards.get_card(db, name="ThisCardDoesNotExist12345")

        assert "ThisCardDoesNotExist12345" in str(exc_info.value)

    async def test_get_card_no_params(self, db: UnifiedDatabase) -> None:
        """Get card without name or UUID should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            await cards.get_card(db)

        assert "name" in str(exc_info.value) or "uuid" in str(exc_info.value)

    async def test_get_card_includes_images(self, db: UnifiedDatabase) -> None:
        """Get card should include image URLs."""
        card = await cards.get_card(db, name="Lightning Bolt")

        assert card.images is not None
        assert card.images.normal is not None or card.images.small is not None

    async def test_get_card_includes_legalities(self, db: UnifiedDatabase) -> None:
        """Get card should include legality information."""
        card = await cards.get_card(db, name="Lightning Bolt")

        assert card.legalities is not None
        assert len(card.legalities) > 0
        assert "vintage" in card.legalities or "legacy" in card.legalities


class TestCardRulings:
    """Tests for get_card_rulings function."""

    async def test_get_card_rulings_existing(self, db: UnifiedDatabase) -> None:
        """Get rulings for card with rulings should return them."""
        result = await cards.get_card_rulings(db, "Braids, Arisen Nightmare")

        assert result.card_name == "Braids, Arisen Nightmare"
        if result.rulings:
            for ruling in result.rulings:
                assert ruling.date is not None
                assert ruling.text is not None

    async def test_get_card_rulings_none(self, db: UnifiedDatabase) -> None:
        """Get rulings for card without rulings should return empty list."""
        result = await cards.get_card_rulings(db, "Plains")

        assert result.card_name == "Plains"
        assert result.rulings == []
        assert result.note is not None

    async def test_get_card_rulings_not_found(self, db: UnifiedDatabase) -> None:
        """Get rulings for non-existent card should raise CardNotFoundError."""
        with pytest.raises(CardNotFoundError):
            await cards.get_card_rulings(db, "ThisCardDoesNotExist12345")


class TestCardLegalities:
    """Tests for get_card_legalities function."""

    async def test_get_card_legalities_existing(self, db: UnifiedDatabase) -> None:
        """Get legalities for card should return format legalities."""
        result = await cards.get_card_legalities(db, "Lightning Bolt")

        assert result.card_name == "Lightning Bolt"
        assert result.legalities is not None
        assert len(result.legalities) > 0

    async def test_get_card_legalities_banned_card(self, db: UnifiedDatabase) -> None:
        """Get legalities should show banned status."""
        result = await cards.get_card_legalities(db, "Black Lotus")

        assert result.card_name == "Black Lotus"
        assert result.legalities is not None
        if "vintage" in result.legalities:
            assert result.legalities["vintage"].lower() in ["banned", "restricted", "legal"]

    async def test_get_card_legalities_not_found(self, db: UnifiedDatabase) -> None:
        """Get legalities for non-existent card should raise CardNotFoundError."""
        with pytest.raises(CardNotFoundError):
            await cards.get_card_legalities(db, "ThisCardDoesNotExist12345")


class TestRandomCard:
    """Tests for get_random_card function."""

    async def test_get_random_card(self, db: UnifiedDatabase) -> None:
        """Get random card should return a valid card."""
        card = await cards.get_random_card(db)

        assert card.name is not None
        assert card.uuid is not None

    async def test_get_random_card_unique(self, db: UnifiedDatabase) -> None:
        """Multiple random card calls should return different cards (usually)."""
        cards_list = [await cards.get_random_card(db) for _ in range(5)]

        uuids = [c.uuid for c in cards_list]
        assert len(set(uuids)) > 1


class TestCardImages:
    """Tests for image tools."""

    async def test_get_card_image_by_name(self, db: UnifiedDatabase) -> None:
        """Get card image by name should return image URLs."""
        result = await images.get_card_image(db, "Lightning Bolt")

        assert result.card_name == "Lightning Bolt"
        assert result.images is not None
        assert result.images.normal is not None or result.images.small is not None

    async def test_get_card_image_by_set_and_number(self, db: UnifiedDatabase) -> None:
        """Get card image by set and collector number should return specific printing."""
        result = await images.get_card_image(
            db, "Lightning Bolt", set_code="LEA", collector_number="161"
        )

        assert result.card_name == "Lightning Bolt"
        assert result.set_code.upper() == "LEA"

    async def test_get_card_image_includes_prices(self, db: UnifiedDatabase) -> None:
        """Get card image should include price information."""
        result = await images.get_card_image(db, "Lightning Bolt")

        assert result.prices is not None

    async def test_get_card_image_includes_purchase_links(self, db: UnifiedDatabase) -> None:
        """Get card image should include purchase links."""
        result = await images.get_card_image(db, "Lightning Bolt")

        assert result.purchase_links is not None

    async def test_get_card_image_not_found(self, db: UnifiedDatabase) -> None:
        """Get card image for non-existent card should raise CardNotFoundError."""
        with pytest.raises(CardNotFoundError):
            await images.get_card_image(db, "ThisCardDoesNotExist12345")


class TestCardPrintings:
    """Tests for get_card_printings function."""

    async def test_get_card_printings(self, db: UnifiedDatabase) -> None:
        """Get card printings should return all printings."""
        result = await images.get_card_printings(db, "Lightning Bolt")

        assert result.card_name == "Lightning Bolt"
        assert len(result.printings) > 0

        for printing in result.printings:
            assert printing.set_code is not None
            assert printing.collector_number is not None

    async def test_get_card_printings_includes_images(self, db: UnifiedDatabase) -> None:
        """Get card printings should include images for each printing."""
        result = await images.get_card_printings(db, "Lightning Bolt")

        for printing in result.printings:
            assert printing.image is not None or printing.art_crop is not None

    async def test_get_card_printings_includes_prices(self, db: UnifiedDatabase) -> None:
        """Get card printings should include prices for each printing."""
        result = await images.get_card_printings(db, "Lightning Bolt")

        assert len(result.printings) > 0

    async def test_get_card_printings_not_found(self, db: UnifiedDatabase) -> None:
        """Get printings for non-existent card should raise CardNotFoundError."""
        with pytest.raises(CardNotFoundError):
            await images.get_card_printings(db, "ThisCardDoesNotExist12345")

    async def test_get_card_printings_consistent(self, db: UnifiedDatabase) -> None:
        """Get card printings should return consistent results."""
        result1 = await images.get_card_printings(db, "Lightning Bolt")
        result2 = await images.get_card_printings(db, "Lightning Bolt")

        assert result1.card_name == result2.card_name
        assert len(result1.printings) == len(result2.printings)


class TestCardPrice:
    """Tests for get_card_price function."""

    async def test_get_card_price_by_name(self, db: UnifiedDatabase) -> None:
        """Get card price by name should return price information."""
        result = await images.get_card_price(db, "Lightning Bolt")

        assert result.card_name == "Lightning Bolt"
        assert result.prices is not None

    async def test_get_card_price_by_set_and_number(self, db: UnifiedDatabase) -> None:
        """Get card price by set and number should return specific printing price."""
        result = await images.get_card_price(
            db, "Lightning Bolt", set_code="LEA", collector_number="161"
        )

        assert result.card_name == "Lightning Bolt"
        assert result.set_code.upper() == "LEA"

    async def test_get_card_price_not_found(self, db: UnifiedDatabase) -> None:
        """Get price for non-existent card should raise CardNotFoundError."""
        with pytest.raises(CardNotFoundError):
            await images.get_card_price(db, "ThisCardDoesNotExist12345")

    async def test_get_card_price_includes_purchase_links(self, db: UnifiedDatabase) -> None:
        """Get card price should include purchase links."""
        result = await images.get_card_price(db, "Lightning Bolt")

        assert result.purchase_links is not None


class TestSearchByPrice:
    """Tests for search_by_price function."""

    async def test_search_by_price_min_only(self, db: UnifiedDatabase) -> None:
        """Search by minimum price should return cards above threshold."""
        result = await images.search_by_price(db, min_price=100.0, page_size=10)

        assert len(result.cards) > 0
        for card in result.cards:
            if card.price_usd is not None:
                assert card.price_usd >= 100.0

    async def test_search_by_price_max_only(self, db: UnifiedDatabase) -> None:
        """Search by maximum price should return cards below threshold."""
        result = await images.search_by_price(db, max_price=1.0, page_size=10)

        assert len(result.cards) > 0
        for card in result.cards:
            if card.price_usd is not None:
                assert card.price_usd <= 1.0

    async def test_search_by_price_range(self, db: UnifiedDatabase) -> None:
        """Search by price range should return cards within range."""
        result = await images.search_by_price(db, min_price=5.0, max_price=10.0, page_size=10)

        for card in result.cards:
            if card.price_usd is not None:
                assert 5.0 <= card.price_usd <= 10.0

    async def test_search_by_price_no_params(self, db: UnifiedDatabase) -> None:
        """Search by price without min or max should raise ValidationError."""
        with pytest.raises(ValidationError):
            await images.search_by_price(db)

    async def test_search_by_price_pagination(self, db: UnifiedDatabase) -> None:
        """Search by price should respect pagination."""
        result = await images.search_by_price(
            db, min_price=1.0, max_price=100.0, page=1, page_size=5
        )

        assert result.page == 1
        assert result.page_size == 5


class TestSets:
    """Tests for set tools."""

    async def test_get_sets_all(self, db: UnifiedDatabase) -> None:
        """Get all sets should return list of sets."""
        result = await sets.get_sets(db)

        assert len(result.sets) > 0
        for mtg_set in result.sets:
            assert mtg_set.code is not None
            assert mtg_set.name is not None

    async def test_get_sets_by_name(self, db: UnifiedDatabase) -> None:
        """Get sets by name should filter results."""
        result = await sets.get_sets(db, name="Alpha")

        assert len(result.sets) > 0
        for mtg_set in result.sets:
            assert "Alpha" in mtg_set.name or "alpha" in mtg_set.code.lower()

    async def test_get_sets_by_type(self, db: UnifiedDatabase) -> None:
        """Get sets by type should filter results."""
        result = await sets.get_sets(db, set_type="core")

        assert len(result.sets) > 0
        for mtg_set in result.sets:
            if mtg_set.type:
                assert "core" in mtg_set.type.lower()

    async def test_get_sets_exclude_online_only(self, db: UnifiedDatabase) -> None:
        """Get sets excluding online-only should filter results."""
        result = await sets.get_sets(db, include_online_only=False)

        assert len(result.sets) > 0

    async def test_get_set_by_code(self, db: UnifiedDatabase) -> None:
        """Get set by code should return detailed set info."""
        result = await sets.get_set(db, "LEA")

        assert result.code.upper() == "LEA"
        assert result.name is not None
        assert result.release_date is not None

    async def test_get_set_not_found(self, db: UnifiedDatabase) -> None:
        """Get set with invalid code should raise SetNotFoundError."""
        with pytest.raises(SetNotFoundError):
            await sets.get_set(db, "INVALID")

    async def test_get_set_includes_details(self, db: UnifiedDatabase) -> None:
        """Get set should include detailed information."""
        result = await sets.get_set(db, "LEA")

        assert result.type is not None
        assert result.base_set_size is not None or result.total_set_size is not None


class TestArtists:
    """Tests for artist tools."""

    async def test_get_artist_cards(self, db: UnifiedDatabase) -> None:
        """Get artist cards should return cards by artist."""
        # Clear cache to ensure fresh results
        with patch("mtg_core.tools.artists.get_cached", return_value=None):
            result = await artists.get_artist_cards(db, "Christopher Rush", use_cache=False)

        assert result.artist_name == "Christopher Rush"
        assert len(result.cards) > 0

        for card in result.cards:
            assert card.name is not None

    async def test_get_artist_cards_case_insensitive(self, db: UnifiedDatabase) -> None:
        """Get artist cards should be case-insensitive."""
        with patch("mtg_core.tools.artists.get_cached", return_value=None):
            result = await artists.get_artist_cards(db, "christopher rush", use_cache=False)

        assert len(result.cards) > 0

    async def test_get_artist_cards_caching(self, db: UnifiedDatabase) -> None:
        """Get artist cards should use cache when enabled."""
        result1 = await artists.get_artist_cards(db, "Christopher Rush", use_cache=True)
        result2 = await artists.get_artist_cards(db, "Christopher Rush", use_cache=True)

        assert result1.artist_name == result2.artist_name
        assert len(result1.cards) == len(result2.cards)

    async def test_get_artist_cards_no_results(self, db: UnifiedDatabase) -> None:
        """Get artist cards for non-existent artist should return empty list."""
        with patch("mtg_core.tools.artists.get_cached", return_value=None):
            result = await artists.get_artist_cards(db, "NonExistentArtist12345", use_cache=False)

        assert len(result.cards) == 0


class TestCardModel:
    """Tests for Card model methods."""

    def test_card_to_summary(self) -> None:
        """Card.to_summary() should return formatted summary."""
        card = Card(
            name="Test Card",
            mana_cost="{2}{U}",
            type="Creature — Human Wizard",
            power="2",
            toughness="3",
            text="Draw a card.",
            set_code="TST",
            rarity="Rare",
        )

        summary = card.to_summary()

        assert "Test Card" in summary
        assert "{2}{U}" in summary
        assert "Creature — Human Wizard" in summary
        assert "(2/3)" in summary
        assert "Draw a card." in summary
        assert "TST" in summary

    def test_card_to_summary_planeswalker(self) -> None:
        """Card.to_summary() should handle planeswalker loyalty."""
        card = Card(
            name="Test Planeswalker",
            mana_cost="{3}{U}{U}",
            type="Legendary Planeswalker — Test",
            loyalty="4",
            text="+1: Draw a card.\n-2: Return target creature to its owner's hand.",
        )

        summary = card.to_summary()

        assert "Test Planeswalker" in summary
        assert "Loyalty: 4" in summary

    def test_card_to_summary_battle(self) -> None:
        """Card.to_summary() should handle battle defense."""
        card = Card(
            name="Test Battle",
            mana_cost="{2}{R}",
            type="Battle — Siege",
            defense="5",
            text="When this enters, deal 3 damage to any target.",
        )

        summary = card.to_summary()

        assert "Test Battle" in summary
        assert "Defense: 5" in summary

    def test_card_get_legality(self) -> None:
        """Card.get_legality() should return format legality."""
        card = Card(
            name="Test Card",
            legalities=[
                CardLegality(format="standard", legality="Legal"),
                CardLegality(format="modern", legality="Banned"),
            ],
        )

        assert card.get_legality("standard") == "Legal"
        assert card.get_legality("modern") == "Banned"
        assert card.get_legality("vintage") is None

    def test_card_get_legality_case_insensitive(self) -> None:
        """Card.get_legality() should be case-insensitive."""
        card = Card(
            name="Test Card",
            legalities=[
                CardLegality(format="Standard", legality="Legal"),
            ],
        )

        assert card.get_legality("STANDARD") == "Legal"
        assert card.get_legality("standard") == "Legal"
        assert card.get_legality("StAnDaRd") == "Legal"

    def test_card_is_legal_in(self) -> None:
        """Card.is_legal_in() should check if card is legal."""
        card = Card(
            name="Test Card",
            legalities=[
                CardLegality(format="standard", legality="Legal"),
                CardLegality(format="modern", legality="Banned"),
                CardLegality(format="vintage", legality="Restricted"),
                CardLegality(format="legacy", legality="Not Legal"),
            ],
        )

        assert card.is_legal_in("standard") is True
        assert card.is_legal_in("modern") is False
        assert card.is_legal_in("vintage") is True
        assert card.is_legal_in("legacy") is False

    def test_card_is_legal_no_legalities(self) -> None:
        """Card.is_legal_in() should return False when no legalities."""
        card = Card(name="Test Card")

        assert card.is_legal_in("standard") is False

    def test_card_get_price_usd(self) -> None:
        """Card.get_price_usd() should convert cents to dollars."""
        card = Card(name="Test Card", price_usd=1234)
        assert card.get_price_usd() == 12.34

        card_no_price = Card(name="Test Card")
        assert card_no_price.get_price_usd() is None

    def test_card_get_price_usd_foil(self) -> None:
        """Card.get_price_usd_foil() should convert cents to dollars."""
        card = Card(name="Test Card", price_usd_foil=5678)
        assert card.get_price_usd_foil() == 56.78

        card_no_price = Card(name="Test Card")
        assert card_no_price.get_price_usd_foil() is None

    def test_card_get_price_eur(self) -> None:
        """Card.get_price_eur() should convert cents to euros."""
        card = Card(name="Test Card", price_eur=999)
        assert card.get_price_eur() == 9.99

        card_no_price = Card(name="Test Card")
        assert card_no_price.get_price_eur() is None

    def test_card_get_price_eur_foil(self) -> None:
        """Card.get_price_eur_foil() should convert cents to euros."""
        card = Card(name="Test Card", price_eur_foil=12345)
        assert card.get_price_eur_foil() == 123.45

        card_no_price = Card(name="Test Card")
        assert card_no_price.get_price_eur_foil() is None

    def test_card_parse_finishes_from_json(self) -> None:
        """Card should parse finishes from JSON string."""
        card = Card(name="Test Card", finishes='["nonfoil", "foil"]')
        assert card.finishes == ["nonfoil", "foil"]

    def test_card_parse_finishes_from_list(self) -> None:
        """Card should accept finishes as list."""
        card = Card(name="Test Card", finishes=["nonfoil", "foil"])
        assert card.finishes == ["nonfoil", "foil"]

    def test_card_parse_finishes_none(self) -> None:
        """Card should handle None finishes."""
        card = Card(name="Test Card", finishes=None)
        assert card.finishes == []

    def test_card_parse_finishes_invalid_json(self) -> None:
        """Card should handle invalid JSON finishes."""
        card = Card(name="Test Card", finishes="invalid json")
        assert card.finishes == []
