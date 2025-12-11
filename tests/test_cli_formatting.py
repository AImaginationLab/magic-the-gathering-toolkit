"""Tests for CLI formatting utilities."""

from __future__ import annotations

from mtg_mcp.cli.formatting import (
    GENERIC_MANA,
    MANA_DISPLAY,
    MANA_SYMBOLS,
    prettify_mana,
    strip_quotes,
)


class TestManaSymbols:
    """Tests for mana symbol constants."""

    def test_mana_symbols_has_all_colors(self) -> None:
        """All five colors should be in MANA_SYMBOLS."""
        assert "W" in MANA_SYMBOLS
        assert "U" in MANA_SYMBOLS
        assert "B" in MANA_SYMBOLS
        assert "R" in MANA_SYMBOLS
        assert "G" in MANA_SYMBOLS

    def test_mana_display_has_basic_symbols(self) -> None:
        """MANA_DISPLAY should have all basic mana symbols."""
        assert "{W}" in MANA_DISPLAY
        assert "{U}" in MANA_DISPLAY
        assert "{B}" in MANA_DISPLAY
        assert "{R}" in MANA_DISPLAY
        assert "{G}" in MANA_DISPLAY
        assert "{C}" in MANA_DISPLAY

    def test_mana_display_has_special_symbols(self) -> None:
        """MANA_DISPLAY should have tap, untap, and special symbols."""
        assert "{T}" in MANA_DISPLAY  # Tap
        assert "{Q}" in MANA_DISPLAY  # Untap
        assert "{X}" in MANA_DISPLAY  # X mana
        assert "{S}" in MANA_DISPLAY  # Snow
        assert "{E}" in MANA_DISPLAY  # Energy

    def test_mana_display_uses_emojis(self) -> None:
        """MANA_DISPLAY should use emoji characters."""
        # White uses white circle
        assert "⚪" in MANA_DISPLAY["{W}"]
        # Blue uses water droplet
        assert "💧" in MANA_DISPLAY["{U}"]
        # Black uses skull
        assert "💀" in MANA_DISPLAY["{B}"]
        # Red uses fire
        assert "🔥" in MANA_DISPLAY["{R}"]
        # Green uses evergreen tree
        assert "🌲" in MANA_DISPLAY["{G}"]

    def test_generic_mana_has_numbers(self) -> None:
        """GENERIC_MANA should have 0-10."""
        for i in range(11):
            assert i in GENERIC_MANA


class TestPrettifyMana:
    """Tests for prettify_mana function."""

    def test_prettify_basic_mana(self) -> None:
        """Basic mana symbols should be converted."""
        result = prettify_mana("{W}")
        assert "⚪" in result

        result = prettify_mana("{U}{U}")
        assert result.count("💧") == 2

    def test_prettify_generic_mana(self) -> None:
        """Generic mana numbers should be converted to circled numbers."""
        result = prettify_mana("{1}")
        assert "①" in result

        result = prettify_mana("{3}")
        assert "③" in result

        result = prettify_mana("{10}")
        assert "⑩" in result

    def test_prettify_mixed_mana_cost(self) -> None:
        """Mixed mana costs should be converted properly."""
        # Lightning Bolt: {R}
        result = prettify_mana("{R}")
        assert "🔥" in result

        # Counterspell: {U}{U}
        result = prettify_mana("{U}{U}")
        assert result.count("💧") == 2

        # Wrath of God: {2}{W}{W}
        result = prettify_mana("{2}{W}{W}")
        assert "②" in result
        assert result.count("⚪") == 2

    def test_prettify_hybrid_mana(self) -> None:
        """Hybrid mana like {W/U} should show both symbols."""
        result = prettify_mana("{W/U}")
        assert "⚪" in result
        assert "💧" in result
        assert "/" in result

    def test_prettify_phyrexian_mana(self) -> None:
        """Phyrexian mana like {W/P} should show symbol with P marker."""
        result = prettify_mana("{W/P}")
        assert "⚪" in result
        assert "ᵖ" in result

    def test_prettify_tap_symbol(self) -> None:
        """Tap symbol should be converted."""
        result = prettify_mana("{T}")
        assert "🔄" in result

    def test_prettify_text_with_mana(self) -> None:
        """Rules text with mana symbols should be converted."""
        text = "{T}: Add {G}."
        result = prettify_mana(text)
        assert "🔄" in result
        assert "🌲" in result
        assert ": Add" in result

    def test_prettify_x_spell(self) -> None:
        """X mana should be converted."""
        result = prettify_mana("{X}{R}{R}")
        assert "Ⓧ" in result
        assert result.count("🔥") == 2

    def test_prettify_colorless(self) -> None:
        """Colorless mana should use diamond."""
        result = prettify_mana("{C}")
        assert "◇" in result

    def test_prettify_snow_mana(self) -> None:
        """Snow mana should use snowflake."""
        result = prettify_mana("{S}")
        assert "❄️" in result

    def test_prettify_large_generic_mana(self) -> None:
        """Large generic mana (11-20) should use circled numbers."""
        result = prettify_mana("{15}")
        # Should fall back to circled number (Unicode)
        assert "{15}" not in result

    def test_prettify_preserves_text(self) -> None:
        """Non-mana text should be preserved."""
        text = "Draw a card."
        result = prettify_mana(text)
        assert result == text

    def test_prettify_empty_string(self) -> None:
        """Empty string should return empty string."""
        assert prettify_mana("") == ""


class TestStripQuotes:
    """Tests for strip_quotes function."""

    def test_strip_double_quotes(self) -> None:
        """Double quotes should be stripped."""
        assert strip_quotes('"hello"') == "hello"
        assert strip_quotes('"Lightning Bolt"') == "Lightning Bolt"

    def test_strip_single_quotes(self) -> None:
        """Single quotes should be stripped."""
        assert strip_quotes("'hello'") == "hello"
        assert strip_quotes("'Sol Ring'") == "Sol Ring"

    def test_strip_whitespace(self) -> None:
        """Leading/trailing whitespace should be stripped."""
        assert strip_quotes("  hello  ") == "hello"
        assert strip_quotes('  "hello"  ') == "hello"

    def test_no_quotes(self) -> None:
        """Strings without quotes should be returned as-is (stripped)."""
        assert strip_quotes("hello") == "hello"
        assert strip_quotes("Lightning Bolt") == "Lightning Bolt"

    def test_mismatched_quotes(self) -> None:
        """Mismatched quotes should not be stripped."""
        assert strip_quotes("\"hello'") == "\"hello'"
        assert strip_quotes("'hello\"") == "'hello\""

    def test_empty_string(self) -> None:
        """Empty string should return empty string."""
        assert strip_quotes("") == ""

    def test_only_quotes(self) -> None:
        """String of just quotes should return empty."""
        assert strip_quotes('""') == ""
        assert strip_quotes("''") == ""

    def test_nested_quotes(self) -> None:
        """Nested quotes should only strip outer ones."""
        assert strip_quotes("\"'hello'\"") == "'hello'"
