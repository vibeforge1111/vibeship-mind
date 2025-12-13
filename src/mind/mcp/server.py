"""Mind MCP server - 11 tools for AI memory (v2: daemon-free, stateless)."""

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

from ..context import ContextGenerator
from ..parser import Entity, EntityType, Parser
from ..storage import ProjectsRegistry, get_mind_home
from ..templates import SESSION_TEMPLATE


# Gap threshold for session detection (30 minutes)
GAP_THRESHOLD_MS = 30 * 60 * 1000


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


def append_to_memory(project_path: Path, learnings: list[dict]) -> int:
    """Append promoted learnings to MEMORY.md."""
    if not learnings:
        return 0

    memory_file = project_path / ".mind" / "MEMORY.md"
    if not memory_file.exists():
        return 0

    content = memory_file.read_text(encoding="utf-8")

    # Add learnings at the end
    additions = f"\n\n<!-- Promoted from SESSION.md on {date.today().isoformat()} -->\n"
    for learning in learnings:
        additions += f"{learning['content']}\n"

    memory_file.write_text(content + additions, encoding="utf-8")
    return len(learnings)


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
def update_session_section(project_path: Path, section_name: str, content: str, append: bool = False) -> bool:
    """Update a section in SESSION.md."""
    session_file = get_session_file(project_path)
    if not session_file.exists():
        return False

    session_content = session_file.read_text(encoding="utf-8")

    # Find the section
    pattern = rf"(## {re.escape(section_name)}\s*\n(?:<!--[^>]*-->\s*\n)?)"
    match = re.search(pattern, session_content)

    if not match:
        return False

    insert_pos = match.end()

    if append:
        # Add as new item
        new_entry = f"- {content}\n"
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
    """Get the current project path from CWD."""
    cwd = Path.cwd()

    # Check if CWD has .mind directory
    if (cwd / ".mind").exists():
        return cwd

    # Check parent directories
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
    """Simple keyword search across entities."""
    query_lower = query.lower()
    query_words = set(query_lower.split())

    results = []

    for entity in entities:
        # Filter by type
        if types and entity.type.value not in types:
            continue

        # Score by keyword match
        content_lower = entity.content.lower()
        title_lower = entity.title.lower()

        # Count matching words
        matches = sum(1 for word in query_words if word in content_lower or word in title_lower)

        if matches > 0:
            relevance = matches / len(query_words)
            results.append({
                "type": entity.type.value,
                "title": entity.title,
                "content": entity.content,
                "reasoning": entity.reasoning,
                "status": entity.status.value if entity.status else None,
                "date": entity.date.isoformat() if entity.date else None,
                "source_file": entity.source_file,
                "source_line": entity.source_line,
                "confidence": entity.confidence,
                "relevance": relevance,
                "source": "indexed",
            })

    # Sort by relevance, then confidence
    results.sort(key=lambda r: (r["relevance"], r["confidence"]), reverse=True)

    return results[:limit]


def search_raw_content(content: str, query: str, limit: int = 10) -> list[dict]:
    """Search raw MEMORY.md content for unparsed matches (same-session support)."""
    query_lower = query.lower()
    query_words = set(query_lower.split())
    results = []

    lines = content.split("\n")
    for i, line in enumerate(lines):
        line_lower = line.lower()
        matches = sum(1 for word in query_words if word in line_lower)

        if matches > 0 and line.strip():
            relevance = matches / len(query_words)
            results.append({
                "type": "raw",
                "title": line.strip()[:100],
                "content": line.strip(),
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
                description="Log to session or memory. Routes by type: experience/blocker/assumption/rejected -> SESSION.md (ephemeral), decision/learning/problem/progress -> MEMORY.md (permanent). Call proactively as you work.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "What to log",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["experience", "blocker", "assumption", "rejected", "decision", "learning", "problem", "progress"],
                            "description": "Type determines destination: experience/blocker/assumption/rejected -> SESSION, decision/learning/problem/progress -> MEMORY",
                        },
                    },
                    "required": ["message"],
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
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


async def handle_recall(args: dict[str, Any]) -> list[TextContent]:
    """Handle mind_recall tool - main session context loader with SESSION.md support."""
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
    session_content = None
    if gap_detected:
        old_session = read_session_file(project_path)
        if old_session:
            # Extract learnings worth keeping and promote to MEMORY.md
            learnings = extract_promotable_learnings(old_session)
            promoted_count = append_to_memory(project_path, learnings)

            # Clear SESSION.md for new session
            clear_session_file(project_path)

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

    # Check for due reminders and inject into context
    due_reminders = get_due_reminders(project_path)
    context_reminders = get_context_reminders(project_path)

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
    if session_content:
        session_state = {
            "experience": parse_session_section(session_content, "Experience"),
            "blockers": parse_session_section(session_content, "Blockers"),
            "rejected": parse_session_section(session_content, "Rejected"),
            "assumptions": parse_session_section(session_content, "Assumptions"),
        }

    output = {
        "context": context,
        "session": session_state,
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

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


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

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


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

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


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

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


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

    status = {
        "version": 2,
        "current_project": current_project,
        "global_stats": {
            "projects_registered": len(registry.list_all()),
            "global_edges": len(load_global_edges()),
        },
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

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


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

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def handle_log(args: dict[str, Any]) -> list[TextContent]:
    """Handle mind_log tool - route to SESSION.md or MEMORY.md based on type."""
    message = args.get("message", "")
    entry_type = args.get("type", "experience")

    if not message:
        return [TextContent(type="text", text="Error: message is required")]

    project_path = get_current_project()
    if not project_path:
        return [TextContent(type="text", text="Error: No Mind project found")]

    # Route by type:
    # - SESSION.md (ephemeral): experience, blocker, assumption, rejected
    # - MEMORY.md (permanent): decision, learning, problem, progress
    session_types = {"experience", "blocker", "assumption", "rejected"}
    memory_types = {"decision", "learning", "problem", "progress"}

    # Prefixes for memory entries
    memory_prefixes = {
        "decision": "decided:",
        "learning": "learned:",
        "problem": "problem:",
        "progress": "fixed:",
    }

    if entry_type in session_types:
        # Write to SESSION.md
        session_file = get_session_file(project_path)
        if not session_file.exists():
            clear_session_file(project_path)

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
        output = {
            "success": True,
            "logged": message,
            "type": entry_type,
            "target": target,
        }
    else:
        output = {
            "success": False,
            "error": f"Failed to write to {target}",
        }

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


def run_server() -> None:
    """Run the MCP server."""
    import asyncio

    server = create_server()

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(main())
