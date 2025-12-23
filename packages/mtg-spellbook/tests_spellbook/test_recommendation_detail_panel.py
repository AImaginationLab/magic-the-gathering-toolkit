"""Tests for RecommendationDetailPanel widget."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest
from textual.app import App, ComposeResult

from mtg_spellbook.recommendations.detail_panel import RecommendationDetailPanel


@pytest.fixture
def sample_recommendation() -> Any:
    """Create a sample recommendation."""
    rec = Mock()
    rec.name = "Lightning Bolt"
    rec.mana_cost = "{R}"
    rec.type_line = "Instant"
    rec.total_score = 0.85
    rec.tfidf_score = 0.6
    rec.synergy_score = 0.7
    rec.tribal_score = 0.0
    rec.combo_score = 0.0
    rec.limited_score = 0.5
    rec.curve_score = 0.4
    rec.popularity_score = 0.8
    rec.land_score = 0.0
    rec.in_collection = False
    rec.reasons = ["High synergy with burn spells", "Popular in similar decks"]
    rec.completes_combos = []
    rec.limited_tier = "A"
    rec.limited_gih_wr = 0.56
    return rec


@pytest.fixture
def sample_combo_recommendation() -> Any:
    """Create a recommendation with combos."""
    rec = Mock()
    rec.name = "Thassa's Oracle"
    rec.mana_cost = "{U}{U}"
    rec.type_line = "Creature — Merfolk Wizard"
    rec.total_score = 0.95
    rec.tfidf_score = 0.5
    rec.synergy_score = 0.6
    rec.tribal_score = 0.3
    rec.combo_score = 0.9
    rec.limited_score = 0.2
    rec.curve_score = 0.5
    rec.popularity_score = 0.85
    rec.land_score = 0.0
    rec.in_collection = True
    rec.reasons = ["Combo piece", "Win condition"]
    rec.completes_combos = ["combo-1", "combo-2", "combo-3"]
    rec.limited_tier = None
    rec.limited_gih_wr = None
    return rec


class TestRecommendationDetailPanel:
    """Tests for RecommendationDetailPanel widget."""

    @pytest.mark.asyncio
    async def test_widget_initializes_empty(self) -> None:
        """Test widget initializes with empty state."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)
            assert panel._recommendation is None
            assert panel._in_collection is False

    @pytest.mark.asyncio
    async def test_shows_empty_message_initially(self) -> None:
        """Test that empty message is shown initially."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)

            # Empty message should be visible - check the static widget
            from textual.widgets import Static

            empty_widget = panel.query_one("#rec-detail-empty", Static)
            assert empty_widget.display

    @pytest.mark.asyncio
    async def test_show_recommendation_updates_display(self, sample_recommendation: Any) -> None:
        """Test showing a recommendation updates the display."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)

            panel.show_recommendation(sample_recommendation)
            await pilot.pause()

            # Should show card name
            assert panel._recommendation == sample_recommendation

    @pytest.mark.asyncio
    async def test_clear_resets_panel(self, sample_recommendation: Any) -> None:
        """Test clearing the panel resets state."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)

            # Show recommendation
            panel.show_recommendation(sample_recommendation)
            await pilot.pause()

            # Clear
            panel.clear()
            await pilot.pause()

            assert panel._recommendation is None

    @pytest.mark.asyncio
    async def test_render_detail_content_basic(self, sample_recommendation: Any) -> None:
        """Test rendering basic recommendation content."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)
            panel._recommendation = sample_recommendation

            content = panel._render_detail_content()

            # Should include type line
            assert "Instant" in content

    @pytest.mark.asyncio
    async def test_render_score_breakdown(self, sample_recommendation: Any) -> None:
        """Test rendering score breakdown."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)
            panel._recommendation = sample_recommendation

            breakdown = panel._render_score_breakdown()

            # Should have score bars
            assert isinstance(breakdown, str)
            assert len(breakdown) > 0

    @pytest.mark.asyncio
    async def test_generate_insights(self, sample_recommendation: Any) -> None:
        """Test generating insights from scores."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)
            panel._recommendation = sample_recommendation

            insights = panel._generate_insights()

            # Should generate some insights
            assert isinstance(insights, list)

    @pytest.mark.asyncio
    async def test_show_in_collection_status(self, sample_combo_recommendation: Any) -> None:
        """Test showing in collection status."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)

            panel.show_recommendation(sample_combo_recommendation, in_collection=True)
            await pilot.pause()

            assert panel._in_collection is True

    @pytest.mark.asyncio
    async def test_render_combos(self, sample_combo_recommendation: Any) -> None:
        """Test rendering combo information."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)
            panel._recommendation = sample_combo_recommendation

            content = panel._render_detail_content()

            # Should mention combos
            assert "Combo" in content

    @pytest.mark.asyncio
    async def test_get_score_color(self, sample_recommendation: Any) -> None:  # noqa: ARG002
        """Test score color helper."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)

            # Test different score ranges
            high_color = panel._get_score_color(0.8)
            mid_color = panel._get_score_color(0.5)
            low_color = panel._get_score_color(0.2)

            assert isinstance(high_color, str)
            assert isinstance(mid_color, str)
            assert isinstance(low_color, str)
            # Colors should be different
            assert high_color != low_color

    @pytest.mark.asyncio
    async def test_get_tier_color(self) -> None:
        """Test tier color helper."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)

            s_color = panel._get_tier_color("S")
            panel._get_tier_color("A")
            f_color = panel._get_tier_color("F")

            # Should return different colors
            assert s_color != f_color

    @pytest.mark.asyncio
    async def test_get_winrate_color(self) -> None:
        """Test winrate color helper."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)

            high_wr = panel._get_winrate_color(0.65)
            low_wr = panel._get_winrate_color(0.42)

            # Should return different colors
            assert high_wr != low_wr

    @pytest.mark.asyncio
    async def test_get_tier_description(self) -> None:
        """Test tier description helper."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)

            s_desc = panel._get_tier_description("S")
            f_desc = panel._get_tier_description("F")

            assert "Best" in s_desc
            assert "Avoid" in f_desc

    @pytest.mark.asyncio
    async def test_get_winrate_description(self) -> None:
        """Test winrate description helper."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)

            high_desc = panel._get_winrate_description(0.62)
            low_desc = panel._get_winrate_description(0.42)

            assert isinstance(high_desc, str)
            assert isinstance(low_desc, str)

    @pytest.mark.asyncio
    async def test_get_cmc_from_mana(self) -> None:
        """Test CMC extraction from mana cost."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)

            # Test various mana costs
            assert panel._get_cmc_from_mana("{R}") == 1
            assert panel._get_cmc_from_mana("{2}{U}{U}") == 4
            assert panel._get_cmc_from_mana("{3}{W}{B}") == 5

    @pytest.mark.asyncio
    async def test_high_text_similarity_insight(self) -> None:
        """Test insight generation for high text similarity."""
        rec = Mock()
        rec.name = "Card"
        rec.type_line = "Instant"
        rec.total_score = 0.6
        rec.tfidf_score = 0.65
        rec.synergy_score = 0.0
        rec.tribal_score = 0.0
        rec.combo_score = 0.0
        rec.limited_score = 0.0
        rec.curve_score = 0.0
        rec.popularity_score = 0.0
        rec.land_score = 0.0
        rec.in_collection = False
        rec.reasons = []
        rec.completes_combos = []
        rec.limited_tier = None
        rec.limited_gih_wr = None

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)
            panel._recommendation = rec

            insights = panel._generate_insights()

            # Should mention text match
            assert any("text" in i.lower() for i in insights)

    @pytest.mark.asyncio
    async def test_high_synergy_insight(self) -> None:
        """Test insight generation for high synergy."""
        rec = Mock()
        rec.name = "Card"
        rec.type_line = "Creature"
        rec.total_score = 0.8
        rec.tfidf_score = 0.0
        rec.synergy_score = 0.85
        rec.tribal_score = 0.0
        rec.combo_score = 0.0
        rec.limited_score = 0.0
        rec.curve_score = 0.0
        rec.popularity_score = 0.0
        rec.land_score = 0.0
        rec.in_collection = False
        rec.reasons = []
        rec.completes_combos = []
        rec.limited_tier = None
        rec.limited_gih_wr = None

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)
            panel._recommendation = rec

            insights = panel._generate_insights()

            # Should mention synergy
            assert any("synergy" in i.lower() for i in insights)

    @pytest.mark.asyncio
    async def test_popular_card_insight(self) -> None:
        """Test insight generation for popular cards."""
        rec = Mock()
        rec.name = "Card"
        rec.type_line = "Instant"
        rec.total_score = 0.9
        rec.tfidf_score = 0.0
        rec.synergy_score = 0.0
        rec.tribal_score = 0.0
        rec.combo_score = 0.0
        rec.limited_score = 0.0
        rec.curve_score = 0.0
        rec.popularity_score = 0.95
        rec.land_score = 0.0
        rec.in_collection = False
        rec.reasons = []
        rec.completes_combos = []
        rec.limited_tier = None
        rec.limited_gih_wr = None

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)
            panel._recommendation = rec

            insights = panel._generate_insights()

            # Should mention popularity/staple
            assert any("staple" in i.lower() or "popular" in i.lower() for i in insights)

    @pytest.mark.asyncio
    async def test_combo_insight(self) -> None:
        """Test insight generation for combo cards."""
        rec = Mock()
        rec.name = "Card"
        rec.type_line = "Creature"
        rec.total_score = 0.9
        rec.tfidf_score = 0.0
        rec.synergy_score = 0.0
        rec.tribal_score = 0.0
        rec.combo_score = 0.8
        rec.limited_score = 0.0
        rec.curve_score = 0.0
        rec.popularity_score = 0.0
        rec.land_score = 0.0
        rec.in_collection = False
        rec.reasons = []
        rec.completes_combos = ["combo-1", "combo-2"]
        rec.limited_tier = None
        rec.limited_gih_wr = None

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)
            panel._recommendation = rec

            insights = panel._generate_insights()

            # Should mention combo
            assert any("combo" in i.lower() for i in insights)

    @pytest.mark.asyncio
    async def test_land_score_insight(self) -> None:
        """Test insight generation for land recommendations."""
        rec = Mock()
        rec.name = "Command Tower"
        rec.type_line = "Land"
        rec.total_score = 1.2
        rec.tfidf_score = 0.0
        rec.synergy_score = 0.0
        rec.tribal_score = 0.0
        rec.combo_score = 0.0
        rec.limited_score = 0.0
        rec.curve_score = 0.0
        rec.popularity_score = 0.0
        rec.land_score = 1.2
        rec.in_collection = False
        rec.reasons = []
        rec.completes_combos = []
        rec.limited_tier = None
        rec.limited_gih_wr = None

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)
            panel._recommendation = rec

            insights = panel._generate_insights()

            # Should mention mana/land
            assert any("mana" in i.lower() or "land" in i.lower() for i in insights)

    @pytest.mark.asyncio
    async def test_in_collection_insight(self) -> None:
        """Test insight generation for cards already in collection."""
        rec = Mock()
        rec.name = "Card"
        rec.type_line = "Instant"
        rec.total_score = 0.5
        rec.tfidf_score = 0.0
        rec.synergy_score = 0.0
        rec.tribal_score = 0.0
        rec.combo_score = 0.0
        rec.limited_score = 0.0
        rec.curve_score = 0.0
        rec.popularity_score = 0.0
        rec.land_score = 0.0
        rec.in_collection = True
        rec.reasons = []
        rec.completes_combos = []
        rec.limited_tier = None
        rec.limited_gih_wr = None

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)
            panel._recommendation = rec

            insights = panel._generate_insights()

            # Should mention owned/collection
            assert any("owned" in i.lower() or "collection" in i.lower() for i in insights)

    @pytest.mark.asyncio
    async def test_basic_land_skips_text_insights(self) -> None:
        """Test that basic lands don't get text similarity insights."""
        rec = Mock()
        rec.name = "Forest"
        rec.type_line = "Basic Land — Forest"
        rec.total_score = 0.5
        rec.tfidf_score = 0.05  # Low complexity
        rec.synergy_score = 0.0
        rec.tribal_score = 0.0
        rec.combo_score = 0.0
        rec.limited_score = 0.0
        rec.curve_score = 0.0
        rec.popularity_score = 0.95  # High popularity
        rec.land_score = 0.8
        rec.in_collection = False
        rec.reasons = []
        rec.completes_combos = []
        rec.limited_tier = None
        rec.limited_gih_wr = None

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield RecommendationDetailPanel(id="detail-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", RecommendationDetailPanel)
            panel._recommendation = rec

            insights = panel._generate_insights()

            # Should NOT mention text similarity or popularity for basic lands
            text_insights = [i for i in insights if "text" in i.lower() and "match" in i.lower()]
            popularity_insights = [
                i for i in insights if "popular" in i.lower() or "staple" in i.lower()
            ]

            assert len(text_insights) == 0
            assert len(popularity_insights) == 0
