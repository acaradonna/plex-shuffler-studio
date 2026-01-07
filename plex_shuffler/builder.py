"""Playlist builder that assembles shuffled media items."""

from __future__ import annotations

import datetime as dt
import fnmatch
import logging
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from plex_shuffler.models import MediaGroup, MediaItem
from plex_shuffler.plex_client import PlexClient
from plex_shuffler.shuffle import interleave_movies, shuffle_groups
from plex_shuffler.utils import cutoff_from_days, ensure_list, parse_query_string

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class BuildStats:
    shows: int
    episodes: int
    movies: int
    collections: int
    total_items: int


def build_playlist_items(
    client: PlexClient,
    playlist_config: dict,
    now: dt.datetime,
) -> tuple[list[MediaItem], BuildStats]:
    tv_config = playlist_config.get("tv", {})
    movie_config = playlist_config.get("movies", {})
    output_config = playlist_config.get("output", {})

    tv_groups = _build_tv_groups(client, tv_config, now)
    tv_rng = _create_rng(tv_config.get("order", {}).get("seed"), now)
    tv_items = shuffle_groups(
        tv_groups,
        tv_rng,
        strategy=tv_config.get("order", {}).get("strategy", "rounds"),
        chunk_size=int(tv_config.get("order", {}).get("chunk_size", 1) or 1),
    )

    movie_items: list[MediaItem] = []
    collections_count = 0
    if movie_config.get("enabled"):
        movie_groups, collections_count = _build_movie_groups(client, movie_config, now)
        movie_rng = _create_rng(movie_config.get("order", {}).get("seed"), now)
        movie_items = shuffle_groups(
            movie_groups,
            movie_rng,
            strategy=movie_config.get("order", {}).get("strategy", "rounds"),
            chunk_size=int(movie_config.get("order", {}).get("chunk_size", 1) or 1),
        )
        ratio = int(movie_config.get("ratio", {}).get("every_episodes", 0) or 0)
        max_movies = int(movie_config.get("ratio", {}).get("max_movies", 0) or 0)
        if max_movies > 0:
            movie_items = movie_items[:max_movies]
        tv_items = interleave_movies(tv_items, movie_items, ratio)

    limit = int(output_config.get("limit_items", 0) or 0)
    if limit > 0:
        tv_items = tv_items[:limit]

    stats = BuildStats(
        shows=len(tv_groups),
        episodes=sum(1 for item in tv_items if item.type == "episode"),
        movies=sum(1 for item in tv_items if item.type == "movie"),
        collections=collections_count,
        total_items=len(tv_items),
    )
    return tv_items, stats


def _build_tv_groups(client: PlexClient, tv_config: dict, now: dt.datetime) -> list[MediaGroup]:
    section = client.get_section_by_title(tv_config.get("library", ""))
    query = parse_query_string(tv_config.get("query", ""))

    shows = client.get_shows(section.key, query=query)
    shows = _filter_titles(
        shows,
        include=ensure_list(tv_config.get("include_titles")),
        exclude=ensure_list(tv_config.get("exclude_titles")),
    )

    episode_filters = tv_config.get("episode_filters", {})
    max_per_show = int(episode_filters.get("max_per_show", 0) or 0)
    cutoff = cutoff_from_days(episode_filters.get("exclude_watched_days"), now)
    unwatched_only = bool(episode_filters.get("unwatched_only"))

    groups: list[MediaGroup] = []
    if not shows:
        return groups

    max_workers = min(8, max(1, len(shows)))
    LOGGER.info("Fetching episodes for %s shows", len(shows))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(client.get_show_episodes, show.rating_key, None): show
            for show in shows
        }
        for future in as_completed(futures):
            show = futures[future]
            try:
                episodes = future.result()
            except Exception as exc:  # pragma: no cover - defensive
                LOGGER.warning("Failed to fetch episodes for %s: %s", show.title, exc)
                continue
            filtered = _filter_watched(episodes, cutoff, unwatched_only)
            ordered = sorted(filtered, key=_episode_sort_key)
            if max_per_show > 0:
                ordered = ordered[:max_per_show]
            if not ordered:
                continue
            groups.append(MediaGroup(name=show.title, items=ordered, source="show"))
    return groups


def _build_movie_groups(
    client: PlexClient,
    movie_config: dict,
    now: dt.datetime,
) -> tuple[list[MediaGroup], int]:
    section = client.get_section_by_title(movie_config.get("library", ""))
    query = parse_query_string(movie_config.get("query", ""))

    cutoff = cutoff_from_days(movie_config.get("filters", {}).get("exclude_watched_days"), now)
    unwatched_only = bool(movie_config.get("filters", {}).get("unwatched_only"))

    if movie_config.get("collections_as_shows"):
        collections = client.get_collections(section.key, query=query)
        collections = _filter_titles(
            collections,
            include=ensure_list(movie_config.get("include_collections")),
            exclude=ensure_list(movie_config.get("exclude_collections")),
        )
        groups = []
        for collection in collections:
            items = client.get_collection_items(collection.rating_key)
            filtered = _filter_watched(items, cutoff, unwatched_only)
            ordered = sorted(filtered, key=_movie_sort_key)
            if not ordered:
                continue
            groups.append(
                MediaGroup(
                    name=collection.title,
                    items=ordered,
                    source="collection",
                )
            )
        return groups, len(collections)

    movies = client.get_movies(section.key, query=query)
    filtered_movies = _filter_watched(movies, cutoff, unwatched_only)
    groups = [MediaGroup(name=movie.title, items=[movie], source="movie") for movie in filtered_movies]
    return groups, 0


def _filter_titles(items: list[MediaItem], include: list[str], exclude: list[str]) -> list[MediaItem]:
    include_patterns = [pattern.strip().lower() for pattern in include if pattern]
    exclude_patterns = [pattern.strip().lower() for pattern in exclude if pattern]

    def matches(patterns: list[str], title: str) -> bool:
        if not patterns:
            return True
        lowered = title.lower()
        return any(fnmatch.fnmatch(lowered, pattern) for pattern in patterns)

    results: list[MediaItem] = []
    for item in items:
        title = item.title or ""
        if include_patterns and not matches(include_patterns, title):
            continue
        if exclude_patterns and matches(exclude_patterns, title):
            continue
        results.append(item)
    return results


def _filter_watched(
    items: list[MediaItem],
    cutoff: dt.datetime | None,
    unwatched_only: bool,
) -> list[MediaItem]:
    filtered = []
    for item in items:
        if unwatched_only and item.view_count:
            continue
        if cutoff and item.last_viewed_at and item.last_viewed_at >= cutoff:
            continue
        filtered.append(item)
    return filtered


def _episode_sort_key(item: MediaItem) -> tuple:
    season = item.season_index if item.season_index is not None else 0
    episode = item.episode_index if item.episode_index is not None else 0
    date = item.originally_available_at or dt.date.min
    return (season, episode, date, item.title)


def _movie_sort_key(item: MediaItem) -> tuple:
    date = item.originally_available_at or dt.date.min
    return (date, item.title)


def _create_rng(seed: str | None, now: dt.datetime) -> random.Random:
    if not seed:
        return random.Random()
    seed_value = seed.strip().lower()
    if seed_value == "daily":
        return random.Random(int(now.strftime("%Y%m%d")))
    if seed_value == "weekly":
        return random.Random(int(now.strftime("%G%V")))
    if seed_value == "monthly":
        return random.Random(int(now.strftime("%Y%m")))
    try:
        return random.Random(int(seed_value))
    except ValueError:
        return random.Random(seed_value)
