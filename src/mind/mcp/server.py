"""Mind MCP Server implementation."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from mind.models import (
    ProjectCreate, ProjectUpdate,
    DecisionCreate, Alternative,
    IssueCreate, IssueUpdate, Attempt,
    SharpEdgeCreate, DetectionPattern,
)
from mind.models.base import EntityType
from mind.storage.sqlite import SQLiteStorage
from mind.storage.embeddings import EmbeddingStore
from mind.engine.session import SessionManager
from mind.engine.detection import EdgeDetector
from mind.engine.context import ContextEngine

logger = logging.getLogger(__name__)

# Default data directory
DEFAULT_DATA_DIR = Path.home() / ".mind"


class MindServer:
    """Mind MCP Server with all tools."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or DEFAULT_DATA_DIR
        self.storage: Optional[SQLiteStorage] = None
        self.embeddings: Optional[EmbeddingStore] = None
        self.session_manager: Optional[SessionManager] = None
        self.edge_detector: Optional[EdgeDetector] = None
        self.context_engine: Optional[ContextEngine] = None

    async def initialize(self) -> None:
        """Initialize storage and engines."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize SQLite
        self.storage = SQLiteStorage(self.data_dir / "mind.db")
        await self.storage.initialize()

        # Initialize ChromaDB
        self.embeddings = EmbeddingStore(self.data_dir)
        self.embeddings.initialize()

        # Initialize engines
        self.session_manager = SessionManager(self.storage)
        self.edge_detector = EdgeDetector()
        self.context_engine = ContextEngine(self.embeddings, self.storage)

        logger.info("Mind server initialized with data dir: %s", self.data_dir)

    async def close(self) -> None:
        """Close connections."""
        if self.storage:
            await self.storage.close()

    # ============ Tool Implementations ============

    async def mind_start_session(
        self,
        project_id: Optional[str] = None,
        project_name: Optional[str] = None,
        detect_from_path: Optional[str] = None,
    ) -> dict[str, Any]:
        """Start a new session."""
        if not self.session_manager:
            raise RuntimeError("Server not initialized")

        result = await self.session_manager.start_session(
            project_id=project_id,
            project_name=project_name,
            detect_from_path=detect_from_path,
        )

        # Load edges for detection and reset session state
        warnings = []
        if self.storage and self.edge_detector:
            edges = await self.storage.list_sharp_edges(result.project.id)
            # Also load global edges
            global_edges = await self.storage.list_sharp_edges(None)
            all_edges = edges + [e for e in global_edges if e.id not in {ed.id for ed in edges}]
            self.edge_detector.load_edges(all_edges)
            self.edge_detector.reset_session()

            # Proactive: Check stack + goal for relevant edges
            if result.project.stack or result.project.current_goal:
                stack_warnings = self.edge_detector.check_stack(
                    stack=result.project.stack,
                    current_goal=result.project.current_goal,
                )
                warnings = [w.model_dump() for w in stack_warnings]

        return {
            "session_id": result.session_id,
            "project": result.project.model_dump(),
            "primer": result.primer,
            "open_issues": [i.model_dump() for i in result.open_issues],
            "pending_decisions": [d.model_dump() for d in result.pending_decisions],
            "relevant_edges": [e.model_dump() for e in result.relevant_edges],
            "warnings": warnings,
        }

    async def mind_end_session(
        self,
        summary: str,
        progress: list[str],
        still_open: list[str],
        next_steps: list[str],
        mood: Optional[str] = None,
        episode_title: Optional[str] = None,
    ) -> dict[str, Any]:
        """End the current session."""
        if not self.session_manager:
            raise RuntimeError("Server not initialized")

        return await self.session_manager.end_session(
            summary=summary,
            progress=progress,
            still_open=still_open,
            next_steps=next_steps,
            mood=mood,
            episode_title=episode_title,
        )

    async def mind_get_context(
        self,
        query: str,
        code: Optional[str] = None,
        types: Optional[list[str]] = None,
        project_id: Optional[str] = None,
        include_global: bool = True,
    ) -> dict[str, Any]:
        """Search for relevant context."""
        if not self.storage or not self.context_engine:
            raise RuntimeError("Server not initialized")

        # Get current project ID
        if not project_id and self.session_manager and self.session_manager.current_session:
            project_id = self.session_manager.current_session.project_id

        if not project_id:
            raise ValueError("No project_id provided and no active session")

        # Convert type strings to EntityType
        entity_types = None
        if types:
            entity_types = [EntityType(t) for t in types]

        # Search embeddings
        results = await self.context_engine.get_relevant_context(
            query=query,
            project_id=project_id,
            entity_types=entity_types,
        )

        # Record accesses for relevance scoring
        if results:
            accesses = [(r["entity_type"], r["entity_id"]) for r in results]
            await self.storage.record_accesses(accesses)

        # Also do text search in SQLite
        text_results = await self.storage.search_all(project_id, query)

        # Proactive: Check query intent + code for edge warnings
        warnings = []
        if self.edge_detector:
            # Get project stack for context
            project = await self.storage.get_project(project_id)
            stack = project.stack if project else []

            # Check intent (always) and code (if provided)
            edge_warnings = self.edge_detector.check_all(
                query=query,
                code=code,
                stack=stack,
            )
            warnings = [w.model_dump() for w in edge_warnings]

        return {
            "semantic_results": results,
            "decisions": [d.model_dump() for d in text_results["decisions"]],
            "issues": [i.model_dump() for i in text_results["issues"]],
            "edges": [e.model_dump() for e in text_results["edges"]],
            "episodes": [ep.model_dump() for ep in text_results["episodes"]],
            "warnings": warnings,
        }

    async def mind_check_edges(
        self,
        code: Optional[str] = None,
        intent: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Check for sharp edges (manual check - also runs automatically in other tools)."""
        if not self.edge_detector or not self.storage:
            raise RuntimeError("Server not initialized")

        # Get project stack for context
        stack: list[str] = []
        if self.session_manager and self.session_manager.current_session:
            project = await self.storage.get_project(
                self.session_manager.current_session.project_id
            )
            if project:
                stack = project.stack

        # Use the new check_all API
        file_path = context.get("file_path") if context else None
        warnings = self.edge_detector.check_all(
            query=intent,
            code=code,
            stack=stack,
            file_path=file_path,
        )

        return {
            "warnings": [w.model_dump() for w in warnings]
        }

    async def mind_add_decision(
        self,
        title: str,
        description: str,
        context: str,
        reasoning: str,
        alternatives: Optional[list[dict[str, Any]]] = None,
        confidence: float = 0.7,
        revisit_if: Optional[str] = None,
        trigger_phrases: Optional[list[str]] = None,
        project_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Add a new decision."""
        if not self.storage or not self.embeddings:
            raise RuntimeError("Server not initialized")

        # Get project ID from session if not provided
        if not project_id and self.session_manager and self.session_manager.current_session:
            project_id = self.session_manager.current_session.project_id

        if not project_id:
            raise ValueError("No project_id provided and no active session")

        # Create alternatives
        alts = []
        if alternatives:
            alts = [Alternative(**a) for a in alternatives]

        # Create decision
        session_id = self.session_manager.current_session.id if self.session_manager and self.session_manager.current_session else None
        decision = await self.storage.create_decision(
            DecisionCreate(
                project_id=project_id,
                title=title,
                description=description,
                context=context,
                reasoning=reasoning,
                alternatives=alts,
                confidence=confidence,
                revisit_if=revisit_if,
                trigger_phrases=trigger_phrases or [],
            ),
            session_id=session_id,
        )

        # Add embedding
        await self.embeddings.add_embedding(
            entity_type=EntityType.DECISION,
            entity_id=decision.id,
            text=decision.embedding_text,
            metadata={"project_id": project_id},
        )

        # Track in session
        if session_id:
            await self.storage.add_session_artifact(session_id, "decision", decision.id)

        # Proactive: Check reasoning text for edge warnings
        warnings = []
        if self.edge_detector:
            # Combine reasoning and context for intent check
            reasoning_text = f"{title} {description} {context} {reasoning}"
            edge_warnings = self.edge_detector.check_intent(reasoning_text)
            warnings = [w.model_dump() for w in edge_warnings]

        return {"decision": decision.model_dump(), "warnings": warnings}

    async def mind_add_issue(
        self,
        title: str,
        description: str,
        severity: str = "major",
        symptoms: Optional[list[str]] = None,
        trigger_phrases: Optional[list[str]] = None,
        project_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Add a new issue."""
        if not self.storage or not self.embeddings:
            raise RuntimeError("Server not initialized")

        # Get project ID from session if not provided
        if not project_id and self.session_manager and self.session_manager.current_session:
            project_id = self.session_manager.current_session.project_id

        if not project_id:
            raise ValueError("No project_id provided and no active session")

        session_id = self.session_manager.current_session.id if self.session_manager and self.session_manager.current_session else None
        issue = await self.storage.create_issue(
            IssueCreate(
                project_id=project_id,
                title=title,
                description=description,
                severity=severity,  # type: ignore
                symptoms=symptoms or [],
            ),
            session_id=session_id,
        )

        # Add embedding
        await self.embeddings.add_embedding(
            entity_type=EntityType.ISSUE,
            entity_id=issue.id,
            text=issue.embedding_text,
            metadata={"project_id": project_id},
        )

        # Track in session
        if session_id:
            await self.storage.add_session_artifact(session_id, "issue_opened", issue.id)

        # Proactive: Check symptoms for matching edges
        warnings = []
        if self.edge_detector:
            # Check symptoms text against known edge symptoms
            symptoms_text = f"{title} {description} {' '.join(symptoms or [])}"
            edge_warnings = self.edge_detector.check_symptoms(symptoms_text)
            warnings = [w.model_dump() for w in edge_warnings]

        return {"issue": issue.model_dump(), "warnings": warnings}

    async def mind_update_issue(
        self,
        issue_id: str,
        status: Optional[str] = None,
        add_attempt: Optional[dict[str, Any]] = None,
        current_theory: Optional[str] = None,
        blocked_by: Optional[str] = None,
        resolution: Optional[str] = None,
    ) -> dict[str, Any]:
        """Update an existing issue."""
        if not self.storage or not self.embeddings:
            raise RuntimeError("Server not initialized")

        attempt = None
        if add_attempt:
            attempt = Attempt(**add_attempt)

        issue = await self.storage.update_issue(
            issue_id,
            IssueUpdate(
                status=status,  # type: ignore
                add_attempt=attempt,
                current_theory=current_theory,
                blocked_by=blocked_by,
                resolution=resolution,
            ),
        )

        if not issue:
            raise ValueError(f"Issue not found: {issue_id}")

        # Update embedding
        await self.embeddings.add_embedding(
            entity_type=EntityType.ISSUE,
            entity_id=issue.id,
            text=issue.embedding_text,
            metadata={"project_id": issue.project_id},
        )

        # Track in session
        if self.session_manager and self.session_manager.current_session:
            await self.storage.add_session_artifact(
                self.session_manager.current_session.id,
                "issue_updated",
                issue.id,
            )
            # Also track if issue was resolved
            if status == "resolved":
                await self.storage.add_session_artifact(
                    self.session_manager.current_session.id,
                    "issue_resolved",
                    issue.id,
                )

        return {"issue": issue.model_dump()}

    async def mind_add_edge(
        self,
        title: str,
        description: str,
        workaround: str,
        detection_patterns: Optional[list[dict[str, Any]]] = None,
        symptoms: Optional[list[str]] = None,
        root_cause: Optional[str] = None,
        project_id: Optional[str] = None,
        share_with_community: bool = False,
    ) -> dict[str, Any]:
        """Add a new sharp edge."""
        if not self.storage or not self.embeddings or not self.edge_detector:
            raise RuntimeError("Server not initialized")

        # Parse detection patterns
        patterns = []
        if detection_patterns:
            patterns = [DetectionPattern(**p) for p in detection_patterns]

        edge = await self.storage.create_sharp_edge(
            SharpEdgeCreate(
                project_id=project_id,  # None for global edge
                title=title,
                description=description,
                workaround=workaround,
                detection_patterns=patterns,
                symptoms=symptoms or [],
                root_cause=root_cause,
            )
        )

        # Add embedding
        await self.embeddings.add_embedding(
            entity_type=EntityType.SHARP_EDGE,
            entity_id=edge.id,
            text=edge.embedding_text,
            metadata={"project_id": project_id} if project_id else {},
        )

        # Reload edges for detection
        if self.session_manager and self.session_manager.current_session:
            edges = await self.storage.list_sharp_edges(self.session_manager.current_session.project_id)
            self.edge_detector.load_edges(edges)

            # Track in session
            await self.storage.add_session_artifact(
                self.session_manager.current_session.id,
                "edge",
                edge.id,
            )

        return {"edge": edge.model_dump()}

    async def mind_update_project(
        self,
        current_goal: Optional[str] = None,
        blocked_by: Optional[list[str]] = None,
        open_threads: Optional[list[str]] = None,
        add_to_stack: Optional[list[str]] = None,
        status: Optional[str] = None,
    ) -> dict[str, Any]:
        """Update the current project."""
        if not self.storage or not self.session_manager:
            raise RuntimeError("Server not initialized")

        if not self.session_manager.current_session:
            raise ValueError("No active session")

        project_id = self.session_manager.current_session.project_id
        project = await self.storage.update_project(
            project_id,
            ProjectUpdate(
                current_goal=current_goal,
                blocked_by=blocked_by,
                open_threads=open_threads,
                add_to_stack=add_to_stack,
                status=status,  # type: ignore
            ),
        )

        if not project:
            raise ValueError(f"Project not found: {project_id}")

        return {"project": project.model_dump()}

    async def mind_export(
        self,
        format: str = "json",
        project_id: Optional[str] = None,
        include_sessions: bool = False,
    ) -> dict[str, Any]:
        """Export all data for backup."""
        if not self.storage:
            raise RuntimeError("Server not initialized")

        export_data: dict[str, Any] = {
            "exported_at": str(datetime.utcnow()),
            "format": format,
            "projects": [],
            "decisions": [],
            "issues": [],
            "edges": [],
            "episodes": [],
        }

        # Get projects
        projects = await self.storage.list_projects()
        if project_id:
            projects = [p for p in projects if p.id == project_id]

        export_data["projects"] = [p.model_dump() for p in projects]

        # Get data for each project
        for project in projects:
            decisions = await self.storage.list_decisions(project.id)
            export_data["decisions"].extend([d.model_dump() for d in decisions])

            issues = await self.storage.list_issues(project.id)
            export_data["issues"].extend([i.model_dump() for i in issues])

            edges = await self.storage.list_sharp_edges(project.id)
            export_data["edges"].extend([e.model_dump() for e in edges])

            episodes = await self.storage.list_episodes(project.id)
            export_data["episodes"].extend([ep.model_dump() for ep in episodes])

        # Save export
        from datetime import datetime
        export_dir = self.data_dir / "exports"
        export_dir.mkdir(exist_ok=True)

        filename = f"mind_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        export_path = export_dir / filename

        with open(export_path, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        return {
            "path": str(export_path),
            "entities": {
                "projects": len(export_data["projects"]),
                "decisions": len(export_data["decisions"]),
                "issues": len(export_data["issues"]),
                "edges": len(export_data["edges"]),
                "episodes": len(export_data["episodes"]),
            },
        }


def create_server(data_dir: Optional[Path] = None) -> Server:
    """Create the MCP server with all Mind tools."""
    server = Server("mind")
    mind = MindServer(data_dir)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List all Mind tools."""
        return [
            Tool(
                name="mind_start_session",
                description="Start a new session, get project context and primer.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Existing project ID"},
                        "project_name": {"type": "string", "description": "Find or create project by name"},
                        "detect_from_path": {"type": "string", "description": "Detect project from repo path"},
                    },
                },
            ),
            Tool(
                name="mind_end_session",
                description="End the current session, capture summary and state. Creates an Episode if session is significant.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string", "description": "What happened this session"},
                        "progress": {"type": "array", "items": {"type": "string"}, "description": "What was accomplished"},
                        "still_open": {"type": "array", "items": {"type": "string"}, "description": "Unresolved threads"},
                        "next_steps": {"type": "array", "items": {"type": "string"}, "description": "For next session"},
                        "mood": {"type": "string", "description": "Optional mood observation (frustrated, stuck, breakthrough, accomplished, exploratory, tired)"},
                        "episode_title": {"type": "string", "description": "Optional custom title for the episode (overrides auto-generated)"},
                    },
                    "required": ["summary"],
                },
            ),
            Tool(
                name="mind_get_context",
                description="Search for relevant context across decisions, issues, edges, and episodes. Also checks for edge warnings based on query intent.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Natural language query"},
                        "code": {"type": "string", "description": "Optional code snippet to check for edge patterns"},
                        "types": {"type": "array", "items": {"type": "string"}, "description": "Filter to specific entity types"},
                        "project_id": {"type": "string", "description": "Scope to specific project"},
                        "include_global": {"type": "boolean", "description": "Include global edges", "default": True},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="mind_check_edges",
                description="Check for sharp edges that might apply to current code or intent.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Code being written/suggested"},
                        "intent": {"type": "string", "description": "What we're trying to do"},
                        "context": {
                            "type": "object",
                            "description": "Additional context (runtime, framework, file_path)",
                            "properties": {
                                "runtime": {"type": "string"},
                                "framework": {"type": "string"},
                                "file_path": {"type": "string"},
                            },
                        },
                    },
                },
            ),
            Tool(
                name="mind_add_decision",
                description="Record a new decision with full reasoning.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Short description"},
                        "description": {"type": "string", "description": "Full explanation"},
                        "context": {"type": "string", "description": "What situation led to this"},
                        "reasoning": {"type": "string", "description": "Why this choice"},
                        "alternatives": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "option": {"type": "string"},
                                    "rejected_because": {"type": "string"},
                                },
                            },
                            "description": "Alternatives considered",
                        },
                        "confidence": {"type": "number", "description": "0.0 to 1.0", "default": 0.7},
                        "revisit_if": {"type": "string", "description": "Condition to reconsider"},
                        "trigger_phrases": {"type": "array", "items": {"type": "string"}, "description": "For retrieval"},
                        "project_id": {"type": "string", "description": "Project ID (default: current session)"},
                    },
                    "required": ["title", "description", "context", "reasoning"],
                },
            ),
            Tool(
                name="mind_add_issue",
                description="Open a new issue.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "severity": {"type": "string", "enum": ["blocking", "major", "minor", "cosmetic"], "default": "major"},
                        "symptoms": {"type": "array", "items": {"type": "string"}, "description": "Error messages, behaviors"},
                        "trigger_phrases": {"type": "array", "items": {"type": "string"}},
                        "project_id": {"type": "string"},
                    },
                    "required": ["title", "description"],
                },
            ),
            Tool(
                name="mind_update_issue",
                description="Update an existing issue.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_id": {"type": "string"},
                        "status": {"type": "string", "enum": ["open", "investigating", "blocked", "resolved", "wont_fix"]},
                        "add_attempt": {
                            "type": "object",
                            "properties": {
                                "what": {"type": "string"},
                                "result": {"type": "string"},
                                "learned": {"type": "string"},
                            },
                        },
                        "current_theory": {"type": "string"},
                        "blocked_by": {"type": "string"},
                        "resolution": {"type": "string"},
                    },
                    "required": ["issue_id"],
                },
            ),
            Tool(
                name="mind_add_edge",
                description="Register a new sharp edge (gotcha).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "workaround": {"type": "string"},
                        "detection_patterns": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string", "enum": ["code", "context", "intent"]},
                                    "pattern": {"type": "string"},
                                    "description": {"type": "string"},
                                },
                            },
                        },
                        "symptoms": {"type": "array", "items": {"type": "string"}},
                        "root_cause": {"type": "string"},
                        "project_id": {"type": "string", "description": "null for global edge"},
                        "share_with_community": {"type": "boolean", "default": False},
                    },
                    "required": ["title", "description", "workaround"],
                },
            ),
            Tool(
                name="mind_update_project",
                description="Update current project state.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "current_goal": {"type": "string"},
                        "blocked_by": {"type": "array", "items": {"type": "string"}},
                        "open_threads": {"type": "array", "items": {"type": "string"}},
                        "add_to_stack": {"type": "array", "items": {"type": "string"}},
                        "status": {"type": "string", "enum": ["active", "paused", "archived"]},
                    },
                },
            ),
            Tool(
                name="mind_export",
                description="Export all data for backup or migration.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "format": {"type": "string", "enum": ["json", "markdown"], "default": "json"},
                        "project_id": {"type": "string", "description": "Specific project or all"},
                        "include_sessions": {"type": "boolean", "default": False},
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls."""
        # Initialize on first call
        if not mind.storage:
            await mind.initialize()

        try:
            if name == "mind_start_session":
                result = await mind.mind_start_session(**arguments)
            elif name == "mind_end_session":
                result = await mind.mind_end_session(**arguments)
            elif name == "mind_get_context":
                result = await mind.mind_get_context(**arguments)
            elif name == "mind_check_edges":
                result = await mind.mind_check_edges(**arguments)
            elif name == "mind_add_decision":
                result = await mind.mind_add_decision(**arguments)
            elif name == "mind_add_issue":
                result = await mind.mind_add_issue(**arguments)
            elif name == "mind_update_issue":
                result = await mind.mind_update_issue(**arguments)
            elif name == "mind_add_edge":
                result = await mind.mind_add_edge(**arguments)
            elif name == "mind_update_project":
                result = await mind.mind_update_project(**arguments)
            elif name == "mind_export":
                result = await mind.mind_export(**arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        except Exception as e:
            logger.exception("Error in tool %s", name)
            error_result = {
                "error": {
                    "code": type(e).__name__,
                    "message": str(e),
                }
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]

    return server


async def run_server(data_dir: Optional[Path] = None) -> None:
    """Run the MCP server."""
    server = create_server(data_dir)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
