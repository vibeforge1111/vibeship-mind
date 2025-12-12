# Mind

> Memory that accumulates automatically.

Mind gives AI coding assistants persistent memory across sessions. Not through explicit tool calls—through natural file writing.

**The file is the memory. Mind is the lens.**

## The Problem

Every AI conversation starts from zero:
- What we decided yesterday? Forgotten.
- What we tried that didn't work? Unknown.
- The gotchas we've hit before? Re-discovered.
- Where we left off? Lost.

The obvious approach—explicit tool calls for memory—fails because Claude forgets to call them.

## The the new Solution

```
project/
├── .mind/
│   └── MEMORY.md     ← Claude writes here naturally
└── CLAUDE.md         ← Mind injects context automatically
```

**Zero tools during work. Zero commands at session end. Memory just accumulates.**

---

## How It Works

### 1. Initialize Once

```bash
cd my-project
mind init

✓ Created .mind/MEMORY.md
✓ Added MIND:CONTEXT to CLAUDE.md
✓ Detected stack: sveltekit, typescript
✓ Watching for changes
```

### 2. Work Normally

Claude writes to `.mind/MEMORY.md` as you work:

```markdown
## 2024-12-12

Working on auth flow.

**Decided:** JWT over sessions - stateless, simpler
**Problem:** Safari cookies - ITP blocking cross-domain
**Learned:** Safari deletes third-party cookies after 7 days

Next: implement refresh tokens
```

Or drops inline comments in code:

```typescript
// MEMORY: decided Zod for validation - runtime type safety
// MEMORY: problem - TypeScript inference broken with generics
```

### 3. Mind Handles the Rest

Mind daemon (runs in background):
- Watches for file changes
- Parses natural language (loose regex, accepts messy input)
- Updates search index
- Detects session end (30 min inactivity)
- Injects fresh context into CLAUDE.md

### 4. Next Session Starts Informed

Claude reads CLAUDE.md (it does this automatically) and sees:

```markdown
<!-- MIND:CONTEXT -->
## Session Context
Last active: 2 hours ago

## Recent Decisions
- JWT over sessions (Dec 12) - stateless, simpler

## Open Loops
⚠️ Safari cookies - mentioned 2 sessions ago, unresolved
⚠️ "implement refresh tokens" - noted as next, not started

## Gotchas (This Stack)
- Safari ITP blocks cross-domain cookies after 7 days
- Vercel Edge can't use Node crypto → use Web Crypto

## Continue From
Last: Auth flow
Next: Implement refresh tokens
<!-- MIND:END -->
```

**No tool call. No command. Context just appears.**

---

## Quick Start

### One-Line Install

```bash
curl -sSL https://mind.vibeship.dev/install | sh
```

Does everything: installs, initializes, starts daemon, configures Claude Code.

### Or Manual (3 Commands)

```bash
pip install mind-memory
mind init
mind daemon start
```

### Add to Claude Code

Add to `~/.config/claude/mcp.json`:

```json
{
  "mcpServers": {
    "mind": {
      "command": "mind",
      "args": ["mcp"]
    }
  }
}
```

That's it. Work normally. Memory accumulates.

See [Onboarding Guide](docs/ONBOARDING.md) for detailed setup.

---

## Three Ways to Capture

Mind watches all three:

### 1. Direct to MEMORY.md

```markdown
## Dec 12

decided JWT because simpler. hit Safari cookie issue.
learned ITP blocks cross-domain after 7 days.
```

### 2. Inline Comments

```typescript
// MEMORY: decided Zod for validation
// MEMORY: problem - generic inference broken
```

### 3. Git Commits

```bash
git commit -m "feat: auth

decided: JWT over sessions - stateless
learned: Safari ITP blocks third-party cookies"
```

Any of these work. Use what's natural.

---

## MCP Tools (4 Total)

Most functionality is automatic. Tools are for explicit queries:

| Tool | Purpose |
|------|---------|
| `mind_search` | Semantic search when CLAUDE.md context isn't enough |
| `mind_edges` | Check for gotchas before implementing risky code |
| `mind_add_global_edge` | Add cross-project gotcha |
| `mind_status` | Check daemon health |

**Typical session: 0-2 tool calls.** Everything else is automatic.

---

## CLI Reference

```bash
# Project setup
mind init                # Initialize Mind in project
mind add .               # Register project with daemon

# Daemon
mind daemon start        # Start background daemon
mind daemon stop         # Stop daemon
mind daemon status       # Check status

# Information
mind list                # List projects
mind search "query"      # Search memories
mind context             # Show current MIND:CONTEXT
mind edges               # List global edges

# Maintenance
mind index               # Force reindex
mind doctor              # Health check
```

---

## File Structure

```
project/
├── .mind/
│   ├── MEMORY.md        # Source of truth (git-tracked)
│   └── .index/          # Search cache (gitignored)
└── CLAUDE.md            # Gets MIND:CONTEXT injected

~/.mind/
├── config.toml          # Settings
├── projects.json        # Registered projects
└── global_edges.json    # Cross-project gotchas
```

---

## Configuration

```toml
# ~/.mind/config.toml

[daemon]
inactivity_minutes = 30    # Session end detection

[context]
max_decisions = 5          # Recent decisions to show
max_open_loops = 3         # Open loops to show
max_gotchas = 5            # Gotchas to show

[parser]
confidence_threshold = 0.3 # Minimum extraction confidence
```

---


---

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design
- [MCP Tools](docs/MCP_TOOLS.md) - Tool specifications
- [Parser](docs/PARSER.md) - Extraction patterns
- [Daemon](docs/DAEMON.md) - Background process
- [CLI](docs/CLI.md) - Command reference
- [Implementation](docs/IMPLEMENTATION.md) - Build plan

---

## Philosophy

**The obvious approach:** Explicit tool calls for memory.
**The problem:** Claude forgets to call them.

**Mind's approach:** Claude writes files anyway. Watch those files.
**The result:** Memory accumulates naturally.

The shift: From "remember to call memory tools" to "write to files like you already do."

---

## Part of VibeShip

Mind is one component of the VibeShip ecosystem:

- **Scanner** - Find what's wrong in your code
- **Mind** - Remember everything across sessions
- **Spawner** - AI skills and validation for shipping
- **Experts** - Connect with humans when stuck

---

## License

MIT - do whatever you want.

---

*Memory should be automatic, not another task.*
