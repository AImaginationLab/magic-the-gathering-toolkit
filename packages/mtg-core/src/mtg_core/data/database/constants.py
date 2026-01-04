"""Database constants and SQL fragments."""

# SQL fragments for excluding promo/funny cards (MTGJson uses NULL for false)
EXCLUDE_PROMOS = "(c.isPromo IS NULL OR c.isPromo = 0)"
EXCLUDE_FUNNY = "(c.isFunny IS NULL OR c.isFunny = 0)"
EXCLUDE_EXTRAS = f"{EXCLUDE_PROMOS} AND {EXCLUDE_FUNNY}"

# Base card columns for queries (with table prefix)
CARD_COLUMNS = """
    c.uuid, c.name, c.flavorName, c.manaCost, c.manaValue, c.colors, c.colorIdentity,
    c.type, c.supertypes, c.types, c.subtypes, c.text, c.flavorText,
    c.power, c.toughness, c.loyalty, c.defense, c.setCode, c.rarity,
    c.number, c.artist, c.layout, c.keywords, c.edhrecRank, s.releaseDate
""".strip()

# Same columns without table prefix (for CTEs and subqueries)
CARD_COLUMNS_PLAIN = """
    uuid, name, flavorName, manaCost, manaValue, colors, colorIdentity,
    type, supertypes, types, subtypes, text, flavorText,
    power, toughness, loyalty, defense, setCode, rarity,
    number, artist, layout, keywords, edhrecRank, releaseDate
""".strip()

# Valid format keys in cards.legalities JSON column
VALID_FORMATS = frozenset(
    {
        "standard",
        "modern",
        "legacy",
        "vintage",
        "commander",
        "pioneer",
        "pauper",
        "historic",
        "brawl",
        "alchemy",
        "explorer",
        "timeless",
        "oathbreaker",
        "penny",
        "duel",
        "gladiator",
        "premodern",
        "oldschool",
        "predh",
        "paupercommander",
    }
)
