"""Mind MCP server - 4 tools for AI memory."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from ..parser import Entity, EntityType, Parser
from ..storage import DaemonState, ProjectsRegistry, get_mind_home, is_daemon_running


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
            })

    # Sort by relevance, then confidence
    results.sort(key=lambda r: (r["relevance"], r["confidence"]), reverse=True)

    return results[:limit]


def match_edges(
    intent: str,
    code: Optional[str],
    stack: list[str],
    global_edges: list[dict],
    project_edges: list[dict],
) -> list[dict]:
    """Match edges against intent and code."""
    intent_lower = intent.lower()
    code_lower = code.lower() if code else ""
    stack_set = set(s.lower() for s in stack)

    warnings = []

    # Check global edges
    for edge in global_edges:
        detection = edge.get("detection", {})

        # Check context match (stack)
        context_patterns = detection.get("context", [])
        context_match = any(
            p.lower() in stack_set or any(p.lower() in s for s in stack_set)
            for p in context_patterns
        )

        # Check intent match
        intent_patterns = detection.get("intent", [])
        intent_match = any(p.lower() in intent_lower for p in intent_patterns)

        # Check code match
        code_patterns = detection.get("code", [])
        code_match = code and any(p.lower() in code_lower for p in code_patterns)

        # Calculate confidence
        matches = sum([context_match, intent_match, code_match])
        if matches >= 1:
            confidence = matches / 3
            warnings.append({
                "id": edge.get("id", ""),
                "title": edge.get("title", ""),
                "description": edge.get("description", ""),
                "workaround": edge.get("workaround", ""),
                "severity": edge.get("severity", "warning"),
                "source": "global",
                "matched_on": ", ".join(filter(None, [
                    "context" if context_match else None,
                    "intent" if intent_match else None,
                    "code" if code_match else None,
                ])),
                "confidence": confidence,
            })

    # Check project edges (simpler matching)
    for edge in project_edges:
        title_lower = edge.get("title", "").lower()
        if any(word in title_lower for word in intent_lower.split()):
            warnings.append({
                "id": "",
                "title": edge.get("title", ""),
                "description": "",
                "workaround": edge.get("workaround", ""),
                "severity": "info",
                "source": "project",
                "matched_on": "title",
                "confidence": 0.5,
            })

    # Sort by confidence
    warnings.sort(key=lambda w: w["confidence"], reverse=True)

    return warnings


def create_server() -> Server:
    """Create the MCP server with 4 tools."""
    server = Server("mind")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return [
            Tool(
                name="mind_search",
                description="Search across memories. Use when CLAUDE.md context isn't enough.",
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
                name="mind_status",
                description="Check Mind daemon status and project stats.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle tool calls."""

        if name == "mind_search":
            return await handle_search(arguments)
        elif name == "mind_edges":
            return await handle_edges(arguments)
        elif name == "mind_add_global_edge":
            return await handle_add_global_edge(arguments)
        elif name == "mind_status":
            return await handle_status(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


async def handle_search(args: dict[str, Any]) -> list[TextContent]:
    """Handle mind_search tool."""
    query = args.get("query", "")
    scope = args.get("scope", "project")
    types = args.get("types")
    limit = args.get("limit", 10)

    if not query:
        return [TextContent(type="text", text="Error: query is required")]

    all_entities: list[Entity] = []
    parser = Parser()

    if scope == "project":
        project_path = get_current_project()
        if not project_path:
            return [TextContent(type="text", text="No Mind project found in current directory")]

        memory_file = project_path / ".mind" / "MEMORY.md"
        if memory_file.exists():
            content = memory_file.read_text(encoding="utf-8")
            result = parser.parse(content, str(memory_file))
            all_entities.extend(result.entities)
    else:
        # Search all projects
        registry = ProjectsRegistry.load()
        for project in registry.list_all():
            memory_file = Path(project.path) / ".mind" / "MEMORY.md"
            if memory_file.exists():
                content = memory_file.read_text(encoding="utf-8")
                result = parser.parse(content, str(memory_file))
                all_entities.extend(result.entities)

    results = search_entities(query, all_entities, types, limit)

    output = {
        "query": query,
        "total": len(results),
        "results": results,
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

    # Generate ID
    import hashlib
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

    # Save
    edges = load_global_edges()
    edges.append(edge)
    save_global_edges(edges)

    return [TextContent(type="text", text=json.dumps(edge, indent=2))]


async def handle_status(args: dict[str, Any]) -> list[TextContent]:
    """Handle mind_status tool."""
    daemon_state = DaemonState.load()
    registry = ProjectsRegistry.load()

    # Current project info
    current_project = None
    project_path = get_current_project()
    if project_path:
        project_info = registry.get(project_path)
        if project_info:
            # Count entities
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

            current_project = {
                "path": project_info.path,
                "name": project_info.name,
                "stack": project_info.stack,
                "last_activity": project_info.last_activity,
                "stats": entity_counts,
            }

    status = {
        "daemon": {
            "running": is_daemon_running(),
            "pid": daemon_state.pid,
            "started_at": daemon_state.started_at,
            "projects_watching": len(daemon_state.projects_watching),
        },
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
