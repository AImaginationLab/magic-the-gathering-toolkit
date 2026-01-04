"""Tests for collection sorting functionality."""

import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from mtg_core.data.database.user import UserDatabase


@pytest.fixture
async def db() -> AsyncIterator[UserDatabase]:
    """Create a temporary test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_user.db"
        user_db = UserDatabase(db_path, max_connections=5)
        await user_db.connect()
        yield user_db
        await user_db.close()


class TestFastSortFields:
    """Test sorting by fast fields (collection table only)."""

    @pytest.mark.asyncio
    async def test_sort_by_name_asc(self, db: UserDatabase):
        """Sort by name ascending should be alphabetical A-Z."""
        await db.add_to_collection("Lightning Bolt", 4, 0, "M21", "199")
        await db.add_to_collection("Counterspell", 2, 1, "MH2", "267")
        await db.add_to_collection("Wrath of God", 1, 0, "2XM", "39")
        await db.add_to_collection("Birds of Paradise", 3, 2, "M12", "165")
        await db.add_to_collection("Dark Ritual", 4, 0, "A25", "82")

        cards = await db.get_collection_cards(limit=100, offset=0, sort_by="name", sort_order="asc")

        names = [c.card_name for c in cards]
        assert names == sorted(names), f"Expected alphabetical order, got: {names}"
        assert names[0] == "Birds of Paradise"
        assert names[-1] == "Wrath of God"

    @pytest.mark.asyncio
    async def test_sort_by_name_desc(self, db: UserDatabase):
        """Sort by name descending should be alphabetical Z-A."""
        await db.add_to_collection("Lightning Bolt", 4, 0, "M21", "199")
        await db.add_to_collection("Counterspell", 2, 1, "MH2", "267")
        await db.add_to_collection("Wrath of God", 1, 0, "2XM", "39")

        cards = await db.get_collection_cards(
            limit=100, offset=0, sort_by="name", sort_order="desc"
        )

        names = [c.card_name for c in cards]
        assert names == sorted(names, reverse=True), f"Expected reverse alphabetical, got: {names}"
        assert names[0] == "Wrath of God"
        assert names[-1] == "Counterspell"

    @pytest.mark.asyncio
    async def test_sort_by_quantity_desc(self, db: UserDatabase):
        """Sort by quantity descending should show highest quantities first."""
        await db.add_to_collection("Card A", 1, 0, "SET", "1")  # total: 1
        await db.add_to_collection("Card B", 4, 2, "SET", "2")  # total: 6
        await db.add_to_collection("Card C", 2, 1, "SET", "3")  # total: 3

        cards = await db.get_collection_cards(
            limit=100, offset=0, sort_by="quantity", sort_order="desc"
        )

        totals = [(c.card_name, c.quantity + c.foil_quantity) for c in cards]
        assert totals[0] == ("Card B", 6), f"Expected Card B (6) first, got: {totals}"
        assert totals[1] == ("Card C", 3), f"Expected Card C (3) second, got: {totals}"
        assert totals[2] == ("Card A", 1), f"Expected Card A (1) last, got: {totals}"

    @pytest.mark.asyncio
    async def test_sort_by_quantity_asc(self, db: UserDatabase):
        """Sort by quantity ascending should show lowest quantities first."""
        await db.add_to_collection("Card A", 1, 0, "SET", "1")  # total: 1
        await db.add_to_collection("Card B", 4, 2, "SET", "2")  # total: 6
        await db.add_to_collection("Card C", 2, 1, "SET", "3")  # total: 3

        cards = await db.get_collection_cards(
            limit=100, offset=0, sort_by="quantity", sort_order="asc"
        )

        totals = [(c.card_name, c.quantity + c.foil_quantity) for c in cards]
        assert totals[0] == ("Card A", 1), f"Expected Card A (1) first, got: {totals}"
        assert totals[-1] == ("Card B", 6), f"Expected Card B (6) last, got: {totals}"

    @pytest.mark.asyncio
    async def test_sort_by_date_added_desc(self, db: UserDatabase):
        """Sort by dateAdded descending should show newest first."""
        # Add cards with explicit timestamps to avoid same-second race condition
        # SQLite CURRENT_TIMESTAMP has second precision, so rapid inserts get same time
        await db.conn.execute(
            """
            INSERT INTO collection_cards (card_name, quantity, foil_quantity, set_code, collector_number, added_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("Old Card", 1, 0, "SET", "1", "2024-01-01 10:00:00"),
        )
        await db.conn.execute(
            """
            INSERT INTO collection_cards (card_name, quantity, foil_quantity, set_code, collector_number, added_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("Middle Card", 1, 0, "SET", "2", "2024-01-01 11:00:00"),
        )
        await db.conn.execute(
            """
            INSERT INTO collection_cards (card_name, quantity, foil_quantity, set_code, collector_number, added_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("New Card", 1, 0, "SET", "3", "2024-01-01 12:00:00"),
        )
        await db.conn.commit()

        cards = await db.get_collection_cards(
            limit=100, offset=0, sort_by="dateAdded", sort_order="desc"
        )

        names = [c.card_name for c in cards]
        # Newest should be first (added last)
        assert names[0] == "New Card", f"Expected 'New Card' first, got: {names}"
        assert names[-1] == "Old Card", f"Expected 'Old Card' last, got: {names}"

    @pytest.mark.asyncio
    async def test_sort_by_set_code_asc(self, db: UserDatabase):
        """Sort by setCode ascending should be alphabetical by set code."""
        await db.add_to_collection("Card 1", 1, 0, "ZNR", "1")
        await db.add_to_collection("Card 2", 1, 0, "AFR", "2")
        await db.add_to_collection("Card 3", 1, 0, "MH2", "3")

        cards = await db.get_collection_cards(
            limit=100, offset=0, sort_by="setCode", sort_order="asc"
        )

        set_codes = [c.set_code for c in cards]
        assert set_codes == ["AFR", "MH2", "ZNR"], (
            f"Expected alphabetical set codes, got: {set_codes}"
        )

    @pytest.mark.asyncio
    async def test_sort_by_set_code_desc(self, db: UserDatabase):
        """Sort by setCode descending should be reverse alphabetical by set code."""
        await db.add_to_collection("Card 1", 1, 0, "ZNR", "1")
        await db.add_to_collection("Card 2", 1, 0, "AFR", "2")
        await db.add_to_collection("Card 3", 1, 0, "MH2", "3")

        cards = await db.get_collection_cards(
            limit=100, offset=0, sort_by="setCode", sort_order="desc"
        )

        set_codes = [c.set_code for c in cards]
        assert set_codes == ["ZNR", "MH2", "AFR"], (
            f"Expected reverse alphabetical set codes, got: {set_codes}"
        )

    @pytest.mark.asyncio
    async def test_sort_by_date_added_asc(self, db: UserDatabase):
        """Sort by dateAdded ascending should show oldest first."""
        await db.conn.execute(
            """
            INSERT INTO collection_cards (card_name, quantity, foil_quantity, set_code, collector_number, added_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("Old Card", 1, 0, "SET", "1", "2024-01-01 10:00:00"),
        )
        await db.conn.execute(
            """
            INSERT INTO collection_cards (card_name, quantity, foil_quantity, set_code, collector_number, added_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("Middle Card", 1, 0, "SET", "2", "2024-01-01 11:00:00"),
        )
        await db.conn.execute(
            """
            INSERT INTO collection_cards (card_name, quantity, foil_quantity, set_code, collector_number, added_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("New Card", 1, 0, "SET", "3", "2024-01-01 12:00:00"),
        )
        await db.conn.commit()

        cards = await db.get_collection_cards(
            limit=100, offset=0, sort_by="dateAdded", sort_order="asc"
        )

        names = [c.card_name for c in cards]
        # Oldest should be first
        assert names[0] == "Old Card", f"Expected 'Old Card' first, got: {names}"
        assert names[-1] == "New Card", f"Expected 'New Card' last, got: {names}"


class TestMetadataSortFields:
    """Test sorting by metadata fields (require mtg.sqlite lookup)."""

    @pytest.fixture
    def mock_mtg_db(self, tmp_path):
        """Create a mock mtg.sqlite with card metadata."""
        import sqlite3

        db_path = tmp_path / "mtg.sqlite"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE cards (
                name TEXT,
                set_code TEXT,
                cmc REAL,
                rarity TEXT,
                type_line TEXT,
                colors TEXT,
                price_usd REAL
            )
        """)

        # Insert test card metadata
        cards_data = [
            ("Lightning Bolt", "M21", 1.0, "uncommon", "Instant", '["R"]', 2.50),
            ("Counterspell", "MH2", 2.0, "uncommon", "Instant", '["U"]', 1.00),
            ("Wrath of God", "2XM", 4.0, "rare", "Sorcery", '["W"]', 15.00),
            ("Birds of Paradise", "M12", 1.0, "rare", "Creature — Bird", '["G"]', 8.00),
            ("Dark Ritual", "A25", 1.0, "common", "Instant", '["B"]', 0.50),
            (
                "Emrakul, the Aeons Torn",
                "UMA",
                15.0,
                "mythic",
                "Legendary Creature — Eldrazi",
                "[]",
                45.00,
            ),
        ]

        conn.executemany("INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?, ?)", cards_data)
        conn.commit()
        conn.close()
        return db_path

    @pytest.mark.asyncio
    async def test_sort_by_cmc_asc(self, db: UserDatabase, mock_mtg_db):
        """Sort by cmc ascending should show lowest mana value first."""
        await db.add_to_collection("Wrath of God", 1, 0, "2XM", "39")  # CMC 4
        await db.add_to_collection("Lightning Bolt", 1, 0, "M21", "199")  # CMC 1
        await db.add_to_collection("Counterspell", 1, 0, "MH2", "267")  # CMC 2

        cards = await db.get_collection_cards(
            limit=100, offset=0, sort_by="cmc", sort_order="asc", mtg_db_path=mock_mtg_db
        )

        names = [c.card_name for c in cards]
        # CMC 1, 2, 4
        assert names[0] == "Lightning Bolt", f"Expected Lightning Bolt (CMC 1) first, got: {names}"
        assert names[-1] == "Wrath of God", f"Expected Wrath of God (CMC 4) last, got: {names}"

    @pytest.mark.asyncio
    async def test_sort_by_cmc_desc(self, db: UserDatabase, mock_mtg_db):
        """Sort by cmc descending should show highest mana value first."""
        await db.add_to_collection("Wrath of God", 1, 0, "2XM", "39")  # CMC 4
        await db.add_to_collection("Lightning Bolt", 1, 0, "M21", "199")  # CMC 1
        await db.add_to_collection("Emrakul, the Aeons Torn", 1, 0, "UMA", "4")  # CMC 15

        cards = await db.get_collection_cards(
            limit=100, offset=0, sort_by="cmc", sort_order="desc", mtg_db_path=mock_mtg_db
        )

        names = [c.card_name for c in cards]
        assert names[0] == "Emrakul, the Aeons Torn", (
            f"Expected Emrakul (CMC 15) first, got: {names}"
        )
        assert names[-1] == "Lightning Bolt", f"Expected Lightning Bolt (CMC 1) last, got: {names}"

    @pytest.mark.asyncio
    async def test_sort_by_price_desc(self, db: UserDatabase, mock_mtg_db):
        """Sort by price descending should show most expensive first."""
        await db.add_to_collection("Dark Ritual", 1, 0, "A25", "82")  # $0.50
        await db.add_to_collection("Wrath of God", 1, 0, "2XM", "39")  # $15.00
        await db.add_to_collection("Birds of Paradise", 1, 0, "M12", "165")  # $8.00

        cards = await db.get_collection_cards(
            limit=100, offset=0, sort_by="price", sort_order="desc", mtg_db_path=mock_mtg_db
        )

        names = [c.card_name for c in cards]
        assert names[0] == "Wrath of God", f"Expected Wrath ($15) first, got: {names}"
        assert names[-1] == "Dark Ritual", f"Expected Dark Ritual ($0.50) last, got: {names}"

    @pytest.mark.asyncio
    async def test_sort_by_price_asc(self, db: UserDatabase, mock_mtg_db):
        """Sort by price ascending should show cheapest first."""
        await db.add_to_collection("Dark Ritual", 1, 0, "A25", "82")  # $0.50
        await db.add_to_collection("Wrath of God", 1, 0, "2XM", "39")  # $15.00
        await db.add_to_collection("Birds of Paradise", 1, 0, "M12", "165")  # $8.00

        cards = await db.get_collection_cards(
            limit=100, offset=0, sort_by="price", sort_order="asc", mtg_db_path=mock_mtg_db
        )

        names = [c.card_name for c in cards]
        assert names[0] == "Dark Ritual", f"Expected Dark Ritual ($0.50) first, got: {names}"
        assert names[-1] == "Wrath of God", f"Expected Wrath ($15) last, got: {names}"

    @pytest.mark.asyncio
    async def test_sort_by_rarity_desc(self, db: UserDatabase, mock_mtg_db):
        """Sort by rarity descending should show mythic > rare > uncommon > common."""
        await db.add_to_collection("Dark Ritual", 1, 0, "A25", "82")  # common
        await db.add_to_collection("Lightning Bolt", 1, 0, "M21", "199")  # uncommon
        await db.add_to_collection("Wrath of God", 1, 0, "2XM", "39")  # rare
        await db.add_to_collection("Emrakul, the Aeons Torn", 1, 0, "UMA", "4")  # mythic

        cards = await db.get_collection_cards(
            limit=100, offset=0, sort_by="rarity", sort_order="desc", mtg_db_path=mock_mtg_db
        )

        names = [c.card_name for c in cards]
        assert names[0] == "Emrakul, the Aeons Torn", (
            f"Expected Emrakul (mythic) first, got: {names}"
        )
        assert names[-1] == "Dark Ritual", f"Expected Dark Ritual (common) last, got: {names}"

    @pytest.mark.asyncio
    async def test_sort_by_rarity_asc(self, db: UserDatabase, mock_mtg_db):
        """Sort by rarity ascending should show common > uncommon > rare > mythic."""
        await db.add_to_collection("Dark Ritual", 1, 0, "A25", "82")  # common
        await db.add_to_collection("Lightning Bolt", 1, 0, "M21", "199")  # uncommon
        await db.add_to_collection("Wrath of God", 1, 0, "2XM", "39")  # rare
        await db.add_to_collection("Emrakul, the Aeons Torn", 1, 0, "UMA", "4")  # mythic

        cards = await db.get_collection_cards(
            limit=100, offset=0, sort_by="rarity", sort_order="asc", mtg_db_path=mock_mtg_db
        )

        names = [c.card_name for c in cards]
        assert names[0] == "Dark Ritual", f"Expected Dark Ritual (common) first, got: {names}"
        assert names[-1] == "Emrakul, the Aeons Torn", (
            f"Expected Emrakul (mythic) last, got: {names}"
        )

    @pytest.mark.asyncio
    async def test_sort_by_color_asc(self, db: UserDatabase, mock_mtg_db):
        """Sort by color ascending should follow WUBRG order."""
        await db.add_to_collection("Birds of Paradise", 1, 0, "M12", "165")  # G
        await db.add_to_collection("Wrath of God", 1, 0, "2XM", "39")  # W
        await db.add_to_collection("Lightning Bolt", 1, 0, "M21", "199")  # R
        await db.add_to_collection("Counterspell", 1, 0, "MH2", "267")  # U
        await db.add_to_collection("Dark Ritual", 1, 0, "A25", "82")  # B

        cards = await db.get_collection_cards(
            limit=100, offset=0, sort_by="color", sort_order="asc", mtg_db_path=mock_mtg_db
        )

        names = [c.card_name for c in cards]
        # WUBRG order: W=Wrath, U=Counterspell, B=Dark Ritual, R=Lightning Bolt, G=Birds
        expected_order = [
            "Wrath of God",
            "Counterspell",
            "Dark Ritual",
            "Lightning Bolt",
            "Birds of Paradise",
        ]
        assert names == expected_order, f"Expected WUBRG order {expected_order}, got: {names}"

    @pytest.mark.asyncio
    async def test_sort_by_color_desc(self, db: UserDatabase, mock_mtg_db):
        """Sort by color descending should follow reverse WUBRG order (Green first)."""
        await db.add_to_collection("Birds of Paradise", 1, 0, "M12", "165")  # G
        await db.add_to_collection("Wrath of God", 1, 0, "2XM", "39")  # W
        await db.add_to_collection("Lightning Bolt", 1, 0, "M21", "199")  # R
        await db.add_to_collection("Counterspell", 1, 0, "MH2", "267")  # U
        await db.add_to_collection("Dark Ritual", 1, 0, "A25", "82")  # B

        cards = await db.get_collection_cards(
            limit=100, offset=0, sort_by="color", sort_order="desc", mtg_db_path=mock_mtg_db
        )

        names = [c.card_name for c in cards]
        # Reverse WUBRG order: G=Birds, R=Lightning Bolt, B=Dark Ritual, U=Counterspell, W=Wrath
        expected_order = [
            "Birds of Paradise",
            "Lightning Bolt",
            "Dark Ritual",
            "Counterspell",
            "Wrath of God",
        ]
        assert names == expected_order, (
            f"Expected reverse WUBRG order {expected_order}, got: {names}"
        )

    @pytest.mark.asyncio
    async def test_sort_by_type_asc(self, db: UserDatabase, mock_mtg_db):
        """Sort by type ascending should be alphabetical by type line."""
        await db.add_to_collection("Wrath of God", 1, 0, "2XM", "39")  # Sorcery
        await db.add_to_collection("Lightning Bolt", 1, 0, "M21", "199")  # Instant
        await db.add_to_collection("Birds of Paradise", 1, 0, "M12", "165")  # Creature

        cards = await db.get_collection_cards(
            limit=100, offset=0, sort_by="type", sort_order="asc", mtg_db_path=mock_mtg_db
        )

        names = [c.card_name for c in cards]
        # Alphabetical: Creature, Instant, Sorcery
        assert names[0] == "Birds of Paradise", f"Expected Creature first, got: {names}"
        assert names[-1] == "Wrath of God", f"Expected Sorcery last, got: {names}"

    @pytest.mark.asyncio
    async def test_sort_by_type_desc(self, db: UserDatabase, mock_mtg_db):
        """Sort by type descending should be reverse alphabetical by type line."""
        await db.add_to_collection("Wrath of God", 1, 0, "2XM", "39")  # Sorcery
        await db.add_to_collection("Lightning Bolt", 1, 0, "M21", "199")  # Instant
        await db.add_to_collection("Birds of Paradise", 1, 0, "M12", "165")  # Creature

        cards = await db.get_collection_cards(
            limit=100, offset=0, sort_by="type", sort_order="desc", mtg_db_path=mock_mtg_db
        )

        names = [c.card_name for c in cards]
        # Reverse alphabetical: Sorcery, Instant, Creature
        assert names[0] == "Wrath of God", f"Expected Sorcery first, got: {names}"
        assert names[-1] == "Birds of Paradise", f"Expected Creature last, got: {names}"


class TestGameplaySortFields:
    """Test sorting by gameplay fields (require gameplay.duckdb lookup)."""

    @pytest.fixture
    def mock_gameplay_db(self, tmp_path):
        """Create a mock gameplay.duckdb with stats."""
        try:
            import duckdb
        except ImportError:
            pytest.skip("duckdb not installed")

        db_path = tmp_path / "gameplay.duckdb"
        conn = duckdb.connect(str(db_path))
        conn.execute("""
            CREATE TABLE card_stats (
                card_name VARCHAR,
                set_code VARCHAR,
                gih_wr DOUBLE,
                tier VARCHAR
            )
        """)
        conn.execute("""
            CREATE TABLE draft_stats (
                card_name VARCHAR,
                set_code VARCHAR,
                ata DOUBLE
            )
        """)

        # Insert test gameplay stats (card_stats has win rate and tier)
        stats_data = [
            ("Lightning Bolt", "M21", 0.58, "A"),
            ("Counterspell", "MH2", 0.52, "B"),
            ("Wrath of God", "2XM", 0.61, "S"),
            ("Birds of Paradise", "M12", 0.48, "C"),
            ("Dark Ritual", "A25", 0.45, "D"),
        ]
        for card_name, set_code, wr, tier in stats_data:
            conn.execute(
                "INSERT INTO card_stats VALUES (?, ?, ?, ?)",
                [card_name, set_code, wr, tier],
            )

        # Insert draft stats (draft_stats has ATA)
        draft_data = [
            ("Lightning Bolt", "M21", 2.5),
            ("Counterspell", "MH2", 5.0),
            ("Wrath of God", "2XM", 1.2),
            ("Birds of Paradise", "M12", 8.0),
            ("Dark Ritual", "A25", 12.0),
        ]
        for card_name, set_code, ata in draft_data:
            conn.execute(
                "INSERT INTO draft_stats VALUES (?, ?, ?)",
                [card_name, set_code, ata],
            )

        conn.close()
        return db_path

    @pytest.mark.asyncio
    async def test_sort_by_win_rate_desc(self, db: UserDatabase, mock_gameplay_db):
        """Sort by winRate descending should show highest win rate first."""
        await db.add_to_collection("Dark Ritual", 1, 0, "A25", "82")  # 45%
        await db.add_to_collection("Wrath of God", 1, 0, "2XM", "39")  # 61%
        await db.add_to_collection("Lightning Bolt", 1, 0, "M21", "199")  # 58%

        cards = await db.get_collection_cards(
            limit=100,
            offset=0,
            sort_by="winRate",
            sort_order="desc",
            gameplay_db_path=mock_gameplay_db,
        )

        names = [c.card_name for c in cards]
        assert names[0] == "Wrath of God", f"Expected Wrath (61%) first, got: {names}"
        assert names[-1] == "Dark Ritual", f"Expected Dark Ritual (45%) last, got: {names}"

    @pytest.mark.asyncio
    async def test_sort_by_win_rate_asc(self, db: UserDatabase, mock_gameplay_db):
        """Sort by winRate ascending should show lowest win rate first."""
        await db.add_to_collection("Dark Ritual", 1, 0, "A25", "82")  # 45%
        await db.add_to_collection("Wrath of God", 1, 0, "2XM", "39")  # 61%
        await db.add_to_collection("Lightning Bolt", 1, 0, "M21", "199")  # 58%

        cards = await db.get_collection_cards(
            limit=100,
            offset=0,
            sort_by="winRate",
            sort_order="asc",
            gameplay_db_path=mock_gameplay_db,
        )

        names = [c.card_name for c in cards]
        assert names[0] == "Dark Ritual", f"Expected Dark Ritual (45%) first, got: {names}"
        assert names[-1] == "Wrath of God", f"Expected Wrath (61%) last, got: {names}"

    @pytest.mark.asyncio
    async def test_sort_by_tier_desc(self, db: UserDatabase, mock_gameplay_db):
        """Sort by tier descending should show S > A > B > C > D > F."""
        await db.add_to_collection("Dark Ritual", 1, 0, "A25", "82")  # D
        await db.add_to_collection("Wrath of God", 1, 0, "2XM", "39")  # S
        await db.add_to_collection("Lightning Bolt", 1, 0, "M21", "199")  # A
        await db.add_to_collection("Counterspell", 1, 0, "MH2", "267")  # B

        cards = await db.get_collection_cards(
            limit=100,
            offset=0,
            sort_by="tier",
            sort_order="desc",
            gameplay_db_path=mock_gameplay_db,
        )

        names = [c.card_name for c in cards]
        assert names[0] == "Wrath of God", f"Expected Wrath (S) first, got: {names}"
        assert names[1] == "Lightning Bolt", f"Expected Lightning Bolt (A) second, got: {names}"
        assert names[-1] == "Dark Ritual", f"Expected Dark Ritual (D) last, got: {names}"

    @pytest.mark.asyncio
    async def test_sort_by_draft_pick_asc(self, db: UserDatabase, mock_gameplay_db):
        """Sort by draftPick ascending should show lowest ATA first (picked earliest)."""
        await db.add_to_collection("Dark Ritual", 1, 0, "A25", "82")  # ATA 12.0
        await db.add_to_collection("Wrath of God", 1, 0, "2XM", "39")  # ATA 1.2
        await db.add_to_collection("Lightning Bolt", 1, 0, "M21", "199")  # ATA 2.5

        cards = await db.get_collection_cards(
            limit=100,
            offset=0,
            sort_by="draftPick",
            sort_order="asc",
            gameplay_db_path=mock_gameplay_db,
        )

        names = [c.card_name for c in cards]
        assert names[0] == "Wrath of God", f"Expected Wrath (ATA 1.2) first, got: {names}"
        assert names[-1] == "Dark Ritual", f"Expected Dark Ritual (ATA 12) last, got: {names}"

    @pytest.mark.asyncio
    async def test_sort_by_draft_pick_desc(self, db: UserDatabase, mock_gameplay_db):
        """Sort by draftPick descending should show highest ATA first (picked latest)."""
        await db.add_to_collection("Dark Ritual", 1, 0, "A25", "82")  # ATA 12.0
        await db.add_to_collection("Wrath of God", 1, 0, "2XM", "39")  # ATA 1.2
        await db.add_to_collection("Lightning Bolt", 1, 0, "M21", "199")  # ATA 2.5

        cards = await db.get_collection_cards(
            limit=100,
            offset=0,
            sort_by="draftPick",
            sort_order="desc",
            gameplay_db_path=mock_gameplay_db,
        )

        names = [c.card_name for c in cards]
        assert names[0] == "Dark Ritual", f"Expected Dark Ritual (ATA 12) first, got: {names}"
        assert names[-1] == "Wrath of God", f"Expected Wrath (ATA 1.2) last, got: {names}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ============================================================================
# Integration tests - verify sorting through the API endpoint
# ============================================================================


class TestAPICollectionSorting:
    """Test collection sorting via the FastAPI endpoint."""

    @pytest.fixture
    async def populated_db(self) -> AsyncIterator[tuple[UserDatabase, Path]]:
        """Create a populated test database with realistic cards."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_user.db"
            user_db = UserDatabase(db_path, max_connections=5)
            await user_db.connect()

            # Add cards with explicit timestamps for dateAdded testing
            # Using raw SQL to set specific added_at values
            await user_db.conn.execute(
                """
                INSERT INTO collection_cards (card_name, quantity, foil_quantity, set_code, collector_number, added_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("Lightning Bolt", 4, 0, "M21", "199", "2024-01-01 10:00:00"),
            )
            await user_db.conn.execute(
                """
                INSERT INTO collection_cards (card_name, quantity, foil_quantity, set_code, collector_number, added_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("Counterspell", 2, 1, "MH2", "267", "2024-01-02 11:00:00"),
            )
            await user_db.conn.execute(
                """
                INSERT INTO collection_cards (card_name, quantity, foil_quantity, set_code, collector_number, added_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("Birds of Paradise", 1, 0, "M12", "165", "2024-01-03 12:00:00"),
            )
            await user_db.conn.execute(
                """
                INSERT INTO collection_cards (card_name, quantity, foil_quantity, set_code, collector_number, added_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("Sol Ring", 5, 2, "C21", "263", "2024-01-04 13:00:00"),
            )
            await user_db.conn.commit()

            yield user_db, db_path
            await user_db.close()

    @pytest.mark.asyncio
    async def test_api_sort_by_name_asc(self, populated_db: tuple[UserDatabase, Path]):
        """API: Sort by name ascending."""
        db, _ = populated_db
        cards = await db.get_collection_cards(limit=100, sort_by="name", sort_order="asc")
        names = [c.card_name for c in cards]
        assert names == ["Birds of Paradise", "Counterspell", "Lightning Bolt", "Sol Ring"]

    @pytest.mark.asyncio
    async def test_api_sort_by_name_desc(self, populated_db: tuple[UserDatabase, Path]):
        """API: Sort by name descending."""
        db, _ = populated_db
        cards = await db.get_collection_cards(limit=100, sort_by="name", sort_order="desc")
        names = [c.card_name for c in cards]
        assert names == ["Sol Ring", "Lightning Bolt", "Counterspell", "Birds of Paradise"]

    @pytest.mark.asyncio
    async def test_api_sort_by_quantity_desc(self, populated_db: tuple[UserDatabase, Path]):
        """API: Sort by quantity descending (highest first)."""
        db, _ = populated_db
        cards = await db.get_collection_cards(limit=100, sort_by="quantity", sort_order="desc")
        # Sol Ring: 5+2=7, Lightning Bolt: 4, Counterspell: 2+1=3, Birds: 1
        quantities = [c.quantity + c.foil_quantity for c in cards]
        assert quantities == [7, 4, 3, 1]

    @pytest.mark.asyncio
    async def test_api_sort_by_date_added_desc(self, populated_db: tuple[UserDatabase, Path]):
        """API: Sort by dateAdded descending (newest first)."""
        db, _ = populated_db
        cards = await db.get_collection_cards(limit=100, sort_by="dateAdded", sort_order="desc")
        names = [c.card_name for c in cards]
        # Sol Ring (Jan 4), Birds (Jan 3), Counterspell (Jan 2), Lightning Bolt (Jan 1)
        assert names == ["Sol Ring", "Birds of Paradise", "Counterspell", "Lightning Bolt"]

    @pytest.mark.asyncio
    async def test_api_sort_by_set_code_asc(self, populated_db: tuple[UserDatabase, Path]):
        """API: Sort by set code ascending."""
        db, _ = populated_db
        cards = await db.get_collection_cards(limit=100, sort_by="setCode", sort_order="asc")
        set_codes = [c.set_code for c in cards]
        # C21, M12, M21, MH2 (alphabetical)
        assert set_codes == ["C21", "M12", "M21", "MH2"]

    @pytest.mark.asyncio
    async def test_api_pagination_with_sort(self, populated_db: tuple[UserDatabase, Path]):
        """API: Verify pagination works correctly with sorting."""
        db, _ = populated_db

        # Get first 2 cards sorted by name
        page1 = await db.get_collection_cards(limit=2, offset=0, sort_by="name", sort_order="asc")
        names1 = [c.card_name for c in page1]
        assert names1 == ["Birds of Paradise", "Counterspell"]

        # Get next 2 cards
        page2 = await db.get_collection_cards(limit=2, offset=2, sort_by="name", sort_order="asc")
        names2 = [c.card_name for c in page2]
        assert names2 == ["Lightning Bolt", "Sol Ring"]


# ============================================================================
# Tests for metadata sorts with real mtg.sqlite database
# These test the mana_value -> cmc column fix
# ============================================================================


class TestMetadataSortsWithRealDB:
    """Test metadata sorting with real mtg.sqlite database.

    These tests verify the mana_value -> cmc column fix works correctly.
    They require the real mtg.sqlite database to be present.
    """

    @pytest.fixture
    async def populated_db(self) -> AsyncIterator[UserDatabase]:
        """Create a test database with real card names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_user.db"
            user_db = UserDatabase(db_path, max_connections=5)
            await user_db.connect()

            # Add cards with known rarities and CMCs
            # These are real cards that exist in mtg.sqlite
            await user_db.add_to_collection(
                "Lightning Bolt", 4, 0, "M21", "199"
            )  # common/uncommon, cmc 1
            await user_db.add_to_collection("Counterspell", 2, 0, "MH2", "267")  # uncommon, cmc 2
            await user_db.add_to_collection("Wrath of God", 1, 0, "2XM", "39")  # rare, cmc 4
            await user_db.add_to_collection("Black Lotus", 1, 0, "VMA", "4")  # mythic/rare, cmc 0
            await user_db.add_to_collection("Sol Ring", 2, 0, "C21", "263")  # uncommon, cmc 1
            await user_db.add_to_collection("Force of Will", 1, 0, "ALL", "28")  # rare, cmc 5

            yield user_db
            await user_db.close()

    def _get_mtg_db_path(self) -> Path | None:
        """Get path to mtg.sqlite if it exists."""
        candidate = Path.home() / ".mtg-spellbook" / "mtg.sqlite"
        if candidate.exists():
            return candidate
        return None

    @pytest.mark.asyncio
    async def test_rarity_sort_uses_cmc_column_not_mana_value(self, populated_db: UserDatabase):
        """Verify rarity sort works (tests the mana_value -> cmc fix).

        This was broken because the code used 'mana_value' column which doesn't exist.
        The fix changed it to 'cmc' which is the actual column name.
        """
        mtg_db_path = self._get_mtg_db_path()
        if mtg_db_path is None:
            pytest.skip("mtg.sqlite not found")

        # This should NOT raise an exception or fall back to name sort
        cards = await populated_db.get_collection_cards(
            limit=100,
            offset=0,
            sort_by="rarity",
            sort_order="desc",
            mtg_db_path=mtg_db_path,
        )

        # Should have all 6 cards
        assert len(cards) == 6

        # The first cards should NOT be alphabetically sorted (which would mean fallback)
        # If sorted by rarity desc, mythics/rares should come before commons
        names = [c.card_name for c in cards]

        # Black Lotus and Force of Will are rare/mythic, should be near top
        # Lightning Bolt (common/uncommon) should be lower
        # The key test: cards are NOT in alphabetical order (which would indicate fallback)
        assert names != sorted(names), (
            "Cards appear alphabetically sorted - rarity sort may have failed"
        )

    @pytest.mark.asyncio
    async def test_cmc_sort_works(self, populated_db: UserDatabase):
        """Verify CMC sort works with the cmc column."""
        mtg_db_path = self._get_mtg_db_path()
        if mtg_db_path is None:
            pytest.skip("mtg.sqlite not found")

        cards = await populated_db.get_collection_cards(
            limit=100,
            offset=0,
            sort_by="cmc",
            sort_order="asc",
            mtg_db_path=mtg_db_path,
        )

        assert len(cards) == 6
        names = [c.card_name for c in cards]

        # Black Lotus (cmc 0) should be first when sorting asc
        assert names[0] == "Black Lotus", f"Expected Black Lotus first (cmc 0), got {names[0]}"

        # Force of Will (cmc 5) should be last when sorting asc
        assert names[-1] == "Force of Will", f"Expected Force of Will last (cmc 5), got {names[-1]}"

    @pytest.mark.asyncio
    async def test_cmc_sort_desc(self, populated_db: UserDatabase):
        """Verify CMC sort descending puts high CMC first."""
        mtg_db_path = self._get_mtg_db_path()
        if mtg_db_path is None:
            pytest.skip("mtg.sqlite not found")

        cards = await populated_db.get_collection_cards(
            limit=100,
            offset=0,
            sort_by="cmc",
            sort_order="desc",
            mtg_db_path=mtg_db_path,
        )

        names = [c.card_name for c in cards]

        # Force of Will (cmc 5) should be first when sorting desc
        assert names[0] == "Force of Will", f"Expected Force of Will first (cmc 5), got {names[0]}"

        # Black Lotus (cmc 0) should be last when sorting desc
        assert names[-1] == "Black Lotus", f"Expected Black Lotus last (cmc 0), got {names[-1]}"

    @pytest.mark.asyncio
    async def test_price_sort_works(self, populated_db: UserDatabase):
        """Verify price sort works (also uses the fixed query)."""
        mtg_db_path = self._get_mtg_db_path()
        if mtg_db_path is None:
            pytest.skip("mtg.sqlite not found")

        cards = await populated_db.get_collection_cards(
            limit=100,
            offset=0,
            sort_by="price",
            sort_order="desc",
            mtg_db_path=mtg_db_path,
        )

        # Should return cards without error
        assert len(cards) == 6

        # Cards should NOT be alphabetically sorted (which would indicate fallback)
        names = [c.card_name for c in cards]
        assert names != sorted(names), (
            "Cards appear alphabetically sorted - price sort may have failed"
        )

    @pytest.mark.asyncio
    async def test_color_sort_works(self, populated_db: UserDatabase):
        """Verify color sort works."""
        mtg_db_path = self._get_mtg_db_path()
        if mtg_db_path is None:
            pytest.skip("mtg.sqlite not found")

        cards = await populated_db.get_collection_cards(
            limit=100,
            offset=0,
            sort_by="color",
            sort_order="asc",
            mtg_db_path=mtg_db_path,
        )

        # Should return cards without error
        assert len(cards) == 6

    @pytest.mark.asyncio
    async def test_type_sort_works(self, populated_db: UserDatabase):
        """Verify type sort works."""
        mtg_db_path = self._get_mtg_db_path()
        if mtg_db_path is None:
            pytest.skip("mtg.sqlite not found")

        cards = await populated_db.get_collection_cards(
            limit=100,
            offset=0,
            sort_by="type",
            sort_order="asc",
            mtg_db_path=mtg_db_path,
        )

        # Should return cards without error
        assert len(cards) == 6


class TestAPIMetadataEnrichment:
    """Test that API response includes enriched metadata for client-side sorting."""

    def _get_mtg_db_path(self) -> Path | None:
        """Get path to mtg.sqlite if it exists."""
        candidate = Path.home() / ".mtg-spellbook" / "mtg.sqlite"
        if candidate.exists():
            return candidate
        return None

    @pytest.mark.asyncio
    async def test_api_response_includes_cmc(self):
        """Verify API response includes cmc field for client-side sorting.

        This tests the _fetch_card_metadata function uses 'cmc' column not 'mana_value'.
        """
        mtg_db_path = self._get_mtg_db_path()
        if mtg_db_path is None:
            pytest.skip("mtg.sqlite not found")

        from mtg_core.api.routes.collection import _fetch_card_metadata

        # Test with real card names
        card_names = ["Lightning Bolt", "Counterspell", "Wrath of God"]
        metadata = _fetch_card_metadata(card_names, mtg_db_path)

        # Should have metadata for all cards
        assert len(metadata) == 3, f"Expected metadata for 3 cards, got {len(metadata)}"

        # Each should have cmc field populated (not None)
        for name in card_names:
            key = name.lower()
            assert key in metadata, f"Missing metadata for {name}"
            assert "cmc" in metadata[key], f"Missing cmc field for {name}"
            assert metadata[key]["cmc"] is not None, f"cmc is None for {name}"

        # Verify specific CMC values
        assert metadata["lightning bolt"]["cmc"] == 1.0, "Lightning Bolt should be CMC 1"
        assert metadata["counterspell"]["cmc"] == 2.0, "Counterspell should be CMC 2"
        assert metadata["wrath of god"]["cmc"] == 4.0, "Wrath of God should be CMC 4"

    @pytest.mark.asyncio
    async def test_api_response_includes_rarity(self):
        """Verify API response includes rarity field."""
        mtg_db_path = self._get_mtg_db_path()
        if mtg_db_path is None:
            pytest.skip("mtg.sqlite not found")

        from mtg_core.api.routes.collection import _fetch_card_metadata

        card_names = ["Lightning Bolt", "Black Lotus"]
        metadata = _fetch_card_metadata(card_names, mtg_db_path)

        assert len(metadata) >= 1

        # Lightning Bolt should have rarity
        if "lightning bolt" in metadata:
            assert metadata["lightning bolt"]["rarity"] is not None

    @pytest.mark.asyncio
    async def test_api_response_includes_colors(self):
        """Verify API response includes colors field as list."""
        mtg_db_path = self._get_mtg_db_path()
        if mtg_db_path is None:
            pytest.skip("mtg.sqlite not found")

        from mtg_core.api.routes.collection import _fetch_card_metadata

        card_names = ["Lightning Bolt", "Counterspell"]
        metadata = _fetch_card_metadata(card_names, mtg_db_path)

        # Lightning Bolt is red
        assert metadata["lightning bolt"]["colors"] == ["R"], "Lightning Bolt should be red"

        # Counterspell is blue
        assert metadata["counterspell"]["colors"] == ["U"], "Counterspell should be blue"


class TestColorSortDisplayData:
    """Test color field data for UI mana icon display.

    The UI displays mana icons (ms ms-{color} ms-cost) for color sorting.
    These tests verify the API returns correct color data for the frontend.
    """

    def _get_mtg_db_path(self) -> Path | None:
        """Get path to mtg.sqlite if it exists."""
        candidate = Path.home() / ".mtg-spellbook" / "mtg.sqlite"
        if candidate.exists():
            return candidate
        return None

    @pytest.mark.asyncio
    async def test_mono_color_cards_return_single_color(self):
        """Mono-color cards should return single-element color array.

        UI renders: <i className="ms ms-r ms-cost" /> for red cards
        """
        mtg_db_path = self._get_mtg_db_path()
        if mtg_db_path is None:
            pytest.skip("mtg.sqlite not found")

        from mtg_core.api.routes.collection import _fetch_card_metadata

        # Test each color
        card_names = [
            "Lightning Bolt",  # Red
            "Counterspell",  # Blue
            "Dark Ritual",  # Black
            "Giant Growth",  # Green
            "Swords to Plowshares",  # White
        ]
        metadata = _fetch_card_metadata(card_names, mtg_db_path)

        # Each should have exactly one color
        assert metadata["lightning bolt"]["colors"] == ["R"], "Lightning Bolt should be mono-red"
        assert metadata["counterspell"]["colors"] == ["U"], "Counterspell should be mono-blue"
        assert metadata["dark ritual"]["colors"] == ["B"], "Dark Ritual should be mono-black"
        assert metadata["giant growth"]["colors"] == ["G"], "Giant Growth should be mono-green"
        assert metadata["swords to plowshares"]["colors"] == ["W"], "Swords should be mono-white"

    @pytest.mark.asyncio
    async def test_colorless_cards_return_empty_array(self):
        """Colorless cards should return empty color array.

        UI renders: <i className="ms ms-c ms-cost" /> for colorless cards
        """
        mtg_db_path = self._get_mtg_db_path()
        if mtg_db_path is None:
            pytest.skip("mtg.sqlite not found")

        from mtg_core.api.routes.collection import _fetch_card_metadata

        # Colorless artifacts and lands
        card_names = ["Sol Ring", "Mana Crypt", "Wastes"]
        metadata = _fetch_card_metadata(card_names, mtg_db_path)

        # Sol Ring is colorless
        assert metadata["sol ring"]["colors"] == [], "Sol Ring should be colorless (empty array)"

        # Mana Crypt is colorless
        assert metadata["mana crypt"]["colors"] == [], "Mana Crypt should be colorless"

    @pytest.mark.asyncio
    async def test_multicolor_cards_return_multiple_colors(self):
        """Multi-color cards should return array with all colors.

        UI renders multiple icons: <i className="ms ms-w ms-cost" /><i className="ms ms-u ms-cost" />
        """
        mtg_db_path = self._get_mtg_db_path()
        if mtg_db_path is None:
            pytest.skip("mtg.sqlite not found")

        from mtg_core.api.routes.collection import _fetch_card_metadata

        card_names = ["Teferi, Hero of Dominaria", "Nicol Bolas, Dragon-God"]
        metadata = _fetch_card_metadata(card_names, mtg_db_path)

        # Teferi is white-blue (WU)
        teferi_colors = metadata.get("teferi, hero of dominaria", {}).get("colors", [])
        assert "W" in teferi_colors, "Teferi should contain white"
        assert "U" in teferi_colors, "Teferi should contain blue"
        assert len(teferi_colors) == 2, f"Teferi should have 2 colors, got {teferi_colors}"

        # Nicol Bolas is blue-black-red (UBR)
        bolas_colors = metadata.get("nicol bolas, dragon-god", {}).get("colors", [])
        assert "U" in bolas_colors, "Bolas should contain blue"
        assert "B" in bolas_colors, "Bolas should contain black"
        assert "R" in bolas_colors, "Bolas should contain red"
        assert len(bolas_colors) == 3, f"Bolas should have 3 colors, got {bolas_colors}"

    @pytest.mark.asyncio
    async def test_colors_are_list_type_not_string(self):
        """Colors must be a list, not a JSON string.

        The UI iterates over colors array: cardColors.map((c, i) => ...)
        If colors were a string, this would iterate over characters.
        """
        mtg_db_path = self._get_mtg_db_path()
        if mtg_db_path is None:
            pytest.skip("mtg.sqlite not found")

        from mtg_core.api.routes.collection import _fetch_card_metadata

        card_names = ["Lightning Bolt"]
        metadata = _fetch_card_metadata(card_names, mtg_db_path)

        colors = metadata["lightning bolt"]["colors"]

        # Must be a list, not a string
        assert isinstance(colors, list), f"Colors should be list, got {type(colors)}"
        assert colors != '["R"]', "Colors should not be a JSON string"
        assert colors == ["R"], "Colors should be parsed as a Python list"

    @pytest.mark.asyncio
    async def test_color_sort_order_follows_wubrg(self):
        """Color sorting should follow WUBRG order (White, Blue, Black, Red, Green).

        This is the canonical MTG color order used throughout the game.
        """
        mtg_db_path = self._get_mtg_db_path()
        if mtg_db_path is None:
            pytest.skip("mtg.sqlite not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_user.db"
            user_db = UserDatabase(db_path, max_connections=5)
            await user_db.connect()

            # Add one card of each color
            await user_db.add_to_collection("Swords to Plowshares", 1, 0, "A25", "35")  # W
            await user_db.add_to_collection("Counterspell", 1, 0, "MH2", "267")  # U
            await user_db.add_to_collection("Dark Ritual", 1, 0, "A25", "82")  # B
            await user_db.add_to_collection("Lightning Bolt", 1, 0, "M21", "199")  # R
            await user_db.add_to_collection("Giant Growth", 1, 0, "M12", "176")  # G

            cards = await user_db.get_collection_cards(
                limit=100,
                offset=0,
                sort_by="color",
                sort_order="asc",
                mtg_db_path=mtg_db_path,
            )
            await user_db.close()

            names = [c.card_name for c in cards]

            # WUBRG order: White first, Green last
            expected_order = [
                "Swords to Plowshares",  # W
                "Counterspell",  # U
                "Dark Ritual",  # B
                "Lightning Bolt",  # R
                "Giant Growth",  # G
            ]
            assert names == expected_order, f"Expected WUBRG order {expected_order}, got {names}"

    @pytest.mark.asyncio
    async def test_colorless_sorted_after_colored_cards(self):
        """Colorless cards should sort after all colored cards in ascending order."""
        mtg_db_path = self._get_mtg_db_path()
        if mtg_db_path is None:
            pytest.skip("mtg.sqlite not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_user.db"
            user_db = UserDatabase(db_path, max_connections=5)
            await user_db.connect()

            # Add colored and colorless cards
            await user_db.add_to_collection("Lightning Bolt", 1, 0, "M21", "199")  # R
            await user_db.add_to_collection("Sol Ring", 1, 0, "C21", "263")  # Colorless
            await user_db.add_to_collection("Counterspell", 1, 0, "MH2", "267")  # U

            cards = await user_db.get_collection_cards(
                limit=100,
                offset=0,
                sort_by="color",
                sort_order="asc",
                mtg_db_path=mtg_db_path,
            )
            await user_db.close()

            names = [c.card_name for c in cards]

            # Colorless should be last in ascending order
            # Order should be: U (Counterspell), R (Lightning Bolt), Colorless (Sol Ring)
            assert names[-1] == "Sol Ring", (
                f"Sol Ring (colorless) should be last in asc order, got {names}"
            )


class TestGameplayNullsAlwaysLast:
    """Test that cards without gameplay data always appear last, regardless of sort order.

    This ensures that when sorting by winRate, tier, or draftPick, cards with actual
    values always appear before cards without data - whether sorting ASC or DESC.
    """

    @pytest.fixture
    def mock_gameplay_db(self, tmp_path):
        """Create a mock gameplay.duckdb with stats for some cards but not others."""
        try:
            import duckdb
        except ImportError:
            pytest.skip("duckdb not installed")

        db_path = tmp_path / "gameplay.duckdb"
        conn = duckdb.connect(str(db_path))
        conn.execute("""
            CREATE TABLE card_stats (
                card_name VARCHAR,
                set_code VARCHAR,
                gih_wr DOUBLE,
                tier VARCHAR
            )
        """)
        conn.execute("""
            CREATE TABLE draft_stats (
                card_name VARCHAR,
                set_code VARCHAR,
                ata DOUBLE
            )
        """)

        # Only add stats for some cards - others will have NULL values
        # card_stats has win rate and tier
        stats_data = [
            ("Card With High WR", "SET", 0.65, "S"),
            ("Card With Mid WR", "SET", 0.52, "B"),
            ("Card With Low WR", "SET", 0.42, "D"),
            # "Card Without Stats" intentionally not in database
        ]
        for card_name, set_code, wr, tier in stats_data:
            conn.execute(
                "INSERT INTO card_stats VALUES (?, ?, ?, ?)",
                [card_name, set_code, wr, tier],
            )

        # draft_stats has ATA
        draft_data = [
            ("Card With High WR", "SET", 1.5),
            ("Card With Mid WR", "SET", 5.0),
            ("Card With Low WR", "SET", 10.0),
        ]
        for card_name, set_code, ata in draft_data:
            conn.execute(
                "INSERT INTO draft_stats VALUES (?, ?, ?)",
                [card_name, set_code, ata],
            )

        conn.close()
        return db_path

    @pytest.fixture
    async def db_with_mixed_cards(self, tmp_path) -> AsyncIterator[UserDatabase]:
        """Create a database with cards that have stats and cards that don't."""
        db_path = tmp_path / "test_user.db"
        user_db = UserDatabase(db_path, max_connections=5)
        await user_db.connect()

        # Cards WITH gameplay stats
        await user_db.add_to_collection("Card With High WR", 1, 0, "SET", "1")
        await user_db.add_to_collection("Card With Mid WR", 1, 0, "SET", "2")
        await user_db.add_to_collection("Card With Low WR", 1, 0, "SET", "3")
        # Card WITHOUT gameplay stats
        await user_db.add_to_collection("Card Without Stats", 1, 0, "SET", "4")

        yield user_db
        await user_db.close()

    @pytest.mark.asyncio
    async def test_win_rate_desc_nulls_last(
        self, db_with_mixed_cards: UserDatabase, mock_gameplay_db
    ):
        """Win rate DESC: highest win rate first, cards without data last."""
        cards = await db_with_mixed_cards.get_collection_cards(
            limit=100,
            offset=0,
            sort_by="winRate",
            sort_order="desc",
            gameplay_db_path=mock_gameplay_db,
        )

        names = [c.card_name for c in cards]

        # Card without stats should be LAST even in DESC order
        assert names[-1] == "Card Without Stats", (
            f"Card without stats should be last in DESC order, got: {names}"
        )
        # Highest win rate should be first
        assert names[0] == "Card With High WR", (
            f"Highest WR card should be first in DESC order, got: {names}"
        )

    @pytest.mark.asyncio
    async def test_win_rate_asc_nulls_last(
        self, db_with_mixed_cards: UserDatabase, mock_gameplay_db
    ):
        """Win rate ASC: lowest win rate first, cards without data last."""
        cards = await db_with_mixed_cards.get_collection_cards(
            limit=100,
            offset=0,
            sort_by="winRate",
            sort_order="asc",
            gameplay_db_path=mock_gameplay_db,
        )

        names = [c.card_name for c in cards]

        # Card without stats should be LAST even in ASC order
        assert names[-1] == "Card Without Stats", (
            f"Card without stats should be last in ASC order, got: {names}"
        )
        # Lowest win rate should be first
        assert names[0] == "Card With Low WR", (
            f"Lowest WR card should be first in ASC order, got: {names}"
        )

    @pytest.mark.asyncio
    async def test_tier_desc_nulls_last(self, db_with_mixed_cards: UserDatabase, mock_gameplay_db):
        """Tier DESC: S tier first, cards without data last."""
        cards = await db_with_mixed_cards.get_collection_cards(
            limit=100,
            offset=0,
            sort_by="tier",
            sort_order="desc",
            gameplay_db_path=mock_gameplay_db,
        )

        names = [c.card_name for c in cards]

        # Card without stats should be LAST
        assert names[-1] == "Card Without Stats", (
            f"Card without stats should be last in tier DESC, got: {names}"
        )
        # S tier should be first
        assert names[0] == "Card With High WR", (
            f"S tier card should be first in DESC order, got: {names}"
        )

    @pytest.mark.asyncio
    async def test_tier_asc_nulls_last(self, db_with_mixed_cards: UserDatabase, mock_gameplay_db):
        """Tier ASC: D tier first, cards without data last."""
        cards = await db_with_mixed_cards.get_collection_cards(
            limit=100,
            offset=0,
            sort_by="tier",
            sort_order="asc",
            gameplay_db_path=mock_gameplay_db,
        )

        names = [c.card_name for c in cards]

        # Card without stats should be LAST even in ASC order
        assert names[-1] == "Card Without Stats", (
            f"Card without stats should be last in tier ASC, got: {names}"
        )
        # D tier should be first
        assert names[0] == "Card With Low WR", (
            f"D tier card should be first in ASC order, got: {names}"
        )

    @pytest.mark.asyncio
    async def test_draft_pick_desc_nulls_last(
        self, db_with_mixed_cards: UserDatabase, mock_gameplay_db
    ):
        """Draft pick DESC: highest ATA first, cards without data last."""
        cards = await db_with_mixed_cards.get_collection_cards(
            limit=100,
            offset=0,
            sort_by="draftPick",
            sort_order="desc",
            gameplay_db_path=mock_gameplay_db,
        )

        names = [c.card_name for c in cards]

        # Card without stats should be LAST
        assert names[-1] == "Card Without Stats", (
            f"Card without stats should be last in draftPick DESC, got: {names}"
        )
        # Highest ATA (10.0) should be first in DESC
        assert names[0] == "Card With Low WR", (
            f"Highest ATA card should be first in DESC order, got: {names}"
        )

    @pytest.mark.asyncio
    async def test_draft_pick_asc_nulls_last(
        self, db_with_mixed_cards: UserDatabase, mock_gameplay_db
    ):
        """Draft pick ASC: lowest ATA first, cards without data last."""
        cards = await db_with_mixed_cards.get_collection_cards(
            limit=100,
            offset=0,
            sort_by="draftPick",
            sort_order="asc",
            gameplay_db_path=mock_gameplay_db,
        )

        names = [c.card_name for c in cards]

        # Card without stats should be LAST even in ASC order
        assert names[-1] == "Card Without Stats", (
            f"Card without stats should be last in draftPick ASC, got: {names}"
        )
        # Lowest ATA (1.5) should be first in ASC
        assert names[0] == "Card With High WR", (
            f"Lowest ATA card should be first in ASC order, got: {names}"
        )
