"""Episode model - narrative of significant sessions."""

from datetime import datetime
from typing import Optional

from pydantic import Field

from mind.models.base import MindBaseModel, generate_id


class MoodPoint(MindBaseModel):
    """A point in the emotional arc."""
    timestamp: datetime
    mood: str  # "frustrated", "curious", "breakthrough", etc.
    trigger: Optional[str] = None  # What caused the shift


class Episode(MindBaseModel):
    """Narrative of significant sessions."""

    id: str = Field(default_factory=lambda: generate_id("ep"))
    project_id: str
    session_id: str

    # The story
    title: str  # "The Great Auth Debugging Session"
    narrative: str  # What happened, in prose

    # Timeline
    started_at: datetime
    ended_at: datetime
    duration_minutes: int

    # Emotional arc
    mood_arc: list[MoodPoint] = Field(default_factory=list)
    overall_mood: Optional[str] = None

    # Outcomes
    lessons: list[str] = Field(default_factory=list)
    breakthroughs: list[str] = Field(default_factory=list)
    frustrations: list[str] = Field(default_factory=list)

    # Artifacts created
    decisions_made: list[str] = Field(default_factory=list)
    issues_opened: list[str] = Field(default_factory=list)
    issues_resolved: list[str] = Field(default_factory=list)
    edges_discovered: list[str] = Field(default_factory=list)

    # Retrieval
    keywords: list[str] = Field(default_factory=list)
    summary: str  # Short version for embedding

    @property
    def embedding_text(self) -> str:
        """Text for embedding generation."""
        return f"{self.title}. {self.summary}"


class EpisodeCreate(MindBaseModel):
    """For creating episodes (usually auto-generated)."""
    project_id: str
    session_id: str
    title: str
    narrative: str
    started_at: datetime
    ended_at: datetime
    lessons: list[str] = Field(default_factory=list)
    breakthroughs: list[str] = Field(default_factory=list)
    summary: str
