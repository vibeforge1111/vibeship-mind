"""System routes for the HTTP API."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import datetime

from mind.storage.sqlite import SQLiteStorage
from mind.api.deps import get_storage


router = APIRouter(tags=["system"])


class StatusResponse(BaseModel):
    """Health check and stats response."""
    status: str
    version: str
    timestamp: str
    stats: dict


@router.get("/status")
async def get_status(
    storage: SQLiteStorage = Depends(get_storage),
) -> StatusResponse:
    """Get server status and stats."""
    # Count entities
    projects = await storage.list_projects(limit=1000)
    project_count = len(projects)

    # Count other entities across all projects
    decision_count = 0
    issue_count = 0
    edge_count = 0
    episode_count = 0

    for project in projects:
        decisions = await storage.list_decisions(project.id, limit=1000)
        decision_count += len(decisions)

        issues = await storage.list_issues(project.id, limit=1000)
        issue_count += len(issues)

        episodes = await storage.list_episodes(project.id, limit=1000)
        episode_count += len(episodes)

    # Global edges
    edges = await storage.list_sharp_edges(project_id=None)
    edge_count = len(edges)

    return StatusResponse(
        status="ok",
        version="0.1.0",
        timestamp=datetime.utcnow().isoformat(),
        stats={
            "projects": project_count,
            "decisions": decision_count,
            "issues": issue_count,
            "edges": edge_count,
            "episodes": episode_count,
        },
    )
