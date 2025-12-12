"""Mind MCP server - 6 tools for AI memory (v2: daemon-free, with session memory)."""

import hashlib
import json
import os
import re
from datetime import date, datetime
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

    Promotion rules (v2 goal-oriented structure):
    - "Rejected Approaches" with strategic reasoning -> decision
    - "Discoveries" with tech patterns or file paths -> learning
    - "Blockers" that were resolved -> gotcha (if tech-specific)
    """
    learnings = []

    # "Rejected Approaches" become decisions (strategic, not tactical)
    rejected_items = parse_session_section(session_content, "Rejected Approaches")
    for item in rejected_items:
        # Only promote if it has reasoning (contains " - " separator)
        if " - " in item:
            learnings.append({
                "type": "decision",
                "content": f"decided against: {item}",
            })

    # "Discoveries" items with tech patterns or file paths persist
    discovered_items = parse_session_section(session_content, "Discoveries")
    for item in discovered_items:
        has_path = bool(re.search(r'[/\\][\w.-]+\.\w+|`[^`]+`', item))
        has_tech = bool(re.search(
            r'\b(Safari|Chrome|Firefox|Windows|Linux|macOS|iOS|Android|'
            r'npm|yarn|pip|cargo|apt|brew|docker|kubernetes|'
            r'React|Vue|Angular|Node|Python|Rust|Go|Java|'
            r'httpOnly|cookie|localStorage|JWT|OAuth|CORS|'
            r'bcrypt|hash|SSL|TLS|HTTP|HTTPS)\b',
            item, re.IGNORECASE
        ))
        has_structure = bool(re.search(
            r'\b(table|column|field|endpoint|middleware|component|'
            r'function|class|module|directory|file|config)\b',
            item, re.IGNORECASE
        ))
        has_arrow = '->' in item or '=>' in item

        if has_path or has_tech or has_structure or has_arrow:
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
    """Create the MCP server with 4 tools (v2: daemon-free)."""
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
            "goal": parse_session_section(session_content, "The Goal"),
            "current_approach": parse_session_section(session_content, "Current Approach"),
            "blockers": parse_session_section(session_content, "Blockers"),
            "rejected_approaches": parse_session_section(session_content, "Rejected Approaches"),
            "working_assumptions": parse_session_section(session_content, "Working Assumptions"),
            "discoveries": parse_session_section(session_content, "Discoveries"),
        }

    output = {
        "context": context,
        "session": session_state,
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
    """Handle mind_session tool - get current session state (v2 goal-oriented)."""
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

    # Parse all sections (v2 goal-oriented structure)
    session_state = {
        "goal": parse_session_section(session_content, "The Goal"),
        "current_approach": parse_session_section(session_content, "Current Approach"),
        "blockers": parse_session_section(session_content, "Blockers"),
        "rejected_approaches": parse_session_section(session_content, "Rejected Approaches"),
        "working_assumptions": parse_session_section(session_content, "Working Assumptions"),
        "discoveries": parse_session_section(session_content, "Discoveries"),
    }

    # Count items
    total_items = sum(len(v) for v in session_state.values())

    output = {
        "session": session_state,
        "stats": {
            "total_items": total_items,
            "blockers_count": len(session_state["blockers"]),
            "discoveries_count": len(session_state["discoveries"]),
        },
        "workflow": {
            "stuck": "Add to Blockers (triggers memory search), check Working Assumptions, check pivot condition",
            "before_proposing": "Check Rejected Approaches - don't re-propose strategic rejects",
            "lost": "Check The Goal - are you still working toward user outcome?",
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


def run_server() -> None:
    """Run the MCP server."""
    import asyncio

    server = create_server()

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(main())
