"""Sharp Edge model - gotchas with detection patterns."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field

from mind.models.base import MindBaseModel, generate_id


class DetectionPattern(MindBaseModel):
    """Pattern for detecting when edge might be hit."""
    type: Literal["code", "context", "intent"]
    pattern: str  # Regex for code, keywords for context/intent
    description: str  # Human readable explanation
    file_pattern: Optional[str] = None  # e.g., "*.edge.ts"


class SharpEdge(MindBaseModel):
    """Gotchas with detection patterns."""

    id: str = Field(default_factory=lambda: generate_id("edge"))
    project_id: Optional[str] = None  # None = global edge

    # The gotcha
    title: str
    description: str

    # Detection
    detection_patterns: list[DetectionPattern] = Field(default_factory=list)
    trigger_phrases: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)

    # Solution
    workaround: str
    root_cause: Optional[str] = None
    proper_fix: Optional[str] = None

    # Origin
    discovered_in_episode: Optional[str] = None
    discovered_at: datetime = Field(default_factory=datetime.utcnow)

    # Connections
    related_decisions: list[str] = Field(default_factory=list)
    related_issues: list[str] = Field(default_factory=list)

    # For community registry
    submitted_by: Optional[str] = None
    verification_count: int = 0
    verified_by: list[str] = Field(default_factory=list)

    @property
    def embedding_text(self) -> str:
        """Text for embedding generation."""
        parts = [self.title, self.description, self.workaround]
        parts.extend(self.symptoms)
        return ". ".join(parts)


class SharpEdgeCreate(MindBaseModel):
    """For creating new sharp edges."""
    title: str
    description: str
    workaround: str
    detection_patterns: list[DetectionPattern] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    project_id: Optional[str] = None
    root_cause: Optional[str] = None
