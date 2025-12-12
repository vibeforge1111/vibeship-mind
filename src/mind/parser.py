"""Loose parser for extracting entities from natural language."""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class EntityType(Enum):
    DECISION = "decision"
    ISSUE = "issue"
    LEARNING = "learning"
    EDGE = "edge"


class IssueStatus(Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    BLOCKED = "blocked"


@dataclass
class Entity:
    type: EntityType
    title: str
    content: str
    source_file: str
    source_line: int
    confidence: float
    reasoning: Optional[str] = None
    alternatives: list[str] = field(default_factory=list)
    status: Optional[IssueStatus] = None
    date: Optional[date] = None
    matched_pattern: str = ""
    is_key: bool = False  # Marked with KEY: or important: - never fades
    days_ago: Optional[int] = None  # For recency sorting


@dataclass
class SessionSummary:
    """Summary line for a session: ## 2025-12-13 | what happened | mood: X"""
    date: date
    summary: Optional[str] = None
    mood: Optional[str] = None


@dataclass
class ProjectState:
    goal: Optional[str] = None
    stack: list[str] = field(default_factory=list)
    blocked_by: Optional[str] = None


@dataclass
class Edge:
    title: str
    workaround: Optional[str] = None
    source: str = "project"


@dataclass
class ParseResult:
    project_state: ProjectState
    entities: list[Entity]
    project_edges: list[Edge]
    session_summaries: list[SessionSummary] = field(default_factory=list)

    def entities_by_recency(self) -> list[Entity]:
        """Return entities sorted by recency. Key items first, then by days_ago."""
        def sort_key(e: Entity) -> tuple[int, int]:
            # Key items always first (0), others second (1)
            key_rank = 0 if e.is_key else 1
            # Then by days_ago (None treated as very old)
            days = e.days_ago if e.days_ago is not None else 9999
            return (key_rank, days)

        return sorted(self.entities, key=sort_key)


# Decision patterns - ordered by specificity
DECISION_PATTERNS = [
    (r"\*\*[Dd]ecided:?\*\*\s*(.+)", 0.9),
    (r"[Dd]ecided\s+(?:to\s+)?(.+?)(?:\.|$)", 0.5),
    (r"[Cc]hose\s+(.+?)\s+(?:over|because|instead|\.|$)", 0.6),
    (r"[Gg]oing\s+with\s+(.+?)(?:\.|$)", 0.5),
    (r"[Uu]sing\s+(.+?)\s+(?:instead|over|because|rather|\.|$)", 0.5),
    (r"[Ww]ent\s+with\s+(.+?)(?:\.|$)", 0.5),
    (r"[Ss]ettled\s+on\s+(.+?)(?:\.|$)", 0.5),
    (r"[Pp]icked\s+(.+?)\s+(?:over|because|\.|$)", 0.5),
    (r"MEMORY:\s*decided\s+(.+)", 0.7),
]

# Issue patterns
ISSUE_PATTERNS = [
    (r"\*\*[Pp]roblem:?\*\*\s*(.+)", 0.9),
    (r"\*\*[Ii]ssue:?\*\*\s*(.+)", 0.9),
    (r"\*\*[Bb]ug:?\*\*\s*(.+)", 0.9),
    (r"[Pp]roblem:?\s*[-–]?\s*(.+?)(?:\.|$)", 0.6),
    (r"[Ii]ssue:?\s*[-–]?\s*(.+?)(?:\.|$)", 0.6),
    (r"[Bb]ug:?\s*[-–]?\s*(.+?)(?:\.|$)", 0.6),
    (r"[Hh]it\s+(?:a\s+)?(?:problem|issue|bug)\s+(?:with\s+)?(.+?)(?:\.|$)", 0.5),
    (r"[Ss]truggling\s+with\s+(.+?)(?:\.|$)", 0.5),
    (r"[Ss]tuck\s+on\s+(.+?)(?:\.|$)", 0.5),
    (r"(.+?)\s+(?:doesn't|does not|won't|isn't|is not)\s+work", 0.4),
    (r"(.+?)\s+(?:broken|failing|failed)", 0.4),
    (r"MEMORY:\s*(?:problem|issue)\s+(.+)", 0.7),
]

# Learning patterns
LEARNING_PATTERNS = [
    (r"\*\*[Ll]earned:?\*\*\s*(.+)", 0.9),
    (r"\*\*[Tt][Ii][Ll]:?\*\*\s*(.+)", 0.9),
    (r"\*\*[Gg]otcha:?\*\*\s*(.+)", 0.9),
    (r"[Ll]earned\s+(?:that\s+)?(.+?)(?:\.|$)", 0.5),
    (r"[Dd]iscovered\s+(?:that\s+)?(.+?)(?:\.|$)", 0.5),
    (r"[Rr]ealized\s+(?:that\s+)?(.+?)(?:\.|$)", 0.5),
    (r"[Tt]urns\s+out\s+(?:that\s+)?(.+?)(?:\.|$)", 0.5),
    (r"[Ff]ound\s+out\s+(?:that\s+)?(.+?)(?:\.|$)", 0.5),
    (r"[Tt][Ii][Ll]:?\s*(.+?)(?:\.|$)", 0.6),
    (r"[Gg]otcha:?\s*(.+?)(?:\.|$)", 0.6),
    (r"MEMORY:\s*(?:learned|til)\s+(.+)", 0.7),
]

# Status patterns for issues
RESOLVED_PATTERNS = [
    r"\*\*[Ff]ixed:?\*\*",
    r"[Ff]ixed:?\s",
    r"[Rr]esolved:?\s",
    r"[Ss]olved:?\s",
    r"\[x\]",
]

BLOCKED_PATTERNS = [
    r"[Bb]locked\s+(?:by|on)",
    r"[Ww]aiting\s+(?:for|on)",
    r"[Nn]eed(?:s)?\s+(?:to|more)",
]

# Reasoning patterns
REASONING_PATTERNS = [
    r"\bbecause\s+(.+?)(?:\.|$)",
    r"\bsince\s+(.+?)(?:\.|$)",
    r"\bso\s+(?:that\s+)?(.+?)(?:\.|$)",
    r"\bdue\s+to\s+(.+?)(?:\.|$)",
    r"\breason:?\s*(.+?)(?:\.|$)",
]

# Alternative patterns
ALTERNATIVE_PATTERNS = [
    r"\bover\s+(.+?)(?:\s+because|\.|$)",
    r"\binstead\s+of\s+(.+?)(?:\.|$)",
    r"\brather\s+than\s+(.+?)(?:\.|$)",
]

# Date patterns
DATE_PATTERNS = [
    (r"^##\s*(\d{4}-\d{2}-\d{2})", "%Y-%m-%d"),
    (r"^##\s*(\d{1,2}/\d{1,2}/\d{4})", "%m/%d/%Y"),
    (r"^##\s*(\w+\s+\d{1,2},?\s+\d{4})", None),  # December 12, 2024
]

# False positive patterns to skip
FALSE_POSITIVE_PATTERNS = [
    r"i\s+decided\s+not\s+to",
    r"haven't\s+decided",
    r"should\s+we\s+decide",
    r"if\s+we\s+decide",
    r"might\s+decide",
    r"need\s+to\s+decide",
]

# Key/important patterns - items that never fade
KEY_PATTERNS = [
    r"^KEY:\s*",
    r"^\*\*KEY:?\*\*\s*",
    r"^important:\s*",
    r"^\*\*important:?\*\*\s*",
    r"^IMPORTANT:\s*",
]


class Parser:
    """Loose parser for extracting entities from MEMORY.md content."""

    def parse(self, content: str, source_file: str = "MEMORY.md") -> ParseResult:
        """Parse content and extract entities."""
        entities = []
        date_context = self._extract_date_context(content)
        today = date.today()

        for line_num, line in enumerate(content.split("\n")):
            if self._should_skip(line):
                continue

            current_date = date_context.get(line_num)

            # Try each entity type
            if entity := self._try_parse_decision(line, line_num, source_file, current_date):
                entities.append(entity)
            elif entity := self._try_parse_issue(line, line_num, source_file, current_date):
                entities.append(entity)
            elif entity := self._try_parse_learning(line, line_num, source_file, current_date):
                entities.append(entity)

        # Calculate days_ago and detect key items for all entities
        for entity in entities:
            # Check if marked as key/important
            entity.is_key = self._is_key_item(entity.content)

            # Calculate days ago
            if entity.date:
                entity.days_ago = (today - entity.date).days

        # Extract project state, edges, and session summaries
        project_state = self._extract_project_state(content)
        project_edges = self._extract_project_edges(content)
        session_summaries = self._extract_session_summaries(content)

        return ParseResult(
            project_state=project_state,
            entities=entities,
            project_edges=project_edges,
            session_summaries=session_summaries,
        )

    def _is_key_item(self, line: str) -> bool:
        """Check if line is marked as key/important."""
        for pattern in KEY_PATTERNS:
            if re.match(pattern, line.strip(), re.IGNORECASE):
                return True
        return False

    def _should_skip(self, line: str) -> bool:
        """Check if line should be skipped."""
        stripped = line.strip()
        if not stripped:
            return True
        if stripped.startswith("#") and not stripped.startswith("##"):
            return True
        if stripped.startswith("<!--"):
            return True
        if "MIND MEMORY" in stripped:
            return True
        if stripped == "---":
            return True
        if stripped.startswith("- Goal:") or stripped.startswith("- Stack:") or stripped.startswith("- Blocked:"):
            return True
        if stripped.startswith("Keywords:"):
            return True
        # Skip session summary lines (## DATE | summary | mood: X)
        if stripped.startswith("##") and "|" in stripped:
            return True
        return False

    def _is_false_positive(self, line: str) -> bool:
        """Check if line is a false positive."""
        line_lower = line.lower()
        for pattern in FALSE_POSITIVE_PATTERNS:
            if re.search(pattern, line_lower):
                return True
        return False

    def _try_parse_decision(
        self, line: str, line_num: int, source_file: str, current_date: Optional[date]
    ) -> Optional[Entity]:
        """Try to parse a decision from line."""
        if self._is_false_positive(line):
            return None

        for pattern, base_confidence in DECISION_PATTERNS:
            if match := re.search(pattern, line, re.IGNORECASE):
                title = match.group(1).strip()
                if len(title) < 3:
                    continue

                confidence = self._score_confidence(line, base_confidence)
                reasoning = self._find_reasoning(line)
                alternatives = self._find_alternatives(line)

                return Entity(
                    type=EntityType.DECISION,
                    title=title,
                    content=line.strip(),
                    source_file=source_file,
                    source_line=line_num,
                    confidence=confidence,
                    reasoning=reasoning,
                    alternatives=alternatives,
                    date=current_date,
                    matched_pattern=pattern,
                )
        return None

    def _try_parse_issue(
        self, line: str, line_num: int, source_file: str, current_date: Optional[date]
    ) -> Optional[Entity]:
        """Try to parse an issue from line."""
        for pattern, base_confidence in ISSUE_PATTERNS:
            if match := re.search(pattern, line, re.IGNORECASE):
                title = match.group(1).strip()
                if len(title) < 3:
                    continue

                confidence = self._score_confidence(line, base_confidence)
                status = self._detect_issue_status(line)
                reasoning = self._find_reasoning(line)

                return Entity(
                    type=EntityType.ISSUE,
                    title=title,
                    content=line.strip(),
                    source_file=source_file,
                    source_line=line_num,
                    confidence=confidence,
                    reasoning=reasoning,
                    status=status,
                    date=current_date,
                    matched_pattern=pattern,
                )
        return None

    def _try_parse_learning(
        self, line: str, line_num: int, source_file: str, current_date: Optional[date]
    ) -> Optional[Entity]:
        """Try to parse a learning from line."""
        for pattern, base_confidence in LEARNING_PATTERNS:
            if match := re.search(pattern, line, re.IGNORECASE):
                title = match.group(1).strip()
                if len(title) < 3:
                    continue

                confidence = self._score_confidence(line, base_confidence)

                return Entity(
                    type=EntityType.LEARNING,
                    title=title,
                    content=line.strip(),
                    source_file=source_file,
                    source_line=line_num,
                    confidence=confidence,
                    date=current_date,
                    matched_pattern=pattern,
                )
        return None

    def _score_confidence(self, line: str, base_confidence: float) -> float:
        """Score confidence based on line characteristics."""
        confidence = base_confidence

        if "**" in line:  # Explicit markdown
            confidence += 0.2
        if re.search(r"\bbecause\b", line, re.IGNORECASE):  # Has reasoning
            confidence += 0.15
        if re.search(r"\bover\b", line, re.IGNORECASE):  # Has alternative
            confidence += 0.1
        if line.strip().startswith("MEMORY:"):  # Quick syntax
            confidence += 0.1

        return min(confidence, 1.0)

    def _find_reasoning(self, line: str) -> Optional[str]:
        """Extract reasoning from line."""
        for pattern in REASONING_PATTERNS:
            if match := re.search(pattern, line, re.IGNORECASE):
                return match.group(1).strip()
        return None

    def _find_alternatives(self, line: str) -> list[str]:
        """Extract alternatives from line."""
        alternatives = []
        for pattern in ALTERNATIVE_PATTERNS:
            if match := re.search(pattern, line, re.IGNORECASE):
                alternatives.append(match.group(1).strip())
        return alternatives

    def _detect_issue_status(self, line: str) -> IssueStatus:
        """Detect issue status from line."""
        for pattern in RESOLVED_PATTERNS:
            if re.search(pattern, line):
                return IssueStatus.RESOLVED

        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, line):
                return IssueStatus.BLOCKED

        return IssueStatus.OPEN

    def _extract_date_context(self, content: str) -> dict[int, date]:
        """Map line numbers to their date context."""
        date_map: dict[int, date] = {}
        current_date: Optional[date] = None

        for line_num, line in enumerate(content.split("\n")):
            for pattern, date_format in DATE_PATTERNS:
                if match := re.match(pattern, line):
                    date_str = match.group(1)
                    try:
                        if date_format:
                            current_date = datetime.strptime(date_str, date_format).date()
                        else:
                            # Handle "December 12, 2024" format
                            current_date = self._parse_natural_date(date_str)
                    except ValueError:
                        pass
                    break

            if current_date:
                date_map[line_num] = current_date

        return date_map

    def _parse_natural_date(self, date_str: str) -> Optional[date]:
        """Parse natural date formats like 'December 12, 2024'."""
        formats = [
            "%B %d, %Y",
            "%B %d %Y",
            "%b %d, %Y",
            "%b %d %Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None

    def _extract_project_state(self, content: str) -> ProjectState:
        """Extract project state from ## Project State section."""
        state = ProjectState()

        state_match = re.search(
            r"##\s*[Pp]roject\s*[Ss]tate\s*\n(.*?)(?=\n##|\Z)",
            content,
            re.DOTALL,
        )

        if not state_match:
            return state

        section = state_match.group(1)

        for line in section.split("\n"):
            line = line.strip()
            if match := re.match(r"-\s*[Gg]oal:?\s*(.+)", line):
                goal = match.group(1).strip()
                if goal and goal.lower() not in ("", ":", "(describe your goal)"):
                    state.goal = goal
            elif match := re.match(r"-\s*[Ss]tack:?\s*(.+)", line):
                stack_str = match.group(1).strip()
                if stack_str and stack_str.lower() not in ("", "(add your stack)"):
                    state.stack = [s.strip() for s in stack_str.split(",")]
            elif match := re.match(r"-\s*[Bb]locked:?\s*(.+)", line):
                blocked = match.group(1).strip()
                if blocked.lower() not in ("none", ""):
                    state.blocked_by = blocked

        return state

    def _extract_project_edges(self, content: str) -> list[Edge]:
        """Extract edges from ## Gotchas section."""
        gotchas_match = re.search(
            r"##\s*[Gg]otchas?\s*\n(.*?)(?=\n##|\n---|\Z)",
            content,
            re.DOTALL,
        )

        if not gotchas_match:
            return []

        edges = []
        for line in gotchas_match.group(1).split("\n"):
            line = line.strip()
            if not line or line.startswith("<!--"):
                continue
            if line.startswith("-") or line.startswith("*"):
                # Parse: "- Thing -> Workaround" or "- Thing - Workaround"
                text = line.lstrip("-* ").strip()
                if not text:
                    continue

                parts = re.split(r"\s*(?:->|→|--)\s*", text, maxsplit=1)
                title = parts[0].strip()
                workaround = parts[1].strip() if len(parts) > 1 else None

                if title:
                    edges.append(Edge(title=title, workaround=workaround))

        return edges

    def _extract_session_summaries(self, content: str) -> list[SessionSummary]:
        """Extract session summary lines: ## 2025-12-13 | summary | mood: X"""
        summaries = []

        # Pattern: ## DATE | summary | mood: X  (mood is optional)
        # DATE can be 2025-12-13 or natural format
        pattern = r"^##\s*(\d{4}-\d{2}-\d{2}|\w+\s+\d{1,2},?\s+\d{4})\s*\|\s*(.+?)(?:\s*\|\s*mood:\s*(.+))?$"

        for line in content.split("\n"):
            if match := re.match(pattern, line.strip(), re.IGNORECASE):
                date_str = match.group(1)
                summary_text = match.group(2).strip() if match.group(2) else None
                mood = match.group(3).strip() if match.group(3) else None

                # Parse the date
                parsed_date = None
                try:
                    parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    parsed_date = self._parse_natural_date(date_str)

                if parsed_date:
                    summaries.append(SessionSummary(
                        date=parsed_date,
                        summary=summary_text,
                        mood=mood,
                    ))

        return summaries


class InlineScanner:
    """Scanner for MEMORY: comments in code files."""

    PATTERNS = {
        ".py": r"#\s*MEMORY:\s*(.+)",
        ".ts": r"//\s*MEMORY:\s*(.+)",
        ".tsx": r"//\s*MEMORY:\s*(.+)",
        ".js": r"//\s*MEMORY:\s*(.+)",
        ".jsx": r"//\s*MEMORY:\s*(.+)",
        ".svelte": r"<!--\s*MEMORY:\s*(.+?)\s*-->",
        ".vue": r"<!--\s*MEMORY:\s*(.+?)\s*-->",
        ".html": r"<!--\s*MEMORY:\s*(.+?)\s*-->",
        ".css": r"/\*\s*MEMORY:\s*(.+?)\s*\*/",
        ".rs": r"//\s*MEMORY:\s*(.+)",
        ".go": r"//\s*MEMORY:\s*(.+)",
    }

    def __init__(self):
        self.parser = Parser()

    def scan_file(self, path: Path) -> list[Entity]:
        """Scan code file for MEMORY: comments."""
        suffix = path.suffix
        if suffix not in self.PATTERNS:
            return []

        pattern = self.PATTERNS[suffix]

        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return []

        entities = []

        for line_num, line in enumerate(content.split("\n")):
            if match := re.search(pattern, line):
                memory_content = match.group(1).strip()

                # Parse the memory content as if it were a MEMORY.md line
                result = self.parser.parse(memory_content, source_file=str(path))

                for entity in result.entities:
                    entity.source_line = line_num
                    entities.append(entity)

        return entities

    def scan_directory(self, directory: Path, exclude_dirs: Optional[set[str]] = None) -> list[Entity]:
        """Scan directory for MEMORY: comments in code files."""
        if exclude_dirs is None:
            exclude_dirs = {
                "node_modules",
                ".git",
                ".venv",
                "venv",
                "__pycache__",
                "dist",
                "build",
                ".mind",
            }

        entities = []

        for path in directory.rglob("*"):
            if path.is_file() and path.suffix in self.PATTERNS:
                # Skip excluded directories
                if any(excluded in path.parts for excluded in exclude_dirs):
                    continue
                entities.extend(self.scan_file(path))

        return entities
