"""Global preferences management for Mind.

Stores user preferences in ~/.mind/preferences.json for reuse across projects.
"""

import json
from pathlib import Path
from typing import Any
from datetime import date


def get_global_mind_dir() -> Path:
    """Get the global Mind directory (~/.mind)."""
    return Path.home() / ".mind"


def get_preferences_file() -> Path:
    """Get path to global preferences file."""
    return get_global_mind_dir() / "preferences.json"


DEFAULT_PREFERENCES = {
    "version": 1,
    "logging_level": "balanced",  # efficient, balanced, detailed
    "auto_promote": True,  # Auto-promote learnings from SESSION to MEMORY
    "retention_mode": "smart",  # smart (decay unused), keep_all (no decay)
    "created": None,  # Set on first save
    "last_project": None,  # Path to last project worked on
}


def get_default_preferences() -> dict[str, Any]:
    """Get a fresh copy of default preferences."""
    prefs = DEFAULT_PREFERENCES.copy()
    prefs["created"] = date.today().isoformat()
    return prefs


def load_global_preferences() -> dict[str, Any] | None:
    """Load global preferences from ~/.mind/preferences.json.

    Returns:
        Preferences dict if file exists and is valid, None otherwise.
    """
    prefs_file = get_preferences_file()

    if not prefs_file.exists():
        return None

    try:
        content = prefs_file.read_text(encoding="utf-8")
        if not content.strip():
            return None
        return json.loads(content)
    except (json.JSONDecodeError, OSError):
        return None


def save_global_preferences(preferences: dict[str, Any]) -> bool:
    """Save preferences to ~/.mind/preferences.json.

    Creates ~/.mind directory if it doesn't exist.

    Returns:
        True if saved successfully, False otherwise.
    """
    try:
        global_dir = get_global_mind_dir()
        global_dir.mkdir(parents=True, exist_ok=True)

        prefs_file = get_preferences_file()
        prefs_file.write_text(
            json.dumps(preferences, indent=2),
            encoding="utf-8"
        )
        return True
    except OSError:
        return False


def has_existing_preferences() -> bool:
    """Check if user has existing global preferences."""
    return load_global_preferences() is not None


def update_last_project(project_path: Path) -> None:
    """Update the last_project field in global preferences."""
    prefs = load_global_preferences()
    if prefs is None:
        prefs = get_default_preferences()

    prefs["last_project"] = str(project_path.resolve())
    save_global_preferences(prefs)


def get_logging_level() -> str:
    """Get the configured logging level (efficient, balanced, detailed)."""
    prefs = load_global_preferences()
    if prefs is None:
        return DEFAULT_PREFERENCES["logging_level"]
    return prefs.get("logging_level", DEFAULT_PREFERENCES["logging_level"])


def get_auto_promote() -> bool:
    """Get whether auto-promote is enabled."""
    prefs = load_global_preferences()
    if prefs is None:
        return DEFAULT_PREFERENCES["auto_promote"]
    return prefs.get("auto_promote", DEFAULT_PREFERENCES["auto_promote"])


def get_retention_mode() -> str:
    """Get the configured retention mode (smart, keep_all)."""
    prefs = load_global_preferences()
    if prefs is None:
        return DEFAULT_PREFERENCES["retention_mode"]
    return prefs.get("retention_mode", DEFAULT_PREFERENCES["retention_mode"])


def merge_with_defaults(prefs: dict[str, Any]) -> dict[str, Any]:
    """Merge user preferences with defaults, filling in missing fields."""
    defaults = get_default_preferences()

    # Start with defaults
    merged = defaults.copy()

    # Override with user preferences
    for key, value in prefs.items():
        if value is not None:
            merged[key] = value

    return merged
