# Mind Data Models

Complete entity definitions for all Mind stores.

## Project

The current state of a project. Not history—the now.

```python
class Project(BaseModel):
    id: str = Field(default_factory=lambda: f"proj_{ulid.new()}")
    name: str
    description: Optional[str] = None
    status: Literal["active", "paused", "archived"] = "active"
    
    # Tech context
    stack: List[str] = []  # ["nextjs", "supabase", "vercel"]
    repo_path: Optional[str] = None
    
    # Current focus
    current_goal: Optional[str] = None
    blocked_by: List[str] = []
    open_threads: List[str] = []
    
    # Session tracking
    last_session_id: Optional[str] = None
    last_session_date: Optional[datetime] = None
    last_session_summary: Optional[str] = None
    last_session_mood: Optional[str] = None
    last_session_next_step: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectCreate(BaseModel):
    """For creating new projects"""
    name: str
    description: Optional[str] = None
    stack: List[str] = []
    repo_path: Optional[str] = None


class ProjectUpdate(BaseModel):
    """For updating project state"""
    current_goal: Optional[str] = None
    blocked_by: Optional[List[str]] = None
    open_threads: Optional[List[str]] = None
    status: Optional[Literal["active", "paused", "archived"]] = None
```

## Decision

Choices with full reasoning chain.

```python
class Alternative(BaseModel):
    """An option that was considered"""
    option: str
    considered: bool = True
    rejected_because: Optional[str] = None


class Decision(BaseModel):
    id: str = Field(default_factory=lambda: f"dec_{ulid.new()}")
    project_id: str
    
    # The decision
    title: str  # "Use Supabase for backend"
    description: str  # Full explanation
    
    # The reasoning
    context: str  # What situation led to this
    reasoning: str  # Why we chose this
    alternatives: List[Alternative] = []
    
    # Confidence & validity
    confidence: float = 0.7  # 0.0 to 1.0
    revisit_if: Optional[str] = None  # Condition that triggers reconsideration
    valid_until: Optional[datetime] = None  # Some decisions expire
    status: Literal["active", "superseded", "revisiting"] = "active"
    superseded_by: Optional[str] = None  # ID of newer decision
    
    # Connections
    related_issues: List[str] = []
    related_edges: List[str] = []
    triggered_by_episode: Optional[str] = None
    
    # Retrieval
    trigger_phrases: List[str] = []  # ["why supabase", "database choice"]
    
    # Metadata
    decided_at: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    
    # For embedding
    @property
    def embedding_text(self) -> str:
        return f"{self.title}. {self.description}. {self.reasoning}"


class DecisionCreate(BaseModel):
    """For creating new decisions"""
    project_id: str
    title: str
    description: str
    context: str
    reasoning: str
    alternatives: List[Alternative] = []
    confidence: float = 0.7
    revisit_if: Optional[str] = None
    trigger_phrases: List[str] = []
```

## Issue

Problems with investigation history.

```python
class Attempt(BaseModel):
    """A solution attempt"""
    what: str  # What we tried
    result: str  # What happened
    learned: Optional[str] = None  # What we learned
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Issue(BaseModel):
    id: str = Field(default_factory=lambda: f"iss_{ulid.new()}")
    project_id: str
    
    # The problem
    title: str
    description: str
    severity: Literal["blocking", "major", "minor", "cosmetic"] = "major"
    status: Literal["open", "investigating", "blocked", "resolved", "wont_fix"] = "open"
    
    # Investigation
    attempts: List[Attempt] = []
    current_theory: Optional[str] = None
    blocked_by: Optional[str] = None
    
    # Resolution
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by_decision: Optional[str] = None
    
    # Connections
    related_decisions: List[str] = []
    related_edges: List[str] = []
    caused_by_episode: Optional[str] = None
    
    # Retrieval
    symptoms: List[str] = []  # Error messages, behaviors
    trigger_phrases: List[str] = []
    
    # Metadata
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    
    @property
    def embedding_text(self) -> str:
        parts = [self.title, self.description]
        parts.extend(self.symptoms)
        if self.current_theory:
            parts.append(self.current_theory)
        return ". ".join(parts)


class IssueCreate(BaseModel):
    """For creating new issues"""
    project_id: str
    title: str
    description: str
    severity: Literal["blocking", "major", "minor", "cosmetic"] = "major"
    symptoms: List[str] = []


class IssueUpdate(BaseModel):
    """For updating issues"""
    status: Optional[Literal["open", "investigating", "blocked", "resolved", "wont_fix"]] = None
    add_attempt: Optional[Attempt] = None
    current_theory: Optional[str] = None
    blocked_by: Optional[str] = None
    resolution: Optional[str] = None
```

## Sharp Edge

Gotchas with detection patterns.

```python
class DetectionPattern(BaseModel):
    """Pattern for detecting when edge might be hit"""
    type: Literal["code", "context", "intent"]
    pattern: str  # Regex for code, keywords for context/intent
    description: str  # Human readable explanation
    
    # For code patterns
    file_pattern: Optional[str] = None  # e.g., "*.edge.ts"
    

class SharpEdge(BaseModel):
    id: str = Field(default_factory=lambda: f"edge_{ulid.new()}")
    project_id: Optional[str] = None  # None = global edge
    
    # The gotcha
    title: str
    description: str
    
    # Detection
    detection_patterns: List[DetectionPattern] = []
    trigger_phrases: List[str] = []
    symptoms: List[str] = []  # What you see when you hit it
    
    # Solution
    workaround: str
    root_cause: Optional[str] = None
    proper_fix: Optional[str] = None  # If there's a real fix vs workaround
    
    # Origin
    discovered_in_episode: Optional[str] = None
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Connections
    related_decisions: List[str] = []
    related_issues: List[str] = []
    
    # For community registry
    submitted_by: Optional[str] = None  # Anonymous or user ID
    verification_count: int = 0
    verified_by: List[str] = []
    
    @property
    def embedding_text(self) -> str:
        parts = [self.title, self.description, self.workaround]
        parts.extend(self.symptoms)
        return ". ".join(parts)


class SharpEdgeCreate(BaseModel):
    """For creating new sharp edges"""
    title: str
    description: str
    workaround: str
    detection_patterns: List[DetectionPattern] = []
    symptoms: List[str] = []
    project_id: Optional[str] = None
    root_cause: Optional[str] = None
```

## Episode

Narrative of significant sessions.

```python
class MoodPoint(BaseModel):
    """A point in the emotional arc"""
    timestamp: datetime
    mood: str  # "frustrated", "curious", "breakthrough", etc.
    trigger: Optional[str] = None  # What caused the shift


class Episode(BaseModel):
    id: str = Field(default_factory=lambda: f"ep_{ulid.new()}")
    project_id: str
    session_id: str
    
    # The story
    title: str  # "The Great Auth Debugging Session"
    narrative: str  # What happened, in prose
    
    # Timeline
    started_at: datetime
    ended_at: datetime
    duration_minutes: int
    
    # Emotional arc
    mood_arc: List[MoodPoint] = []
    overall_mood: Optional[str] = None
    
    # Outcomes
    lessons: List[str] = []
    breakthroughs: List[str] = []
    frustrations: List[str] = []
    
    # Artifacts created
    decisions_made: List[str] = []
    issues_opened: List[str] = []
    issues_resolved: List[str] = []
    edges_discovered: List[str] = []
    
    # Retrieval
    keywords: List[str] = []
    summary: str  # Short version for embedding
    
    @property
    def embedding_text(self) -> str:
        return f"{self.title}. {self.summary}"


class EpisodeCreate(BaseModel):
    """For creating episodes (usually auto-generated)"""
    project_id: str
    session_id: str
    title: str
    narrative: str
    started_at: datetime
    ended_at: datetime
    lessons: List[str] = []
    breakthroughs: List[str] = []
    summary: str
```

## User Model

How the human works.

```python
class CommunicationPrefs(BaseModel):
    """How user prefers to communicate"""
    prefers: List[str] = []  # ["direct feedback", "examples over theory"]
    dislikes: List[str] = []  # ["hedging", "excessive caveats"]


class ExpertiseMap(BaseModel):
    """User's skill levels"""
    strong: List[str] = []  # ["product thinking", "react"]
    learning: List[str] = []  # ["devops", "security"]


class WorkingPatterns(BaseModel):
    """Observed patterns in how user works"""
    works_late: bool = False
    pushes_through_frustration: bool = False
    tendency_to_over_architect: bool = False
    prefers_shipping_over_perfection: bool = True
    # Add more as we learn


class UserModel(BaseModel):
    id: str = Field(default_factory=lambda: f"user_{ulid.new()}")
    
    # Identity
    name: Optional[str] = None
    
    # Stable traits
    communication: CommunicationPrefs = CommunicationPrefs()
    expertise: ExpertiseMap = ExpertiseMap()
    patterns: WorkingPatterns = WorkingPatterns()
    
    # Dynamic state
    current_energy: Optional[str] = None  # "high", "low", "tired"
    current_focus: Optional[str] = None  # What they're focused on
    recent_wins: List[str] = []
    recent_frustrations: List[str] = []
    
    # Calibration
    what_works: List[str] = []  # Things that work in our collaboration
    what_doesnt_work: List[str] = []  # Things that don't
    
    # History
    projects: List[str] = []
    total_sessions: int = 0
    first_session: Optional[datetime] = None
    last_session: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserModelUpdate(BaseModel):
    """For updating user model"""
    name: Optional[str] = None
    current_energy: Optional[str] = None
    current_focus: Optional[str] = None
    add_win: Optional[str] = None
    add_frustration: Optional[str] = None
    add_pattern: Optional[str] = None
    learned_preference: Optional[str] = None
```

## Session

Container for a conversation.

```python
class Message(BaseModel):
    """A message in the session (optional storage)"""
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Session(BaseModel):
    id: str = Field(default_factory=lambda: f"sess_{ulid.new()}")
    project_id: str
    user_id: str
    
    # Lifecycle
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    status: Literal["active", "ended", "abandoned"] = "active"
    
    # Context loaded at start
    primer_content: Optional[str] = None
    memories_surfaced: List[str] = []  # IDs of memories used
    
    # What happened (optional - could just store transcript)
    messages: List[Message] = []
    
    # Captured at end
    summary: Optional[str] = None
    progress: List[str] = []
    still_open: List[str] = []
    next_steps: List[str] = []
    mood: Optional[str] = None
    
    # Artifacts created during session
    decisions_made: List[str] = []
    issues_opened: List[str] = []
    issues_updated: List[str] = []
    edges_discovered: List[str] = []
    
    # If significant enough to become episode
    episode_id: Optional[str] = None


class SessionStart(BaseModel):
    """Response when starting a session"""
    session_id: str
    project: Project
    primer: str
    open_issues: List[Issue]
    pending_decisions: List[Decision]
    relevant_edges: List[SharpEdge]


class SessionEnd(BaseModel):
    """Request when ending a session"""
    summary: str
    progress: List[str] = []
    still_open: List[str] = []
    next_steps: List[str] = []
    mood: Optional[str] = None
```

## Shared Types

```python
from enum import Enum

class EntityType(str, Enum):
    PROJECT = "project"
    DECISION = "decision"
    ISSUE = "issue"
    SHARP_EDGE = "sharp_edge"
    EPISODE = "episode"
    USER = "user"
    SESSION = "session"


class ChangeType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class Change(BaseModel):
    """For tracking changes (sync)"""
    id: str = Field(default_factory=lambda: f"chg_{ulid.new()}")
    entity_type: EntityType
    entity_id: str
    change_type: ChangeType
    data: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    synced: bool = False
```

## SQLite Schema

```sql
-- Projects
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active',
    stack TEXT,  -- JSON array
    repo_path TEXT,
    current_goal TEXT,
    blocked_by TEXT,  -- JSON array
    open_threads TEXT,  -- JSON array
    last_session_id TEXT,
    last_session_date TEXT,
    last_session_summary TEXT,
    last_session_mood TEXT,
    last_session_next_step TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Decisions
CREATE TABLE decisions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    context TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    alternatives TEXT,  -- JSON array
    confidence REAL DEFAULT 0.7,
    revisit_if TEXT,
    valid_until TEXT,
    status TEXT DEFAULT 'active',
    superseded_by TEXT,
    related_issues TEXT,  -- JSON array
    related_edges TEXT,  -- JSON array
    triggered_by_episode TEXT,
    trigger_phrases TEXT,  -- JSON array
    decided_at TEXT NOT NULL,
    session_id TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Issues
CREATE TABLE issues (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT DEFAULT 'major',
    status TEXT DEFAULT 'open',
    attempts TEXT,  -- JSON array
    current_theory TEXT,
    blocked_by TEXT,
    resolution TEXT,
    resolved_at TEXT,
    resolved_by_decision TEXT,
    related_decisions TEXT,  -- JSON array
    related_edges TEXT,  -- JSON array
    caused_by_episode TEXT,
    symptoms TEXT,  -- JSON array
    trigger_phrases TEXT,  -- JSON array
    opened_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    session_id TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Sharp Edges
CREATE TABLE sharp_edges (
    id TEXT PRIMARY KEY,
    project_id TEXT,  -- NULL for global edges
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    detection_patterns TEXT,  -- JSON array
    trigger_phrases TEXT,  -- JSON array
    symptoms TEXT,  -- JSON array
    workaround TEXT NOT NULL,
    root_cause TEXT,
    proper_fix TEXT,
    discovered_in_episode TEXT,
    discovered_at TEXT NOT NULL,
    related_decisions TEXT,  -- JSON array
    related_issues TEXT,  -- JSON array
    submitted_by TEXT,
    verification_count INTEGER DEFAULT 0,
    verified_by TEXT,  -- JSON array
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Episodes
CREATE TABLE episodes (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    title TEXT NOT NULL,
    narrative TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    duration_minutes INTEGER,
    mood_arc TEXT,  -- JSON array
    overall_mood TEXT,
    lessons TEXT,  -- JSON array
    breakthroughs TEXT,  -- JSON array
    frustrations TEXT,  -- JSON array
    decisions_made TEXT,  -- JSON array
    issues_opened TEXT,  -- JSON array
    issues_resolved TEXT,  -- JSON array
    edges_discovered TEXT,  -- JSON array
    keywords TEXT,  -- JSON array
    summary TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- User Model (typically just one record)
CREATE TABLE user_model (
    id TEXT PRIMARY KEY,
    name TEXT,
    communication TEXT,  -- JSON object
    expertise TEXT,  -- JSON object
    patterns TEXT,  -- JSON object
    current_energy TEXT,
    current_focus TEXT,
    recent_wins TEXT,  -- JSON array
    recent_frustrations TEXT,  -- JSON array
    what_works TEXT,  -- JSON array
    what_doesnt_work TEXT,  -- JSON array
    projects TEXT,  -- JSON array
    total_sessions INTEGER DEFAULT 0,
    first_session TEXT,
    last_session TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Sessions
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT DEFAULT 'active',
    primer_content TEXT,
    memories_surfaced TEXT,  -- JSON array
    summary TEXT,
    progress TEXT,  -- JSON array
    still_open TEXT,  -- JSON array
    next_steps TEXT,  -- JSON array
    mood TEXT,
    decisions_made TEXT,  -- JSON array
    issues_opened TEXT,  -- JSON array
    issues_updated TEXT,  -- JSON array
    edges_discovered TEXT,  -- JSON array
    episode_id TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Changes (for sync)
CREATE TABLE changes (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    change_type TEXT NOT NULL,
    data TEXT NOT NULL,  -- JSON
    timestamp TEXT NOT NULL,
    synced INTEGER DEFAULT 0
);

-- Indexes
CREATE INDEX idx_decisions_project ON decisions(project_id);
CREATE INDEX idx_issues_project ON issues(project_id);
CREATE INDEX idx_issues_status ON issues(status);
CREATE INDEX idx_edges_project ON sharp_edges(project_id);
CREATE INDEX idx_episodes_project ON episodes(project_id);
CREATE INDEX idx_sessions_project ON sessions(project_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_changes_synced ON changes(synced);
CREATE INDEX idx_changes_timestamp ON changes(timestamp);
```
