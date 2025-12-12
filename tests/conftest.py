"""Pytest configuration and fixtures."""

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio

from mind.storage.sqlite import SQLiteStorage


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def storage() -> AsyncGenerator[SQLiteStorage, None]:
    """Create a temporary SQLite storage for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_mind.db"
        store = SQLiteStorage(db_path)
        await store.initialize()
        yield store
        await store.close()


@pytest.fixture
def temp_data_dir() -> Path:
    """Create a temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
