"""Feature flags and project configuration."""

import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = {
    "version": 1,
    "mascot": True,  # Show Mindful mascot in MCP responses
    "self_improve": {
        "enabled": True,           # Phases 1-5: Core self-improvement
        "decay": True,             # Phase 6: Patterns lose confidence over time
        "reinforcement": True,     # Phase 7: Track when patterns help
        "contradiction": True,     # Phase 8: Detect conflicting patterns
        "learning_style": True,    # Phase 9: Model HOW user learns
    },
    "experimental": {
        # Add experimental features here
    },
}


def get_config_file(project_path: Path) -> Path:
    """Get path to project config file."""
    return project_path / ".mind" / "config.json"


def load_config(project_path: Path) -> dict[str, Any]:
    """Load project config, return defaults if missing."""
    config_file = get_config_file(project_path)
    if not config_file.exists():
        return DEFAULT_CONFIG.copy()
    try:
        return json.loads(config_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return DEFAULT_CONFIG.copy()


def save_config(project_path: Path, config: dict[str, Any]) -> None:
    """Save project config to disk."""
    config_file = get_config_file(project_path)
    config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")


def is_feature_enabled(feature: str, project_path: Path) -> bool:
    """Check if an experimental feature is enabled.

    Usage:
        if is_feature_enabled("auto_mark_reminders", project_path):
            mark_reminder_done(...)
    """
    config = load_config(project_path)
    return config.get("experimental", {}).get(feature, False)


def is_self_improve_feature_enabled(feature: str, project_path: Path) -> bool:
    """Check if a self-improvement feature is enabled.

    Features:
        - "enabled": Core self-improvement (Phases 1-5)
        - "decay": Confidence decay over time (Phase 6)
        - "reinforcement": Track pattern usage (Phase 7)
        - "contradiction": Detect conflicting patterns (Phase 8)
        - "learning_style": Model how user learns (Phase 9)

    Usage:
        if is_self_improve_feature_enabled("contradiction", project_path):
            check_for_contradictions(...)
    """
    config = load_config(project_path)
    self_improve = config.get("self_improve", DEFAULT_CONFIG["self_improve"])
    return self_improve.get(feature, False)


def enable_feature(feature: str, project_path: Path) -> None:
    """Enable an experimental feature."""
    config = load_config(project_path)
    if "experimental" not in config:
        config["experimental"] = {}
    config["experimental"][feature] = True
    save_config(project_path, config)


def disable_feature(feature: str, project_path: Path) -> None:
    """Disable an experimental feature."""
    config = load_config(project_path)
    if "experimental" not in config:
        config["experimental"] = {}
    config["experimental"][feature] = False
    save_config(project_path, config)


def is_mascot_enabled(project_path: Path) -> bool:
    """Check if Mindful mascot is enabled for this project."""
    config = load_config(project_path)
    return config.get("mascot", True)  # Default on


def set_mascot_enabled(project_path: Path, enabled: bool) -> None:
    """Enable or disable Mindful mascot for this project."""
    config = load_config(project_path)
    config["mascot"] = enabled
    save_config(project_path, config)


def create_default_config(project_path: Path) -> None:
    """Create default config.json for a project."""
    config_file = get_config_file(project_path)
    if not config_file.exists():
        save_config(project_path, DEFAULT_CONFIG)
