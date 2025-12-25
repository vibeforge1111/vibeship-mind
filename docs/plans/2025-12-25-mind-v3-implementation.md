# Mind v3 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform Mind from passive memory into an intelligent context graph - a system of record for AI decisions.

**Architecture:** Modular, event-sourced architecture with clear separation of concerns. Each component is independently testable and replaceable. LanceDB for storage, model cascade for intelligence, hooks for capture/injection.

**Tech Stack:** Python 3.11+, LanceDB, watchdog, Claude/OpenAI APIs, pytest, pydantic

---

## Architecture Overview

```
src/mind/
├── __init__.py
├── __main__.py
├── cli.py                    # CLI commands (KEEP)
├── config.py                 # Configuration (EXTEND)
├── mascot.py                 # Mindful mascot (KEEP)
│
├── v3/                       # NEW: Mind v3 modules
│   ├── __init__.py
│   │
│   ├── capture/              # Layer 1: Event Capture
│   │   ├── __init__.py
│   │   ├── watcher.py        # Transcript file watcher
│   │   ├── extractor.py      # Event extraction from transcripts
│   │   └── events.py         # Event types and schemas
│   │
│   ├── intelligence/         # Layer 2: AI Processing
│   │   ├── __init__.py
│   │   ├── cascade.py        # Model cascade router
│   │   ├── extractors/       # Specialized extractors
│   │   │   ├── __init__.py
│   │   │   ├── decision.py   # Decision trace extraction
│   │   │   ├── entity.py     # Entity extraction
│   │   │   └── pattern.py    # Pattern detection
│   │   └── synthesis.py      # Deep synthesis
│   │
│   ├── graph/                # Layer 3: Context Graph
│   │   ├── __init__.py
│   │   ├── store.py          # LanceDB wrapper
│   │   ├── nodes/            # Node type implementations
│   │   │   ├── __init__.py
│   │   │   ├── decision.py
│   │   │   ├── entity.py
│   │   │   ├── pattern.py
│   │   │   ├── policy.py
│   │   │   ├── exception.py
│   │   │   ├── precedent.py
│   │   │   └── outcome.py
│   │   └── queries.py        # Graph query helpers
│   │
│   ├── retrieval/            # Layer 4: Context Retrieval
│   │   ├── __init__.py
│   │   ├── search.py         # Hybrid search
│   │   ├── rerank.py         # Reranking
│   │   └── inject.py         # Context injection
│   │
│   ├── memory/               # Cognitive Memory System
│   │   ├── __init__.py
│   │   ├── working.py        # Working memory
│   │   ├── consolidation.py  # Episode → Semantic
│   │   ├── decay.py          # Memory decay
│   │   └── reinforcement.py  # Pattern reinforcement
│   │
│   ├── autonomy/             # Progressive Autonomy
│   │   ├── __init__.py
│   │   ├── confidence.py     # Confidence tracking
│   │   ├── levels.py         # Autonomy level management
│   │   └── feedback.py       # Feedback loop
│   │
│   └── hooks/                # Claude Code Hooks
│       ├── __init__.py
│       ├── prompt_submit.py  # UserPromptSubmit hook
│       └── session_end.py    # Backup capture
│
├── mcp/                      # MCP Server (REFACTOR)
│   ├── __init__.py
│   ├── server.py             # Main server (slim)
│   ├── handlers/             # Tool handlers (extracted)
│   │   ├── __init__.py
│   │   ├── recall.py
│   │   ├── log.py
│   │   ├── search.py
│   │   ├── session.py
│   │   └── remind.py
│   └── tools.py              # Tool definitions
│
└── legacy/                   # ARCHIVED: Old implementations
    ├── __init__.py
    ├── parser.py             # Old regex parser
    ├── context.py            # Old context generator
    └── similarity.py         # Old embedding similarity
```

---

## Phase 0: Preparation

### Task 0.1: Create Archive Structure

**Files:**
- Create: `src/mind/legacy/__init__.py`
- Move: `src/mind/parser.py` → `src/mind/legacy/parser.py`
- Move: `src/mind/context.py` → `src/mind/legacy/context.py`
- Move: `src/mind/similarity.py` → `src/mind/legacy/similarity.py`

**Step 1: Create legacy directory**

```bash
mkdir -p src/mind/legacy
```

**Step 2: Create legacy __init__.py**

```python
"""
Legacy Mind modules (v1/v2).

These modules are archived for reference but replaced by v3 implementations.
Import from here only for migration purposes.
"""

from .parser import Parser
from .context import ContextGenerator
from .similarity import compute_similarity, retrieve_relevant_memories

__all__ = [
    "Parser",
    "ContextGenerator",
    "compute_similarity",
    "retrieve_relevant_memories",
]
```

**Step 3: Move files with git**

```bash
git mv src/mind/parser.py src/mind/legacy/parser.py
git mv src/mind/context.py src/mind/legacy/context.py
git mv src/mind/similarity.py src/mind/legacy/similarity.py
```

**Step 4: Update imports in server.py**

Find and replace:
- `from .parser import` → `from .legacy.parser import`
- `from .context import` → `from .legacy.context import`
- `from .similarity import` → `from .legacy.similarity import`

**Step 5: Run tests to verify nothing broke**

```bash
uv run pytest tests/ -v
```

**Step 6: Commit**

```bash
git add -A
git commit -m "refactor: archive legacy parser, context, similarity modules

Preparation for Mind v3 context graph architecture.
Old implementations preserved in src/mind/legacy/ for reference."
```

---

### Task 0.2: Create v3 Module Structure

**Files:**
- Create: `src/mind/v3/__init__.py`
- Create: `src/mind/v3/capture/__init__.py`
- Create: `src/mind/v3/intelligence/__init__.py`
- Create: `src/mind/v3/graph/__init__.py`
- Create: `src/mind/v3/retrieval/__init__.py`
- Create: `src/mind/v3/memory/__init__.py`
- Create: `src/mind/v3/autonomy/__init__.py`
- Create: `src/mind/v3/hooks/__init__.py`

**Step 1: Create directory structure**

```bash
mkdir -p src/mind/v3/{capture,intelligence,intelligence/extractors,graph,graph/nodes,retrieval,memory,autonomy,hooks}
```

**Step 2: Create v3 __init__.py**

```python
"""
Mind v3: Context Graph Architecture

A system of record for AI decisions - capturing not just what happened,
but why it was allowed to happen.

Modules:
- capture: Event capture from Claude Code transcripts
- intelligence: AI-powered analysis and extraction
- graph: Context graph storage (LanceDB)
- retrieval: Hybrid search and context injection
- memory: Cognitive memory system
- autonomy: Progressive autonomy tracking
- hooks: Claude Code integration hooks
"""

__version__ = "3.0.0-alpha"
```

**Step 3: Create empty __init__.py files**

```python
# For each submodule:
"""Mind v3 [module_name] module."""
```

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: scaffold Mind v3 module structure

Creates modular architecture for context graph implementation:
- capture/: Event sourcing from transcripts
- intelligence/: Model cascade and extractors
- graph/: LanceDB context graph
- retrieval/: Hybrid search + reranking
- memory/: Cognitive memory system
- autonomy/: Progressive autonomy
- hooks/: Claude Code integration"
```

---

### Task 0.3: Add Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add new dependencies**

Add to `[project.dependencies]`:

```toml
dependencies = [
    # Existing...

    # v3 additions
    "lancedb>=0.4.0",
    "watchdog>=4.0.0",
    "pydantic>=2.5.0",
]

[project.optional-dependencies]
embeddings = [
    "sentence-transformers>=2.2.0",
    "numpy>=1.24.0",
]
api = [
    "anthropic>=0.18.0",
    "openai>=1.12.0",
]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
]
```

**Step 2: Install dependencies**

```bash
uv sync
```

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add Mind v3 dependencies

- lancedb: Vector database for context graph
- watchdog: File system monitoring for transcript capture
- pydantic: Data validation for graph schemas
- Optional: sentence-transformers, anthropic, openai"
```

---

## Phase 1: Event Sourcing Foundation

### Task 1.1: Event Schema

**Files:**
- Create: `src/mind/v3/capture/events.py`
- Create: `tests/v3/capture/test_events.py`

**Step 1: Write the failing test**

```python
# tests/v3/capture/test_events.py
"""Tests for event schema and validation."""
import pytest
from datetime import datetime
from mind.v3.capture.events import (
    Event,
    EventType,
    ToolCallEvent,
    ToolResultEvent,
    UserMessageEvent,
    AssistantMessageEvent,
    DecisionEvent,
)


class TestEventType:
    """Test EventType enum."""

    def test_event_types_exist(self):
        """All required event types should exist."""
        assert EventType.TOOL_CALL
        assert EventType.TOOL_RESULT
        assert EventType.USER_MESSAGE
        assert EventType.ASSISTANT_MESSAGE
        assert EventType.DECISION


class TestEvent:
    """Test base Event class."""

    def test_create_event(self):
        """Should create event with auto-generated id and timestamp."""
        event = Event(type=EventType.USER_MESSAGE, data={"content": "hello"})

        assert event.id is not None
        assert event.id.startswith("evt_")
        assert event.timestamp is not None
        assert event.type == EventType.USER_MESSAGE
        assert event.data == {"content": "hello"}

    def test_event_to_dict(self):
        """Should serialize to dictionary."""
        event = Event(type=EventType.USER_MESSAGE, data={"content": "hello"})
        d = event.to_dict()

        assert "id" in d
        assert "timestamp" in d
        assert d["type"] == "user_message"
        assert d["data"] == {"content": "hello"}


class TestToolCallEvent:
    """Test ToolCallEvent schema."""

    def test_create_tool_call_event(self):
        """Should create tool call event with required fields."""
        event = ToolCallEvent(
            tool_name="Read",
            tool_input={"file_path": "/foo/bar.py"},
        )

        assert event.type == EventType.TOOL_CALL
        assert event.tool_name == "Read"
        assert event.tool_input == {"file_path": "/foo/bar.py"}


class TestDecisionEvent:
    """Test DecisionEvent schema."""

    def test_create_decision_event(self):
        """Should create decision event with reasoning."""
        event = DecisionEvent(
            action="Used SQLite for storage",
            reasoning="Need portability, single file",
            alternatives=["PostgreSQL", "JSON files"],
        )

        assert event.type == EventType.DECISION
        assert event.action == "Used SQLite for storage"
        assert event.reasoning == "Need portability, single file"
        assert "PostgreSQL" in event.alternatives
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/v3/capture/test_events.py -v
```

Expected: FAIL - module not found

**Step 3: Implement events.py**

```python
# src/mind/v3/capture/events.py
"""
Event types and schemas for Mind v3 event sourcing.

Events are immutable records of everything that happens during a session.
They form the foundation for the context graph.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events captured from Claude Code sessions."""

    # Raw events from transcripts
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"

    # Extracted/inferred events
    DECISION = "decision"
    ERROR = "error"
    FILE_CHANGE = "file_change"
    PATTERN_DETECTED = "pattern_detected"


def generate_event_id() -> str:
    """Generate a unique event ID."""
    return f"evt_{uuid.uuid4().hex[:12]}"


class Event(BaseModel):
    """Base event class for all Mind events."""

    id: str = Field(default_factory=generate_event_id)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: EventType
    session_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize event to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.type if isinstance(self.type, str) else self.type.value,
            "session_id": self.session_id,
            "data": self.data,
        }


class ToolCallEvent(Event):
    """Event representing a tool call by Claude."""

    type: EventType = EventType.TOOL_CALL
    tool_name: str
    tool_input: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["tool_name"] = self.tool_name
        d["tool_input"] = self.tool_input
        return d


class ToolResultEvent(Event):
    """Event representing a tool result."""

    type: EventType = EventType.TOOL_RESULT
    tool_name: str
    success: bool = True
    result: Any = None
    error: str | None = None


class UserMessageEvent(Event):
    """Event representing a user message."""

    type: EventType = EventType.USER_MESSAGE
    content: str = ""


class AssistantMessageEvent(Event):
    """Event representing an assistant response."""

    type: EventType = EventType.ASSISTANT_MESSAGE
    content: str = ""


class DecisionEvent(Event):
    """Event representing a decision made during the session."""

    type: EventType = EventType.DECISION
    action: str  # What was decided
    reasoning: str = ""  # Why (the gold)
    alternatives: list[str] = Field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["action"] = self.action
        d["reasoning"] = self.reasoning
        d["alternatives"] = self.alternatives
        d["confidence"] = self.confidence
        return d


class ErrorEvent(Event):
    """Event representing an error encountered."""

    type: EventType = EventType.ERROR
    error_type: str = ""
    error_message: str = ""
    file_path: str | None = None
    line_number: int | None = None


class FileChangeEvent(Event):
    """Event representing a file modification."""

    type: EventType = EventType.FILE_CHANGE
    file_path: str
    change_type: str  # created, modified, deleted
    lines_added: int = 0
    lines_removed: int = 0
```

**Step 4: Create test directory and __init__.py**

```bash
mkdir -p tests/v3/capture
touch tests/v3/__init__.py
touch tests/v3/capture/__init__.py
```

**Step 5: Run tests**

```bash
uv run pytest tests/v3/capture/test_events.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add -A
git commit -m "feat(v3): add event schema for event sourcing

Implements base Event class with types:
- ToolCallEvent, ToolResultEvent
- UserMessageEvent, AssistantMessageEvent
- DecisionEvent (with reasoning capture)
- ErrorEvent, FileChangeEvent

Foundation for transcript capture and context graph."
```

---

### Task 1.2: Event Store

**Files:**
- Create: `src/mind/v3/capture/store.py`
- Create: `tests/v3/capture/test_store.py`

**Step 1: Write the failing test**

```python
# tests/v3/capture/test_store.py
"""Tests for event store."""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from mind.v3.capture.events import Event, EventType, ToolCallEvent, DecisionEvent
from mind.v3.capture.store import EventStore


@pytest.fixture
def temp_store():
    """Create a temporary event store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = EventStore(Path(tmpdir) / "events")
        yield store


class TestEventStore:
    """Test EventStore class."""

    def test_append_event(self, temp_store):
        """Should append event to store."""
        event = ToolCallEvent(tool_name="Read", tool_input={"file_path": "/foo"})

        temp_store.append(event)

        events = list(temp_store.iter_events())
        assert len(events) == 1
        assert events[0]["tool_name"] == "Read"

    def test_append_multiple_events(self, temp_store):
        """Should append multiple events in order."""
        e1 = ToolCallEvent(tool_name="Read", tool_input={})
        e2 = ToolCallEvent(tool_name="Write", tool_input={})
        e3 = DecisionEvent(action="Used X", reasoning="Because Y")

        temp_store.append(e1)
        temp_store.append(e2)
        temp_store.append(e3)

        events = list(temp_store.iter_events())
        assert len(events) == 3
        assert events[0]["tool_name"] == "Read"
        assert events[1]["tool_name"] == "Write"
        assert events[2]["action"] == "Used X"

    def test_events_persisted_to_file(self, temp_store):
        """Events should be persisted to JSONL file."""
        event = ToolCallEvent(tool_name="Read", tool_input={})
        temp_store.append(event)

        # Create new store instance pointing to same directory
        store2 = EventStore(temp_store.path)
        events = list(store2.iter_events())

        assert len(events) == 1

    def test_iter_events_since(self, temp_store):
        """Should filter events by timestamp."""
        e1 = ToolCallEvent(tool_name="Read", tool_input={})
        temp_store.append(e1)

        cutoff = datetime.utcnow()

        e2 = ToolCallEvent(tool_name="Write", tool_input={})
        temp_store.append(e2)

        events = list(temp_store.iter_events(since=cutoff))
        assert len(events) == 1
        assert events[0]["tool_name"] == "Write"

    def test_get_event_count(self, temp_store):
        """Should return correct event count."""
        assert temp_store.count() == 0

        temp_store.append(ToolCallEvent(tool_name="Read", tool_input={}))
        assert temp_store.count() == 1

        temp_store.append(ToolCallEvent(tool_name="Write", tool_input={}))
        assert temp_store.count() == 2
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/v3/capture/test_store.py -v
```

**Step 3: Implement store.py**

```python
# src/mind/v3/capture/store.py
"""
Event store for Mind v3.

Append-only storage for events using JSONL format.
Events are immutable once written.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator, Any

from .events import Event


class EventStore:
    """
    Append-only event store using JSONL files.

    Events are stored in daily files: YYYY-MM-DD.jsonl
    This enables efficient date-range queries and archival.
    """

    def __init__(self, path: Path):
        """
        Initialize event store.

        Args:
            path: Directory to store event files
        """
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def _get_file_for_date(self, date: datetime) -> Path:
        """Get the JSONL file path for a given date."""
        return self.path / f"{date.strftime('%Y-%m-%d')}.jsonl"

    def _get_current_file(self) -> Path:
        """Get the JSONL file for today."""
        return self._get_file_for_date(datetime.utcnow())

    def append(self, event: Event) -> None:
        """
        Append an event to the store.

        Args:
            event: Event to append
        """
        file_path = self._get_file_for_date(event.timestamp)

        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    def iter_events(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        event_types: list[str] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """
        Iterate over events in the store.

        Args:
            since: Only return events after this timestamp
            until: Only return events before this timestamp
            event_types: Only return events of these types

        Yields:
            Event dictionaries
        """
        # Get all JSONL files, sorted by date
        files = sorted(self.path.glob("*.jsonl"))

        for file_path in files:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue

                    event = json.loads(line)

                    # Parse timestamp for filtering
                    event_time = datetime.fromisoformat(event["timestamp"])

                    # Apply filters
                    if since and event_time <= since:
                        continue
                    if until and event_time >= until:
                        continue
                    if event_types and event["type"] not in event_types:
                        continue

                    yield event

    def count(self) -> int:
        """Return total number of events in store."""
        total = 0
        for file_path in self.path.glob("*.jsonl"):
            with open(file_path, "r", encoding="utf-8") as f:
                total += sum(1 for line in f if line.strip())
        return total

    def get_latest(self, n: int = 10) -> list[dict[str, Any]]:
        """
        Get the N most recent events.

        Args:
            n: Number of events to return

        Returns:
            List of event dictionaries, most recent first
        """
        events = list(self.iter_events())
        return events[-n:][::-1]
```

**Step 4: Update capture __init__.py**

```python
# src/mind/v3/capture/__init__.py
"""Mind v3 event capture module."""

from .events import (
    Event,
    EventType,
    ToolCallEvent,
    ToolResultEvent,
    UserMessageEvent,
    AssistantMessageEvent,
    DecisionEvent,
    ErrorEvent,
    FileChangeEvent,
)
from .store import EventStore

__all__ = [
    "Event",
    "EventType",
    "ToolCallEvent",
    "ToolResultEvent",
    "UserMessageEvent",
    "AssistantMessageEvent",
    "DecisionEvent",
    "ErrorEvent",
    "FileChangeEvent",
    "EventStore",
]
```

**Step 5: Run tests**

```bash
uv run pytest tests/v3/capture/test_store.py -v
```

**Step 6: Commit**

```bash
git add -A
git commit -m "feat(v3): add event store with JSONL persistence

Append-only event store using daily JSONL files.
Supports:
- Immutable event appending
- Date-range filtering
- Event type filtering
- Efficient iteration"
```

---

### Task 1.3: Transcript Extractor

**Files:**
- Create: `src/mind/v3/capture/extractor.py`
- Create: `tests/v3/capture/test_extractor.py`

**Step 1: Write the failing test**

```python
# tests/v3/capture/test_extractor.py
"""Tests for transcript event extraction."""
import pytest
import json
import base64
from mind.v3.capture.extractor import TranscriptExtractor
from mind.v3.capture.events import EventType


class TestTranscriptExtractor:
    """Test TranscriptExtractor class."""

    def test_extract_user_message(self):
        """Should extract user message events."""
        extractor = TranscriptExtractor()

        # Simulated transcript turn
        turn = {
            "role": "user",
            "content": "Help me fix this bug"
        }

        events = extractor.extract_from_turn(turn)

        assert len(events) == 1
        assert events[0].type == EventType.USER_MESSAGE
        assert "fix this bug" in events[0].content

    def test_extract_tool_call(self):
        """Should extract tool call events."""
        extractor = TranscriptExtractor()

        turn = {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "name": "Read",
                    "input": {"file_path": "/foo/bar.py"}
                }
            ]
        }

        events = extractor.extract_from_turn(turn)

        tool_calls = [e for e in events if e.type == EventType.TOOL_CALL]
        assert len(tool_calls) == 1
        assert tool_calls[0].tool_name == "Read"
        assert tool_calls[0].tool_input["file_path"] == "/foo/bar.py"

    def test_extract_decision_keywords(self):
        """Should detect decisions from keywords in assistant messages."""
        extractor = TranscriptExtractor()

        turn = {
            "role": "assistant",
            "content": "I decided to use SQLite because it's portable and doesn't require a server."
        }

        events = extractor.extract_from_turn(turn)

        decisions = [e for e in events if e.type == EventType.DECISION]
        assert len(decisions) >= 1
        assert "SQLite" in decisions[0].action

    def test_extract_multiple_tool_calls(self):
        """Should extract multiple tool calls from single turn."""
        extractor = TranscriptExtractor()

        turn = {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "name": "Read", "input": {"file_path": "/a.py"}},
                {"type": "tool_use", "name": "Read", "input": {"file_path": "/b.py"}},
            ]
        }

        events = extractor.extract_from_turn(turn)

        tool_calls = [e for e in events if e.type == EventType.TOOL_CALL]
        assert len(tool_calls) == 2
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/v3/capture/test_extractor.py -v
```

**Step 3: Implement extractor.py**

```python
# src/mind/v3/capture/extractor.py
"""
Transcript event extraction for Mind v3.

Extracts structured events from Claude Code conversation transcripts.
"""
from __future__ import annotations

import re
from typing import Any

from .events import (
    Event,
    EventType,
    ToolCallEvent,
    ToolResultEvent,
    UserMessageEvent,
    AssistantMessageEvent,
    DecisionEvent,
    ErrorEvent,
)


# Keywords that indicate a decision was made
DECISION_KEYWORDS = [
    r"\bdecided\s+to\b",
    r"\bchose\s+to\b",
    r"\bgoing\s+with\b",
    r"\busing\b",
    r"\bwent\s+with\b",
    r"\bsettled\s+on\b",
    r"\bI'll\s+use\b",
    r"\blet's\s+use\b",
    r"\bbecause\b.*\bbetter\b",
]

# Keywords that indicate reasoning
REASONING_KEYWORDS = [
    r"\bbecause\b",
    r"\bsince\b",
    r"\bas\b",
    r"\bdue\s+to\b",
    r"\bfor\s+this\s+reason\b",
]


class TranscriptExtractor:
    """
    Extracts events from Claude Code transcript turns.

    This is the local (Layer 1) extraction using regex and heuristics.
    AI-powered extraction (Layer 2) enhances these results.
    """

    def __init__(self):
        """Initialize extractor with compiled patterns."""
        self.decision_patterns = [re.compile(p, re.IGNORECASE) for p in DECISION_KEYWORDS]
        self.reasoning_patterns = [re.compile(p, re.IGNORECASE) for p in REASONING_KEYWORDS]

    def extract_from_turn(self, turn: dict[str, Any]) -> list[Event]:
        """
        Extract events from a single conversation turn.

        Args:
            turn: Conversation turn with 'role' and 'content'

        Returns:
            List of extracted events
        """
        events: list[Event] = []
        role = turn.get("role", "")
        content = turn.get("content", "")

        if role == "user":
            events.extend(self._extract_user_events(content))
        elif role == "assistant":
            events.extend(self._extract_assistant_events(content))

        return events

    def _extract_user_events(self, content: Any) -> list[Event]:
        """Extract events from user message."""
        events = []

        if isinstance(content, str):
            events.append(UserMessageEvent(content=content))
        elif isinstance(content, list):
            # Handle structured content
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
            if text_parts:
                events.append(UserMessageEvent(content=" ".join(text_parts)))

        return events

    def _extract_assistant_events(self, content: Any) -> list[Event]:
        """Extract events from assistant message."""
        events = []

        if isinstance(content, str):
            # Text response
            events.append(AssistantMessageEvent(content=content))
            events.extend(self._detect_decisions(content))

        elif isinstance(content, list):
            # Structured content with tool calls
            text_parts = []

            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "tool_use":
                        events.append(ToolCallEvent(
                            tool_name=part.get("name", "unknown"),
                            tool_input=part.get("input", {}),
                        ))
                    elif part.get("type") == "tool_result":
                        events.append(ToolResultEvent(
                            tool_name=part.get("name", "unknown"),
                            success=not part.get("is_error", False),
                            result=part.get("content"),
                            error=part.get("content") if part.get("is_error") else None,
                        ))
                    elif part.get("type") == "text":
                        text_parts.append(part.get("text", ""))

            if text_parts:
                full_text = " ".join(text_parts)
                events.append(AssistantMessageEvent(content=full_text))
                events.extend(self._detect_decisions(full_text))

        return events

    def _detect_decisions(self, text: str) -> list[DecisionEvent]:
        """
        Detect decision statements in text using keyword patterns.

        This is basic heuristic detection. AI extraction improves on this.
        """
        decisions = []

        for pattern in self.decision_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                # Extract sentence containing the decision
                start = max(0, text.rfind(".", 0, match.start()) + 1)
                end = text.find(".", match.end())
                if end == -1:
                    end = len(text)

                sentence = text[start:end].strip()

                if len(sentence) > 10:  # Skip very short matches
                    # Try to extract reasoning
                    reasoning = ""
                    for r_pattern in self.reasoning_patterns:
                        r_match = r_pattern.search(sentence)
                        if r_match:
                            reasoning = sentence[r_match.start():].strip()
                            break

                    decisions.append(DecisionEvent(
                        action=sentence[:200],  # Truncate if too long
                        reasoning=reasoning[:500],
                        confidence=0.5,  # Low confidence for heuristic detection
                    ))
                    break  # One decision per pattern match

        return decisions

    def extract_from_transcript(self, transcript: list[dict[str, Any]]) -> list[Event]:
        """
        Extract all events from a full transcript.

        Args:
            transcript: List of conversation turns

        Returns:
            List of all extracted events
        """
        all_events = []

        for turn in transcript:
            events = self.extract_from_turn(turn)
            all_events.extend(events)

        return all_events
```

**Step 4: Run tests**

```bash
uv run pytest tests/v3/capture/test_extractor.py -v
```

**Step 5: Commit**

```bash
git add -A
git commit -m "feat(v3): add transcript event extractor

Local (Layer 1) extraction using regex and heuristics:
- User/assistant message extraction
- Tool call/result detection
- Decision keyword detection with reasoning capture

Foundation for AI-enhanced extraction in Layer 2."
```

---

## Phase 2: Context Graph (LanceDB)

### Task 2.1: Graph Store

**Files:**
- Create: `src/mind/v3/graph/store.py`
- Create: `tests/v3/graph/test_store.py`

**Step 1: Write the failing test**

```python
# tests/v3/graph/test_store.py
"""Tests for LanceDB graph store."""
import pytest
import tempfile
from pathlib import Path

from mind.v3.graph.store import GraphStore


@pytest.fixture
def temp_graph():
    """Create a temporary graph store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = GraphStore(Path(tmpdir) / "graph")
        yield store


class TestGraphStore:
    """Test GraphStore class."""

    def test_create_store(self, temp_graph):
        """Should create store with all tables."""
        assert temp_graph.is_initialized()
        assert "decisions" in temp_graph.list_tables()
        assert "entities" in temp_graph.list_tables()
        assert "patterns" in temp_graph.list_tables()

    def test_add_decision(self, temp_graph):
        """Should add decision to graph."""
        decision = {
            "action": "Used SQLite for storage",
            "reasoning": "Need portability",
            "confidence": 0.85,
        }

        doc_id = temp_graph.add_decision(decision)

        assert doc_id is not None
        retrieved = temp_graph.get_decision(doc_id)
        assert retrieved["action"] == "Used SQLite for storage"

    def test_search_decisions(self, temp_graph):
        """Should search decisions by text."""
        temp_graph.add_decision({
            "action": "Used SQLite for storage",
            "reasoning": "Need portability",
        })
        temp_graph.add_decision({
            "action": "Used PostgreSQL for production",
            "reasoning": "Need scalability",
        })

        results = temp_graph.search_decisions("portable storage", limit=5)

        assert len(results) >= 1
        assert "SQLite" in results[0]["action"]

    def test_add_entity(self, temp_graph):
        """Should add entity to graph."""
        entity = {
            "name": "storage.py",
            "type": "file",
            "description": "Storage module",
        }

        doc_id = temp_graph.add_entity(entity)

        assert doc_id is not None

    def test_add_pattern(self, temp_graph):
        """Should add pattern to graph."""
        pattern = {
            "description": "Prefers functional style",
            "confidence": 0.8,
            "evidence_count": 5,
        }

        doc_id = temp_graph.add_pattern(pattern)

        assert doc_id is not None
```

**Step 2: Run test to verify it fails**

```bash
mkdir -p tests/v3/graph
touch tests/v3/graph/__init__.py
uv run pytest tests/v3/graph/test_store.py -v
```

**Step 3: Implement store.py**

```python
# src/mind/v3/graph/store.py
"""
LanceDB graph store for Mind v3 context graph.

Provides vector storage and search for all graph node types.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import lancedb
from lancedb.pydantic import LanceModel, Vector


# Embedding dimension (using small model for now)
EMBED_DIM = 384


class DecisionModel(LanceModel):
    """LanceDB model for decisions."""
    id: str
    action: str
    reasoning: str = ""
    confidence: float = 0.0
    timestamp: str = ""
    vector: Vector(EMBED_DIM) = None  # type: ignore


class EntityModel(LanceModel):
    """LanceDB model for entities."""
    id: str
    name: str
    type: str
    description: str = ""
    vector: Vector(EMBED_DIM) = None  # type: ignore


class PatternModel(LanceModel):
    """LanceDB model for patterns."""
    id: str
    description: str
    confidence: float = 0.0
    evidence_count: int = 0
    vector: Vector(EMBED_DIM) = None  # type: ignore


def generate_id(prefix: str) -> str:
    """Generate a unique ID with prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def get_dummy_vector() -> list[float]:
    """Get a dummy vector for testing (replaced by real embeddings later)."""
    import random
    return [random.random() for _ in range(EMBED_DIM)]


class GraphStore:
    """
    LanceDB-backed context graph store.

    Provides storage and vector search for:
    - Decisions
    - Entities
    - Patterns
    - Policies
    - Exceptions
    - Precedents
    - Outcomes
    """

    def __init__(self, path: Path):
        """
        Initialize graph store.

        Args:
            path: Directory for LanceDB files
        """
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

        self.db = lancedb.connect(str(self.path))
        self._init_tables()

    def _init_tables(self) -> None:
        """Initialize all graph tables."""
        existing = set(self.db.table_names())

        # Create tables if they don't exist
        if "decisions" not in existing:
            self.db.create_table(
                "decisions",
                schema=DecisionModel,
                mode="create",
            )

        if "entities" not in existing:
            self.db.create_table(
                "entities",
                schema=EntityModel,
                mode="create",
            )

        if "patterns" not in existing:
            self.db.create_table(
                "patterns",
                schema=PatternModel,
                mode="create",
            )

    def is_initialized(self) -> bool:
        """Check if store is properly initialized."""
        required = {"decisions", "entities", "patterns"}
        return required.issubset(set(self.db.table_names()))

    def list_tables(self) -> list[str]:
        """List all tables in the store."""
        return self.db.table_names()

    # Decision operations

    def add_decision(self, decision: dict[str, Any]) -> str:
        """
        Add a decision to the graph.

        Args:
            decision: Decision data

        Returns:
            Generated decision ID
        """
        doc_id = generate_id("dec")

        record = DecisionModel(
            id=doc_id,
            action=decision.get("action", ""),
            reasoning=decision.get("reasoning", ""),
            confidence=decision.get("confidence", 0.0),
            timestamp=decision.get("timestamp", datetime.utcnow().isoformat()),
            vector=get_dummy_vector(),  # TODO: Real embeddings
        )

        table = self.db.open_table("decisions")
        table.add([record])

        return doc_id

    def get_decision(self, doc_id: str) -> dict[str, Any] | None:
        """Get a decision by ID."""
        table = self.db.open_table("decisions")
        results = table.search().where(f"id = '{doc_id}'").limit(1).to_list()

        if results:
            return dict(results[0])
        return None

    def search_decisions(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search decisions by text similarity.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching decisions
        """
        table = self.db.open_table("decisions")

        # For now, use dummy vector search (will be replaced with real embeddings)
        query_vector = get_dummy_vector()

        results = table.search(query_vector).limit(limit).to_list()
        return [dict(r) for r in results]

    # Entity operations

    def add_entity(self, entity: dict[str, Any]) -> str:
        """Add an entity to the graph."""
        doc_id = generate_id("ent")

        record = EntityModel(
            id=doc_id,
            name=entity.get("name", ""),
            type=entity.get("type", "unknown"),
            description=entity.get("description", ""),
            vector=get_dummy_vector(),
        )

        table = self.db.open_table("entities")
        table.add([record])

        return doc_id

    # Pattern operations

    def add_pattern(self, pattern: dict[str, Any]) -> str:
        """Add a pattern to the graph."""
        doc_id = generate_id("pat")

        record = PatternModel(
            id=doc_id,
            description=pattern.get("description", ""),
            confidence=pattern.get("confidence", 0.0),
            evidence_count=pattern.get("evidence_count", 0),
            vector=get_dummy_vector(),
        )

        table = self.db.open_table("patterns")
        table.add([record])

        return doc_id
```

**Step 4: Run tests**

```bash
uv run pytest tests/v3/graph/test_store.py -v
```

**Step 5: Commit**

```bash
git add -A
git commit -m "feat(v3): add LanceDB graph store

Vector storage for context graph nodes:
- Decisions with action, reasoning, confidence
- Entities with name, type, description
- Patterns with evidence tracking

Uses dummy vectors for now, real embeddings in next task."
```

---

## Phase 3-6: Continued Implementation

*The remaining phases follow the same TDD pattern:*

### Phase 3: Intelligence Layer
- Task 3.1: Model Cascade Router
- Task 3.2: Decision Extractor (AI-powered)
- Task 3.3: Entity Extractor
- Task 3.4: Pattern Detector

### Phase 4: Retrieval Layer
- Task 4.1: Embedding Service
- Task 4.2: Hybrid Search
- Task 4.3: Reranking
- Task 4.4: Context Injection Hook

### Phase 5: Memory System
- Task 5.1: Working Memory
- Task 5.2: Memory Consolidation
- Task 5.3: Decay System
- Task 5.4: Reinforcement

### Phase 6: Autonomy System
- Task 6.1: Confidence Tracking
- Task 6.2: Autonomy Levels
- Task 6.3: Feedback Loop
- Task 6.4: Observability Dashboard

---

## Verification Checklist

After each phase, verify:

- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] No regressions in existing functionality
- [ ] Code follows project conventions
- [ ] New modules are properly exported
- [ ] Changes committed with descriptive messages

---

## Architecture Decisions

### Why Event Sourcing?
- Immutable audit trail
- Time-travel debugging
- Flexible projections
- Natural for context graph building

### Why LanceDB?
- Battle-tested (Midjourney, Runway)
- File-based (matches Mind philosophy)
- Hybrid search support
- No server required

### Why Model Cascade?
- Cost optimization (90% local, 10% API)
- Speed for real-time capture
- Intelligence where it matters

### Why This Module Structure?
- Clear separation of concerns
- Independent testability
- Easy to extend/replace components
- Gradual migration from v2

---

*Document created: 2025-12-25*
*Total tasks: ~24 across 6 phases*
*Estimated implementation: 8-10 weeks*
