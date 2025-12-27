# Mind v4: The Complete Architecture

> From memory store to cognitive infrastructure for humanity

---

## Executive Summary

Mind v4 is not a memory system. It's a **decision-making substrate** that enables agents to:
- Remember what happened
- Understand why decisions were made
- Learn from outcomes
- Share knowledge across agents
- Stay aligned with human intent and values

This document defines the complete architecture, the phased implementation path, and the vision it enables.

---

## Part 1: The Vision

### What We're Building

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              THE FULL STACK                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   LAYER 5: VALUES                                                            │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Who you are. What you won't compromise. How you move through       │   │
│   │  the world. The constitution that governs everything below.         │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   LAYER 4: INTENT                                                            │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  What you're trying to accomplish. Structured goals with success    │   │
│   │  metrics, constraints, and priorities. Maintained over time.        │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   LAYER 3: MIND (This Document)                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Memory, judgment, learning. The accumulated wisdom that informs    │   │
│   │  decisions. Shared across agents. Improves through outcomes.        │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   LAYER 2: SPAWNER                                                           │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Agent orchestration. Deploy intelligent workers with roles,        │   │
│   │  capabilities, and coordination.                                    │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   LAYER 1: EXECUTION                                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  The actual work. Code, analysis, research, creation.               │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Transformation

| Today | Tomorrow |
|-------|----------|
| Agents forget everything between sessions | Agents remember, learn, improve |
| Each agent works in isolation | Agents share knowledge and learn from each other |
| Decisions are black boxes | Every decision has traceable reasoning |
| Mistakes get repeated | Mistakes become lessons that propagate |
| Humans manage tasks | Humans declare intent; agents figure out how |
| Organizations lose knowledge when people leave | Knowledge compounds forever |

---

## Part 2: Architecture Versions

### v3 Current (Simplify First)

Before building v4, we must simplify v3. The current v3 has:
- 9 tables (most empty)
- Complex extraction pipelines (mostly broken)
- Architecture ahead of implementation

**v3 Target State:**

```
.mind/
├── MEMORY.md              # Human-readable backup (v2, keep as-is)
├── SESSION.md             # Working memory (v2, keep as-is)
├── REMINDERS.md           # Time/context triggers (v2, keep as-is)
├── state.json             # Session detection
│
└── v3/
    ├── memories.lance     # ALL memories with embeddings + structure
    ├── edges.lance        # Relationships between memories
    └── outcomes.lance     # Decision → result tracking
```

**That's it. Three tables.**

Everything else (decisions, patterns, policies, entities) becomes **fields on memories**, not separate tables. This solves the extraction problem—we don't need perfect extraction into separate tables, we need good-enough extraction into structured fields.

### v4 Target (The Full System)

Once v3 is stable and learning is working, v4 adds:

```
.mind/
├── [v2 layer - unchanged]
│
└── v4/
    ├── core/
    │   ├── memories.lance         # All memories with structure
    │   ├── edges.lance            # Relationship graph
    │   └── outcomes.lance         # Results tracking
    │
    ├── agents/
    │   ├── profiles.lance         # Agent identities & specializations
    │   ├── trust.lance            # Inter-agent trust scores
    │   └── performance.lance      # Success rates by domain
    │
    ├── coordination/
    │   ├── consensus.lance        # Multi-agent decisions
    │   ├── handoffs.lance         # Work transfers between agents
    │   └── conflicts.lance        # Detected contradictions
    │
    ├── learning/
    │   ├── patterns.lance         # Emerged patterns (consolidated)
    │   ├── precedents.lance       # Reusable decision templates
    │   └── procedures.lance       # Crystallized workflows
    │
    ├── governance/
    │   ├── policies.lance         # Rules with versions & exceptions
    │   ├── approvals.lance        # Decision approval chains
    │   └── audit.lance            # Immutable event log
    │
    └── shared/
        ├── ontology.lance         # Shared vocabulary & entity types
        └── experiences.lance      # Cross-agent episodic memory
```

### v5 Future (Intent + Values)

The layers above Mind:

```
.intent/
├── goals.lance            # Declared intents with structure
├── alignment.lance        # Activity → intent mapping
├── drift.lance            # Detected misalignments
└── graph.lance            # Connected intents across users

.values/
├── principles.lance       # Core values
├── constraints.lance      # Hard limits
├── tradeoffs.lance        # How to balance competing values
└── history.lance          # How values evolved
```

---

## Part 3: Core Data Structures

### Memory Record (v3/v4)

```python
{
    # Identity
    "id": "mem_abc123",
    "created_at": "2025-12-27T10:30:00Z",
    "updated_at": "2025-12-27T10:30:00Z",
    
    # Content
    "content": "Decided to use Redis for caching because latency requirement is <100ms",
    "type": "decision",  # observation | decision | outcome | learning | pattern
    "source": "user",    # user | agent | system | consolidation
    
    # Embedding for semantic search
    "embedding": [0.1, 0.2, ...],  # 384-dim from sentence-transformers
    
    # Extracted Structure (AI-powered)
    "structure": {
        "decision": {
            "action": "use Redis for caching",
            "reasoning": "latency requirement <100ms, read-heavy workload",
            "alternatives_considered": [
                {"option": "Memcached", "why_rejected": "lower persistence"},
                {"option": "PostgreSQL", "why_rejected": "can't meet latency target"}
            ],
            "confidence": 0.8,
            "predicted_outcome": "latency drops to <100ms"
        },
        "entities": [
            {"name": "Redis", "type": "technology"},
            {"name": "caching", "type": "concept"}
        ],
        "domain": "infrastructure"
    },
    
    # Confidence & Learning
    "confidence": 0.8,
    "access_count": 0,
    "last_accessed": null,
    "usefulness_score": null,  # Updated when this memory helps
    
    # Provenance
    "agent_id": "agent_infra_001",  # null for single-agent
    "session_id": "session_xyz",
    "project_id": "project_abc",
    
    # Lifecycle
    "status": "active",  # active | deprecated | superseded | archived
    "superseded_by": null,
    "deprecation_reason": null
}
```

### Edge Record

```python
{
    "id": "edge_xyz789",
    "created_at": "2025-12-27T10:31:00Z",
    
    # Connection
    "source_id": "mem_abc123",
    "source_type": "memory",
    "target_id": "mem_def456", 
    "target_type": "memory",
    
    # Relationship
    "edge_type": "led_to",  # See edge types below
    "weight": 0.9,          # Strength of relationship
    "bidirectional": false,
    
    # Evidence
    "evidence": ["event_001", "event_002"],  # What justified this edge
    "created_by": "system",  # system | user | agent | consolidation
    
    # Lifecycle
    "status": "active",
    "confidence": 0.9
}
```

**Edge Types:**

| Edge Type | Meaning | Example |
|-----------|---------|---------|
| `led_to` | Causal relationship | decision → outcome |
| `outcome_of` | Result of action | outcome → decision |
| `same_entity` | Share an entity | memory ↔ memory |
| `similar_to` | Semantically similar | memory ↔ memory |
| `contradicts` | Logical conflict | memory ↔ memory |
| `supersedes` | Replaces/updates | new_memory → old_memory |
| `supports` | Evidence for | memory → pattern |
| `informed_by` | Used as input | decision → precedent |
| `contributed_to` | Part of | memories → pattern |

### Outcome Record

```python
{
    "id": "outcome_uvw321",
    "created_at": "2025-12-27T14:00:00Z",
    
    # Link to decision
    "decision_id": "mem_abc123",
    
    # Result
    "success": true,
    "result_summary": "Latency dropped to 85ms, exceeding target",
    
    # Metrics (if applicable)
    "predicted": {"latency_ms": 100},
    "actual": {"latency_ms": 85},
    "delta": {"latency_ms": -15},  # Positive = better than expected
    
    # Learning
    "lessons": [
        "Redis consistently outperforms predictions for read-heavy workloads"
    ],
    "confidence_adjustment": 0.05,  # How much to adjust decision confidence
    
    # Feedback
    "feedback_source": "user",  # user | automated | agent
    "feedback_notes": "Exceeded expectations. Adopted by 3 other teams."
}
```

### Agent Profile (v4)

```python
{
    "id": "agent_infra_001",
    "created_at": "2025-12-01T00:00:00Z",
    
    # Identity
    "name": "Infrastructure Agent",
    "role": "infrastructure_specialist",
    "description": "Handles caching, databases, deployment decisions",
    
    # Capabilities
    "specializations": ["caching", "databases", "deployment", "performance"],
    "domains": {
        "infrastructure": 0.95,
        "security": 0.60,
        "frontend": 0.20
    },
    
    # Performance
    "decisions_made": 247,
    "success_rate": 0.89,
    "confidence_calibration": 0.92,  # How accurate are confidence estimates
    
    # Autonomy
    "autonomy_level": "ACT_NOTIFY",  # RECORD_ONLY | SUGGEST | ASK_PERMISSION | ACT_NOTIFY | SILENT
    "autonomy_by_domain": {
        "infrastructure": "ACT_NOTIFY",
        "security": "ASK_PERMISSION",
        "frontend": "SUGGEST"
    },
    
    # Trust relationships
    "trusts": {
        "agent_security_001": 0.85,
        "agent_frontend_001": 0.70
    },
    "trusted_by": {
        "agent_backend_001": 0.90
    },
    
    # Failure modes (learned from outcomes)
    "known_weaknesses": [
        "Tends to over-engineer for small projects",
        "Underestimates migration complexity"
    ],
    
    # Team
    "team_id": "team_platform",
    "reports_to": "agent_lead_001"
}
```

### Consensus Record (v4)

```python
{
    "id": "consensus_abc123",
    "created_at": "2025-12-27T10:00:00Z",
    
    # Proposal
    "proposal": {
        "description": "Migrate from PostgreSQL to CockroachDB for multi-region",
        "proposing_agent": "agent_infra_001",
        "decision_type": "architecture",
        "stakes": "high"  # low | medium | high | critical
    },
    
    # Positions
    "positions": [
        {
            "agent_id": "agent_infra_001",
            "stance": "approve",
            "confidence": 0.85,
            "reasoning": "Necessary for latency requirements in APAC"
        },
        {
            "agent_id": "agent_security_001",
            "stance": "conditional_approve",
            "confidence": 0.70,
            "reasoning": "Approve if we maintain encryption at rest",
            "conditions": ["encryption_at_rest", "audit_logging"]
        },
        {
            "agent_id": "agent_cost_001",
            "stance": "oppose",
            "confidence": 0.60,
            "reasoning": "3x cost increase, ROI unclear"
        }
    ],
    
    # Resolution
    "outcome": "conditional_approve",
    "conditions_imposed": ["encryption_at_rest", "audit_logging", "cost_review_30d"],
    "dissenting_views_acknowledged": ["Cost concern noted, will review in 30 days"],
    "final_confidence": 0.72,
    
    # Tracking
    "status": "implemented",  # proposed | voting | decided | implemented | reviewed
    "decision_id": "mem_decision_xyz",  # Link to resulting decision memory
    "outcome_id": null  # Link to outcome when available
}
```

### Pattern Record (v4 - Consolidated)

```python
{
    "id": "pattern_xyz789",
    "created_at": "2025-12-27T00:00:00Z",
    
    # Pattern
    "description": "For read-heavy workloads with <100ms latency requirements, Redis outperforms alternatives",
    "type": "preference",  # preference | habit | avoidance | correlation
    
    # Evidence
    "supporting_memories": ["mem_001", "mem_023", "mem_045", "mem_067"],
    "evidence_count": 47,
    "success_rate": 0.94,
    
    # Confidence
    "confidence": 0.91,
    "confidence_history": [
        {"date": "2025-11-01", "value": 0.75},
        {"date": "2025-12-01", "value": 0.85},
        {"date": "2025-12-27", "value": 0.91}
    ],
    
    # Applicability
    "conditions": {
        "workload_type": "read_heavy",
        "latency_requirement_ms": {"lt": 100},
        "data_persistence": "required"
    },
    
    # Lifecycle
    "status": "active",
    "promoted_to_policy": null,  # If crystallized into a policy
    "contradicted_by": []  # Patterns that conflict
}
```

---

## Part 4: The Learning Loop

This is the heart of Mind. Without this loop, you just have storage. With it, you have intelligence.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           THE LEARNING LOOP                                  │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │   1. OBSERVE     │
                    │   Capture event  │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   2. RETRIEVE    │
                    │   Find relevant  │◄────────────────────────────┐
                    │   precedents     │                             │
                    └────────┬─────────┘                             │
                             │                                       │
                             ▼                                       │
                    ┌──────────────────┐                             │
                    │   3. DECIDE      │                             │
                    │   Make choice    │                             │
                    │   with reasoning │                             │
                    │   + prediction   │                             │
                    └────────┬─────────┘                             │
                             │                                       │
                             ▼                                       │
                    ┌──────────────────┐                             │
                    │   4. ACT         │                             │
                    │   Execute        │                             │
                    └────────┬─────────┘                             │
                             │                                       │
                             ▼                                       │
                    ┌──────────────────┐                             │
                    │   5. OUTCOME     │                             │
                    │   Record result  │                             │
                    └────────┬─────────┘                             │
                             │                                       │
                             ▼                                       │
                    ┌──────────────────┐                             │
                    │   6. UPDATE      │                             │
                    │   Adjust         │                             │
                    │   confidence     │─────────────────────────────┘
                    │   everywhere     │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  7. CONSOLIDATE  │
                    │  Extract patterns│
                    │  Update policies │
                    └──────────────────┘
```

### Confidence Propagation

When an outcome is recorded, confidence updates propagate through the graph:

```python
def process_outcome(outcome: Outcome):
    decision = get_memory(outcome.decision_id)
    
    # 1. Update the decision's confidence
    decision.confidence = bayesian_update(
        prior=decision.confidence,
        evidence=outcome.success,
        strength=outcome.confidence_adjustment
    )
    
    # 2. Update precedents that informed this decision
    for edge in get_edges(decision.id, type="informed_by"):
        precedent = get_memory(edge.target_id)
        precedent.usefulness_score = update_usefulness(
            current=precedent.usefulness_score,
            outcome=outcome.success,
            weight=edge.weight
        )
    
    # 3. Update patterns that were relied upon
    for edge in get_edges(decision.id, type="supported_by"):
        pattern = get_pattern(edge.target_id)
        if outcome.success:
            pattern.evidence_count += 1
            pattern.success_rate = recalculate_success_rate(pattern)
        else:
            pattern.contradicted_by.append(outcome.id)
            if len(pattern.contradicted_by) > threshold:
                flag_pattern_for_review(pattern)
    
    # 4. Update agent performance
    agent = get_agent(decision.agent_id)
    domain = decision.structure.get("domain")
    agent.domains[domain] = update_domain_confidence(
        current=agent.domains[domain],
        outcome=outcome.success
    )
    
    # 5. Check for contradiction with existing patterns
    if not outcome.success:
        similar_patterns = find_similar_patterns(decision)
        for pattern in similar_patterns:
            if pattern.confidence > 0.8:
                create_contradiction(
                    item_a=pattern,
                    item_b=outcome,
                    type="evidence_conflict"
                )
```

---

## Part 5: Consolidation Pipeline

The Gardener—a background process that keeps Mind healthy.

### Stage 1: Episode → Semantic (Hourly)

Convert raw session events into structured memories with patterns.

```python
def consolidate_episodes():
    """Run hourly or after N events."""
    
    # Get unprocessed session events
    events = get_session_events(status="unprocessed")
    
    # Cluster similar events
    clusters = cluster_by_embedding(events, min_similarity=0.85)
    
    for cluster in clusters:
        if len(cluster) >= 3:
            # Multiple similar events → potential pattern
            pattern = extract_pattern(cluster)
            if pattern.confidence > 0.6:
                save_pattern(pattern)
                
                # Link contributing events
                for event in cluster:
                    create_edge(event.id, pattern.id, "contributed_to")
        
        # Mark events as processed
        for event in cluster:
            event.status = "processed"
            save_memory(event)
```

### Stage 2: Semantic → Procedural (Daily)

Promote stable patterns to policies/procedures.

```python
def consolidate_patterns():
    """Run daily."""
    
    # Find patterns ready for promotion
    stable_patterns = query_patterns(
        confidence__gt=0.85,
        evidence_count__gt=20,
        status="active",
        promoted_to_policy=None
    )
    
    for pattern in stable_patterns:
        # Generate policy from pattern
        policy = generate_policy(pattern)
        
        # Check for conflicts with existing policies
        conflicts = find_conflicting_policies(policy)
        
        if conflicts:
            for conflict in conflicts:
                create_contradiction(
                    item_a=policy,
                    item_b=conflict,
                    type="policy_conflict",
                    severity="high"
                )
            # Don't promote yet, needs resolution
            continue
        
        # Promote
        save_policy(policy)
        pattern.promoted_to_policy = policy.id
        save_pattern(pattern)
        
        # Create edge
        create_edge(pattern.id, policy.id, "crystallized_into")
```

### Stage 3: Hygiene (Daily)

Clean up, dedupe, detect contradictions.

```python
def run_hygiene():
    """Run daily."""
    
    # 1. Deduplicate similar memories
    duplicates = find_near_duplicates(similarity_threshold=0.95)
    for dup_group in duplicates:
        primary = select_primary(dup_group)  # Most accessed, most recent
        for dup in dup_group:
            if dup.id != primary.id:
                dup.status = "superseded"
                dup.superseded_by = primary.id
                save_memory(dup)
    
    # 2. Decay unused memories
    stale_memories = query_memories(
        last_accessed__lt=days_ago(90),
        usefulness_score__lt=0.3,
        status="active"
    )
    for memory in stale_memories:
        memory.status = "archived"
        save_memory(memory)
    
    # 3. Detect contradictions
    detect_policy_contradictions()
    detect_pattern_contradictions()
    detect_prediction_failures()
    
    # 4. Update confidence decay
    for memory in query_memories(type="decision"):
        if memory.outcome_id is None:
            days_since = (now() - memory.created_at).days
            if days_since > 30:
                # Unvalidated decision loses confidence over time
                memory.confidence *= 0.99  # 1% decay per day after 30 days
                save_memory(memory)
```

---

## Part 6: Multi-Agent Coordination

### Scoped Retrieval

```python
def mind_recall(
    query: str,
    agent_id: str,
    scopes: List[str] = ["self", "team", "global"]
) -> Context:
    """
    Retrieve memories with appropriate scoping.
    
    Scopes:
    - self: This agent's own memories
    - team: Team-level shared memories
    - global: Organization-wide policies and precedents
    - domain:{name}: Domain-specific knowledge
    """
    
    results = []
    
    for scope in scopes:
        if scope == "self":
            # Agent's own memories - high relevance threshold
            results += search_memories(
                query=query,
                filter={"agent_id": agent_id},
                min_relevance=0.5
            )
        
        elif scope == "team":
            # Team memories - patterns and policies only
            team_id = get_agent(agent_id).team_id
            results += search_memories(
                query=query,
                filter={
                    "team_id": team_id,
                    "type__in": ["pattern", "policy", "precedent"]
                },
                min_relevance=0.7
            )
        
        elif scope == "global":
            # Global - only high-confidence policies and precedents
            results += search_memories(
                query=query,
                filter={
                    "type__in": ["policy", "precedent"],
                    "confidence__gt": 0.9
                },
                min_relevance=0.8
            )
        
        elif scope.startswith("domain:"):
            domain = scope.split(":")[1]
            results += search_memories(
                query=query,
                filter={"structure.domain": domain},
                min_relevance=0.6
            )
    
    # Dedupe and rank
    return Context(
        memories=dedupe_by_id(results),
        agent_context=get_agent_context(agent_id),
        active_contradictions=get_relevant_contradictions(query)
    )
```

### Trust-Based Routing

```python
def route_decision(decision_request: DecisionRequest) -> Agent:
    """Route a decision to the best-suited agent."""
    
    domain = decision_request.domain
    stakes = decision_request.stakes
    
    # Find agents with relevant expertise
    candidates = query_agents(
        domains__contains=domain,
        autonomy_level__gte=required_autonomy(stakes)
    )
    
    # Score by expertise + trust + availability
    scores = []
    for agent in candidates:
        score = (
            agent.domains[domain] * 0.4 +           # Domain expertise
            agent.success_rate * 0.3 +              # Track record
            agent.confidence_calibration * 0.2 +   # Calibration quality
            get_trust_score(agent.id) * 0.1        # Peer trust
        )
        scores.append((agent, score))
    
    # Return highest scorer
    return max(scores, key=lambda x: x[1])[0]
```

### Contradiction Resolution

```python
def handle_contradiction(contradiction: Contradiction):
    """Resolve detected contradictions."""
    
    if contradiction.severity == "low":
        # Auto-resolve: lower confidence item yields
        item_a = get_item(contradiction.item_a_id)
        item_b = get_item(contradiction.item_b_id)
        
        if item_a.confidence < item_b.confidence:
            item_a.status = "deprecated"
            item_a.deprecation_reason = f"Contradicted by {item_b.id}"
            save_item(item_a)
        else:
            item_b.status = "deprecated"
            item_b.deprecation_reason = f"Contradicted by {item_a.id}"
            save_item(item_b)
        
        contradiction.status = "resolved"
        contradiction.resolution = "auto_deprecate"
    
    elif contradiction.severity in ["medium", "high"]:
        # Flag for review
        contradiction.status = "flagged"
        notify_for_review(contradiction)
    
    elif contradiction.severity == "critical":
        # Pause affected decisions
        affected_decisions = find_affected_decisions(contradiction)
        for decision in affected_decisions:
            decision.status = "paused"
            decision.paused_reason = f"Contradiction {contradiction.id}"
            save_memory(decision)
        
        # Urgent notification
        notify_urgent(contradiction)
    
    save_contradiction(contradiction)
```

---

## Part 7: Implementation Phases

### Current State Assessment

```
v3 Current State:
├── memories.lance    → 140 items (from MEMORY.md migration)
├── decisions.lance   → 1 item (test)
├── entities.lance    → 3 items (test)
├── patterns.lance    → 0 items
├── policies.lance    → 0 items
├── precedents.lance  → 0 items
├── outcomes.lance    → 0 items
├── exceptions.lance  → 0 items
└── autonomy.lance    → 0 items

Problems:
1. Extraction not working → structured tables empty
2. No edges → no relationships
3. No outcomes → no learning
4. Too many tables → complexity without value
```

---

### Phase 1: v3 Simplification (Weeks 1-2)

**Goal:** Working foundation with three tables

**Week 1: The Purge**

- [ ] Create `archived/v3/` directory
- [ ] Move all complex extractors to archive
- [ ] Move 6 unused tables to archive (keep memories, create edges, outcomes)
- [ ] Simplify memories.lance schema to include structure field
- [ ] Run tests, fix breakages
- [ ] Commit: "Simplified v3 to three-table core"

**Week 2: AI Extraction**

- [ ] Create `extract_structure()` function using Haiku
- [ ] Test on 50 sample memories
- [ ] Integrate into `mind_log()` flow
- [ ] Backfill existing memories with structure
- [ ] Commit: "AI-powered structure extraction"

**Deliverable:** Every memory has extracted structure (decision, entities, domain)

---

### Phase 2: Relationships (Weeks 3-4)

**Goal:** Memories connected by edges

**Week 3: Edge Detection**

- [ ] Implement `edges.lance` table
- [ ] Create `find_edges()` function:
  - Same entity detection
  - Semantic similarity detection
  - Outcome → decision linking
- [ ] Add edge creation to `mind_log()` flow
- [ ] Commit: "Automatic edge detection"

**Week 4: Graph-Aware Retrieval**

- [ ] Update `mind_search()` to follow edges
- [ ] Update `mind_recall()` to include related memories
- [ ] Add relevance scoring that includes edge weights
- [ ] Commit: "Graph-aware retrieval"

**Deliverable:** Search returns related memories, not just similar text

---

### Phase 3: Learning Loop (Weeks 5-6)

**Goal:** Outcomes update confidence everywhere

**Week 5: Outcome Tracking**

- [ ] Implement `outcomes.lance` table
- [ ] Create `mind_outcome()` MCP tool
- [ ] Link outcomes to decisions via edges
- [ ] Commit: "Outcome tracking"

**Week 6: Confidence Propagation**

- [ ] Implement `process_outcome()` with confidence updates
- [ ] Update decision confidence
- [ ] Update precedent usefulness
- [ ] Track prediction accuracy
- [ ] Commit: "Confidence propagation"

**Deliverable:** When outcomes are recorded, the system learns

---

### Phase 4: Consolidation (Weeks 7-8)

**Goal:** Background process that maintains system health

**Week 7: The Gardener**

- [ ] Create consolidation module
- [ ] Implement episode → semantic consolidation
- [ ] Implement hygiene (dedupe, decay)
- [ ] Add CLI command: `mind consolidate`
- [ ] Commit: "Consolidation pipeline"

**Week 8: Pattern Emergence**

- [ ] Implement pattern detection from clustered memories
- [ ] Add patterns.lance (now as derived data, not input)
- [ ] Create edges from memories to patterns
- [ ] Commit: "Automatic pattern detection"

**Deliverable:** Patterns emerge from accumulated experience

---

### Phase 5: Multi-Agent Foundation (Weeks 9-12)

**Goal:** Mind works for agent teams

**Week 9: Agent Profiles**

- [ ] Implement `agent_profiles.lance`
- [ ] Add agent_id to memory records
- [ ] Create agent performance tracking
- [ ] Commit: "Agent identity"

**Week 10: Scoped Retrieval**

- [ ] Implement scope parameter in `mind_recall()`
- [ ] Add team_id to relevant structures
- [ ] Create scope-based filtering
- [ ] Commit: "Scoped retrieval"

**Week 11: Trust Tracking**

- [ ] Implement `trust.lance`
- [ ] Track inter-agent trust scores
- [ ] Create trust-based routing
- [ ] Commit: "Trust network"

**Week 12: Contradiction Detection**

- [ ] Implement `contradictions.lance`
- [ ] Create contradiction detection in consolidation
- [ ] Add resolution workflows
- [ ] Commit: "Contradiction handling"

**Deliverable:** Multiple agents can share Mind without chaos

---

### Phase 6: Coordination (Weeks 13-16)

**Goal:** Agents make decisions together

**Week 13-14: Consensus Mechanism**

- [ ] Implement `consensus.lance`
- [ ] Create proposal → voting → resolution flow
- [ ] Add `mind_propose()` and `mind_vote()` tools
- [ ] Commit: "Multi-agent consensus"

**Week 15-16: Shared Experiences**

- [ ] Implement `experiences.lance`
- [ ] Create cross-agent learning events
- [ ] Propagate lessons across agent boundaries
- [ ] Commit: "Shared learning"

**Deliverable:** Agents collaborate on decisions

---

### Phase 7: Governance (Weeks 17-20)

**Goal:** Enterprise-ready governance

**Weeks 17-18: Policy Management**

- [ ] Add versioning to policies
- [ ] Implement exceptions
- [ ] Create policy lifecycle (draft → active → deprecated)
- [ ] Commit: "Policy governance"

**Weeks 19-20: Audit & Compliance**

- [ ] Implement immutable audit log
- [ ] Create decision explanation generator
- [ ] Add compliance reporting
- [ ] Commit: "Audit trail"

**Deliverable:** Regulators can understand why decisions were made

---

### Phase 8: Intent Layer (Weeks 21-24)

**Goal:** Agents stay aligned with human goals

**Weeks 21-22: Intent Capture**

- [ ] Create `.intent/` structure
- [ ] Implement intent interrogation flow
- [ ] Build goal tree data structure
- [ ] Commit: "Intent declaration"

**Weeks 23-24: Alignment Tracking**

- [ ] Connect activities to intents
- [ ] Detect drift from declared intent
- [ ] Create realignment suggestions
- [ ] Commit: "Intent alignment"

**Deliverable:** System maintains focus on what actually matters

---

### Phase 9: Intent Graph (Weeks 25-28)

**Goal:** Connected intents across users

**Weeks 25-26: Intent Matching**

- [ ] Find similar intents across users
- [ ] Enable opt-in sharing
- [ ] Create intent collaboration proposals
- [ ] Commit: "Intent discovery"

**Weeks 27-28: Collective Intelligence**

- [ ] Share relevant learnings across matched intents
- [ ] Propagate successful patterns
- [ ] Build network effects into retrieval
- [ ] Commit: "The Graph"

**Deliverable:** Strangers working on similar problems help each other automatically

---

### Phase 10: Values Layer (Weeks 29-32)

**Goal:** Agents respect human values

**Weeks 29-30: Values Capture**

- [ ] Create `.values/` structure
- [ ] Implement values elicitation
- [ ] Build constraint system
- [ ] Commit: "Values declaration"

**Weeks 31-32: Values Enforcement**

- [ ] Check decisions against values
- [ ] Flag value conflicts
- [ ] Create values-aware routing
- [ ] Commit: "Values alignment"

**Deliverable:** Agents act in accordance with who you are, not just what you want

---

## Part 8: MCP Tools

### v3 Tools (Current + Simplified)

```python
# Core
mind_recall(scopes=["self"])      # Load context
mind_log(msg, type)                # Log memory with AI extraction
mind_search(query)                 # Graph-aware semantic search

# Session
mind_session()                     # Session state
mind_checkpoint()                  # Force consolidation

# New in v3 simplified
mind_outcome(decision_id, success, notes)  # Record outcome
mind_edges(memory_id)              # View edges for a memory
```

### v4 Tools (Multi-Agent)

```python
# Agent
mind_profile(agent_id)             # View agent profile
mind_specialize(domain, level)     # Declare specialization
mind_trust(agent_id, score)        # Update trust

# Coordination  
mind_propose(decision, stakes)     # Propose decision for consensus
mind_vote(proposal_id, stance)     # Cast vote
mind_consensus(proposal_id)        # Check consensus status

# Learning
mind_pattern(memory_ids)           # Manually create pattern
mind_contradict(item_a, item_b)    # Flag contradiction
mind_resolve(contradiction_id)     # Resolve contradiction

# Governance
mind_policy(rule, scope)           # Create policy
mind_exception(policy_id, condition)  # Add exception
mind_audit(decision_id)            # Get full audit trail
```

### v5 Tools (Intent + Values)

```python
# Intent
mind_intent(description)           # Declare intent
mind_refine_intent(intent_id)      # Interactive refinement
mind_align(activity_id, intent_id) # Link activity to intent
mind_drift()                       # Check for drift

# Values
mind_value(principle)              # Declare value
mind_constraint(hard_limit)        # Declare constraint
mind_tradeoff(value_a, value_b)    # Define how to balance
```

---

## Part 9: Success Metrics

### Phase Metrics

| Phase | Metric | Target | Measurement |
|-------|--------|--------|-------------|
| 1 | Memories with structure | 100% | `SELECT COUNT(*) WHERE structure IS NOT NULL` |
| 2 | Memories with edges | >50% | `SELECT COUNT(DISTINCT source_id) FROM edges` |
| 3 | Decisions with outcomes | >30% | `SELECT COUNT(*) FROM outcomes` |
| 4 | Pattern emergence rate | >5/week | `SELECT COUNT(*) FROM patterns WHERE created_at > week_ago` |
| 5 | Multi-agent retrieval latency | <200ms | P95 latency |
| 6 | Consensus decisions | >10/week | `SELECT COUNT(*) FROM consensus` |
| 7 | Policy coverage | >80% decisions | Decisions that match a policy |
| 8 | Intent alignment | >90% activities | Activities linked to intents |

### North Star Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **Decision quality** | Outcome success rate | >85% |
| **Learning velocity** | Confidence improvement per week | >0.02 |
| **Knowledge retention** | Precedent reuse rate | >40% |
| **Agent calibration** | Predicted vs actual outcomes | <10% error |
| **Cross-agent learning** | Patterns used by multiple agents | >50% |

---

## Part 10: The Endgame

When all phases are complete, you have:

1. **For Individuals:** An AI team that remembers everything, learns from mistakes, and stays focused on what you actually want to accomplish.

2. **For Organizations:** Institutional knowledge that compounds, decision-making that's transparent and auditable, and agents that improve continuously.

3. **For Humanity:** Collective intelligence that connects strangers working on similar problems, shares learnings across the species, and makes good judgment accessible to everyone.

The gap between human intention and human capability closes.

What someone wants to accomplish and what they can actually accomplish converges.

That's the endgame.

---

## Appendix A: File Structure

```
vibeship-mind/
├── src/mind/
│   ├── __init__.py
│   ├── cli.py                    # CLI commands
│   ├── mcp_server.py             # MCP tool definitions
│   │
│   ├── v2/                       # Legacy layer (keep stable)
│   │   ├── memory.py             # MEMORY.md operations
│   │   ├── session.py            # SESSION.md operations
│   │   └── reminders.py          # REMINDERS.md operations
│   │
│   ├── v3/                       # Simplified v3
│   │   ├── store.py              # LanceDB operations
│   │   ├── extract.py            # AI structure extraction
│   │   ├── edges.py              # Edge detection & management
│   │   ├── outcomes.py           # Outcome tracking
│   │   ├── search.py             # Graph-aware search
│   │   └── consolidate.py        # Gardener pipeline
│   │
│   ├── v4/                       # Multi-agent (future)
│   │   ├── agents.py
│   │   ├── consensus.py
│   │   ├── trust.py
│   │   ├── governance.py
│   │   └── coordination.py
│   │
│   └── v5/                       # Intent + Values (future)
│       ├── intent.py
│       ├── values.py
│       └── graph.py
│
├── tests/
│   ├── v2/
│   ├── v3/
│   ├── v4/
│   └── v5/
│
├── docs/
│   ├── ARCHITECTURE.md           # This document
│   ├── API.md                    # MCP tool reference
│   └── GUIDES/
│       ├── single_agent.md
│       ├── multi_agent.md
│       └── enterprise.md
│
└── archived/
    └── v3_complex/               # Archived complex v3 code
```

---

## Appendix B: Quick Reference

### Memory Types

| Type | Persists | Description |
|------|----------|-------------|
| observation | Session | Something noticed |
| decision | Forever | Choice made with reasoning |
| outcome | Forever | Result of a decision |
| learning | Forever | Insight gained |
| pattern | Forever | Recurring behavior detected |
| policy | Forever | Rule established |

### Edge Types

| Type | Direction | Meaning |
|------|-----------|---------|
| led_to | A → B | A caused B |
| outcome_of | A → B | A is result of B |
| same_entity | A ↔ B | Share an entity |
| similar_to | A ↔ B | Semantically similar |
| contradicts | A ↔ B | Conflict |
| supersedes | A → B | A replaces B |
| supports | A → B | A is evidence for B |
| informed_by | A → B | A used B as input |

### Autonomy Levels

| Level | Behavior |
|-------|----------|
| RECORD_ONLY | Observe, don't act |
| SUGGEST | Propose, wait for approval |
| ASK_PERMISSION | Propose with confidence, ask |
| ACT_NOTIFY | Act, then inform |
| SILENT | Act, log only |

---

*Document Version: 1.0*
*Created: December 27, 2025*
*Author: Human + Claude collaboration*
*Status: Blueprint for implementation*
