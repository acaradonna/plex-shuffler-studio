# NOTES.md — Engineering Decision Log

**Last updated:** 2026-01-08

This file captures design decisions, investigations, and gotchas so agents don't re-litigate past choices or repeat mistakes.

---

## Decisions

### D001: Stdlib-only approach (no `plexapi` dependency)
- **Date:** 2026-01-06
- **Decision:** Use stdlib `urllib` + `xml.etree.ElementTree` for Plex API calls instead of `plexapi` library.
- **Rationale:**
  - Faster startup (no dependency install).
  - Simpler distribution (fewer moving parts).
  - Full control over HTTP requests and error handling.
- **Alternatives considered:**
  - **plexapi:** More features, but adds complexity and installation friction for a CLI tool.
  - **Manual REST + JSON:** Plex API is XML-based, so parsing JSON would require transcoding or using unofficial endpoints.
- **Trade-offs:**
  - More code to maintain (XML parsing, request handling).
  - May need to add `plexapi` later if XML parsing becomes too fragile or if we need advanced features (OAuth, webhooks).
- **Status:** Active (MVP); revisit in MVP+ if pain points emerge.

### D002: Cron/job mode as primary scheduler
- **Date:** 2026-01-07
- **Decision:** Prioritize "run once and exit" mode for cron/systemd timer usage; loop mode is secondary.
- **Rationale:**
  - Simpler code (no signal handling, no long-running process management).
  - More robust (external scheduler handles retries, logging, alerting).
  - More "Unixy" (fits standard automation patterns).
- **Alternatives considered:**
  - **Daemon/loop mode first:** Could handle "missed runs" better, but adds complexity and resource overhead.
- **Trade-offs:**
  - Users who want "always on" behavior need to set up cron/systemd themselves (but we can provide examples).
  - Loop mode still supported for users who prefer it.
- **Status:** Active (MVP).

### D003: JSON config format (not YAML or TOML)
- **Date:** 2026-01-06
- **Decision:** Use JSON for config files instead of YAML or TOML.
- **Rationale:**
  - Stdlib support (`json` module).
  - Familiar to most developers.
  - Easy to validate with JSON Schema (future).
- **Alternatives considered:**
  - **YAML:** More human-friendly, but requires `PyYAML` dependency.
  - **TOML:** Good for Python projects (`pyproject.toml`), but less familiar to non-Python users.
- **Trade-offs:**
  - JSON is verbose (no comments, quoted keys).
  - May add YAML/TOML support later as optional.
- **Status:** Active (MVP).

### D004: Playlists as primary output (not live TV channels)
- **Date:** 2026-01-06
- **Decision:** Focus on generating Plex playlists, not full live TV channels with EPG/streaming.
- **Rationale:**
  - Playlists are simpler (no EPG generation, no streaming server).
  - Playlists are native to Plex (no third-party tools required).
  - Users who want live TV can use ErsatzTV or Dizque TV.
- **Alternatives considered:**
  - **Full live TV setup:** More "TV-like," but requires EPG, streaming server, and Plex DVR/Live TV feature.
- **Trade-offs:**
  - Playlists don't auto-advance or show "what's on now" UX.
  - Future enhancement: add EPG export for ErsatzTV integration.
- **Status:** Active (MVP); live TV channel export could be a Future phase feature.

### D005: Documentation system (AGENTS/PLAN/BACKLOG/TASKS/CHANGELOG/NOTES)
- **Date:** 2026-01-07
- **Decision:** Use six markdown files to coordinate agent work and track changes.
- **Rationale:**
  - Clear separation of concerns (process vs roadmap vs work items vs history).
  - Easy to read/update (plain text, version-controlled).
  - Scales to multiple agents (no need for external tools like Jira/Trello).
- **Alternatives considered:**
  - **GitHub Issues/Projects:** More features, but harder for agents to update programmatically.
  - **Single TODO.md:** Too monolithic; hard to find relevant info.
- **Trade-offs:**
  - Requires discipline to keep docs in sync.
  - Six files is more overhead than one, but each file has a clear purpose.
- **Status:** Active (MVP).

### D006: Query builder boolean semantics + v1 field set
- **Date:** 2026-01-07
- **Decision:** The web query builder outputs the existing raw `tv.query`/`movies.query` string and treats it as the sole source of truth.
- **Rationale:**
  - Keeps backward compatibility (no schema change; existing configs still work).
  - Matches current plumbing: `parse_qsl(..., keep_blank_values=True)` preserves order + duplicates and `urlencode(..., doseq=True)` sends them unchanged.
  - Simple UX: non-technical users pick common filters; advanced users can edit the raw query directly.
- **Boolean logic (as implemented):**
  - **AND across fields:** separate keys joined with `&` (e.g., `genre=Animation&unwatched=1`).
  - **OR within a field:** repeat the same key (e.g., `genre=Animation&genre=Comedy`).
  - **No cross-field OR or grouping:** no parentheses; the builder does not attempt to express `(A OR B) AND C` across different keys.
  - **List separators are opaque:** commas/pipes stay inside the value; if Plex interprets them, that is Plex behavior, not ours.
- **V1 supported fields (UI-generated `key=value` pairs):**
  - `genre` (multi-value text)
  - `unwatched` (checkbox -> `unwatched=1`)
  - `year` (exact year text/number)
  - `studio` (text)
  - `contentRating` (text)
  - `collection` (text)
  - `label` (text)
  - `title` (text)
- **Custom escape hatch:**
  - Provide a raw query string input (advanced) that writes directly to `tv.query`/`movies.query` and overrides the builder output on save.
- **Status:** Active (MVP); validate Plex behavior with real libraries before expanding field list or adding operators.

### D007: Store query builder state alongside query strings
- **Date:** 2026-01-07
- **Decision:** Keep `tv.query`/`movies.query` as the canonical values, but attach optional `query_state` for UI round-tripping; API GET derives `query_state` from the query string, API POST serializes `query_state` back to the string when provided.
- **Rationale:**
  - Preserves existing CLI + builder pipeline (string remains source of truth).
  - Allows UI to edit safely without losing duplicate keys or ordering intent.
  - Supports automatic fallback to Advanced mode when unsupported fields appear.
- **Alternatives considered:**
  - **Make query_state primary:** Higher risk of breaking existing configs and CLI behavior.
  - **No structured state:** Keeps config simple but blocks round-trip UI editing.
- **Trade-offs:**
  - Web-saved configs include extra `query_state` fields.
  - Re-serialization can normalize repeated-key ordering (stable but not identical).
- **Status:** Active (Web UI).

### D008: Curated query field catalog + custom filters in web UI
- **Date:** 2026-01-07
- **Decision:** The web query builder exposes only verified fields (genre, unwatched, year, collection, content rating, studio) plus a Custom filter escape hatch; unvalidated mappings (title/summary/actor/director and year range ops) stay hidden until confirmed.
- **Rationale:**
  - Prevents shipping misleading field/operator mappings.
  - Keeps the builder approachable while still supporting arbitrary keys/values.
  - Allows custom filters to persist by retaining stored `query_state` when it matches the query string.
- **Alternatives considered:**
  - **Expose all suggested fields immediately:** Higher risk of broken filters if Plex mappings differ.
  - **Force Advanced mode for any unknown key:** Blocks the Custom filter UX and round-tripping.
- **Trade-offs:**
  - Some common fields are only available via Custom or Advanced until validation.
  - Builder feature set is intentionally conservative in v1.
- **Status:** Superseded by D009.

---


### D009: Validate title + year range filters for builder
- **Date:** 2026-01-07
- **Decision:** Promote `title` and year range operators (>=, <=) to verified fields in the query builder; keep `summary`, `actor`, and `director` pending until Plex mappings are confirmed.
- **Rationale:**
  - Plexopedia documents `year>=`/`year<=` filters and partial matching via `=` for string fields.
  - PlexAPI docs show `title=...` as a working filter example, but `actor` is noted as ID-based and unverified.
- **Alternatives considered:**
  - **Promote all text/tag fields now:** Higher risk of shipping filters that require IDs or unsupported ops.
  - **Keep year range hidden:** Blocks common use cases like "2010+" without Advanced mode.
- **Trade-offs:**
  - Title filter assumes Plex treats `title=...` as contains; actual behavior may vary by server metadata.
  - Actor/director are exposed in the builder catalog, but Plex behavior can vary (e.g., some servers may require IDs rather than names).
- **Status:** Active (Web UI).

### D012: Top-N prepopulation for Plex-backed option lists
- **Date:** 2026-01-08
- **Decision:** Support optional `limit` on Plex-backed option/facet endpoints and slice results after normalization/caching.
- **Rationale:**
  - Keeps UI pickers fast and usable without loading thousands of tag values.
  - Avoids polluting caches with many limit variants (cache stores full normalized list; responses slice after cache).
- **Trade-offs:**
  - Users may not see rare values in the picker without switching to Custom/Advanced.
- **Status:** Active (Web UI).

### D010: Facet lookups use Plex tag directories per section
- **Date:** 2026-01-07
- **Decision:** Fetch facet values (genre, collection, contentRating, studio, actor, director) from `/library/sections/{key}/{facet}` tag endpoints, mapping `content_rating`/`contentRating` to Plex's `contentRating` path.
- **Rationale:**
  - Keeps responses small (tag listings only, no full library scan).
  - Aligns with Plex's tag directory endpoints used by smart filters.
- **Alternatives considered:**
  - **Scan `/library/sections/{key}/all` and aggregate tags:** Too heavy for large libraries.
  - **Use only `/library/sections/{key}/collections`:** Doesn't cover non-collection facets.
- **Trade-offs:**
  - Relies on Plex tag endpoints being available; collection uses the existing `/collections` fallback in the Plex client.
- **Status:** Active (Web UI).

### D011: Package web UI assets as package data
- **Date:** 2026-01-07
- **Decision:** Include `plex_shuffler/web/*` in Python package data so the web UI continues to work when installed from a wheel/sdist.
- **Rationale:** `run_web_server()` serves static assets from `Path(__file__).parent / "web"`, which must exist in installed distributions.
- **Status:** Active (Packaging).

## Investigations

### I001: Plex API rate limits and pagination
- **Date:** 2026-01-06
- **Finding:** Plex API doesn't document formal rate limits, but large requests (500+ items) can be slow.
- **Action:** Use pagination (`?X-Plex-Container-Start=0&X-Plex-Container-Size=100`) for large libraries.
- **References:** Plex API docs (unofficial), forum posts about slow `/library/sections` calls.
- **Status:** Implemented in `plex_client.py`.

### I002: Seed-based shuffle reproducibility
- **Date:** 2026-01-06
- **Finding:** Python's `random.seed()` produces different results across Python versions (pre-3.9 vs 3.9+).
- **Action:** Document Python version requirement (3.10+) and note that seeds are not portable across versions.
- **References:** Python docs on `random.seed()` hash randomization.
- **Status:** Documented in README (requires Python 3.10+).

---

## Gotchas

### G001: Plex playlist API quirks
- **Issue:** Plex playlist API uses `POST /playlists` to create, but requires `ratingKey` (not `key`) for items.
- **Workaround:** Extract `ratingKey` from episode/movie XML, not `key` (which is a URL path).
- **Impact:** If you use `key` instead of `ratingKey`, playlist creation silently fails (empty playlist).
- **Fixed in:** `plex_client.py` (fetch/parse `ratingKey` attribute).

### G002: Collection items order is not guaranteed
- **Issue:** Plex API returns collection items in arbitrary order (not the user-defined order shown in UI).
- **Workaround:** Use `?sort=titleSort` or `?sort=addedAt` to get a stable order, or fetch collection via `/library/collections/{id}/children`.
- **Impact:** If you rely on default order, collection-as-show feature may produce unexpected results.
- **Status:** Implemented stable sort in `plex_client.py`.

### G003: Watch history is per-user, not global
- **Issue:** Plex watch history (`viewCount`, `lastViewedAt`) is per-user, not global.
- **Workaround:** Config must specify a user token (or use owner token and filter by specific user).
- **Impact:** Multi-user setups need per-user playlists or aggregated watch logic.
- **Status:** Not yet implemented; add to BACKLOG for MVP+.

### G004: Jitter in schedule can cause clock skew issues
- **Issue:** If system clock drifts or changes (DST, NTP sync), jitter calculation may produce unexpected delays.
- **Workaround:** Use monotonic time (`time.monotonic()`) instead of wall clock for sleep intervals.
- **Status:** Implemented in `cli.py` (uses `time.sleep()` with calculated interval, not absolute timestamps).

### G005: Plex /identity response formats vary
- **Issue:** Some Plex servers return `machineIdentifier` on the root `<MediaContainer>` without a `<Server>` child.
- **Workaround:** Accept `machineIdentifier` from either the root element or the `<Server>` element.

---

## Agent Acknowledgements

- 2026-01-08: Agent GitHub Copilot acknowledged AGENTS.md.
- **Impact:** Playlist creation fails if client only checks for `<Server>` (no machine identifier).
- **Status:** Implemented in `plex_client.py` (root + Server fallback).

### G006: CLI run loops when schedule interval is set
- **Issue:** `run` continued looping if `schedule.interval_minutes` > 0, even without `--loop`.
- **Workaround:** *(no longer needed)*
- **Impact:** Confusing behavior (looked like a hang after first run).
- **Status:** Fixed (CLI now only loops when `--loop` is set).

---

## Agent Acknowledgments

*(Agents: add a timestamped entry here when you read AGENTS.md for the first time in a session.)*

- **2026-01-07:** Agent Codex acknowledged AGENTS.md on 2026-01-07.
- **2026-01-07:** Agent GitHub Copilot acknowledged AGENTS.md on 2026-01-07.
- **2026-01-07:** Agent Codex acknowledged AGENTS.md on 2026-01-07 (web facets session).
- **2026-01-07:** Agent Codex acknowledged AGENTS.md on 2026-01-07.
- **2026-01-07:** Agent Codex acknowledged AGENTS.md on 2026-01-07.
- **2026-01-07:** Agent Codex acknowledged AGENTS.md on 2026-01-07.
- **2026-01-07:** Agent (current session) acknowledged AGENTS.md and created initial documentation system.
- **2026-01-07:** Agent Codex acknowledged AGENTS.md.
- **2026-01-07:** Agent Codex acknowledged AGENTS.md on 2026-01-07.

---

## How to Use This File

### Decisions
- **When to add:** Any design choice that affects architecture, dependencies, or user-facing behavior.
- **Format:** Date, decision, rationale, alternatives, trade-offs, status.

### Investigations
- **When to add:** Any research or testing that uncovers non-obvious behavior (Plex API quirks, library limits, performance).
- **Format:** Date, finding, action, references, status.

### Gotchas
- **When to add:** Any bug, quirk, or "footgun" that wasted time or could surprise future contributors.
- **Format:** Issue, workaround, impact, status.

### Agent Acknowledgments
- **When to add:** First time you read AGENTS.md in a new session.
- **Format:** Date, agent name/ID, brief note.

---

**Next update:** When first test suite is added, or when a new design decision is made.
