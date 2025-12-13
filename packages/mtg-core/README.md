# MTG Core

Shared library for the Magic: The Gathering toolkit. Provides database access, card models, and business logic used by both the MCP server and TUI.

## Installation

```bash
# As part of the workspace
uv sync
```

## Usage

```python
from mtg_core.config import get_settings
from mtg_core.data.database import DatabaseManager
from mtg_core.data.models import SearchCardsInput
from mtg_core.tools import cards, deck, synergy

# Initialize database
settings = get_settings()
db_manager = DatabaseManager(settings)
await db_manager.start()

# Search for cards
filters = SearchCardsInput(name="Lightning", colors=["R"], limit=10)
results = await cards.search_cards(db_manager.db, db_manager.scryfall, filters)

# Get card details
card = await cards.get_card(db_manager.db, db_manager.scryfall, name="Lightning Bolt")

# Analyze a deck
deck_cards = [{"name": "Lightning Bolt", "quantity": 4}, ...]
validation = await deck.validate_deck(db_manager.db, deck_cards, format="modern")
curve = await deck.analyze_mana_curve(db_manager.db, deck_cards)

# Find synergies
synergies = await synergy.find_synergies(db_manager.db, "Rhystic Study")

await db_manager.stop()
```

## Modules

### `data/`

- **`database/`** - Async SQLite database access
  - `MTGDatabase` - MTGJson database (cards, rulings, legalities)
  - `ScryfallDatabase` - Scryfall database (images, prices)
  - `DatabaseManager` - Connection lifecycle management
  - `QueryBuilder` - Type-safe query construction

- **`models/`** - Pydantic models
  - `Card`, `CardRuling`, `CardLegality`, `CardImage`
  - `Deck`, `DeckCard`
  - `Set`
  - Input/output models for all tools

### `tools/`

- **`cards.py`** - Card search, details, rulings, legalities, random
- **`deck.py`** - Deck validation, mana curve, color analysis, composition, pricing
- **`synergy.py`** - Synergy detection, combo identification, card suggestions
- **`sets.py`** - Set listing and details
- **`images.py`** - Image URLs, printings, prices

### `utils/`

- **`mana.py`** - Mana cost parsing and color extraction

### `config.py`

Settings via pydantic-settings:

```python
from mtg_core.config import get_settings

settings = get_settings()
print(settings.mtg_db_path)      # Path to AllPrintings.sqlite
print(settings.scryfall_db_path) # Path to scryfall.sqlite
print(settings.log_level)        # INFO
print(settings.cache_max_size)   # 1000
```

Environment variables:
- `MTG_DB_PATH` - Path to MTGJson database
- `SCRYFALL_DB_PATH` - Path to Scryfall database
- `LOG_LEVEL` - Logging level (default: INFO)
- `CACHE_MAX_SIZE` - Card cache size (default: 1000)
- `CACHE_TTL_SECONDS` - Cache TTL (default: 3600)

### `exceptions.py`

Custom exceptions for error handling:

```python
from mtg_core.exceptions import CardNotFoundError, SetNotFoundError, ValidationError

try:
    card = await cards.get_card(db, scryfall, name="Nonexistent Card")
except CardNotFoundError as e:
    print(f"Card not found: {e}")
```

## Dependencies

- `aiosqlite` - Async SQLite access
- `pydantic` - Data validation and models
- `pydantic-settings` - Configuration management
- `httpx` - HTTP client (for Scryfall API fallback)
