# Context-Matching Reminders Design

## Overview

Add keyword-triggered reminders that fire when relevant topics come up in conversation, not just at specific times.

## User Story

```
User: "remind me to check the security audit when we work on auth"
Claude: Sets reminder with keywords: auth

[Later session]
User: "Let's work on the authentication system"
Claude: "By the way, you wanted me to remind you to check the security audit when working on auth."
```

## Design Decisions

1. **Trigger source:** User messages only (not file paths - too noisy)
2. **Matching:** Exact keywords (not fuzzy/semantic - keep it simple)
3. **Interface:** Same `mind_remind` tool, extended `when` parameter
4. **Detection:** Claude handles matching (context reminders shown in recall output with keywords visible)

## Implementation

### 1. Extend `parse_when()` in server.py

Detect patterns like:
- "when I mention auth"
- "when I mention auth, login, oauth"
- "when we work on auth"

Return: `(keywords_csv, "context")` instead of `(date, type)`

```python
def parse_when(when_str: str) -> tuple[str, str]:
    # Existing time-based parsing...

    # New: context-based triggers
    context_patterns = [
        r"when I mention (.+)",
        r"when we (?:work on|discuss|touch) (.+)",
        r"when (.+) comes up",
    ]
    for pattern in context_patterns:
        match = re.match(pattern, when_str, re.IGNORECASE)
        if match:
            keywords = match.group(1)
            # Normalize: "auth, login" or "auth and login" -> "auth,login"
            keywords = re.split(r"[,\s]+(?:and\s+)?", keywords)
            keywords = [k.strip() for k in keywords if k.strip()]
            return ",".join(keywords), "context"

    # Fall through to existing parsing...
```

### 2. Update REMINDERS.md format

```markdown
## Reminders

- [ ] 2025-12-14 | absolute | deploy the fix
- [ ] 2025-12-13 | next session | review PR comments
- [ ] auth,login | context | check security audit
```

Context reminders use keywords in the "due" field instead of a date.

### 3. Update `mind_recall()` output

Always include context reminders (not just when "due"):

```markdown
## Reminders Due
You have 1 reminder(s) for this session:
- review PR comments

## Context Reminders
Mention these when relevant keywords come up:
- "check security audit" -> triggers on: auth, login
```

### 4. Update `get_due_reminders()`

Context reminders are never "due" in the time sense - they're surfaced separately.

```python
def get_context_reminders(project_path: Path) -> list[dict]:
    """Get all context-triggered reminders."""
    reminders = parse_reminders(project_path)
    return [r for r in reminders if r["type"] == "context" and not r["done"]]
```

## Files to Change

1. `src/mind/mcp/server.py`
   - `parse_when()` - add context pattern detection
   - `get_context_reminders()` - new function
   - `handle_recall()` - include context reminders section
   - Update tool description for `mind_remind`

## Testing

```python
def test_parse_when_context():
    assert parse_when("when I mention auth") == ("auth", "context")
    assert parse_when("when I mention auth, login") == ("auth,login", "context")
    assert parse_when("when we work on authentication") == ("authentication", "context")

def test_context_reminders_in_recall():
    # Add a context reminder
    # Call mind_recall
    # Verify context reminders section appears
```

## Not In Scope

- Fuzzy/semantic matching (future enhancement)
- File path triggers (too noisy)
- Mid-session checking tool (Claude handles naturally)
- Auto-completion of context reminders (manual for now)
