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

## Completed - Phase 2: Intelligence

- [x] Proactive edge detection during coding
  - Detection at decision points (context queries, decisions, issues)
  - Intent detection via keyword matching
  - Code detection via regex patterns
  - Session-based throttling (same edge won't warn twice per session)
  - Inline warnings in MCP tool responses
- [x] Context relevance scoring (semantic + recency + usage)
  - Semantic similarity from ChromaDB
  - Recency boost with 7-day exponential decay
  - Frequency boost from access tracking (logarithmic scaling)
  - Trigger phrase matching boost
  - Access recording on context retrieval
- [x] Session narrative capture (auto Episode creation)
  - Hybrid significance detection (artifacts, substance, struggle, user-declared)
  - Auto-generated titles from primary artifacts + mood
  - Human-readable summaries (not log entries)
  - User's words preserved as the "soul" of the episode
  - Optional custom episode title override
  - Resolved issues tracking in sessions
- [x] Memory decay for stale entries
  - Staleness based on time since last ACCESS (not creation)
  - Entity type-specific half-lives (Decision: 60d, Issue: 30d, Sharp Edge: 120d, Episode: 90d)
  - Status multipliers (superseded: 5x faster, resolved: 2x faster)
  - Entities below 10% relevance filtered from results
  - Access recorded for primer, search, and edge warnings

## Completed - Phase 3: HTTP API

- [x] FastAPI server with uvicorn (`uv run mind serve`)
- [x] Core endpoints:
  - `/status` - Health check with stats
  - `/projects` - Full CRUD with cascade delete
  - `/decisions/{project_id}` - CRUD operations
  - `/issues/{project_id}` - CRUD with open filter
  - `/edges` - CRUD with global_only filter
  - `/episodes/{project_id}` - Read-only list/get
  - `/sessions/{project_id}` - List with /active shortcut
  - `/user` - Get/update user model
  - `/search` - Cross-entity text search
  - `/export` - JSON export with project filter
- [x] Consistent response shapes (`{items, count, has_more}`)
- [x] Error handling (NOT_FOUND, VALIDATION_ERROR)
- [x] CORS enabled for local development
- [x] 148 tests passing (42 API tests)

## Current Status

**Mind is connected to Claude Code.** 148 tests passing. Restart Claude Code to activate.

After restart, Mind tools will be available:
- `mind_start_session` - Begin session, get context primer + edge warnings
- `mind_end_session` - Save session summary
- `mind_get_context` - Search with relevance scoring + decay + edge warnings
- `mind_check_edges` - Check code for gotchas
- `mind_add_decision` - Record decision with reasoning + edge warnings
- `mind_add_issue` - Track a problem + edge warnings
- `mind_update_issue` - Add solution attempts
- `mind_add_edge` - Register sharp edge
- `mind_update_project` - Update project state
- `mind_export` - Export all data

## Completed - Phase 2: Intelligence (Remaining)

- [x] Primer generation with smart prioritization
  - Entity-specific scoring (severity for issues, revisit_if for decisions, stack match for edges)
  - Continuity boost for items mentioned in last session's next_steps
  - Goal alignment boost for items related to current_goal
  - Access frequency boost from entity_access table
  - Subtle hints for non-obvious prioritization ("from last session", "goal-related")

## Future Phases

### Phase 4: Dashboard UI
- [ ] Simple web dashboard for viewing Mind data
- [ ] Project overview with stats
- [ ] Decision/Issue/Edge browsers
- [ ] Session history viewer

### Phase 5: Cloud Sync (Optional)
- [ ] Cloudflare D1 for SQLite sync
- [ ] Cloudflare Vectorize for embeddings
- [ ] End-to-end encryption
- [ ] Multi-device support

## Known Issues

None currently. All 148 tests passing.

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
