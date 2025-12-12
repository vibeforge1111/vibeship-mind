"""Export routes for the HTTP API."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from mind.storage.sqlite import SQLiteStorage
from mind.api.deps import get_storage
from mind.api.errors import not_found


router = APIRouter(prefix="/export", tags=["export"])


class ExportData(BaseModel):
    """Exported Mind data."""
    exported_at: str
    format: str
    project_id: Optional[str]
    projects: list[dict]
    decisions: list[dict]
    issues: list[dict]
    edges: list[dict]
    episodes: list[dict]
    sessions: list[dict]


@router.get("")
async def export_data(
    project_id: Optional[str] = None,
    include_sessions: bool = False,
    storage: SQLiteStorage = Depends(get_storage),
) -> ExportData:
    """Export Mind data as JSON.

    Args:
        project_id: Export specific project only (None = all projects)
        include_sessions: Include session history in export
    """
    # If project_id specified, verify it exists
    if project_id:
        project = await storage.get_project(project_id)
        if not project:
            raise not_found("Project", project_id)
        projects = [project]
    else:
        projects = await storage.list_projects()

    export = {
        "exported_at": datetime.utcnow().isoformat(),
        "format": "json",
        "project_id": project_id,
        "projects": [],
        "decisions": [],
        "issues": [],
        "edges": [],
        "episodes": [],
        "sessions": [],
    }

    for p in projects:
        export["projects"].append(p.model_dump(mode="json"))

        decisions = await storage.list_decisions(p.id)
        export["decisions"].extend([d.model_dump(mode="json") for d in decisions])

        issues = await storage.list_issues(p.id)
        export["issues"].extend([i.model_dump(mode="json") for i in issues])

        episodes = await storage.list_episodes(p.id)
        export["episodes"].extend([e.model_dump(mode="json") for e in episodes])

        if include_sessions:
            # Get sessions via direct query
            async with storage.db.execute(
                "SELECT * FROM sessions WHERE project_id = ? ORDER BY started_at DESC",
                (p.id,),
            ) as cursor:
                rows = await cursor.fetchall()
                sessions = [storage._row_to_session(row) for row in rows]
                export["sessions"].extend([s.model_dump(mode="json") for s in sessions])

    # Get edges (global + project-specific)
    edges = await storage.list_sharp_edges(project_id)
    export["edges"] = [e.model_dump(mode="json") for e in edges]

    return ExportData(**export)
