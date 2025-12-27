# Mind Architecture (v2)

<!-- doc-version: 2.2.0 | last-updated: 2025-12-15 -->

## Overview

Mind is a file-based memory system for AI coding assistants. The core insight:

**The file is the memory. Mind is the lens.**

Claude writes directly to `.mind/MEMORY.md`. Mind provides tools to search, detect gotchas, and load session context on demand.

---

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
| 12 focused MCP tools | Memorable, purposeful |
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
|                    MCP Server (12 tools)                         |
|                   (Stateless, on-demand)                         |
|                                                                  |
|  CORE:                                                           |
|    mind_recall()  - Load session context (CALL FIRST!)           |
|    mind_log()     - Log to session or memory (routes by type)    |
|                                                                  |
|  READING:                                                        |
|    mind_session() - Get current session state                    |
|    mind_search()  - Semantic search across memories              |
|    mind_status()  - Check memory health                          |
|    mind_reminders() - List pending reminders                     |
|                                                                  |
|  ACTIONS:                                                        |
|    mind_blocker() - Log blocker + auto-search memory             |
|    mind_remind()  - Set time or context reminder                 |
|    mind_reminder_done() - Mark reminder as complete              |
|    mind_edges()   - Check for gotchas before coding              |
|    mind_checkpoint() - Force process pending memories            |
|    mind_add_global_edge() - Add cross-project gotcha             |
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
6. Returns fresh context + session state + due reminders
```

### During Session

```
Claude uses mind_log() to capture:
- experience, blocker, assumption, rejected -> SESSION.md
- decision, learning, problem, progress -> MEMORY.md

No manual file editing needed.
```

### Session End (Lazy)

```
1. User stops working (no explicit end needed)
2. Next time mind_recall() is called:
   - Detects gap > 30 min
   - Promotes discoveries from SESSION.md to MEMORY.md
   - Clears SESSION.md for new session
   - Auto-marks "next session" reminders as done
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
|   +-- REMINDERS.md           # Time and context reminders
|   +-- config.json            # Feature flags
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

Working memory buffer. Cleared on new session.

```markdown
# Current Session

## Experience
<!-- Raw moments, thoughts, what's happening -->

## Blockers
<!-- Things stopping progress -->

## Rejected
<!-- What didn't work and why -->

## Assumptions
<!-- What I'm assuming true -->
```

### 3. Reminders File (REMINDERS.md)

Time-based and context-based reminders.

```markdown
# Reminders

## Pending
- [ ] Check security audit | due: tomorrow
- [ ] Review auth flow | trigger: when I mention auth

## Done
- [x] Update docs | completed: 2025-12-13
```

### 4. Context Section (in CLAUDE.md)

Auto-generated at `mind_recall()`:

```markdown
<!-- MIND:CONTEXT - Auto-generated. Do not edit. -->
## Memory: Active
Last captured: 5 min ago

## Reminders Due
You have 1 reminder(s) for this session:
- Check if X works

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

## Gotchas (This Stack)
- Safari ITP blocks cross-domain auth

## Continue From
Last: Hero component CSS animations
<!-- MIND:END -->
```

### 5. Semantic Similarity Engine

Mind uses TF-IDF based similarity for intelligent memory operations:

**Loop Detection:**
When logging a `rejected` approach, Mind checks similarity against previous rejections. If >60% similar, it warns with severity levels:
- Critical (>95%): Exact match - you've tried this before
- High (>80%): Very similar approach
- Moderate (>60%): Similar enough to reconsider

**Smart Promotion:**
When promoting SESSION.md items to MEMORY.md, Mind checks novelty:
- Novel content: Added normally
- Duplicate (>90%): Skipped
- Similar (70-90%): Links to existing entry or supersedes it

**Semantic Search:**
`mind_search()` ranks results by TF-IDF relevance, not just keyword match.

Lightweight implementation - no embeddings, no external API, works offline.

### 6. Parser

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

See [archive/PARSER.md](archive/PARSER.md) for full specification.

### 7. MCP Server (12 tools)

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `mind_recall` | Load session context | **FIRST every session** |
| `mind_log` | Log to session or memory (with loop detection) | As you work |
| `mind_session` | Get current session state | Feeling lost or off-track |
| `mind_search` | Semantic search | CLAUDE.md context isn't enough |
| `mind_status` | Check health | Debugging |
| `mind_reminders` | List pending reminders | Check what's set |
| `mind_blocker` | Log blocker + search memory | When stuck |
| `mind_remind` | Set time/context reminder | "Remind me..." |
| `mind_reminder_done` | Mark reminder complete | After completing reminded task |
| `mind_edges` | Check gotchas | Before risky code |
| `mind_checkpoint` | Force process memories | After many writes |
| `mind_add_global_edge` | Add cross-project gotcha | Found platform issue |

See [MCP_TOOLS.md](MCP_TOOLS.md) for full parameter documentation.

---

## Design Principles

### 1. File is the Memory

MEMORY.md is the source of truth. Everything else is cache.

- Human-readable and editable
- Git-trackable (history for free)
- Survives crashes (it's just a file)
- Works without Mind running
- Claude already knows how to write files

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
- Decisions, problems, learnings, progress
- Persists across sessions
- Git-tracked

**Short-term (SESSION.md):**
- Experience, blockers, rejected, assumptions
- Working buffer
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

## Trade-offs Accepted

### Less Structured Data

Tool-based approach gives perfectly structured data. File-based gives prose that needs parsing.

**Accepted because:** Having messy-but-present memory > having perfectly-structured-but-empty memory.

### Parser Imperfection

Loose parsing will miss some things, occasionally misinterpret, have false positives.

**Accepted because:** Confidence scoring flags uncertainty. Something captured > nothing captured.

### Stale Context Possibility

If `mind_recall()` isn't called, CLAUDE.md context may be stale.

**Accepted because:** CLAUDE.md instructions tell Claude to call it first. Stale context is still useful.

---

## What We Removed (v2)

- **Daemon** - Background process for file watching
- **Real-time context updates** - Required daemon
- **PID file management** - Platform-specific
- **Signal handlers** - Daemon complexity
- **Auto-start configs** - launchd, systemd, Task Scheduler

**Why:** Stateless MCP is simpler and more reliable.

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
- state.json is gitignored
- No network calls

### Global Edges

- Stored in ~/.mind/global_edges.json
- Local edges always trusted
- User controls what gets added

### CLAUDE.md Modification

- Only modify between MIND: markers
- Preserve user content outside markers
