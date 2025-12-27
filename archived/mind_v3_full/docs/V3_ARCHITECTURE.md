# Mind v3 Architecture

## Overview

Mind v3 uses a **dual-layer architecture** where the human-readable v2 system (MEMORY.md) runs alongside a semantic graph database (LanceDB).

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER / CLAUDE                               │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            MCP SERVER (12 tools)                         │
│  mind_recall() │ mind_log() │ mind_search() │ mind_session() │ ...      │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                 ▼
┌──────────────────────────────┐    ┌──────────────────────────────────────┐
│        V2 LAYER (Legacy)      │    │           V3 LAYER (New)              │
│   Human-readable markdown     │    │    Semantic graph + vectors           │
│                               │    │                                       │
│  .mind/                       │    │  .mind/v3/graph/                      │
│  ├── MEMORY.md   (permanent)  │    │  ├── memories.lance                   │
│  ├── SESSION.md  (ephemeral)  │    │  ├── decisions.lance                  │
│  └── REMINDERS.md             │    │  ├── entities.lance                   │
│                               │    │  ├── patterns.lance                   │
│  ✓ Git-trackable              │    │  ├── policies.lance                   │
│  ✓ Human-editable             │    │  └── ...                              │
│  ✓ Always works               │    │                                       │
└──────────────────────────────┘    │  ✓ Semantic search                    │
                                     │  ✓ Entity extraction                  │
                                     │  ✓ Pattern detection                  │
                                     └──────────────────────────────────────┘
```

## Data Flow

### 1. When User Calls `mind_log("decided to use Redis", type="decision")`

```
mind_log()
    │
    ├──► V2: Append to MEMORY.md
    │         "**Decided:** use Redis"
    │
    └──► V3 Bridge
            │
            ├──► Add to memories.lance (with embedding)
            │
            ├──► Decision Extractor
            │         └──► Add to decisions.lance
            │               {action: "use Redis", reasoning: "...", confidence: 0.6}
            │
            └──► Entity Extractor
                      └──► Add to entities.lance
                            {name: "Redis", type: "technology"}
```

### 2. When User Calls `mind_recall()`

```
mind_recall()
    │
    ├──► V2: Read MEMORY.md + SESSION.md
    │         → Generate context string
    │
    └──► V3 Bridge
            │
            ├──► Seed memories from MEMORY.md (if not done)
            │
            └──► PromptSubmitHook.process(user_query)
                    │
                    ├──► Query Expander
                    │         → Generate sub-queries
                    │         → Extract entities from query
                    │
                    ├──► Search memories.lance (vector search)
                    │
                    ├──► Score & Rank results
                    │
                    ├──► Reranker (cross-encoder)
                    │
                    └──► Return "## Relevant Context\n- [decision] ..."
```

### 3. When User Calls `mind_search("authentication")`

```
mind_search("authentication")
    │
    ├──► V2: Keyword search in MEMORY.md
    │         → TF-IDF similarity
    │
    └──► V3: Vector search in memories.lance
              → Semantic similarity (cosine distance)
              → Returns related content even with different wording
```

## The 9 Graph Tables

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           GRAPH STORE (LanceDB)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  CORE TABLES                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  memories   │  │  decisions  │  │  entities   │  │  patterns   │     │
│  │             │  │             │  │             │  │             │     │
│  │ - content   │  │ - action    │  │ - name      │  │ - desc      │     │
│  │ - type      │  │ - reasoning │  │ - type      │  │ - type      │     │
│  │ - vector    │  │ - alts      │  │ - desc      │  │ - confidence│     │
│  │             │  │ - confidence│  │ - vector    │  │ - evidence  │     │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                                          │
│  GOVERNANCE TABLES                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │  policies   │  │ exceptions  │  │ precedents  │                      │
│  │             │  │             │  │             │                      │
│  │ - rule      │  │ - policy_id │  │ - decision  │                      │
│  │ - scope     │  │ - condition │  │ - context   │                      │
│  │ - active    │  │ - reason    │  │ - outcome   │                      │
│  └─────────────┘  └─────────────┘  └─────────────┘                      │
│                                                                          │
│  LEARNING TABLES                                                         │
│  ┌─────────────┐  ┌─────────────┐                                       │
│  │  outcomes   │  │  autonomy   │                                       │
│  │             │  │             │                                       │
│  │ - decision  │  │ - action    │                                       │
│  │ - success   │  │ - level     │                                       │
│  │ - feedback  │  │ - confidence│                                       │
│  └─────────────┘  └─────────────┘                                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### Intelligence Router

Routes extraction tasks to appropriate handlers based on cost/capability:

```
┌─────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE LEVELS                       │
├─────────────────────────────────────────────────────────────┤
│  LOCAL   │ Regex/rules     │ Free, instant    │ ✓ Default  │
│  LOW     │ Basic NLP       │ spaCy            │            │
│  MEDIUM  │ AI batched      │ Haiku            │            │
│  HIGH    │ AI frequent     │ Sonnet           │            │
│  ULTRA   │ Real-time AI    │ Opus             │            │
└─────────────────────────────────────────────────────────────┘

Currently implemented: LOCAL level (regex-based extraction)
```

### Query Expander

Improves search recall by expanding queries:

```
Input:  "fix auth bug"
           │
           ▼
┌─────────────────────────────────────────┐
│           QUERY EXPANDER                 │
├─────────────────────────────────────────┤
│  Sub-queries:                            │
│    - "authentication error"              │
│    - "login problem"                     │
│    - "auth fix"                          │
│                                          │
│  Entities:                               │
│    - "auth" (concept)                    │
│    - "bug" (issue type)                  │
└─────────────────────────────────────────┘
           │
           ▼
Output: Multiple searches → merged results
```

### Reranker

Refines search results using cross-encoder:

```
Initial Results (by vector distance)    Reranked Results (by relevance)
┌────────────────────────────────┐     ┌────────────────────────────────┐
│ 1. "auth module created"       │     │ 1. "fixed auth bug in login"   │
│ 2. "fixed auth bug in login"   │ ──► │ 2. "auth validation error"     │
│ 3. "auth validation error"     │     │ 3. "auth module created"       │
└────────────────────────────────┘     └────────────────────────────────┘
```

### View Generator

Creates human-readable markdown from graph data:

```
┌─────────────────────────────────────────────────────────────┐
│                    VIEW GENERATOR                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  decisions.lance  ──►  DECISIONS.md                         │
│    - Grouped by date                                         │
│    - Shows reasoning & alternatives                          │
│                                                              │
│  patterns.lance   ──►  PATTERNS.md                          │
│    - Grouped by type (preference, habit, avoidance)          │
│    - Shows confidence & evidence count                       │
│                                                              │
│  policies.lance   ──►  POLICIES.md                          │
│    - Separated: active vs inactive                           │
│    - Shows scope & source                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Should You Still Use MEMORY.md?

**YES.** Here's why:

| Feature | MEMORY.md (v2) | Graph Store (v3) |
|---------|----------------|------------------|
| Human-readable | ✓ Always | ✗ Binary format |
| Git-trackable | ✓ Yes | ✗ No |
| Editable by user | ✓ Yes | ✗ Requires code |
| Works offline | ✓ Yes | ✓ Yes |
| Semantic search | ✗ Keyword only | ✓ Yes |
| Entity extraction | ✗ No | ✓ Automatic |
| Pattern detection | ✗ No | ✓ Automatic |

**The design:** V2 is the source of truth. V3 enhances it with intelligence.

```
User edits MEMORY.md
        │
        ▼
mind_recall() syncs to v3
        │
        ▼
v3 provides semantic search
        │
        ▼
Results shown to Claude
```

## Current Issue: Why Are Views Empty?

The migration from MEMORY.md puts everything in `memories.lance` (general bucket), not in the structured tables. Here's the fix:

```
CURRENT FLOW:
MEMORY.md ──► memories.lance (140 items)
              decisions.lance (1 test item)
              entities.lance (3 test items)

IDEAL FLOW:
MEMORY.md ──► Parse each entry
                  │
                  ├──► Is it a decision? → decisions.lance
                  ├──► Contains entities? → entities.lance
                  ├──► Is it a pattern? → patterns.lance
                  └──► General → memories.lance
```

## Recommended Actions

1. **Keep using MEMORY.md** - It's your human-readable backup
2. **Let v3 enhance search** - Semantic retrieval is automatic
3. **Populate structured tables** - Re-process memories to extract decisions/entities
4. **Use `mind generate-views`** - After structured tables are populated

Would you like me to create a migration that properly populates the structured tables from your existing memories?
