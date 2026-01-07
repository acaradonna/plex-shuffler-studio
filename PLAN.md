# PLAN.md — Project Roadmap

**Last updated:** 2026-01-07

This file defines the long-term vision, phases, and milestones for the Plex Shuffler Studio project.

---

## Vision

Build a **fast, configurable, and user-friendly** playlist builder for Plex that:
- Shuffles TV shows while keeping each show's episodes in order (the "shuffle-in-order" pattern).
- Optionally mixes movies into playlists at a configurable cadence (e.g., 1 movie per 6 episodes).
- Supports smart filters (query strings, watch history, title patterns) to control what goes into playlists.
- Can run on-demand or on a schedule (cron/job mode first, daemon/loop mode later).
- Produces "live-TV-like" playlists without requiring full live TV channel infrastructure (no EPG, no streaming server).

---

## Non-Goals

- **No live TV channel management.** We focus on playlists; users who want actual "channels" in Plex can use ErsatzTV or Dizque TV.
- **No web UI (MVP).** Start with a CLI-first approach; web UI is a future phase.
- **No third-party Plex library dependencies (MVP).** Keep it stdlib-only for simplicity and speed; only add `plexapi` or similar if truly necessary in later phases.
- **No complex "smart" AI scheduling.** Keep scheduling simple (interval + jitter); users can use cron for more advanced patterns.

---

## Phases

### MVP (Current State — Q1 2026)

**Goal:** Deliver a working CLI tool that can generate shuffled playlists with show + movie mixing, suitable for cron/job usage.

**Deliverables:**
- [x] Stdlib-only Plex client (XML parsing, basic auth)
- [x] Config file schema (JSON) with validation
- [x] Show shuffling with episode order preserved (round-robin or weighted strategies)
- [x] Movie mixing (ratio-based: 1 movie per N episodes)
- [x] Collection-as-show support (treat collections like a show to preserve order)
- [x] Watch history filters (exclude recently watched items)
- [x] CLI commands: `libraries` (list), `run` (build/sync playlists)
- [x] Dry-run mode (preview without writing to Plex)
- [x] Optional loop mode (run continuously with interval + jitter)
- [x] README with quick start, config examples, and CLI docs
- [ ] Basic test coverage for shuffle/builder logic
- [ ] Documentation system (AGENTS, PLAN, BACKLOG, TASKS, CHANGELOG, NOTES)

**Acceptance Criteria:**
- User can install/run from repo checkout (`python -m plex_shuffler`).
- User can generate a shuffled playlist with 100+ items (shows + movies) in <10 seconds.
- Config errors are reported clearly with helpful messages.
- Playlist updates are idempotent (running twice with same config produces same output).

---

### MVP+ (Q2 2026)

**Goal:** Add polish, robustness, and packaging for wider distribution.

**Planned Features:**
- [ ] Proper Python packaging (`pyproject.toml`, installable via `pip install .`)
- [ ] CLI entrypoint command (`plex-shuffler-studio` instead of `python -m plex_shuffler`)
- [ ] State store (SQLite or JSON) to track last build, last items included, and per-item watch state
- [ ] "Refresh" command that reads state and only updates changed items (incremental rebuild)
- [ ] Advanced shuffle strategies (weighted by rating, random walk, "recently played" penalty)
- [ ] Query DSL or Plex smart filter support (parse query strings more intelligently)
- [ ] Logging to file (structured logs for easier debugging)
- [ ] GitHub Actions CI (lint, test, build)
- [ ] Pre-built binaries (PyInstaller or similar) for Linux/macOS/Windows

**Acceptance Criteria:**
- User can `pip install` from repo and run `plex-shuffler-studio` command globally.
- Refresh mode reduces Plex API calls by 80% for unchanged items.
- State store is backward compatible (old state files work with new code).

---

### Future (Q3+ 2026)

**Goal:** Add advanced features and optional web UI for non-technical users.

**Possible Features:**
- [ ] Web UI (Flask/FastAPI backend + simple HTML frontend)
  - Visual playlist builder (drag-and-drop shows, adjust ratios)
  - Live preview (see playlist order before syncing)
  - Manage multiple configs (switch between profiles)
- [ ] Plex OAuth support (avoid manual token management)
- [ ] Multi-user support (per-user playlists with different filters)
- [ ] "Time-of-day" scheduling (different playlists at different times)
- [ ] Integration with Plex Watchlists (auto-add new items from watchlist)
- [ ] Metrics/reporting (how many items watched, playlist engagement stats)
- [ ] Docker image (one-command deployment)

**Acceptance Criteria:**
- Web UI can be run with `plex-shuffler-studio web` and accessed at `http://localhost:8080`.
- Docker image runs headless and persists config/state across restarts.

---

## Release Checklist

Before tagging a release (e.g., `v0.1.0`):
- [ ] All "MVP" or "MVP+" features for that version are complete and tested.
- [ ] README.md is up-to-date (config schema, CLI commands, examples).
- [ ] CHANGELOG.md has a dated section for the release (move "Unreleased" to version).
- [ ] No open P0/P1 bugs in BACKLOG.md.
- [ ] Manual validation: Run against a real Plex server with 100+ shows and 500+ movies.
- [ ] Tag commit with version (e.g., `git tag v0.1.0`).
- [ ] (Later) Publish to PyPI and/or GitHub Releases.

---

## Risks & Assumptions

| Risk | Mitigation |
|------|-----------|
| Plex API changes break stdlib XML parsing | Monitor Plex API changelog; consider adding `plexapi` fallback in MVP+ |
| Large libraries (1000+ shows) cause OOM | Implement pagination and lazy loading; add `--limit` flag for testing |
| Token management is fragile | Document token creation steps clearly; add validation at startup |
| Users expect GUI, not CLI | Build MVP first, validate demand, then add web UI in Future phase |
| Scheduling drift (cron misses runs) | Provide clear cron examples; add jitter to reduce contention |

---

## Assumptions

- Users have Python 3.10+ installed.
- Users can create and manage a Plex token (documented in README).
- Plex server is reachable over HTTP/HTTPS (no Plex Relay support needed for MVP).
- Playlists are the primary output (not live TV channels).
- Cron/job mode is the primary usage pattern (daemon mode is secondary).

---

**Next milestone:** Complete MVP → tag v0.1.0 → publish to GitHub.
