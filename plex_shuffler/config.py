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


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _as_str(value: Any) -> str:
    return "" if value is None else str(value)


def _require_non_negative_int(errors: list[str], path: str, value: Any) -> None:
    if value is None:
        return
    if not _is_int(value):
        errors.append(f"{path} must be an integer")
        return
    if value < 0:
        errors.append(f"{path} must be >= 0")


def _require_positive_int(errors: list[str], path: str, value: Any) -> None:
    if value is None:
        return
    if not _is_int(value):
        errors.append(f"{path} must be an integer")
        return
    if value <= 0:
        errors.append(f"{path} must be > 0")


def _require_enum(errors: list[str], path: str, value: Any, allowed: set[str]) -> None:
    if value is None:
        return
    raw = _as_str(value).strip()
    if not raw:
        return
    normalized = raw.lower()
    if normalized not in allowed:
        errors.append(f"{path} must be one of: {', '.join(sorted(allowed))}")


def _require_list_of_strings(errors: list[str], path: str, value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        errors.append(f"{path} must be a list")
        return
    for idx, entry in enumerate(value):
        if not isinstance(entry, str):
            errors.append(f"{path}[{idx}] must be a string")


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
    plex_url = _as_str(plex.get("url")).strip()
    if not plex_url:
        errors.append("plex.url is required")
    elif not (plex_url.startswith("http://") or plex_url.startswith("https://")):
        errors.append("plex.url must start with http:// or https://")

    plex_token = _as_str(plex.get("token")).strip()
    if not plex_token:
        errors.append("plex.token is required (or set PLEX_TOKEN env var)")

    _require_positive_int(errors, "plex.timeout_seconds", plex.get("timeout_seconds"))

    playlists = config.get("playlists", [])
    if not playlists:
        errors.append("playlists must contain at least one playlist")

    for idx, playlist in enumerate(playlists, start=1):
        base = f"playlists[{idx}]"
        if not isinstance(playlist, dict):
            errors.append(f"{base} must be an object")
            continue
        name = playlist.get("name")
        if not name:
            errors.append(f"{base}.name is required")
        tv = playlist.get("tv", {})
        if not tv.get("library"):
            errors.append(f"{base}.tv.library is required")

        _require_list_of_strings(errors, f"{base}.tv.include_titles", tv.get("include_titles"))
        _require_list_of_strings(errors, f"{base}.tv.exclude_titles", tv.get("exclude_titles"))

        episode_filters = tv.get("episode_filters", {}) if isinstance(tv.get("episode_filters"), dict) else {}
        _require_non_negative_int(errors, f"{base}.tv.episode_filters.exclude_watched_days", episode_filters.get("exclude_watched_days"))
        _require_non_negative_int(errors, f"{base}.tv.episode_filters.max_per_show", episode_filters.get("max_per_show"))

        tv_order = tv.get("order", {}) if isinstance(tv.get("order"), dict) else {}
        _require_enum(errors, f"{base}.tv.order.strategy", tv_order.get("strategy"), {"rounds", "round_robin", "random"})
        _require_positive_int(errors, f"{base}.tv.order.chunk_size", tv_order.get("chunk_size"))

        movies = playlist.get("movies", {})
        if movies.get("enabled") and not movies.get("library"):
            errors.append(f"{base}.movies.library is required when movies.enabled=true")

        if isinstance(movies, dict):
            _require_list_of_strings(errors, f"{base}.movies.include_collections", movies.get("include_collections"))
            _require_list_of_strings(errors, f"{base}.movies.exclude_collections", movies.get("exclude_collections"))

            movie_order = movies.get("order", {}) if isinstance(movies.get("order"), dict) else {}
            _require_enum(errors, f"{base}.movies.order.strategy", movie_order.get("strategy"), {"rounds", "round_robin", "random"})
            _require_positive_int(errors, f"{base}.movies.order.chunk_size", movie_order.get("chunk_size"))

            ratio = movies.get("ratio", {}) if isinstance(movies.get("ratio"), dict) else {}
            every = ratio.get("every_episodes")
            max_movies = ratio.get("max_movies")
            _require_non_negative_int(errors, f"{base}.movies.ratio.every_episodes", every)
            _require_non_negative_int(errors, f"{base}.movies.ratio.max_movies", max_movies)
            if _is_int(max_movies) and max_movies > 0:
                if not (_is_int(every) and every > 0):
                    errors.append(f"{base}.movies.ratio.max_movies requires movies.ratio.every_episodes > 0")

            movie_filters = movies.get("filters", {}) if isinstance(movies.get("filters"), dict) else {}
            _require_non_negative_int(errors, f"{base}.movies.filters.exclude_watched_days", movie_filters.get("exclude_watched_days"))

        output_cfg = playlist.get("output", {})
        if isinstance(output_cfg, dict):
            _require_enum(errors, f"{base}.output.mode", output_cfg.get("mode"), {"replace", "append"})
            _require_non_negative_int(errors, f"{base}.output.limit_items", output_cfg.get("limit_items"))
            _require_positive_int(errors, f"{base}.output.chunk_size", output_cfg.get("chunk_size"))

    if errors:
        raise ConfigError("Config errors:\n- " + "\n- ".join(errors))
