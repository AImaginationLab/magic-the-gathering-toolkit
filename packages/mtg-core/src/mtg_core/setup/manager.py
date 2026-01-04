"""Setup manager that orchestrates the full data setup process."""

from __future__ import annotations

import sqlite3
import tempfile
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from mtg_core.setup.builder import DatabaseBuilder
from mtg_core.setup.downloader import DataDownloader
from mtg_core.setup.themes import populate_card_themes


class SetupPhase(str, Enum):
    """Phases of the setup process."""

    CHECKING = "checking"
    DOWNLOADING_CARDS = "downloading_cards"
    DOWNLOADING_SETS = "downloading_sets"
    DOWNLOADING_RULINGS = "downloading_rulings"
    DOWNLOADING_MTGJSON = "downloading_mtgjson"
    BUILDING_DATABASE = "building_database"
    CREATING_INDEXES = "creating_indexes"
    DOWNLOADING_COMBOS = "downloading_combos"
    DOWNLOADING_GAMEPLAY = "downloading_gameplay"
    DETECTING_THEMES = "detecting_themes"
    CACHING_PRICES = "caching_prices"
    COMPLETE = "complete"
    ERROR = "error"
    UP_TO_DATE = "up_to_date"


@dataclass
class SetupProgress:
    """Progress update during setup."""

    phase: SetupPhase
    progress: float  # 0.0 to 1.0
    message: str
    details: str | None = None
    # Track supplementary database status
    combo_db_success: bool | None = None
    gameplay_db_success: bool | None = None
    themes_success: bool | None = None


class SetupManager:
    """Orchestrates the full data setup and update process."""

    def __init__(
        self,
        mtg_db_path: Path,
        combo_db_path: Path,
        gameplay_db_path: Path,
        gameplay_sqlite_path: Path | None = None,
    ) -> None:
        """Initialize setup manager.

        Args:
            mtg_db_path: Path to the main MTG database
            combo_db_path: Path to the combo database
            gameplay_db_path: Path to the gameplay database (DuckDB for 17lands)
            gameplay_sqlite_path: Path to gameplay SQLite (for abilities, themes)
        """
        self.mtg_db_path = mtg_db_path
        self.combo_db_path = combo_db_path
        self.gameplay_db_path = gameplay_db_path
        # Default to same directory as gameplay_db_path but with .sqlite extension
        self.gameplay_sqlite_path = gameplay_sqlite_path or gameplay_db_path.with_suffix(".sqlite")

        self._progress_callback: Callable[[SetupProgress], None] | None = None
        self._current_progress = 0.0
        self._current_message = ""

    def _report(self, progress: float, message: str) -> None:
        """Report progress via callback."""
        self._current_progress = progress
        self._current_message = message
        if self._progress_callback:
            self._progress_callback(
                SetupProgress(
                    phase=SetupPhase.CHECKING,  # Will be refined
                    progress=progress,
                    message=message,
                )
            )

    def _get_stored_update_time(self) -> str | None:
        """Get the stored Scryfall update time from the database meta table."""
        if not self.mtg_db_path.exists():
            return None

        try:
            conn = sqlite3.connect(self.mtg_db_path)
            cursor = conn.cursor()
            result = cursor.execute(
                "SELECT value FROM meta WHERE key = 'scryfall_updated_at'"
            ).fetchone()
            conn.close()
            return result[0] if result else None
        except (sqlite3.Error, IndexError):
            return None

    async def check_needs_update(self) -> tuple[bool, str | None, str | None]:
        """Check if the database needs updating.

        Returns:
            (needs_update, current_version, latest_version)
        """
        downloader = DataDownloader()

        try:
            metadata = await downloader.get_scryfall_bulk_metadata()
            latest_updated_at = metadata.get("default_cards", {}).get("updated_at")

            if not latest_updated_at:
                return True, None, None

            stored_updated_at = self._get_stored_update_time()

            if stored_updated_at is None:
                return True, None, latest_updated_at

            if latest_updated_at > stored_updated_at:
                return True, stored_updated_at, latest_updated_at

            return False, stored_updated_at, latest_updated_at

        except Exception:
            if self.mtg_db_path.exists():
                return False, self._get_stored_update_time(), None
            return True, None, None

    async def run_update(
        self,
        progress_callback: Callable[[SetupProgress], None] | None = None,
        force: bool = False,
    ) -> bool:
        """Run the full update process.

        Args:
            progress_callback: Called with progress updates
            force: If True, update even if data is current

        Returns:
            True if update was performed, False if already up to date
        """
        self._progress_callback = progress_callback

        def report(progress: float, message: str) -> None:
            self._report(progress, message)

        downloader = DataDownloader(progress_callback=report)
        builder = DatabaseBuilder(progress_callback=report)

        try:
            # Check freshness
            report(0.02, "Checking for updates...")

            needs_update, _current, latest = await self.check_needs_update()

            if not needs_update and not force:
                # Main DB is fresh, but still check supplementary DBs
                combo_ok, gameplay_ok, themes_ok = await self._update_supplementary_databases(
                    downloader
                )
                report(1.0, "Data is up to date!")
                if self._progress_callback:
                    self._progress_callback(
                        SetupProgress(
                            phase=SetupPhase.UP_TO_DATE,
                            progress=1.0,
                            message="Data is up to date!",
                            combo_db_success=combo_ok,
                            gameplay_db_success=gameplay_ok,
                            themes_success=themes_ok,
                        )
                    )
                return False

            scryfall_updated_at = latest

            # Create output directory
            self.mtg_db_path.parent.mkdir(parents=True, exist_ok=True)

            # Download and build database
            with tempfile.TemporaryDirectory() as tmpdir:
                tmppath = Path(tmpdir)

                # Download Scryfall data
                cards_json, sets_json, rulings_json = await downloader.download_scryfall_data(
                    tmppath
                )

                # Download MTGJson set metadata
                mtgjson_path = await downloader.download_mtgjson_setlist(tmppath)

                # Build the database
                builder.build_database(
                    self.mtg_db_path,
                    cards_json,
                    sets_json,
                    rulings_json,
                    mtgjson_path,
                    scryfall_updated_at,
                )

            # Update supplementary databases
            combo_ok, gameplay_ok, themes_ok = await self._update_supplementary_databases(
                downloader
            )

            report(1.0, "Update complete!")
            if self._progress_callback:
                self._progress_callback(
                    SetupProgress(
                        phase=SetupPhase.COMPLETE,
                        progress=1.0,
                        message="Update complete!",
                        combo_db_success=combo_ok,
                        gameplay_db_success=gameplay_ok,
                        themes_success=themes_ok,
                    )
                )
            return True

        except Exception as e:
            if self._progress_callback:
                self._progress_callback(
                    SetupProgress(
                        phase=SetupPhase.ERROR,
                        progress=self._current_progress,
                        message=f"Update failed: {e}",
                        details=str(e),
                    )
                )
            raise

    async def _update_supplementary_databases(
        self, downloader: DataDownloader
    ) -> tuple[bool, bool, bool]:
        """Update combo and gameplay databases if needed.

        Returns:
            Tuple of (combo_success, gameplay_success, themes_success)
        """
        # Ensure directories exist
        self.combo_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.gameplay_db_path.parent.mkdir(parents=True, exist_ok=True)

        combo_success = False
        gameplay_success = False
        themes_success = False

        # Update combo database
        try:
            self._report(0.88, "Downloading combo database...")
            await downloader.download_combo_database(self.combo_db_path)
            combo_success = True
            self._report(0.90, "Combo database ready")
        except Exception as e:
            self._report(0.90, f"Combo database unavailable: {e!s:.50}")

        # Update gameplay database
        try:
            self._report(0.92, "Downloading gameplay stats...")
            await downloader.download_gameplay_database(self.gameplay_db_path)
            gameplay_success = True
            self._report(0.94, "Gameplay stats ready")
        except Exception as e:
            self._report(0.94, f"Gameplay stats unavailable: {e!s:.50}")

        # Populate card themes from oracle text
        try:
            self._report(0.95, "Detecting card themes...")
            populate_card_themes(
                self.mtg_db_path,
                self.gameplay_sqlite_path,
                progress_callback=lambda p, m: self._report(0.95 + p * 0.04, m),
            )
            themes_success = True
            self._report(0.99, "Card themes indexed")
        except Exception as e:
            self._report(0.99, f"Theme detection skipped: {e!s:.50}")

        return combo_success, gameplay_success, themes_success

    async def run_update_streaming(self, force: bool = False) -> AsyncIterator[SetupProgress]:
        """Run update and yield progress updates as an async iterator.

        This is useful for SSE endpoints.
        """
        updates: list[SetupProgress] = []

        def collect_progress(progress: SetupProgress) -> None:
            updates.append(progress)

        # Start update in background and yield updates
        import asyncio

        update_task = asyncio.create_task(
            self.run_update(progress_callback=collect_progress, force=force)
        )

        last_yielded = 0
        while not update_task.done():
            # Yield any new updates
            while last_yielded < len(updates):
                yield updates[last_yielded]
                last_yielded += 1
            await asyncio.sleep(0.1)

        # Yield remaining updates
        while last_yielded < len(updates):
            yield updates[last_yielded]
            last_yielded += 1

        # Check for exceptions
        try:
            await update_task
        except Exception as e:
            yield SetupProgress(
                phase=SetupPhase.ERROR,
                progress=0.0,
                message=f"Update failed: {e}",
                details=str(e),
            )
