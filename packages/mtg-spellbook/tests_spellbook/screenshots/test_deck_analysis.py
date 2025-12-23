"""Tests for deck analysis panel content.

This test verifies that the DeckAnalysisPanel actually displays content
when a deck is loaded.

Run with: uv run pytest packages/mtg-spellbook/tests_spellbook/screenshots/test_deck_analysis.py -v
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from mtg_spellbook.app import MTGSpellbook
from mtg_spellbook.deck.analysis_panel import DeckAnalysisPanel
from mtg_spellbook.deck.full_screen import FullDeckScreen
from mtg_spellbook.deck_manager import DeckCardWithData, DeckWithCards

if TYPE_CHECKING:
    from mtg_core.data.models.card import Card


def create_mock_card(
    name: str,
    mana_cost: str,
    type_line: str,
    text: str = "",
    cmc: float = 0,
    colors: list[str] | None = None,
    keywords: list[str] | None = None,
    rarity: str = "common",
    power: str | None = None,
    toughness: str | None = None,
) -> Card:
    """Create a mock Card object with specified properties."""
    from mtg_core.data.models.card import Card

    return Card(
        uuid=f"uuid-{name.lower().replace(' ', '-')}",
        name=name,
        manaCost=mana_cost,
        manaValue=cmc,
        colors=colors or [],
        colorIdentity=colors or [],
        type=type_line,
        types=[t.strip() for t in type_line.split("-")[0].split() if t.strip() not in ("Legendary", "Basic")],
        text=text,
        rarity=rarity,
        setCode="TST",
        number="001",
        artist="Test Artist",
        keywords=keywords or [],
        power=power,
        toughness=toughness,
    )


@pytest.fixture
def sample_deck_for_analysis() -> DeckWithCards:
    """Create a sample deck with diverse cards for analysis testing."""
    cards = [
        DeckCardWithData(
            card_name="Goblin Guide",
            quantity=4,
            is_sideboard=False,
            is_commander=False,
            set_code="ZEN",
            collector_number="126",
            card=create_mock_card(
                name="Goblin Guide",
                mana_cost="{R}",
                type_line="Creature — Goblin Scout",
                text="Haste",
                cmc=1,
                colors=["R"],
                keywords=["Haste"],
                power="2",
                toughness="2",
            ),
        ),
        DeckCardWithData(
            card_name="Monastery Swiftspear",
            quantity=4,
            is_sideboard=False,
            is_commander=False,
            set_code="KTK",
            collector_number="118",
            card=create_mock_card(
                name="Monastery Swiftspear",
                mana_cost="{R}",
                type_line="Creature — Human Monk",
                text="Haste\nProwess",
                cmc=1,
                colors=["R"],
                keywords=["Haste", "Prowess"],
                power="1",
                toughness="2",
            ),
        ),
        DeckCardWithData(
            card_name="Eidolon of the Great Revel",
            quantity=4,
            is_sideboard=False,
            is_commander=False,
            set_code="JOU",
            collector_number="94",
            card=create_mock_card(
                name="Eidolon of the Great Revel",
                mana_cost="{R}{R}",
                type_line="Enchantment Creature — Spirit",
                text="Whenever a player casts a spell with mana value 3 or less, Eidolon deals 2 damage to that player.",
                cmc=2,
                colors=["R"],
                power="2",
                toughness="2",
            ),
        ),
        DeckCardWithData(
            card_name="Lightning Bolt",
            quantity=4,
            is_sideboard=False,
            is_commander=False,
            set_code="M21",
            collector_number="152",
            card=create_mock_card(
                name="Lightning Bolt",
                mana_cost="{R}",
                type_line="Instant",
                text="Lightning Bolt deals 3 damage to any target.",
                cmc=1,
                colors=["R"],
            ),
        ),
        DeckCardWithData(
            card_name="Lava Spike",
            quantity=4,
            is_sideboard=False,
            is_commander=False,
            set_code="MMA",
            collector_number="121",
            card=create_mock_card(
                name="Lava Spike",
                mana_cost="{R}",
                type_line="Sorcery — Arcane",
                text="Lava Spike deals 3 damage to target player or planeswalker.",
                cmc=1,
                colors=["R"],
            ),
        ),
        DeckCardWithData(
            card_name="Rift Bolt",
            quantity=4,
            is_sideboard=False,
            is_commander=False,
            set_code="TSP",
            collector_number="176",
            card=create_mock_card(
                name="Rift Bolt",
                mana_cost="{2}{R}",
                type_line="Sorcery",
                text="Rift Bolt deals 3 damage to any target.",
                cmc=3,
                colors=["R"],
                keywords=["Suspend"],
            ),
        ),
        DeckCardWithData(
            card_name="Searing Blaze",
            quantity=4,
            is_sideboard=False,
            is_commander=False,
            set_code="WWK",
            collector_number="90",
            card=create_mock_card(
                name="Searing Blaze",
                mana_cost="{R}{R}",
                type_line="Instant",
                text="Searing Blaze deals 1 damage to target player and 1 damage to target creature.",
                cmc=2,
                colors=["R"],
            ),
        ),
        DeckCardWithData(
            card_name="Light Up the Stage",
            quantity=4,
            is_sideboard=False,
            is_commander=False,
            set_code="RNA",
            collector_number="107",
            card=create_mock_card(
                name="Light Up the Stage",
                mana_cost="{2}{R}",
                type_line="Sorcery",
                text="Spectacle {R}\nExile the top two cards of your library. You may play those cards.",
                cmc=3,
                colors=["R"],
                keywords=["Spectacle"],
            ),
        ),
        DeckCardWithData(
            card_name="Mountain",
            quantity=18,
            is_sideboard=False,
            is_commander=False,
            set_code="TST",
            collector_number="001",
            card=create_mock_card(
                name="Mountain",
                mana_cost="",
                type_line="Basic Land — Mountain",
                text="({T}: Add {R}.)",
                cmc=0,
                colors=[],
            ),
        ),
        DeckCardWithData(
            card_name="Inspiring Vantage",
            quantity=4,
            is_sideboard=False,
            is_commander=False,
            set_code="KLD",
            collector_number="246",
            card=create_mock_card(
                name="Inspiring Vantage",
                mana_cost="",
                type_line="Land",
                text="Inspiring Vantage enters tapped unless you control two or fewer other lands.",
                cmc=0,
                colors=[],
            ),
        ),
        DeckCardWithData(
            card_name="Smash to Smithereens",
            quantity=4,
            is_sideboard=True,
            is_commander=False,
            set_code="ORI",
            collector_number="163",
            card=create_mock_card(
                name="Smash to Smithereens",
                mana_cost="{1}{R}",
                type_line="Instant",
                text="Destroy target artifact. Smash to Smithereens deals 3 damage to that artifact's controller.",
                cmc=2,
                colors=["R"],
            ),
        ),
    ]

    return DeckWithCards(
        id=1,
        name="Mono-Red Burn",
        format="modern",
        commander=None,
        cards=cards,
    )


class TestDeckAnalysisPanel:
    """Tests for the DeckAnalysisPanel widget."""

    @pytest.mark.asyncio
    async def test_analysis_panel_shows_content_not_empty(
        self,
        sample_deck_for_analysis: DeckWithCards,
    ) -> None:
        """Verify analysis panel shows actual content when a deck is provided."""
        from textual.app import App, ComposeResult
        from textual.widgets import Static

        class TestApp(App[None]):
            CSS = """
            DeckAnalysisPanel {
                width: 100%;
                height: 100%;
            }
            """

            def compose(self) -> ComposeResult:
                yield DeckAnalysisPanel(id="analysis-panel")

        async with TestApp().run_test(size=(80, 40)) as pilot:
            panel = pilot.app.query_one("#analysis-panel", DeckAnalysisPanel)

            # Initially shows empty state
            empty_static = panel.query_one("#analysis-empty", Static)
            assert empty_static.display is True, "Should show empty state initially"

            # Now update with the deck
            panel.update_analysis(sample_deck_for_analysis)

            # Wait for UI to update
            await pilot.pause()

            # The empty state should be hidden
            assert empty_static.display is False, "Empty state should be hidden after update"

            # Content should be visible
            content = panel.query_one("#analysis-content", Static)
            assert content.display is True, "Content should be visible"

            # Content should have the deck name
            rendered = str(content.render())
            assert "Mono-Red Burn" in rendered, f"Deck name not found. Got: {rendered[:200]}..."
            assert "Creatures" in rendered, f"'Creatures' not found. Got: {rendered[:200]}..."
            assert "Lands" in rendered, f"'Lands' not found. Got: {rendered[:200]}..."

    @pytest.mark.asyncio
    async def test_analysis_panel_shows_deck_score(
        self,
        sample_deck_for_analysis: DeckWithCards,
    ) -> None:
        """Verify the DECK SCORE section is rendered with score value."""
        from textual.app import App, ComposeResult
        from textual.widgets import Static

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckAnalysisPanel(id="analysis-panel")

        async with TestApp().run_test(size=(80, 40)) as pilot:
            panel = pilot.app.query_one("#analysis-panel", DeckAnalysisPanel)
            panel.update_analysis(sample_deck_for_analysis)
            await pilot.pause()

            # Check content for score
            content = panel.query_one("#analysis-content", Static)
            rendered = str(content.render())

            # Should have DECK SCORE section
            assert "DECK SCORE" in rendered, f"DECK SCORE header not found. Got: {rendered[:300]}..."
            # Should have a score like "XX/100"
            assert "/100" in rendered, f"Score format '/100' not found. Got: {rendered[:300]}..."

    @pytest.mark.asyncio
    async def test_analysis_panel_shows_type_breakdown(
        self,
        sample_deck_for_analysis: DeckWithCards,
    ) -> None:
        """Verify KEY METRICS section shows type breakdown."""
        from textual.app import App, ComposeResult
        from textual.widgets import Static

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield DeckAnalysisPanel(id="analysis-panel")

        async with TestApp().run_test(size=(80, 40)) as pilot:
            panel = pilot.app.query_one("#analysis-panel", DeckAnalysisPanel)
            panel.update_analysis(sample_deck_for_analysis)
            await pilot.pause()

            content = panel.query_one("#analysis-content", Static)
            rendered = str(content.render())

            assert "Creatures" in rendered, "Should show creature count"
            assert "Instants" in rendered, "Should show instant count"
            assert "Lands" in rendered, "Should show land count"

    @pytest.mark.asyncio
    async def test_analysis_svg_contains_content(
        self,
        sample_deck_for_analysis: DeckWithCards,
    ) -> None:
        """Verify the SVG export contains the actual text content."""
        from textual.app import App, ComposeResult

        class TestApp(App[None]):
            CSS = """
            DeckAnalysisPanel {
                width: 100%;
                height: 100%;
            }
            """

            def compose(self) -> ComposeResult:
                yield DeckAnalysisPanel(id="analysis-panel")

        async with TestApp().run_test(size=(80, 80)) as pilot:
            panel = pilot.app.query_one("#analysis-panel", DeckAnalysisPanel)
            panel.update_analysis(sample_deck_for_analysis)
            await pilot.pause()

            # Export SVG
            svg = pilot.app.export_screenshot()

            # Check for content in SVG (sections now reordered)
            assert "Mono-Red" in svg, "SVG should contain 'Mono-Red'"
            assert "MANA" in svg and "CURVE" in svg, "SVG should contain 'MANA CURVE'"
            # Check for deck score header (may be HTML-escaped)
            assert "DECK" in svg and "SCORE" in svg, "SVG should contain 'DECK SCORE'"
