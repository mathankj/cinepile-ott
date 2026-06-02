"""Home / browse-rows response."""
from __future__ import annotations

from pydantic import BaseModel

from app.schemas.title import TitleSummary


class HomeRow(BaseModel):
    kind: str
    # row identifier — frontend can switch on this for rendering nuances.
    # Examples: 'continue_watching', 'my_list', 'new_releases', 'trending_now',
    # 'top_in_country', 'because_you_watched:42', 'genre:action'
    title: str
    items: list[TitleSummary]


class HomeResponse(BaseModel):
    rows: list[HomeRow]
