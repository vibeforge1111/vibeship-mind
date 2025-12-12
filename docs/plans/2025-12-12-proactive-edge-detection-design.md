# Proactive Edge Detection Design

## Overview

Make edge detection automatic by embedding it in existing MCP tools at decision points, not file writes.

## Core Insight

Detection matters at the **decision moment** - when thinking about an approach - not when writing code. By the time code is being written, the mistake already happened in thinking.

## Integration Points

| Tool | What to Check | Why |
|------|---------------|-----|
| `mind_start_session` | Stack + current goal | Surface relevant edges immediately |
| `mind_get_context` | Query intent + code in query | The decision moment |
| `mind_add_decision` | Reasoning text | Catch edges in thinking |
| `mind_add_issue` | Symptoms | Connect issues to known gotchas |

## Throttling

Per-edge-per-session, not time-based:

```python
class EdgeDetector:
    def __init__(self):
        self.warned_this_session: set[str] = set()
```

- Same edge won't warn twice in one session
- Resets when new session starts
- Acknowledged edges don't repeat

## Warning Schema

```python
class EdgeWarning(BaseModel):
    edge_id: str
    title: str
    severity: Literal["info", "medium", "high"]
    matched: str  # What triggered this warning
    workaround: str  # Quick solution

    # Optional
    symptoms: list[str] = []
    link: Optional[str] = None
```

## Response Format

Warnings inline in each tool's response:

```python
# mind_start_session
{
  "session_id": "sess_01HX...",
  "project": {...},
  "primer": "...",
  "warnings": [
    {
      "edge_id": "edge_abc",
      "title": "Vercel Edge can't use Node crypto",
      "matched": "stack: vercel, edge-functions",
      "severity": "info",
      "workaround": "Use Web Crypto API instead"
    }
  ]
}

# mind_get_context
{
  "decisions": [...],
  "issues": [...],
  "edges": [...],
  "warnings": [
    {
      "edge_id": "edge_abc",
      "title": "Vercel Edge can't use Node crypto",
      "matched": "query: 'token generation middleware'",
      "severity": "high",
      "workaround": "Use Web Crypto API instead"
    }
  ]
}
```

## Severity Levels

| Level | Meaning | How to Handle |
|-------|---------|---------------|
| `info` | Relevant context | Mention if relevant, don't interrupt |
| `medium` | Worth noting | Note before proceeding |
| `high` | Address first | Discuss before writing code |

## Implementation Tasks

1. Add `EdgeWarning` model to `models/base.py`
2. Update `EdgeDetector` class:
   - Add `warned_this_session: set[str]`
   - Add `reset_session()` method
   - Add `check_intent()` for cheap string matching
   - Update `check()` to use session tracking
3. Integrate into MCP tools:
   - `mind_start_session`: Check stack + goal
   - `mind_get_context`: Check query + code
   - `mind_add_decision`: Check reasoning
   - `mind_add_issue`: Check symptoms
4. Add tests for:
   - Intent matching
   - Session-based throttling
   - Warning generation

## What This Doesn't Do

- No file watchers
- No background processes
- No hooking every Edit/Write/Bash call
- No time-based throttling

Detection is embedded at decision points, not sprayed everywhere.
