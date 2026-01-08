# BACKLOG.md — Prioritized Work Items

**Last updated:** 2026-01-07

This file contains all known work items, grouped by priority. New items go to "Discovered" first, then are triaged to P0/P1/P2.

---

## Priority 0 (Critical — Blocks MVP)

### B001: Add basic test coverage for shuffle/builder logic
- **Outcome:** Unit tests for `shuffle.py` and `builder.py` that validate round-robin, chunking, and movie injection.
- **Acceptance Criteria:** 
  - `tests/test_shuffle.py` covers all shuffle strategies (rounds, weighted).
  - `tests/test_builder.py` validates episode + movie mixing logic.
  - Tests run with `python -m pytest tests/` and pass.
- **Status:** Not started

### B002: Complete documentation system (AGENTS/PLAN/BACKLOG/TASKS/CHANGELOG/NOTES)
- **Outcome:** All six docs exist, seeded with current state, and agents know how to update them.
- **Acceptance Criteria:**
  - All files created with proper structure.
  - PLAN reflects MVP/MVP+/Future phases.
  - BACKLOG has ~10-15 prioritized items.
  - TASKS has 1-3 WIP items and instructions for agents.
- **Status:** In progress

---

## Priority 1 (High — Should be in MVP)

### B003: Add proper Python packaging (pyproject.toml)
- **Outcome:** Project can be installed with `pip install .` and has a CLI entrypoint (`plex-shuffler-studio`).
- **Acceptance Criteria:**
  - `pyproject.toml` defines project metadata, dependencies, and entrypoint.
  - User can run `pip install .` and then `plex-shuffler-studio --help`.
  - README updated with installation instructions.
- **Status:** Not started

### B004: Improve error messages for config validation
- **Outcome:** Config errors include helpful hints (e.g., "library 'XYZ' not found; available libraries: A, B, C").
- **Acceptance Criteria:**
  - `ConfigError` messages include context (field name, expected format).
  - README has a "Troubleshooting" section with common errors.
- **Status:** Not started

### B005: Add --version flag to CLI
- **Outcome:** User can run `plex-shuffler-studio --version` to see current version.
- **Acceptance Criteria:**
  - Version is sourced from `__init__.py` or `pyproject.toml`.
  - Output format: `plex-shuffler-studio 0.1.0`.
- **Status:** Not started

### B006: Document cron/systemd timer setup in README
- **Outcome:** README has copy-paste examples for running playlist refresh on a schedule.
- **Acceptance Criteria:**
  - Example cron entry (e.g., `0 */6 * * * /usr/bin/plex-shuffler-studio ...`).
  - Example systemd timer unit file.
  - Explanation of when to use `--once` vs `--loop`.
- **Status:** Not started

---

## Priority 2 (Nice-to-Have — Can wait for MVP+)

### B007: Add state store (SQLite or JSON) for incremental refresh
- **Outcome:** Playlist refresh can read last build state and only update changed items.
- **Acceptance Criteria:**
  - State file tracks: last build time, list of items included, per-item watch state.
  - New `refresh` command reads state and diffs against current Plex state.
  - State is backward compatible (old state works with new code).
- **Status:** Not started

### B008: Add weighted shuffle strategy (by rating, recently played penalty)
- **Outcome:** Shows with higher ratings or less recent plays appear more often in shuffled order.
- **Acceptance Criteria:**
  - Config supports `strategy: "weighted"` with optional `weight_by` field.
  - Shuffle order is reproducible with same seed + weights.
- **Status:** Not started

### B009: Add query DSL or smart filter parser
- **Outcome:** Users can write complex queries like `(genre=Animation OR genre=Comedy) AND year>=2010`.
- **Acceptance Criteria:**
  - Parser converts DSL to Plex API filter params.
  - Syntax is documented in README with examples.
  - Fallback to raw query string if parsing fails.
- **Status:** Not started

### B010: Add logging to file (structured logs)
- **Outcome:** CLI can log to a file for easier debugging (especially for cron jobs).
- **Acceptance Criteria:**
  - Config has `log_file` field (optional).
  - Log format is JSON or structured text (easy to parse).
  - Logs include: timestamp, level, message, context (playlist name, item count).
- **Status:** Not started

### B011: Add GitHub Actions CI (lint + test)
- **Outcome:** Every push/PR runs linting and tests automatically.
- **Acceptance Criteria:**
  - `.github/workflows/ci.yml` runs `ruff check` and `pytest`.
  - Badge in README shows build status.
- **Status:** Not started

### B012: Add pre-built binaries (PyInstaller)
- **Outcome:** Non-Python users can download a single executable (Linux/macOS/Windows).
- **Acceptance Criteria:**
  - GitHub Actions builds binaries on release tags.
  - Binaries are attached to GitHub Release.
  - README has download links and instructions.
- **Status:** Not started

---

## Discovered (Newly Found Work — Needs Triage)

### B019: Add facets API for library tag values (genres, collections, etc.)
- **Source:** UI query builder follow-up
- **Priority:** TBD
- **Outcome:** Web API can return sorted unique facet values for a chosen library, with caching and graceful errors for UI checkboxes.
- **Acceptance Criteria:**
  - API supports `GET /api/facets?section_title=...&facet=genre` and/or `GET /api/libraries/{sectionKey}/facets/{facet}`.
  - Responses are a list of unique names (strings), sorted for display.
  - Errors return an empty list plus a helpful error message (UI can fallback).
  - In-memory caching avoids repeated Plex calls per (section, facet).
  - Tests cover endpoint shape and caching without a live Plex server.

### B018: Validate remaining query catalog fields (summary/actor/director)
- **Source:** Query builder follow-up
- **Priority:** TBD
- **Outcome:** Confirm Plex mappings for summary/actor/director (including ID vs name requirements) and promote verified fields into the catalog.
- **Notes:** Actor filters may require tag IDs; validate with Plex API before exposing in the builder.

### B017: Add query field catalog + custom filters in web UI
- **Source:** User request
- **Priority:** TBD
- **Outcome:** Web UI exposes a friendly query field catalog with a custom filter escape hatch and dynamic option loading where possible.
- **Acceptance Criteria:**
  - Non-technical user can build a genre-based filter using checkboxes without typing query syntax.
  - Advanced user can still type any raw query string and have it used verbatim.
  - User can add an "Other..." value for any multiselect field and it persists.
  - Fields with uncertain Plex mappings remain available only via Custom filter until validated.
- **Status:** Done (see TASKS.md T008)

### B013: Add support for Plex OAuth (avoid manual token management)
- **Source:** User feedback
- **Priority:** TBD (likely P2 or Future)
- **Notes:** Requires web server to handle OAuth callback; may be overkill for CLI-first tool.

### B014: Add metrics/reporting (watch stats, playlist engagement)
- **Source:** User feedback
- **Priority:** TBD (likely Future)
- **Notes:** Could track: items added, items watched, time since last refresh. May need state store first.

### B015: Add web UI (Flask/FastAPI + HTML frontend)
- **Source:** Original project goal
- **Priority:** Future phase
- **Notes:** See PLAN.md for full spec; depends on state store and packaging.

### B016: Add query builder domain model + serialization helpers
- **Outcome:** Structured query state with parsing + serialization for UI round-tripping.
- **Acceptance Criteria:**
  - `plex_shuffler/query_builder.py` defines QueryState/Group/Clause plus parse/serialize helpers.
  - Tests cover empty query, repeated keys, whitespace trimming, stable ordering, and round-trips.
  - Queries with unsupported fields default to Advanced mode without data loss.
- **Status:** Done (see TASKS.md T007)

---

## Closed / Won't Do

### B999: Add dependency on `plexapi` library
- **Outcome:** N/A (rejected)
- **Reason:** Keeping stdlib-only for MVP to reduce complexity and installation friction. May revisit in MVP+ if XML parsing becomes too fragile.
- **Closed:** 2026-01-07

---

## How to Use This File

1. **Adding new work:** Add to "Discovered" section with a brief description and source.
2. **Triaging:** Move from "Discovered" to P0/P1/P2 based on urgency and impact.
3. **Closing items:** Move to "Closed / Won't Do" with reason and date.
4. **Cross-referencing:** Link to TASKS.md (e.g., "See TASKS.md T001") for active work.

---

**Next steps:** Triage "Discovered" items and move top 2-3 to P1. Start working through P0 items.
