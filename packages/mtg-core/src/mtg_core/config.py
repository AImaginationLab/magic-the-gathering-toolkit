"""Configuration management using pydantic-settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_workspace_root() -> Path:
    """Find the workspace root by looking for pyproject.toml with workspace config."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        pyproject = parent / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            if "tool.uv.workspace" in content or "magic-the-gathering" in content:
                return parent
    # Fallback to current directory
    return current


def _get_default_db_path() -> Path:
    """Get default path to AllPrintings.sqlite."""
    workspace = _find_workspace_root()
    return workspace / "resources" / "AllPrintings.sqlite"


def _get_default_scryfall_path() -> Path:
    """Get default path to scryfall.sqlite."""
    workspace = _find_workspace_root()
    return workspace / "resources" / "scryfall.sqlite"


def _get_default_user_db_path() -> Path:
    """Get default path to user database."""
    return Path.home() / ".mtg-spellbook" / "user_data.sqlite"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database paths
    mtg_db_path: Path = Field(
        default_factory=_get_default_db_path,
        description="Path to MTGJson AllPrintings.sqlite database",
    )
    scryfall_db_path: Path = Field(
        default_factory=_get_default_scryfall_path,
        description="Path to Scryfall database",
    )
    user_db_path: Path = Field(
        default_factory=_get_default_user_db_path,
        description="Path to user database (decks, collections)",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    # Cache settings
    cache_max_size: int = Field(
        default=1000,
        description="Maximum number of cards to cache",
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        description="Cache TTL in seconds",
    )


# Singleton instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get application settings (cached singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
