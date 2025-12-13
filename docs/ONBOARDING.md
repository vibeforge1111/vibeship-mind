# Mind Onboarding (v2)

## Quick Install

```bash
# 1. Clone and install
git clone https://github.com/anthropics/vibeship-mind.git
cd vibeship-mind
uv sync

# 2. Add MCP to Claude Code config
# See "Claude Code Setup" section below

# 3. Initialize in your project
cd /path/to/your-project
uv run --directory /path/to/vibeship-mind mind init
```

Done. Start working.

---

## Claude Code Setup

Add Mind to your MCP config:

**macOS/Linux:** `~/.config/claude/mcp.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mind": {
      "command": "uv",
      "args": ["--directory", "/path/to/vibeship-mind", "run", "mind", "mcp"]
    }
  }
}
```

Restart Claude Code after adding.

---

## First-Run Output

After `mind init`, you'll see:

```
[+] Created .mind/MEMORY.md
[+] Created .mind/SESSION.md
[+] Updated CLAUDE.md with MIND:CONTEXT
[+] Detected stack: sveltekit, typescript, tailwind
[+] Registered project with Mind

Mind initialized! Start working - append notes to .mind/MEMORY.md

MCP tools available:
  - mind_recall() : Load session context (call first!)
  - mind_session() : Get current session state
  - mind_search() : Search memories
  - mind_checkpoint() : Force process pending memories
  - mind_edges() : Check for gotchas
```

---

## How It Works

1. **CLAUDE.md tells Claude to call `mind_recall()` first**
2. **Claude writes to `.mind/MEMORY.md` as it works**
3. **Next session, `mind_recall()` loads the context**

No daemon. No background processes. Just files and MCP.

---

## Memory Status Indicator

MIND:CONTEXT shows proof it's working:

```markdown
<!-- MIND:CONTEXT -->
## Memory: Active
Last captured: 5 min ago

## Project State
- Stack: python, fastapi
- Goal: Ship v1 dashboard
- Blocked: None

## Recent Decisions
- Use JWT for auth (Dec 12) - simpler than sessions
...
```

---

## Writing Memory

Claude writes to `.mind/MEMORY.md` naturally:

```markdown
## 2024-12-12

Working on hero section.

decided: CSS animations over Three.js - simpler, no deps
problem: Safari gradient - tried standard CSS, fixed with -webkit
learned: Safari needs vendor prefixes for backdrop-filter in 2024

Next: implement node connections
```

**Keywords that get parsed:**
- `decided`, `chose`, `going with` - Decisions
- `problem`, `bug`, `stuck`, `blocked` - Issues
- `learned`, `TIL`, `gotcha`, `realized` - Learnings
- `KEY`, `important` - Never-fade items

---

## Session Tracking

`.mind/SESSION.md` keeps you focused:

```markdown
# Session: 2024-12-13

## The Goal
User can upload images and see them in their gallery

## Current Approach
Using multer for uploads. Pivot if: memory issues with large files

## Blockers
- Image resize quality is poor

## Discoveries
- multer stores files in /tmp by default
```

When you add a blocker, use `mind_blocker()` to auto-search memory for solutions.

---

## MCP Tools

| Tool | When to Use |
|------|-------------|
| `mind_recall()` | **FIRST every session** |
| `mind_session()` | Feeling lost or off-track |
| `mind_blocker()` | When stuck on something |
| `mind_search()` | Need details not in context |
| `mind_edges()` | Before risky code |
| `mind_checkpoint()` | Force process memories |

Most sessions: Just `mind_recall()` at start, then work normally.

---

## Troubleshooting

### "MIND:CONTEXT not appearing"

```bash
# Check CLAUDE.md exists
cat CLAUDE.md | head -20

# Reinitialize
uv run mind init
```

### "mind_recall returns old data"

```bash
# Force refresh
# In Claude: mind_recall(force_refresh=True)

# Or checkpoint
# In Claude: mind_checkpoint()
```

### "Search returns nothing"

Check MEMORY.md has content with keywords:
- decided, chose, going with
- problem, issue, bug, stuck
- learned, discovered, realized

### "MCP not connecting"

1. Check config path is correct
2. Check `uv` is available in PATH
3. Restart Claude Code
4. Check MCP logs

---

## Success Indicators

**It's working if:**
- CLAUDE.md has MIND:CONTEXT section
- `mind_recall()` returns context
- `mind_search("anything")` returns results
- Claude references past decisions without being told

**Something's wrong if:**
- No MIND:CONTEXT in CLAUDE.md (run `mind init`)
- mind_recall returns empty (check MEMORY.md has content)
- Search returns nothing (check keywords in MEMORY.md)

---

## Adoption Timeline

| Time | What Happens |
|------|--------------|
| Day 1 | Install, init, start using |
| Day 2 | Notice context appearing |
| Week 1 | Start writing more explicitly |
| Week 2 | Use search and blocker tools |
| Month 1 | Muscle memory, automatic |

---

## Quick Reference

```bash
# Initialize
uv run mind init

# Check health
uv run mind doctor

# Parse and show entities
uv run mind parse

# Show status
uv run mind status
```

In Claude Code:
- `mind_recall()` - Always first
- `mind_session()` - When lost
- `mind_blocker("stuck on X")` - When stuck
- `mind_search("auth")` - Find memories
