# Mind Onboarding

## One-Line Install

```bash
curl -sSL https://mind.vibeship.dev/install | sh
```

This does everything:
1. Installs Mind via pip
2. Initializes current project
3. Starts daemon
4. Adds to Claude Code MCP config
5. Shows first-run guide

---

## Manual Install (3 Commands)

```bash
pip install mind-memory
mind init
mind daemon start
```

Done. Start working.

---

## First-Run Output

After `mind init`, user sees:

```
✓ Mind initialized for my-project!

📁 Created:
   .mind/MEMORY.md     ← Write here as you work
   CLAUDE.md           ← Context auto-injected here

🔍 Detected stack: sveltekit, typescript, tailwind

📝 How to capture memory:
   • Write naturally in .mind/MEMORY.md
   • Use keywords: decided, problem, learned, fixed
   • Or quick syntax: MEMORY: decided X because Y
   • Or inline comments: // MEMORY: decided X

🤖 Mind will automatically:
   • Watch your files for changes
   • Extract decisions, issues, learnings
   • Update CLAUDE.md with fresh context
   • Build searchable memory

▶️  Start daemon:
   mind daemon start

📊 Check status anytime:
   mind daemon status

Ready to build!
```

---

## Memory Status Indicator

MIND:CONTEXT shows proof it's working:

```markdown
<!-- MIND:CONTEXT -->
## Memory: ✓ Active
Last captured: 5 min ago
This session: 2 decisions, 1 issue, 1 learning

## Session Context
...
```

If stale:

```markdown
## Memory: ⚠️ Stale (2 days)
Run `mind daemon start` to resume capture
```

---

## Pre-Populated Example

MEMORY.md starts with one example entry so users see the format:

```markdown
<!-- MIND MEMORY - Append as you work. Write naturally. -->

# my-project

## Project State
- Goal: (describe your goal)
- Stack: sveltekit, typescript, tailwind
- Blocked: None

## Gotchas
<!-- Add project-specific gotchas here -->

---

## Session Log

## 2024-12-12

**Decided:** Initialize Mind for this project
- Gives Claude persistent memory across sessions
- Context appears automatically in CLAUDE.md

Next: Start building!

---

<!-- 
Your turn! Add entries as you work:

**Decided:** Use X because Y
**Problem:** Something isn't working
**Learned:** Discovered that X does Y
**Fixed:** Resolved the issue by doing Z

Or quick syntax:
MEMORY: decided JWT because simpler
MEMORY: problem - Safari cookies broken
MEMORY: learned - ITP blocks cross-domain
-->
```

---

## Install Script

```bash
#!/bin/bash
# install.sh - One-line Mind installer

set -e

echo "🧠 Installing Mind..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 required. Install from python.org"
    exit 1
fi

# Install Mind
pip install mind-memory --quiet

# Initialize if in a project directory
if [ -f "package.json" ] || [ -f "pyproject.toml" ] || [ -f "Cargo.toml" ] || [ -f "go.mod" ]; then
    echo "📁 Detected project directory, initializing..."
    mind init
fi

# Start daemon
echo "🚀 Starting daemon..."
mind daemon start

# Add to Claude Code MCP config
CLAUDE_CONFIG="$HOME/.config/claude/mcp.json"
if [ -f "$CLAUDE_CONFIG" ]; then
    echo "⚙️  Adding to Claude Code config..."
    # Use jq if available, otherwise manual instructions
    if command -v jq &> /dev/null; then
        jq '.mcpServers.mind = {"command": "mind", "args": ["mcp"]}' "$CLAUDE_CONFIG" > tmp.json && mv tmp.json "$CLAUDE_CONFIG"
        echo "✓ Added to MCP config"
    else
        echo "📝 Add to $CLAUDE_CONFIG manually:"
        echo '   "mind": {"command": "mind", "args": ["mcp"]}'
    fi
else
    echo "📝 Add to Claude Code MCP config:"
    echo '   "mind": {"command": "mind", "args": ["mcp"]}'
fi

echo ""
echo "✅ Mind installed!"
echo ""
echo "Commands:"
echo "  mind init          - Initialize in a project"
echo "  mind daemon status - Check if running"
echo "  mind search        - Search memories"
echo ""
echo "Start working - memory accumulates automatically."
```

---

## Claude Code MCP Config

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

Or if using uv:

```json
{
  "mcpServers": {
    "mind": {
      "command": "uv",
      "args": ["--directory", "/path/to/mind", "run", "mind", "mcp"]
    }
  }
}
```

---

## Troubleshooting First Run

### "Daemon not running"

```bash
mind daemon start
mind daemon status  # Verify
```

### "MIND:CONTEXT not appearing"

```bash
mind index          # Force reindex
mind context        # Check what would be generated
```

### "Nothing being captured"

Check MEMORY.md has content with keywords:
- decided, chose, going with
- problem, issue, bug, stuck
- learned, discovered, realized

### "Search returns nothing"

```bash
mind daemon status  # Is daemon running?
mind index          # Rebuild index
```

---

## Adoption Timeline

| Time | What Happens |
|------|--------------|
| Day 1 | Install, init, start daemon |
| Day 2 | Notice MIND:CONTEXT appearing |
| Week 1 | Start writing more explicitly |
| Week 2 | Use search occasionally |
| Month 1 | Muscle memory, automatic |

---

## Success Indicators

**It's working if:**
- CLAUDE.md has fresh MIND:CONTEXT
- `mind daemon status` shows "Running"
- `mind search "anything"` returns results
- Claude references past decisions without being told

**Something's wrong if:**
- MIND:CONTEXT is stale (check daemon)
- Claude keeps asking same questions (check MEMORY.md has content)
- Search returns nothing (run `mind index`)
