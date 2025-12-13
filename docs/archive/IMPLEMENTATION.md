# Mind Implementation (v2)

## Overview

Mind v2 is a stateless, MCP-only architecture. No daemon, no file watchers, no background processes.

---

## Architecture

```
src/mind/
+-- cli.py               # CLI commands (init, list, status, etc.)
+-- parser.py            # Loose markdown parser
+-- context.py           # MIND:CONTEXT generation
+-- detection.py         # Stack detection
+-- storage.py           # Projects registry
+-- templates.py         # File templates
+-- mcp/
|   +-- server.py        # 8 MCP tools
+-- __init__.py          # Package version
```

### Core Components

| Component | Purpose |
|-----------|---------|
| Source of truth | .mind/MEMORY.md |
| Session tracking | .mind/SESSION.md |
| MCP tools | 8 (recall, session, blocker, search, edges, checkpoint, add_global_edge, status) |
| Session detection | Lazy via `mind_recall()` |
| Context delivery | CLAUDE.md injection |
| Parsing | Loose regex, confidence scoring |

---

## Key Files

### parser.py

Extracts entities from natural language:

```python
class Parser:
    def parse(self, content: str, source_file: str) -> ParseResult:
        """Parse MEMORY.md content."""
        # Returns: project_state, entities, project_edges

class InlineScanner:
    def scan_directory(self, path: Path) -> list[Entity]:
        """Scan code files for // MEMORY: comments."""
```

**Entity Types:**
- `decision` - Choices made (decided, chose, going with)
- `issue` - Problems (problem, bug, stuck, blocked)
- `learning` - Discoveries (learned, TIL, gotcha, realized)

**Confidence Scoring:**
- Explicit format (`**Decided:**`) = 0.9
- Clear keywords = 0.7
- Has reasoning (`because`) = +0.1
- Vague = 0.4

### context.py

Generates MIND:CONTEXT for CLAUDE.md:

```python
def generate_context(project_path: Path, result: ParseResult) -> str:
    """Generate MIND:CONTEXT markdown section."""

def update_claude_md(project_path: Path, stack: list[str]):
    """Inject MIND:CONTEXT into CLAUDE.md."""
```

### mcp/server.py

8 stateless MCP tools:

```python
@tool
async def mind_recall(project_path: str = None, force_refresh: bool = False):
    """Load session context - CALL FIRST every session."""

@tool
async def mind_session(project_path: str = None):
    """Get current session state from SESSION.md."""

@tool
async def mind_blocker(description: str, keywords: list[str] = None):
    """Log blocker and auto-search memory for solutions."""

@tool
async def mind_search(query: str, scope: str = "project", ...):
    """Search across memories."""

@tool
async def mind_edges(intent: str, code: str = None, stack: list[str] = None):
    """Check for gotchas before coding."""

@tool
async def mind_checkpoint(project_path: str = None):
    """Force process pending memories."""

@tool
async def mind_add_global_edge(title: str, description: str, ...):
    """Add cross-project gotcha."""

@tool
async def mind_status():
    """Check Mind health and stats."""
```

### storage.py

Project registry management:

```python
class ProjectsRegistry:
    def register(self, path: Path, stack: list[str]):
        """Register a project."""

    def list_all(self) -> list[ProjectInfo]:
        """List all registered projects."""
```

### templates.py

File templates for init:

```python
MEMORY_TEMPLATE = """..."""   # .mind/MEMORY.md
SESSION_TEMPLATE = """..."""  # .mind/SESSION.md
CONTEXT_TEMPLATE = """..."""  # CLAUDE.md injection
GITIGNORE_CONTENT = """...""" # .mind/.gitignore
```

---

## Session Detection (Lazy)

v2 uses lazy session detection instead of a daemon:

```python
async def mind_recall(project_path, force_refresh=False):
    # 1. Load state.json (last_activity, memory_hash)
    state = load_state(project_path)

    # 2. Check for session gap (>30 min)
    gap = now - state.last_activity
    if gap > 30_MINUTES:
        # Promote SESSION.md discoveries to MEMORY.md
        promote_session_learnings(project_path)
        # Clear SESSION.md for new session
        reset_session(project_path)

    # 3. Check if MEMORY.md changed
    current_hash = hash_file(memory_path)
    if current_hash != state.memory_hash:
        # Reparse MEMORY.md
        entities = parse_memory(project_path)
        # Regenerate context
        context = generate_context(project_path, entities)

    # 4. Update state
    state.last_activity = now
    state.memory_hash = current_hash
    save_state(state)

    # 5. Return fresh context
    return RecallResult(context, session_state, health)
```

---

## State File

`.mind/state.json` (gitignored):

```json
{
  "last_activity": 1702400000000,
  "memory_hash": "a1b2c3d4e5f6",
  "schema_version": 2
}
```

Used for:
- Session gap detection (30 min threshold)
- Change detection (skip reparse if unchanged)

---

## Testing

```bash
# Run all tests
uv run pytest tests/

# Run specific test file
uv run pytest tests/test_parser.py

# Run with coverage
uv run pytest --cov=src/mind tests/
```

### Test Structure

```
tests/
+-- test_parser.py       # Parser and entity extraction
+-- test_context.py      # Context generation
+-- test_cli.py          # CLI commands
+-- test_mcp.py          # MCP tools
+-- conftest.py          # Fixtures
```

---

## Running

```bash
# CLI
uv run mind <command>

# MCP Server (for Claude Code)
uv run mind mcp

# Development
uv run mind init .
uv run mind status
uv run mind parse --json
```

---

## MCP Configuration

### Claude Code

Add to `~/.config/claude/mcp.json`:

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

### Windows

```json
{
  "mcpServers": {
    "mind": {
      "command": "uv",
      "args": ["--directory", "C:\\path\\to\\vibeship-mind", "run", "mind", "mcp"]
    }
  }
}
```

---

## v1 to v2 Migration

### Removed

- `daemon.py` - Background daemon
- `watcher.py` - File system watcher
- `mind daemon start/stop/status/logs` - CLI commands
- PID file management
- Signal handlers
- Platform auto-start configs (launchd, systemd)

### Added

- `mind_recall()` - Lazy session detection
- `mind_session()` - Session state access
- `mind_blocker()` - Blocker logging with auto-search
- `SESSION.md` - Goal-oriented session tracking
- Promotion logic (SESSION.md -> MEMORY.md)

### Changed

- Session detection: Proactive (daemon) -> Lazy (mind_recall)
- MCP tools: 4 -> 8
- State file: Simplified schema
