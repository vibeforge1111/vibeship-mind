# Mind

<!-- doc-version: 2.1.0 | last-updated: 2025-12-13 -->

> Mind gives Claude a mind - not just memory across sessions, but focus within them. It remembers what worked, what didn't, and what it's supposed to be building.

When you're vibe coding with Claude, it forgets everything between sessions. What you decided, what broke, what worked - gone. Even worse, in long sessions it starts suggesting the same failed fixes over and over.

Mind fixes both problems with two-layer memory:
- **MEMORY.md** - Long-term memory across sessions
- **SESSION.md** - Short-term focus within a session

---

## Why Mind?

**2 commands.** Install, init. Done.

**Fully automated.** Memory just works - no commands required:
- Claude writes memories as it works
- Session gaps auto-detected (30 min)
- Learnings auto-promoted to long-term memory
- Context auto-injected into CLAUDE.md
- Reminders auto-surface when due or when keywords match

Optional tools are there when you want them, but the core memory flow runs hands-free.

**Two-layer memory:**
- Cross-session recall (MEMORY.md)
- Within-session focus (SESSION.md)

**Zero friction.** Claude writes to files, MCP reads them lazily. No database, no cloud, no sync issues.

**Human-readable.** Plain `.md` files you can open, edit, or git-track anytime.

**Open source.** See exactly how it works. No black box.

---

## Ready to Give Claude a Mind?

**2 commands. Zero friction.**

### 1. Install Mind

```bash
pip install vibeship-mind
```

### 2. Initialize in your project

```bash
cd your-project
mind init
```

### 3. Connect to Claude Code

Add to your MCP config:

**Mac/Linux:** `~/.config/claude/mcp.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

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

Restart Claude Code, then say: **"Let's run The Mind"**

---

<details>
<summary><strong>Alternative: Install from source</strong></summary>

```bash
git clone https://github.com/vibeforge1111/vibeship-mind.git
cd vibeship-mind
uv sync
uv run mind init
```

MCP config for source install:
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

</details>

---

## MCP Tools (12 total)

**Core:**
| Tool | What it does |
|------|--------------|
| `mind_recall()` | Load session context - CALL FIRST every session |
| `mind_log(msg, type)` | Log to session or memory (routes by type) |

**Type routing for `mind_log()`:**
- SESSION.md: `experience`, `blocker`, `assumption`, `rejected`
- MEMORY.md: `decision`, `learning`, `problem`, `progress`
- SELF_IMPROVE.md: `feedback`, `preference`, `blind_spot`, `skill`
- Special: `reinforce` (boosts pattern confidence)

**Reading:**
| Tool | What it does |
|------|--------------|
| `mind_session()` | Check current session state |
| `mind_search(query)` | Search past memories |
| `mind_status()` | Check memory health |
| `mind_reminders()` | List pending reminders |

**Actions:**
| Tool | What it does |
|------|--------------|
| `mind_blocker(desc)` | Log blocker + auto-search memory for solutions |
| `mind_remind(msg, when)` | Set reminder - time or context-based |
| `mind_reminder_done(index)` | Mark a reminder as done |
| `mind_edges(intent)` | Check for gotchas before risky code |
| `mind_checkpoint()` | Force process pending memories |
| `mind_add_global_edge()` | Add cross-project gotcha |

---

## How It Works

**Long-term (MEMORY.md):** Permanent knowledge - decisions, learnings, problems, progress. `mind_recall()` loads this as context each session.

**Short-term (SESSION.md):** Working memory buffer:
- **Experience** - Raw moments, thoughts, what's happening
- **Blockers** - Things stopping progress
- **Rejected** - What didn't work and why
- **Assumptions** - What you're assuming true

When a new session starts (30 min gap), valuable items get promoted from SESSION.md to MEMORY.md automatically.

See [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) for the full architecture.

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

```bash
cd your-project
mind init
```

That's it! This creates `.mind/MEMORY.md` and `.mind/SESSION.md`.

---

## Quick Commands

```bash
# Check if everything is working
mind doctor

# See what Mind extracted from your notes
mind parse

# Check project status
mind status

# List all registered projects
mind list
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
│   ├── config.json   ← Feature flags for experiments
│   └── state.json    ← Timestamps for session detection
└── CLAUDE.md         ← Mind injects context here
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Command not found" | Make sure `pip install vibeship-mind` completed and `mind` is in your PATH |
| Nothing being captured | Use keywords: `decided`, `problem`, `learned`, `gotcha` |
| Claude repeating mistakes | Tell Claude: "Check SESSION.md" or "Add to Rejected Approaches" |
| Need to check health | Run `mind doctor` |

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - Technical deep-dive, design principles
- [How It Works](docs/HOW_IT_WORKS.md) - Visual diagrams explaining the system
- [MCP Tools](docs/MCP_TOOLS.md) - Full tool reference with parameters

---

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

Built by [@meta_alchemist](https://x.com/meta_alchemist)

A [vibeship.co](https://vibeship.co) ecosystem project
