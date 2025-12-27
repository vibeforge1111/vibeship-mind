# API Intelligence Layer Design

## Overview

Add Claude API integration to Mind v3 for enhanced context extraction, session summaries, and intelligent reranking. This implements Phase 8 (Intelligence Levels) from the original v3 plan plus new capabilities.

**Core Principle:** Local-first with optional API escalation based on user's chosen intelligence level.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Mind v3 + API Layer                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │ Active      │───>│ Background       │───>│ Session End   │  │
│  │ Capture     │    │ Processing       │    │ AI Synthesis  │  │
│  └─────────────┘    └──────────────────┘    └───────────────┘  │
│        │                    │                      │            │
│        v                    v                      v            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    ClaudeClient                             ││
│  │   call_haiku() │ call_sonnet() │ call_opus()                ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                  │
└──────────────────────────────│──────────────────────────────────┘
                               v
                    ┌─────────────────────┐
                    │   Anthropic API     │
                    └─────────────────────┘
```

## 1. API Client

### File: `src/mind/v3/api/client.py`

```python
@dataclass
class ClaudeConfig:
    """Configuration for Claude API."""
    api_key: str | None = None  # From ANTHROPIC_API_KEY env var
    intelligence_level: str = "FREE"  # FREE, LITE, BALANCED, PRO, ULTRA
    max_retries: int = 3
    timeout: float = 30.0


class ClaudeClient:
    """Unified client for Claude API calls."""

    MODELS = {
        "haiku": "claude-3-5-haiku-20241022",
        "sonnet": "claude-sonnet-4-20250514",
        "opus": "claude-opus-4-20250514",
    }

    def __init__(self, config: ClaudeConfig | None = None):
        self.config = config or ClaudeConfig()
        self._client: anthropic.Anthropic | None = None

    @property
    def enabled(self) -> bool:
        """Check if API is configured and enabled."""
        return (
            self.config.api_key is not None
            and self.config.intelligence_level != "FREE"
        )

    async def call_haiku(self, prompt: str, system: str = "") -> str:
        """Fast, cheap calls for extraction and simple reranking."""
        ...

    async def call_sonnet(self, prompt: str, system: str = "") -> str:
        """Balanced calls for summaries and complex extraction."""
        ...

    async def call_opus(self, prompt: str, system: str = "") -> str:
        """Deep reasoning for ULTRA-level synthesis."""
        ...
```

## 2. Active Capture Layer

Captures events in real-time throughout the session, not just at session end.

### File: `src/mind/v3/capture/events.py`

```python
@dataclass
class PromptEvent:
    """User prompt with context."""
    timestamp: datetime
    content: str
    context_items: list[str]  # What context was injected


@dataclass
class ToolCallEvent:
    """Tool invocation."""
    timestamp: datetime
    tool_name: str
    arguments: dict
    result_summary: str  # First 500 chars
    success: bool
    duration_ms: float


@dataclass
class FileChangeEvent:
    """File modification."""
    timestamp: datetime
    path: str
    change_type: str  # created, modified, deleted
    lines_changed: int


@dataclass
class ErrorEvent:
    """Error or failure."""
    timestamp: datetime
    error_type: str
    message: str
    context: str  # What was being attempted
```

### File: `src/mind/v3/capture/watcher.py`

```python
class TranscriptWatcher:
    """
    Watches Claude Code transcript for events.

    Parses JSONL from ~/.claude/projects/<hash>/sessions/<id>.jsonl
    """

    def __init__(self, project_path: Path, event_store: SessionEventStore):
        self.project_path = project_path
        self.event_store = event_store
        self._last_position: int = 0

    def poll(self) -> list[BaseEvent]:
        """
        Poll for new events since last check.
        Called periodically during session.
        """
        transcript = self._find_active_transcript()
        if not transcript:
            return []

        events = []
        with open(transcript) as f:
            f.seek(self._last_position)
            for line in f:
                event = self._parse_line(line)
                if event:
                    events.append(event)
                    self.event_store.add(event)
            self._last_position = f.tell()

        return events

    def _parse_line(self, line: str) -> BaseEvent | None:
        """Parse JSONL line into typed event."""
        data = json.loads(line)

        if data.get("type") == "user":
            return PromptEvent(...)
        elif data.get("type") == "tool_use":
            return ToolCallEvent(...)
        # ... etc
```

### File: `src/mind/v3/capture/store.py`

```python
class SessionEventStore:
    """
    In-memory store for session events.

    Persists to .mind/v3/sessions/<date>/<session_id>.json
    """

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.events: list[BaseEvent] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def add(self, event: BaseEvent) -> None:
        """Add event to store."""
        self.events.append(event)
        # Trigger background processing if queue threshold reached
        if len(self.events) % 10 == 0:
            self._trigger_processing()

    def get_events_since(self, timestamp: datetime) -> list[BaseEvent]:
        """Get events after timestamp."""
        return [e for e in self.events if e.timestamp > timestamp]

    def persist(self) -> None:
        """Save session to disk."""
        ...
```

## 3. Background Processing Layer

Processes captured events into structured data for LanceDB storage.

### File: `src/mind/v3/processing/queue.py`

```python
class ProcessingQueue:
    """
    Background queue for event processing.

    Batches events and processes them asynchronously
    to avoid blocking the session.
    """

    def __init__(self, graph_store: GraphStore, client: ClaudeClient):
        self.graph_store = graph_store
        self.client = client
        self._queue: list[BaseEvent] = []
        self._processing = False

    async def enqueue(self, events: list[BaseEvent]) -> None:
        """Add events to processing queue."""
        self._queue.extend(events)
        if not self._processing and len(self._queue) >= 5:
            await self._process_batch()

    async def _process_batch(self) -> None:
        """Process queued events."""
        self._processing = True
        batch = self._queue[:10]
        self._queue = self._queue[10:]

        # Pipeline: Categorize → Extract → Link → Store
        categorized = await self._categorizer.categorize(batch)
        structured = await self._extractor.extract(categorized)
        linked = await self._linker.link(structured)
        await self._store(linked)

        self._processing = False
```

### File: `src/mind/v3/processing/categorize.py`

```python
class EventCategorizer:
    """
    Categorizes raw events into types.

    Uses local heuristics first, escalates to Haiku
    when confidence is low.
    """

    CATEGORIES = [
        "decision",      # Choice made between alternatives
        "learning",      # New knowledge gained
        "problem",       # Issue encountered
        "progress",      # Work completed
        "exploration",   # Code reading/understanding
        "routine",       # Standard operations (ignore)
    ]

    async def categorize(
        self,
        events: list[BaseEvent],
        client: ClaudeClient | None = None,
    ) -> list[CategorizedEvent]:
        """
        Categorize events.

        Returns events with category and confidence.
        Low-confidence events get API escalation if enabled.
        """
        results = []
        for event in events:
            category, confidence = self._local_categorize(event)

            if confidence < 0.6 and client and client.enabled:
                # Escalate to Haiku for uncertain cases
                category = await self._api_categorize(event, client)
                confidence = 0.9

            if category != "routine":
                results.append(CategorizedEvent(
                    event=event,
                    category=category,
                    confidence=confidence,
                ))

        return results
```

### File: `src/mind/v3/processing/extract.py`

```python
class StructuredExtractor:
    """
    Extracts structured data from categorized events.

    Decisions → decisions table
    Learnings → memories table
    Problems → memories + entities
    Progress → outcomes table
    """

    async def extract(
        self,
        events: list[CategorizedEvent],
        client: ClaudeClient | None = None,
    ) -> list[StructuredData]:
        """Extract structured data based on category."""
        results = []

        for event in events:
            if event.category == "decision":
                data = await self._extract_decision(event, client)
            elif event.category == "learning":
                data = await self._extract_learning(event, client)
            elif event.category == "problem":
                data = await self._extract_problem(event, client)
            elif event.category == "progress":
                data = await self._extract_outcome(event, client)
            else:
                continue

            results.append(data)

        return results
```

### File: `src/mind/v3/processing/link.py`

```python
class GraphLinker:
    """
    Links extracted data to existing graph nodes.

    Finds relationships:
    - Decisions that affect entities
    - Learnings about patterns
    - Problems related to past decisions
    """

    async def link(
        self,
        data: list[StructuredData],
        graph_store: GraphStore,
    ) -> list[LinkedData]:
        """Find and create graph relationships."""
        results = []

        for item in data:
            # Find related entities
            related_entities = await self._find_related_entities(
                item, graph_store
            )

            # Find related decisions
            related_decisions = await self._find_related_decisions(
                item, graph_store
            )

            # Create edges
            for entity in related_entities:
                graph_store.add_edge(item.id, entity.id, "relates_to")

            for decision in related_decisions:
                graph_store.add_edge(item.id, decision.id, "influenced_by")

            results.append(LinkedData(item, related_entities, related_decisions))

        return results
```

### File: `src/mind/v3/processing/consolidate.py`

```python
class MemoryConsolidator:
    """
    Consolidates redundant memories.

    Runs periodically to:
    - Merge similar memories
    - Update confidence scores
    - Apply decay to stale items
    """

    async def consolidate(
        self,
        graph_store: GraphStore,
        client: ClaudeClient | None = None,
    ) -> ConsolidationResult:
        """Run consolidation pass."""
        # Find similar memories
        clusters = await self._find_clusters(graph_store)

        merged = 0
        for cluster in clusters:
            if len(cluster) > 1:
                # Merge into single memory
                if client and client.enabled:
                    merged_text = await self._ai_merge(cluster, client)
                else:
                    merged_text = self._local_merge(cluster)

                # Keep highest-confidence, delete others
                primary = max(cluster, key=lambda m: m.confidence)
                primary.content = merged_text
                graph_store.update_memory(primary)

                for memory in cluster:
                    if memory.id != primary.id:
                        graph_store.delete_memory(memory.id)
                        merged += 1

        return ConsolidationResult(merged=merged)
```

## 4. Session End AI Synthesis

At session end, AI reviews all processed data for a second pass.

### File: `src/mind/v3/synthesis/session_end.py`

```python
class SessionEndSynthesizer:
    """
    AI synthesis at session end.

    Reviews all captured and processed data to:
    - Generate session summary
    - Double-confirm decisions (second pass)
    - Extract patterns across the session
    - Identify unresolved items
    """

    SONNET_SYSTEM = """You are analyzing a coding session.
    Extract:
    1. Key decisions made and their reasoning
    2. Important learnings/discoveries
    3. Patterns that emerged
    4. Unresolved problems or blockers
    5. A 2-3 sentence summary of what was accomplished

    Be specific and actionable. Skip routine operations."""

    async def synthesize(
        self,
        event_store: SessionEventStore,
        graph_store: GraphStore,
        client: ClaudeClient,
    ) -> SessionSummary:
        """Generate session synthesis."""

        # Build context from session
        context = self._build_context(event_store, graph_store)

        # Choose model based on intelligence level
        if client.config.intelligence_level == "ULTRA":
            response = await client.call_opus(
                prompt=self._format_prompt(context),
                system=self.OPUS_SYSTEM,  # More thorough prompt for Opus
            )
        else:
            response = await client.call_sonnet(
                prompt=self._format_prompt(context),
                system=self.SONNET_SYSTEM,
            )

        # Parse response
        summary = self._parse_response(response)

        # Double-confirm decisions
        for decision in summary.decisions:
            existing = graph_store.find_similar_decision(decision)
            if existing:
                existing.confirmed = True
                existing.confirmation_count += 1
                graph_store.update_decision(existing)
            else:
                graph_store.add_decision(decision)

        # Store session summary
        graph_store.add_session_summary(summary)

        return summary

    def _build_context(
        self,
        event_store: SessionEventStore,
        graph_store: GraphStore,
    ) -> SessionContext:
        """Build context for AI synthesis."""
        return SessionContext(
            events=event_store.events,
            memories_added=graph_store.get_recent_memories(hours=2),
            decisions_made=graph_store.get_recent_decisions(hours=2),
            entities_touched=graph_store.get_recent_entities(hours=2),
        )
```

## 5. Intelligence Levels

### File: `src/mind/v3/api/levels.py`

```python
@dataclass
class IntelligenceLevel:
    """Configuration for an intelligence level."""
    name: str
    description: str
    extraction_model: str | None  # None = local only
    reranking_model: str | None
    summary_model: str | None
    estimated_cost: str


LEVELS = {
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
```

## 6. Setup Flow

### Updated `mind init`

```
$ mind init

  Mind v3 Setup

  Creating .mind/ directory... done

  Enhanced Intelligence (optional)
  ───────────────────────────────
  Mind can use Claude API for smarter context extraction,
  session summaries, and memory consolidation.

  Choose your intelligence level:

  > FREE      │ Local only, no API ($0/mo)
    LITE      │ + Haiku escalation (~$2/mo)
    BALANCED  │ + Haiku + Sonnet summaries (~$15/mo)
    PRO       │ + Full Haiku + Sonnet (~$40/mo)
    ULTRA     │ + Opus for deep synthesis (~$150/mo)

  (Use arrow keys, Enter to select)

  [If non-FREE selected:]
  Enter ANTHROPIC_API_KEY (or press Enter to set later):
  > sk-ant-...

  Configuration saved to .mind/config.toml
```

### Config File: `.mind/config.toml`

```toml
[v3]
intelligence_level = "BALANCED"

[v3.api]
# API key from ANTHROPIC_API_KEY env var or stored here
# api_key = "sk-ant-..."  # Not recommended to store in file

[v3.capture]
poll_interval_seconds = 5
batch_size = 10

[v3.processing]
consolidation_interval_hours = 24
decay_half_life_hours = 168  # 7 days
```

## 7. Integration Points

### Updated `bridge.py`

```python
class V3Bridge:
    def __init__(self, project_path: Path, config: V3Config | None = None):
        # ... existing init ...

        # Initialize API client
        self._api_client = ClaudeClient(self._load_api_config())

        # Initialize capture layer
        self._event_store = SessionEventStore(project_path)
        self._transcript_watcher = TranscriptWatcher(
            project_path, self._event_store
        )

        # Initialize background processing
        self._processing_queue = ProcessingQueue(
            self._graph_store, self._api_client
        )

        # Start polling if API enabled
        if self._api_client.enabled:
            self._start_capture_polling()

    def _start_capture_polling(self) -> None:
        """Start background polling for events."""
        # Poll every 5 seconds
        # Implementation depends on async strategy
        ...

    async def finalize_session(self) -> SessionSummary | None:
        """Finalize session with AI synthesis."""
        if self._api_client.enabled:
            synthesizer = SessionEndSynthesizer()
            return await synthesizer.synthesize(
                self._event_store,
                self._graph_store,
                self._api_client,
            )
        return None
```

## Implementation Order

1. **Phase 1: API Client** - ClaudeClient with Haiku/Sonnet/Opus
2. **Phase 2: Intelligence Config** - Levels, setup flow, config.toml
3. **Phase 3: Active Capture** - Event types, TranscriptWatcher, SessionEventStore
4. **Phase 4: Background Processing** - Queue, Categorizer, Extractor, Linker
5. **Phase 5: Session Synthesis** - SessionEndSynthesizer with double-confirm
6. **Phase 6: Consolidation** - MemoryConsolidator, decay integration

## Testing Strategy

- Unit tests for each component with mocked API
- Integration tests with real API (optional, requires key)
- Cost tracking tests to verify model selection
- Session simulation tests for full pipeline
