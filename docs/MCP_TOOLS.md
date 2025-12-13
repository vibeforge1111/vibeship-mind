# Mind MCP Tools

<!-- doc-version: 2.1.0 | last-updated: 2025-12-13 -->

Mind has **12 MCP tools**. The architecture is stateless - tools load and process on demand.

---

## Core Tools

### mind_recall

**CALL THIS FIRST every session.** Loads fresh context, detects session gaps, promotes learnings.

```python
mind_recall(project_path=None, force_refresh=False)
```

Returns:
- `context` - MIND:CONTEXT markdown
- `session` - Current session state (experience, blockers, rejected, assumptions)
- `session_info` - Gap detection, promotions count
- `health` - File size, suggestions
- `reminders_due` - Time-based reminders that are due
- `context_reminders` - Context-triggered reminders

### mind_log

Log to session or memory. Routes by type automatically.

```python
mind_log(message, type="experience")
```

**Type routing:**

| Type | Destination | Use for |
|------|-------------|---------|
| `experience` | SESSION.md | Raw moments, thoughts |
| `blocker` | SESSION.md | Things stopping progress |
| `assumption` | SESSION.md | What you're assuming true |
| `rejected` | SESSION.md | What didn't work and why |
| `decision` | MEMORY.md | Decided X because Y |
| `learning` | MEMORY.md | Learned that X |
| `problem` | MEMORY.md | Problem: X |
| `progress` | MEMORY.md | Fixed: X |

---

## Reading Tools

### mind_session

Get current session state from SESSION.md.

```python
mind_session(project_path=None)
```

Returns session state with experience, blockers, rejected, assumptions.

### mind_search

Search across memories when CLAUDE.md context isn't enough.

```python
mind_search(query, scope="project", types=None, limit=10)
```

- `scope` - "project" (current) or "all" (all registered projects)
- `types` - Filter: "decision", "issue", "learning"

### mind_status

Check Mind health and project statistics.

```python
mind_status()
```

Returns version, current project info, stats.

### mind_reminders

List all pending reminders.

```python
mind_reminders()
```

Returns pending reminders and done count.

---

## Action Tools

### mind_blocker

Log a blocker and auto-search memory for solutions.

```python
mind_blocker(description, keywords=None)
```

Adds to SESSION.md Blockers section and searches MEMORY.md for related past solutions.

### mind_remind

Set a reminder for later.

```python
mind_remind(message, when)
```

**Time-based:**
- `"next session"` - fires on next mind_recall()
- `"tomorrow"` - tomorrow's date
- `"in 3 days"` - relative days
- `"2025-12-20"` - specific date

**Context-based:**
- `"when I mention auth"` - triggers when keywords match
- `"when we work on database"` - triggers on related context

### mind_edges

Check for gotchas before implementing risky code.

```python
mind_edges(intent, code=None, stack=None)
```

- `intent` - What you're about to do
- `code` - Optional code snippet to analyze
- `stack` - Override auto-detected stack

### mind_checkpoint

Force process pending memories and regenerate context.

```python
mind_checkpoint(project_path=None)
```

### mind_add_global_edge

Add a cross-project gotcha.

```python
mind_add_global_edge(title, description, workaround, detection, stack_tags=None, severity="warning")
```

Use for platform/language issues, not project-specific. Project-specific gotchas go in MEMORY.md Gotchas section.

---

## Tool Usage Summary

| Situation | Tool |
|-----------|------|
| Session start | `mind_recall()` - ALWAYS FIRST |
| Log something | `mind_log(msg, type)` |
| Feeling lost | `mind_session()` |
| Stuck on something | `mind_blocker()` |
| Need details not in context | `mind_search()` |
| About to implement risky code | `mind_edges()` |
| User says "remind me..." | `mind_remind()` |
| Check pending reminders | `mind_reminders()` |
| After writing several memories | `mind_checkpoint()` |
| Found a platform gotcha | `mind_add_global_edge()` |
| Something seems wrong | `mind_status()` |

---

## MCP Configuration

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
