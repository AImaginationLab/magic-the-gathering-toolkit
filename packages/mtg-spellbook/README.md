# MTG Spellbook

Interactive terminal UI for Magic: The Gathering card lookup, deck analysis, and synergy exploration. Built with [Textual](https://textual.textualize.io/).

## Installation

```bash
# As part of the workspace
uv sync

# Or standalone
uv pip install -e packages/mtg-spellbook
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

| Key | Action |
|-----|--------|
| `/` | Focus search bar |
| `Tab` | Cycle through tabs |
| `Ctrl+S` | Find synergies for current card |
| `Ctrl+O` | Detect combos for current card |
| `Ctrl+Q` | Quit |

## Architecture

```
src/mtg_spellbook/
├── __init__.py     # Entry point (main function)
├── app.py          # Main Textual application
├── widgets.py      # Custom widgets (search, results, card details)
├── styles.py       # CSS styling (dark theme with gold accents)
├── commands.py     # Command palette commands
└── context.py      # Application context
```

## Dependencies

- `mtg-core` - Shared library (database, models, tools)
- `textual` - TUI framework
- `textual-image` - Terminal image rendering
- `pillow` - Image processing
- `rich` - Rich text formatting
- `httpx` - HTTP client for image fetching
