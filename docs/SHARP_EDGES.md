# Sharp Edges

Known gotchas when building and using Mind. We eat our own dog food.

## Technical Edges

### ChromaDB Cold Start

```yaml
edge: "ChromaDB downloads embedding model on first use"
symptoms:
  - First query takes 30+ seconds
  - User thinks it's frozen
  - No progress indicator

workaround: |
  Pre-download model during install:
  
  ```python
  # In setup or first-run
  from sentence_transformers import SentenceTransformer
  model = SentenceTransformer('all-MiniLM-L6-v2')
  # This triggers the ~90MB download
  ```

detection:
  - First run without cached model
  - Fresh install

root_cause: |
  sentence-transformers downloads models lazily on first use.
  The all-MiniLM-L6-v2 model is ~90MB.
```

### SQLite File Locking

```yaml
edge: "SQLite doesn't handle concurrent writes well"
symptoms:
  - "database is locked" errors
  - Corruption if multiple processes write
  - Timeout errors

workaround: |
  1. Use WAL mode:
  ```sql
  PRAGMA journal_mode=WAL;
  ```
  
  2. Serialize all writes through single connection
  
  3. Use connection pool with max 1 writer

detection:
  - Multiple MCP tool calls in parallel
  - Multiple Claude Code sessions on same project
  - Background sync while user is working

root_cause: |
  SQLite is designed for single-writer scenarios.
  Multiple concurrent writers cause lock contention.
```

### MCP Tool Latency

```yaml
edge: "MCP tools that take >2s break conversational flow"
symptoms:
  - Awkward pauses
  - User thinks Claude is stuck
  - Conversation feels unnatural

workaround: |
  1. Keep hot paths fast (<500ms):
     - Session primer generation
     - Context queries
     - Edge checks
  
  2. Defer expensive ops to session end:
     - Episode extraction
     - User model updates
     - Decay processing
  
  3. Cache aggressively:
     - Recent queries
     - Active project state
     - User model

detection:
  - Any tool doing semantic search + LLM call
  - Complex query across many entities
  - First query after long pause

root_cause: |
  MCP is synchronous. Long-running tools block 
  the entire conversation.
```

### Embedding Model Consistency

```yaml
edge: "Changing embedding model invalidates all vectors"
symptoms:
  - Search returns garbage after model change
  - Similarity scores meaningless
  - Old memories invisible to search

workaround: |
  1. Pin embedding model version in config
  2. If must change: re-embed everything
  3. Store model version in metadata
  4. Detect model change on startup, warn user

detection:
  - Upgrading sentence-transformers
  - Switching embedding provider
  - Model file corruption

root_cause: |
  Different embedding models produce incompatible 
  vector spaces. Can't mix embeddings from different models.
```

### JSON in SQLite

```yaml
edge: "SQLite JSON fields don't auto-serialize Pydantic models"
symptoms:
  - Type errors on save
  - Empty lists become NULL
  - Nested objects lost

workaround: |
  Always explicitly serialize/deserialize:
  
  ```python
  # Save
  row['alternatives'] = json.dumps([a.dict() for a in decision.alternatives])
  
  # Load
  alternatives = [Alternative(**a) for a in json.loads(row['alternatives'] or '[]')]
  ```

detection:
  - Storing List[BaseModel] fields
  - Storing Optional[dict] fields
  - Any complex nested structure

root_cause: |
  SQLite stores JSON as TEXT. Python's sqlite3 doesn't 
  automatically handle Pydantic serialization.
```

## Product Edges

### Empty State Problem

```yaml
edge: "New user has no memories—Mind seems useless"
symptoms:
  - "What does this even do?"
  - Session primer is empty
  - No context to retrieve
  - User abandons before value

workaround: |
  1. Project detection on first run:
     - Scan for package.json, pyproject.toml
     - Infer stack from dependencies
     - Create initial project state
  
  2. Smart onboarding:
     - Ask 2-3 key questions
     - Seed initial decisions ("What are you building?")
  
  3. Show value fast:
     - "I see you're using Next.js with Supabase..."
     - Suggest relevant community edges

detection:
  - First session
  - No existing project
  - Empty primer generated

root_cause: |
  Mind's value is emergent—it grows with use.
  First session has nothing to draw from.
```

### Memory Creep

```yaml
edge: "Users accumulate irrelevant memories over time"
symptoms:
  - Retrieval gets noisy
  - Old decisions surface when not relevant
  - Context becomes stale
  - Search returns too much

workaround: |
  1. Decay system:
     - Track access frequency
     - Lower priority of unused memories
     - Archive after threshold
  
  2. Project scoping:
     - Archive all memories when project completes
     - Separate active vs archived
  
  3. Manual cleanup:
     - "Mind cleanup" command
     - Show stale memories for review

detection:
  - Project age > 3 months
  - Many memories, low access rate
  - User complains about irrelevant results

root_cause: |
  Without decay, every memory has equal weight.
  Old, irrelevant memories pollute retrieval.
```

### Abandoned Sessions

```yaml
edge: "User closes terminal without ending session"
symptoms:
  - Session never captured
  - Next session doesn't know what happened
  - Orphaned session records
  - Lost progress

workaround: |
  1. Auto-save interval:
     - Save session state every 5 minutes
     - Capture in-progress summary
  
  2. Session timeout detection:
     - Mark stale sessions as abandoned
     - Recover what we can on next start
  
  3. Recovery prompt:
     - "Last session ended unexpectedly"
     - "What happened? Want to add notes?"

detection:
  - Session active > 4 hours with no end
  - Process killed / terminal closed
  - No end_session call before start_session

root_cause: |
  MCP doesn't have reliable shutdown hooks.
  Terminal close doesn't trigger cleanup.
```

### Over-Reliance

```yaml
edge: "User trusts Mind too much, doesn't verify"
symptoms:
  - Outdated decision treated as current
  - Sharp edge workaround that's no longer needed
  - User doesn't question AI
  - Mistakes compound

workaround: |
  1. Show dates on everything:
     - "Decision from 6 months ago"
     - "Edge discovered 2024-03-15"
  
  2. Show confidence levels:
     - Decisions have confidence scores
     - Low-confidence decisions flagged
  
  3. Prompt for review:
     - "This decision is 6 months old—still valid?"
     - revisit_if conditions surface prominently
  
  4. Never present as absolute truth:
     - "Based on our previous work..."
     - "If I recall correctly..."

detection:
  - Accessing old memories (>3 months)
  - Low-confidence decisions being applied
  - revisit_if conditions triggered

root_cause: |
  Memory implies authority. Users may trust 
  stored information without verification.
```

### Trigger Phrase Collisions

```yaml
edge: "Multiple memories match same trigger phrase"
symptoms:
  - Wrong memory surfaces
  - Inconsistent results
  - User confusion

workaround: |
  1. Require unique trigger phrases per project
  2. Weight by recency when collisions occur
  3. Return multiple matches, let context resolve
  4. Refine triggers after collisions

detection:
  - Multiple entities with same trigger_phrase
  - Retrieval returns multiple strong matches
  - User says "no, the other one"

root_cause: |
  Trigger phrases are added organically.
  No validation for uniqueness.
```

## Development Edges

### Pydantic V2 Migration

```yaml
edge: "Pydantic V2 has different API than V1"
symptoms:
  - .dict() deprecated, use .model_dump()
  - ValidationError structure changed
  - Field(...) syntax differences

workaround: |
  Use Pydantic V2 from the start:
  
  ```python
  # V2 style
  from pydantic import BaseModel, Field
  
  class Decision(BaseModel):
      title: str = Field(description="...")
      
      def to_dict(self):
          return self.model_dump()
  ```

detection:
  - pydantic>=2.0.0 in dependencies
  - .dict() calls
  - validator decorator usage

root_cause: |
  Pydantic V2 is a major rewrite with breaking changes.
  Much code online uses V1 patterns.
```

### Async SQLite

```yaml
edge: "sqlite3 module is blocking, not async"
symptoms:
  - Async MCP server blocks on DB calls
  - Poor concurrency
  - Timeouts under load

workaround: |
  Use aiosqlite for async operations:
  
  ```python
  import aiosqlite
  
  async def get_decision(id: str):
      async with aiosqlite.connect(DB_PATH) as db:
          async with db.execute("SELECT * FROM decisions WHERE id = ?", [id]) as cursor:
              row = await cursor.fetchone()
              return Decision.from_row(row)
  ```

detection:
  - sqlite3 import in async code
  - MCP tools with DB calls
  - High latency under concurrent requests

root_cause: |
  Standard sqlite3 is synchronous and blocks 
  the event loop when used in async context.
```

### MCP Stdio Buffering

```yaml
edge: "MCP stdio transport can buffer unexpectedly"
symptoms:
  - Messages delayed or batched
  - Tool responses seem stuck
  - Inconsistent timing

workaround: |
  1. Flush stdout explicitly
  2. Use line-buffered mode
  3. Keep messages small
  
  ```python
  import sys
  sys.stdout.reconfigure(line_buffering=True)
  ```

detection:
  - Large tool responses
  - Streaming-style tools
  - Debugging MCP communication

root_cause: |
  Python buffers stdout by default. MCP expects 
  line-delimited JSON messages without buffering.
```

## Operational Edges

### Backup Before Upgrade

```yaml
edge: "Schema changes can break existing data"
symptoms:
  - Errors after upgrade
  - Data loss
  - Rollback not possible

workaround: |
  1. Always backup before upgrade:
     ```bash
     cp -r ~/.mind ~/.mind-backup-$(date +%Y%m%d)
     ```
  
  2. Run migration scripts
  3. Verify data integrity
  4. Keep backup until confirmed working

detection:
  - Major version upgrade
  - Schema changes in changelog
  - New required fields

root_cause: |
  SQLite schema changes require migration.
  No automatic rollback if migration fails.
```

### Debug Data Contamination

```yaml
edge: "Test data leaks into production Mind"
symptoms:
  - Weird memories appearing
  - Test projects in production
  - Confusion about what's real

workaround: |
  1. Use separate data directories:
     ```bash
     MIND_DATA_DIR=~/.mind-test mind serve
     ```
  
  2. Clear test data before switching
  3. Use distinct project names for tests
  4. Check data dir on startup, warn if wrong

detection:
  - Running tests without isolation
  - Switching between dev and production
  - Project names like "test" or "foo"

root_cause: |
  Default data dir is shared across all uses.
  Easy to mix test and real data.
```

---

## Adding New Edges

When you discover a new sharp edge:

1. Document it in this file
2. Add detection pattern to Mind's edge registry
3. Consider if it should be a community edge
4. Update workaround if better solution found

Format:

```yaml
edge: "Short title"
symptoms:
  - What user sees
  - Error messages
  - Confusing behavior

workaround: |
  Step by step solution with code if needed

detection:
  - When this edge might be hit
  - Patterns to match

root_cause: |
  Why this happens
```

---

*This file is Mind eating its own dog food. Every edge here should also be in Mind's sharp edge registry.*
