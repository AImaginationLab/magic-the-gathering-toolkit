"""Splash screen with database setup for first-time users."""

from __future__ import annotations

import asyncio
import contextlib
import random
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Center, Vertical
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

# ASCII art splash screen - colorful MTG-themed with mana & card types
SPELLBOOK_ART = """
[#fffcd6]  ☀[/]    [#aad5f5]💧[/]    [#cbc2d9]💀[/]    [#e86a58]🔥[/]    [#7bc96a]🌲[/]             [#fffcd6]☀[/]    [#aad5f5]💧[/]    [#cbc2d9]💀[/]    [#e86a58]🔥[/]    [#7bc96a]🌲[/]

                    [bold #c9a227]╔═══════════════════════════════════════╗[/]
                    [bold #c9a227]║[/]  [bold #e6c84a]✦  M T G    S P E L L B O O K  ✦[/]  [bold #c9a227]║[/]
                    [bold #c9a227]╚═══════════════════════════════════════╝[/]

    [#aad5f5]╭────────╮[/]                                            [#e86a58]╭────────╮[/]
    [#aad5f5]│[/][bold #aad5f5]INSTANT [/][#aad5f5]│[/]         [bold #c9a227]┏━━━━━━━━━━━━━┓[/]         [#e86a58]│[/][bold #e86a58]SORCERY [/][#e86a58]│[/]
    [#aad5f5]│[/]   [bold #aad5f5]⚡[/]    [#aad5f5]│[/]         [bold #c9a227]┃[/]  [#e6c84a]◈[/] [bold]DECK[/] [#e6c84a]◈[/]  [bold #c9a227]┃[/]         [#e86a58]│[/]   [bold #e86a58]🔥[/]    [#e86a58]│[/]
    [#aad5f5]╰────────╯[/]         [bold #c9a227]┃[/]   33,000+   [bold #c9a227]┃[/]         [#e86a58]╰────────╯[/]
                              [bold #c9a227]┃[/]    [dim]CARDS[/]    [bold #c9a227]┃[/]
    [#7bc96a]╭────────╮[/]         [bold #c9a227]┗━━━━━━━━━━━━━┛[/]         [#cbc2d9]╭────────╮[/]
    [#7bc96a]│[/][bold #7bc96a]CREATURE[/][#7bc96a]│[/]                                      [#cbc2d9]│[/][bold #cbc2d9]ENCHANT [/][#cbc2d9]│[/]
    [#7bc96a]│[/]   [bold #7bc96a]⚔[/]    [#7bc96a]│[/]    [#fffcd6]◯[/]   [#aad5f5]◯[/]   [#cbc2d9]◯[/]   [#e86a58]◯[/]   [#7bc96a]◯[/]    [#cbc2d9]│[/]   [bold #cbc2d9]✨[/]    [#cbc2d9]│[/]
    [#7bc96a]╰────────╯[/]    [dim #fffcd6]W[/]   [dim #aad5f5]U[/]   [dim #cbc2d9]B[/]   [dim #e86a58]R[/]   [dim #7bc96a]G[/]    [#cbc2d9]╰────────╯[/]

               [#c9a227]⚝[/]   Tapping into the multiverse...   [#c9a227]⚝[/]
                  [#7bc96a]✧[/]  [#e86a58]✧[/]  [#c9a227]✧[/]  [#aad5f5]✧[/]  [#fffcd6]✧[/]  [#cbc2d9]✧[/]  [#7bc96a]✧[/]
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
        max-width: 50;
        height: auto;
        align: center middle;
        margin-top: 2;
    }

    #status-message {
        text-align: center;
        width: 100%;
        color: $text;
        margin-bottom: 1;
    }

    #progress-bar {
        width: 100%;
        height: 1;
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
        self._last_message_time: float = 0
        self._message_interval: float = 2.5  # Seconds between message changes

    def compose(self) -> ComposeResult:
        with Vertical(id="splash-container"):
            yield Static(SPELLBOOK_ART, id="spellbook-art")
            with Center(), Vertical(id="status-container"):
                yield Label("Preparing your spellbook...", id="status-message")
                yield ProgressBar(id="progress-bar", total=100, show_eta=False)
                yield Label("", id="error-message")

    def on_mount(self) -> None:
        """Start the setup process."""
        # Initialize progress bar
        bar = self.query_one("#progress-bar", ProgressBar)
        bar.update(total=100, progress=0)
        self.run_setup()

    def _get_random_message(self) -> str:
        """Get a random loading message."""
        return random.choice(LOADING_MESSAGES)

    def _update_status(self, message: str) -> None:
        """Update the status message."""
        status = self.query_one("#status-message", Label)
        status.update(message)

    def _maybe_update_cheeky_message(self) -> None:
        """Update to a cheeky message if enough time has passed."""
        import time

        now = time.time()
        if now - self._last_message_time >= self._message_interval:
            self._update_status(self._get_random_message())
            self._last_message_time = now

    def _update_progress(self, progress: float) -> None:
        """Update progress bar (0.0 to 1.0)."""
        bar = self.query_one("#progress-bar", ProgressBar)
        bar.update(progress=progress * 100)

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
        scryfall_db = settings.scryfall_db_path

        import time

        self._last_message_time = time.time()

        try:
            # Phase 1: Check what needs to be downloaded
            self._update_status("Checking for database files...")
            self._update_progress(0.02)
            await asyncio.sleep(1.0)

            need_mtgjson = not mtg_db.exists()
            need_scryfall = not scryfall_db.exists()

            if not need_mtgjson and not need_scryfall:
                # Shouldn't happen, but handle gracefully
                self._update_status("Databases found! Starting app...")
                self._update_progress(1.0)
                await asyncio.sleep(0.5)
                self._setup_complete = True
                self.exit(True)
                return

            # Create output directory
            output_dir = mtg_db.parent
            output_dir.mkdir(parents=True, exist_ok=True)

            total_steps = (1 if need_mtgjson else 0) + (1 if need_scryfall else 0) + 1
            current_step = 0

            # Phase 2: Download MTGJson if needed
            if need_mtgjson:
                await self._download_mtgjson(output_dir, current_step, total_steps)
                current_step += 1

            # Phase 3: Download Scryfall if needed
            if need_scryfall:
                await self._download_scryfall(output_dir, current_step, total_steps)
                current_step += 1

            # Phase 4: Initialize combo database
            await self._init_combos(current_step, total_steps)

            # Done!
            self._update_status("[bold green]Setup complete! Opening Spellbook...[/]")
            self._update_progress(1.0)
            await asyncio.sleep(1.0)
            self._setup_complete = True
            self.exit(True)

        except Exception as e:
            self._show_error(f"Setup failed: {e}")
            self._update_status("[red]Press any key to exit...[/]")
            self._error = str(e)

    async def _download_mtgjson(
        self, output_dir: Path, current_step: int, total_steps: int
    ) -> None:
        """Download MTGJson database."""
        import gzip
        import tempfile

        import httpx

        base_progress = current_step / total_steps
        step_progress = 1 / total_steps

        self._update_status(self._get_random_message())
        self._update_progress(base_progress + step_progress * 0.1)
        await asyncio.sleep(0.3)

        url = "https://mtgjson.com/api/v5/AllPrintings.sqlite.gz"
        output_file = output_dir / "AllPrintings.sqlite"

        # Download
        self._update_status("Downloading MTGJson card database...")
        self._update_progress(base_progress + step_progress * 0.15)

        with tempfile.NamedTemporaryFile(suffix=".sqlite.gz", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)
            async with (
                httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client,
                client.stream("GET", url) as response,
            ):
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))
                downloaded = 0

                with tmp_path.open("wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            dl_progress = downloaded / total
                            self._update_progress(
                                base_progress + step_progress * (0.15 + 0.5 * dl_progress)
                            )
                        # Show cheeky messages during download (time-based)
                        self._maybe_update_cheeky_message()

            # Extract
            self._maybe_update_cheeky_message()
            self._update_progress(base_progress + step_progress * 0.7)

            with gzip.open(tmp_path, "rb") as f_in, output_file.open("wb") as f_out:
                while chunk := f_in.read(65536):
                    f_out.write(chunk)

        finally:
            tmp_path.unlink(missing_ok=True)

        # Create indexes
        self._update_status("Creating search indexes...")
        self._update_progress(base_progress + step_progress * 0.85)
        await asyncio.to_thread(self._create_indexes, output_file)

        self._update_status(self._get_random_message())
        self._update_progress(base_progress + step_progress)

    def _create_indexes(self, db_path: Path) -> None:
        """Create database indexes (runs in thread)."""
        import sqlite3

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        indexes = [
            ("idx_cards_name", "cards", "name"),
            ("idx_cards_type", "cards", "type"),
            ("idx_cards_artist", "cards", "artist"),
            ("idx_cards_setCode", "cards", "setCode"),
            ("idx_cardLegalities_uuid", "cardLegalities", "uuid"),
        ]

        for idx_name, table, column in indexes:
            with contextlib.suppress(sqlite3.OperationalError):
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")

        conn.commit()
        conn.close()

    async def _download_scryfall(
        self, output_dir: Path, current_step: int, total_steps: int
    ) -> None:
        """Download Scryfall database."""
        import tempfile

        import httpx

        base_progress = current_step / total_steps
        step_progress = 1 / total_steps

        self._update_status(self._get_random_message())
        self._update_progress(base_progress + step_progress * 0.1)

        # Get download URL
        timeout = httpx.Timeout(connect=30.0, read=60.0, write=30.0, pool=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get("https://api.scryfall.com/bulk-data")
            response.raise_for_status()
            data = response.json()

        download_url = None
        for item in data["data"]:
            if item["type"] == "unique_artwork":
                download_url = item["download_uri"]
                break

        if not download_url:
            raise ValueError("Could not find Scryfall download URL")

        # Download JSON
        self._update_status("Downloading Scryfall image database...")
        self._update_progress(base_progress + step_progress * 0.15)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)
            async with (
                httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client,
                client.stream("GET", download_url) as response,
            ):
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))
                downloaded = 0

                with tmp_path.open("wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            dl_progress = downloaded / total
                            self._update_progress(
                                base_progress + step_progress * (0.15 + 0.5 * dl_progress)
                            )
                        # Show cheeky messages during download (time-based)
                        self._maybe_update_cheeky_message()

            # Convert to SQLite
            self._update_status("Converting to optimized format...")
            self._update_progress(base_progress + step_progress * 0.7)

            output_file = output_dir / "scryfall.sqlite"
            await asyncio.to_thread(self._create_scryfall_db, tmp_path, output_file)

        finally:
            tmp_path.unlink(missing_ok=True)

        self._update_status(self._get_random_message())
        self._update_progress(base_progress + step_progress)

    def _create_scryfall_db(self, json_path: Path, db_path: Path) -> None:
        """Create Scryfall SQLite database (runs in thread)."""
        import json
        import sqlite3

        db_path.unlink(missing_ok=True)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Schema must match what ScryfallDatabase._row_to_card_image expects
        cursor.execute("""
            CREATE TABLE cards (
                scryfall_id TEXT PRIMARY KEY,
                oracle_id TEXT,
                name TEXT NOT NULL,
                set_code TEXT,
                collector_number TEXT,
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
                image_status TEXT,
                highres_image INTEGER,
                border_color TEXT,
                frame TEXT,
                full_art INTEGER,
                art_priority INTEGER DEFAULT 2,
                games TEXT,
                finishes TEXT
            )
        """)

        cursor.execute("CREATE INDEX idx_cards_name ON cards(name)")
        cursor.execute("CREATE INDEX idx_cards_oracle_id ON cards(oracle_id)")

        with json_path.open() as f:
            cards = json.load(f)

        for card in cards:
            images = card.get("image_uris", {})
            prices = card.get("prices", {})
            purchase = card.get("purchase_uris", {})
            related = card.get("related_uris", {})

            def price_to_cents(p: str | None) -> int | None:
                if p is None:
                    return None
                try:
                    return int(float(p) * 100)
                except (ValueError, TypeError):
                    return None

            art_priority = 2
            if card.get("border_color") == "borderless":
                art_priority = 0
            elif card.get("full_art"):
                art_priority = 1

            cursor.execute(
                """
                INSERT OR REPLACE INTO cards VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    card.get("id"),
                    card.get("oracle_id"),
                    card.get("name"),
                    card.get("set"),
                    card.get("collector_number"),
                    images.get("small"),
                    images.get("normal"),
                    images.get("large"),
                    images.get("png"),
                    images.get("art_crop"),
                    images.get("border_crop"),
                    price_to_cents(prices.get("usd")),
                    price_to_cents(prices.get("usd_foil")),
                    price_to_cents(prices.get("eur")),
                    price_to_cents(prices.get("eur_foil")),
                    purchase.get("tcgplayer"),
                    purchase.get("cardmarket"),
                    purchase.get("cardhoarder"),
                    related.get("edhrec"),
                    related.get("gatherer"),
                    card.get("illustration_id"),
                    card.get("image_status"),
                    1 if card.get("highres_image") else 0,
                    card.get("border_color"),
                    card.get("frame"),
                    1 if card.get("full_art") else 0,
                    art_priority,
                    json.dumps(card.get("games", [])),
                    json.dumps(card.get("finishes", [])),
                ),
            )

        conn.commit()
        conn.close()

    async def _init_combos(self, current_step: int, total_steps: int) -> None:
        """Initialize combo database."""
        from mtg_core.config import get_settings
        from mtg_core.data.database.combos import ComboDatabase
        from mtg_core.tools.synergy.constants import KNOWN_COMBOS

        base_progress = current_step / total_steps
        step_progress = 1 / total_steps

        self._update_status("Indexing known combos...")
        self._update_progress(base_progress + step_progress * 0.3)

        settings = get_settings()
        db_path = settings.combo_db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

        combo_db = ComboDatabase(db_path)
        await combo_db.connect()

        try:
            await combo_db.import_from_legacy_format(KNOWN_COMBOS)
        finally:
            await combo_db.close()

        self._update_status(self._get_random_message())
        self._update_progress(base_progress + step_progress)

    def on_key(self) -> None:
        """Handle key press (exit on error)."""
        if self._error:
            self.exit(False)


def check_databases_exist() -> bool:
    """Check if required databases exist."""
    from mtg_core.config import get_settings

    settings = get_settings()
    return settings.mtg_db_path.exists() and settings.scryfall_db_path.exists()


def run_splash_if_needed() -> bool:
    """Run splash screen if databases don't exist. Returns True if setup succeeded."""
    if check_databases_exist():
        return True

    app = SplashScreen()
    return app.run() or False
