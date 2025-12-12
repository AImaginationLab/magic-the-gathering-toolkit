"""MTG Spellbook TUI - Textual-based terminal interface."""

from .app import MTGSpellbook

__all__ = ["MTGSpellbook", "run_app"]


def run_app() -> None:
    """Run the MTG Spellbook TUI app."""
    app = MTGSpellbook()
    app.run()
