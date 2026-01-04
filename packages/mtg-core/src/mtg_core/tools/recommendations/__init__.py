"""Card recommendation system using TF-IDF similarity and hybrid scoring."""

from .deck_finder import DeckFinder, get_deck_finder
from .features import CardEncoder, CardFeatures, DeckEncoder, DeckFeatures
from .gameplay import (
    GameplayCardStats,
    GameplayDB,
    get_gameplay_db,
)
from .hybrid import (
    ComboMatch,
    ComboPieceDetector,
    HybridRecommender,
    ScoredRecommendation,
    SynergyScorer,
    get_hybrid_recommender,
    initialize_hybrid_recommender,
)
from .models import (
    CardData,
    ComboSummary,
    CommanderMatch,
    DeckFilters,
    DeckSuggestion,
    FilterResult,
)
from .tfidf import (
    CardRecommendation,
    CardRecommender,
    get_recommender,
    initialize_recommender,
)

__all__ = [
    "CardData",
    "CardEncoder",
    "CardFeatures",
    "CardRecommendation",
    "CardRecommender",
    "ComboMatch",
    "ComboPieceDetector",
    "ComboSummary",
    "CommanderMatch",
    "DeckEncoder",
    "DeckFeatures",
    "DeckFilters",
    "DeckFinder",
    "DeckSuggestion",
    "FilterResult",
    "GameplayCardStats",
    "GameplayDB",
    "HybridRecommender",
    "ScoredRecommendation",
    "SynergyScorer",
    "get_deck_finder",
    "get_gameplay_db",
    "get_hybrid_recommender",
    "get_recommender",
    "initialize_hybrid_recommender",
    "initialize_recommender",
]
