# Magic: The Gathering Toolkit

Magic: The Gathering Toolkit is a set of core packages, terminal UI, and MCP server for exploring and analyzing your cards and decks.  Search 33,000+ cards, browse artwork, check prices, save and maintain decks, explore synergies and more, powered by local SQLite databases.

## Packages

This is a UV workspace with three packages:

| Package | Description |
|---------|-------------|
| [mtg-core](packages/mtg-core/) | Shared library: database access, card models, tools |
| [mtg-mcp](packages/mtg-mcp/) | MCP server for Claude Desktop integration |
| [mtg-spellbook](packages/mtg-spellbook/) | Interactive terminal UI (Textual) |

## Quick Start

```bash
# Clone and install
git clone https://github.com/AImaginationLab/magic-the-gathering-toolkit.git
cd magic-the-gathering-toolkit
uv sync

# Download databases (required)
uv run create-datasources

# Launch the TUI
uv run mtg-spellbook

# Or start the MCP server
uv run mtg-mcp
```

## MTG Spellbook (TUI)

A themed terminal interface for card lookups, artwork browsing, and synergies, and deck analysis.

```bash
uv run mtg-spellbook
```

**Features:**
- Search cards with 15+ filters (name, colors, type, CMC, keywords, format, rarity, set)
- Browse high-resolution card artwork
- Check prices and printings
- Analyze deck composition, mana curve, and color balance
- Find card synergies and combos
- Keyboard shortcuts for quick navigation

## MCP Server

Integrate with Claude Desktop or any MCP-compatible client for AI-powered assistance.

```bash
uv run mtg-mcp
```

Add to Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "mtg": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/magic-the-gathering-toolkit", "mtg-mcp"]
      
    }
  }
}
```

Then ask things like:
- "Build me a budget Mono-Red Commander deck under $50"
- "What are the best counterspells in Modern?"
- "Find cards that synergize with Rhystic Study"
- "Is this deck legal in Pioneer?" (paste your decklist)

## Available Tools

### Card Lookup
| Tool | Description |
|------|-------------|
| `search_cards` | Filter by name, colors, type, CMC, keywords, format, rarity, set |
| `get_card` | Full card details with images and prices |
| `get_card_rulings` | Official rulings from Gatherer |
| `get_card_legalities` | Format legality (Standard, Modern, Commander, etc.) |
| `get_random_card` | Discover something new |

### Images & Prices
| Tool | Description |
|------|-------------|
| `get_card_image` | Image URLs in multiple sizes |
| `get_card_printings` | Every printing with artwork and prices |
| `get_card_price` | Current USD/EUR prices |
| `search_by_price` | Find cards in a price range |

### Deck Analysis
| Tool | Description |
|------|-------------|
| `validate_deck` | Check format legality, deck size, copy limits |
| `analyze_mana_curve` | CMC distribution and average |
| `analyze_colors` | Color balance and recommended land ratios |
| `analyze_deck_composition` | Creature/spell/land breakdown |
| `analyze_deck_price` | Total cost and expensive cards |

### Synergy & Strategy
| Tool | Description |
|------|-------------|
| `find_synergies` | Find cards that synergize with a given card |
| `detect_combos` | Identify known combos in a deck or for a card |
| `suggest_cards` | Recommend cards based on deck theme/strategy |

### Sets
| Tool | Description |
|------|-------------|
| `get_sets` | List and search all sets |
| `get_set` | Set details (release date, card count, type) |
| `get_database_stats` | Database version and statistics |

## Data Sources

| Database | Source | Contents |
|----------|--------|----------|
| `AllPrintings.sqlite` | [MTGJson](https://mtgjson.com/downloads/all-files/) | Cards, rules, legalities (required) |
| `scryfall.sqlite` | [Scryfall](https://scryfall.com/docs/api/bulk-data) | Images, prices, purchase links (optional) |

Place databases in `resources/` or set paths via environment variables:

```bash
MTG_DB_PATH=resources/AllPrintings.sqlite
SCRYFALL_DB_PATH=resources/scryfall.sqlite
```

## Development

```bash
uv sync --all-extras    # Install dev dependencies
uv run pytest           # Run tests (78 tests)
uv run ruff check .     # Lint
uv run mypy .           # Type check
```

## Project Structure

```
magic-the-gathering-mcp/
├── packages/
│   ├── mtg-core/           # Shared library
│   ├── mtg-mcp/            # MCP server
│   └── mtg-spellbook/      # Terminal UI
├── resources/              # SQLite databases
├── tests/                  # Test suite
└── pyproject.toml          # Workspace config
```

## License

MIT

## Copyright

All rights to Magic: The Gathering belong to Wizards of the Coast, a subsidiary of Hasbro, Inc.
