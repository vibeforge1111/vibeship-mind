"""Search routes for the HTTP API."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from mind.models import Decision, Issue, SharpEdge, Episode
from mind.storage.sqlite import SQLiteStorage
from mind.api.deps import get_storage
from mind.api.errors import not_found


router = APIRouter(prefix="/search", tags=["search"])


class SearchResults(BaseModel):
    """Search results across all entity types."""
    query: str
    project_id: str
    decisions: list[Decision]
    issues: list[Issue]
    edges: list[SharpEdge]
    episodes: list[Episode]
    total: int


@router.get("")
async def search(
    q: str,
    project_id: str,
    storage: SQLiteStorage = Depends(get_storage),
) -> SearchResults:
    """Search across all entities in a project.

    Args:
        q: Search query (searches titles, descriptions, etc.)
        project_id: Project to search within
    """
    # Verify project exists
    project = await storage.get_project(project_id)
    if not project:
        raise not_found("Project", project_id)

    results = await storage.search_all(project_id, q)

    return SearchResults(
        query=q,
        project_id=project_id,
        decisions=results["decisions"],
        issues=results["issues"],
        edges=results["edges"],
        episodes=results["episodes"],
        total=(
            len(results["decisions"]) +
            len(results["issues"]) +
            len(results["edges"]) +
            len(results["episodes"])
        ),
    )
