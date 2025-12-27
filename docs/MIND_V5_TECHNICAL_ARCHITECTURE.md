# Mind v5: Definitive Technical Architecture
## The Complete Stack for Best-in-Class Decision Intelligence

> **Version**: 5.0 Final
> **Date**: December 27, 2025
> **Status**: Ready to Build

---

## Executive Summary

This is the **final, implementation-ready architecture** that integrates:
- All fact-checked technology decisions from v4
- The five strategic upgrades for benchmark leadership
- Production-proven components at every layer

---

## The Complete Technology Stack

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MIND v5 ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ╔═══════════════════════════════════════════════════════════════════════╗  │
│  ║                        INTENT GRAPH (Phase 5)                         ║  │
│  ║  ┌─────────────────────────────────────────────────────────────────┐  ║  │
│  ║  │  Pattern Federation: NATS JetStream (cross-cluster pub/sub)     │  ║  │
│  ║  │  Privacy Layer: Differential Privacy (ε=0.1, δ=10⁻⁵)            │  ║  │
│  ║  │  Aggregation: Apache Flink (streaming pattern extraction)       │  ║  │
│  ║  │  Pattern Store: PostgreSQL + TimescaleDB (time-series patterns) │  ║  │
│  ║  └─────────────────────────────────────────────────────────────────┘  ║  │
│  ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                      │                                      │
│                                      ▼                                      │
│  ╔═══════════════════════════════════════════════════════════════════════╗  │
│  ║                         MIND (Per User)                               ║  │
│  ║                                                                       ║  │
│  ║  ┌─────────────────────────────────────────────────────────────────┐  ║  │
│  ║  │                    EVENT BACKBONE                               │  ║  │
│  ║  │                                                                 │  ║  │
│  ║  │  Primary: NATS JetStream                                        │  ║  │
│  ║  │  ├── 200-400K msg/sec with persistence                          │  ║  │
│  ║  │  ├── Sub-millisecond latency                                    │  ║  │
│  ║  │  ├── Exactly-once delivery                                      │  ║  │
│  ║  │  └── 17MB binary, zero external deps                            │  ║  │
│  ║  │                                                                 │  ║  │
│  ║  │  Scale Fallback: Apache Kafka (if >500K msg/sec needed)         │  ║  │
│  ║  │                                                                 │  ║  │
│  ║  │  Event Types:                                                   │  ║  │
│  ║  │  ├── InteractionRecorded (raw observations)                     │  ║  │
│  ║  │  ├── MemoryExtracted (processed memories)                       │  ║  │
│  ║  │  ├── DecisionMade (with context snapshot)                       │  ║  │
│  ║  │  ├── OutcomeObserved (feedback signal)                          │  ║  │
│  ║  │  ├── CausalLinkDiscovered (new causal edge)                     │  ║  │
│  ║  │  └── PatternValidated (ready for federation)                    │  ║  │
│  ║  └─────────────────────────────────────────────────────────────────┘  ║  │
│  ║                                                                       ║  │
│  ║  ┌─────────────────────────────────────────────────────────────────┐  ║  │
│  ║  │                    PROJECTION LAYER                             │  ║  │
│  ║  │                                                                 │  ║  │
│  ║  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ║  │
│  ║  │  │   RELATIONAL    │  │     VECTOR      │  │   CAUSAL GRAPH  │  ║  │
│  ║  │  │                 │  │                 │  │                 │  ║  │
│  ║  │  │  PostgreSQL 16  │  │  Qdrant 1.9+    │  │  FalkorDB 4.0+  │  ║  │
│  ║  │  │  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │  ║  │
│  ║  │  │  │ Metadata  │  │  │  │ Embeddings│  │  │  │ Entities  │  │  ║  │
│  ║  │  │  │ Decisions │  │  │  │ 1536-dim  │  │  │  │ Relations │  │  ║  │
│  ║  │  │  │ Outcomes  │  │  │  │ HNSW idx  │  │  │  │ CAUSAL    │  │  ║  │
│  ║  │  │  │ Traces    │  │  │  │ <20ms p99 │  │  │  │ EDGES     │  │  ║  │
│  ║  │  │  └───────────┘  │  │  └───────────┘  │  │  │ Temporal  │  │  ║  │
│  ║  │  │                 │  │                 │  │  │ Validity  │  │  ║  │
│  ║  │  │  Also stores:   │  │  Fallback:      │  │  │ <140ms p99│  │  ║  │
│  ║  │  │  - pgvector for │  │  pgvectorscale  │  │  └───────────┘  │  ║  │
│  ║  │  │    lean start   │  │  (11x throughput│  │                 │  ║  │
│  ║  │  │                 │  │   if needed)    │  │  Fallback:      │  ║  │
│  ║  │  └─────────────────┘  └─────────────────┘  │  Neo4j (mature) │  ║  │
│  ║  │                                            └─────────────────┘  ║  │
│  ║  └─────────────────────────────────────────────────────────────────┘  ║  │
│  ║                                                                       ║  │
│  ║  ┌─────────────────────────────────────────────────────────────────┐  ║  │
│  ║  │                 INTELLIGENCE LAYER                              │  ║  │
│  ║  │                                                                 │  ║  │
│  ║  │  ┌─────────────────────────────────────────────────────────┐    ║  │
│  ║  │  │              HIERARCHICAL TEMPORAL MEMORY               │    ║  │
│  ║  │  │                                                         │    ║  │
│  ║  │  │  Engine: Zep/Graphiti (temporal KG, 94.8% DMR)          │    ║  │
│  ║  │  │                                                         │    ║  │
│  ║  │  │  L4: IDENTITY    (years)   → Core values, stable prefs  │    ║  │
│  ║  │  │  L3: SEASONAL    (months)  → Projects, recurring patterns│   ║  │
│  ║  │  │  L2: SITUATIONAL (weeks)   → Active tasks, recent events│    ║  │
│  ║  │  │  L1: IMMEDIATE   (session) → Current focus, working mem │    ║  │
│  ║  │  │                                                         │    ║  │
│  ║  │  │  Promotion: Stable patterns auto-elevate to higher level│    ║  │
│  ║  │  │  Retrieval: Multi-scale fusion with temporal weighting  │    ║  │
│  ║  │  └─────────────────────────────────────────────────────────┘    ║  │
│  ║  │                                                                 │  ║  │
│  ║  │  ┌─────────────────────────────────────────────────────────┐    ║  │
│  ║  │  │              DECISION OUTCOME TRACKER                   │    ║  │
│  ║  │  │                                                         │    ║  │
│  ║  │  │  Storage: PostgreSQL (decision_traces table)            │    ║  │
│  ║  │  │                                                         │    ║  │
│  ║  │  │  Flow:                                                  │    ║  │
│  ║  │  │  1. Context Retrieved → snapshot what was used          │    ║  │
│  ║  │  │  2. Decision Made → log choice + alternatives           │    ║  │
│  ║  │  │  3. Outcome Observed → async feedback signal            │    ║  │
│  ║  │  │  4. Attribution → which memories helped/hurt            │    ║  │
│  ║  │  │  5. Reweight → adjust salience based on outcomes        │    ║  │
│  ║  │  │                                                         │    ║  │
│  ║  │  │  Metrics: Decision Success Rate (DSR) per user          │    ║  │
│  ║  │  └─────────────────────────────────────────────────────────┘    ║  │
│  ║  │                                                                 │  ║  │
│  ║  │  ┌─────────────────────────────────────────────────────────┐    ║  │
│  ║  │  │              CAUSAL INFERENCE ENGINE                    │    ║  │
│  ║  │  │                                                         │    ║  │
│  ║  │  │  Library: DoWhy + CausalNex (Python)                    │    ║  │
│  ║  │  │                                                         │    ║  │
│  ║  │  │  Capabilities:                                          │    ║  │
│  ║  │  │  ├── Causal discovery from interaction data             │    ║  │
│  ║  │  │  ├── Counterfactual reasoning ("what if...")            │    ║  │
│  ║  │  │  ├── Intervention effect estimation                     │    ║  │
│  ║  │  │  └── Confound detection and adjustment                  │    ║  │
│  ║  │  │                                                         │    ║  │
│  ║  │  │  Output: CausalEdge objects stored in FalkorDB          │    ║  │
│  ║  │  └─────────────────────────────────────────────────────────┘    ║  │
│  ║  │                                                                 │  ║  │
│  ║  │  ┌─────────────────────────────────────────────────────────┐    ║  │
│  ║  │  │              EXTRACTION & OPTIMIZATION                  │    ║  │
│  ║  │  │                                                         │    ║  │
│  ║  │  │  Fast Path (10ms):                                      │    ║  │
│  ║  │  │  ├── Embedding: text-embedding-3-small                  │    ║  │
│  ║  │  │  ├── NER: GLiNER (outperforms spaCy)                    │    ║  │
│  ║  │  │  └── Classification: DistilBERT fine-tuned              │    ║  │
│  ║  │  │                                                         │    ║  │
│  ║  │  │  Cognitive Path (200ms):                                │    ║  │
│  ║  │  │  ├── Extraction: Claude Haiku 3.5                       │    ║  │
│  ║  │  │  ├── Optimization: DSPy MIPROv2                         │    ║  │
│  ║  │  │  └── Validation: Multi-model consensus                  │    ║  │
│  ║  │  └─────────────────────────────────────────────────────────┘    ║  │
│  ║  └─────────────────────────────────────────────────────────────────┘  ║  │
│  ║                                                                       ║  │
│  ║  ┌─────────────────────────────────────────────────────────────────┐  ║  │
│  ║  │                 ORCHESTRATION LAYER                             │  ║  │
│  ║  │                                                                 │  ║  │
│  ║  │  ┌─────────────────────────────────────────────────────────┐    ║  │
│  ║  │  │              TEMPORAL.IO GARDENER                       │    ║  │
│  ║  │  │                                                         │    ║  │
│  ║  │  │  Why: Durable execution, automatic retry, state persist │    ║  │
│  ║  │  │  Used by: Stripe, Netflix, Coinbase, Snap               │    ║  │
│  ║  │  │                                                         │    ║  │
│  ║  │  │  Workflows:                                             │    ║  │
│  ║  │  │  ├── MemoryConsolidation (daily, hierarchical merge)    │    ║  │
│  ║  │  │  ├── CausalDiscovery (weekly, pattern mining)           │    ║  │
│  ║  │  │  ├── PatternFederation (continuous, to Intent Graph)    │    ║  │
│  ║  │  │  ├── OutcomeAttribution (async, on feedback)            │    ║  │
│  ║  │  │  └── GraphMaintenance (monthly, prune + reindex)        │    ║  │
│  ║  │  │                                                         │    ║  │
│  ║  │  │  Activities:                                            │    ║  │
│  ║  │  │  ├── ExtractMemories (from raw observations)            │    ║  │
│  ║  │  │  ├── ResolveEntities (dedup, merge, link)               │    ║  │
│  ║  │  │  ├── InferCausality (DoWhy pipeline)                    │    ║  │
│  ║  │  │  ├── ValidatePatterns (statistical significance)        │    ║  │
│  ║  │  │  └── SanitizeForFederation (remove PII, abstract)       │    ║  │
│  ║  │  └─────────────────────────────────────────────────────────┘    ║  │
│  ║  │                                                                 │  ║  │
│  ║  │  ┌─────────────────────────────────────────────────────────┐    ║  │
│  ║  │  │              RETRIEVAL & FUSION                         │    ║  │
│  ║  │  │                                                         │    ║  │
│  ║  │  │  Strategy: Reciprocal Rank Fusion (RRF)                 │    ║  │
│  ║  │  │                                                         │    ║  │
│  ║  │  │  score = Σ 1/(k + rank_i) for each retrieval method     │    ║  │
│  ║  │  │                                                         │    ║  │
│  ║  │  │  Methods fused:                                         │    ║  │
│  ║  │  │  ├── Vector similarity (Qdrant)                         │    ║  │
│  ║  │  │  ├── Graph traversal (FalkorDB, 2-hop)                  │    ║  │
│  ║  │  │  ├── Keyword/BM25 (PostgreSQL full-text)                │    ║  │
│  ║  │  │  ├── Temporal recency (decay function)                  │    ║  │
│  ║  │  │  └── Outcome-weighted salience (learned)                │    ║  │
│  ║  │  │                                                         │    ║  │
│  ║  │  │  Final rerank: Cross-encoder (ms-marco-MiniLM)          │    ║  │
│  ║  │  └─────────────────────────────────────────────────────────┘    ║  │
│  ║  └─────────────────────────────────────────────────────────────────┘  ║  │
│  ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                      │                                      │
│                                      ▼                                      │
│  ╔═══════════════════════════════════════════════════════════════════════╗  │
│  ║                           SPAWNER                                     ║  │
│  ║                                                                       ║  │
│  ║  ┌─────────────────────────────────────────────────────────────────┐  ║  │
│  ║  │              AGENT TEAM (Emergent Specialization)              │  ║  │
│  ║  │                                                                 │  ║  │
│  ║  │  Topology: Small-world network (research-backed)                │  ║  │
│  ║  │  Specialization: Emergent from competency tracking              │  ║  │
│  ║  │                                                                 │  ║  │
│  ║  │  ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐  ║  │
│  ║  │  │  Agent 1  │◄─►│  Agent 2  │◄─►│  Agent 3  │◄─►│  Agent N  │  ║  │
│  ║  │  │           │   │           │   │           │   │           │  ║  │
│  ║  │  │ Competency│   │ Competency│   │ Competency│   │ Competency│  ║  │
│  ║  │  │ Vector    │   │ Vector    │   │ Vector    │   │ Vector    │  ║  │
│  ║  │  └───────────┘   └───────────┘   └───────────┘   └───────────┘  ║  │
│  ║  │        │               │               │               │        ║  │
│  ║  │        └───────────────┴───────────────┴───────────────┘        ║  │
│  ║  │                            │                                    ║  │
│  ║  │                    ┌───────▼───────┐                            ║  │
│  ║  │                    │ Task Router   │                            ║  │
│  ║  │                    │ (competency-  │                            ║  │
│  ║  │                    │  based)       │                            ║  │
│  ║  │                    └───────────────┘                            ║  │
│  ║  └─────────────────────────────────────────────────────────────────┘  ║  │
│  ║                                                                       ║  │
│  ║  Communication: NATS (async), gRPC (sync)                             ║  │
│  ║  State: Each agent has Mind connection                                ║  │
│  ║  Learning: Competency updated on every outcome                        ║  │
│  ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                          INFRASTRUCTURE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Observability:                                                             │
│  ├── Metrics: Prometheus + Grafana                                          │
│  ├── Tracing: OpenTelemetry → Jaeger                                        │
│  ├── Logging: Structured JSON → Loki                                        │
│  └── Alerting: PagerDuty integration                                        │
│                                                                             │
│  Security:                                                                  │
│  ├── Secrets: HashiCorp Vault                                               │
│  ├── Auth: JWT + mTLS between services                                      │
│  ├── Encryption: AES-256 at rest, TLS 1.3 in transit                        │
│  └── Privacy: Differential privacy for federation (ε=0.1)                   │
│                                                                             │
│  Deployment:                                                                │
│  ├── Container: Docker + containerd                                         │
│  ├── Orchestration: Kubernetes (k8s)                                        │
│  ├── Service Mesh: Istio (optional, for complex deployments)                │
│  └── CI/CD: GitHub Actions → ArgoCD                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Selection: Final Decisions

### Core Data Stores

| Component | Technology | Why | Benchmark Evidence |
|-----------|------------|-----|-------------------|
| **Relational** | PostgreSQL 16 | Universal foundation, pgvector fallback | Industry standard |
| **Vector** | Qdrant (primary) | Best p99 latency (38.71ms) | Timescale May 2025 |
| **Vector fallback** | pgvector + pgvectorscale | 11.4x throughput when needed | Timescale May 2025 |
| **Graph** | FalkorDB | 500x faster p99 vs Neo4j | FalkorDB Dec 2024 |
| **Graph fallback** | Neo4j | Maturity, ecosystem | Industry standard |
| **Time-series** | TimescaleDB | Pattern analytics, hypertables | Native Postgres ext |

### Event & Messaging

| Component | Technology | Why | Benchmark Evidence |
|-----------|------------|-----|-------------------|
| **Event backbone** | NATS JetStream | Sub-ms latency, 400K msg/s, tiny footprint | 2025 VPS benchmarks |
| **Scale fallback** | Apache Kafka | 1M+ msg/s, mature ecosystem | 2025 VPS benchmarks |
| **RPC** | gRPC | Type-safe, streaming, efficient | Industry standard |

### Intelligence & Learning

| Component | Technology | Why | Benchmark Evidence |
|-----------|------------|-----|-------------------|
| **Memory layer** | Zep/Graphiti | Temporal KG, 94.8% DMR, 90% latency reduction | arxiv 2501.13956 |
| **Causal inference** | DoWhy + CausalNex | SCM support, interventions, counterfactuals | Peer-reviewed |
| **Prompt optimization** | DSPy MIPROv2 | 46%→64% accuracy improvement | Stanford research |
| **Fast NER** | GLiNER | Outperforms spaCy on benchmarks | HuggingFace |
| **Embeddings** | text-embedding-3-small | Cost/quality balance | OpenAI |
| **LLM extraction** | Claude Haiku 3.5 | Fast, accurate, cost-effective | Anthropic |

### Orchestration & Reliability

| Component | Technology | Why | Evidence |
|-----------|------------|-----|----------|
| **Workflow orchestration** | Temporal.io | Durable execution, used by Stripe/Netflix/Snap | Production proven |
| **Scheduling** | Temporal (built-in) | Long-running, fault-tolerant | Production proven |
| **Circuit breaking** | Resilience4j | JVM-native, well-tested | Industry standard |

### Retrieval & Fusion

| Component | Technology | Why | Evidence |
|-----------|------------|-----|----------|
| **Fusion algorithm** | Reciprocal Rank Fusion (RRF) | Robust, proven in IR research | ACM SIGIR 2009 |
| **Reranking** | Cross-encoder (ms-marco-MiniLM) | High accuracy, reasonable latency | HuggingFace |
| **BM25** | PostgreSQL full-text | Integrated, no extra service | Native |

---

## Data Schemas

### Core Event Schema

```sql
-- PostgreSQL: events table (append-only)
CREATE TABLE events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Partitioning for scale
    CONSTRAINT events_partition CHECK (created_at IS NOT NULL)
) PARTITION BY RANGE (created_at);

-- Index for common queries
CREATE INDEX idx_events_user_type ON events (user_id, event_type);
CREATE INDEX idx_events_created ON events (created_at DESC);
```

### Decision Trace Schema

```sql
-- PostgreSQL: decision tracking for outcome learning
CREATE TABLE decision_traces (
    trace_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    session_id UUID NOT NULL,
    
    -- What was retrieved
    context_snapshot JSONB NOT NULL,  -- Memories used
    context_memory_ids UUID[] NOT NULL,
    retrieval_scores JSONB NOT NULL,  -- Relevance scores
    
    -- What was decided
    decision_type VARCHAR(100) NOT NULL,
    decision_content TEXT NOT NULL,
    confidence FLOAT NOT NULL,
    alternatives_considered JSONB DEFAULT '[]',
    
    -- Outcome (filled async)
    outcome_observed BOOLEAN DEFAULT FALSE,
    outcome_quality FLOAT,  -- -1 to 1
    outcome_timestamp TIMESTAMPTZ,
    outcome_signal TEXT,  -- How we detected outcome
    
    -- Attribution (computed after outcome)
    memory_attribution JSONB,  -- {memory_id: contribution_score}
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX idx_traces_user_outcome ON decision_traces (user_id, outcome_observed);
CREATE INDEX idx_traces_pending ON decision_traces (outcome_observed) WHERE NOT outcome_observed;
```

### Causal Edge Schema (FalkorDB/Cypher)

```cypher
// Causal edge with temporal validity and evidence
CREATE (e1:Entity)-[r:CAUSES {
    // Core relationship
    relationship_type: "preference",
    
    // Causal metadata (THE DIFFERENTIATOR)
    causal_direction: "causes",  // causes | correlates | prevents
    causal_strength: 0.73,
    
    // Temporal context
    valid_from: datetime("2024-06-01"),
    valid_until: null,  // Still valid
    temporal_conditions: ["morning", "weekday"],
    
    // Conditions
    conditions: ["under_deadline", "low_energy"],
    
    // Effects chain
    downstream_effects: ["increased_focus", "faster_completion"],
    
    // Counterfactuals
    counterfactual: "Without coffee, task completion drops 23%",
    
    // Evidence
    evidence_count: 47,
    confidence: 0.87,
    last_validated: datetime("2025-12-20"),
    
    // Provenance
    discovered_by: "causal_discovery_workflow",
    discovery_method: "doWhy_backdoor"
}]->(e2:Entity)
```

### Hierarchical Memory Schema

```sql
-- PostgreSQL: Multi-level temporal memory
CREATE TABLE memories (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    
    -- Content
    content TEXT NOT NULL,
    content_type VARCHAR(50) NOT NULL,  -- fact, preference, event, goal, etc.
    embedding VECTOR(1536),  -- For vector search
    
    -- Hierarchical level
    temporal_level INT NOT NULL,  -- 1=immediate, 2=situational, 3=seasonal, 4=identity
    
    -- Temporal validity
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,  -- NULL = still valid
    
    -- Salience (outcome-weighted)
    base_salience FLOAT DEFAULT 1.0,
    outcome_adjustment FLOAT DEFAULT 0.0,
    effective_salience FLOAT GENERATED ALWAYS AS (base_salience + outcome_adjustment) STORED,
    
    -- Usage stats
    retrieval_count INT DEFAULT 0,
    last_retrieved TIMESTAMPTZ,
    decision_count INT DEFAULT 0,  -- How many decisions used this
    positive_outcomes INT DEFAULT 0,
    negative_outcomes INT DEFAULT 0,
    
    -- Promotion tracking
    promoted_from_level INT,
    promotion_timestamp TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Indexes
CREATE INDEX idx_memories_user_level ON memories (user_id, temporal_level);
CREATE INDEX idx_memories_salience ON memories (user_id, effective_salience DESC);
CREATE INDEX idx_memories_vector ON memories USING ivfflat (embedding vector_cosine_ops);
```

### Pattern Schema (For Intent Graph Federation)

```sql
-- PostgreSQL: Sanitized patterns for cross-user learning
CREATE TABLE federated_patterns (
    pattern_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Abstract pattern (NO PII)
    trigger_type VARCHAR(100) NOT NULL,  -- "frustration", "confusion", etc.
    trigger_indicators JSONB NOT NULL,  -- Abstract signals
    
    response_strategy VARCHAR(100) NOT NULL,  -- "empathetic_acknowledgment", etc.
    response_template TEXT,  -- Abstract template
    
    -- Measured outcome
    outcome_improvement FLOAT NOT NULL,  -- Avg improvement %
    confidence_interval JSONB NOT NULL,  -- {lower: x, upper: y}
    
    -- Aggregation stats
    source_count INT NOT NULL,  -- Must be >= 100 for privacy
    user_count INT NOT NULL,  -- Must be >= 10 for privacy
    
    -- Privacy
    differential_privacy_applied BOOLEAN DEFAULT TRUE,
    epsilon FLOAT DEFAULT 0.1,
    
    -- Validity
    first_observed TIMESTAMPTZ NOT NULL,
    last_validated TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Only index active, validated patterns
CREATE INDEX idx_patterns_active ON federated_patterns (trigger_type) WHERE is_active;
```

---

## API Contracts

### Memory Service API

```protobuf
// memory_service.proto
syntax = "proto3";

service MemoryService {
    // Core operations
    rpc RecordInteraction(InteractionRequest) returns (InteractionResponse);
    rpc RetrieveContext(ContextRequest) returns (ContextResponse);
    rpc RecordOutcome(OutcomeRequest) returns (OutcomeResponse);
    
    // Causal operations
    rpc QueryCausalChain(CausalQuery) returns (CausalChainResponse);
    rpc PredictOutcome(PredictionRequest) returns (PredictionResponse);
    
    // Pattern operations
    rpc GetRelevantPatterns(PatternRequest) returns (PatternResponse);
}

message ContextRequest {
    string user_id = 1;
    string query = 2;
    repeated string required_levels = 3;  // ["immediate", "identity"]
    int32 max_results = 4;
    bool include_causal = 5;
}

message ContextResponse {
    repeated MemoryItem memories = 1;
    repeated CausalEdge causal_context = 2;
    repeated Pattern relevant_patterns = 3;
    float retrieval_latency_ms = 4;
}

message MemoryItem {
    string memory_id = 1;
    string content = 2;
    string temporal_level = 3;
    float salience = 4;
    float recency_score = 5;
    float outcome_score = 6;  // Learned from outcomes
}

message CausalEdge {
    string source_entity = 1;
    string target_entity = 2;
    string relationship = 3;
    float causal_strength = 4;
    repeated string conditions = 5;
    string counterfactual = 6;
}
```

### Decision Service API

```protobuf
// decision_service.proto
syntax = "proto3";

service DecisionService {
    rpc RecordDecision(DecisionRequest) returns (DecisionResponse);
    rpc RecordOutcome(OutcomeRequest) returns (OutcomeResponse);
    rpc GetDecisionStats(StatsRequest) returns (StatsResponse);
}

message DecisionRequest {
    string user_id = 1;
    string session_id = 2;
    
    // Context used
    repeated string memory_ids = 3;
    map<string, float> memory_weights = 4;
    
    // Decision made
    string decision_type = 5;
    string decision_content = 6;
    float confidence = 7;
    repeated string alternatives = 8;
}

message OutcomeRequest {
    string trace_id = 1;
    float outcome_quality = 2;  // -1 to 1
    string outcome_signal = 3;  // How detected
}

message StatsResponse {
    float decision_success_rate = 1;  // DSR
    int32 total_decisions = 2;
    int32 positive_outcomes = 3;
    map<string, float> memory_effectiveness = 4;  // Which memories help most
}
```

---

## Performance Targets

### Latency SLOs

| Operation | p50 | p95 | p99 | Target |
|-----------|-----|-----|-----|--------|
| Context retrieval | 30ms | 75ms | 100ms | Phase 1 |
| Context retrieval | 20ms | 50ms | 75ms | Phase 3 |
| Causal query (2-hop) | 50ms | 100ms | 150ms | Phase 2 |
| Outcome recording | 5ms | 10ms | 20ms | All phases |
| Pattern lookup | 10ms | 25ms | 50ms | Phase 4 |

### Throughput SLOs

| Operation | Sustained | Burst | Target |
|-----------|-----------|-------|--------|
| Event ingestion | 10K/sec | 50K/sec | Phase 1 |
| Event ingestion | 100K/sec | 500K/sec | Phase 5 |
| Context queries | 1K/sec | 10K/sec | Phase 1 |
| Context queries | 10K/sec | 100K/sec | Phase 5 |

### Accuracy SLOs

| Metric | Phase 1 | Phase 3 | Phase 5 |
|--------|---------|---------|---------|
| Memory retrieval recall | 70% | 80% | 90% |
| Causal prediction accuracy | 60% | 70% | 80% |
| Decision Success Rate (DSR) | Baseline | +10% | +25% |
| Collective Intelligence Quotient | N/A | N/A | +15% |

---

## Deployment Architecture

### Kubernetes Resources

```yaml
# mind-v5-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mind-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mind-api
  template:
    metadata:
      labels:
        app: mind-api
    spec:
      containers:
      - name: mind-api
        image: mind/api:v5.0
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        ports:
        - containerPort: 8080  # HTTP
        - containerPort: 9090  # gRPC
        env:
        - name: POSTGRES_URL
          valueFrom:
            secretKeyRef:
              name: mind-secrets
              key: postgres-url
        - name: QDRANT_URL
          value: "qdrant:6333"
        - name: FALKORDB_URL
          value: "falkordb:6379"
        - name: NATS_URL
          value: "nats://nats:4222"
        - name: TEMPORAL_URL
          value: "temporal:7233"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mind-gardener
spec:
  replicas: 2
  selector:
    matchLabels:
      app: mind-gardener
  template:
    spec:
      containers:
      - name: gardener
        image: mind/gardener:v5.0
        resources:
          requests:
            memory: "4Gi"
            cpu: "2000m"
          limits:
            memory: "8Gi"
            cpu: "4000m"
        env:
        - name: TEMPORAL_TASK_QUEUE
          value: "gardener-queue"
```

### Resource Estimates by Scale

| Scale | PostgreSQL | Qdrant | FalkorDB | NATS | Monthly Cost |
|-------|------------|--------|----------|------|--------------|
| 1K users | 2 vCPU, 8GB | 2 vCPU, 8GB | 2 vCPU, 4GB | 1 vCPU, 2GB | ~$200 |
| 10K users | 4 vCPU, 16GB | 4 vCPU, 16GB | 4 vCPU, 8GB | 2 vCPU, 4GB | ~$800 |
| 100K users | 8 vCPU, 32GB | 8 vCPU, 32GB | 8 vCPU, 16GB | 4 vCPU, 8GB | ~$3,000 |
| 1M users | 16 vCPU, 64GB (cluster) | 16 vCPU, 64GB (cluster) | 16 vCPU, 32GB | 8 vCPU, 16GB | ~$15,000 |

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-6)
```
Week 1-2: Core infrastructure
├── PostgreSQL + pgvector setup
├── NATS JetStream deployment
├── Basic event schema
└── API scaffolding

Week 3-4: Memory layer
├── Zep/Graphiti integration
├── Hierarchical memory schema
├── Basic retrieval (vector + recency)
└── Decision trace logging

Week 5-6: Testing & baseline
├── LoCoMo benchmark baseline
├── Latency SLO validation
├── Load testing
└── Monitoring setup
```

### Phase 2: Intelligence (Weeks 7-12)
```
Week 7-8: Causal foundation
├── FalkorDB deployment
├── Causal edge schema
├── DoWhy integration
└── Basic causal queries

Week 9-10: Outcome learning
├── Outcome tracking pipeline
├── Attribution computation
├── Salience reweighting
└── DSR metrics

Week 11-12: Retrieval fusion
├── RRF implementation
├── Multi-source retrieval
├── Outcome-weighted ranking
└── A/B testing framework
```

### Phase 3: Orchestration (Weeks 13-18)
```
Week 13-14: Temporal.io
├── Workflow definitions
├── Activity implementations
├── Error handling
└── Observability

Week 15-16: Gardener workflows
├── MemoryConsolidation
├── CausalDiscovery
├── OutcomeAttribution
└── GraphMaintenance

Week 17-18: DSPy optimization
├── Extraction prompts
├── MIPROv2 training
├── Prompt versioning
└── Performance tracking
```

### Phase 4: Collective Intelligence (Weeks 19-24)
```
Week 19-20: Pattern extraction
├── Sanitization pipeline
├── Privacy validation
├── Aggregation rules
└── Pattern schema

Week 21-22: Intent Graph MVP
├── Federation protocol
├── Cross-user patterns
├── Pattern retrieval
└── Privacy audit

Week 23-24: Specialization
├── Competency tracking
├── Task routing
├── Team metrics
└── TIQ baseline
```

### Phase 5: Benchmark Leadership (Weeks 25-30)
```
Week 25-26: New benchmarks
├── CDQ benchmark creation
├── DSR tracking dashboard
├── CIQ measurement
└── TCS benchmark

Week 27-28: Optimization
├── Performance tuning
├── Cost optimization
├── Scale testing
└── Chaos engineering

Week 29-30: Launch
├── Documentation
├── Benchmark publication
├── Open-source components
└── Production deployment
```

---

## Success Metrics

### Phase 1 Exit Criteria
- [ ] LoCoMo score ≥ 74% (match Letta baseline)
- [ ] Context retrieval p99 < 100ms
- [ ] Event ingestion > 10K/sec

### Phase 3 Exit Criteria
- [ ] DSR tracking operational
- [ ] Causal queries < 150ms p99
- [ ] Memory reweighting showing improvement

### Phase 5 Exit Criteria
- [ ] CDQ benchmark published
- [ ] CIQ > 15% improvement over isolated agents
- [ ] DSR > 25% improvement over baseline
- [ ] Ready for 100K+ users

---

## Final Technology Summary

| Layer | Primary | Fallback | Why Primary |
|-------|---------|----------|-------------|
| Events | NATS JetStream | Kafka | Simpler, sub-ms latency, sufficient scale |
| Relational | PostgreSQL 16 | - | Universal, proven, extensible |
| Vector | Qdrant | pgvectorscale | Best p99 latency for hot path |
| Graph | FalkorDB | Neo4j | 500x faster p99, Redis-native |
| Memory | Zep/Graphiti | Custom | Temporal KG, 94.8% accuracy, research-backed |
| Causal | DoWhy + CausalNex | - | Industry standard, SCM support |
| Orchestration | Temporal.io | - | Durable execution, production proven |
| Optimization | DSPy | - | Automatic prompt improvement |
| Federation | NATS + Flink | Kafka Streams | Real-time pattern streaming |

---

**This is the architecture. Let's build it.**

---

*Document Version: 5.0 Final*
*Created: December 27, 2025*
*Status: Ready for Implementation*
