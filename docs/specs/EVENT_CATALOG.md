# Mind v5 Event Catalog

> **Version**: 1.0.0
> **Status**: Authoritative Specification
> **Last Updated**: December 27, 2025
> **Owner**: Event Architecture Team

---

## Table of Contents

1. [Event Design Principles](#event-design-principles)
2. [Event Envelope Structure](#event-envelope-structure)
3. [Event Categories](#event-categories)
   - [Memory Events](#1-memory-events)
   - [Decision Events](#2-decision-events)
   - [Causal Events](#3-causal-events)
   - [Federation Events](#4-federation-events)
   - [System Events](#5-system-events)
4. [NATS Subject Naming Convention](#nats-subject-naming-convention)
5. [Event Versioning Strategy](#event-versioning-strategy)
6. [Replay and Projection Rules](#replay-and-projection-rules)
7. [Event Processing Guarantees](#event-processing-guarantees)
8. [Appendix: Complete Schema Reference](#appendix-complete-schema-reference)

---

## Event Design Principles

### The Sacred Laws of Events

Mind v5 is built on event sourcing. These principles are non-negotiable:

#### 1. Immutability is Absolute

```
Events are facts that happened. Facts cannot be changed.

WRONG: Modify event payload after publishing
RIGHT: Publish a new corrective event (e.g., MemoryCorrected)
```

Every event, once published, is permanent. If business logic changes, we publish new events - we never alter history.

#### 2. Events Carry Complete Context

Each event must contain all information needed to understand what happened, without requiring external lookups at read time:

```python
# BAD: Requires lookup to understand what changed
class MemoryUpdated:
    memory_id: UUID  # What changed? Unknown without DB lookup

# GOOD: Self-describing, complete context
class MemoryUpdated:
    memory_id: UUID
    user_id: UUID
    previous_content: str
    new_content: str
    change_reason: str
    changed_fields: List[str]
```

#### 3. Correlation and Causation Are Distinct

Every event carries two IDs that answer different questions:

| ID | Question Answered | Example |
|----|------------------|---------|
| `correlation_id` | "Which business operation?" | User session, API request |
| `causation_id` | "What event caused this?" | The specific triggering event |

```
User clicks "remember this" button
├── InteractionRecorded (correlation=REQ-123, causation=null)
│   └── MemoryExtracted (correlation=REQ-123, causation=InteractionRecorded.event_id)
│       └── EmbeddingGenerated (correlation=REQ-123, causation=MemoryExtracted.event_id)
│           └── MemoryCreated (correlation=REQ-123, causation=EmbeddingGenerated.event_id)
```

#### 4. Events are Domain-Centric, Not Technical

Name events after business concepts, not implementation details:

```python
# BAD: Technical/CRUD naming
class MemoryRowInserted: ...
class DatabaseRecordUpdated: ...

# GOOD: Domain/business naming
class MemoryCreated: ...
class MemoryPromoted: ...
class OutcomeObserved: ...
```

#### 5. Events are Versioned from Day One

Every event type has a schema version. No exceptions.

```python
@dataclass(frozen=True)
class EventEnvelope:
    schema_version: int = 1  # ALWAYS present
```

---

## Event Envelope Structure

All events in Mind v5 share a common envelope structure. The envelope provides metadata; the payload carries domain-specific data.

### Base Event Envelope

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID, uuid4


class EventCategory(Enum):
    """Top-level event categorization."""
    MEMORY = "memory"
    DECISION = "decision"
    CAUSAL = "causal"
    FEDERATION = "federation"
    SYSTEM = "system"


@dataclass(frozen=True)
class EventMetadata:
    """
    Metadata attached to every event.

    These fields enable tracing, debugging, and operational insights
    without exposing sensitive payload data.
    """
    # Tracing
    correlation_id: UUID  # Groups related events (e.g., single user request)
    causation_id: Optional[UUID]  # The event that directly caused this one
    trace_id: Optional[str] = None  # OpenTelemetry trace ID
    span_id: Optional[str] = None  # OpenTelemetry span ID

    # Origin
    source_service: str = "mind-api"  # Which service emitted this
    source_version: str = "1.0.0"  # Service version for debugging

    # Timing
    processing_started_at: Optional[datetime] = None
    processing_duration_ms: Optional[float] = None

    # Privacy
    contains_pii: bool = False  # If true, payload is encrypted
    data_classification: str = "internal"  # internal, confidential, restricted


@dataclass(frozen=True)
class EventEnvelope:
    """
    The universal wrapper for all Mind v5 events.

    This structure enables:
    - Unified serialization/deserialization
    - Consistent routing via NATS subjects
    - Schema evolution without breaking consumers
    - Full audit trail via immutable event log
    """
    # Identity
    event_id: UUID = field(default_factory=uuid4)
    event_type: str = ""  # e.g., "MemoryCreated", "DecisionMade"
    category: EventCategory = EventCategory.SYSTEM

    # Versioning
    schema_version: int = 1

    # Ownership
    user_id: UUID = field(default_factory=uuid4)  # Always present for user-scoped events
    tenant_id: Optional[UUID] = None  # For multi-tenant deployments

    # Timing
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    recorded_at: datetime = field(default_factory=datetime.utcnow)

    # Metadata
    metadata: EventMetadata = field(default_factory=lambda: EventMetadata(
        correlation_id=uuid4(),
        causation_id=None
    ))

    # Payload
    payload: Dict[str, Any] = field(default_factory=dict)

    # Idempotency
    idempotency_key: Optional[str] = None  # For exactly-once processing

    def to_nats_subject(self) -> str:
        """Generate NATS subject for routing."""
        return f"mind.{self.category.value}.{self.event_type.lower()}.{self.user_id}"
```

### Serialization Format

Events are serialized as JSON for NATS transmission. Binary payloads (embeddings, encrypted content) use base64 encoding.

```json
{
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "event_type": "MemoryCreated",
    "category": "memory",
    "schema_version": 1,
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "tenant_id": null,
    "occurred_at": "2025-12-27T10:30:00.000Z",
    "recorded_at": "2025-12-27T10:30:00.001Z",
    "metadata": {
        "correlation_id": "789e0123-e45b-67d8-a901-234567890abc",
        "causation_id": "456e7890-a12b-34c5-d678-901234567890",
        "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
        "span_id": "00f067aa0ba902b7",
        "source_service": "mind-api",
        "source_version": "5.0.1",
        "contains_pii": true,
        "data_classification": "confidential"
    },
    "payload": {
        "memory_id": "def01234-5678-90ab-cdef-ghijklmnopqr",
        "content_encrypted": "gAAAAABj...",
        "temporal_level": "SITUATIONAL",
        "base_salience": 0.75
    },
    "idempotency_key": "mem-create-123e4567-1703673000"
}
```

---

## Event Categories

### 1. Memory Events

Memory events track the complete lifecycle of memories in the hierarchical temporal memory system.

#### MemoryCreated

Published when a new memory is extracted and stored.

```python
@dataclass(frozen=True)
class MemoryCreatedPayload:
    """
    Payload for MemoryCreated events.

    Represents the birth of a memory in the system. Memories are
    created from interactions, never directly by users.
    """
    # Identity
    memory_id: UUID

    # Content (encrypted if contains_pii=True in metadata)
    content: str
    content_type: str  # fact, preference, event, goal, skill, relationship
    content_hash: str  # SHA-256 for deduplication

    # Source
    source_interaction_id: UUID  # The interaction this was extracted from
    extraction_method: str  # "llm_extraction", "rule_based", "user_explicit"
    extraction_confidence: float  # 0.0-1.0

    # Temporal classification
    temporal_level: int  # 1=immediate, 2=situational, 3=seasonal, 4=identity
    valid_from: datetime
    valid_until: Optional[datetime]  # None = indefinite validity

    # Initial scoring
    base_salience: float  # 0.0-1.0, initial importance estimate

    # Embedding reference (actual vector stored in Qdrant)
    embedding_id: Optional[UUID]  # Reference to vector store
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Entity links (references to FalkorDB entities)
    entity_ids: List[UUID] = field(default_factory=list)


# NATS Subject: mind.memory.created.{user_id}
# Schema Version: 1
```

#### MemoryUpdated

Published when memory metadata changes (content is immutable).

```python
@dataclass(frozen=True)
class MemoryUpdatedPayload:
    """
    Payload for MemoryUpdated events.

    Memory content is immutable. This event captures changes to:
    - Temporal validity
    - Salience (via outcome learning)
    - Entity associations
    """
    # Identity
    memory_id: UUID

    # What changed
    updated_fields: List[str]  # ["salience", "valid_until", "entity_ids"]

    # Previous values (for audit/replay)
    previous_values: Dict[str, Any]

    # New values
    new_values: Dict[str, Any]

    # Why
    update_reason: str  # "outcome_feedback", "temporal_expiry", "entity_merge"
    update_source: str  # "gardener_workflow", "api_request", "system_rule"


# NATS Subject: mind.memory.updated.{user_id}
# Schema Version: 1
```

#### MemoryPromoted

Published when a memory moves to a higher temporal level (proving stability).

```python
@dataclass(frozen=True)
class MemoryPromotedPayload:
    """
    Payload for MemoryPromoted events.

    Memories that prove stable and valuable over time are promoted
    to higher temporal levels (situational -> seasonal -> identity).
    """
    # Identity
    memory_id: UUID

    # Promotion details
    previous_level: int  # 1, 2, or 3
    new_level: int  # 2, 3, or 4

    # Evidence
    stability_score: float  # How consistent this memory has been
    retrieval_count: int  # How often retrieved
    positive_outcome_count: int  # How many good decisions it supported
    decision_support_rate: float  # positive / total decisions using this

    # Temporal stats
    first_observed: datetime
    promotion_threshold_met_at: datetime
    observation_window_days: int


# NATS Subject: mind.memory.promoted.{user_id}
# Schema Version: 1
```

#### MemoryDecayed

Published when a memory loses salience due to disuse or negative outcomes.

```python
@dataclass(frozen=True)
class MemoryDecayedPayload:
    """
    Payload for MemoryDecayed events.

    Memories that consistently lead to poor outcomes or are never
    retrieved gradually decay. Heavy decay may lead to archival.
    """
    # Identity
    memory_id: UUID

    # Decay details
    previous_salience: float
    new_salience: float
    decay_amount: float

    # Why decayed
    decay_reason: str  # "negative_outcomes", "disuse", "contradiction", "temporal_expiry"

    # Evidence
    days_since_last_retrieval: int
    negative_outcome_count: int
    contradiction_memory_ids: List[UUID]  # If decayed due to contradiction

    # Outcome
    archived: bool  # If salience dropped below threshold


# NATS Subject: mind.memory.decayed.{user_id}
# Schema Version: 1
```

#### MemoryMerged

Published when duplicate or highly similar memories are consolidated.

```python
@dataclass(frozen=True)
class MemoryMergedPayload:
    """
    Payload for MemoryMerged events.

    The Gardener workflow periodically identifies and merges
    duplicate or highly similar memories to prevent bloat.
    """
    # Identity
    surviving_memory_id: UUID
    merged_memory_ids: List[UUID]  # Memories that were absorbed

    # Merge details
    merge_reason: str  # "semantic_duplicate", "temporal_overlap", "entity_consolidation"
    similarity_scores: Dict[str, float]  # {merged_id: similarity_score}

    # Result
    combined_retrieval_count: int
    combined_outcome_adjustment: float


# NATS Subject: mind.memory.merged.{user_id}
# Schema Version: 1
```

---

### 2. Decision Events

Decision events implement the decision outcome tracking system - the core of Mind v5's learning capability.

#### DecisionRequested

Published when an agent requests context for a decision.

```python
@dataclass(frozen=True)
class DecisionRequestedPayload:
    """
    Payload for DecisionRequested events.

    This event marks the start of a decision flow. The context
    retrieval that follows will be traced back to this request.
    """
    # Identity
    decision_id: UUID
    session_id: UUID

    # Request details
    query: str  # The question or context needed
    decision_type: str  # "recommendation", "classification", "generation", "planning"

    # Constraints
    required_temporal_levels: List[int]  # [1, 4] = immediate + identity
    max_memories: int
    max_latency_ms: int
    include_causal_context: bool
    include_federated_patterns: bool

    # Requester
    requesting_agent_id: Optional[UUID]
    requesting_service: str


# NATS Subject: mind.decision.requested.{user_id}
# Schema Version: 1
```

#### ContextRetrieved

Published when context is successfully retrieved for a decision.

```python
@dataclass(frozen=True)
class ContextRetrievedPayload:
    """
    Payload for ContextRetrieved events.

    Captures exactly what context was provided for a decision.
    This snapshot is critical for outcome attribution.
    """
    # Identity
    decision_id: UUID
    retrieval_id: UUID

    # Retrieved memories
    memory_ids: List[UUID]
    memory_scores: Dict[str, float]  # {memory_id: relevance_score}
    memory_sources: Dict[str, str]  # {memory_id: "vector"|"graph"|"keyword"}

    # Retrieved causal context
    causal_edge_ids: List[UUID]
    causal_paths: List[List[str]]  # Paths traversed in graph

    # Retrieved patterns (from Intent Graph)
    pattern_ids: List[UUID]
    pattern_relevance: Dict[str, float]

    # Performance
    retrieval_latency_ms: float
    vector_search_ms: float
    graph_traversal_ms: float
    fusion_ms: float

    # Fusion details
    fusion_method: str  # "rrf", "weighted_sum", "learned"
    reranker_model: Optional[str]

    # Context snapshot (for replay/audit - may be large)
    context_snapshot: Dict[str, Any]  # Full context provided to decision maker


# NATS Subject: mind.decision.context_retrieved.{user_id}
# Schema Version: 1
```

#### DecisionMade

Published when a decision is finalized.

```python
@dataclass(frozen=True)
class DecisionMadePayload:
    """
    Payload for DecisionMade events.

    Records the actual decision made, the context used, and the
    confidence level. This is the anchor for outcome tracking.
    """
    # Identity
    decision_id: UUID
    trace_id: UUID  # Links to decision_traces table

    # Decision details
    decision_type: str
    decision_content: str  # The actual decision/recommendation
    decision_rationale: Optional[str]  # Why this decision

    # Confidence
    confidence: float  # 0.0-1.0
    confidence_factors: Dict[str, float]  # What contributed to confidence

    # Alternatives
    alternatives_considered: List[Dict[str, Any]]
    rejection_reasons: Dict[str, str]  # {alternative: reason}

    # Context used (references)
    memory_ids_used: List[UUID]
    memory_weights: Dict[str, float]  # How much each memory contributed
    causal_edges_used: List[UUID]
    patterns_applied: List[UUID]

    # Maker
    decision_maker: str  # "claude_haiku", "gpt4", "rule_engine"
    decision_maker_version: str


# NATS Subject: mind.decision.made.{user_id}
# Schema Version: 1
```

#### OutcomeObserved

Published when feedback on a decision is received.

```python
@dataclass(frozen=True)
class OutcomeObservedPayload:
    """
    Payload for OutcomeObserved events.

    This is the learning signal. Every observed outcome triggers
    memory salience updates and causal strength adjustments.
    """
    # Identity
    decision_id: UUID
    outcome_id: UUID

    # Outcome measurement
    outcome_quality: float  # -1.0 (terrible) to 1.0 (excellent)
    outcome_type: str  # "explicit_feedback", "implicit_signal", "inferred"

    # Signal source
    signal_source: str  # "user_rating", "task_completion", "engagement", "correction"
    signal_confidence: float  # How sure are we about this signal

    # Timing
    decision_to_outcome_ms: int  # Latency between decision and outcome

    # Raw signal (for audit)
    raw_signal: Dict[str, Any]  # The actual feedback received

    # Attribution (computed by attribution workflow)
    memory_attribution: Dict[str, float]  # {memory_id: contribution_score}
    causal_attribution: Dict[str, float]  # {edge_id: contribution_score}
    pattern_attribution: Dict[str, float]  # {pattern_id: contribution_score}


# NATS Subject: mind.decision.outcome_observed.{user_id}
# Schema Version: 1
```

#### AttributionComputed

Published when outcome attribution analysis completes.

```python
@dataclass(frozen=True)
class AttributionComputedPayload:
    """
    Payload for AttributionComputed events.

    After an outcome is observed, the attribution workflow determines
    which memories, edges, and patterns contributed to the result.
    """
    # Identity
    decision_id: UUID
    outcome_id: UUID
    attribution_id: UUID

    # Method
    attribution_method: str  # "shapley", "gradient", "counterfactual"

    # Memory impact
    memory_adjustments: Dict[str, float]  # {memory_id: salience_delta}
    memories_promoted: List[UUID]
    memories_demoted: List[UUID]

    # Causal impact
    edge_adjustments: Dict[str, float]  # {edge_id: strength_delta}
    edges_validated: List[UUID]
    edges_weakened: List[UUID]

    # Pattern impact
    pattern_adjustments: Dict[str, float]
    patterns_reinforced: List[UUID]

    # Metrics
    attribution_confidence: float
    computation_time_ms: float


# NATS Subject: mind.decision.attribution_computed.{user_id}
# Schema Version: 1
```

---

### 3. Causal Events

Causal events track the discovery, validation, and evolution of cause-effect relationships.

#### CausalEdgeCreated

Published when a new causal relationship is discovered.

```python
@dataclass(frozen=True)
class CausalEdgeCreatedPayload:
    """
    Payload for CausalEdgeCreated events.

    Represents discovery of a cause-effect relationship between
    entities in the knowledge graph.
    """
    # Identity
    edge_id: UUID

    # Endpoints
    source_entity_id: UUID
    source_entity_type: str
    target_entity_id: UUID
    target_entity_type: str

    # Relationship
    relationship_type: str  # "causes", "prevents", "enables", "correlates"
    causal_direction: str  # "forward", "reverse", "bidirectional"

    # Strength
    initial_strength: float  # 0.0-1.0
    confidence: float

    # Temporal context
    valid_from: datetime
    valid_until: Optional[datetime]
    temporal_conditions: List[str]  # ["morning", "weekday", "high_stress"]

    # Conditions
    activation_conditions: List[str]  # When this edge applies

    # Discovery
    discovery_method: str  # "doWhy_backdoor", "pattern_mining", "user_stated"
    evidence_count: int
    supporting_decision_ids: List[UUID]

    # Counterfactual
    counterfactual_statement: Optional[str]
    estimated_effect_size: Optional[float]


# NATS Subject: mind.causal.edge_created.{user_id}
# Schema Version: 1
```

#### CausalStrengthUpdated

Published when evidence changes a causal relationship's strength.

```python
@dataclass(frozen=True)
class CausalStrengthUpdatedPayload:
    """
    Payload for CausalStrengthUpdated events.

    Causal edges strengthen or weaken based on observed outcomes.
    """
    # Identity
    edge_id: UUID

    # Change
    previous_strength: float
    new_strength: float
    strength_delta: float

    # Evidence
    update_reason: str  # "positive_outcome", "negative_outcome", "new_evidence", "contradiction"
    supporting_outcome_ids: List[UUID]
    evidence_count_delta: int
    new_total_evidence: int

    # Confidence
    previous_confidence: float
    new_confidence: float


# NATS Subject: mind.causal.strength_updated.{user_id}
# Schema Version: 1
```

#### CausalCycleDetected

Published when a cycle is detected in the causal graph.

```python
@dataclass(frozen=True)
class CausalCycleDetectedPayload:
    """
    Payload for CausalCycleDetected events.

    Cycles in causal graphs indicate either feedback loops (valid)
    or modeling errors (invalid). This event triggers review.
    """
    # Identity
    detection_id: UUID

    # Cycle
    cycle_edges: List[UUID]  # Edges forming the cycle
    cycle_path: List[str]  # Human-readable path: "A -> B -> C -> A"

    # Analysis
    cycle_type: str  # "feedback_loop", "modeling_error", "temporal_paradox"
    severity: str  # "info", "warning", "error"

    # Resolution
    suggested_resolution: str
    auto_resolved: bool
    resolution_action: Optional[str]


# NATS Subject: mind.causal.cycle_detected.{user_id}
# Schema Version: 1
```

#### CausalGraphPruned

Published when the causal discovery workflow prunes weak edges.

```python
@dataclass(frozen=True)
class CausalGraphPrunedPayload:
    """
    Payload for CausalGraphPruned events.

    Periodic maintenance removes edges that lack evidence
    or have been consistently contradicted.
    """
    # Identity
    prune_id: UUID

    # Scope
    edges_evaluated: int
    edges_pruned: int
    pruned_edge_ids: List[UUID]

    # Criteria
    min_strength_threshold: float
    min_evidence_threshold: int
    max_age_days: int

    # Results
    graph_size_before: int
    graph_size_after: int

    # Triggered by
    trigger: str  # "scheduled", "manual", "threshold_exceeded"


# NATS Subject: mind.causal.graph_pruned.{user_id}
# Schema Version: 1
```

---

### 4. Federation Events

Federation events enable collective intelligence while preserving privacy.

#### PatternExtracted

Published when a reusable pattern is identified from user data.

```python
@dataclass(frozen=True)
class PatternExtractedPayload:
    """
    Payload for PatternExtracted events.

    Patterns are abstracted, anonymized learnings that can
    potentially be shared across users.
    """
    # Identity
    pattern_id: UUID

    # Pattern definition
    trigger_type: str  # Abstract category: "frustration", "confusion", "delight"
    trigger_indicators: List[str]  # Abstract signals, NO PII
    response_strategy: str  # What works

    # Evidence
    source_decision_count: int
    positive_outcome_rate: float
    outcome_improvement: float  # vs baseline
    confidence_interval: Dict[str, float]  # {"lower": 0.12, "upper": 0.18}

    # Privacy status
    pii_detected: bool
    sanitization_applied: bool
    sanitization_method: Optional[str]

    # Federation eligibility
    eligible_for_federation: bool
    ineligibility_reason: Optional[str]


# NATS Subject: mind.federation.pattern_extracted.{user_id}
# Schema Version: 1
```

#### PatternPublished

Published when a pattern is approved for the Intent Graph.

```python
@dataclass(frozen=True)
class PatternPublishedPayload:
    """
    Payload for PatternPublished events.

    A pattern has passed privacy validation and is now available
    in the shared Intent Graph for cross-user benefit.
    """
    # Identity
    pattern_id: UUID
    intent_graph_id: UUID  # ID in the shared graph

    # Sanitized pattern (NO PII, NO user-specific content)
    trigger_type: str
    trigger_indicators: List[str]
    response_strategy: str
    response_template: Optional[str]

    # Aggregated evidence
    source_count: int  # Must be >= 100
    user_count: int  # Must be >= 10
    outcome_improvement: float
    confidence: float

    # Privacy guarantees
    differential_privacy_epsilon: float  # Must be <= 0.1
    k_anonymity: int  # Must be >= 10

    # Validation
    privacy_review_id: UUID
    published_at: datetime


# NATS Subject: mind.federation.pattern_published (global, not user-scoped)
# Schema Version: 1
```

#### PatternConsumed

Published when a user's Mind uses a federated pattern.

```python
@dataclass(frozen=True)
class PatternConsumedPayload:
    """
    Payload for PatternConsumed events.

    Tracks when federated patterns are used, enabling
    measurement of collective intelligence benefit.
    """
    # Identity
    consumption_id: UUID
    pattern_id: UUID
    intent_graph_id: UUID

    # Usage context
    decision_id: UUID
    trigger_matched: bool
    response_applied: bool

    # Adaptation
    local_adaptation: Optional[str]  # How pattern was customized

    # For measurement
    baseline_confidence: float  # Confidence without pattern
    pattern_boost: float  # Additional confidence from pattern


# NATS Subject: mind.federation.pattern_consumed.{user_id}
# Schema Version: 1
```

#### PatternFeedback

Published when outcome data contributes back to pattern quality.

```python
@dataclass(frozen=True)
class PatternFeedbackPayload:
    """
    Payload for PatternFeedback events.

    Outcomes from pattern usage flow back to improve
    the shared pattern (with privacy protection).
    """
    # Identity
    feedback_id: UUID
    pattern_id: UUID
    consumption_id: UUID

    # Feedback (aggregated, not raw)
    outcome_quality: float  # -1 to 1, with noise added

    # Differential privacy
    noise_added: float
    epsilon_consumed: float

    # Pattern impact
    pattern_effectiveness_delta: float  # Change to pattern's effectiveness score


# NATS Subject: mind.federation.pattern_feedback (global)
# Schema Version: 1
```

---

### 5. System Events

System events track infrastructure and lifecycle concerns.

#### UserCreated

Published when a new user is onboarded.

```python
@dataclass(frozen=True)
class UserCreatedPayload:
    """
    Payload for UserCreated events.

    Initializes a user's Mind with default settings.
    """
    # Identity
    user_id: UUID

    # Tenant (for multi-tenant)
    tenant_id: Optional[UUID]

    # Settings
    privacy_level: str  # "strict", "balanced", "open"
    federation_opt_in: bool
    retention_policy: str

    # Encryption
    encryption_key_id: UUID  # Reference to key in Vault

    # Initial state
    initial_memories_count: int = 0


# NATS Subject: mind.system.user_created.{user_id}
# Schema Version: 1
```

#### SessionStarted

Published when a new interaction session begins.

```python
@dataclass(frozen=True)
class SessionStartedPayload:
    """
    Payload for SessionStarted events.

    Sessions group related interactions and decisions.
    """
    # Identity
    session_id: UUID

    # Context
    session_type: str  # "interactive", "batch", "background"
    client_info: Dict[str, str]  # Browser, app version, etc. (no PII)

    # Timing
    expected_duration_minutes: Optional[int]

    # Continuity
    previous_session_id: Optional[UUID]
    days_since_last_session: Optional[int]


# NATS Subject: mind.system.session_started.{user_id}
# Schema Version: 1
```

#### SessionEnded

Published when a session concludes.

```python
@dataclass(frozen=True)
class SessionEndedPayload:
    """
    Payload for SessionEnded events.

    Captures session summary for analytics.
    """
    # Identity
    session_id: UUID

    # Duration
    duration_seconds: int

    # Activity
    interaction_count: int
    decision_count: int
    memory_created_count: int

    # Outcomes
    positive_outcomes: int
    negative_outcomes: int
    pending_outcomes: int

    # Termination
    end_reason: str  # "user_logout", "timeout", "error", "client_disconnect"


# NATS Subject: mind.system.session_ended.{user_id}
# Schema Version: 1
```

#### InteractionRecorded

Published for every raw interaction (the source of truth).

```python
@dataclass(frozen=True)
class InteractionRecordedPayload:
    """
    Payload for InteractionRecorded events.

    Every user interaction is recorded before any processing.
    This is the raw input that memory extraction acts on.
    """
    # Identity
    interaction_id: UUID
    session_id: UUID

    # Content (encrypted)
    content_type: str  # "text", "voice_transcript", "action", "feedback"
    content_encrypted: bytes  # Always encrypted
    content_length: int  # For analytics without decryption

    # Context
    interaction_context: Dict[str, Any]  # UI state, previous turns, etc.

    # Timing
    client_timestamp: datetime  # When user initiated
    server_timestamp: datetime  # When server received

    # Processing hints
    extraction_priority: str  # "immediate", "batch", "skip"
    requires_response: bool


# NATS Subject: mind.system.interaction_recorded.{user_id}
# Schema Version: 1
```

#### GardenerWorkflowCompleted

Published when a Temporal workflow completes.

```python
@dataclass(frozen=True)
class GardenerWorkflowCompletedPayload:
    """
    Payload for GardenerWorkflowCompleted events.

    Tracks completion of background maintenance workflows.
    """
    # Identity
    workflow_id: str  # Temporal workflow ID
    workflow_run_id: str  # Temporal run ID

    # Workflow type
    workflow_type: str  # "memory_consolidation", "causal_discovery", "pattern_federation"

    # Scope
    users_processed: int

    # Results
    status: str  # "completed", "failed", "timed_out", "cancelled"
    items_processed: int
    items_modified: int
    errors: List[Dict[str, Any]]

    # Performance
    duration_seconds: int
    activities_executed: int
    retries_total: int


# NATS Subject: mind.system.gardener_completed (global)
# Schema Version: 1
```

#### SystemHealthChanged

Published when system health status changes.

```python
@dataclass(frozen=True)
class SystemHealthChangedPayload:
    """
    Payload for SystemHealthChanged events.

    Enables automated response to health changes.
    """
    # Identity
    health_check_id: UUID

    # Status
    previous_status: str  # "healthy", "degraded", "unhealthy"
    new_status: str

    # Component
    component: str  # "postgres", "qdrant", "falkordb", "nats", "temporal"

    # Details
    check_type: str  # "connectivity", "latency", "capacity"
    check_result: Dict[str, Any]
    threshold_breached: Optional[str]

    # Impact
    affected_capabilities: List[str]


# NATS Subject: mind.system.health_changed (global)
# Schema Version: 1
```

---

## NATS Subject Naming Convention

### Subject Hierarchy

```
mind.{category}.{event_type}.{user_id}

Examples:
  mind.memory.created.550e8400-e29b-41d4-a716-446655440000
  mind.decision.made.550e8400-e29b-41d4-a716-446655440000
  mind.causal.edge_created.550e8400-e29b-41d4-a716-446655440000
  mind.federation.pattern_published  (no user_id - global)
  mind.system.health_changed  (no user_id - global)
```

### Subscription Patterns

```
# All events for a specific user
mind.*.*.550e8400-e29b-41d4-a716-446655440000

# All memory events across all users
mind.memory.*.*

# All events of a specific type
mind.*.created.*

# All global events (no user scope)
mind.federation.>
mind.system.health_*
```

### Stream Configuration

```yaml
# NATS JetStream stream definition
streams:
  # User-scoped events (partitioned by user)
  - name: mind-user-events
    subjects:
      - "mind.memory.*.>"
      - "mind.decision.*.>"
      - "mind.causal.*.>"
      - "mind.system.session_*.>"
      - "mind.system.interaction_recorded.>"
    retention: limits
    max_age: 365d  # 1 year retention
    max_bytes: 10GB
    storage: file
    replicas: 3

  # Global events (federation, system)
  - name: mind-global-events
    subjects:
      - "mind.federation.pattern_published"
      - "mind.federation.pattern_feedback"
      - "mind.system.gardener_completed"
      - "mind.system.health_changed"
    retention: limits
    max_age: 90d  # 90 day retention for global
    storage: file
    replicas: 3
```

### Consumer Groups

```yaml
consumers:
  # Memory projector - maintains memory read model
  - name: memory-projector
    stream: mind-user-events
    filter_subject: "mind.memory.*.>"
    deliver_policy: all
    ack_policy: explicit
    max_deliver: 5

  # Decision tracker - maintains decision traces
  - name: decision-tracker
    stream: mind-user-events
    filter_subject: "mind.decision.*.>"
    deliver_policy: all
    ack_policy: explicit

  # Causal graph updater
  - name: causal-projector
    stream: mind-user-events
    filter_subject: "mind.causal.*.>"
    deliver_policy: all
    ack_policy: explicit

  # Pattern aggregator (for Intent Graph)
  - name: pattern-aggregator
    stream: mind-global-events
    filter_subject: "mind.federation.>"
    deliver_policy: all
    ack_policy: explicit
```

---

## Event Versioning Strategy

### Version Numbering

Events use semantic versioning within their schema:

```
Schema Version: MAJOR.MINOR (stored as integer for simplicity)

MAJOR (breaking): 1 -> 2
  - Field removed
  - Field type changed incompatibly
  - Required field added

MINOR (compatible): 1 -> 1 (tracked in metadata)
  - Optional field added
  - Field deprecated (but still present)
  - Enum value added
```

### Schema Evolution Rules

#### Rule 1: Never Remove Fields

```python
# Version 1
@dataclass
class MemoryCreatedV1:
    memory_id: UUID
    content: str
    salience: float  # Oops, we want to rename this

# Version 2 - WRONG approach
@dataclass
class MemoryCreatedV2:
    memory_id: UUID
    content: str
    base_salience: float  # Removed 'salience', added 'base_salience'

# Version 2 - CORRECT approach
@dataclass
class MemoryCreatedV2:
    memory_id: UUID
    content: str
    salience: float  # Keep old field (deprecated)
    base_salience: float  # Add new field
```

#### Rule 2: New Required Fields Need Defaults

```python
# Version 1
@dataclass
class DecisionMadeV1:
    decision_id: UUID
    content: str

# Version 2 - Adding required field
@dataclass
class DecisionMadeV2:
    decision_id: UUID
    content: str
    confidence: float = 0.5  # DEFAULT for old events during replay
```

#### Rule 3: Type Widening Only

```python
# Allowed: int -> float, str -> Optional[str]
# Not allowed: float -> int, Optional[str] -> str
```

### Upcasting During Replay

When replaying events, consumers must upcast old versions:

```python
class EventUpcaster:
    """Transform old event versions to current schema."""

    @staticmethod
    def upcast_memory_created(event: dict, from_version: int) -> MemoryCreatedPayload:
        if from_version == 1:
            # V1 had 'salience', V2 split into 'base_salience' + 'outcome_adjustment'
            return MemoryCreatedPayload(
                memory_id=event["memory_id"],
                content=event["content"],
                base_salience=event.get("salience", 0.5),  # Use old field
                outcome_adjustment=0.0,  # Default for new field
                # ... other fields with defaults
            )
        elif from_version == 2:
            return MemoryCreatedPayload(**event)
        else:
            raise UnknownSchemaVersion(from_version)
```

### Version Registry

```python
# src/core/events/registry.py

EVENT_VERSIONS = {
    "MemoryCreated": {
        "current": 2,
        "supported": [1, 2],
        "deprecated": [1],
        "upcaster": MemoryCreatedUpcaster,
    },
    "DecisionMade": {
        "current": 1,
        "supported": [1],
        "deprecated": [],
        "upcaster": None,
    },
    # ... all event types
}
```

---

## Replay and Projection Rules

### Projection Architecture

```
Events (NATS) ─────────────────────────────────────────────────────────┐
                                                                        │
    ┌──────────────────────────────────────────────────────────────────┤
    │                                                                   │
    ▼                                                                   ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Memory     │   │  Decision   │   │  Causal     │   │  Pattern    │
│  Projector  │   │  Projector  │   │  Projector  │   │  Projector  │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │                 │                 │                 │
       ▼                 ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ PostgreSQL  │   │ PostgreSQL  │   │  FalkorDB   │   │ PostgreSQL  │
│ + Qdrant    │   │             │   │             │   │ TimescaleDB │
│ (memories)  │   │ (traces)    │   │ (graph)     │   │ (patterns)  │
└─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
```

### Projection Handlers

Each projector subscribes to relevant events and maintains read models:

```python
# src/workers/projectors/memory_projector.py

class MemoryProjector:
    """
    Maintains the memory read model from events.

    Subscribes to: mind.memory.*.*
    Writes to: PostgreSQL (memories table), Qdrant (embeddings)
    """

    async def handle_memory_created(self, event: EventEnvelope) -> None:
        """Project MemoryCreated event."""
        payload = MemoryCreatedPayload(**event.payload)

        # Idempotency check
        if await self.db.memory_exists(payload.memory_id):
            logger.info("memory_already_projected", memory_id=str(payload.memory_id))
            return

        # Write to PostgreSQL
        await self.db.insert_memory(
            memory_id=payload.memory_id,
            user_id=event.user_id,
            content=payload.content,
            temporal_level=payload.temporal_level,
            base_salience=payload.base_salience,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
            created_at=event.occurred_at,
        )

        # Write embedding to Qdrant
        if payload.embedding_id:
            await self.qdrant.upsert_point(
                collection="memories",
                id=str(payload.memory_id),
                vector=await self.get_embedding(payload.embedding_id),
                payload={
                    "user_id": str(event.user_id),
                    "temporal_level": payload.temporal_level,
                    "salience": payload.base_salience,
                }
            )

        # Update projection checkpoint
        await self.checkpoint.advance(event.event_id)

    async def handle_memory_updated(self, event: EventEnvelope) -> None:
        """Project MemoryUpdated event."""
        payload = MemoryUpdatedPayload(**event.payload)

        # Apply updates
        await self.db.update_memory(
            memory_id=payload.memory_id,
            updates=payload.new_values,
        )

        # Update Qdrant metadata if salience changed
        if "base_salience" in payload.updated_fields or "outcome_adjustment" in payload.updated_fields:
            salience = payload.new_values.get("base_salience", 0) + payload.new_values.get("outcome_adjustment", 0)
            await self.qdrant.update_payload(
                collection="memories",
                id=str(payload.memory_id),
                payload={"salience": salience}
            )

        await self.checkpoint.advance(event.event_id)
```

### Replay Procedure

When a projection needs to be rebuilt:

```python
# src/workers/projectors/replay.py

async def replay_projection(
    projector: Projector,
    from_event_id: Optional[UUID] = None,
    to_event_id: Optional[UUID] = None,
) -> ReplayResult:
    """
    Rebuild a projection from event history.

    Steps:
    1. Pause live consumption
    2. Clear projection state (optional)
    3. Replay events in order
    4. Resume live consumption
    """
    logger.info("replay_started", projector=projector.name)

    # Pause live consumer
    await projector.pause()

    # Get events to replay
    events = await event_store.get_events(
        subjects=projector.subscribed_subjects,
        from_id=from_event_id,
        to_id=to_event_id,
        order="asc",
    )

    # Replay with progress tracking
    replayed = 0
    errors = []

    for event in events:
        try:
            # Upcast if needed
            upcasted = upcast_event(event)

            # Process
            await projector.handle(upcasted)
            replayed += 1

            if replayed % 10000 == 0:
                logger.info("replay_progress", replayed=replayed)

        except Exception as e:
            errors.append({"event_id": str(event.event_id), "error": str(e)})
            if len(errors) > 100:
                raise ReplayAborted("Too many errors")

    # Resume live consumption
    await projector.resume()

    logger.info("replay_completed", replayed=replayed, errors=len(errors))

    return ReplayResult(
        replayed=replayed,
        errors=errors,
        duration_seconds=elapsed,
    )
```

### Projection Checkpoints

Each projector maintains a checkpoint to enable resume after failure:

```sql
-- PostgreSQL: projection checkpoints
CREATE TABLE projection_checkpoints (
    projector_name VARCHAR(100) PRIMARY KEY,
    last_event_id UUID NOT NULL,
    last_event_timestamp TIMESTAMPTZ NOT NULL,
    events_processed BIGINT DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);
```

### Consistency Guarantees

| Guarantee | Implementation |
|-----------|---------------|
| **At-least-once delivery** | NATS JetStream with explicit ACK |
| **Idempotent processing** | Event ID checked before processing |
| **Ordered per user** | Partition by user_id in NATS |
| **Eventual consistency** | Projections may lag events by seconds |

---

## Event Processing Guarantees

### Exactly-Once Semantics

While NATS provides at-least-once delivery, we achieve exactly-once through idempotency:

```python
class IdempotentEventHandler:
    """Wrapper for exactly-once event processing."""

    def __init__(self, handler: Callable, dedup_store: DedupStore):
        self.handler = handler
        self.dedup_store = dedup_store

    async def process(self, event: EventEnvelope) -> None:
        # Check idempotency key
        key = event.idempotency_key or str(event.event_id)

        if await self.dedup_store.was_processed(key):
            logger.debug("event_already_processed", key=key)
            return

        # Process
        try:
            await self.handler(event)
            await self.dedup_store.mark_processed(key)
        except Exception as e:
            # Don't mark as processed - will retry
            raise
```

### Dead Letter Queue

Failed events after max retries go to DLQ:

```yaml
# DLQ stream configuration
streams:
  - name: mind-dlq
    subjects:
      - "mind.dlq.>"
    retention: limits
    max_age: 30d
    storage: file
```

```python
async def handle_with_dlq(event: EventEnvelope, max_retries: int = 5) -> None:
    for attempt in range(max_retries):
        try:
            await process_event(event)
            return
        except RetryableError as e:
            logger.warning("event_processing_retry", attempt=attempt, error=str(e))
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
        except NonRetryableError as e:
            logger.error("event_processing_failed", error=str(e))
            break

    # Send to DLQ
    await nats.publish(
        f"mind.dlq.{event.category.value}.{event.event_type}",
        event.to_json(),
    )
    logger.error("event_sent_to_dlq", event_id=str(event.event_id))
```

### Backpressure Handling

```python
class BackpressureAwareConsumer:
    """Consumer that respects processing capacity."""

    def __init__(self, max_concurrent: int = 100):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.pending = 0

    async def consume(self, msg: NATSMessage) -> None:
        async with self.semaphore:
            self.pending += 1
            try:
                event = EventEnvelope.from_json(msg.data)
                await self.process(event)
                await msg.ack()
            except Exception as e:
                await msg.nak()  # Will be redelivered
            finally:
                self.pending -= 1
```

---

## Appendix: Complete Schema Reference

### Event Type Index

| Category | Event Type | Subject Pattern | Schema Version |
|----------|-----------|-----------------|----------------|
| **Memory** | MemoryCreated | mind.memory.created.{user_id} | 1 |
| | MemoryUpdated | mind.memory.updated.{user_id} | 1 |
| | MemoryPromoted | mind.memory.promoted.{user_id} | 1 |
| | MemoryDecayed | mind.memory.decayed.{user_id} | 1 |
| | MemoryMerged | mind.memory.merged.{user_id} | 1 |
| **Decision** | DecisionRequested | mind.decision.requested.{user_id} | 1 |
| | ContextRetrieved | mind.decision.context_retrieved.{user_id} | 1 |
| | DecisionMade | mind.decision.made.{user_id} | 1 |
| | OutcomeObserved | mind.decision.outcome_observed.{user_id} | 1 |
| | AttributionComputed | mind.decision.attribution_computed.{user_id} | 1 |
| **Causal** | CausalEdgeCreated | mind.causal.edge_created.{user_id} | 1 |
| | CausalStrengthUpdated | mind.causal.strength_updated.{user_id} | 1 |
| | CausalCycleDetected | mind.causal.cycle_detected.{user_id} | 1 |
| | CausalGraphPruned | mind.causal.graph_pruned.{user_id} | 1 |
| **Federation** | PatternExtracted | mind.federation.pattern_extracted.{user_id} | 1 |
| | PatternPublished | mind.federation.pattern_published | 1 |
| | PatternConsumed | mind.federation.pattern_consumed.{user_id} | 1 |
| | PatternFeedback | mind.federation.pattern_feedback | 1 |
| **System** | UserCreated | mind.system.user_created.{user_id} | 1 |
| | SessionStarted | mind.system.session_started.{user_id} | 1 |
| | SessionEnded | mind.system.session_ended.{user_id} | 1 |
| | InteractionRecorded | mind.system.interaction_recorded.{user_id} | 1 |
| | GardenerWorkflowCompleted | mind.system.gardener_completed | 1 |
| | SystemHealthChanged | mind.system.health_changed | 1 |

### Field Type Reference

| Python Type | JSON Type | Notes |
|-------------|-----------|-------|
| `UUID` | string | UUID v4 format |
| `datetime` | string | ISO 8601 with timezone |
| `Optional[T]` | T \| null | Null when not present |
| `List[T]` | array | May be empty |
| `Dict[str, T]` | object | Keys are strings |
| `bytes` | string | Base64 encoded |
| `float` | number | Double precision |
| `int` | integer | 64-bit signed |
| `bool` | boolean | true/false |
| `Enum` | string | Enum value as string |

### Metrics Exposed

Each event type emits standard metrics:

```python
# Counters
mind_events_published_total{category, event_type, user_id_hash}
mind_events_processed_total{category, event_type, projector}
mind_events_failed_total{category, event_type, error_type}

# Histograms
mind_event_publish_latency_seconds{category, event_type}
mind_event_processing_latency_seconds{category, event_type, projector}

# Gauges
mind_event_stream_lag_seconds{stream, consumer}
mind_dlq_depth{category}
```

---

## Document Metadata

| Field | Value |
|-------|-------|
| **Specification Version** | 1.0.0 |
| **Status** | Draft -> Review -> **Approved** |
| **Reviewers** | Event Architecture Team |
| **Approval Date** | December 27, 2025 |
| **Next Review** | March 27, 2026 |

### Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-27 | Event Architecture Team | Initial specification |

---

*This document is the authoritative source for all event definitions in Mind v5. Any implementation that diverges from this specification is a bug.*
