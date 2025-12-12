# Context Relevance Scoring Design

## Overview

Enhance context retrieval to combine multiple signals for more relevant results:
1. **Semantic similarity** - ChromaDB cosine similarity (existing)
2. **Recency weighting** - Boost recent items
3. **Access frequency** - Boost frequently accessed items
4. **Trigger phrase matching** - Exact match boost (existing)

## Scoring Formula

```
final_score = semantic_similarity * (1 + recency_boost + frequency_boost + trigger_boost)
```

Where:
- `semantic_similarity`: 0.0-1.0 from ChromaDB cosine distance
- `recency_boost`: 0.0-0.3 based on age (newer = higher)
- `frequency_boost`: 0.0-0.2 based on access count
- `trigger_boost`: 0.0-0.2 for exact phrase matches

### Recency Decay

Use exponential decay with configurable half-life:

```python
days_old = (now - entity_timestamp).days
recency_boost = 0.3 * (0.5 ** (days_old / HALF_LIFE_DAYS))
```

With `HALF_LIFE_DAYS = 7`:
- 0 days old: +0.30 boost
- 7 days old: +0.15 boost
- 14 days old: +0.075 boost
- 30 days old: ~0.01 boost

### Frequency Boost

Logarithmic scaling to prevent runaway boost:

```python
frequency_boost = min(0.2, 0.1 * log2(1 + access_count))
```

- 0 accesses: +0.00 boost
- 1 access: +0.10 boost
- 3 accesses: +0.20 boost (capped)
- 10 accesses: +0.20 boost (capped)

## Implementation

### 1. Access Tracking Table

New SQLite table to track access patterns:

```sql
CREATE TABLE IF NOT EXISTS entity_access (
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    access_count INTEGER DEFAULT 0,
    last_accessed TEXT,
    PRIMARY KEY (entity_type, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_access_count ON entity_access(entity_type, access_count DESC);
```

### 2. Storage Methods

Add to `SQLiteStorage`:
- `record_access(entity_type, entity_id)` - Increment count and update timestamp
- `get_access_stats(entity_type, entity_ids)` - Bulk fetch access stats

### 3. ContextEngine Enhancement

Update `get_relevant_context()` to:
1. Get semantic results from ChromaDB
2. Fetch access stats for all result IDs
3. Fetch entity timestamps for recency calculation
4. Apply combined scoring formula
5. Re-sort by final score

### 4. Integration Points

Record access when entities are returned in context:
- `mind_get_context` - After returning results
- `mind_start_session` - For primer entities

## Entity Timestamps

Use existing fields for recency:
- Decisions: `decided_at`
- Issues: `updated_at` (or `resolved_at` if resolved)
- Sharp Edges: `discovered_at`
- Episodes: `ended_at`

## API Changes

None - scoring is internal to context retrieval.

## Files to Modify

1. `src/mind/storage/sqlite.py` - Add access tracking table + methods
2. `src/mind/engine/context.py` - Enhanced scoring algorithm
3. `src/mind/mcp/server.py` - Record access after context retrieval
4. `tests/test_context.py` - New test file for scoring

## Testing

1. Test recency boost calculation
2. Test frequency boost calculation
3. Test combined scoring ranks correctly
4. Test access recording increments count
5. Test bulk access stat retrieval
