# CLAUDE.md - Mind v5 Development Guidelines

> **Project**: Mind v5 + Spawner Integration
> **Goal**: Best-in-class decision intelligence system
> **Standards**: Production-grade, maintainable, secure, scalable

---

## 🎯 Project Identity

You are building **Mind v5**, the intelligence layer that helps AI agents make better decisions over time. This is not a toy project. This system will:
- Store and reason about user context across years
- Learn from decision outcomes to improve future recommendations
- Enable collective intelligence across users while preserving privacy
- Power agentic teams that self-organize for optimal performance

**Every line of code matters. Build it like lives depend on it.**

---

## 🏗️ Architecture Principles

### The Five Laws of Mind v5

1. **Events are Sacred**
   - All state changes flow through the event backbone
   - Events are immutable, append-only, never deleted
   - If it's not in the event log, it didn't happen
   - Projections can always be rebuilt from events

2. **Memory Serves Decisions**
   - Memory exists to improve decision quality, not just storage
   - Every retrieval should be traced to outcomes
   - Memories that lead to good decisions gain salience
   - Memories that mislead get demoted

3. **Causality Over Correlation**
   - Store WHY, not just WHAT
   - Every important relationship should have causal metadata
   - Enable counterfactual reasoning ("what if...")
   - Distinguish causes from correlations explicitly

4. **Privacy is Non-Negotiable**
   - User data never leaves their Mind without explicit consent
   - Federated patterns are sanitized with differential privacy
   - No PII in logs, traces, or error messages
   - Encryption at rest, in transit, always

5. **Failure is Expected**
   - Every external call will eventually fail
   - Design for graceful degradation
   - Temporal.io workflows are your friend
   - Chaos monkey should be survivable

---

## 📁 Project Structure

```
mind-v5/
├── CLAUDE.md                    # This file - read first
├── README.md                    # Project overview
├── docs/
│   ├── architecture/            # ADRs and design docs
│   ├── api/                     # API specifications
│   ├── runbooks/                # Operational procedures
│   └── skills/                  # AI agent skill definitions
│
├── src/
│   ├── core/                    # Core domain logic
│   │   ├── events/              # Event definitions
│   │   ├── memory/              # Memory management
│   │   ├── causal/              # Causal inference
│   │   └── decision/            # Decision tracking
│   │
│   ├── infrastructure/          # External integrations
│   │   ├── postgres/            # PostgreSQL adapters
│   │   ├── qdrant/              # Vector DB adapters
│   │   ├── falkordb/            # Graph DB adapters
│   │   ├── nats/                # Event backbone
│   │   └── temporal/            # Workflow orchestration
│   │
│   ├── api/                     # API layer
│   │   ├── grpc/                # gRPC services
│   │   ├── rest/                # REST endpoints
│   │   └── graphql/             # GraphQL (if needed)
│   │
│   ├── workers/                 # Background workers
│   │   ├── gardener/            # Temporal workflows
│   │   ├── projectors/          # Event projectors
│   │   └── extractors/          # Memory extractors
│   │
│   └── shared/                  # Shared utilities
│       ├── errors/              # Error types
│       ├── logging/             # Structured logging
│       ├── metrics/             # Observability
│       └── security/            # Auth, encryption
│
├── tests/
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   ├── e2e/                     # End-to-end tests
│   └── benchmarks/              # Performance tests
│
├── deploy/
│   ├── docker/                  # Docker configurations
│   ├── k8s/                     # Kubernetes manifests
│   └── terraform/               # Infrastructure as code
│
└── scripts/                     # Development scripts
```

---

## 💻 Code Standards

### Language: Python 3.12+ (Primary), Rust (Performance-Critical)

**Why Python**: 
- DSPy, DoWhy, ML ecosystem
- Temporal SDK maturity
- Rapid iteration

**Why Rust (selective)**:
- Event processing hot paths
- Embedding generation
- Memory-critical components

### Python Standards

```python
# ✅ GOOD: Type hints everywhere, explicit, documented
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from uuid import UUID

@dataclass(frozen=True)  # Immutable by default
class Memory:
    """
    A single memory unit in the hierarchical memory system.
    
    Memories are immutable once created. Updates create new versions.
    Salience is adjusted based on decision outcomes.
    """
    memory_id: UUID
    user_id: UUID
    content: str
    temporal_level: TemporalLevel
    valid_from: datetime
    valid_until: Optional[datetime]
    base_salience: float
    outcome_adjustment: float = 0.0
    
    @property
    def effective_salience(self) -> float:
        """Salience after outcome-based adjustment."""
        return max(0.0, min(1.0, self.base_salience + self.outcome_adjustment))
    
    def with_outcome_adjustment(self, delta: float) -> "Memory":
        """Return new Memory with adjusted salience. Original unchanged."""
        return Memory(
            memory_id=self.memory_id,
            user_id=self.user_id,
            content=self.content,
            temporal_level=self.temporal_level,
            valid_from=self.valid_from,
            valid_until=self.valid_until,
            base_salience=self.base_salience,
            outcome_adjustment=self.outcome_adjustment + delta,
        )


# ❌ BAD: No types, mutable, unclear purpose
class Memory:
    def __init__(self, id, content):
        self.id = id
        self.content = content
        self.salience = 1.0
    
    def update(self, delta):
        self.salience += delta  # Mutation!
```

### Error Handling

```python
# ✅ GOOD: Explicit error types, no silent failures
from enum import Enum
from dataclasses import dataclass
from typing import TypeVar, Generic

T = TypeVar('T')

class ErrorCode(Enum):
    MEMORY_NOT_FOUND = "MEMORY_NOT_FOUND"
    INVALID_TEMPORAL_LEVEL = "INVALID_TEMPORAL_LEVEL"
    CAUSAL_CYCLE_DETECTED = "CAUSAL_CYCLE_DETECTED"
    PRIVACY_VIOLATION = "PRIVACY_VIOLATION"
    DATABASE_ERROR = "DATABASE_ERROR"

@dataclass
class MindError(Exception):
    """Base error for all Mind operations."""
    code: ErrorCode
    message: str
    context: dict = None
    
    def __str__(self) -> str:
        return f"[{self.code.value}] {self.message}"

@dataclass
class Result(Generic[T]):
    """Explicit success/failure wrapper. Never raise for expected failures."""
    value: Optional[T] = None
    error: Optional[MindError] = None
    
    @property
    def is_ok(self) -> bool:
        return self.error is None
    
    @classmethod
    def ok(cls, value: T) -> "Result[T]":
        return cls(value=value)
    
    @classmethod
    def err(cls, error: MindError) -> "Result[T]":
        return cls(error=error)


# Usage
async def get_memory(memory_id: UUID) -> Result[Memory]:
    try:
        memory = await db.fetch_memory(memory_id)
        if memory is None:
            return Result.err(MindError(
                code=ErrorCode.MEMORY_NOT_FOUND,
                message=f"Memory {memory_id} not found",
                context={"memory_id": str(memory_id)}
            ))
        return Result.ok(memory)
    except DatabaseException as e:
        return Result.err(MindError(
            code=ErrorCode.DATABASE_ERROR,
            message="Failed to fetch memory",
            context={"original_error": str(e)}  # Never log PII!
        ))
```

### Logging Standards

```python
# ✅ GOOD: Structured, contextual, NO PII
import structlog

logger = structlog.get_logger()

async def process_decision(user_id: UUID, decision: Decision) -> Result[Trace]:
    log = logger.bind(
        user_id=str(user_id),  # UUID only, not name/email
        decision_id=str(decision.decision_id),
        operation="process_decision"
    )
    
    log.info("processing_decision_started")
    
    result = await memory_service.retrieve_context(user_id, decision.query)
    if not result.is_ok:
        log.error("context_retrieval_failed", error_code=result.error.code.value)
        return Result.err(result.error)
    
    log.info(
        "context_retrieved",
        memory_count=len(result.value),
        retrieval_ms=result.latency_ms
    )
    
    # NEVER log: content, user data, PII, secrets
    # ❌ BAD: log.info("retrieved", memories=result.value)
    
    return Result.ok(trace)
```

### Testing Standards

```python
# Every public function needs tests
# Test files mirror source structure: src/core/memory/retrieval.py -> tests/unit/core/memory/test_retrieval.py

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

class TestMemoryRetrieval:
    """Tests for memory retrieval with outcome weighting."""
    
    @pytest.fixture
    def sample_memories(self) -> List[Memory]:
        """Fixture: representative memory set."""
        return [
            Memory(
                memory_id=uuid4(),
                user_id=uuid4(),
                content="User prefers detailed explanations",
                temporal_level=TemporalLevel.IDENTITY,
                valid_from=datetime(2024, 1, 1),
                valid_until=None,
                base_salience=0.9,
                outcome_adjustment=0.05,  # Proven helpful
            ),
            # ... more fixtures
        ]
    
    @pytest.mark.asyncio
    async def test_retrieval_orders_by_effective_salience(
        self, 
        sample_memories: List[Memory]
    ):
        """Memories with better outcomes should rank higher."""
        # Arrange
        retriever = MemoryRetriever(db=AsyncMock())
        retriever.db.fetch_memories.return_value = sample_memories
        
        # Act
        result = await retriever.retrieve(
            user_id=uuid4(),
            query="How should I explain this?",
            limit=5
        )
        
        # Assert
        assert result.is_ok
        memories = result.value
        saliences = [m.effective_salience for m in memories]
        assert saliences == sorted(saliences, reverse=True), \
            "Memories must be ordered by effective salience"
    
    @pytest.mark.asyncio
    async def test_retrieval_respects_temporal_validity(self):
        """Expired memories should not be retrieved."""
        # ... test implementation
    
    @pytest.mark.asyncio
    async def test_retrieval_handles_database_failure_gracefully(self):
        """Database errors should return Result.err, not raise."""
        # ... test implementation


# Integration tests use real databases (in containers)
@pytest.mark.integration
class TestMemoryRetrievalIntegration:
    """Integration tests against real PostgreSQL + Qdrant."""
    
    @pytest.fixture(scope="class")
    async def database(self):
        """Spin up test containers."""
        async with TestContainers() as containers:
            yield containers.get_connection()
    
    # ... integration tests
```

---

## 🔒 Security Standards

### Secrets Management

```python
# ✅ GOOD: Secrets from environment/Vault, never hardcoded
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Configuration loaded from environment."""
    
    # Database
    postgres_url: SecretStr
    qdrant_api_key: SecretStr
    falkordb_password: SecretStr
    
    # API Keys
    openai_api_key: SecretStr
    anthropic_api_key: SecretStr
    
    # Security
    jwt_secret: SecretStr
    encryption_key: SecretStr
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Usage: settings.postgres_url.get_secret_value()
# NEVER: print(settings.postgres_url) or log it

# ❌ NEVER DO THIS
OPENAI_KEY = "sk-..."  # Hardcoded secret
```

### Data Encryption

```python
# All PII encrypted at rest
from cryptography.fernet import Fernet

class EncryptedField:
    """Transparent encryption for sensitive fields."""
    
    def __init__(self, key: bytes):
        self.fernet = Fernet(key)
    
    def encrypt(self, plaintext: str) -> bytes:
        return self.fernet.encrypt(plaintext.encode())
    
    def decrypt(self, ciphertext: bytes) -> str:
        return self.fernet.decrypt(ciphertext).decode()


# Memory content is always encrypted
@dataclass
class EncryptedMemory:
    memory_id: UUID
    user_id: UUID
    encrypted_content: bytes  # Encrypted at rest
    # ... other fields
```

### Privacy Enforcement

```python
# Federation patterns MUST be sanitized
@dataclass
class SanitizedPattern:
    """Pattern safe for cross-user federation."""
    
    pattern_id: UUID
    trigger_type: str  # Abstract category, not specific content
    response_strategy: str
    outcome_improvement: float
    
    # Privacy guarantees
    source_count: int  # Must be >= 100
    user_count: int  # Must be >= 10
    epsilon: float = 0.1  # Differential privacy parameter
    
    def validate_privacy(self) -> bool:
        """Ensure pattern meets privacy thresholds."""
        return (
            self.source_count >= 100 and
            self.user_count >= 10 and
            self.epsilon <= 0.1 and
            not self._contains_pii()
        )
    
    def _contains_pii(self) -> bool:
        """Check for any PII leakage."""
        # Names, emails, specific content, etc.
        # This should be thorough
        pass
```

---

## 📊 Observability Standards

### Metrics (Prometheus)

```python
from prometheus_client import Counter, Histogram, Gauge

# Standard metrics for every service
REQUESTS_TOTAL = Counter(
    "mind_requests_total",
    "Total requests",
    ["service", "method", "status"]
)

REQUEST_LATENCY = Histogram(
    "mind_request_latency_seconds",
    "Request latency",
    ["service", "method"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
)

# Mind-specific metrics
DECISION_SUCCESS_RATE = Gauge(
    "mind_decision_success_rate",
    "Rolling decision success rate",
    ["user_cohort"]
)

MEMORY_RETRIEVAL_RELEVANCE = Histogram(
    "mind_memory_retrieval_relevance",
    "Relevance score of retrieved memories",
    ["temporal_level"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

CAUSAL_PREDICTION_ACCURACY = Gauge(
    "mind_causal_prediction_accuracy",
    "Accuracy of causal outcome predictions",
    ["prediction_type"]
)
```

### Tracing (OpenTelemetry)

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer("mind.memory")

async def retrieve_context(user_id: UUID, query: str) -> Result[List[Memory]]:
    with tracer.start_as_current_span("retrieve_context") as span:
        span.set_attribute("user_id", str(user_id))
        span.set_attribute("query_length", len(query))
        
        # Vector search
        with tracer.start_as_current_span("vector_search"):
            vector_results = await qdrant.search(query)
            span.set_attribute("vector_results", len(vector_results))
        
        # Graph traversal
        with tracer.start_as_current_span("graph_traversal"):
            graph_results = await falkordb.traverse(query)
            span.set_attribute("graph_results", len(graph_results))
        
        # Fusion
        with tracer.start_as_current_span("rrf_fusion"):
            fused = reciprocal_rank_fusion(vector_results, graph_results)
        
        span.set_status(Status(StatusCode.OK))
        return Result.ok(fused)
```

---

## 🔄 Git Workflow

### Branch Naming

```
main              # Production-ready, protected
├── develop       # Integration branch
├── feature/*     # New features: feature/causal-edge-schema
├── fix/*         # Bug fixes: fix/memory-retrieval-timeout
├── refactor/*    # Refactoring: refactor/event-handler-cleanup
└── docs/*        # Documentation: docs/api-specification
```

### Commit Messages

```
# Format: <type>(<scope>): <subject>
#
# Types: feat, fix, refactor, docs, test, chore, perf
# Scope: core, memory, causal, api, infra, gardener, etc.

# ✅ GOOD
feat(memory): add outcome-weighted salience to retrieval
fix(causal): prevent cycles in causal graph insertion
refactor(api): extract common validation logic
test(memory): add integration tests for hierarchical retrieval
perf(events): optimize NATS batch publishing

# ❌ BAD
fixed stuff
update
WIP
```

### Pull Request Template

```markdown
## Description
[What does this PR do?]

## Type of Change
- [ ] Feature
- [ ] Bug fix
- [ ] Refactor
- [ ] Documentation
- [ ] Performance improvement

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Security Checklist
- [ ] No secrets in code
- [ ] No PII in logs
- [ ] Input validation added
- [ ] Error messages don't leak sensitive info

## Documentation
- [ ] Code comments updated
- [ ] API docs updated (if applicable)
- [ ] CHANGELOG updated

## Checklist
- [ ] Self-reviewed code
- [ ] Types are complete
- [ ] Tests pass locally
- [ ] No new warnings
```

---

## 🚀 Performance Guidelines

### Database Queries

```python
# ✅ GOOD: Batched, indexed, with limits
async def get_user_memories(
    user_id: UUID,
    limit: int = 100,
    offset: int = 0
) -> List[Memory]:
    query = """
        SELECT * FROM memories
        WHERE user_id = $1
          AND valid_until IS NULL  -- Only active memories
        ORDER BY effective_salience DESC
        LIMIT $2 OFFSET $3
    """
    return await db.fetch_all(query, user_id, limit, offset)


# ❌ BAD: Unbounded, unindexed
async def get_all_memories(user_id: UUID):
    return await db.fetch_all(
        "SELECT * FROM memories WHERE user_id = $1",
        user_id
    )  # Could return millions!
```

### Async Everywhere

```python
# ✅ GOOD: Concurrent I/O
async def retrieve_multi_source(query: str) -> FusedResults:
    # Run all searches concurrently
    vector_task = asyncio.create_task(qdrant.search(query))
    graph_task = asyncio.create_task(falkordb.traverse(query))
    keyword_task = asyncio.create_task(postgres.fulltext(query))
    
    vector, graph, keyword = await asyncio.gather(
        vector_task, graph_task, keyword_task,
        return_exceptions=True
    )
    
    # Handle partial failures gracefully
    results = []
    if not isinstance(vector, Exception):
        results.extend(vector)
    # ... etc
    
    return fuse(results)


# ❌ BAD: Sequential I/O
async def retrieve_slow(query: str):
    vector = await qdrant.search(query)  # Wait...
    graph = await falkordb.traverse(query)  # Wait more...
    keyword = await postgres.fulltext(query)  # Even more...
    return fuse(vector, graph, keyword)
```

### Caching Strategy

```python
from functools import lru_cache
from aiocache import cached, Cache

# Hot data: In-memory with TTL
@cached(ttl=300, cache=Cache.MEMORY)  # 5 min TTL
async def get_user_identity_memories(user_id: UUID) -> List[Memory]:
    """Identity-level memories change rarely, cache aggressively."""
    return await db.fetch_identity_memories(user_id)


# Warm data: Redis with longer TTL
@cached(ttl=3600, cache=Cache.REDIS)  # 1 hour TTL
async def get_federated_patterns(trigger_type: str) -> List[Pattern]:
    """Patterns shared across users, very stable."""
    return await db.fetch_patterns(trigger_type)


# Cold data: No caching, always fresh
async def get_recent_decisions(user_id: UUID) -> List[Decision]:
    """Recent decisions need real-time accuracy."""
    return await db.fetch_recent_decisions(user_id)
```

---

## 📋 Definition of Done

A feature is DONE when:

1. **Code Complete**
   - [ ] Implementation matches specification
   - [ ] Types are complete and correct
   - [ ] No TODO comments (create issues instead)
   - [ ] Code reviewed and approved

2. **Tested**
   - [ ] Unit tests pass (>80% coverage)
   - [ ] Integration tests pass
   - [ ] Performance benchmarks meet SLOs
   - [ ] Security scan passes

3. **Documented**
   - [ ] Code has docstrings
   - [ ] API changes documented
   - [ ] Runbook updated if operational change

4. **Observable**
   - [ ] Metrics exposed
   - [ ] Logs structured
   - [ ] Traces propagated
   - [ ] Alerts configured

5. **Deployed**
   - [ ] Migrations run
   - [ ] Feature flags configured
   - [ ] Canary deployment successful
   - [ ] Rollback tested

---

## 🆘 When You're Stuck

1. **Check the ADRs** in `docs/architecture/` - someone may have decided this already
2. **Search the codebase** - similar patterns exist
3. **Ask the team** - we're building this together
4. **Write a spike** - quick prototype to learn
5. **Document the decision** - help the next person

---

## 📚 Required Reading

Before contributing, understand:

1. **Event Sourcing**: [Martin Fowler's article](https://martinfowler.com/eaaDev/EventSourcing.html)
2. **CQRS**: [Microsoft's guide](https://docs.microsoft.com/en-us/azure/architecture/patterns/cqrs)
3. **Temporal.io**: [Core concepts](https://docs.temporal.io/concepts)
4. **Causal Inference**: [DoWhy documentation](https://microsoft.github.io/dowhy/)
5. **Differential Privacy**: [OpenDP primer](https://opendp.org/)

---

## 🎯 Remember

> "We are building the memory and intelligence layer for AI agents. 
> Every interaction we handle could influence important decisions.
> Build with care, test thoroughly, ship with confidence."

---

*Last Updated: December 27, 2025*
*Version: 5.0*
