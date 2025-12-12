"""MTG Spellbook - Interactive terminal UI for Magic: The Gathering."""

from mtg_spellbook.app import MTGSpellbook


def main() -> None:
    """Run the MTG Spellbook TUI."""
    app = MTGSpellbook()
    app.run()


__all__ = ["MTGSpellbook", "main"]
