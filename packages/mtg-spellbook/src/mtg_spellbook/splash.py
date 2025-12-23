"""Splash screen with database setup for first-time users."""

from __future__ import annotations

import asyncio
import json
import random
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Center, Vertical
from textual.timer import Timer
from textual.widgets import Label, ProgressBar, Static

# Cheeky loading messages (gamers will appreciate these)
LOADING_MESSAGES = [
    "Reticulating splines...",
    "Summoning mana from the Blind Eternities...",
    "Consulting the Thran archives...",
    "Shuffling the multiverse...",
    "Tapping lands for setup mana...",
    "Tutoring for database cards...",
    "Resolving the stack...",
    "Exiling temporary files to the shadow realm...",
    "Casting Brainstorm on your storage...",
    "Activating Necropotence... paying life for data...",
    "Untapping, upkeeping, drawing...",
    "Rolling for initiative...",
    "Waiting for priority to pass...",
    "Countering entropy with Blue mana...",
    "Flashbacking Snapcaster optimizations...",
    "Proliferating index counters...",
    "Fateseal-ing your cache...",
    "Scrying the top cards of your database...",
    "Transmuting data into searchable form...",
    "Dredging through the graveyard of old formats...",
    "Cascade... cascade... cascade...",
    "Storm count: increasing...",
    "Forcing of Will through network congestion...",
    "Thoughtseizing redundant packets...",
    "Dark Ritual: adding BBB to the mana pool...",
    "Channeling fireball at technical debt...",
    "Sol Ring goes brrr...",
    "Phyrexian mana: paying 2 life for speed...",
    "Mutating database schema...",
    "Convoke: tapping all available threads...",
    "Calculating optimal mana curves...",
    "Searching for the One Ring...",
    "Sacrificing goats to RNGesus...",
    "Preparing the battlefield...",
    "Assembling Tron pieces...",
    "Checking if Colossal Dreadmaw is in the set...",
    "Loading 99 cards and a commander...",
    "Decompressing the Library of Leng...",
    "Parsing the Comprehensive Rules...",
    "Fetching lands from the deck...",
    "Cracking packs for rare cards...",
    "Calculating storm count...",
    "Paying the one generic and two blue...",
    "Generating infinite squirrel tokens...",
    "Checking the reserved list...",
    "Establishing dominance on the stack...",
]

# ASCII art splash screen - MTG themed with emojis and card types
SPELLBOOK_ART = """
                    ✨ [#fffcd6]☀️[/]  [#aad5f5]💧[/]  [#cbc2d9]💀[/]  [#e86a58]🔥[/]  [#7bc96a]🌲[/] ✨

        [bold #c9a227]╔════════════════════════════════════════════╗[/]
        [bold #c9a227]║[/]     [bold #e6c84a]⚔️  M T G   S P E L L B O O K  ⚔️[/]     [bold #c9a227]║[/]
        [bold #c9a227]╚════════════════════════════════════════════╝[/]

  [#aad5f5]┌────────────┐[/]     [bold #c9a227]┌───────────────┐[/]     [#e86a58]┌────────────┐[/]
  [#aad5f5]│[/] ⚡ INSTANT [#aad5f5]│[/]     [bold #c9a227]│[/]    [bold]33,000+[/]    [bold #c9a227]│[/]     [#e86a58]│[/] 🔮 SORCERY [#e86a58]│[/]
  [#aad5f5]│[/]    [dim]~ ~ ~[/]   [#aad5f5]│[/]     [bold #c9a227]│[/]   📚 CARDS    [bold #c9a227]│[/]     [#e86a58]│[/]    [dim]~ ~ ~[/]   [#e86a58]│[/]
  [#aad5f5]└────────────┘[/]     [bold #c9a227]└───────────────┘[/]     [#e86a58]└────────────┘[/]

  [#7bc96a]┌────────────┐[/]   [#fffcd6]W[/]  [#aad5f5]U[/]  [#cbc2d9]B[/]  [#e86a58]R[/]  [#7bc96a]G[/]   [#cbc2d9]┌────────────┐[/]
  [#7bc96a]│[/] 🐉 CREATURE[#7bc96a]│[/]   [#fffcd6]◉[/]  [#aad5f5]◉[/]  [#cbc2d9]◉[/]  [#e86a58]◉[/]  [#7bc96a]◉[/]   [#cbc2d9]│[/] ✨ ENCHANT [#cbc2d9]│[/]
  [#7bc96a]│[/]    [dim]~ ~ ~[/]   [#7bc96a]│[/]                   [#cbc2d9]│[/]    [dim]~ ~ ~[/]   [#cbc2d9]│[/]
  [#7bc96a]└────────────┘[/]                   [#cbc2d9]└────────────┘[/]

           🌟 [dim]Tapping into the multiverse...[/] 🌟
"""


class SplashScreen(App[bool]):
    """Splash screen that sets up databases on first run."""

    CSS = """
    Screen {
        align: center middle;
        background: $surface;
    }

    #splash-container {
        width: 100%;
        height: auto;
        align: center middle;
    }

    #spellbook-art {
        text-align: center;
        width: 100%;
        height: auto;
        content-align: center middle;
    }

    #status-container {
        width: 90%;
        max-width: 60;
        height: auto;
        align: center middle;
        margin-top: 2;
    }

    #status-message {
        text-align: center;
        width: 100%;
        color: $text;
        margin-bottom: 0;
    }

    #flavor-message {
        text-align: center;
        width: 100%;
        color: $text-muted;
        margin-bottom: 1;
        height: 1;
    }

    #progress-bar {
        width: 100%;
        height: 1;
    }

    #eta-label {
        text-align: center;
        width: 100%;
        color: $text-muted;
        margin-top: 0;
    }

    #error-message {
        text-align: center;
        color: $error;
        margin-top: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._current_message_index = 0
        self._setup_complete = False
        self._error: str | None = None
        self._last_flavor_time: float = 0
        self._flavor_interval: float = 3.0  # Seconds between flavor message changes
        self._start_time: float = 0
        self._last_progress: float = 0
        self._progress_times: list[tuple[float, float]] = []  # (time, progress) for ETA
        self._timer_handle: Timer | None = None
        self._scryfall_updated_at: str | None = None  # Timestamp from Scryfall API

    def compose(self) -> ComposeResult:
        with Vertical(id="splash-container"):
            yield Static(SPELLBOOK_ART, id="spellbook-art")
            with Center(), Vertical(id="status-container"):
                yield Label("Preparing your spellbook...", id="status-message")
                yield Label("", id="flavor-message")
                yield ProgressBar(id="progress-bar", total=100, show_eta=False)
                yield Label("", id="eta-label")
                yield Label("", id="error-message")

    def on_mount(self) -> None:
        """Start the setup process."""
        import time

        # Initialize progress bar
        bar = self.query_one("#progress-bar", ProgressBar)
        bar.update(total=100, progress=0)

        # Start timer immediately for elapsed time display
        self._start_time = time.time()
        self._last_flavor_time = time.time()
        self._timer_handle = self.set_interval(1.0, self._tick_timer)

        self.run_setup()

    def _tick_timer(self) -> None:
        """Called every second to update elapsed time and ETA display."""
        import time

        now = time.time()
        elapsed = now - self._start_time

        eta_label = self.query_one("#eta-label", Label)

        # Calculate ETA if we have enough data
        eta_text = ""
        if len(self._progress_times) >= 2 and self._last_progress > 0:
            oldest = self._progress_times[0]
            time_elapsed = now - oldest[0]
            progress_made = self._last_progress - oldest[1]

            if time_elapsed > 0 and progress_made > 0:
                rate = progress_made / time_elapsed
                remaining_progress = 1.0 - self._last_progress
                eta_seconds = remaining_progress / rate

                if eta_seconds < 1800:  # Only show if < 30 minutes
                    eta_text = f" | Remaining: ~{self._format_time(eta_seconds)}"

        eta_label.update(f"[dim]Elapsed: {self._format_time(elapsed)}{eta_text}[/]")

        # Update flavor message if enough time has passed
        self._update_flavor()

    def _get_random_message(self) -> str:
        """Get a random loading message."""
        return random.choice(LOADING_MESSAGES)

    def _update_status(self, message: str) -> None:
        """Update the main status message (always shown immediately)."""
        status = self.query_one("#status-message", Label)
        status.update(message)

    def _update_flavor(self) -> None:
        """Update flavor message if enough time has passed."""
        import time

        now = time.time()
        if now - self._last_flavor_time >= self._flavor_interval:
            flavor = self.query_one("#flavor-message", Label)
            flavor.update(f"[dim]{self._get_random_message()}[/]")
            self._last_flavor_time = now

    def _format_time(self, seconds: float) -> str:
        """Format seconds into human-readable time."""
        if seconds < 60:
            return f"{int(seconds)}s"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"

    def _record_progress(self, progress: float) -> None:
        """Record progress point for ETA calculation (timer handles display)."""
        import time

        now = time.time()

        # Record progress point for ETA calculation
        self._progress_times.append((now, progress))

        # Keep only last 20 data points for smoothing
        if len(self._progress_times) > 20:
            self._progress_times = self._progress_times[-20:]

    def _stop_timer(self) -> None:
        """Stop the elapsed time timer."""
        if self._timer_handle is not None:
            self._timer_handle.stop()
            self._timer_handle = None

    def _update_progress(self, progress: float) -> None:
        """Update progress bar (0.0 to 1.0) and record progress for ETA."""
        bar = self.query_one("#progress-bar", ProgressBar)
        bar.update(progress=progress * 100)
        self._last_progress = progress
        self._record_progress(progress)

    def _show_error(self, message: str) -> None:
        """Show an error message."""
        error_label = self.query_one("#error-message", Label)
        error_label.update(f"[red]{message}[/]")

    @work(exclusive=True)
    async def run_setup(self) -> None:
        """Run the database setup process."""
        from mtg_core.config import get_settings

        settings = get_settings()
        mtg_db = settings.mtg_db_path

        try:
            # Phase 1: Check freshness
            needs_update, scryfall_updated_at = await self._check_freshness(mtg_db)

            if not needs_update:
                # Main DB is fresh, but still check if combo DB needs download
                await self._ensure_combo_database()
                self._update_status("Data is up to date! Starting app...")
                self._update_progress(1.0)
                self._stop_timer()
                await asyncio.sleep(0.5)
                self._setup_complete = True
                self.exit(True)
                return

            # Store the updated_at for later
            self._scryfall_updated_at = scryfall_updated_at

            # Create output directory
            output_dir = mtg_db.parent
            output_dir.mkdir(parents=True, exist_ok=True)

            # Build unified database
            await self._build_database(output_dir)

            # Pre-populate price cache if there's an existing collection
            await self._prepopulate_price_cache()

            # Done!
            self._update_status("[bold green]Setup complete! Opening Spellbook...[/]")
            self._update_progress(1.0)
            self._stop_timer()
            await asyncio.sleep(1.0)
            self._setup_complete = True
            self.exit(True)

        except Exception as e:
            self._show_error(f"Setup failed: {e}")
            self._update_status("[red]Press any key to exit...[/]")
            self._error = str(e)

    async def _prepopulate_price_cache(self) -> None:
        """Pre-populate the price cache if there's an existing collection."""
        import aiosqlite

        from mtg_core.config import get_settings
        from mtg_core.data.database import UnifiedDatabase, UserDatabase

        from .collection_manager import CollectionManager

        settings = get_settings()
        user_db_path = settings.user_db_path

        # Check if user database exists
        if not user_db_path.exists():
            return

        self._update_status("Caching collection prices...")
        self._update_progress(0.96)

        try:
            # Connect to user database
            user_db = UserDatabase(user_db_path)
            await user_db.connect()

            # Connect to unified database (requires aiosqlite connection)
            conn = await aiosqlite.connect(settings.mtg_db_path)
            unified_db = UnifiedDatabase(conn)

            try:
                # Get collection cards
                cards = await user_db.get_collection_cards(limit=10000, offset=0)
                if not cards:
                    return

                # Build list of (set_code, collector_number) for price lookup
                printings: list[tuple[str, str]] = []
                for card in cards:
                    if card.set_code and card.collector_number:
                        printings.append((card.set_code, card.collector_number))

                if not printings:
                    return

                # Fetch prices
                prices = await unified_db.get_prices_by_set_and_numbers(printings)

                # Build price cache dict
                price_cache: dict[str, tuple[float | None, float | None]] = {}
                for card in cards:
                    if card.set_code and card.collector_number:
                        key = (card.set_code.upper(), card.collector_number)
                        if key in prices:
                            usd, usd_foil = prices[key]
                            # Convert cents to dollars
                            usd_dollars = usd / 100.0 if usd else None
                            usd_foil_dollars = usd_foil / 100.0 if usd_foil else None
                            cache_key = (
                                f"{card.card_name}|{card.set_code.upper()}|{card.collector_number}"
                            )
                            price_cache[cache_key] = (usd_dollars, usd_foil_dollars)

                if price_cache:
                    # Save to disk using CollectionManager's format
                    manager = CollectionManager(user_db, unified_db)
                    manager.set_cached_prices(price_cache)

            finally:
                await user_db.close()
                await conn.close()

        except Exception:
            # Don't fail setup if price caching fails
            pass

    async def _get_scryfall_bulk_metadata(self) -> dict[str, dict[str, str]]:
        """Fetch Scryfall bulk data metadata (URLs and updated_at times)."""
        import httpx

        timeout = httpx.Timeout(connect=30.0, read=60.0, write=30.0, pool=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get("https://api.scryfall.com/bulk-data")
            response.raise_for_status()
            data = response.json()

        result: dict[str, dict[str, str]] = {}
        for item in data["data"]:
            result[item["type"]] = {
                "download_uri": item["download_uri"],
                "updated_at": item["updated_at"],
            }
        return result

    async def _get_scryfall_bulk_url(self, bulk_type: str) -> str:
        """Get download URL for a Scryfall bulk data type."""
        metadata = await self._get_scryfall_bulk_metadata()
        if bulk_type not in metadata:
            raise ValueError(f"Bulk data type '{bulk_type}' not found")
        return metadata[bulk_type]["download_uri"]

    def _get_stored_update_time(self, db_path: Path) -> str | None:
        """Get the stored Scryfall update time from the database meta table."""
        if not db_path.exists():
            return None

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            result = cursor.execute(
                "SELECT value FROM meta WHERE key = 'scryfall_updated_at'"
            ).fetchone()
            conn.close()
            return result[0] if result else None
        except (sqlite3.Error, IndexError):
            return None

    async def _check_freshness(self, db_path: Path) -> tuple[bool, str | None]:
        """Check if the database needs updating.

        Returns (needs_update, latest_updated_at).
        """
        self._update_status("Checking for updates...")
        self._update_progress(0.02)

        try:
            metadata = await self._get_scryfall_bulk_metadata()
            latest_updated_at = metadata.get("default_cards", {}).get("updated_at")

            if not latest_updated_at:
                # Can't determine freshness, assume update needed
                return True, None

            stored_updated_at = self._get_stored_update_time(db_path)

            if stored_updated_at is None:
                # No stored time, need to build
                return True, latest_updated_at

            # Compare timestamps (ISO format strings compare correctly)
            if latest_updated_at > stored_updated_at:
                return True, latest_updated_at

            # Data is current
            return False, latest_updated_at

        except Exception:
            # Network error or other issue - if DB exists, use it
            if db_path.exists():
                return False, None
            return True, None

    async def _download_file(
        self,
        url: str,
        dest: Path,
        base_progress: float,
        step_progress: float,
    ) -> None:
        """Download a file with progress updates."""
        import httpx

        timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)
        async with (
            httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client,
            client.stream("GET", url) as response,
        ):
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            downloaded = 0

            with dest.open("wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        dl_progress = downloaded / total
                        self._update_progress(base_progress + step_progress * dl_progress)

    async def _download_scryfall_sources(self, tmpdir: Path) -> tuple[Path, Path, Path]:
        """Download Scryfall bulk data files."""
        import httpx

        # Get download URLs
        self._update_status("Connecting to Scryfall API...")
        self._update_progress(0.05)

        cards_url = await self._get_scryfall_bulk_url("default_cards")
        rulings_url = await self._get_scryfall_bulk_url("rulings")

        # Download cards (largest file - ~350MB, majority of download time)
        self._update_status("Downloading 110,000+ cards from Scryfall (~350MB)...")
        cards_json = tmpdir / "default_cards.json"
        await self._download_file(cards_url, cards_json, 0.08, 0.35)

        # Download sets from API endpoint (not bulk data)
        self._update_status("Downloading set information...")
        sets_json = tmpdir / "sets.json"
        timeout = httpx.Timeout(connect=30.0, read=60.0, write=30.0, pool=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get("https://api.scryfall.com/sets")
            response.raise_for_status()
            with sets_json.open("w") as f:
                f.write(response.text)
        self._update_progress(0.45)

        # Download rulings
        self._update_status("Downloading card rulings...")
        rulings_json = tmpdir / "rulings.json"
        await self._download_file(rulings_url, rulings_json, 0.45, 0.05)

        return cards_json, sets_json, rulings_json

    async def _download_mtgjson(self, tmpdir: Path) -> Path:
        """Download MTGJson SetList for set metadata.

        Uses SetList.json instead of AllPrintings.json.gz - much smaller file
        with just set metadata (block, keyruneCode, etc). EDHREC ranks come from Scryfall.
        """
        self._update_status("Downloading set metadata...")

        # SetList.json is ~100KB vs AllPrintings.json.gz at ~200MB
        mtgjson_url = "https://mtgjson.com/api/v5/SetList.json"
        mtgjson_path = tmpdir / "SetList.json"
        await self._download_file(mtgjson_url, mtgjson_path, 0.50, 0.05)

        return mtgjson_path

    def _create_schema(self, cursor: sqlite3.Cursor) -> None:
        """Create the unified database schema."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cards (
                id TEXT PRIMARY KEY,
                oracle_id TEXT,
                name TEXT NOT NULL,
                flavor_name TEXT,
                layout TEXT,
                mana_cost TEXT,
                cmc REAL,
                colors TEXT,
                color_identity TEXT,
                type_line TEXT,
                oracle_text TEXT,
                flavor_text TEXT,
                power TEXT,
                toughness TEXT,
                loyalty TEXT,
                defense TEXT,
                keywords TEXT,
                set_code TEXT NOT NULL,
                set_name TEXT,
                rarity TEXT CHECK(rarity IN ('common','uncommon','rare','mythic','special','bonus') OR rarity IS NULL),
                collector_number TEXT NOT NULL,
                artist TEXT,
                release_date TEXT,
                is_token INTEGER DEFAULT 0 CHECK(is_token IN (0, 1)),
                is_promo INTEGER DEFAULT 0 CHECK(is_promo IN (0, 1)),
                is_digital_only INTEGER DEFAULT 0 CHECK(is_digital_only IN (0, 1)),
                edhrec_rank INTEGER,
                image_small TEXT,
                image_normal TEXT,
                image_large TEXT,
                image_png TEXT,
                image_art_crop TEXT,
                image_border_crop TEXT,
                price_usd INTEGER,
                price_usd_foil INTEGER,
                price_eur INTEGER,
                price_eur_foil INTEGER,
                purchase_tcgplayer TEXT,
                purchase_cardmarket TEXT,
                purchase_cardhoarder TEXT,
                link_edhrec TEXT,
                link_gatherer TEXT,
                illustration_id TEXT,
                highres_image INTEGER DEFAULT 0,
                border_color TEXT,
                frame TEXT,
                full_art INTEGER DEFAULT 0,
                art_priority INTEGER DEFAULT 2,
                finishes TEXT,
                legalities TEXT NOT NULL,
                legal_commander INTEGER GENERATED ALWAYS AS (
                    json_extract(legalities, '$.commander') = 'legal'
                ) STORED,
                legal_modern INTEGER GENERATED ALWAYS AS (
                    json_extract(legalities, '$.modern') = 'legal'
                ) STORED,
                legal_standard INTEGER GENERATED ALWAYS AS (
                    json_extract(legalities, '$.standard') = 'legal'
                ) STORED
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sets (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                set_type TEXT,
                release_date TEXT,
                card_count INTEGER,
                icon_svg_uri TEXT,
                block TEXT,
                base_set_size INTEGER,
                total_set_size INTEGER,
                is_online_only INTEGER DEFAULT 0,
                is_foil_only INTEGER DEFAULT 0,
                keyrune_code TEXT
            ) WITHOUT ROWID
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rulings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                oracle_id TEXT,
                published_at TEXT,
                comment TEXT,
                source TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

    def _create_indexes(self, cursor: sqlite3.Cursor) -> None:
        """Create performance indexes."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_cards_oracle_id ON cards(oracle_id)",
            "CREATE INDEX IF NOT EXISTS idx_cards_name ON cards(name COLLATE NOCASE)",
            "CREATE INDEX IF NOT EXISTS idx_cards_set_number ON cards(set_code, collector_number)",
            "CREATE INDEX IF NOT EXISTS idx_cards_type_line ON cards(type_line)",
            "CREATE INDEX IF NOT EXISTS idx_cards_artist ON cards(artist)",
            "CREATE INDEX IF NOT EXISTS idx_cards_cmc ON cards(cmc)",
            "CREATE INDEX IF NOT EXISTS idx_cards_rarity ON cards(rarity)",
            "CREATE INDEX IF NOT EXISTS idx_cards_illustration ON cards(name, illustration_id, art_priority)",
            "CREATE INDEX IF NOT EXISTS idx_rulings_oracle_id ON rulings(oracle_id)",
            """CREATE INDEX IF NOT EXISTS idx_cards_name_covering ON cards(
                name COLLATE NOCASE, release_date DESC,
                set_code, collector_number, mana_cost, type_line,
                image_normal, price_usd
            )""",
            "CREATE INDEX IF NOT EXISTS idx_cards_real ON cards(name, set_code) WHERE is_token = 0 AND is_digital_only = 0",
            "CREATE INDEX IF NOT EXISTS idx_cards_price ON cards(price_usd) WHERE price_usd IS NOT NULL",
            "CREATE INDEX IF NOT EXISTS idx_cards_tokens ON cards(name, set_code) WHERE is_token = 1",
            "CREATE INDEX IF NOT EXISTS idx_legal_commander ON cards(legal_commander) WHERE legal_commander = 1",
            "CREATE INDEX IF NOT EXISTS idx_legal_modern ON cards(legal_modern) WHERE legal_modern = 1",
            "CREATE INDEX IF NOT EXISTS idx_legal_standard ON cards(legal_standard) WHERE legal_standard = 1",
        ]
        for sql in indexes:
            cursor.execute(sql)

    def _import_sets(self, cursor: sqlite3.Cursor, sets_json: Path) -> int:
        """Import sets from Scryfall sets bulk file."""
        with sets_json.open() as f:
            data = json.load(f)

        sets_data = data if isinstance(data, list) else data.get("data", [])
        count = 0

        for s in sets_data:
            cursor.execute(
                "INSERT OR REPLACE INTO sets (code, name, set_type, release_date, card_count, icon_svg_uri) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    s.get("code"),
                    s.get("name"),
                    s.get("set_type"),
                    s.get("released_at"),
                    s.get("card_count"),
                    s.get("icon_svg_uri"),
                ),
            )
            count += 1

        return count

    def _price_to_cents(self, price: str | None) -> int | None:
        """Convert price string to cents."""
        if price is None:
            return None
        try:
            return int(float(price) * 100)
        except (ValueError, TypeError):
            return None

    def _calculate_art_priority(self, card: dict[str, Any]) -> int:
        """Calculate art priority: 0=borderless, 1=full_art, 2=regular."""
        if card.get("border_color") == "borderless":
            return 0
        if card.get("full_art"):
            return 1
        return 2

    def _insert_card(self, cursor: sqlite3.Cursor, card: dict[str, Any]) -> None:
        """Insert a single card into the database."""
        images = card.get("image_uris", {})
        if not images and "card_faces" in card:
            faces = card.get("card_faces", [])
            if faces:
                images = faces[0].get("image_uris", {})

        prices = card.get("prices", {})
        purchase = card.get("purchase_uris", {})
        related = card.get("related_uris", {})
        legalities = json.dumps(card.get("legalities", {}))
        layout = card.get("layout", "")
        is_token = 1 if layout in ("token", "double_faced_token", "emblem") else 0

        cursor.execute(
            """INSERT OR REPLACE INTO cards (
                id, oracle_id, name, flavor_name, layout, mana_cost, cmc, colors, color_identity,
                type_line, oracle_text, flavor_text, power, toughness, loyalty, defense, keywords,
                set_code, set_name, rarity, collector_number, artist, release_date,
                is_token, is_promo, is_digital_only, edhrec_rank,
                image_small, image_normal, image_large, image_png, image_art_crop, image_border_crop,
                price_usd, price_usd_foil, price_eur, price_eur_foil,
                purchase_tcgplayer, purchase_cardmarket, purchase_cardhoarder, link_edhrec, link_gatherer,
                illustration_id, highres_image, border_color, frame, full_art, art_priority, finishes, legalities
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                card.get("id"),
                card.get("oracle_id"),
                card.get("name"),
                card.get("flavor_name"),
                layout,
                card.get("mana_cost"),
                card.get("cmc"),
                json.dumps(card.get("colors", [])),
                json.dumps(card.get("color_identity", [])),
                card.get("type_line"),
                card.get("oracle_text"),
                card.get("flavor_text"),
                card.get("power"),
                card.get("toughness"),
                card.get("loyalty"),
                card.get("defense"),
                json.dumps(card.get("keywords", [])),
                card.get("set"),
                card.get("set_name"),
                card.get("rarity"),
                card.get("collector_number"),
                card.get("artist"),
                card.get("released_at"),
                is_token,
                1 if card.get("promo") else 0,
                1 if card.get("digital") else 0,
                card.get("edhrec_rank"),
                images.get("small"),
                images.get("normal"),
                images.get("large"),
                images.get("png"),
                images.get("art_crop"),
                images.get("border_crop"),
                self._price_to_cents(prices.get("usd")),
                self._price_to_cents(prices.get("usd_foil")),
                self._price_to_cents(prices.get("eur")),
                self._price_to_cents(prices.get("eur_foil")),
                purchase.get("tcgplayer"),
                purchase.get("cardmarket"),
                purchase.get("cardhoarder"),
                related.get("edhrec"),
                related.get("gatherer"),
                card.get("illustration_id"),
                1 if card.get("highres_image") else 0,
                card.get("border_color"),
                card.get("frame"),
                1 if card.get("full_art") else 0,
                self._calculate_art_priority(card),
                json.dumps(card.get("finishes", [])),
                legalities,
            ),
        )

    def _prepare_card_row(self, card: dict[str, Any]) -> tuple[Any, ...]:
        """Prepare a card row tuple for batch insert."""
        images = card.get("image_uris", {})
        if not images and "card_faces" in card:
            faces = card.get("card_faces", [])
            if faces:
                images = faces[0].get("image_uris", {})

        prices = card.get("prices", {})
        purchase = card.get("purchase_uris", {})
        related = card.get("related_uris", {})
        legalities = json.dumps(card.get("legalities", {}))
        layout = card.get("layout", "")
        is_token = 1 if layout in ("token", "double_faced_token", "emblem") else 0

        # ijson returns Decimal for numbers, which SQLite can't bind - convert cmc to float
        cmc = card.get("cmc")
        cmc_float = float(cmc) if cmc is not None else None

        return (
            card.get("id"),
            card.get("oracle_id"),
            card.get("name"),
            card.get("flavor_name"),
            layout,
            card.get("mana_cost"),
            cmc_float,
            json.dumps(card.get("colors", [])),
            json.dumps(card.get("color_identity", [])),
            card.get("type_line"),
            card.get("oracle_text"),
            card.get("flavor_text"),
            card.get("power"),
            card.get("toughness"),
            card.get("loyalty"),
            card.get("defense"),
            json.dumps(card.get("keywords", [])),
            card.get("set"),
            card.get("set_name"),
            card.get("rarity"),
            card.get("collector_number"),
            card.get("artist"),
            card.get("released_at"),
            is_token,
            1 if card.get("promo") else 0,
            1 if card.get("digital") else 0,
            card.get("edhrec_rank"),
            images.get("small"),
            images.get("normal"),
            images.get("large"),
            images.get("png"),
            images.get("art_crop"),
            images.get("border_crop"),
            self._price_to_cents(prices.get("usd")),
            self._price_to_cents(prices.get("usd_foil")),
            self._price_to_cents(prices.get("eur")),
            self._price_to_cents(prices.get("eur_foil")),
            purchase.get("tcgplayer"),
            purchase.get("cardmarket"),
            purchase.get("cardhoarder"),
            related.get("edhrec"),
            related.get("gatherer"),
            card.get("illustration_id"),
            1 if card.get("highres_image") else 0,
            card.get("border_color"),
            card.get("frame"),
            1 if card.get("full_art") else 0,
            self._calculate_art_priority(card),
            json.dumps(card.get("finishes", [])),
            legalities,
        )

    def _import_cards_streaming(
        self,
        cursor: sqlite3.Cursor,
        cards_json: Path,
        progress_callback: Any = None,
    ) -> int:
        """Import cards from Scryfall default_cards bulk file using streaming and batching."""
        import ijson

        BATCH_SIZE = 5000
        batch: list[tuple[Any, ...]] = []
        count = 0

        insert_sql = """INSERT OR REPLACE INTO cards (
            id, oracle_id, name, flavor_name, layout, mana_cost, cmc, colors, color_identity,
            type_line, oracle_text, flavor_text, power, toughness, loyalty, defense, keywords,
            set_code, set_name, rarity, collector_number, artist, release_date,
            is_token, is_promo, is_digital_only, edhrec_rank,
            image_small, image_normal, image_large, image_png, image_art_crop, image_border_crop,
            price_usd, price_usd_foil, price_eur, price_eur_foil,
            purchase_tcgplayer, purchase_cardmarket, purchase_cardhoarder, link_edhrec, link_gatherer,
            illustration_id, highres_image, border_color, frame, full_art, art_priority, finishes, legalities
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

        # Streaming JSON parsing - does not load entire file into memory
        with cards_json.open("rb") as f:
            for card in ijson.items(f, "item"):
                batch.append(self._prepare_card_row(card))
                count += 1

                if len(batch) >= BATCH_SIZE:
                    cursor.executemany(insert_sql, batch)
                    batch.clear()
                    if progress_callback:
                        progress_callback(count)

        # Insert remaining cards
        if batch:
            cursor.executemany(insert_sql, batch)
            if progress_callback:
                progress_callback(count)

        return count

    def _import_cards(self, cursor: sqlite3.Cursor, cards_json: Path) -> int:
        """Import cards from Scryfall default_cards bulk file (legacy method for compatibility)."""
        return self._import_cards_streaming(cursor, cards_json)

    def _import_rulings(self, cursor: sqlite3.Cursor, rulings_json: Path) -> int:
        """Import rulings from Scryfall rulings bulk file using batching."""
        import ijson

        BATCH_SIZE = 5000
        batch: list[tuple[Any, ...]] = []
        count = 0

        insert_sql = (
            "INSERT INTO rulings (oracle_id, published_at, comment, source) VALUES (?, ?, ?, ?)"
        )

        with rulings_json.open("rb") as f:
            for ruling in ijson.items(f, "item"):
                batch.append(
                    (
                        ruling.get("oracle_id"),
                        ruling.get("published_at"),
                        ruling.get("comment"),
                        ruling.get("source"),
                    )
                )
                count += 1

                if len(batch) >= BATCH_SIZE:
                    cursor.executemany(insert_sql, batch)
                    batch.clear()

        if batch:
            cursor.executemany(insert_sql, batch)

        return count

    def _supplement_from_mtgjson_setlist(
        self,
        cursor: sqlite3.Cursor,
        setlist_path: Path,
    ) -> int:
        """Supplement set metadata from MTGJson SetList.json.

        SetList.json is ~100KB and contains just set metadata.
        EDHREC ranks are already provided by Scryfall.
        """
        BATCH_SIZE = 1000

        with setlist_path.open() as f:
            data = json.load(f)

        sets_list = data.get("data", [])
        set_updates: list[tuple[Any, ...]] = []

        for set_info in sets_list:
            set_updates.append(
                (
                    set_info.get("block"),
                    set_info.get("baseSetSize"),
                    set_info.get("totalSetSize"),
                    1 if set_info.get("isOnlineOnly") else 0,
                    1 if set_info.get("isFoilOnly") else 0,
                    set_info.get("keyruneCode"),
                    set_info.get("code"),
                )
            )

        sets_updated = 0
        for i in range(0, len(set_updates), BATCH_SIZE):
            batch = set_updates[i : i + BATCH_SIZE]
            cursor.executemany(
                """UPDATE sets SET
                    block = COALESCE(?, block),
                    base_set_size = COALESCE(?, base_set_size),
                    total_set_size = COALESCE(?, total_set_size),
                    is_online_only = ?,
                    is_foil_only = ?,
                    keyrune_code = COALESCE(?, keyrune_code)
                WHERE code COLLATE NOCASE = ?""",
                batch,
            )
            sets_updated += cursor.rowcount

        return sets_updated

    def _create_fts_index(self, cursor: sqlite3.Cursor) -> None:
        """Create FTS5 full-text search index."""
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
                id UNINDEXED,
                name,
                type_line,
                oracle_text,
                tokenize='porter unicode61'
            )
        """)

        cursor.execute("""
            INSERT INTO cards_fts(id, name, type_line, oracle_text)
            SELECT id, name, type_line, oracle_text FROM cards
        """)

        cursor.execute("INSERT INTO cards_fts(cards_fts) VALUES('optimize')")

    def _build_unified_db_sync(
        self,
        output_path: Path,
        cards_json: Path,
        sets_json: Path,
        rulings_json: Path,
        mtgjson_path: Path | None = None,
        progress_callback: Any = None,
        scryfall_updated_at: str | None = None,
    ) -> tuple[int, int, int]:
        """Build the unified database (runs in thread)."""
        output_path.unlink(missing_ok=True)

        conn = sqlite3.connect(output_path, isolation_level=None)
        cursor = conn.cursor()

        try:
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA synchronous = NORMAL")
            cursor.execute("PRAGMA cache_size = -64000")
            cursor.execute("PRAGMA temp_store = MEMORY")

            cursor.execute("BEGIN IMMEDIATE")
            self._create_schema(cursor)
            cursor.execute("COMMIT")

            cursor.execute("BEGIN IMMEDIATE")
            set_count = self._import_sets(cursor, sets_json)
            cursor.execute("COMMIT")

            cursor.execute("BEGIN IMMEDIATE")
            card_count = self._import_cards_streaming(cursor, cards_json, progress_callback)
            cursor.execute("COMMIT")

            cursor.execute("BEGIN IMMEDIATE")
            ruling_count = self._import_rulings(cursor, rulings_json)
            cursor.execute("COMMIT")

            if mtgjson_path and mtgjson_path.exists():
                cursor.execute("BEGIN IMMEDIATE")
                self._supplement_from_mtgjson_setlist(cursor, mtgjson_path)
                cursor.execute("COMMIT")

            cursor.execute("BEGIN IMMEDIATE")
            self._create_indexes(cursor)
            cursor.execute("COMMIT")

            cursor.execute("BEGIN IMMEDIATE")
            self._create_fts_index(cursor)
            cursor.execute("COMMIT")

            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute("INSERT INTO meta (key, value) VALUES (?, ?)", ("schema_version", "1"))
            cursor.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?)",
                ("created_at", datetime.now().isoformat()),
            )
            cursor.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?)", ("card_count", str(card_count))
            )
            cursor.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?)", ("set_count", str(set_count))
            )
            cursor.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?)", ("ruling_count", str(ruling_count))
            )
            if scryfall_updated_at:
                cursor.execute(
                    "INSERT INTO meta (key, value) VALUES (?, ?)",
                    ("scryfall_updated_at", scryfall_updated_at),
                )
            cursor.execute("COMMIT")

            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")

        finally:
            conn.close()

        return card_count, set_count, ruling_count

    def _get_combo_db_timestamp(self, db_path: Path) -> str | None:
        """Get the stored release timestamp from combo database meta table."""
        if not db_path.exists():
            return None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            result = cursor.execute(
                "SELECT value FROM meta WHERE key = 'release_updated_at'"
            ).fetchone()
            conn.close()
            return result[0] if result else None
        except sqlite3.Error:
            return None

    def _set_combo_db_timestamp(self, db_path: Path, timestamp: str) -> None:
        """Store the release timestamp in combo database meta table."""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            # Create meta table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            cursor.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("release_updated_at", timestamp),
            )
            conn.commit()
            conn.close()
        except sqlite3.Error:
            pass  # Non-fatal

    async def _ensure_combo_database(self) -> None:
        """Check combo database freshness and download if needed."""
        import gzip
        import shutil

        import httpx

        from mtg_core.config import get_settings

        settings = get_settings()
        db_path = settings.combo_db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Get local timestamp if database exists
        local_timestamp = self._get_combo_db_timestamp(db_path) if db_path.exists() else None

        # Fetch releases to check freshness
        self._update_status("Checking combo database...")
        self._update_progress(0.05)

        releases_url = (
            "https://api.github.com/repos/aimaginationlab/magic-the-gathering-toolkit/releases"
        )

        try:
            timeout = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                # Get releases list
                response = await client.get(releases_url)
                response.raise_for_status()
                releases = response.json()

                # Sort by updated_at descending to get the latest first
                releases.sort(key=lambda r: r.get("updated_at", ""), reverse=True)

                # Find combo asset and release timestamp
                asset_url: str | None = None
                release_updated_at: str | None = None
                is_gzipped = False

                for release in releases:
                    release_updated_at = release.get("updated_at")
                    for asset in release.get("assets", []):
                        if asset["name"] == "combos.sqlite.gz":
                            asset_url = asset["browser_download_url"]
                            is_gzipped = True
                            break
                        elif asset["name"] == "combos.sqlite" and not asset_url:
                            asset_url = asset["browser_download_url"]
                    if asset_url:
                        break

                if not asset_url:
                    self._update_status("Combo database not found in releases")
                    self._update_progress(0.10)
                    return

                # Check if we need to download (no local db or release is newer)
                needs_download = not db_path.exists()
                if not needs_download and local_timestamp and release_updated_at:
                    needs_download = release_updated_at > local_timestamp

                if not needs_download:
                    self._update_status("Combo database up to date")
                    self._update_progress(0.10)
                    return

                # Download
                gz_path = db_path.with_suffix(".sqlite.gz") if is_gzipped else db_path
                await self._download_combo_database(client, asset_url, gz_path)

                # Decompress if gzipped
                if is_gzipped:
                    self._update_status("Decompressing combo database...")
                    with gzip.open(gz_path, "rb") as f_in, open(db_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                    gz_path.unlink()  # Remove compressed file

                if release_updated_at:
                    self._set_combo_db_timestamp(db_path, release_updated_at)

        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.ConnectError) as e:
            # Network error - if we have a local db, continue; otherwise note error
            if db_path.exists():
                self._update_status("Combo database ready (offline)")
            else:
                self._update_status(f"Combo download failed: {type(e).__name__}")
            self._update_progress(0.10)

    async def _download_combo_database(
        self,
        client: httpx.AsyncClient,
        asset_url: str,
        db_path: Path,
    ) -> None:
        """Download combo database with progress."""
        self._update_status("Downloading combo database (73K+ combos)...")
        self._update_progress(0.10)

        async with client.stream("GET", asset_url) as stream:
            stream.raise_for_status()
            total_size = int(stream.headers.get("content-length", 0))
            downloaded = 0

            with open(db_path, "wb") as f:
                async for chunk in stream.aiter_bytes(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        dl_progress = downloaded / total_size
                        progress = 0.10 + dl_progress * 0.85
                        self._update_progress(progress)
                        if downloaded % (5 * 1024 * 1024) < 65536:  # Every ~5MB
                            mb_done = downloaded / (1024 * 1024)
                            mb_total = total_size / (1024 * 1024)
                            self._update_status(
                                f"Downloading combos: {mb_done:.1f}/{mb_total:.1f} MB"
                            )

        self._update_status("Combo database ready!")
        self._update_progress(0.95)

    async def _init_combos(self, current_step: int, total_steps: int) -> None:
        """Download combo database from GitHub releases if needed."""
        import gzip
        import shutil

        import httpx

        from mtg_core.config import get_settings

        base_progress = current_step / total_steps
        step_progress = 1 / total_steps

        settings = get_settings()
        db_path = settings.combo_db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Get local timestamp if database exists
        local_timestamp = self._get_combo_db_timestamp(db_path) if db_path.exists() else None

        self._update_status("Checking combo database...")
        self._update_progress(base_progress + step_progress * 0.05)

        releases_url = (
            "https://api.github.com/repos/aimaginationlab/magic-the-gathering-toolkit/releases"
        )

        try:
            timeout = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                # Get releases list
                response = await client.get(releases_url)
                response.raise_for_status()
                releases = response.json()

                # Sort by updated_at descending to get the latest first
                releases.sort(key=lambda r: r.get("updated_at", ""), reverse=True)

                # Find combo asset and release timestamp
                asset_url: str | None = None
                release_updated_at: str | None = None
                is_gzipped = False

                for release in releases:
                    release_updated_at = release.get("updated_at")
                    for asset in release.get("assets", []):
                        if asset["name"] == "combos.sqlite.gz":
                            asset_url = asset["browser_download_url"]
                            is_gzipped = True
                            break
                        elif asset["name"] == "combos.sqlite" and not asset_url:
                            asset_url = asset["browser_download_url"]
                    if asset_url:
                        break

                if not asset_url:
                    self._update_status("Combo database not found in releases")
                    self._update_progress(base_progress + step_progress)
                    return

                # Check if we need to download (no local db or release is newer)
                needs_download = not db_path.exists()
                if not needs_download and local_timestamp and release_updated_at:
                    needs_download = release_updated_at > local_timestamp

                if not needs_download:
                    self._update_status("Combo database up to date")
                    self._update_progress(base_progress + step_progress)
                    return

                # Determine download path
                download_path = db_path.with_suffix(".sqlite.gz") if is_gzipped else db_path

                # Download with progress
                self._update_status("Downloading combo database (73K+ combos)...")
                self._update_progress(base_progress + step_progress * 0.1)

                async with client.stream("GET", asset_url) as stream:
                    stream.raise_for_status()
                    total_size = int(stream.headers.get("content-length", 0))
                    downloaded = 0

                    with open(download_path, "wb") as f:
                        async for chunk in stream.aiter_bytes(chunk_size=65536):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                dl_progress = downloaded / total_size
                                progress = base_progress + step_progress * (
                                    0.1 + dl_progress * 0.80
                                )
                                self._update_progress(progress)
                                if downloaded % (5 * 1024 * 1024) < 65536:
                                    mb_done = downloaded / (1024 * 1024)
                                    mb_total = total_size / (1024 * 1024)
                                    self._update_status(
                                        f"Downloading combos: {mb_done:.1f}/{mb_total:.1f} MB"
                                    )

                # Decompress if gzipped
                if is_gzipped:
                    self._update_status("Decompressing combo database...")
                    self._update_progress(base_progress + step_progress * 0.92)
                    with gzip.open(download_path, "rb") as f_in, open(db_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                    download_path.unlink()  # Remove compressed file

                # Store the release timestamp
                if release_updated_at:
                    self._set_combo_db_timestamp(db_path, release_updated_at)

        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.ConnectError) as e:
            if db_path.exists():
                self._update_status("Combo database ready (offline)")
            else:
                self._update_status(f"Combo download failed: {type(e).__name__}")

        self._update_status("Combo database ready!")
        self._update_progress(base_progress + step_progress)

    async def _build_database(self, output_dir: Path) -> None:
        """Build the unified database.

        Downloads source data and builds mtg.sqlite.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # Phase 1: Download Scryfall data (cards, sets, rulings) - 5% to 50%
            cards_json, sets_json, rulings_json = await self._download_scryfall_sources(tmp)

            # Phase 2: Download MTGJson for set metadata - 50% to 55%
            self._update_status("Downloading set metadata from MTGJson...")
            self._update_progress(0.50)
            mtgjson_path = await self._download_mtgjson(tmp)

            # Phase 3: Build unified database - 55% to 92%
            # This is CPU-bound, so we run in thread but update progress via callback
            self._update_status("Building database: Creating schema...")
            self._update_progress(0.56)

            output_path = output_dir / "mtg.sqlite"

            # Progress callback for card import (the slow part)
            def on_card_progress(count: int) -> None:
                # Cards are 57% to 85% of progress (biggest chunk)
                # Estimate ~110k cards total
                card_progress = min(count / 110000, 1.0)
                progress = 0.57 + (card_progress * 0.28)
                # Use call_from_thread to update UI from worker thread
                self.call_from_thread(
                    self._update_status, f"Importing cards: {count:,} processed..."
                )
                self.call_from_thread(self._update_progress, progress)

            await asyncio.to_thread(
                self._build_unified_db_sync,
                output_path,
                cards_json,
                sets_json,
                rulings_json,
                mtgjson_path,
                on_card_progress,
                self._scryfall_updated_at,
            )

            self._update_status("Building database: Creating search indexes...")
            self._update_progress(0.88)

        # Phase 4: Initialize combo database - 92% to 98%
        self._update_status("Indexing known combos...")
        self._update_progress(0.92)
        await self._init_combos(3, 4)

    def on_key(self) -> None:
        """Handle key press (exit on error)."""
        if self._error:
            self.exit(False)


def check_databases_exist() -> bool:
    """Check if the unified database exists."""
    from mtg_core.config import get_settings

    settings = get_settings()
    return settings.mtg_db_path.exists()


def run_splash_if_needed() -> bool:
    """Run splash screen to check for updates. Returns True if setup succeeded.

    Always runs the splash screen, which will:
    - Check if data needs updating (freshness check against Scryfall API)
    - If data is current, exit immediately
    - If data needs updating, download and rebuild
    """
    app = SplashScreen()
    return app.run() or False
