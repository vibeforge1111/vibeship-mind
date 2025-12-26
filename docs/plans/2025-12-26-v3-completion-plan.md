# V3 Completion Plan: Making the Context Graph Real

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform v3 from 80% dead code into a working context graph with decisions, patterns, autonomy, and real semantic search.

**Architecture:** Wire existing modules into the bridge/hooks, populate the empty tables, add transcript watching, and enable real embeddings.

**Tech Stack:** LanceDB, sentence-transformers (for embeddings), watchdog (for transcript watching), existing v3 modules

---

## Phase 1: Wire the Dead Code (Foundation)

The modules exist but aren't connected. Wire them into the bridge.

### Task 1.1: Wire Working Memory to PromptSubmitHook

**Files:**
- Modify: `src/mind/v3/hooks/prompt_submit.py`
- Modify: `src/mind/v3/bridge.py`

**Step 1: Import WorkingMemory in prompt_submit.py**

Add to imports:
```python
from ..memory.working_memory import WorkingMemory, MemoryItem, MemoryType
```

**Step 2: Initialize WorkingMemory in PromptSubmitHook.__init__**

Add after `self._memories`:
```python
self._working_memory = WorkingMemory()
```

**Step 3: Use WorkingMemory when adding memories**

In `add_to_memory()`, also add to working memory:
```python
# Add to working memory for session tracking
item = MemoryItem(
    id=generate_id("wm"),
    content=content,
    memory_type=MemoryType.DECISION if memory_type == "decision" else MemoryType.LEARNING,
    activation=1.0,
    importance=0.5,
)
self._working_memory.add(item)
```

**Step 4: Run tests**

```bash
uv run pytest tests/v3/test_hooks.py -v
```

**Step 5: Commit**

```bash
git add -A && git commit -m "feat(v3): wire WorkingMemory to PromptSubmitHook"
```

---

### Task 1.2: Wire Decay System

**Files:**
- Modify: `src/mind/v3/hooks/prompt_submit.py`
- Modify: `src/mind/v3/bridge.py`

**Step 1: Import DecayManager**

```python
from ..memory.decay import DecayManager, DecayConfig
```

**Step 2: Initialize in PromptSubmitHook**

```python
self._decay_manager = DecayManager(DecayConfig(half_life_hours=48))
```

**Step 3: Apply decay when retrieving context**

In `_retrieve_relevant()`, apply decay to working memory items:
```python
# Apply decay to working memory before retrieval
decayed_items = self._decay_manager.apply_decay_batch(
    list(self._working_memory._items.values())
)
```

**Step 4: Run tests**

```bash
uv run pytest tests/v3/ -v -k "decay or hook"
```

**Step 5: Commit**

```bash
git add -A && git commit -m "feat(v3): wire DecayManager to retrieval"
```

---

### Task 1.3: Wire Consolidation System

**Files:**
- Modify: `src/mind/v3/hooks/session_end.py`
- Modify: `src/mind/v3/bridge.py`

**Step 1: Import MemoryConsolidator**

In session_end.py:
```python
from ..memory.consolidation import MemoryConsolidator, ConsolidationConfig
```

**Step 2: Initialize in SessionEndHook**

```python
self._consolidator = MemoryConsolidator(ConsolidationConfig(min_occurrences=2))
```

**Step 3: Run consolidation in finalize()**

Add to `finalize()`:
```python
# Consolidate session memories into patterns
if hasattr(self, '_working_memory') and self._working_memory:
    items = list(self._working_memory._items.values())
    patterns = self._consolidator.consolidate(items)

    # Store patterns in graph
    if self._graph_store:
        for pattern in patterns:
            self._graph_store.add_pattern({
                "description": pattern.description,
                "pattern_type": pattern.metadata.get("memory_type", "general"),
                "confidence": pattern.confidence,
                "evidence_count": pattern.occurrences,
            })
```

**Step 4: Pass working memory from PromptSubmitHook to SessionEndHook**

In bridge.py, share working memory between hooks.

**Step 5: Run tests and commit**

```bash
uv run pytest tests/v3/ -v
git add -A && git commit -m "feat(v3): wire consolidation to session end"
```

---

### Task 1.4: Wire Autonomy System

**Files:**
- Modify: `src/mind/v3/bridge.py`
- Create: `src/mind/v3/autonomy/tracker.py`

**Step 1: Create unified autonomy tracker**

```python
# src/mind/v3/autonomy/tracker.py
from .confidence import ConfidenceTracker
from .levels import AutonomyManager, AutonomyConfig
from .feedback import FeedbackProcessor

class AutonomyTracker:
    """Unified autonomy tracking for v3."""

    def __init__(self):
        self.confidence = ConfidenceTracker()
        self.levels = AutonomyManager(confidence_tracker=self.confidence)
        self.feedback = FeedbackProcessor(confidence_tracker=self.confidence)

    def record_decision(self, action_type: str, success: bool):
        """Record a decision outcome."""
        self.confidence.record_outcome(action_type, success)

    def get_autonomy_level(self, action_type: str):
        """Get current autonomy level for an action."""
        return self.levels.get_level(action_type)
```

**Step 2: Initialize in V3Bridge**

```python
from .autonomy.tracker import AutonomyTracker

# In __init__:
self._autonomy = AutonomyTracker()
```

**Step 3: Expose autonomy in get_stats()**

```python
if self._autonomy:
    stats["autonomy"] = self._autonomy.levels.get_summary()
```

**Step 4: Run tests and commit**

```bash
uv run pytest tests/v3/ -v
git add -A && git commit -m "feat(v3): wire autonomy system to bridge"
```

---

## Phase 2: Populate Empty Tables

The decisions, entities, patterns tables are empty. Wire extraction to populate them.

### Task 2.1: Extract Decisions from mind_log

**Files:**
- Modify: `src/mind/v3/hooks/prompt_submit.py`

**Step 1: Import decision extractor**

```python
from ..intelligence.extractors.decision import DecisionExtractor
```

**Step 2: Initialize extractor**

```python
self._decision_extractor = DecisionExtractor()
```

**Step 3: Extract and store decisions**

In `add_to_memory()`, when type is "decision":
```python
if memory_type == "decision" and self._graph_store:
    # Extract structured decision
    extraction = self._decision_extractor.extract(content)
    if extraction.decisions:
        for dec in extraction.decisions:
            self._graph_store.add_decision({
                "action": dec.action,
                "reasoning": dec.reasoning,
                "alternatives": dec.alternatives,
                "confidence": dec.confidence,
            })
```

**Step 4: Run tests and commit**

```bash
uv run pytest tests/v3/ -v
git add -A && git commit -m "feat(v3): extract decisions to decisions table"
```

---

### Task 2.2: Extract Entities

**Files:**
- Modify: `src/mind/v3/hooks/prompt_submit.py`

**Step 1: Import entity extractor**

```python
from ..intelligence.extractors.entity import EntityExtractor
```

**Step 2: Extract entities from all memories**

In `add_to_memory()`:
```python
# Extract entities
entity_extraction = self._entity_extractor.extract(content)
if entity_extraction.entities and self._graph_store:
    for ent in entity_extraction.entities:
        self._graph_store.add_entity({
            "name": ent.name,
            "type": ent.entity_type,
            "description": ent.context or "",
        })
```

**Step 3: Run tests and commit**

```bash
uv run pytest tests/v3/ -v
git add -A && git commit -m "feat(v3): extract entities to entities table"
```

---

### Task 2.3: Extract Patterns via Consolidation

Already wired in Task 1.3. Verify patterns are being created:

**Step 1: Write a test**

```python
# tests/v3/test_pattern_extraction.py
def test_consolidation_creates_patterns():
    """Test that consolidation creates patterns in graph."""
    # Add multiple similar memories
    hook.add_to_memory("Using SQLite for storage", "decision")
    hook.add_to_memory("Chose SQLite over PostgreSQL", "decision")
    hook.add_to_memory("SQLite is the right choice here", "decision")

    # Trigger consolidation
    result = session_hook.finalize()

    # Check patterns table
    patterns = graph_store.search_patterns("SQLite")
    assert len(patterns) > 0
```

**Step 2: Run and verify**

```bash
uv run pytest tests/v3/test_pattern_extraction.py -v
```

---

## Phase 3: Real Embeddings

Replace hash-based pseudo-embeddings with real semantic embeddings.

### Task 3.1: Add sentence-transformers dependency

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add dependency**

```toml
[project.optional-dependencies]
embeddings = ["sentence-transformers>=2.2.0"]
```

**Step 2: Install**

```bash
uv add sentence-transformers --optional embeddings
```

---

### Task 3.2: Implement Real Embedding Service

**Files:**
- Modify: `src/mind/v3/retrieval/embeddings.py`

**Step 1: Add SentenceTransformer embedding**

```python
class SentenceTransformerEmbedding:
    """Real semantic embeddings using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return [e.tolist() for e in embeddings]
```

**Step 2: Update EmbeddingService to prefer real embeddings**

```python
def _init_embedding(self) -> None:
    try:
        self._embedding = SentenceTransformerEmbedding()
        self._available = True
    except ImportError:
        if self.config.fallback_to_hash:
            self._fallback = HashEmbedding(dimension=self.config.dimension)
```

---

### Task 3.3: Update GraphStore to use EmbeddingService

**Files:**
- Modify: `src/mind/v3/graph/store.py`

**Step 1: Use EmbeddingService instead of hash function**

Replace `get_embedding()` with:
```python
from ..retrieval.embeddings import EmbeddingService

# Module-level service (lazy init)
_embedding_service = None

def get_embedding(text: str) -> list[float]:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service.embed(text)
```

**Step 2: Run tests**

```bash
uv run pytest tests/v3/ -v
```

---

## Phase 4: Transcript Watcher

Build the missing transcript watcher for passive capture.

### Task 4.1: Create Transcript Watcher

**Files:**
- Create: `src/mind/v3/capture/watcher.py`

**Step 1: Add watchdog dependency**

```bash
uv add watchdog
```

**Step 2: Implement watcher**

```python
# src/mind/v3/capture/watcher.py
"""
Real-time transcript watcher for Mind v3.

Watches Claude Code transcript files and extracts events.
"""
from __future__ import annotations

import json
import base64
from pathlib import Path
from typing import Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from .events import Event, EventType
from .extractor import TranscriptExtractor


class TranscriptHandler(FileSystemEventHandler):
    """Handler for transcript file changes."""

    def __init__(
        self,
        on_event: Callable[[Event], None],
        extractor: TranscriptExtractor,
    ):
        self.on_event = on_event
        self.extractor = extractor
        self._file_positions: dict[str, int] = {}

    def on_modified(self, event: FileModifiedEvent) -> None:
        if not event.src_path.endswith('.jsonl'):
            return

        path = Path(event.src_path)
        last_pos = self._file_positions.get(str(path), 0)

        with open(path, 'r', encoding='utf-8') as f:
            f.seek(last_pos)
            new_content = f.read()
            self._file_positions[str(path)] = f.tell()

        # Process new lines
        for line in new_content.strip().split('\n'):
            if not line:
                continue
            try:
                entry = json.loads(line)
                events = self.extractor.extract_from_entry(entry)
                for evt in events:
                    self.on_event(evt)
            except Exception:
                pass


class TranscriptWatcher:
    """Watches Claude Code transcripts for events."""

    def __init__(
        self,
        transcript_dir: Path,
        on_event: Callable[[Event], None],
    ):
        self.transcript_dir = transcript_dir
        self.on_event = on_event
        self.extractor = TranscriptExtractor()
        self._observer = None

    def start(self) -> None:
        """Start watching transcripts."""
        handler = TranscriptHandler(self.on_event, self.extractor)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.transcript_dir), recursive=True)
        self._observer.start()

    def stop(self) -> None:
        """Stop watching."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
```

**Step 3: Write tests**

```python
# tests/v3/test_watcher.py
def test_watcher_detects_new_content(tmp_path):
    """Test that watcher detects new transcript content."""
    events = []
    watcher = TranscriptWatcher(tmp_path, events.append)
    watcher.start()

    # Write a transcript entry
    transcript = tmp_path / "test.jsonl"
    transcript.write_text('{"type": "user", "message": "test"}\n')

    time.sleep(0.5)
    watcher.stop()

    # Should have extracted events
    assert len(events) > 0
```

**Step 4: Commit**

```bash
git add -A && git commit -m "feat(v3): add transcript watcher for passive capture"
```

---

## Phase 5: Query Expansion

Add query expansion for better retrieval.

### Task 5.1: Implement Query Expander

**Files:**
- Create: `src/mind/v3/retrieval/query_expansion.py`

**Step 1: Create expander**

```python
# src/mind/v3/retrieval/query_expansion.py
"""
Query expansion for better retrieval.

Expands queries with related terms for broader matching.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


# Domain-specific expansions
EXPANSIONS = {
    "auth": ["authentication", "login", "session", "token", "jwt", "oauth"],
    "db": ["database", "sql", "query", "postgres", "sqlite", "mysql"],
    "api": ["endpoint", "rest", "http", "request", "response"],
    "bug": ["error", "issue", "fix", "problem", "broken"],
    "test": ["testing", "unittest", "pytest", "spec", "assertion"],
    "deploy": ["deployment", "release", "production", "ci", "cd"],
}


@dataclass
class ExpandedQuery:
    """Query with expanded terms."""
    original: str
    expanded_terms: list[str]
    full_query: str


class QueryExpander:
    """Expands queries with related terms."""

    def __init__(self, custom_expansions: dict[str, list[str]] | None = None):
        self.expansions = {**EXPANSIONS}
        if custom_expansions:
            self.expansions.update(custom_expansions)

    def expand(self, query: str) -> ExpandedQuery:
        """Expand a query with related terms."""
        words = re.findall(r'\b\w+\b', query.lower())
        expanded = set(words)

        for word in words:
            if word in self.expansions:
                expanded.update(self.expansions[word])

        expanded_terms = list(expanded - set(words))
        full_query = query + " " + " ".join(expanded_terms)

        return ExpandedQuery(
            original=query,
            expanded_terms=expanded_terms,
            full_query=full_query.strip(),
        )
```

**Step 2: Use in PromptSubmitHook**

In `_retrieve_relevant()`:
```python
from ..retrieval.query_expansion import QueryExpander

# Expand query
expander = QueryExpander()
expanded = expander.expand(prompt)

# Search with expanded query
results = self._graph_store.search_memories(expanded.full_query, limit=limit)
```

**Step 3: Commit**

```bash
git add -A && git commit -m "feat(v3): add query expansion for better retrieval"
```

---

## Phase 6: Configuration System

Add user-configurable intelligence presets.

### Task 6.1: Create Config Schema

**Files:**
- Create: `src/mind/v3/config.py`

```python
# src/mind/v3/config.py
"""
V3 configuration system.

Supports intelligence presets and per-feature settings.
"""
from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


class IntelligenceLevel(str, Enum):
    LOCAL = "local"      # Free, regex only
    LOW = "low"          # Basic NLP
    MEDIUM = "medium"    # AI batched (Haiku)
    HIGH = "high"        # AI frequent (Sonnet)
    ULTRA = "ultra"      # Real-time AI (Opus)


@dataclass
class IntelligenceSettings:
    capture: IntelligenceLevel = IntelligenceLevel.MEDIUM
    decisions: IntelligenceLevel = IntelligenceLevel.MEDIUM
    patterns: IntelligenceLevel = IntelligenceLevel.LOW
    retrieval: IntelligenceLevel = IntelligenceLevel.MEDIUM
    synthesis: IntelligenceLevel = IntelligenceLevel.LOCAL
    decay: IntelligenceLevel = IntelligenceLevel.LOW


PRESETS = {
    "free": IntelligenceSettings(
        capture=IntelligenceLevel.LOCAL,
        decisions=IntelligenceLevel.LOCAL,
        patterns=IntelligenceLevel.LOCAL,
        retrieval=IntelligenceLevel.LOCAL,
        synthesis=IntelligenceLevel.LOCAL,
        decay=IntelligenceLevel.LOCAL,
    ),
    "lite": IntelligenceSettings(
        capture=IntelligenceLevel.MEDIUM,
        decisions=IntelligenceLevel.LOW,
        patterns=IntelligenceLevel.LOW,
        retrieval=IntelligenceLevel.MEDIUM,
        synthesis=IntelligenceLevel.LOCAL,
        decay=IntelligenceLevel.LOW,
    ),
    "balanced": IntelligenceSettings(
        capture=IntelligenceLevel.MEDIUM,
        decisions=IntelligenceLevel.MEDIUM,
        patterns=IntelligenceLevel.MEDIUM,
        retrieval=IntelligenceLevel.MEDIUM,
        synthesis=IntelligenceLevel.LOW,
        decay=IntelligenceLevel.MEDIUM,
    ),
    "pro": IntelligenceSettings(
        capture=IntelligenceLevel.HIGH,
        decisions=IntelligenceLevel.HIGH,
        patterns=IntelligenceLevel.HIGH,
        retrieval=IntelligenceLevel.HIGH,
        synthesis=IntelligenceLevel.MEDIUM,
        decay=IntelligenceLevel.HIGH,
    ),
}


@dataclass
class V3Config:
    """Full v3 configuration."""

    enabled: bool = True
    preset: str = "balanced"
    intelligence: IntelligenceSettings = field(default_factory=IntelligenceSettings)

    @classmethod
    def load(cls, project_path: Path) -> "V3Config":
        """Load config from .mind/config.yaml"""
        config_path = project_path / ".mind" / "config.yaml"

        if not config_path.exists():
            return cls()

        with open(config_path, 'r') as f:
            data = yaml.safe_load(f) or {}

        preset = data.get("preset", "balanced")
        if preset in PRESETS:
            intelligence = PRESETS[preset]
        else:
            intelligence = IntelligenceSettings()

        return cls(
            enabled=data.get("enabled", True),
            preset=preset,
            intelligence=intelligence,
        )

    def save(self, project_path: Path) -> None:
        """Save config to .mind/config.yaml"""
        config_path = project_path / ".mind" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "enabled": self.enabled,
            "preset": self.preset,
        }

        with open(config_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
```

**Step 2: Use config in bridge**

```python
from .config import V3Config

# In V3Bridge.__init__:
self.config = V3Config.load(project_path)
```

**Step 3: Commit**

```bash
git add -A && git commit -m "feat(v3): add configuration system with presets"
```

---

## Verification Checklist

After each phase:

- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] LanceDB tables have data: decisions > 0, patterns > 0
- [ ] Context injection works with real memories
- [ ] No regressions in existing functionality

---

## Summary

| Phase | What It Does | Impact |
|-------|--------------|--------|
| 1 | Wire dead code | Enables memory lifecycle |
| 2 | Populate tables | Real decisions/entities/patterns |
| 3 | Real embeddings | Semantic search works |
| 4 | Transcript watcher | Passive capture |
| 5 | Query expansion | Better retrieval |
| 6 | Config system | User control |

**Total tasks:** 15 across 6 phases

---

## Phase 7: Missing Graph Tables (Architecture Alignment)

The design document specifies 8 node types, but only 4 tables exist. Add the missing tables.

### Task 7.1: Add Policy Table

**Files:**
- Modify: `src/mind/v3/graph/store.py`
- Modify: `src/mind/v3/graph/schema.py`

**Step 1: Add Policy schema**

In `schema.py`:
```python
@dataclass
class PolicyNode:
    """A policy or rule that governs decisions."""
    id: str
    rule: str
    scope: str  # "file", "directory", "project", "global"
    source: str  # Where this policy came from
    created_at: datetime = field(default_factory=datetime.now)
    active: bool = True
    vector: list[float] = field(default_factory=list)
```

**Step 2: Add policies table to GraphStore**

In `store.py`, add table creation:
```python
POLICIES_SCHEMA = pa.schema([
    pa.field("id", pa.string()),
    pa.field("rule", pa.string()),
    pa.field("scope", pa.string()),
    pa.field("source", pa.string()),
    pa.field("created_at", pa.string()),
    pa.field("active", pa.bool_()),
    pa.field("vector", pa.list_(pa.float32(), VECTOR_DIM)),
])

def _init_policies_table(self):
    if "policies" not in self.db.table_names():
        self.db.create_table("policies", schema=POLICIES_SCHEMA)
```

**Step 3: Add CRUD methods**

```python
def add_policy(self, policy: dict[str, Any]) -> str:
    """Add a policy to the graph."""
    policy_id = generate_id("pol")
    vector = get_embedding(policy["rule"])

    table = self.db.open_table("policies")
    table.add([{
        "id": policy_id,
        "rule": policy["rule"],
        "scope": policy.get("scope", "project"),
        "source": policy.get("source", "inferred"),
        "created_at": datetime.now().isoformat(),
        "active": policy.get("active", True),
        "vector": vector,
    }])
    return policy_id

def search_policies(self, query: str, limit: int = 5) -> list[dict]:
    """Search policies by semantic similarity."""
    vector = get_embedding(query)
    table = self.db.open_table("policies")
    results = table.search(vector).limit(limit).to_list()
    return results
```

**Step 4: Run tests and commit**

```bash
uv run pytest tests/v3/graph/ -v
git add -A && git commit -m "feat(v3): add policies table to graph store"
```

---

### Task 7.2: Add Exceptions Table

**Files:**
- Modify: `src/mind/v3/graph/store.py`
- Modify: `src/mind/v3/graph/schema.py`

**Step 1: Add Exception schema**

```python
@dataclass
class ExceptionNode:
    """An exception or override to a policy."""
    id: str
    policy_id: str  # Reference to overridden policy
    condition: str  # When this exception applies
    reason: str
    created_at: datetime = field(default_factory=datetime.now)
    vector: list[float] = field(default_factory=list)
```

**Step 2: Add exceptions table and methods**

Similar pattern to policies table.

**Step 3: Commit**

```bash
git add -A && git commit -m "feat(v3): add exceptions table to graph store"
```

---

### Task 7.3: Add Precedents Table

**Files:**
- Modify: `src/mind/v3/graph/store.py`
- Modify: `src/mind/v3/graph/schema.py`

**Step 1: Add Precedent schema**

```python
@dataclass
class PrecedentNode:
    """A historical decision that sets precedent."""
    id: str
    decision_id: str  # Reference to the decision
    context: str  # Context in which this applies
    outcome: str  # What happened as a result
    weight: float  # How much weight to give this precedent
    created_at: datetime = field(default_factory=datetime.now)
    vector: list[float] = field(default_factory=list)
```

**Step 2: Add table and methods**

**Step 3: Commit**

```bash
git add -A && git commit -m "feat(v3): add precedents table to graph store"
```

---

### Task 7.4: Add Outcomes Table

**Files:**
- Modify: `src/mind/v3/graph/store.py`
- Modify: `src/mind/v3/graph/schema.py`

**Step 1: Add Outcome schema**

```python
@dataclass
class OutcomeNode:
    """The outcome of a decision."""
    id: str
    decision_id: str
    success: bool
    feedback: str  # User feedback or observed result
    impact: str  # "positive", "negative", "neutral"
    created_at: datetime = field(default_factory=datetime.now)
    vector: list[float] = field(default_factory=list)
```

**Step 2: Add table and methods**

**Step 3: Commit**

```bash
git add -A && git commit -m "feat(v3): add outcomes table to graph store"
```

---

### Task 7.5: Add Autonomy Table

**Files:**
- Modify: `src/mind/v3/graph/store.py`
- Modify: `src/mind/v3/graph/schema.py`

**Step 1: Add Autonomy schema**

```python
@dataclass
class AutonomyNode:
    """Autonomy level for a specific action type."""
    id: str
    action_type: str  # "file_edit", "commit", "refactor", etc.
    level: str  # "ask", "suggest", "auto"
    confidence: float
    sample_count: int
    last_updated: datetime = field(default_factory=datetime.now)
```

**Step 2: Wire to AutonomyTracker**

Make AutonomyTracker persist to this table.

**Step 3: Commit**

```bash
git add -A && git commit -m "feat(v3): add autonomy table and wire to tracker"
```

---

## Phase 8: Intelligence Levels (Model Cascade)

Implement the intelligence level system that routes to different models.

### Task 8.1: Create Intelligence Router

**Files:**
- Create: `src/mind/v3/intelligence/router.py`

**Step 1: Create router that selects model based on level**

```python
# src/mind/v3/intelligence/router.py
"""Routes requests to appropriate intelligence level."""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from typing import Callable, Any

class IntelligenceLevel(str, Enum):
    LOCAL = "local"    # Regex/rule-based only
    LOW = "low"        # Basic NLP (spaCy, etc.)
    MEDIUM = "medium"  # AI batched (Haiku)
    HIGH = "high"      # AI frequent (Sonnet)
    ULTRA = "ultra"    # Real-time (Opus)


@dataclass
class IntelligenceRouter:
    """Routes intelligence requests to appropriate handlers."""

    level: IntelligenceLevel = IntelligenceLevel.MEDIUM

    # Handler registrations
    _local_handlers: dict[str, Callable] = None
    _low_handlers: dict[str, Callable] = None
    _medium_handlers: dict[str, Callable] = None
    _high_handlers: dict[str, Callable] = None
    _ultra_handlers: dict[str, Callable] = None

    def route(self, task: str, *args, **kwargs) -> Any:
        """Route a task to the appropriate handler based on level."""
        handlers = self._get_handlers_for_level()
        if task in handlers:
            return handlers[task](*args, **kwargs)
        # Fallback to lower levels
        return self._fallback(task, *args, **kwargs)

    def _get_handlers_for_level(self) -> dict:
        """Get handlers for current level."""
        level_map = {
            IntelligenceLevel.LOCAL: self._local_handlers or {},
            IntelligenceLevel.LOW: self._low_handlers or {},
            IntelligenceLevel.MEDIUM: self._medium_handlers or {},
            IntelligenceLevel.HIGH: self._high_handlers or {},
            IntelligenceLevel.ULTRA: self._ultra_handlers or {},
        }
        return level_map.get(self.level, {})
```

**Step 2: Create LOCAL handlers (regex-based)**

```python
# src/mind/v3/intelligence/local.py
"""Local intelligence handlers - no external dependencies."""

import re
from typing import Any

def extract_decisions_local(text: str) -> list[dict]:
    """Extract decisions using regex patterns."""
    patterns = [
        r"(?:decided|chose|going with|using)\s+(.+?)(?:\s+because|\s+since|\.|\n)",
        r"(?:decision|choice):\s*(.+?)(?:\.|\n)",
    ]
    decisions = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            decisions.append({
                "action": match.group(1).strip(),
                "confidence": 0.6,  # Lower confidence for regex
                "source": "local",
            })
    return decisions
```

**Step 3: Commit**

```bash
git add -A && git commit -m "feat(v3): add intelligence router with level-based dispatch"
```

---

### Task 8.2: Wire Intelligence Levels to Extractors

**Files:**
- Modify: `src/mind/v3/intelligence/extractors/decision.py`
- Modify: `src/mind/v3/intelligence/extractors/entity.py`

**Step 1: Add level awareness to extractors**

Make extractors use router to select extraction method.

**Step 2: Commit**

```bash
git add -A && git commit -m "feat(v3): wire intelligence levels to extractors"
```

---

## Phase 9: Wire Query Expansion to Retrieval

Connect the QueryExpander to the PromptSubmitHook.

### Task 9.1: Integrate Query Expansion

**Files:**
- Modify: `src/mind/v3/hooks/prompt_submit.py`

**Step 1: Import and use QueryExpander**

```python
from ..retrieval.query_expander import QueryExpander

# In __init__:
self._query_expander = QueryExpander()

# In _retrieve_relevant():
def _retrieve_relevant(self, prompt: str, limit: int = 5) -> list[dict]:
    """Retrieve relevant context using expanded query."""
    # Expand the query
    expanded = self._query_expander.expand(prompt)

    # Search with both original and expanded terms
    all_results = []

    # Search with original
    if self._graph_store:
        results = self._graph_store.search_memories(prompt, limit=limit)
        all_results.extend(results)

        # Search with expanded query for broader matches
        for sub_query in expanded.sub_queries[:2]:
            results = self._graph_store.search_memories(sub_query, limit=2)
            all_results.extend(results)

        # Search for specific entities
        for entity in expanded.entities:
            results = self._graph_store.search_entities(entity, limit=2)
            all_results.extend(results)

    # Deduplicate and rank
    return self._dedupe_and_rank(all_results, limit)
```

**Step 2: Run tests and commit**

```bash
uv run pytest tests/v3/hooks/ -v
git add -A && git commit -m "feat(v3): wire query expansion to prompt submit hook"
```

---

## Phase 10: Cross-Encoder Reranking

Add reranking for better result quality.

### Task 10.1: Implement Cross-Encoder Reranker

**Files:**
- Modify: `src/mind/v3/retrieval/reranker.py`

**Step 1: Add cross-encoder implementation**

The file exists with SimpleReranker. Add actual cross-encoder:

```python
class CrossEncoderReranker(Reranker):
    """Cross-encoder based reranking using sentence-transformers."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(model_name)
            self._available = True
        except ImportError:
            self._available = False

    def rerank(self, query: str, results: list[SearchResult], top_k: int = 5) -> list[SearchResult]:
        if not self._available or not results:
            return results[:top_k]

        # Create pairs for scoring
        pairs = [(query, r.content) for r in results]

        # Get cross-encoder scores
        scores = self.model.predict(pairs)

        # Attach scores and sort
        for result, score in zip(results, scores):
            result.cross_encoder_score = float(score)

        return sorted(results, key=lambda r: r.cross_encoder_score, reverse=True)[:top_k]
```

**Step 2: Wire to retrieval pipeline**

**Step 3: Commit**

```bash
git add -A && git commit -m "feat(v3): add cross-encoder reranking"
```

---

## Phase 11: Human-Readable Views

Generate markdown files from graph data.

### Task 11.1: Create View Generator

**Files:**
- Create: `src/mind/v3/views/generator.py`
- Create: `src/mind/v3/views/__init__.py`

**Step 1: Create view generator**

```python
# src/mind/v3/views/generator.py
"""Generate human-readable markdown views from graph data."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..graph.store import GraphStore


class ViewGenerator:
    """Generates markdown views from graph store."""

    def __init__(self, graph_store: "GraphStore", output_dir: Path):
        self.graph = graph_store
        self.output_dir = output_dir

    def generate_decisions_view(self) -> Path:
        """Generate DECISIONS.md with all decisions."""
        decisions = self.graph.get_all_decisions()

        lines = [
            "# Decisions",
            "",
            f"*Generated: {datetime.now().isoformat()}*",
            "",
        ]

        for dec in decisions:
            lines.extend([
                f"## {dec.get('action', 'Unknown')}",
                "",
                f"**Reasoning:** {dec.get('reasoning', 'N/A')}",
                "",
                f"**Confidence:** {dec.get('confidence', 0):.0%}",
                "",
                "---",
                "",
            ])

        path = self.output_dir / "DECISIONS.md"
        path.write_text("\n".join(lines))
        return path

    def generate_patterns_view(self) -> Path:
        """Generate PATTERNS.md with all patterns."""
        patterns = self.graph.get_all_patterns()

        lines = [
            "# Patterns",
            "",
            f"*Generated: {datetime.now().isoformat()}*",
            "",
        ]

        for pat in patterns:
            lines.extend([
                f"## {pat.get('description', 'Unknown')}",
                "",
                f"**Type:** {pat.get('pattern_type', 'general')}",
                f"**Confidence:** {pat.get('confidence', 0):.0%}",
                f"**Evidence:** {pat.get('evidence_count', 0)} occurrences",
                "",
                "---",
                "",
            ])

        path = self.output_dir / "PATTERNS.md"
        path.write_text("\n".join(lines))
        return path

    def generate_policies_view(self) -> Path:
        """Generate POLICIES.md with all policies."""
        policies = self.graph.search_policies("", limit=100)

        lines = [
            "# Policies",
            "",
            f"*Generated: {datetime.now().isoformat()}*",
            "",
        ]

        for pol in policies:
            status = "Active" if pol.get("active", True) else "Inactive"
            lines.extend([
                f"## {pol.get('rule', 'Unknown')}",
                "",
                f"**Scope:** {pol.get('scope', 'project')}",
                f"**Source:** {pol.get('source', 'inferred')}",
                f"**Status:** {status}",
                "",
                "---",
                "",
            ])

        path = self.output_dir / "POLICIES.md"
        path.write_text("\n".join(lines))
        return path

    def generate_all(self) -> list[Path]:
        """Generate all views."""
        return [
            self.generate_decisions_view(),
            self.generate_patterns_view(),
            self.generate_policies_view(),
        ]
```

**Step 2: Add CLI command for view generation**

```python
# In cli.py
@cli.command()
def generate_views():
    """Generate human-readable markdown views from graph."""
    from .v3.views import ViewGenerator
    from .v3.graph import GraphStore

    store = GraphStore(get_project_path())
    generator = ViewGenerator(store, get_project_path() / ".mind")
    paths = generator.generate_all()

    for path in paths:
        click.echo(f"Generated: {path}")
```

**Step 3: Commit**

```bash
git add -A && git commit -m "feat(v3): add human-readable view generation"
```

---

## Updated Summary

| Phase | What It Does | Status |
|-------|--------------|--------|
| 1 | Wire dead code | ✅ Complete |
| 2 | Populate tables | ✅ Complete |
| 3 | Real embeddings | ✅ Complete |
| 4 | Transcript watcher | ✅ Complete |
| 5 | Query expansion | ✅ Complete |
| 6 | Config system | ✅ Complete |
| 7 | Missing graph tables | ✅ Complete |
| 8 | Intelligence levels | ✅ Complete |
| 9 | Wire query expansion | ✅ Complete |
| 10 | Cross-encoder reranking | ✅ Complete |
| 11 | Human-readable views | ✅ Complete |

**Completed tasks:** 25 across 11 phases
**Remaining tasks:** 0

---

*Document created: 2025-12-26*
*Updated: 2025-12-26 - Added phases 7-11 for architecture alignment*
