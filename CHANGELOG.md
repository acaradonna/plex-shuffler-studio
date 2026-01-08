# CHANGELOG.md — User-Facing Changes

**Last updated:** 2026-01-07

This file tracks all user-visible changes to the Plex Shuffler Studio project. Format follows [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased]

### Added
- Python packaging via `pyproject.toml`, including a `plex-shuffler-studio` console script.
- Query builder now supports title filters and year range operators (>=, <=).
- Documentation system (AGENTS.md, PLAN.md, BACKLOG.md, TASKS.md, CHANGELOG.md, NOTES.md) to coordinate agent collaboration and track work.
- Web config API now includes optional `query_state` for TV/movie queries, with parsing/serialization helpers for UI round-tripping.
- Web UI query builder with curated field catalog, custom filters, and Plex-backed option loading for multiselect fields.
- Web API endpoints for library facet values (genres/collections/etc.) with in-memory caching and graceful error fallback.
- Optional `limit` support for Plex-backed query option/facet endpoints to enable top-N prepopulation.
- Actor/director fields are now available in the query builder catalog.

### Changed
- Web UI preview/run actions now show in-progress states instead of only a save toast.
- Rebranded UI and Plex client identifiers as Plex Shuffler Studio.

### Fixed
- Playlist creation now handles Plex `/identity` responses that expose `machineIdentifier` on the root element.
- CLI no longer loops unless `--loop` is provided (even if `schedule.interval_minutes` is set).
- Plex library queries now paginate to support large libraries.
- Config validation now catches more invalid values early (enum/range checks) with clearer field-scoped errors.

### Changed
- Plex requests now use `plex.client_id` (when set) as the `X-Plex-Client-Identifier` header.

### Removed
- *(none yet)*

---

## [0.1.0] - Pre-release (Current State)

### Added
- CLI with two commands: `libraries` (list Plex sections) and `run` (build/sync playlists).
- JSON config file with validation for Plex connection, schedule, and playlist definitions.
- Show shuffling with episode order preserved (round-robin and weighted strategies).
- Movie mixing at configurable ratio (e.g., 1 movie per 6 episodes).
- Collection-as-show support (treat movie collections like a show to preserve order).
- Watch history filters (exclude items watched in last N days).
- Dry-run mode (`--dry-run`) to preview playlists without writing to Plex.
- Loop mode (`--loop`) to run continuously with interval + jitter from config.
- Optional per-run overrides: `--once`, `--interval-minutes`, `--playlist` (filter to specific playlists).
- Print mode (`--print N`) to show first N items of generated playlist.
- Stdlib-only Plex client (no third-party dependencies).
- README with quick start, config examples, and CLI usage.

### Known Limitations
- No automated tests (manual validation only).
- No proper Python packaging (must run from repo checkout).
- No CLI entrypoint (must use `python -m plex_shuffler`).
- No state store (playlist rebuild is always full, not incremental).
- No logging to file (console only).
- No `--version` flag.
- No web UI.

---

## How to Use This File

### When to add an entry:
- Any change that affects CLI usage (new flags, command changes, output format).
- Any change to config schema (new fields, renamed fields, changed defaults).
- Any change to playlist generation logic (shuffle strategy, filters, movie mixing).
- Any bug fix that users would notice.

### When NOT to add an entry:
- Internal refactors that don't change behavior.
- Documentation updates (unless they clarify a breaking change).
- Test additions (unless they reveal a previously undocumented behavior).

### Format:
```markdown
### Added
- New feature or capability (user perspective).

### Changed
- Existing feature behavior changed (document old → new).

### Fixed
- Bug fix (what was broken, what works now).

### Removed
- Feature removed (explain why if relevant).
```

### Releasing a version:
1. Move all "Unreleased" entries to a new dated section (e.g., `## [0.2.0] - 2026-02-15`).
2. Create an empty "Unreleased" section at the top.
3. Tag the commit with the version (e.g., `git tag v0.2.0`).

---

**Next update:** When first test suite is added, or when pyproject.toml/CLI entrypoint ships.
