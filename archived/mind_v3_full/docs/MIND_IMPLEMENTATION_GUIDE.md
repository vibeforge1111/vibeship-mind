# Mind v3→v4 Implementation Guide

> Your step-by-step roadmap for vibe coding Mind into reality

---

## Current Goal: Phase 1 - Simplify v3

**Timeline:** 2 weeks
**Outcome:** Working three-table foundation with AI extraction

Before building the future, we fix the present. Your v3 has 9 tables but only 1 has data. Let's simplify to three tables that actually work.

---

## Session 1: The Purge (Day 1)

### What You'll Tell Claude Code:

```
I'm simplifying Mind v3. We have 9 LanceDB tables but most are empty because 
extraction isn't working. We're going to:

1. Keep only: memories.lance, edges.lance (new), outcomes.lance (new)
2. Archive the rest: decisions, patterns, policies, entities, precedents, 
   exceptions, autonomy
3. Store structured data AS FIELDS on memories, not separate tables

Let's start by creating an archived/ directory and moving the complex v3 code there.
Don't delete anything - just move it.
```

### Expected Changes:

```
src/mind/v3/
├── graph/                    # Keep but simplify
│   ├── memories.lance        # Keep - add structure field
│   ├── edges.lance           # New
│   └── outcomes.lance        # New
│
├── archived/                 # New - move here
│   ├── decisions.lance
│   ├── patterns.lance
│   ├── policies.lance
│   ├── entities.lance
│   ├── precedents.lance
│   ├── exceptions.lance
│   ├── autonomy.lance
│   └── extractors/           # Complex extractors
```

### Verify:

```bash
uv run pytest tests/v3/ -v  # Some tests will fail - that's expected
uv run mind status          # Should still work
```

---

## Session 2: Simplified Memory Schema (Day 2)

### What You'll Tell Claude Code:

```
Now let's update the memory schema. Instead of separate tables for decisions, 
entities, patterns - we store that as a 'structure' field on each memory.

Here's the new schema:

{
    "id": "mem_xxx",
    "content": "...",
    "type": "decision",  # observation | decision | outcome | learning
    "embedding": [...],
    "structure": {
        "decision": {
            "action": "...",
            "reasoning": "...",
            "alternatives": [...],
            "confidence": 0.8,
            "predicted_outcome": "..."
        },
        "entities": [{"name": "...", "type": "..."}],
        "domain": "..."
    },
    "confidence": 0.8,
    "agent_id": null,
    "session_id": "...",
    "status": "active",
    "created_at": "...",
    "updated_at": "..."
}

Update the LanceDB schema and any code that reads/writes memories.
```

### Verify:

```bash
uv run mind recall           # Should work
uv run mind log "test" decision  # Should work
```

---

## Session 3: AI Extraction Function (Day 3-4)

### What You'll Tell Claude Code:

```
Now the key part: we need an extract_structure() function that uses an LLM 
to extract structured data from memory content.

Use Anthropic's Haiku model (claude-3-haiku-20240307) - it's cheap and fast.

Function signature:
def extract_structure(content: str, memory_type: str) -> dict:
    """
    Extract structured data from memory content.
    
    Returns:
    {
        "decision": {...} or null,
        "entities": [...],
        "domain": "..." or null
    }
    """

The prompt should:
1. Identify if this is a decision (has action, reasoning, alternatives)
2. Extract mentioned entities (technologies, people, concepts)
3. Identify the domain (infrastructure, frontend, security, etc.)

Make it fail gracefully - if extraction fails, return empty structure.
Don't block mind_log() if extraction fails.
```

### Test Cases:

```python
# Test 1: Clear decision
content = "Decided to use Redis for caching because latency requirement is <100ms. Considered Memcached but Redis has better persistence."
result = extract_structure(content, "decision")
assert result["decision"]["action"] == "use Redis for caching"
assert "Memcached" in [a["option"] for a in result["decision"]["alternatives"]]
assert "Redis" in [e["name"] for e in result["entities"]]

# Test 2: Simple observation
content = "The API is returning 500 errors intermittently"
result = extract_structure(content, "observation")
assert result["decision"] is None
assert "API" in [e["name"] for e in result["entities"]]

# Test 3: Learning
content = "Learned that connection pooling prevents timeout issues under load"
result = extract_structure(content, "learning")
assert "connection pooling" in [e["name"] for e in result["entities"]]
```

---

## Session 4: Integrate Extraction (Day 5)

### What You'll Tell Claude Code:

```
Now integrate extract_structure() into the mind_log() flow.

When mind_log() is called:
1. Write to MEMORY.md (v2 layer - unchanged)
2. Generate embedding
3. Call extract_structure() to get structured data
4. Store in memories.lance with structure field

Make extraction async/background if possible - don't slow down the response.
If extraction fails, store memory without structure (structure = {}).

Also add a backfill command:
uv run mind backfill-structure

This should process all existing memories that don't have structure yet.
```

### Verify:

```bash
uv run mind log "Decided to use PostgreSQL for the user database because we need ACID compliance" decision
uv run mind search "database"  # Should show the decision with structure
```

---

## Session 5: Edges Table (Day 6-7)

### What You'll Tell Claude Code:

```
Now let's add the edges table. Edges connect memories to each other.

Schema:
{
    "id": "edge_xxx",
    "source_id": "mem_xxx",
    "target_id": "mem_xxx",
    "edge_type": "same_entity",  # same_entity | similar_to | outcome_of | led_to
    "weight": 0.9,
    "created_at": "...",
    "status": "active"
}

Create the table and add a find_edges() function that:
1. Finds memories with same entities
2. Finds semantically similar memories (embedding similarity > 0.85)

When a new memory is added, automatically find and create edges.
```

### Test:

```bash
uv run mind log "Redis is failing under high load" problem
uv run mind log "Fixed Redis by adding connection pooling" decision
# These should be automatically linked (same entity: Redis)

uv run mind edges mem_xxx  # Should show the connection
```

---

## Session 6: Graph-Aware Search (Day 8)

### What You'll Tell Claude Code:

```
Update mind_search() to use edges.

Current: Returns top N memories by embedding similarity
New: Returns top N memories by similarity, PLUS related memories via edges

Algorithm:
1. Vector search for query → get top 10 matches
2. For top 3 matches, follow edges (weight > 0.7) 
3. Add connected memories to results
4. Dedupe and re-rank by relevance
5. Return combined results

This way, searching for "Redis" returns not just mentions of Redis, 
but also decisions that led to Redis problems, outcomes of Redis decisions, etc.
```

### Test:

```bash
uv run mind search "caching performance"
# Should return:
# 1. Direct matches about caching
# 2. Related decisions about caching choices
# 3. Outcomes of those decisions (via edges)
```

---

## Session 7: Outcomes Table (Day 9-10)

### What You'll Tell Claude Code:

```
Add outcomes tracking. This is where learning happens.

Schema:
{
    "id": "outcome_xxx",
    "decision_id": "mem_xxx",
    "success": true,
    "result_summary": "...",
    "predicted": {...},
    "actual": {...},
    "lessons": [...],
    "confidence_adjustment": 0.05,
    "created_at": "..."
}

Add MCP tool:
mind_outcome(decision_id: str, success: bool, notes: str = "")

When outcome is recorded:
1. Create outcome record
2. Create edge: outcome → decision (type: outcome_of)
3. Update decision's confidence based on success
4. Log the learning
```

### Test:

```bash
# First, make a decision
uv run mind log "Decided to use Redis for session storage" decision
# Returns: mem_abc123

# Later, record outcome
uv run mind outcome mem_abc123 true "Working great, 5ms latency"

# Verify
uv run mind search "Redis session"
# Should show decision + outcome linked
```

---

## Session 8: Confidence Propagation (Day 11-12)

### What You'll Tell Claude Code:

```
When outcomes are recorded, confidence should propagate through the graph.

Implement process_outcome():
1. Update decision's confidence (Bayesian update)
2. Find precedents that informed this decision (via 'informed_by' edges)
3. Update precedent usefulness scores
4. If failure: check for patterns that might be invalidated
5. Track prediction accuracy (if predicted_outcome was set)

Simple Bayesian update:
new_confidence = old_confidence + (adjustment * (1 if success else -1))
Clamp between 0.1 and 0.99

This creates the learning loop: outcomes improve future decisions.
```

---

## Session 9: Basic Consolidation (Day 13)

### What You'll Tell Claude Code:

```
Add a basic consolidation command that runs the Gardener tasks.

uv run mind consolidate

Should:
1. Find near-duplicate memories (similarity > 0.95) and mark as superseded
2. Decay confidence of old decisions without outcomes (>30 days)
3. Find clusters of similar memories that might be patterns
4. Report: "Consolidated X memories, found Y potential patterns, decayed Z stale items"

For now, just detection and reporting. We'll add automatic pattern creation later.
```

---

## Session 10: Verification & Polish (Day 14)

### What You'll Tell Claude Code:

```
Let's verify everything works end-to-end and fix any issues.

Test the full flow:
1. mind_recall() - should show recent memories with structure
2. mind_log() with decision - should extract structure automatically
3. mind_search() - should follow edges
4. mind_outcome() - should update confidence
5. mind_consolidate() - should run without errors

Also update mind_recall() output to show:
- Recent decisions with confidence
- Related memories (via edges)
- Any pending outcomes needed

Fix any bugs found during testing.
```

---

## Phase 1 Complete Checklist

Before moving to Phase 2, verify:

- [ ] Only 3 LanceDB tables: memories, edges, outcomes
- [ ] All memories have structure field (even if empty)
- [ ] AI extraction works on new mind_log() calls
- [ ] Existing memories backfilled with structure
- [ ] Edges automatically created for same-entity and similarity
- [ ] mind_search() follows edges
- [ ] mind_outcome() creates outcomes and updates confidence
- [ ] mind_consolidate() runs without errors
- [ ] All v2 functionality still works (MEMORY.md, SESSION.md)

---

## What's Next: Phase 2 Preview

Once Phase 1 is solid, Phase 2 adds:

1. **Pattern Detection**: Automatically detect patterns from clustered memories
2. **Prediction Tracking**: Log expected outcomes on decisions, compare to actual
3. **Contradiction Detection**: Find conflicting patterns/decisions
4. **Better Consolidation**: Automatic pattern creation, policy suggestions

But don't start Phase 2 until Phase 1 is rock solid. The foundation matters.

---

## Tips for Vibe Coding This

### Start Each Session With Context

```
I'm working on Mind v4. Current phase: Phase 1 - Simplification.
Current session goal: [specific goal from above]

Here's the architecture doc: [paste relevant section]

Let's continue from where we left off.
```

### When Stuck

```
This isn't working as expected. Here's what I see: [error/behavior]
Here's what I expected: [expected behavior]

Can you help me debug? Let's check the code step by step.
```

### When It Works

```
That's working. Let's commit this: "feat: [description]"

Then let's move to the next step: [next goal]
```

### End Each Session With

```
Let's summarize what we accomplished and what's next.
Log this to Mind so we remember: mind_log("...", type="progress")
```

---

## The Bigger Picture

Remember what we're building toward:

**Phase 1-2 (Now):** Working memory with structure and relationships
**Phase 3-4:** Learning loop that actually improves decisions  
**Phase 5-6:** Multi-agent coordination
**Phase 7-8:** Intent alignment
**Phase 9-10:** The Graph - connected intelligence across users

Each phase builds on the last. Get Phase 1 right, and everything else becomes possible.

You're building cognitive infrastructure for humanity. One session at a time.

---

*Start with Session 1. Ship something working. Iterate.*
