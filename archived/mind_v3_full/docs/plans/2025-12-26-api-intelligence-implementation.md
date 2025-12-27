# API Intelligence Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Claude API integration for enhanced context extraction, session summaries, and intelligent reranking with configurable intelligence levels.

**Architecture:** Local-first with optional API escalation. Active capture during sessions feeds background processing which structures data into LanceDB. Session end triggers AI synthesis for double-confirmation.

**Tech Stack:** Anthropic Python SDK, asyncio, existing LanceDB/sentence-transformers stack.

---

## Task 1: API Client Foundation

**Files:**
- Create: `src/mind/v3/api/__init__.py`
- Create: `src/mind/v3/api/client.py`
- Test: `tests/v3/api/test_client.py`

**Step 1: Create test file with imports and basic tests**

Create `tests/v3/api/__init__.py`:
```python
"""API module tests."""
```

Create `tests/v3/api/test_client.py`:
```python
"""Tests for Claude API client."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from mind.v3.api.client import ClaudeClient, ClaudeConfig


class TestClaudeConfig:
    """Test ClaudeConfig dataclass."""

    def test_defaults(self):
        """Default config has no API key and FREE level."""
        config = ClaudeConfig()
        assert config.api_key is None
        assert config.intelligence_level == "FREE"
        assert config.max_retries == 3
        assert config.timeout == 30.0

    def test_from_env(self):
        """Config loads API key from environment."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test-123"}):
            config = ClaudeConfig.from_env()
            assert config.api_key == "sk-test-123"


class TestClaudeClient:
    """Test ClaudeClient."""

    def test_enabled_requires_key_and_level(self):
        """Client is only enabled with API key and non-FREE level."""
        # No key = disabled
        client = ClaudeClient(ClaudeConfig())
        assert not client.enabled

        # Key but FREE = disabled
        client = ClaudeClient(ClaudeConfig(api_key="sk-test", intelligence_level="FREE"))
        assert not client.enabled

        # Key and LITE = enabled
        client = ClaudeClient(ClaudeConfig(api_key="sk-test", intelligence_level="LITE"))
        assert client.enabled

    def test_model_selection(self):
        """Correct model IDs are used."""
        client = ClaudeClient(ClaudeConfig(api_key="sk-test", intelligence_level="BALANCED"))
        assert "haiku" in client.MODELS
        assert "sonnet" in client.MODELS
        assert "opus" in client.MODELS

    @pytest.mark.asyncio
    async def test_call_haiku_disabled(self):
        """Haiku call returns empty when disabled."""
        client = ClaudeClient(ClaudeConfig())
        result = await client.call_haiku("test prompt")
        assert result == ""

    @pytest.mark.asyncio
    async def test_call_haiku_mocked(self):
        """Haiku call works with mocked API."""
        config = ClaudeConfig(api_key="sk-test", intelligence_level="BALANCED")
        client = ClaudeClient(config)

        mock_response = Mock()
        mock_response.content = [Mock(text="extracted data")]

        with patch.object(client, "_get_client") as mock_get:
            mock_client = Mock()
            mock_client.messages.create = Mock(return_value=mock_response)
            mock_get.return_value = mock_client

            result = await client.call_haiku("test prompt", system="extract")
            assert result == "extracted data"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/v3/api/test_client.py -v`
Expected: ModuleNotFoundError for mind.v3.api.client

**Step 3: Create the api module init**

Create `src/mind/v3/api/__init__.py`:
```python
"""
Claude API integration for Mind v3.

Provides optional API escalation for:
- Enhanced extraction when local confidence is low
- Context reranking for better retrieval
- Session summaries and synthesis
"""
from .client import ClaudeClient, ClaudeConfig

__all__ = ["ClaudeClient", "ClaudeConfig"]
```

**Step 4: Implement ClaudeClient**

Create `src/mind/v3/api/client.py`:
```python
"""
Claude API client for Mind v3.

Provides unified access to Haiku, Sonnet, and Opus models
based on configured intelligence level.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ClaudeConfig:
    """Configuration for Claude API."""

    api_key: str | None = None
    intelligence_level: str = "FREE"  # FREE, LITE, BALANCED, PRO, ULTRA
    max_retries: int = 3
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "ClaudeConfig":
        """Create config from environment variables."""
        return cls(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            intelligence_level=os.getenv("MIND_INTELLIGENCE_LEVEL", "FREE"),
        )


class ClaudeClient:
    """
    Unified client for Claude API calls.

    Provides call_haiku, call_sonnet, call_opus methods
    that respect the configured intelligence level.
    """

    MODELS = {
        "haiku": "claude-3-5-haiku-20241022",
        "sonnet": "claude-sonnet-4-20250514",
        "opus": "claude-opus-4-20250514",
    }

    def __init__(self, config: ClaudeConfig | None = None):
        """
        Initialize client.

        Args:
            config: API configuration
        """
        self.config = config or ClaudeConfig()
        self._client: Any = None

    @property
    def enabled(self) -> bool:
        """Check if API is configured and enabled."""
        return (
            self.config.api_key is not None
            and self.config.intelligence_level != "FREE"
        )

    def _get_client(self) -> Any:
        """Get or create Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(
                    api_key=self.config.api_key,
                    timeout=self.config.timeout,
                    max_retries=self.config.max_retries,
                )
            except ImportError:
                logger.warning("anthropic package not installed, API calls disabled")
                return None
        return self._client

    async def call_haiku(self, prompt: str, system: str = "") -> str:
        """
        Call Haiku model for fast, cheap operations.

        Args:
            prompt: User prompt
            system: System prompt

        Returns:
            Model response text, empty string if disabled
        """
        if not self.enabled:
            return ""

        return await self._call_model("haiku", prompt, system)

    async def call_sonnet(self, prompt: str, system: str = "") -> str:
        """
        Call Sonnet model for balanced operations.

        Args:
            prompt: User prompt
            system: System prompt

        Returns:
            Model response text, empty string if disabled
        """
        if not self.enabled:
            return ""

        return await self._call_model("sonnet", prompt, system)

    async def call_opus(self, prompt: str, system: str = "") -> str:
        """
        Call Opus model for deep reasoning.

        Args:
            prompt: User prompt
            system: System prompt

        Returns:
            Model response text, empty string if disabled
        """
        if not self.enabled:
            return ""

        return await self._call_model("opus", prompt, system)

    async def _call_model(self, model_key: str, prompt: str, system: str) -> str:
        """
        Make API call to specified model.

        Args:
            model_key: Key in MODELS dict
            prompt: User prompt
            system: System prompt

        Returns:
            Response text
        """
        client = self._get_client()
        if not client:
            return ""

        try:
            messages = [{"role": "user", "content": prompt}]
            kwargs: dict[str, Any] = {
                "model": self.MODELS[model_key],
                "max_tokens": 1024,
                "messages": messages,
            }
            if system:
                kwargs["system"] = system

            response = client.messages.create(**kwargs)
            return response.content[0].text

        except Exception as e:
            logger.error(f"API call to {model_key} failed: {e}")
            return ""
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/v3/api/test_client.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/mind/v3/api tests/v3/api
git commit -m "feat(v3): add Claude API client foundation"
```

---

## Task 2: Intelligence Levels Configuration

**Files:**
- Create: `src/mind/v3/api/levels.py`
- Test: `tests/v3/api/test_levels.py`
- Modify: `src/mind/v3/config.py` (add API config section)

**Step 1: Write tests for intelligence levels**

Create `tests/v3/api/test_levels.py`:
```python
"""Tests for intelligence levels configuration."""
import pytest
from mind.v3.api.levels import IntelligenceLevel, LEVELS, get_level


class TestIntelligenceLevel:
    """Test IntelligenceLevel dataclass."""

    def test_free_level_no_models(self):
        """FREE level uses no API models."""
        level = LEVELS["FREE"]
        assert level.extraction_model is None
        assert level.reranking_model is None
        assert level.summary_model is None

    def test_lite_level_haiku_escalation(self):
        """LITE level uses Haiku for escalation only."""
        level = LEVELS["LITE"]
        assert level.extraction_model == "haiku"
        assert level.reranking_model is None
        assert level.summary_model is None

    def test_balanced_level(self):
        """BALANCED uses Haiku extraction, Sonnet summaries."""
        level = LEVELS["BALANCED"]
        assert level.extraction_model == "haiku"
        assert level.reranking_model == "haiku"
        assert level.summary_model == "sonnet"

    def test_pro_level(self):
        """PRO uses Haiku extraction, Sonnet for rest."""
        level = LEVELS["PRO"]
        assert level.extraction_model == "haiku"
        assert level.reranking_model == "sonnet"
        assert level.summary_model == "sonnet"

    def test_ultra_level_opus(self):
        """ULTRA uses Opus for reranking and summaries."""
        level = LEVELS["ULTRA"]
        assert level.extraction_model == "sonnet"
        assert level.reranking_model == "opus"
        assert level.summary_model == "opus"

    def test_get_level_valid(self):
        """get_level returns correct level."""
        level = get_level("BALANCED")
        assert level.name == "BALANCED"

    def test_get_level_invalid_returns_free(self):
        """get_level returns FREE for invalid names."""
        level = get_level("INVALID")
        assert level.name == "FREE"

    def test_all_levels_have_cost(self):
        """All levels have estimated cost."""
        for name, level in LEVELS.items():
            assert level.estimated_cost is not None
            assert "$" in level.estimated_cost
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/v3/api/test_levels.py -v`
Expected: ModuleNotFoundError

**Step 3: Implement intelligence levels**

Create `src/mind/v3/api/levels.py`:
```python
"""
Intelligence levels for Mind v3.

Defines model selection for each processing task
based on user's chosen cost/quality tradeoff.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IntelligenceLevel:
    """Configuration for an intelligence level."""

    name: str
    description: str
    extraction_model: str | None  # None = local only
    reranking_model: str | None
    summary_model: str | None
    estimated_cost: str


LEVELS: dict[str, IntelligenceLevel] = {
    "FREE": IntelligenceLevel(
        name="FREE",
        description="100% local processing, no API calls",
        extraction_model=None,
        reranking_model=None,
        summary_model=None,
        estimated_cost="$0/mo",
    ),
    "LITE": IntelligenceLevel(
        name="LITE",
        description="Local + Haiku escalation for low-confidence extractions",
        extraction_model="haiku",  # Only when confidence < 0.6
        reranking_model=None,
        summary_model=None,
        estimated_cost="~$2/mo",
    ),
    "BALANCED": IntelligenceLevel(
        name="BALANCED",
        description="Haiku extraction, Haiku reranking, Sonnet summaries",
        extraction_model="haiku",
        reranking_model="haiku",
        summary_model="sonnet",
        estimated_cost="~$15/mo",
    ),
    "PRO": IntelligenceLevel(
        name="PRO",
        description="Full Haiku extraction, Sonnet reranking and summaries",
        extraction_model="haiku",
        reranking_model="sonnet",
        summary_model="sonnet",
        estimated_cost="~$40/mo",
    ),
    "ULTRA": IntelligenceLevel(
        name="ULTRA",
        description="Sonnet extraction, Opus reranking and synthesis",
        extraction_model="sonnet",
        reranking_model="opus",
        summary_model="opus",
        estimated_cost="~$150/mo",
    ),
}


def get_level(name: str) -> IntelligenceLevel:
    """
    Get intelligence level by name.

    Args:
        name: Level name (case-insensitive)

    Returns:
        IntelligenceLevel, defaults to FREE if invalid
    """
    return LEVELS.get(name.upper(), LEVELS["FREE"])
```

**Step 4: Update api/__init__.py**

Edit `src/mind/v3/api/__init__.py`:
```python
"""
Claude API integration for Mind v3.

Provides optional API escalation for:
- Enhanced extraction when local confidence is low
- Context reranking for better retrieval
- Session summaries and synthesis
"""
from .client import ClaudeClient, ClaudeConfig
from .levels import IntelligenceLevel, LEVELS, get_level

__all__ = [
    "ClaudeClient",
    "ClaudeConfig",
    "IntelligenceLevel",
    "LEVELS",
    "get_level",
]
```

**Step 5: Run tests**

Run: `uv run pytest tests/v3/api/test_levels.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/mind/v3/api tests/v3/api
git commit -m "feat(v3): add intelligence levels configuration"
```

---

## Task 3: Add API Config to V3Settings

**Files:**
- Modify: `src/mind/v3/config.py`
- Modify: `tests/v3/test_config.py`

**Step 1: Write tests for API config**

Add to `tests/v3/test_config.py`:
```python
class TestAPIConfig:
    """Test API configuration in V3Settings."""

    def test_default_api_config(self):
        """Default has FREE intelligence level."""
        settings = V3Settings()
        assert settings.api.intelligence_level == "FREE"
        assert settings.api.api_key is None

    def test_api_config_from_dict(self):
        """API config loads from dict."""
        settings = V3Settings.from_dict({
            "api": {
                "intelligence_level": "BALANCED",
            }
        })
        assert settings.api.intelligence_level == "BALANCED"

    def test_api_config_from_env(self):
        """API key loads from environment."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
            settings = V3Settings()
            settings._apply_env_overrides()
            assert settings.api.api_key == "sk-test"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/v3/test_config.py::TestAPIConfig -v`
Expected: AttributeError (no api attribute)

**Step 3: Add APIConfig to V3Settings**

Edit `src/mind/v3/config.py`, add import and config class:

After line 28 (after other imports), add:
```python
from .api.client import ClaudeConfig
```

In V3Settings dataclass (after autonomy settings around line 63), add:
```python
    # API settings
    api: ClaudeConfig = field(default_factory=ClaudeConfig)
```

In from_dict method (after autonomy section), add:
```python
        # API settings
        if "api" in data:
            settings.api = ClaudeConfig(**data["api"])
```

In _apply_env_overrides method, add:
```python
        # API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            self.api.api_key = api_key
        level = os.getenv("MIND_INTELLIGENCE_LEVEL")
        if level:
            self.api.intelligence_level = level
```

**Step 4: Run tests**

Run: `uv run pytest tests/v3/test_config.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/mind/v3/config.py tests/v3/test_config.py
git commit -m "feat(v3): add API config to V3Settings"
```

---

## Task 4: Enhanced Event Types for Active Capture

**Files:**
- Modify: `src/mind/v3/capture/events.py`
- Modify: `tests/v3/capture/test_events.py`

**Step 1: Write tests for new event types**

Add to `tests/v3/capture/test_events.py`:
```python
from datetime import datetime
from mind.v3.capture.events import (
    PromptEvent, ToolCallEvent, FileChangeEvent, ErrorEvent, BaseEvent
)


class TestPromptEvent:
    """Test PromptEvent dataclass."""

    def test_create_prompt_event(self):
        """PromptEvent captures user prompt with context."""
        event = PromptEvent(
            timestamp=datetime.now(),
            content="Fix the login bug",
            context_items=["auth module uses JWT"],
        )
        assert event.content == "Fix the login bug"
        assert len(event.context_items) == 1
        assert isinstance(event, BaseEvent)


class TestToolCallEvent:
    """Test ToolCallEvent dataclass."""

    def test_create_tool_call(self):
        """ToolCallEvent captures tool invocation."""
        event = ToolCallEvent(
            timestamp=datetime.now(),
            tool_name="Read",
            arguments={"file_path": "src/auth.py"},
            result_summary="File contents...",
            success=True,
            duration_ms=150.0,
        )
        assert event.tool_name == "Read"
        assert event.success is True


class TestFileChangeEvent:
    """Test FileChangeEvent dataclass."""

    def test_create_file_change(self):
        """FileChangeEvent captures file modifications."""
        event = FileChangeEvent(
            timestamp=datetime.now(),
            path="src/auth.py",
            change_type="modified",
            lines_changed=15,
        )
        assert event.change_type == "modified"


class TestErrorEvent:
    """Test ErrorEvent dataclass."""

    def test_create_error_event(self):
        """ErrorEvent captures errors."""
        event = ErrorEvent(
            timestamp=datetime.now(),
            error_type="SyntaxError",
            message="Unexpected token",
            context="Editing auth.py",
        )
        assert event.error_type == "SyntaxError"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/v3/capture/test_events.py -v`
Expected: ImportError (new classes don't exist)

**Step 3: Implement new event types**

Edit `src/mind/v3/capture/events.py`, add new dataclasses:

```python
"""
Event types for Mind v3 capture layer.

Defines structured events captured from Claude Code sessions:
- PromptEvent: User prompts with injected context
- ToolCallEvent: Tool invocations with results
- FileChangeEvent: File modifications
- ErrorEvent: Errors and failures
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(Enum):
    """Types of captured events."""
    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"
    TOOL_CALL = "tool_call"
    FILE_CHANGE = "file_change"
    ERROR = "error"
    DECISION = "decision"


@dataclass
class BaseEvent:
    """Base class for all events."""
    timestamp: datetime
    type: EventType = field(init=False)

    def __post_init__(self):
        if not hasattr(self, 'type') or self.type is None:
            self.type = EventType.USER_MESSAGE


@dataclass
class Event(BaseEvent):
    """Generic event with arbitrary data."""
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.type = EventType.USER_MESSAGE


@dataclass
class PromptEvent(BaseEvent):
    """User prompt with context."""
    content: str = ""
    context_items: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.type = EventType.USER_MESSAGE


@dataclass
class ToolCallEvent(BaseEvent):
    """Tool invocation."""
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    result_summary: str = ""
    success: bool = True
    duration_ms: float = 0.0

    def __post_init__(self):
        self.type = EventType.TOOL_CALL


@dataclass
class FileChangeEvent(BaseEvent):
    """File modification."""
    path: str = ""
    change_type: str = ""  # created, modified, deleted
    lines_changed: int = 0

    def __post_init__(self):
        self.type = EventType.FILE_CHANGE


@dataclass
class ErrorEvent(BaseEvent):
    """Error or failure."""
    error_type: str = ""
    message: str = ""
    context: str = ""

    def __post_init__(self):
        self.type = EventType.ERROR


@dataclass
class DecisionEvent(BaseEvent):
    """Decision extracted from conversation."""
    action: str = ""
    reasoning: str = ""
    alternatives: list[str] = field(default_factory=list)
    confidence: float = 0.0
    content: str = ""

    def __post_init__(self):
        self.type = EventType.DECISION
```

**Step 4: Run tests**

Run: `uv run pytest tests/v3/capture/test_events.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/mind/v3/capture/events.py tests/v3/capture/test_events.py
git commit -m "feat(v3): add enhanced event types for active capture"
```

---

## Task 5: Session Event Store

**Files:**
- Modify: `src/mind/v3/capture/store.py`
- Modify: `tests/v3/capture/test_store.py`

**Step 1: Write tests for SessionEventStore**

Add to `tests/v3/capture/test_store.py`:
```python
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from mind.v3.capture.store import SessionEventStore
from mind.v3.capture.events import PromptEvent, ToolCallEvent


class TestSessionEventStore:
    """Test SessionEventStore."""

    def test_add_event(self, tmp_path):
        """Events can be added to store."""
        store = SessionEventStore(tmp_path)
        event = PromptEvent(
            timestamp=datetime.now(),
            content="test prompt",
            context_items=[],
        )
        store.add(event)
        assert len(store.events) == 1

    def test_get_events_since(self, tmp_path):
        """Can filter events by timestamp."""
        store = SessionEventStore(tmp_path)
        old_time = datetime.now() - timedelta(hours=1)
        new_time = datetime.now()

        store.add(PromptEvent(timestamp=old_time, content="old"))
        store.add(PromptEvent(timestamp=new_time, content="new"))

        cutoff = datetime.now() - timedelta(minutes=30)
        recent = store.get_events_since(cutoff)
        assert len(recent) == 1
        assert recent[0].content == "new"

    def test_persist_and_load(self, tmp_path):
        """Store persists to disk and can be loaded."""
        store = SessionEventStore(tmp_path)
        store.add(PromptEvent(
            timestamp=datetime.now(),
            content="test",
            context_items=["ctx1"],
        ))
        store.persist()

        # Verify file exists
        session_dir = tmp_path / ".mind" / "v3" / "sessions"
        assert session_dir.exists()
        files = list(session_dir.glob("*.json"))
        assert len(files) == 1

    def test_session_id_format(self, tmp_path):
        """Session ID has expected format."""
        store = SessionEventStore(tmp_path)
        assert store.session_id is not None
        # Format: YYYYMMDD_HHMMSS
        assert "_" in store.session_id
        assert len(store.session_id) == 15
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/v3/capture/test_store.py::TestSessionEventStore -v`
Expected: ImportError or AttributeError

**Step 3: Implement SessionEventStore**

Edit `src/mind/v3/capture/store.py`:

```python
"""
Session event store for Mind v3.

Provides in-memory storage with disk persistence for
session events captured during Claude Code sessions.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .events import BaseEvent, PromptEvent, ToolCallEvent, FileChangeEvent, ErrorEvent

logger = logging.getLogger(__name__)


class SessionEventStore:
    """
    In-memory store for session events.

    Persists to .mind/v3/sessions/<session_id>.json
    """

    def __init__(self, project_path: Path):
        """
        Initialize store.

        Args:
            project_path: Project root directory
        """
        self.project_path = Path(project_path)
        self.events: list[BaseEvent] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._processing_callback: callable | None = None

    def add(self, event: BaseEvent) -> None:
        """
        Add event to store.

        Args:
            event: Event to add
        """
        self.events.append(event)

        # Trigger processing callback every 10 events
        if self._processing_callback and len(self.events) % 10 == 0:
            try:
                self._processing_callback(self.events[-10:])
            except Exception:
                logger.debug("Processing callback failed", exc_info=True)

    def get_events_since(self, timestamp: datetime) -> list[BaseEvent]:
        """
        Get events after timestamp.

        Args:
            timestamp: Cutoff timestamp

        Returns:
            List of events after timestamp
        """
        return [e for e in self.events if e.timestamp > timestamp]

    def set_processing_callback(self, callback: callable) -> None:
        """
        Set callback for batch processing.

        Args:
            callback: Function to call with event batches
        """
        self._processing_callback = callback

    def persist(self) -> Path:
        """
        Save session to disk.

        Returns:
            Path to saved file
        """
        session_dir = self.project_path / ".mind" / "v3" / "sessions"
        session_dir.mkdir(parents=True, exist_ok=True)

        file_path = session_dir / f"{self.session_id}.json"

        # Serialize events
        data = {
            "session_id": self.session_id,
            "event_count": len(self.events),
            "events": [self._serialize_event(e) for e in self.events],
        }

        file_path.write_text(json.dumps(data, indent=2, default=str))
        return file_path

    def _serialize_event(self, event: BaseEvent) -> dict:
        """Serialize event to dict."""
        data = {
            "type": event.type.value,
            "timestamp": event.timestamp.isoformat(),
        }

        if isinstance(event, PromptEvent):
            data["content"] = event.content
            data["context_items"] = event.context_items
        elif isinstance(event, ToolCallEvent):
            data["tool_name"] = event.tool_name
            data["arguments"] = event.arguments
            data["result_summary"] = event.result_summary
            data["success"] = event.success
            data["duration_ms"] = event.duration_ms
        elif isinstance(event, FileChangeEvent):
            data["path"] = event.path
            data["change_type"] = event.change_type
            data["lines_changed"] = event.lines_changed
        elif isinstance(event, ErrorEvent):
            data["error_type"] = event.error_type
            data["message"] = event.message
            data["context"] = event.context

        return data

    def clear(self) -> None:
        """Clear all events."""
        self.events = []
```

**Step 4: Run tests**

Run: `uv run pytest tests/v3/capture/test_store.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/mind/v3/capture/store.py tests/v3/capture/test_store.py
git commit -m "feat(v3): add SessionEventStore for active capture"
```

---

## Task 6: Event Categorizer with API Escalation

**Files:**
- Create: `src/mind/v3/processing/__init__.py`
- Create: `src/mind/v3/processing/categorize.py`
- Create: `tests/v3/processing/__init__.py`
- Create: `tests/v3/processing/test_categorize.py`

**Step 1: Write tests**

Create `tests/v3/processing/__init__.py`:
```python
"""Processing module tests."""
```

Create `tests/v3/processing/test_categorize.py`:
```python
"""Tests for event categorizer."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from mind.v3.processing.categorize import EventCategorizer, CategorizedEvent
from mind.v3.capture.events import PromptEvent, ToolCallEvent
from mind.v3.api.client import ClaudeClient, ClaudeConfig


class TestEventCategorizer:
    """Test EventCategorizer."""

    def test_local_categorize_decision(self):
        """Detects decision keywords locally."""
        categorizer = EventCategorizer()
        event = PromptEvent(
            timestamp=datetime.now(),
            content="I decided to use PostgreSQL instead of MySQL",
        )
        category, confidence = categorizer._local_categorize(event)
        assert category == "decision"
        assert confidence >= 0.6

    def test_local_categorize_learning(self):
        """Detects learning keywords locally."""
        categorizer = EventCategorizer()
        event = PromptEvent(
            timestamp=datetime.now(),
            content="TIL that Python 3.11 is much faster",
        )
        category, confidence = categorizer._local_categorize(event)
        assert category == "learning"

    def test_local_categorize_problem(self):
        """Detects problem keywords locally."""
        categorizer = EventCategorizer()
        event = PromptEvent(
            timestamp=datetime.now(),
            content="Bug: the login fails with empty password",
        )
        category, confidence = categorizer._local_categorize(event)
        assert category == "problem"

    def test_local_categorize_routine(self):
        """Routine operations are filtered out."""
        categorizer = EventCategorizer()
        event = ToolCallEvent(
            timestamp=datetime.now(),
            tool_name="Read",
            arguments={},
            result_summary="",
            success=True,
            duration_ms=100,
        )
        category, confidence = categorizer._local_categorize(event)
        assert category == "routine"

    @pytest.mark.asyncio
    async def test_categorize_no_client(self):
        """Categorize works without API client."""
        categorizer = EventCategorizer()
        events = [
            PromptEvent(
                timestamp=datetime.now(),
                content="decided to use Redis",
            )
        ]
        results = await categorizer.categorize(events)
        assert len(results) == 1
        assert results[0].category == "decision"

    @pytest.mark.asyncio
    async def test_categorize_filters_routine(self):
        """Routine events are not returned."""
        categorizer = EventCategorizer()
        events = [
            ToolCallEvent(
                timestamp=datetime.now(),
                tool_name="Glob",
                arguments={},
                result_summary="",
                success=True,
                duration_ms=50,
            )
        ]
        results = await categorizer.categorize(events)
        assert len(results) == 0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/v3/processing/test_categorize.py -v`
Expected: ModuleNotFoundError

**Step 3: Create processing module**

Create `src/mind/v3/processing/__init__.py`:
```python
"""
Background processing for Mind v3.

Processes captured events into structured data:
- Categorizes events by type
- Extracts structured information
- Links to existing graph nodes
- Consolidates redundant data
"""
from .categorize import EventCategorizer, CategorizedEvent

__all__ = ["EventCategorizer", "CategorizedEvent"]
```

**Step 4: Implement EventCategorizer**

Create `src/mind/v3/processing/categorize.py`:
```python
"""
Event categorizer for Mind v3.

Categorizes raw events into semantic types:
- decision: Choices made between alternatives
- learning: New knowledge gained
- problem: Issues encountered
- progress: Work completed
- exploration: Code reading/understanding
- routine: Standard operations (filtered out)
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..capture.events import BaseEvent, PromptEvent, ToolCallEvent, FileChangeEvent, ErrorEvent

if TYPE_CHECKING:
    from ..api.client import ClaudeClient

logger = logging.getLogger(__name__)


@dataclass
class CategorizedEvent:
    """Event with category assignment."""
    event: BaseEvent
    category: str
    confidence: float


class EventCategorizer:
    """
    Categorizes raw events into types.

    Uses local heuristics first, escalates to Haiku
    when confidence is low and API is enabled.
    """

    CATEGORIES = [
        "decision",
        "learning",
        "problem",
        "progress",
        "exploration",
        "routine",
    ]

    # Keyword patterns for local categorization
    DECISION_PATTERNS = [
        r"\b(decided|chose|going with|using|went with|settled on)\b",
        r"\b(will use|let's use|picked|selected)\b",
        r"\binstead of\b",
    ]

    LEARNING_PATTERNS = [
        r"\b(learned|discovered|realized|turns out|TIL)\b",
        r"\b(gotcha|figured out|now I know)\b",
        r"\b(apparently|interestingly)\b",
    ]

    PROBLEM_PATTERNS = [
        r"\b(bug|error|issue|problem|fails?|broken)\b",
        r"\b(stuck|blocked|can't|cannot|doesn't work)\b",
        r"\b(exception|crash|timeout)\b",
    ]

    PROGRESS_PATTERNS = [
        r"\b(fixed|resolved|completed|done|shipped)\b",
        r"\b(implemented|added|created|built)\b",
        r"\b(works now|passing|success)\b",
    ]

    def __init__(self):
        """Initialize categorizer."""
        self._decision_re = re.compile("|".join(self.DECISION_PATTERNS), re.IGNORECASE)
        self._learning_re = re.compile("|".join(self.LEARNING_PATTERNS), re.IGNORECASE)
        self._problem_re = re.compile("|".join(self.PROBLEM_PATTERNS), re.IGNORECASE)
        self._progress_re = re.compile("|".join(self.PROGRESS_PATTERNS), re.IGNORECASE)

    async def categorize(
        self,
        events: list[BaseEvent],
        client: "ClaudeClient | None" = None,
    ) -> list[CategorizedEvent]:
        """
        Categorize events.

        Args:
            events: Events to categorize
            client: Optional API client for escalation

        Returns:
            Non-routine events with categories
        """
        results = []

        for event in events:
            category, confidence = self._local_categorize(event)

            # Escalate to API if low confidence and client available
            if confidence < 0.6 and client and client.enabled:
                api_category = await self._api_categorize(event, client)
                if api_category:
                    category = api_category
                    confidence = 0.9

            # Filter out routine events
            if category != "routine":
                results.append(CategorizedEvent(
                    event=event,
                    category=category,
                    confidence=confidence,
                ))

        return results

    def _local_categorize(self, event: BaseEvent) -> tuple[str, float]:
        """
        Categorize event using local heuristics.

        Args:
            event: Event to categorize

        Returns:
            Tuple of (category, confidence)
        """
        # Tool calls are mostly routine
        if isinstance(event, ToolCallEvent):
            if event.tool_name in ("Read", "Glob", "Grep", "Bash"):
                return "routine", 0.9
            elif event.tool_name in ("Edit", "Write"):
                return "progress", 0.7
            return "exploration", 0.6

        # Errors are problems
        if isinstance(event, ErrorEvent):
            return "problem", 0.9

        # File changes are progress
        if isinstance(event, FileChangeEvent):
            return "progress", 0.7

        # For prompts, check content
        if isinstance(event, PromptEvent):
            content = event.content

            if self._decision_re.search(content):
                return "decision", 0.8
            if self._learning_re.search(content):
                return "learning", 0.8
            if self._problem_re.search(content):
                return "problem", 0.7
            if self._progress_re.search(content):
                return "progress", 0.7

            # Default to exploration for prompts
            return "exploration", 0.5

        return "routine", 0.5

    async def _api_categorize(
        self,
        event: BaseEvent,
        client: "ClaudeClient",
    ) -> str | None:
        """
        Categorize using API.

        Args:
            event: Event to categorize
            client: API client

        Returns:
            Category string or None
        """
        content = ""
        if isinstance(event, PromptEvent):
            content = event.content
        elif isinstance(event, ErrorEvent):
            content = f"{event.error_type}: {event.message}"

        if not content:
            return None

        prompt = f"""Categorize this text into exactly one category:
- decision: A choice between alternatives
- learning: New knowledge or discovery
- problem: An issue or bug
- progress: Work completed
- exploration: Code reading or understanding

Text: {content[:500]}

Reply with just the category name."""

        try:
            response = await client.call_haiku(prompt)
            category = response.strip().lower()
            if category in self.CATEGORIES:
                return category
        except Exception:
            logger.debug("API categorization failed", exc_info=True)

        return None
```

**Step 5: Run tests**

Run: `uv run pytest tests/v3/processing/test_categorize.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/mind/v3/processing tests/v3/processing
git commit -m "feat(v3): add EventCategorizer with API escalation"
```

---

## Task 7: Session End Synthesizer

**Files:**
- Create: `src/mind/v3/synthesis/__init__.py`
- Create: `src/mind/v3/synthesis/session_end.py`
- Create: `tests/v3/synthesis/__init__.py`
- Create: `tests/v3/synthesis/test_session_end.py`

**Step 1: Write tests**

Create `tests/v3/synthesis/__init__.py`:
```python
"""Synthesis module tests."""
```

Create `tests/v3/synthesis/test_session_end.py`:
```python
"""Tests for session end synthesizer."""
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from mind.v3.synthesis.session_end import SessionEndSynthesizer, SessionSummary
from mind.v3.capture.store import SessionEventStore
from mind.v3.capture.events import PromptEvent
from mind.v3.api.client import ClaudeClient, ClaudeConfig


class TestSessionSummary:
    """Test SessionSummary dataclass."""

    def test_create_summary(self):
        """Can create session summary."""
        summary = SessionSummary(
            session_id="20251226_120000",
            summary="Fixed auth bug and added tests",
            decisions=["chose JWT over sessions"],
            learnings=["Redis needs connection pooling"],
            unresolved=["need to add rate limiting"],
        )
        assert len(summary.decisions) == 1
        assert "auth" in summary.summary


class TestSessionEndSynthesizer:
    """Test SessionEndSynthesizer."""

    @pytest.fixture
    def event_store(self, tmp_path):
        """Create event store with test events."""
        store = SessionEventStore(tmp_path)
        store.add(PromptEvent(
            timestamp=datetime.now(),
            content="Fix the login bug",
        ))
        store.add(PromptEvent(
            timestamp=datetime.now(),
            content="decided to use bcrypt for hashing",
        ))
        return store

    @pytest.fixture
    def mock_graph_store(self):
        """Create mock graph store."""
        store = Mock()
        store.get_recent_memories.return_value = []
        store.get_recent_decisions.return_value = []
        store.get_recent_entities.return_value = []
        store.find_similar_decision.return_value = None
        store.add_decision.return_value = None
        store.add_session_summary.return_value = None
        return store

    @pytest.mark.asyncio
    async def test_synthesize_disabled_client(self, event_store, mock_graph_store):
        """Returns None when client is disabled."""
        client = ClaudeClient(ClaudeConfig())  # No API key
        synthesizer = SessionEndSynthesizer()
        result = await synthesizer.synthesize(event_store, mock_graph_store, client)
        assert result is None

    @pytest.mark.asyncio
    async def test_synthesize_with_mock_api(self, event_store, mock_graph_store):
        """Synthesizes with mocked API."""
        config = ClaudeConfig(api_key="sk-test", intelligence_level="BALANCED")
        client = ClaudeClient(config)

        # Mock the API call
        mock_response = """
        Summary: Fixed authentication bug using bcrypt.
        Decisions: chose bcrypt for password hashing
        Learnings: bcrypt is CPU-intensive
        Unresolved: none
        """
        client.call_sonnet = AsyncMock(return_value=mock_response)

        synthesizer = SessionEndSynthesizer()
        result = await synthesizer.synthesize(event_store, mock_graph_store, client)

        assert result is not None
        assert "bcrypt" in result.summary or "authentication" in result.summary

    def test_build_context(self, event_store, mock_graph_store):
        """Context includes events and recent data."""
        synthesizer = SessionEndSynthesizer()
        context = synthesizer._build_context(event_store, mock_graph_store)

        assert context is not None
        assert len(context.events) == 2
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/v3/synthesis/test_session_end.py -v`
Expected: ModuleNotFoundError

**Step 3: Create synthesis module**

Create `src/mind/v3/synthesis/__init__.py`:
```python
"""
Session synthesis for Mind v3.

AI-powered synthesis at session end:
- Generate session summaries
- Double-confirm decisions
- Extract cross-session patterns
"""
from .session_end import SessionEndSynthesizer, SessionSummary

__all__ = ["SessionEndSynthesizer", "SessionSummary"]
```

**Step 4: Implement SessionEndSynthesizer**

Create `src/mind/v3/synthesis/session_end.py`:
```python
"""
Session end synthesizer for Mind v3.

Uses AI to analyze session events and extract:
- Session summary
- Key decisions
- Important learnings
- Unresolved items
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..api.client import ClaudeClient
    from ..capture.store import SessionEventStore
    from ..graph.store import GraphStore

logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    """Context for AI synthesis."""
    events: list[Any]
    memories_added: list[dict]
    decisions_made: list[dict]
    entities_touched: list[dict]


@dataclass
class SessionSummary:
    """Result of session synthesis."""
    session_id: str
    summary: str
    decisions: list[str] = field(default_factory=list)
    learnings: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class SessionEndSynthesizer:
    """
    AI synthesis at session end.

    Reviews all captured and processed data to generate
    a comprehensive session summary with double-confirmation.
    """

    SYSTEM_PROMPT = """You are analyzing a coding session transcript.
Extract the following in a structured format:

Summary: A 2-3 sentence summary of what was accomplished.
Decisions: Key technical decisions made (one per line, prefixed with "- ")
Learnings: Important discoveries or gotchas (one per line, prefixed with "- ")
Unresolved: Problems or blockers not yet resolved (one per line, prefixed with "- ")

Be specific and actionable. Focus on what matters for future sessions.
Skip routine operations like reading files or running commands."""

    OPUS_SYSTEM = """You are a senior software architect analyzing a coding session.
Provide deep analysis of:

Summary: A thorough 3-4 sentence summary of the session's accomplishments and context.
Decisions: Key technical decisions with their reasoning (one per line, prefixed with "- ")
Learnings: Important discoveries, gotchas, and insights (one per line, prefixed with "- ")
Patterns: Recurring themes or approaches observed (one per line, prefixed with "- ")
Unresolved: Outstanding issues requiring attention (one per line, prefixed with "- ")

Be thorough but concise. Focus on architectural implications and knowledge worth preserving."""

    async def synthesize(
        self,
        event_store: "SessionEventStore",
        graph_store: "GraphStore",
        client: "ClaudeClient",
    ) -> SessionSummary | None:
        """
        Generate session synthesis.

        Args:
            event_store: Store with session events
            graph_store: Graph store for persistence
            client: API client

        Returns:
            SessionSummary or None if disabled
        """
        if not client.enabled:
            return None

        # Build context
        context = self._build_context(event_store, graph_store)

        # Format prompt
        prompt = self._format_prompt(context)

        # Choose model based on intelligence level
        if client.config.intelligence_level == "ULTRA":
            response = await client.call_opus(prompt, system=self.OPUS_SYSTEM)
        else:
            response = await client.call_sonnet(prompt, system=self.SYSTEM_PROMPT)

        if not response:
            return None

        # Parse response
        summary = self._parse_response(response, event_store.session_id)

        # Double-confirm decisions
        await self._confirm_decisions(summary, graph_store)

        # Store summary
        try:
            graph_store.add_session_summary({
                "session_id": summary.session_id,
                "summary": summary.summary,
                "decisions": summary.decisions,
                "learnings": summary.learnings,
                "unresolved": summary.unresolved,
                "timestamp": summary.timestamp.isoformat(),
            })
        except Exception:
            logger.debug("Failed to store session summary", exc_info=True)

        return summary

    def _build_context(
        self,
        event_store: "SessionEventStore",
        graph_store: "GraphStore",
    ) -> SessionContext:
        """Build context for AI synthesis."""
        # Get recent graph data
        try:
            memories = graph_store.get_recent_memories(hours=2)
        except Exception:
            memories = []

        try:
            decisions = graph_store.get_recent_decisions(hours=2)
        except Exception:
            decisions = []

        try:
            entities = graph_store.get_recent_entities(hours=2)
        except Exception:
            entities = []

        return SessionContext(
            events=event_store.events,
            memories_added=memories,
            decisions_made=decisions,
            entities_touched=entities,
        )

    def _format_prompt(self, context: SessionContext) -> str:
        """Format context into prompt."""
        lines = ["# Session Transcript\n"]

        # Add events
        for event in context.events:
            if hasattr(event, "content") and event.content:
                lines.append(f"- {event.content[:200]}")
            elif hasattr(event, "tool_name"):
                lines.append(f"- [Tool: {event.tool_name}]")

        # Add already-extracted data
        if context.decisions_made:
            lines.append("\n# Decisions Already Recorded")
            for d in context.decisions_made[:5]:
                lines.append(f"- {d.get('action', '')[:100]}")

        if context.memories_added:
            lines.append("\n# Memories Added This Session")
            for m in context.memories_added[:5]:
                lines.append(f"- {m.get('content', '')[:100]}")

        return "\n".join(lines)

    def _parse_response(self, response: str, session_id: str) -> SessionSummary:
        """Parse AI response into SessionSummary."""
        summary = ""
        decisions = []
        learnings = []
        unresolved = []

        current_section = None
        for line in response.split("\n"):
            line = line.strip()

            if line.lower().startswith("summary:"):
                current_section = "summary"
                summary = line[8:].strip()
            elif line.lower().startswith("decisions:"):
                current_section = "decisions"
            elif line.lower().startswith("learnings:"):
                current_section = "learnings"
            elif line.lower().startswith("unresolved:"):
                current_section = "unresolved"
            elif line.lower().startswith("patterns:"):
                current_section = "learnings"  # Merge patterns into learnings
            elif line.startswith("- "):
                item = line[2:].strip()
                if current_section == "decisions":
                    decisions.append(item)
                elif current_section == "learnings":
                    learnings.append(item)
                elif current_section == "unresolved":
                    unresolved.append(item)
            elif current_section == "summary" and line:
                summary += " " + line

        return SessionSummary(
            session_id=session_id,
            summary=summary.strip(),
            decisions=decisions,
            learnings=learnings,
            unresolved=unresolved,
        )

    async def _confirm_decisions(
        self,
        summary: SessionSummary,
        graph_store: "GraphStore",
    ) -> None:
        """Double-confirm decisions from summary."""
        for decision_text in summary.decisions:
            try:
                # Check if similar decision exists
                existing = graph_store.find_similar_decision(decision_text)
                if existing:
                    # Increment confirmation count
                    existing["confirmed"] = True
                    existing["confirmation_count"] = existing.get("confirmation_count", 0) + 1
                    graph_store.update_decision(existing)
                else:
                    # Add as new decision
                    graph_store.add_decision({
                        "action": decision_text,
                        "reasoning": f"Extracted from session {summary.session_id}",
                        "alternatives": [],
                        "confidence": 0.8,
                    })
            except Exception:
                logger.debug(f"Failed to confirm decision: {decision_text}", exc_info=True)
```

**Step 5: Run tests**

Run: `uv run pytest tests/v3/synthesis/test_session_end.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/mind/v3/synthesis tests/v3/synthesis
git commit -m "feat(v3): add SessionEndSynthesizer for AI session summaries"
```

---

## Task 8: Update Bridge Integration

**Files:**
- Modify: `src/mind/v3/bridge.py`
- Modify: `tests/v3/test_bridge.py`

**Step 1: Write tests for new bridge methods**

Add to `tests/v3/test_bridge.py`:
```python
class TestV3BridgeAPI:
    """Test API integration in V3Bridge."""

    def test_api_client_initialized(self, tmp_path):
        """Bridge initializes API client from config."""
        bridge = V3Bridge(tmp_path)
        assert hasattr(bridge, "_api_client")

    def test_event_store_initialized(self, tmp_path):
        """Bridge initializes event store."""
        bridge = V3Bridge(tmp_path)
        assert hasattr(bridge, "_event_store")

    def test_get_stats_includes_api(self, tmp_path):
        """Stats include API status."""
        bridge = V3Bridge(tmp_path)
        stats = bridge.get_stats()
        assert "api_enabled" in stats

    @pytest.mark.asyncio
    async def test_finalize_session_no_api(self, tmp_path):
        """Finalize without API returns None."""
        bridge = V3Bridge(tmp_path)
        result = await bridge.finalize_session_async()
        assert result is None
```

**Step 2: Run tests to verify some fail**

Run: `uv run pytest tests/v3/test_bridge.py::TestV3BridgeAPI -v`
Expected: Some tests fail (new methods don't exist)

**Step 3: Update bridge.py**

Add imports at top of `src/mind/v3/bridge.py`:
```python
from .api.client import ClaudeClient, ClaudeConfig
from .capture.store import SessionEventStore
from .synthesis.session_end import SessionEndSynthesizer, SessionSummary
```

In V3Bridge.__init__, add after `self._autonomy = AutonomyTracker()`:
```python
        # Initialize API client
        self._api_client = ClaudeClient(ClaudeConfig.from_env())

        # Initialize event store
        self._event_store = SessionEventStore(project_path)
```

Add new method to V3Bridge:
```python
    async def finalize_session_async(self) -> SessionSummary | None:
        """
        Finalize session with AI synthesis.

        Returns:
            SessionSummary or None if API disabled
        """
        if not self._api_client.enabled or not self._graph_store:
            return None

        try:
            synthesizer = SessionEndSynthesizer()
            return await synthesizer.synthesize(
                self._event_store,
                self._graph_store,
                self._api_client,
            )
        except Exception:
            logger.debug("Session synthesis failed", exc_info=True)
            return None
```

Update get_stats to include API:
```python
        stats["api_enabled"] = self._api_client.enabled if self._api_client else False
```

**Step 4: Run tests**

Run: `uv run pytest tests/v3/test_bridge.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/mind/v3/bridge.py tests/v3/test_bridge.py
git commit -m "feat(v3): integrate API client and synthesis into bridge"
```

---

## Task 9: Update mind init with Intelligence Level Prompt

**Files:**
- Modify: `src/mind/cli.py`

**Step 1: Add intelligence level selection to init**

In `src/mind/cli.py`, add after the existing preferences prompts (around line 150):

```python
    # Ask about intelligence level (new feature)
    click.echo()
    click.echo("Enhanced Intelligence (optional)")
    click.echo("─" * 35)
    click.echo("Mind can use Claude API for smarter context")
    click.echo("extraction, session summaries, and memory.")
    click.echo()
    click.echo("Choose your intelligence level:")
    click.echo()
    click.echo("  1. FREE      - Local only, no API ($0/mo)")
    click.echo("  2. LITE      - + Haiku escalation (~$2/mo)")
    click.echo("  3. BALANCED  - + Haiku + Sonnet summaries (~$15/mo)")
    click.echo("  4. PRO       - + Full Haiku + Sonnet (~$40/mo)")
    click.echo("  5. ULTRA     - + Opus for deep synthesis (~$150/mo)")
    click.echo()

    level_choice = click.prompt(
        "Enter number",
        type=click.Choice(["1", "2", "3", "4", "5"]),
        default="1",
    )
    level_map = {"1": "FREE", "2": "LITE", "3": "BALANCED", "4": "PRO", "5": "ULTRA"}
    intelligence_level = level_map[level_choice]

    # If non-FREE, prompt for API key
    api_key = None
    if intelligence_level != "FREE":
        import os
        existing_key = os.getenv("ANTHROPIC_API_KEY")
        if existing_key:
            click.echo(f"Found ANTHROPIC_API_KEY in environment.")
            use_existing = click.confirm("Use this key?", default=True)
            if not use_existing:
                api_key = click.prompt("Enter ANTHROPIC_API_KEY", hide_input=True)
        else:
            api_key = click.prompt(
                "Enter ANTHROPIC_API_KEY (or press Enter to set later)",
                default="",
                hide_input=True,
            )

    # Save to config
    config = load_config(mind_dir)
    config["v3"] = config.get("v3", {})
    config["v3"]["intelligence_level"] = intelligence_level
    if api_key:
        config["v3"]["api_key"] = api_key
    save_config(config, mind_dir)
```

**Step 2: Test manually**

Run: `uv run mind init --help`
Verify help text shows correctly.

**Step 3: Commit**

```bash
git add src/mind/cli.py
git commit -m "feat(cli): add intelligence level selection to mind init"
```

---

## Task 10: Run Full Test Suite and Version Bump

**Step 1: Run all tests**

Run: `uv run pytest tests/ -v --tb=short`
Expected: All tests PASS

**Step 2: Update pyproject.toml version**

Edit `pyproject.toml`:
```toml
version = "3.2.0"
```

**Step 3: Update CHANGELOG or README if needed**

**Step 4: Commit version bump**

```bash
git add pyproject.toml
git commit -m "chore: bump version to 3.2.0 for API intelligence layer"
```

---

## Summary

This plan implements the API Intelligence Layer in 10 tasks:

1. **API Client** - ClaudeClient with Haiku/Sonnet/Opus methods
2. **Intelligence Levels** - FREE through ULTRA configuration
3. **V3Settings Integration** - Add API config to settings
4. **Enhanced Events** - PromptEvent, ToolCallEvent, etc.
5. **Session Event Store** - Capture and persist events
6. **Event Categorizer** - Local + API categorization
7. **Session Synthesizer** - AI-powered session summaries
8. **Bridge Integration** - Wire up all components
9. **CLI Init Update** - Intelligence level selection
10. **Test and Version** - Full test suite, version bump

Each task follows TDD with bite-sized steps.

---

Plan complete and saved to `docs/plans/2025-12-26-api-intelligence-implementation.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
