# Plex Shuffler Studio (MVP)

A fast, configurable playlist builder for Plex that shuffles shows while keeping episode order intact. Designed for “live-TV-like” playlists, with optional movie drops and automation.

## What this does

- Shuffle shows while keeping each show’s episodes sequential.
- Mix movies into the playlist at a configurable ratio.
- Treat movie collections as mini “shows” to keep their order.
- Filter by Plex query strings (smart-list style) and watch history.
- Re-generate playlists on a schedule or via cron.

## Requirements

- Python 3.10+
- Plex server URL + Plex token

## Quick start

1) Create a config file:

```json
{
  "plex": {
    "url": "http://localhost:32400",
    "token": "$PLEX_TOKEN",
    "timeout_seconds": 30
  },
  "schedule": {
    "interval_minutes": 360,
    "jitter_seconds": 60
  },
  "playlists": [
    {
      "name": "Animation Shuffle",
      "description": "Shuffled shows with movie drops",
      "tv": {
        "library": "TV Shows",
        "query": "genre=Animation",
        "exclude_titles": ["*News*"],
        "episode_filters": {
          "unwatched_only": false,
          "exclude_watched_days": 14,
          "max_per_show": 50
        },
        "order": {
          "strategy": "rounds",
          "chunk_size": 1,
          "seed": "daily"
        }
      },
      "movies": {
        "enabled": true,
        "library": "Movies",
        "query": "genre=Animation",
        "collections_as_shows": true,
        "include_collections": ["Pixar*"],
        "ratio": {
          "every_episodes": 6,
          "max_movies": 12
        },
        "filters": {
          "exclude_watched_days": 30
        },
        "order": {
          "strategy": "rounds",
          "chunk_size": 1,
          "seed": "daily"
        }
      },
      "output": {
        "mode": "replace",
        "limit_items": 400,
        "chunk_size": 200
      }
    }
  ]
}
```

2) List libraries:

```bash
python -m plex_shuffler --config config.json libraries
```

3) Run once (dry-run + preview):

```bash
python -m plex_shuffler --config config.json run --dry-run --print 20
```

4) Run and sync playlists:

```bash
python -m plex_shuffler --config config.json run
```

5) Run continuously using the schedule in config:

```bash
python -m plex_shuffler --config config.json run --loop
```

## Web UI

Launch the web UI for a non-code setup flow:

```bash
python -m plex_shuffler.web --config config.json --host 127.0.0.1 --port 8181
```

Then open `http://127.0.0.1:8181` in your browser. Use the Connect button to authorize Plex in a new tab. The UI saves your token to `config.json` and lets you configure playlists, preview, and generate.

The query builder exposes a curated catalog of common Plex fields (genre, unwatched, year, collection, content rating, studio), plus a Custom filter escape hatch for any raw key/value. Multiselect fields load options from Plex when a library is selected, and you can add "Other..." values that persist. Switch to Advanced mode to paste a raw query string; it is used verbatim.

## Configuration details

### TV selection

- `tv.library`: Plex library name.
- `tv.query`: Optional Plex query string (smart-list style). Example: `genre=Animation&unwatched=1`.
- `tv.include_titles` / `tv.exclude_titles`: Optional wildcard patterns (`*` supported).
- `tv.episode_filters.exclude_watched_days`: Skip episodes watched recently.
- `tv.episode_filters.unwatched_only`: Only include unwatched episodes.
- `tv.episode_filters.max_per_show`: Cap episodes per show.
- `tv.order.strategy`: `rounds` (shuffle each round), `round_robin`, or `random`.
- `tv.order.chunk_size`: How many episodes per show before switching.
- `tv.order.seed`: `daily`, `weekly`, `monthly`, or a numeric/string seed.

### Movie mixing

- `movies.enabled`: Enable movie inserts.
- `movies.library`: Plex movie library name.
- `movies.query`: Optional Plex query string.
- `movies.collections_as_shows`: Treat collections as mini-shows to keep order.
- `movies.include_collections` / `movies.exclude_collections`: Optional wildcard patterns.
- `movies.ratio.every_episodes`: Insert 1 movie after N episodes.
- `movies.ratio.max_movies`: Cap inserted movies.
- `movies.filters.exclude_watched_days`: Skip movies watched recently.
- `movies.filters.unwatched_only`: Only include unwatched movies.

### Output and scheduling

- `output.mode`: `replace` (delete + recreate playlist) or `append`.
- `output.limit_items`: Cap total items in the final playlist.
- `output.chunk_size`: Items per Plex API call.
- `schedule.interval_minutes`: Loop interval for automation.
- `schedule.jitter_seconds`: Random extra delay to avoid predictable refreshes.

## Notes

- Plex query strings accept advanced filters. If you already use smart playlists, you can reuse those filter parameters here.
- For automation without `--loop`, run `python -m plex_shuffler --config config.json run` on cron or a systemd timer.
- The web UI may store optional `query_state` alongside `tv.query`/`movies.query` for query-builder round-tripping; the CLI ignores it.
