# Mind Design Rationale (v2)

## Why File-Based Memory?

Mind uses `.mind/MEMORY.md` as the source of truth instead of a database with explicit tool calls. This document explains why.

---

## The Problem with Tool-Based Memory

The obvious approach to AI memory: create tools for capturing and retrieving memories.

```
mind_start_session()
mind_add_decision(title, reasoning, ...)
mind_add_issue(title, symptoms, ...)
mind_end_session(summary, ...)
mind_get_context()
```

**Why this fails:**

| Issue | Impact |
|-------|--------|
| Claude forgets to call tools | Memory stays empty |
| Explicit session lifecycle | Users forget to end sessions |
| Many tools to remember | Cognitive overload |
| Rigid schemas | High friction to capture |
| On-request context | Must remember to ask |

**Result:** Sessions stay empty. Memory doesn't accumulate.

---

## The File-Based Solution

**Insight:** Claude already writes files constantly. Leverage that.

```
project/.mind/MEMORY.md  <- Claude writes here naturally
project/CLAUDE.md        <- Mind injects context automatically
```

| Aspect | Tool-Based | File-Based |
|--------|------------|------------|
| Source of truth | Database | .mind/MEMORY.md |
| MCP tools needed | 10+ | 8 (focused) |
| Session management | Explicit | Lazy (mind_recall) |
| Capture method | Tool calls | File writes |
| Format | Rigid schemas | Loose parsing |
| Context delivery | On request | Auto-injected |
| Human readable | No | Yes |
| Git trackable | No | Yes |

---

## Key Design Decisions

### 1. File is the Memory

MEMORY.md is the source of truth. Everything else is cache.

**Why:**
- Human-readable and editable
- Git-trackable (history for free)
- Survives crashes (it's just a file)
- Works without Mind running
- Claude already knows how to write files

### 2. CLAUDE.md Injection

Mind auto-injects context into CLAUDE.md rather than requiring a tool call.

**Why:**
- Claude Code reads CLAUDE.md automatically
- Zero tool calls needed for context
- Always fresh (updated on recall)
- Fails gracefully (stale context still useful)

### 3. Loose Parsing

Accept natural language, score confidence:

```
"decided JWT because simpler"        -> confidence: 0.6
"**Decided:** Use JWT - simpler"     -> confidence: 0.9
```

**Why:**
- Lower friction than structured formats
- Captures something rather than nothing
- Confidence scores flag uncertain extractions
- Natural for Claude to write

### 4. Multiple Capture Methods

Three ways to capture, all parsed:
- Direct to MEMORY.md
- Inline comments (`// MEMORY: decided X`)
- Git commits (keywords in messages)

**Why:**
- If one method fails, others might work
- Fits different workflows
- No single point of failure

### 5. Lazy Session Detection (v2)

Sessions detected lazily via `mind_recall()` instead of a background daemon.

**Why:**
- No daemon to crash or manage
- No file watchers consuming resources
- No platform-specific configs (launchd, systemd)
- Simpler = more reliable
- MCP is stateless by design

### 6. Two-Layer Memory

Long-term (MEMORY.md) + Short-term (SESSION.md):

**MEMORY.md:**
- Decisions, problems, learnings
- Persists forever
- Git-tracked

**SESSION.md:**
- Goal, approach, blockers
- Prevents rabbit holes
- Cleared on session end

**Why:**
- Different concerns need different lifespans
- SESSION.md prevents Claude from losing focus
- Discoveries get promoted to MEMORY.md automatically

### 7. Focused MCP Tools (8)

Only tools that add value beyond file operations:

| Tool | Why It Can't Be a File |
|------|------------------------|
| `mind_recall` | Needs lazy session detection |
| `mind_session` | Structured session state access |
| `mind_blocker` | Auto-search + logging |
| `mind_search` | Semantic search across memories |
| `mind_edges` | Pattern matching + global edges |
| `mind_checkpoint` | Force reprocessing |
| `mind_add_global_edge` | Cross-project storage |
| `mind_status` | Health check |

Everything else goes through MEMORY.md.

---

## Trade-offs Accepted

### Less Structured Data

Tool-based approach gives perfectly structured data:
```python
Decision(
    title="Use JWT",
    reasoning="Simpler than sessions",
    alternatives=[...],
    confidence=0.8
)
```

File-based approach gives prose that needs parsing:
```markdown
decided to use JWT because simpler than sessions
```

**Accepted because:** Having messy-but-present memory > having perfectly-structured-but-empty memory.

### Parser Imperfection

Loose parsing will:
- Miss some things
- Occasionally misinterpret
- Have false positives

**Accepted because:**
- Confidence scoring flags uncertainty
- Something captured > nothing captured
- Users can always write explicitly

### Stale Context Possibility

If `mind_recall()` isn't called, CLAUDE.md context may be stale.

**Accepted because:**
- CLAUDE.md instructions tell Claude to call it first
- Stale context is still useful
- Better than daemon reliability issues

---

## What We Removed (v2)

### Daemon

v1 had a background daemon for file watching and session detection.

**Removed because:**
- Daemons crash and need restart
- PID file management is fragile
- Platform-specific configs (launchd, systemd, Task Scheduler)
- Resource consumption even when not coding
- MCP can do lazy detection instead

### Real-Time Context Updates

v1 updated CLAUDE.md immediately on file changes.

**Removed because:**
- Requires daemon running
- Same-session context not that important
- `mind_recall()` can refresh on demand

---

## What We Didn't Build

### Real-Time Conversation Capture

MCP can't see conversation content. If it could, memory would be truly passive.

**Limitation:** Platform constraint, not a design choice.

### IDE Hooks

If Claude Code had on-start/on-end hooks, session detection would be trivial.

**Limitation:** Platform constraint, not a design choice.

### Structured Extraction

We could require `**Decided:**` format everywhere for perfect parsing.

**Rejected because:** Too much friction. Users won't do it consistently.

---

## Summary

| Principle | Implementation |
|-----------|----------------|
| File is the memory | .mind/MEMORY.md source of truth |
| Mind is the lens | Indexes, searches, injects context |
| Auto-inject context | MIND:CONTEXT in CLAUDE.md |
| Multiple capture | File, comments, commits |
| Loose parsing | Natural language, confidence scores |
| Lazy sessions | mind_recall() checks timestamps |
| Two-layer memory | MEMORY.md (long) + SESSION.md (short) |
| Focused tools | 8 tools for things files can't do |
| No daemon | Stateless MCP, zero ops |

**The goal:** Memory that accumulates through normal work, not explicit memory management.
