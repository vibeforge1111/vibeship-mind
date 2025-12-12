"""Episode routes for the HTTP API.

Episodes are read-only - they're created automatically by session end.
"""

from fastapi import APIRouter, Depends

from mind.models import Episode
from mind.storage.sqlite import SQLiteStorage
from mind.api.deps import get_storage
from mind.api.errors import not_found
from mind.api.responses import ListResponse, DEFAULT_LIMIT


router = APIRouter(prefix="/episodes", tags=["episodes"])


@router.get("/project/{project_id}")
async def list_episodes(
    project_id: str,
    limit: int = DEFAULT_LIMIT,
    storage: SQLiteStorage = Depends(get_storage),
) -> ListResponse[Episode]:
    """List episodes for a project."""
    # Verify project exists
    project = await storage.get_project(project_id)
    if not project:
        raise not_found("Project", project_id)

    episodes = await storage.list_episodes(project_id)
    has_more = len(episodes) > limit
    return ListResponse(
        items=episodes[:limit],
        count=min(len(episodes), limit),
        has_more=has_more,
    )


@router.get("/{episode_id}")
async def get_episode(
    episode_id: str,
    storage: SQLiteStorage = Depends(get_storage),
) -> Episode:
    """Get an episode by ID."""
    episode = await storage.get_episode(episode_id)
    if not episode:
        raise not_found("Episode", episode_id)
    return episode
