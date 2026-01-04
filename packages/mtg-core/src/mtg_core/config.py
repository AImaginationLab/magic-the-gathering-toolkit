"""Configuration management using pydantic-settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_default_db_path() -> Path:
    """Get default path to unified mtg.sqlite database."""
    return Path.home() / ".mtg-spellbook" / "mtg.sqlite"


def _get_default_user_db_path() -> Path:
    """Get default path to user database."""
    return Path.home() / ".mtg-spellbook" / "user_data.sqlite"


def _get_default_combo_db_path() -> Path:
    """Get default path to combo database."""
    return Path.home() / ".mtg-spellbook" / "combos.sqlite"


def _get_default_gameplay_db_path() -> Path:
    """Get default path to gameplay database (17lands stats)."""
    return Path.home() / ".mtg-spellbook" / "gameplay.duckdb"


def _get_default_gameplay_sqlite_path() -> Path:
    """Get default path to gameplay SQLite database (abilities, themes)."""
    return Path.home() / ".mtg-spellbook" / "gameplay.sqlite"


def _get_default_image_cache_path() -> Path:
    """Get default path to image cache directory."""
    return Path.home() / ".cache" / "mtg-spellbook" / "images"


def _get_default_data_cache_path() -> Path:
    """Get default path to data cache directory."""
    return Path.home() / ".cache" / "mtg-spellbook" / "data"


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
        description="Path to unified MTG database (mtg.sqlite)",
    )
    user_db_path: Path = Field(
        default_factory=_get_default_user_db_path,
        description="Path to user database (decks, collections)",
    )
    combo_db_path: Path = Field(
        default_factory=_get_default_combo_db_path,
        description="Path to combo database",
    )
    gameplay_db_path: Path = Field(
        default_factory=_get_default_gameplay_db_path,
        description="Path to gameplay database (17lands Limited stats)",
    )
    gameplay_sqlite_path: Path = Field(
        default_factory=_get_default_gameplay_sqlite_path,
        description="Path to gameplay SQLite database (abilities, themes)",
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

    # Query performance logging
    log_slow_queries: bool = Field(
        default=False,
        description="Enable logging of slow database queries",
    )
    slow_query_threshold_ms: int = Field(
        default=100,
        description="Threshold in milliseconds for slow query warnings",
    )

    # Connection pooling
    db_max_connections: int = Field(
        default=50,
        description="Maximum concurrent database operations (semaphore limit)",
    )

    # Image cache settings
    image_cache_dir: Path = Field(
        default_factory=_get_default_image_cache_path,
        description="Directory for cached card images",
    )
    image_cache_max_mb: int = Field(
        default=1024,
        description="Maximum disk cache size for card images in MB (default 1GB, ~1000 cards)",
    )
    image_memory_cache_count: int = Field(
        default=20,
        description="Maximum images to keep in memory (RAM) for fast access",
    )

    # Data cache settings (printings, synergies, etc.)
    data_cache_dir: Path = Field(
        default_factory=_get_default_data_cache_path,
        description="Directory for cached data (printings, synergies)",
    )
    data_cache_max_mb: int = Field(
        default=100,
        description="Maximum disk cache size for data in MB",
    )


# Singleton instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get application settings (cached singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
