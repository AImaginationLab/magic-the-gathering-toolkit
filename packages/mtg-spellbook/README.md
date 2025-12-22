# MTG Spellbook

Interactive terminal UI for Magic: The Gathering card lookup, deck analysis, and synergy exploration. Built with [Textual](https://textual.textualize.io/).

## Installation

```bash
# As part of the workspace
uv sync
```

## Usage

```bash
uv run mtg-spellbook
```

## Features

### Card Search
- Search 33,000+ cards with 15+ filters
- Filter by name, colors, type, CMC, keywords, format, rarity, set
- Results update as you type

### Card Details
- Full oracle text and flavor text
- Mana cost and color identity
- Power/toughness, loyalty
- Set and rarity information

### Artwork Browser
- High-resolution card images
- Browse all unique artworks for a card
- Works in iTerm2, Kitty, and other image-capable terminals

### Prices & Printings
- Current USD/EUR prices from Scryfall
- All printings with set codes
- Price history across printings

### Rulings & Legalities
- Official rulings from Gatherer
- Format legality (Standard, Modern, Pioneer, Commander, etc.)

### Synergy & Combos
- Find cards that synergize with any card
- Detect known combos
- Get card suggestions based on themes

## Keyboard Shortcuts

### Global
| Key | Action |
|-----|--------|
| `Esc` | Focus search / go back |
| `?` | Help screen |
| `Tab` | Cycle through tabs |
| `a` | Browse artists |
| `s` | Browse sets |
| `d` | Browse decks |
| `c` | Browse collection |
| `r` | Random card |
| `Ctrl+Q` | Quit |

### Card Panel
| Key | Action |
|-----|--------|
| `g` | Gallery view |
| `f` | Focus view |
| `c` | Compare view |
| `e` | Explore artist |
| `a` | Toggle art crop |
| `Ctrl+S` | Find synergies |
| `Ctrl+O` | Detect combos |
| `Ctrl+E` | Add to deck |
| `Ctrl+D` | Toggle deck panel |

## Architecture

```
src/mtg_spellbook/
├── __init__.py           # Entry point
├── app.py                # Main Textual application
├── styles.py             # CSS styling
├── context.py            # Application context
├── collection_manager.py # Collection tracking
├── deck_manager.py       # Deck management
├── collection/           # Collection view widgets
├── commands/             # Command palette
├── deck/                 # Deck builder widgets
├── recommendations/      # Deck recommendations
├── screens/              # Application screens
├── ui/                   # UI utilities and theming
└── widgets/              # Reusable UI widgets
    └── art_navigator/    # Artwork browser
```

## Dependencies

- `mtg-core` - Shared library (database, models, tools)
- `textual` - TUI framework
- `textual-image` - Terminal image rendering
- `pillow` - Image processing
- `rich` - Rich text formatting
- `httpx` - HTTP client for image fetching
