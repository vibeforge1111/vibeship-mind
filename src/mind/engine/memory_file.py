"""MEMORY.md file parser and indexer.

The MEMORY.md file is the source of truth for project memory.
Claude writes directly to it. Mind watches, parses, and indexes it.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class MemoryEntry:
    """A single session entry parsed from MEMORY.md."""

    date: datetime
    duration: Optional[str] = None
    content: str = ""
    decisions: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    learnings: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    raw_text: str = ""


@dataclass
class ParsedMemory:
    """Parsed contents of a MEMORY.md file."""

    project_name: str
    entries: list[MemoryEntry] = field(default_factory=list)
    raw_content: str = ""
    project_state: Optional["ProjectState"] = None

    @property
    def latest_entry(self) -> Optional[MemoryEntry]:
        """Get the most recent entry."""
        return self.entries[0] if self.entries else None

    @property
    def all_decisions(self) -> list[str]:
        """Get all decisions across all entries."""
        return [d for e in self.entries for d in e.decisions]

    @property
    def all_learnings(self) -> list[str]:
        """Get all learnings across all entries."""
        return [l for e in self.entries for l in e.learnings]

    @property
    def all_problems(self) -> list[str]:
        """Get all problems across all entries."""
        return [p for e in self.entries for p in e.problems]


@dataclass
class ProjectState:
    """Extracted project state from MEMORY.md header."""

    goal: Optional[str] = None
    stack: list[str] = field(default_factory=list)
    status: Optional[str] = None
    gotchas: list[str] = field(default_factory=list)
    key_decisions: list[str] = field(default_factory=list)


class MemoryFileParser:
    """Parser for MEMORY.md files.

    Supports both structured format (**Decided:**, **Problem:**) and
    loose stream-of-consciousness writing. Uses keyword detection to
    extract meaning from natural language.
    """

    # Patterns for structured parsing
    HEADER_PATTERN = re.compile(r'^#\s+(.+)$', re.MULTILINE)
    DATE_PATTERN = re.compile(r'^##\s+(?:(\d{4}-\d{2}-\d{2})|([A-Z][a-z]{2}\s+\d{1,2}))(?:\s+\((.+)\))?', re.MULTILINE)
    DECIDED_PATTERN = re.compile(r'\*\*Decided:\*\*\s*(.+?)(?=\n\n|\n\*\*|\n##|\n---|\Z)', re.DOTALL)
    PROBLEM_PATTERN = re.compile(r'\*\*Problem:\*\*\s*(.+?)(?=\n\n|\n\*\*|\n##|\n---|\Z)', re.DOTALL)
    LEARNED_PATTERN = re.compile(r'\*\*Learned:\*\*\s*(.+?)(?=\n\n|\n\*\*|\n##|\n---|\Z)', re.DOTALL)
    NEXT_PATTERN = re.compile(r'(?:next:|next steps:|next time:)\s*(.+?)(?=\n\n|\n##|\n---|\Z)', re.DOTALL | re.IGNORECASE)

    # Patterns for project state section
    PROJECT_STATE_PATTERN = re.compile(r'^## Project State\s*\n(.*?)(?=\n##|\n---|\Z)', re.MULTILINE | re.DOTALL)
    GOTCHAS_PATTERN = re.compile(r'^## Gotchas\s*\n(.*?)(?=\n##|\n---|\Z)', re.MULTILINE | re.DOTALL)
    KEY_DECISIONS_PATTERN = re.compile(r'^## Key Decisions\s*\n(.*?)(?=\n##|\n---|\Z)', re.MULTILINE | re.DOTALL)

    # Loose keyword patterns for stream-of-consciousness
    LOOSE_DECIDED = re.compile(r'(?:decided|chose|went with|picked|using)\s+(.+?)(?:\.|$)', re.IGNORECASE)
    LOOSE_PROBLEM = re.compile(r'(?:problem|issue|bug|broke|broken|doesn\'t work|failed|error)\s*[:\-]?\s*(.+?)(?:\.|$)', re.IGNORECASE)
    LOOSE_LEARNED = re.compile(r'(?:learned|discovered|found out|realized|turns out)\s+(.+?)(?:\.|$)', re.IGNORECASE)
    LOOSE_TRIED = re.compile(r'(?:tried|attempted|tested)\s+(.+?)(?:\.|$)', re.IGNORECASE)
    LOOSE_BLOCKED = re.compile(r'(?:blocked|stuck|waiting)\s+(?:on|by)\s+(.+?)(?:\.|$)', re.IGNORECASE)

    def parse(self, content: str) -> ParsedMemory:
        """Parse MEMORY.md content into structured data.

        Handles both structured format and loose writing.
        """
        # Get project name from header
        header_match = self.HEADER_PATTERN.search(content)
        project_name = header_match.group(1) if header_match else "Unknown"

        # Extract project state
        project_state = self._extract_project_state(content)

        # Split by date headers (support both YYYY-MM-DD and "Dec 12" formats)
        entries = []
        date_matches = list(self.DATE_PATTERN.finditer(content))

        for i, match in enumerate(date_matches):
            # Get content until next date header or end
            start = match.end()
            end = date_matches[i + 1].start() if i + 1 < len(date_matches) else len(content)
            section_content = content[start:end].strip()

            # Remove --- separators from content
            section_content = re.sub(r'^---\s*$', '', section_content, flags=re.MULTILINE).strip()

            # Parse date - support both formats
            date_str = match.group(1) or match.group(2)  # YYYY-MM-DD or "Dec 12"
            try:
                if match.group(1):  # Full date
                    date = datetime.strptime(date_str, '%Y-%m-%d')
                else:  # Short date like "Dec 12"
                    # Assume current year
                    date = datetime.strptime(f"{date_str} {datetime.now().year}", '%b %d %Y')
            except ValueError:
                continue

            duration = match.group(3)  # e.g., "2 hours" or "Session 1"

            # Extract structured items (try structured format first)
            decisions = self._extract_items(section_content, self.DECIDED_PATTERN)
            problems = self._extract_items(section_content, self.PROBLEM_PATTERN)
            learnings = self._extract_items(section_content, self.LEARNED_PATTERN)
            next_steps = self._extract_items(section_content, self.NEXT_PATTERN)

            # Also extract from loose writing
            decisions.extend(self._extract_loose(section_content, self.LOOSE_DECIDED))
            problems.extend(self._extract_loose(section_content, self.LOOSE_PROBLEM))
            learnings.extend(self._extract_loose(section_content, self.LOOSE_LEARNED))

            # Deduplicate while preserving order
            decisions = list(dict.fromkeys(decisions))
            problems = list(dict.fromkeys(problems))
            learnings = list(dict.fromkeys(learnings))

            entries.append(MemoryEntry(
                date=date,
                duration=duration,
                content=self._clean_content(section_content),
                decisions=decisions,
                problems=problems,
                learnings=learnings,
                next_steps=next_steps,
                raw_text=section_content,
            ))

        return ParsedMemory(
            project_name=project_name,
            entries=entries,
            raw_content=content,
            project_state=project_state,
        )

    def _extract_project_state(self, content: str) -> ProjectState:
        """Extract project state from header sections."""
        state = ProjectState()

        # Extract Project State section
        state_match = self.PROJECT_STATE_PATTERN.search(content)
        if state_match:
            state_text = state_match.group(1)
            # Parse bullet points
            for line in state_text.split('\n'):
                line = line.strip()
                if line.startswith('- **Goal:**') or line.startswith('- Goal:'):
                    state.goal = re.sub(r'^-\s*\*?\*?Goal:\*?\*?\s*', '', line)
                elif line.startswith('- **Stack:**') or line.startswith('- Stack:'):
                    stack_str = re.sub(r'^-\s*\*?\*?Stack:\*?\*?\s*', '', line)
                    state.stack = [s.strip() for s in stack_str.split(',')]
                elif line.startswith('- **Status:**') or line.startswith('- Status:'):
                    state.status = re.sub(r'^-\s*\*?\*?Status:\*?\*?\s*', '', line)

        # Extract Gotchas section
        gotchas_match = self.GOTCHAS_PATTERN.search(content)
        if gotchas_match:
            gotchas_text = gotchas_match.group(1)
            state.gotchas = [
                line.lstrip('- ').strip()
                for line in gotchas_text.split('\n')
                if line.strip().startswith('-')
            ]

        # Extract Key Decisions section
        decisions_match = self.KEY_DECISIONS_PATTERN.search(content)
        if decisions_match:
            decisions_text = decisions_match.group(1)
            state.key_decisions = [
                line.lstrip('- ').strip()
                for line in decisions_text.split('\n')
                if line.strip().startswith('-')
            ]

        return state

    def _extract_items(self, content: str, pattern: re.Pattern) -> list[str]:
        """Extract items matching a pattern."""
        items = []
        for match in pattern.finditer(content):
            text = match.group(1).strip()
            # Clean up the text
            text = re.sub(r'\n\s*-\s*', '\n  - ', text)  # Preserve sub-bullets
            text = re.sub(r'\n\s+', ' ', text)  # Collapse other newlines
            if text:
                items.append(text)
        return items

    def _extract_loose(self, content: str, pattern: re.Pattern) -> list[str]:
        """Extract items from loose/natural language writing."""
        items = []
        for match in pattern.finditer(content):
            text = match.group(1).strip()
            # Only include if it's substantial (more than just a word)
            if text and len(text) > 10:
                items.append(text)
        return items

    def _clean_content(self, content: str) -> str:
        """Clean content by removing structured markers."""
        # Remove the **Decided:** etc markers for plain content
        clean = re.sub(r'\*\*(Decided|Problem|Learned):\*\*', '', content)
        return clean.strip()


class MemoryFileManager:
    """Manages MEMORY.md files for projects."""

    MEMORY_DIR = ".mind"
    MEMORY_FILE = "MEMORY.md"

    def __init__(self, parser: Optional[MemoryFileParser] = None):
        self.parser = parser or MemoryFileParser()
        self._cache: dict[str, tuple[float, ParsedMemory]] = {}  # path -> (mtime, parsed)

    def get_memory_path(self, repo_path: str | Path) -> Path:
        """Get the MEMORY.md path for a repo."""
        return Path(repo_path) / self.MEMORY_DIR / self.MEMORY_FILE

    def exists(self, repo_path: str | Path) -> bool:
        """Check if MEMORY.md exists for a repo."""
        return self.get_memory_path(repo_path).exists()

    def read(self, repo_path: str | Path) -> Optional[ParsedMemory]:
        """Read and parse MEMORY.md for a repo.

        Uses caching based on file modification time.
        """
        path = self.get_memory_path(repo_path)
        if not path.exists():
            return None

        # Check cache
        mtime = path.stat().st_mtime
        if str(path) in self._cache:
            cached_mtime, cached_parsed = self._cache[str(path)]
            if cached_mtime == mtime:
                return cached_parsed

        # Parse fresh
        content = path.read_text(encoding='utf-8')
        parsed = self.parser.parse(content)

        # Update cache
        self._cache[str(path)] = (mtime, parsed)

        return parsed

    def get_primer_context(self, repo_path: str | Path) -> Optional[str]:
        """Get context suitable for session primer from MEMORY.md.

        Returns a summary of recent activity and important items.
        """
        parsed = self.read(repo_path)
        if not parsed:
            return None

        lines = [f"# Memory from {parsed.project_name}"]

        # Recent entries (last 3)
        recent = parsed.entries[:3]
        if recent:
            lines.append("\n## Recent Sessions")
            for entry in recent:
                date_str = entry.date.strftime('%Y-%m-%d')
                duration_str = f" ({entry.duration})" if entry.duration else ""
                lines.append(f"\n### {date_str}{duration_str}")

                # First paragraph of content
                first_para = entry.content.split('\n\n')[0][:200]
                if first_para:
                    lines.append(first_para)

                # Key items
                if entry.decisions:
                    lines.append(f"\nDecisions: {len(entry.decisions)}")
                    for d in entry.decisions[:2]:
                        lines.append(f"  - {d[:100]}...")

                if entry.problems:
                    lines.append(f"\nProblems: {len(entry.problems)}")
                    for p in entry.problems[:2]:
                        lines.append(f"  - {p[:100]}...")

        # All learnings (important to carry forward)
        all_learnings = parsed.all_learnings
        if all_learnings:
            lines.append("\n## Key Learnings")
            for learning in all_learnings[-5:]:  # Last 5
                lines.append(f"- {learning[:150]}")

        # Latest next steps
        if recent and recent[0].next_steps:
            lines.append("\n## Next Steps (from last session)")
            for step in recent[0].next_steps:
                lines.append(f"- {step}")

        return '\n'.join(lines)

    def ensure_dir(self, repo_path: str | Path) -> Path:
        """Ensure .mind directory exists in repo."""
        mind_dir = Path(repo_path) / self.MEMORY_DIR
        mind_dir.mkdir(parents=True, exist_ok=True)
        return mind_dir

    def create_initial(self, repo_path: str | Path, project_name: str) -> Path:
        """Create initial MEMORY.md file for a new project."""
        self.ensure_dir(repo_path)
        path = self.get_memory_path(repo_path)

        if not path.exists():
            initial_content = f"# {project_name}\n\n"
            path.write_text(initial_content, encoding='utf-8')

        return path
