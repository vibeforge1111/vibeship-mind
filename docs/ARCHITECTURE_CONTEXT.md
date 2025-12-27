# Mind v5 Architecture Context for Skills

> **Purpose**: Deep context for skills to understand the system they're building
> **Usage**: Reference this when skills need architectural understanding
> **Location**: Place at root of skills directory for Opus access

---

## System Overview

Mind v5 is a **decision intelligence system** that helps AI agents make better decisions over time by:

1. **Remembering** context across interactions (hierarchical memory)
2. **Learning** what context leads to good decisions (outcome tracking)
3. **Reasoning** about causes and effects (causal knowledge graph)
4. **Sharing** successful patterns across users (privacy-preserving federation)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERACTION                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        MIND v5 CORE                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │   MEMORY     │  │    CAUSAL    │  │   DECISION   │                  │
│  │   SYSTEM     │◄─┤    GRAPH     │◄─┤   TRACKER    │                  │
│  │              │  │              │  │              │                  │
│  │ • Hierarchical│  │ • Causes    │  │ • Traces     │                  │
│  │ • Temporal   │  │ • Effects   │  │ • Outcomes   │                  │
│  │ • Salience   │  │ • Confidence│  │ • Attribution│                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│         │                  │                  │                         │
│         └──────────────────┼──────────────────┘                         │
│                            │                                            │
│                            ▼                                            │
│                   ┌──────────────────┐                                  │
│                   │  INTENT GRAPH    │                                  │
│                   │  (Federation)    │                                  │
│                   │                  │                                  │
│                   │ Privacy-preserving│                                 │
│                   │ pattern sharing  │                                  │
│                   └──────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## The Five Laws (Architectural Principles)

Every skill must internalize these laws:

### Law 1: Events are Sacred
```
All state changes flow through the event backbone.
Events are immutable, append-only, never deleted.
If it's not in the event log, it didn't happen.
Projections can always be rebuilt from events.
```

**Implications for skills:**
- event-architect defines all event schemas
- All skills that change state must emit events
- Projections must be idempotent (replay-safe)
- No direct database mutations outside event handlers

### Law 2: Memory Serves Decisions
```
Memory exists to improve decision quality, not just storage.
Every retrieval should be traced to outcomes.
Memories that lead to good decisions gain salience.
Memories that mislead get demoted.
```

**Implications for skills:**
- ml-memory tracks decision traces
- vector-specialist optimizes for decision-relevant retrieval
- causal-scientist attributes outcomes to memories
- Retrieval quality measured by decision success rate

### Law 3: Causality Over Correlation
```
Store WHY, not just WHAT.
Every important relationship should have causal metadata.
Enable counterfactual reasoning ("what if...").
Distinguish causes from correlations explicitly.
```

**Implications for skills:**
- graph-engineer stores causal edges with strength/confidence
- causal-scientist validates causal claims
- ml-memory uses causal context in retrieval
- Decision support includes counterfactual analysis

### Law 4: Privacy is Non-Negotiable
```
User data never leaves their Mind without explicit consent.
Federated patterns are sanitized with differential privacy.
No PII in logs, traces, or error messages.
Encryption at rest, in transit, always.
```

**Implications for skills:**
- privacy-guardian has blocking authority on all data changes
- data-engineer implements DP in federation pipeline
- All skills sanitize logs (no content, only IDs)
- Federation requires ε≤0.1, 100+ sources, 10+ users

### Law 5: Failure is Expected
```
Every external call will eventually fail.
Design for graceful degradation.
Temporal.io workflows handle long-running operations.
Chaos monkey should be survivable.
```

**Implications for skills:**
- temporal-craftsman wraps all fallible flows
- chaos-engineer tests all failure modes
- All services have circuit breakers
- Graceful degradation paths defined

---

## Data Flow Architecture

### The Complete Flow

```
USER INPUT
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│ 1. INTERACTION CAPTURE                                      │
│    InteractionRecorded event published to NATS              │
│    Owner: event-architect                                   │
└────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│ 2. MEMORY EXTRACTION                                        │
│    LLM extracts memories from interaction                   │
│    MemoryExtracted event published                          │
│    Owner: ml-memory                                         │
└────────────────────────────────────────────────────────────┘
    │
    ├───────────────────────┬───────────────────────┐
    ▼                       ▼                       ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 3a. EMBED    │    │ 3b. GRAPH    │    │ 3c. STORE    │
│              │    │              │    │              │
│ Create vector│    │ Link to      │    │ PostgreSQL   │
│ in Qdrant    │    │ entities in  │    │ with hier-   │
│              │    │ FalkorDB     │    │ archical     │
│ vector-      │    │              │    │ level        │
│ specialist   │    │ graph-       │    │              │
│              │    │ engineer     │    │ postgres-    │
└──────────────┘    └──────────────┘    │ wizard       │
                                        └──────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│ 4. CONTEXT RETRIEVAL (on next query)                        │
│    Hybrid search: vector + graph + keyword                  │
│    RRF fusion of results                                    │
│    Outcome-weighted reranking                               │
│    Owner: vector-specialist + ml-memory                     │
└────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│ 5. DECISION MADE                                            │
│    Agent makes decision using retrieved context             │
│    DecisionMade event captures context snapshot             │
│    Owner: event-architect (schema), ml-memory (tracking)    │
└────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│ 6. OUTCOME OBSERVED (async, later)                          │
│    User feedback or implicit signal                         │
│    OutcomeObserved event published                          │
│    Owner: event-architect (schema), ml-memory (tracking)    │
└────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│ 7. ATTRIBUTION & LEARNING                                   │
│    Causal attribution: which memories influenced outcome?   │
│    Salience adjustment based on attribution                 │
│    Owner: causal-scientist + ml-memory                      │
└────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│ 8. CAUSAL DISCOVERY (background)                            │
│    Pattern mining from successful interactions              │
│    CausalLinkDiscovered events                              │
│    Owner: causal-scientist                                  │
└────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│ 9. FEDERATION (when patterns mature)                        │
│    Privacy sanitization (ε=0.1)                             │
│    Aggregation (100+ sources, 10+ users)                    │
│    PatternValidated event → Intent Graph                    │
│    Owner: data-engineer + privacy-guardian                  │
└────────────────────────────────────────────────────────────┘
```

---

## Technology Stack Details

### Event Backbone: NATS JetStream

```yaml
why: "200-400K msg/sec, sub-ms latency, 17MB binary, exactly-once"
alternative: "Apache Kafka for >1M msg/sec"

configuration:
  streams:
    - name: MIND_EVENTS
      subjects: ["mind.events.>"]
      retention: limits
      max_age: 7d  # Keep 7 days for replay
      storage: file
      replicas: 3  # HA
      
  consumers:
    - name: memory-extractor
      durable: true
      ack_policy: explicit
      ack_wait: 2m  # Long for ML processing
      max_deliver: 3
      
    - name: graph-projector
      durable: true
      ack_policy: explicit
      deliver_policy: all  # Rebuild capability
```

### Vector Database: Qdrant

```yaml
why: "38ms p99 latency, best tail latency for hot path"
alternative: "pgvectorscale for 11.4x throughput if latency ok"

configuration:
  collection:
    name: memories
    vectors:
      size: 1536  # text-embedding-3-small
      distance: Cosine
      
    # Shard by user for locality
    shard_number: 16
    replication_factor: 2
    
  indexes:
    hnsw:
      m: 16
      ef_construct: 100
      
  payload_schema:
    user_id: keyword  # For filtering
    temporal_level: integer
    valid_until: datetime
    model_version: keyword  # For model migrations
```

### Graph Database: FalkorDB

```yaml
why: "500x faster p99 than Neo4j, Redis-native"
alternative: "Neo4j for larger ecosystem needs"

configuration:
  # Redis config
  maxmemory: 16gb
  maxmemory-policy: noeviction  # Never evict graph data
  
  # FalkorDB indexes
  indexes:
    - "CREATE INDEX FOR (u:User) ON (u.user_id)"
    - "CREATE INDEX FOR (m:Memory) ON (m.memory_id)"
    - "CREATE INDEX FOR (e:Entity) ON (e.entity_id)"
    
  # Causal edge properties (always include)
  causal_edge_schema:
    - causal_direction  # causes|prevents|correlates
    - causal_strength   # 0.0-1.0
    - confidence        # 0.0-1.0
    - valid_from        # datetime
    - valid_until       # datetime|null
    - evidence_count    # int
    - discovery_method  # statistical|expert|observed
    - counterfactual    # text|null
```

### Relational: PostgreSQL 16

```yaml
why: "Universal foundation, pgvector fallback, proven at scale"

key_tables:
  memories:
    partitioning: HASH(user_id)  # 16 partitions
    indexes:
      - "(user_id, temporal_level) WHERE valid_until IS NULL"
      - "(user_id, effective_salience DESC)"
      - "USING BRIN (created_at)"
      
  decision_traces:
    partitioning: RANGE(created_at)  # Monthly partitions
    indexes:
      - "(user_id, outcome_observed)"
      - "(trace_id)"
      
  federated_patterns:
    indexes:
      - "(trigger_type) WHERE is_active"
```

### Orchestration: Temporal.io

```yaml
why: "Durable execution, used by Stripe/Netflix/Snap"

workflows:
  MemoryConsolidation:
    schedule: "0 2 * * *"  # Daily 2am
    timeout: 4h
    
  CausalDiscovery:
    schedule: "0 3 * * 0"  # Weekly Sunday 3am
    timeout: 8h
    
  PatternFederation:
    trigger: PatternValidated event
    timeout: 1h
    
  OutcomeAttribution:
    trigger: OutcomeObserved event
    timeout: 30m
    
  GraphMaintenance:
    schedule: "0 4 1 * *"  # Monthly 1st 4am
    timeout: 12h
```

---

## Key Metrics

### Decision Quality Metrics (Primary)

| Metric | Description | Target |
|--------|-------------|--------|
| `mind_decision_success_rate` | % of decisions with positive outcomes | >70% |
| `mind_causal_prediction_accuracy` | Accuracy of outcome predictions | >65% |
| `mind_collective_intelligence_quotient` | Improvement from federation | >15% |

### Retrieval Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| `mind_retrieval_latency_p99` | Context retrieval latency | <100ms |
| `mind_retrieval_relevance` | Relevance score of retrieved memories | >0.7 |
| `mind_memory_salience_correlation` | Correlation between salience and usefulness | >0.5 |

### System Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| `mind_event_processing_latency` | Time from event to projection | <50ms |
| `mind_causal_discovery_edges` | New causal edges discovered weekly | >100 |
| `mind_federation_patterns_active` | Active federated patterns | >1000 |

---

## File Structure Reference

```
mind-v5/
├── src/
│   ├── core/
│   │   ├── events/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py          # Event dataclasses
│   │   │   ├── publisher.py        # NATS publishing
│   │   │   └── handlers/           # Event handlers
│   │   │
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   ├── models.py           # Memory dataclasses
│   │   │   ├── hierarchy.py        # Temporal level logic
│   │   │   ├── retrieval.py        # RRF fusion
│   │   │   ├── salience.py         # Outcome-weighted salience
│   │   │   └── consolidation.py    # Memory consolidation
│   │   │
│   │   ├── causal/
│   │   │   ├── __init__.py
│   │   │   ├── models.py           # CausalEdge dataclasses
│   │   │   ├── discovery.py        # DoWhy integration
│   │   │   ├── attribution.py      # Outcome attribution
│   │   │   └── counterfactual.py   # Counterfactual queries
│   │   │
│   │   └── decision/
│   │       ├── __init__.py
│   │       ├── models.py           # DecisionTrace dataclasses
│   │       ├── tracker.py          # Decision tracking
│   │       └── outcome.py          # Outcome processing
│   │
│   ├── infrastructure/
│   │   ├── postgres/
│   │   │   ├── __init__.py
│   │   │   ├── pool.py             # Connection pooling
│   │   │   ├── migrations/         # Alembic migrations
│   │   │   └── repositories/       # Data access
│   │   │
│   │   ├── qdrant/
│   │   │   ├── __init__.py
│   │   │   ├── client.py           # Qdrant client
│   │   │   └── search.py           # Search operations
│   │   │
│   │   ├── falkordb/
│   │   │   ├── __init__.py
│   │   │   ├── client.py           # FalkorDB client
│   │   │   └── queries.py          # Cypher queries
│   │   │
│   │   ├── nats/
│   │   │   ├── __init__.py
│   │   │   ├── client.py           # NATS client
│   │   │   └── streams.py          # Stream management
│   │   │
│   │   └── temporal/
│   │       ├── __init__.py
│   │       ├── client.py           # Temporal client
│   │       ├── workflows/          # Workflow definitions
│   │       └── activities/         # Activity implementations
│   │
│   ├── api/
│   │   ├── grpc/                   # gRPC services
│   │   └── rest/                   # REST endpoints
│   │
│   ├── workers/
│   │   ├── gardener/               # Temporal workers
│   │   ├── projectors/             # Event projectors
│   │   └── extractors/             # Memory extractors
│   │
│   └── shared/
│       ├── errors/                 # Error types
│       ├── logging/                # Structured logging
│       ├── metrics/                # Prometheus metrics
│       └── security/               # Auth, encryption
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── benchmarks/
│
├── deploy/
│   ├── docker/
│   ├── k8s/
│   └── terraform/
│
└── docs/
    ├── architecture/
    ├── api/
    ├── runbooks/
    └── skills/
```

---

## Skill Ownership Map

| Directory | Primary Owner | Secondary |
|-----------|--------------|-----------|
| src/core/events/ | event-architect | - |
| src/core/memory/ | ml-memory | vector-specialist |
| src/core/causal/ | causal-scientist | graph-engineer |
| src/core/decision/ | ml-memory | causal-scientist |
| src/infrastructure/postgres/ | postgres-wizard | - |
| src/infrastructure/qdrant/ | vector-specialist | - |
| src/infrastructure/falkordb/ | graph-engineer | - |
| src/infrastructure/nats/ | event-architect | - |
| src/infrastructure/temporal/ | temporal-craftsman | - |
| src/api/ | api-designer | python-craftsman |
| src/workers/gardener/ | temporal-craftsman | - |
| src/workers/projectors/ | event-architect | - |
| src/workers/extractors/ | ml-memory | - |
| src/shared/security/ | privacy-guardian | - |
| src/shared/metrics/ | observability-sre | - |
| tests/ | test-architect | - |
| deploy/ | infra-architect | - |
| docs/ | docs-engineer | - |

---

## Using This Context

When Opus works on any skill:

1. **Read this file first** for architectural understanding
2. **Check ownership map** to know domain boundaries
3. **Reference data flow** to understand skill's place in the system
4. **Use technology details** for specific implementation guidance
5. **Validate against Five Laws** before any change

This context ensures all skills build toward the same vision.
