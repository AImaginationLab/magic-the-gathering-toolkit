# MTG CLI Reference

A command-line interface for Magic: The Gathering card lookup, deck analysis, and set browsing. Features a themed interactive REPL with card images rendered directly in your terminal.

## Installation

```bash
git clone git@github.com:aimaginationlab/magic-the-gathering-mcp.git
cd magic-the-gathering-mcp
uv sync

# Download AllPrintings.sqlite from https://mtgjson.com/downloads/all-files/
# Place in resources/ directory
```

## Quick Start

```bash
# Start interactive REPL (recommended)
uv run mtg repl

# Or use direct commands
uv run mtg card get "Lightning Bolt"
uv run mtg deck validate deck.txt -f modern
```

---

## Interactive REPL

The REPL provides a themed, Magic-style interface for quick lookups:

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

Library loaded! 33,044 cards across 839 sets
Type a card name to look it up, or ? for help

⚡
```

### REPL Commands

| Command | Aliases | Description |
|---------|---------|-------------|
| `<card name>` | - | Just type a card name to look it up |
| `search <query>` | - | Search cards with filters (see below) |
| `art <name>` | `img`, `image`, `pic` | Browse & display card artwork |
| `rulings <name>` | `r` | Show official card rulings |
| `legal <name>` | `legality`, `l` | Show format legalities |
| `price <name>` | `p` | Show current prices |
| `random` | - | Display a random card |
| `sets` | - | Browse all sets (paginated) |
| `set <name>` | - | Show set details (by code or name) |
| `stats` | - | Show database statistics |
| `help` | `?` | Show help |
| `quit` | `exit`, `q` | Exit REPL |

### Search Filters

The `search` command supports powerful filtering with a `filter:value` syntax:

```text
⚡ search dragon t:creature c:R
⚡ search t:instant f:modern cmc<:3
⚡ search text:"draw a card" c:U
⚡ search r:mythic set:MOM
```

**Available Filters:**

| Filter | Aliases | Description | Example |
|--------|---------|-------------|---------|
| `t:` | `type:` | Card type | `t:creature`, `t:instant` |
| `s:` | `sub:`, `subtype:` | Subtype | `s:elf`, `s:dragon` |
| `c:` | `color:`, `colors:` | Colors (W/U/B/R/G) | `c:R`, `c:RG`, `c:R,G` |
| `ci:` | `identity:` | Color identity | `ci:WUBRG` |
| `cmc:` | `mv:`, `mana:` | Exact mana value | `cmc:3` |
| `cmc>:` | `mv>:` | Minimum mana value | `cmc>:4` |
| `cmc<:` | `mv<:` | Maximum mana value | `cmc<:2` |
| `f:` | `format:`, `legal:` | Format legality | `f:modern`, `f:commander` |
| `r:` | `rarity:` | Rarity | `r:mythic`, `r:rare` |
| `set:` | `e:`, `edition:` | Set code | `set:DOM`, `set:MOM` |
| `text:` | `o:`, `oracle:` | Rules text | `text:"draw a card"` |
| `kw:` | `keyword:`, `keywords:` | Keyword ability | `kw:flying`, `kw:trample` |
| `pow:` | `power:` | Power | `pow:4` |
| `tou:` | `toughness:` | Toughness | `tou:5` |
| `sort:` | `sort_by:` | Sort field | `sort:cmc`, `sort:rarity` |
| `order:` | `sort_order:` | Sort order | `order:asc`, `order:desc` |

**Sorting:**

Results can be sorted by any of these fields:
- `name` - Alphabetical (default)
- `cmc` - Mana value
- `color` - Color (WUBRG order)
- `rarity` - Rarity (common → mythic)
- `type` - Card type

Examples:
```text
⚡ search t:creature c:R sort:cmc order:desc
⚡ search dragon sort:rarity
```

**Notes:**
- Filters can be combined: `search dragon t:creature c:R cmc>:4`
- Use quotes for multi-word values: `text:"destroy target"`
- Colors can be specified as `c:RG` or `c:R,G`
- Everything not in a filter is treated as a name search
- Results are paginated (20 per page) with interactive navigation:
  - `Enter` - next page
  - `b` - previous page
  - `#` - view card details (e.g., type `5` to view card #5)
  - `q` - exit search results

### Card Display

Cards are rendered as styled panels with color-coded borders:

- **White cards**: Light gray border
- **Blue cards**: Blue border
- **Black cards**: Purple border
- **Red cards**: Red border
- **Green cards**: Green border
- **Multicolor cards**: Gold border
- **Colorless/Artifacts**: Gray border

Mana costs use emoji symbols:
- 🌞 White
- 💧 Blue
- 💀 Black
- 🔥 Red
- 🌳 Green
- 💠 Colorless
- 🔄 Tap
- ❄️ Snow

### Artwork Browser

The `art` command lets you browse all unique artworks for a card:

```text
⚡ art Lightning Bolt

🎨 12 unique artworks for Lightning Bolt:

   1) LEA  Alpha
   2) 2XM  M15 borderless
   3) STA  M15 full-art etched
   4) A25  M15
   ...

Enter a number to view, or press Enter to skip:
# 3
```

Images display directly in supported terminals:
- **iTerm2**: Full image support via inline images protocol
- **Kitty**: Native image protocol
- **Sixel terminals**: Sixel graphics (experimental)
- **Other terminals**: ANSI half-block character rendering

### Set Browser

Browse sets with pagination and filtering:

```text
⚡ sets

📚 839 sets:
    1) LEA    Limited Edition Alpha (1993-08-05)
    2) LEB    Limited Edition Beta (1993-10-04)
    3) 2ED    Unlimited Edition (1993-12-01)
    ...

Showing 1-15 of 839. Enter=more | b=back | /<text>=filter | q=done
sets> /final fantasy

📚 1 sets matching 'final fantasy':
    1) FIC    Final Fantasy (2025-06-13)
```

### Command History

The REPL saves command history to `~/.mtg_repl_history` for recall with up/down arrows.

---

## CLI Commands

All commands support `--json` for machine-readable output.

### Card Commands

#### `mtg card search`

Search for cards with multiple filters.

```bash
# Basic name search
mtg card search -n "Lightning"

# Filter by type
mtg card search -t Instant

# Filter by colors (W=White, U=Blue, B=Black, R=Red, G=Green)
mtg card search -c R,U -n "bolt"

# Filter by mana value
mtg card search --cmc 3
mtg card search --cmc-min 5 --cmc-max 7

# Filter by format legality
mtg card search -f modern -t Creature

# Filter by rarity
mtg card search --rarity mythic -t Dragon

# Filter by set
mtg card search --set DOM -t Legendary

# Filter by rules text
mtg card search --text "draw a card" -c U

# Pagination
mtg card search -t Creature --page 2 --page-size 50

# JSON output
mtg card search -n "Shock" --json
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--name` | `-n` | Card name (partial match) |
| `--type` | `-t` | Card type (Creature, Instant, etc.) |
| `--subtype` | `-s` | Subtype (Elf, Dragon, Equipment, etc.) |
| `--colors` | `-c` | Colors (comma-separated: W,U,B,R,G) |
| `--cmc` | | Exact mana value |
| `--cmc-min` | | Minimum mana value |
| `--cmc-max` | | Maximum mana value |
| `--format` | `-f` | Format legality (standard, modern, etc.) |
| `--text` | | Rules text search |
| `--rarity` | | Rarity (common, uncommon, rare, mythic) |
| `--set` | | Set code |
| `--page` | | Page number (default: 1) |
| `--page-size` | | Results per page (default: 25) |
| `--json` | | Output as JSON |

#### `mtg card get`

Get detailed information about a specific card.

```bash
mtg card get "Sol Ring"
mtg card get "Lightning Bolt" --json
```

#### `mtg card rulings`

Get official rulings from Gatherer.

```bash
mtg card rulings "Doubling Season"
mtg card rulings "Blood Moon" --json
```

#### `mtg card legality`

Check format legality for a card.

```bash
mtg card legality "Black Lotus"
mtg card legality "Ragavan, Nimble Pilferer" --json
```

#### `mtg card price`

Get current market prices (requires Scryfall database).

```bash
mtg card price "Mox Diamond"
mtg card price "Force of Will" --set ALL --json
```

#### `mtg card random`

Get a random card.

```bash
mtg card random
mtg card random --json
```

---

### Set Commands

#### `mtg set list`

List Magic sets with optional filters.

```bash
# List all sets
mtg set list

# Filter by name
mtg set list -n "Innistrad"

# Filter by type
mtg set list -t expansion

# Include online-only sets
mtg set list --include-online

# JSON output
mtg set list --json
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--name` | `-n` | Filter by name |
| `--type` | `-t` | Filter by type (expansion, core, draft_innovation, etc.) |
| `--include-online` | | Include online-only sets (MTGO, Arena) |
| `--json` | | Output as JSON |

#### `mtg set get`

Get details for a specific set.

```bash
mtg set get DOM       # By code
mtg set get lea --json
```

---

### Deck Commands

All deck commands accept a deck file in simple text format:

```text
# Main deck
4 Lightning Bolt
4 Monastery Swiftspear
4 Goblin Guide
20 Mountain

# Sideboard (prefix with SB:)
SB: 3 Smash to Smithereens
SB: 2 Pyroblast
```

#### `mtg deck validate`

Validate a deck against format rules.

```bash
mtg deck validate deck.txt -f modern
mtg deck validate edh.txt -f commander --commander "Atraxa, Praetors' Voice"
mtg deck validate deck.txt -f standard --json
```

Checks:
- Deck size requirements (60+ for constructed, 100 for Commander)
- Copy limits (4 max, or singleton for Commander)
- Card legality in the format
- Color identity (Commander only)
- Sideboard limits

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--format` | `-f` | Format to validate (required) |
| `--commander` | | Commander name (for Commander format) |
| `--json` | | Output as JSON |

#### `mtg deck curve`

Analyze mana curve distribution.

```bash
mtg deck curve deck.txt
mtg deck curve deck.txt --json
```

Output includes:
- Average mana value
- Mana value distribution (visual bar chart)
- Land vs non-land count
- X-spell count

#### `mtg deck colors`

Analyze color distribution and mana requirements.

```bash
mtg deck colors deck.txt
mtg deck colors deck.txt --json
```

Output includes:
- Deck colors
- Mana pip counts by color
- Multicolor/colorless card counts
- Recommended land ratios

#### `mtg deck composition`

Analyze card type breakdown.

```bash
mtg deck composition deck.txt
mtg deck composition deck.txt --json
```

Output includes:
- Total card count
- Creatures, lands, spells breakdown
- Card type distribution table

#### `mtg deck price`

Calculate total deck price (requires Scryfall database).

```bash
mtg deck price deck.txt
mtg deck price deck.txt --json
```

Output includes:
- Total price (mainboard + sideboard)
- Most expensive cards (top 10)
- Cards with missing price data

---

### Utility Commands

#### `mtg stats`

Show database statistics.

```bash
mtg stats
mtg stats --json
```

#### `mtg serve`

Start the MCP server (for Claude Desktop integration).

```bash
mtg serve
# Or use the dedicated command:
mtg-mcp
```

---

## Deck File Format

The CLI accepts deck files in a simple text format:

```text
# Comments start with #
# Quantity followed by card name
4 Lightning Bolt
4 Monastery Swiftspear
2 Eidolon of the Great Revel
20 Mountain

# Cards without quantity default to 1
Black Lotus

# Sideboard cards prefixed with SB:
SB: 3 Smash to Smithereens
SB: 2 Pyroblast
```

---

## Environment Variables

Configure database paths:

```bash
export MTG_DB_PATH=/path/to/AllPrintings.sqlite
export SCRYFALL_DB_PATH=/path/to/scryfall.sqlite
```

Or create a `.env` file:

```text
MTG_DB_PATH=resources/AllPrintings.sqlite
SCRYFALL_DB_PATH=resources/scryfall.sqlite
LOG_LEVEL=INFO
```

---

## Data Sources

| Database | Source | Required | Contents |
|----------|--------|----------|----------|
| `AllPrintings.sqlite` | [MTGJson](https://mtgjson.com/downloads/all-files/) | Yes | Cards, rules, legalities |
| `scryfall.sqlite` | [Scryfall](https://scryfall.com/docs/api/bulk-data) | No | Images, prices |

---

## Terminal Compatibility

### Image Display

The CLI automatically detects your terminal and uses the best available image display method:

| Terminal | Method | Quality |
|----------|--------|---------|
| iTerm2 | Inline images | Excellent |
| Kitty | Kitty protocol | Excellent |
| Sixel terminals | Sixel graphics | Good |
| Others | ANSI half-blocks | Basic |

### Rich Formatting

The CLI uses [Rich](https://rich.readthedocs.io/) for styled output. Best experience with:
- True color terminal (16 million colors)
- Unicode font support
- Emoji font (for mana symbols)

---

## Examples

### Quick card lookup
```bash
⚡ Sol Ring
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   Sol Ring  1️⃣                                          │
│   ──────────────────────────────────────────────────    │
│   Artifact                                              │
│   ──────────────────────────────────────────────────    │
│   🔄 : Add 💠 💠 .                                       │
│   ──────────────────────────────────────────────────    │
│   ○ LEA · 💰 $350.00                                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Validate a Commander deck
```bash
$ mtg deck validate edh.txt -f commander --commander "Atraxa, Praetors' Voice"

Deck Validation: VALID
Format: commander
Cards: 99 mainboard, 0 sideboard

Warnings:
  • Consider adding more ramp cards
```

### Find budget options
```bash
$ mtg card search -f modern --cmc 1 -c R -t Creature --json | jq '.cards[] | select(.prices.usd < 1)'
```
