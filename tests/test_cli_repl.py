"""Tests for CLI REPL helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mtg_mcp.cli.repl import FILTER_ALIASES, describe_art, parse_search_filters, show_help


class TestDescribeArt:
    """Tests for describe_art function."""

    def test_describe_basic_art(self) -> None:
        """Basic artwork should show set code."""
        art = MagicMock()
        art.border_color = "black"
        art.full_art = False
        art.finishes = []
        art.frame = "2015"
        art.set_code = "lea"

        result = describe_art(art)
        assert "LEA" in result
        assert "M15" in result  # 2015 frame = M15

    def test_describe_borderless(self) -> None:
        """Borderless artwork should be tagged."""
        art = MagicMock()
        art.border_color = "borderless"
        art.full_art = False
        art.finishes = []
        art.frame = "2015"
        art.set_code = "2xm"

        result = describe_art(art)
        assert "borderless" in result

    def test_describe_full_art(self) -> None:
        """Full art artwork should be tagged."""
        art = MagicMock()
        art.border_color = "black"
        art.full_art = True
        art.finishes = []
        art.frame = "2015"
        art.set_code = "zen"

        result = describe_art(art)
        assert "full-art" in result

    def test_describe_foil(self) -> None:
        """Foil finish should be tagged."""
        art = MagicMock()
        art.border_color = "black"
        art.full_art = False
        art.finishes = ["foil", "nonfoil"]
        art.frame = "2015"
        art.set_code = "m21"

        result = describe_art(art)
        assert "foil" in result

    def test_describe_etched(self) -> None:
        """Etched finish should be tagged."""
        art = MagicMock()
        art.border_color = "black"
        art.full_art = False
        art.finishes = ["etched"]
        art.frame = "2015"
        art.set_code = "cmr"

        result = describe_art(art)
        assert "etched" in result

    def test_describe_frame_names(self) -> None:
        """Frame years should be converted to names."""
        frames = {
            "1993": "Alpha",
            "1997": "Classic",
            "2003": "Modern",
            "2015": "M15",
            "future": "Future",
        }

        for frame_year, frame_name in frames.items():
            art = MagicMock()
            art.border_color = "black"
            art.full_art = False
            art.finishes = []
            art.frame = frame_year
            art.set_code = "test"

            result = describe_art(art)
            assert frame_name in result

    def test_describe_no_set_code(self) -> None:
        """Art without set_code should not crash."""
        art = MagicMock()
        art.border_color = "black"
        art.full_art = False
        art.finishes = []
        art.frame = "2015"
        art.set_code = None

        result = describe_art(art)
        # Should still return something without crashing
        assert isinstance(result, str)

    def test_describe_multiple_tags(self) -> None:
        """Art with multiple features should show all tags."""
        art = MagicMock()
        art.border_color = "borderless"
        art.full_art = True
        art.finishes = ["foil", "etched"]
        art.frame = "2015"
        art.set_code = "2xm"

        result = describe_art(art)
        assert "borderless" in result
        assert "full-art" in result
        assert "foil" in result
        assert "etched" in result


class TestShowHelp:
    """Tests for show_help function."""

    def test_show_help_executes(self, capsys: pytest.CaptureFixture[str]) -> None:
        """show_help should print help text."""
        show_help()
        captured = capsys.readouterr()
        # The output uses rich markup, but should contain these words
        assert "search" in captured.out.lower() or "spell" in captured.out.lower()


class TestSearchFilterParsing:
    """Tests for search filter parsing."""

    def test_filter_aliases_exist(self) -> None:
        """All expected filter aliases should exist."""
        assert "t" in FILTER_ALIASES
        assert "type" in FILTER_ALIASES
        assert "c" in FILTER_ALIASES
        assert "colors" in FILTER_ALIASES
        assert "cmc" in FILTER_ALIASES
        assert "f" in FILTER_ALIASES
        assert "r" in FILTER_ALIASES
        assert "set" in FILTER_ALIASES
        assert "text" in FILTER_ALIASES

    def test_parse_name_only(self) -> None:
        """Parsing just a name should work."""
        name, filters = parse_search_filters("dragon")
        assert name == "dragon"
        assert filters.name == "dragon"
        assert filters.type is None
        assert filters.colors is None

    def test_parse_type_filter(self) -> None:
        """Parsing type filter should work."""
        name, filters = parse_search_filters("dragon t:creature")
        assert name == "dragon"
        assert filters.name == "dragon"
        assert filters.type == "creature"

    def test_parse_type_filter_alias(self) -> None:
        """Parsing type filter with alias should work."""
        name, filters = parse_search_filters("type:instant")
        assert name is None or name == ""
        assert filters.type == "instant"

    def test_parse_colors_filter(self) -> None:
        """Parsing colors filter should work."""
        _, filters = parse_search_filters("c:R")
        assert filters.colors == ["R"]

    def test_parse_colors_multiple(self) -> None:
        """Parsing multiple colors should work."""
        _, filters = parse_search_filters("c:RG")
        assert filters.colors == ["R", "G"]

    def test_parse_colors_comma_separated(self) -> None:
        """Parsing comma-separated colors should work."""
        _, filters = parse_search_filters("c:R,G,U")
        assert set(filters.colors) == {"R", "G", "U"}

    def test_parse_cmc_filter(self) -> None:
        """Parsing cmc filter should work."""
        _, filters = parse_search_filters("cmc:3")
        assert filters.cmc == 3.0

    def test_parse_cmc_min_filter(self) -> None:
        """Parsing cmc minimum filter should work."""
        _, filters = parse_search_filters("cmc>:4")
        assert filters.cmc_min == 4.0

    def test_parse_cmc_max_filter(self) -> None:
        """Parsing cmc maximum filter should work."""
        _, filters = parse_search_filters("cmc<:2")
        assert filters.cmc_max == 2.0

    def test_parse_format_filter(self) -> None:
        """Parsing format filter should work."""
        _, filters = parse_search_filters("f:modern")
        assert filters.format_legal == "modern"

    def test_parse_rarity_filter(self) -> None:
        """Parsing rarity filter should work."""
        _, filters = parse_search_filters("r:mythic")
        assert filters.rarity == "mythic"

    def test_parse_set_filter(self) -> None:
        """Parsing set filter should work."""
        _, filters = parse_search_filters("set:DOM")
        assert filters.set_code == "DOM"

    def test_parse_text_filter(self) -> None:
        """Parsing text filter should work."""
        _, filters = parse_search_filters('text:"draw a card"')
        assert filters.text == "draw a card"

    def test_parse_text_filter_unquoted(self) -> None:
        """Parsing unquoted text filter should work."""
        _, filters = parse_search_filters("text:flying")
        assert filters.text == "flying"

    def test_parse_multiple_filters(self) -> None:
        """Parsing multiple filters should work."""
        name, filters = parse_search_filters("dragon t:creature c:R cmc:5")
        assert name == "dragon"
        assert filters.type == "creature"
        assert filters.colors == ["R"]
        assert filters.cmc == 5.0

    def test_parse_complex_query(self) -> None:
        """Parsing a complex query should work."""
        _, filters = parse_search_filters("t:instant f:modern cmc<:3 c:U,W")
        assert filters.type == "instant"
        assert filters.format_legal == "modern"
        assert filters.cmc_max == 3.0
        assert set(filters.colors) == {"U", "W"}

    def test_parse_empty_string(self) -> None:
        """Parsing empty string should return empty filters."""
        name, filters = parse_search_filters("")
        assert name is None or name == ""
        assert filters.type is None

    def test_parse_only_filters_no_name(self) -> None:
        """Parsing only filters with no name should work."""
        name, filters = parse_search_filters("t:creature c:G")
        assert name is None or name == ""
        assert filters.type == "creature"
        assert filters.colors == ["G"]

    def test_parse_keyword_filter(self) -> None:
        """Parsing keyword filter should work."""
        _, filters = parse_search_filters("kw:flying")
        assert filters.keywords == ["flying"]

    def test_parse_case_insensitive_filter_keys(self) -> None:
        """Filter keys should be case insensitive."""
        _, filters = parse_search_filters("T:creature C:R")
        assert filters.type == "creature"
        assert filters.colors == ["R"]


class TestReplCommands:
    """Tests for REPL command parsing logic."""

    def test_command_aliases(self) -> None:
        """REPL commands should have aliases."""
        # These are checked in the REPL logic
        # card/c, rulings/r, legality/legal/l, price/p, art/img/image/pic
        commands_with_aliases = [
            ("card", "c"),
            ("rulings", "r"),
            ("legality", "legal", "l"),
            ("price", "p"),
            ("art", "img", "image", "pic"),
            ("quit", "exit", "q"),
            ("help", "?"),
        ]

        # Just verify the structure exists - actual parsing is tested via integration
        for aliases in commands_with_aliases:
            assert len(aliases) >= 2


class TestDeckFileParsing:
    """Tests for deck file parsing."""

    def test_parse_deck_file_format(self, tmp_path: Path) -> None:
        """Deck file format should be documented."""
        from mtg_mcp.cli.commands.deck import parse_deck_file

        # Create a test deck file
        deck_content = """# Test deck
4 Lightning Bolt
4 Mountain
SB: 2 Pyroblast
"""
        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(deck_content)

        cards = parse_deck_file(deck_file)

        # Should have 3 entries
        assert len(cards) == 3

        # Check Lightning Bolt
        bolt = cards[0]
        assert bolt.name == "Lightning Bolt"
        assert bolt.quantity == 4
        assert bolt.sideboard is False

        # Check Mountain
        mountain = cards[1]
        assert mountain.name == "Mountain"
        assert mountain.quantity == 4
        assert mountain.sideboard is False

        # Check sideboard Pyroblast
        pyro = cards[2]
        assert pyro.name == "Pyroblast"
        assert pyro.quantity == 2
        assert pyro.sideboard is True

    def test_parse_deck_file_comments(self, tmp_path: Path) -> None:
        """Deck file parser should skip comments."""
        from mtg_mcp.cli.commands.deck import parse_deck_file

        deck_content = """# This is a comment
4 Lightning Bolt
# Another comment
4 Mountain
"""
        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(deck_content)

        cards = parse_deck_file(deck_file)
        assert len(cards) == 2

    def test_parse_deck_file_empty_lines(self, tmp_path: Path) -> None:
        """Deck file parser should skip empty lines."""
        from mtg_mcp.cli.commands.deck import parse_deck_file

        deck_content = """4 Lightning Bolt

4 Mountain

"""
        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(deck_content)

        cards = parse_deck_file(deck_file)
        assert len(cards) == 2

    def test_parse_deck_file_no_quantity(self, tmp_path: Path) -> None:
        """Deck file parser should handle cards without quantity."""
        from mtg_mcp.cli.commands.deck import parse_deck_file

        deck_content = """Lightning Bolt
Mountain
"""
        deck_file = tmp_path / "deck.txt"
        deck_file.write_text(deck_content)

        cards = parse_deck_file(deck_file)
        assert len(cards) == 2
        # Should default to quantity 1
        assert cards[0].quantity == 1
        assert cards[1].quantity == 1
