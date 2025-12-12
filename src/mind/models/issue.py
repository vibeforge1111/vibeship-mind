"""Issue model - problems with investigation history."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field

from mind.models.base import MindBaseModel, generate_id


class Attempt(MindBaseModel):
    """A solution attempt."""
    what: str  # What we tried
    result: str  # What happened
    learned: Optional[str] = None  # What we learned
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Issue(MindBaseModel):
    """Problems with investigation history."""

    id: str = Field(default_factory=lambda: generate_id("iss"))
    project_id: str

    # The problem
    title: str
    description: str
    severity: Literal["blocking", "major", "minor", "cosmetic"] = "major"
    status: Literal["open", "investigating", "blocked", "resolved", "wont_fix"] = "open"

    # Investigation
    attempts: list[Attempt] = Field(default_factory=list)
    current_theory: Optional[str] = None
    blocked_by: Optional[str] = None

    # Resolution
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by_decision: Optional[str] = None

    # Connections
    related_decisions: list[str] = Field(default_factory=list)
    related_edges: list[str] = Field(default_factory=list)
    caused_by_episode: Optional[str] = None

    # Retrieval
    symptoms: list[str] = Field(default_factory=list)
    trigger_phrases: list[str] = Field(default_factory=list)

    # Metadata
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None

    @property
    def embedding_text(self) -> str:
        """Text for embedding generation."""
        parts = [self.title, self.description]
        parts.extend(self.symptoms)
        if self.current_theory:
            parts.append(self.current_theory)
        return ". ".join(parts)


class IssueCreate(MindBaseModel):
    """For creating new issues."""
    project_id: str
    title: str
    description: str
    severity: Literal["blocking", "major", "minor", "cosmetic"] = "major"
    symptoms: list[str] = Field(default_factory=list)


class IssueUpdate(MindBaseModel):
    """For updating issues."""
    status: Optional[Literal["open", "investigating", "blocked", "resolved", "wont_fix"]] = None
    add_attempt: Optional[Attempt] = None
    current_theory: Optional[str] = None
    blocked_by: Optional[str] = None
    resolution: Optional[str] = None
