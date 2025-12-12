<!-- MIND MEMORY - This file IS the project context.
Read fully at session start. Append as you work.
Format doesn't matter - just write. Mind will parse.

Keywords Mind looks for: decided, problem, learned, tried, gotcha, blocked, next -->

# vibeship-mind

## Project State
- **Goal:** Build Mind MCP - semantic memory layer for Claude Code
- **Stack:** Python, FastAPI, SQLite, MCP, Next.js (dashboard)
- **Status:** Active development, v0.1

## Gotchas
- Vercel Edge runtime: use Web Crypto API, not Node.js crypto
- Safari ITP blocks cross-domain cookies after 7 days
- MCP tools can't see conversation - only tool calls

## Key Decisions
- SQLite + vector embeddings for storage (local-first, portable)
- Six entity types: decisions, issues, edges, episodes, sessions, user
- MCP primary interface, HTTP secondary (for dashboard)
- File-based memory (.mind/MEMORY.md) as source of truth
- In-repo storage, not global (~/.mind/)

---

## Dec 12 (Session 6 - continuing)

context restored from previous session summary. fixed ParsedMemory dataclass -
was missing project_state field that parser was setting. now properly typed.

all 148 tests pass. memory system is complete:
- MEMORY.md as load-bearing source of truth
- MemoryFileParser extracts structured data from loose writing
- session.py reads MEMORY.md on start, combines with primer
- CLAUDE.md references the memory file

remaining work:
- Mind feedback comments (write back `<!-- MIND: Too vague -->`)
- project registry (~/.mind/projects.json)
- mind_search tool to query indexed memories

---

## Dec 12 (Session 5)

redesigning memory capture. problem is discipline - humans forget end_session,
claude forgets periodic tool calls. any "remember to do X" fails.

decided file-based approach. MEMORY.md is the source of truth. claude writes
directly, mind watches and indexes. works even without mind running.

key insight: make the file load-bearing. it contains project context, not just
history. if claude skips reading it, claude gives worse answers. self-interest
drives adoption.

also: stream of consciousness is fine. no rigid format. just dump thoughts.
mind parses loosely - keywords like "decided", "problem", "learned" are enough.

built MemoryFileParser and integrated into session start. tests pass.
updated CLAUDE.md to reference this file.

---

## Dec 12 (Session 4 - 45 min)

fixed session auto-close. was losing artifacts when sessions timed out.
now auto-close captures decisions/issues/edges made during session.
also fixed export datetime serialization bug.

---

## Dec 12 (Session 3 - 1.5 hours)

built next.js dashboard. vibeship design language - dark theme, purple/blue
gradients, card-based. "living mind" visualization concept.

pages: dashboard hero, project detail (5 tabs), global edges, navbar with logo.

---

## Dec 12 (Session 2 - 1 hour)

added HTTP API on top of MCP. routes for all entities. MCP stays primary,
HTTP for dashboard and external tools.

---

## Dec 12 (Session 1 - 2 hours)

built Mind MCP foundation. sqlite + vectors, six entity types, mcp tools.
learned about vercel edge crypto limitation - use web crypto api.

---
