import pytest

from plex_shuffler.config import ConfigError, validate_config


def test_validate_config_reports_enum_and_range_errors() -> None:
    bad = {
        "plex": {"url": "localhost:32400", "token": "", "timeout_seconds": 0},
        "playlists": [
            {
                "name": "",
                "tv": {
                    "library": "",
                    "order": {"strategy": "bogus", "chunk_size": 0},
                    "episode_filters": {"exclude_watched_days": -1, "max_per_show": -5},
                    "include_titles": "not-a-list",
                },
                "movies": {
                    "enabled": True,
                    "library": "",
                    "ratio": {"every_episodes": 0, "max_movies": 3},
                    "order": {"strategy": "random", "chunk_size": 0},
                },
                "output": {"mode": "explode", "chunk_size": 0, "limit_items": -1},
            }
        ],
    }

    with pytest.raises(ConfigError) as exc:
        validate_config(bad)

    message = str(exc.value)
    assert "plex.url must start with http:// or https://" in message
    assert "plex.token is required" in message
    assert "plex.timeout_seconds must be > 0" in message
    assert "playlists[1].name is required" in message
    assert "playlists[1].tv.library is required" in message
    assert "playlists[1].tv.order.strategy must be one of" in message
    assert "playlists[1].tv.order.chunk_size must be > 0" in message
    assert "playlists[1].tv.episode_filters.exclude_watched_days must be >= 0" in message
    assert "playlists[1].movies.library is required when movies.enabled=true" in message
    assert "playlists[1].movies.ratio.max_movies requires movies.ratio.every_episodes > 0" in message
    assert "playlists[1].output.mode must be one of" in message


def test_validate_config_accepts_minimal_valid_config() -> None:
    good = {
        "plex": {"url": "http://localhost:32400", "token": "token", "timeout_seconds": 30},
        "playlists": [
            {
                "name": "Test",
                "tv": {"library": "TV", "order": {"strategy": "rounds", "chunk_size": 1}},
                "movies": {"enabled": False},
                "output": {"mode": "replace", "chunk_size": 200, "limit_items": 0},
            }
        ],
    }

    validate_config(good)
