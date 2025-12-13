# Mind

> Mind gives Claude a mind - not just memory across sessions, but focus within them. It remembers what worked, what didn't, and what it's supposed to be building.

When you're vibe coding with Claude, it forgets everything between sessions. What you decided, what broke, what worked - gone. Even worse, in long sessions it starts suggesting the same failed fixes over and over.

Mind fixes both problems with two-layer memory:
- **MEMORY.md** - Long-term memory across sessions
- **SESSION.md** - Short-term focus within a session

---

## Why Mind?

**2-prompt install.** Clone the repo, tell Claude to add the MCP server. Done.

**Fully automated.** No commands to run during or after work:
- Claude writes memories as it works
- Session gaps auto-detected (30 min)
- Learnings auto-promoted to long-term memory
- Context auto-injected into CLAUDE.md
- Reminders auto-surface when due or when keywords match

**Two-layer memory:**
- Cross-session recall (MEMORY.md)
- Within-session focus (SESSION.md)

**Zero friction.** Claude writes to files, MCP reads them lazily. No database, no cloud, no sync issues.

**Human-readable.** Plain `.md` files you can open, edit, or git-track anytime.

**Open source.** See exactly how it works. No black box.

---

## Install

**Requires:** [uv](https://docs.astral.sh/uv/) (Claude Code installs uv automatically)

```bash
git clone https://github.com/vibeforge1111/vibeship-mind.git
cd vibeship-mind
uv sync
uv run mind init
```

That's it. Now connect to Claude Code below.

---

## Connect to Claude Code

Add Mind as an MCP server to give Claude memory tools:

**Easy way:** Just paste this to Claude:

> Add Mind MCP server from github.com/vibeforge1111/vibeship-mind to my config

**Manual way:**

1. Open your MCP config file:
   - Mac/Linux: `~/.config/claude/mcp.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add this (replace path with where you cloned vibeship-mind):

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

3. Restart Claude Code

---

## MCP Tools

| Tool | What it does |
|------|--------------|
| `mind_recall()` | Load session context - CALL FIRST every session |
| `mind_session()` | Check current session state (goal, approach, blockers) |
| `mind_blocker(desc)` | Log blocker + auto-search memory for solutions |
| `mind_search(query)` | Search past memories |
| `mind_edges(intent)` | Check for gotchas before risky code |
| `mind_checkpoint()` | Force process pending memories |
| `mind_status()` | Check memory health |
| `mind_add_global_edge()` | Add cross-project gotcha (platform/language issues) |
| `mind_remind(msg, when)` | Set reminder - time or context-based |
| `mind_reminders()` | List pending reminders |

---

## How It Works

**Long-term (MEMORY.md):** Claude writes decisions, problems, learnings. Next session, `mind_recall()` loads context so Claude knows what happened before.

**Short-term (SESSION.md):** Goal-oriented session tracking:
- **The Goal** - User outcome (not technical task)
- **Current Approach** - What you're trying + when to pivot
- **Blockers** - When stuck, triggers memory search
- **Rejected Approaches** - Strategic decisions with WHY
- **Working Assumptions** - Question these when stuck
- **Discoveries** - Gets promoted to MEMORY.md on session end

When a new session starts (30 min gap), important learnings get promoted from SESSION.md to MEMORY.md automatically.

---

## Reminders

Mind supports two types of reminders:

**Time-based:**
- `"tomorrow"`, `"in 3 days"`, `"next session"`, `"2025-12-20"`

**Context-based:**
- `"when I mention auth"` - triggers when relevant keywords come up
- `"when we work on database"` - Claude sees keywords and surfaces reminder naturally

Example: *"Remind me to check the security audit when we work on auth"*

Reminders are stored in `.mind/REMINDERS.md` and shown in `mind_recall()` output.

---

## Initialize Mind in Any Project

From your project folder, run:

```bash
uv --directory ~/vibeship-mind run mind init
```

(Adjust `~/vibeship-mind` if you cloned it somewhere else)

**Using Claude Code?** Just paste this:

> Run `uv --directory ~/vibeship-mind run mind init` to set up Mind in this project

This creates `.mind/MEMORY.md` and `.mind/SESSION.md`.

---

## Quick Commands

```bash
# Check if everything is working
uv --directory /path/to/vibeship-mind run mind doctor

# See what Mind extracted from your notes
uv --directory /path/to/vibeship-mind run mind parse

# Check project status
uv --directory /path/to/vibeship-mind run mind status
```

---

## The Problem This Solves

**Across sessions:**
- "What did we decide yesterday?" → Forgotten
- "What gotchas did we hit?" → Re-discovered every time

**Within sessions:**
- "Didn't we already try that?" → Suggests same failed fix 3 times
- "What are we building again?" → Drifts into rabbit holes

**Mind fixes both.** Two layers of memory, zero friction.

---

## File Structure

```
your-project/
├── .mind/
│   ├── MEMORY.md     ← Long-term memory (persists)
│   ├── SESSION.md    ← Short-term focus (cleared each session)
│   ├── REMINDERS.md  ← Time and context-based reminders
│   └── state.json    ← Timestamps for session detection
└── CLAUDE.md         ← Mind injects context here
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Command not found" | Use full path: `uv --directory /path/to/vibeship-mind run mind ...` |
| Nothing being captured | Use keywords: `decided`, `problem`, `learned`, `gotcha` |
| Claude repeating mistakes | Tell Claude: "Check SESSION.md" or "Add to Rejected Approaches" |
| Need to check health | `uv --directory /path/to/vibeship-mind run mind doctor` |

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - How it works internally
- [v2 Migration](docs/mind-v2-architecture-migration.md) - Daemon-free architecture
- [Session Memory](docs/mind-v2-session-memory.md) - Within-session focus

---

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

Built by [@meta_alchemist](https://x.com/meta_alchemist)

A [vibeship.co](https://vibeship.co) ecosystem project
