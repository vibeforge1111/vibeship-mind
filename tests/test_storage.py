"""Tests for SQLite storage."""

import pytest
from datetime import datetime

from mind.models import (
    ProjectCreate, ProjectUpdate,
    DecisionCreate, Alternative,
    IssueCreate, IssueUpdate, Attempt,
    SharpEdgeCreate, DetectionPattern,
    SessionEnd,
)
from mind.storage.sqlite import SQLiteStorage


class TestProjectStorage:
    """Tests for project storage operations."""

    @pytest.mark.asyncio
    async def test_create_project(self, storage: SQLiteStorage):
        """Test creating a project."""
        project = await storage.create_project(
            ProjectCreate(name="test-project", description="A test project")
        )

        assert project.id.startswith("proj_")
        assert project.name == "test-project"
        assert project.description == "A test project"

    @pytest.mark.asyncio
    async def test_get_project(self, storage: SQLiteStorage):
        """Test getting a project by ID."""
        created = await storage.create_project(ProjectCreate(name="get-test"))

        fetched = await storage.get_project(created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == "get-test"

    @pytest.mark.asyncio
    async def test_get_project_by_name(self, storage: SQLiteStorage):
        """Test getting a project by name."""
        await storage.create_project(ProjectCreate(name="by-name-test"))

        fetched = await storage.get_project_by_name("by-name-test")

        assert fetched is not None
        assert fetched.name == "by-name-test"

    @pytest.mark.asyncio
    async def test_list_projects(self, storage: SQLiteStorage):
        """Test listing projects."""
        await storage.create_project(ProjectCreate(name="project-1"))
        await storage.create_project(ProjectCreate(name="project-2"))

        projects = await storage.list_projects()

        assert len(projects) >= 2
        names = [p.name for p in projects]
        assert "project-1" in names
        assert "project-2" in names

    @pytest.mark.asyncio
    async def test_update_project(self, storage: SQLiteStorage):
        """Test updating a project."""
        project = await storage.create_project(ProjectCreate(name="update-test"))

        updated = await storage.update_project(
            project.id,
            ProjectUpdate(current_goal="Build MVP", blocked_by=["Time"]),
        )

        assert updated is not None
        assert updated.current_goal == "Build MVP"
        assert updated.blocked_by == ["Time"]


class TestDecisionStorage:
    """Tests for decision storage operations."""

    @pytest.mark.asyncio
    async def test_create_decision(self, storage: SQLiteStorage):
        """Test creating a decision."""
        project = await storage.create_project(ProjectCreate(name="decision-test"))

        decision = await storage.create_decision(
            DecisionCreate(
                project_id=project.id,
                title="Use Python",
                description="Use Python for the backend",
                context="Need a backend language",
                reasoning="Team knows Python",
                alternatives=[
                    Alternative(option="Go", rejected_because="Team doesn't know Go"),
                ],
            )
        )

        assert decision.id.startswith("dec_")
        assert decision.title == "Use Python"
        assert len(decision.alternatives) == 1

    @pytest.mark.asyncio
    async def test_list_decisions(self, storage: SQLiteStorage):
        """Test listing decisions."""
        project = await storage.create_project(ProjectCreate(name="list-decisions"))

        await storage.create_decision(
            DecisionCreate(
                project_id=project.id,
                title="Decision 1",
                description="First decision",
                context="Context",
                reasoning="Reasoning",
            )
        )
        await storage.create_decision(
            DecisionCreate(
                project_id=project.id,
                title="Decision 2",
                description="Second decision",
                context="Context",
                reasoning="Reasoning",
            )
        )

        decisions = await storage.list_decisions(project.id)

        assert len(decisions) == 2


class TestIssueStorage:
    """Tests for issue storage operations."""

    @pytest.mark.asyncio
    async def test_create_issue(self, storage: SQLiteStorage):
        """Test creating an issue."""
        project = await storage.create_project(ProjectCreate(name="issue-test"))

        issue = await storage.create_issue(
            IssueCreate(
                project_id=project.id,
                title="Bug in login",
                description="Users can't log in",
                severity="blocking",
                symptoms=["500 error", "Session not created"],
            )
        )

        assert issue.id.startswith("iss_")
        assert issue.severity == "blocking"
        assert len(issue.symptoms) == 2

    @pytest.mark.asyncio
    async def test_update_issue_with_attempt(self, storage: SQLiteStorage):
        """Test adding an attempt to an issue."""
        project = await storage.create_project(ProjectCreate(name="attempt-test"))
        issue = await storage.create_issue(
            IssueCreate(
                project_id=project.id,
                title="Performance issue",
                description="App is slow",
            )
        )

        updated = await storage.update_issue(
            issue.id,
            IssueUpdate(
                status="investigating",
                add_attempt=Attempt(
                    what="Added caching",
                    result="Improved by 50%",
                    learned="Caching helps",
                ),
                current_theory="Database queries are slow",
            ),
        )

        assert updated is not None
        assert updated.status == "investigating"
        assert len(updated.attempts) == 1
        assert updated.current_theory == "Database queries are slow"

    @pytest.mark.asyncio
    async def test_list_open_issues(self, storage: SQLiteStorage):
        """Test listing open issues."""
        project = await storage.create_project(ProjectCreate(name="open-issues"))

        # Create issues with different statuses
        await storage.create_issue(
            IssueCreate(project_id=project.id, title="Open 1", description="Open issue", severity="blocking")
        )
        await storage.create_issue(
            IssueCreate(project_id=project.id, title="Open 2", description="Open issue", severity="minor")
        )

        issue3 = await storage.create_issue(
            IssueCreate(project_id=project.id, title="Resolved", description="Resolved issue")
        )
        await storage.update_issue(issue3.id, IssueUpdate(status="resolved", resolution="Fixed"))

        open_issues = await storage.list_open_issues(project.id)

        assert len(open_issues) == 2
        # Should be sorted by severity (blocking first)
        assert open_issues[0].severity == "blocking"


class TestSharpEdgeStorage:
    """Tests for sharp edge storage operations."""

    @pytest.mark.asyncio
    async def test_create_global_edge(self, storage: SQLiteStorage):
        """Test creating a global sharp edge."""
        edge = await storage.create_sharp_edge(
            SharpEdgeCreate(
                title="No eval in production",
                description="Never use eval() in production code",
                workaround="Use safer alternatives like JSON.parse()",
                project_id=None,  # Global
            )
        )

        assert edge.id.startswith("edge_")
        assert edge.project_id is None

    @pytest.mark.asyncio
    async def test_create_project_edge(self, storage: SQLiteStorage):
        """Test creating a project-specific edge."""
        project = await storage.create_project(ProjectCreate(name="edge-project"))

        edge = await storage.create_sharp_edge(
            SharpEdgeCreate(
                title="Don't use ORM for bulk",
                description="ORM is slow for bulk operations",
                workaround="Use raw SQL for bulk inserts",
                project_id=project.id,
                detection_patterns=[
                    DetectionPattern(
                        type="code",
                        pattern=r"for.*in.*:\s*session\.add",
                        description="Loop with ORM add",
                    ),
                ],
            )
        )

        assert edge.project_id == project.id
        assert len(edge.detection_patterns) == 1

    @pytest.mark.asyncio
    async def test_list_edges_includes_global(self, storage: SQLiteStorage):
        """Test that listing edges includes global edges."""
        project = await storage.create_project(ProjectCreate(name="edges-list"))

        # Create global edge
        await storage.create_sharp_edge(
            SharpEdgeCreate(
                title="Global edge",
                description="A global gotcha",
                workaround="Do this instead",
            )
        )

        # Create project edge
        await storage.create_sharp_edge(
            SharpEdgeCreate(
                title="Project edge",
                description="Project-specific gotcha",
                workaround="Do that instead",
                project_id=project.id,
            )
        )

        edges = await storage.list_sharp_edges(project.id)

        # Should include both global and project edges
        assert len(edges) >= 2


class TestSessionStorage:
    """Tests for session storage operations."""

    @pytest.mark.asyncio
    async def test_create_session(self, storage: SQLiteStorage):
        """Test creating a session."""
        project = await storage.create_project(ProjectCreate(name="session-test"))
        user = await storage.get_or_create_user()

        session = await storage.create_session(project.id, user.id)

        assert session.id.startswith("sess_")
        assert session.project_id == project.id
        assert session.status == "active"

    @pytest.mark.asyncio
    async def test_end_session(self, storage: SQLiteStorage):
        """Test ending a session."""
        project = await storage.create_project(ProjectCreate(name="end-session"))
        user = await storage.get_or_create_user()
        session = await storage.create_session(project.id, user.id)

        ended = await storage.end_session(
            session.id,
            SessionEnd(
                summary="Good session",
                progress=["Fixed bug", "Added feature"],
                still_open=["Performance issue"],
                next_steps=["Optimize queries"],
                mood="Productive",
            ),
        )

        assert ended is not None
        assert ended.status == "ended"
        assert ended.summary == "Good session"
        assert len(ended.progress) == 2


class TestUserStorage:
    """Tests for user storage operations."""

    @pytest.mark.asyncio
    async def test_get_or_create_user(self, storage: SQLiteStorage):
        """Test getting or creating user."""
        user1 = await storage.get_or_create_user()
        user2 = await storage.get_or_create_user()

        # Should return the same user
        assert user1.id == user2.id

    @pytest.mark.asyncio
    async def test_increment_sessions(self, storage: SQLiteStorage):
        """Test incrementing user sessions."""
        project = await storage.create_project(ProjectCreate(name="sessions-count"))

        user1 = await storage.get_or_create_user()
        initial_count = user1.total_sessions

        await storage.increment_user_sessions(project.id)

        user2 = await storage.get_or_create_user()
        assert user2.total_sessions == initial_count + 1
        assert project.id in user2.projects


class TestSearchStorage:
    """Tests for search operations."""

    @pytest.mark.asyncio
    async def test_search_all(self, storage: SQLiteStorage):
        """Test searching across all entities."""
        project = await storage.create_project(ProjectCreate(name="search-test"))

        # Create some searchable content
        await storage.create_decision(
            DecisionCreate(
                project_id=project.id,
                title="Use PostgreSQL",
                description="Use PostgreSQL for the database",
                context="Need a database",
                reasoning="Robust and scalable",
            )
        )
        await storage.create_issue(
            IssueCreate(
                project_id=project.id,
                title="PostgreSQL connection error",
                description="Can't connect to PostgreSQL",
            )
        )

        results = await storage.search_all(project.id, "PostgreSQL")

        assert len(results["decisions"]) >= 1
        assert len(results["issues"]) >= 1
