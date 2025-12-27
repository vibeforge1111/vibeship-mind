# Mind v3 Migration Plan

## Overview

Migrate the production MCP server from legacy modules to the new v3 architecture while maintaining backward compatibility.

## Current State

### Legacy Modules (in use)
```
src/mind/legacy/
├── parser.py      # Regex-based extraction
├── context.py     # CLAUDE.md context generation
├── similarity.py  # Embedding similarity search
```

### v3 Modules (ready)
```
src/mind/v3/
├── capture/       # Event sourcing
├── graph/         # LanceDB storage
├── intelligence/  # Model cascade + extractors
├── retrieval/     # Embeddings, search, reranking, injection
├── memory/        # Working memory, consolidation, decay
├── autonomy/      # Confidence, levels, feedback, dashboard
└── hooks/         # Claude Code integration (TO IMPLEMENT)
```

## Migration Phases

### Phase A: Implement v3 Hooks
**Goal:** Create Claude Code hook handlers that use v3 modules.

1. `prompt_submit.py` - UserPromptSubmit hook
   - Inject relevant context before Claude sees the prompt
   - Uses: retrieval.context_injection, memory.working_memory

2. `session_end.py` - Session end handler
   - Consolidate session memories
   - Uses: memory.consolidation, capture.store

3. `transcript_capture.py` - Real-time capture
   - Extract events from conversation
   - Uses: capture.extractor, intelligence.extractors

### Phase B: Parallel Operation
**Goal:** Run v3 alongside legacy without breaking changes.

1. Add v3 context to MCP responses (append, don't replace)
2. Log v3 decisions for comparison
3. Capture events to v3 store while legacy still operates

### Phase C: Gradual Replacement
**Goal:** Replace legacy functions one by one.

| Legacy Function | v3 Replacement | Priority |
|-----------------|----------------|----------|
| `Parser.extract_decisions` | `intelligence.extractors.decision` | High |
| `semantic_similarity` | `retrieval.embeddings` | High |
| `ContextGenerator.generate` | `retrieval.context_injection` | Medium |
| `Parser.extract_entities` | `intelligence.extractors.entity` | Low |

### Phase D: Deprecate Legacy
**Goal:** Remove legacy modules entirely.

1. Update all imports to v3
2. Remove legacy/ folder
3. Update tests

## Implementation Order

```
1. hooks/prompt_submit.py     ← START HERE
2. hooks/session_end.py
3. Wire hooks to MCP server
4. Add v3 to mind_recall()
5. Parallel testing period
6. Replace legacy imports
7. Remove legacy/
```

## Risk Mitigation

- **Feature flag:** `use_v3=True/False` in config
- **Fallback:** If v3 fails, return legacy result
- **Logging:** Compare v3 vs legacy outputs
- **Gradual rollout:** One function at a time
