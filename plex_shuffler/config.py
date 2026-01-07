"""Load and validate Plex Shuffler Studio configuration."""

from __future__ import annotations

import json
import os
from typing import Any

from plex_shuffler.utils import merge_dicts

DEFAULTS: dict[str, Any] = {
    "plex": {
        "url": "http://localhost:32400",
        "token": "",
        "timeout_seconds": 30,
        "client_id": "",
    },
    "schedule": {
        "interval_minutes": 0,
        "jitter_seconds": 30,
    },
    "playlists": [],
}

DEFAULT_PLAYLIST: dict[str, Any] = {
    "name": "",
    "description": "",
    "tv": {
        "library": "",
        "query": "",
        "include_titles": [],
        "exclude_titles": [],
        "episode_filters": {
            "unwatched_only": False,
            "exclude_watched_days": 0,
            "max_per_show": 0,
        },
        "order": {
            "strategy": "rounds",
            "chunk_size": 1,
            "seed": "",
        },
    },
    "movies": {
        "enabled": False,
        "library": "",
        "query": "",
        "collections_as_shows": False,
        "include_collections": [],
        "exclude_collections": [],
        "order": {
            "strategy": "rounds",
            "chunk_size": 1,
            "seed": "",
        },
        "ratio": {
            "every_episodes": 0,
            "max_movies": 0,
        },
        "filters": {
            "unwatched_only": False,
            "exclude_watched_days": 0,
        },
    },
    "output": {
        "mode": "replace",
        "limit_items": 0,
        "chunk_size": 200,
    },
}


class ConfigError(ValueError):
    pass


def default_playlist(name: str = "New Playlist") -> dict[str, Any]:
    playlist = merge_dicts(DEFAULT_PLAYLIST, {})
    playlist["name"] = name
    return playlist


def default_config() -> dict[str, Any]:
    return merge_dicts(DEFAULTS, {"playlists": [default_playlist()]})


def _resolve_token(raw_token: str) -> str:
    token = raw_token or ""
    token = token.strip()
    if token.startswith("env:"):
        env_name = token.split(":", 1)[1].strip()
        return os.getenv(env_name, "").strip()
    if token.startswith("$"):
        env_name = token[1:]
        return os.getenv(env_name, "").strip()
    if not token:
        return os.getenv("PLEX_TOKEN", "").strip()
    return token


def _normalize_playlist(raw: dict[str, Any]) -> dict[str, Any]:
    return merge_dicts(DEFAULT_PLAYLIST, raw)


def load_config(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)

    config = merge_dicts(DEFAULTS, raw)
    playlists = []
    for entry in raw.get("playlists", []):
        playlists.append(_normalize_playlist(entry))
    config["playlists"] = playlists

    config["plex"]["token"] = _resolve_token(config["plex"].get("token", ""))
    return config


def load_config_raw(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        return default_config()

    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)

    config = merge_dicts(DEFAULTS, raw)
    playlists = []
    for entry in raw.get("playlists", []):
        playlists.append(_normalize_playlist(entry))
    if not playlists:
        playlists = [default_playlist()]
    config["playlists"] = playlists
    return config


def save_config(path: str, config: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2, sort_keys=False)
        handle.write("\n")


def apply_plex_overrides(config: dict[str, Any], plex_url: str | None) -> dict[str, Any]:
    if plex_url is None:
        return config
    url = plex_url.strip()
    if not url:
        return config
    config.setdefault("plex", {})["url"] = url
    return config


def validate_config(config: dict[str, Any]) -> None:
    errors: list[str] = []
    plex = config.get("plex", {})
    if not plex.get("url"):
        errors.append("plex.url is required")
    if not plex.get("token"):
        errors.append("plex.token is required (or set PLEX_TOKEN env var)")

    playlists = config.get("playlists", [])
    if not playlists:
        errors.append("playlists must contain at least one playlist")

    for idx, playlist in enumerate(playlists, start=1):
        name = playlist.get("name")
        if not name:
            errors.append(f"playlists[{idx}].name is required")
        tv = playlist.get("tv", {})
        if not tv.get("library"):
            errors.append(f"playlists[{idx}].tv.library is required")
        movies = playlist.get("movies", {})
        if movies.get("enabled") and not movies.get("library"):
            errors.append(f"playlists[{idx}].movies.library is required when movies.enabled=true")

    if errors:
        raise ConfigError("Config errors:\n- " + "\n- ".join(errors))
