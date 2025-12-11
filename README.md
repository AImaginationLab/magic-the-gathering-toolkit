# Magic: The Gathering MCP Server

A fast, local MCP server and CLI for Magic: The Gathering. Search 33,000+ cards, browse artwork, check prices, validate decks, and get AI-powered deck-building assistance—all powered by offline SQLite databases.

## Quick Start

```bash
# Install
git clone git@github.com:aimaginationlab/magic-the-gathering-mcp.git
cd magic-the-gathering-mcp
uv sync
uv run create-datasources

# Run the CLI
uv run mtg repl
```

## Two Ways to Use

### 1. Interactive CLI

A themed REPL for quick card lookups, artwork browsing, and deck analysis.

```bash
uv run mtg repl
```

```text
    ╔╦╗╔═╗╔═╗╦╔═╗  ┌┬┐┬ ┬┌─┐
    ║║║╠═╣║ ╦║║     │ ├─┤├┤
    ╩ ╩╩ ╩╚═╝╩╚═╝   ┴ ┴ ┴└─┘
  ╔═╗╔═╗╔╦╗╦ ╦╔═╗╦═╗╦╔╗╔╔═╗
  ║ ╦╠═╣ ║ ╠═╣║╣ ╠╦╝║║║║║ ╦
  ╚═╝╩ ╩ ╩ ╩ ╩╚═╝╩╚═╩╝╚╝╚═╝

"Every planeswalker was once a beginner."

Tapping mana sources...

Library loaded! 33,044 cards across 839 sets
Type a card name to look it up, or ? for help

⚡ Sol Ring
⚡ art Lightning Bolt
⚡ set final fantasy
⚡ search dragon
```

**Features:**
- Just type a card name to look it up
- `art <card>` — Browse all unique artworks, pick one to display
- `set <name>` — Find sets by name or code
- `search`, `rulings`, `legal`, `price`, `random`
- Card images display directly in iTerm2, Kitty, or any true-color terminal

### 2. MCP Server

Integrate with Claude Desktop or any MCP-compatible client for AI-powered assistance.

```bash
uv run mtg-mcp
```

Add to Claude Desktop config (default macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`):

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

Then ask Claude things like:
- "Build me a budget Mono-Red Commander deck under $50"
- "What are the best counterspells in Modern?"
- "Compare Lightning Bolt vs Chain Lightning"
- "Is this deck legal in Pioneer?" (paste your decklist)

## Tools

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

### Sets

| Tool | Description |
|------|-------------|
| `get_sets` | List and search all sets |
| `get_set` | Set details (release date, card count, type) |
| `get_database_stats` | Database version and statistics |

## CLI Commands

```bash
# Card commands
mtg card search -n "Lightning" -c R           # Search red cards with "Lightning"
mtg card get "Sol Ring"                       # Card details
mtg card rulings "Doubling Season"            # Rulings
mtg card price "Black Lotus"                  # Prices

# Set commands
mtg set list --type expansion                 # List expansion sets
mtg set get DOM                               # Dominaria details

# Deck commands
mtg deck validate deck.txt -f modern          # Validate Modern deck
mtg deck curve deck.txt                       # Mana curve analysis
mtg deck price deck.txt                       # Price breakdown

# Database stats
mtg stats
```

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
uv run pytest           # Run tests
uv run ruff check src/  # Lint
uv run mypy src/        # Type check
```

## Copyright 
All rights to Magic: The Gathering belong to Wizards of the Coast, a subsidiary of Hasbro, Inc.
