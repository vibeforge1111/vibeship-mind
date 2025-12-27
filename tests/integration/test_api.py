"""Integration tests for API endpoints."""

from datetime import UTC, datetime
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from mind.api.app import create_app
from mind.infrastructure.postgres.database import Database


pytestmark = pytest.mark.asyncio


@pytest.fixture
async def app(postgres_url: str, engine):
    """Create test application with database."""
    app = create_app()

    # Override database
    test_db = Database(url=postgres_url)

    # Patch get_database to return test instance
    with patch("mind.api.routes.memories.get_database", return_value=test_db):
        with patch("mind.api.routes.decisions.get_database", return_value=test_db):
            with patch("mind.api.routes.health.get_database", return_value=test_db):
                yield app

    await test_db.close()


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    async def test_liveness(self, client: AsyncClient):
        """Health check should return ok."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_readiness(self, client: AsyncClient):
        """Readiness check should return component status."""
        response = await client.get("/ready")

        # May fail if DB not connected, but should return 200
        assert response.status_code == 200
        data = response.json()
        assert "database" in data
        assert "nats" in data


class TestMemoryEndpoints:
    """Tests for memory API endpoints."""

    async def test_create_memory(self, client: AsyncClient, user_id):
        """Creating a memory via API should work."""
        payload = {
            "user_id": str(user_id),
            "content": "User prefers Python over JavaScript",
            "content_type": "preference",
            "temporal_level": 4,
            "salience": 0.8,
        }

        response = await client.post("/v1/memories/", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["content"] == payload["content"]
        assert data["temporal_level"] == 4
        assert "memory_id" in data

    async def test_create_memory_invalid_temporal_level(
        self,
        client: AsyncClient,
        user_id,
    ):
        """Creating memory with invalid temporal level should fail."""
        payload = {
            "user_id": str(user_id),
            "content": "Test content",
            "content_type": "fact",
            "temporal_level": 10,  # Invalid
            "salience": 0.5,
        }

        response = await client.post("/v1/memories/", json=payload)

        assert response.status_code == 422  # Validation error

    async def test_get_memory(self, client: AsyncClient, user_id):
        """Getting a memory by ID should work."""
        # First create a memory
        payload = {
            "user_id": str(user_id),
            "content": "Test memory for retrieval",
            "content_type": "fact",
            "temporal_level": 2,
            "salience": 0.7,
        }
        create_response = await client.post("/v1/memories/", json=payload)
        memory_id = create_response.json()["memory_id"]

        # Then get it
        response = await client.get(f"/v1/memories/{memory_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["memory_id"] == memory_id
        assert data["content"] == payload["content"]

    async def test_get_nonexistent_memory(self, client: AsyncClient):
        """Getting nonexistent memory should return 404."""
        fake_id = str(uuid4())

        response = await client.get(f"/v1/memories/{fake_id}")

        assert response.status_code == 404

    async def test_retrieve_memories(self, client: AsyncClient, user_id):
        """Retrieving memories should return relevant results."""
        # Create some memories
        for i in range(3):
            payload = {
                "user_id": str(user_id),
                "content": f"Memory content {i}",
                "content_type": "fact",
                "temporal_level": 2,
                "salience": 0.5 + (i * 0.1),
            }
            await client.post("/v1/memories/", json=payload)

        # Retrieve
        retrieve_payload = {
            "user_id": str(user_id),
            "query": "memory content",
            "limit": 10,
        }

        # Mock embedder since we don't have OpenAI key in tests
        with patch("mind.api.routes.memories.get_embedder") as mock_embedder:
            mock_embedder.return_value.embed = AsyncMock(return_value=[0.1] * 1536)

            response = await client.post("/v1/memories/retrieve", json=retrieve_payload)

        assert response.status_code == 200
        data = response.json()
        assert "memories" in data
        assert "retrieval_id" in data


class TestDecisionEndpoints:
    """Tests for decision tracking API endpoints."""

    async def test_create_decision_trace(self, client: AsyncClient, user_id):
        """Creating a decision trace should work."""
        payload = {
            "user_id": str(user_id),
            "session_id": str(uuid4()),
            "memory_ids": [],
            "memory_scores": {},
            "decision_type": "recommendation",
            "decision_summary": "Recommended option A",
            "confidence": 0.85,
            "alternatives_count": 3,
        }

        response = await client.post("/v1/decisions/track", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert "trace_id" in data
        assert "created_at" in data

    async def test_record_outcome(self, client: AsyncClient, user_id):
        """Recording an outcome should work."""
        # Create trace
        trace_payload = {
            "user_id": str(user_id),
            "session_id": str(uuid4()),
            "memory_ids": [],
            "memory_scores": {},
            "decision_type": "action",
            "decision_summary": "Selected action",
            "confidence": 0.8,
        }
        trace_response = await client.post("/v1/decisions/track", json=trace_payload)
        trace_id = trace_response.json()["trace_id"]

        # Record outcome
        outcome_payload = {
            "trace_id": trace_id,
            "quality": 0.7,
            "signal": "user_accepted",
        }

        response = await client.post("/v1/decisions/outcome", json=outcome_payload)

        assert response.status_code == 200
        data = response.json()
        assert data["trace_id"] == trace_id
        assert data["outcome_quality"] == 0.7
        assert "memories_updated" in data

    async def test_record_outcome_twice_fails(self, client: AsyncClient, user_id):
        """Recording outcome twice should fail."""
        # Create trace
        trace_payload = {
            "user_id": str(user_id),
            "session_id": str(uuid4()),
            "memory_ids": [],
            "memory_scores": {},
            "decision_type": "action",
            "decision_summary": "Selected action",
            "confidence": 0.8,
        }
        trace_response = await client.post("/v1/decisions/track", json=trace_payload)
        trace_id = trace_response.json()["trace_id"]

        # Record first outcome
        outcome_payload = {
            "trace_id": trace_id,
            "quality": 0.5,
            "signal": "test",
        }
        await client.post("/v1/decisions/outcome", json=outcome_payload)

        # Second recording should fail
        response = await client.post("/v1/decisions/outcome", json=outcome_payload)

        assert response.status_code == 400

    async def test_record_outcome_nonexistent_trace(self, client: AsyncClient):
        """Recording outcome for nonexistent trace should fail."""
        outcome_payload = {
            "trace_id": str(uuid4()),
            "quality": 0.5,
            "signal": "test",
        }

        response = await client.post("/v1/decisions/outcome", json=outcome_payload)

        assert response.status_code == 404


class TestMetricsEndpoint:
    """Tests for Prometheus metrics endpoint."""

    async def test_metrics_endpoint(self, client: AsyncClient):
        """Metrics endpoint should return Prometheus format."""
        response = await client.get("/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        # Should contain some Mind metrics
        content = response.text
        assert "mind_" in content or "python_" in content
