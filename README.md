# Mind

> Memory for vibe coding.

When you're vibe coding with Claude, it forgets everything between sessions. What you decided, what broke, what worked - gone. You end up re-explaining the same things over and over.

Mind fixes this. It gives Claude persistent memory so your next session picks up where you left off.

---

## Why Mind?

- **Automatic** - memories save as you work, no extra steps
- **Simple** - 5 commands to install, then forget about it
- **Zero friction** - Claude writes to a file, Mind watches it
- **Readable** - memories stored in plain `.md` files you can open anytime
- **Open source** - see exactly how it works, modify if you want

---

## Install

**Requires:** [uv](https://docs.astral.sh/uv/) (Claude Code installs uv automatically)

```bash
git clone https://github.com/vibeforge1111/vibeship-mind.git
cd vibeship-mind
uv sync
uv run mind init
uv run mind daemon start
```

That's it. Mind is now running.

---

## Initialize Mind in Any Project

After installing once, run this in any project folder:

```bash
mind init
```

---

## Connect to Claude Code (Optional)

Mind works without this, but connecting via MCP gives Claude extra powers:

| Tool | What it does |
|------|--------------|
| `mind_search` | Search past memories ("what did we decide about auth?") |
| `mind_edges` | Check for gotchas before writing risky code |
| `mind_status` | See what's being tracked |

**Easy way:** Just tell Claude:

> "Install the Mind MCP server from ~/vibeship-mind"

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
      "args": ["--directory", "/Users/you/vibeship-mind", "run", "mind", "mcp"]
    }
  }
}
```

3. Restart Claude Code (Cmd/Ctrl+Shift+P → "Reload Window" or just close and reopen)

---

## How It Works

As you vibe code, Claude writes memories to `.mind/MEMORY.md` - decisions, problems, learnings, fixes.

Next session, Claude reads the file and knows:
- What you decided and why
- What problems came up
- What you learned
- Where you left off

Just keep vibe coding. Mind handles the rest.

---

## Quick Commands

```bash
# Check if everything is working
uv --directory /path/to/vibeship-mind run mind doctor

# See what Mind extracted from your notes
uv --directory /path/to/vibeship-mind run mind parse

# Check daemon status
uv --directory /path/to/vibeship-mind run mind daemon status
```

---

## The Problem This Solves

Every AI conversation starts from zero:
- "What did we decide yesterday?" → Forgotten
- "What did we try that didn't work?" → Unknown
- "What gotchas did we hit?" → Re-discovered every time
- "Where did we leave off?" → Lost

**Mind fixes this.** Your AI remembers everything across sessions.

---

## File Structure

After setup, your project has:

```
your-project/
├── .mind/
│   └── MEMORY.md     ← You write here
└── CLAUDE.md         ← Mind updates this automatically
```

Global config lives at:
```
~/.mind/
├── projects.json     ← Registered projects
└── global_edges.json ← Cross-project gotchas
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Command not found" | Use full path: `uv --directory /path/to/vibeship-mind run mind ...` |
| Daemon not running | `uv --directory /path/to/vibeship-mind run mind daemon start` |
| Nothing being captured | Make sure you use keywords like `decided`, `problem`, `learned` |
| Need to check health | `uv --directory /path/to/vibeship-mind run mind doctor` |

---

## Documentation

For deeper details:
- [Architecture](docs/ARCHITECTURE.md) - How it works internally
- [Parser](docs/PARSER.md) - What patterns Mind recognizes
- [CLI Reference](docs/CLI.md) - All commands
- [MCP Tools](docs/MCP_TOOLS.md) - AI tool specifications

---

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

*Memory should be automatic, not another task.*
