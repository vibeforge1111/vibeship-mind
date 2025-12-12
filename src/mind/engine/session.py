"""Session management and primer generation."""

from datetime import datetime, timezone
from typing import Optional

from mind.models import (
    Project, Session, SessionStart, SessionEnd,
    Decision, Issue, SharpEdge, EpisodeCreate,
)
from mind.storage.sqlite import SQLiteStorage


def should_create_episode(session: Session) -> bool:
    """Determine if a session is significant enough to become an Episode.

    A session becomes an Episode if ANY of these are true:
    1. Artifacts created (decisions, resolved issues, edges)
    2. Substance (15+ min with issue activity)
    3. Struggle signal (45+ min, or multiple attempts, or mood signal)
    4. User declared ("significant" in summary)
    """
    # Calculate duration
    if session.ended_at and session.started_at:
        duration_minutes = (session.ended_at - session.started_at).total_seconds() / 60
    else:
        duration_minutes = 0

    # 1. Artifacts created - clear value
    has_artifacts = (
        len(session.decisions_made) > 0 or
        len(session.issues_resolved) > 0 or
        len(session.edges_discovered) > 0
    )

    # 2. Substance - meaningful work happened
    has_substance = duration_minutes >= 15 and (
        len(session.issues_opened) > 0 or
        len(session.issues_updated) > 0 or
        has_artifacts
    )

    # 3. Struggle signal - the journey matters
    has_struggle = (
        len(session.issues_updated) >= 3 or  # Multiple attempts
        duration_minutes >= 45 or  # Long session regardless
        session.mood in ["frustrated", "stuck", "breakthrough"]
    )

    # 4. User declared
    user_declared = "significant" in (session.summary or "").lower()

    return has_artifacts or has_substance or has_struggle or user_declared


def generate_episode_title(
    session: Session,
    issues: dict[str, Issue],
    decisions: dict[str, Decision],
) -> str:
    """Generate a human-readable title for an Episode."""
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
    if session.ended_at:
        date = session.ended_at.strftime("%b %d")
    else:
        date = datetime.now(timezone.utc).strftime("%b %d")

    mood_label = {
        "exploratory": "Exploration",
        "tired": "Late night session",
    }.get(session.mood, "Session")
    return f"{date} {mood_label}"


def generate_episode_summary(
    session: Session,
    issues: dict[str, Issue],
    decisions: dict[str, Decision],
) -> str:
    """Generate a human-readable summary for an Episode.

    Structured template that reads like a summary, not a log.
    User's words are the soul.
    """
    parts = []

    # Calculate duration
    if session.ended_at and session.started_at:
        duration = int((session.ended_at - session.started_at).total_seconds() / 60)
    else:
        duration = 0

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


class PrimerGenerator:
    """Generates session primers with relevant context."""

    def generate(
        self,
        project: Project,
        open_issues: list[Issue],
        pending_decisions: list[Decision],
        relevant_edges: list[SharpEdge],
    ) -> str:
        """Generate a session primer.

        The primer is a human-readable summary of current context
        that helps continue where we left off.
        """
        lines: list[str] = []

        # Last session info
        if project.last_session_date:
            time_ago = self._format_time_ago(project.last_session_date)
            lines.append(f"Last session: {time_ago}")

            if project.last_session_summary:
                lines.append(f"Ended with: {project.last_session_summary}")

            if project.last_session_mood:
                lines.append(f"Mood: {project.last_session_mood}")

            if project.last_session_next_step:
                lines.append(f"Next step was: {project.last_session_next_step}")

            lines.append("")

        # Current goal
        if project.current_goal:
            lines.append(f"Current goal: {project.current_goal}")

        # Blockers
        if project.blocked_by:
            lines.append(f"Blocked by: {', '.join(project.blocked_by)}")

        # Open threads
        if project.open_threads:
            lines.append(f"Open threads: {', '.join(project.open_threads)}")

        if lines and lines[-1] != "":
            lines.append("")

        # Open issues
        if open_issues:
            lines.append(f"Open issues ({len(open_issues)}):")
            for issue in open_issues[:3]:  # Top 3
                severity_icon = {"blocking": "🔴", "major": "🟠", "minor": "🟡"}.get(issue.severity, "⚪")
                lines.append(f"  {severity_icon} {issue.title}")
            if len(open_issues) > 3:
                lines.append(f"  ... and {len(open_issues) - 3} more")
            lines.append("")

        # Pending decisions (decisions that should be revisited)
        if pending_decisions:
            lines.append(f"Decisions to revisit ({len(pending_decisions)}):")
            for decision in pending_decisions[:2]:
                lines.append(f"  - {decision.title}")
                if decision.revisit_if:
                    lines.append(f"    Reason: {decision.revisit_if}")
            lines.append("")

        # Relevant sharp edges
        if relevant_edges:
            lines.append(f"Watch out for:")
            for edge in relevant_edges[:2]:
                lines.append(f"  ⚠️ {edge.title}")
            lines.append("")

        # Closing prompt
        if lines:
            lines.append("What would you like to focus on?")
        else:
            lines.append("No prior context. What are we working on?")

        return "\n".join(lines)

    def _format_time_ago(self, dt: datetime) -> str:
        """Format datetime as human-readable time ago."""
        now = datetime.utcnow()
        diff = now - dt

        if diff.days == 0:
            if diff.seconds < 3600:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        else:
            return dt.strftime("%B %d, %Y")


class SessionManager:
    """Manages session lifecycle."""

    def __init__(self, storage: SQLiteStorage):
        self.storage = storage
        self.primer_generator = PrimerGenerator()
        self._current_session: Optional[Session] = None

    @property
    def current_session(self) -> Optional[Session]:
        """Get the current active session."""
        return self._current_session

    async def start_session(
        self,
        project_id: Optional[str] = None,
        project_name: Optional[str] = None,
        detect_from_path: Optional[str] = None,
    ) -> SessionStart:
        """Start a new session.

        Args:
            project_id: Existing project ID
            project_name: Find or create project by name
            detect_from_path: Detect project from repository path

        Returns:
            SessionStart with session info, project, and primer
        """
        # Find or create project
        project: Optional[Project] = None

        if project_id:
            project = await self.storage.get_project(project_id)
        elif detect_from_path:
            project = await self.storage.get_project_by_path(detect_from_path)
        elif project_name:
            project = await self.storage.get_project_by_name(project_name)

        if not project and project_name:
            # Create new project
            from mind.models import ProjectCreate
            project = await self.storage.create_project(ProjectCreate(name=project_name))

        if not project:
            raise ValueError("Could not find or create project. Provide project_id, project_name, or detect_from_path.")

        # Get user
        user = await self.storage.get_or_create_user()

        # End any previous active session for this project
        active_session = await self.storage.get_active_session(project.id)
        if active_session:
            await self.storage.end_session(
                active_session.id,
                SessionEnd(summary="Session ended (new session started)", progress=[], still_open=[], next_steps=[])
            )

        # Create new session
        session = await self.storage.create_session(project.id, user.id)
        self._current_session = session

        # Increment user session count
        await self.storage.increment_user_sessions(project.id)

        # Get context for primer
        open_issues = await self.storage.list_open_issues(project.id)
        all_decisions = await self.storage.list_decisions(project.id, status="active")

        # Find decisions that should be revisited
        pending_decisions = [d for d in all_decisions if d.revisit_if]

        # Get relevant edges
        edges = await self.storage.list_sharp_edges(project.id)

        # Generate primer
        primer = self.primer_generator.generate(
            project=project,
            open_issues=open_issues,
            pending_decisions=pending_decisions,
            relevant_edges=edges[:3],
        )

        return SessionStart(
            session_id=session.id,
            project=project,
            primer=primer,
            open_issues=open_issues,
            pending_decisions=pending_decisions,
            relevant_edges=edges[:5],
        )

    async def end_session(
        self,
        summary: str,
        progress: list[str],
        still_open: list[str],
        next_steps: list[str],
        mood: Optional[str] = None,
        episode_title: Optional[str] = None,
    ) -> dict:
        """End the current session.

        Args:
            summary: What happened this session
            progress: What was accomplished
            still_open: Unresolved threads
            next_steps: For next session
            mood: Optional mood observation
            episode_title: Optional override for auto-generated episode title

        Returns:
            Dict with session_id, captured status, and optional episode_id
        """
        if not self._current_session:
            raise ValueError("No active session to end")

        session = self._current_session
        session_data = SessionEnd(
            summary=summary,
            progress=progress,
            still_open=still_open,
            next_steps=next_steps,
            mood=mood,
            episode_title=episode_title,
        )

        # End session in storage
        ended_session = await self.storage.end_session(session.id, session_data)

        # Update project's last session info
        next_step = next_steps[0] if next_steps else None
        await self.storage.update_project_session(
            project_id=session.project_id,
            session_id=session.id,
            summary=summary,
            mood=mood,
            next_step=next_step,
        )

        self._current_session = None

        # Check if session is significant enough to become episode
        episode_id = None
        if ended_session and should_create_episode(ended_session):
            episode_id = await self._create_episode(
                ended_session,
                episode_title_override=episode_title,
            )

        return {
            "session_id": session.id,
            "captured": True,
            "episode_created": episode_id,
        }

    async def _create_episode(
        self,
        session: Session,
        episode_title_override: Optional[str] = None,
    ) -> Optional[str]:
        """Create an Episode from a significant session.

        Args:
            session: The ended session
            episode_title_override: Optional user-provided title

        Returns:
            Episode ID if created, None otherwise
        """
        # Lookup issues and decisions for title/summary generation
        issues: dict[str, Issue] = {}
        decisions: dict[str, Decision] = {}

        # Gather all issue IDs we need
        issue_ids = set(
            session.issues_opened +
            session.issues_updated +
            session.issues_resolved
        )
        for issue_id in issue_ids:
            issue = await self.storage.get_issue(issue_id)
            if issue:
                issues[issue_id] = issue

        # Gather all decision IDs we need
        for decision_id in session.decisions_made:
            decision = await self.storage.get_decision(decision_id)
            if decision:
                decisions[decision_id] = decision

        # Generate title (user override or auto-generated)
        if episode_title_override:
            title = episode_title_override
        else:
            title = generate_episode_title(session, issues, decisions)

        # Generate summary
        summary = generate_episode_summary(session, issues, decisions)

        # Create episode
        episode = await self.storage.create_episode(
            EpisodeCreate(
                project_id=session.project_id,
                session_id=session.id,
                title=title,
                narrative="",  # Reserved for future LLM enrichment
                summary=summary,
                started_at=session.started_at,
                ended_at=session.ended_at or datetime.now(timezone.utc),
                lessons=session.next_steps,  # User's next_steps become lessons
                breakthroughs=[session.summary] if session.mood == "breakthrough" else [],
            )
        )

        # Link episode to session
        await self.storage.link_session_episode(session.id, episode.id)

        return episode.id
