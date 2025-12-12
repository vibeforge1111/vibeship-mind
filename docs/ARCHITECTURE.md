# Mind Architecture

## Overview

Mind is a **context engine**, not a memory database. It maintains structured state across six specialized stores, with intelligent retrieval and session lifecycle management.

```
┌─────────────────────────────────────────────────────────────────┐
│                         MIND                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CONTEXT LAYER (What I Know)                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ Project  │ │ Decision │ │  Issue   │ │  Sharp   │          │
│  │  State   │ │   Log    │ │ Tracker  │ │  Edges   │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│  ┌──────────┐ ┌──────────┐                                     │
│  │ Episode  │ │   User   │                                     │
│  │ Memory   │ │  Model   │                                     │
│  └──────────┘ └──────────┘                                     │
│                                                                 │
│  INTELLIGENCE LAYER (How I Use It)                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Context Engine │ Edge Detector │ Pattern Matcher │ Decay │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  SESSION LAYER (How We Interact)                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │     Primer     │    Context     │     Capture            │  │
│  │   (start)      │   (during)     │     (end)              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  STORAGE LAYER (Where It Lives)                                │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│  │   SQLite     │ │  ChromaDB    │ │    Files     │           │
│  │  (structure) │ │  (vectors)   │ │ (transcripts)│           │
│  └──────────────┘ └──────────────┘ └──────────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Context Layer

Six specialized stores, each with distinct purpose:

#### Project State
Current reality of a project. Not history—the now.

- Current goal
- Active blockers  
- Open threads
- Last session context
- Tech stack

#### Decision Log
Choices with full reasoning chain.

- What was decided
- Why (detailed reasoning)
- Alternatives considered and why rejected
- Confidence level (0.0-1.0)
- Conditions that should trigger revisit
- Links to related issues/edges

#### Issue Tracker
Problems with investigation history.

- Description and severity
- Status lifecycle: open → investigating → blocked → resolved
- Attempted solutions with outcomes
- Current theory
- What we learned from each attempt

#### Sharp Edge Registry
Gotchas with detection patterns.

- Description of the trap
- Detection patterns (code, context, intent)
- Symptoms when you hit it
- Workaround
- Root cause
- Where/when discovered

#### Episode Memory
Narrative of significant sessions.

- What happened (prose, not data)
- Emotional arc (mood shifts)
- Lessons learned
- Breakthroughs and frustrations
- Artifacts created (decisions, issues, edges)

#### User Model
How the human works.

- Communication preferences
- Expertise areas
- Working patterns (pushes through frustration, works late, etc.)
- What works in our collaboration
- Current state (energy, focus, recent wins/frustrations)

### 2. Intelligence Layer

#### Context Engine
Retrieves relevant context for a query.

Not just semantic similarity. Weights by:
- **Recency**: Recent decisions matter more
- **Frequency**: Oft-referenced things matter
- **Relation**: Connected to current project
- **Trigger match**: Explicit trigger phrases
- **Importance**: Some memories more critical

```python
def get_relevant_context(query: str, session: Session) -> Context:
    results = []
    
    # 1. Exact trigger phrase matches (highest priority)
    results += self.match_triggers(query)
    
    # 2. Semantic search with weights
    semantic = self.vectors.search(query, k=20)
    for item in semantic:
        score = item.similarity
        score *= self.recency_weight(item.created_at)
        score *= self.frequency_weight(item.access_count)
        score *= self.relation_weight(item, session.project_id)
        results.append((item, score))
    
    # 3. Return top N, deduplicated
    return self.dedupe_and_rank(results, k=5)
```

#### Edge Detector
Proactively catches sharp edges before mistakes.

```python
def check_edges(code: str, intent: str, context: dict) -> List[Warning]:
    warnings = []
    
    for edge in self.get_active_edges():
        for pattern in edge.detection_patterns:
            if pattern.type == "code" and re.search(pattern.pattern, code):
                warnings.append(Warning(edge, pattern, "high"))
            elif pattern.type == "context" and self.matches_context(pattern, context):
                warnings.append(Warning(edge, pattern, "medium"))
            elif pattern.type == "intent" and self.matches_intent(pattern, intent):
                warnings.append(Warning(edge, pattern, "low"))
                
    return warnings
```

#### Decay Engine
Old, unused memories fade.

Factors preventing decay:
- Recent access
- High importance
- Active links (referenced by other memories)
- Part of active project

Decay thresholds:
- `ARCHIVE_THRESHOLD`: Still searchable, lower priority
- `DELETE_THRESHOLD`: Hidden, recoverable

### 3. Session Layer

#### Session Primer (Start)
Generated when session begins:

```
Last session: [date/time]
Ended with: [summary]
Mood: [observation]
Current goal: [from project state]
Blocked by: [active blockers]
Open decisions: [pending choices]
Active issues: [unresolved problems]

What would you like to focus on?
```

Short. Scannable. Actionable.

#### Context Surfacing (During)
As conversation flows:
- Detect queries that need context
- Retrieve relevant memories
- Surface naturally (not "according to my database...")
- Check sharp edges when writing code

#### Session Capture (End)
When session ends:

```python
def end_session(
    summary: str,
    progress: List[str],
    still_open: List[str],
    next_steps: List[str],
    mood: Optional[str]
) -> SessionCapture:
    # 1. Store session record
    # 2. Update project state
    # 3. Check if qualifies as Episode
    # 4. Trigger any deferred processing
```

### 4. Storage Layer

#### Local Storage (Default)

```
~/.mind/
├── mind.db          # SQLite - structured data
├── chroma/          # ChromaDB - vector embeddings
├── transcripts/     # Session transcripts (optional)
└── exports/         # User exports
```

SQLite schema mirrors data models exactly. ChromaDB stores embeddings for semantic search.

#### Cloud Storage (Optional)

Cloudflare stack:
- **D1**: SQLite at edge (same schema as local!)
- **Vectorize**: Vector embeddings
- **Workers**: Sync API
- **KV**: Sessions, cache
- **R2**: Backups, exports

SQLite-to-SQLite sync is simpler than SQLite-to-Postgres translation.

#### Sync Architecture

```
┌─────────────┐                      ┌─────────────┐
│   Local     │                      │   Cloud     │
│   SQLite    │◄────── Sync ────────►│     D1      │
└─────────────┘                      └─────────────┘
       │                                    │
       │                                    │
       ▼                                    ▼
┌─────────────┐                      ┌─────────────┐
│  ChromaDB   │◄────── Sync ────────►│  Vectorize  │
└─────────────┘                      └─────────────┘
```

Sync strategy:
1. Track changes locally with timestamps
2. Push changes to cloud on sync
3. Pull remote changes
4. Resolve conflicts (last-write-wins)
5. All data encrypted before leaving device

## File Structure

```
mind/
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── project.py
│   │   ├── decision.py
│   │   ├── issue.py
│   │   ├── sharp_edge.py
│   │   ├── episode.py
│   │   ├── user.py
│   │   └── session.py
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── local.py          # SQLite + ChromaDB
│   │   ├── cloud.py          # Cloudflare D1 + Vectorize
│   │   ├── sync.py           # Sync engine
│   │   └── embeddings.py     # Embedding generation
│   │
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── context.py        # Context retrieval
│   │   ├── detection.py      # Sharp edge detection
│   │   ├── decay.py          # Memory decay
│   │   └── session.py        # Session lifecycle
│   │
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── server.py         # MCP server
│   │   └── tools.py          # Tool implementations
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── server.py         # HTTP API (optional)
│   │
│   └── cli/
│       ├── __init__.py
│       └── main.py           # CLI commands
│
├── data/                      # Default local data
├── tests/
├── docs/
├── pyproject.toml
├── CLAUDE.md
└── README.md
```

## Data Flow

### Starting a Session

```
1. User: "Let's work on spawner"

2. Claude calls: mind_start_session(project="spawner")

3. Mind:
   a. Load project state
   b. Load last session
   c. Find open issues, pending decisions
   d. Check for triggered revisit conditions
   e. Generate primer

4. Return primer to Claude

5. Claude: "Last session you were debugging the webhook 
   timeout. Did moving to serverless fix that?"
```

### Surfacing Context

```
1. User: "Why are we using Supabase?"

2. Claude calls: mind_get_context(query="supabase decision")

3. Mind:
   a. Match trigger phrases
   b. Semantic search across decisions
   c. Weight by recency, relevance
   d. Return top matches

4. Return: Decision with full reasoning + alternatives

5. Claude: "We chose Supabase in October because Vercel 
   Edge times out at 10s and our webhooks need 30s+. 
   We considered Cloudflare Workers but needed native Postgres."
```

### Detecting Sharp Edges

```
1. Claude about to write: crypto.randomUUID() in edge function

2. Claude calls: mind_check_edges(
     code="crypto.randomUUID()",
     context={"runtime": "edge"}
   )

3. Mind:
   a. Run detection patterns
   b. Match: "crypto" + "edge" pattern
   c. Return warning with workaround

4. Claude: "Wait—Edge functions can't use Node crypto. 
   Let me use Web Crypto API instead..."
```

### Ending a Session

```
1. User: "Good for today"

2. Claude calls: mind_end_session(
     summary="Resolved webhook timeout",
     progress=["Moved to serverless", "Added retry logic"],
     still_open=["Error handling edge cases"],
     next_steps=["Add dead letter queue"],
     mood="Productive"
   )

3. Mind:
   a. Store session record
   b. Update project state
   c. Check if Episode-worthy
   d. Update user model if patterns noticed

4. Claude: "Captured. Good progress on webhooks. 
   Next time: dead letter queue. See you."
```

## Security Model

### Local Storage
- Data never leaves device
- No network calls (unless sync enabled)
- Standard file permissions

### Cloud Sync
- End-to-end encryption
- Key derived from user password
- Cloud sees only encrypted blobs
- We cannot read your data

### Sharp Edge Registry
- Submission is optional
- Edges anonymized before sharing
- Community verification
- No project-specific data exposed

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Session start | <500ms | Primer generation |
| Context query | <200ms | Semantic search |
| Edge check | <100ms | Pattern matching |
| Session end | <1s | Can defer Episode extraction |
| Sync | <5s | Typical delta sync |

Critical path is session start and context queries. These must be fast or conversation flow breaks.
