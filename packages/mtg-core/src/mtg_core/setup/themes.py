"""Pre-compute card themes from oracle text and keywords - fully database-driven."""

from __future__ import annotations

import contextlib
import json
import re
import sqlite3
from collections.abc import Callable
from pathlib import Path


def _ensure_theme_patterns_exist(gameplay_sqlite_path: Path) -> None:
    """Ensure conceptual theme patterns exist in abilities table.

    These are oracle text patterns that detect synergy themes like:
    - etb (enters the battlefield)
    - tokens (token creation)
    - graveyard (recursion/reanimation)
    - etc.

    The patterns are stored with category='theme_pattern' and the text
    field contains a regex pattern to match in oracle text.
    """
    if not gameplay_sqlite_path.exists():
        return

    # Check if theme patterns already exist
    conn = sqlite3.connect(str(gameplay_sqlite_path))
    cursor = conn.execute("SELECT COUNT(*) FROM abilities WHERE category = 'theme_pattern'")
    count = cursor.fetchone()[0]

    if count > 0:
        conn.close()
        return

    # Seed theme patterns - these detect conceptual themes from oracle text
    # Format: (theme_name, regex_pattern)
    theme_patterns = [
        # ETB triggers
        ("etb", r"enters the battlefield"),
        ("etb", r"when .* enters"),
        ("etb", r"whenever .* enters"),
        ("etb", r"this creature enters"),
        ("etb", r"this enchantment enters"),
        ("etb", r"this artifact enters"),
        # Token creation
        ("tokens", r"creates? .* tokens?"),
        ("tokens", r"puts? .* tokens? onto"),
        # Graveyard/recursion
        ("graveyard", r"graveyard"),
        ("recursion", r"return .* from your graveyard to"),
        # Death triggers
        ("death_trigger", r"when .* dies"),
        ("death_trigger", r"whenever .* dies"),
        ("sacrifice", r"sacrifices?"),
        # Hand manipulation
        ("hand_reveal", r"reveal .* from .* hand"),
        ("hand_reveal", r"reveals .* hand"),
        ("hand_reveal", r"look at .* hand"),
        ("discard", r"discard "),
        ("draw", r"draw [\w\s]* cards?"),
        ("draw", r"draws? a card"),
        ("draw", r"draws? .* cards"),
        ("draw", r"draws? that many"),
        ("draw", r"draw cards equal"),
        ("draw", r"draws an additional"),
        # Counters
        ("counters", r"\+1/\+1 counter"),
        ("counters", r"-1/-1 counter"),
        ("counters", r"counter on"),
        # Lifegain (avoid matching "gains lifelink" or "gains indestructible")
        ("lifegain", r"gain \d+ life"),
        ("lifegain", r"gains \d+ life"),
        ("lifegain", r"gain life equal"),
        ("lifegain", r"gains life equal"),
        ("lifegain", r"you gain life"),
        ("lifegain", r"gained .* life"),
        ("lifegain", r"whenever .* gains? life"),
        ("lifegain", r"life you.* gained"),
        # Combat
        ("evasion", r"can't be blocked"),
        ("combat", r"deals combat damage"),
        ("combat", r"attacking creature"),
        # Exile
        ("exile", r"exile "),
        # Ramp/mana
        ("ramp", r"add .* mana"),
        ("ramp", r"search .* library .* land"),
        # Control
        ("removal", r"destroy target"),
        ("removal", r"exile target"),
        ("bounce", r"return .* to .* owner's hand"),
        # Copy effects
        ("copy", r"copy "),
        ("copy", r"becomes a copy"),
        # Tutors
        ("tutor", r"search your library"),
        # Protection
        ("protection", r"hexproof"),
        ("protection", r"indestructible"),
        ("protection", r"protection from"),
    ]

    # Insert theme patterns
    for theme, pattern in theme_patterns:
        conn.execute(
            "INSERT OR IGNORE INTO abilities (text, category) VALUES (?, ?)",
            (f"{theme}:{pattern}", "theme_pattern"),
        )

    conn.commit()
    conn.close()


def _load_theme_patterns_from_db(
    gameplay_sqlite_path: Path,
) -> dict[str, list[re.Pattern[str]]]:
    """Load theme patterns from abilities table.

    Returns dict mapping theme name to list of compiled regex patterns.
    """
    if not gameplay_sqlite_path.exists():
        return {}

    patterns: dict[str, list[re.Pattern[str]]] = {}

    try:
        conn = sqlite3.connect(str(gameplay_sqlite_path))
        cursor = conn.execute("SELECT text FROM abilities WHERE category = 'theme_pattern'")

        for (text,) in cursor.fetchall():
            if not text or ":" not in text:
                continue

            theme, regex = text.split(":", 1)
            if theme not in patterns:
                patterns[theme] = []

            with contextlib.suppress(re.error):
                patterns[theme].append(re.compile(regex, re.IGNORECASE))

        conn.close()
    except Exception:
        pass

    return patterns


def _load_mechanics_from_db(gameplay_sqlite_path: Path) -> set[str]:
    """Load all keyword mechanics from the abilities table.

    Returns lowercase mechanic names that should be treated as themes.
    """
    if not gameplay_sqlite_path.exists():
        return set()

    mechanics: set[str] = set()

    try:
        conn = sqlite3.connect(str(gameplay_sqlite_path))
        cursor = conn.execute("SELECT DISTINCT text FROM abilities WHERE category = 'keyword'")

        for (text,) in cursor.fetchall():
            if not text:
                continue

            # Normalize: lowercase, extract base mechanic name
            text_lower = text.lower().strip()

            # Skip non-mechanic entries like "Draw a card.", "You gain 2 life."
            if text_lower.startswith("you ") or text_lower.startswith("draw "):
                continue
            if text_lower.endswith(" life.") or text_lower.endswith(" cards."):
                continue

            # Extract base mechanic (remove numbers like "Amass Orcs 2" -> "amass")
            # Also handles "Afflict 3" -> "afflict", "Crew 2" -> "crew"
            parts = text_lower.split()
            if parts:
                base = parts[0].rstrip(".")

                # Skip common words that aren't mechanics
                noise_words = {
                    "a",
                    "an",
                    "the",
                    "of",
                    "to",
                    "for",
                    "in",
                    "on",
                    "at",
                    "and",
                    "or",
                    "but",
                    "if",
                    "when",
                    "whenever",
                    "where",
                    "all",
                    "any",
                    "each",
                    "every",
                    "this",
                    "that",
                    "it",
                    "put",
                    "get",
                    "has",
                    "have",
                    "had",
                    "was",
                    "were",
                    "is",
                    "can",
                    "may",
                    "must",
                    "will",
                    "would",
                    "could",
                    "should",
                    "add",
                    "gain",
                    "lose",
                    "pay",
                    "tap",
                    "untap",
                    "choose",
                    "target",
                    "card",
                    "creature",
                    "artifact",
                    "enchantment",
                }

                # Skip if it's just a number, very short, or a noise word
                if len(base) >= 3 and not base.isdigit() and base not in noise_words:
                    mechanics.add(base)

        conn.close()
    except Exception:
        pass

    return mechanics


def populate_card_themes(
    mtg_db_path: Path,
    gameplay_sqlite_path: Path,
    progress_callback: Callable[[float, str], None] | None = None,
) -> int:
    """Populate card_themes table - fully database-driven.

    Detects themes from:
    1. Card's keywords JSON field (mechanics like Suspect, Investigate, etc.)
    2. Oracle text patterns matching known mechanics from abilities table
    3. Conceptual theme patterns stored in abilities table (category='theme_pattern')

    Args:
        mtg_db_path: Path to the main MTG database (source of card data)
        gameplay_sqlite_path: Path to gameplay.sqlite (destination for themes)
        progress_callback: Optional progress callback (progress 0-1, message)

    Returns:
        Number of theme entries created
    """
    report = progress_callback or (lambda _p, _m: None)

    report(0.0, "Loading mechanics from database...")

    # Ensure theme patterns exist in database
    _ensure_theme_patterns_exist(gameplay_sqlite_path)

    # Load mechanics from abilities table
    known_mechanics = _load_mechanics_from_db(gameplay_sqlite_path)

    # Load conceptual theme patterns from database
    theme_patterns = _load_theme_patterns_from_db(gameplay_sqlite_path)
    report(
        0.02,
        f"Found {len(known_mechanics)} mechanics, {len(theme_patterns)} theme types",
    )

    # Ensure gameplay.sqlite exists with correct schema
    gameplay_sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    gameplay_conn = sqlite3.connect(str(gameplay_sqlite_path))
    gameplay_cursor = gameplay_conn.cursor()

    # Create card_themes table if not exists
    gameplay_cursor.execute("""
        CREATE TABLE IF NOT EXISTS card_themes (
            card_name TEXT NOT NULL,
            theme TEXT NOT NULL,
            PRIMARY KEY (card_name, theme)
        )
    """)
    gameplay_cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_card_themes_theme ON card_themes(theme)"
    )

    # Clear existing themes
    gameplay_cursor.execute("DELETE FROM card_themes")
    gameplay_conn.commit()

    # Load cards from mtg database
    mtg_conn = sqlite3.connect(str(mtg_db_path))
    mtg_cursor = mtg_conn.cursor()

    # Get all unique cards with oracle text AND keywords
    mtg_cursor.execute("""
        SELECT DISTINCT name, oracle_text, keywords
        FROM cards
        WHERE is_token = 0
    """)

    cards = mtg_cursor.fetchall()
    total = len(cards)
    report(0.05, f"Processing {total:,} cards...")

    # Build regex patterns for oracle text detection
    # Only include mechanics that make sense to search in oracle text
    mechanic_patterns: dict[str, re.Pattern[str]] = {}
    for mechanic in known_mechanics:
        # Create pattern that matches the mechanic as a standalone word
        # or with common verb suffixes (-s, -ed, -ing, -er)
        # Avoid matching "battle" in "battlefield" by using specific suffixes
        pattern = re.compile(rf"\b{re.escape(mechanic)}(e?s|e?d|ing|er)?\b", re.IGNORECASE)
        mechanic_patterns[mechanic] = pattern

    # Detect themes for each card
    theme_entries: list[tuple[str, str]] = []

    for processed, (name, oracle_text, keywords_json) in enumerate(cards, 1):
        card_themes: set[str] = set()

        # 1. Extract keywords from the keywords JSON field
        if keywords_json:
            try:
                keywords = json.loads(keywords_json)
                for kw in keywords:
                    kw_lower = kw.lower()
                    # Extract base mechanic name (e.g., "Amass Orcs" -> "amass")
                    base = kw_lower.split()[0] if kw_lower else ""
                    if base in known_mechanics:
                        card_themes.add(base)
            except (json.JSONDecodeError, TypeError):
                pass

        # 2. Detect mechanics from oracle text
        if oracle_text:
            oracle_lower = oracle_text.lower()
            for mechanic, pattern in mechanic_patterns.items():
                if pattern.search(oracle_lower):
                    card_themes.add(mechanic)

            # 3. Detect conceptual themes from oracle text patterns
            for theme, patterns_list in theme_patterns.items():
                for pattern in patterns_list:
                    if pattern.search(oracle_lower):
                        card_themes.add(theme)
                        break  # Found match, no need to check other patterns for this theme

        # Add all themes for this card
        for theme in card_themes:
            theme_entries.append((name, theme))

        if processed % 10000 == 0:
            progress = 0.05 + 0.85 * (processed / total)
            report(progress, f"Processed {processed:,}/{total:,} cards...")

    mtg_conn.close()

    # Insert theme entries in batches
    report(0.92, f"Saving {len(theme_entries):,} theme entries...")

    batch_size = 5000
    for i in range(0, len(theme_entries), batch_size):
        batch = theme_entries[i : i + batch_size]
        gameplay_cursor.executemany(
            "INSERT OR IGNORE INTO card_themes (card_name, theme) VALUES (?, ?)",
            batch,
        )

    gameplay_conn.commit()
    gameplay_conn.close()

    report(1.0, f"Theme detection complete: {len(theme_entries):,} entries")
    return len(theme_entries)


def get_card_themes(gameplay_sqlite_path: Path, card_name: str) -> set[str]:
    """Get pre-computed themes for a card.

    Args:
        gameplay_sqlite_path: Path to gameplay.sqlite
        card_name: Card name to look up

    Returns:
        Set of theme names
    """
    if not gameplay_sqlite_path.exists():
        return set()

    try:
        conn = sqlite3.connect(str(gameplay_sqlite_path))
        cursor = conn.execute(
            "SELECT theme FROM card_themes WHERE card_name = ?",
            (card_name,),
        )
        themes = {row[0] for row in cursor.fetchall()}
        conn.close()
        return themes
    except Exception:
        return set()


def get_cards_with_theme(gameplay_sqlite_path: Path, theme: str) -> list[str]:
    """Get all cards with a specific theme.

    Args:
        gameplay_sqlite_path: Path to gameplay.sqlite
        theme: Theme name to search for

    Returns:
        List of card names
    """
    if not gameplay_sqlite_path.exists():
        return []

    try:
        conn = sqlite3.connect(str(gameplay_sqlite_path))
        cursor = conn.execute(
            "SELECT card_name FROM card_themes WHERE theme = ?",
            (theme,),
        )
        cards = [row[0] for row in cursor.fetchall()]
        conn.close()
        return cards
    except Exception:
        return []
