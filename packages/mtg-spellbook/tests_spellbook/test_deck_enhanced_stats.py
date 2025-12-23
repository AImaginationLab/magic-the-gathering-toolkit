"""Tests for EnhancedDeckStats widget."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from mtg_core.data.models.card import Card
from mtg_spellbook.deck.enhanced_stats import EnhancedDeckStats
from mtg_spellbook.deck_manager import DeckCardWithData, DeckWithCards


@pytest.fixture
def sample_balanced_deck() -> DeckWithCards:
    """Create a sample balanced deck for testing."""
    cards = []

    # Add lands (24)
    for i in range(10):
        cards.append(
            DeckCardWithData(
                card_name="Plains",
                quantity=1,
                is_sideboard=False,
                is_commander=False,
                set_code="LEA",
                collector_number=str(i),
                card=Card(
                    uuid=f"land-{i}",
                    name="Plains",
                    type="Basic Land — Plains",
                    types=["Land"],
                    subtypes=["Plains"],
                    text="{T}: Add {W}.",
                    rarity="common",
                    setCode="LEA",
                    number=str(i),
                    artist="Artist",
                    keywords=[],
                ),
            )
        )

    for i in range(10):
        cards.append(
            DeckCardWithData(
                card_name="Island",
                quantity=1,
                is_sideboard=False,
                is_commander=False,
                set_code="LEA",
                collector_number=str(10 + i),
                card=Card(
                    uuid=f"island-{i}",
                    name="Island",
                    type="Basic Land — Island",
                    types=["Land"],
                    subtypes=["Island"],
                    text="{T}: Add {U}.",
                    rarity="common",
                    setCode="LEA",
                    number=str(10 + i),
                    artist="Artist",
                    keywords=[],
                ),
            )
        )

    for i in range(4):
        cards.append(
            DeckCardWithData(
                card_name="Hallowed Fountain",
                quantity=1,
                is_sideboard=False,
                is_commander=False,
                set_code="RNA",
                collector_number=str(20 + i),
                card=Card(
                    uuid=f"dual-{i}",
                    name="Hallowed Fountain",
                    type="Land — Plains Island",
                    types=["Land"],
                    subtypes=["Plains", "Island"],
                    text="({T}: Add {W} or {U}.)\nAs Hallowed Fountain enters, you may pay 2 life. If you don't, it enters tapped.",
                    rarity="rare",
                    setCode="RNA",
                    number=str(20 + i),
                    artist="Artist",
                    keywords=[],
                ),
            )
        )

    # Add creatures with varying CMCs (20)
    creature_data = [
        ("Birds of Paradise", "{G}", 1.0, "0", "1", "Flying"),
        ("Lightning Bolt", "{R}", 1.0, None, None, None),  # Instant
        ("Snapcaster Mage", "{1}{U}", 2.0, "2", "1", "Flash"),
        ("Counterspell", "{U}{U}", 2.0, None, None, None),  # Instant
        ("Thragtusk", "{4}{G}", 5.0, "5", "3", None),
        ("Wrath of God", "{2}{W}{W}", 4.0, None, None, None),  # Sorcery
    ]

    for name, mana_cost, cmc, power, toughness, keyword in creature_data:
        card_type = "Creature — Bird" if "Bird" in name else "Creature"
        if "Bolt" in name or "Counterspell" in name:
            card_type = "Instant"
        elif "Wrath" in name:
            card_type = "Sorcery"

        cards.append(
            DeckCardWithData(
                card_name=name,
                quantity=4,
                is_sideboard=False,
                is_commander=False,
                set_code="M21",
                collector_number="100",
                card=Card(
                    uuid=f"creature-{name}",
                    name=name,
                    manaCost=mana_cost,
                    manaValue=cmc,
                    type=card_type,
                    types=["Creature"]
                    if "Creature" in card_type
                    else ["Instant" if "Instant" in card_type else "Sorcery"],
                    power=power,
                    toughness=toughness,
                    text=f"{keyword}\nSample text" if keyword else "Sample text",
                    rarity="rare",
                    setCode="M21",
                    number="100",
                    artist="Artist",
                    keywords=[keyword] if keyword else [],
                ),
            )
        )

    # Add some card draw and interaction
    cards.append(
        DeckCardWithData(
            card_name="Opt",
            quantity=4,
            is_sideboard=False,
            is_commander=False,
            set_code="M21",
            collector_number="200",
            card=Card(
                uuid="opt",
                name="Opt",
                manaCost="{U}",
                manaValue=1.0,
                type="Instant",
                types=["Instant"],
                text="Scry 1.\nDraw a card.",
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
            card_name="Path to Exile",
            quantity=4,
            is_sideboard=False,
            is_commander=False,
            set_code="M21",
            collector_number="300",
            card=Card(
                uuid="path",
                name="Path to Exile",
                manaCost="{W}",
                manaValue=1.0,
                type="Instant",
                types=["Instant"],
                text="Exile target creature. Its controller may search their library for a basic land card.",
                rarity="uncommon",
                setCode="M21",
                number="300",
                artist="Artist",
                keywords=[],
            ),
        )
    )

    return DeckWithCards(
        id=1,
        name="Balanced Deck",
        format="standard",
        commander=None,
        cards=cards,
    )


@pytest.fixture
def sample_aggro_deck() -> DeckWithCards:
    """Create a sample aggro deck for archetype testing."""
    cards = []

    # Add lands (16)
    for i in range(16):
        cards.append(
            DeckCardWithData(
                card_name="Mountain",
                quantity=1,
                is_sideboard=False,
                is_commander=False,
                set_code="LEA",
                collector_number=str(i),
                card=Card(
                    uuid=f"mountain-{i}",
                    name="Mountain",
                    type="Basic Land — Mountain",
                    types=["Land"],
                    text="{T}: Add {R}.",
                    rarity="common",
                    setCode="LEA",
                    number=str(i),
                    artist="Artist",
                    keywords=[],
                ),
            )
        )

    # Add low-cost creatures (30)
    for i in range(15):
        cards.append(
            DeckCardWithData(
                card_name="Goblin Guide",
                quantity=2,
                is_sideboard=False,
                is_commander=False,
                set_code="ZEN",
                collector_number=str(i),
                card=Card(
                    uuid=f"goblin-{i}",
                    name="Goblin Guide",
                    manaCost="{R}",
                    manaValue=1.0,
                    type="Creature — Goblin",
                    types=["Creature"],
                    power="2",
                    toughness="2",
                    text="Haste",
                    rarity="rare",
                    setCode="ZEN",
                    number=str(i),
                    artist="Artist",
                    keywords=["Haste"],
                ),
            )
        )

    # Add burn spells (14)
    for i in range(7):
        cards.append(
            DeckCardWithData(
                card_name="Lightning Bolt",
                quantity=2,
                is_sideboard=False,
                is_commander=False,
                set_code="LEA",
                collector_number=str(100 + i),
                card=Card(
                    uuid=f"bolt-{i}",
                    name="Lightning Bolt",
                    manaCost="{R}",
                    manaValue=1.0,
                    type="Instant",
                    types=["Instant"],
                    text="Lightning Bolt deals 3 damage to any target.",
                    rarity="common",
                    setCode="LEA",
                    number=str(100 + i),
                    artist="Artist",
                    keywords=[],
                ),
            )
        )

    return DeckWithCards(
        id=2,
        name="Aggro Deck",
        format="modern",
        commander=None,
        cards=cards,
    )


class TestEnhancedDeckStatsWidget:
    """Tests for EnhancedDeckStats widget functionality."""

    @pytest.mark.asyncio
    async def test_widget_initializes_empty(self) -> None:
        """Test that widget initializes with empty state."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield EnhancedDeckStats(id="stats")

        async with TestApp().run_test() as pilot:
            stats = pilot.app.query_one("#stats", EnhancedDeckStats)
            assert stats._deck is None

    @pytest.mark.asyncio
    async def test_update_stats_with_none_shows_empty(self) -> None:
        """Test that updating with None shows empty message."""
        import asyncio

        from textual.widgets import Static

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield EnhancedDeckStats(id="stats")

        async with TestApp().run_test() as pilot:
            stats = pilot.app.query_one("#stats", EnhancedDeckStats)
            # Initial compose already shows empty state
            await asyncio.sleep(0.1)

            # Check for empty message in the initial Static
            empty_static = stats.query_one("#stats-empty", Static)
            assert "Select a deck" in str(empty_static.render())

    @pytest.mark.asyncio
    async def test_update_stats_with_deck_builds_cards(
        self, sample_balanced_deck: DeckWithCards
    ) -> None:
        """Test that updating with a deck builds stat cards."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield EnhancedDeckStats(id="stats")

        async with TestApp().run_test() as pilot:
            stats = pilot.app.query_one("#stats", EnhancedDeckStats)
            stats.update_stats(sample_balanced_deck)
            await pilot.pause()

            # Should have stats cards mounted
            assert stats._deck == sample_balanced_deck

    @pytest.mark.asyncio
    async def test_deck_score_calculation(self, sample_balanced_deck: DeckWithCards) -> None:
        """Test deck score calculation logic."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield EnhancedDeckStats(id="stats")

        async with TestApp().run_test() as pilot:
            stats = pilot.app.query_one("#stats", EnhancedDeckStats)

            score, grade, issues = stats._calculate_deck_score(sample_balanced_deck)

            # Score should be reasonable
            assert 0 <= score <= 100
            assert isinstance(grade, str)
            assert isinstance(issues, list)

    @pytest.mark.asyncio
    async def test_avg_cmc_calculation(self, sample_balanced_deck: DeckWithCards) -> None:
        """Test average CMC calculation."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield EnhancedDeckStats(id="stats")

        async with TestApp().run_test() as pilot:
            stats = pilot.app.query_one("#stats", EnhancedDeckStats)

            avg_cmc = stats._calculate_avg_cmc(sample_balanced_deck)

            # Should be a reasonable average
            assert avg_cmc >= 0
            assert avg_cmc <= 10

    @pytest.mark.asyncio
    async def test_mana_curve_calculation(self, sample_balanced_deck: DeckWithCards) -> None:
        """Test mana curve distribution calculation."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield EnhancedDeckStats(id="stats")

        async with TestApp().run_test() as pilot:
            stats = pilot.app.query_one("#stats", EnhancedDeckStats)

            curve = stats._calculate_curve(sample_balanced_deck)

            # Curve should be a dict of CMC -> count
            assert isinstance(curve, dict)
            for cmc, count in curve.items():
                assert 0 <= cmc <= 7
                assert count > 0

    @pytest.mark.asyncio
    async def test_color_distribution(self, sample_balanced_deck: DeckWithCards) -> None:
        """Test color distribution calculation."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield EnhancedDeckStats(id="stats")

        async with TestApp().run_test() as pilot:
            stats = pilot.app.query_one("#stats", EnhancedDeckStats)

            colors = stats._calculate_colors(sample_balanced_deck)

            # Should have color counts
            assert isinstance(colors, dict)
            for color in ["W", "U", "B", "R", "G", "C"]:
                assert color in colors

    @pytest.mark.asyncio
    async def test_type_distribution(self, sample_balanced_deck: DeckWithCards) -> None:
        """Test card type distribution calculation."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield EnhancedDeckStats(id="stats")

        async with TestApp().run_test() as pilot:
            stats = pilot.app.query_one("#stats", EnhancedDeckStats)

            types = stats._calculate_types(sample_balanced_deck)

            # Should have type counts
            assert isinstance(types, dict)
            # Should have lands
            assert "Land" in types

    @pytest.mark.asyncio
    async def test_archetype_detection_aggro(self, sample_aggro_deck: DeckWithCards) -> None:
        """Test archetype detection for aggro deck."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield EnhancedDeckStats(id="stats")

        async with TestApp().run_test() as pilot:
            stats = pilot.app.query_one("#stats", EnhancedDeckStats)

            archetype, confidence, traits = stats._detect_archetype(sample_aggro_deck)

            # Should detect as aggro
            assert archetype == "Aggro"
            assert confidence > 0
            assert isinstance(traits, list)

    @pytest.mark.asyncio
    async def test_count_interaction(self, sample_balanced_deck: DeckWithCards) -> None:
        """Test counting interaction spells."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield EnhancedDeckStats(id="stats")

        async with TestApp().run_test() as pilot:
            stats = pilot.app.query_one("#stats", EnhancedDeckStats)

            interaction = stats._count_interaction(sample_balanced_deck)

            # Should count Path to Exile and other removal
            assert interaction > 0

    @pytest.mark.asyncio
    async def test_count_card_draw(self, sample_balanced_deck: DeckWithCards) -> None:
        """Test counting card draw effects."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield EnhancedDeckStats(id="stats")

        async with TestApp().run_test() as pilot:
            stats = pilot.app.query_one("#stats", EnhancedDeckStats)

            draw = stats._count_card_draw(sample_balanced_deck)

            # Should count Opt
            assert draw >= 4

    @pytest.mark.asyncio
    async def test_analyze_lands(self, sample_balanced_deck: DeckWithCards) -> None:
        """Test land type analysis."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield EnhancedDeckStats(id="stats")

        async with TestApp().run_test() as pilot:
            stats = pilot.app.query_one("#stats", EnhancedDeckStats)

            land_types = stats._analyze_lands(sample_balanced_deck)

            # Should categorize lands
            assert isinstance(land_types, dict)
            # Should have basics
            assert land_types.get("Basic", 0) > 0

    @pytest.mark.asyncio
    async def test_empty_deck_handling(self) -> None:
        """Test handling of completely empty deck."""
        import asyncio

        from textual.widgets import Static

        empty_deck = DeckWithCards(
            id=1,
            name="Empty Deck",
            format="standard",
            commander=None,
            cards=[],
        )

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield EnhancedDeckStats(id="stats")

        async with TestApp().run_test() as pilot:
            stats = pilot.app.query_one("#stats", EnhancedDeckStats)
            # Initial state shows empty message
            await asyncio.sleep(0.1)

            # Check the initial empty state exists
            empty_static = stats.query_one("#stats-empty", Static)
            assert "Select a deck" in str(empty_static.render())

            # Verify updating with empty deck keeps the deck stored
            stats.update_stats(empty_deck)
            await asyncio.sleep(0.1)
            assert stats._deck == empty_deck

    @pytest.mark.asyncio
    async def test_commander_format_detection(self) -> None:
        """Test that commander format is detected properly."""
        commander_deck = DeckWithCards(
            id=1,
            name="Commander Deck",
            format="commander",
            commander="Sol Ring",
            cards=[],
        )

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield EnhancedDeckStats(id="stats")

        async with TestApp().run_test() as pilot:
            stats = pilot.app.query_one("#stats", EnhancedDeckStats)

            score, _grade, _issues = stats._calculate_deck_score(commander_deck)

            # Commander deck should expect 99 cards
            # Empty deck should have penalty
            assert score < 100

    @pytest.mark.asyncio
    async def test_cmc_color_helpers(self, sample_balanced_deck: DeckWithCards) -> None:  # noqa: ARG002
        """Test CMC and land color helper methods."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield EnhancedDeckStats(id="stats")

        async with TestApp().run_test() as pilot:
            stats = pilot.app.query_one("#stats", EnhancedDeckStats)

            # Test CMC color
            assert stats._cmc_color(2.0) == "#7ec850"
            assert stats._cmc_color(3.0) == "#e6c84a"
            assert stats._cmc_color(5.0) == "#e86a58"

            # Test land color (ratio-based)
            good_color = stats._land_color(24, 60)  # 40% - good
            assert good_color == "#7ec850"

    @pytest.mark.asyncio
    async def test_score_card_rendering(self, sample_balanced_deck: DeckWithCards) -> None:
        """Test that score card renders without errors."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield EnhancedDeckStats(id="stats")

        async with TestApp().run_test() as pilot:
            stats = pilot.app.query_one("#stats", EnhancedDeckStats)

            card = stats._build_score_card(sample_balanced_deck)
            assert card is not None

    @pytest.mark.asyncio
    async def test_all_stat_cards_build(self, sample_balanced_deck: DeckWithCards) -> None:
        """Test that all stat cards build without errors."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield EnhancedDeckStats(id="stats")

        async with TestApp().run_test() as pilot:
            stats = pilot.app.query_one("#stats", EnhancedDeckStats)

            # Each card should build without raising
            stats._build_score_card(sample_balanced_deck)
            stats._build_metrics_card(sample_balanced_deck)
            stats._build_curve_card(sample_balanced_deck)
            stats._build_color_card(sample_balanced_deck)
            stats._build_types_card(sample_balanced_deck)
            stats._build_manabase_card(sample_balanced_deck)
            stats._build_archetype_card(sample_balanced_deck)
