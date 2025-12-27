# Mind Reminders - Design Doc

## Overview

Add a reminder system to Mind that lets users set time-based or session-based reminders that surface at the right moment.

## Phase A (This Implementation)

Timed reminders with "next session" support. Simple date/time triggers.

## Phase B (Future)

Context-triggered reminders - "remind me when we work on auth" - requires keyword matching against current session context.

---

## Data Model

**File:** `.mind/REMINDERS.md`

```markdown
## Reminders

- [ ] 2025-12-14 | next session | Improve reminders with context-matching
- [ ] 2025-12-15 | absolute | Review PR #42
- [x] 2025-12-13 | done | Set up Mind v2
```

Format: `- [ ] {due} | {type} | {message}`

Types:
- `next session` - fires on next `mind_recall()`
- `absolute` - fires when date/time reached
- `done` - completed, pending promotion to MEMORY.md

---

## MCP Tools

### `mind_remind(msg, when)`

Create a new reminder.

| Param | Type | Description |
|-------|------|-------------|
| `msg` | string | What to remind about |
| `when` | string | "next session", "tomorrow", "in 3 days", "2025-12-20", etc. |

Returns: Confirmation with parsed due date.

### `mind_reminders()`

List all pending reminders. No parameters.

Returns: List of pending reminders with due dates.

---

## Reminder Lifecycle

1. **Created** - `mind_remind("improve reminders", "next session")` saves to REMINDERS.md
2. **Due** - `mind_recall()` checks date/type, finds due reminders
3. **Surfaced** - Due reminders shown in MIND:CONTEXT under `## Reminders Due`
4. **User responds** - "work on it now" or "snooze" (with optional time)
5. **If work** - Mark done, promote to MEMORY.md
6. **If snooze** - Call `mind_remind()` again with new time, mark old one done (no promotion)

---

## Context Injection

Due reminders appear in MIND:CONTEXT after the Memory status:

```
## Memory: Active
Last captured: 2h ago

## Reminders Due
You have 2 reminders for this session:
- Improve reminders with context-matching
- Review PR #42

## Session Context
...
```

---

## Snooze Behavior

When Claude surfaces a due reminder, it asks:

> "You have a reminder: **{message}**
>
> Want to work on this now, or should I remind you later? (You can say 'snooze', 'next session', 'in a week', etc.)"

- "snooze" / no time specified -> next session (default)
- "next session" -> next session
- "in a week" / "tomorrow" / specific date -> parse and set

---

## Implementation

### Files to Modify

- `src/mind/mcp/server.py` - add 2 tools, modify `handle_recall()` to check reminders

### New File

- `.mind/REMINDERS.md` - created on first reminder

### Internal Functions

```python
get_reminders_file(project_path) -> Path
parse_reminders(project_path) -> list[dict]
add_reminder(project_path, msg, due, type) -> None
mark_reminder_done(project_path, index) -> None
get_due_reminders(project_path) -> list[dict]
promote_reminder_to_memory(project_path, reminder) -> None
parse_when(when_str) -> tuple[date, str]  # returns (due_date, type)
```

### `when` Parsing

| Input | Parsed As |
|-------|-----------|
| "next session" | type="next session", due=today |
| "tomorrow" | type="absolute", due=today+1 |
| "in 3 days" | type="absolute", due=today+3 |
| "in 2 weeks" | type="absolute", due=today+14 |
| "in 1 hour" | type="absolute", due=now+1h |
| "2025-12-20" | type="absolute", due=2025-12-20 |
| "December 20" | type="absolute", due=2025-12-20 |

---

## Memory Promotion

When a reminder is completed (user says "work on it"), it's promoted to MEMORY.md:

```
reminder completed: {message}
```

This preserves the history of what was reminded and acted upon.
