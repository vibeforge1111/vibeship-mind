# CLAUDE.md

Context for Claude Code when working on Mind.

## What is Mind?

Mind is a context engine for AI-assisted development. It maintains memory across sessions:
- **Decisions** with full reasoning and alternatives
- **Issues** with attempted solutions
- **Sharp Edges** with detection patterns
- **Episodes** as narrative of significant sessions
- **User Model** of working patterns

## Project Structure

```
mind/
├── src/
│   ├── models/        # Pydantic data models
│   ├── storage/       # SQLite + ChromaDB storage
│   ├── engine/        # Context retrieval, detection, decay
│   ├── mcp/           # MCP server and tools
│   ├── api/           # HTTP API (optional)
│   └── cli/           # Command line interface
├── docs/              # Documentation
├── tests/             # Test suite
└── data/              # Local data (gitignored)
```

## Tech Stack

- **Python 3.11+** with type hints
- **uv** for package management
- **Pydantic V2** for data models
- **SQLite** for structured data
- **ChromaDB** for vector embeddings
- **sentence-transformers** for embeddings (all-MiniLM-L6-v2)
- **MCP** for Claude Code integration
- **FastAPI** for optional HTTP API

## Key Files

- `docs/DATA_MODELS.md` - All entity definitions
- `docs/MCP_TOOLS.md` - Tool specifications
- `docs/ARCHITECTURE.md` - System design
- `docs/SHARP_EDGES.md` - Known gotchas

## Development Commands

```bash
# Install dependencies
uv sync

# Run Mind server (MCP mode)
uv run mind mcp

# Run Mind server (HTTP mode)
uv run mind serve

# Run tests
uv run pytest

# Format code
uv run black src/
uv run ruff check src/ --fix

# Type check
uv run mypy src/
```

## Data Location

Default: `~/.mind/`
- `mind.db` - SQLite database
- `chroma/` - ChromaDB vectors
- `exports/` - User exports

Override with `MIND_DATA_DIR` environment variable.

## Implementation Priorities

1. **Working MCP tools first** - Everything else is secondary
2. **Fast hot paths** - Primer <500ms, queries <200ms
3. **Correct storage** - Data integrity over features
4. **Good error messages** - Users will hit issues

## Coding Standards

### Data Models
- Use Pydantic V2 (`model_dump()` not `dict()`)
- All fields typed with Optional where nullable
- Default factories for dynamic defaults
- Validation in models, not in storage

### Storage
- Use aiosqlite for async operations
- JSON serialize lists/dicts explicitly
- Track changes for sync
- Handle NULL vs empty list

### MCP Tools
- Keep tools focused (one job each)
- Return structured data, not strings
- Handle missing entities gracefully
- Log for debugging, don't spam

### Error Handling
- Custom exception classes
- User-friendly error messages
- Never crash on bad data
- Recover when possible

## Common Patterns

### Creating Entities
```python
decision = Decision(
    project_id=project.id,
    title="Use Supabase",
    description="Full explanation...",
    reasoning="Because...",
    alternatives=[Alternative(option="X", rejected_because="Y")],
    trigger_phrases=["why supabase", "database choice"]
)
await storage.save_decision(decision)
```

### Querying
```python
results = await context_engine.search(
    query="authentication decision",
    project_id=current_project.id,
    types=[EntityType.DECISION, EntityType.EDGE]
)
```

### Session Lifecycle
```python
# Start
session = await session_manager.start(project_id="proj_xxx")
primer = await primer_generator.generate(session)

# During - tools called as needed

# End
await session_manager.end(
    session_id=session.id,
    summary="What happened",
    progress=["Thing 1", "Thing 2"],
    next_steps=["Thing 3"]
)
```

## Known Issues

See `docs/SHARP_EDGES.md` for full list.

Key ones:
- ChromaDB cold start is slow (pre-download model)
- SQLite needs WAL mode for concurrency
- MCP tools must be <2s or conversation breaks

## Testing

```bash
# All tests
uv run pytest

# Specific module
uv run pytest tests/test_storage.py

# With coverage
uv run pytest --cov=src

# Verbose
uv run pytest -v
```

## Current Focus

Check `docs/ROADMAP.md` for current phase.

## Questions?

- Architecture: `docs/ARCHITECTURE.md`
- Data models: `docs/DATA_MODELS.md`  
- MCP tools: `docs/MCP_TOOLS.md`
- Philosophy: `docs/PHILOSOPHY.md`
