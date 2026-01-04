"""API route registration."""

from fastapi import APIRouter

from .artists import router as artists_router
from .cards import router as cards_router
from .collection import router as collection_router
from .combos import router as combos_router
from .decks import router as decks_router
from .recommendations import router as recommendations_router
from .sets import router as sets_router
from .setup import router as setup_router
from .synergies import router as synergies_router
from .user import router as user_router

api_router = APIRouter()

api_router.include_router(artists_router, prefix="/artists", tags=["artists"])
api_router.include_router(cards_router, prefix="/cards", tags=["cards"])
api_router.include_router(collection_router, prefix="/collection", tags=["collection"])

api_router.include_router(sets_router, prefix="/sets", tags=["sets"])
api_router.include_router(synergies_router, prefix="/synergies", tags=["synergies"])
api_router.include_router(combos_router, prefix="/combos", tags=["combos"])
api_router.include_router(
    recommendations_router, prefix="/recommendations", tags=["recommendations"]
)
api_router.include_router(decks_router, prefix="/decks", tags=["decks"])
api_router.include_router(user_router, prefix="/user", tags=["user"])
api_router.include_router(setup_router, prefix="/setup", tags=["setup"])

__all__ = ["api_router"]
