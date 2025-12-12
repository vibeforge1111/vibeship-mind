"""Project routes for the HTTP API."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from mind.models import Project, ProjectCreate
from mind.storage.sqlite import SQLiteStorage
from mind.api.deps import get_storage
from mind.api.errors import not_found, validation_error
from mind.api.responses import ListResponse, DEFAULT_LIMIT


router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectUpdate(BaseModel):
    """Request body for updating a project."""
    name: Optional[str] = None
    current_goal: Optional[str] = None
    stack: Optional[list[str]] = None
    blocked_by: Optional[list[str]] = None
    open_threads: Optional[list[str]] = None
    status: Optional[str] = None


@router.get("")
async def list_projects(
    limit: int = DEFAULT_LIMIT,
    storage: SQLiteStorage = Depends(get_storage),
) -> ListResponse[Project]:
    """List all projects."""
    projects = await storage.list_projects(limit=limit + 1)
    return ListResponse.from_items(projects, limit=limit)


@router.post("", status_code=201)
async def create_project(
    data: ProjectCreate,
    storage: SQLiteStorage = Depends(get_storage),
) -> Project:
    """Create a new project."""
    # Check for duplicate name
    existing = await storage.get_project_by_name(data.name)
    if existing:
        raise validation_error(
            "Project with this name already exists",
            {"name": f"'{data.name}' already exists"},
        )
    return await storage.create_project(data)


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    storage: SQLiteStorage = Depends(get_storage),
) -> Project:
    """Get a project by ID."""
    project = await storage.get_project(project_id)
    if not project:
        raise not_found("Project", project_id)
    return project


@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    storage: SQLiteStorage = Depends(get_storage),
) -> Project:
    """Update a project."""
    project = await storage.get_project(project_id)
    if not project:
        raise not_found("Project", project_id)

    # Check if any fields are being updated
    updates = data.model_dump(exclude_none=True)
    if not updates:
        return project  # Nothing to update

    # Convert API update model to storage update model
    from mind.models import ProjectUpdate as StorageProjectUpdate
    storage_update = StorageProjectUpdate(
        current_goal=data.current_goal,
        blocked_by=data.blocked_by,
        open_threads=data.open_threads,
        status=data.status,
        add_to_stack=data.stack,  # API uses 'stack', storage uses 'add_to_stack'
    )

    updated = await storage.update_project(project_id, storage_update)
    if not updated:
        raise not_found("Project", project_id)
    return updated


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    cascade: bool = True,
    storage: SQLiteStorage = Depends(get_storage),
) -> None:
    """Delete a project.

    Args:
        project_id: Project ID to delete
        cascade: If True, delete all related data (decisions, issues, etc.)
    """
    project = await storage.get_project(project_id)
    if not project:
        raise not_found("Project", project_id)

    await storage.delete_project(project_id, cascade=cascade)
