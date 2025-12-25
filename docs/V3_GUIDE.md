# Mind v3 Guide

Complete guide to the v3 architecture - what's changed, how to use it, and what's next.

## Quick Status

| Component | Status | Notes |
|-----------|--------|-------|
| Event Sourcing | Ready | Captures all events with timestamps |
| Graph Storage | Ready | LanceDB-based vector storage |
| Intelligence Layer | Ready | Model cascade + extractors |
| Retrieval System | Ready | Embeddings, hybrid search, reranking |
| Memory System | Ready | Working memory, consolidation, decay |
| Autonomy System | Ready | Confidence tracking, feedback loops |
| Claude Code Hooks | Ready | Prompt submit, session end |
| MCP Integration | **Live** | Running in parallel with legacy |

**Current Mode:** Observation (v3 captures alongside legacy, doesn't replace yet)

---

## What's Changed

### Architecture Shift

| Before (Legacy) | After (v3) |
|-----------------|------------|
| Regex-based parsing | Event sourcing + extractors |
| Simple similarity search | Hybrid search (vector + keyword) |
| Static MEMORY.md | Dynamic graph with decay |
| Manual categorization | Intelligent auto-extraction |
| No confidence tracking | Progressive autonomy system |

### New Capabilities

1. **Event Sourcing**: Every action is an immutable event with timestamp
2. **Hybrid Search**: Combines vector similarity + keyword matching + reranking
3. **Memory Decay**: Unused memories fade, frequently accessed ones strengthen
4. **Confidence Tracking**: Tracks success/failure of actions
5. **Progressive Autonomy**: Earns trust through demonstrated judgment
6. **Observability Dashboard**: System health monitoring

---

## Where Things Are Stored

### File Locations

```
.mind/
├── MEMORY.md          # Permanent memories (legacy + v3 writes here)
├── SESSION.md         # Ephemeral session data (cleared between sessions)
├── REMINDERS.md       # Scheduled reminders
├── state.json         # Session state tracking
└── v3/                # v3-specific storage (future)
    ├── events/        # Event sourcing store
    ├── graph/         # LanceDB vector store
    └── autonomy/      # Confidence + feedback data
```

### Memory Types and Destinations

| Type | Destination | Persistence | v3 Captures |
|------|-------------|-------------|-------------|
| `experience` | SESSION.md | Ephemeral | Yes (session events) |
| `blocker` | SESSION.md | Ephemeral | Yes (session events) |
| `assumption` | SESSION.md | Ephemeral | Yes (session events) |
| `rejected` | SESSION.md | Ephemeral | Yes (session events) |
| `decision` | MEMORY.md | Permanent | Yes (retrieval memory) |
| `learning` | MEMORY.md | Permanent | Yes (retrieval memory) |
| `problem` | MEMORY.md | Permanent | Yes (retrieval memory) |
| `progress` | MEMORY.md | Permanent | Yes (retrieval memory) |

---

## How to Use v3

### Automatic (Already Enabled)

v3 captures automatically when you use these MCP tools:

```python
# These now feed v3 automatically:
mind_recall()           # Initializes v3 bridge
mind_log(msg, type)     # Records to v3 session/memory
```

### Check v3 Status

After `mind_recall()`, look for the `v3` field in the response:

```json
{
  "context": "...",
  "v3": {
    "enabled": true,
    "hooks_initialized": true,
    "retrieval": {
      "total_retrievals": 0,
      "memory_count": 5
    },
    "session_events": 3
  }
}
```

### v3 Stats Explained

| Field | Meaning |
|-------|---------|
| `enabled` | v3 bridge is active |
| `hooks_initialized` | Prompt and session hooks ready |
| `memory_count` | Memories added this session |
| `session_events` | Session events captured |
| `total_retrievals` | Times context was retrieved |

---

## Verification Checklist

Use this to verify v3 is working correctly:

### Session Start
- [ ] `mind_recall()` returns `v3` field in response
- [ ] `v3.enabled` is `true`
- [ ] `v3.hooks_initialized` is `true`

### During Work
- [ ] `mind_log("doing X", type="experience")` increments `session_events`
- [ ] `mind_log("decided Y", type="decision")` increments `memory_count`
- [ ] No errors in responses

### Session End
- [ ] Session events were captured
- [ ] Memories are stored for future retrieval

---

## What's Operational

### Fully Working

1. **Event Capture**: All `mind_log` calls feed v3
2. **Session Tracking**: Session events recorded in v3 bridge
3. **Memory Storage**: Decisions/learnings added to v3 memory
4. **Parallel Operation**: v3 runs alongside legacy safely
5. **Stats Reporting**: v3 stats included in `mind_recall()` response

### Not Yet Active (Phase C)

1. **Context Injection**: v3 doesn't inject context into prompts yet (legacy still does this)
2. **Semantic Retrieval**: v3 memories aren't searched yet for context
3. **Session Consolidation**: Session end hook isn't called automatically

### Future Phases

| Phase | Description | Status |
|-------|-------------|--------|
| A | Implement v3 hooks | Done |
| B | Parallel operation | **Current** |
| C | Gradual replacement | Next |
| D | Deprecate legacy | Future |

---

## v3 Module Reference

### Capture Layer (`mind.v3.capture`)
- `EventStore`: Immutable event storage
- `CaptureExtractor`: Extract events from text

### Graph Layer (`mind.v3.graph`)
- `MemoryGraph`: LanceDB-based graph storage
- `Node`, `Edge`: Graph primitives

### Intelligence Layer (`mind.v3.intelligence`)
- `ModelCascade`: Fast model -> powerful model fallback
- `DecisionExtractor`, `LearningExtractor`: Smart extraction

### Retrieval Layer (`mind.v3.retrieval`)
- `HybridSearch`: Vector + keyword search
- `Reranker`: Result reranking
- `ContextInjector`: Format context for Claude

### Memory Layer (`mind.v3.memory`)
- `WorkingMemory`: Short-term session memory
- `Consolidation`: Session -> permanent memory
- `Decay`: Usage-based retention

### Autonomy Layer (`mind.v3.autonomy`)
- `ConfidenceTracker`: Track action success/failure
- `AutonomyManager`: Progressive autonomy levels
- `FeedbackLoop`: User feedback processing
- `ObservabilityDashboard`: System health

### Hooks (`mind.v3.hooks`)
- `PromptSubmitHook`: Inject context before prompts
- `SessionEndHook`: Consolidate at session end

### Bridge (`mind.v3.bridge`)
- `V3Bridge`: Clean interface for MCP server
- `get_v3_bridge()`: Get/create bridge instance

---

## Troubleshooting

### v3 Field Missing from mind_recall()

**Cause**: v3 import failed or not available
**Fix**: Check for import errors in MCP server logs

### v3.enabled is False

**Cause**: Bridge disabled in config
**Fix**: Check `V3Config.enabled` setting

### session_events Not Incrementing

**Cause**: Only session types (experience, blocker, etc.) increment this
**Fix**: Use correct type in `mind_log()`

### memory_count Not Incrementing

**Cause**: Only memory types (decision, learning, etc.) increment this
**Fix**: Use correct type in `mind_log()`

---

## Next Steps

When you're ready to move to Phase C (gradual replacement):

1. **Enable v3 context injection** in `mind_recall()`
2. **Compare v3 vs legacy** context quality
3. **Switch one function at a time** (retrieval first, then extraction)
4. **Monitor for regressions**

To enable Phase C, we'll modify `handle_recall()` to use v3 context instead of legacy.

---

## Test Coverage

All v3 modules have comprehensive tests:

```
tests/v3/
├── capture/           # 23 tests
├── graph/             # 33 tests
├── intelligence/      # 35 tests
├── retrieval/         # 56 tests
├── memory/            # 70 tests
├── autonomy/          # 70 tests
├── hooks/             # 25 tests
└── test_bridge.py     # 18 tests

Total: 362 v3 tests (all passing)
```

Run tests:
```bash
uv run pytest tests/v3/ -v
```

---

## Quick Reference

### MCP Tools That Feed v3

| Tool | v3 Action |
|------|-----------|
| `mind_recall()` | Initialize bridge, return stats |
| `mind_log(type=session_type)` | Record session event |
| `mind_log(type=memory_type)` | Add to retrieval memory |

### Session Types (Ephemeral)
`experience`, `blocker`, `assumption`, `rejected`

### Memory Types (Permanent)
`decision`, `learning`, `problem`, `progress`

### Autonomy Levels
1. RECORD_ONLY - Observe only
2. SUGGEST - Propose based on precedent
3. ASK_PERMISSION - Propose with confidence
4. ACT_NOTIFY - Act automatically, inform user
5. SILENT - Handle automatically, log only

---

*Last updated: 2025-12-26*
*v3 Status: Observation Mode (Phase B)*
