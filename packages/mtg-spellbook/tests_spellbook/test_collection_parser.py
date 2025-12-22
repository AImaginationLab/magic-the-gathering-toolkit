"""Tests for collection card input parser."""

from mtg_spellbook.collection.parser import parse_card_input


class TestParseCardInput:
    """Tests for parse_card_input function."""

    def test_simple_card_name(self) -> None:
        """Test parsing a simple card name."""
        result = parse_card_input("Lightning Bolt")
        assert result.card_name == "Lightning Bolt"
        assert result.quantity == 1
        assert result.foil is False
        assert result.set_code is None
        assert result.collector_number is None

    def test_card_name_with_quantity(self) -> None:
        """Test parsing card name with quantity prefix."""
        result = parse_card_input("4 Lightning Bolt")
        assert result.card_name == "Lightning Bolt"
        assert result.quantity == 4
        assert result.foil is False

    def test_card_name_with_quantity_x_suffix(self) -> None:
        """Test parsing card name with 4x style quantity."""
        result = parse_card_input("4x Lightning Bolt")
        assert result.card_name == "Lightning Bolt"
        assert result.quantity == 4

    def test_set_number_format_no_quantity(self) -> None:
        """Test parsing SET NUMBER format without quantity (defaults to 1)."""
        result = parse_card_input("fca 27")
        assert result.card_name is None
        assert result.set_code == "fca"
        assert result.collector_number == "27"
        assert result.quantity == 1
        assert result.foil is False

    def test_set_number_format_with_quantity(self) -> None:
        """Test parsing SET NUMBER format with quantity."""
        result = parse_card_input("2 fca 27")
        assert result.card_name is None
        assert result.set_code == "fca"
        assert result.collector_number == "27"
        assert result.quantity == 2

    def test_set_number_format_with_quantity_x(self) -> None:
        """Test parsing SET NUMBER format with 4x style quantity."""
        result = parse_card_input("4x fca 27")
        assert result.card_name is None
        assert result.set_code == "fca"
        assert result.collector_number == "27"
        assert result.quantity == 4

    def test_set_number_format_uppercase(self) -> None:
        """Test SET NUMBER format with uppercase set code."""
        result = parse_card_input("FCA 27")
        assert result.set_code == "fca"  # Should be lowercased
        assert result.collector_number == "27"

    def test_set_number_with_hash(self) -> None:
        """Test SET NUMBER format with # prefix on number."""
        result = parse_card_input("fca #27")
        assert result.set_code == "fca"
        assert result.collector_number == "27"

    def test_set_number_with_leading_zeros(self) -> None:
        """Test SET NUMBER format with leading zeros in collector number."""
        result = parse_card_input("fca 0027")
        assert result.set_code == "fca"
        assert result.collector_number == "0027"

    def test_set_number_with_letter_suffix(self) -> None:
        """Test SET NUMBER format with letter suffix (e.g., 123a)."""
        result = parse_card_input("m21 123a")
        assert result.set_code == "m21"
        assert result.collector_number == "123a"

    def test_bracket_set_code(self) -> None:
        """Test card name with bracket set code."""
        result = parse_card_input("Lightning Bolt [M21]")
        assert result.card_name == "Lightning Bolt"
        assert result.set_code == "m21"
        assert result.collector_number is None

    def test_bracket_set_and_number(self) -> None:
        """Test card name with bracket set code and collector number."""
        result = parse_card_input("Lightning Bolt [M21 #123]")
        assert result.card_name == "Lightning Bolt"
        assert result.set_code == "m21"
        assert result.collector_number == "123"

    def test_paren_set_code(self) -> None:
        """Test card name with parenthesis set code."""
        result = parse_card_input("Lightning Bolt (M21)")
        assert result.card_name == "Lightning Bolt"
        assert result.set_code == "m21"

    def test_paren_set_and_number(self) -> None:
        """Test card name with parenthesis set code and collector number."""
        result = parse_card_input("Lightning Bolt (M21 123)")
        assert result.card_name == "Lightning Bolt"
        assert result.set_code == "m21"
        assert result.collector_number == "123"

    def test_foil_marker_asterisk(self) -> None:
        """Test foil marker with *F*."""
        result = parse_card_input("Lightning Bolt *F*")
        assert result.card_name == "Lightning Bolt"
        assert result.foil is True

    def test_foil_marker_word(self) -> None:
        """Test foil marker with 'foil' word."""
        result = parse_card_input("Lightning Bolt foil")
        assert result.card_name == "Lightning Bolt"
        assert result.foil is True

    def test_foil_marker_paren(self) -> None:
        """Test foil marker with (foil)."""
        result = parse_card_input("Lightning Bolt (foil)")
        assert result.card_name == "Lightning Bolt"
        assert result.foil is True

    def test_foil_marker_trailing_asterisk(self) -> None:
        """Test foil marker with trailing asterisk."""
        result = parse_card_input("Lightning Bolt *")
        assert result.card_name == "Lightning Bolt"
        assert result.foil is True

    def test_foil_marker_short_f(self) -> None:
        """Test foil marker with short 'f' suffix."""
        result = parse_card_input("fca 27 f")
        assert result.set_code == "fca"
        assert result.collector_number == "27"
        assert result.foil is True

    def test_set_number_foil_combined(self) -> None:
        """Test SET NUMBER format with foil marker."""
        result = parse_card_input("2 fca 27 *F*")
        assert result.set_code == "fca"
        assert result.collector_number == "27"
        assert result.quantity == 2
        assert result.foil is True

    def test_full_format_quantity_name_set_foil(self) -> None:
        """Test full format with all components."""
        result = parse_card_input("4 Lightning Bolt [M21 #123] *F*")
        assert result.card_name == "Lightning Bolt"
        assert result.quantity == 4
        assert result.set_code == "m21"
        assert result.collector_number == "123"
        assert result.foil is True

    def test_default_quantity_override(self) -> None:
        """Test that default_quantity is used when no quantity in input."""
        result = parse_card_input("Lightning Bolt", default_quantity=3)
        assert result.quantity == 3

    def test_input_quantity_overrides_default(self) -> None:
        """Test that input quantity overrides default."""
        result = parse_card_input("4 Lightning Bolt", default_quantity=1)
        assert result.quantity == 4

    def test_numeric_set_codes(self) -> None:
        """Test set codes with numbers (e.g., 2xm, j21)."""
        result = parse_card_input("2xm 123")
        assert result.set_code == "2xm"
        assert result.collector_number == "123"

        result = parse_card_input("j21 62")
        assert result.set_code == "j21"
        assert result.collector_number == "62"

    def test_case_insensitive_foil_markers(self) -> None:
        """Test that foil markers are case insensitive."""
        result = parse_card_input("Lightning Bolt FOIL")
        assert result.foil is True

        result = parse_card_input("Lightning Bolt *FOIL*")
        assert result.foil is True

    def test_whitespace_handling(self) -> None:
        """Test that extra whitespace is handled."""
        result = parse_card_input("  Lightning Bolt  ")
        assert result.card_name == "Lightning Bolt"

    def test_empty_input(self) -> None:
        """Test empty input."""
        result = parse_card_input("")
        assert result.card_name is None  # Empty string results in None
        assert result.quantity == 1

    def test_card_name_not_confused_with_set_number(self) -> None:
        """Test that card names aren't confused with SET NUMBER format."""
        # "Sol Ring" should NOT be parsed as set=Sol, number=Ring
        result = parse_card_input("Sol Ring")
        assert result.card_name == "Sol Ring"
        assert result.set_code is None

    def test_real_world_examples(self) -> None:
        """Test real-world import examples."""
        # Standard deck list format
        result = parse_card_input("4 Counterspell")
        assert result.card_name == "Counterspell"
        assert result.quantity == 4

        # MTGO format
        result = parse_card_input("4x Path to Exile")
        assert result.card_name == "Path to Exile"
        assert result.quantity == 4

        # With set info
        result = parse_card_input("4 Fatal Push [KLR]")
        assert result.card_name == "Fatal Push"
        assert result.set_code == "klr"
        assert result.quantity == 4

        # Collector format
        result = parse_card_input("fca 27")
        assert result.set_code == "fca"
        assert result.collector_number == "27"
        assert result.quantity == 1
