"""Tests for CLI commands."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mtg_mcp.cli.main import cli

runner = CliRunner()


class TestCliHelp:
    """Tests for CLI help and basic functionality."""

    def test_cli_help(self) -> None:
        """CLI should show help when invoked with --help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "MTG CLI" in result.stdout
        assert "card" in result.stdout
        assert "set" in result.stdout
        assert "deck" in result.stdout

    def test_cli_no_args_shows_help(self) -> None:
        """CLI should show help when invoked with no args (exit code 0 or 2 both acceptable)."""
        result = runner.invoke(cli)
        # Typer with no_args_is_help=True returns exit code 0, but some versions return 2
        assert result.exit_code in (0, 2)
        assert "MTG CLI" in result.stdout


class TestCardCommands:
    """Tests for card subcommands."""

    def test_card_help(self) -> None:
        """Card subcommand should show help."""
        result = runner.invoke(cli, ["card", "--help"])
        assert result.exit_code == 0
        assert "search" in result.stdout
        assert "get" in result.stdout
        assert "rulings" in result.stdout
        assert "legality" in result.stdout
        assert "price" in result.stdout
        assert "random" in result.stdout

    def test_card_search(self) -> None:
        """Card search should return results."""
        result = runner.invoke(cli, ["card", "search", "-n", "Lightning Bolt"])
        assert result.exit_code == 0
        assert "Lightning Bolt" in result.stdout or "Found" in result.stdout

    def test_card_search_json(self) -> None:
        """Card search with --json should return valid JSON."""
        result = runner.invoke(cli, ["card", "search", "-n", "Lightning Bolt", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "cards" in data
        assert "count" in data

    def test_card_get(self) -> None:
        """Card get should return card details."""
        result = runner.invoke(cli, ["card", "get", "Lightning Bolt"])
        assert result.exit_code == 0
        assert "Lightning Bolt" in result.stdout

    def test_card_get_json(self) -> None:
        """Card get with --json should return valid JSON."""
        result = runner.invoke(cli, ["card", "get", "Lightning Bolt", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["name"] == "Lightning Bolt"

    def test_card_rulings(self) -> None:
        """Card rulings should return rulings."""
        result = runner.invoke(cli, ["card", "rulings", "Lightning Bolt"])
        assert result.exit_code == 0
        assert "Rulings" in result.stdout or "rulings" in result.stdout.lower()

    def test_card_rulings_json(self) -> None:
        """Card rulings with --json should return valid JSON."""
        result = runner.invoke(cli, ["card", "rulings", "Lightning Bolt", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "card_name" in data
        assert "rulings" in data

    def test_card_legality(self) -> None:
        """Card legality should return format legalities."""
        result = runner.invoke(cli, ["card", "legality", "Lightning Bolt"])
        assert result.exit_code == 0
        assert "Legalities" in result.stdout or "Legal" in result.stdout

    def test_card_legality_json(self) -> None:
        """Card legality with --json should return valid JSON."""
        result = runner.invoke(cli, ["card", "legality", "Lightning Bolt", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "card_name" in data
        assert "legalities" in data

    def test_card_random(self) -> None:
        """Card random should return a random card."""
        result = runner.invoke(cli, ["card", "random"])
        assert result.exit_code == 0
        # Should have some card output (panel with card name)
        assert len(result.stdout) > 10

    def test_card_random_json(self) -> None:
        """Card random with --json should return valid JSON."""
        result = runner.invoke(cli, ["card", "random", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "name" in data

    def test_card_search_by_type(self) -> None:
        """Card search should filter by type."""
        result = runner.invoke(cli, ["card", "search", "-t", "Instant", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["count"] > 0

    def test_card_search_by_colors(self) -> None:
        """Card search should filter by colors."""
        result = runner.invoke(cli, ["card", "search", "-c", "R", "-n", "bolt", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        # Should find red cards with "bolt" in name
        assert isinstance(data["cards"], list)

    def test_card_search_pagination(self) -> None:
        """Card search should support pagination."""
        result = runner.invoke(
            cli, ["card", "search", "-t", "Creature", "--page", "1", "--page-size", "5", "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["cards"]) <= 5
        assert data["page"] == 1


class TestSetCommands:
    """Tests for set subcommands."""

    def test_set_help(self) -> None:
        """Set subcommand should show help."""
        result = runner.invoke(cli, ["set", "--help"])
        assert result.exit_code == 0
        assert "list" in result.stdout
        assert "get" in result.stdout

    def test_set_list(self) -> None:
        """Set list should return sets."""
        result = runner.invoke(cli, ["set", "list"])
        assert result.exit_code == 0
        assert "Found" in result.stdout

    def test_set_list_json(self) -> None:
        """Set list with --json should return valid JSON."""
        result = runner.invoke(cli, ["set", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "sets" in data
        assert "count" in data

    def test_set_list_filter_by_name(self) -> None:
        """Set list should filter by name."""
        result = runner.invoke(cli, ["set", "list", "-n", "Alpha", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        # Should find sets with "Alpha" in name
        assert isinstance(data["sets"], list)

    def test_set_get(self) -> None:
        """Set get should return set details."""
        result = runner.invoke(cli, ["set", "get", "lea"])
        assert result.exit_code == 0
        # Should show Alpha set info
        assert "Alpha" in result.stdout or "lea" in result.stdout.lower()

    def test_set_get_json(self) -> None:
        """Set get with --json should return valid JSON."""
        result = runner.invoke(cli, ["set", "get", "lea", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "name" in data
        assert "code" in data


class TestDeckCommands:
    """Tests for deck subcommands."""

    def test_deck_help(self) -> None:
        """Deck subcommand should show help."""
        result = runner.invoke(cli, ["deck", "--help"])
        assert result.exit_code == 0
        assert "validate" in result.stdout
        assert "curve" in result.stdout
        assert "colors" in result.stdout
        assert "composition" in result.stdout
        assert "price" in result.stdout


class TestStatsCommand:
    """Tests for stats command."""

    def test_stats(self) -> None:
        """Stats should return database statistics."""
        result = runner.invoke(cli, ["stats"])
        assert result.exit_code == 0
        assert "Database Statistics" in result.stdout or "cards" in result.stdout.lower()

    def test_stats_json(self) -> None:
        """Stats with --json should return valid JSON."""
        result = runner.invoke(cli, ["stats", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "mtg_database" in data


class TestCardPrice:
    """Tests for card price command."""

    def test_card_price(self) -> None:
        """Card price should return price info."""
        result = runner.invoke(cli, ["card", "price", "Lightning Bolt"])
        # May fail if Scryfall DB not available
        assert result.exit_code == 0

    def test_card_price_json(self) -> None:
        """Card price with --json should return valid JSON."""
        result = runner.invoke(cli, ["card", "price", "Lightning Bolt", "--json"])
        if result.exit_code == 0:
            data = json.loads(result.stdout)
            assert "card_name" in data
