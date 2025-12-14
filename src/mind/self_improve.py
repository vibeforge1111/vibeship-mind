"""Self-improvement module - cross-project pattern learning for Mind.

This module handles parsing and managing SELF_IMPROVE.md, the global file
that stores patterns about the user across all projects:
- PREFERENCE: coding style, workflow, communication preferences
- SKILL: things you're good at in specific contexts
- BLIND_SPOT: things you consistently miss or forget
- ANTI_PATTERN: approaches that don't work for you
- FEEDBACK: raw corrections for pattern extraction
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from .storage import get_self_improve_path
from .templates import SELF_IMPROVE_TEMPLATE


class PatternType(Enum):
    """Types of self-improvement patterns."""
    PREFERENCE = "preference"
    SKILL = "skill"
    BLIND_SPOT = "blind_spot"
    ANTI_PATTERN = "anti_pattern"
    FEEDBACK = "feedback"


@dataclass
class Pattern:
    """A single self-improvement pattern."""
    type: PatternType
    category: str  # e.g., "coding", "workflow", "react:hooks"
    description: str
    confidence: float = 0.5  # 0.0 to 1.0, increases with occurrences
    occurrences: int = 1
    date_added: Optional[date] = None
    source_line: int = 0

    def __post_init__(self):
        if not self.date_added:
            self.date_added = date.today()


@dataclass
class SelfImproveData:
    """Parsed self-improvement data."""
    preferences: list[Pattern] = field(default_factory=list)
    skills: list[Pattern] = field(default_factory=list)
    blind_spots: list[Pattern] = field(default_factory=list)
    anti_patterns: list[Pattern] = field(default_factory=list)
    feedback: list[Pattern] = field(default_factory=list)

    def all_patterns(self) -> list[Pattern]:
        """Get all patterns as a flat list."""
        return (
            self.preferences +
            self.skills +
            self.blind_spots +
            self.anti_patterns +
            self.feedback
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "preferences": [
                {"category": p.category, "description": p.description, "confidence": p.confidence}
                for p in self.preferences
            ],
            "skills": [
                {"category": p.category, "description": p.description, "confidence": p.confidence}
                for p in self.skills
            ],
            "blind_spots": [
                {"category": p.category, "description": p.description, "confidence": p.confidence}
                for p in self.blind_spots
            ],
            "anti_patterns": [
                {"category": p.category, "description": p.description, "confidence": p.confidence}
                for p in self.anti_patterns
            ],
            "feedback": [
                {"category": p.category, "description": p.description, "date": str(p.date_added)}
                for p in self.feedback
            ],
        }


class SelfImproveParser:
    """Parser for SELF_IMPROVE.md file."""

    # Patterns for each type
    # PREFERENCE: [category] description
    PREFERENCE_PATTERN = re.compile(
        r"^(?:-\s*)?PREFERENCE:\s*\[([^\]]+)\]\s*(.+)$",
        re.IGNORECASE | re.MULTILINE
    )

    # SKILL: [stack:context] description
    SKILL_PATTERN = re.compile(
        r"^(?:-\s*)?SKILL:\s*\[([^\]]+)\]\s*(.+)$",
        re.IGNORECASE | re.MULTILINE
    )

    # BLIND_SPOT: [category] description
    BLIND_SPOT_PATTERN = re.compile(
        r"^(?:-\s*)?BLIND_SPOT:\s*\[([^\]]+)\]\s*(.+)$",
        re.IGNORECASE | re.MULTILINE
    )

    # ANTI_PATTERN: [category] description
    ANTI_PATTERN_PATTERN = re.compile(
        r"^(?:-\s*)?ANTI_PATTERN:\s*\[([^\]]+)\]\s*(.+)$",
        re.IGNORECASE | re.MULTILINE
    )

    # FEEDBACK: [date] context -> correction
    FEEDBACK_PATTERN = re.compile(
        r"^(?:-\s*)?FEEDBACK:\s*\[([^\]]+)\]\s*(.+)$",
        re.IGNORECASE | re.MULTILINE
    )

    def parse(self, content: str) -> SelfImproveData:
        """Parse SELF_IMPROVE.md content into structured data."""
        data = SelfImproveData()

        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith("<!--") or line.startswith("#"):
                continue

            # Try each pattern type
            if match := self.PREFERENCE_PATTERN.match(line):
                data.preferences.append(Pattern(
                    type=PatternType.PREFERENCE,
                    category=match.group(1).strip(),
                    description=match.group(2).strip(),
                    source_line=i,
                ))
            elif match := self.SKILL_PATTERN.match(line):
                data.skills.append(Pattern(
                    type=PatternType.SKILL,
                    category=match.group(1).strip(),
                    description=match.group(2).strip(),
                    source_line=i,
                ))
            elif match := self.BLIND_SPOT_PATTERN.match(line):
                data.blind_spots.append(Pattern(
                    type=PatternType.BLIND_SPOT,
                    category=match.group(1).strip(),
                    description=match.group(2).strip(),
                    source_line=i,
                ))
            elif match := self.ANTI_PATTERN_PATTERN.match(line):
                data.anti_patterns.append(Pattern(
                    type=PatternType.ANTI_PATTERN,
                    category=match.group(1).strip(),
                    description=match.group(2).strip(),
                    source_line=i,
                ))
            elif match := self.FEEDBACK_PATTERN.match(line):
                # Parse date from category field for feedback
                date_str = match.group(1).strip()
                try:
                    parsed_date = date.fromisoformat(date_str)
                except ValueError:
                    parsed_date = date.today()

                data.feedback.append(Pattern(
                    type=PatternType.FEEDBACK,
                    category=date_str,
                    description=match.group(2).strip(),
                    date_added=parsed_date,
                    source_line=i,
                ))

        return data


def load_self_improve() -> SelfImproveData:
    """Load and parse the global SELF_IMPROVE.md file.

    Returns empty data if file doesn't exist.
    """
    path = get_self_improve_path()
    if not path.exists():
        return SelfImproveData()

    content = path.read_text(encoding="utf-8")
    parser = SelfImproveParser()
    return parser.parse(content)


def ensure_self_improve_exists() -> Path:
    """Ensure SELF_IMPROVE.md exists, creating it if necessary.

    Returns the path to the file.
    """
    path = get_self_improve_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(SELF_IMPROVE_TEMPLATE)
    return path


def append_pattern(pattern_type: PatternType, category: str, description: str) -> bool:
    """Append a new pattern to SELF_IMPROVE.md.

    Args:
        pattern_type: Type of pattern (PREFERENCE, SKILL, etc.)
        category: Category/context for the pattern
        description: Description of the pattern

    Returns:
        True if successful, False otherwise.
    """
    path = ensure_self_improve_exists()
    content = path.read_text(encoding="utf-8")

    # Format the entry
    type_str = pattern_type.value.upper()
    if pattern_type == PatternType.FEEDBACK:
        category = date.today().isoformat()

    entry = f"{type_str}: [{category}] {description}\n"

    # Find the appropriate section
    section_map = {
        PatternType.PREFERENCE: "## Preferences",
        PatternType.SKILL: "## Skills",
        PatternType.BLIND_SPOT: "## Blind Spots",
        PatternType.ANTI_PATTERN: "## Anti-Patterns",
        PatternType.FEEDBACK: "## Feedback Log",
    }

    section_header = section_map.get(pattern_type)
    if not section_header:
        return False

    # Find section and insert after header
    pattern = rf"({re.escape(section_header)}\s*\n(?:<!--[^>]*-->\s*\n)?)"
    match = re.search(pattern, content)

    if match:
        insert_pos = match.end()
        new_content = content[:insert_pos] + entry + content[insert_pos:]
    else:
        # Section not found, append at end
        new_content = content.rstrip() + f"\n\n{section_header}\n{entry}"

    path.write_text(new_content, encoding="utf-8")
    return True


def append_feedback(context: str, correction: str) -> bool:
    """Append a feedback entry to SELF_IMPROVE.md.

    Args:
        context: What was happening when correction was made
        correction: What the correct approach/answer was

    Returns:
        True if successful, False otherwise.
    """
    description = f"{context} -> {correction}"
    return append_pattern(PatternType.FEEDBACK, "", description)


def get_patterns_for_stack(data: SelfImproveData, stack: list[str]) -> dict:
    """Filter patterns relevant to the given tech stack.

    Args:
        data: Parsed self-improvement data
        stack: List of technologies (e.g., ["python", "fastapi", "postgresql"])

    Returns:
        Dictionary with filtered patterns.
    """
    stack_lower = set(s.lower() for s in stack)

    # Categories that are always relevant regardless of stack
    universal_categories = {
        "general", "workflow", "communication", "coding",
        "testing", "security", "architecture", "documentation",
        "debugging", "performance", "error-handling", "design",
    }

    def is_relevant(pattern: Pattern, include_warnings: bool = False) -> bool:
        """Check if a pattern is relevant to the stack.

        Args:
            pattern: The pattern to check
            include_warnings: If True, always include (for blind spots/anti-patterns)
        """
        cat_lower = pattern.category.lower()

        # Universal categories are always relevant
        if cat_lower in universal_categories:
            return True

        # Check if category matches any stack item
        if any(s in cat_lower or cat_lower in s for s in stack_lower):
            return True

        # For warnings (blind spots, anti-patterns), be more inclusive
        if include_warnings:
            return True

        return False

    return {
        "preferences": [p for p in data.preferences if is_relevant(p)],
        "skills": [p for p in data.skills if is_relevant(p)],
        # Blind spots and anti-patterns are warnings - always include them
        "blind_spots": [p for p in data.blind_spots if is_relevant(p, include_warnings=True)],
        "anti_patterns": [p for p in data.anti_patterns if is_relevant(p, include_warnings=True)],
    }


def generate_intuition_context(data: SelfImproveData, stack: list[str]) -> str:
    """Generate context string for Claude from self-improvement data.

    This creates a concise summary that can be injected into MIND:CONTEXT.

    Args:
        data: Parsed self-improvement data
        stack: Current project's tech stack

    Returns:
        Formatted context string.
    """
    relevant = get_patterns_for_stack(data, stack)

    lines = []

    # Add preferences (top 3)
    if relevant["preferences"]:
        lines.append("## Your Preferences")
        for p in relevant["preferences"][:3]:
            lines.append(f"- [{p.category}] {p.description}")

    # Add skills (top 3)
    if relevant["skills"]:
        lines.append("\n## Your Skills")
        for p in relevant["skills"][:3]:
            lines.append(f"- [{p.category}] {p.description}")

    # Add blind spots - these are warnings (all of them, they're important)
    if relevant["blind_spots"]:
        lines.append("\n## Watch Out (Your Blind Spots)")
        for p in relevant["blind_spots"]:
            lines.append(f"- [{p.category}] {p.description}")

    # Add anti-patterns - these are warnings (all of them, they're important)
    if relevant["anti_patterns"]:
        lines.append("\n## Avoid (Your Anti-Patterns)")
        for p in relevant["anti_patterns"]:
            lines.append(f"- [{p.category}] {p.description}")

    return "\n".join(lines) if lines else ""
