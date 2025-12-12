# Session Narrative Capture Design

## Overview

Automatically convert significant sessions into searchable Episodes with lessons learned. Episodes are the long-term memory of what happened—they feed back into future primers and context searches.

## When to Create an Episode

A session becomes an Episode if ANY of these are true:

### 1. Artifacts Created
```python
has_artifacts = (
    len(session.decisions_made) > 0 or
    len(session.issues_resolved) > 0 or
    len(session.edges_discovered) > 0
)
```
Clear value was captured.

### 2. Substance (Duration + Activity)
```python
duration_minutes = (session.ended_at - session.started_at).total_seconds() / 60
has_substance = duration_minutes >= 15 and (
    len(session.issues_opened) > 0 or
    len(session.issues_updated) > 0 or
    has_artifacts
)
```
Meaningful work happened.

### 3. Struggle Signal
```python
has_struggle = (
    len(session.issues_updated) >= 3 or  # Multiple attempts
    duration_minutes >= 45 or             # Long session regardless
    session.mood in ["frustrated", "stuck", "breakthrough"]
)
```
The journey matters, even without resolution.

### 4. User Declared
```python
user_declared = "significant" in (session.summary or "").lower()
```
User knows when something matters.

### Combined Logic
```python
def should_create_episode(session: Session) -> bool:
    duration_minutes = (session.ended_at - session.started_at).total_seconds() / 60

    has_artifacts = (
        len(session.decisions_made) > 0 or
        len(session.issues_resolved) > 0 or
        len(session.edges_discovered) > 0
    )

    has_substance = duration_minutes >= 15 and (
        len(session.issues_opened) > 0 or
        len(session.issues_updated) > 0 or
        has_artifacts
    )

    has_struggle = (
        len(session.issues_updated) >= 3 or
        duration_minutes >= 45 or
        session.mood in ["frustrated", "stuck", "breakthrough"]
    )

    user_declared = "significant" in (session.summary or "").lower()

    return has_artifacts or has_substance or has_struggle or user_declared
```

| Path | Example | Why it matters |
|------|---------|----------------|
| Artifacts | Made a decision, discovered edge | Clear value |
| Substance | 15+ min with issue work | Meaningful work happened |
| Struggle | 45+ min OR multiple attempts OR mood shift | The journey matters |
| Declared | User says "significant" | They know |

## Episode Title Generation

Titles should read like titles, not database fields.

```python
def generate_episode_title(
    session: Session,
    issues: dict[str, Issue],
    decisions: dict[str, Decision],
) -> str:
    # User override takes precedence
    if session.episode_title:
        return session.episode_title

    if session.issues_resolved:
        issue = issues.get(session.issues_resolved[0])
        if issue:
            return f"Resolved {issue.title}"

    if session.decisions_made:
        decision = decisions.get(session.decisions_made[0])
        if decision:
            return decision.title  # Already descriptive

    if session.edges_discovered:
        count = len(session.edges_discovered)
        return f"Discovered {count} sharp edge{'s' if count > 1 else ''}"

    if session.issues_updated:
        issue = issues.get(session.issues_updated[0])
        if issue:
            mood_prefix = {
                "frustrated": "Struggling with",
                "stuck": "Stuck on",
                "breakthrough": "Breakthrough on",
                "accomplished": "Progress on",
            }.get(session.mood, "Working on")
            return f"{mood_prefix} {issue.title}"

    # Fallback
    date = session.ended_at.strftime("%b %d")
    mood_label = {
        "exploratory": "Exploration",
        "tired": "Late night session",
    }.get(session.mood, "Session")
    return f"{date} {mood_label}"
```

Example outputs:
- "Resolved Safari auth fix"
- "Move to same-domain auth"
- "Breakthrough on OAuth callback issue"
- "Dec 12 Exploration"

## Episode Summary Generation

Structured template that reads like a summary, not a log. User's words are the soul.

```python
def generate_episode_summary(
    session: Session,
    issues: dict[str, Issue],
    decisions: dict[str, Decision],
) -> str:
    parts = []
    duration = int((session.ended_at - session.started_at).total_seconds() / 60)

    # Opening - what and how long
    if duration < 20:
        parts.append("Quick session.")
    elif duration < 60:
        parts.append(f"Worked for about {duration} minutes.")
    else:
        hours = duration // 60
        parts.append(f"Long session ({hours}+ hour{'s' if hours > 1 else ''}).")

    # The work - what we focused on
    if session.issues_updated:
        issue_titles = [
            issues[id].title for id in session.issues_updated
            if id in issues
        ]
        if len(issue_titles) == 1:
            parts.append(f"Focused on {issue_titles[0]}.")
        elif issue_titles:
            parts.append(f"Worked on {', '.join(issue_titles)}.")

    # The outcomes - what happened
    outcomes = []
    if session.issues_resolved:
        resolved = [
            issues[id].title for id in session.issues_resolved
            if id in issues
        ]
        if resolved:
            outcomes.append(f"resolved {', '.join(resolved)}")

    if session.decisions_made:
        decided = [
            decisions[id].title.lower() for id in session.decisions_made
            if id in decisions
        ]
        if decided:
            outcomes.append(f"decided to {', '.join(decided)}")

    if session.edges_discovered:
        count = len(session.edges_discovered)
        outcomes.append(f"discovered {count} gotcha{'s' if count > 1 else ''}")

    if outcomes:
        parts.append(f"Outcome: {', '.join(outcomes)}.")
    elif session.issues_updated:
        parts.append("No resolution yet.")

    # The user's words - most important part
    if session.summary:
        parts.append(session.summary)

    # Mood - color the memory
    mood_phrases = {
        "frustrated": "Ended frustrated.",
        "stuck": "Still stuck.",
        "breakthrough": "Breakthrough moment.",
        "accomplished": "Good progress.",
        "exploratory": "Exploratory session.",
        "tired": "Pushed through tired.",
    }
    if session.mood and session.mood in mood_phrases:
        parts.append(mood_phrases[session.mood])

    return " ".join(parts)
```

Example output:
> "Long session (2+ hours). Focused on Safari auth issue. Outcome: resolved Safari auth fix, decided to move auth to same domain, discovered 1 gotcha. Finally figured out ITP was blocking cross-domain cookies. Breakthrough moment."

## Schema Changes

### SessionEnd Model Update
```python
class SessionEnd(BaseModel):
    summary: str
    progress: list[str] = []
    still_open: list[str] = []
    next_steps: list[str] = []
    mood: Optional[str] = None
    episode_title: Optional[str] = None  # NEW: Override auto-generated title
```

### Session Model Update
Add `issues_resolved` field to track resolved issues during session:
```python
class Session(BaseModel):
    # ... existing fields ...
    issues_resolved: list[str] = []  # NEW: Track resolved issues
```

### SQLite Schema
Add column to sessions table:
```sql
ALTER TABLE sessions ADD COLUMN issues_resolved TEXT DEFAULT '[]';
```

## Implementation Flow

### 1. During Session
When an issue is resolved via `mind_update_issue`:
```python
if data.status == "resolved" and session_manager.current_session:
    await storage.add_session_artifact(
        session_id=session.id,
        artifact_type="issue_resolved",
        artifact_id=issue_id,
    )
```

### 2. At Session End
In `SessionManager.end_session()`:
```python
async def end_session(self, ...) -> dict:
    # ... existing code ...

    # Check if session is significant enough for episode
    if should_create_episode(ended_session):
        # Lookup titles for summary generation
        issues = await self._get_session_issues(ended_session)
        decisions = await self._get_session_decisions(ended_session)

        # Generate episode
        episode = await self.storage.create_episode(EpisodeCreate(
            project_id=session.project_id,
            session_id=session.id,
            title=generate_episode_title(ended_session, issues, decisions),
            narrative="",  # Reserved for future LLM enrichment
            summary=generate_episode_summary(ended_session, issues, decisions),
            started_at=session.started_at,
            ended_at=session.ended_at,
            lessons=next_steps,  # User's next_steps become lessons
            breakthroughs=[session.summary] if session.mood == "breakthrough" else [],
        ))

        # Link episode to session
        await self.storage.link_session_episode(session.id, episode.id)

        episode_id = episode.id

    return {
        "session_id": session.id,
        "captured": True,
        "episode_created": episode_id,
    }
```

## What Doesn't Change

- `mind_end_session` MCP tool interface (just add optional `episode_title` param)
- Episode model structure (already has all needed fields)
- ChromaDB indexing (episodes already indexed)

## Future Enhancements (Not in Phase 1)

1. **LLM narrative enrichment** - Generate richer narratives when API key available
2. **Title snapshots** - Store issue/decision titles at episode creation time for historical accuracy
3. **Episode linking** - Link related episodes (e.g., "Continued from Dec 11 session")
4. **Mood inference** - Auto-detect mood from session patterns when not provided

## Testing

1. Quick Q&A session (< 15 min, no artifacts) → No episode
2. 20-min session with issue opened → Episode (substance)
3. 50-min session with no artifacts → Episode (struggle/duration)
4. 10-min session with decision made → Episode (artifacts)
5. Session with mood="breakthrough" → Episode (struggle signal)
6. Session with "significant" in summary → Episode (user declared)
