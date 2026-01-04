"""Data downloading utilities for Scryfall and other sources."""

from __future__ import annotations

import gzip
import shutil
from collections.abc import Callable
from pathlib import Path

import httpx

# GitHub release configuration for supplementary databases
GITHUB_REPO = "AImaginationLab/magic-the-gathering-toolkit"
GITHUB_RELEASE_TAG = "data-v3"


class DataDownloader:
    """Downloads data files from Scryfall, MTGJson, and GitHub."""

    def __init__(
        self,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> None:
        """Initialize downloader.

        Args:
            progress_callback: Called with (progress 0-1, message) during downloads
        """
        self._progress_callback = progress_callback or (lambda _p, _m: None)
        # Long timeouts for large downloads (350MB+ card data)
        self._timeout = httpx.Timeout(connect=60.0, read=600.0, write=60.0, pool=60.0)

    def _report(self, progress: float, message: str) -> None:
        """Report progress to callback."""
        self._progress_callback(progress, message)

    async def get_scryfall_bulk_metadata(self) -> dict[str, dict[str, str]]:
        """Fetch Scryfall bulk data metadata (URLs and updated_at times)."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
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

    async def get_scryfall_bulk_url(self, bulk_type: str) -> str:
        """Get download URL for a Scryfall bulk data type."""
        metadata = await self.get_scryfall_bulk_metadata()
        if bulk_type not in metadata:
            raise ValueError(f"Bulk data type '{bulk_type}' not found")
        return metadata[bulk_type]["download_uri"]

    async def download_file(
        self,
        url: str,
        dest: Path,
        base_progress: float = 0.0,
        step_progress: float = 1.0,
        message: str | None = None,
    ) -> None:
        """Download a file with progress updates.

        Args:
            url: URL to download
            dest: Destination path
            base_progress: Starting progress value (0-1)
            step_progress: Progress range for this download (0-1)
            message: Status message to show
        """
        if message:
            self._report(base_progress, message)

        async with (
            httpx.AsyncClient(follow_redirects=True, timeout=self._timeout) as client,
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
                        self._report(
                            base_progress + step_progress * dl_progress,
                            message or "Downloading...",
                        )

    async def download_scryfall_data(self, tmpdir: Path) -> tuple[Path, Path, Path]:
        """Download all Scryfall data files.

        Returns (cards_json, sets_json, rulings_json) paths.
        """
        # Get download URLs
        self._report(0.05, "Connecting to Scryfall API...")
        cards_url = await self.get_scryfall_bulk_url("default_cards")
        rulings_url = await self.get_scryfall_bulk_url("rulings")

        # Download cards (largest file - ~350MB)
        cards_json = tmpdir / "default_cards.json"
        await self.download_file(
            cards_url,
            cards_json,
            base_progress=0.08,
            step_progress=0.35,
            message="Downloading 110,000+ cards from Scryfall (~350MB)...",
        )

        # Download sets from API endpoint
        self._report(0.43, "Downloading set information...")
        sets_json = tmpdir / "sets.json"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get("https://api.scryfall.com/sets")
            response.raise_for_status()
            with sets_json.open("w") as f:
                f.write(response.text)
        self._report(0.45, "Set data downloaded")

        # Download rulings
        rulings_json = tmpdir / "rulings.json"
        await self.download_file(
            rulings_url,
            rulings_json,
            base_progress=0.45,
            step_progress=0.05,
            message="Downloading card rulings...",
        )

        return cards_json, sets_json, rulings_json

    async def download_mtgjson_setlist(self, tmpdir: Path) -> Path:
        """Download MTGJson SetList for set metadata."""
        mtgjson_url = "https://mtgjson.com/api/v5/SetList.json"
        mtgjson_path = tmpdir / "SetList.json"
        await self.download_file(
            mtgjson_url,
            mtgjson_path,
            base_progress=0.50,
            step_progress=0.02,
            message="Downloading set metadata...",
        )
        return mtgjson_path

    async def download_combo_database(self, dest_path: Path) -> bool:
        """Download combo database from GitHub releases.

        Returns True if downloaded/updated, False if already current.
        """
        import sqlite3

        self._report(0.88, "Checking combo database...")

        # Check current version
        current_updated_at: str | None = None
        if dest_path.exists():
            try:
                conn = sqlite3.connect(dest_path)
                cursor = conn.cursor()
                result = cursor.execute(
                    "SELECT value FROM metadata WHERE key = 'release_updated_at'"
                ).fetchone()
                conn.close()
                current_updated_at = result[0] if result else None
            except sqlite3.Error:
                pass

        # Check GitHub for release by tag
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{GITHUB_RELEASE_TAG}"
            )
            if response.status_code != 200:
                return False
            release = response.json()

        latest_updated_at = release.get("published_at")
        if current_updated_at and latest_updated_at <= current_updated_at:
            self._report(0.90, "Combo database is up to date")
            return False

        # Find the combos.sqlite.gz asset
        assets = release.get("assets", [])
        combo_asset = next((a for a in assets if a["name"] == "combos.sqlite.gz"), None)
        if not combo_asset:
            return False

        # Download and decompress
        self._report(0.89, "Downloading combo database...")
        download_url = combo_asset["browser_download_url"]
        gz_path = dest_path.with_suffix(".sqlite.gz")

        await self.download_file(download_url, gz_path, 0.89, 0.05)

        # Decompress
        self._report(0.94, "Decompressing combo database...")
        with gzip.open(gz_path, "rb") as f_in, dest_path.open("wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        gz_path.unlink()

        # Store release timestamp
        conn = sqlite3.connect(dest_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ("release_updated_at", latest_updated_at),
        )
        conn.commit()
        conn.close()

        self._report(0.95, "Combo database updated")
        return True

    async def download_gameplay_database(self, dest_path: Path) -> bool:
        """Download gameplay (17Lands) database from GitHub releases.

        Returns True if downloaded/updated, False if already current.
        """
        self._report(0.95, "Checking gameplay database...")

        # Check current version
        current_updated_at: str | None = None
        if dest_path.exists():
            try:
                import duckdb

                conn = duckdb.connect(str(dest_path), read_only=True)
                result = conn.execute(
                    "SELECT value FROM metadata WHERE key = 'release_updated_at'"
                ).fetchone()
                conn.close()
                current_updated_at = result[0] if result else None
            except Exception:
                pass

        # Check GitHub for release by tag (same repo as combo database)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{GITHUB_RELEASE_TAG}"
            )
            if response.status_code != 200:
                return False
            release = response.json()

        latest_updated_at = release.get("published_at")
        if current_updated_at and latest_updated_at <= current_updated_at:
            self._report(0.97, "Gameplay database is up to date")
            return False

        # Find the gameplay.duckdb.gz asset
        assets = release.get("assets", [])
        gameplay_asset = next((a for a in assets if a["name"] == "gameplay.duckdb.gz"), None)
        if not gameplay_asset:
            return False

        # Download and decompress
        self._report(0.96, "Downloading gameplay database...")
        download_url = gameplay_asset["browser_download_url"]
        gz_path = dest_path.with_suffix(".duckdb.gz")

        await self.download_file(download_url, gz_path, 0.96, 0.02)

        # Decompress
        self._report(0.98, "Decompressing gameplay database...")
        with gzip.open(gz_path, "rb") as f_in, dest_path.open("wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        gz_path.unlink()

        # Store release timestamp
        import duckdb

        conn = duckdb.connect(str(dest_path))
        conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ("release_updated_at", latest_updated_at),
        )
        conn.close()

        self._report(0.99, "Gameplay database updated")
        return True
