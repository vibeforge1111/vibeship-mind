# Mind MCP Tools

## Overview

Mind has **4 MCP tools**. Most functionality is automatic via the daemon; tools are for explicit queries.

---

## Tool: mind_search

### Purpose

Semantic search across memories when CLAUDE.md context isn't enough.

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
        types: Filter by type - "decision", "issue", "learning", "edge"
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
    type: str              # decision, issue, learning, edge
    title: str
    content: str
    reasoning: Optional[str]
    project: str           # Project name
    source_file: str       # MEMORY.md or code file
    source_line: int
    confidence: float      # Extraction confidence 0-1
    relevance: float       # Search relevance 0-1
    date: datetime
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
    source: Literal["global", "project", "stack"]
    matched_on: str        # What triggered this match
    confidence: float      # How confident the match is
```

### Example Usage

```python
# Before implementing crypto
warnings = mind_edges("implementing token generation with crypto")
# Returns: Vercel Edge crypto limitation

# With code snippet
warnings = mind_edges(
    intent="auth middleware",
    code="import crypto from 'crypto'"
)

# Override stack detection
warnings = mind_edges("database queries", stack=["supabase", "edge"])
```

### Detection Patterns

Edges have detection patterns for:

```python
class EdgePatterns(BaseModel):
    context: list[str]    # Project context keywords
    intent: list[str]     # Intent keywords
    code: list[str]       # Regex patterns for code
```

Example:
```json
{
    "title": "Vercel Edge crypto limitation",
    "detection": {
        "context": ["vercel", "edge", "middleware"],
        "intent": ["crypto", "uuid", "random", "token"],
        "code": ["import.*crypto", "require.*crypto"]
    }
}
```

### When to Use

- Before implementing security-sensitive code
- When working with platform-specific features
- Starting work on area with known issues
- Proactively avoiding past mistakes

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

### Response Schema

```python
class Edge(BaseModel):
    id: str
    title: str
    description: str
    workaround: str
    detection: EdgePatterns
    stack_tags: list[str]
    severity: str
    created_at: datetime
    verified_count: int = 0
```

### Example Usage

```python
# Add a new global edge
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

Check Mind daemon status and project statistics.

### Signature

```python
@tool
def mind_status() -> Status:
    """
    Check Mind health and stats.
    
    Returns:
        Status with daemon info and project stats
    """
```

### Response Schema

```python
class Status(BaseModel):
    daemon: DaemonStatus
    current_project: Optional[ProjectStatus]
    global_stats: GlobalStats

class DaemonStatus(BaseModel):
    running: bool
    pid: Optional[int]
    uptime_seconds: Optional[int]
    projects_watching: int
    last_index: Optional[datetime]

class ProjectStatus(BaseModel):
    path: str
    name: str
    stack: list[str]
    memory_health: str           # "good", "stale", "empty"
    last_activity: datetime
    stats: ProjectStats

class ProjectStats(BaseModel):
    decisions: int
    issues_open: int
    issues_resolved: int
    learnings: int
    edges: int
    sessions_inferred: int

class GlobalStats(BaseModel):
    projects_registered: int
    global_edges: int
    total_memories: int
```

### Example Usage

```python
status = mind_status()

if not status.daemon.running:
    print("Mind daemon not running. Start with: mind daemon start")

if status.current_project:
    print(f"Memory health: {status.current_project.memory_health}")
```

### When to Use

- Debugging memory issues
- Checking if daemon is running
- Getting project statistics
- Health checks

---

## Tool Usage Guidelines

### When CLAUDE.md Context is Enough

Don't call tools when MIND:CONTEXT has what you need:

```markdown
<!-- MIND:CONTEXT -->
## Recent Decisions
- Use JWT for auth (Dec 10)
```

If you see a relevant decision, don't call `mind_search("auth")`.

### When to Use Tools

| Situation | Tool |
|-----------|------|
| Need details not in MIND:CONTEXT | `mind_search` |
| About to implement risky code | `mind_edges` |
| Found a platform gotcha | `mind_add_global_edge` |
| Something seems wrong | `mind_status` |

### Tool Call Frequency

Expected frequency per session:

| Tool | Typical Usage |
|------|---------------|
| `mind_search` | 0-3 calls |
| `mind_edges` | 0-2 calls |
| `mind_add_global_edge` | 0-1 calls |
| `mind_status` | 0-1 calls |

Most sessions: **0-2 tool calls total**. Everything else is automatic.

---

## Error Handling

### Common Errors

```python
class MindError(Exception):
    code: str
    message: str
    details: Optional[dict]

# Error codes:
# DAEMON_NOT_RUNNING - Daemon needs to be started
# PROJECT_NOT_REGISTERED - Run `mind init` first
# INDEX_NOT_READY - Wait for initial indexing
# SEARCH_FAILED - Embedding/search error
# EDGE_EXISTS - Duplicate edge
```

### Graceful Degradation

If daemon isn't running:
- `mind_search` → Returns empty, suggests starting daemon
- `mind_edges` → Returns global edges only (from file)
- `mind_status` → Shows daemon not running
- Context injection → Doesn't happen (stale MIND:CONTEXT)

---

## MCP Configuration

### Claude Code Config

```json
{
  "mcpServers": {
    "mind": {
      "command": "uv",
      "args": ["--directory", "/path/to/mind", "run", "mind", "mcp"],
      "env": {}
    }
  }
}
```

### Tool Definitions (for MCP)

```json
{
  "tools": [
    {
      "name": "mind_search",
      "description": "Semantic search across memories. Use when CLAUDE.md context isn't enough.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {"type": "string", "description": "Search query"},
          "scope": {"type": "string", "enum": ["project", "all"], "default": "project"},
          "types": {"type": "array", "items": {"type": "string"}},
          "limit": {"type": "integer", "default": 10}
        },
        "required": ["query"]
      }
    },
    {
      "name": "mind_edges",
      "description": "Check for gotchas before implementing risky code.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "intent": {"type": "string", "description": "What you're about to do"},
          "code": {"type": "string", "description": "Optional code to analyze"},
          "stack": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["intent"]
      }
    },
    {
      "name": "mind_add_global_edge",
      "description": "Add a cross-project gotcha.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "title": {"type": "string"},
          "description": {"type": "string"},
          "workaround": {"type": "string"},
          "detection": {"type": "object"},
          "stack_tags": {"type": "array", "items": {"type": "string"}},
          "severity": {"type": "string", "enum": ["info", "warning", "critical"]}
        },
        "required": ["title", "description", "workaround", "detection"]
      }
    },
    {
      "name": "mind_status",
      "description": "Check Mind daemon status and project stats.",
      "inputSchema": {
        "type": "object",
        "properties": {}
      }
    }
  ]
}
```
