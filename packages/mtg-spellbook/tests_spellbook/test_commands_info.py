"""Tests for info commands mixin."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from mtg_core.data.models.responses import CardDetail, PriceResponse, Prices, PurchaseLinks
from mtg_core.exceptions import CardNotFoundError


@pytest.fixture
def sample_card() -> CardDetail:
    """Sample card for testing."""
    return CardDetail(
        uuid="test-uuid",
        name="Test Card",
        mana_cost="{2}{U}",
        type="Creature — Human Wizard",
        text="Test text",
        power="2",
        toughness="2",
        colors=["U"],
        color_identity=["U"],
        keywords=["Flying"],
        cmc=3.0,
        rarity="rare",
        set_code="TST",
        number="1",
        artist="Test Artist",
        legalities={"standard": "legal", "modern": "legal"},
        prices=Prices(usd=5.50, usd_foil=12.00),
    )


class TestInfoCommands:
    """Tests for InfoCommandsMixin functionality."""

    @pytest.mark.asyncio
    async def test_load_legalities(self, mock_app_with_database, sample_card: CardDetail) -> None:
        """Test loading legalities for a card."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._current_card = sample_card
            app._update_card_panel(sample_card)
            await pilot.pause()

            panel = app.query_one("#card-panel")
            panel.load_legalities = AsyncMock()

            app.load_legalities("Test Card")
            await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_load_legalities_no_database(self, mock_app_with_database) -> None:
        """Test load legalities with no database."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db = None

            app.load_legalities("Test Card")
            await pilot.pause(0.1)

    @pytest.mark.asyncio
    async def test_show_price_with_usd(self, mock_app_with_database) -> None:
        """Test showing price for a card with USD price."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            price_result = PriceResponse(
                card_name="Test Card",
                set_code="TST",
                prices=Prices(usd=5.50),
                purchase_links=PurchaseLinks(),
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.images.get_card_price", AsyncMock(return_value=price_result)
                )
                app.show_price("Test Card")
                await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_show_price_with_foil(self, mock_app_with_database) -> None:
        """Test showing price with foil price."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            price_result = PriceResponse(
                card_name="Test Card",
                set_code="TST",
                prices=Prices(usd=5.50, usd_foil=12.00),
                purchase_links=PurchaseLinks(),
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.images.get_card_price", AsyncMock(return_value=price_result)
                )
                app.show_price("Test Card")
                await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_show_price_no_price(self, mock_app_with_database) -> None:
        """Test showing price when no price available."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            price_result = PriceResponse(
                card_name="Test Card",
                set_code="TST",
                prices=Prices(),
                purchase_links=PurchaseLinks(),
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.images.get_card_price", AsyncMock(return_value=price_result)
                )
                app.show_price("Test Card")
                await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_show_price_card_not_found(self, mock_app_with_database) -> None:
        """Test showing price for non-existent card."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.images.get_card_price",
                    AsyncMock(side_effect=CardNotFoundError("Not found")),
                )
                app.show_price("Nonexistent Card")
                await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_show_price_no_database(self, mock_app_with_database) -> None:
        """Test show price with no database."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db = None

            app.show_price("Test Card")
            await pilot.pause(0.1)

    @pytest.mark.asyncio
    async def test_show_art(self, mock_app_with_database, sample_card: CardDetail) -> None:
        """Test showing card art with printings."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._current_card = sample_card
            app._update_card_panel(sample_card)
            await pilot.pause()

            panel = app.query_one("#card-panel")
            panel.load_printings = AsyncMock()

            app.show_art("Test Card")
            await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_show_art_no_database(self, mock_app_with_database) -> None:
        """Test show art with no database."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db = None

            app.show_art("Test Card")
            await pilot.pause(0.1)


class TestInfoCommandsIntegration:
    """Integration tests for info commands."""

    @pytest.mark.asyncio
    async def test_sequential_info_commands(
        self, mock_app_with_database, sample_card: CardDetail
    ) -> None:
        """Test running multiple info commands in sequence."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._current_card = sample_card
            app._update_card_panel(sample_card)
            await pilot.pause()

            panel = app.query_one("#card-panel")
            panel.load_legalities = AsyncMock()
            panel.load_printings = AsyncMock()

            # Run commands sequentially
            app.load_legalities("Test Card")
            await pilot.pause(0.1)

            app.show_art("Test Card")
            await pilot.pause(0.1)
