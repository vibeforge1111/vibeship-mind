# Mind Architecture

## Overview

Mind is a file-based memory system for AI coding assistants. The core insight:

**The file is the memory. Mind is the lens.**

Instead of storing memories in a database via explicit tool calls, Claude writes directly to `.mind/MEMORY.md`. Mind watches, indexes, and injects context into `CLAUDE.md` automatically.

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
| 4 MCP tools | Focused, memorable |
| File-based memory | Claude already writes files |
| Daemon handles lifecycle | No explicit calls needed |
| Loose parsing | Natural language accepted |
| CLAUDE.md injection | Context appears automatically |

**Result:** Memory accumulates with normal work.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     .mind/MEMORY.md                         │
│                   (Source of Truth)                         │
│            Claude reads and writes directly                 │
└─────────────────────────────────────────────────────────────┘
                          │
            ┌─────────────┼─────────────┐
            ▼             ▼             ▼
     ┌──────────┐  ┌──────────┐  ┌──────────┐
     │ MEMORY.md│  │// MEMORY:│  │git commit│
     │ (direct) │  │(comments)│  │(messages)│
     └──────────┘  └──────────┘  └──────────┘
            │             │             │
            └─────────────┼─────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Mind Daemon                              │
│         (Runs in background, watches files)                 │
│                                                             │
│  • Detects file changes                                     │
│  • Parses memory content (loose regex)                      │
│  • Extracts decisions, issues, learnings                    │
│  • Updates search index                                     │
│  • Detects session end (30 min inactivity)                  │
│  • Updates CLAUDE.md with fresh context                     │
│  • Generates smart prompts (open loops, stale decisions)    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      CLAUDE.md                              │
│          (MIND:CONTEXT section auto-updated)                │
│                                                             │
│  Claude Code reads this automatically every session.        │
│  Memory is injected. No tool call needed.                   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   MCP Server (4 tools)                      │
│                                                             │
│  mind_search   - Semantic search across memories            │
│  mind_edges    - Check for gotchas before coding            │
│  mind_add_global_edge - Add cross-project gotcha            │
│  mind_status   - Check daemon status                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Session Start (Automatic)

```
1. Claude Code opens project
2. Claude Code reads CLAUDE.md (built-in behavior)
3. MIND:CONTEXT section is already there
4. Claude has full context without any tool call
```

### During Session (Multiple Capture Methods)

```
Method A: Direct to MEMORY.md
└── Claude appends: "decided JWT because simpler"
└── Mind watcher detects change
└── Parser extracts decision

Method B: Inline comments in code
└── Claude writes: // MEMORY: problem - Safari cookies
└── Mind watcher scans for MEMORY: prefix
└── Parser extracts issue

Method C: Git commits
└── Claude commits: "feat: auth - decided JWT over OAuth"
└── Mind watches .git/COMMIT_EDITMSG
└── Parser extracts from commit message
```

### Session End (Automatic)

```
1. Mind daemon detects 30 min inactivity
2. Parses all captured content
3. Extracts entities with confidence scores
4. Updates search index
5. Generates MIND:CONTEXT section
6. Writes to CLAUDE.md
7. Ready for next session
```

### Next Session (Automatic)

```
1. Claude Code opens project
2. CLAUDE.md has fresh MIND:CONTEXT
3. Claude immediately knows:
   - What we worked on last time
   - Open issues and loops
   - Relevant gotchas for current stack
   - Where to continue
```

---

## File Structure

### Project Level

```
project/
├── .mind/
│   ├── MEMORY.md              # Source of truth (git-tracked)
│   ├── .index/                # Mind's cache (gitignored)
│   │   ├── extracted.json     # Parsed entities
│   │   └── embeddings.db      # Vector search index
│   └── archive/               # Old entries (auto-rotated)
│       └── 2024.md
├── CLAUDE.md                  # Contains MIND:CONTEXT section
├── src/
└── ...
```

### Global Level

```
~/.mind/
├── config.toml                # Global settings
├── projects.json              # Registered projects
├── global_edges.json          # Cross-project gotchas
├── user_model.json            # User patterns/preferences
└── daemon.pid                 # Daemon process ID
```

---

## Components

### 1. Memory File (MEMORY.md)

The source of truth. Human-readable, git-tracked.

```markdown
<!-- MIND MEMORY - Append as you work. Write naturally.
Keywords: decided, problem, learned, tried, fixed, blocked, todo -->

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

**Decided:** CSS animations over Three.js - simpler, no deps
**Problem:** Safari gradient - tried standard CSS, fixed with -webkit
**Learned:** Safari needs vendor prefixes for backdrop-filter in 2024

Next: implement node connections

---
```

### 2. Context Section (in CLAUDE.md)

Auto-generated, always fresh:

```markdown
<!-- MIND:CONTEXT - Auto-generated. Do not edit. -->
## Memory: ✓ Active
Last captured: 5 min ago
This session: 2 decisions, 1 issue

## Session Context
- Last active: 2 hours ago (Dec 12, 3:45pm)
- Recent focus: Dashboard hero section

## Project State
- Goal: Ship v1 dashboard
- Stack: SvelteKit, FastAPI, SQLite
- Blocked: None

## Recent Decisions
- CSS animations over Three.js (Dec 12) - simpler
- File-based memory over database (Dec 12) - human-readable

## Open Loops
⚠️ Safari cookies bug - mentioned 2 sessions ago, no resolution
⚠️ "add refresh tokens" - noted as next step, not started

## Gotchas (This Stack)
- Safari ITP blocks cross-domain auth
- SvelteKit: auth checks in +page.server.ts
- Vercel Edge: use Web Crypto, not Node crypto

## Continue From
Last: Hero component CSS animations
Next suggested: Implement node connections
<!-- MIND:END -->
```

### 3. Daemon

Background process handling automation:

- Watches registered project directories
- Detects file changes (MEMORY.md, code files, git)
- Parses content with loose regex
- Updates search index
- Detects session boundaries (inactivity)
- Generates and injects MIND:CONTEXT

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

### 5. MCP Server

Four focused tools:

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `mind_search` | Semantic search | CLAUDE.md context isn't enough |
| `mind_edges` | Check gotchas | Before implementing risky code |
| `mind_add_global_edge` | Add cross-project gotcha | Found platform-wide issue |
| `mind_status` | Check daemon | Debugging, health check |

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
- **Intelligence (relationships, staleness)**

But Memory works without Mind.

### 3. Zero-Friction Intelligence

Mind detects patterns automatically:

- **Implicit relationships** - Links entities that reference each other
- **Temporal markers** - Flags "for MVP", "quick fix" decisions for review

No special syntax required. See [Intelligence Features](INTELLIGENCE.md).

### 3. Multiple Capture Points

Three ways to capture, all watched:

- MEMORY.md (direct)
- Code comments (// MEMORY:)
- Git commits (keywords)

If one fails, others might work.

### 4. Zero Commands During Work

After `mind init`:

- No start command
- No periodic checkpoints
- No end command
- Just work normally

### 5. Proactive, Not Passive

MIND:CONTEXT doesn't just show history:

- Open loops (unfinished business)
- Stale decisions (might need revisiting)
- Relevant gotchas (for current stack)
- Suggested next steps

### 6. Graceful Degradation

| Scenario | What Works |
|----------|------------|
| Daemon running | Full automation |
| Daemon stopped | Manual MEMORY.md, no auto-inject |
| Mind not installed | MEMORY.md still useful for Claude |
| New project | Immediate value after `mind init` |

---

## Performance Considerations

### File Watching

- Use OS-native watchers (inotify, FSEvents)
- Debounce rapid changes (100ms)
- Ignore .index/ directory

### Parsing

- Parse on change, not on read
- Cache parsed entities in .index/
- Incremental updates (diff-based)

### Embeddings

- Generate on first index, update incrementally
- Store in SQLite (portable)
- Lazy load (only when searching)

### CLAUDE.md Injection

- Update only on session boundary
- Atomic write (temp file + rename)
- Preserve non-MIND sections

---

## Security Considerations

### Local Data

- All data stays local by default
- .index/ is gitignored
- No network calls without explicit sync

### Global Edges

- Community edges could be poisoned
- Verification count as trust signal
- Local edges always trusted

### CLAUDE.md Modification

- Only modify between MIND: markers
- Preserve user content outside markers
- Backup before modification

---

## Future Considerations

### Potential Enhancements

- Cloud sync (encrypted, optional)
- Team shared edges
- IDE plugins (VSCode, Cursor)
- Voice capture integration
- Image/screenshot memory

### Platform Dependencies

- MCP can't see conversations (limitation)
- Claude Code has no hooks (limitation)
- File watching varies by OS

### Scaling

- Single project: trivial
- 10 projects: fine
- 100+ projects: may need selective watching
