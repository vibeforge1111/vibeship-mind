"""Health system for Mind - auto-repair and diagnostics.

Provides silent auto-repair of common issues and health checks.
"""

import json
import re
from pathlib import Path
from datetime import date
from typing import Any

from .templates import SESSION_TEMPLATE, MEMORY_TEMPLATE, REMINDERS_TEMPLATE


def get_mind_dir(project_path: Path) -> Path:
    """Get the .mind directory path for a project."""
    return project_path / ".mind"


def check_health(project_path: Path) -> dict[str, Any]:
    """Check the health of Mind files for a project.

    Returns:
        dict with:
        - healthy: bool - Overall health status
        - issues: list - List of detected issues
        - suggestions: list - Suggested fixes
    """
    mind_dir = get_mind_dir(project_path)

    result = {
        "healthy": True,
        "issues": [],
        "suggestions": [],
    }

    # Check if .mind directory exists
    if not mind_dir.exists():
        result["healthy"] = False
        result["issues"].append({
            "type": "missing_mind_dir",
            "message": ".mind directory does not exist",
            "auto_fixable": True,
        })
        return result

    # Check SESSION.md
    session_issues = check_session_health(project_path)
    if session_issues:
        result["issues"].extend(session_issues)

    # Check MEMORY.md
    memory_issues = check_memory_health(project_path)
    if memory_issues:
        result["issues"].extend(memory_issues)

    # Check config.json
    config_issues = check_config_health(project_path)
    if config_issues:
        result["issues"].extend(config_issues)

    # Check REMINDERS.md
    reminders_issues = check_reminders_health(project_path)
    if reminders_issues:
        result["issues"].extend(reminders_issues)

    # Update healthy status
    if result["issues"]:
        result["healthy"] = False

    return result


def check_session_health(project_path: Path) -> list[dict]:
    """Check SESSION.md health."""
    issues = []
    session_file = get_mind_dir(project_path) / "SESSION.md"

    if not session_file.exists():
        issues.append({
            "type": "missing_session",
            "message": "SESSION.md does not exist",
            "auto_fixable": True,
        })
        return issues

    try:
        content = session_file.read_text(encoding="utf-8")
    except OSError as e:
        issues.append({
            "type": "session_read_error",
            "message": f"Cannot read SESSION.md: {e}",
            "auto_fixable": True,
        })
        return issues

    # Check for required sections
    required_sections = ["Experience", "Blockers", "Rejected", "Assumptions"]
    for section in required_sections:
        pattern = rf"## {re.escape(section)}\s*\n"
        if not re.search(pattern, content, re.IGNORECASE):
            issues.append({
                "type": "missing_session_section",
                "message": f"SESSION.md missing '## {section}' section",
                "section": section,
                "auto_fixable": True,
            })

    return issues


def check_memory_health(project_path: Path) -> list[dict]:
    """Check MEMORY.md health."""
    issues = []
    memory_file = get_mind_dir(project_path) / "MEMORY.md"

    if not memory_file.exists():
        issues.append({
            "type": "missing_memory",
            "message": "MEMORY.md does not exist",
            "auto_fixable": True,
        })
        return issues

    try:
        content = memory_file.read_text(encoding="utf-8")
    except OSError as e:
        issues.append({
            "type": "memory_read_error",
            "message": f"Cannot read MEMORY.md: {e}",
            "auto_fixable": False,
        })
        return issues

    # Check for basic structure
    if "## Project State" not in content:
        issues.append({
            "type": "malformed_memory",
            "message": "MEMORY.md missing '## Project State' section",
            "auto_fixable": False,  # Don't auto-fix as it may have user content
        })

    return issues


def check_config_health(project_path: Path) -> list[dict]:
    """Check config.json health."""
    issues = []
    config_file = get_mind_dir(project_path) / "config.json"

    if not config_file.exists():
        issues.append({
            "type": "missing_config",
            "message": "config.json does not exist",
            "auto_fixable": True,
        })
        return issues

    try:
        content = config_file.read_text(encoding="utf-8")
        json.loads(content)
    except json.JSONDecodeError:
        issues.append({
            "type": "invalid_config_json",
            "message": "config.json contains invalid JSON",
            "auto_fixable": True,
        })
    except OSError as e:
        issues.append({
            "type": "config_read_error",
            "message": f"Cannot read config.json: {e}",
            "auto_fixable": True,
        })

    return issues


def check_reminders_health(project_path: Path) -> list[dict]:
    """Check REMINDERS.md health."""
    issues = []
    reminders_file = get_mind_dir(project_path) / "REMINDERS.md"

    if not reminders_file.exists():
        issues.append({
            "type": "missing_reminders",
            "message": "REMINDERS.md does not exist",
            "auto_fixable": True,
        })

    return issues


def repair_issues(project_path: Path, issues: list[dict] | None = None) -> dict[str, Any]:
    """Repair auto-fixable issues.

    Args:
        project_path: Project root directory.
        issues: Optional list of issues to fix. If None, runs check_health first.

    Returns:
        dict with:
        - repaired: list - Issues that were fixed
        - failed: list - Issues that couldn't be fixed
        - skipped: list - Issues that aren't auto-fixable
    """
    if issues is None:
        health = check_health(project_path)
        issues = health["issues"]

    result = {
        "repaired": [],
        "failed": [],
        "skipped": [],
    }

    mind_dir = get_mind_dir(project_path)

    for issue in issues:
        if not issue.get("auto_fixable", False):
            result["skipped"].append(issue)
            continue

        try:
            if issue["type"] == "missing_mind_dir":
                mind_dir.mkdir(parents=True, exist_ok=True)
                result["repaired"].append(issue)

            elif issue["type"] == "missing_session":
                repair_session_file(project_path)
                result["repaired"].append(issue)

            elif issue["type"] == "missing_session_section":
                repair_session_sections(project_path)
                result["repaired"].append(issue)

            elif issue["type"] == "session_read_error":
                repair_session_file(project_path)
                result["repaired"].append(issue)

            elif issue["type"] == "missing_memory":
                repair_memory_file(project_path)
                result["repaired"].append(issue)

            elif issue["type"] == "missing_config":
                repair_config_file(project_path)
                result["repaired"].append(issue)

            elif issue["type"] == "invalid_config_json":
                repair_config_file(project_path)
                result["repaired"].append(issue)

            elif issue["type"] == "config_read_error":
                repair_config_file(project_path)
                result["repaired"].append(issue)

            elif issue["type"] == "missing_reminders":
                repair_reminders_file(project_path)
                result["repaired"].append(issue)

            else:
                result["skipped"].append(issue)

        except Exception as e:
            issue["error"] = str(e)
            result["failed"].append(issue)

    return result


def repair_session_file(project_path: Path) -> bool:
    """Create or repair SESSION.md."""
    session_file = get_mind_dir(project_path) / "SESSION.md"

    try:
        content = SESSION_TEMPLATE.format(date=date.today().isoformat())
        session_file.write_text(content, encoding="utf-8")
        return True
    except OSError:
        return False


def repair_session_sections(project_path: Path) -> bool:
    """Add missing sections to SESSION.md."""
    session_file = get_mind_dir(project_path) / "SESSION.md"

    if not session_file.exists():
        return repair_session_file(project_path)

    try:
        content = session_file.read_text(encoding="utf-8")
    except OSError:
        return repair_session_file(project_path)

    required_sections = ["Experience", "Blockers", "Rejected", "Assumptions"]
    modified = False

    for section in required_sections:
        pattern = rf"## {re.escape(section)}\s*\n"
        if not re.search(pattern, content, re.IGNORECASE):
            content += f"\n## {section}\n\n"
            modified = True

    if modified:
        try:
            session_file.write_text(content, encoding="utf-8")
        except OSError:
            return False

    return True


def repair_memory_file(project_path: Path) -> bool:
    """Create MEMORY.md with template."""
    memory_file = get_mind_dir(project_path) / "MEMORY.md"

    try:
        content = MEMORY_TEMPLATE.format(
            project_name=project_path.name,
            date=date.today().isoformat(),
            stack="(auto-detected)"
        )
        memory_file.write_text(content, encoding="utf-8")
        return True
    except OSError:
        return False


def repair_config_file(project_path: Path) -> bool:
    """Create or repair config.json with defaults."""
    from .config import DEFAULT_CONFIG

    config_file = get_mind_dir(project_path) / "config.json"

    try:
        config_file.write_text(
            json.dumps(DEFAULT_CONFIG, indent=2),
            encoding="utf-8"
        )
        return True
    except OSError:
        return False


def repair_reminders_file(project_path: Path) -> bool:
    """Create REMINDERS.md with template."""
    reminders_file = get_mind_dir(project_path) / "REMINDERS.md"

    try:
        reminders_file.write_text(REMINDERS_TEMPLATE, encoding="utf-8")
        return True
    except OSError:
        return False


def auto_repair(project_path: Path) -> dict[str, Any]:
    """Run health check and silently repair any auto-fixable issues.

    This is the main entry point for silent auto-repair.
    Iterates until healthy or no more progress can be made.

    Returns:
        dict with:
        - was_healthy: bool - Whether project was healthy before repair
        - is_healthy: bool - Whether project is healthy after repair
        - repaired_count: int - Number of issues repaired
    """
    # Check initial health
    initial_health = check_health(project_path)

    result = {
        "was_healthy": initial_health["healthy"],
        "is_healthy": initial_health["healthy"],
        "repaired_count": 0,
        "repairs": [],
    }

    if initial_health["healthy"]:
        return result

    # Iterate repairs until healthy or no more progress
    max_iterations = 5  # Prevent infinite loops
    for _ in range(max_iterations):
        health = check_health(project_path)

        if health["healthy"]:
            break

        # Attempt repairs
        repair_result = repair_issues(project_path, health["issues"])

        if not repair_result["repaired"]:
            # No progress made, stop
            break

        result["repaired_count"] += len(repair_result["repaired"])
        result["repairs"].extend([r["type"] for r in repair_result["repaired"]])

    # Check final health
    final_health = check_health(project_path)
    result["is_healthy"] = final_health["healthy"]

    return result
