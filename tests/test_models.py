"""Tests for Mind data models."""

import pytest
from datetime import datetime

from mind.models import (
    Project, ProjectCreate,
    Decision, DecisionCreate, Alternative,
    Issue, IssueCreate, Attempt,
    SharpEdge, SharpEdgeCreate, DetectionPattern,
    Episode, EpisodeCreate,
    UserModel,
    Session,
)


class TestProject:
    """Tests for Project model."""

    def test_create_project(self):
        """Test creating a project."""
        project = Project(name="test-project")

        assert project.name == "test-project"
        assert project.id.startswith("proj_")
        assert project.status == "active"
        assert project.stack == []
        assert project.blocked_by == []

    def test_project_create_dto(self):
        """Test ProjectCreate DTO."""
        dto = ProjectCreate(
            name="my-app",
            description="A test application",
            stack=["python", "fastapi"],
            repo_path="/path/to/repo",
        )

        assert dto.name == "my-app"
        assert dto.description == "A test application"
        assert dto.stack == ["python", "fastapi"]


class TestDecision:
    """Tests for Decision model."""

    def test_create_decision(self):
        """Test creating a decision."""
        decision = Decision(
            project_id="proj_123",
            title="Use FastAPI",
            description="Use FastAPI for the backend API",
            context="Need a modern async Python framework",
            reasoning="FastAPI is fast, has good DX, and great docs",
        )

        assert decision.id.startswith("dec_")
        assert decision.confidence == 0.7
        assert decision.status == "active"

    def test_decision_with_alternatives(self):
        """Test decision with alternatives."""
        decision = Decision(
            project_id="proj_123",
            title="Use SQLite",
            description="Use SQLite for local storage",
            context="Need persistent storage",
            reasoning="Simple, no server needed",
            alternatives=[
                Alternative(option="PostgreSQL", rejected_because="Too heavy for local use"),
                Alternative(option="Redis", rejected_because="Not persistent by default"),
            ],
        )

        assert len(decision.alternatives) == 2
        assert decision.alternatives[0].option == "PostgreSQL"

    def test_embedding_text(self):
        """Test embedding text generation."""
        decision = Decision(
            project_id="proj_123",
            title="Use TypeScript",
            description="Use TypeScript for frontend",
            context="Need type safety",
            reasoning="Catches errors at compile time",
        )

        text = decision.embedding_text
        assert "Use TypeScript" in text
        assert "compile time" in text


class TestIssue:
    """Tests for Issue model."""

    def test_create_issue(self):
        """Test creating an issue."""
        issue = Issue(
            project_id="proj_123",
            title="Auth not working",
            description="Users can't log in",
        )

        assert issue.id.startswith("iss_")
        assert issue.severity == "major"
        assert issue.status == "open"
        assert issue.attempts == []

    def test_issue_with_attempts(self):
        """Test issue with solution attempts."""
        issue = Issue(
            project_id="proj_123",
            title="Slow queries",
            description="Database queries are slow",
            attempts=[
                Attempt(what="Added index", result="No improvement", learned="Not an index issue"),
                Attempt(what="Checked N+1", result="Found the issue", learned="N+1 query pattern"),
            ],
        )

        assert len(issue.attempts) == 2
        assert issue.attempts[1].learned == "N+1 query pattern"


class TestSharpEdge:
    """Tests for SharpEdge model."""

    def test_create_edge(self):
        """Test creating a sharp edge."""
        edge = SharpEdge(
            title="No Node crypto in Edge",
            description="Edge functions can't use Node crypto module",
            workaround="Use Web Crypto API instead",
        )

        assert edge.id.startswith("edge_")
        assert edge.project_id is None  # Global edge

    def test_edge_with_patterns(self):
        """Test edge with detection patterns."""
        edge = SharpEdge(
            title="SQLite concurrent writes",
            description="SQLite doesn't handle concurrent writes well",
            workaround="Use WAL mode and serialize writes",
            detection_patterns=[
                DetectionPattern(
                    type="code",
                    pattern=r"sqlite3\.connect",
                    description="SQLite connection",
                ),
                DetectionPattern(
                    type="context",
                    pattern="concurrent|parallel",
                    description="Concurrent access context",
                ),
            ],
        )

        assert len(edge.detection_patterns) == 2
        assert edge.detection_patterns[0].type == "code"


class TestEpisode:
    """Tests for Episode model."""

    def test_create_episode(self):
        """Test creating an episode."""
        episode = Episode(
            project_id="proj_123",
            session_id="sess_456",
            title="The Great Debugging Session",
            narrative="We spent hours tracking down a bug...",
            started_at=datetime(2024, 1, 1, 10, 0),
            ended_at=datetime(2024, 1, 1, 14, 0),
            duration_minutes=240,
            summary="Found and fixed the auth bug",
        )

        assert episode.id.startswith("ep_")
        assert episode.duration_minutes == 240


class TestUserModel:
    """Tests for UserModel."""

    def test_create_user(self):
        """Test creating a user model."""
        user = UserModel()

        assert user.id.startswith("user_")
        assert user.total_sessions == 0
        assert user.patterns.prefers_shipping_over_perfection is True


class TestSession:
    """Tests for Session model."""

    def test_create_session(self):
        """Test creating a session."""
        session = Session(
            project_id="proj_123",
            user_id="user_456",
        )

        assert session.id.startswith("sess_")
        assert session.status == "active"
        assert session.decisions_made == []
