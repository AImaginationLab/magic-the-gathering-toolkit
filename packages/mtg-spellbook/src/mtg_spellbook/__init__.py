"""MTG Spellbook - Interactive terminal UI for Magic: The Gathering."""

from mtg_spellbook.app import MTGSpellbook


def main() -> None:
    """Run the MTG Spellbook TUI."""
    from mtg_spellbook.splash import run_splash_if_needed

    # Show splash screen and setup databases if needed
    if not run_splash_if_needed():
        # Setup failed or was cancelled
        return

    # Run the main app
    app = MTGSpellbook()
    app.run()


__all__ = ["MTGSpellbook", "main"]
