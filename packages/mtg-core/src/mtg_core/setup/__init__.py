"""Data setup and update module.

Handles downloading Scryfall data, building the card database,
and updating supplementary databases (combos, gameplay).
"""

from mtg_core.setup.builder import DatabaseBuilder
from mtg_core.setup.downloader import DataDownloader
from mtg_core.setup.manager import SetupManager, SetupPhase, SetupProgress

__all__ = [
    "DataDownloader",
    "DatabaseBuilder",
    "SetupManager",
    "SetupPhase",
    "SetupProgress",
]
