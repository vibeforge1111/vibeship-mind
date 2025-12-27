# Mind v5 Skill Collaboration Matrix

> **Purpose**: Complete delegation and collaboration mappings for all 20 skills
> **Usage**: Reference when updating collaboration.yaml for each skill

---

## The Collaboration Graph

```
                              ┌─────────────────────┐
                              │   code-reviewer     │
                              │   (reviews all)     │
                              └──────────┬──────────┘
                                         │
         ┌───────────────────────────────┼───────────────────────────────┐
         │                               │                               │
         ▼                               ▼                               ▼
┌─────────────────┐            ┌─────────────────┐            ┌─────────────────┐
│    CORE POD     │            │  PLATFORM POD   │            │ INTERFACE POD   │
│                 │            │                 │            │                 │
│ event-architect │◄──────────►│ infra-architect │◄──────────►│  api-designer   │
│ graph-engineer  │            │ postgres-wizard │            │  sdk-builder    │
│ vector-specialist            │ observability-sre            │  docs-engineer  │
│ temporal-craftsman           │ migration-specialist         │ python-craftsman│
│ ml-memory       │            │ chaos-engineer  │            │                 │
│ causal-scientist│            │                 │            │                 │
└────────┬────────┘            └────────┬────────┘            └────────┬────────┘
         │                               │                               │
         └───────────────────────────────┼───────────────────────────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │    QUALITY POD      │
                              │                     │
                              │  test-architect     │
                              │  privacy-guardian   │
                              │  performance-hunter │
                              │  data-engineer      │
                              └─────────────────────┘
```

---

## Full Delegation Matrix

### Who Delegates to Whom

| Skill | Delegates To | When | Pattern |
|-------|--------------|------|---------|
| **event-architect** | graph-engineer | Entity relationships in events | sequential |
| | vector-specialist | Event content needs embedding | parallel |
| | temporal-craftsman | Long-running event flows | sequential |
| | ml-memory | Memory extraction from events | sequential |
| | privacy-guardian | PII in event schemas | review |
| **graph-engineer** | causal-scientist | Causal inference on graph | sequential |
| | postgres-wizard | Graph-relational sync | parallel |
| | vector-specialist | Entity embeddings | parallel |
| | privacy-guardian | Entity PII concerns | review |
| **vector-specialist** | ml-memory | Memory retrieval integration | sequential |
| | performance-hunter | Search optimization | parallel |
| | graph-engineer | Graph-vector fusion | parallel |
| **temporal-craftsman** | event-architect | Event definitions for workflows | review |
| | infra-architect | Temporal cluster setup | sequential |
| | observability-sre | Workflow monitoring | parallel |
| **ml-memory** | vector-specialist | Embedding strategy | sequential |
| | graph-engineer | Memory-entity linking | parallel |
| | causal-scientist | Outcome attribution | sequential |
| | temporal-craftsman | Consolidation workflows | sequential |
| **causal-scientist** | graph-engineer | Causal edge storage | sequential |
| | data-engineer | Data for causal discovery | sequential |
| | ml-memory | Outcome signals | parallel |
| **privacy-guardian** | *all skills* | Security review | review |
| | infra-architect | Encryption infrastructure | sequential |
| **performance-hunter** | postgres-wizard | Query optimization | sequential |
| | vector-specialist | Search optimization | parallel |
| | observability-sre | Performance metrics | parallel |
| **infra-architect** | observability-sre | Monitoring setup | parallel |
| | chaos-engineer | Resilience testing | sequential |
| | postgres-wizard | Database infrastructure | sequential |
| **postgres-wizard** | migration-specialist | Schema changes | sequential |
| | performance-hunter | Query analysis | parallel |
| **observability-sre** | infra-architect | Alert infrastructure | parallel |
| | chaos-engineer | Incident simulations | sequential |
| **migration-specialist** | postgres-wizard | Schema review | review |
| | event-architect | Event versioning | sequential |
| **chaos-engineer** | infra-architect | Failure injection setup | sequential |
| | observability-sre | Monitoring during tests | parallel |
| **test-architect** | *all skills* | Test coverage | review |
| | chaos-engineer | Resilience tests | sequential |
| **code-reviewer** | *all skills* | Code quality | review |
| **data-engineer** | event-architect | Pipeline events | sequential |
| | postgres-wizard | Data storage | parallel |
| | privacy-guardian | Data privacy | review |
| **api-designer** | docs-engineer | API documentation | sequential |
| | sdk-builder | Client implications | review |
| | code-reviewer | API code review | review |
| **sdk-builder** | api-designer | API contract | review |
| | docs-engineer | SDK documentation | sequential |
| | python-craftsman | Python patterns | review |
| **docs-engineer** | *all skills* | Technical accuracy | review |
| **python-craftsman** | code-reviewer | Pattern review | review |
| | performance-hunter | Performance patterns | parallel |

---

## Collaboration YAML Templates

### For Each Skill's collaboration.yaml

```yaml
# Template structure for collaboration.yaml

prerequisites:
  skills: []  # Skills that must exist before this one
  knowledge:
    - "Required human knowledge 1"
    - "Required human knowledge 2"

complementary_skills:
  - skill: <other-skill-id>
    relationship: "How they work together"
    brings: "What that skill contributes"
    
delegation:
  - trigger: "Natural language trigger"
    delegate_to: <skill-id>
    pattern: sequential|parallel|review
    context: "What to pass to them"
    receive: "What to expect back"

collaboration_patterns:
  sequential:
    - "I do X, then they do Y"
  parallel:
    - "We both work on different aspects"
  review:
    - "They review my work for X concern"

cross_domain_insights:
  - domain: "Field outside our domain"
    insight: "Relevant wisdom from that field"
    applies_when: "When to apply this insight"

mind_v5_specific:
  primary_responsibility: "What this skill owns in Mind v5"
  critical_artifacts:
    - "Key file/component 1"
    - "Key file/component 2"
  metrics_owned:
    - "metric_name: description"
```

---

## Complete Collaboration Maps Per Skill

### 1. event-architect collaboration.yaml

```yaml
prerequisites:
  skills: []
  knowledge:
    - "Event sourcing fundamentals"
    - "Distributed systems basics"
    - "Message queue concepts"

complementary_skills:
  - skill: graph-engineer
    relationship: "Event-to-graph projection"
    brings: "Entity extraction and graph updates from events"
    
  - skill: temporal-craftsman
    relationship: "Saga orchestration"
    brings: "Long-running workflows coordinating events"
    
  - skill: ml-memory
    relationship: "Memory extraction pipeline"
    brings: "MemoryExtracted events from interactions"
    
  - skill: data-engineer
    relationship: "Event pipeline to analytics"
    brings: "Streaming aggregations for federation"

delegation:
  - trigger: "need to store entity relationships from events"
    delegate_to: graph-engineer
    pattern: sequential
    context: "Event schema with entity references"
    receive: "Graph projection implementation"

  - trigger: "need semantic search on event content"
    delegate_to: vector-specialist
    pattern: parallel
    context: "Events needing embedding"
    receive: "Embedding pipeline design"

  - trigger: "need long-running coordinated flow"
    delegate_to: temporal-craftsman
    pattern: sequential
    context: "Event flow requirements"
    receive: "Workflow wrapping events"

  - trigger: "need memory extraction from events"
    delegate_to: ml-memory
    pattern: sequential
    context: "InteractionRecorded event schema"
    receive: "MemoryExtracted event producer"

  - trigger: "schema contains PII"
    delegate_to: privacy-guardian
    pattern: review
    context: "Event schema for review"
    receive: "Approval or required changes"

collaboration_patterns:
  sequential:
    - "I define event schema → graph-engineer creates projection"
    - "I design event flow → temporal-craftsman wraps in workflow"
  parallel:
    - "I handle persistence while vector-specialist handles embeddings"
    - "I store events while data-engineer aggregates patterns"
  review:
    - "privacy-guardian reviews all schemas with user data"
    - "code-reviewer validates event patterns"

cross_domain_insights:
  - domain: accounting
    insight: "Double-entry bookkeeping - every action has compensation"
    applies_when: "Designing saga compensation events"
    
  - domain: version-control
    insight: "Append-only log enables history and rollback"
    applies_when: "Explaining event sourcing benefits"

mind_v5_specific:
  primary_responsibility: "Event backbone and all event schemas"
  critical_artifacts:
    - "src/core/events/*.py"
    - "src/infrastructure/nats/*.py"
    - "src/workers/projectors/*.py"
  metrics_owned:
    - "mind_events_published_total"
    - "mind_event_processing_latency"
    - "mind_projection_lag_seconds"
  critical_events:
    - "InteractionRecorded"
    - "MemoryExtracted"
    - "DecisionMade"
    - "OutcomeObserved"
    - "CausalLinkDiscovered"
    - "PatternValidated"
```

### 2. ml-memory collaboration.yaml

```yaml
prerequisites:
  skills:
    - event-architect  # Needs event infrastructure
  knowledge:
    - "Memory systems concepts"
    - "Hierarchical representation"
    - "Retrieval-augmented generation"

complementary_skills:
  - skill: vector-specialist
    relationship: "Embedding and retrieval"
    brings: "Semantic search over memories"
    
  - skill: graph-engineer
    relationship: "Memory-entity relationships"
    brings: "Graph structure for memory connections"
    
  - skill: causal-scientist
    relationship: "Outcome attribution"
    brings: "Causal analysis of memory effectiveness"
    
  - skill: temporal-craftsman
    relationship: "Consolidation workflows"
    brings: "Scheduled memory maintenance"

delegation:
  - trigger: "need embedding strategy for memories"
    delegate_to: vector-specialist
    pattern: sequential
    context: "Memory content types and retrieval needs"
    receive: "Embedding model and index design"

  - trigger: "need to link memories to entities"
    delegate_to: graph-engineer
    pattern: parallel
    context: "Memory schema and entity extraction"
    receive: "Graph integration for memory-entity links"

  - trigger: "need to understand why memories helped/hurt"
    delegate_to: causal-scientist
    pattern: sequential
    context: "Decision traces with outcomes"
    receive: "Attribution scores for salience updates"

  - trigger: "need scheduled consolidation"
    delegate_to: temporal-craftsman
    pattern: sequential
    context: "Consolidation logic and schedule"
    receive: "MemoryConsolidationWorkflow"

  - trigger: "need to optimize retrieval performance"
    delegate_to: performance-hunter
    pattern: parallel
    context: "Current latency and bottlenecks"
    receive: "Optimization recommendations"

mind_v5_specific:
  primary_responsibility: "Hierarchical memory system with outcome learning"
  critical_artifacts:
    - "src/core/memory/*.py"
    - "src/workers/extractors/*.py"
  metrics_owned:
    - "mind_memory_retrieval_relevance"
    - "mind_memory_salience_distribution"
    - "mind_decision_success_rate"
  hierarchy:
    level_1: "IMMEDIATE - hours, session context"
    level_2: "SITUATIONAL - days/weeks, active tasks"
    level_3: "SEASONAL - months, projects and patterns"
    level_4: "IDENTITY - years, core values and preferences"
```

### 3. privacy-guardian collaboration.yaml

```yaml
prerequisites:
  skills: []  # Reviews all, no dependencies
  knowledge:
    - "Differential privacy theory"
    - "Encryption standards"
    - "GDPR/CCPA requirements"
    - "Security threat modeling"

complementary_skills:
  - skill: infra-architect
    relationship: "Security infrastructure"
    brings: "Encryption key management, network policies"
    
  - skill: data-engineer
    relationship: "Privacy in pipelines"
    brings: "Sanitization in data flows"

delegation:
  - trigger: "need encryption infrastructure"
    delegate_to: infra-architect
    pattern: sequential
    context: "Encryption requirements and key management"
    receive: "Vault setup and key rotation"

  - trigger: "need privacy-preserving aggregation"
    delegate_to: data-engineer
    pattern: sequential
    context: "Aggregation privacy requirements"
    receive: "DP-compliant pipeline design"

# CRITICAL: This skill is consulted by ALL others
receives_from:
  - skill: event-architect
    for: "Event schema PII review"
    pattern: review
    
  - skill: graph-engineer
    for: "Entity data privacy review"
    pattern: review
    
  - skill: ml-memory
    for: "Memory content handling"
    pattern: review
    
  - skill: data-engineer
    for: "Federation pattern sanitization"
    pattern: review
    
  - skill: api-designer
    for: "API data exposure review"
    pattern: review

mind_v5_specific:
  primary_responsibility: "Security, privacy, differential privacy"
  critical_artifacts:
    - "src/shared/security/*.py"
    - "src/workers/gardener/sanitizer.py"
  metrics_owned:
    - "mind_federation_epsilon_budget"
    - "mind_pii_detection_count"
  blocking_authority:
    - "All changes touching user data"
    - "All federation patterns"
    - "All API responses with user content"
  thresholds:
    epsilon: "≤0.1 for federation"
    min_sources: "≥100 for pattern aggregation"
    min_users: "≥10 for cross-user patterns"
```

---

## Cross-Skill Review Requirements

### Mandatory Reviews by Change Type

```yaml
review_requirements:
  
  event_schema_change:
    required:
      - event-architect  # Domain owner
      - privacy-guardian  # PII check
    optional:
      - graph-engineer  # If entity implications
      - ml-memory  # If memory implications

  memory_schema_change:
    required:
      - ml-memory  # Domain owner
      - postgres-wizard  # Schema change
      - privacy-guardian  # Data privacy
    optional:
      - migration-specialist  # If complex migration

  causal_edge_change:
    required:
      - causal-scientist  # Domain owner
      - graph-engineer  # Graph schema
    optional:
      - privacy-guardian  # If user behavior inferred

  api_change:
    required:
      - api-designer  # Domain owner
      - code-reviewer  # Standards
    optional:
      - sdk-builder  # Client impact
      - docs-engineer  # Documentation

  infrastructure_change:
    required:
      - infra-architect  # Domain owner
      - observability-sre  # Monitoring
    optional:
      - chaos-engineer  # Resilience

  workflow_change:
    required:
      - temporal-craftsman  # Domain owner
      - code-reviewer  # Standards
    optional:
      - observability-sre  # Monitoring

  performance_critical:
    required:
      - performance-hunter  # Performance review
      - code-reviewer  # Standards
    optional:
      - postgres-wizard  # If DB involved

  security_sensitive:
    required:
      - privacy-guardian  # BLOCKING
      - code-reviewer  # Standards
    blocking: true

  federation_pattern:
    required:
      - privacy-guardian  # BLOCKING
      - data-engineer  # Pipeline owner
    blocking: true
```

---

## Integration Points

### Event Flow Collaborations

```
InteractionRecorded (event-architect)
         │
         ▼
    ml-memory extracts
         │
         ▼
MemoryExtracted (event-architect)
         │
         ├──► vector-specialist embeds
         │
         └──► graph-engineer links entities
                    │
                    ▼
         causal-scientist discovers edges
                    │
                    ▼
    CausalLinkDiscovered (event-architect)
                    │
                    ▼
         data-engineer aggregates
                    │
                    ▼
    PatternValidated (event-architect)
                    │
                    ▼
    privacy-guardian sanitizes
                    │
                    ▼
         Intent Graph (federated)
```

### Decision Flow Collaborations

```
Context Query
     │
     ▼
ml-memory + vector-specialist + graph-engineer
     │
     ▼
  Fused Context
     │
     ▼
DecisionMade (event-architect)
     │
     ▼
  [Time passes, outcome observed]
     │
     ▼
OutcomeObserved (event-architect)
     │
     ▼
causal-scientist attributes
     │
     ▼
ml-memory updates salience
```

---

## Using This Matrix

1. **When updating any collaboration.yaml**: Reference this matrix for complete relationships
2. **When adding new feature**: Trace through the flow to identify all affected skills
3. **When debugging issues**: Follow the collaboration chain
4. **When onboarding**: Use to understand skill interactions

This matrix ensures no skill operates in isolation—they form a cohesive team.
