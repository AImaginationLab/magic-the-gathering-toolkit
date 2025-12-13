"""Tests for the combo database."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mtg_core.data.database.combos import ComboDatabase


@pytest.fixture
async def combo_db():
    """Create a temporary combo database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_combos.sqlite"
        db = ComboDatabase(db_path)
        await db.connect()
        yield db
        await db.close()


@pytest.mark.asyncio
async def test_add_and_get_combo(combo_db: ComboDatabase):
    """Test adding and retrieving a combo."""
    await combo_db.add_combo(
        combo_id="test-combo",
        combo_type="infinite",
        description="Test combo description",
        cards=[
            ("Card A", "Does thing A"),
            ("Card B", "Does thing B"),
        ],
        colors=["U", "R"],
    )

    result = await combo_db.get_combo("test-combo")
    assert result is not None

    combo, cards = result
    assert combo.id == "test-combo"
    assert combo.combo_type == "infinite"
    assert combo.description == "Test combo description"
    assert combo.colors == ["U", "R"]
    assert len(cards) == 2
    assert cards[0].card_name == "Card A"
    assert cards[0].role == "Does thing A"
    assert cards[1].card_name == "Card B"


@pytest.mark.asyncio
async def test_find_combos_by_card(combo_db: ComboDatabase):
    """Test finding combos containing a specific card."""
    await combo_db.add_combo(
        combo_id="combo-1",
        combo_type="infinite",
        description="Combo 1",
        cards=[
            ("Lightning Bolt", "Deals damage"),
            ("Snapcaster Mage", "Gives flashback"),
        ],
    )

    await combo_db.add_combo(
        combo_id="combo-2",
        combo_type="value",
        description="Combo 2",
        cards=[
            ("Counterspell", "Counters"),
            ("Snapcaster Mage", "Gives flashback"),
        ],
    )

    await combo_db.add_combo(
        combo_id="combo-3",
        combo_type="win",
        description="Combo 3",
        cards=[
            ("Sol Ring", "Makes mana"),
            ("Arcane Signet", "Makes mana"),
        ],
    )

    # Find combos with Snapcaster Mage
    results = await combo_db.find_combos_by_card("Snapcaster Mage")
    assert len(results) == 2

    combo_ids = {combo.id for combo, _ in results}
    assert combo_ids == {"combo-1", "combo-2"}


@pytest.mark.asyncio
async def test_find_combos_by_card_case_insensitive(combo_db: ComboDatabase):
    """Test that card name matching is case insensitive."""
    await combo_db.add_combo(
        combo_id="twin-combo",
        combo_type="infinite",
        description="Twin combo",
        cards=[
            ("Splinter Twin", "Enchant creature"),
            ("Deceiver Exarch", "Untaps enchanted"),
        ],
    )

    # Search with different case
    results = await combo_db.find_combos_by_card("splinter twin")
    assert len(results) == 1
    assert results[0][0].id == "twin-combo"

    results = await combo_db.find_combos_by_card("DECEIVER EXARCH")
    assert len(results) == 1


@pytest.mark.asyncio
async def test_find_combos_in_deck_complete(combo_db: ComboDatabase):
    """Test finding complete combos in a deck."""
    await combo_db.add_combo(
        combo_id="twin-combo",
        combo_type="infinite",
        description="Twin combo",
        cards=[
            ("Splinter Twin", "Enchant creature"),
            ("Deceiver Exarch", "Untaps enchanted"),
        ],
    )

    # Deck has both pieces
    deck = ["Splinter Twin", "Deceiver Exarch", "Island", "Mountain"]
    complete, potential = await combo_db.find_combos_in_deck(deck)

    assert len(complete) == 1
    assert complete[0][0].id == "twin-combo"
    assert len(potential) == 0


@pytest.mark.asyncio
async def test_find_combos_in_deck_partial(combo_db: ComboDatabase):
    """Test finding partial combos (missing 1-2 pieces)."""
    await combo_db.add_combo(
        combo_id="twin-combo",
        combo_type="infinite",
        description="Twin combo",
        cards=[
            ("Splinter Twin", "Enchant creature"),
            ("Deceiver Exarch", "Untaps enchanted"),
        ],
    )

    # Deck has only one piece
    deck = ["Splinter Twin", "Island", "Mountain"]
    complete, potential = await combo_db.find_combos_in_deck(deck)

    assert len(complete) == 0
    assert len(potential) == 1
    combo, cards, missing = potential[0]
    assert combo.id == "twin-combo"
    assert missing == ["Deceiver Exarch"]


@pytest.mark.asyncio
async def test_find_combos_in_deck_too_many_missing(combo_db: ComboDatabase):
    """Test that combos missing 3+ pieces aren't returned as potential."""
    await combo_db.add_combo(
        combo_id="four-card-combo",
        combo_type="win",
        description="Four card combo",
        cards=[
            ("Card A", "Role A"),
            ("Card B", "Role B"),
            ("Card C", "Role C"),
            ("Card D", "Role D"),
        ],
    )

    # Deck has only one piece (missing 3)
    deck = ["Card A", "Other Card"]
    complete, potential = await combo_db.find_combos_in_deck(deck)

    assert len(complete) == 0
    assert len(potential) == 0


@pytest.mark.asyncio
async def test_import_from_legacy_format(combo_db: ComboDatabase):
    """Test importing from legacy KNOWN_COMBOS format."""
    legacy_combos = [
        {
            "id": "twin",
            "cards": [
                ("Splinter Twin", "Enchant creature, tap to copy"),
                ("Deceiver Exarch", "Untap enchanted creature"),
            ],
            "type": "infinite",
            "desc": "Infinite hasty token copies",
            "colors": ["U", "R"],
        },
        {
            "id": "sanguine-exquisite",
            "cards": [
                ("Sanguine Bond", "Life gain causes life loss"),
                ("Exquisite Blood", "Life loss causes life gain"),
            ],
            "type": "infinite",
            "desc": "Infinite life drain loop",
            "colors": ["B"],
        },
    ]

    count = await combo_db.import_from_legacy_format(legacy_combos)
    assert count == 2

    total = await combo_db.get_combo_count()
    assert total == 2

    result = await combo_db.get_combo("twin")
    assert result is not None
    combo, cards = result
    assert combo.colors == ["U", "R"]
    assert len(cards) == 2


@pytest.mark.asyncio
async def test_import_from_json(combo_db: ComboDatabase, tmp_path: Path):
    """Test importing from JSON file."""
    import json

    combos_json = {
        "combos": [
            {
                "id": "test-json-combo",
                "cards": [
                    {"name": "Test Card A", "role": "Does A"},
                    {"name": "Test Card B", "role": "Does B"},
                ],
                "type": "value",
                "description": "Test combo from JSON",
                "colors": ["G"],
            }
        ]
    }

    json_path = tmp_path / "test_combos.json"
    with open(json_path, "w") as f:
        json.dump(combos_json, f)

    count = await combo_db.import_from_json(json_path)
    assert count == 1

    result = await combo_db.get_combo("test-json-combo")
    assert result is not None
    combo, cards = result
    assert combo.description == "Test combo from JSON"
    assert combo.colors == ["G"]


@pytest.mark.asyncio
async def test_get_all_combos(combo_db: ComboDatabase):
    """Test getting all combos."""
    await combo_db.add_combo("combo-1", "infinite", "Combo 1", [("A", "a")])
    await combo_db.add_combo("combo-2", "value", "Combo 2", [("B", "b")])
    await combo_db.add_combo("combo-3", "win", "Combo 3", [("C", "c")])

    all_combos = await combo_db.get_all_combos()
    assert len(all_combos) == 3

    ids = {combo.id for combo, _ in all_combos}
    assert ids == {"combo-1", "combo-2", "combo-3"}


@pytest.mark.asyncio
async def test_clear_all(combo_db: ComboDatabase):
    """Test clearing all combos."""
    await combo_db.add_combo("combo-1", "infinite", "Combo 1", [("A", "a")])
    await combo_db.add_combo("combo-2", "value", "Combo 2", [("B", "b")])

    count = await combo_db.get_combo_count()
    assert count == 2

    await combo_db.clear_all()

    count = await combo_db.get_combo_count()
    assert count == 0
