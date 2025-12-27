"""Shared fixtures for integration tests."""

import asyncio
from datetime import UTC, datetime
from typing import AsyncGenerator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from mind.infrastructure.postgres.models import Base, UserModel


# Test user ID (consistent across tests)
TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for session-scoped async fixtures."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container with pgvector for the test session."""
    # Use pgvector image
    container = PostgresContainer(
        image="pgvector/pgvector:pg16",
        username="test",
        password="test",
        dbname="mind_test",
    )
    container.start()

    yield container

    container.stop()


@pytest.fixture(scope="session")
def postgres_url(postgres_container: PostgresContainer) -> str:
    """Get async PostgreSQL URL from container."""
    # Get sync URL and convert to async
    sync_url = postgres_container.get_connection_url()
    # Replace psycopg2 with asyncpg
    async_url = sync_url.replace("psycopg2", "asyncpg")
    async_url = async_url.replace("postgresql://", "postgresql+asyncpg://")
    return async_url


@pytest.fixture(scope="session")
async def engine(postgres_url: str):
    """Create async SQLAlchemy engine."""
    engine = create_async_engine(
        postgres_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
    )

    async with engine.begin() as conn:
        # Enable extensions
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector"'))

        # Create tables without vector index (ivfflat requires data)
        # Drop existing tables first for clean slate
        await conn.run_sync(Base.metadata.drop_all)

        # Create tables - skip vector index for now
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                # Skip problematic indexes that require data
                checkfirst=True,
            )
        )

        # Create test user
        await conn.execute(
            text("""
                INSERT INTO users (user_id, external_id)
                VALUES (:user_id, 'test-user')
                ON CONFLICT DO NOTHING
            """),
            {"user_id": str(TEST_USER_ID)},
        )

    yield engine

    await engine.dispose()


@pytest.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for each test."""
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session
        # Rollback to clean up test data
        await session.rollback()


@pytest.fixture
def user_id() -> UUID:
    """Get consistent test user ID."""
    return TEST_USER_ID


@pytest.fixture
def sample_memory_data(user_id: UUID) -> dict:
    """Sample memory data for tests."""
    return {
        "memory_id": uuid4(),
        "user_id": user_id,
        "content": "User prefers detailed explanations with examples",
        "content_type": "preference",
        "temporal_level": 4,  # IDENTITY
        "valid_from": datetime.now(UTC),
        "valid_until": None,
        "base_salience": 0.8,
        "outcome_adjustment": 0.0,
    }


@pytest.fixture
def sample_trace_data(user_id: UUID) -> dict:
    """Sample decision trace data for tests."""
    return {
        "trace_id": uuid4(),
        "user_id": user_id,
        "session_id": uuid4(),
        "context_memory_ids": [],
        "memory_scores": {},
        "decision_type": "recommendation",
        "decision_summary": "Recommended detailed explanation approach",
        "confidence": 0.85,
        "alternatives_count": 2,
    }
