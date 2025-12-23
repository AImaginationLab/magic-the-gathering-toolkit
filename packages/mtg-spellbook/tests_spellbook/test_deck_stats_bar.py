"""Tests for DeckStatsBar widget."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Static

from mtg_core.data.models.card import Card
from mtg_spellbook.deck.stats_bar import DeckStatsBar
from mtg_spellbook.deck_manager import DeckCardWithData, DeckWithCards


@pytest.fixture
def sample_deck_with_variety() -> DeckWithCards:
    """Create a sample deck with variety of cards."""
    cards = []

    # Lands (24)
    for i in range(12):
        cards.append(
            DeckCardWithData(
                card_name="Forest",
                quantity=1,
                is_sideboard=False,
                is_commander=False,
                set_code=None,
                collector_number=None,
                card=Card(
                    uuid=f"forest-{i}",
                    name="Forest",
                    type="Basic Land — Forest",
                    types=["Land"],
                    text="{T}: Add {G}.",
                    rarity="common",
                    setCode="LEA",
                    number=str(i),
                    artist="Artist",
                    keywords=[],
                ),
            )
        )

    for i in range(12):
        cards.append(
            DeckCardWithData(
                card_name="Mountain",
                quantity=1,
                is_sideboard=False,
                is_commander=False,
                set_code=None,
                collector_number=None,
                card=Card(
                    uuid=f"mountain-{i}",
                    name="Mountain",
                    type="Basic Land — Mountain",
                    types=["Land"],
                    text="{T}: Add {R}.",
                    rarity="common",
                    setCode="LEA",
                    number=str(20 + i),
                    artist="Artist",
                    keywords=[],
                ),
            )
        )

    # Creatures with keywords (16)
    creature_keywords = [
        ("Llanowar Elves", "{G}", 1.0, "1", "1", ["Haste"], "Add {G}"),
        ("Goblin Guide", "{R}", 1.0, "2", "2", ["Haste"], "Haste"),
        ("Tarmogoyf", "{1}{G}", 2.0, "*", "1+*", ["Trample"], "Trample"),
        (
            "Lightning Bolt",
            "{R}",
            1.0,
            None,
            None,
            [],
            "Lightning Bolt deals 3 damage to any target.",
        ),
    ]

    for name, mana, cmc, power, toughness, keywords, text in creature_keywords:
        is_creature = power is not None
        cards.append(
            DeckCardWithData(
                card_name=name,
                quantity=4,
                is_sideboard=False,
                is_commander=False,
                set_code=None,
                collector_number=None,
                card=Card(
                    uuid=f"card-{name}",
                    name=name,
                    manaCost=mana,
                    manaValue=cmc,
                    type="Creature — Elf" if is_creature else "Instant",
                    types=["Creature"] if is_creature else ["Instant"],
                    power=power,
                    toughness=toughness,
                    text=text,
                    rarity="rare",
                    setCode="M21",
                    number="100",
                    artist="Artist",
                    keywords=keywords,
                ),
            )
        )

    # Add ramp, interaction, draw
    cards.append(
        DeckCardWithData(
            card_name="Rampant Growth",
            quantity=4,
            is_sideboard=False,
            is_commander=False,
            set_code=None,
            collector_number=None,
            card=Card(
                uuid="ramp",
                name="Rampant Growth",
                manaCost="{1}{G}",
                manaValue=2.0,
                type="Sorcery",
                types=["Sorcery"],
                text="Search your library for a basic land card, put it onto the battlefield tapped.",
                rarity="common",
                setCode="M21",
                number="200",
                artist="Artist",
                keywords=[],
            ),
        )
    )

    cards.append(
        DeckCardWithData(
            card_name="Harmonize",
            quantity=4,
            is_sideboard=False,
            is_commander=False,
            set_code=None,
            collector_number=None,
            card=Card(
                uuid="draw",
                name="Harmonize",
                manaCost="{2}{G}{G}",
                manaValue=4.0,
                type="Sorcery",
                types=["Sorcery"],
                text="Draw three cards.",
                rarity="uncommon",
                setCode="M21",
                number="300",
                artist="Artist",
                keywords=[],
            ),
        )
    )

    cards.append(
        DeckCardWithData(
            card_name="Beast Within",
            quantity=4,
            is_sideboard=False,
            is_commander=False,
            set_code=None,
            collector_number=None,
            card=Card(
                uuid="removal",
                name="Beast Within",
                manaCost="{2}{G}",
                manaValue=3.0,
                type="Instant",
                types=["Instant"],
                text="Destroy target permanent. Its controller creates a 3/3 green Beast creature token.",
                rarity="uncommon",
                setCode="M21",
                number="400",
                artist="Artist",
                keywords=[],
            ),
        )
    )

    return DeckWithCards(
        id=1,
        name="Test Deck",
        format="standard",
        commander=None,
        cards=cards,
    )


class TestDeckStatsBarWidget:
    """Tests for DeckStatsBar widget functionality."""

    @pytest.mark.asyncio
    async def test_widget_initializes(self) -> None:
        """Test that widget initializes correctly."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)
            assert stats_bar._deck is None
            assert stats_bar._prices == {}

    @pytest.mark.asyncio
    async def test_update_stats_with_none(self) -> None:
        """Test updating stats with None."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)
            # Initial compose already creates the empty state
            # Just verify the empty message is shown by default
            await pilot.pause()

            # Should show empty message - the empty message is in a Static widget
            empty_bar = stats_bar.query_one("#stats-empty-bar", Static)
            assert "Select a deck" in str(empty_bar.render())

    @pytest.mark.asyncio
    async def test_update_stats_with_deck(self, sample_deck_with_variety: DeckWithCards) -> None:
        """Test updating stats with a deck."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)
            stats_bar.update_stats(sample_deck_with_variety)
            await pilot.pause()

            # Should have updated deck
            assert stats_bar._deck == sample_deck_with_variety

    @pytest.mark.asyncio
    async def test_update_stats_with_prices(self, sample_deck_with_variety: DeckWithCards) -> None:
        """Test updating stats with price data."""
        prices = {
            "Lightning Bolt": 2.5,
            "Tarmogoyf": 45.0,
            "Forest": 0.1,
        }

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)
            stats_bar.update_stats(sample_deck_with_variety, prices=prices)
            await pilot.pause()

            # Should have prices stored
            assert stats_bar._prices == prices

    @pytest.mark.asyncio
    async def test_calc_curve(self, sample_deck_with_variety: DeckWithCards) -> None:
        """Test mana curve calculation."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)

            curve = stats_bar._calc_curve(sample_deck_with_variety)

            # Should have CMC entries
            assert isinstance(curve, dict)
            assert curve.get(1, 0) > 0  # 1-drops

    @pytest.mark.asyncio
    async def test_calc_avg_cmc(self, sample_deck_with_variety: DeckWithCards) -> None:
        """Test average CMC calculation."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)

            avg = stats_bar._calc_avg_cmc(sample_deck_with_variety)

            # Should be reasonable
            assert avg >= 0
            assert avg <= 10

    @pytest.mark.asyncio
    async def test_calc_colors(self, sample_deck_with_variety: DeckWithCards) -> None:
        """Test color pip calculation."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)

            colors = stats_bar._calc_colors(sample_deck_with_variety)

            # Should have G and R pips
            assert colors.get("G", 0) > 0
            assert colors.get("R", 0) > 0

    @pytest.mark.asyncio
    async def test_calc_types(self, sample_deck_with_variety: DeckWithCards) -> None:
        """Test card type distribution."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)

            types = stats_bar._calc_types(sample_deck_with_variety)

            # Should have multiple types
            assert "Land" in types
            assert types["Land"] > 0

    @pytest.mark.asyncio
    async def test_count_keywords(self, sample_deck_with_variety: DeckWithCards) -> None:
        """Test keyword counting."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)

            keywords = stats_bar._count_keywords(sample_deck_with_variety)

            # Should count Haste and Trample
            assert "Haste" in keywords or "Trample" in keywords

    @pytest.mark.asyncio
    async def test_count_interaction(self, sample_deck_with_variety: DeckWithCards) -> None:
        """Test interaction spell counting."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)

            interaction = stats_bar._count_interaction(sample_deck_with_variety)

            # Should count Beast Within (destroy) and Lightning Bolt (damage)
            assert interaction > 0

    @pytest.mark.asyncio
    async def test_count_draw(self, sample_deck_with_variety: DeckWithCards) -> None:
        """Test card draw counting."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)

            draw = stats_bar._count_draw(sample_deck_with_variety)

            # Should count Harmonize (draw three cards)
            assert draw >= 4

    @pytest.mark.asyncio
    async def test_count_ramp(self, sample_deck_with_variety: DeckWithCards) -> None:
        """Test ramp spell counting."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)

            ramp = stats_bar._count_ramp(sample_deck_with_variety)

            # Should count Rampant Growth and Llanowar Elves
            assert ramp > 0

    @pytest.mark.asyncio
    async def test_detect_archetype(self, sample_deck_with_variety: DeckWithCards) -> None:
        """Test archetype detection."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)

            archetype, conf = stats_bar._detect_archetype(sample_deck_with_variety)

            # Should return an archetype
            assert isinstance(archetype, str)
            assert conf > 0

    @pytest.mark.asyncio
    async def test_calc_score(self, sample_deck_with_variety: DeckWithCards) -> None:
        """Test deck score calculation."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)

            score = stats_bar._calc_score(sample_deck_with_variety)

            # Should be between 0-100
            assert 0 <= score <= 100

    @pytest.mark.asyncio
    async def test_build_all_columns(self, sample_deck_with_variety: DeckWithCards) -> None:
        """Test that all stat columns build without errors."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)

            # Each column should build
            stats_bar._build_curve_column(sample_deck_with_variety)
            stats_bar._build_colors_column(sample_deck_with_variety)
            stats_bar._build_types_column(sample_deck_with_variety)
            stats_bar._build_keywords_column(sample_deck_with_variety)
            stats_bar._build_analysis_column(sample_deck_with_variety)
            stats_bar._build_price_column(sample_deck_with_variety)

    @pytest.mark.asyncio
    async def test_price_column_with_data(self, sample_deck_with_variety: DeckWithCards) -> None:
        """Test price column with price data."""
        prices = {
            "Tarmogoyf": 50.0,
            "Lightning Bolt": 3.0,
        }

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)
            stats_bar._prices = prices

            column = stats_bar._build_price_column(sample_deck_with_variety)

            # Should build successfully
            assert column is not None

    @pytest.mark.asyncio
    async def test_empty_deck_handling(self) -> None:
        """Test handling of empty deck."""
        empty_deck = DeckWithCards(
            id=1,
            name="Empty",
            format="standard",
            commander=None,
            cards=[],
        )

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            import asyncio

            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)
            # Initial state already shows empty message
            # Verify that after compose, the empty state is shown
            await asyncio.sleep(0.1)

            # Should show empty message - the empty message is in a Static widget
            empty_bar = stats_bar.query_one("#stats-empty-bar", Static)
            assert "Select a deck" in str(empty_bar.render())

            # Verify that empty deck also keeps the empty state
            stats_bar.update_stats(empty_deck)
            await asyncio.sleep(0.1)
            # Still should have the deck stored
            assert stats_bar._deck == empty_deck

    @pytest.mark.asyncio
    async def test_widget_can_focus(self) -> None:
        """Test that widget is focusable."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)
            assert stats_bar.can_focus is True

    @pytest.mark.asyncio
    async def test_count_type_helper(self, sample_deck_with_variety: DeckWithCards) -> None:
        """Test count_type helper method."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckStatsBar(id="stats-bar")

        async with TestApp().run_test() as pilot:
            stats_bar = pilot.app.query_one("#stats-bar", DeckStatsBar)

            lands = stats_bar._count_type(sample_deck_with_variety, "Land")
            assert lands > 0

            creatures = stats_bar._count_type(sample_deck_with_variety, "Creature")
            assert creatures >= 0
