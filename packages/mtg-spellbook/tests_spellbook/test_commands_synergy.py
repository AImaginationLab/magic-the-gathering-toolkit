"""Tests for synergy commands mixin."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from mtg_core.data.models.responses import (
    CardDetail,
    Combo,
    DetectCombosResult,
    FindSynergiesResult,
    Prices,
    SynergyResult,
)
from mtg_core.exceptions import CardNotFoundError


@pytest.fixture
def sample_source_card() -> CardDetail:
    """Sample source card for synergy testing."""
    return CardDetail(
        uuid="source-uuid",
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
        legalities={"vintage": "legal", "legacy": "legal"},
        prices=Prices(usd=8.50),
    )


@pytest.fixture
def sample_synergies() -> list[SynergyResult]:
    """Sample synergies for testing."""
    return [
        SynergyResult(
            name="Sol Ring",
            synergy_type="keyword",
            reason="Ramp synergy",
            score=0.9,
        ),
        SynergyResult(
            name="Chromatic Lantern",
            synergy_type="ability",
            reason="Mana fixing",
            score=0.8,
        ),
        SynergyResult(
            name="Llanowar Elves",
            synergy_type="theme",
            reason="Mana acceleration theme",
            score=0.7,
        ),
    ]


@pytest.fixture
def sample_combos() -> list[Combo]:
    """Sample combos for testing."""
    from mtg_core.data.models.responses import ComboCard

    return [
        Combo(
            id="combo1",
            combo_type="infinite",
            description="Infinite mana combo",
            cards=[
                ComboCard(name="Deadeye Navigator", role="repeater"),
                ComboCard(name="Palinchron", role="untapper"),
            ],
            colors=["U"],
        ),
        Combo(
            id="combo2",
            combo_type="infinite",
            description="Infinite damage combo",
            cards=[
                ComboCard(name="Splinter Twin", role="copier"),
                ComboCard(name="Pestermite", role="untapper"),
            ],
            colors=["U", "R"],
        ),
    ]


class TestSynergyCommands:
    """Tests for SynergyCommandsMixin functionality."""

    @pytest.mark.asyncio
    async def test_find_synergies(
        self,
        mock_app_with_database,
        sample_source_card: CardDetail,
        sample_synergies: list[SynergyResult],
    ) -> None:
        """Test finding synergies for a card."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            synergy_result = FindSynergiesResult(
                card_name=sample_source_card.name,
                synergies=sample_synergies,
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.cards.get_card", AsyncMock(return_value=sample_source_card)
                )
                m.setattr(
                    "mtg_core.tools.synergy.find_synergies", AsyncMock(return_value=synergy_result)
                )

                app.find_synergies("Birds of Paradise")
                await pilot.pause(0.3)

                assert app._synergy_mode is True
                assert len(app._synergy_info) > 0

    @pytest.mark.asyncio
    async def test_find_synergies_card_not_found(self, mock_app_with_database) -> None:
        """Test finding synergies for non-existent card."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.cards.get_card",
                    AsyncMock(side_effect=CardNotFoundError("Not found")),
                )

                app.find_synergies("Nonexistent Card")
                await pilot.pause(0.2)

                assert app._synergy_mode is False

    @pytest.mark.asyncio
    async def test_find_synergies_no_results(
        self, mock_app_with_database, sample_source_card: CardDetail
    ) -> None:
        """Test finding synergies when none exist."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            synergy_result = FindSynergiesResult(
                card_name=sample_source_card.name,
                synergies=[],
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.cards.get_card", AsyncMock(return_value=sample_source_card)
                )
                m.setattr(
                    "mtg_core.tools.synergy.find_synergies", AsyncMock(return_value=synergy_result)
                )

                app.find_synergies("Birds of Paradise")
                await pilot.pause(0.2)

                assert app._synergy_mode is False

    @pytest.mark.asyncio
    async def test_find_synergies_no_database(self, mock_app_with_database) -> None:
        """Test finding synergies with no database."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db = None

            app.find_synergies("Test Card")
            await pilot.pause(0.1)

    @pytest.mark.asyncio
    async def test_find_synergies_with_collection(
        self,
        mock_app_with_database,
        sample_source_card: CardDetail,
        sample_synergies: list[SynergyResult],
    ) -> None:
        """Test finding synergies with collection manager."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            # Mock collection manager
            app._collection_manager = AsyncMock()
            app._collection_manager.get_collection_card_names = AsyncMock(
                return_value={"Sol Ring", "Chromatic Lantern"}
            )

            synergy_result = FindSynergiesResult(
                card_name=sample_source_card.name,
                synergies=sample_synergies,
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.cards.get_card", AsyncMock(return_value=sample_source_card)
                )
                m.setattr(
                    "mtg_core.tools.synergy.find_synergies", AsyncMock(return_value=synergy_result)
                )

                app.find_synergies("Birds of Paradise")
                await pilot.pause(0.3)

    @pytest.mark.asyncio
    async def test_find_combos(self, mock_app_with_database, sample_combos: list[Combo]) -> None:
        """Test finding combos for a card."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            combo_result = DetectCombosResult(
                combos=sample_combos[:1],
                potential_combos=sample_combos[1:],
                missing_cards={"combo2": ["Splinter Twin"]},
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.synergy.detect_combos", AsyncMock(return_value=combo_result)
                )

                app.find_combos("Deadeye Navigator")
                await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_find_combos_no_results(self, mock_app_with_database) -> None:
        """Test finding combos when none exist."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            combo_result = DetectCombosResult(
                combos=[],
                potential_combos=[],
                missing_cards={},
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.synergy.detect_combos", AsyncMock(return_value=combo_result)
                )

                app.find_combos("Test Card")
                await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_find_combos_only_complete(
        self, mock_app_with_database, sample_combos: list[Combo]
    ) -> None:
        """Test finding only complete combos."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            combo_result = DetectCombosResult(
                combos=sample_combos,
                potential_combos=[],
                missing_cards={},
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.synergy.detect_combos", AsyncMock(return_value=combo_result)
                )

                app.find_combos("Deadeye Navigator")
                await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_find_combos_only_potential(
        self, mock_app_with_database, sample_combos: list[Combo]
    ) -> None:
        """Test finding only potential combos."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            combo_result = DetectCombosResult(
                combos=[],
                potential_combos=sample_combos,
                missing_cards={
                    "combo1": ["Card A"],
                    "combo2": ["Card B", "Card C"],
                },
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.synergy.detect_combos", AsyncMock(return_value=combo_result)
                )

                app.find_combos("Test Card")
                await pilot.pause(0.2)

    @pytest.mark.asyncio
    async def test_find_combos_no_database(self, mock_app_with_database) -> None:
        """Test finding combos with no database."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._db = None

            app.find_combos("Test Card")
            await pilot.pause(0.1)

    @pytest.mark.asyncio
    async def test_update_card_panel_with_synergy(
        self, mock_app_with_database, sample_source_card: CardDetail
    ) -> None:
        """Test updating card panel with synergy info."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._synergy_info = {
                sample_source_card.name: {
                    "type": "keyword",
                    "reason": "Test synergy",
                    "score": 0.9,
                }
            }

            app._current_card = sample_source_card
            app._update_card_panel(sample_source_card)
            await pilot.pause()

            app._update_card_panel_with_synergy(sample_source_card)
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_show_source_card(
        self, mock_app_with_database, sample_source_card: CardDetail
    ) -> None:
        """Test showing source card in comparison panel."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            app._show_source_card(sample_source_card)
            await pilot.pause()

            source_panel = app.query_one("#source-card-panel")
            assert "visible" in source_panel.classes


class TestSynergyCommandsIntegration:
    """Integration tests for synergy commands."""

    @pytest.mark.asyncio
    async def test_synergy_workflow(
        self,
        mock_app_with_database,
        sample_source_card: CardDetail,
        sample_synergies: list[SynergyResult],
    ) -> None:
        """Test complete synergy workflow."""
        app = mock_app_with_database()

        async with app.run_test() as pilot:
            synergy_result = FindSynergiesResult(
                card_name=sample_source_card.name,
                synergies=sample_synergies,
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "mtg_core.tools.cards.get_card", AsyncMock(return_value=sample_source_card)
                )
                m.setattr(
                    "mtg_core.tools.synergy.find_synergies", AsyncMock(return_value=synergy_result)
                )

                # Find synergies
                app.find_synergies("Birds of Paradise")
                await pilot.pause(0.3)

                # Verify synergy mode active
                assert app._synergy_mode is True

                # Verify synergy info populated
                assert len(app._synergy_info) == len(sample_synergies)

                # Verify panels updated
                main_container = app.query_one("#main-container")
                assert "synergy-layout" in main_container.classes
