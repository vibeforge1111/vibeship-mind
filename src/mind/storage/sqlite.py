"""SQLite storage implementation."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiosqlite

from mind.models import (
    Project, ProjectCreate, ProjectUpdate,
    Decision, DecisionCreate, Alternative,
    Issue, IssueCreate, IssueUpdate, Attempt,
    SharpEdge, SharpEdgeCreate, DetectionPattern,
    Episode, EpisodeCreate, MoodPoint,
    UserModel, UserModelUpdate,
    Session, SessionEnd, Message,
)
from mind.models.base import generate_id


SCHEMA = """
-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active',
    stack TEXT,
    repo_path TEXT,
    current_goal TEXT,
    blocked_by TEXT,
    open_threads TEXT,
    last_session_id TEXT,
    last_session_date TEXT,
    last_session_summary TEXT,
    last_session_mood TEXT,
    last_session_next_step TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Decisions
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    context TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    alternatives TEXT,
    confidence REAL DEFAULT 0.7,
    revisit_if TEXT,
    valid_until TEXT,
    status TEXT DEFAULT 'active',
    superseded_by TEXT,
    related_issues TEXT,
    related_edges TEXT,
    triggered_by_episode TEXT,
    trigger_phrases TEXT,
    decided_at TEXT NOT NULL,
    session_id TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Issues
CREATE TABLE IF NOT EXISTS issues (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT DEFAULT 'major',
    status TEXT DEFAULT 'open',
    attempts TEXT,
    current_theory TEXT,
    blocked_by TEXT,
    resolution TEXT,
    resolved_at TEXT,
    resolved_by_decision TEXT,
    related_decisions TEXT,
    related_edges TEXT,
    caused_by_episode TEXT,
    symptoms TEXT,
    trigger_phrases TEXT,
    opened_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    session_id TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Sharp Edges
CREATE TABLE IF NOT EXISTS sharp_edges (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    detection_patterns TEXT,
    trigger_phrases TEXT,
    symptoms TEXT,
    workaround TEXT NOT NULL,
    root_cause TEXT,
    proper_fix TEXT,
    discovered_in_episode TEXT,
    discovered_at TEXT NOT NULL,
    related_decisions TEXT,
    related_issues TEXT,
    submitted_by TEXT,
    verification_count INTEGER DEFAULT 0,
    verified_by TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Episodes
CREATE TABLE IF NOT EXISTS episodes (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    title TEXT NOT NULL,
    narrative TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    duration_minutes INTEGER,
    mood_arc TEXT,
    overall_mood TEXT,
    lessons TEXT,
    breakthroughs TEXT,
    frustrations TEXT,
    decisions_made TEXT,
    issues_opened TEXT,
    issues_resolved TEXT,
    edges_discovered TEXT,
    keywords TEXT,
    summary TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- User Model
CREATE TABLE IF NOT EXISTS user_model (
    id TEXT PRIMARY KEY,
    name TEXT,
    communication TEXT,
    expertise TEXT,
    patterns TEXT,
    current_energy TEXT,
    current_focus TEXT,
    recent_wins TEXT,
    recent_frustrations TEXT,
    what_works TEXT,
    what_doesnt_work TEXT,
    projects TEXT,
    total_sessions INTEGER DEFAULT 0,
    first_session TEXT,
    last_session TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Sessions
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT DEFAULT 'active',
    primer_content TEXT,
    memories_surfaced TEXT,
    summary TEXT,
    progress TEXT,
    still_open TEXT,
    next_steps TEXT,
    mood TEXT,
    decisions_made TEXT,
    issues_opened TEXT,
    issues_updated TEXT,
    edges_discovered TEXT,
    episode_id TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Changes (for sync)
CREATE TABLE IF NOT EXISTS changes (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    change_type TEXT NOT NULL,
    data TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    synced INTEGER DEFAULT 0
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_decisions_project ON decisions(project_id);
CREATE INDEX IF NOT EXISTS idx_issues_project ON issues(project_id);
CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_edges_project ON sharp_edges(project_id);
CREATE INDEX IF NOT EXISTS idx_episodes_project ON episodes(project_id);
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_changes_synced ON changes(synced);
CREATE INDEX IF NOT EXISTS idx_changes_timestamp ON changes(timestamp);
"""


def _json_dumps(obj: Any) -> str:
    """Serialize object to JSON string."""
    if obj is None:
        return "[]"
    if isinstance(obj, list):
        return json.dumps(
            [item.model_dump() if hasattr(item, "model_dump") else item for item in obj],
            default=str,
        )
    if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump(), default=str)
    return json.dumps(obj, default=str)


def _json_loads(s: str | None, default: Any = None) -> Any:
    """Deserialize JSON string."""
    if s is None or s == "":
        return default if default is not None else []
    return json.loads(s)


def _datetime_str(dt: datetime | None) -> str | None:
    """Convert datetime to ISO string."""
    return dt.isoformat() if dt else None


def _parse_datetime(s: str | None) -> datetime | None:
    """Parse ISO datetime string."""
    return datetime.fromisoformat(s) if s else None


class SQLiteStorage:
    """SQLite-based storage for Mind entities."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Initialize the database with schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row

        # Enable WAL mode for better concurrency
        await self._db.execute("PRAGMA journal_mode=WAL")

        # Create schema
        await self._db.executescript(SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        """Close database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        """Get database connection."""
        if self._db is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._db

    # ============ Projects ============

    async def create_project(self, data: ProjectCreate) -> Project:
        """Create a new project."""
        project = Project(
            name=data.name,
            description=data.description,
            stack=data.stack,
            repo_path=data.repo_path,
        )

        await self.db.execute(
            """INSERT INTO projects
               (id, name, description, status, stack, repo_path, blocked_by, open_threads, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                project.id, project.name, project.description, project.status,
                _json_dumps(project.stack), project.repo_path,
                _json_dumps(project.blocked_by), _json_dumps(project.open_threads),
                _datetime_str(project.created_at), _datetime_str(project.updated_at),
            ),
        )
        await self.db.commit()
        return project

    async def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        async with self.db.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_project(row)

    async def get_project_by_name(self, name: str) -> Optional[Project]:
        """Get a project by name."""
        async with self.db.execute(
            "SELECT * FROM projects WHERE name = ?", (name,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_project(row)

    async def get_project_by_path(self, repo_path: str) -> Optional[Project]:
        """Get a project by repository path."""
        async with self.db.execute(
            "SELECT * FROM projects WHERE repo_path = ?", (repo_path,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_project(row)

    async def list_projects(self, status: Optional[str] = None) -> list[Project]:
        """List all projects, optionally filtered by status."""
        if status:
            query = "SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC"
            params = (status,)
        else:
            query = "SELECT * FROM projects ORDER BY updated_at DESC"
            params = ()

        async with self.db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_project(row) for row in rows]

    async def update_project(self, project_id: str, data: ProjectUpdate) -> Optional[Project]:
        """Update a project."""
        project = await self.get_project(project_id)
        if not project:
            return None

        updates = []
        params = []

        if data.current_goal is not None:
            updates.append("current_goal = ?")
            params.append(data.current_goal)
        if data.blocked_by is not None:
            updates.append("blocked_by = ?")
            params.append(_json_dumps(data.blocked_by))
        if data.open_threads is not None:
            updates.append("open_threads = ?")
            params.append(_json_dumps(data.open_threads))
        if data.status is not None:
            updates.append("status = ?")
            params.append(data.status)
        if data.add_to_stack:
            new_stack = list(set(project.stack + data.add_to_stack))
            updates.append("stack = ?")
            params.append(_json_dumps(new_stack))

        if updates:
            updates.append("updated_at = ?")
            params.append(_datetime_str(datetime.utcnow()))
            params.append(project_id)

            await self.db.execute(
                f"UPDATE projects SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            await self.db.commit()

        return await self.get_project(project_id)

    async def update_project_session(
        self,
        project_id: str,
        session_id: str,
        summary: str,
        mood: Optional[str] = None,
        next_step: Optional[str] = None,
    ) -> None:
        """Update project's last session info."""
        await self.db.execute(
            """UPDATE projects SET
               last_session_id = ?, last_session_date = ?,
               last_session_summary = ?, last_session_mood = ?,
               last_session_next_step = ?, updated_at = ?
               WHERE id = ?""",
            (
                session_id, _datetime_str(datetime.utcnow()),
                summary, mood, next_step, _datetime_str(datetime.utcnow()),
                project_id,
            ),
        )
        await self.db.commit()

    def _row_to_project(self, row: aiosqlite.Row) -> Project:
        """Convert database row to Project."""
        return Project(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            status=row["status"],
            stack=_json_loads(row["stack"], []),
            repo_path=row["repo_path"],
            current_goal=row["current_goal"],
            blocked_by=_json_loads(row["blocked_by"], []),
            open_threads=_json_loads(row["open_threads"], []),
            last_session_id=row["last_session_id"],
            last_session_date=_parse_datetime(row["last_session_date"]),
            last_session_summary=row["last_session_summary"],
            last_session_mood=row["last_session_mood"],
            last_session_next_step=row["last_session_next_step"],
            created_at=_parse_datetime(row["created_at"]) or datetime.utcnow(),
            updated_at=_parse_datetime(row["updated_at"]) or datetime.utcnow(),
        )

    # ============ Decisions ============

    async def create_decision(self, data: DecisionCreate, session_id: Optional[str] = None) -> Decision:
        """Create a new decision."""
        decision = Decision(
            project_id=data.project_id,
            title=data.title,
            description=data.description,
            context=data.context,
            reasoning=data.reasoning,
            alternatives=data.alternatives,
            confidence=data.confidence,
            revisit_if=data.revisit_if,
            trigger_phrases=data.trigger_phrases,
            session_id=session_id,
        )

        await self.db.execute(
            """INSERT INTO decisions
               (id, project_id, title, description, context, reasoning, alternatives,
                confidence, revisit_if, status, trigger_phrases, decided_at, session_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                decision.id, decision.project_id, decision.title, decision.description,
                decision.context, decision.reasoning,
                _json_dumps([a.model_dump() for a in decision.alternatives]),
                decision.confidence, decision.revisit_if, decision.status,
                _json_dumps(decision.trigger_phrases),
                _datetime_str(decision.decided_at), session_id,
            ),
        )
        await self.db.commit()
        return decision

    async def get_decision(self, decision_id: str) -> Optional[Decision]:
        """Get a decision by ID."""
        async with self.db.execute(
            "SELECT * FROM decisions WHERE id = ?", (decision_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_decision(row)

    async def list_decisions(
        self, project_id: str, status: Optional[str] = None
    ) -> list[Decision]:
        """List decisions for a project."""
        if status:
            query = "SELECT * FROM decisions WHERE project_id = ? AND status = ? ORDER BY decided_at DESC"
            params = (project_id, status)
        else:
            query = "SELECT * FROM decisions WHERE project_id = ? ORDER BY decided_at DESC"
            params = (project_id,)

        async with self.db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_decision(row) for row in rows]

    def _row_to_decision(self, row: aiosqlite.Row) -> Decision:
        """Convert database row to Decision."""
        alternatives_data = _json_loads(row["alternatives"], [])
        alternatives = [Alternative(**a) for a in alternatives_data]

        return Decision(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"],
            description=row["description"],
            context=row["context"],
            reasoning=row["reasoning"],
            alternatives=alternatives,
            confidence=row["confidence"],
            revisit_if=row["revisit_if"],
            valid_until=_parse_datetime(row["valid_until"]),
            status=row["status"],
            superseded_by=row["superseded_by"],
            related_issues=_json_loads(row["related_issues"], []),
            related_edges=_json_loads(row["related_edges"], []),
            triggered_by_episode=row["triggered_by_episode"],
            trigger_phrases=_json_loads(row["trigger_phrases"], []),
            decided_at=_parse_datetime(row["decided_at"]) or datetime.utcnow(),
            session_id=row["session_id"],
        )

    # ============ Issues ============

    async def create_issue(self, data: IssueCreate, session_id: Optional[str] = None) -> Issue:
        """Create a new issue."""
        issue = Issue(
            project_id=data.project_id,
            title=data.title,
            description=data.description,
            severity=data.severity,
            symptoms=data.symptoms,
            session_id=session_id,
        )

        await self.db.execute(
            """INSERT INTO issues
               (id, project_id, title, description, severity, status, symptoms,
                attempts, opened_at, updated_at, session_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                issue.id, issue.project_id, issue.title, issue.description,
                issue.severity, issue.status, _json_dumps(issue.symptoms),
                _json_dumps([]), _datetime_str(issue.opened_at),
                _datetime_str(issue.updated_at), session_id,
            ),
        )
        await self.db.commit()
        return issue

    async def get_issue(self, issue_id: str) -> Optional[Issue]:
        """Get an issue by ID."""
        async with self.db.execute(
            "SELECT * FROM issues WHERE id = ?", (issue_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_issue(row)

    async def list_issues(
        self, project_id: str, status: Optional[str] = None
    ) -> list[Issue]:
        """List issues for a project."""
        if status:
            query = "SELECT * FROM issues WHERE project_id = ? AND status = ? ORDER BY opened_at DESC"
            params = (project_id, status)
        else:
            query = "SELECT * FROM issues WHERE project_id = ? ORDER BY opened_at DESC"
            params = (project_id,)

        async with self.db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_issue(row) for row in rows]

    async def list_open_issues(self, project_id: str) -> list[Issue]:
        """List open issues for a project."""
        query = """SELECT * FROM issues
                   WHERE project_id = ? AND status IN ('open', 'investigating', 'blocked')
                   ORDER BY
                       CASE severity
                           WHEN 'blocking' THEN 1
                           WHEN 'major' THEN 2
                           WHEN 'minor' THEN 3
                           ELSE 4
                       END,
                       opened_at DESC"""

        async with self.db.execute(query, (project_id,)) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_issue(row) for row in rows]

    async def update_issue(self, issue_id: str, data: IssueUpdate) -> Optional[Issue]:
        """Update an issue."""
        issue = await self.get_issue(issue_id)
        if not issue:
            return None

        updates = ["updated_at = ?"]
        params: list[Any] = [_datetime_str(datetime.utcnow())]

        if data.status is not None:
            updates.append("status = ?")
            params.append(data.status)
            if data.status == "resolved":
                updates.append("resolved_at = ?")
                params.append(_datetime_str(datetime.utcnow()))

        if data.current_theory is not None:
            updates.append("current_theory = ?")
            params.append(data.current_theory)

        if data.blocked_by is not None:
            updates.append("blocked_by = ?")
            params.append(data.blocked_by)

        if data.resolution is not None:
            updates.append("resolution = ?")
            params.append(data.resolution)

        if data.add_attempt is not None:
            new_attempts = issue.attempts + [data.add_attempt]
            updates.append("attempts = ?")
            params.append(_json_dumps([a.model_dump() for a in new_attempts]))

        params.append(issue_id)
        await self.db.execute(
            f"UPDATE issues SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        await self.db.commit()

        return await self.get_issue(issue_id)

    def _row_to_issue(self, row: aiosqlite.Row) -> Issue:
        """Convert database row to Issue."""
        attempts_data = _json_loads(row["attempts"], [])
        attempts = [Attempt(**a) for a in attempts_data]

        return Issue(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"],
            description=row["description"],
            severity=row["severity"],
            status=row["status"],
            attempts=attempts,
            current_theory=row["current_theory"],
            blocked_by=row["blocked_by"],
            resolution=row["resolution"],
            resolved_at=_parse_datetime(row["resolved_at"]),
            resolved_by_decision=row["resolved_by_decision"],
            related_decisions=_json_loads(row["related_decisions"], []),
            related_edges=_json_loads(row["related_edges"], []),
            caused_by_episode=row["caused_by_episode"],
            symptoms=_json_loads(row["symptoms"], []),
            trigger_phrases=_json_loads(row["trigger_phrases"], []),
            opened_at=_parse_datetime(row["opened_at"]) or datetime.utcnow(),
            updated_at=_parse_datetime(row["updated_at"]) or datetime.utcnow(),
            session_id=row["session_id"],
        )

    # ============ Sharp Edges ============

    async def create_sharp_edge(self, data: SharpEdgeCreate) -> SharpEdge:
        """Create a new sharp edge."""
        edge = SharpEdge(
            project_id=data.project_id,
            title=data.title,
            description=data.description,
            workaround=data.workaround,
            detection_patterns=data.detection_patterns,
            symptoms=data.symptoms,
            root_cause=data.root_cause,
        )

        await self.db.execute(
            """INSERT INTO sharp_edges
               (id, project_id, title, description, detection_patterns, symptoms,
                workaround, root_cause, discovered_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                edge.id, edge.project_id, edge.title, edge.description,
                _json_dumps([p.model_dump() for p in edge.detection_patterns]),
                _json_dumps(edge.symptoms), edge.workaround, edge.root_cause,
                _datetime_str(edge.discovered_at),
            ),
        )
        await self.db.commit()
        return edge

    async def get_sharp_edge(self, edge_id: str) -> Optional[SharpEdge]:
        """Get a sharp edge by ID."""
        async with self.db.execute(
            "SELECT * FROM sharp_edges WHERE id = ?", (edge_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_sharp_edge(row)

    async def list_sharp_edges(self, project_id: Optional[str] = None) -> list[SharpEdge]:
        """List sharp edges, optionally filtered by project."""
        if project_id:
            # Include global edges (project_id IS NULL) and project-specific edges
            query = "SELECT * FROM sharp_edges WHERE project_id IS NULL OR project_id = ? ORDER BY discovered_at DESC"
            params = (project_id,)
        else:
            query = "SELECT * FROM sharp_edges ORDER BY discovered_at DESC"
            params = ()

        async with self.db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_sharp_edge(row) for row in rows]

    def _row_to_sharp_edge(self, row: aiosqlite.Row) -> SharpEdge:
        """Convert database row to SharpEdge."""
        patterns_data = _json_loads(row["detection_patterns"], [])
        patterns = [DetectionPattern(**p) for p in patterns_data]

        return SharpEdge(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"],
            description=row["description"],
            detection_patterns=patterns,
            trigger_phrases=_json_loads(row["trigger_phrases"], []),
            symptoms=_json_loads(row["symptoms"], []),
            workaround=row["workaround"],
            root_cause=row["root_cause"],
            proper_fix=row["proper_fix"],
            discovered_in_episode=row["discovered_in_episode"],
            discovered_at=_parse_datetime(row["discovered_at"]) or datetime.utcnow(),
            related_decisions=_json_loads(row["related_decisions"], []),
            related_issues=_json_loads(row["related_issues"], []),
            submitted_by=row["submitted_by"],
            verification_count=row["verification_count"],
            verified_by=_json_loads(row["verified_by"], []),
        )

    # ============ Episodes ============

    async def create_episode(self, data: EpisodeCreate) -> Episode:
        """Create a new episode."""
        duration = int((data.ended_at - data.started_at).total_seconds() / 60)

        episode = Episode(
            project_id=data.project_id,
            session_id=data.session_id,
            title=data.title,
            narrative=data.narrative,
            started_at=data.started_at,
            ended_at=data.ended_at,
            duration_minutes=duration,
            lessons=data.lessons,
            breakthroughs=data.breakthroughs,
            summary=data.summary,
        )

        await self.db.execute(
            """INSERT INTO episodes
               (id, project_id, session_id, title, narrative, started_at, ended_at,
                duration_minutes, lessons, breakthroughs, summary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                episode.id, episode.project_id, episode.session_id,
                episode.title, episode.narrative,
                _datetime_str(episode.started_at), _datetime_str(episode.ended_at),
                episode.duration_minutes, _json_dumps(episode.lessons),
                _json_dumps(episode.breakthroughs), episode.summary,
            ),
        )
        await self.db.commit()
        return episode

    async def get_episode(self, episode_id: str) -> Optional[Episode]:
        """Get an episode by ID."""
        async with self.db.execute(
            "SELECT * FROM episodes WHERE id = ?", (episode_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_episode(row)

    async def list_episodes(self, project_id: str) -> list[Episode]:
        """List episodes for a project."""
        async with self.db.execute(
            "SELECT * FROM episodes WHERE project_id = ? ORDER BY started_at DESC",
            (project_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_episode(row) for row in rows]

    def _row_to_episode(self, row: aiosqlite.Row) -> Episode:
        """Convert database row to Episode."""
        mood_arc_data = _json_loads(row["mood_arc"], [])
        mood_arc = [MoodPoint(**m) for m in mood_arc_data]

        return Episode(
            id=row["id"],
            project_id=row["project_id"],
            session_id=row["session_id"],
            title=row["title"],
            narrative=row["narrative"],
            started_at=_parse_datetime(row["started_at"]) or datetime.utcnow(),
            ended_at=_parse_datetime(row["ended_at"]) or datetime.utcnow(),
            duration_minutes=row["duration_minutes"],
            mood_arc=mood_arc,
            overall_mood=row["overall_mood"],
            lessons=_json_loads(row["lessons"], []),
            breakthroughs=_json_loads(row["breakthroughs"], []),
            frustrations=_json_loads(row["frustrations"], []),
            decisions_made=_json_loads(row["decisions_made"], []),
            issues_opened=_json_loads(row["issues_opened"], []),
            issues_resolved=_json_loads(row["issues_resolved"], []),
            edges_discovered=_json_loads(row["edges_discovered"], []),
            keywords=_json_loads(row["keywords"], []),
            summary=row["summary"],
        )

    # ============ User Model ============

    async def get_or_create_user(self) -> UserModel:
        """Get or create the user model."""
        async with self.db.execute("SELECT * FROM user_model LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_user(row)

        # Create new user
        user = UserModel()
        await self.db.execute(
            """INSERT INTO user_model
               (id, communication, expertise, patterns, recent_wins, recent_frustrations,
                what_works, what_doesnt_work, projects, total_sessions, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user.id, _json_dumps(user.communication.model_dump()),
                _json_dumps(user.expertise.model_dump()),
                _json_dumps(user.patterns.model_dump()),
                _json_dumps([]), _json_dumps([]), _json_dumps([]), _json_dumps([]),
                _json_dumps([]), 0, _datetime_str(user.created_at),
                _datetime_str(user.updated_at),
            ),
        )
        await self.db.commit()
        return user

    async def update_user(self, data: UserModelUpdate) -> UserModel:
        """Update the user model."""
        user = await self.get_or_create_user()

        updates = ["updated_at = ?"]
        params: list[Any] = [_datetime_str(datetime.utcnow())]

        if data.name is not None:
            updates.append("name = ?")
            params.append(data.name)
        if data.current_energy is not None:
            updates.append("current_energy = ?")
            params.append(data.current_energy)
        if data.current_focus is not None:
            updates.append("current_focus = ?")
            params.append(data.current_focus)
        if data.add_win:
            wins = user.recent_wins + [data.add_win]
            updates.append("recent_wins = ?")
            params.append(_json_dumps(wins[-10:]))  # Keep last 10
        if data.add_frustration:
            frustrations = user.recent_frustrations + [data.add_frustration]
            updates.append("recent_frustrations = ?")
            params.append(_json_dumps(frustrations[-10:]))

        params.append(user.id)
        await self.db.execute(
            f"UPDATE user_model SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        await self.db.commit()

        return await self.get_or_create_user()

    async def increment_user_sessions(self, project_id: str) -> None:
        """Increment user's total sessions and update project list."""
        user = await self.get_or_create_user()

        projects = list(set(user.projects + [project_id]))
        first_session = user.first_session or datetime.utcnow()

        await self.db.execute(
            """UPDATE user_model SET
               total_sessions = total_sessions + 1,
               projects = ?,
               first_session = ?,
               last_session = ?,
               updated_at = ?
               WHERE id = ?""",
            (
                _json_dumps(projects), _datetime_str(first_session),
                _datetime_str(datetime.utcnow()), _datetime_str(datetime.utcnow()),
                user.id,
            ),
        )
        await self.db.commit()

    def _row_to_user(self, row: aiosqlite.Row) -> UserModel:
        """Convert database row to UserModel."""
        from mind.models.user import CommunicationPrefs, ExpertiseMap, WorkingPatterns

        comm_data = _json_loads(row["communication"], {})
        expertise_data = _json_loads(row["expertise"], {})
        patterns_data = _json_loads(row["patterns"], {})

        return UserModel(
            id=row["id"],
            name=row["name"],
            communication=CommunicationPrefs(**comm_data) if comm_data else CommunicationPrefs(),
            expertise=ExpertiseMap(**expertise_data) if expertise_data else ExpertiseMap(),
            patterns=WorkingPatterns(**patterns_data) if patterns_data else WorkingPatterns(),
            current_energy=row["current_energy"],
            current_focus=row["current_focus"],
            recent_wins=_json_loads(row["recent_wins"], []),
            recent_frustrations=_json_loads(row["recent_frustrations"], []),
            what_works=_json_loads(row["what_works"], []),
            what_doesnt_work=_json_loads(row["what_doesnt_work"], []),
            projects=_json_loads(row["projects"], []),
            total_sessions=row["total_sessions"],
            first_session=_parse_datetime(row["first_session"]),
            last_session=_parse_datetime(row["last_session"]),
            created_at=_parse_datetime(row["created_at"]) or datetime.utcnow(),
            updated_at=_parse_datetime(row["updated_at"]) or datetime.utcnow(),
        )

    # ============ Sessions ============

    async def create_session(self, project_id: str, user_id: str) -> Session:
        """Create a new session."""
        session = Session(project_id=project_id, user_id=user_id)

        await self.db.execute(
            """INSERT INTO sessions
               (id, project_id, user_id, started_at, status, memories_surfaced,
                progress, still_open, next_steps, decisions_made, issues_opened,
                issues_updated, edges_discovered)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session.id, project_id, user_id,
                _datetime_str(session.started_at), session.status,
                _json_dumps([]), _json_dumps([]), _json_dumps([]),
                _json_dumps([]), _json_dumps([]), _json_dumps([]),
                _json_dumps([]), _json_dumps([]),
            ),
        )
        await self.db.commit()
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        async with self.db.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_session(row)

    async def get_active_session(self, project_id: str) -> Optional[Session]:
        """Get the active session for a project."""
        async with self.db.execute(
            "SELECT * FROM sessions WHERE project_id = ? AND status = 'active' ORDER BY started_at DESC LIMIT 1",
            (project_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_session(row)

    async def end_session(self, session_id: str, data: SessionEnd) -> Optional[Session]:
        """End a session with summary."""
        session = await self.get_session(session_id)
        if not session:
            return None

        await self.db.execute(
            """UPDATE sessions SET
               ended_at = ?, status = 'ended', summary = ?,
               progress = ?, still_open = ?, next_steps = ?, mood = ?
               WHERE id = ?""",
            (
                _datetime_str(datetime.utcnow()), data.summary,
                _json_dumps(data.progress), _json_dumps(data.still_open),
                _json_dumps(data.next_steps), data.mood, session_id,
            ),
        )
        await self.db.commit()

        return await self.get_session(session_id)

    async def add_session_artifact(
        self,
        session_id: str,
        artifact_type: str,
        artifact_id: str,
    ) -> None:
        """Add an artifact to a session."""
        session = await self.get_session(session_id)
        if not session:
            return

        column_map = {
            "decision": "decisions_made",
            "issue_opened": "issues_opened",
            "issue_updated": "issues_updated",
            "edge": "edges_discovered",
        }

        column = column_map.get(artifact_type)
        if not column:
            return

        current = getattr(session, column.replace("_made", "s_made").replace("_opened", "s_opened"), [])
        if artifact_id not in current:
            updated = current + [artifact_id]
            await self.db.execute(
                f"UPDATE sessions SET {column} = ? WHERE id = ?",
                (_json_dumps(updated), session_id),
            )
            await self.db.commit()

    def _row_to_session(self, row: aiosqlite.Row) -> Session:
        """Convert database row to Session."""
        messages_data = _json_loads(row.get("messages") if hasattr(row, "get") else None, [])
        messages = [Message(**m) for m in messages_data]

        return Session(
            id=row["id"],
            project_id=row["project_id"],
            user_id=row["user_id"],
            started_at=_parse_datetime(row["started_at"]) or datetime.utcnow(),
            ended_at=_parse_datetime(row["ended_at"]),
            status=row["status"],
            primer_content=row["primer_content"],
            memories_surfaced=_json_loads(row["memories_surfaced"], []),
            messages=messages,
            summary=row["summary"],
            progress=_json_loads(row["progress"], []),
            still_open=_json_loads(row["still_open"], []),
            next_steps=_json_loads(row["next_steps"], []),
            mood=row["mood"],
            decisions_made=_json_loads(row["decisions_made"], []),
            issues_opened=_json_loads(row["issues_opened"], []),
            issues_updated=_json_loads(row["issues_updated"], []),
            edges_discovered=_json_loads(row["edges_discovered"], []),
            episode_id=row["episode_id"],
        )

    # ============ Search ============

    async def search_all(
        self,
        project_id: str,
        query: str,
    ) -> dict[str, list]:
        """Basic text search across all entities."""
        query_pattern = f"%{query}%"
        results: dict[str, list] = {
            "decisions": [],
            "issues": [],
            "edges": [],
            "episodes": [],
        }

        # Search decisions
        async with self.db.execute(
            """SELECT * FROM decisions
               WHERE project_id = ? AND (title LIKE ? OR description LIKE ? OR reasoning LIKE ?)
               ORDER BY decided_at DESC LIMIT 10""",
            (project_id, query_pattern, query_pattern, query_pattern),
        ) as cursor:
            rows = await cursor.fetchall()
            results["decisions"] = [self._row_to_decision(row) for row in rows]

        # Search issues
        async with self.db.execute(
            """SELECT * FROM issues
               WHERE project_id = ? AND (title LIKE ? OR description LIKE ? OR current_theory LIKE ?)
               ORDER BY opened_at DESC LIMIT 10""",
            (project_id, query_pattern, query_pattern, query_pattern),
        ) as cursor:
            rows = await cursor.fetchall()
            results["issues"] = [self._row_to_issue(row) for row in rows]

        # Search edges (include global)
        async with self.db.execute(
            """SELECT * FROM sharp_edges
               WHERE (project_id IS NULL OR project_id = ?)
               AND (title LIKE ? OR description LIKE ? OR workaround LIKE ?)
               ORDER BY discovered_at DESC LIMIT 10""",
            (project_id, query_pattern, query_pattern, query_pattern),
        ) as cursor:
            rows = await cursor.fetchall()
            results["edges"] = [self._row_to_sharp_edge(row) for row in rows]

        # Search episodes
        async with self.db.execute(
            """SELECT * FROM episodes
               WHERE project_id = ? AND (title LIKE ? OR narrative LIKE ? OR summary LIKE ?)
               ORDER BY started_at DESC LIMIT 10""",
            (project_id, query_pattern, query_pattern, query_pattern),
        ) as cursor:
            rows = await cursor.fetchall()
            results["episodes"] = [self._row_to_episode(row) for row in rows]

        return results
