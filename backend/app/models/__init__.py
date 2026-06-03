"""
Import every model here so SQLAlchemy's metadata is populated by the time
anyone calls Base.metadata.create_all (tests) or Alembic autogen scans.
"""
from app.models.audit import AuditLog
from app.models.availability import AvailabilityWindow, MaturityRating
from app.models.episode import Episode, EpisodeAsset
from app.models.genre import Genre
from app.models.language import AudioTrack, SubtitleTrack
from app.models.person import Person, TitleCredit
from app.models.profile import Profile
from app.models.reaction import Reaction
from app.models.refresh_token import RefreshToken
from app.models.season import Season
from app.models.subscription import Plan, Subscription
from app.models.title import Title, TitleAsset, titles_genres
from app.models.user import User
from app.models.watch_progress import WatchProgress
from app.models.watchlist import WatchlistItem
from app.models.webhook_event import WebhookEvent

__all__ = [
    "AuditLog",
    "AudioTrack",
    "AvailabilityWindow",
    "Episode",
    "EpisodeAsset",
    "Genre",
    "MaturityRating",
    "Person",
    "Plan",
    "Profile",
    "Reaction",
    "RefreshToken",
    "Season",
    "SubtitleTrack",
    "Subscription",
    "Title",
    "TitleAsset",
    "TitleCredit",
    "User",
    "WatchProgress",
    "WatchlistItem",
    "WebhookEvent",
    "titles_genres",
]
