# Mind v5 Team Orchestration

> **Purpose**: Define how 20 specialized agents collaborate as a world-class team
> **Philosophy**: Specialists who know when to lead and when to defer

---

## Team Philosophy

### The Orchestra Model

This team operates like a world-class orchestra:
- **Each musician** (agent) is a master of their instrument (domain)
- **No permanent conductor** - leadership shifts based on the piece (task)
- **Shared score** (CLAUDE.md) - everyone reads from the same standards
- **Sections** (pods) - related instruments collaborate closely
- **The music** (output) - matters more than any individual part

### Core Principles

1. **Domain Authority**: The specialist leads in their domain
2. **Humble Handoffs**: Know when you're out of your depth
3. **Review Culture**: Every significant change gets expert eyes
4. **Shared Ownership**: The team ships together, fails together
5. **Continuous Learning**: Each interaction improves the whole

---

## Team Structure

### The Four Pods

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MIND v5 TEAM                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────┐          ┌─────────────────────┐          │
│  │    CORE POD         │          │   PLATFORM POD      │          │
│  │                     │          │                     │          │
│  │  • event-architect  │◄────────►│  • infra-architect  │          │
│  │  • graph-engineer   │          │  • postgres-wizard  │          │
│  │  • vector-specialist│          │  • observability-sre│          │
│  │  • temporal-craftsman          │  • migration-specialist        │
│  │  • ml-memory        │          │  • chaos-engineer   │          │
│  │  • causal-scientist │          │                     │          │
│  └─────────────────────┘          └─────────────────────┘          │
│            │                                │                       │
│            │         ┌──────────┐           │                       │
│            └────────►│ QUALITY  │◄──────────┘                       │
│                      │   HUB    │                                   │
│            ┌────────►│          │◄──────────┐                       │
│            │         └──────────┘           │                       │
│            │                                │                       │
│  ┌─────────────────────┐          ┌─────────────────────┐          │
│  │   QUALITY POD       │          │   INTERFACE POD     │          │
│  │                     │          │                     │          │
│  │  • test-architect   │◄────────►│  • api-designer     │          │
│  │  • code-reviewer    │          │  • sdk-builder      │          │
│  │  • privacy-guardian │          │  • docs-engineer    │          │
│  │  • performance-hunter│         │  • python-craftsman │          │
│  │  • data-engineer    │          │                     │          │
│  └─────────────────────┘          └─────────────────────┘          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Pod Responsibilities

#### Core Pod (The Brain)
**Mission**: Build the intelligence that makes Mind v5 special

| Agent | Primary Domain | Consults With |
|-------|---------------|---------------|
| event-architect | Event backbone, CQRS | temporal-craftsman, data-engineer |
| graph-engineer | Causal graphs, FalkorDB | causal-scientist, postgres-wizard |
| vector-specialist | Embeddings, Qdrant | ml-memory, performance-hunter |
| temporal-craftsman | Workflows, Temporal.io | event-architect, infra-architect |
| ml-memory | Memory systems, Zep | causal-scientist, vector-specialist |
| causal-scientist | DoWhy, inference | graph-engineer, data-engineer |

#### Platform Pod (The Foundation)
**Mission**: Make it run, scale, and survive

| Agent | Primary Domain | Consults With |
|-------|---------------|---------------|
| infra-architect | Kubernetes, Terraform | observability-sre, chaos-engineer |
| postgres-wizard | PostgreSQL optimization | graph-engineer, performance-hunter |
| observability-sre | Monitoring, alerting | all pods on metrics |
| migration-specialist | Zero-downtime deploys | postgres-wizard, event-architect |
| chaos-engineer | Resilience testing | all pods on failure modes |

#### Quality Pod (The Guardians)
**Mission**: Ensure everything works and nothing breaks

| Agent | Primary Domain | Consults With |
|-------|---------------|---------------|
| test-architect | Testing strategy | all pods on testability |
| code-reviewer | Code quality | all pods on standards |
| privacy-guardian | Security, privacy | all pods on data handling |
| performance-hunter | Optimization | all pods on hot paths |
| data-engineer | Data pipelines | ml-memory, causal-scientist |

#### Interface Pod (The Bridge)
**Mission**: Make it usable by humans and other systems

| Agent | Primary Domain | Consults With |
|-------|---------------|---------------|
| api-designer | API contracts | all pods on interfaces |
| sdk-builder | Client libraries | api-designer, docs-engineer |
| docs-engineer | Documentation | all pods on explanations |
| python-craftsman | Python excellence | code-reviewer, all Python code |

---

## Collaboration Protocols

### Protocol 1: Task Routing

When a task arrives, it flows through routing:

```
┌──────────────┐
│  New Task    │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  TASK CLASSIFICATION                                  │
│                                                       │
│  Keywords → Primary Agent                             │
│  ─────────────────────────                            │
│  "event", "NATS", "CQRS" → event-architect           │
│  "graph", "cypher", "FalkorDB" → graph-engineer      │
│  "vector", "embedding", "Qdrant" → vector-specialist │
│  "workflow", "Temporal" → temporal-craftsman          │
│  "memory", "retrieval", "Zep" → ml-memory            │
│  "causal", "DoWhy", "counterfactual" → causal-scientist│
│  "kubernetes", "terraform" → infra-architect         │
│  "postgres", "SQL", "query" → postgres-wizard        │
│  "metrics", "alerting", "SLO" → observability-sre    │
│  "migration", "schema change" → migration-specialist │
│  "chaos", "resilience", "failure" → chaos-engineer   │
│  "test", "coverage", "CI" → test-architect           │
│  "review", "pattern", "quality" → code-reviewer      │
│  "privacy", "security", "encryption" → privacy-guardian│
│  "performance", "latency", "optimize" → performance-hunter│
│  "pipeline", "ETL", "data quality" → data-engineer   │
│  "API", "REST", "gRPC" → api-designer                │
│  "SDK", "client library" → sdk-builder               │
│  "documentation", "ADR" → docs-engineer              │
│  "python", "async", "typing" → python-craftsman      │
│                                                       │
│  Multiple keywords? → Most specific wins              │
│  Ambiguous? → code-reviewer triages                   │
└──────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│ Primary Agent│
│ Takes Lead   │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  COLLABORATION CHECK                                  │
│                                                       │
│  Primary asks: "Who else needs to be involved?"       │
│                                                       │
│  Cross-cutting concerns:                              │
│  • Touches database? → postgres-wizard               │
│  • New API? → api-designer                           │
│  • Security implications? → privacy-guardian          │
│  • Performance critical? → performance-hunter         │
│  • Needs testing strategy? → test-architect          │
│  • Needs documentation? → docs-engineer              │
│  • Deployment changes? → infra-architect             │
└──────────────────────────────────────────────────────┘
```

### Protocol 2: The Handoff

When work needs to move between agents:

```python
# Handoff Protocol
class Handoff:
    """Standard handoff between agents."""
    
    from_agent: str
    to_agent: str
    
    # Context (MANDATORY)
    task_summary: str           # What needs to be done
    work_completed: str         # What I already did
    decisions_made: List[str]   # Decisions and rationale
    files_modified: List[str]   # What files were touched
    
    # Guidance (RECOMMENDED)
    suggested_approach: str     # How I'd do it
    watch_out_for: List[str]    # Sharp edges I noticed
    open_questions: List[str]   # Things I couldn't decide
    
    # Links (HELPFUL)
    related_docs: List[str]     # Relevant documentation
    similar_examples: List[str] # Similar past work

# Example handoff
Handoff(
    from_agent="event-architect",
    to_agent="postgres-wizard",
    
    task_summary="Optimize event projection query that's hitting 500ms",
    work_completed="Identified the slow projection in consolidation workflow",
    decisions_made=[
        "Query needs to filter by user_id first (high cardinality)",
        "Should use partial index on valid_until IS NULL"
    ],
    files_modified=["src/workers/projectors/memory_projection.py"],
    
    suggested_approach="Add composite index, consider partitioning",
    watch_out_for=["Table has 50M rows", "Vacuum hasn't run recently"],
    open_questions=["Should we partition by user or by date?"],
    
    related_docs=["docs/architecture/adr-002-postgres.md"],
    similar_examples=["PR #234 optimized similar query"]
)
```

### Protocol 3: Review Chains

Different types of changes require different reviewers:

```yaml
# Review requirements by change type
review_chains:
  
  # Core logic changes
  core_logic:
    required:
      - code-reviewer
      - domain_expert  # The relevant specialist
    recommended:
      - test-architect  # If tests affected
      
  # Database changes
  database:
    required:
      - postgres-wizard
      - migration-specialist
      - code-reviewer
    recommended:
      - performance-hunter
      
  # API changes
  api:
    required:
      - api-designer
      - code-reviewer
    recommended:
      - sdk-builder  # Client impact
      - docs-engineer  # Documentation
      
  # Security-sensitive
  security:
    required:
      - privacy-guardian
      - code-reviewer
    blocking: true  # Cannot merge without approval
    
  # Infrastructure
  infrastructure:
    required:
      - infra-architect
      - observability-sre
    recommended:
      - chaos-engineer  # Failure modes
      
  # Performance-critical
  performance:
    required:
      - performance-hunter
      - code-reviewer
    recommended:
      - domain_expert
      
  # New features
  feature:
    required:
      - code-reviewer
      - test-architect
      - docs-engineer
    recommended:
      - api-designer  # If exposed
```

### Protocol 4: Conflict Resolution

When agents disagree:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DISAGREEMENT RESOLUTION                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Level 1: Domain Authority                                           │
│  ─────────────────────────                                           │
│  The specialist in the relevant domain has final say                 │
│  on technical decisions within their domain.                         │
│                                                                      │
│  Example: postgres-wizard decides on index strategy                  │
│                                                                      │
│  Level 2: Cross-Domain Discussion                                    │
│  ──────────────────────────────                                      │
│  When domains overlap, affected specialists discuss.                 │
│  Goal: Find solution that satisfies all constraints.                 │
│                                                                      │
│  Example: performance-hunter wants denormalization,                  │
│           postgres-wizard prefers normalized design                  │
│           → Discuss tradeoffs, find middle ground                    │
│                                                                      │
│  Level 3: Principle Alignment                                        │
│  ────────────────────────────                                        │
│  Refer to CLAUDE.md and Architecture Principles.                     │
│  The option most aligned with principles wins.                       │
│                                                                      │
│  Example: "Events are Sacred" principle resolves                     │
│           debate about mutable vs immutable design                   │
│                                                                      │
│  Level 4: User Impact                                                │
│  ─────────────────────                                               │
│  When principles don't resolve, choose the option                    │
│  that best serves the end user.                                      │
│                                                                      │
│  Level 5: Explicit Documentation                                     │
│  ───────────────────────────────                                     │
│  If still unresolved, document both options in an ADR,              │
│  make a decision, and record the rationale.                          │
│  This becomes learning for the team.                                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Communication Patterns

### Pattern 1: Broadcast (One to All)

When something affects everyone:

```yaml
# Triggers for broadcast
broadcast_triggers:
  - "Breaking change to shared interface"
  - "New pattern/anti-pattern discovered"
  - "Security vulnerability found"
  - "Architecture decision made"
  - "Outage or incident"

# Format
broadcast:
  from: privacy-guardian
  type: security_alert
  urgency: high
  message: "New PII pattern detected that bypasses current checks"
  action_required: "All agents review data handling in your domain"
  deadline: "Before next merge"
```

### Pattern 2: Consultation (One to One)

When you need specific expertise:

```yaml
# Consultation request
consultation:
  from: ml-memory
  to: causal-scientist
  context: "Building outcome attribution for memory reweighting"
  question: "Should we use Shapley values or simpler attribution?"
  constraints:
    - "Must run in <100ms"
    - "Need to handle 20+ memories per decision"
  my_thinking: "Leaning toward simplified linear attribution"

# Consultation response
response:
  from: causal-scientist
  recommendation: "Use simplified attribution for v1"
  rationale: |
    Shapley is more accurate but O(2^n) complexity.
    For 20 memories, that's 1M+ calculations.
    Linear attribution with interaction terms is sufficient
    until we have data showing it's inadequate.
  code_suggestion: |
    # Simple but effective
    attribution = memory_weight * outcome_signal
  follow_up: "Let's revisit when we have 6 months of data"
```

### Pattern 3: Review Request (One to Few)

When you need sign-off:

```yaml
# Review request
review_request:
  from: event-architect
  to: 
    - code-reviewer
    - temporal-craftsman
  type: design_review
  
  summary: "New event schema for decision tracing"
  
  artifacts:
    - "src/core/events/decision_events.py"
    - "docs/architecture/adr-007-decision-events.md"
  
  specific_questions:
    - "Is the event granularity right?"
    - "Should outcome be a separate event or field?"
  
  context: |
    Part of Phase 2 decision tracking work.
    Needs to support outcome attribution pipeline.

# Review response
review_response:
  from: code-reviewer
  status: approved_with_comments
  
  comments:
    - file: "decision_events.py"
      line: 45
      type: suggestion
      comment: "Consider adding event_version field for future evolution"
    
    - file: "decision_events.py"
      line: 78
      type: blocking
      comment: "Missing causation_id - required by our event standards"
  
  overall: "Good design, minor fixes needed"
```

### Pattern 4: Incident Response (All Hands)

When things break:

```yaml
# Incident declaration
incident:
  severity: P1  # User-facing impact
  declared_by: observability-sre
  
  symptoms:
    - "Retrieval latency > 5s"
    - "Error rate > 10%"
  
  initial_assessment: "Qdrant appears unresponsive"
  
  # Automatic mobilization
  primary_responders:
    - vector-specialist  # Domain owner
    - infra-architect    # Infrastructure
    - observability-sre  # Diagnostics
  
  standby:
    - postgres-wizard    # If DB related
    - performance-hunter # If optimization needed

# During incident - rapid updates
update:
  from: vector-specialist
  timestamp: "2025-12-27T15:45:00Z"
  finding: "HNSW index corruption after disk full event"
  action: "Rebuilding index from backup"
  eta: "30 minutes"

# Resolution
resolution:
  root_cause: "Disk full caused partial index write"
  fix_applied: "Rebuilt index, added disk space alerts"
  follow_ups:
    - owner: infra-architect
      task: "Add disk space monitoring and alerts"
    - owner: chaos-engineer
      task: "Add disk full scenario to chaos tests"
    - owner: docs-engineer
      task: "Update runbook for index corruption"
```

---

## Workflow Patterns

### Pattern A: New Feature

```
┌─────────────────────────────────────────────────────────────────────┐
│                     NEW FEATURE WORKFLOW                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. DESIGN PHASE                                                     │
│     └─► Primary: Domain specialist                                   │
│         └─► Consult: api-designer (if exposed)                       │
│         └─► Consult: privacy-guardian (if data)                      │
│         └─► Output: Design doc / ADR                                 │
│                                                                      │
│  2. REVIEW PHASE                                                     │
│     └─► code-reviewer: Architecture review                           │
│     └─► test-architect: Testability review                           │
│     └─► Affected specialists: Domain review                          │
│     └─► Output: Approved design                                      │
│                                                                      │
│  3. IMPLEMENTATION PHASE                                             │
│     └─► Primary: Domain specialist implements                        │
│     └─► python-craftsman: Code quality                               │
│     └─► test-architect: Test implementation                          │
│     └─► Output: Code + tests                                         │
│                                                                      │
│  4. REVIEW PHASE                                                     │
│     └─► code-reviewer: Code review                                   │
│     └─► Domain specialists: Technical review                         │
│     └─► performance-hunter: If performance-critical                  │
│     └─► Output: Approved code                                        │
│                                                                      │
│  5. DOCUMENTATION PHASE                                              │
│     └─► docs-engineer: User-facing docs                              │
│     └─► api-designer: API docs (if applicable)                       │
│     └─► Primary: Code comments and ADR                               │
│     └─► Output: Complete documentation                               │
│                                                                      │
│  6. DEPLOYMENT PHASE                                                 │
│     └─► migration-specialist: If schema changes                      │
│     └─► infra-architect: If infra changes                            │
│     └─► observability-sre: Monitoring setup                          │
│     └─► Output: Deployed feature                                     │
│                                                                      │
│  7. VALIDATION PHASE                                                 │
│     └─► chaos-engineer: Failure testing                              │
│     └─► observability-sre: Metrics validation                        │
│     └─► Output: Production-verified feature                          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Pattern B: Bug Fix

```
┌─────────────────────────────────────────────────────────────────────┐
│                       BUG FIX WORKFLOW                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. TRIAGE                                                           │
│     └─► code-reviewer classifies bug                                 │
│     └─► Routes to domain specialist                                  │
│                                                                      │
│  2. INVESTIGATION                                                    │
│     └─► Domain specialist investigates                               │
│     └─► Consults observability-sre for logs/traces                   │
│     └─► Output: Root cause identified                                │
│                                                                      │
│  3. FIX                                                              │
│     └─► Domain specialist implements fix                             │
│     └─► test-architect adds regression test                          │
│     └─► Output: Fix + test                                           │
│                                                                      │
│  4. REVIEW                                                           │
│     └─► code-reviewer: Quick review                                  │
│     └─► Domain expert: Sanity check                                  │
│     └─► Output: Approved fix                                         │
│                                                                      │
│  5. DEPLOY                                                           │
│     └─► Fast path to production                                      │
│     └─► observability-sre monitors                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Pattern C: Performance Optimization

```
┌─────────────────────────────────────────────────────────────────────┐
│                  PERFORMANCE OPTIMIZATION WORKFLOW                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. MEASUREMENT                                                      │
│     └─► performance-hunter profiles system                           │
│     └─► observability-sre provides metrics                           │
│     └─► Output: Bottleneck identified with data                      │
│                                                                      │
│  2. ANALYSIS                                                         │
│     └─► Domain specialist explains behavior                          │
│     └─► performance-hunter proposes optimizations                    │
│     └─► Output: Optimization plan with expected gains                │
│                                                                      │
│  3. IMPLEMENTATION                                                   │
│     └─► Collaboration between:                                       │
│         - performance-hunter (optimization)                          │
│         - Domain specialist (correctness)                            │
│         - postgres-wizard (if DB-related)                            │
│     └─► Output: Optimized code                                       │
│                                                                      │
│  4. VALIDATION                                                       │
│     └─► test-architect ensures no regressions                        │
│     └─► performance-hunter benchmarks improvement                    │
│     └─► Output: Measured improvement                                 │
│                                                                      │
│  5. DOCUMENTATION                                                    │
│     └─► docs-engineer documents the optimization                     │
│     └─► For future reference and learning                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Quality Gates

Every change must pass these gates:

```yaml
gates:
  
  # Gate 1: Code Quality
  code_quality:
    owner: code-reviewer
    checks:
      - "Follows CLAUDE.md standards"
      - "Types are complete"
      - "No obvious bugs"
      - "Appropriate abstraction"
    blocking: true
  
  # Gate 2: Testing
  testing:
    owner: test-architect
    checks:
      - "Unit tests pass"
      - "Integration tests pass"
      - "Coverage threshold met"
      - "No flaky tests added"
    blocking: true
  
  # Gate 3: Security
  security:
    owner: privacy-guardian
    checks:
      - "No secrets in code"
      - "No PII in logs"
      - "Input validation present"
      - "Auth checks complete"
    blocking: true
  
  # Gate 4: Performance
  performance:
    owner: performance-hunter
    checks:
      - "No N+1 queries"
      - "Appropriate caching"
      - "Benchmarks pass"
    blocking: false  # Warning, not blocking
    blocking_for: ["hot_path", "data_intensive"]
  
  # Gate 5: Documentation
  documentation:
    owner: docs-engineer
    checks:
      - "Code has docstrings"
      - "API docs updated"
      - "ADR if architectural"
    blocking: false
    blocking_for: ["new_feature", "api_change"]
  
  # Gate 6: Observability
  observability:
    owner: observability-sre
    checks:
      - "Metrics exposed"
      - "Logs structured"
      - "Traces propagated"
    blocking: false
    blocking_for: ["new_service", "critical_path"]
```

---

## Learning & Improvement

### After Every Significant Task

```yaml
retrospective:
  what_went_well:
    - "Vector search optimization reduced p99 by 40%"
    - "Cross-pod collaboration was smooth"
  
  what_could_improve:
    - "Should have consulted postgres-wizard earlier"
    - "Missing test case that would have caught bug"
  
  learnings:
    - pattern: "Always benchmark before and after optimization"
      add_to: performance-hunter skill
    
    - sharp_edge: "FalkorDB MATCH without LIMIT can timeout"
      add_to: graph-engineer skill
    
    - question: "Did we consider the failure mode?"
      add_to: code-reviewer checklist
```

### Skill Evolution

Skills should grow from experience:

```yaml
skill_update:
  skill: postgres-wizard
  type: add_sharp_edge
  
  content: |
    ### Partial Index Gotcha (Discovered 2025-12-27)
    
    When using partial indexes with `WHERE valid_until IS NULL`:
    - The planner only uses the index if query has EXACT same condition
    - `WHERE valid_until IS NULL AND ...` works
    - `WHERE (valid_until IS NULL OR valid_until > now())` does NOT use the index
    
    Learned from: Memory retrieval optimization, PR #456
  
  added_by: postgres-wizard
  validated_by: performance-hunter
```

---

## Emergency Protocols

### When to Escalate

```yaml
escalation_triggers:
  
  immediate:
    - "Production is down"
    - "Data breach suspected"
    - "Security vulnerability discovered"
    action: "All hands incident response"
  
  urgent:
    - "Performance degraded >50%"
    - "Error rate >5%"
    - "Critical bug in production"
    action: "Primary responders + domain expert"
  
  normal:
    - "Bug affecting subset of users"
    - "Non-critical performance issue"
    - "Technical debt concern"
    action: "Route to appropriate specialist"
```

### The Unblocking Protocol

When an agent is stuck:

```
1. TIMEBOX: 30 minutes of solo investigation
2. ASK: Consult the most relevant specialist
3. PAIR: If still stuck, pair with specialist
4. ESCALATE: If blocking critical path, broadcast for help
5. DOCUMENT: Whatever the solution, document it
```

---

## Success Metrics

### Team Health

| Metric | Target | Measured By |
|--------|--------|-------------|
| Handoff clarity | >90% no-clarification-needed | Receiving agent feedback |
| Review turnaround | <4 hours for normal, <1 hour for urgent | Timestamps |
| Conflict resolution | <2 escalations/week | Escalation log |
| Knowledge sharing | 1+ skill update/week | Skill changelog |
| Cross-pod collaboration | Every feature involves 2+ pods | PR tags |

### Output Quality

| Metric | Target | Measured By |
|--------|--------|-------------|
| Production incidents | <1/week | Incident log |
| Post-merge bugs | <5% of PRs | Bug tracking |
| Test coverage | >80% | CI metrics |
| Documentation completeness | 100% public APIs | Doc audit |
| Performance regressions | 0 unintended | Benchmark CI |

---

*This is how 20 specialists become one world-class team.*
