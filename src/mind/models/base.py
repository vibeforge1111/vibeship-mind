"""Base model utilities."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from ulid import ULID


def generate_id(prefix: str) -> str:
    """Generate a ULID-based ID with prefix."""
    return f"{prefix}_{ULID()}"


class EntityType(str, Enum):
    """Types of entities in Mind."""
    PROJECT = "project"
    DECISION = "decision"
    ISSUE = "issue"
    SHARP_EDGE = "sharp_edge"
    EPISODE = "episode"
    USER = "user"
    SESSION = "session"


class ChangeType(str, Enum):
    """Types of changes for sync tracking."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class Change(BaseModel):
    """Track changes for sync."""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    entity_type: EntityType
    entity_id: str
    change_type: ChangeType
    data: dict[str, Any]
    timestamp: datetime
    synced: bool = False

    @classmethod
    def create(
        cls,
        entity_type: EntityType,
        entity_id: str,
        change_type: ChangeType,
        data: dict[str, Any],
    ) -> "Change":
        return cls(
            id=generate_id("chg"),
            entity_type=entity_type,
            entity_id=entity_id,
            change_type=change_type,
            data=data,
            timestamp=datetime.utcnow(),
        )


class MindBaseModel(BaseModel):
    """Base model with common config."""
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
    )


class EdgeWarning(MindBaseModel):
    """Warning about a potential sharp edge.

    Returned inline with tool responses when detection triggers.
    """
    edge_id: str
    title: str
    severity: Literal["info", "medium", "high"]
    matched: str  # What triggered this warning (e.g., "query: 'token generation'")
    workaround: str  # Quick solution

    # Optional details
    symptoms: list[str] = Field(default_factory=list)
    link: Optional[str] = None  # Link to full edge details
