# Mind v3: The Context Graph Architecture

> A system of record for decisions, not just objects.

## Executive Summary

Mind v3 transforms from a passive memory system into an **intelligent context graph** - capturing not just what happened, but *why* it was allowed to happen. This positions Mind as infrastructure for the next generation of AI agents: a queryable record of decision traces that enables progressive autonomy, tribal knowledge capture, and enterprise-scale precedent reasoning.

**The core insight:** AI agents don't just need data - they need access to the decision traces that show how rules were applied, where exceptions were granted, and which precedents actually govern reality.

---

## Table of Contents

1. [Vision](#1-vision)
2. [Architecture Overview](#2-architecture-overview)
3. [Four-Layer Processing Pipeline](#3-four-layer-processing-pipeline)
4. [Configurable Intelligence](#4-configurable-intelligence)
5. [The Context Graph Schema](#5-the-context-graph-schema)
6. [Cognitive Memory System](#6-cognitive-memory-system)
7. [Progressive Autonomy](#7-progressive-autonomy)
8. [Technology Choices](#8-technology-choices)
9. [File Structure](#9-file-structure)
10. [Enterprise Features](#10-enterprise-features)
11. [Implementation Roadmap](#11-implementation-roadmap)

---

## 1. Vision

### The Problem

Current AI assistants have no memory. Each session starts fresh. Even with explicit logging:
- SESSION.md almost never gets used
- MEMORY.md gets rarely populated
- Key decisions are lost
- Context utilization is minimal

### The Insight

From the viral article "Systems of Record, Reimagined" (1M+ views, Dec 2025):

> "Rules tell an agent what should happen in general. Decision traces capture what happened in this specific case - the exceptions, overrides, precedents, and cross-system context that currently live in people's heads."

Mind sits in the execution path. Every Claude Code session flows through transcripts we can capture. We're not bolting on memory after the fact - we're **in the path**.

### The Vision

Mind becomes a **system of record for AI decisions**:

```
What exists today:              What Mind v3 enables:
─────────────────────           ─────────────────────
"20% discount applied"    →     "20% discount applied because:
                                 - Policy allows 10% max
                                 - Exception granted due to 3 SEV-1 incidents
                                 - Precedent: similar exception for Client X in Q3
                                 - Approved by: user on 2025-12-25
                                 - Outcome: successful (client renewed)"
```

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MIND v3 ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    CAPTURE LAYER (Always-On)                        │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │   │
│  │  │ Transcript  │───▶│   Event     │───▶│   Event     │             │   │
│  │  │  Watcher    │    │  Extractor  │    │   Store     │             │   │
│  │  └─────────────┘    └─────────────┘    └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                   INTELLIGENCE LAYER (Configurable)                 │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │   │
│  │  │   Model     │───▶│  Decision   │───▶│  Context    │             │   │
│  │  │  Cascade    │    │  Extractor  │    │   Graph     │             │   │
│  │  │ (Local→API) │    │             │    │  Builder    │             │   │
│  │  └─────────────┘    └─────────────┘    └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     STORAGE LAYER (LanceDB)                         │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │   │
│  │  │ Decisions   │    │  Entities   │    │  Patterns   │             │   │
│  │  │             │    │             │    │             │             │   │
│  │  └─────────────┘    └─────────────┘    └─────────────┘             │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │   │
│  │  │  Policies   │    │ Exceptions  │    │ Precedents  │             │   │
│  │  │             │    │             │    │             │             │   │
│  │  └─────────────┘    └─────────────┘    └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    RETRIEVAL LAYER (Per-Prompt)                     │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │   │
│  │  │   Hybrid    │───▶│  Reranking  │───▶│  Context    │             │   │
│  │  │   Search    │    │             │    │  Injection  │             │   │
│  │  └─────────────┘    └─────────────┘    └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    AUTONOMY LAYER (Learning)                        │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │   │
│  │  │ Confidence  │───▶│ Progressive │───▶│  Feedback   │             │   │
│  │  │  Scoring    │    │  Autonomy   │    │    Loop     │             │   │
│  │  └─────────────┘    └─────────────┘    └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Four-Layer Processing Pipeline

### Layer 1: Local Capture (Always-On, Free)

**Purpose:** Capture every event in real-time, zero cost.

```
Transcript files (~/.claude/projects/*/chat_*.jsonl)
                    │
                    ▼
            ┌───────────────┐
            │ File Watcher  │  (watchdog library)
            │  <1s latency  │
            └───────────────┘
                    │
                    ▼
            ┌───────────────┐
            │ Event Parser  │  (decode base64, extract turns)
            └───────────────┘
                    │
                    ▼
            ┌───────────────┐
            │ Local Extract │  (regex, keywords, heuristics)
            │ - Tool calls  │
            │ - Errors      │
            │ - File changes│
            │ - Keywords    │
            └───────────────┘
                    │
                    ▼
            ┌───────────────┐
            │ Event Store   │  (append-only, immutable)
            │ .jsonl files  │
            └───────────────┘
```

**Keywords detected locally:**
- Decisions: "decided", "chose", "going with", "using", "settled on"
- Problems: "error", "bug", "issue", "doesn't work", "failed"
- Learnings: "learned", "discovered", "realized", "turns out", "TIL"
- Rejections: "tried", "didn't work", "rejected", "too complex"

### Layer 2: AI Synthesis (Configurable Frequency)

**Purpose:** Extract meaning, build relationships, understand "why".

```
Event Store
     │
     ▼
┌─────────────────────────────────────────────────┐
│              MODEL CASCADE                       │
├─────────────────────────────────────────────────┤
│                                                 │
│  Tier 1: Local Models (free, instant)           │
│  ├── phi-3-mini, gemma-2-2b                     │
│  ├── Classification: "Is this a decision?"     │
│  ├── Entity extraction (NER)                   │
│  └── Simple pattern matching                   │
│                                                 │
│  Tier 2: Fast API (cheap, quick)                │
│  ├── Claude Haiku, GPT-4o-mini                  │
│  ├── Decision trace extraction                 │
│  ├── Reasoning capture                         │
│  └── Entity relationship mapping               │
│                                                 │
│  Tier 3: Powerful API (smart, periodic)         │
│  ├── Claude Sonnet/Opus                         │
│  ├── Deep synthesis across sessions            │
│  ├── Complex precedent reasoning               │
│  └── Generalization & pattern discovery        │
│                                                 │
└─────────────────────────────────────────────────┘
     │
     ▼
Context Graph (LanceDB)
```

**Routing Logic:**
```python
def route_to_model(event):
    if is_simple_classification(event):
        return "local"  # Free, instant
    elif needs_understanding(event):
        return "haiku"  # ~$0.001 per extraction
    elif needs_deep_reasoning(event):
        return "sonnet"  # ~$0.01 per synthesis
```

### Layer 3: Retrieval (Per-Prompt)

**Purpose:** Find relevant context for the current moment.

```
User sends message
        │
        ▼
┌───────────────────────────────────────────────────┐
│           UserPromptSubmit Hook                   │
└───────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────┐
│  STEP 1: Query Expansion                          │
│  ├── Original: "fix the auth bug"                │
│  ├── Expanded: "authentication", "login",        │
│  │   "token", "session", "401", "security"       │
│  └── Method: Local embeddings or Haiku           │
└───────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────┐
│  STEP 2: Hybrid Search                            │
│  ├── Dense vectors (semantic similarity)          │
│  ├── Sparse BM25 (keyword matching)               │
│  └── Merge with RRF (Reciprocal Rank Fusion)     │
└───────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────┐
│  STEP 3: Reranking                                │
│  ├── Cross-encoder scores query vs results        │
│  ├── Model: Cohere Rerank or local cross-encoder │
│  └── Output: Top-K perfectly ranked              │
└───────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────┐
│  STEP 4: Context Injection                        │
│  ├── Format relevant context                      │
│  ├── Add to user's prompt                         │
│  └── Claude sees: message + relevant history     │
└───────────────────────────────────────────────────┘
```

### Layer 4: Memory Management (Background)

**Purpose:** Keep the graph healthy, relevant, and performant.

```
┌─────────────────────────────────────────────────────────────┐
│                    MEMORY PROCESSES                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  REINFORCEMENT                                              │
│  ├── Track usage of each memory                             │
│  ├── Frequently retrieved → higher weight                   │
│  ├── Successfully used → boost confidence                   │
│  └── Positive feedback → reinforce pattern                  │
│                                                             │
│  DECAY                                                      │
│  ├── Unused memories lose weight over time                  │
│  ├── Configurable decay curves                              │
│  ├── Never deleted, just deprioritized                      │
│  └── Can be resurrected by relevance                        │
│                                                             │
│  CONSOLIDATION (nightly/weekly)                             │
│  ├── Episodes → Semantic memory                             │
│  ├── Specific decisions → General patterns                  │
│  ├── "You chose X three times" → "You prefer X"            │
│  └── Compress while preserving meaning                      │
│                                                             │
│  PRUNING                                                    │
│  ├── Archive old, low-relevance items                       │
│  ├── Keep graph query performance high                      │
│  └── Archived items still searchable                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Configurable Intelligence

### The Settings Panel

Users control intelligence per-feature, like game graphics settings:

```
┌─────────────────────────────────────────────────────────────┐
│                   MIND INTELLIGENCE SETTINGS                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  CAPTURE                                                    │
│  How thoroughly Mind records what happens                   │
│  ○ Local    ○ Low    ● Medium    ○ High    ○ Ultra         │
│  ├─────────────────────●───────────────────────┤            │
│                                                             │
│  DECISIONS                                                  │
│  How deeply Mind understands why you chose something        │
│  ○ Local    ○ Low    ○ Medium    ○ High    ● Ultra         │
│  ├───────────────────────────────────────────●─┤            │
│                                                             │
│  PATTERNS                                                   │
│  How well Mind detects recurring behaviors & preferences    │
│  ○ Local    ○ Low    ● Medium    ○ High    ○ Ultra         │
│  ├─────────────────────●───────────────────────┤            │
│                                                             │
│  RETRIEVAL                                                  │
│  How smart Mind is at finding relevant context              │
│  ○ Local    ○ Low    ○ Medium    ● High    ○ Ultra         │
│  ├─────────────────────────────●───────────────┤            │
│                                                             │
│  PRECEDENTS                                                 │
│  How well Mind links current situation to past decisions    │
│  ○ Local    ○ Low    ○ Medium    ○ High    ● Ultra         │
│  ├───────────────────────────────────────────●─┤            │
│                                                             │
│  SYNTHESIS                                                  │
│  How often Mind summarizes & connects learnings             │
│  ○ Local    ● Low    ○ Medium    ○ High    ○ Ultra         │
│  ├───────●─────────────────────────────────────┤            │
│                                                             │
│  DECAY                                                      │
│  How intelligently Mind forgets irrelevant memories         │
│  ○ Local    ○ Low    ● Medium    ○ High    ○ Ultra         │
│  ├─────────────────────●───────────────────────┤            │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Estimated monthly cost: ~$12    Tokens: ~1.2M              │
│  [Presets ▾]  [Save]  [Reset to defaults]                   │
└─────────────────────────────────────────────────────────────┘
```

### Intelligence Levels Explained

| Level | Method | Cost | Speed | Intelligence |
|-------|--------|------|-------|--------------|
| **Local** | Regex, heuristics, local models | $0 | Instant | Basic |
| **Low** | + Light NLP, basic embeddings | ~$1/mo | Fast | Good |
| **Medium** | + AI batched (Haiku) | ~$5/mo | Moderate | Better |
| **High** | + AI frequent (Sonnet) | ~$15/mo | Slower | Great |
| **Ultra** | + Real-time AI (Opus) | ~$30+/mo | Variable | Maximum |

### Presets

```yaml
presets:
  free:        # $0/mo - All local
    capture: local
    decisions: local
    patterns: local
    retrieval: local
    precedents: local
    synthesis: local
    decay: local

  lite:        # ~$3/mo
    capture: medium
    decisions: low
    patterns: low
    retrieval: medium
    precedents: low
    synthesis: local
    decay: low

  balanced:    # ~$10/mo
    capture: medium
    decisions: medium
    patterns: medium
    retrieval: medium
    precedents: medium
    synthesis: low
    decay: medium

  decision-max: # ~$15/mo - Focus on decisions
    capture: medium
    decisions: ultra
    patterns: medium
    retrieval: high
    precedents: ultra
    synthesis: low
    decay: medium

  pro:         # ~$25/mo
    capture: high
    decisions: high
    patterns: high
    retrieval: high
    precedents: high
    synthesis: medium
    decay: high

  enterprise:  # ~$50+/mo
    capture: ultra
    decisions: ultra
    patterns: ultra
    retrieval: ultra
    precedents: ultra
    synthesis: high
    decay: ultra
```

### Configuration File

```yaml
# .mind/config.yaml

intelligence:
  # Use a preset
  preset: "decision-max"

  # Or customize individual features
  custom:
    capture: medium
    decisions: ultra
    patterns: medium
    retrieval: high
    precedents: ultra
    synthesis: low
    decay: medium

  # Budget controls
  budget:
    monthly_cap_tokens: 1500000
    monthly_cap_dollars: 15
    warn_at_percent: 80
    pause_at_cap: true  # or "downgrade" to lower tier

  # Model preferences
  models:
    local: "phi-3-mini"          # For local inference
    fast: "claude-haiku"          # For quick API calls
    powerful: "claude-sonnet"     # For deep reasoning
    embedding: "voyage-code-2"    # For code understanding
    reranker: "cohere-rerank-v3"  # For retrieval reranking
```

---

## 5. The Context Graph Schema

### Overview

The Context Graph is a **knowledge graph optimized for decision traces**:

```
┌─────────────────────────────────────────────────────────────────┐
│                     THE CONTEXT GRAPH                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│    ┌──────────┐         decides          ┌──────────┐          │
│    │  ENTITY  │◄────────────────────────►│ DECISION │          │
│    └──────────┘                          └──────────┘          │
│         │                                      │               │
│         │ relates_to                           │ based_on      │
│         ▼                                      ▼               │
│    ┌──────────┐         follows          ┌──────────┐          │
│    │  POLICY  │◄────────────────────────►│ EXCEPTION│          │
│    └──────────┘                          └──────────┘          │
│         │                                      │               │
│         │ has_pattern                          │ creates       │
│         ▼                                      ▼               │
│    ┌──────────┐         informs          ┌──────────┐          │
│    │ PATTERN  │◄────────────────────────►│PRECEDENT │          │
│    └──────────┘                          └──────────┘          │
│         │                                      │               │
│         │ predicts                             │ leads_to      │
│         ▼                                      ▼               │
│    ┌──────────┐                          ┌──────────┐          │
│    │ AUTONOMY │◄─────── feedback ───────►│ OUTCOME  │          │
│    └──────────┘                          └──────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Node Types

#### 1. DECISION (The Core)

Every meaningful choice captured with full context:

```yaml
Decision:
  id: "dec_20251225_143052_abc123"
  timestamp: "2025-12-25T14:30:52Z"
  session_id: "sess_20251225_140000"

  # What was decided
  action: "Used SQLite instead of PostgreSQL for storage"
  action_type: "technology_choice"  # or: approach, fix, refactor, etc.

  # Why (THE GOLD - this is what systems don't capture)
  reasoning: |
    Need portability, single-file, no server dependency.
    PostgreSQL would require Docker setup.
    JSON files considered but lack query capability.
    SQLite is the sweet spot for local-first tools.

  # Context snapshot at decision time
  context:
    goal: "Implement persistent storage for Mind"
    constraints:
      - "Must work offline"
      - "No external server dependencies"
      - "Should be portable across machines"
    files_involved:
      - path: "src/storage.py"
        action: "created"
      - path: "config.yaml"
        action: "modified"

  # Alternatives considered (shows reasoning depth)
  alternatives:
    - option: "PostgreSQL"
      considered: true
      rejected: true
      reason: "Requires server, not portable"
    - option: "JSON files"
      considered: true
      rejected: true
      reason: "No query capability, slow at scale"
    - option: "MongoDB"
      considered: false
      reason: "Never came up"

  # Policy context
  policy_context:
    policy_id: "pol_minimize_dependencies"
    compliant: true
    exception_required: false

  # Links
  entities: ["ent_storage_module", "ent_sqlite"]
  patterns: ["pat_prefer_simple_deps"]
  precedents: ["dec_20251115_092030"]  # Similar past decision
  outcome: "out_20251225_143100"

  # Metadata
  confidence: 0.92
  importance: 0.85
  times_referenced: 5
  last_referenced: "2025-12-25T18:00:00Z"

  # Embedding for semantic search
  embedding: [0.123, 0.456, ...]  # Stored in LanceDB
```

#### 2. ENTITY (Things in Your World)

```yaml
Entity:
  id: "ent_storage_module"
  type: "code_module"  # file, function, concept, error, person, tool
  name: "Storage Module"

  # Description (evolves over time)
  description: "Handles persistence layer for Mind using SQLite"

  # Properties (type-specific)
  properties:
    path: "src/mind/storage.py"
    language: "python"
    lines_of_code: 245
    created: "2025-11-01"
    last_modified: "2025-12-25"

  # Knowledge about this entity
  facts:
    - "Uses SQLite with WAL mode"
    - "Has transaction support"
    - "Handles concurrent access"

  # Gotchas (problems encountered)
  gotchas:
    - "Must close connections explicitly"
    - "WAL mode required for concurrent reads"

  # Links
  decisions_about: ["dec_20251225_143052", "dec_20251226_091000"]
  related_entities: ["ent_sqlite", "ent_lancedb"]
  patterns: ["pat_always_use_transactions"]

  # Metadata
  importance: 0.9
  last_touched: "2025-12-25T14:30:52Z"
```

#### 3. POLICY (Rules & Guidelines)

```yaml
Policy:
  id: "pol_code_style"
  name: "Code Style Guidelines"
  type: "guideline"  # or: rule, preference, constraint

  # The rules
  rules:
    - id: "rule_001"
      text: "Use functional style over OOP"
      strictness: "prefer"  # must, should, prefer
    - id: "rule_002"
      text: "No classes unless necessary"
      strictness: "should"
    - id: "rule_003"
      text: "Prefer immutability"
      strictness: "prefer"

  # Source
  source: "inferred"  # or: explicit, imported
  created: "2025-12-01"
  version: "1.2"

  # Stats (how often followed vs overridden)
  stats:
    times_followed: 45
    times_overridden: 3
    override_rate: 0.0625

  # Links
  decisions_following: ["dec_001", "dec_002", ...]
  exceptions: ["exc_001", "exc_002"]
```

#### 4. EXCEPTION (Tribal Knowledge)

```yaml
Exception:
  id: "exc_20251225_001"
  timestamp: "2025-12-25T15:00:00Z"

  # What rule was bent
  policy_id: "pol_code_style"
  rule_violated: "rule_002"  # "No classes unless necessary"

  # The exception
  description: "Used a class instead of functions"
  reason: "State management was too complex for pure functions"

  # Context
  decision_id: "dec_20251225_150000"
  files_affected: ["src/mind/graph.py"]

  # Approval
  approved_by: "user"
  approval_method: "explicit"  # or: implicit, precedent

  # Does this become a pattern?
  creates_precedent: true
  precedent_conditions:
    - "Complex state management required"
    - "Multiple methods need shared state"
  precedent_description: "Classes are acceptable for complex state management"
```

#### 5. PATTERN (Learned Behaviors)

```yaml
Pattern:
  id: "pat_prefers_functional"
  type: "preference"  # habit, blind_spot, anti_pattern, workflow

  # What the pattern is
  description: "User prefers functional programming style over OOP"

  # Evidence (why Mind believes this)
  evidence:
    - decision_id: "dec_20251220_..."
      signal: "Chose map/filter over for-loop"
      weight: 0.3
    - decision_id: "dec_20251218_..."
      signal: "Refactored class to pure functions"
      weight: 0.5
    - decision_id: "dec_20251210_..."
      signal: "Asked for immutable data structures"
      weight: 0.2

  # Confidence (strengthens with evidence)
  confidence: 0.87
  evidence_count: 12

  # When to surface this
  triggers:
    - "writing new code"
    - "refactoring"
    - "code review"

  # Autonomy level for this pattern
  autonomy_level: 3  # Ask permission (see Progressive Autonomy)

  # Counter-evidence (times pattern was wrong)
  counter_evidence:
    - decision_id: "exc_20251225_001"
      signal: "Chose class over functions"
      reason: "Complex state management"
```

#### 6. PRECEDENT (Links Between Decisions)

```yaml
Precedent:
  id: "prec_20251225_001"

  # The link
  source_decision: "dec_20251225_143052"  # Current decision
  target_decision: "dec_20251115_092030"  # Past decision

  # Why they're linked
  similarity_type: "same_problem"  # same_approach, same_entity, same_outcome
  similarity_score: 0.89

  # What makes them similar
  shared_context:
    - "Both about choosing storage technology"
    - "Both prioritized portability"
    - "Both rejected heavy dependencies"

  # The insight
  insight: "When portability matters, SQLite > PostgreSQL > JSON files"

  # Was this precedent useful?
  was_helpful: true
  feedback: "Applied same approach successfully"
```

#### 7. OUTCOME (What Actually Happened)

```yaml
Outcome:
  id: "out_20251225_143100"
  decision_id: "dec_20251225_143052"

  # Result
  result: "success"  # failure, partial, unknown

  # What actually happened
  description: |
    SQLite worked perfectly. 10x faster than JSON approach.
    No issues with portability. WAL mode handles concurrent access.

  # Learnings extracted
  learnings:
    - "SQLite is ideal for local-first tools"
    - "WAL mode essential for concurrent access"
    - "Single-file databases simplify deployment"

  # Problems encountered
  problems: []

  # Metrics (if measurable)
  metrics:
    performance_improvement: "10x"
    bugs_caused: 0
    refactors_needed: 0

  # Feedback loop
  reinforces_patterns: ["pat_prefer_simple_deps"]
  weakens_patterns: []
  spawned_decisions: ["dec_20251226_..."]  # Follow-up decisions

  # Timestamp
  observed_at: "2025-12-26T10:00:00Z"
```

#### 8. AUTONOMY (Confidence Tracking)

```yaml
Autonomy:
  id: "auto_technology_choice"
  decision_type: "technology_choice"

  # Current autonomy level
  level: 3  # 1-5 scale
  level_name: "ask_permission"

  # Confidence metrics
  total_decisions: 15
  successful_decisions: 14
  success_rate: 0.93

  # Level history
  level_history:
    - level: 1
      from: "2025-11-01"
      to: "2025-11-15"
      decisions: 3
    - level: 2
      from: "2025-11-15"
      to: "2025-12-01"
      decisions: 5
    - level: 3
      from: "2025-12-01"
      to: null  # Current
      decisions: 7

  # Promotion criteria
  promotion_threshold:
    required_decisions: 10
    required_success_rate: 0.95

  # Demotion triggers
  demotion_triggers:
    - "3 consecutive overrides"
    - "Success rate drops below 0.8"
    - "User explicitly demotes"
```

---

## 6. Cognitive Memory System

Mind implements a cognitively-inspired memory architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                   COGNITIVE MEMORY SYSTEM                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  WORKING MEMORY (current session)                               │
│  ├── Limited capacity (~10-20 active items)                     │
│  ├── What you're focused on right now                           │
│  ├── Recent tool calls, errors, decisions                       │
│  └── Fades when session ends → promotes important items         │
│                                                                 │
│  EPISODIC MEMORY (specific events)                              │
│  ├── "On Dec 25, we fixed the auth bug by..."                   │
│  ├── Time-stamped, contextual, replayable                       │
│  ├── Linked to entities, decisions, outcomes                    │
│  └── Source for pattern extraction                              │
│                                                                 │
│  SEMANTIC MEMORY (generalized knowledge)                        │
│  ├── "SQLite is good for portable apps"                         │
│  ├── Extracted from many episodes                               │
│  ├── Abstract, timeless, high-confidence                        │
│  └── Policies, patterns, preferences                            │
│                                                                 │
│  PROCEDURAL MEMORY (how to do things)                           │
│  ├── "When deploying, always run tests first"                   │
│  ├── Learned workflows and sequences                            │
│  ├── Automatic, triggered by context                            │
│  └── Can reach high autonomy levels                             │
│                                                                 │
│  PROSPECTIVE MEMORY (future intentions)                         │
│  ├── Reminders, todos, scheduled reviews                        │
│  ├── "Next time you touch auth, remember X"                     │
│  ├── Context-triggered notifications                            │
│  └── Time-triggered notifications                               │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                     MEMORY PROCESSES                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ENCODING: Event → Working Memory                               │
│  ├── Capture raw events from transcripts                        │
│  ├── Extract structured data                                    │
│  └── Assign initial importance                                  │
│                                                                 │
│  CONSOLIDATION: Episodic → Semantic                             │
│  ├── "You did X three times" → "You prefer X"                  │
│  ├── Extract patterns from episodes                             │
│  ├── Build semantic understanding                               │
│  └── Runs during low-activity periods                           │
│                                                                 │
│  RETRIEVAL: Query → Relevant Memories                           │
│  ├── Semantic search (embeddings)                               │
│  ├── Keyword search (BM25)                                      │
│  ├── Graph traversal (relationships)                            │
│  └── Reranking (relevance scoring)                              │
│                                                                 │
│  DECAY: Active → Dormant                                        │
│  ├── Unused memories lose activation                            │
│  ├── Can be reactivated by relevance                            │
│  ├── Eventually archived (not deleted)                          │
│  └── Importance modulates decay rate                            │
│                                                                 │
│  REINFORCEMENT: Use → Strengthen                                │
│  ├── Retrieved memories gain activation                         │
│  ├── Correct predictions boost confidence                       │
│  ├── Positive feedback reinforces patterns                      │
│  └── Forms stable long-term memories                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Progressive Autonomy

Mind earns trust through demonstrated good judgment:

```
┌─────────────────────────────────────────────────────────────────┐
│                 PROGRESSIVE AUTONOMY LADDER                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  LEVEL 1: RECORD ONLY                                           │
│  ├── Mind observes and captures                                 │
│  ├── Human makes all decisions                                  │
│  ├── "I don't know this pattern yet"                            │
│  └── Trigger: New situation, no precedent                       │
│                                                                 │
│  LEVEL 2: SUGGEST                                               │
│  ├── Mind suggests based on precedent                           │
│  ├── "Last time you did X, want to do that again?"              │
│  ├── Human decides                                              │
│  └── Trigger: Similar situation seen 2-3 times                  │
│                                                                 │
│  LEVEL 3: ASK PERMISSION                                        │
│  ├── Mind proposes specific action                              │
│  ├── "I'm 85% sure we should do X. Proceed?"                    │
│  ├── Human confirms or overrides                                │
│  └── Trigger: Pattern with 80%+ confidence                      │
│                                                                 │
│  LEVEL 4: ACT + NOTIFY                                          │
│  ├── Mind acts automatically                                    │
│  ├── "I did X based on precedent Y"                             │
│  ├── Human can undo if wrong                                    │
│  └── Trigger: Pattern with 90%+ confidence, 10+ instances       │
│                                                                 │
│  LEVEL 5: SILENT                                                │
│  ├── Mind handles automatically                                 │
│  ├── Only logs for audit                                        │
│  ├── Human doesn't see unless they look                         │
│  └── Trigger: Pattern with 95%+ confidence, 20+ instances       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PROMOTION CRITERIA:                                            │
│  ├── N successful decisions at current level                    │
│  ├── Success rate above threshold                               │
│  ├── No recent overrides                                        │
│  └── Time at current level                                      │
│                                                                 │
│  DEMOTION TRIGGERS:                                             │
│  ├── User overrides Mind's action                               │
│  ├── Decision leads to bad outcome                              │
│  ├── User explicitly reduces trust                              │
│  └── Context shift (new project, new domain)                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Autonomy Configuration

```yaml
# .mind/config.yaml

autonomy:
  enabled: true
  max_level: 4  # Never go fully silent

  # Per-category settings
  categories:
    code_style:
      max_level: 5
      promotion_threshold: 10
      success_rate_required: 0.9
    technology_choice:
      max_level: 3  # Always ask for big decisions
      promotion_threshold: 15
      success_rate_required: 0.95
    bug_fix:
      max_level: 4
      promotion_threshold: 8
      success_rate_required: 0.85

  # Safety rails
  safety:
    always_ask_for:
      - "production deployments"
      - "data migrations"
      - "security changes"
    never_automate:
      - "deleting files"
      - "git push to main"
```

---

## 8. Technology Choices

### Storage: LanceDB

**Why LanceDB over SQLite + vectors:**

| Criteria | SQLite + sqlite-vec | LanceDB |
|----------|---------------------|---------|
| Vector search | Bolted on | Native |
| Performance at scale | Degrades | Optimized |
| Multimodal | No | Yes |
| Used by | Small projects | Midjourney, Runway, Character.ai |
| File-based | Yes | Yes |
| Serverless | Yes | Yes |

**LanceDB is battle-tested:**
- Midjourney: Billions of vectors
- Runway: Petabyte-scale training data
- $30M Series A (June 2025)

### Embeddings: Specialized Models

| Use Case | Model | Why |
|----------|-------|-----|
| Code | `voyage-code-2` | Trained on code, understands syntax |
| Decisions | `voyage-large-2` | Better semantic similarity |
| Hybrid | `BGE-M3` | Dense + sparse in one |
| Local/free | `nomic-embed-text` | Good quality, runs locally |

### Retrieval: Hybrid + Reranking

```
Query
  │
  ├──► Dense vectors (semantic)
  │
  ├──► Sparse BM25 (keywords)
  │
  └──► Merge with RRF
         │
         ▼
      Rerank with cross-encoder
         │
         ▼
      Top-K results
```

### Local Models (for free tier)

| Task | Model | Size |
|------|-------|------|
| Classification | `phi-3-mini` | 3.8B |
| Extraction | `gemma-2-2b` | 2B |
| Embeddings | `nomic-embed-text` | 137M |

---

## 9. File Structure

```
.mind/
├── config.yaml                 # Intelligence settings, autonomy config
│
├── graph/                      # LanceDB tables
│   ├── decisions.lance/        # All decisions
│   ├── entities.lance/         # All entities
│   ├── patterns.lance/         # All patterns
│   ├── policies.lance/         # All policies
│   ├── exceptions.lance/       # All exceptions
│   ├── precedents.lance/       # All precedent links
│   ├── outcomes.lance/         # All outcomes
│   └── autonomy.lance/         # Autonomy tracking
│
├── events/                     # Raw event store (append-only)
│   ├── 2025-12-25.jsonl
│   ├── 2025-12-26.jsonl
│   └── ...
│
├── views/                      # Human-readable exports (generated)
│   ├── MEMORY.md               # Summary for humans
│   ├── DECISIONS.md            # Recent decisions
│   ├── PATTERNS.md             # Learned patterns
│   └── POLICIES.md             # Active policies
│
├── archive/                    # Old, low-relevance items
│   └── ...
│
└── cache/                      # Temporary files
    ├── embeddings/             # Cached embeddings
    └── synthesis/              # Pending synthesis batches
```

---

## 10. Enterprise Features

### Multi-Level Graphs

```
┌─────────────────────────────────────────────────────────────────┐
│                     KNOWLEDGE LEVELS                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PERSONAL GRAPH (individual)                                    │
│  ├── Your decisions, patterns, preferences                      │
│  ├── Your projects                                              │
│  └── Private by default                                         │
│                                                                 │
│  PROJECT GRAPH (codebase)                                       │
│  ├── Decisions about this codebase                              │
│  ├── Architecture patterns                                      │
│  └── Shared with project collaborators                          │
│                                                                 │
│  TEAM GRAPH (organization)                                      │
│  ├── Team-wide patterns and policies                            │
│  ├── Shared precedents                                          │
│  ├── "How we do things here"                                    │
│  └── Onboarding accelerator                                     │
│                                                                 │
│  GLOBAL GRAPH (anonymized)                                      │
│  ├── "Most Python projects do X"                                │
│  ├── Common patterns across all users                           │
│  ├── Privacy-preserving aggregation                             │
│  └── Powers smarter defaults                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Enterprise Features

| Feature | Description |
|---------|-------------|
| **Team Sync** | Share patterns, policies across team |
| **SSO/SAML** | Enterprise authentication |
| **Audit Logs** | Immutable record of all decisions |
| **Compliance** | SOC2, GDPR support |
| **On-Prem** | Self-hosted deployment |
| **API Access** | Query graph from other tools |
| **Role-Based Access** | Control who sees what |
| **Retention Policies** | Configurable data retention |

### Decision Observability Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│              DECISION QUALITY DASHBOARD                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  OVERVIEW                               Last 30 days            │
│  ├── Total decisions: 247                                       │
│  ├── Success rate: 91%                                          │
│  ├── Patterns discovered: 12                                    │
│  └── Autonomy level avg: 2.8                                    │
│                                                                 │
│  PATTERN PERFORMANCE                                            │
│  ├── "Prefer SQLite" ────────────────────── 95% ✓               │
│  ├── "Use functional style" ─────────────── 92% ✓               │
│  ├── "Skip tests for prototypes" ────────── 60% ⚠               │
│  └── "Always use TypeScript" ────────────── 88% ✓               │
│                                                                 │
│  AUTONOMY PROGRESSION                                           │
│  ├── Level 5: ████████ 45 patterns                              │
│  ├── Level 4: ██████ 23 patterns                                │
│  ├── Level 3: ████ 15 patterns                                  │
│  ├── Level 2: ███ 12 patterns                                   │
│  └── Level 1: █ 5 patterns                                      │
│                                                                 │
│  RECENT ISSUES                                                  │
│  ├── "Skip tests" pattern has 40% failure rate                 │
│  ├── 3 overrides in "deployment" category                       │
│  └── New domain detected: "machine learning"                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 11. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Event sourcing architecture
- [ ] Transcript file watcher
- [ ] Basic event extraction (local, regex)
- [ ] LanceDB integration
- [ ] Decision node schema

### Phase 2: Intelligence (Weeks 3-4)
- [ ] Model cascade implementation
- [ ] Decision trace extraction (AI-powered)
- [ ] Entity extraction
- [ ] Basic pattern detection
- [ ] Configurable intelligence levels

### Phase 3: Retrieval (Weeks 5-6)
- [ ] Embedding generation
- [ ] Hybrid search (dense + sparse)
- [ ] Reranking integration
- [ ] UserPromptSubmit hook
- [ ] Context injection

### Phase 4: Autonomy (Weeks 7-8)
- [ ] Confidence tracking
- [ ] Progressive autonomy levels
- [ ] Outcome tracking
- [ ] Feedback loops
- [ ] Pattern reinforcement

### Phase 5: Polish (Weeks 9-10)
- [ ] Settings UI
- [ ] Human-readable views
- [ ] Decision observability
- [ ] Documentation
- [ ] Performance optimization

### Phase 6: Enterprise (Future)
- [ ] Team graphs
- [ ] Sync infrastructure
- [ ] Audit logging
- [ ] Compliance features
- [ ] API access

---

## Appendix: Key Insights from "Systems of Record, Reimagined"

> "Rules tell an agent what should happen in general. Decision traces capture what happened in this specific case."

> "Agents don't just need rules. They need access to the decision traces that show how rules were applied, where exceptions were granted, how conflicts were resolved."

> "The context graph becomes the real source of truth for autonomy – because it explains not just what happened, but why it was allowed to happen."

> "The feedback loop is what makes this compound. Captured decision traces become searchable precedent."

> "Capturing decision traces requires being in the execution path at commit time, not bolting on governance after the fact."

---

## Conclusion

Mind v3 transforms from a memory tool into a **system of record for AI decisions**. By capturing decision traces automatically, building a context graph, and enabling progressive autonomy, Mind becomes the foundation for truly intelligent AI assistants that learn, remember, and improve over time.

The goal: AI that earns trust through demonstrated good judgment, not AI that's trusted blindly.

---

*Design document created: 2025-12-25*
*Version: 3.0-draft*
*Status: Ready for review*
