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

*Document created: 2025-12-26*
