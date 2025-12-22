"""Card recommendation system using TF-IDF similarity and hybrid scoring."""

from .features import CardEncoder, CardFeatures, DeckEncoder, DeckFeatures
from .hybrid import (
    ComboMatch,
    ComboPieceDetector,
    HybridRecommender,
    ScoredRecommendation,
    SynergyScorer,
    get_hybrid_recommender,
    initialize_hybrid_recommender,
)
from .limited_stats import (
    LimitedCardStats,
    LimitedStatsDB,
    get_limited_stats_db,
)
from .tfidf import (
    CardRecommendation,
    CardRecommender,
    get_recommender,
    initialize_recommender,
)

__all__ = [
    # Features
    "CardEncoder",
    "CardFeatures",
    # TF-IDF
    "CardRecommendation",
    "CardRecommender",
    # Hybrid
    "ComboMatch",
    "ComboPieceDetector",
    "DeckEncoder",
    "DeckFeatures",
    "HybridRecommender",
    # Limited Stats (17lands)
    "LimitedCardStats",
    "LimitedStatsDB",
    "ScoredRecommendation",
    "SynergyScorer",
    "get_hybrid_recommender",
    "get_limited_stats_db",
    "get_recommender",
    "initialize_hybrid_recommender",
    "initialize_recommender",
]
