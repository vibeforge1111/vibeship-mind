# How Mind Works

Mind gives Claude persistent memory through simple markdown files. No database, no cloud, no friction.

## Architecture

```
.mind/
├── MEMORY.md      # Permanent knowledge (decisions, learnings, gotchas)
├── SESSION.md     # Working memory (current session experiences)
├── REMINDERS.md   # Time and context-based reminders
└── state.json     # Timestamps for session detection

CLAUDE.md          # Context auto-injected here
```

## Two-Layer Memory

### MEMORY.md (Permanent)
Cross-session knowledge that persists forever:
- **Decisions** - "decided X because Y"
- **Learnings** - "learned that X", "TIL: X"
- **Problems** - "problem: X"
- **Progress** - "fixed: X"
- **Gotchas** - Project-specific gotchas

### SESSION.md (Working)
Within-session buffer that gets cleared on new sessions:
- **Experience** - Raw moments, thoughts, what's happening
- **Blockers** - Things stopping progress
- **Rejected** - What didn't work and why
- **Assumptions** - What I'm assuming true

When a new session starts (30 min gap), valuable items from SESSION.md get promoted to MEMORY.md automatically.

## The Flow

```
Session Start
     │
     ▼
mind_recall()  ──────► Loads MEMORY.md + SESSION.md
     │                  Detects session gap (>30 min)
     │                  If gap: promotes learnings, clears SESSION.md
     ▼
Claude works  ──────► mind_log() writes to appropriate file:
     │                  - experience/blocker/assumption/rejected → SESSION.md
     │                  - decision/learning/problem/progress → MEMORY.md
     ▼
Session End   ──────► SESSION.md preserved until next session
     │
     ▼
Next Session  ──────► Gap detected → promote → clear → fresh start
```

## MCP Tools (11 total)

### Core (use every session)
| Tool | Purpose |
|------|---------|
| `mind_recall()` | **CALL FIRST** - loads context, detects gaps |
| `mind_log(msg, type)` | Log to session or memory based on type |

### Type Routing for mind_log()

**SESSION.md (ephemeral):**
- `type="experience"` → raw moments, thoughts
- `type="blocker"` → things stopping progress
- `type="assumption"` → what you're assuming true
- `type="rejected"` → what didn't work and why

**MEMORY.md (permanent):**
- `type="decision"` → decided X because Y
- `type="learning"` → learned that X
- `type="problem"` → problem: X
- `type="progress"` → fixed: X

### Reading Tools
| Tool | Purpose |
|------|---------|
| `mind_session()` | Check current session state |
| `mind_search(query)` | Search past memories |
| `mind_status()` | Check memory health |
| `mind_reminders()` | List pending reminders |

### Action Tools
| Tool | Purpose |
|------|---------|
| `mind_blocker(desc)` | Log blocker + auto-search memory |
| `mind_remind(msg, when)` | Set time or context-based reminder |
| `mind_edges(intent)` | Check for gotchas before coding |
| `mind_checkpoint()` | Force process pending memories |
| `mind_add_global_edge()` | Add cross-project gotcha |

## Session Gap Detection

When `mind_recall()` is called:

1. Check time since last activity
2. If >30 minutes (configurable):
   - **Promote** valuable items from SESSION.md to MEMORY.md
   - **Clear** SESSION.md for fresh start
3. Return fresh context

### What Gets Promoted

From SESSION.md's **Rejected** section:
- Items with reasoning (contains " - ") → become decisions in MEMORY.md

From SESSION.md's **Experience** section:
- Items with tech patterns (React, Python, etc.) → become learnings
- Items with file paths or code references → become learnings
- Items with insight keywords (realized, learned, discovered) → become learnings

## Reminders

Two types:

**Time-based:**
```
mind_remind("Check security audit", "tomorrow")
mind_remind("Review PR", "in 3 days")
mind_remind("Demo prep", "next session")
```

**Context-based:**
```
mind_remind("Update auth tokens", "when I mention auth")
mind_remind("Check rate limits", "when we work on API")
```

Context reminders surface in `mind_recall()` output when keywords match.

## CLAUDE.md Integration

Mind injects a `<!-- MIND:CONTEXT -->` section into CLAUDE.md with:
- Recent decisions
- Open issues
- Key learnings
- Gotchas
- Session history

This happens lazily when `mind_recall()` is called - no daemon needed.

## Design Principles

1. **File is the memory** - MEMORY.md is source of truth, human-readable
2. **Zero friction** - Claude writes naturally, Mind extracts meaning
3. **Loose parsing** - Accept natural language, score confidence
4. **Stateless MCP** - Tools load and process on demand, no daemon
5. **Two layers** - Permanent memory + working session buffer
