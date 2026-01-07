# TASKS.md — Current Execution Board

**Last updated:** 2026-01-07

This file tracks what's being worked on **right now**. Keep it small (max 1-3 items in "Now"). Move completed tasks to "Done" with a brief outcome.

---

## Now (Work in Progress)


---

## Next (Ready Queue — Pick from here next)

### T002: Add basic test coverage for shuffle.py
- **From:** BACKLOG.md B001
- **Goal:** Unit tests for round-robin and weighted shuffle strategies.
- **Acceptance:** Tests pass with `python -m pytest tests/test_shuffle.py`.

### T003: Add pyproject.toml with packaging metadata
- **From:** BACKLOG.md B003
- **Goal:** Project can be installed with `pip install .` and has CLI entrypoint.
- **Acceptance:** User can run `plex-shuffler-studio --help` after install.

### T004: Improve config validation error messages
- **From:** BACKLOG.md B004
- **Goal:** Config errors include context (field name, available options).
- **Acceptance:** README has "Troubleshooting" section with examples.

---

## Blocked

### T009: Cleanup monorepo + rename/init plex-shuffler-studio repo
- **From:** User request 2026-01-07
- **Owner:** Codex
- **Started:** 2026-01-07
- **Goal:** Remove accidental parent monorepo, rename `plex-shuffler-studio` folder, initialize git + remote, and audit other projects for missing repos/remotes.
- **Acceptance:** Parent `.git` removed or archived per user confirmation, `plex-shuffler-studio` has a clean git repo with remote set, and audit report delivered for other folders.
- **Blocked:** GitHub repo `acaradonna/harmony` already exists; need decision to merge or force-push local history.

---

## Done (Last 20 Items — Rolling History)

### T008: Implement query field catalog + custom filters in web UI
- **Completed:** 2026-01-07
- **Outcome:** Added a curated query field catalog with a builder/advanced toggle, custom filters, and Plex-backed option loading for multiselect fields.
- **Notes:** Query builder now persists custom fields via stored `query_state`; unvalidated fields remain hidden until confirmed.

### T007: Add query builder domain model + serialization helpers
- **Completed:** 2026-01-07
- **Outcome:** Added query builder parsing/serialization helpers + tests, and wired web config API to round-trip `query_state`.
- **Notes:** See NOTES.md D007 for source-of-truth and ordering details.

### T006: Define query-builder semantics + v1 fields
- **Completed:** 2026-01-07
- **Outcome:** Documented boolean logic rules, v1 field list, and raw query escape hatch for the web query builder.
- **Notes:** See NOTES.md D006 for limitations and rationale.

### T005: Fix web playlist generation + add progress feedback
- **Completed:** 2026-01-07
- **Outcome:** Fixed Plex `/identity` parsing to unblock playlist creation and added in-progress UI states for preview/run.
- **Notes:** Hosted Plex servers returning `machineIdentifier` at the root now work; buttons show spinners while building.

### T001: Create documentation system (AGENTS/PLAN/BACKLOG/TASKS/CHANGELOG/NOTES)
- **Completed:** 2026-01-07
- **Outcome:** Six markdown files created with proper structure: AGENTS.md (process rules), PLAN.md (roadmap with MVP/MVP+/Future phases), BACKLOG.md (15 prioritized work items), TASKS.md (execution board), CHANGELOG.md (user-facing history), NOTES.md (decision log with 5 decisions, 2 investigations, 4 gotchas).
- **Notes:** Docs are seeded with current project state (working CLI, stdlib Plex client, shuffle/builder logic). README.md is now the authoritative contract per user request. Cron/job mode prioritized over daemon/loop mode.

### T000: Initial codebase setup (before doc system)
- **Completed:** 2026-01-06
- **Outcome:** Working CLI with `libraries` and `run` commands; stdlib-only Plex client; shuffle/builder logic; config validation; dry-run mode; loop mode with interval + jitter.
- **Notes:** MVP feature set mostly complete; missing tests, packaging, and docs.

---

## Instructions for Agents

1. **Before starting work:** 
   - Pick ONE task from "Next" and move it to "Now".
   - Add your agent name/ID as "Owner".
   - Update "Started" with current date.

2. **While working:**
   - If you discover sub-tasks, break them out and add to "Next" (or BACKLOG if not urgent).
   - If you hit a blocker, note it in the task and move to "Blocked" section (create if needed).

3. **After completing work:**
   - Move the task to "Done" with:
     - **Completed:** date
     - **Outcome:** 1-2 sentence summary of what was delivered.
     - **Notes:** Any gotchas, decisions, or follow-ups (or link to NOTES.md).
   - Update CHANGELOG.md if user-visible.
   - Update NOTES.md if non-trivial decision was made.

4. **Keeping "Done" clean:**
   - Keep last ~20 items; archive older items to a separate doc or delete if not critical.

---

## Task Status Definitions

- **Now:** Actively being worked on (limit 1-3 items; more than that means work is fragmented).
- **Next:** Ready to start; no blockers; clear acceptance criteria.
- **Done:** Completed and verified; ready for user review.
- **Blocked:** Waiting on user input, external dependency, or design decision.

---

**Next action:** Complete T001 (this file + 5 others), then move to T002 (tests).
