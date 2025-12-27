"""
Schema definitions for Mind v3 context graph nodes.

Defines all node types in the context graph:
- Decisions: Actions taken with reasoning
- Entities: Files, functions, concepts
- Patterns: Preferences, habits, blind spots
- Policies: Rules that govern decisions
- Exceptions: Overrides to policies
- Precedents: Historical decisions that set precedent
- Outcomes: Results of decisions
- Autonomy: Autonomy levels for action types
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


@dataclass
class DecisionNode:
    """A decision made during a session."""
    id: str
    action: str
    reasoning: str
    alternatives: list[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=_now)
    vector: list[float] = field(default_factory=list)


@dataclass
class EntityNode:
    """An entity in the codebase (file, function, concept)."""
    id: str
    name: str
    type: str  # "file", "function", "class", "concept"
    description: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    vector: list[float] = field(default_factory=list)


@dataclass
class PatternNode:
    """A pattern observed in user behavior or preferences."""
    id: str
    description: str
    pattern_type: str  # "preference", "habit", "blind_spot"
    confidence: float = 0.0
    evidence_count: int = 0
    vector: list[float] = field(default_factory=list)


@dataclass
class PolicyNode:
    """A policy or rule that governs decisions."""
    id: str
    rule: str
    scope: str = "project"  # "file", "directory", "project", "global"
    source: str = "inferred"  # Where this policy came from
    created_at: datetime = field(default_factory=_now)
    active: bool = True
    vector: list[float] = field(default_factory=list)


@dataclass
class ExceptionNode:
    """An exception or override to a policy."""
    id: str
    policy_id: str  # Reference to overridden policy
    condition: str  # When this exception applies
    reason: str
    created_at: datetime = field(default_factory=_now)
    vector: list[float] = field(default_factory=list)


@dataclass
class PrecedentNode:
    """A historical decision that sets precedent."""
    id: str
    decision_id: str  # Reference to the decision
    context: str  # Context in which this applies
    outcome: str  # What happened as a result
    weight: float = 1.0  # How much weight to give this precedent
    created_at: datetime = field(default_factory=_now)
    vector: list[float] = field(default_factory=list)


@dataclass
class OutcomeNode:
    """The outcome of a decision."""
    id: str
    decision_id: str
    success: bool
    feedback: str = ""  # User feedback or observed result
    impact: str = "neutral"  # "positive", "negative", "neutral"
    created_at: datetime = field(default_factory=_now)
    vector: list[float] = field(default_factory=list)


@dataclass
class AutonomyNode:
    """Autonomy level for a specific action type."""
    id: str
    action_type: str  # "file_edit", "commit", "refactor", etc.
    level: str = "ask"  # "ask", "suggest", "auto"
    confidence: float = 0.0
    sample_count: int = 0
    last_updated: datetime = field(default_factory=_now)
