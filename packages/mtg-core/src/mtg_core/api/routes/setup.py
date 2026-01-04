"""Database setup and initialization routes."""

from __future__ import annotations

import logging
from enum import Enum

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class SetupPhase(str, Enum):
    """Setup phases for progress tracking."""

    CHECKING = "checking"
    DOWNLOADING_CARDS = "downloading_cards"
    DOWNLOADING_SETS = "downloading_sets"
    DOWNLOADING_RULINGS = "downloading_rulings"
    DOWNLOADING_MTGJSON = "downloading_mtgjson"
    BUILDING_DATABASE = "building_database"
    CREATING_INDEXES = "creating_indexes"
    DOWNLOADING_COMBOS = "downloading_combos"
    DOWNLOADING_GAMEPLAY = "downloading_gameplay"
    CACHING_PRICES = "caching_prices"
    COMPLETE = "complete"
    ERROR = "error"
    UP_TO_DATE = "up_to_date"


class SetupStatus(BaseModel):
    """Status response for setup check."""

    needs_update: bool
    needs_initial_setup: bool = False
    current_version: str | None = None
    latest_version: str | None = None
    mtg_db_exists: bool = False
    combo_db_exists: bool = False
    gameplay_db_exists: bool = False
    user_db_exists: bool = False


class SetupProgress(BaseModel):
    """Progress update during setup."""

    phase: SetupPhase
    progress: float  # 0.0 to 1.0
    message: str
    details: str | None = None
    # Supplementary database status (set on completion)
    combo_db_success: bool | None = None
    gameplay_db_success: bool | None = None
    themes_success: bool | None = None


@router.get("/status")
async def get_setup_status() -> SetupStatus:
    """Check if databases exist and need updating.

    Returns status including whether update is needed and which databases exist.
    If mtg_db_exists is False, the user needs to run initial setup (via mtg-spellbook).
    """
    from mtg_core.config import get_settings

    settings = get_settings()

    # Check database existence
    combo_exists = settings.combo_db_path.exists()
    gameplay_exists = settings.gameplay_db_path.exists()
    user_exists = settings.user_db_path.exists()

    # Check if mtg database exists AND has data (not just an empty file)
    mtg_exists = False
    if settings.mtg_db_path.exists():
        try:
            import sqlite3 as sql

            conn = sql.connect(settings.mtg_db_path)
            cursor = conn.cursor()
            # Check if cards table exists and has rows
            result = cursor.execute("SELECT COUNT(*) FROM cards LIMIT 1").fetchone()
            conn.close()
            mtg_exists = result is not None and result[0] > 0
        except Exception:
            # Table doesn't exist or other error - treat as not existing
            mtg_exists = False

    # If main DB doesn't exist or is empty, needs initial setup
    if not mtg_exists:
        return SetupStatus(
            needs_update=True,
            needs_initial_setup=True,
            mtg_db_exists=False,
            combo_db_exists=combo_exists,
            gameplay_db_exists=gameplay_exists,
            user_db_exists=user_exists,
        )

    # Check freshness against Scryfall API
    try:
        import sqlite3

        import httpx

        # Get local timestamp
        conn = sqlite3.connect(settings.mtg_db_path)
        cursor = conn.cursor()
        result = cursor.execute(
            "SELECT value FROM meta WHERE key = 'scryfall_updated_at'"
        ).fetchone()
        conn.close()
        local_timestamp = result[0] if result else None

        # Get latest from Scryfall
        timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get("https://api.scryfall.com/bulk-data")
            response.raise_for_status()
            data = response.json()

        latest_timestamp = None
        for item in data["data"]:
            if item["type"] == "default_cards":
                latest_timestamp = item["updated_at"]
                break

        if not latest_timestamp:
            # Can't determine, assume current
            return SetupStatus(
                needs_update=False,
                current_version=local_timestamp,
                mtg_db_exists=True,
                combo_db_exists=combo_exists,
                gameplay_db_exists=gameplay_exists,
                user_db_exists=user_exists,
            )

        needs_update = local_timestamp is None or latest_timestamp > local_timestamp

        return SetupStatus(
            needs_update=needs_update,
            current_version=local_timestamp,
            latest_version=latest_timestamp,
            mtg_db_exists=True,
            combo_db_exists=combo_exists,
            gameplay_db_exists=gameplay_exists,
            user_db_exists=user_exists,
        )

    except Exception:
        # Network error - if DB exists, assume OK
        return SetupStatus(
            needs_update=False,
            mtg_db_exists=mtg_exists,
            combo_db_exists=combo_exists,
            gameplay_db_exists=gameplay_exists,
            user_db_exists=user_exists,
        )


@router.post("/ensure-user-db")
async def ensure_user_database() -> dict[str, bool]:
    """Ensure the user database exists with proper schema.

    Creates the user database and all required tables if they don't exist.
    This should be called on app startup before any collection operations.
    """
    from mtg_core.config import get_settings
    from mtg_core.data.database import UserDatabase

    settings = get_settings()

    # Ensure directory exists
    settings.user_db_path.parent.mkdir(parents=True, exist_ok=True)

    # Connect to create/open database (this runs migrations)
    user_db = UserDatabase(settings.user_db_path)
    await user_db.connect()
    await user_db.close()

    return {"success": True}


@router.post("/update")
async def run_update(force: bool = False) -> dict[str, bool | str]:
    """Run the full data update process.

    Downloads the latest Scryfall data, rebuilds the card database,
    and updates supplementary databases (combos, gameplay).

    Args:
        force: If True, run update even if data is current

    Returns:
        {"success": True, "message": "..."} on success
        {"success": False, "error": "..."} on failure
    """
    from mtg_core.config import get_settings
    from mtg_core.setup import SetupManager

    settings = get_settings()

    manager = SetupManager(
        mtg_db_path=settings.mtg_db_path,
        combo_db_path=settings.combo_db_path,
        gameplay_db_path=settings.gameplay_db_path,
    )

    try:
        updated = await manager.run_update(force=force)
        if updated:
            return {"success": True, "message": "Data updated successfully"}
        else:
            return {"success": True, "message": "Data is already up to date"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/init-database")
async def init_database(request: Request) -> dict[str, bool | str]:
    """Initialize the database connection after data has been downloaded.

    This endpoint should be called after /update or /update/stream completes
    when the server was started in setup mode (without existing database).
    It creates the DatabaseManager and makes the database available for queries.

    Returns:
        {"success": True} on success
        {"success": False, "error": "..."} on failure
    """
    from mtg_core.config import get_settings
    from mtg_core.data.database import DatabaseManager

    settings = get_settings()

    # Check if database file now exists
    if not settings.mtg_db_path.exists():
        return {"success": False, "error": "Database file does not exist"}

    # Check if already initialized
    if request.app.state.db_available:
        return {"success": True, "message": "Database already initialized"}

    try:
        db_manager = DatabaseManager(settings)
        await db_manager.start()

        request.app.state.db_manager = db_manager
        request.app.state.db_available = True

        logger.info("Database initialized after setup")
        return {"success": True}
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        return {"success": False, "error": str(e)}


@router.get("/update/stream")
async def run_update_stream(force: bool = False) -> StreamingResponse:
    """Run the full data update with streaming progress via SSE.

    Returns Server-Sent Events with progress updates during the update process.
    Each event is a JSON object with: phase, progress (0-1), message, details.

    Args:
        force: If True, run update even if data is current
    """
    import json
    from collections.abc import AsyncIterator

    from mtg_core.config import get_settings
    from mtg_core.setup import SetupManager

    settings = get_settings()

    manager = SetupManager(
        mtg_db_path=settings.mtg_db_path,
        combo_db_path=settings.combo_db_path,
        gameplay_db_path=settings.gameplay_db_path,
    )

    async def event_generator() -> AsyncIterator[str]:
        async for progress in manager.run_update_streaming(force=force):
            data = {
                "phase": progress.phase.value,
                "progress": progress.progress,
                "message": progress.message,
                "details": progress.details,
                "combo_db_success": progress.combo_db_success,
                "gameplay_db_success": progress.gameplay_db_success,
                "themes_success": progress.themes_success,
            }
            yield f"data: {json.dumps(data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
