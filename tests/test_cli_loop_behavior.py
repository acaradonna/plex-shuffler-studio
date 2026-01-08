from __future__ import annotations

import plex_shuffler.cli as cli


def test_run_without_loop_runs_once(monkeypatch):
    # This test ensures the CLI no longer loops just because schedule interval is set.
    config = {
        "plex": {"url": "http://example", "token": "t"},
        "schedule": {"interval_minutes": 10, "jitter_seconds": 0},
        "playlists": [{"name": "P", "tv": {"library": "TV"}, "movies": {"enabled": False}}],
    }

    class _Args:
        config = "config.json"
        verbose = False
        command = "run"
        dry_run = True
        print_count = 0
        playlist = []
        loop = False
        once = False
        interval_minutes = 0

    ran = {"count": 0}

    def fake_load_config(_path: str):
        return config

    def fake_validate_config(_cfg):
        return None

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

    def fake_build_playlist_items(_client, _playlist_cfg, _now):
        ran["count"] += 1
        return ([], type("Stats", (), {"shows": 0, "episodes": 0, "movies": 0, "total_items": 0})())

    monkeypatch.setattr(cli, "load_config", fake_load_config)
    monkeypatch.setattr(cli, "validate_config", fake_validate_config)
    monkeypatch.setattr(cli, "PlexClient", _FakeClient)
    monkeypatch.setattr(cli, "build_playlist_items", fake_build_playlist_items)

    def fake_parse_args():
        return _Args()

    monkeypatch.setattr(cli.argparse.ArgumentParser, "parse_args", lambda self: fake_parse_args())

    assert cli.main() == 0
    assert ran["count"] == 1
