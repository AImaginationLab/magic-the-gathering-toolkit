"""TF-IDF based card recommendation system."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import NDArray

# Lazy imports for sklearn/scipy to speed up startup time
# These are only imported when actually needed (in initialize())
if TYPE_CHECKING:
    from scipy.sparse import csr_matrix
    from sklearn.feature_extraction.text import TfidfVectorizer

    from mtg_core.data.database import UnifiedDatabase

logger = logging.getLogger(__name__)


@dataclass
class CardRecommendation:
    """A recommended card with similarity score."""

    name: str
    score: float
    uuid: str | None = None
    type_line: str | None = None
    mana_cost: str | None = None
    colors: list[str] | None = None


@dataclass
class CardRecommender:
    """TF-IDF based card recommendation engine.

    Builds feature vectors from card text and finds similar cards using
    cosine similarity. Vectors are computed lazily on first use.
    """

    _vectorizer: TfidfVectorizer | None = field(default=None, repr=False)
    _tfidf_matrix: csr_matrix | None = field(default=None, repr=False)
    _card_names: list[str] = field(default_factory=list, repr=False)
    _card_data: dict[str, dict[str, Any]] = field(default_factory=dict, repr=False)
    _name_to_idx: dict[str, int] = field(default_factory=dict, repr=False)
    _initialized: bool = False
    _init_time: float = 0.0

    async def initialize(self, db: UnifiedDatabase) -> float:
        """Initialize the recommender with card data from the database.

        Returns:
            Time taken to initialize in seconds.
        """
        if self._initialized:
            return self._init_time

        start = time.perf_counter()
        logger.info("Initializing TF-IDF card recommender...")

        # Lazy import sklearn here to avoid slow startup
        from sklearn.feature_extraction.text import TfidfVectorizer

        # Fetch all unique cards (one per name, prefer non-promo)
        cards = await self._fetch_unique_cards(db)
        logger.info(f"Loaded {len(cards)} unique cards")

        # Build feature documents
        documents: list[str] = []
        self._card_names = []
        self._card_data = {}
        self._name_to_idx = {}

        for idx, card in enumerate(cards):
            name = card["name"]
            doc = self._build_document(card)
            documents.append(doc)
            self._card_names.append(name)
            self._card_data[name] = card
            self._name_to_idx[name] = idx

        # Fit TF-IDF vectorizer
        self._vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95,
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(documents)

        self._init_time = time.perf_counter() - start
        self._initialized = True
        logger.info(f"TF-IDF recommender initialized in {self._init_time:.2f}s")

        return self._init_time

    async def _fetch_unique_cards(self, db: UnifiedDatabase) -> list[dict[str, Any]]:
        """Fetch unique cards from database (one printing per card name)."""
        query = """
            SELECT
                c.name,
                c.id AS uuid,
                c.type_line AS type,
                c.oracle_text AS text,
                c.mana_cost AS manaCost,
                c.colors,
                c.color_identity AS colorIdentity,
                c.type_line AS types,
                -- subtypes extracted from type_line by _build_document
                c.type_line AS subtypes,
                c.keywords,
                c.power,
                c.toughness,
                c.cmc AS manaValue,
                c.edhrec_rank AS edhrecRank
            FROM cards c
            WHERE (c.is_promo IS NULL OR c.is_promo = 0)
              AND c.is_token = 0
              AND c.name NOT LIKE '%//%'
            GROUP BY c.name
            ORDER BY c.edhrec_rank ASC NULLS LAST
        """
        cards: list[dict[str, Any]] = []
        async with db._execute(query) as cursor:
            async for row in cursor:
                cards.append(dict(row))
        return cards

    def _build_document(self, card: dict[str, Any]) -> str:
        """Build a text document from card features for TF-IDF."""
        parts: list[str] = []

        # Card name (weighted by repeating)
        name = card.get("name", "")
        if name:
            parts.append(name)
            parts.append(name)  # Repeat for weight

        # Type line
        type_line = card.get("type", "")
        if type_line:
            parts.append(type_line)

        # Oracle text
        text = card.get("text", "")
        if text:
            # Clean up mana symbols for better matching
            text = self._clean_mana_symbols(text)
            parts.append(text)

        # Keywords (important for synergy)
        keywords = card.get("keywords", "")
        if keywords:
            if isinstance(keywords, str):
                parts.append(keywords.replace(",", " "))
            elif isinstance(keywords, list):
                parts.append(" ".join(keywords))

        # Subtypes (tribal)
        subtypes = card.get("subtypes", "")
        if subtypes:
            if isinstance(subtypes, str):
                # Repeat subtypes for tribal weight
                subtypes_list = subtypes.replace(",", " ")
                parts.append(subtypes_list)
                parts.append(subtypes_list)
            elif isinstance(subtypes, list):
                subtypes_str = " ".join(subtypes)
                parts.append(subtypes_str)
                parts.append(subtypes_str)

        # Colors (for color identity matching)
        colors = card.get("colors", "")
        if colors:
            if isinstance(colors, str):
                color_names = self._expand_colors(colors)
                parts.append(color_names)
            elif isinstance(colors, list):
                color_names = self._expand_colors(",".join(colors))
                parts.append(color_names)

        return " ".join(parts)

    def _clean_mana_symbols(self, text: str) -> str:
        """Convert mana symbols to words for better TF-IDF matching."""
        replacements = {
            "{W}": "white mana",
            "{U}": "blue mana",
            "{B}": "black mana",
            "{R}": "red mana",
            "{G}": "green mana",
            "{C}": "colorless mana",
            "{T}": "tap",
            "{Q}": "untap",
            "{X}": "variable",
        }
        for symbol, word in replacements.items():
            text = text.replace(symbol, word)
        return text

    def _expand_colors(self, colors: str) -> str:
        """Expand color codes to full names."""
        color_map = {
            "W": "white",
            "U": "blue",
            "B": "black",
            "R": "red",
            "G": "green",
        }
        expanded: list[str] = []
        for char in colors.upper():
            if char in color_map:
                expanded.append(color_map[char])
        return " ".join(expanded)

    def find_similar(
        self,
        card_name: str,
        n: int = 10,
        exclude_self: bool = True,
    ) -> list[CardRecommendation]:
        """Find cards similar to the given card.

        Args:
            card_name: Name of the source card.
            n: Number of recommendations to return.
            exclude_self: Whether to exclude the source card from results.

        Returns:
            List of CardRecommendation sorted by similarity score.
        """
        from sklearn.metrics.pairwise import cosine_similarity

        if not self._initialized or self._tfidf_matrix is None:
            raise RuntimeError("Recommender not initialized. Call initialize() first.")

        if card_name not in self._name_to_idx:
            # Try case-insensitive match
            card_name_lower = card_name.lower()
            for name in self._card_names:
                if name.lower() == card_name_lower:
                    card_name = name
                    break
            else:
                return []

        idx = self._name_to_idx[card_name]
        card_vector = self._tfidf_matrix[idx : idx + 1]

        # Compute similarities
        similarities = cosine_similarity(card_vector, self._tfidf_matrix).flatten()

        # Get top N indices (excluding self if requested)
        top_indices = np.argsort(similarities)[::-1]

        results: list[CardRecommendation] = []
        for i in top_indices:
            if len(results) >= n:
                break
            name = self._card_names[i]
            if exclude_self and name == card_name:
                continue

            card_data = self._card_data[name]
            results.append(
                CardRecommendation(
                    name=name,
                    score=float(similarities[i]),
                    uuid=card_data.get("uuid"),
                    type_line=card_data.get("type"),
                    mana_cost=card_data.get("manaCost"),
                    colors=self._parse_colors(card_data.get("colors")),
                )
            )

        return results

    def find_similar_to_text(
        self,
        text: str,
        n: int = 10,
    ) -> list[CardRecommendation]:
        """Find cards similar to arbitrary text (e.g., deck description).

        Args:
            text: Free-form text describing desired card characteristics.
            n: Number of recommendations to return.

        Returns:
            List of CardRecommendation sorted by similarity score.
        """
        from sklearn.metrics.pairwise import cosine_similarity

        if not self._initialized or self._vectorizer is None or self._tfidf_matrix is None:
            raise RuntimeError("Recommender not initialized. Call initialize() first.")

        # Transform text to TF-IDF vector
        text_vector = self._vectorizer.transform([text])

        # Compute similarities
        similarities = cosine_similarity(text_vector, self._tfidf_matrix).flatten()

        # Get top N indices
        top_indices = np.argsort(similarities)[::-1][:n]

        results: list[CardRecommendation] = []
        for i in top_indices:
            name = self._card_names[i]
            card_data = self._card_data[name]
            results.append(
                CardRecommendation(
                    name=name,
                    score=float(similarities[i]),
                    uuid=card_data.get("uuid"),
                    type_line=card_data.get("type"),
                    mana_cost=card_data.get("manaCost"),
                    colors=self._parse_colors(card_data.get("colors")),
                )
            )

        return results

    def find_similar_to_cards(
        self,
        card_names: list[str],
        n: int = 10,
        exclude_input: bool = True,
    ) -> list[CardRecommendation]:
        """Find cards similar to a group of cards (e.g., a deck).

        Computes the centroid of the input cards and finds cards similar to it.

        Args:
            card_names: List of card names.
            n: Number of recommendations to return.
            exclude_input: Whether to exclude input cards from results.

        Returns:
            List of CardRecommendation sorted by similarity score.
        """
        from sklearn.metrics.pairwise import cosine_similarity

        if not self._initialized or self._tfidf_matrix is None:
            raise RuntimeError("Recommender not initialized. Call initialize() first.")

        # Get indices for valid cards
        indices: list[int] = []
        input_set: set[str] = set()
        for name in card_names:
            if name in self._name_to_idx:
                indices.append(self._name_to_idx[name])
                input_set.add(name)
            else:
                # Try case-insensitive
                name_lower = name.lower()
                for stored_name in self._card_names:
                    if stored_name.lower() == name_lower:
                        indices.append(self._name_to_idx[stored_name])
                        input_set.add(stored_name)
                        break

        if not indices:
            return []

        # Compute centroid (mean) of card vectors
        card_vectors = self._tfidf_matrix[indices]
        centroid = card_vectors.mean(axis=0)

        # Convert to 2D array for cosine_similarity
        centroid_2d: NDArray[np.float64] = np.asarray(centroid)

        # Compute similarities
        similarities = cosine_similarity(centroid_2d, self._tfidf_matrix).flatten()

        # Get top N indices
        top_indices = np.argsort(similarities)[::-1]

        results: list[CardRecommendation] = []
        for i in top_indices:
            if len(results) >= n:
                break
            name = self._card_names[i]
            if exclude_input and name in input_set:
                continue

            card_data = self._card_data[name]
            results.append(
                CardRecommendation(
                    name=name,
                    score=float(similarities[i]),
                    uuid=card_data.get("uuid"),
                    type_line=card_data.get("type"),
                    mana_cost=card_data.get("manaCost"),
                    colors=self._parse_colors(card_data.get("colors")),
                )
            )

        return results

    def _parse_colors(self, colors: Any) -> list[str] | None:
        """Parse colors from database format."""
        if colors is None:
            return None
        if isinstance(colors, list):
            return [str(c) for c in colors]
        if isinstance(colors, str):
            # Could be JSON or comma-separated
            colors = colors.strip()
            if colors.startswith("["):
                try:
                    parsed = json.loads(colors)
                    if isinstance(parsed, list):
                        return [str(c) for c in parsed]
                except (json.JSONDecodeError, TypeError):
                    pass
            return [c.strip() for c in colors.split(",") if c.strip()]
        return None

    @property
    def is_initialized(self) -> bool:
        """Check if the recommender has been initialized."""
        return self._initialized

    @property
    def card_count(self) -> int:
        """Number of cards in the index."""
        return len(self._card_names)


# Global singleton instance
_recommender: CardRecommender | None = None


def get_recommender() -> CardRecommender:
    """Get or create the global recommender instance."""
    global _recommender
    if _recommender is None:
        _recommender = CardRecommender()
    return _recommender


async def initialize_recommender(db: UnifiedDatabase) -> float:
    """Initialize the global recommender with database.

    Returns:
        Time taken to initialize in seconds.
    """
    recommender = get_recommender()
    return await recommender.initialize(db)
