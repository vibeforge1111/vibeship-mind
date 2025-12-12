"""Primer generation with smart prioritization.

Primers surface the most relevant context for a session, not just the most recent.
Entity-specific scoring ensures blocking issues, triggered revisit conditions,
and stack-relevant edges rise to the top.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from mind.models import Project, Session, Decision, Issue, SharpEdge
from mind.models.base import EntityType
from mind.storage.sqlite import SQLiteStorage


@dataclass
class PrimerResult:
    """Result of primer generation."""
    text: str                       # Formatted text for Claude to read
    issues: list[Issue]             # Structured data for MCP response
    decisions: list[Decision]       # Decisions to revisit
    edges: list[SharpEdge]          # Relevant sharp edges


class PrimerScorer:
    """Scores entities for primer relevance.

    Entity-specific scoring because different types have different signals:
    - Issues: severity is primary
    - Decisions: revisit_if condition is primary
    - Edges: stack match is primary
    """

    def __init__(
        self,
        project: Project,
        last_session: Optional[Session],
        now: datetime,
    ):
        self.project = project
        self.last_session = last_session
        self.now = now

        # Pre-compute context terms for matching
        self._next_steps_text = ""
        if last_session and last_session.next_steps:
            self._next_steps_text = " ".join(last_session.next_steps).lower()

        self._context_terms = self._build_context_terms()

    def _build_context_terms(self) -> list[str]:
        """Build list of context terms for keyword matching."""
        terms = []

        if self.project.current_goal:
            terms.extend(self.project.current_goal.lower().split())

        terms.extend(t.lower() for t in self.project.stack)
        terms.extend(t.lower() for t in self.project.open_threads)

        if self.last_session and self.last_session.next_steps:
            for step in self.last_session.next_steps:
                terms.extend(step.lower().split())

        # Filter out tiny words
        return [t for t in terms if len(t) > 3]

    def score_issue(self, issue: Issue, access_count: int) -> tuple[float, Optional[str]]:
        """Score an issue for primer relevance.

        Returns:
            Tuple of (score, hint_reason). Hint is only for non-obvious reasons.
        """
        score = 0.0
        hint = None

        # Severity is primary for issues
        severity_scores = {"blocking": 100, "major": 50, "minor": 20, "cosmetic": 5}
        score += severity_scores.get(issue.severity, 20)

        # Continuity from last session (strong signal)
        mentioned = self._mentioned_in_next_steps(issue.title)
        if mentioned:
            score += 80

        # Goal alignment
        goal_related = self._related_to_goal(issue.title)
        if goal_related:
            score += 60

        # Recent activity (up to 30 points)
        score += self._recency_score(issue.updated_at, max_points=30)

        # Access frequency (up to 30 points)
        score += min(access_count * 5, 30)

        # Hint: only for non-obvious reasons
        # Blocking speaks for itself, so only hint if that's NOT why it's top
        if issue.severity != "blocking":
            if mentioned:
                hint = "from last session"
            elif goal_related:
                hint = "goal-related"

        return score, hint

    def score_decision(self, decision: Decision, access_count: int) -> tuple[float, Optional[str]]:
        """Score a decision for primer relevance.

        Returns:
            Tuple of (score, hint_reason).
        """
        score = 0.0
        hint = None

        # revisit_if is primary for decisions
        condition_triggered = False
        if decision.revisit_if:
            condition_triggered = self._condition_might_apply(decision.revisit_if)
            if condition_triggered:
                score += 100
                hint = f'condition triggered: "{self._truncate(decision.revisit_if, 30)}"'

        # Low confidence = worth surfacing
        if decision.confidence < 0.5:
            score += 40
            if not hint:
                hint = "low confidence"
        elif decision.confidence < 0.7:
            score += 20

        # Goal alignment
        if self._related_to_goal(decision.title):
            score += 50
            if not hint:
                hint = "goal-related"

        # Recency (decisions can be old but valid, so less weight)
        score += self._recency_score(decision.decided_at, max_points=15)

        # Access frequency
        score += min(access_count * 3, 20)

        return score, hint

    def score_edge(self, edge: SharpEdge, access_count: int) -> tuple[float, Optional[str]]:
        """Score a sharp edge for primer relevance.

        Returns:
            Tuple of (score, hint_reason).
        """
        score = 0.0
        hint = None

        # Stack overlap is primary for edges
        stack_match = self._matches_stack(edge)
        if stack_match:
            score += 80
            hint = "matches stack"

        # Goal overlap
        if self._related_to_goal(edge.title):
            score += 60
            if not hint:
                hint = "goal-related"

        # Has been triggered before (proven relevant)
        if access_count > 0:
            score += 40
            if not hint:
                hint = "seen before"

        # Detection pattern relevance to current context
        if self._detection_might_apply(edge):
            score += 50

        return score, hint

    def _mentioned_in_next_steps(self, title: str) -> bool:
        """Check if title appears in last session's next_steps."""
        if not self._next_steps_text:
            return False
        return title.lower() in self._next_steps_text

    def _related_to_goal(self, title: str) -> bool:
        """Check if title relates to current goal."""
        if not self.project.current_goal:
            return False

        title_lower = title.lower()
        goal_lower = self.project.current_goal.lower()

        # Direct containment
        if title_lower in goal_lower or goal_lower in title_lower:
            return True

        # Word overlap (significant words only)
        title_words = set(w for w in title_lower.split() if len(w) > 3)
        goal_words = set(w for w in goal_lower.split() if len(w) > 3)

        return len(title_words & goal_words) >= 1

    def _condition_might_apply(self, revisit_if: str) -> bool:
        """Check if revisit condition might be relevant now."""
        revisit_lower = revisit_if.lower()
        return any(term in revisit_lower for term in self._context_terms)

    def _matches_stack(self, edge: SharpEdge) -> bool:
        """Check if edge relates to project stack."""
        if not self.project.stack:
            return False

        edge_text = f"{edge.title} {edge.description}".lower()
        return any(tech.lower() in edge_text for tech in self.project.stack)

    def _detection_might_apply(self, edge: SharpEdge) -> bool:
        """Check if edge detection patterns might fire."""
        context = f"{self.project.current_goal or ''} {' '.join(self.project.stack)}".lower()

        for pattern in edge.detection_patterns:
            if pattern.type == "context":
                try:
                    if re.search(pattern.pattern, context, re.IGNORECASE):
                        return True
                except re.error:
                    pass  # Invalid regex, skip

        # Also check trigger phrases
        return any(phrase.lower() in context for phrase in edge.trigger_phrases)

    def _recency_score(self, dt: datetime, max_points: float) -> float:
        """Calculate recency score. More recent = higher score."""
        if not dt:
            return 0.0

        days_old = (self.now - dt).days
        if days_old < 0:
            days_old = 0

        # Linear decay over 30 days
        return max(0, max_points - days_old)

    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text with ellipsis."""
        if len(text) <= max_len:
            return text
        return text[:max_len - 3] + "..."


class PrimerGenerator:
    """Generates session primers with smart prioritization.

    Selects the most relevant items (not just most recent) based on:
    - Severity, continuity, goal alignment for issues
    - Triggered conditions, confidence for decisions
    - Stack match, past triggers for edges
    """

    # Limits for each section
    MAX_ISSUES = 3
    MAX_DECISIONS = 2
    MAX_EDGES = 2

    # Emoji for severity
    SEVERITY_EMOJI = {
        "blocking": "🔴",
        "major": "🟠",
        "minor": "🟡",
        "cosmetic": "⚪",
    }

    def __init__(self, storage: SQLiteStorage):
        self.storage = storage

    async def generate(
        self,
        project: Project,
        last_session: Optional[Session],
    ) -> PrimerResult:
        """Generate primer with smart prioritization.

        Args:
            project: Current project
            last_session: Last ended session for continuity context

        Returns:
            PrimerResult with formatted text and structured data
        """
        now = datetime.utcnow()
        scorer = PrimerScorer(project, last_session, now)

        # Get and score items
        top_issues = await self._get_top_issues(project, scorer)
        top_decisions = await self._get_top_decisions(project, scorer)
        top_edges = await self._get_top_edges(project, scorer)

        # Build text
        text = self._build_primer_text(
            project, last_session, top_issues, top_decisions, top_edges
        )

        return PrimerResult(
            text=text,
            issues=[item for _, _, item in top_issues],
            decisions=[item for _, _, item in top_decisions],
            edges=[item for _, _, item in top_edges],
        )

    async def _get_top_issues(
        self,
        project: Project,
        scorer: PrimerScorer,
    ) -> list[tuple[float, Optional[str], Issue]]:
        """Get top issues by relevance score."""
        issues = await self.storage.list_open_issues(project.id)
        if not issues:
            return []

        # Get access stats in batch
        issue_ids = [i.id for i in issues]
        access_stats = await self.storage.get_access_stats(issue_ids)

        # Score each issue
        scored = []
        for issue in issues:
            access_count = access_stats.get(issue.id, {}).get("access_count", 0)
            score, hint = scorer.score_issue(issue, access_count)
            scored.append((score, hint, issue))

        # Sort by score descending, take top N
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:self.MAX_ISSUES]

    async def _get_top_decisions(
        self,
        project: Project,
        scorer: PrimerScorer,
    ) -> list[tuple[float, Optional[str], Decision]]:
        """Get top decisions to revisit by relevance score."""
        # Only get decisions that have revisit conditions or low confidence
        all_decisions = await self.storage.list_decisions(project.id, status="active")
        candidates = [d for d in all_decisions if d.revisit_if or d.confidence < 0.7]

        if not candidates:
            return []

        # Get access stats in batch
        decision_ids = [d.id for d in candidates]
        access_stats = await self.storage.get_access_stats(decision_ids)

        # Score each decision
        scored = []
        for decision in candidates:
            access_count = access_stats.get(decision.id, {}).get("access_count", 0)
            score, hint = scorer.score_decision(decision, access_count)
            scored.append((score, hint, decision))

        # Sort by score descending, take top N
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:self.MAX_DECISIONS]

    async def _get_top_edges(
        self,
        project: Project,
        scorer: PrimerScorer,
    ) -> list[tuple[float, Optional[str], SharpEdge]]:
        """Get top relevant edges by relevance score."""
        edges = await self.storage.list_sharp_edges(project.id)
        if not edges:
            return []

        # Get access stats in batch
        edge_ids = [e.id for e in edges]
        access_stats = await self.storage.get_access_stats(edge_ids)

        # Score each edge
        scored = []
        for edge in edges:
            access_count = access_stats.get(edge.id, {}).get("access_count", 0)
            score, hint = scorer.score_edge(edge, access_count)
            scored.append((score, hint, edge))

        # Sort by score descending, take top N
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:self.MAX_EDGES]

    def _build_primer_text(
        self,
        project: Project,
        last_session: Optional[Session],
        issues: list[tuple[float, Optional[str], Issue]],
        decisions: list[tuple[float, Optional[str], Decision]],
        edges: list[tuple[float, Optional[str], SharpEdge]],
    ) -> str:
        """Build formatted primer text."""
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

        # Open issues with hints
        if issues:
            lines.append(f"Open issues ({len(issues)}):")
            for score, hint, issue in issues:
                emoji = self.SEVERITY_EMOJI.get(issue.severity, "⚪")
                line = f"  {emoji} {issue.title} ({issue.severity})"
                if hint:
                    line += f" ← {hint}"
                lines.append(line)
            lines.append("")

        # Decisions to revisit with hints
        if decisions:
            lines.append(f"Decisions to revisit ({len(decisions)}):")
            for score, hint, decision in decisions:
                line = f"  - {decision.title}"
                if hint:
                    line += f" ← {hint}"
                lines.append(line)
            lines.append("")

        # Relevant sharp edges with hints
        if edges:
            lines.append("Watch out for:")
            for score, hint, edge in edges:
                line = f"  ⚠️ {edge.title}"
                if hint:
                    line += f" ← {hint}"
                lines.append(line)
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
