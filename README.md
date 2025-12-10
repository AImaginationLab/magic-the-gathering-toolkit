# Magic: The Gathering MCP Server

An MCP (Model Context Protocol) server for Magic: The Gathering. Provides card lookup, deck building assistance, pricing, and more using local data from [MTGJson](https://mtgjson.com) and [Scryfall](https://scryfall.com).

## Features

- **Card Search**: Find cards by name, color, type, mana cost, keywords, format legality, and more
- **Card Details**: Comprehensive card information with images and prices
- **Pricing**: Current USD/EUR prices from TCGPlayer and Cardmarket
- **Rulings**: Official card rulings
- **Format Legality**: Check legality in Standard, Modern, Commander, etc.
- **Set Information**: Browse all MTG sets
- **Resources**: Browse cards, sets, and rulings via `mtg://` URIs
- **Prompts**: Pre-built templates for deck building, card analysis, and strategy

## Data Sources

This server uses two offline SQLite databases:

| Database | Source | Size | Contents |
|----------|--------|------|----------|
| `AllPrintings.sqlite` | [MTGJson](https://mtgjson.com) | ~500MB | 33,000+ unique cards, rules, legalities |
| `scryfall.sqlite` | [Scryfall](https://scryfall.com) | ~75MB | Card images, prices, purchase links |

## Setup

### 1. Clone the repository

```bash
git clone git@github.com:AImaginationLab/magic-the-gathering-mcp.git
cd magic-the-gathering-mcp
```

### 2. Download the databases

```bash
mkdir -p resources
```

**Required:** Download `AllPrintings.sqlite` from MTGJson:
- https://mtgjson.com/downloads/all-files/

**Optional (for images/prices):** Create Scryfall database:
- Download `unique-artwork` from https://scryfall.com/docs/api/bulk-data
- Run the import script to create `scryfall.sqlite`

```
resources/
├── AllPrintings.sqlite
└── scryfall.sqlite  (optional)
```

### 3. Configure environment

```bash
cp .env.example .env
```

### 4. Install

```bash
uv sync
```

For development tools (ruff, mypy, pytest):

```bash
uv sync --all-extras
```

## Usage

### Run the server

```bash
mtg-mcp
```

### Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mtg": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/magic-the-gathering-mcp", "mtg-mcp"]
    }
  }
}
```

## Tools

### Card Tools

| Tool | Description |
|------|-------------|
| `search_cards` | Search with filters (name, color, type, keywords, format, etc.) |
| `get_card` | Detailed card info with images, prices, purchase links |
| `get_card_rulings` | Official rulings |
| `get_card_legalities` | Format legalities |
| `get_random_card` | Random card for discovery |

### Image & Price Tools

| Tool | Description |
|------|-------------|
| `get_card_image` | Image URLs and pricing for a card |
| `get_card_printings` | All printings with images and prices |
| `get_card_price` | Current prices |
| `search_by_price` | Find cards in a price range |

### Set Tools

| Tool | Description |
|------|-------------|
| `get_sets` | List and search sets |
| `get_set` | Set details |
| `get_database_stats` | Database version and counts |

## Resources

Browse data via URI templates:

| URI | Description |
|-----|-------------|
| `mtg://cards/{name}` | Card details |
| `mtg://sets/{code}` | Set details |
| `mtg://rulings/{name}` | Card rulings |
| `mtg://stats` | Database statistics |

## Prompts

Pre-built templates for common tasks:

| Prompt | Description |
|--------|-------------|
| `build_commander_deck` | EDH deck building with budget support |
| `analyze_card` | Comprehensive card analysis |
| `find_cards_for_strategy` | Strategy-based card search |
| `compare_cards` | Side-by-side card comparison |

## Example Queries

```python
# Search for red dragons legal in Commander
search_cards(colors=["R"], subtype="Dragon", format_legal="commander")

# Get card with images and prices
get_card(name="Sol Ring")

# Find expensive cards
search_by_price(min_price=100, max_price=500)

# Get all printings
get_card_printings(name="Lightning Bolt")
```

## Updating Data

Re-download the database files to update:

1. **MTGJson**: Download `AllPrintings.sqlite` from https://mtgjson.com/downloads/all-files/
2. **Scryfall**: Download `unique-artwork` JSON and run import script
