"""Session model - container for a conversation."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field

from mind.models.base import MindBaseModel, generate_id
from mind.models.project import Project
from mind.models.decision import Decision
from mind.models.issue import Issue
from mind.models.sharp_edge import SharpEdge


class Message(MindBaseModel):
    """A message in the session (optional storage)."""
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Session(MindBaseModel):
    """Container for a conversation."""

    id: str = Field(default_factory=lambda: generate_id("sess"))
    project_id: str
    user_id: str

    # Lifecycle
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    status: Literal["active", "ended", "abandoned"] = "active"

    # Context loaded at start
    primer_content: Optional[str] = None
    memories_surfaced: list[str] = Field(default_factory=list)

    # What happened
    messages: list[Message] = Field(default_factory=list)

    # Captured at end
    summary: Optional[str] = None
    progress: list[str] = Field(default_factory=list)
    still_open: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    mood: Optional[str] = None

    # Artifacts created during session
    decisions_made: list[str] = Field(default_factory=list)
    issues_opened: list[str] = Field(default_factory=list)
    issues_updated: list[str] = Field(default_factory=list)
    issues_resolved: list[str] = Field(default_factory=list)
    edges_discovered: list[str] = Field(default_factory=list)

    # If significant enough to become episode
    episode_id: Optional[str] = None


class SessionStart(MindBaseModel):
    """Response when starting a session."""
    session_id: str
    project: Project
    primer: str
    open_issues: list[Issue] = Field(default_factory=list)
    pending_decisions: list[Decision] = Field(default_factory=list)
    relevant_edges: list[SharpEdge] = Field(default_factory=list)


class SessionEnd(MindBaseModel):
    """Request when ending a session."""
    summary: str
    progress: list[str] = Field(default_factory=list)
    still_open: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    mood: Optional[str] = None
    episode_title: Optional[str] = None  # Override auto-generated episode title
