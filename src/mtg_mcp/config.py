"""Configuration management using pydantic-settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_default_db_path() -> Path:
    """Get default path to AllPrintings.sqlite."""
    return Path(__file__).parent.parent.parent / "resources" / "AllPrintings.sqlite"


def _get_default_scryfall_path() -> Path:
    """Get default path to scryfall.sqlite."""
    return Path(__file__).parent.parent.parent / "resources" / "scryfall.sqlite"


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
