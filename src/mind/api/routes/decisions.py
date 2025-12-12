"""Decision routes for the HTTP API."""

from fastapi import APIRouter, Depends
from typing import Optional

from mind.models import Decision, DecisionCreate
from mind.storage.sqlite import SQLiteStorage
from mind.api.deps import get_storage
from mind.api.errors import not_found
from mind.api.responses import ListResponse, DEFAULT_LIMIT


router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("/project/{project_id}")
async def list_decisions(
    project_id: str,
    status: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
    storage: SQLiteStorage = Depends(get_storage),
) -> ListResponse[Decision]:
    """List decisions for a project."""
    # Verify project exists
    project = await storage.get_project(project_id)
    if not project:
        raise not_found("Project", project_id)

    decisions = await storage.list_decisions(project_id, status=status)
    # Apply limit manually since storage doesn't support it yet
    has_more = len(decisions) > limit
    return ListResponse(
        items=decisions[:limit],
        count=min(len(decisions), limit),
        has_more=has_more,
    )


@router.post("", status_code=201)
async def create_decision(
    data: DecisionCreate,
    storage: SQLiteStorage = Depends(get_storage),
) -> Decision:
    """Create a new decision."""
    # Verify project exists
    project = await storage.get_project(data.project_id)
    if not project:
        raise not_found("Project", data.project_id)

    return await storage.create_decision(data)


@router.get("/{decision_id}")
async def get_decision(
    decision_id: str,
    storage: SQLiteStorage = Depends(get_storage),
) -> Decision:
    """Get a decision by ID."""
    decision = await storage.get_decision(decision_id)
    if not decision:
        raise not_found("Decision", decision_id)
    return decision
