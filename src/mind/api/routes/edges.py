"""Sharp edge routes for the HTTP API."""

from fastapi import APIRouter, Depends
from typing import Optional

from mind.models import SharpEdge, SharpEdgeCreate
from mind.storage.sqlite import SQLiteStorage
from mind.api.deps import get_storage
from mind.api.errors import not_found
from mind.api.responses import ListResponse, DEFAULT_LIMIT


router = APIRouter(prefix="/edges", tags=["edges"])


@router.get("")
async def list_edges(
    project_id: Optional[str] = None,
    global_only: bool = False,
    limit: int = DEFAULT_LIMIT,
    storage: SQLiteStorage = Depends(get_storage),
) -> ListResponse[SharpEdge]:
    """List sharp edges.

    Args:
        project_id: If provided, includes global edges + project-specific edges
        global_only: If True, only return global edges (project_id=None)
        limit: Maximum number of edges to return
    """
    if global_only:
        # Only global edges
        edges = await storage.list_sharp_edges(project_id=None)
        # Filter to only those with no project_id
        edges = [e for e in edges if e.project_id is None]
    elif project_id:
        # Verify project exists
        project = await storage.get_project(project_id)
        if not project:
            raise not_found("Project", project_id)
        # Global + project-specific
        edges = await storage.list_sharp_edges(project_id=project_id)
    else:
        # All edges
        edges = await storage.list_sharp_edges()

    has_more = len(edges) > limit
    return ListResponse(
        items=edges[:limit],
        count=min(len(edges), limit),
        has_more=has_more,
    )


@router.post("", status_code=201)
async def create_edge(
    data: SharpEdgeCreate,
    storage: SQLiteStorage = Depends(get_storage),
) -> SharpEdge:
    """Create a new sharp edge.

    If project_id is None, creates a global edge.
    """
    # Verify project exists if specified
    if data.project_id:
        project = await storage.get_project(data.project_id)
        if not project:
            raise not_found("Project", data.project_id)

    return await storage.create_sharp_edge(data)


@router.get("/{edge_id}")
async def get_edge(
    edge_id: str,
    storage: SQLiteStorage = Depends(get_storage),
) -> SharpEdge:
    """Get a sharp edge by ID."""
    edge = await storage.get_sharp_edge(edge_id)
    if not edge:
        raise not_found("SharpEdge", edge_id)
    return edge
