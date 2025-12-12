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
