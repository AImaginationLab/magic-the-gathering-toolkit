"""FastAPI HTTP server for MTG Core."""

from __future__ import annotations

import argparse
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mtg_core.config import get_settings
from mtg_core.data.database import DatabaseManager

from .routes import api_router

logger = logging.getLogger(__name__)

# Default port for the API server
DEFAULT_PORT = 8765


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifespan - initialize and cleanup database."""
    settings = get_settings()
    db_manager = DatabaseManager(settings)

    logger.info("Starting MTG API server...")

    # Try to start the database, but allow server to run without it
    # (needed for initial setup when database doesn't exist yet)
    db_available = False
    try:
        await db_manager.start()
        db_available = True
        logger.info("Database initialized successfully")
    except FileNotFoundError as e:
        logger.warning("Database not available: %s", e)
        logger.info("Server starting in setup mode - only /setup and /health endpoints will work")

    # Store in app state for access in routes
    app.state.db_manager = db_manager if db_available else None
    app.state.db_available = db_available

    yield

    # Cleanup
    logger.info("Shutting down MTG API server...")
    if db_available:
        await db_manager.stop()
        logger.info("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="MTG Core API",
    description="Magic: The Gathering card database and analysis API",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware for Electron app
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


def main() -> None:
    """Run the API server."""
    import uvicorn

    parser = argparse.ArgumentParser(description="MTG Core API Server")
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MTG_API_PORT", DEFAULT_PORT)),
        help=f"Port to listen on (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Logging level (default: info)",
    )

    args = parser.parse_args()

    # Use app object directly instead of string import for PyInstaller compatibility
    # Note: reload=True won't work with direct app reference, but it's a dev-only feature
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=False,  # reload requires string import, disable for bundled builds
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
