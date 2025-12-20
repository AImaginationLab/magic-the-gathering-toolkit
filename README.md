# Magic: The Gathering Toolkit

A comprehensive toolkit for Magic: The Gathering players featuring a terminal UI deck builder, card collection manager, synergy finder, and MCP server for AI integration. Search 33,000+ cards, browse artwork and artist profiles, get deck recommendations based on your collection, and more.

<img src="https://iili.io/f0va8kg.png" alt="Collection View" width="800"/>

<details>
  <summary>More Screenshots</summary>
  <p>Synergy Suggestions</p>
  <img src="https://iili.io/f0vc49e.png" alt="Card search results"  width="800"/>
  <p>Deck Addition Recommendations</p>
  <img src="https://iili.io/f0vltzG.png" alt="Card details with artwork" width="800"/>
</details>

## Features

- **Card Search** - Search 33,000+ cards with 15+ filters (name, colors, type, CMC, keywords, format, rarity, set)
- **Artwork Browser** - High-resolution card art with gallery, focus, and compare views
- **Deck Builder** - Full deck management with mana curve, color balance, and format validation
- **Collection Tracker** - Track owned cards, wishlist, multiple printings, foils
- **Synergy Finder** - Discover card synergies and combos based on keywords, types, and abilities
- **Recommendations** - Get personalized card suggestions for your decks based on your collection
- **Price Tracking** - Current USD/EUR prices from Scryfall
- **Artist Portfolios** - Browse cards by artist
- **MCP Server** - Integrate with MCP capable client applications for AI-powered deck building assistance

## Packages

This is a UV workspace with three packages:

| Package | Description |
|---------|-------------|
| [mtg-core](packages/mtg-core/) | Shared library: database access, card models, synergy tools |
| [mtg-mcp](packages/mtg-mcp/) | MCP server for Claude Desktop integration |
| [mtg-spellbook](packages/mtg-spellbook/) | Interactive terminal UI (Textual) |

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Terminal with true color support (iTerm2, Kitty, Windows Terminal, etc.)

## Quick Start

```bash
# Clone and install
git clone https://github.com/AImaginationLab/magic-the-gathering-toolkit.git
cd magic-the-gathering-toolkit
uv sync

# Download card databases (~500MB)
# If launching the terminal UI, this is done automatically at startup.
uv run create-datasources

# Launch the terminal UI
uv run mtg-spellbook
```

## MTG Spellbook (Terminal UI)

A themed terminal interface for card lookups, artwork browsing, deck building, and synergy discovery.

```bash
uv run mtg-spellbook
```

### Search Syntax

Type directly in the search bar `search` followed by:

| Prefix | Description | Example |
|--------|-------------|---------|
| `t:` | Card type | `search t:dragon` |
| `c:` | Card colors | `search c:rb` (red/black) |
| `ci:` | Color identity | `search ci:wubrg` |
| `cmc:` | Mana value | `search cmc:3` or `search cmc:>=5` |
| `f:` | Format legal | `search f:modern` |
| `r:` | Rarity | `search r:mythic` |
| `set:` | Set code | `search set:MH3` |
| `kw:` | Keyword | `search kw:flying` |
| `o:` | Oracle text | `search o:draw a card` |

Combine filters: `search t:creature c:r cmc:3 f:standard`

### Keyboard Shortcuts
The terminal UI is designed to be navigated through with keyboard shortcuts, tabs + arrows, or with your mouse.

| Key | Action |
|-----|--------|
| `Esc` | Focus search / go back |
| `?` | Help screen |
| `a` | Browse artists |
| `s` | Browse sets |
| `d` | Browse decks |
| `c` | Browse collection |
| `r` | Random card |
| `g` | Gallery view |
| `f` | Focus view |
| `Ctrl+S` | Find synergies |
| `Ctrl+O` | Find combos |
| `Ctrl+E` | Add to deck |
| `Ctrl+D` | Toggle deck panel |

### Card View Modes

- **Gallery View** (`g`) - Filmstrip of all printings with prices
- **Focus View** (`f`) - Full card display with metadata
- **Compare View** (`c`) - Side-by-side comparison (up to 4 cards)

## MCP Server

Integrate with Claude Desktop or other MCP-compatible clients for AI-powered assistance.

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

### Example Prompts

- "Build me a budget Mono-Red Commander deck under $50"
- "What are the best counterspells in Modern?"
- "Find cards that synergize with Rhystic Study"
- "Is this deck legal in Pioneer?" (paste your decklist)

### Available Tools

<details>
<summary><strong>Card Lookup</strong></summary>

| Tool | Description |
|------|-------------|
| `search_cards` | Filter by name, colors, type, CMC, keywords, format, rarity, set |
| `get_card` | Full card details with images and prices |
| `get_card_rulings` | Official rulings from Gatherer |
| `get_card_legalities` | Format legality (Standard, Modern, Commander, etc.) |
| `get_random_card` | Discover something new |

</details>

<details>
<summary><strong>Images & Prices</strong></summary>

| Tool | Description |
|------|-------------|
| `get_card_image` | Image URLs in multiple sizes |
| `get_card_printings` | Every printing with artwork and prices |
| `get_card_price` | Current USD/EUR prices |
| `search_by_price` | Find cards in a price range |

</details>

<details>
<summary><strong>Deck Analysis</strong></summary>

| Tool | Description |
|------|-------------|
| `validate_deck` | Check format legality, deck size, copy limits |
| `analyze_mana_curve` | CMC distribution and average |
| `analyze_colors` | Color balance and recommended land ratios |
| `analyze_deck_composition` | Creature/spell/land breakdown |
| `analyze_deck_price` | Total cost and expensive cards |

</details>

<details>
<summary><strong>Synergy & Strategy</strong></summary>

| Tool | Description |
|------|-------------|
| `find_synergies` | Find cards that synergize with a given card |
| `detect_combos` | Identify known combos in a deck or for a card |
| `suggest_cards` | Recommend cards based on deck theme/strategy |

</details>

<details>
<summary><strong>Sets</strong></summary>

| Tool | Description |
|------|-------------|
| `get_sets` | List and search all sets |
| `get_set` | Set details (release date, card count, type) |
| `get_database_stats` | Database version and statistics |

</details>

## Data Sources

| Database | Source | Contents |
|----------|--------|----------|
| `AllPrintings.sqlite` | [MTGJson](https://mtgjson.com/) | Cards, rules, legalities |
| `scryfall.sqlite` | [Scryfall](https://scryfall.com/) | Images, prices, purchase links |

Databases are downloaded automatically with `uv run create-datasources`. To refresh:

```bash
uv run create-datasources          # Re-download databases
uv run create-datasources clear-cache  # Clear cached data
```

### Environment Variables

```bash
MTG_DB_PATH=resources/AllPrintings.sqlite
SCRYFALL_DB_PATH=resources/scryfall.sqlite
LOG_LEVEL=INFO

# Cache settings
CACHE_MAX_SIZE=1000
CACHE_TTL_SECONDS=3600

# Image cache settings
# Disk cache limit in MB (default 1024 = 1GB, stores ~1000 card images as PNG)
IMAGE_CACHE_MAX_MB=1024
# Number of images to keep in memory for fast access
IMAGE_MEMORY_CACHE_COUNT=20

# Data cache settings (printings, synergies - stored as compressed JSON)
# Disk cache limit in MB (default 100MB, gzip compressed)
DATA_CACHE_MAX_MB=100
```

## Development

```bash
uv sync --all-extras    # Install dev dependencies
uv run pytest packages/ # Run tests
uv run ruff check packages/  # Lint
uv run ruff format packages/ # Format
uv run mypy packages/        # Type check
```

*Magic: The Gathering Toolkit is unofficial Fan Content permitted under the Fan Content Policy. Not approved/endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC.*

Data used in this project obtained from MTGJson, Scryfall, 17lands and CommanderSpellbook.
