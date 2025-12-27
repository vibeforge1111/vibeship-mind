"""Logging levels for Mind - Efficient/Balanced/Detailed modes.

Controls what gets logged based on user preference.
"""

import re
from pathlib import Path
from typing import Literal

from .config import load_config


LoggingLevel = Literal["efficient", "balanced", "detailed"]


def get_logging_level(project_path: Path) -> LoggingLevel:
    """Get the configured logging level for a project.

    Returns:
        One of: "efficient", "balanced", "detailed"
    """
    config = load_config(project_path)

    # Check new v2 config structure
    if "logging" in config and isinstance(config["logging"], dict):
        return config["logging"].get("level", "balanced")

    # Fallback to old structure or default
    return "balanced"


def should_log_message(
    message: str,
    entry_type: str,
    logging_level: LoggingLevel
) -> tuple[bool, str | None]:
    """Determine if a message should be logged based on logging level.

    Args:
        message: The message to potentially log.
        entry_type: The type of log entry (experience, blocker, etc.)
        logging_level: The configured logging level.

    Returns:
        Tuple of (should_log: bool, reason: str | None)
        If should_log is False, reason explains why.
    """
    # Types that always get logged regardless of level
    always_log_types = {"decision", "problem", "blocker", "learning", "progress", "rejected"}

    if entry_type in always_log_types:
        return True, None

    # Efficient mode: Only log critical items
    if logging_level == "efficient":
        # Skip routine experiences unless they have insight markers
        if entry_type == "experience":
            if not _has_insight_markers(message):
                return False, "Skipped in efficient mode (no insight markers)"

        # Skip assumptions that are obvious
        if entry_type == "assumption":
            if _is_obvious_assumption(message):
                return False, "Skipped in efficient mode (obvious assumption)"

        return True, None

    # Balanced mode: Log most things, skip only truly routine
    if logging_level == "balanced":
        if entry_type == "experience":
            # Skip very short, routine messages
            if len(message) < 20 and not _has_insight_markers(message):
                return False, "Skipped in balanced mode (too short, no insight)"

        return True, None

    # Detailed mode: Log everything
    return True, None


def _has_insight_markers(message: str) -> bool:
    """Check if message contains markers suggesting insight worth keeping."""
    msg_lower = message.lower()

    insight_patterns = [
        # Technical specifics
        r'\b(found|discovered|noticed|realized)\b',
        r'\b(because|since|due to|caused by)\b',
        r'\b(workaround|solution|fix|resolved)\b',
        # Paths and code references
        r'[/\\][\w.-]+\.\w+',  # File paths
        r'`[^`]+`',  # Code in backticks
        # Version/config specifics
        r'\bv?\d+\.\d+',  # Version numbers
        r'\b(config|setting|option|flag)\b',
        # Decision indicators
        r'\b(chose|decided|going with|using)\b',
        r'\b(instead of|rather than|over)\b',
    ]

    for pattern in insight_patterns:
        if re.search(pattern, msg_lower):
            return True

    return False


def _is_obvious_assumption(message: str) -> bool:
    """Check if assumption is obvious and not worth logging."""
    msg_lower = message.lower()

    # Very short assumptions are often obvious
    if len(message) < 30:
        obvious_patterns = [
            r'^assuming (this|it|that) (works?|is|will)',
            r'^assuming (the )?(api|server|database) (is|will be)',
            r'^assuming (user|they) (has?|will|can)',
        ]
        for pattern in obvious_patterns:
            if re.match(pattern, msg_lower):
                return True

    return False


def get_level_description(level: LoggingLevel) -> str:
    """Get a human-readable description of a logging level."""
    descriptions = {
        "efficient": "Only critical decisions and blockers",
        "balanced": "Key moments + context (recommended)",
        "detailed": "Everything, compacted to Memory periodically",
    }
    return descriptions.get(level, "Unknown")
