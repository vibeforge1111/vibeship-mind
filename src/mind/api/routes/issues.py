"""Issue routes for the HTTP API."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from mind.models import Issue, IssueCreate, IssueUpdate, Attempt
from mind.storage.sqlite import SQLiteStorage
from mind.api.deps import get_storage
from mind.api.errors import not_found
from mind.api.responses import ListResponse, DEFAULT_LIMIT


router = APIRouter(prefix="/issues", tags=["issues"])


class IssueUpdateRequest(BaseModel):
    """Request body for updating an issue."""
    status: Optional[str] = None
    current_theory: Optional[str] = None
    blocked_by: Optional[str] = None
    resolution: Optional[str] = None
    add_attempt: Optional[Attempt] = None


@router.get("/project/{project_id}")
async def list_issues(
    project_id: str,
    status: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
    storage: SQLiteStorage = Depends(get_storage),
) -> ListResponse[Issue]:
    """List issues for a project."""
    # Verify project exists
    project = await storage.get_project(project_id)
    if not project:
        raise not_found("Project", project_id)

    issues = await storage.list_issues(project_id, status=status)
    has_more = len(issues) > limit
    return ListResponse(
        items=issues[:limit],
        count=min(len(issues), limit),
        has_more=has_more,
    )


@router.get("/project/{project_id}/open")
async def list_open_issues(
    project_id: str,
    limit: int = DEFAULT_LIMIT,
    storage: SQLiteStorage = Depends(get_storage),
) -> ListResponse[Issue]:
    """List open issues for a project (sorted by severity)."""
    # Verify project exists
    project = await storage.get_project(project_id)
    if not project:
        raise not_found("Project", project_id)

    issues = await storage.list_open_issues(project_id)
    has_more = len(issues) > limit
    return ListResponse(
        items=issues[:limit],
        count=min(len(issues), limit),
        has_more=has_more,
    )


@router.post("", status_code=201)
async def create_issue(
    data: IssueCreate,
    storage: SQLiteStorage = Depends(get_storage),
) -> Issue:
    """Create a new issue."""
    # Verify project exists
    project = await storage.get_project(data.project_id)
    if not project:
        raise not_found("Project", data.project_id)

    return await storage.create_issue(data)


@router.get("/{issue_id}")
async def get_issue(
    issue_id: str,
    storage: SQLiteStorage = Depends(get_storage),
) -> Issue:
    """Get an issue by ID."""
    issue = await storage.get_issue(issue_id)
    if not issue:
        raise not_found("Issue", issue_id)
    return issue


@router.patch("/{issue_id}")
async def update_issue(
    issue_id: str,
    data: IssueUpdateRequest,
    storage: SQLiteStorage = Depends(get_storage),
) -> Issue:
    """Update an issue."""
    issue = await storage.get_issue(issue_id)
    if not issue:
        raise not_found("Issue", issue_id)

    # Convert to storage update model
    storage_update = IssueUpdate(
        status=data.status,
        current_theory=data.current_theory,
        blocked_by=data.blocked_by,
        resolution=data.resolution,
        add_attempt=data.add_attempt,
    )

    updated = await storage.update_issue(issue_id, storage_update)
    if not updated:
        raise not_found("Issue", issue_id)
    return updated
