# Mind Development Tasks

## Completed - Phase 1: Foundation

- [x] Project structure setup (pyproject.toml, src/mind/)
- [x] Pydantic data models (Project, Decision, Issue, SharpEdge, Episode, User, Session)
- [x] SQLite storage layer with full CRUD
- [x] ChromaDB embedding storage for semantic search
- [x] MCP server with 10 tools
- [x] CLI commands (mcp, projects, decisions, issues, edges, export, status)
- [x] Test suite (36 tests passing)
- [x] GitHub repo: https://github.com/vibeforge1111/vibeship-mind
- [x] Added Mind to Claude Code MCP config

## Current Status

**Mind is ready for testing.** Restart Claude Code to activate.

After restart, Mind tools will be available:
- `mind_start_session` - Begin session, get context primer
- `mind_end_session` - Save session summary
- `mind_get_context` - Search decisions/issues/edges
- `mind_check_edges` - Check code for gotchas
- `mind_add_decision` - Record decision with reasoning
- `mind_add_issue` - Track a problem
- `mind_update_issue` - Add solution attempts
- `mind_add_edge` - Register sharp edge
- `mind_update_project` - Update project state
- `mind_export` - Export all data

## Next Up - Phase 2: Intelligence

- [ ] Context relevance scoring (TF-IDF + recency + usage)
- [ ] Primer generation with smart truncation
- [ ] Proactive edge detection during coding
- [ ] Session narrative capture
- [ ] Memory decay for stale entries

## Future Phases

### Phase 3: Polish
- [ ] HTTP API for web dashboard
- [ ] Export/import in multiple formats
- [ ] Backup and restore
- [ ] Settings management

### Phase 4: Cloud Sync (Optional)
- [ ] Cloudflare D1 for SQLite sync
- [ ] Cloudflare Vectorize for embeddings
- [ ] End-to-end encryption
- [ ] Multi-device support

## Known Issues

None currently. All 36 tests passing.

## Tech Stack

- Python 3.11+ with uv
- Pydantic V2 for models
- SQLite (WAL mode) for storage
- ChromaDB for vectors
- sentence-transformers (all-MiniLM-L6-v2)
- MCP for Claude Code integration

## Data Location

Default: `~/.mind/`
- `mind.db` - SQLite database
- `chroma/` - Vector embeddings
- `exports/` - User exports

## Commands

```bash
# Run MCP server (used by Claude Code)
uv run mind mcp

# Run HTTP server
uv run mind serve

# Check status
uv run mind status

# Run tests
uv run pytest

# List projects
uv run mind projects
```
