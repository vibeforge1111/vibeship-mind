"""Session management and primer generation."""

from datetime import datetime
from typing import Optional

from mind.models import (
    Project, Session, SessionStart, SessionEnd,
    Decision, Issue, SharpEdge,
)
from mind.storage.sqlite import SQLiteStorage


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
    ) -> dict:
        """End the current session.

        Args:
            summary: What happened this session
            progress: What was accomplished
            still_open: Unresolved threads
            next_steps: For next session
            mood: Optional mood observation

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

        # TODO: Check if session is significant enough to become episode
        episode_id = None

        return {
            "session_id": session.id,
            "captured": True,
            "episode_created": episode_id,
        }
