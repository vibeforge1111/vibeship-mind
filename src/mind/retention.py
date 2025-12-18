"""Usage-based retention for Mind - relevance scoring and decay.

Tracks how valuable each memory is based on usage patterns.
"""

import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from .config import load_config


RetentionMode = Literal["smart", "keep_all"]


def get_retention_mode(project_path: Path) -> RetentionMode:
    """Get the configured retention mode for a project.

    Returns:
        One of: "smart", "keep_all"
    """
    config = load_config(project_path)

    # Check v2 config structure
    if "memory" in config and isinstance(config["memory"], dict):
        return config["memory"].get("retention_mode", "smart")

    return "smart"


def get_decay_settings(project_path: Path) -> dict[str, Any]:
    """Get decay settings from config.

    Returns:
        dict with decay_period_days, decay_rate, min_relevance
    """
    config = load_config(project_path)

    defaults = {
        "decay_period_days": 30,
        "decay_rate": 0.1,
        "min_relevance": 0.2,
    }

    if "memory" in config and isinstance(config["memory"], dict):
        memory_config = config["memory"]
        return {
            "decay_period_days": memory_config.get("decay_period_days", defaults["decay_period_days"]),
            "decay_rate": memory_config.get("decay_rate", defaults["decay_rate"]),
            "min_relevance": memory_config.get("min_relevance", defaults["min_relevance"]),
        }

    return defaults


def get_relevance_file(project_path: Path) -> Path:
    """Get the relevance tracking file path."""
    return project_path / ".mind" / "relevance.json"


def load_relevance_data(project_path: Path) -> dict[str, Any]:
    """Load relevance tracking data.

    Returns:
        dict with memory_id -> {score, last_accessed, access_count, created}
    """
    relevance_file = get_relevance_file(project_path)

    if not relevance_file.exists():
        return {"version": 1, "entries": {}}

    try:
        content = relevance_file.read_text(encoding="utf-8")
        return json.loads(content)
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "entries": {}}


def save_relevance_data(project_path: Path, data: dict[str, Any]) -> bool:
    """Save relevance tracking data.

    Returns:
        True if saved successfully.
    """
    relevance_file = get_relevance_file(project_path)

    try:
        relevance_file.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )
        return True
    except OSError:
        return False


def get_memory_id(content: str) -> str:
    """Generate a stable ID for a memory entry.

    Uses first 8 chars of MD5 hash of normalized content.
    """
    normalized = content.strip().lower()
    return hashlib.md5(normalized.encode()).hexdigest()[:8]


def track_memory_access(project_path: Path, content: str) -> dict[str, Any]:
    """Track that a memory was accessed (searched, viewed, used).

    This reinforces the memory's relevance.

    Returns:
        dict with the updated entry data
    """
    mode = get_retention_mode(project_path)
    if mode == "keep_all":
        return {"score": 1.0, "access_count": 0, "mode": "keep_all"}

    memory_id = get_memory_id(content)
    data = load_relevance_data(project_path)
    now = datetime.now().isoformat()

    if memory_id not in data["entries"]:
        # New entry - start at 1.0
        data["entries"][memory_id] = {
            "score": 1.0,
            "last_accessed": now,
            "access_count": 1,
            "created": now,
            "preview": content[:50],
        }
    else:
        entry = data["entries"][memory_id]
        entry["last_accessed"] = now
        entry["access_count"] = entry.get("access_count", 0) + 1
        # Reinforce on access - boost score
        entry["score"] = min(1.0, entry.get("score", 0.5) + 0.1)

    save_relevance_data(project_path, data)
    return data["entries"][memory_id]


def reinforce_memory(project_path: Path, content: str, boost: float = 0.2) -> dict[str, Any]:
    """Explicitly reinforce a memory's relevance.

    Call this when:
    - Memory helped solve a problem
    - User explicitly referenced it
    - Memory appears in search results user acts on

    Args:
        project_path: Project root directory.
        content: The memory content to reinforce.
        boost: Amount to boost score (default 0.2).

    Returns:
        dict with the updated entry data
    """
    mode = get_retention_mode(project_path)
    if mode == "keep_all":
        return {"score": 1.0, "mode": "keep_all"}

    memory_id = get_memory_id(content)
    data = load_relevance_data(project_path)
    now = datetime.now().isoformat()

    if memory_id not in data["entries"]:
        # New entry
        data["entries"][memory_id] = {
            "score": min(1.0, 0.5 + boost),
            "last_accessed": now,
            "access_count": 1,
            "created": now,
            "preview": content[:50],
        }
    else:
        entry = data["entries"][memory_id]
        entry["last_accessed"] = now
        entry["score"] = min(1.0, entry.get("score", 0.5) + boost)

    save_relevance_data(project_path, data)
    return data["entries"][memory_id]


def decay_memories(project_path: Path) -> dict[str, Any]:
    """Apply decay to memories that haven't been accessed recently.

    Should be called periodically (e.g., on mind_recall).

    Returns:
        dict with decay statistics
    """
    mode = get_retention_mode(project_path)
    if mode == "keep_all":
        return {"decayed": 0, "mode": "keep_all"}

    settings = get_decay_settings(project_path)
    decay_period = settings["decay_period_days"]
    decay_rate = settings["decay_rate"]
    min_relevance = settings["min_relevance"]

    data = load_relevance_data(project_path)
    now = datetime.now()
    decayed_count = 0

    for memory_id, entry in data["entries"].items():
        if "last_accessed" not in entry:
            continue

        try:
            last_accessed = datetime.fromisoformat(entry["last_accessed"])
        except (ValueError, TypeError):
            continue

        days_since_access = (now - last_accessed).days

        if days_since_access >= decay_period:
            # Calculate decay periods elapsed
            periods_elapsed = days_since_access // decay_period
            decay_amount = periods_elapsed * decay_rate

            old_score = entry.get("score", 1.0)
            new_score = max(min_relevance, old_score - decay_amount)

            if new_score != old_score:
                entry["score"] = new_score
                decayed_count += 1

    if decayed_count > 0:
        save_relevance_data(project_path, data)

    return {
        "decayed": decayed_count,
        "total_entries": len(data["entries"]),
    }


def get_memory_relevance(project_path: Path, content: str) -> float:
    """Get the relevance score for a memory.

    Args:
        project_path: Project root directory.
        content: The memory content.

    Returns:
        Relevance score (0.0 to 1.0), defaults to 0.5 if not tracked.
    """
    mode = get_retention_mode(project_path)
    if mode == "keep_all":
        return 1.0

    memory_id = get_memory_id(content)
    data = load_relevance_data(project_path)

    if memory_id in data["entries"]:
        return data["entries"][memory_id].get("score", 0.5)

    return 0.5  # Default for untracked memories


def filter_by_relevance(
    project_path: Path,
    memories: list[str],
    threshold: float = 0.4
) -> list[str]:
    """Filter memories by relevance score.

    Args:
        project_path: Project root directory.
        memories: List of memory content strings.
        threshold: Minimum relevance to include (default 0.4).

    Returns:
        List of memories above the threshold.
    """
    mode = get_retention_mode(project_path)
    if mode == "keep_all":
        return memories

    result = []
    for memory in memories:
        score = get_memory_relevance(project_path, memory)
        if score >= threshold:
            result.append(memory)

    return result


def prioritize_by_relevance(
    project_path: Path,
    memories: list[str]
) -> list[tuple[str, float]]:
    """Sort memories by relevance score (highest first).

    Args:
        project_path: Project root directory.
        memories: List of memory content strings.

    Returns:
        List of (memory, score) tuples sorted by score descending.
    """
    mode = get_retention_mode(project_path)
    if mode == "keep_all":
        return [(m, 1.0) for m in memories]

    scored = []
    for memory in memories:
        score = get_memory_relevance(project_path, memory)
        scored.append((memory, score))

    return sorted(scored, key=lambda x: x[1], reverse=True)


def get_relevance_tier(score: float) -> str:
    """Get the relevance tier for display purposes.

    Returns:
        "high", "medium", or "low"
    """
    if score >= 0.7:
        return "high"
    elif score >= 0.4:
        return "medium"
    else:
        return "low"


def get_retention_stats(project_path: Path) -> dict[str, Any]:
    """Get statistics about memory retention.

    Returns:
        dict with stats about tracked memories
    """
    mode = get_retention_mode(project_path)
    data = load_relevance_data(project_path)
    entries = data.get("entries", {})

    if not entries:
        return {
            "mode": mode,
            "total": 0,
            "high_relevance": 0,
            "medium_relevance": 0,
            "low_relevance": 0,
        }

    scores = [e.get("score", 0.5) for e in entries.values()]
    high = sum(1 for s in scores if s >= 0.7)
    medium = sum(1 for s in scores if 0.4 <= s < 0.7)
    low = sum(1 for s in scores if s < 0.4)

    return {
        "mode": mode,
        "total": len(entries),
        "high_relevance": high,
        "medium_relevance": medium,
        "low_relevance": low,
        "average_score": sum(scores) / len(scores) if scores else 0,
    }
