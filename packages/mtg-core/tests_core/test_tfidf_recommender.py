"""Tests for TF-IDF recommendation system.

Tests focus on unit testing helper methods and data structures.
Integration tests would require a real database and are covered in integration test suite.
Target coverage: 60%+ (helper methods and error paths).
"""

from __future__ import annotations

import pytest

from mtg_core.tools.recommendations.tfidf import (
    CardRecommendation,
    CardRecommender,
    get_recommender,
)


class TestCardRecommendation:
    """Tests for CardRecommendation dataclass."""

    def test_card_recommendation_basic(self) -> None:
        """Test creating a basic CardRecommendation."""
        rec = CardRecommendation(name="Lightning Bolt", score=0.95)

        assert rec.name == "Lightning Bolt"
        assert rec.score == 0.95
        assert rec.uuid is None
        assert rec.type_line is None

    def test_card_recommendation_with_details(self) -> None:
        """Test CardRecommendation with all fields."""
        rec = CardRecommendation(
            name="Lightning Bolt",
            score=0.85,
            uuid="uuid-123",
            type_line="Instant",
            mana_cost="{R}",
            colors=["R"],
        )

        assert rec.uuid == "uuid-123"
        assert rec.type_line == "Instant"
        assert rec.mana_cost == "{R}"
        assert rec.colors == ["R"]


class TestCardRecommenderHelpers:
    """Tests for CardRecommender helper methods (no database required)."""

    def test_clean_mana_symbols_basic_colors(self) -> None:
        """Test cleaning basic color symbols."""
        recommender = CardRecommender()

        text = "{W}{U}{B}{R}{G}"
        cleaned = recommender._clean_mana_symbols(text)

        assert "white mana" in cleaned
        assert "blue mana" in cleaned
        assert "black mana" in cleaned
        assert "red mana" in cleaned
        assert "green mana" in cleaned

    def test_clean_mana_symbols_special(self) -> None:
        """Test cleaning special symbols."""
        recommender = CardRecommender()

        text = "{C}{T}{Q}{X}"
        cleaned = recommender._clean_mana_symbols(text)

        assert "colorless mana" in cleaned
        assert "tap" in cleaned
        assert "untap" in cleaned
        assert "variable" in cleaned

    def test_clean_mana_symbols_preserves_text(self) -> None:
        """Test cleaning preserves surrounding text."""
        recommender = CardRecommender()

        text = "Pay {R}: Deal damage"
        cleaned = recommender._clean_mana_symbols(text)

        assert "Pay" in cleaned
        assert "Deal damage" in cleaned
        assert "red mana" in cleaned

    def test_expand_colors_basic(self) -> None:
        """Test expanding color codes."""
        recommender = CardRecommender()

        expanded = recommender._expand_colors("WUBRG")

        assert "white" in expanded
        assert "blue" in expanded
        assert "black" in expanded
        assert "red" in expanded
        assert "green" in expanded

    def test_expand_colors_case_insensitive(self) -> None:
        """Test color expansion is case-insensitive."""
        recommender = CardRecommender()

        expanded = recommender._expand_colors("wubrg")

        assert "white" in expanded
        assert "blue" in expanded

    def test_expand_colors_empty(self) -> None:
        """Test expanding empty color string."""
        recommender = CardRecommender()

        expanded = recommender._expand_colors("")

        assert expanded == ""

    def test_expand_colors_unknown(self) -> None:
        """Test expanding unknown color codes."""
        recommender = CardRecommender()

        expanded = recommender._expand_colors("XYZ")

        assert expanded == ""

    def test_expand_colors_mixed_valid_invalid(self) -> None:
        """Test expanding mix of valid and invalid codes."""
        recommender = CardRecommender()

        expanded = recommender._expand_colors("RXG")

        assert "red" in expanded
        assert "green" in expanded

    def test_parse_colors_none(self) -> None:
        """Test parsing None colors."""
        recommender = CardRecommender()

        result = recommender._parse_colors(None)

        assert result is None

    def test_parse_colors_list(self) -> None:
        """Test parsing list colors."""
        recommender = CardRecommender()

        result = recommender._parse_colors(["R", "G"])

        assert result == ["R", "G"]

    def test_parse_colors_json_string(self) -> None:
        """Test parsing JSON string colors."""
        recommender = CardRecommender()

        result = recommender._parse_colors('["W", "U"]')

        assert result == ["W", "U"]

    def test_parse_colors_comma_separated(self) -> None:
        """Test parsing comma-separated colors."""
        recommender = CardRecommender()

        result = recommender._parse_colors("R, G, B")

        assert result == ["R", "G", "B"]

    def test_parse_colors_invalid_json(self) -> None:
        """Test parsing invalid JSON falls back to split."""
        recommender = CardRecommender()

        result = recommender._parse_colors("[invalid")

        assert result == ["[invalid"]

    def test_parse_colors_empty_string(self) -> None:
        """Test parsing empty string."""
        recommender = CardRecommender()

        result = recommender._parse_colors("")

        assert result == []

    def test_parse_colors_non_list_json(self) -> None:
        """Test parsing non-list JSON."""
        recommender = CardRecommender()

        result = recommender._parse_colors('{"key": "value"}')

        # Should fall back to split behavior
        assert result is not None

    def test_build_document_includes_name(self) -> None:
        """Test document includes card name."""
        recommender = CardRecommender()

        card = {"name": "Lightning Bolt", "type": "", "text": ""}
        doc = recommender._build_document(card)

        assert "Lightning Bolt" in doc

    def test_build_document_repeats_name_for_weight(self) -> None:
        """Test document repeats name for TF-IDF weight."""
        recommender = CardRecommender()

        card = {"name": "Lightning Bolt"}
        doc = recommender._build_document(card)

        # Name should appear twice
        assert doc.count("Lightning Bolt") == 2

    def test_build_document_includes_type(self) -> None:
        """Test document includes type line."""
        recommender = CardRecommender()

        card = {"name": "Card", "type": "Instant"}
        doc = recommender._build_document(card)

        assert "Instant" in doc

    def test_build_document_includes_oracle_text(self) -> None:
        """Test document includes oracle text."""
        recommender = CardRecommender()

        card = {"name": "Card", "text": "Destroy target creature"}
        doc = recommender._build_document(card)

        assert "Destroy target creature" in doc

    def test_build_document_cleans_mana_symbols(self) -> None:
        """Test document converts mana symbols to words."""
        recommender = CardRecommender()

        card = {"name": "Card", "text": "Pay {W}{U}"}
        doc = recommender._build_document(card)

        assert "white mana" in doc
        assert "blue mana" in doc

    def test_build_document_includes_keywords_string(self) -> None:
        """Test document includes keywords from string."""
        recommender = CardRecommender()

        card = {"name": "Card", "keywords": "Flying,Haste"}
        doc = recommender._build_document(card)

        assert "Flying" in doc
        assert "Haste" in doc

    def test_build_document_includes_keywords_list(self) -> None:
        """Test document includes keywords from list."""
        recommender = CardRecommender()

        card = {"name": "Card", "keywords": ["Flying", "Vigilance"]}
        doc = recommender._build_document(card)

        assert "Flying" in doc
        assert "Vigilance" in doc

    def test_build_document_includes_colors_string(self) -> None:
        """Test document includes expanded color names from string."""
        recommender = CardRecommender()

        card = {"name": "Card", "colors": "WU"}
        doc = recommender._build_document(card)

        assert "white" in doc or "blue" in doc

    def test_build_document_includes_colors_list(self) -> None:
        """Test document includes expanded color names from list."""
        recommender = CardRecommender()

        card = {"name": "Card", "colors": ["R", "G"]}
        doc = recommender._build_document(card)

        # Should expand to color names
        assert "red" in doc or "green" in doc

    def test_build_document_handles_missing_fields(self) -> None:
        """Test document handles missing optional fields."""
        recommender = CardRecommender()

        card = {"name": "Card"}
        doc = recommender._build_document(card)

        assert "Card" in doc
        assert len(doc) > 0

    def test_build_document_subtypes_repeated(self) -> None:
        """Test document repeats subtypes for tribal weight."""
        recommender = CardRecommender()

        card = {"name": "Card", "subtypes": "Elf Warrior"}
        doc = recommender._build_document(card)

        # Subtypes should appear twice
        assert doc.count("Elf Warrior") == 2

    def test_build_document_subtypes_list(self) -> None:
        """Test document handles subtypes list."""
        recommender = CardRecommender()

        card = {"name": "Card", "subtypes": ["Elf", "Warrior"]}
        doc = recommender._build_document(card)

        assert "Elf" in doc
        assert "Warrior" in doc


class TestCardRecommenderState:
    """Tests for CardRecommender state management."""

    def test_is_initialized_false(self) -> None:
        """Test is_initialized property when not initialized."""
        recommender = CardRecommender()

        assert recommender.is_initialized is False

    def test_card_count_zero(self) -> None:
        """Test card_count property when not initialized."""
        recommender = CardRecommender()

        assert recommender.card_count == 0

    def test_find_similar_not_initialized(self) -> None:
        """Test find_similar raises error when not initialized."""
        recommender = CardRecommender()

        with pytest.raises(RuntimeError, match="not initialized"):
            recommender.find_similar("Lightning Bolt")

    def test_find_similar_to_text_not_initialized(self) -> None:
        """Test find_similar_to_text raises error when not initialized."""
        recommender = CardRecommender()

        with pytest.raises(RuntimeError, match="not initialized"):
            recommender.find_similar_to_text("some text")

    def test_find_similar_to_cards_not_initialized(self) -> None:
        """Test find_similar_to_cards raises error when not initialized."""
        recommender = CardRecommender()

        with pytest.raises(RuntimeError, match="not initialized"):
            recommender.find_similar_to_cards(["Lightning Bolt"])

    def test_find_similar_to_cards_empty_list(self) -> None:
        """Test find_similar_to_cards with empty list when not initialized."""
        recommender = CardRecommender()

        with pytest.raises(RuntimeError, match="not initialized"):
            recommender.find_similar_to_cards([])


class TestGlobalSingleton:
    """Tests for global singleton functions."""

    def test_get_recommender_creates_instance(self) -> None:
        """Test get_recommender creates instance."""
        recommender = get_recommender()

        assert isinstance(recommender, CardRecommender)

    def test_get_recommender_returns_same_instance(self) -> None:
        """Test get_recommender returns singleton."""
        rec1 = get_recommender()
        rec2 = get_recommender()

        assert rec1 is rec2
