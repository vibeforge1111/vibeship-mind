# Mind

> Context and continuity for AI-assisted development

Mind gives AI coding assistants memory that persists across sessions. Not just facts—decisions with reasoning, issues with attempted solutions, sharp edges that prevent repeated mistakes, and the narrative arc of building together.

**Open source. MIT license. Local-first.**

## The Problem

Every AI conversation starts from zero. Claude doesn't know:
- What we decided yesterday and why
- What we already tried that didn't work  
- The gotchas we've hit before
- Where we left off

You end up re-explaining context, re-hitting the same errors, re-making the same decisions.

## The Solution

Mind maintains six types of context:

| Store | What It Holds | Why It Matters |
|-------|---------------|----------------|
| **Project State** | Current goals, blockers, open threads | Know where we are |
| **Decision Log** | Choices with full reasoning and alternatives | Know why we chose |
| **Issue Tracker** | Problems with attempted solutions | Don't repeat failures |
| **Sharp Edge Registry** | Gotchas with detection patterns | Catch mistakes before making them |
| **Episode Memory** | Narrative of significant sessions | Remember the journey |
| **User Model** | Your patterns and preferences | Adapt to how you work |

## Quick Start

### Prerequisites

Install [uv](https://docs.astral.sh/uv/):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install

```bash
git clone https://github.com/vibeship/mind.git
cd mind
uv sync
```

### Run

```bash
uv run mind serve
```

Mind is now running at `http://localhost:8765`.

### Connect to Claude Code

Add to your Claude Code MCP config:

```json
{
  "mcpServers": {
    "mind": {
      "command": "uv",
      "args": ["--directory", "/path/to/mind", "run", "mind", "mcp"],
      "env": {}
    }
  }
}
```

Restart Claude Code. Mind is now active.

## How It Works

### Session Start
```
Claude: "Last session: Yesterday 11pm
Working on: Payment webhook timeout
Blocked by: Vercel Edge 10s limit
Decision pending: Move to serverless function

Ready to continue?"
```

### During Session
```
You: "Let's add crypto for tokens"

Claude: "Since this is Edge middleware, I'll use Web Crypto API. 
We hit an issue with Node crypto in Edge functions before—
it's not supported in V8 isolates."
```

### Session End
```
Claude: "Captured. Progress: moved webhook to serverless, 
timeout resolved. Next: add retry logic.

See you next time."
```

## Storage

**Local (default):** SQLite + ChromaDB in `~/.mind/`

**Cloud (optional):** Encrypted sync via Cloudflare D1 + Vectorize

Your data stays local unless you choose to sync. Export anytime.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - Technical deep dive
- [Data Models](docs/DATA_MODELS.md) - Entity definitions
- [MCP Tools](docs/MCP_TOOLS.md) - Tool specifications  
- [Roadmap](docs/ROADMAP.md) - Implementation phases
- [Philosophy](docs/PHILOSOPHY.md) - The deeper why
- [Sharp Edges](docs/SHARP_EDGES.md) - Gotchas when building Mind
- [Contributing](CONTRIBUTING.md) - How to help

## Part of VibeShip

Mind is one component of the VibeShip ecosystem:

- **Scanner** - Find what's wrong in your code
- **Mind** - Remember everything across sessions
- **Spawner** - AI skills and validation for shipping
- **Marketplace** - Connect with experts when stuck

## License

MIT - do whatever you want.

---

*Built for vibe coders who ship.*
