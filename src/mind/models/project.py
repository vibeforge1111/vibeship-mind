"""Project model - current state of a project."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field

from mind.models.base import MindBaseModel, generate_id


class Project(MindBaseModel):
    """The current state of a project. Not history—the now."""

    id: str = Field(default_factory=lambda: generate_id("proj"))
    name: str
    description: Optional[str] = None
    status: Literal["active", "paused", "archived"] = "active"

    # Tech context
    stack: list[str] = Field(default_factory=list)
    repo_path: Optional[str] = None

    # Current focus
    current_goal: Optional[str] = None
    blocked_by: list[str] = Field(default_factory=list)
    open_threads: list[str] = Field(default_factory=list)

    # Session tracking
    last_session_id: Optional[str] = None
    last_session_date: Optional[datetime] = None
    last_session_summary: Optional[str] = None
    last_session_mood: Optional[str] = None
    last_session_next_step: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectCreate(MindBaseModel):
    """For creating new projects."""
    name: str
    description: Optional[str] = None
    stack: list[str] = Field(default_factory=list)
    repo_path: Optional[str] = None


class ProjectUpdate(MindBaseModel):
    """For updating project state."""
    current_goal: Optional[str] = None
    blocked_by: Optional[list[str]] = None
    open_threads: Optional[list[str]] = None
    status: Optional[Literal["active", "paused", "archived"]] = None
    add_to_stack: Optional[list[str]] = None
