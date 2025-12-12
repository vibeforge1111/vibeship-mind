"""User model - how the human works."""

from datetime import datetime
from typing import Optional

from pydantic import Field

from mind.models.base import MindBaseModel, generate_id


class CommunicationPrefs(MindBaseModel):
    """How user prefers to communicate."""
    prefers: list[str] = Field(default_factory=list)  # ["direct feedback", "examples over theory"]
    dislikes: list[str] = Field(default_factory=list)  # ["hedging", "excessive caveats"]


class ExpertiseMap(MindBaseModel):
    """User's skill levels."""
    strong: list[str] = Field(default_factory=list)  # ["product thinking", "react"]
    learning: list[str] = Field(default_factory=list)  # ["devops", "security"]


class WorkingPatterns(MindBaseModel):
    """Observed patterns in how user works."""
    works_late: bool = False
    pushes_through_frustration: bool = False
    tendency_to_over_architect: bool = False
    prefers_shipping_over_perfection: bool = True


class UserModel(MindBaseModel):
    """How the human works."""

    id: str = Field(default_factory=lambda: generate_id("user"))

    # Identity
    name: Optional[str] = None

    # Stable traits
    communication: CommunicationPrefs = Field(default_factory=CommunicationPrefs)
    expertise: ExpertiseMap = Field(default_factory=ExpertiseMap)
    patterns: WorkingPatterns = Field(default_factory=WorkingPatterns)

    # Dynamic state
    current_energy: Optional[str] = None  # "high", "low", "tired"
    current_focus: Optional[str] = None  # What they're focused on
    recent_wins: list[str] = Field(default_factory=list)
    recent_frustrations: list[str] = Field(default_factory=list)

    # Calibration
    what_works: list[str] = Field(default_factory=list)
    what_doesnt_work: list[str] = Field(default_factory=list)

    # History
    projects: list[str] = Field(default_factory=list)
    total_sessions: int = 0
    first_session: Optional[datetime] = None
    last_session: Optional[datetime] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserModelUpdate(MindBaseModel):
    """For updating user model."""
    name: Optional[str] = None
    current_energy: Optional[str] = None
    current_focus: Optional[str] = None
    add_win: Optional[str] = None
    add_frustration: Optional[str] = None
    add_pattern: Optional[str] = None
    learned_preference: Optional[str] = None
