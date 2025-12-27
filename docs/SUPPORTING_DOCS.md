# Mind v5 Supporting Documents

> **Purpose**: Additional MD files to bring into the project for excellence
> **Status**: Ready to use

---

## Document 1: ARCHITECTURE_DECISIONS.md

```markdown
# Architecture Decision Records (ADRs)

## ADR-001: Event Backbone Selection

**Status**: Accepted
**Date**: 2025-12-27

### Context
We need a message backbone for event sourcing that handles 100K+ events/sec with sub-millisecond latency.

### Decision
Use **NATS JetStream** as primary, with Kafka as scale fallback.

### Rationale
- NATS: 200-400K msg/sec, sub-ms latency, 17MB binary
- Kafka: 1M+ msg/sec but 10-50ms latency, complex ops
- NATS sufficient for Phase 1-4, Kafka for Intent Graph scale

### Consequences
- Simpler operations initially
- May need migration at extreme scale
- Team needs NATS training

---

## ADR-002: Vector Database Selection

**Status**: Accepted
**Date**: 2025-12-27

### Context
We need vector search with <50ms p99 latency at 10M+ vectors.

### Decision
Use **Qdrant** as primary, **pgvectorscale** as fallback.

### Rationale
- Qdrant: 38ms p99, best tail latency
- pgvectorscale: 11.4x throughput, good for batch
- Keep option open for Postgres-only deployment

### Consequences
- Two vector systems to maintain
- Qdrant requires separate infrastructure
- Better latency for hot path

---

## ADR-003: Graph Database Selection

**Status**: Accepted
**Date**: 2025-12-27

### Context
We need a graph database for causal knowledge with <150ms traversal.

### Decision
Use **FalkorDB** as primary, **Neo4j** as mature fallback.

### Rationale
- FalkorDB: 500x faster p99 than Neo4j
- Redis-native, operational simplicity
- Cypher compatible for migration

### Consequences
- FalkorDB is newer, smaller community
- Neo4j available if needed
- Redis dependency

---

## ADR-004: Memory Layer Architecture

**Status**: Accepted
**Date**: 2025-12-27

### Context
We need a temporal memory system that learns from outcomes.

### Decision
Build on **Zep/Graphiti** patterns with custom outcome learning.

### Rationale
- Zep: 94.8% DMR accuracy, temporal KG
- Add hierarchical levels (4-tier)
- Add outcome-weighted salience (custom)

### Consequences
- Depends on Zep evolution
- Custom outcome learning is novel
- Need to validate approach

---

## ADR-005: Workflow Orchestration

**Status**: Accepted
**Date**: 2025-12-27

### Context
We need durable execution for long-running workflows.

### Decision
Use **Temporal.io** for all background workflows.

### Rationale
- Production-proven (Stripe, Netflix, Snap)
- Durable execution with automatic retry
- Python SDK mature

### Consequences
- Temporal cluster to operate
- Team needs Temporal training
- Excellent visibility into workflows
```

---

## Document 2: API_CONTRACTS.md

```markdown
# API Contracts

## Memory Service API

### Endpoints

#### POST /v1/memories
Create a new memory from interaction.

**Request:**
```json
{
  "user_id": "uuid",
  "content": "string",
  "source": "interaction|extraction|import",
  "metadata": {
    "session_id": "uuid",
    "confidence": 0.95
  }
}
```

**Response:**
```json
{
  "memory_id": "uuid",
  "temporal_level": "immediate|situational|seasonal|identity",
  "created_at": "iso8601"
}
```

#### POST /v1/context/retrieve
Retrieve relevant context for a query.

**Request:**
```json
{
  "user_id": "uuid",
  "query": "string",
  "limit": 20,
  "include_causal": true,
  "temporal_levels": ["immediate", "identity"]
}
```

**Response:**
```json
{
  "memories": [
    {
      "memory_id": "uuid",
      "content": "string",
      "temporal_level": "identity",
      "effective_salience": 0.87,
      "causal_context": [
        {
          "relationship": "causes",
          "target": "increased_focus",
          "strength": 0.73
        }
      ]
    }
  ],
  "retrieval_latency_ms": 45
}
```

#### POST /v1/decisions/record
Record a decision for outcome tracking.

**Request:**
```json
{
  "user_id": "uuid",
  "session_id": "uuid",
  "memory_ids": ["uuid"],
  "decision_type": "recommendation|action|response",
  "decision_content": "string",
  "confidence": 0.85
}
```

**Response:**
```json
{
  "trace_id": "uuid",
  "created_at": "iso8601"
}
```

#### POST /v1/decisions/{trace_id}/outcome
Record outcome for a decision.

**Request:**
```json
{
  "outcome_quality": 0.8,
  "outcome_signal": "user_feedback|implicit|explicit"
}
```

**Response:**
```json
{
  "updated": true,
  "memories_adjusted": 5
}
```

---

## gRPC Service Definitions

```protobuf
syntax = "proto3";

package mind.v1;

service MemoryService {
  rpc StoreMemory(StoreMemoryRequest) returns (StoreMemoryResponse);
  rpc RetrieveContext(RetrieveContextRequest) returns (RetrieveContextResponse);
  rpc RecordDecision(RecordDecisionRequest) returns (RecordDecisionResponse);
  rpc RecordOutcome(RecordOutcomeRequest) returns (RecordOutcomeResponse);
  
  // Streaming for batch operations
  rpc StreamMemories(StreamMemoriesRequest) returns (stream Memory);
}

service CausalService {
  rpc QueryCausalChain(CausalChainRequest) returns (CausalChainResponse);
  rpc PredictIntervention(InterventionRequest) returns (InterventionResponse);
}
```
```

---

## Document 3: TESTING_STRATEGY.md

```markdown
# Testing Strategy

## Test Pyramid

```
        /\
       /  \     E2E Tests (10%)
      /    \    - Full system tests
     /------\   - Critical paths only
    /        \  
   /  Integ   \ Integration Tests (30%)
  /    Tests   \ - Database tests
 /--------------\ - Service tests
/                \
/   Unit Tests    \ Unit Tests (60%)
/------------------\ - Fast, isolated
```

## Unit Testing Standards

### Coverage Target: 80%

```python
# Every public function needs tests
# Test file: tests/unit/core/memory/test_retrieval.py

import pytest
from unittest.mock import AsyncMock

class TestMemoryRetrieval:
    @pytest.fixture
    def retriever(self):
        return MemoryRetriever(
            db=AsyncMock(),
            qdrant=AsyncMock(),
            cache=AsyncMock(),
        )
    
    @pytest.mark.asyncio
    async def test_retrieves_by_salience_order(self, retriever):
        """Memories should be ordered by effective salience."""
        # Arrange
        retriever.db.fetch.return_value = [
            Memory(salience=0.5),
            Memory(salience=0.9),
            Memory(salience=0.7),
        ]
        
        # Act
        result = await retriever.retrieve(user_id, "query")
        
        # Assert
        saliences = [m.salience for m in result]
        assert saliences == [0.9, 0.7, 0.5]
    
    @pytest.mark.asyncio
    async def test_handles_empty_results(self, retriever):
        """Should return empty list, not error, when no results."""
        retriever.db.fetch.return_value = []
        
        result = await retriever.retrieve(user_id, "query")
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_respects_limit(self, retriever):
        """Should not return more than limit."""
        retriever.db.fetch.return_value = [Memory()] * 100
        
        result = await retriever.retrieve(user_id, "query", limit=10)
        
        assert len(result) <= 10
```

## Integration Testing

### Use Testcontainers

```python
# tests/integration/conftest.py
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("postgres:16") as pg:
        yield pg.get_connection_url()

@pytest.fixture(scope="session")  
def redis():
    with RedisContainer("redis:7") as r:
        yield r.get_connection_url()

@pytest.fixture
async def db(postgres):
    """Fresh database for each test."""
    async with get_connection(postgres) as conn:
        await conn.execute(SCHEMA)
        yield conn
        await conn.execute("TRUNCATE ALL")
```

## Performance Testing

### Benchmark Suite

```python
# tests/benchmarks/test_retrieval_performance.py
import pytest

@pytest.mark.benchmark
class TestRetrievalPerformance:
    
    @pytest.fixture
    def populated_db(self, db):
        """Database with 100K memories."""
        # Insert test data
        return db
    
    def test_retrieval_latency_p99(self, benchmark, populated_db):
        """p99 latency must be under 100ms."""
        result = benchmark.pedantic(
            lambda: retriever.retrieve(user_id, "query"),
            iterations=100,
            rounds=5,
        )
        
        assert result.stats.percentile(99) < 0.100  # 100ms
    
    def test_retrieval_throughput(self, benchmark, populated_db):
        """Must handle 1000 QPS."""
        result = benchmark.pedantic(
            lambda: asyncio.gather(*[
                retriever.retrieve(user_id, f"query_{i}")
                for i in range(100)
            ]),
            iterations=10,
        )
        
        qps = 100 / result.stats.mean
        assert qps >= 1000
```

## CI Pipeline

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[test]"
      - run: pytest tests/unit --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v4
  
  integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
      redis:
        image: redis:7
    steps:
      - uses: actions/checkout@v4
      - run: pytest tests/integration
  
  benchmark:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
      - run: pytest tests/benchmarks --benchmark-json=output.json
      - uses: benchmark-action/github-action-benchmark@v1
```
```

---

## Document 4: RUNBOOKS.md

```markdown
# Operational Runbooks

## Runbook: High Memory Retrieval Latency

### Symptoms
- `mind_retrieval_latency_seconds{quantile="0.99"} > 0.1`
- User complaints about slow responses

### Diagnosis Steps

1. **Check Qdrant health**
   ```bash
   curl http://qdrant:6333/health
   ```

2. **Check vector search latency**
   ```bash
   curl http://qdrant:6333/metrics | grep search_latency
   ```

3. **Check PostgreSQL connections**
   ```sql
   SELECT count(*) FROM pg_stat_activity;
   ```

4. **Check for slow queries**
   ```sql
   SELECT query, mean_time 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC LIMIT 10;
   ```

### Resolution Steps

1. **If Qdrant overloaded**: Scale up Qdrant replicas
2. **If PostgreSQL connections exhausted**: Increase pool size
3. **If slow queries**: Add missing indexes
4. **If cache miss rate high**: Increase cache TTL/size

---

## Runbook: Event Backlog Growing

### Symptoms
- NATS consumer lag increasing
- `nats_consumer_pending` > 10000

### Diagnosis Steps

1. **Check consumer health**
   ```bash
   nats consumer info MIND events
   ```

2. **Check worker CPU/memory**
   ```bash
   kubectl top pods -l app=mind-worker
   ```

3. **Check for errors in worker logs**
   ```bash
   kubectl logs -l app=mind-worker --tail=100
   ```

### Resolution Steps

1. **Scale workers**
   ```bash
   kubectl scale deployment mind-worker --replicas=10
   ```

2. **If DB bottleneck**: Scale database or optimize queries

3. **If persistent**: Enable batch processing mode

---

## Runbook: Temporal Workflow Failures

### Symptoms
- Workflow failure rate > 1%
- Alerts on `temporal_workflow_failed_total`

### Diagnosis Steps

1. **Check Temporal UI**
   - Go to http://temporal:8080
   - Filter by failed workflows
   - Check error message

2. **Check activity failures**
   ```bash
   temporal workflow show --workflow-id <id>
   ```

3. **Check worker logs**
   ```bash
   kubectl logs -l app=mind-gardener
   ```

### Resolution Steps

1. **If transient errors**: Workflows will auto-retry
2. **If persistent errors**: Fix bug, redeploy
3. **If stuck workflows**: Reset to last good checkpoint
   ```bash
   temporal workflow reset --workflow-id <id> --event-id <event>
   ```

---

## Runbook: Privacy Alert

### Symptoms
- Alert: "PII detected in federated pattern"
- Audit log shows sanitization failure

### IMMEDIATE ACTIONS

1. **Stop federation immediately**
   ```bash
   kubectl scale deployment pattern-federator --replicas=0
   ```

2. **Identify affected patterns**
   ```sql
   SELECT * FROM federated_patterns 
   WHERE created_at > NOW() - INTERVAL '1 hour';
   ```

3. **Delete affected patterns from federation**
   ```sql
   DELETE FROM federated_patterns WHERE pattern_id IN (...);
   ```

4. **Notify security team**
   - Page on-call security
   - Document incident timeline

### Post-Incident

1. Root cause analysis
2. Fix sanitization bug
3. Audit all recent patterns
4. Update PII detection rules
```

---

## Document 5: GLOSSARY.md

```markdown
# Mind v5 Glossary

## Core Concepts

### Memory
A unit of stored information about a user, extracted from interactions. Memories have temporal levels, salience scores, and can be linked to causal relationships.

### Temporal Level
One of four hierarchical levels for memory organization:
- **Immediate**: Current session, decays in hours
- **Situational**: Current context, decays in days
- **Seasonal**: Current projects/goals, decays in months
- **Identity**: Core values/preferences, decays in years

### Salience
A score (0-1) indicating how important/relevant a memory is. Composed of:
- **Base salience**: Initial importance based on source
- **Outcome adjustment**: Learning from decision outcomes
- **Effective salience**: base + adjustment, used for retrieval

### Decision Trace
A record of a decision made using context from the memory system. Links context used → decision made → outcome observed.

### Causal Edge
A directed relationship between entities indicating causation, not just correlation. Includes strength, conditions, temporal validity, and counterfactuals.

## Events

### InteractionRecorded
Raw interaction from a user session. Source of all memories.

### MemoryExtracted
A memory successfully extracted from an interaction.

### DecisionMade
A decision was made using retrieved context.

### OutcomeObserved
Feedback on a previous decision (positive/negative).

### CausalLinkDiscovered
A new causal relationship was inferred from data.

### PatternValidated
A local pattern met thresholds for federation.

## Metrics

### DSR (Decision Success Rate)
Percentage of decisions that led to positive outcomes. Target: >75%.

### CDQ (Causal Decision Quality)
Accuracy of causal predictions for interventions. Target: >70%.

### CIQ (Collective Intelligence Quotient)
Improvement from networked patterns vs isolated agent. Target: >15%.

### TIQ (Team Intelligence Quotient)
Team performance vs sum of individual agents. Target: >20%.

## Infrastructure

### Projection
A read model built from events. Can be rebuilt by replaying events.

### Gardener
Background workflow system (runs on Temporal) that maintains the memory system.

### Federation
Privacy-preserving sharing of patterns across users via Intent Graph.

### RRF (Reciprocal Rank Fusion)
Algorithm for combining results from multiple retrieval sources.
```

---

## Document 6: SECURITY_CHECKLIST.md

```markdown
# Security Checklist

## Before Every PR

### Code Review
- [ ] No secrets in code (use environment variables)
- [ ] No PII in logs or error messages
- [ ] Input validation on all external inputs
- [ ] SQL uses parameterized queries
- [ ] Authentication required on all endpoints

### Data Handling
- [ ] Sensitive fields encrypted at rest
- [ ] TLS for all network communication
- [ ] User data scoped by user_id
- [ ] No cross-user data leakage possible

### Dependencies
- [ ] `pip audit` passes
- [ ] No known CVEs in dependencies
- [ ] Dependencies pinned to specific versions

## Before Every Deploy

### Infrastructure
- [ ] Secrets rotated if compromised
- [ ] Database backups verified
- [ ] Encryption keys backed up securely
- [ ] Network policies restrict access

### Access Control
- [ ] IAM roles follow least privilege
- [ ] Service accounts have minimal permissions
- [ ] Audit logging enabled

### Federation (if applicable)
- [ ] Differential privacy budget tracked
- [ ] Minimum aggregation thresholds enforced
- [ ] No PII in federated patterns
- [ ] Sanitization tests passing

## Quarterly Review

- [ ] Access audit: who has access to what?
- [ ] Secret rotation: all secrets < 90 days old
- [ ] Penetration testing scheduled
- [ ] Incident response plan reviewed
- [ ] Data retention policies enforced
```

---

## Document 7: ONBOARDING.md

```markdown
# Developer Onboarding

## Day 1: Environment Setup

### Prerequisites
- Python 3.12+
- Docker + Docker Compose
- kubectl (for production debugging)

### Steps

1. **Clone repository**
   ```bash
   git clone git@github.com:org/mind-v5.git
   cd mind-v5
   ```

2. **Install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. **Start local services**
   ```bash
   docker compose up -d
   ```

4. **Run tests**
   ```bash
   pytest tests/unit
   ```

5. **Read CLAUDE.md**
   - Understand project structure
   - Learn code standards
   - Know the architecture principles

## Day 2-3: Understand the System

### Read These Documents
1. CLAUDE.md (this file)
2. ARCHITECTURE_DECISIONS.md
3. API_CONTRACTS.md
4. GLOSSARY.md

### Run the System
1. Start all services locally
2. Send test requests
3. Watch the event flow
4. Query the databases directly

### Review Recent PRs
- Understand code patterns
- See how reviews work
- Learn from feedback

## Week 1: First Contribution

### Good First Issues
- Documentation improvements
- Test coverage increases
- Small bug fixes
- Logging improvements

### PR Process
1. Create feature branch
2. Write tests first
3. Implement feature
4. Self-review against CLAUDE.md
5. Request review
6. Address feedback
7. Merge when approved

## Week 2+: Deeper Work

### Pick a Skill Area
- Event systems
- Graph engineering
- Vector search
- Memory architecture
- Causal inference

### Pair with Expert
- Schedule pairing sessions
- Learn the sharp edges
- Understand the "why"

### Contribute to Skills
- Document what you learn
- Add to skill definitions
- Help the next person
```

---

## Summary: All Documents to Create

| Document | Purpose |
|----------|---------|
| `CLAUDE.md` | Master ruleset for Claude Code |
| `SKILLS.md` | Skill definitions for Spawner agents |
| `ARCHITECTURE_DECISIONS.md` | ADRs for key decisions |
| `API_CONTRACTS.md` | API specifications |
| `TESTING_STRATEGY.md` | Testing approach and standards |
| `RUNBOOKS.md` | Operational procedures |
| `GLOSSARY.md` | Term definitions |
| `SECURITY_CHECKLIST.md` | Security requirements |
| `ONBOARDING.md` | New developer guide |
| `CHANGELOG.md` | Version history |
| `CONTRIBUTING.md` | Contribution guidelines |
| `CODE_OF_CONDUCT.md` | Community standards |
