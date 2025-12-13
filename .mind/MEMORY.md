<!-- MIND MEMORY - Append as you work. Write naturally.
Keywords: decided, problem, learned, tried, fixed, blocked, todo -->

# vibeship-mind

## Project State
- Goal:
- Stack: python
- Blocked: None

## Gotchas
- Windows cp1252 encoding -> use ASCII symbols or set PYTHONIOENCODING=utf-8
- uv sync removes unlisted packages

---

## Session Log

## 2025-12-13

**Decided:** File-based memory over database approach - simpler, human-readable, git-trackable
**Decided:** Use Click for CLI because it's simple and well-documented

**Problem:** Windows console doesn't support Unicode checkmarks
**Fixed:** Replaced Unicode symbols with ASCII alternatives

**Learned:** Python on Windows uses cp1252 encoding by default, not UTF-8
TIL: uv sync removes packages not in dependencies

Going with loose regex parsing over strict schemas because lower friction

---

## 2025-12-13 (continued)

Built all 5 phases of Mind - CLI, Parser, Daemon, MCP Server, Polish

decided to rewrite README for vibe coders - simpler language, less jargon
decided on 5-command install instead of multi-step guides
decided to remove competitive comparison chart - felt too aggressive
learned that users get confused by technical paths like `uv --directory`
learned that "note taking" framing is wrong - it's about memory, not notes

problem: README was too confusing for beginners
fixed by simplifying to copy-paste commands and plain English

Added MCP tools explanation with easy install prompt:
> Add Mind MCP server from github.com/vibeforge1111/vibeship-mind to my config

decided to enhance capture instructions with ideas from archived version - alternatives rejected, symptoms/theories, mood tracking, session end notes
learned that the archived version had rich session management (Episodes, mood tracking, primer generation) that we can borrow concepts from
fixed memory capture gap by adding explicit instructions to CLAUDE.md template - Claude needs to be told to write memories

---

## 2025-12-13 | Added intelligence from archives: recency, KEY markers, session summaries, context budget, stack-aware edges | mood: productive

**Researched competition:** Mem0, mcp-memory-service, task-orchestrator, claude-memory-mcp, memory banks
KEY: decided to stay file-based - that's our identity vs database-heavy competitors
decided to add only necessary intelligence: recency scoring, KEY markers, session summaries, context budget, stack-aware edges
decided NOT to add: databases, embeddings, workflow commands, episodes, user model - too much friction

**Implemented:**
- Recency scoring (days_ago field, entities_by_recency() method)
- KEY: and important: markers for items that never fade
- Session summary lines: `## DATE | what happened | mood: X`
- Context budget: key items section, session history compression
- Stack-aware edge matching: surfaces relevant gotchas based on project stack

learned that competition (Mem0, mcp-memory-service) all use databases/embeddings - we stay simpler with files
learned that session summary format `## DATE | summary | mood` compresses history naturally
gotcha: session summary lines were being parsed as entities - fixed by skipping lines with `|` in _should_skip

---

## 2025-12-13 | Fixed daemon bugs: async coroutine awaiting, Windows process detection with ctypes | mood: debugging

fixed: debouncer callbacks were returning unawaited coroutines - pass async functions directly with args instead of lambdas
fixed: Windows `os.kill(pid, 0)` doesn't work for process detection - use ctypes OpenProcess instead
gotcha: Windows os.kill returns WinError 87 instead of checking process existence like Unix
gotcha: Windows file.replace() fails when target file is open - use direct write with retries instead

---

## 2025-12-13 | Migrated to Mind v2: daemon-free, MCP-only architecture | mood: shipped

KEY: decided to remove daemon entirely - MCP handles everything lazily via mind_recall()

**Implemented v2 migration:**
- Deleted daemon.py and watcher.py
- Removed all daemon CLI commands (start, stop, status, logs)
- Added mind_recall() with session gap detection (30 min threshold) and hash checking
- Added mind_checkpoint() for manual processing trigger
- Updated mind_search() to read raw MEMORY.md for same-session support
- Simplified state.json schema (last_activity, memory_hash, schema_version)
- Updated CLAUDE.md template with new MCP-only protocol

learned: daemons are inherently unstable (crashes, PID issues, platform configs) - stateless MCP is more reliable
learned: session detection doesn't need real-time - lazy detection at next recall() works just as well
gotcha: same-session writes aren't indexed yet - search must read raw MEMORY.md too

---

## 2025-12-13 | Added within-session memory (SESSION.md) | mood: productive

KEY: decided to add SESSION.md for within-session memory - prevents loops and drift during long conversations

**Implemented:**
- SESSION.md template with 6 sections: Focus, Constraints, Tried, Discovered, Open Questions, Out of Scope
- `mind_session()` MCP tool to check current session state
- Promotion logic: extracts tech-specific gotchas and path-based learnings on session end
- recall() now processes old SESSION.md on gap detection and returns current session state

learned: within-session memory is different from cross-session - it's about preventing repeating failures and rabbit holes
learned: promotion rules use regex to detect tech patterns (Safari, bcrypt, JWT) and file paths (/lib/file.ts)
gotcha: SESSION.md gets cleared on new session - important learnings must be promoted to MEMORY.md first

---

## 2025-12-13 | Upgraded SESSION.md to goal-oriented structure | mood: shipped

KEY: decided to restructure SESSION.md around goals, not tasks - prevents rabbit holes by keeping user outcomes visible

**Implemented:**
- Goal-oriented SESSION.md with 6 sections: The Goal, Current Approach, Blockers, Rejected Approaches, Working Assumptions, Discoveries
- `mind_blocker(description)` MCP tool - logs blocker AND auto-searches memory for solutions
- Updated CONTEXT_TEMPLATE with workflow guidance (stuck? check assumptions, check pivot condition)
- Promotion logic now promotes Rejected Approaches (with reasoning) as decisions, Discoveries with tech patterns as learnings

**Key Design Decisions:**
- "The Goal" = user outcome not technical task ("User can X" not "Implement Y")
- "Current Approach" includes pivot condition ("Pivot if: X")
- "Rejected Approaches" = strategic with WHY (to prevent circles)
- "Working Assumptions" = things to question when stuck
- "Blockers" triggers memory search via mind_blocker tool

learned: goal-oriented session structure keeps Claude focused on user outcomes, not implementation details
learned: mind_blocker auto-extracts keywords and searches memory - found relevant Windows encoding gotcha immediately
gotcha: SESSION.md blocker insertion needs extra newline before next section to preserve formatting

---

## 2025-12-13 | Documentation cleanup for v2 | mood: productive

**Completed:**
- Deleted docs/DAEMON.md entirely (no longer relevant)
- Rewrote docs/ARCHITECTURE.md for v2 (MCP-only, stateless)
- Rewrote docs/CLI.md (removed daemon commands)
- Rewrote docs/IMPLEMENTATION.md for v2
- Updated docs/DESIGN_RATIONALE.md (removed daemon trade-off section, added v2 rationale)
- Rewrote docs/ONBOARDING.md (no daemon, MCP-only flow)
- Rewrote docs/MCP_TOOLS.md (documents all 8 tools now)
- Cleaned CLAUDE.md daemon references
- Fixed server.py comments (4/6 tools -> 8 tools)

**Also added to CLAUDE.md:**
- CRITICAL section telling Claude to call mind_recall() FIRST every session
- Quick reference table for all 8 MCP tools with when to use each

learned: docs were way out of date - said 4 tools when we have 8, still mentioned daemon commands
learned: mind_recall() rule in CLAUDE.md is critical - without it, Claude won't call it first

**Also fixed:**
- Parser bug: issue patterns were too loose, matching "PID issues" in prose as an issue entity
- Changed `[Ii]ssue:?\s*` to `^[Ii]ssue[:–-]\s*` to require : or - after keyword

**Future idea:**
- `mind_remind(msg, when)` tool - for scheduled reminders across sessions


<!-- Promoted from SESSION.md on 2025-12-13 -->
decided against: Database for session storage - Too much friction, files are simpler and human-readable
decided against: Complex episode management from archived version - Overkill for the problem we're solving
learned: `parse_session_section()` function handles any section name via regex


reminder completed: Improve reminders with context-matching

## 2025-12-13: Added Reminder System (Phase A)

decided: Use separate REMINDERS.md file instead of storing in MEMORY.md - reminders are transient, memory is permanent
decided: Single mind_remind(msg, when) tool that parses natural language times - simpler than multiple tools
decided: Fired reminders get promoted to MEMORY.md - preserves history of what was reminded
decided: Auto-dismiss after surfacing, with snooze option - user says "snooze" to push back, default is next session

learned: parse_when() handles "next session", "tomorrow", "in X days/weeks", ISO dates, "December 25" etc.
learned: Due reminders inject into MIND:CONTEXT after "## Memory: Active" section
learned: Reminder lifecycle: created -> due -> surfaced -> work/snooze -> done/rescheduled

**Implementation:**
- Added ~200 lines to server.py: helper functions + 2 MCP tools (mind_remind, mind_reminders)
- Modified handle_recall() to check get_due_reminders() and inject into context
- REMINDERS.md format: `- [ ] {due} | {type} | {message}`
- Types: "next session" (fires on recall), "absolute" (fires when date passed), "done"

**Phase B (future):** Context-triggered reminders - "remind me when we work on auth"
**Shipped:** Context-matching reminders (Phase B) - 'when I mention X' triggers that surface in mind_recall output
**Learned:** Simple approach for context reminders - just show keywords to Claude and let it match naturally vs complex mid-session checking

decided: skip Claude Code hooks for memory automation - adds complexity without value. Commit messages don't capture "why". Real value is in-conversation logging via mind_log()
decided: Mind's real purpose: not just a dev tool, but substrate for AI persistent identity. Memory = facts, Session = raw experience, Self-Improvement = meta-learning patterns. The md files aren't documentation - they're becoming.
decided: Simplified SESSION.md from 6 sections to 4: Experience, Blockers, Rejected, Assumptions - removed goal, approach, discoveries, working_assumptions
fixed: cleaned up codebase: HOW_IT_WORKS.md added, outdated docs archived, hooks folder removed, unused code removed, website updated
fixed: implemented maintainability system - CHANGELOG.md, semantic versioning (v2.0.0), feature flags (config.py), layered docs structure
fixed: added mind_reminder_done tool + auto-mark for next session reminders - v2.1.0 shipped
decided: Consolidated docs: merged DESIGN_RATIONALE into ARCHITECTURE, archived PARSER.md, deleted obsolete CLI/IMPLEMENTATION/ONBOARDING. Added version banners (doc-version + last-updated) to all docs. Set 30-day periodic review reminder.
fixed: Updated website: get-started page, theme colors (light mode blue-tinted green #0d847a, dark mode bright #00C49A), smaller navbar/logo
learned: Light mode green needs more blue tint for readability - #0a8a6a was too pure green
learned: Theme variables need explicit overrides in both light AND dark mode sections - dark mode was falling back to root which got overwritten by light mode
decided: SESSION.md should be used for stream-of-consciousness logging, MEMORY.md for important permanent stuff only