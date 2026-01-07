"""Dataclasses for Plex media items and groupings."""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt


@dataclass(frozen=True)
class LibrarySection:
    key: str
    title: str
    type: str


@dataclass(frozen=True)
class MediaItem:
    rating_key: str
    title: str
    type: str
    show_title: str | None = None
    season_index: int | None = None
    episode_index: int | None = None
    collection_title: str | None = None
    originally_available_at: dt.date | None = None
    view_count: int | None = None
    last_viewed_at: dt.datetime | None = None


@dataclass
class MediaGroup:
    name: str
    items: list[MediaItem]
    source: str


@dataclass(frozen=True)
class PlaylistInfo:
    rating_key: str
    title: str
    playlist_type: str
