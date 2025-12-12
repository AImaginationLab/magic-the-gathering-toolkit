"""CLI command modules."""

from mtg_mcp.cli.commands.card import card_app
from mtg_mcp.cli.commands.deck import deck_app
from mtg_mcp.cli.commands.set import set_app
from mtg_mcp.cli.commands.synergy import synergy_app

__all__ = ["card_app", "deck_app", "set_app", "synergy_app"]
