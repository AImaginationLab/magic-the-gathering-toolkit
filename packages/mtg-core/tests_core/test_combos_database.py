"""Comprehensive tests for ComboDatabase class.

Tests cover:
- Database initialization and schema creation
- Adding and retrieving combos
- Searching combos by card name
- Finding combos in decks (complete and potential)
- Importing from JSON files
- Importing from legacy Python format
- Edge cases and error handling
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from mtg_core.data.database.combos import (
    COMBO_SCHEMA_VERSION,
    ComboDatabase,
)


@pytest.fixture
async def temp_db() -> AsyncIterator[ComboDatabase]:
    """Create a temporary combo database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = Path(f.name)

    db = ComboDatabase(db_path, max_connections=5)
    await db.connect()
    yield db
    await db.close()

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def sample_combo_data() -> dict[str, object]:
    """Sample combo data for testing."""
    return {
        "id": "thoracle-consult",
        "type": "win",
        "description": "Draw your library and win with Thassa's Oracle trigger",
        "cards": [
            ("Thassa's Oracle", "Win condition"),
            ("Demonic Consultation", "Enabler"),
        ],
        "colors": ["U", "B"],
    }


@pytest.fixture
def sample_json_combos() -> list[dict[str, object]]:
    """Sample JSON combo data for import testing."""
    return [
        {
            "id": "combo-1",
            "type": "value",
            "description": "Generate infinite mana",
            "cards": [
                {"name": "Devoted Druid", "role": "Mana source"},
                {"name": "Vizier of Remedies", "role": "Enabler"},
            ],
            "colors": ["G", "W"],
        },
        {
            "id": "combo-2",
            "type": "win",
            "description": "Infinite damage combo",
            "cards": [
                {"name": "Pestermite", "role": "Combo piece"},
                {"name": "Splinter Twin", "role": "Enabler"},
            ],
            "colors": ["U", "R"],
        },
    ]


class TestDatabaseInitialization:
    """Tests for database connection and schema creation."""

    async def test_connect_creates_schema(self, temp_db: ComboDatabase) -> None:
        """Database connection should create tables and schema version."""
        # Verify tables exist
        async with temp_db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cursor:
            tables = {row[0] for row in await cursor.fetchall()}

        assert "combos" in tables
        assert "combo_cards" in tables
        assert "combo_schema_version" in tables

    async def test_schema_version_is_set(self, temp_db: ComboDatabase) -> None:
        """Schema version should be set on initialization."""
        async with temp_db.conn.execute("SELECT version FROM combo_schema_version") as cursor:
            row = await cursor.fetchone()

        assert row is not None
        assert row[0] == COMBO_SCHEMA_VERSION

    async def test_foreign_keys_enabled(self, temp_db: ComboDatabase) -> None:
        """Foreign keys should be enabled."""
        async with temp_db.conn.execute("PRAGMA foreign_keys") as cursor:
            row = await cursor.fetchone()

        assert row[0] == 1

    async def test_conn_property_raises_when_not_connected(self) -> None:
        """Accessing conn before connect should raise RuntimeError."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = Path(f.name)

        db = ComboDatabase(db_path)

        with pytest.raises(RuntimeError, match="not connected"):
            _ = db.conn

        # Cleanup
        if db_path.exists():
            db_path.unlink()

    async def test_close_sets_conn_to_none(self, temp_db: ComboDatabase) -> None:
        """Closing database should set connection to None."""
        await temp_db.close()

        with pytest.raises(RuntimeError, match="not connected"):
            _ = temp_db.conn

    async def test_multiple_close_calls_safe(self, temp_db: ComboDatabase) -> None:
        """Calling close multiple times should be safe."""
        await temp_db.close()
        await temp_db.close()  # Should not raise


class TestAddAndRetrieveCombo:
    """Tests for adding and retrieving individual combos."""

    async def test_add_combo(
        self, temp_db: ComboDatabase, sample_combo_data: dict[str, object]
    ) -> None:
        """Should successfully add a combo to the database."""
        await temp_db.add_combo(
            combo_id=sample_combo_data["id"],
            combo_type=sample_combo_data["type"],
            description=sample_combo_data["description"],
            cards=sample_combo_data["cards"],
            colors=sample_combo_data["colors"],
        )

        count = await temp_db.get_combo_count()
        assert count == 1

    async def test_get_combo(
        self, temp_db: ComboDatabase, sample_combo_data: dict[str, object]
    ) -> None:
        """Should retrieve a combo by ID."""
        await temp_db.add_combo(
            combo_id=sample_combo_data["id"],
            combo_type=sample_combo_data["type"],
            description=sample_combo_data["description"],
            cards=sample_combo_data["cards"],
            colors=sample_combo_data["colors"],
        )

        result = await temp_db.get_combo(sample_combo_data["id"])
        assert result is not None

        combo, cards = result
        assert combo.id == sample_combo_data["id"]
        assert combo.combo_type == sample_combo_data["type"]
        assert combo.description == sample_combo_data["description"]
        assert combo.colors == sample_combo_data["colors"]

        assert len(cards) == 2
        assert cards[0].card_name == "Thassa's Oracle"
        assert cards[0].role == "Win condition"
        assert cards[1].card_name == "Demonic Consultation"
        assert cards[1].role == "Enabler"

    async def test_get_nonexistent_combo(self, temp_db: ComboDatabase) -> None:
        """Getting a non-existent combo should return None."""
        result = await temp_db.get_combo("nonexistent-id")
        assert result is None

    async def test_add_combo_with_replace(
        self, temp_db: ComboDatabase, sample_combo_data: dict[str, object]
    ) -> None:
        """Adding a combo with existing ID should replace it."""
        # Add original
        await temp_db.add_combo(
            combo_id=sample_combo_data["id"],
            combo_type=sample_combo_data["type"],
            description=sample_combo_data["description"],
            cards=sample_combo_data["cards"],
            colors=sample_combo_data["colors"],
        )

        # Replace with updated version
        updated_description = "Updated description"
        await temp_db.add_combo(
            combo_id=sample_combo_data["id"],
            combo_type="value",
            description=updated_description,
            cards=[("Card A", "Role A")],
            colors=["R"],
        )

        # Should only have one combo
        count = await temp_db.get_combo_count()
        assert count == 1

        # Should have updated data
        result = await temp_db.get_combo(sample_combo_data["id"])
        assert result is not None
        combo, cards = result
        assert combo.description == updated_description
        assert combo.combo_type == "value"
        assert len(cards) == 1

    async def test_add_combo_without_colors(self, temp_db: ComboDatabase) -> None:
        """Adding a combo without colors should use empty list."""
        await temp_db.add_combo(
            combo_id="test-combo",
            combo_type="value",
            description="Test",
            cards=[("Card A", "Role")],
        )

        result = await temp_db.get_combo("test-combo")
        assert result is not None
        combo, _ = result
        assert combo.colors == []

    async def test_card_position_ordering(self, temp_db: ComboDatabase) -> None:
        """Cards should be ordered by position."""
        cards = [
            ("First Card", "Role 1"),
            ("Second Card", "Role 2"),
            ("Third Card", "Role 3"),
        ]
        await temp_db.add_combo(
            combo_id="test",
            combo_type="value",
            description="Test ordering",
            cards=cards,
        )

        result = await temp_db.get_combo("test")
        assert result is not None
        _, retrieved_cards = result

        assert len(retrieved_cards) == 3
        assert retrieved_cards[0].card_name == "First Card"
        assert retrieved_cards[1].card_name == "Second Card"
        assert retrieved_cards[2].card_name == "Third Card"
        assert retrieved_cards[0].position == 0
        assert retrieved_cards[1].position == 1
        assert retrieved_cards[2].position == 2


class TestComboCount:
    """Tests for get_combo_count method."""

    async def test_empty_database_count(self, temp_db: ComboDatabase) -> None:
        """Empty database should have count of 0."""
        count = await temp_db.get_combo_count()
        assert count == 0

    async def test_combo_count_after_adding(self, temp_db: ComboDatabase) -> None:
        """Count should increase after adding combos."""
        await temp_db.add_combo("c1", "value", "Desc 1", [("Card", "Role")])
        assert await temp_db.get_combo_count() == 1

        await temp_db.add_combo("c2", "win", "Desc 2", [("Card", "Role")])
        assert await temp_db.get_combo_count() == 2

        await temp_db.add_combo("c3", "value", "Desc 3", [("Card", "Role")])
        assert await temp_db.get_combo_count() == 3


class TestFindCombosByCard:
    """Tests for finding combos by card name."""

    async def test_find_combos_by_card_name(self, temp_db: ComboDatabase) -> None:
        """Should find all combos containing a specific card."""
        await temp_db.add_combo(
            "combo-1",
            "win",
            "Combo with Lightning Bolt",
            [("Lightning Bolt", "Damage"), ("Guttersnipe", "Enabler")],
        )
        await temp_db.add_combo(
            "combo-2",
            "value",
            "Another Lightning Bolt combo",
            [("Lightning Bolt", "Removal"), ("Young Pyromancer", "Token maker")],
        )
        await temp_db.add_combo(
            "combo-3",
            "value",
            "Different combo",
            [("Birds of Paradise", "Ramp"), ("Llanowar Elves", "Ramp")],
        )

        results = await temp_db.find_combos_by_card("Lightning Bolt")
        assert len(results) == 2

        combo_ids = {combo.id for combo, _ in results}
        assert "combo-1" in combo_ids
        assert "combo-2" in combo_ids
        assert "combo-3" not in combo_ids

    async def test_find_combos_case_insensitive(self, temp_db: ComboDatabase) -> None:
        """Card name search should be case-insensitive."""
        await temp_db.add_combo(
            "test",
            "value",
            "Test",
            [("Lightning Bolt", "Damage")],
        )

        for query in ["Lightning Bolt", "LIGHTNING BOLT", "lightning bolt", "LiGhTnInG BoLt"]:
            results = await temp_db.find_combos_by_card(query)
            assert len(results) == 1
            assert results[0][0].id == "test"

    async def test_find_combos_no_matches(self, temp_db: ComboDatabase) -> None:
        """Should return empty list when no combos found."""
        await temp_db.add_combo(
            "test",
            "value",
            "Test",
            [("Card A", "Role")],
        )

        results = await temp_db.find_combos_by_card("Nonexistent Card")
        assert results == []

    async def test_find_combos_returns_all_cards(self, temp_db: ComboDatabase) -> None:
        """Should return all cards in found combos, not just the searched card."""
        await temp_db.add_combo(
            "test",
            "value",
            "Multi-card combo",
            [
                ("Card A", "Role A"),
                ("Card B", "Role B"),
                ("Card C", "Role C"),
            ],
        )

        results = await temp_db.find_combos_by_card("Card B")
        assert len(results) == 1

        _, cards = results[0]
        assert len(cards) == 3
        card_names = {c.card_name for c in cards}
        assert card_names == {"Card A", "Card B", "Card C"}


class TestFindCombosInDeck:
    """Tests for finding combos in a deck."""

    async def test_find_complete_combo(self, temp_db: ComboDatabase) -> None:
        """Should find complete combos when all pieces are in deck."""
        await temp_db.add_combo(
            "combo-1",
            "win",
            "Simple combo",
            [("Card A", "Piece 1"), ("Card B", "Piece 2")],
        )

        deck = ["Card A", "Card B", "Card C"]
        complete, potential = await temp_db.find_combos_in_deck(deck)

        assert len(complete) == 1
        assert len(potential) == 0
        assert complete[0][0].id == "combo-1"

    async def test_find_potential_combo_missing_one(self, temp_db: ComboDatabase) -> None:
        """Should find potential combos missing 1-2 pieces."""
        await temp_db.add_combo(
            "combo-1",
            "win",
            "Three-card combo",
            [("Card A", "P1"), ("Card B", "P2"), ("Card C", "P3")],
        )

        # Missing Card C
        deck = ["Card A", "Card B"]
        complete, potential = await temp_db.find_combos_in_deck(deck)

        assert len(complete) == 0
        assert len(potential) == 1

        combo, _, missing = potential[0]
        assert combo.id == "combo-1"
        assert "Card C" in missing
        assert len(missing) == 1

    async def test_find_potential_combo_missing_two(self, temp_db: ComboDatabase) -> None:
        """Should find potential combos missing exactly 2 pieces."""
        await temp_db.add_combo(
            "combo-1",
            "win",
            "Four-card combo",
            [("Card A", "P1"), ("Card B", "P2"), ("Card C", "P3"), ("Card D", "P4")],
        )

        # Missing Card C and Card D
        deck = ["Card A", "Card B"]
        complete, potential = await temp_db.find_combos_in_deck(deck)

        assert len(complete) == 0
        assert len(potential) == 1

        _, _, missing = potential[0]
        assert len(missing) == 2
        assert "Card C" in missing
        assert "Card D" in missing

    async def test_ignore_combo_missing_three_or_more(self, temp_db: ComboDatabase) -> None:
        """Should ignore combos missing 3+ pieces."""
        await temp_db.add_combo(
            "combo-1",
            "win",
            "Five-card combo",
            [("A", "P"), ("B", "P"), ("C", "P"), ("D", "P"), ("E", "P")],
        )

        # Only has 1 card, missing 4
        deck = ["A"]
        complete, potential = await temp_db.find_combos_in_deck(deck)

        assert len(complete) == 0
        assert len(potential) == 0  # Missing too many pieces

    async def test_empty_deck(self, temp_db: ComboDatabase) -> None:
        """Empty deck should return empty results."""
        await temp_db.add_combo("test", "value", "Test", [("Card A", "Role")])

        complete, potential = await temp_db.find_combos_in_deck([])
        assert complete == []
        assert potential == []

    async def test_deck_case_insensitive(self, temp_db: ComboDatabase) -> None:
        """Deck card matching should be case-insensitive."""
        await temp_db.add_combo(
            "test",
            "value",
            "Test",
            [("Lightning Bolt", "Damage"), ("Shock", "Burn")],
        )

        deck = ["lightning bolt", "SHOCK"]
        complete, potential = await temp_db.find_combos_in_deck(deck)

        assert len(complete) == 1
        assert len(potential) == 0

    async def test_multiple_combos_in_deck(self, temp_db: ComboDatabase) -> None:
        """Should find multiple combos in the same deck."""
        await temp_db.add_combo("combo-1", "win", "Combo 1", [("A", "P"), ("B", "P")])
        await temp_db.add_combo("combo-2", "value", "Combo 2", [("C", "P"), ("D", "P")])
        await temp_db.add_combo("combo-3", "win", "Combo 3", [("E", "P"), ("F", "P")])

        deck = ["A", "B", "C", "D"]  # Has combo-1 and combo-2, not combo-3
        complete, _ = await temp_db.find_combos_in_deck(deck)

        assert len(complete) == 2
        combo_ids = {c[0].id for c in complete}
        assert "combo-1" in combo_ids
        assert "combo-2" in combo_ids

    async def test_potential_combo_requires_at_least_one_card(self, temp_db: ComboDatabase) -> None:
        """Potential combos must have at least one card present."""
        await temp_db.add_combo(
            "combo-1",
            "win",
            "Two-card combo",
            [("Card A", "P1"), ("Card B", "P2")],
        )

        # Deck has neither card
        deck = ["Card C", "Card D"]
        complete, potential = await temp_db.find_combos_in_deck(deck)

        assert len(complete) == 0
        assert len(potential) == 0  # No cards present


class TestGetAllCombos:
    """Tests for retrieving all combos."""

    async def test_get_all_combos_empty(self, temp_db: ComboDatabase) -> None:
        """Empty database should return empty list."""
        combos = await temp_db.get_all_combos()
        assert combos == []

    async def test_get_all_combos(self, temp_db: ComboDatabase) -> None:
        """Should retrieve all combos with their cards."""
        await temp_db.add_combo("c1", "win", "Combo 1", [("A", "R1"), ("B", "R2")])
        await temp_db.add_combo("c2", "value", "Combo 2", [("C", "R3")])
        await temp_db.add_combo("c3", "win", "Combo 3", [("D", "R4"), ("E", "R5"), ("F", "R6")])

        combos = await temp_db.get_all_combos()
        assert len(combos) == 3

        combo_ids = {combo.id for combo, _ in combos}
        assert combo_ids == {"c1", "c2", "c3"}

        # Verify cards are included
        for combo, cards in combos:
            assert len(cards) > 0
            if combo.id == "c1":
                assert len(cards) == 2
            elif combo.id == "c2":
                assert len(cards) == 1
            elif combo.id == "c3":
                assert len(cards) == 3


class TestImportFromJSON:
    """Tests for importing combos from JSON files."""

    async def test_import_from_json(
        self, temp_db: ComboDatabase, sample_json_combos: list[dict[str, object]]
    ) -> None:
        """Should import combos from JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_json_combos, f)
            json_path = Path(f.name)

        try:
            count = await temp_db.import_from_json(json_path)
            assert count == 2

            db_count = await temp_db.get_combo_count()
            assert db_count == 2

            # Verify combos were imported correctly
            combo = await temp_db.get_combo("combo-1")
            assert combo is not None
            assert combo[0].description == "Generate infinite mana"
        finally:
            json_path.unlink()

    async def test_import_from_json_with_wrapper(self, temp_db: ComboDatabase) -> None:
        """Should handle JSON with 'combos' wrapper key."""
        data = {
            "version": 1,
            "combos": [
                {
                    "id": "test",
                    "type": "value",
                    "description": "Test combo",
                    "cards": [{"name": "Card A", "role": "Role"}],
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            json_path = Path(f.name)

        try:
            count = await temp_db.import_from_json(json_path)
            assert count == 1
        finally:
            json_path.unlink()

    async def test_import_tuple_format(self, temp_db: ComboDatabase) -> None:
        """Should handle cards in tuple/list format."""
        data = [
            {
                "id": "test",
                "type": "value",
                "description": "Test",
                "cards": [["Card A", "Role A"], ["Card B", "Role B"]],
            }
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            json_path = Path(f.name)

        try:
            count = await temp_db.import_from_json(json_path)
            assert count == 1

            result = await temp_db.get_combo("test")
            assert result is not None
            _, cards = result
            assert len(cards) == 2
        finally:
            json_path.unlink()

    async def test_import_string_card_format(self, temp_db: ComboDatabase) -> None:
        """Should handle cards as plain strings (default role)."""
        data = [
            {
                "id": "test",
                "type": "value",
                "description": "Test",
                "cards": ["Card A", "Card B"],
            }
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            json_path = Path(f.name)

        try:
            count = await temp_db.import_from_json(json_path)
            assert count == 1

            result = await temp_db.get_combo("test")
            assert result is not None
            _, cards = result
            assert all(c.role == "Combo piece" for c in cards)
        finally:
            json_path.unlink()

    async def test_import_missing_optional_fields(self, temp_db: ComboDatabase) -> None:
        """Should handle missing optional fields with defaults."""
        data = [
            {
                "id": "test",
                "cards": [{"name": "Card A"}],
            }
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            json_path = Path(f.name)

        try:
            count = await temp_db.import_from_json(json_path)
            assert count == 1

            result = await temp_db.get_combo("test")
            assert result is not None
            combo, _ = result
            assert combo.combo_type == "value"  # Default type
            assert combo.description == ""  # Default description
            assert combo.colors == []  # Default colors
        finally:
            json_path.unlink()


class TestImportFromLegacyFormat:
    """Tests for importing combos from legacy Python format."""

    async def test_import_from_legacy_format(self, temp_db: ComboDatabase) -> None:
        """Should import combos from legacy Python list format."""
        legacy_data = [
            {
                "id": "legacy-1",
                "type": "win",
                "desc": "Legacy combo description",
                "cards": [("Card A", "Role A"), ("Card B", "Role B")],
                "colors": ["R", "G"],
            },
            {
                "id": "legacy-2",
                "type": "value",
                "desc": "Another legacy combo",
                "cards": [("Card C", "Role C")],
                "colors": ["U"],
            },
        ]

        count = await temp_db.import_from_legacy_format(legacy_data)
        assert count == 2

        db_count = await temp_db.get_combo_count()
        assert db_count == 2

        # Verify import
        result = await temp_db.get_combo("legacy-1")
        assert result is not None
        combo, cards = result
        assert combo.description == "Legacy combo description"
        assert len(cards) == 2

    async def test_legacy_import_default_values(self, temp_db: ComboDatabase) -> None:
        """Should use defaults for missing fields in legacy format."""
        legacy_data = [
            {
                "id": "minimal",
                "cards": [("Card A", "Role")],
            }
        ]

        count = await temp_db.import_from_legacy_format(legacy_data)
        assert count == 1

        result = await temp_db.get_combo("minimal")
        assert result is not None
        combo, _ = result
        assert combo.combo_type == "value"
        assert combo.description == ""
        assert combo.colors == []

    async def test_legacy_import_string_cards(self, temp_db: ComboDatabase) -> None:
        """Should handle string-only cards in legacy format."""
        legacy_data = [
            {
                "id": "test",
                "desc": "Test",
                "cards": ["Card A", "Card B"],
            }
        ]

        count = await temp_db.import_from_legacy_format(legacy_data)
        assert count == 1

        result = await temp_db.get_combo("test")
        assert result is not None
        _, cards = result
        assert all(c.role == "Combo piece" for c in cards)


class TestClearAll:
    """Tests for clearing all combos."""

    async def test_clear_all(self, temp_db: ComboDatabase) -> None:
        """Should remove all combos and cards."""
        await temp_db.add_combo("c1", "win", "Combo 1", [("A", "R")])
        await temp_db.add_combo("c2", "value", "Combo 2", [("B", "R")])

        assert await temp_db.get_combo_count() == 2

        await temp_db.clear_all()

        assert await temp_db.get_combo_count() == 0
        combos = await temp_db.get_all_combos()
        assert combos == []

    async def test_clear_all_empty_database(self, temp_db: ComboDatabase) -> None:
        """Clearing empty database should not raise errors."""
        await temp_db.clear_all()
        assert await temp_db.get_combo_count() == 0


class TestConcurrency:
    """Tests for concurrent database operations."""

    async def test_semaphore_limits_connections(self, temp_db: ComboDatabase) -> None:
        """Semaphore should limit concurrent operations."""
        import asyncio

        # Add test data
        for i in range(10):
            await temp_db.add_combo(f"c{i}", "value", f"Combo {i}", [("Card", "Role")])

        # Run many concurrent queries
        tasks = [temp_db.get_combo(f"c{i}") for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r is not None for r in results)


# Integration test with real combo database (if available)
@pytest.fixture
def combo_json_path() -> Path | None:
    """Get path to real combos.json if it exists."""
    candidates = [
        Path("resources/combos.json"),
        Path("../../resources/combos.json"),
        Path(__file__).parent.parent.parent.parent / "resources" / "combos.json",
    ]

    for path in candidates:
        if path.exists():
            return path.resolve()

    return None


@pytest.mark.skipif(
    not Path(__file__).parent.parent.parent.parent.joinpath("resources/combos.json").exists(),
    reason="combos.json not found in resources",
)
class TestRealComboData:
    """Integration tests with real combo data."""

    async def test_import_real_combos(
        self, temp_db: ComboDatabase, combo_json_path: Path | None
    ) -> None:
        """Should successfully import real combo data from combos.json."""
        if combo_json_path is None:
            pytest.skip("combos.json not found")

        count = await temp_db.import_from_json(combo_json_path)
        assert count > 0

        db_count = await temp_db.get_combo_count()
        assert db_count == count

    async def test_search_real_combos(
        self, temp_db: ComboDatabase, combo_json_path: Path | None
    ) -> None:
        """Should be able to search imported combos."""
        if combo_json_path is None:
            pytest.skip("combos.json not found")

        await temp_db.import_from_json(combo_json_path)

        # Try to find combos with a common card (this will vary by dataset)
        all_combos = await temp_db.get_all_combos()
        if all_combos:
            # Get first card from first combo
            _, first_cards = all_combos[0]
            if first_cards:
                search_card = first_cards[0].card_name
                results = await temp_db.find_combos_by_card(search_card)
                assert len(results) > 0
