"""Session routes for the HTTP API."""

from fastapi import APIRouter, Depends
from typing import Optional

from mind.models import Session
from mind.storage.sqlite import SQLiteStorage
from mind.api.deps import get_storage
from mind.api.errors import not_found
from mind.api.responses import ListResponse, DEFAULT_LIMIT


router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/project/{project_id}")
async def list_sessions(
    project_id: str,
    status: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
    storage: SQLiteStorage = Depends(get_storage),
) -> ListResponse[Session]:
    """List sessions for a project."""
    # Verify project exists
    project = await storage.get_project(project_id)
    if not project:
        raise not_found("Project", project_id)

    # Get sessions - need to add list_sessions to storage
    # For now, we'll use a direct query approach
    sessions = await _list_sessions(storage, project_id, status, limit + 1)
    has_more = len(sessions) > limit
    return ListResponse(
        items=sessions[:limit],
        count=min(len(sessions), limit),
        has_more=has_more,
    )


@router.get("/project/{project_id}/active")
async def get_active_session(
    project_id: str,
    storage: SQLiteStorage = Depends(get_storage),
) -> Session:
    """Get the active session for a project.

    Shortcut for finding the current active session.
    """
    # Verify project exists
    project = await storage.get_project(project_id)
    if not project:
        raise not_found("Project", project_id)

    session = await storage.get_active_session(project_id)
    if not session:
        raise not_found("Active session for project", project_id)
    return session


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    storage: SQLiteStorage = Depends(get_storage),
) -> Session:
    """Get a session by ID."""
    session = await storage.get_session(session_id)
    if not session:
        raise not_found("Session", session_id)
    return session


async def _list_sessions(
    storage: SQLiteStorage,
    project_id: str,
    status: Optional[str],
    limit: int,
) -> list[Session]:
    """List sessions for a project.

    Helper until we add list_sessions to storage.
    """
    if status:
        query = """SELECT * FROM sessions
                   WHERE project_id = ? AND status = ?
                   ORDER BY started_at DESC LIMIT ?"""
        params = (project_id, status, limit)
    else:
        query = """SELECT * FROM sessions
                   WHERE project_id = ?
                   ORDER BY started_at DESC LIMIT ?"""
        params = (project_id, limit)

    async with storage.db.execute(query, params) as cursor:
        rows = await cursor.fetchall()
        return [storage._row_to_session(row) for row in rows]
