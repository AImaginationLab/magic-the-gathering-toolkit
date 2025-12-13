# MTG MCP Server

MCP (Model Context Protocol) server for Magic: The Gathering. Integrates with Claude Desktop and other MCP-compatible clients to provide AI-powered card lookup, deck building assistance, and strategy advice.

## Installation

```bash
# As part of the workspace
uv sync
```

## Usage

### Start the Server

```bash
uv run mtg-mcp
```

### Claude Desktop Configuration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

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

### Example Prompts

Once configured, you can ask Claude:

- "Search for red creatures with flying that cost 3 or less mana"
- "What are the rulings for Doubling Season?"
- "Build me a budget Mono-Red Commander deck under $50"
- "Find cards that synergize with Rhystic Study"
- "Is this deck legal in Modern?" (paste your decklist)
- "What combos can I make with Thassa's Oracle?"

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

## Architecture

Built with [FastMCP](https://github.com/jlowin/fastmcp) for clean, decorator-based tool registration:

```
src/mtg_mcp_server/
├── server.py       # FastMCP server with lifespan management
├── context.py      # Application context (database connections)
└── routes/         # Tool registrations
    ├── cards.py    # Card lookup tools
    ├── deck.py     # Deck analysis tools
    ├── synergy.py  # Synergy/combo tools
    ├── sets.py     # Set tools
    ├── images.py   # Image/price tools
    ├── resources.py # MCP resources
    └── prompts.py  # MCP prompts
```

## Dependencies

- `mtg-core` - Shared library (database, models, tools)
- `mcp` - Model Context Protocol SDK
