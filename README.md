# Mind

> Memory that accumulates automatically.

Mind gives AI coding assistants persistent memory across sessions. Your AI remembers what you decided, what broke, and where you left off.

---

## Install

**Requires:** [uv](https://docs.astral.sh/uv/) (Python package manager)

```bash
git clone https://github.com/vibeforge1111/vibeship-mind.git
cd vibeship-mind
uv sync
uv run mind init
uv run mind daemon start
```

That's it. Mind is now running.

---

## Use in Any Project

```bash
cd ~/your-other-project
uv --directory ~/vibeship-mind run mind init
```

---

## Connect to Claude Code (Optional)

Add to MCP config (`~/.config/claude/mcp.json` or `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mind": {
      "command": "uv",
      "args": ["--directory", "/full/path/to/vibeship-mind", "run", "mind", "mcp"]
    }
  }
}
```

---

## How It Actually Works

### You write notes as you work

In `.mind/MEMORY.md` (created by `mind init`):

```markdown
## Dec 13

Working on auth today.

decided to use JWT instead of sessions - simpler, stateless
problem: cookies not working in Safari
learned that Safari blocks third-party cookies after 7 days
fixed it by using same-domain auth

Next: add refresh tokens
```

**That's it.** Just write naturally. Use words like:
- `decided`, `chose`, `going with` → captures decisions
- `problem`, `issue`, `bug` → captures issues
- `learned`, `realized`, `discovered` → captures learnings
- `fixed`, `resolved` → marks things as solved

### Mind reads it and remembers

Next time you open Claude, it automatically knows:
- What you decided and why
- What problems you hit
- What you learned
- Where you left off

No commands. No tool calls. It just works.

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
