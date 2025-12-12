"""Decision model - choices with full reasoning chain."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field

from mind.models.base import MindBaseModel, generate_id


class Alternative(MindBaseModel):
    """An option that was considered."""
    option: str
    considered: bool = True
    rejected_because: Optional[str] = None


class Decision(MindBaseModel):
    """Choices with full reasoning chain."""

    id: str = Field(default_factory=lambda: generate_id("dec"))
    project_id: str

    # The decision
    title: str
    description: str

    # The reasoning
    context: str  # What situation led to this
    reasoning: str  # Why we chose this
    alternatives: list[Alternative] = Field(default_factory=list)

    # Confidence & validity
    confidence: float = 0.7  # 0.0 to 1.0
    revisit_if: Optional[str] = None  # Condition that triggers reconsideration
    valid_until: Optional[datetime] = None
    status: Literal["active", "superseded", "revisiting"] = "active"
    superseded_by: Optional[str] = None

    # Connections
    related_issues: list[str] = Field(default_factory=list)
    related_edges: list[str] = Field(default_factory=list)
    triggered_by_episode: Optional[str] = None

    # Retrieval
    trigger_phrases: list[str] = Field(default_factory=list)

    # Metadata
    decided_at: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None

    @property
    def embedding_text(self) -> str:
        """Text for embedding generation."""
        return f"{self.title}. {self.description}. {self.reasoning}"


class DecisionCreate(MindBaseModel):
    """For creating new decisions."""
    project_id: str
    title: str
    description: str
    context: str
    reasoning: str
    alternatives: list[Alternative] = Field(default_factory=list)
    confidence: float = 0.7
    revisit_if: Optional[str] = None
    trigger_phrases: list[str] = Field(default_factory=list)
