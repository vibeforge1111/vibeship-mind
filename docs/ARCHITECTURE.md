# Mind Architecture (v2)

## Overview

Mind is a file-based memory system for AI coding assistants. The core insight:

**The file is the memory. Mind is the lens.**

Claude writes directly to `.mind/MEMORY.md`. Mind provides tools to search, detect gotchas, and load session context on demand.

## Why File-Based?

The obvious approach—explicit MCP tools for memory—fails:

| Issue | Impact |
|-------|--------|
| Many MCP tools | Too many for Claude to remember |
| Explicit session lifecycle | Claude forgets to call start/end |
| Rigid schemas | High friction, low adoption |
| Database-centric | Opaque, not human-readable |

**Result:** Memory doesn't accumulate.

Mind's approach:

| Design | Benefit |
|--------|---------|
| 8 focused MCP tools | Memorable, purposeful |
| File-based memory | Claude already writes files |
| Lazy session detection | `mind_recall()` checks timestamps |
| Loose parsing | Natural language accepted |
| CLAUDE.md injection | Context appears automatically |

**Result:** Memory accumulates with normal work.

---

## System Architecture (v2: MCP-Only)

```
+-----------------------------------------------------------------+
|                     .mind/MEMORY.md                              |
|                   (Source of Truth)                              |
|            Claude reads and writes directly                      |
+-----------------------------------------------------------------+
                          |
            +-------------+-------------+
            v             v             v
     +----------+  +----------+  +----------+
     | MEMORY.md|  |// MEMORY:|  |git commit|
     | (direct) |  |(comments)|  |(messages)|
     +----------+  +----------+  +----------+
            |             |             |
            +-------------+-------------+
                          v
+-----------------------------------------------------------------+
|                    MCP Server (8 tools)                          |
|                   (Stateless, on-demand)                         |
|                                                                  |
|  mind_recall()  - Load session context (CALL FIRST!)             |
|  mind_session() - Get current session state                      |
|  mind_blocker() - Log blocker + auto-search memory               |
|  mind_search()  - Semantic search across memories                |
|  mind_edges()   - Check for gotchas before coding                |
|  mind_checkpoint() - Force process pending memories              |
|  mind_add_global_edge() - Add cross-project gotcha               |
|  mind_status()  - Check memory health                            |
+-----------------------------------------------------------------+
                          |
                          v
+-----------------------------------------------------------------+
|                      CLAUDE.md                                   |
|          (MIND:CONTEXT section auto-updated)                     |
|                                                                  |
|  Claude Code reads this automatically every session.             |
|  Memory is injected. No tool call needed.                        |
+-----------------------------------------------------------------+
```

---

## Data Flow (v2)

### Session Start

```
1. Claude Code opens project
2. Claude Code reads CLAUDE.md (built-in behavior)
3. MIND:CONTEXT section has cached context
4. Claude calls mind_recall() (instructed by CLAUDE.md)
5. MCP checks timestamps:
   - Gap > 30 min? Process old SESSION.md, start fresh
   - MEMORY.md changed? Reparse
6. Returns fresh context + session state
```

### During Session

```
Claude writes to:
- .mind/MEMORY.md (decisions, problems, learnings)
- .mind/SESSION.md (goal, approach, blockers)
- Code comments (// MEMORY: decided X)

No MCP calls needed during work.
```

### Session End (Lazy)

```
1. User stops working (no explicit end needed)
2. Next time mind_recall() is called:
   - Detects gap > 30 min
   - Promotes discoveries from SESSION.md to MEMORY.md
   - Clears SESSION.md for new session
   - Returns fresh context
```

---

## File Structure

### Project Level

```
project/
+-- .mind/
|   +-- MEMORY.md              # Long-term memory (git-tracked)
|   +-- SESSION.md             # Session state (current session)
|   +-- state.json             # Timestamps for session detection
|   +-- .gitignore             # Ignores state.json
+-- CLAUDE.md                  # Contains MIND:CONTEXT section
+-- src/
+-- ...
```

### Global Level

```
~/.mind/
+-- config.toml                # Global settings
+-- projects.json              # Registered projects
+-- global_edges.json          # Cross-project gotchas
```

---

## Components

### 1. Memory File (MEMORY.md)

The source of truth. Human-readable, git-tracked.

```markdown
<!-- MIND MEMORY - Append as you work. Write naturally.
Keywords: decided, problem, learned, tried, fixed, blocked, KEY, important -->

# project-name

## Project State
- Goal: Ship v1 dashboard
- Stack: SvelteKit, FastAPI, SQLite
- Blocked: None

## Gotchas
- Safari ITP blocks cross-domain cookies after 7 days
- Vercel Edge can't use Node crypto

---

## Session Log

## 2024-12-12

Working on hero section. User wants living mind visualization.

decided: CSS animations over Three.js - simpler, no deps
problem: Safari gradient - tried standard CSS, fixed with -webkit
learned: Safari needs vendor prefixes for backdrop-filter in 2024

Next: implement node connections

---
```

### 2. Session File (SESSION.md)

Goal-oriented session tracking. Prevents rabbit holes.

```markdown
# Session: 2024-12-13

## The Goal
<!-- USER OUTCOME, not technical task -->
User can upload images and see them in their gallery

## Current Approach
<!-- What you're trying NOW + pivot condition -->
Using multer for uploads. Pivot if: memory issues with large files

## Blockers
<!-- When you add here, triggers memory search -->
- Image resize quality is poor

## Rejected Approaches
<!-- Strategic decisions with WHY -->
- Client-side resize - Quality loss unacceptable for photography app

## Working Assumptions
<!-- Question these when stuck -->
- User has stable internet
- Files under 10MB

## Discoveries
<!-- Tech patterns get promoted to MEMORY.md on session end -->
- multer stores files in /tmp by default
```

### 3. Context Section (in CLAUDE.md)

Auto-generated at `mind_recall()`:

```markdown
<!-- MIND:CONTEXT - Auto-generated. Do not edit. -->
## Memory: Active
Last captured: 5 min ago

## Session Context
Last active: 2 hours ago (Dec 12, 3:45pm)

## Project State
- Goal: Ship v1 dashboard
- Stack: SvelteKit, FastAPI, SQLite
- Blocked: None

## Recent Decisions
- CSS animations over Three.js (Dec 12) - simpler
- File-based memory over database (Dec 12) - human-readable

## Open Loops
[!] Safari cookies bug - mentioned 2 sessions ago, no resolution
[!] "add refresh tokens" - noted as next step, not started

## Gotchas (This Stack)
- Safari ITP blocks cross-domain auth
- SvelteKit: auth checks in +page.server.ts

## Continue From
Last: Hero component CSS animations
<!-- MIND:END -->
```

### 4. Parser

Loose extraction from natural language:

```python
# Accepts all of these as decisions:
"decided to use JWT"
"chose Supabase over Firebase"
"going with CSS animations"
"**Decided:** Use Web Crypto API"

# Confidence scoring:
# - Explicit format (**Decided:**) = high
# - Has reasoning ("because") = +0.2
# - Clear keywords = medium
# - Vague mention = low
```

### 5. MCP Server (8 tools)

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `mind_recall` | Load session context | **FIRST every session** |
| `mind_session` | Get current session state | Feeling lost or off-track |
| `mind_blocker` | Log blocker + search memory | When stuck |
| `mind_search` | Semantic search | CLAUDE.md context isn't enough |
| `mind_edges` | Check gotchas | Before risky code |
| `mind_checkpoint` | Force process memories | After many writes |
| `mind_add_global_edge` | Add cross-project gotcha | Found platform issue |
| `mind_status` | Check health | Debugging |

---

## Design Principles

### 1. File is the Memory

MEMORY.md is the source of truth. Everything else is cache.

- Human-readable
- Git-trackable
- Survives crashes
- Works without Mind running

### 2. Mind is the Lens

Mind adds value through:

- Indexing (fast search)
- Extraction (structure from prose)
- Injection (context into CLAUDE.md)
- Detection (edges before mistakes)

But Memory works without Mind.

### 3. Stateless MCP (v2)

No daemon, no file watchers, no background processes.

- `mind_recall()` does lazy session detection
- Checks timestamps and file hashes on demand
- Promotes learnings when gap detected
- Zero ops burden

### 4. Two-Layer Memory

**Long-term (MEMORY.md):**
- Decisions, problems, learnings
- Persists across sessions
- Git-tracked

**Short-term (SESSION.md):**
- Goal, approach, blockers
- Prevents rabbit holes
- Cleared on session end

### 5. Zero Commands During Work

After `mind init`:

- No start command
- No periodic checkpoints
- No end command
- Just work normally

### 6. Graceful Degradation

| Scenario | What Works |
|----------|------------|
| MCP available | Full functionality |
| MCP unavailable | MEMORY.md still useful, stale CLAUDE.md |
| New project | Immediate value after `mind init` |

---

## Performance

### Lazy Processing

- Parse MEMORY.md only when `mind_recall()` called
- Check hash to skip if unchanged
- No background CPU usage

### State File

```json
{
  "last_activity": 1702400000000,
  "memory_hash": "a1b2c3d4e5f6",
  "schema_version": 2
}
```

Used for:
- Gap detection (30 min threshold)
- Change detection (hash comparison)

---

## Security

### Local Data

- All data stays local by default
- .index/ is gitignored
- No network calls

### Global Edges

- Stored in ~/.mind/global_edges.json
- Local edges always trusted
- User controls what gets added

### CLAUDE.md Modification

- Only modify between MIND: markers
- Preserve user content outside markers
