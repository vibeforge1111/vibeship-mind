"""Memory decay calculations for stale entries.

Decay is based on time since last ACCESS (not creation), entity status,
and entity type. Old but accessed = fresh; resolved but recent = stale.

Formula:
    decay = 0.5 ^ (days_since_access / adjusted_half_life)
    adjusted_half_life = base_half_life * status_multiplier

Entity Type Half-Lives:
    - Decision: 60 days (architecture choices stay valid longer)
    - Issue: 30 days (either active or done)
    - Sharp Edge: 120 days (universal truths, rarely stale)
    - Episode: 90 days (historical, reference occasionally)

Status Multipliers (affect decay speed):
    - superseded: 0.2 (decays 5x faster)
    - resolved/wont_fix: 0.5 (decays 2x faster)
    - active/open: 1.0 (normal decay)
"""

from datetime import datetime
from typing import Optional

from mind.models.base import EntityType


# Base half-life by entity type (days)
HALF_LIFE_DAYS = {
    EntityType.DECISION: 60,
    EntityType.ISSUE: 30,
    EntityType.SHARP_EDGE: 120,
    EntityType.EPISODE: 90,
}

DEFAULT_HALF_LIFE = 30

# Status multipliers (lower = faster decay)
STATUS_MULTIPLIERS = {
    "superseded": 0.2,   # Decays 5x faster
    "resolved": 0.5,     # Decays 2x faster
    "wont_fix": 0.5,     # Same as resolved
    "active": 1.0,       # Normal decay
    "open": 1.0,         # Normal decay
    "investigating": 1.0,
    "blocked": 0.8,      # Slightly faster (stalled)
    "revisiting": 1.0,   # Active consideration
}

DEFAULT_STATUS_MULTIPLIER = 1.0


def calculate_decay(
    entity_type: EntityType,
    status: Optional[str],
    days_since_access: float,
) -> float:
    """Calculate decay multiplier for an entity.

    Args:
        entity_type: Type of entity (decision, issue, etc.)
        status: Current status of the entity (active, resolved, etc.)
        days_since_access: Days since entity was last accessed

    Returns:
        Decay multiplier between 0.0 and 1.0 (1.0 = no decay, 0.0 = fully decayed)

    Examples:
        - Decision accessed today, active: ~1.0
        - Decision accessed 60 days ago, active: ~0.5
        - Issue accessed 30 days ago, resolved: ~0.25 (2x faster decay)
        - Edge accessed 120 days ago, active: ~0.5
    """
    if days_since_access < 0:
        days_since_access = 0

    # Get base half-life for entity type
    half_life = HALF_LIFE_DAYS.get(entity_type, DEFAULT_HALF_LIFE)

    # Get status multiplier (affects decay speed)
    status_multiplier = STATUS_MULTIPLIERS.get(status or "active", DEFAULT_STATUS_MULTIPLIER)

    # Adjusted half-life (lower multiplier = shorter half-life = faster decay)
    adjusted_half_life = half_life * status_multiplier

    # Prevent division by zero
    if adjusted_half_life <= 0:
        return 0.0

    # Exponential decay: 0.5 ^ (t / half_life)
    decay = 0.5 ** (days_since_access / adjusted_half_life)

    return decay


def calculate_decay_from_timestamp(
    entity_type: EntityType,
    status: Optional[str],
    last_accessed: Optional[datetime],
    now: Optional[datetime] = None,
) -> float:
    """Calculate decay from a last_accessed timestamp.

    Args:
        entity_type: Type of entity
        status: Current status
        last_accessed: When the entity was last accessed (None = never accessed)
        now: Current time (defaults to utcnow)

    Returns:
        Decay multiplier between 0.0 and 1.0
    """
    if now is None:
        now = datetime.utcnow()

    if last_accessed is None:
        # Never accessed - use a large value (6 months)
        days_since_access = 180.0
    else:
        delta = now - last_accessed
        days_since_access = delta.total_seconds() / (24 * 60 * 60)

    return calculate_decay(entity_type, status, days_since_access)


def get_decay_threshold(min_relevance: float = 0.1) -> float:
    """Get the decay value below which entities are considered stale.

    Args:
        min_relevance: Minimum decay value to consider relevant

    Returns:
        Threshold value (entities below this are filtered out)
    """
    return min_relevance
