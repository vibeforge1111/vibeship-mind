# Mind MCP Tools

## Overview

Mind has **10 MCP tools** for AI memory. The architecture is stateless (v2: daemon-free) - tools load and process on demand.

---

## Tool: mind_recall

### Purpose

**CALL THIS FIRST every session.** Loads fresh context, detects session gaps, and ensures you have the latest memory state.

### Why First?

- The MIND:CONTEXT in CLAUDE.md may be stale
- `mind_recall()` gets live data and detects session gaps
- If gap detected (>30 min), promotes learnings from SESSION.md to MEMORY.md and starts fresh session

### Signature

```python
@tool
def mind_recall(
    project_path: Optional[str] = None,
    force_refresh: bool = False
) -> RecallResult:
    """
    Load session context. ALWAYS call this first.

    Args:
        project_path: Project path (defaults to cwd)
        force_refresh: Force regenerate context even if no changes

    Returns:
        RecallResult with context, session state, and health info
    """
```

### Response Schema

```python
class RecallResult(BaseModel):
    context: str                    # MIND:CONTEXT markdown
    session: Optional[SessionState] # Current session state
    session_info: SessionInfo       # Gap detection, promotions
    health: HealthInfo              # File size, suggestions

class SessionState(BaseModel):
    goal: list[str]
    current_approach: list[str]
    blockers: list[str]
    rejected_approaches: list[str]
    working_assumptions: list[str]
    discoveries: list[str]

class SessionInfo(BaseModel):
    last_session: Optional[str]     # ISO timestamp
    gap_detected: bool              # True if >30 min gap
    new_session_started: bool       # True if SESSION.md was cleared
    promoted_to_memory: int         # Count of items promoted
    entries_processed: int          # Total entities parsed
    refreshed: bool                 # True if context regenerated
```

### When to Use

- **START of every session** - before responding to user
- When you need fresh context after being away
- After significant changes to MEMORY.md

---

## Tool: mind_session

### Purpose

Get current session state from SESSION.md. Use to check goal, approach, blockers, rejected approaches, assumptions, and discoveries.

### Signature

```python
@tool
def mind_session(
    project_path: Optional[str] = None
) -> SessionResult:
    """
    Get current session state from SESSION.md.

    Args:
        project_path: Project path (defaults to cwd)

    Returns:
        SessionResult with parsed session state and workflow hints
    """
```

### Response Schema

```python
class SessionResult(BaseModel):
    session: SessionState
    stats: SessionStats
    workflow: WorkflowHints

class SessionStats(BaseModel):
    total_items: int
    blockers_count: int
    discoveries_count: int

class WorkflowHints(BaseModel):
    stuck: str       # What to do when stuck
    before_proposing: str  # Check rejected approaches
    lost: str        # Check the goal
```

### When to Use

- When you feel lost or off-track
- Before proposing a new approach (check rejected approaches)
- To remind yourself of the current goal

---

## Tool: mind_blocker

### Purpose

Log a blocker and auto-search memory for solutions. Call this when stuck - it adds to SESSION.md Blockers and searches MEMORY.md for relevant past solutions.

### Signature

```python
@tool
def mind_blocker(
    description: str,
    keywords: Optional[list[str]] = None
) -> BlockerResult:
    """
    Log a blocker and auto-search memory for solutions.

    Args:
        description: What's blocking you
        keywords: Optional specific keywords to search for

    Returns:
        BlockerResult with logged status and memory search results
    """
```

### Response Schema

```python
class BlockerResult(BaseModel):
    blocker_logged: bool
    description: str
    keywords_searched: list[str]
    memory_search_results: list[SearchResult]
    suggestions: list[str]
```

### When to Use

- When you're stuck on something
- When hitting an error you've seen before
- When an approach isn't working

---

## Tool: mind_search

### Purpose

Semantic search across memories when CLAUDE.md context isn't enough. Searches both indexed and current session content.

### Signature

```python
@tool
def mind_search(
    query: str,
    scope: Literal["project", "all"] = "project",
    types: Optional[list[str]] = None,
    limit: int = 10
) -> SearchResults:
    """
    Search across memories.

    Args:
        query: Natural language search query
        scope: "project" (current) or "all" (all registered projects)
        types: Filter by type - "decision", "issue", "learning"
        limit: Max results to return

    Returns:
        SearchResults with matches, scores, and source locations
    """
```

### Response Schema

```python
class SearchResults(BaseModel):
    query: str
    total: int
    results: list[SearchResult]

class SearchResult(BaseModel):
    type: str              # decision, issue, learning, raw
    title: str
    content: str
    reasoning: Optional[str]
    project: str           # Project name
    source_file: str       # MEMORY.md or code file
    source_line: int
    confidence: float      # Extraction confidence 0-1
    relevance: float       # Search relevance 0-1
    date: datetime
    source: str            # "indexed" or "unparsed"
```

### Example Usage

```python
# Find past auth decisions
result = mind_search("authentication JWT OAuth")

# Search across all projects
result = mind_search("Safari cookies", scope="all")

# Only issues
result = mind_search("CORS", types=["issue"])
```

### When to Use

- CLAUDE.md context doesn't have what you need
- Looking for specific past decision
- Finding related issues across projects
- Deep dive into topic history

---

## Tool: mind_edges

### Purpose

Check for sharp edges (gotchas) before implementing something risky.

### Signature

```python
@tool
def mind_edges(
    intent: str,
    code: Optional[str] = None,
    stack: Optional[list[str]] = None
) -> list[EdgeWarning]:
    """
    Check for gotchas before coding.

    Combines:
    - Global edges (platform-wide gotchas)
    - Project edges (from MEMORY.md Gotchas section)
    - Stack-specific edges (auto-detected from project)

    Args:
        intent: What you're about to do ("implementing OAuth", "adding crypto")
        code: Optional code snippet to analyze for patterns
        stack: Override auto-detected stack (optional)

    Returns:
        List of relevant warnings
    """
```

### Response Schema

```python
class EdgeWarning(BaseModel):
    id: str
    title: str
    description: str
    workaround: str
    severity: Literal["info", "warning", "critical"]
    source: Literal["global", "project"]
    matched_on: str        # What triggered this match
    confidence: float      # How confident the match is
```

### Example Usage

```python
# Before implementing crypto
warnings = mind_edges("implementing token generation with crypto")

# With code snippet
warnings = mind_edges(
    intent="auth middleware",
    code="import crypto from 'crypto'"
)
```

### When to Use

- Before implementing security-sensitive code
- When working with platform-specific features
- Starting work on area with known issues
- Proactively avoiding past mistakes

---

## Tool: mind_checkpoint

### Purpose

Force process pending memories and regenerate context. Use when you want to ensure recent writes are indexed.

### Signature

```python
@tool
def mind_checkpoint(
    project_path: Optional[str] = None
) -> CheckpointResult:
    """
    Force process pending memories.

    Args:
        project_path: Project path (defaults to cwd)

    Returns:
        CheckpointResult with processing stats
    """
```

### Response Schema

```python
class CheckpointResult(BaseModel):
    processed: int
    context_updated: bool
    timestamp: str
```

### When to Use

- After writing several memories to MEMORY.md
- Before ending a session to ensure everything is captured
- When you want to verify recent writes are indexed

---

## Tool: mind_add_global_edge

### Purpose

Add a sharp edge that applies across ALL projects.

### Signature

```python
@tool
def mind_add_global_edge(
    title: str,
    description: str,
    workaround: str,
    detection: dict,
    stack_tags: Optional[list[str]] = None,
    severity: Literal["info", "warning", "critical"] = "warning"
) -> Edge:
    """
    Add a cross-project gotcha.

    Use for platform/language gotchas, not project-specific issues.
    Project-specific gotchas go in .mind/MEMORY.md Gotchas section.

    Args:
        title: Short title ("Vercel Edge crypto limitation")
        description: What the problem is
        workaround: How to fix/avoid it
        detection: Patterns to detect when edge applies
            {"context": [], "intent": [], "code": []}
        stack_tags: Tech this applies to (auto-matched to projects)
        severity: How critical this gotcha is

    Returns:
        Created edge with ID
    """
```

### Example Usage

```python
edge = mind_add_global_edge(
    title="Safari ITP blocks cross-domain cookies",
    description="Safari's Intelligent Tracking Prevention deletes third-party cookies after 7 days",
    workaround="Use same-domain auth or first-party cookies",
    detection={
        "context": ["safari", "ios", "webkit"],
        "intent": ["auth", "cookies", "session", "cross-domain"],
        "code": ["sameSite.*none", "credentials.*include"]
    },
    stack_tags=["safari", "auth", "cookies"],
    severity="warning"
)
```

### When to Use

- Discovered a platform limitation
- Found a language/framework gotcha
- Hit an issue others will likely hit
- NOT for project-specific problems

### Project-Specific vs Global

| Type | Where to Store | Example |
|------|----------------|---------|
| Global | `mind_add_global_edge` | Safari ITP, Vercel Edge limits |
| Project | MEMORY.md Gotchas section | "Our API rate limits to 100/min" |

---

## Tool: mind_status

### Purpose

Check Mind status and project statistics.

### Signature

```python
@tool
def mind_status() -> Status:
    """
    Check Mind health and stats.

    Returns:
        Status with project info and stats
    """
```

### Response Schema

```python
class Status(BaseModel):
    version: int                    # Schema version (2)
    current_project: Optional[ProjectStatus]
    global_stats: GlobalStats

class ProjectStatus(BaseModel):
    path: str
    name: str
    stack: list[str]
    last_activity: Optional[str]    # ISO timestamp
    stats: ProjectStats

class ProjectStats(BaseModel):
    decisions: int
    issues_open: int
    issues_resolved: int
    learnings: int

class GlobalStats(BaseModel):
    projects_registered: int
    global_edges: int
```

### When to Use

- Debugging memory issues
- Getting project statistics
- Health checks

---

## Tool: mind_remind

### Purpose

Set a reminder for later. Use for "remind me to...", "don't forget to...", etc. Supports "next session", "tomorrow", "in 3 days", specific dates.

### Signature

```python
@tool
def mind_remind(
    message: str,
    when: str
) -> RemindResult:
    """
    Set a reminder for later.

    Args:
        message: What to remind about
        when: When to remind - "next session", "tomorrow", "in 3 days", "2025-12-20", etc.

    Returns:
        RemindResult with confirmation and parsed due date
    """
```

### Response Schema

```python
class RemindResult(BaseModel):
    success: bool
    reminder: Reminder
    message: str              # Human-readable confirmation

class Reminder(BaseModel):
    message: str
    due: str                  # ISO date
    type: str                 # "next session" or "absolute"
```

### Supported "when" Formats

| Format | Example | Result |
|--------|---------|--------|
| Next session | "next session" | Fires on next mind_recall() |
| Tomorrow | "tomorrow" | Tomorrow's date |
| Relative days | "in 3 days" | Date + 3 days |
| Relative weeks | "in 2 weeks" | Date + 14 days |
| Relative hours | "in 4 hours" | DateTime + 4 hours |
| ISO date | "2025-12-20" | Exact date |
| Month day | "December 25" | Parsed date (next year if passed) |

### When to Use

- User says "remind me to..."
- User says "don't forget to..."
- Setting up follow-up work for later
- Planning Phase B of a feature

### Example Usage

```python
# Remind next session
mind_remind("Add context-matching to reminders", "next session")

# Remind in a few days
mind_remind("Review PR #42", "in 3 days")

# Remind on specific date
mind_remind("Prepare demo", "December 20")
```

---

## Tool: mind_reminders

### Purpose

List all pending reminders. Use to see what reminders are set.

### Signature

```python
@tool
def mind_reminders() -> RemindersResult:
    """
    List all pending reminders.

    Returns:
        RemindersResult with pending and done counts
    """
```

### Response Schema

```python
class RemindersResult(BaseModel):
    pending: list[Reminder]
    done_count: int
    total: int
```

### When to Use

- Check what reminders are set
- Review upcoming reminders
- Before setting a new reminder (avoid duplicates)

---

## Reminder Lifecycle

1. **Created** - `mind_remind("message", "when")` saves to .mind/REMINDERS.md
2. **Due** - `mind_recall()` checks for due reminders
3. **Surfaced** - Due reminders appear in MIND:CONTEXT under `## Reminders Due`
4. **User responds** - "work on it now" or "snooze"
5. **If work** - Mark done, promote to MEMORY.md
6. **If snooze** - Call `mind_remind()` again with new time

### Snooze Behavior

When a reminder is due, ask the user:

> "You have a reminder: **{message}**
>
> Want to work on this now, or should I remind you later? (You can say 'snooze', 'next session', 'in a week', etc.)"

- "snooze" with no time → next session (default)
- Explicit time → parse and set new reminder

---

## Tool Usage Guidelines

### Session Start Protocol

1. **ALWAYS call `mind_recall()` first** before responding to user
2. Check session state for goal, approach, blockers
3. Review MIND:CONTEXT for recent decisions and gotchas

### When to Use Each Tool

| Situation | Tool |
|-----------|------|
| **Session start** | `mind_recall()` - ALWAYS FIRST |
| Feeling lost or off-track | `mind_session()` |
| Stuck on something | `mind_blocker()` |
| Need details not in MIND:CONTEXT | `mind_search()` |
| About to implement risky code | `mind_edges()` |
| After writing several memories | `mind_checkpoint()` |
| Found a platform gotcha | `mind_add_global_edge()` |
| Something seems wrong | `mind_status()` |
| User says "remind me..." | `mind_remind()` |
| Check pending reminders | `mind_reminders()` |

### Tool Call Frequency

Expected frequency per session:

| Tool | Typical Usage |
|------|---------------|
| `mind_recall` | 1 call (at start) |
| `mind_session` | 0-2 calls |
| `mind_blocker` | 0-3 calls |
| `mind_search` | 0-3 calls |
| `mind_edges` | 0-2 calls |
| `mind_checkpoint` | 0-1 calls |
| `mind_add_global_edge` | 0-1 calls |
| `mind_status` | 0-1 calls |
| `mind_remind` | 0-2 calls |
| `mind_reminders` | 0-1 calls |

Most sessions: **1-5 tool calls total** (mind_recall + as needed).

---

## MCP Configuration

### Claude Code Config

```json
{
  "mcpServers": {
    "mind": {
      "command": "uv",
      "args": ["--directory", "/path/to/vibeship-mind", "run", "mind", "mcp"]
    }
  }
}
```
