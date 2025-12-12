"""Tests for the HTTP API."""

import pytest
from httpx import AsyncClient, ASGITransport

from mind.api.server import create_app
from mind.api import deps


@pytest.fixture
def app(storage):
    """Create test app with test storage."""
    # Override the storage dependency
    async def get_test_storage():
        return storage

    app = create_app()
    app.dependency_overrides[deps.get_storage] = get_test_storage
    return app


@pytest.fixture
async def client(app):
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestSystemRoutes:
    """Test system routes."""

    @pytest.mark.asyncio
    async def test_status(self, client):
        """GET /status returns server status and stats."""
        response = await client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"
        assert "timestamp" in data
        assert "stats" in data
        assert data["stats"]["projects"] == 0
        assert data["stats"]["decisions"] == 0
        assert data["stats"]["issues"] == 0
        assert data["stats"]["edges"] == 0
        assert data["stats"]["episodes"] == 0


class TestProjectRoutes:
    """Test project CRUD routes."""

    @pytest.mark.asyncio
    async def test_create_project(self, client):
        """POST /projects creates a new project."""
        response = await client.post(
            "/projects",
            json={"name": "Test Project", "description": "A test project"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["description"] == "A test project"
        assert data["status"] == "active"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_duplicate_project(self, client, storage):
        """POST /projects with duplicate name returns 400."""
        from mind.models import ProjectCreate

        # Create via storage first
        await storage.create_project(ProjectCreate(name="Existing"))

        response = await client.post(
            "/projects",
            json={"name": "Existing"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert "already exists" in data["error"]

    @pytest.mark.asyncio
    async def test_list_projects_empty(self, client):
        """GET /projects returns empty list when no projects."""
        response = await client.get("/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["count"] == 0
        assert data["has_more"] is False

    @pytest.mark.asyncio
    async def test_list_projects(self, client, storage):
        """GET /projects returns all projects."""
        from mind.models import ProjectCreate

        # Create some projects
        await storage.create_project(ProjectCreate(name="Project A"))
        await storage.create_project(ProjectCreate(name="Project B"))

        response = await client.get("/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["items"]) == 2
        names = {p["name"] for p in data["items"]}
        assert names == {"Project A", "Project B"}

    @pytest.mark.asyncio
    async def test_list_projects_with_limit(self, client, storage):
        """GET /projects respects limit parameter."""
        from mind.models import ProjectCreate

        # Create 5 projects
        for i in range(5):
            await storage.create_project(ProjectCreate(name=f"Project {i}"))

        response = await client.get("/projects?limit=3")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert data["has_more"] is True

    @pytest.mark.asyncio
    async def test_get_project(self, client, storage):
        """GET /projects/{id} returns the project."""
        from mind.models import ProjectCreate

        project = await storage.create_project(ProjectCreate(name="My Project"))

        response = await client.get(f"/projects/{project.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project.id
        assert data["name"] == "My Project"

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, client):
        """GET /projects/{id} returns 404 for unknown ID."""
        response = await client.get("/projects/unknown-id")

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_project(self, client, storage):
        """PATCH /projects/{id} updates the project."""
        from mind.models import ProjectCreate

        project = await storage.create_project(ProjectCreate(name="Original"))

        response = await client.patch(
            f"/projects/{project.id}",
            json={"current_goal": "New goal", "status": "paused"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["current_goal"] == "New goal"
        assert data["status"] == "paused"

    @pytest.mark.asyncio
    async def test_update_project_not_found(self, client):
        """PATCH /projects/{id} returns 404 for unknown ID."""
        response = await client.patch(
            "/projects/unknown-id",
            json={"current_goal": "Some goal"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_project(self, client, storage):
        """DELETE /projects/{id} removes the project."""
        from mind.models import ProjectCreate

        project = await storage.create_project(ProjectCreate(name="To Delete"))

        response = await client.delete(f"/projects/{project.id}")

        assert response.status_code == 204

        # Verify it's gone
        deleted = await storage.get_project(project.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_project_cascade(self, client, storage):
        """DELETE /projects/{id} cascades to related entities."""
        from mind.models import ProjectCreate, DecisionCreate, IssueCreate

        # Create project with related data
        project = await storage.create_project(ProjectCreate(name="To Delete"))
        await storage.create_decision(DecisionCreate(
            project_id=project.id,
            title="Test Decision",
            description="A decision",
            context="Context",
            reasoning="Because",
        ))
        await storage.create_issue(IssueCreate(
            project_id=project.id,
            title="Test Issue",
            description="An issue",
        ))

        # Verify data exists
        decisions = await storage.list_decisions(project.id)
        issues = await storage.list_issues(project.id)
        assert len(decisions) == 1
        assert len(issues) == 1

        # Delete with cascade (default)
        response = await client.delete(f"/projects/{project.id}")
        assert response.status_code == 204

        # Verify all data is gone
        decisions = await storage.list_decisions(project.id)
        issues = await storage.list_issues(project.id)
        assert len(decisions) == 0
        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_delete_project_not_found(self, client):
        """DELETE /projects/{id} returns 404 for unknown ID."""
        response = await client.delete("/projects/unknown-id")

        assert response.status_code == 404


class TestEndToEndFlow:
    """Test complete workflows."""

    @pytest.mark.asyncio
    async def test_project_lifecycle(self, client):
        """Test create -> list -> get -> update -> delete flow."""
        # 1. Create
        create_resp = await client.post(
            "/projects",
            json={"name": "E2E Test", "description": "End to end test"},
        )
        assert create_resp.status_code == 201
        project_id = create_resp.json()["id"]

        # 2. List - should contain our project
        list_resp = await client.get("/projects")
        assert list_resp.status_code == 200
        assert list_resp.json()["count"] == 1
        assert list_resp.json()["items"][0]["id"] == project_id

        # 3. Get by ID
        get_resp = await client.get(f"/projects/{project_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "E2E Test"

        # 4. Update
        update_resp = await client.patch(
            f"/projects/{project_id}",
            json={"current_goal": "Complete E2E test"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["current_goal"] == "Complete E2E test"

        # 5. Delete
        delete_resp = await client.delete(f"/projects/{project_id}")
        assert delete_resp.status_code == 204

        # 6. Verify deletion
        verify_resp = await client.get(f"/projects/{project_id}")
        assert verify_resp.status_code == 404

        # 7. List should be empty
        final_list_resp = await client.get("/projects")
        assert final_list_resp.json()["count"] == 0


class TestDecisionRoutes:
    """Test decision routes."""

    @pytest.mark.asyncio
    async def test_create_decision(self, client, storage):
        """POST /decisions creates a new decision."""
        from mind.models import ProjectCreate

        project = await storage.create_project(ProjectCreate(name="Test"))

        response = await client.post(
            "/decisions",
            json={
                "project_id": project.id,
                "title": "Use FastAPI",
                "description": "We chose FastAPI for the HTTP API",
                "context": "Need an HTTP API",
                "reasoning": "FastAPI is fast and has good docs",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Use FastAPI"
        assert data["project_id"] == project.id

    @pytest.mark.asyncio
    async def test_create_decision_project_not_found(self, client):
        """POST /decisions returns 404 for unknown project."""
        response = await client.post(
            "/decisions",
            json={
                "project_id": "unknown",
                "title": "Test",
                "description": "Test",
                "context": "Test",
                "reasoning": "Test",
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_decisions(self, client, storage):
        """GET /decisions/project/{id} lists decisions."""
        from mind.models import ProjectCreate, DecisionCreate

        project = await storage.create_project(ProjectCreate(name="Test"))
        await storage.create_decision(DecisionCreate(
            project_id=project.id,
            title="Decision 1",
            description="First",
            context="Context",
            reasoning="Why",
        ))
        await storage.create_decision(DecisionCreate(
            project_id=project.id,
            title="Decision 2",
            description="Second",
            context="Context",
            reasoning="Why",
        ))

        response = await client.get(f"/decisions/project/{project.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2

    @pytest.mark.asyncio
    async def test_get_decision(self, client, storage):
        """GET /decisions/{id} returns the decision."""
        from mind.models import ProjectCreate, DecisionCreate

        project = await storage.create_project(ProjectCreate(name="Test"))
        decision = await storage.create_decision(DecisionCreate(
            project_id=project.id,
            title="My Decision",
            description="Details",
            context="Context",
            reasoning="Why",
        ))

        response = await client.get(f"/decisions/{decision.id}")

        assert response.status_code == 200
        assert response.json()["title"] == "My Decision"


class TestIssueRoutes:
    """Test issue routes."""

    @pytest.mark.asyncio
    async def test_create_issue(self, client, storage):
        """POST /issues creates a new issue."""
        from mind.models import ProjectCreate

        project = await storage.create_project(ProjectCreate(name="Test"))

        response = await client.post(
            "/issues",
            json={
                "project_id": project.id,
                "title": "Bug in login",
                "description": "Users can't log in",
                "severity": "blocking",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Bug in login"
        assert data["severity"] == "blocking"
        assert data["status"] == "open"

    @pytest.mark.asyncio
    async def test_list_issues(self, client, storage):
        """GET /issues/project/{id} lists issues."""
        from mind.models import ProjectCreate, IssueCreate

        project = await storage.create_project(ProjectCreate(name="Test"))
        await storage.create_issue(IssueCreate(
            project_id=project.id,
            title="Issue 1",
            description="First",
        ))
        await storage.create_issue(IssueCreate(
            project_id=project.id,
            title="Issue 2",
            description="Second",
        ))

        response = await client.get(f"/issues/project/{project.id}")

        assert response.status_code == 200
        assert response.json()["count"] == 2

    @pytest.mark.asyncio
    async def test_list_open_issues(self, client, storage):
        """GET /issues/project/{id}/open lists open issues by severity."""
        from mind.models import ProjectCreate, IssueCreate, IssueUpdate

        project = await storage.create_project(ProjectCreate(name="Test"))
        issue1 = await storage.create_issue(IssueCreate(
            project_id=project.id,
            title="Minor bug",
            description="Small issue",
            severity="minor",
        ))
        await storage.create_issue(IssueCreate(
            project_id=project.id,
            title="Blocking bug",
            description="Can't work",
            severity="blocking",
        ))
        # Resolve issue1
        await storage.update_issue(issue1.id, IssueUpdate(status="resolved"))

        response = await client.get(f"/issues/project/{project.id}/open")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["items"][0]["title"] == "Blocking bug"

    @pytest.mark.asyncio
    async def test_update_issue(self, client, storage):
        """PATCH /issues/{id} updates the issue."""
        from mind.models import ProjectCreate, IssueCreate

        project = await storage.create_project(ProjectCreate(name="Test"))
        issue = await storage.create_issue(IssueCreate(
            project_id=project.id,
            title="Bug",
            description="A bug",
        ))

        response = await client.patch(
            f"/issues/{issue.id}",
            json={
                "status": "investigating",
                "current_theory": "Might be a race condition",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "investigating"
        assert data["current_theory"] == "Might be a race condition"


class TestEdgeRoutes:
    """Test sharp edge routes."""

    @pytest.mark.asyncio
    async def test_create_global_edge(self, client):
        """POST /edges creates a global edge when project_id is None."""
        response = await client.post(
            "/edges",
            json={
                "title": "SQLite WAL mode gotcha",
                "description": "WAL mode requires specific settings",
                "workaround": "Set journal_mode=WAL explicitly",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "SQLite WAL mode gotcha"
        assert data["project_id"] is None

    @pytest.mark.asyncio
    async def test_create_project_edge(self, client, storage):
        """POST /edges creates a project-specific edge."""
        from mind.models import ProjectCreate

        project = await storage.create_project(ProjectCreate(name="Test"))

        response = await client.post(
            "/edges",
            json={
                "project_id": project.id,
                "title": "Project-specific gotcha",
                "description": "Only applies to this project",
                "workaround": "Do this instead",
            },
        )

        assert response.status_code == 201
        assert response.json()["project_id"] == project.id

    @pytest.mark.asyncio
    async def test_list_edges_all(self, client, storage):
        """GET /edges lists all edges."""
        from mind.models import SharpEdgeCreate

        await storage.create_sharp_edge(SharpEdgeCreate(
            title="Global edge",
            description="Applies everywhere",
            workaround="Fix it",
        ))

        response = await client.get("/edges")

        assert response.status_code == 200
        assert response.json()["count"] == 1

    @pytest.mark.asyncio
    async def test_list_edges_global_only(self, client, storage):
        """GET /edges?global_only=true lists only global edges."""
        from mind.models import ProjectCreate, SharpEdgeCreate

        project = await storage.create_project(ProjectCreate(name="Test"))
        await storage.create_sharp_edge(SharpEdgeCreate(
            title="Global edge",
            description="Applies everywhere",
            workaround="Fix it",
        ))
        await storage.create_sharp_edge(SharpEdgeCreate(
            project_id=project.id,
            title="Project edge",
            description="Only this project",
            workaround="Fix it",
        ))

        response = await client.get("/edges?global_only=true")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["items"][0]["title"] == "Global edge"


class TestEpisodeRoutes:
    """Test episode routes (read-only)."""

    @pytest.mark.asyncio
    async def test_list_episodes(self, client, storage):
        """GET /episodes/project/{id} lists episodes."""
        from mind.models import ProjectCreate, EpisodeCreate
        from datetime import datetime, timedelta

        project = await storage.create_project(ProjectCreate(name="Test"))
        now = datetime.utcnow()
        await storage.create_episode(EpisodeCreate(
            project_id=project.id,
            session_id="sess-1",
            title="First session",
            narrative="Did some work",
            started_at=now - timedelta(hours=2),
            ended_at=now - timedelta(hours=1),
            summary="Worked on features",
        ))

        response = await client.get(f"/episodes/project/{project.id}")

        assert response.status_code == 200
        assert response.json()["count"] == 1

    @pytest.mark.asyncio
    async def test_get_episode(self, client, storage):
        """GET /episodes/{id} returns the episode."""
        from mind.models import ProjectCreate, EpisodeCreate
        from datetime import datetime, timedelta

        project = await storage.create_project(ProjectCreate(name="Test"))
        now = datetime.utcnow()
        episode = await storage.create_episode(EpisodeCreate(
            project_id=project.id,
            session_id="sess-1",
            title="My Session",
            narrative="Did things",
            started_at=now - timedelta(hours=2),
            ended_at=now - timedelta(hours=1),
            summary="Summary",
        ))

        response = await client.get(f"/episodes/{episode.id}")

        assert response.status_code == 200
        assert response.json()["title"] == "My Session"


class TestSessionRoutes:
    """Test session routes."""

    @pytest.mark.asyncio
    async def test_list_sessions(self, client, storage):
        """GET /sessions/project/{id} lists sessions."""
        from mind.models import ProjectCreate

        project = await storage.create_project(ProjectCreate(name="Test"))
        user = await storage.get_or_create_user()
        await storage.create_session(project.id, user.id)
        await storage.create_session(project.id, user.id)

        response = await client.get(f"/sessions/project/{project.id}")

        assert response.status_code == 200
        assert response.json()["count"] == 2

    @pytest.mark.asyncio
    async def test_get_active_session(self, client, storage):
        """GET /sessions/project/{id}/active returns the active session."""
        from mind.models import ProjectCreate

        project = await storage.create_project(ProjectCreate(name="Test"))
        user = await storage.get_or_create_user()
        session = await storage.create_session(project.id, user.id)

        response = await client.get(f"/sessions/project/{project.id}/active")

        assert response.status_code == 200
        assert response.json()["id"] == session.id
        assert response.json()["status"] == "active"

    @pytest.mark.asyncio
    async def test_get_active_session_not_found(self, client, storage):
        """GET /sessions/project/{id}/active returns 404 when no active session."""
        from mind.models import ProjectCreate

        project = await storage.create_project(ProjectCreate(name="Test"))

        response = await client.get(f"/sessions/project/{project.id}/active")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_session(self, client, storage):
        """GET /sessions/{id} returns the session."""
        from mind.models import ProjectCreate

        project = await storage.create_project(ProjectCreate(name="Test"))
        user = await storage.get_or_create_user()
        session = await storage.create_session(project.id, user.id)

        response = await client.get(f"/sessions/{session.id}")

        assert response.status_code == 200
        assert response.json()["project_id"] == project.id


class TestUserRoutes:
    """Test user model routes."""

    @pytest.mark.asyncio
    async def test_get_user(self, client):
        """GET /user returns the user model."""
        response = await client.get("/user")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "total_sessions" in data

    @pytest.mark.asyncio
    async def test_update_user(self, client):
        """PATCH /user updates the user model."""
        response = await client.patch(
            "/user",
            json={
                "name": "Test User",
                "current_energy": "high",
                "current_focus": "API development",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test User"
        assert data["current_energy"] == "high"
        assert data["current_focus"] == "API development"

    @pytest.mark.asyncio
    async def test_update_user_add_win(self, client):
        """PATCH /user can add a win."""
        response = await client.patch(
            "/user",
            json={"add_win": "Completed the HTTP API"},
        )

        assert response.status_code == 200
        assert "Completed the HTTP API" in response.json()["recent_wins"]


class TestSearchRoutes:
    """Test search routes."""

    @pytest.mark.asyncio
    async def test_search(self, client, storage):
        """GET /search returns matching entities."""
        from mind.models import ProjectCreate, DecisionCreate, IssueCreate

        project = await storage.create_project(ProjectCreate(name="Test"))
        await storage.create_decision(DecisionCreate(
            project_id=project.id,
            title="Use FastAPI for HTTP",
            description="FastAPI is our choice",
            context="Need HTTP API",
            reasoning="Good docs",
        ))
        await storage.create_issue(IssueCreate(
            project_id=project.id,
            title="FastAPI installation issue",
            description="Pip install failed",
        ))

        response = await client.get(f"/search?q=FastAPI&project_id={project.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "FastAPI"
        assert data["total"] == 2
        assert len(data["decisions"]) == 1
        assert len(data["issues"]) == 1

    @pytest.mark.asyncio
    async def test_search_no_results(self, client, storage):
        """GET /search returns empty when no matches."""
        from mind.models import ProjectCreate

        project = await storage.create_project(ProjectCreate(name="Test"))

        response = await client.get(f"/search?q=nonexistent&project_id={project.id}")

        assert response.status_code == 200
        assert response.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_search_project_not_found(self, client):
        """GET /search returns 404 for unknown project."""
        response = await client.get("/search?q=test&project_id=unknown")

        assert response.status_code == 404


class TestExportRoutes:
    """Test export routes."""

    @pytest.mark.asyncio
    async def test_export_all(self, client, storage):
        """GET /export exports all data."""
        from mind.models import ProjectCreate, DecisionCreate

        project = await storage.create_project(ProjectCreate(name="Test"))
        await storage.create_decision(DecisionCreate(
            project_id=project.id,
            title="A Decision",
            description="Details",
            context="Context",
            reasoning="Why",
        ))

        response = await client.get("/export")

        assert response.status_code == 200
        data = response.json()
        assert "exported_at" in data
        assert len(data["projects"]) == 1
        assert len(data["decisions"]) == 1

    @pytest.mark.asyncio
    async def test_export_single_project(self, client, storage):
        """GET /export?project_id=X exports only that project."""
        from mind.models import ProjectCreate, DecisionCreate

        project1 = await storage.create_project(ProjectCreate(name="Project 1"))
        project2 = await storage.create_project(ProjectCreate(name="Project 2"))
        await storage.create_decision(DecisionCreate(
            project_id=project1.id,
            title="Decision 1",
            description="D1",
            context="C",
            reasoning="R",
        ))
        await storage.create_decision(DecisionCreate(
            project_id=project2.id,
            title="Decision 2",
            description="D2",
            context="C",
            reasoning="R",
        ))

        response = await client.get(f"/export?project_id={project1.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["projects"]) == 1
        assert data["projects"][0]["name"] == "Project 1"
        assert len(data["decisions"]) == 1
        assert data["decisions"][0]["title"] == "Decision 1"

    @pytest.mark.asyncio
    async def test_export_with_sessions(self, client, storage):
        """GET /export?include_sessions=true includes sessions."""
        from mind.models import ProjectCreate

        project = await storage.create_project(ProjectCreate(name="Test"))
        user = await storage.get_or_create_user()
        await storage.create_session(project.id, user.id)

        response = await client.get("/export?include_sessions=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 1

    @pytest.mark.asyncio
    async def test_export_project_not_found(self, client):
        """GET /export?project_id=X returns 404 for unknown project."""
        response = await client.get("/export?project_id=unknown")

        assert response.status_code == 404
