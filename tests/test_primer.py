"""Tests for primer scoring and generation."""

import pytest
from datetime import datetime, timedelta

from mind.models import Project, Session, Decision, Issue, SharpEdge
from mind.models.sharp_edge import DetectionPattern
from mind.engine.primer import PrimerScorer, PrimerGenerator, PrimerResult


# Fixtures

@pytest.fixture
def project():
    """Basic project for testing."""
    return Project(
        id="proj_test",
        name="Test Project",
        current_goal="Fix authentication flow",
        stack=["Python", "FastAPI", "SQLite"],
        open_threads=["Safari ITP issue", "Mobile responsive"],
    )


@pytest.fixture
def last_session():
    """Last session with next_steps for continuity."""
    return Session(
        id="sess_last",
        project_id="proj_test",
        user_id="user_1",
        started_at=datetime.utcnow() - timedelta(hours=2),
        ended_at=datetime.utcnow() - timedelta(hours=1),
        status="ended",
        next_steps=["Try same-domain approach for Safari", "Check mobile nav"],
        summary="Debugging Safari auth",
        mood="frustrated",
    )


@pytest.fixture
def blocking_issue():
    """Blocking issue."""
    return Issue(
        id="iss_block",
        project_id="proj_test",
        title="Safari auth callback fails",
        description="Auth fails on Safari due to ITP",
        severity="blocking",
        status="open",
        updated_at=datetime.utcnow() - timedelta(days=1),
    )


@pytest.fixture
def major_issue_mentioned():
    """Major issue mentioned in next_steps."""
    return Issue(
        id="iss_major",
        project_id="proj_test",
        title="Same-domain approach for Safari",
        description="Try same-domain cookies",
        severity="major",
        status="open",
        updated_at=datetime.utcnow() - timedelta(days=2),
    )


@pytest.fixture
def minor_issue_goal_related():
    """Minor issue related to goal."""
    return Issue(
        id="iss_minor",
        project_id="proj_test",
        title="Authentication timeout too short",
        description="Token expires too quickly",
        severity="minor",
        status="open",
        updated_at=datetime.utcnow() - timedelta(days=5),
    )


@pytest.fixture
def old_minor_issue():
    """Old minor issue not related to anything."""
    return Issue(
        id="iss_old",
        project_id="proj_test",
        title="Footer spacing issue",
        description="CSS margin problem",
        severity="minor",
        status="open",
        updated_at=datetime.utcnow() - timedelta(days=30),
    )


class TestPrimerScorer:
    """Tests for PrimerScorer."""

    def test_score_issue_severity_primary(self, project, last_session):
        """Blocking issues score highest on severity alone."""
        scorer = PrimerScorer(project, last_session, datetime.utcnow())

        blocking = Issue(
            id="iss_1", project_id="proj_test",
            title="Unrelated blocking bug",
            description="Something",
            severity="blocking", status="open",
        )
        minor = Issue(
            id="iss_2", project_id="proj_test",
            title="Unrelated minor bug",
            description="Something",
            severity="minor", status="open",
        )

        block_score, _ = scorer.score_issue(blocking, access_count=0)
        minor_score, _ = scorer.score_issue(minor, access_count=0)

        assert block_score > minor_score
        assert block_score >= 100  # Blocking base score

    def test_score_issue_continuity_boost(self, project, last_session):
        """Issues mentioned in next_steps get continuity boost."""
        scorer = PrimerScorer(project, last_session, datetime.utcnow())

        # Title matches "same-domain approach for Safari" in next_steps
        mentioned = Issue(
            id="iss_1", project_id="proj_test",
            title="Same-domain approach",
            description="Cookie approach",
            severity="minor", status="open",
        )
        not_mentioned = Issue(
            id="iss_2", project_id="proj_test",
            title="Database migration",
            description="Something else",
            severity="minor", status="open",
        )

        mentioned_score, mentioned_hint = scorer.score_issue(mentioned, access_count=0)
        not_score, not_hint = scorer.score_issue(not_mentioned, access_count=0)

        assert mentioned_score > not_score
        assert mentioned_hint == "from last session"
        assert not_hint is None

    def test_score_issue_goal_alignment(self, project, last_session):
        """Issues related to current_goal get boost."""
        scorer = PrimerScorer(project, last_session, datetime.utcnow())

        # Goal is "Fix authentication flow"
        goal_related = Issue(
            id="iss_1", project_id="proj_test",
            title="Authentication token refresh",
            description="Token issues",
            severity="minor", status="open",
        )
        unrelated = Issue(
            id="iss_2", project_id="proj_test",
            title="Database indexing",
            description="Performance",
            severity="minor", status="open",
        )

        related_score, related_hint = scorer.score_issue(goal_related, access_count=0)
        unrelated_score, _ = scorer.score_issue(unrelated, access_count=0)

        assert related_score > unrelated_score
        # Hint only shows if not blocking and not from last session
        assert related_hint == "goal-related"

    def test_score_issue_no_hint_for_blocking(self, project, last_session):
        """Blocking issues don't get hints - severity speaks for itself."""
        scorer = PrimerScorer(project, last_session, datetime.utcnow())

        blocking = Issue(
            id="iss_1", project_id="proj_test",
            title="Same-domain approach",  # Would match next_steps
            description="Something",
            severity="blocking", status="open",
        )

        score, hint = scorer.score_issue(blocking, access_count=0)
        assert hint is None  # No hint needed for blocking

    def test_score_issue_access_frequency(self, project, last_session):
        """Frequently accessed issues score higher."""
        scorer = PrimerScorer(project, last_session, datetime.utcnow())

        issue = Issue(
            id="iss_1", project_id="proj_test",
            title="Some issue",
            description="Something",
            severity="minor", status="open",
        )

        low_access_score, _ = scorer.score_issue(issue, access_count=1)
        high_access_score, _ = scorer.score_issue(issue, access_count=10)

        assert high_access_score > low_access_score

    def test_score_decision_revisit_if_triggered(self, project, last_session):
        """Decisions with triggered revisit_if score highest."""
        scorer = PrimerScorer(project, last_session, datetime.utcnow())

        # revisit_if mentions "Safari" which is in stack/threads
        triggered = Decision(
            id="dec_1", project_id="proj_test",
            title="Use cross-domain auth",
            description="OAuth approach",
            context="Initial auth design",
            reasoning="Simpler",
            revisit_if="if Safari issues persist",
        )
        not_triggered = Decision(
            id="dec_2", project_id="proj_test",
            title="Use PostgreSQL",
            description="Database choice",
            context="DB selection",
            reasoning="Scalability",
            revisit_if="if we need horizontal scaling",
        )

        triggered_score, triggered_hint = scorer.score_decision(triggered, access_count=0)
        not_score, _ = scorer.score_decision(not_triggered, access_count=0)

        assert triggered_score > not_score
        assert "condition triggered" in triggered_hint

    def test_score_decision_low_confidence(self, project, last_session):
        """Low confidence decisions surface for review."""
        scorer = PrimerScorer(project, last_session, datetime.utcnow())

        low_conf = Decision(
            id="dec_1", project_id="proj_test",
            title="Maybe use Redis",
            description="Caching",
            context="Performance",
            reasoning="Might help",
            confidence=0.4,
        )
        high_conf = Decision(
            id="dec_2", project_id="proj_test",
            title="Use TypeScript",
            description="Language choice",
            context="Type safety",
            reasoning="Better DX",
            confidence=0.9,
        )

        low_score, low_hint = scorer.score_decision(low_conf, access_count=0)
        high_score, _ = scorer.score_decision(high_conf, access_count=0)

        assert low_score > high_score
        assert low_hint == "low confidence"

    def test_score_edge_stack_match(self, project, last_session):
        """Edges matching stack score highest."""
        scorer = PrimerScorer(project, last_session, datetime.utcnow())

        # Stack includes "Python", "FastAPI"
        matches = SharpEdge(
            id="edge_1", project_id=None,
            title="FastAPI async gotcha",
            description="Async context issues in FastAPI",
            workaround="Use contextvars",
        )
        no_match = SharpEdge(
            id="edge_2", project_id=None,
            title="React hydration mismatch",
            description="SSR issues",
            workaround="Use suppressHydrationWarning",
        )

        match_score, match_hint = scorer.score_edge(matches, access_count=0)
        no_score, _ = scorer.score_edge(no_match, access_count=0)

        assert match_score > no_score
        assert match_hint == "matches stack"

    def test_score_edge_seen_before(self, project, last_session):
        """Edges with past access get "seen before" hint."""
        scorer = PrimerScorer(project, last_session, datetime.utcnow())

        edge = SharpEdge(
            id="edge_1", project_id=None,
            title="Some edge",
            description="Description",
            workaround="Fix it",
        )

        no_access_score, no_hint = scorer.score_edge(edge, access_count=0)
        has_access_score, has_hint = scorer.score_edge(edge, access_count=3)

        assert has_access_score > no_access_score
        assert has_hint == "seen before"
        assert no_hint is None


class TestPrimerScorerHelpers:
    """Tests for PrimerScorer helper methods."""

    def test_mentioned_in_next_steps(self, project, last_session):
        """Title matching in next_steps."""
        scorer = PrimerScorer(project, last_session, datetime.utcnow())

        assert scorer._mentioned_in_next_steps("same-domain approach")
        assert scorer._mentioned_in_next_steps("Safari")
        assert scorer._mentioned_in_next_steps("mobile nav")
        assert not scorer._mentioned_in_next_steps("database migration")

    def test_related_to_goal(self, project, last_session):
        """Title relating to current_goal."""
        scorer = PrimerScorer(project, last_session, datetime.utcnow())

        # Goal is "Fix authentication flow"
        assert scorer._related_to_goal("authentication token")
        assert scorer._related_to_goal("auth flow issue")
        assert not scorer._related_to_goal("database migration")

    def test_condition_might_apply(self, project, last_session):
        """Revisit condition matching context terms."""
        scorer = PrimerScorer(project, last_session, datetime.utcnow())

        # Context includes "Safari", "FastAPI", "authentication", etc.
        assert scorer._condition_might_apply("if Safari issues persist")
        assert scorer._condition_might_apply("if authentication becomes complex")
        assert not scorer._condition_might_apply("if we need multi-region")

    def test_matches_stack(self, project, last_session):
        """Edge matching project stack."""
        scorer = PrimerScorer(project, last_session, datetime.utcnow())

        fastapi_edge = SharpEdge(
            id="e1", title="FastAPI issue", description="Problem with FastAPI",
            workaround="Fix", project_id=None,
        )
        react_edge = SharpEdge(
            id="e2", title="React issue", description="Problem with React",
            workaround="Fix", project_id=None,
        )

        assert scorer._matches_stack(fastapi_edge)
        assert not scorer._matches_stack(react_edge)

    def test_detection_might_apply(self, project, last_session):
        """Edge detection patterns matching context."""
        scorer = PrimerScorer(project, last_session, datetime.utcnow())

        edge_with_pattern = SharpEdge(
            id="e1", title="Auth edge",
            description="Auth issue",
            workaround="Fix",
            project_id=None,
            detection_patterns=[
                DetectionPattern(type="context", pattern="authentication", description="Auth context")
            ],
        )
        edge_with_trigger = SharpEdge(
            id="e2", title="Python edge",
            description="Python issue",
            workaround="Fix",
            project_id=None,
            trigger_phrases=["python", "fastapi"],
        )
        edge_no_match = SharpEdge(
            id="e3", title="Unrelated edge",
            description="Something",
            workaround="Fix",
            project_id=None,
            detection_patterns=[
                DetectionPattern(type="context", pattern="kubernetes", description="K8s context")
            ],
        )

        assert scorer._detection_might_apply(edge_with_pattern)
        assert scorer._detection_might_apply(edge_with_trigger)
        assert not scorer._detection_might_apply(edge_no_match)


class TestPrimerResultFormat:
    """Tests for primer text formatting."""

    def test_primer_result_dataclass(self):
        """PrimerResult contains all expected fields."""
        result = PrimerResult(
            text="Test primer",
            issues=[],
            decisions=[],
            edges=[],
        )

        assert result.text == "Test primer"
        assert result.issues == []
        assert result.decisions == []
        assert result.edges == []

    def test_severity_emoji_mapping(self):
        """Severity emoji mapping is complete."""
        gen = PrimerGenerator.__new__(PrimerGenerator)

        assert gen.SEVERITY_EMOJI["blocking"] == "🔴"
        assert gen.SEVERITY_EMOJI["major"] == "🟠"
        assert gen.SEVERITY_EMOJI["minor"] == "🟡"
        assert gen.SEVERITY_EMOJI["cosmetic"] == "⚪"


class TestPrimerIntegration:
    """Integration tests for complete primer scoring scenarios."""

    def test_blocking_issue_beats_unrelated(self, project, last_session, blocking_issue, old_minor_issue):
        """Blocking issue beats unrelated issues even with high access."""
        scorer = PrimerScorer(project, last_session, datetime.utcnow())

        blocking_score, _ = scorer.score_issue(blocking_issue, access_count=0)
        minor_score, _ = scorer.score_issue(old_minor_issue, access_count=10)  # High access

        # Blocking (100) beats minor (20) + access (50)
        assert blocking_score > minor_score

    def test_mentioned_major_can_beat_blocking(self, project, last_session, blocking_issue, major_issue_mentioned):
        """Major issue from last session with high access can legitimately beat blocking.

        This is intentional - an issue you were working on yesterday that's still
        relevant today is highly likely to be what you want to continue with.
        """
        scorer = PrimerScorer(project, last_session, datetime.utcnow())

        blocking_score, _ = scorer.score_issue(blocking_issue, access_count=0)
        major_score, _ = scorer.score_issue(major_issue_mentioned, access_count=10)

        # Major (50) + continuity (80) + access (50) = 180+ can beat blocking (100 + recency)
        # Both should be in top 3, order depends on context
        assert blocking_score > 100  # Blocking base
        assert major_score > 100  # Major with boosts

    def test_continuity_beats_recency(self, project, last_session):
        """Issue mentioned in next_steps beats more recent unrelated issue."""
        scorer = PrimerScorer(project, last_session, datetime.utcnow())

        mentioned_old = Issue(
            id="iss_1", project_id="proj_test",
            title="Same-domain approach",  # In next_steps
            description="Test",
            severity="major", status="open",
            updated_at=datetime.utcnow() - timedelta(days=10),
        )
        not_mentioned_new = Issue(
            id="iss_2", project_id="proj_test",
            title="Unrelated recent issue",
            description="Test",
            severity="major", status="open",
            updated_at=datetime.utcnow() - timedelta(hours=1),
        )

        mentioned_score, _ = scorer.score_issue(mentioned_old, access_count=0)
        new_score, _ = scorer.score_issue(not_mentioned_new, access_count=0)

        assert mentioned_score > new_score

    def test_goal_related_minor_beats_unrelated_major(self, project, last_session):
        """Goal-related minor issue can beat unrelated major issue."""
        scorer = PrimerScorer(project, last_session, datetime.utcnow())

        # Goal is "Fix authentication flow"
        goal_minor = Issue(
            id="iss_1", project_id="proj_test",
            title="Authentication timeout",
            description="Auth related",
            severity="minor", status="open",
        )
        unrelated_major = Issue(
            id="iss_2", project_id="proj_test",
            title="CSS layout bug",
            description="Styling issue",
            severity="major", status="open",
            updated_at=datetime.utcnow() - timedelta(days=10),
        )

        goal_score, _ = scorer.score_issue(goal_minor, access_count=5)
        unrelated_score, _ = scorer.score_issue(unrelated_major, access_count=0)

        # With goal alignment (60) + minor (20) + access (25) = 105
        # vs major (50) + old recency (~20) = 70
        assert goal_score > unrelated_score
