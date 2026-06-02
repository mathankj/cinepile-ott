"""
Import every model here so SQLAlchemy's metadata is populated by the time
anyone calls Base.metadata.create_all (tests) or Alembic autogen scans.
"""
from app.models.film import Category, Film, FilmAsset, films_categories
from app.models.refresh_token import RefreshToken
from app.models.subscription import Plan, Subscription
from app.models.user import User
from app.models.watch_history import WatchHistory

__all__ = [
    "Category",
    "Film",
    "FilmAsset",
    "Plan",
    "RefreshToken",
    "Subscription",
    "User",
    "WatchHistory",
    "films_categories",
]
