"""Mind MCP server - 12 tools for AI memory (v2: daemon-free, stateless)."""

import hashlib
import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from ..config import is_mascot_enabled
from ..legacy.context import ContextGenerator
from ..mascot import get_mindful, mindful_line, ACTION_EMOTIONS
from ..legacy.parser import Entity, EntityType, Parser
from ..storage import ProjectsRegistry, get_mind_home, get_self_improve_path
from ..templates import SESSION_TEMPLATE
from ..self_improve import (
    load_self_improve,
    generate_intuition_context,
    detect_intuitions,
    format_intuitions_for_context,
    SelfImproveData,
    Intuition,
    reinforce_pattern,
    get_confidence_stats,
    filter_by_confidence,
)
from ..legacy.similarity import semantic_similarity, semantic_search, semantic_search_strings

# v3 integration (parallel operation mode)
try:
    from ..v3.bridge import get_v3_bridge, V3Bridge
    V3_AVAILABLE = True
except ImportError:
    V3_AVAILABLE = False


# Gap threshold for session detection (30 minutes)
GAP_THRESHOLD_MS = 30 * 60 * 1000


def mindful_response(action: str, data: dict, message: str = "", project_path: Optional[Path] = None) -> str:
    """Wrap response data with Mindful mascot (if enabled).

    Args:
        action: Mind action (recall, log, search, etc.)
        data: Response data dict
        message: Short message describing what happened
        project_path: Project path to check mascot config (uses current project if None)

    Returns:
        JSON string with optional mindful field added
    """
    # Check if mascot is enabled
    if project_path is None:
        project_path = get_current_project()

    mascot_enabled = is_mascot_enabled(project_path) if project_path else True

    if mascot_enabled:
        emotion = ACTION_EMOTIONS.get(action, "idle")

        # Add mindful to response
        data["mindful"] = {
            "emotion": emotion,
            "art": get_mindful(emotion),
            "says": message,
        }

    return json.dumps(data, indent=2)


# SESSION.md management
def get_session_file(project_path: Path) -> Path:
    """Get path to session file."""
    return project_path / ".mind" / "SESSION.md"


def read_session_file(project_path: Path) -> Optional[str]:
    """Read SESSION.md content."""
    path = get_session_file(project_path)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def clear_session_file(project_path: Path) -> None:
    """Clear SESSION.md for new session."""
    path = get_session_file(project_path)
    content = SESSION_TEMPLATE.format(date=date.today().isoformat())
    path.write_text(content, encoding="utf-8")


def parse_session_section(content: str, section_name: str) -> list[str]:
    """Extract items from a SESSION.md section."""
    pattern = rf"## {re.escape(section_name)}\s*\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if not match:
        return []

    section_content = match.group(1)
    items = []
    for line in section_content.split("\n"):
        line = line.strip()
        # Skip empty lines, comments, and placeholders
        if line and not line.startswith("<!--") and not line.startswith("#"):
            # Remove leading dashes or bullets
            if line.startswith("- "):
                line = line[2:]
            items.append(line)
    return items


# Semantic similarity module - for loop detection and search
from ..legacy.similarity import find_similar_rejection, semantic_search, semantic_search_strings


def extract_promotable_learnings(session_content: str) -> list[dict]:
    """Extract items from SESSION.md worth promoting to MEMORY.md.

    Promotion rules (simplified structure):
    - "Rejected" with reasoning (contains " - ") -> decision
    - "Experience" with tech patterns, paths, or insights -> learning
    """
    learnings = []

    # "Rejected" items become decisions
    rejected_items = parse_session_section(session_content, "Rejected")
    for item in rejected_items:
        # Only promote if it has reasoning (contains " - " separator)
        if " - " in item:
            learnings.append({
                "type": "decision",
                "content": f"decided against: {item}",
            })

    # "Experience" items with tech patterns or insights persist
    experience_items = parse_session_section(session_content, "Experience")
    for item in experience_items:
        has_path = bool(re.search(r'[/\\][\w.-]+\.\w+|`[^`]+`', item))
        has_tech = bool(re.search(
            r'\b(Safari|Chrome|Firefox|Windows|Linux|macOS|iOS|Android|'
            r'npm|yarn|pip|cargo|apt|brew|docker|kubernetes|'
            r'React|Vue|Angular|Node|Python|Rust|Go|Java|'
            r'httpOnly|cookie|localStorage|JWT|OAuth|CORS|'
            r'bcrypt|hash|SSL|TLS|HTTP|HTTPS)\b',
            item, re.IGNORECASE
        ))
        has_insight = bool(re.search(
            r'\b(realized|learned|discovered|turns out|gotcha|'
            r'important|key|critical|always|never)\b',
            item, re.IGNORECASE
        ))
        has_arrow = '->' in item or '=>' in item

        if has_path or has_tech or has_insight or has_arrow:
            learnings.append({
                "type": "learning",
                "content": f"learned: {item}",
            })

    return learnings


def check_novelty_and_link(
    new_content: str,
    memory_file: Path,
    novelty_threshold: float = 0.5,
    supersede_confidence: float = 0.7,
) -> dict:
    """Check if content is novel vs existing memory, and determine link/supersede.

    Args:
        new_content: The content to check
        memory_file: Path to MEMORY.md
        novelty_threshold: Below this similarity = novel (will promote)
        supersede_confidence: Above this confidence = supersede old entry

    Returns:
        Dict with:
        - is_novel: True if should promote (not a duplicate)
        - action: 'add' (new), 'link' (similar exists, low confidence), 'supersede' (similar exists, high confidence), 'skip' (duplicate)
        - similar_entry: The similar entry if found
        - similarity: Similarity score if found
    """
    if not memory_file.exists():
        return {"is_novel": True, "action": "add", "similar_entry": None, "similarity": 0}

    # Parse memory file
    parser = Parser()
    content = memory_file.read_text(encoding="utf-8")
    result = parser.parse(content, str(memory_file))

    if not result.entities:
        return {"is_novel": True, "action": "add", "similar_entry": None, "similarity": 0}

    # Find most similar existing entry
    best_match = None
    best_similarity = 0.0

    for entity in result.entities:
        similarity = semantic_similarity(new_content, entity.content)
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = entity

    # Determine action based on similarity
    if best_similarity < novelty_threshold:
        # Novel - no similar entry exists
        return {"is_novel": True, "action": "add", "similar_entry": None, "similarity": best_similarity}

    if best_similarity > 0.9:
        # Almost identical - skip (duplicate)
        return {
            "is_novel": False,
            "action": "skip",
            "similar_entry": {
                "content": best_match.content,
                "line": best_match.source_line,
                "type": best_match.type.value,
            },
            "similarity": best_similarity,
        }

    # Similar entry exists - check confidence for link vs supersede
    # For memory entries, we use similarity as a proxy for confidence
    # Higher similarity to existing = more likely the new is a refinement (supersede)
    # The idea: if you're saying almost the same thing again, you probably learned more
    confidence = best_similarity

    if confidence >= supersede_confidence:
        # High confidence - supersede
        return {
            "is_novel": True,
            "action": "supersede",
            "similar_entry": {
                "content": best_match.content,
                "line": best_match.source_line,
                "type": best_match.type.value,
                "confidence": confidence,
            },
            "similarity": best_similarity,
        }
    else:
        # Low confidence - link
        return {
            "is_novel": True,
            "action": "link",
            "similar_entry": {
                "content": best_match.content,
                "line": best_match.source_line,
                "type": best_match.type.value,
                "confidence": confidence,
            },
            "similarity": best_similarity,
        }


def format_with_link(content: str, similar_entry: dict) -> str:
    """Format content with wikilink to similar entry.

    Args:
        content: The new content
        similar_entry: Dict with content, line, type of similar entry

    Returns:
        Content with wikilink appended
    """
    # Create wikilink in Obsidian format
    line = similar_entry.get("line", 0)
    entry_type = similar_entry.get("type", "entry")
    link = f"[[MEMORY#L{line}]]"
    return f"{content} (see also: {link})"


def mark_as_superseded(memory_file: Path, line_number: int) -> bool:
    """Mark an entry in MEMORY.md as superseded.

    Args:
        memory_file: Path to MEMORY.md
        line_number: Line number of entry to mark

    Returns:
        True if successful
    """
    if not memory_file.exists():
        return False

    lines = memory_file.read_text(encoding="utf-8").split("\n")

    if line_number < 1 or line_number > len(lines):
        return False

    # Mark the line as superseded
    idx = line_number - 1
    if not lines[idx].startswith("[superseded]"):
        lines[idx] = f"[superseded] {lines[idx]}"

    memory_file.write_text("\n".join(lines), encoding="utf-8")
    return True


# Bug reusability signals - keywords that indicate the bug fix is worth remembering
BUG_REUSABILITY_SIGNALS = {
    # Platform/OS specific
    "platforms": ["windows", "macos", "linux", "unix", "darwin", "win32", "posix"],
    # Common libraries/frameworks
    "libraries": [
        "asyncio", "multiprocessing", "threading", "subprocess",
        "requests", "aiohttp", "flask", "django", "fastapi",
        "numpy", "pandas", "tensorflow", "pytorch",
        "sqlalchemy", "psycopg", "mysql", "sqlite",
        "redis", "celery", "rabbitmq",
        "react", "vue", "angular", "nodejs", "express",
    ],
    # Error patterns
    "errors": [
        "exception", "error", "traceback", "stack",
        "timeout", "deadlock", "race condition", "memory leak",
        "segfault", "core dump", "out of memory", "oom",
        "permission denied", "access denied", "auth",
        "encoding", "unicode", "utf-8", "cp1252",
        "import", "module not found", "dependency",
    ],
    # Technical concepts that hint at reusability
    "concepts": [
        "async", "await", "callback", "promise",
        "lock", "mutex", "semaphore", "concurrent",
        "cache", "memoize", "lazy", "eager",
        "serialize", "deserialize", "json", "pickle",
        "socket", "tcp", "http", "websocket",
        "path", "file", "directory", "permission",
    ],
}


def check_bug_reusability(content: str) -> dict:
    """Check if a bug/problem is worth remembering based on reusability signals.

    Args:
        content: The bug/problem description

    Returns:
        Dict with:
        - is_reusable: True if worth remembering
        - signals: List of detected reusability signals
        - score: Reusability score (0.0-1.0)
        - suggestion: If not reusable, why not
    """
    content_lower = content.lower()
    detected_signals = []
    score = 0.0

    # Check each category
    for category, keywords in BUG_REUSABILITY_SIGNALS.items():
        for keyword in keywords:
            if keyword in content_lower:
                detected_signals.append(f"{category}:{keyword}")
                # Weight by category
                if category == "platforms":
                    score += 0.3  # Platform bugs are highly reusable
                elif category == "libraries":
                    score += 0.25  # Library bugs are often reusable
                elif category == "errors":
                    score += 0.2  # Error patterns useful
                elif category == "concepts":
                    score += 0.15  # Technical concepts somewhat useful

    # Bonus for problem->solution structure
    if "->" in content or "fixed by" in content_lower or "solution:" in content_lower:
        score += 0.2
        detected_signals.append("structure:problem->solution")

    # Bonus for root cause
    if "because" in content_lower or "root cause" in content_lower or "caused by" in content_lower:
        score += 0.15
        detected_signals.append("structure:root_cause")

    # Cap at 1.0
    score = min(score, 1.0)

    # Threshold for reusability
    is_reusable = score >= 0.3 or len(detected_signals) >= 2

    suggestion = None
    if not is_reusable:
        suggestion = "This bug seems specific to this codebase. Consider adding platform/library context or root cause for future reference."

    return {
        "is_reusable": is_reusable,
        "signals": detected_signals,
        "score": round(score, 2),
        "suggestion": suggestion,
    }


def format_bug_for_memory(content: str, signals: list[str]) -> str:
    """Format a bug entry for MEMORY.md with structured format.

    Args:
        content: The bug description
        signals: Detected reusability signals

    Returns:
        Formatted bug entry with tags
    """
    # Extract tags from signals
    tags = set()
    for signal in signals:
        if ":" in signal:
            category, keyword = signal.split(":", 1)
            if category in ("platforms", "libraries"):
                tags.add(keyword)

    # Filter out tags that are already present in content
    content_lower = content.lower()
    new_tags = {tag for tag in tags if f"#{tag}" not in content_lower}

    # Add tags suffix if any new tags
    if new_tags:
        tag_str = " ".join(f"#{tag}" for tag in sorted(new_tags))
        content = f"{content} [{tag_str}]"

    return content


def append_to_memory(project_path: Path, learnings: list[dict]) -> int:
    """Append promoted learnings to MEMORY.md with novelty checking.

    Uses semantic similarity to:
    - Skip duplicates (>90% similar)
    - Link to similar entries (50-90% similar, low confidence)
    - Supersede old entries (50-90% similar, high confidence)
    - Add new entries (<50% similar)

    For bug/problem entries, also checks reusability signals.
    """
    if not learnings:
        return 0

    memory_file = project_path / ".mind" / "MEMORY.md"
    if not memory_file.exists():
        return 0

    promoted = []
    skipped = 0
    superseded = 0

    for learning in learnings:
        content = learning["content"]
        entry_type = learning.get("type", "learning")

        # For problem/bug entries, check reusability
        if entry_type == "problem":
            reuse_check = check_bug_reusability(content)
            if not reuse_check["is_reusable"]:
                # Skip non-reusable bugs
                skipped += 1
                continue
            # Format bug with tags
            content = format_bug_for_memory(content, reuse_check["signals"])

        # Check novelty and get action
        result = check_novelty_and_link(content, memory_file)

        if result["action"] == "skip":
            skipped += 1
            continue

        if result["action"] == "link" and result["similar_entry"]:
            # Add with wikilink to similar entry
            content = format_with_link(content, result["similar_entry"])

        if result["action"] == "supersede" and result["similar_entry"]:
            # Mark old entry as superseded
            mark_as_superseded(memory_file, result["similar_entry"]["line"])
            superseded += 1

        promoted.append({"type": entry_type, "content": content})

    if not promoted:
        return 0

    # Read current content (may have been modified by supersede)
    current_content = memory_file.read_text(encoding="utf-8")

    # Add learnings at the end
    additions = f"\n\n<!-- Promoted from SESSION.md on {date.today().isoformat()} -->\n"
    for learning in promoted:
        additions += f"{learning['content']}\n"

    memory_file.write_text(current_content + additions, encoding="utf-8")
    return len(promoted)


# State file management
def get_state_file(project_path: Path) -> Path:
    """Get path to project state file."""
    return project_path / ".mind" / "state.json"


def load_state(project_path: Path) -> dict:
    """Load project state from disk."""
    path = get_state_file(project_path)
    if not path.exists():
        return {"last_activity": 0, "memory_hash": "", "schema_version": 2}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {"last_activity": 0, "memory_hash": "", "schema_version": 2}


def save_state(project_path: Path, state: dict) -> None:
    """Save project state to disk."""
    path = get_state_file(project_path)
    path.write_text(json.dumps(state, indent=2))


def touch_activity(project_path: Path) -> None:
    """Update last_activity timestamp to keep session alive.

    Call this from any tool that indicates the user is actively working.
    This prevents premature session gap detection.
    """
    state = load_state(project_path)
    state["last_activity"] = int(datetime.now().timestamp() * 1000)
    save_state(project_path, state)


def hash_file(path: Path) -> str:
    """Get hash of file content for change detection."""
    if not path.exists():
        return ""
    content = path.read_bytes()
    return hashlib.md5(content).hexdigest()


# Global edges storage
def get_global_edges_file() -> Path:
    """Get path to global edges file."""
    return get_mind_home() / "global_edges.json"


def load_global_edges() -> list[dict]:
    """Load global edges from disk."""
    path = get_global_edges_file()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def save_global_edges(edges: list[dict]) -> None:
    """Save global edges to disk."""
    path = get_global_edges_file()
    path.write_text(json.dumps(edges, indent=2))


# REMINDERS.md management
def get_reminders_file(project_path: Path) -> Path:
    """Get path to reminders file."""
    return project_path / ".mind" / "REMINDERS.md"


def parse_reminders(project_path: Path) -> list[dict]:
    """Parse REMINDERS.md into list of reminder dicts."""
    path = get_reminders_file(project_path)
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8")
    reminders = []

    # Match lines like: - [ ] 2025-12-14 | next session | message
    # or: - [x] 2025-12-14 | done | message
    pattern = r"^- \[([ x])\] ([^\|]+)\|([^\|]+)\|(.+)$"

    for i, line in enumerate(content.split("\n")):
        match = re.match(pattern, line.strip())
        if match:
            done = match.group(1) == "x"
            due = match.group(2).strip()
            reminder_type = match.group(3).strip()
            message = match.group(4).strip()

            reminders.append({
                "index": i,
                "done": done,
                "due": due,
                "type": reminder_type,
                "message": message,
                "line": line,
            })

    return reminders


def parse_when(when_str: str) -> tuple[str, str]:
    """Parse a 'when' string into (due_date, type).

    Supports:
    - "next session" -> (today, "next session")
    - "tomorrow" -> (today+1, "absolute")
    - "in X days/hours/weeks" -> (calculated, "absolute")
    - "2025-12-20" or "December 20" -> (parsed, "absolute")
    - "when I mention X" -> (keywords, "context")
    - "when we work on X" -> (keywords, "context")
    - "when X comes up" -> (keywords, "context")
    """
    when_lower = when_str.lower().strip()
    today = date.today()

    # Context-based triggers: "when I mention X", "when we work on X", "when X comes up"
    context_patterns = [
        r"when\s+i\s+mention\s+(.+)",
        r"when\s+we\s+(?:work\s+on|discuss|touch)\s+(.+)",
        r"when\s+(.+?)\s+comes\s+up",
    ]
    for pattern in context_patterns:
        match = re.match(pattern, when_lower)
        if match:
            keywords_raw = match.group(1).strip()
            # Normalize: "auth, login" or "auth and login" -> "auth,login"
            # Split on comma, "and", or whitespace (but not within words)
            keywords = re.split(r"\s*,\s*|\s+and\s+", keywords_raw)
            keywords = [k.strip() for k in keywords if k.strip()]
            return ",".join(keywords), "context"

    # Next session
    if "next session" in when_lower:
        return today.isoformat(), "next session"

    # Tomorrow
    if when_lower == "tomorrow":
        return (today + timedelta(days=1)).isoformat(), "absolute"

    # Relative: "in X days/hours/weeks"
    relative_match = re.match(r"in\s+(\d+)\s+(day|hour|week|month)s?", when_lower)
    if relative_match:
        amount = int(relative_match.group(1))
        unit = relative_match.group(2)

        if unit == "day":
            due = today + timedelta(days=amount)
        elif unit == "hour":
            due = datetime.now() + timedelta(hours=amount)
            return due.isoformat(), "absolute"
        elif unit == "week":
            due = today + timedelta(weeks=amount)
        elif unit == "month":
            due = today + timedelta(days=amount * 30)  # Approximate
        else:
            due = today + timedelta(days=1)

        return due.isoformat(), "absolute"

    # ISO date: 2025-12-20
    iso_match = re.match(r"(\d{4}-\d{2}-\d{2})", when_str)
    if iso_match:
        return iso_match.group(1), "absolute"

    # Month day: "December 20" or "Dec 20"
    month_names = {
        "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
        "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6,
        "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "september": 9,
        "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
    }
    month_pattern = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})"
    month_match = re.match(month_pattern, when_lower)
    if month_match:
        month = month_names.get(month_match.group(1).lower()[:3], 1)
        day = int(month_match.group(2))
        year = today.year
        # If the date has passed this year, use next year
        try:
            due = date(year, month, day)
            if due < today:
                due = date(year + 1, month, day)
            return due.isoformat(), "absolute"
        except ValueError:
            pass

    # Default: next session if unparseable
    return today.isoformat(), "next session"


def add_reminder(project_path: Path, message: str, due: str, reminder_type: str) -> dict:
    """Add a new reminder to REMINDERS.md."""
    path = get_reminders_file(project_path)

    # Create file if it doesn't exist
    if not path.exists():
        path.write_text("## Reminders\n\n", encoding="utf-8")

    content = path.read_text(encoding="utf-8")

    # Add new reminder line
    new_line = f"- [ ] {due} | {reminder_type} | {message}\n"

    # Insert after the header
    if "## Reminders" in content:
        parts = content.split("## Reminders", 1)
        # Find end of header line
        header_end = parts[1].find("\n") + 1
        new_content = parts[0] + "## Reminders" + parts[1][:header_end] + new_line + parts[1][header_end:]
    else:
        new_content = "## Reminders\n\n" + new_line + content

    path.write_text(new_content, encoding="utf-8")

    return {
        "message": message,
        "due": due,
        "type": reminder_type,
    }


def mark_reminder_done(project_path: Path, index: int) -> bool:
    """Mark a reminder as done by its line index."""
    path = get_reminders_file(project_path)
    if not path.exists():
        return False

    content = path.read_text(encoding="utf-8")
    lines = content.split("\n")

    if 0 <= index < len(lines):
        line = lines[index]
        if line.strip().startswith("- [ ]"):
            lines[index] = line.replace("- [ ]", "- [x]", 1)
            # Also update type to "done"
            parts = lines[index].split("|")
            if len(parts) >= 2:
                parts[1] = " done "
                lines[index] = "|".join(parts)
            path.write_text("\n".join(lines), encoding="utf-8")
            return True

    return False


def get_due_reminders(project_path: Path) -> list[dict]:
    """Get all reminders that are currently due."""
    reminders = parse_reminders(project_path)
    today = date.today()
    now = datetime.now()
    due_reminders = []

    for r in reminders:
        if r["done"]:
            continue

        # "next session" type is always due when recalled
        if r["type"] == "next session":
            due_reminders.append(r)
            continue

        # Check absolute dates
        if r["type"] == "absolute":
            try:
                # Try datetime first (for hour-based reminders)
                if "T" in r["due"]:
                    due_dt = datetime.fromisoformat(r["due"])
                    if due_dt <= now:
                        due_reminders.append(r)
                else:
                    # Date only
                    due_date = date.fromisoformat(r["due"])
                    if due_date <= today:
                        due_reminders.append(r)
            except ValueError:
                # If parsing fails, consider it due
                due_reminders.append(r)

    return due_reminders


def get_context_reminders(project_path: Path) -> list[dict]:
    """Get all context-triggered reminders (not done)."""
    reminders = parse_reminders(project_path)
    return [r for r in reminders if r["type"] == "context" and not r["done"]]


# MEMORY.md writing helpers
def append_memory_entry(project_path: Path, entry: str, entry_type: str = "general") -> bool:
    """Append an entry to MEMORY.md with timestamp."""
    memory_file = project_path / ".mind" / "MEMORY.md"
    if not memory_file.exists():
        return False

    content = memory_file.read_text(encoding="utf-8")

    # Format the entry based on type
    today = date.today().isoformat()
    formatted_entry = f"\n{entry}"

    memory_file.write_text(content + formatted_entry, encoding="utf-8")
    return True


# SESSION.md writing helpers
def repair_session_file(project_path: Path) -> bool:
    """Repair a malformed SESSION.md by ensuring all sections exist.

    Returns True if repair was needed and performed.
    """
    session_file = get_session_file(project_path)

    if not session_file.exists():
        clear_session_file(project_path)
        return True

    session_content = session_file.read_text(encoding="utf-8")

    # Required sections
    required_sections = ["Experience", "Blockers", "Rejected", "Assumptions"]
    missing_sections = []

    for section in required_sections:
        pattern = rf"## {re.escape(section)}\s*\n"
        if not re.search(pattern, session_content):
            missing_sections.append(section)

    if not missing_sections:
        return False  # No repair needed

    # Add missing sections at the end
    for section in missing_sections:
        session_content += f"\n## {section}\n\n"

    session_file.write_text(session_content, encoding="utf-8")
    return True


def update_session_section(project_path: Path, section_name: str, content: str, append: bool = False) -> bool:
    """Update a section in SESSION.md. Auto-repairs if section missing."""
    session_file = get_session_file(project_path)
    if not session_file.exists():
        clear_session_file(project_path)

    session_content = session_file.read_text(encoding="utf-8")

    # Find the section
    pattern = rf"(## {re.escape(section_name)}\s*\n(?:<!--[^>]*-->\s*\n)?)"
    match = re.search(pattern, session_content)

    if not match:
        # Section missing - try to repair
        repair_session_file(project_path)
        session_content = session_file.read_text(encoding="utf-8")
        match = re.search(pattern, session_content)

        if not match:
            # Still missing after repair - add it manually
            session_content += f"\n## {section_name}\n\n"
            session_file.write_text(session_content, encoding="utf-8")
            session_content = session_file.read_text(encoding="utf-8")
            match = re.search(pattern, session_content)

            if not match:
                return False  # Give up

    insert_pos = match.end()

    if append:
        # Add as new item
        new_entry = f"- {content}\n"
        # Check if we need a blank line before next section
        rest = session_content[insert_pos:].lstrip("\n")
        if rest.startswith("##"):
            # Next section coming - need blank line separator
            new_entry = f"- {content}\n\n"
        new_content = session_content[:insert_pos] + new_entry + session_content[insert_pos:]
    else:
        # Replace section content (find end of section)
        next_section = re.search(r"\n## ", session_content[insert_pos:])
        if next_section:
            end_pos = insert_pos + next_section.start()
        else:
            end_pos = len(session_content)

        new_entry = f"{content}\n\n"
        new_content = session_content[:insert_pos] + new_entry + session_content[end_pos:]

    session_file.write_text(new_content, encoding="utf-8")
    return True


def get_current_project() -> Optional[Path]:
    """Get the current project path.

    Priority order:
    1. MIND_PROJECT environment variable (explicit override)
    2. PWD environment variable (shell's working directory, may differ from Python's cwd)
    3. Python's cwd (Path.cwd())
    4. Walk up parent directories looking for .mind

    This handles the case where the MCP server is started with a different
    working directory than where the user is actually working (e.g., when
    uv --directory points to the Mind package location).
    """
    # Priority 1: Explicit MIND_PROJECT override
    mind_project = os.environ.get("MIND_PROJECT")
    if mind_project:
        path = Path(mind_project)
        if (path / ".mind").exists():
            return path

    # Priority 2: PWD environment variable (shell's actual working directory)
    # This is important because `uv --directory` changes Python's cwd but
    # the shell's PWD may still reflect the user's actual project
    pwd = os.environ.get("PWD")
    if pwd:
        path = Path(pwd)
        if (path / ".mind").exists():
            return path
        # Also check parent directories of PWD
        for parent in path.parents:
            if (parent / ".mind").exists():
                return parent

    # Priority 3: Python's cwd
    cwd = Path.cwd()
    if (cwd / ".mind").exists():
        return cwd

    # Priority 4: Walk up parent directories from cwd
    for parent in cwd.parents:
        if (parent / ".mind").exists():
            return parent

    return None


def search_entities(
    query: str,
    entities: list[Entity],
    types: Optional[list[str]] = None,
    limit: int = 10,
) -> list[dict]:
    """Semantic search across entities with keyword fallback."""
    # Filter by type first
    filtered = entities
    if types:
        filtered = [e for e in entities if e.type.value in types]

    if not filtered:
        return []

    # Convert entities to dicts for semantic search
    items = []
    for entity in filtered:
        items.append({
            "type": entity.type.value,
            "title": entity.title,
            "content": entity.content,
            "reasoning": entity.reasoning,
            "status": entity.status.value if entity.status else None,
            "date": entity.date.isoformat() if entity.date else None,
            "source_file": entity.source_file,
            "source_line": entity.source_line,
            "confidence": entity.confidence,
            "source": "indexed",
        })

    # Try semantic search first
    semantic_results = semantic_search(query, items, content_key="content", threshold=0.3, limit=limit)

    if semantic_results:
        # Map semantic_similarity to relevance for compatibility
        for r in semantic_results:
            r["relevance"] = r.pop("semantic_similarity")
        return semantic_results

    # Fallback to keyword search if semantic returns nothing
    query_lower = query.lower()
    query_words = set(query_lower.split())
    results = []

    for item in items:
        content_lower = item["content"].lower()
        title_lower = item["title"].lower()
        matches = sum(1 for word in query_words if word in content_lower or word in title_lower)

        if matches > 0:
            relevance = matches / len(query_words)
            item["relevance"] = relevance
            results.append(item)

    # Sort by relevance, then confidence
    results.sort(key=lambda r: (r["relevance"], r["confidence"]), reverse=True)

    return results[:limit]


def search_raw_content(content: str, query: str, limit: int = 10) -> list[dict]:
    """Semantic search raw MEMORY.md content for unparsed matches (same-session support)."""
    lines = content.split("\n")
    # Filter out empty lines and headers
    valid_lines = [(i, line.strip()) for i, line in enumerate(lines) if line.strip() and not line.startswith("#")]

    if not valid_lines:
        return []

    # Try semantic search first
    strings = [line for _, line in valid_lines]
    semantic_results = semantic_search_strings(query, strings, threshold=0.3, limit=limit)

    if semantic_results:
        results = []
        for r in semantic_results:
            # Find original line index
            original_idx = valid_lines[r["line_index"]][0]
            results.append({
                "type": "raw",
                "title": r["content"][:100],
                "content": r["content"],
                "reasoning": None,
                "status": None,
                "date": None,
                "source_file": "MEMORY.md",
                "source_line": original_idx + 1,
                "confidence": 0.5,
                "relevance": r["semantic_similarity"],
                "source": "unparsed",
            })
        return results

    # Fallback to keyword search
    query_lower = query.lower()
    query_words = set(query_lower.split())
    results = []

    for i, line in valid_lines:
        line_lower = line.lower()
        matches = sum(1 for word in query_words if word in line_lower)

        if matches > 0:
            relevance = matches / len(query_words)
            results.append({
                "type": "raw",
                "title": line[:100],
                "content": line,
                "reasoning": None,
                "status": None,
                "date": None,
                "source_file": "MEMORY.md",
                "source_line": i + 1,
                "confidence": 0.5,
                "relevance": relevance,
                "source": "unparsed",
            })

    results.sort(key=lambda r: r["relevance"], reverse=True)
    return results[:limit]


def retrieve_relevant_memories(
    query_text: str,
    memory_file: Path,
    threshold: float = 0.5,
    limit: int = 3,
) -> list[dict]:
    """Retrieve memories semantically relevant to given text.

    Used for Memory -> Session retrieval: surfacing past learnings
    when user is working on something related.

    Args:
        query_text: Text to find relevant memories for (e.g., session content, experience log)
        memory_file: Path to MEMORY.md
        threshold: Minimum similarity to include (higher = more relevant)
        limit: Max results to return

    Returns:
        List of relevant memories with similarity scores
    """
    if not query_text or not memory_file.exists():
        return []

    # Parse memory file
    parser = Parser()
    content = memory_file.read_text(encoding="utf-8")
    result = parser.parse(content, str(memory_file))

    if not result.entities:
        return []

    # Convert entities to searchable items
    items = []
    for entity in result.entities:
        # Focus on learnings, decisions, and problems - the useful stuff
        if entity.type.value in ("learning", "decision", "issue"):
            items.append({
                "type": entity.type.value,
                "title": entity.title,
                "content": entity.content,
                "date": entity.date.isoformat() if entity.date else None,
                "source_line": entity.source_line,
            })

    if not items:
        return []

    # Semantic search
    results = semantic_search(query_text, items, content_key="content", threshold=threshold, limit=limit)

    # Rename semantic_similarity to relevance for consistency
    for r in results:
        if "semantic_similarity" in r:
            r["relevance"] = r.pop("semantic_similarity")

    return results


def format_relevant_memories(memories: list[dict]) -> str:
    """Format retrieved memories for injection into response.

    Args:
        memories: List of memory dicts from retrieve_relevant_memories

    Returns:
        Formatted string for display
    """
    if not memories:
        return ""

    lines = ["## Relevant Past Memories", "Based on what you're working on:"]
    for m in memories:
        relevance_pct = int(m.get("relevance", 0) * 100)
        lines.append(f"- [{m['type']}] {m['content'][:150]}{'...' if len(m['content']) > 150 else ''} ({relevance_pct}% relevant)")

    return "\n".join(lines)


def match_edges(
    intent: str,
    code: Optional[str],
    stack: list[str],
    global_edges: list[dict],
    project_edges: list[dict],
) -> list[dict]:
    """Match edges against intent, code, and stack."""
    intent_lower = intent.lower()
    code_lower = code.lower() if code else ""
    stack_set = set(s.lower() for s in stack)

    warnings = []

    # Check global edges
    for edge in global_edges:
        detection = edge.get("detection", {})

        context_patterns = detection.get("context", [])
        context_match = any(
            p.lower() in stack_set or any(p.lower() in s for s in stack_set)
            for p in context_patterns
        )

        stack_tags = edge.get("stack_tags", [])
        stack_match = any(
            tag.lower() in stack_set or any(tag.lower() in s for s in stack_set)
            for tag in stack_tags
        )

        intent_patterns = detection.get("intent", [])
        intent_match = any(p.lower() in intent_lower for p in intent_patterns)

        code_patterns = detection.get("code", [])
        code_match = code and any(p.lower() in code_lower for p in code_patterns)

        full_context_match = context_match or stack_match
        matches = sum([full_context_match, intent_match, code_match])

        if matches >= 1 or stack_match:
            if matches == 0 and stack_match:
                confidence = 0.3
                matched_on = "stack"
            else:
                confidence = matches / 3
                matched_on = ", ".join(filter(None, [
                    "stack" if full_context_match else None,
                    "intent" if intent_match else None,
                    "code" if code_match else None,
                ]))

            warnings.append({
                "id": edge.get("id", ""),
                "title": edge.get("title", ""),
                "description": edge.get("description", ""),
                "workaround": edge.get("workaround", ""),
                "severity": edge.get("severity", "warning"),
                "source": "global",
                "matched_on": matched_on,
                "confidence": confidence,
            })

    # Check project edges
    for edge in project_edges:
        title_lower = edge.get("title", "").lower()
        workaround_lower = (edge.get("workaround") or "").lower()

        stack_in_edge = any(
            s in title_lower or s in workaround_lower
            for s in stack_set
        )

        intent_words = intent_lower.split()
        intent_match = any(word in title_lower for word in intent_words)

        if intent_match or stack_in_edge:
            confidence = 0.6 if intent_match else 0.4
            warnings.append({
                "id": "",
                "title": edge.get("title", ""),
                "description": "",
                "workaround": edge.get("workaround", ""),
                "severity": "info",
                "source": "project",
                "matched_on": "title" if intent_match else "stack",
                "confidence": confidence,
            })

    warnings.sort(key=lambda w: w["confidence"], reverse=True)
    return warnings


def create_server() -> Server:
    """Create the MCP server with 8 tools (v2: stateless)."""
    server = Server("mind")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return [
            Tool(
                name="mind_recall",
                description="Load session context. ALWAYS call this first before responding to user. Detects session gaps and returns fresh context.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Project path (defaults to cwd)",
                        },
                        "force_refresh": {
                            "type": "boolean",
                            "default": False,
                            "description": "Force regenerate context even if no changes",
                        },
                    },
                },
            ),
            Tool(
                name="mind_search",
                description="Search across memories. Use when CLAUDE.md context isn't enough. Searches both indexed and current session content.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language search query",
                        },
                        "scope": {
                            "type": "string",
                            "enum": ["project", "all"],
                            "default": "project",
                            "description": "Search current project or all projects",
                        },
                        "types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by type: decision, issue, learning",
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10,
                            "description": "Max results to return",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="mind_checkpoint",
                description="Force process pending memories and regenerate context. Use when you want to ensure recent writes are indexed.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Project path (defaults to cwd)",
                        },
                    },
                },
            ),
            Tool(
                name="mind_edges",
                description="Check for gotchas before implementing risky code.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "description": "What you're about to do",
                        },
                        "code": {
                            "type": "string",
                            "description": "Optional code snippet to analyze",
                        },
                        "stack": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Override auto-detected stack",
                        },
                    },
                    "required": ["intent"],
                },
            ),
            Tool(
                name="mind_add_global_edge",
                description="Add a cross-project gotcha. Use for platform/language issues, not project-specific.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Short title",
                        },
                        "description": {
                            "type": "string",
                            "description": "What the problem is",
                        },
                        "workaround": {
                            "type": "string",
                            "description": "How to fix/avoid it",
                        },
                        "detection": {
                            "type": "object",
                            "description": "Patterns to detect: {context: [], intent: [], code: []}",
                        },
                        "stack_tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tech this applies to",
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["info", "warning", "critical"],
                            "default": "warning",
                        },
                    },
                    "required": ["title", "description", "workaround", "detection"],
                },
            ),
            Tool(
                name="mind_session",
                description="Get current session state from SESSION.md. Use this to check goal, approach, blockers, rejected approaches, assumptions, and discoveries.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Project path (defaults to cwd)",
                        },
                    },
                },
            ),
            Tool(
                name="mind_blocker",
                description="Log a blocker and auto-search memory for solutions. Call this when stuck - it adds to SESSION.md Blockers and searches MEMORY.md for relevant past solutions.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "What's blocking you",
                        },
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional: specific keywords to search for",
                        },
                    },
                    "required": ["description"],
                },
            ),
            Tool(
                name="mind_status",
                description="Check Mind status and project stats.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="mind_remind",
                description="Set a reminder for later. Use for 'remind me to...', 'don't forget to...', etc. Supports 'next session', 'tomorrow', 'in 3 days', specific dates, OR context triggers like 'when I mention auth'.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "What to remind about",
                        },
                        "when": {
                            "type": "string",
                            "description": "When to remind: 'next session', 'tomorrow', 'in 3 days', '2025-12-20', OR 'when I mention auth', 'when we work on database', etc.",
                        },
                    },
                    "required": ["message", "when"],
                },
            ),
            Tool(
                name="mind_reminders",
                description="List all pending reminders. Use to see what reminders are set.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="mind_log",
                description="Log to session or memory. Routes by type: experience/blocker/assumption/rejected -> SESSION.md (ephemeral), decision/learning/problem/progress -> MEMORY.md (permanent), reinforce -> boosts pattern confidence. Call proactively as you work.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "What to log",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["experience", "blocker", "assumption", "rejected", "decision", "learning", "problem", "progress", "feedback", "preference", "blind_spot", "skill", "reinforce"],
                            "description": "Type determines destination: experience/blocker/assumption/rejected -> SESSION, decision/learning/problem/progress -> MEMORY, feedback/preference/blind_spot/skill -> SELF_IMPROVE, reinforce -> boosts pattern confidence",
                        },
                    },
                    "required": ["message"],
                },
            ),
            Tool(
                name="mind_reminder_done",
                description="Mark a reminder as done. Use after completing a reminded task. 'next session' reminders are auto-marked when surfaced.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "index": {
                            "type": "integer",
                            "description": "Index of reminder to mark done (from mind_reminders output)",
                        },
                    },
                    "required": ["index"],
                },
            ),
            Tool(
                name="mind_spawn_helper",
                description="Package current problem for a fresh agent investigation. Use when stuck after 3+ failed attempts. Returns a structured prompt that can be used to spawn a helper agent via Claude Code's Task tool.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "problem": {
                            "type": "string",
                            "description": "What you're stuck on",
                        },
                        "attempts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "What you've already tried",
                        },
                        "hypothesis": {
                            "type": "string",
                            "description": "Your current theory about the root cause",
                        },
                    },
                    "required": ["problem"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle tool calls."""

        if name == "mind_recall":
            return await handle_recall(arguments)
        elif name == "mind_search":
            return await handle_search(arguments)
        elif name == "mind_checkpoint":
            return await handle_checkpoint(arguments)
        elif name == "mind_edges":
            return await handle_edges(arguments)
        elif name == "mind_add_global_edge":
            return await handle_add_global_edge(arguments)
        elif name == "mind_session":
            return await handle_session(arguments)
        elif name == "mind_blocker":
            return await handle_blocker(arguments)
        elif name == "mind_status":
            return await handle_status(arguments)
        elif name == "mind_remind":
            return await handle_remind(arguments)
        elif name == "mind_reminders":
            return await handle_reminders(arguments)
        elif name == "mind_log":
            return await handle_log(arguments)
        elif name == "mind_reminder_done":
            return await handle_reminder_done(arguments)
        elif name == "mind_spawn_helper":
            return await handle_spawn_helper(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


async def handle_recall(args: dict[str, Any]) -> list[TextContent]:
    """Handle mind_recall tool - main session context loader with SESSION.md support."""
    from ..health import auto_repair

    project_path_str = args.get("project_path")
    force_refresh = args.get("force_refresh", False)

    # Get project path
    if project_path_str:
        project_path = Path(project_path_str)
    else:
        project_path = get_current_project()

    if not project_path:
        return [TextContent(type="text", text="Error: No Mind project found. Run 'mind init' first.")]

    memory_file = project_path / ".mind" / "MEMORY.md"
    if not memory_file.exists():
        return [TextContent(type="text", text="Error: No MEMORY.md found. Run 'mind init' first.")]

    # Run auto-repair to fix any missing files (e.g., REMINDERS.md for older projects)
    auto_repair(project_path)

    # Load state
    state = load_state(project_path)
    current_hash = hash_file(memory_file)
    now = int(datetime.now().timestamp() * 1000)
    gap = now - state.get("last_activity", 0)

    # Determine if we need to reprocess
    gap_detected = gap > GAP_THRESHOLD_MS
    hash_changed = current_hash != state.get("memory_hash", "")
    needs_refresh = force_refresh or gap_detected or hash_changed

    # SESSION.md handling - process old session if gap detected
    promoted_count = 0
    learning_styles_promoted = 0
    decayed_count = 0
    session_content = None
    if gap_detected:
        old_session = read_session_file(project_path)
        if old_session:
            # Extract learnings worth keeping and promote to MEMORY.md
            learnings = extract_promotable_learnings(old_session)
            promoted_count = append_to_memory(project_path, learnings)

            # Clear SESSION.md for new session
            clear_session_file(project_path)

        # Apply memory decay (usage-based retention)
        from ..retention import decay_memories
        decay_result = decay_memories(project_path)
        decayed_count = decay_result.get("decayed", 0)

        # Phase 6: Initialize pattern metadata for decay tracking
        # Phase 9: Extract and promote learning styles from feedback
        from ..config import is_self_improve_feature_enabled
        from ..self_improve import (
            promote_learning_styles_from_feedback,
            append_pattern,
            PatternType,
            initialize_pattern_metadata,
        )
        self_improve_data = load_self_improve()

        # Phase 6: Ensure all patterns have metadata for decay tracking
        if is_self_improve_feature_enabled("decay", project_path):
            initialize_pattern_metadata(self_improve_data)

        # Phase 9: Extract learning styles from feedback
        if is_self_improve_feature_enabled("learning_style", project_path):
            new_styles = promote_learning_styles_from_feedback(self_improve_data)
            for style in new_styles:
                if append_pattern(PatternType.LEARNING_STYLE, style.category, style.description):
                    learning_styles_promoted += 1

    # Read current session state
    session_content = read_session_file(project_path)

    # Parse and generate context
    parser = Parser()
    content = memory_file.read_text(encoding="utf-8")
    result = parser.parse(content, str(memory_file))

    entries_processed = len(result.entities)

    # Generate context
    context_gen = ContextGenerator()
    last_activity = datetime.fromtimestamp(state.get("last_activity", now) / 1000) if state.get("last_activity") else None
    context = context_gen.generate(result, last_activity)

    # Load SELF_IMPROVE.md patterns and inject into context
    self_improve_data = load_self_improve()
    self_improve_context = ""
    detected_intuitions: list[Intuition] = []

    # Get project stack for filtering
    registry = ProjectsRegistry.load()
    project_info = registry.get(project_path)
    stack = project_info.stack if project_info else result.project_state.stack

    if self_improve_data.all_patterns():
        self_improve_context = generate_intuition_context(self_improve_data, stack)

        # Phase 2: Pattern Radar - Detect intuitions from session context
        session_content_for_radar = read_session_file(project_path) or ""
        detected_intuitions = detect_intuitions(
            session_content_for_radar,
            self_improve_data,
            stack
        )

        # Build combined context: patterns + intuitions
        combined_context = ""
        if self_improve_context:
            combined_context = self_improve_context

        if detected_intuitions:
            intuition_context = format_intuitions_for_context(detected_intuitions)
            if combined_context:
                combined_context = combined_context + "\n\n" + intuition_context
            else:
                combined_context = intuition_context

        if combined_context:
            # Insert after Session Context section or at the start if not found
            lines = context.split("\n")
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("## Session Context") or line.startswith("## Project State"):
                    # Find end of this section (next ## or end)
                    for j in range(i + 1, len(lines)):
                        if lines[j].startswith("## "):
                            insert_idx = j
                            break
                    else:
                        insert_idx = len(lines)
                    break

            if insert_idx > 0:
                lines.insert(insert_idx, f"\n{combined_context}\n")
                context = "\n".join(lines)
            else:
                # Fallback: append after first few lines
                context = context + f"\n\n{combined_context}"

    # Check for due reminders and inject into context
    due_reminders = get_due_reminders(project_path)
    context_reminders = get_context_reminders(project_path)

    # Auto-mark "next session" reminders as done (they've now been surfaced)
    for r in due_reminders:
        if r["type"] == "next session":
            mark_reminder_done(project_path, r["index"])

    # Find insertion point for reminders (after "Last captured" or "## Memory: Active")
    def find_insert_index(lines):
        for i, line in enumerate(lines):
            if line.startswith("Last captured:"):
                return i + 1
        for i, line in enumerate(lines):
            if line.startswith("## Memory: Active"):
                return i + 1
        return 1  # After first line if nothing found

    if due_reminders or context_reminders:
        lines = context.split("\n")
        insert_idx = find_insert_index(lines)
        reminder_sections = []

        if due_reminders:
            reminder_text = "\n## Reminders Due\n"
            reminder_text += f"You have {len(due_reminders)} reminder(s) for this session:\n"
            for r in due_reminders:
                reminder_text += f"- {r['message']}\n"
            reminder_sections.append(reminder_text)

        if context_reminders:
            context_text = "\n## Context Reminders\n"
            context_text += "Mention these when relevant keywords come up:\n"
            for r in context_reminders:
                context_text += f"- \"{r['message']}\" -> triggers on: {r['due']}\n"
            reminder_sections.append(context_text)

        for section in reversed(reminder_sections):
            lines.insert(insert_idx, section)
        context = "\n".join(lines)

    # Update state
    state["last_activity"] = now
    state["memory_hash"] = current_hash
    state["schema_version"] = 2
    save_state(project_path, state)

    # Health suggestions
    suggestions = []
    file_size_kb = memory_file.stat().st_size / 1024
    if file_size_kb > 100:
        suggestions.append("MEMORY.md is large (>100KB). Consider running 'mind archive' to move old entries.")

    # Parse session sections for quick access (v2 goal-oriented structure)
    session_state = None
    session_warnings = []
    if session_content:
        session_state = {
            "experience": parse_session_section(session_content, "Experience"),
            "blockers": parse_session_section(session_content, "Blockers"),
            "rejected": parse_session_section(session_content, "Rejected"),
            "assumptions": parse_session_section(session_content, "Assumptions"),
        }
        # Generate warnings for loop/rabbit hole detection
        rejected_count = len(session_state["rejected"])
        blocker_count = len(session_state["blockers"])
        if rejected_count >= 3:
            session_warnings.append(f"WARNING: {rejected_count} rejected approaches this session - check mind_session() before trying more fixes")
        if blocker_count >= 2:
            session_warnings.append(f"WARNING: {blocker_count} blockers logged - consider asking user for direction")

    # Memory -> Session retrieval: surface relevant past memories based on session content
    relevant_memories = []
    if session_content:
        # Combine session experiences into a query
        experiences = parse_session_section(session_content, "Experience")
        if experiences:
            # Use recent experiences as query (last 3)
            query_text = " ".join(experiences[-3:])
            relevant_memories = retrieve_relevant_memories(
                query_text,
                memory_file,
                threshold=0.5,
                limit=3,
            )

            # Inject into context if we found relevant memories
            if relevant_memories:
                memories_section = format_relevant_memories(relevant_memories)
                # Insert after Session Context or at the end
                if "## Session Context" in context:
                    context = context.replace(
                        "## Session Context",
                        f"{memories_section}\n\n## Session Context"
                    )
                else:
                    context = context + f"\n\n{memories_section}"

    # v3 bridge integration (parallel operation)
    v3_stats = None
    if V3_AVAILABLE:
        try:
            v3_bridge = get_v3_bridge(project_path)
            v3_stats = v3_bridge.get_stats()
        except Exception:
            pass  # v3 is optional, don't break recall on errors

    # Build self_improve summary for output
    self_improve_summary = None
    if self_improve_data.all_patterns():
        self_improve_summary = {
            "preferences_count": len(self_improve_data.preferences),
            "skills_count": len(self_improve_data.skills),
            "blind_spots_count": len(self_improve_data.blind_spots),
            "anti_patterns_count": len(self_improve_data.anti_patterns),
            "feedback_count": len(self_improve_data.feedback),
            "learning_styles_count": len(self_improve_data.learning_styles),
            "context_injected": bool(self_improve_context),
            "intuitions_triggered": len(detected_intuitions),
        }

    # Build intuitions list for output
    intuitions_output = None
    if detected_intuitions:
        intuitions_output = [
            {
                "type": i.type,
                "message": i.message,
                "source": i.source_pattern,
                "confidence": i.confidence,
            }
            for i in detected_intuitions
        ]

    output = {
        "context": context,
        "session": session_state,
        "session_warnings": session_warnings if session_warnings else None,
        "relevant_memories": relevant_memories if relevant_memories else None,
        "reminders_due": [{
            "message": r["message"],
            "due": r["due"],
            "type": r["type"],
            "index": r["index"],
        } for r in due_reminders] if due_reminders else [],
        "context_reminders": [{
            "message": r["message"],
            "keywords": r["due"],  # For context type, 'due' field holds keywords
            "index": r["index"],
        } for r in context_reminders] if context_reminders else [],
        "self_improve": self_improve_summary,
        "intuitions": intuitions_output,
        "v3": v3_stats,
        "session_info": {
            "last_session": datetime.fromtimestamp(state["last_activity"] / 1000).isoformat() if state.get("last_activity") else None,
            "gap_detected": gap_detected,
            "new_session_started": gap_detected,
            "promoted_to_memory": promoted_count,
            "entries_processed": entries_processed,
            "refreshed": needs_refresh,
        },
        "health": {
            "memory_count": entries_processed,
            "file_size_kb": round(file_size_kb, 1),
            "suggestions": suggestions,
        },
    }

    # Determine emotion based on state
    action = "recall"
    if session_warnings:
        action = "warning"
    elif gap_detected:
        action = "new_session"
    message = f"Loaded {entries_processed} memories"
    if gap_detected:
        message = f"New session started! {promoted_count} items promoted"

    return [TextContent(type="text", text=mindful_response(action, output, message))]


async def handle_search(args: dict[str, Any]) -> list[TextContent]:
    """Handle mind_search tool - searches both indexed and raw content."""
    query = args.get("query", "")
    scope = args.get("scope", "project")
    types = args.get("types")
    limit = args.get("limit", 10)

    if not query:
        return [TextContent(type="text", text="Error: query is required")]

    all_entities: list[Entity] = []
    raw_content = ""
    parser = Parser()

    if scope == "project":
        project_path = get_current_project()
        if not project_path:
            return [TextContent(type="text", text="No Mind project found in current directory")]

        memory_file = project_path / ".mind" / "MEMORY.md"
        if memory_file.exists():
            raw_content = memory_file.read_text(encoding="utf-8")
            result = parser.parse(raw_content, str(memory_file))
            all_entities.extend(result.entities)
    else:
        # Search all projects
        registry = ProjectsRegistry.load()
        for project in registry.list_all():
            memory_file = Path(project.path) / ".mind" / "MEMORY.md"
            if memory_file.exists():
                content = memory_file.read_text(encoding="utf-8")
                raw_content += content + "\n"
                result = parser.parse(content, str(memory_file))
                all_entities.extend(result.entities)

    # Search indexed entities
    indexed_results = search_entities(query, all_entities, types, limit)

    # Also search raw content for same-session support
    raw_results = search_raw_content(raw_content, query, limit // 2)

    # Merge and dedupe (prefer indexed over raw)
    seen_titles = set(r["title"] for r in indexed_results)
    merged = indexed_results.copy()
    for r in raw_results:
        if r["title"] not in seen_titles:
            merged.append(r)
            seen_titles.add(r["title"])

    # Re-sort and limit
    merged.sort(key=lambda r: (r["relevance"], r.get("confidence", 0)), reverse=True)
    merged = merged[:limit]

    output = {
        "query": query,
        "total": len(merged),
        "results": merged,
    }

    # Keep session alive - user is actively working
    if scope == "project":
        project_path = get_current_project()
        if project_path:
            touch_activity(project_path)

            # Track search result access for usage-based retention
            if merged:
                from ..retention import track_memory_access
                for result in merged[:3]:  # Track top 3 results
                    if "title" in result:
                        track_memory_access(project_path, result["title"])

    match_count = len(output.get("results", []))
    message = f"Found {match_count} matches" if match_count else "No matches found"
    return [TextContent(type="text", text=mindful_response("search", output, message))]


async def handle_checkpoint(args: dict[str, Any]) -> list[TextContent]:
    """Handle mind_checkpoint tool - force process pending memories."""
    project_path_str = args.get("project_path")

    if project_path_str:
        project_path = Path(project_path_str)
    else:
        project_path = get_current_project()

    if not project_path:
        return [TextContent(type="text", text="Error: No Mind project found")]

    memory_file = project_path / ".mind" / "MEMORY.md"
    if not memory_file.exists():
        return [TextContent(type="text", text="Error: No MEMORY.md found")]

    # Parse
    parser = Parser()
    content = memory_file.read_text(encoding="utf-8")
    result = parser.parse(content, str(memory_file))

    # Update state
    state = load_state(project_path)
    state["last_activity"] = int(datetime.now().timestamp() * 1000)
    state["memory_hash"] = hash_file(memory_file)
    save_state(project_path, state)

    output = {
        "processed": len(result.entities),
        "context_updated": True,
        "timestamp": datetime.now().isoformat(),
    }

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def handle_edges(args: dict[str, Any]) -> list[TextContent]:
    """Handle mind_edges tool."""
    intent = args.get("intent", "")
    code = args.get("code")
    stack = args.get("stack")

    if not intent:
        return [TextContent(type="text", text="Error: intent is required")]

    # Get stack from project if not provided
    if not stack:
        project_path = get_current_project()
        if project_path:
            registry = ProjectsRegistry.load()
            project_info = registry.get(project_path)
            if project_info:
                stack = project_info.stack

    stack = stack or []

    # Load global edges
    global_edges = load_global_edges()

    # Load project edges
    project_edges = []
    project_path = get_current_project()
    if project_path:
        memory_file = project_path / ".mind" / "MEMORY.md"
        if memory_file.exists():
            parser = Parser()
            content = memory_file.read_text(encoding="utf-8")
            result = parser.parse(content, str(memory_file))
            project_edges = [{"title": e.title, "workaround": e.workaround} for e in result.project_edges]

    warnings = match_edges(intent, code, stack, global_edges, project_edges)

    return [TextContent(type="text", text=json.dumps(warnings, indent=2))]


async def handle_add_global_edge(args: dict[str, Any]) -> list[TextContent]:
    """Handle mind_add_global_edge tool."""
    title = args.get("title", "")
    description = args.get("description", "")
    workaround = args.get("workaround", "")
    detection = args.get("detection", {})
    stack_tags = args.get("stack_tags", [])
    severity = args.get("severity", "warning")

    if not title or not description or not workaround:
        return [TextContent(type="text", text="Error: title, description, and workaround are required")]

    edge_id = hashlib.md5(f"{title}{datetime.now().isoformat()}".encode()).hexdigest()[:8]

    edge = {
        "id": edge_id,
        "title": title,
        "description": description,
        "workaround": workaround,
        "detection": detection,
        "stack_tags": stack_tags,
        "severity": severity,
        "created_at": datetime.now().isoformat(),
    }

    edges = load_global_edges()
    edges.append(edge)
    save_global_edges(edges)

    return [TextContent(type="text", text=json.dumps(edge, indent=2))]


async def handle_session(args: dict[str, Any]) -> list[TextContent]:
    """Handle mind_session tool - get current session state."""
    project_path_str = args.get("project_path")

    if project_path_str:
        project_path = Path(project_path_str)
    else:
        project_path = get_current_project()

    if not project_path:
        return [TextContent(type="text", text="Error: No Mind project found")]

    session_content = read_session_file(project_path)
    if not session_content:
        return [TextContent(type="text", text=json.dumps({
            "error": "No SESSION.md found. Run 'mind init' or create .mind/SESSION.md",
            "session": None,
        }, indent=2))]

    # Parse all sections (simplified structure)
    session_state = {
        "experience": parse_session_section(session_content, "Experience"),
        "blockers": parse_session_section(session_content, "Blockers"),
        "rejected": parse_session_section(session_content, "Rejected"),
        "assumptions": parse_session_section(session_content, "Assumptions"),
    }

    # Count items
    total_items = sum(len(v) for v in session_state.values())

    output = {
        "session": session_state,
        "stats": {
            "total_items": total_items,
            "blockers_count": len(session_state["blockers"]),
            "experience_count": len(session_state["experience"]),
        },
    }

    # Keep session alive - user is actively working
    touch_activity(project_path)

    message = f"{total_items} items tracked"
    return [TextContent(type="text", text=mindful_response("session", output, message))]


async def handle_blocker(args: dict[str, Any]) -> list[TextContent]:
    """Handle mind_blocker tool - log blocker and auto-search memory."""
    description = args.get("description", "")
    keywords = args.get("keywords", [])

    if not description:
        return [TextContent(type="text", text="Error: description is required")]

    project_path = get_current_project()
    if not project_path:
        return [TextContent(type="text", text="Error: No Mind project found")]

    # 1. Add blocker to SESSION.md
    session_file = get_session_file(project_path)
    if session_file.exists():
        session_content = session_file.read_text(encoding="utf-8")

        # Find Blockers section and add entry
        blockers_pattern = r"(## Blockers\s*\n(?:<!--[^>]*-->\s*\n)?)"
        match = re.search(blockers_pattern, session_content)
        if match:
            insert_pos = match.end()
            # Check if there's already content after the section (no blank line before next section)
            rest = session_content[insert_pos:]
            if rest and not rest.startswith("\n") and not rest.startswith("-"):
                new_entry = f"- {description}\n\n"  # Add extra newline before next section
            else:
                new_entry = f"- {description}\n"
            new_content = session_content[:insert_pos] + new_entry + session_content[insert_pos:]
            session_file.write_text(new_content, encoding="utf-8")

    # 2. Extract keywords from description if not provided
    if not keywords:
        # Extract meaningful words (3+ chars, not common words)
        stop_words = {"the", "and", "for", "with", "that", "this", "from", "have", "not", "but", "are", "was", "been"}
        words = re.findall(r'\b[a-zA-Z]{3,}\b', description.lower())
        keywords = [w for w in words if w not in stop_words][:5]  # Top 5 keywords

    # 3. Search memory for solutions
    query = " ".join(keywords) if keywords else description

    parser = Parser()
    memory_file = project_path / ".mind" / "MEMORY.md"
    all_entities: list[Entity] = []
    raw_content = ""

    if memory_file.exists():
        raw_content = memory_file.read_text(encoding="utf-8")
        result = parser.parse(raw_content, str(memory_file))
        all_entities.extend(result.entities)

    # Search indexed entities
    indexed_results = search_entities(query, all_entities, None, 5)

    # Also search raw content
    raw_results = search_raw_content(raw_content, query, 3)

    # Merge results
    seen_titles = set(r["title"] for r in indexed_results)
    merged = indexed_results.copy()
    for r in raw_results:
        if r["title"] not in seen_titles:
            merged.append(r)
            seen_titles.add(r["title"])

    output = {
        "blocker_logged": True,
        "description": description,
        "keywords_searched": keywords,
        "memory_search_results": merged[:5],
        "suggestions": [],
    }

    # Add suggestions based on results
    if merged:
        output["suggestions"].append(f"Found {len(merged)} potentially relevant memories - review them")
    else:
        output["suggestions"].append("No direct matches in memory - consider:")
        output["suggestions"].append("1. Check Working Assumptions - is one wrong?")
        output["suggestions"].append("2. Check pivot condition in Current Approach")
        output["suggestions"].append("3. Zoom out and ask user for guidance")

    # Keep session alive - user is actively working
    touch_activity(project_path)

    match_count = len(merged)
    message = f"Blocker logged, found {match_count} related memories" if match_count else "Blocker logged, no related memories found"
    return [TextContent(type="text", text=mindful_response("blocker", output, message))]


async def handle_status(args: dict[str, Any]) -> list[TextContent]:
    """Handle mind_status tool (v2: no daemon)."""
    registry = ProjectsRegistry.load()

    # Current project info
    current_project = None
    project_path = get_current_project()
    if project_path:
        project_info = registry.get(project_path)
        if project_info:
            memory_file = project_path / ".mind" / "MEMORY.md"
            entity_counts = {"decisions": 0, "issues_open": 0, "issues_resolved": 0, "learnings": 0}

            if memory_file.exists():
                parser = Parser()
                content = memory_file.read_text(encoding="utf-8")
                result = parser.parse(content, str(memory_file))

                for e in result.entities:
                    if e.type == EntityType.DECISION:
                        entity_counts["decisions"] += 1
                    elif e.type == EntityType.ISSUE:
                        if e.status and e.status.value == "resolved":
                            entity_counts["issues_resolved"] += 1
                        else:
                            entity_counts["issues_open"] += 1
                    elif e.type == EntityType.LEARNING:
                        entity_counts["learnings"] += 1

            # Load state
            state = load_state(project_path)

            current_project = {
                "path": project_info.path,
                "name": project_info.name,
                "stack": project_info.stack,
                "last_activity": datetime.fromtimestamp(state.get("last_activity", 0) / 1000).isoformat() if state.get("last_activity") else None,
                "stats": entity_counts,
            }

    # Get confidence stats for patterns (Phase 6)
    confidence_stats = get_confidence_stats()

    # Get self_improve stats
    self_improve_data = load_self_improve()
    self_improve_stats = None
    if self_improve_data.all_patterns():
        self_improve_stats = {
            "total_patterns": len(self_improve_data.all_patterns()),
            "preferences": len(self_improve_data.preferences),
            "skills": len(self_improve_data.skills),
            "blind_spots": len(self_improve_data.blind_spots),
            "anti_patterns": len(self_improve_data.anti_patterns),
            "feedback": len(self_improve_data.feedback),
            "learning_styles": len(self_improve_data.learning_styles),
        }

    status = {
        "version": 2,
        "current_project": current_project,
        "global_stats": {
            "projects_registered": len(registry.list_all()),
            "global_edges": len(load_global_edges()),
        },
        "self_improve": self_improve_stats,
        "confidence": confidence_stats if confidence_stats.get("total_patterns", 0) > 0 else None,
    }

    return [TextContent(type="text", text=json.dumps(status, indent=2))]


async def handle_remind(args: dict[str, Any]) -> list[TextContent]:
    """Handle mind_remind tool - set a reminder for later."""
    message = args.get("message", "")
    when = args.get("when", "")

    if not message:
        return [TextContent(type="text", text="Error: message is required")]
    if not when:
        return [TextContent(type="text", text="Error: when is required")]

    project_path = get_current_project()
    if not project_path:
        return [TextContent(type="text", text="Error: No Mind project found")]

    # Parse the 'when' string
    due, reminder_type = parse_when(when)

    # Add the reminder
    reminder = add_reminder(project_path, message, due, reminder_type)

    output = {
        "success": True,
        "reminder": reminder,
        "message": f"Reminder set: '{message}' - will remind {reminder_type if reminder_type == 'next session' else f'on {due}'}",
    }

    msg = f"I'll remember! ({reminder_type})"
    return [TextContent(type="text", text=mindful_response("remind", output, msg))]


async def handle_reminders(args: dict[str, Any]) -> list[TextContent]:
    """Handle mind_reminders tool - list all pending reminders."""
    project_path = get_current_project()
    if not project_path:
        return [TextContent(type="text", text="Error: No Mind project found")]

    reminders = parse_reminders(project_path)

    # Separate pending and done
    pending = [r for r in reminders if not r["done"]]
    done = [r for r in reminders if r["done"]]

    output = {
        "pending": [{
            "message": r["message"],
            "due": r["due"],
            "type": r["type"],
        } for r in pending],
        "done_count": len(done),
        "total": len(reminders),
    }

    message = f"{len(pending)} pending reminders"
    return [TextContent(type="text", text=mindful_response("reminders", output, message))]


def auto_categorize_session_type(message: str) -> str:
    """Auto-detect session type from message content.

    Patterns detected:
    - rejected: "tried X, didn't work", "X failed", "won't work", "rejected"
    - blocker: "stuck", "can't", "blocked", "don't know how"
    - assumption: "assuming", "I think", "probably", "should be"
    - experience: default for everything else

    Returns:
        One of: "rejected", "blocker", "assumption", "experience"
    """
    msg_lower = message.lower()

    # Rejected patterns - things that didn't work
    rejected_patterns = [
        "tried", "didn't work", "doesn't work", "won't work", "failed",
        "rejected", "ruled out", "not going to work", "abandoned",
        "gave up on", "scrapped", "discarded", "nope", "no good",
        "too complex", "too slow", "too much", "overkill",
    ]
    if any(p in msg_lower for p in rejected_patterns):
        return "rejected"

    # Blocker patterns - stuck on something
    blocker_patterns = [
        "stuck", "blocked", "can't figure", "don't know how",
        "no idea", "confused", "lost", "help", "struggling",
        "hitting a wall", "dead end", "roadblock",
    ]
    if any(p in msg_lower for p in blocker_patterns):
        return "blocker"

    # Assumption patterns - things being assumed true
    assumption_patterns = [
        "assuming", "assume", "i think", "probably", "should be",
        "i believe", "expecting", "guessing", "hypothesis",
        "if this is true", "based on", "seems like",
    ]
    if any(p in msg_lower for p in assumption_patterns):
        return "assumption"

    # Default to experience
    return "experience"


async def handle_log(args: dict[str, Any]) -> list[TextContent]:
    """Handle mind_log tool - route to SESSION.md, MEMORY.md, or SELF_IMPROVE.md based on type."""
    from ..logging_levels import get_logging_level, should_log_message

    message = args.get("message", "")
    explicit_type = args.get("type", None)

    if not message:
        return [TextContent(type="text", text="Error: message is required")]

    # Auto-categorize if type not explicitly provided or is "experience" (default)
    # This allows explicit types to override, but auto-detects for convenience
    if explicit_type is None or explicit_type == "experience":
        entry_type = auto_categorize_session_type(message)
        was_auto = entry_type != "experience" and explicit_type != entry_type
    else:
        entry_type = explicit_type
        was_auto = False

    project_path = get_current_project()
    if not project_path:
        return [TextContent(type="text", text="Error: No Mind project found")]

    # Check logging level filtering
    logging_level = get_logging_level(project_path)
    should_log, skip_reason = should_log_message(message, entry_type, logging_level)

    if not should_log:
        # Return early - message filtered based on logging level
        output = {
            "success": True,
            "action": "filtered",
            "type": entry_type,
            "logging_level": logging_level,
            "reason": skip_reason,
        }
        return [TextContent(type="text", text=mindful_response("skip", output, skip_reason or "Filtered"))]

    # Handle reinforce type specially - boosts pattern confidence
    if entry_type == "reinforce":
        result = reinforce_pattern(message)
        touch_activity(project_path)
        output = {
            "success": result["success"],
            "action": "reinforced",
            "pattern": message,
            "pattern_hash": result.get("pattern_hash"),
            "reinforcement_count": result.get("reinforcement_count"),
            "new_confidence": result.get("new_confidence"),
        }
        msg = f"Pattern reinforced! Confidence: {result.get('new_confidence', 0):.0%}"
        return [TextContent(type="text", text=mindful_response("reinforce", output, msg))]

    # Route by type:
    # - SESSION.md (ephemeral): experience, blocker, assumption, rejected
    # - MEMORY.md (permanent): decision, learning, problem, progress
    # - SELF_IMPROVE.md (global): feedback, preference, blind_spot, skill
    session_types = {"experience", "blocker", "assumption", "rejected"}
    memory_types = {"decision", "learning", "problem", "progress"}
    global_types = {"feedback", "preference", "blind_spot", "skill"}

    # Prefixes for memory entries
    memory_prefixes = {
        "decision": "decided:",
        "learning": "learned:",
        "problem": "problem:",
        "progress": "fixed:",
    }

    success = False
    target = "unknown"
    contradiction_info = None
    loop_warning = None
    retrieved_memories = None

    if entry_type in global_types:
        # Write to SELF_IMPROVE.md (global, cross-project)
        result = log_to_self_improve(message, entry_type, project_path)
        success = result.get("success", False)
        target = "SELF_IMPROVE.md"
        # Phase 8: Check for contradictions
        if result.get("action") == "contradiction_detected":
            contradiction_info = result.get("conflicts", [])
    elif entry_type in session_types:
        # Memory retrieval for session types
        retrieved_memories = None
        # Write to SESSION.md
        session_file = get_session_file(project_path)
        if not session_file.exists():
            clear_session_file(project_path)

        # Memory -> Session retrieval for experience and blocker types
        memory_file = project_path / ".mind" / "MEMORY.md"
        if entry_type in ("experience", "blocker") and memory_file.exists():
            # Check if this is first experience of session (session file empty or just created)
            session_content = read_session_file(project_path)
            experiences = parse_session_section(session_content, "Experience") if session_content else []

            # Retrieve relevant memories if:
            # - First experience log (empty experiences)
            # - Any blocker log (always help when stuck)
            should_retrieve = (entry_type == "experience" and len(experiences) == 0) or entry_type == "blocker"

            if should_retrieve:
                retrieved_memories = retrieve_relevant_memories(
                    message,
                    memory_file,
                    threshold=0.5,
                    limit=2,
                )

        # Loop detection: check for similar rejections before logging (semantic similarity)
        loop_warning = None
        if entry_type == "rejected":
            session_content = read_session_file(project_path)
            if session_content:
                existing_rejections = parse_session_section(session_content, "Rejected")
                loop_warning = find_similar_rejection(message, existing_rejections, threshold=0.6)

        # Map type to section
        section_map = {
            "experience": "Experience",
            "blocker": "Blockers",
            "assumption": "Assumptions",
            "rejected": "Rejected",
        }
        section = section_map.get(entry_type, "Experience")
        success = update_session_section(project_path, section, message, append=True)
        target = "SESSION.md"
    else:
        # Write to MEMORY.md
        prefix = memory_prefixes.get(entry_type, "")
        if prefix and not any(message.lower().startswith(p) for p in memory_prefixes.values()):
            formatted = f"{prefix} {message}"
        else:
            formatted = message
        success = append_memory_entry(project_path, formatted, entry_type)
        target = "MEMORY.md"
        message = formatted if entry_type in memory_types else message

    if success:
        # Keep session alive - user is actively working
        touch_activity(project_path)
        output = {
            "success": True,
            "logged": message,
            "type": entry_type,
            "target": target,
        }

        # Indicate if auto-categorized
        if was_auto:
            output["auto_categorized"] = True
            output["detected_as"] = entry_type

        # Add loop warning if detected (for rejected type)
        if entry_type == "rejected" and loop_warning:
            output["loop_warning"] = loop_warning
            output["methodology"] = loop_warning.get("methodology", "")
            output["spawn_suggestion"] = loop_warning.get("spawn_suggestion", "")
            similarity = loop_warning.get('similarity', 0)
            severity = loop_warning.get('severity', 'moderate')
            severity_emoji = {"critical": "STOP", "high": "WARNING", "moderate": "CAUTION"}.get(severity, "WARNING")
            msg = f"{severity_emoji}: {similarity:.0%} similar to previous rejection"
            return [TextContent(type="text", text=mindful_response("warning", output, msg))]

        # Add retrieved memories if found (for experience/blocker types)
        if retrieved_memories:
            output["relevant_memories"] = retrieved_memories
            output["memory_hint"] = "You've dealt with similar before - check relevant_memories"
            msg = f"{entry_type} -> {target} (found {len(retrieved_memories)} relevant memories)"
            return [TextContent(type="text", text=mindful_response("log", output, msg))]

        msg = f"{entry_type} -> {target}"
        return [TextContent(type="text", text=mindful_response("log", output, msg))]
    elif contradiction_info:
        # Phase 8: Pattern contradicts existing pattern
        output = {
            "success": False,
            "action": "contradiction_detected",
            "conflicts": contradiction_info,
            "suggestion": (
                "This pattern conflicts with existing patterns. "
                "Use type='reinforce' on the correct one, or remove the outdated pattern."
            ),
        }
        return [TextContent(type="text", text=mindful_response("warning", output, "Contradiction detected"))]
    else:
        output = {
            "success": False,
            "error": f"Failed to write to {target}",
        }
        return [TextContent(type="text", text=mindful_response("error", output, f"Failed to write to {target}"))]


def log_to_self_improve(message: str, log_type: str, project_path: Path = None) -> dict:
    """Log directly to global SELF_IMPROVE.md with contradiction checking.

    Args:
        message: The message to log
        log_type: One of: feedback, preference, blind_spot, skill
        project_path: Project path for config lookup (optional)

    Returns:
        Dict with success status and details (action, conflicts if any)
    """
    from ..self_improve import (
        append_pattern,
        PatternType,
        add_pattern_with_contradiction_check,
    )
    from ..config import is_self_improve_feature_enabled

    # Map log type to PatternType
    type_map = {
        "feedback": PatternType.FEEDBACK,
        "preference": PatternType.PREFERENCE,
        "blind_spot": PatternType.BLIND_SPOT,
        "skill": PatternType.SKILL,
    }

    pattern_type = type_map.get(log_type)
    if not pattern_type:
        return {"success": False, "error": f"Unknown log type: {log_type}"}

    # For feedback, the message is the full description
    # For others, we use "general" as the default category
    category = "general"

    # Phase 8: Check for contradictions if enabled (skip for feedback type)
    if (
        project_path
        and pattern_type != PatternType.FEEDBACK
        and is_self_improve_feature_enabled("contradiction", project_path)
    ):
        result = add_pattern_with_contradiction_check(pattern_type, category, message)
        return result

    # No contradiction check - just append directly
    success = append_pattern(pattern_type, category, message)
    return {"success": success, "action": "added" if success else "failed"}


async def handle_reminder_done(args: dict[str, Any]) -> list[TextContent]:
    """Handle mind_reminder_done tool - mark a reminder as done."""
    index = args.get("index")

    if index is None:
        return [TextContent(type="text", text="Error: index is required")]

    project_path = get_current_project()
    if not project_path:
        return [TextContent(type="text", text="Error: No Mind project found")]

    # Get reminder info before marking
    reminders = parse_reminders(project_path)
    reminder_info = None
    for r in reminders:
        if r["index"] == index:
            reminder_info = r
            break

    if not reminder_info:
        return [TextContent(type="text", text=f"Error: No reminder found at index {index}")]

    if reminder_info["done"]:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "Reminder already marked as done",
            "reminder": reminder_info["message"],
        }, indent=2))]

    success = mark_reminder_done(project_path, index)

    if success:
        output = {
            "success": True,
            "marked_done": reminder_info["message"],
            "index": index,
        }
    else:
        output = {
            "success": False,
            "error": "Failed to mark reminder as done",
        }

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def handle_spawn_helper(args: dict[str, Any]) -> list[TextContent]:
    """Handle mind_spawn_helper tool - package problem for fresh agent investigation."""
    problem = args.get("problem")
    attempts = args.get("attempts", [])
    hypothesis = args.get("hypothesis", "")

    if not problem:
        return [TextContent(type="text", text="Error: problem description is required")]

    project_path = get_current_project()
    if not project_path:
        return [TextContent(type="text", text="Error: No Mind project found")]

    # Get current session state
    session_state = None
    session_file = get_session_file(project_path)
    if session_file.exists():
        session_content = session_file.read_text(encoding="utf-8")
        session_state = {
            "experience": parse_session_section(session_content, "Experience"),
            "blockers": parse_session_section(session_content, "Blockers"),
            "rejected": parse_session_section(session_content, "Rejected"),
            "assumptions": parse_session_section(session_content, "Assumptions"),
        }

    # Build the agent prompt
    rejected_approaches = session_state.get("rejected", []) if session_state else []
    all_attempts = list(set(attempts + rejected_approaches))  # Combine and dedupe

    agent_prompt = f"""## Investigation Task

**Problem:** {problem}

**Previous Attempts (DO NOT REPEAT THESE):**
{chr(10).join(f"- {a}" for a in all_attempts) if all_attempts else "- (none documented)"}

"""
    if hypothesis:
        agent_prompt += f"""**Current Hypothesis:** {hypothesis}

"""

    agent_prompt += """**Your Task:**
1. Read the relevant code files to understand the context
2. Identify what the previous attempts might have missed
3. Look for root causes in different areas than already tried
4. Either:
   a) Implement a fix if you find the solution
   b) Return a detailed analysis of what you found

**Important:**
- Do NOT try any approach listed under "Previous Attempts"
- If you identify the same root cause as the hypothesis, dig deeper
- Check for edge cases, race conditions, or assumptions that might be wrong
- Consider if the problem is actually in a different location than expected

Return your findings with:
- What you discovered
- Why previous attempts didn't work
- Your recommended solution (or next investigation direction)
"""

    output = {
        "success": True,
        "agent_prompt": agent_prompt,
        "usage": (
            "Use Claude Code's Task tool with subagent_type='Explore' or 'general-purpose' "
            "and pass the agent_prompt as the prompt parameter."
        ),
        "problem_summary": problem,
        "attempts_count": len(all_attempts),
    }

    return [TextContent(type="text", text=mindful_response("spawn", output, "Agent prompt packaged"))]


def run_server() -> None:
    """Run the MCP server."""
    import asyncio

    server = create_server()

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(main())
