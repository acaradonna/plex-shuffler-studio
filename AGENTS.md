# AGENTS.md — Agent Operating Rules

**Last updated:** 2026-01-07

This file defines how AI agents collaborate on this project. If you're an agent working on this codebase, follow these rules.

---

## Core Principles

1. **Always read before writing.** Re-scan the workspace at the start of each session to understand current state.
2. **Update tracking docs with every change.** No behavior change ships without updating TASKS, CHANGELOG, and (when relevant) NOTES.
3. **README is the contract.** All documented config keys, CLI commands, and behaviors in README.md must be supported and tested.
4. **Prefer small, testable increments.** Break work into discrete tasks; validate after each.

---

## Change Protocol

### Before making any code change:
- [ ] Check TASKS.md to see if the work is already tracked; if not, add it to the "Now" section.
- [ ] Read relevant modules + tests to understand current behavior.
- [ ] If you discover design constraints or gotchas, add them to NOTES.md immediately.

### After making any code change:
- [ ] Move the task card in TASKS.md to "Done" with a brief outcome note.
- [ ] Add an entry to CHANGELOG.md under "Unreleased" if the change affects user-visible behavior (CLI flags, config schema, playlist logic).
- [ ] If you made a non-trivial design choice, document it in NOTES.md (decision + rationale).

### For new features or modules:
- [ ] Add acceptance criteria to BACKLOG.md before implementation.
- [ ] Update PLAN.md if the feature changes a milestone or adds a new phase.

---

## Scope Rules

### What NOT to change without explicit user request:
- The stdlib-only approach (no third-party dependencies like `plexapi` unless explicitly approved).
- The JSON config file format (keep backward compatibility or document breaking changes clearly).
- The CLI command surface documented in README.md (always update README if you change commands).

### What to default to:
- **Scheduler mode:** Cron/job mode (run once, exit) is the primary use case; daemon/loop mode is secondary.
- **Error handling:** Fail fast with clear messages; log at INFO for user actions, DEBUG for internal steps.
- **Testing:** Write tests for pure logic (shuffle, builder, filters); manual validation for Plex integration.
- **Code style:** Follow existing conventions (type hints, docstrings for public functions, short modules).

---

## Definition of Done

A task is "Done" when:
- [ ] Code runs without errors for the documented use case.
- [ ] User-facing changes are reflected in README.md.
- [ ] CHANGELOG.md has an entry (if user-visible).
- [ ] NOTES.md captures any design decisions or gotchas.
- [ ] TASKS.md is updated (moved to "Done").

---

## Commit/PR Hygiene

- **Commit messages:** Start with a verb (e.g., "Add movie ratio filter", "Fix seed parsing bug").
- **Link to tasks:** Reference TASKS.md or BACKLOG.md item IDs in commit body when relevant.
- **Keep commits atomic:** One logical change per commit (easier to review and revert).

---

## When to Ask the User

- You need to install a third-party dependency (explain pros/cons first).
- A requested feature conflicts with README-documented behavior.
- You discover a critical bug that affects existing functionality (report it, propose a fix, wait for approval).
- You're blocked for >15 minutes and can't infer the right path.

---

## Quick Reference

| Doc | Purpose | Update Frequency |
|-----|---------|-----------------|
| AGENTS.md | Process/rules | Rarely (only when process changes) |
| PLAN.md | Roadmap/milestones | Per phase (e.g., MVP → MVP+) |
| BACKLOG.md | Prioritized work items | Weekly or when new work is discovered |
| TASKS.md | Current WIP board | Every change (move cards, add/close tasks) |
| CHANGELOG.md | User-facing history | Every user-visible change |
| NOTES.md | Decision log | Every non-trivial decision or gotcha |

---

**If you're an agent and you read this file, confirm by updating NOTES.md with a timestamped entry: "Agent [name] acknowledged AGENTS.md on [date]."**
