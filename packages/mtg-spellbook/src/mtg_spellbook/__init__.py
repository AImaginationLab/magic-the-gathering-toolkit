"""MTG Spellbook - Interactive terminal UI for Magic: The Gathering."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_spellbook.app import MTGSpellbook as MTGSpellbookType


def _print_status(msg: str) -> None:
    """Print a status message, overwriting the previous line."""
    print(f"\r  {msg:<40}", end="", flush=True)


def main() -> None:
    """Run the MTG Spellbook TUI."""
    # Show loading progress before heavy imports (sklearn takes ~10s on first run)
    print()  # Start with newline for spacing

    _print_status("Loading card analysis engine, this may take a minute...")
    import mtg_core.tools.recommendations  # noqa: F401 - sklearn lives here

    _print_status("Loading UI framework...")
    import textual  # noqa: F401

    _print_status("Initializing app...")
    from mtg_spellbook.app import MTGSpellbook
    from mtg_spellbook.splash import run_splash_if_needed

    # Clear the loading message
    print("\r" + " " * 45 + "\r", end="", flush=True)

    # Show splash screen and setup databases if needed
    if not run_splash_if_needed():
        # Setup failed or was cancelled
        return

    # Run the main app
    app = MTGSpellbook()
    app.run()


def get_app_class() -> type[MTGSpellbookType]:
    """Get the MTGSpellbook class (for external imports)."""
    from mtg_spellbook.app import MTGSpellbook

    return MTGSpellbook


__all__ = ["get_app_class", "main"]
