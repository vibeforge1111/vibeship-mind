"""Database connection and session management."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from mind.config import get_settings


class Database:
    """Async PostgreSQL database connection manager."""

    def __init__(self, url: str | None = None):
        settings = get_settings()
        self._url = url or settings.postgres_url

        self._engine = create_async_engine(
            self._url,
            echo=settings.debug,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )

        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session."""
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def close(self) -> None:
        """Close database connections."""
        await self._engine.dispose()

    @property
    def engine(self):
        """Get the SQLAlchemy engine."""
        return self._engine


# Global database instance
_database: Database | None = None


def get_database() -> Database:
    """Get or create database instance."""
    global _database
    if _database is None:
        _database = Database()
    return _database


async def init_database() -> Database:
    """Initialize database and return instance."""
    return get_database()


async def close_database() -> None:
    """Close database connections."""
    global _database
    if _database is not None:
        await _database.close()
        _database = None
