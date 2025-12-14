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
    LEARNING_STYLE = "learning_style"  # Phase 9: How user learns best


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
    learning_styles: list[Pattern] = field(default_factory=list)

    def all_patterns(self) -> list[Pattern]:
        """Get all patterns as a flat list."""
        return (
            self.preferences +
            self.skills +
            self.blind_spots +
            self.anti_patterns +
            self.feedback +
            self.learning_styles
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
            "learning_styles": [
                {"category": p.category, "description": p.description, "confidence": p.confidence}
                for p in self.learning_styles
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

    # LEARNING_STYLE: [context] description (Phase 9)
    LEARNING_STYLE_PATTERN = re.compile(
        r"^(?:-\s*)?LEARNING_STYLE:\s*\[([^\]]+)\]\s*(.+)$",
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
            elif match := self.LEARNING_STYLE_PATTERN.match(line):
                data.learning_styles.append(Pattern(
                    type=PatternType.LEARNING_STYLE,
                    category=match.group(1).strip(),
                    description=match.group(2).strip(),
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


def generate_intuition_context(
    data: SelfImproveData,
    stack: list[str],
    min_confidence: float = 0.3
) -> str:
    """Generate context string for Claude from self-improvement data.

    This creates a concise summary that can be injected into MIND:CONTEXT.
    Patterns with low confidence (stale/unused) are filtered out.

    Args:
        data: Parsed self-improvement data
        stack: Current project's tech stack
        min_confidence: Minimum confidence threshold (Phase 6 decay)

    Returns:
        Formatted context string.
    """
    relevant = get_patterns_for_stack(data, stack)

    # Phase 6: Filter by confidence - stale patterns don't get surfaced
    def filter_confident(patterns: list[Pattern]) -> list[Pattern]:
        """Filter patterns by decayed confidence threshold."""
        result = []
        for p in patterns:
            confidence = get_pattern_confidence(p)
            if confidence >= min_confidence:
                result.append(p)
        return result

    lines = []

    # Add preferences (top 3, filtered by confidence)
    confident_prefs = filter_confident(relevant["preferences"])
    if confident_prefs:
        lines.append("## Your Preferences")
        for p in confident_prefs[:3]:
            lines.append(f"- [{p.category}] {p.description}")

    # Add skills (top 3, filtered by confidence)
    confident_skills = filter_confident(relevant["skills"])
    if confident_skills:
        lines.append("\n## Your Skills")
        for p in confident_skills[:3]:
            lines.append(f"- [{p.category}] {p.description}")

    # Add blind spots - these are warnings (all of them, they're important)
    # Still filter by confidence but with lower threshold for warnings
    confident_blinds = filter_confident(relevant["blind_spots"])
    if confident_blinds:
        lines.append("\n## Watch Out (Your Blind Spots)")
        for p in confident_blinds:
            lines.append(f"- [{p.category}] {p.description}")

    # Add anti-patterns - these are warnings (all of them, they're important)
    confident_antis = filter_confident(relevant["anti_patterns"])
    if confident_antis:
        lines.append("\n## Avoid (Your Anti-Patterns)")
        for p in confident_antis:
            lines.append(f"- [{p.category}] {p.description}")

    # Phase 9: Add learning styles
    if data.learning_styles:
        confident_styles = filter_confident(data.learning_styles)
        if confident_styles:
            lines.append("\n## How You Learn Best")
            for ls in confident_styles:
                lines.append(f"- **{ls.category}**: {ls.description}")
            lines.append("\n_Adapt explanations to match these preferences._")

    return "\n".join(lines) if lines else ""


# =============================================================================
# Phase 2: Pattern Radar - Proactive Intuition Detection
# =============================================================================


@dataclass
class Intuition:
    """A proactive warning or tip based on learned patterns."""
    type: str  # "watch", "avoid", "tip"
    message: str
    source_pattern: str  # Which pattern triggered this
    confidence: float


def detect_intuitions(
    session_context: str,
    data: SelfImproveData,
    project_stack: list[str]
) -> list[Intuition]:
    """Scan current context for patterns that should trigger warnings.

    This is the "Pattern Radar" - it scans what the user is working on
    and proactively surfaces relevant warnings based on their blind spots,
    anti-patterns, and skills.

    Args:
        session_context: Current SESSION.md content + recent activity
        data: Parsed SELF_IMPROVE.md data
        project_stack: Detected stack tags for this project

    Returns:
        List of intuitions to surface to the user (max 5)
    """
    intuitions = []
    context_lower = session_context.lower()

    # Check blind spots - these are WATCH warnings
    for blind_spot in data.blind_spots:
        triggers = _extract_triggers(blind_spot.category, blind_spot.description)
        for trigger in triggers:
            if trigger.lower() in context_lower:
                intuitions.append(Intuition(
                    type="watch",
                    message=f"You tend to: {blind_spot.description}",
                    source_pattern=f"BLIND_SPOT: [{blind_spot.category}]",
                    confidence=0.8
                ))
                break  # One match per blind spot

    # Check anti-patterns - these are AVOID warnings
    for anti_pattern in data.anti_patterns:
        triggers = _extract_triggers(anti_pattern.category, anti_pattern.description)
        for trigger in triggers:
            if trigger.lower() in context_lower:
                intuitions.append(Intuition(
                    type="avoid",
                    message=f"Watch out: {anti_pattern.description}",
                    source_pattern=f"ANTI_PATTERN: [{anti_pattern.category}]",
                    confidence=0.7
                ))
                break

    # Check skills - these are TIP suggestions (only for matching stack)
    stack_lower = [s.lower() for s in project_stack]
    for skill in data.skills:
        # Check if skill is relevant to current stack
        skill_stack = skill.category.split(':')[0].lower()
        if skill_stack in stack_lower or skill_stack in {"general", "workflow"}:
            # Check if context suggests this skill applies
            skill_triggers = _extract_triggers(skill.category, skill.description)
            for trigger in skill_triggers:
                if trigger.lower() in context_lower:
                    intuitions.append(Intuition(
                        type="tip",
                        message=f"Remember: {skill.description}",
                        source_pattern=f"SKILL: [{skill.category}]",
                        confidence=0.6
                    ))
                    break

    # Dedupe by message
    seen = set()
    unique = []
    for i in intuitions:
        if i.message not in seen:
            seen.add(i.message)
            unique.append(i)

    # Return top 5 by confidence
    return sorted(unique, key=lambda x: x.confidence, reverse=True)[:5]


def _extract_triggers(category: str, description: str) -> list[str]:
    """Extract trigger words from a pattern.

    E.g., "[error-handling] forgets network timeouts"
    -> ["error", "handling", "network", "timeout", "api", "fetch"]
    """
    triggers = []

    # From category - split on common delimiters
    triggers.extend(category.replace('-', ' ').replace(':', ' ').replace('_', ' ').split())

    # From description - extract key words (4+ chars, not stop words)
    stop_words = {
        'this', 'that', 'with', 'from', 'have', 'been', 'were', 'they',
        'when', 'what', 'which', 'where', 'will', 'would', 'could', 'should',
        'your', 'their', 'about', 'there', 'here', 'some', 'more', 'also',
        'just', 'only', 'than', 'then', 'very', 'much', 'most', 'other',
        'into', 'over', 'after', 'before', 'between', 'through', 'during',
        'tend', 'tends', 'forget', 'forgets', 'sometimes', 'often', 'always',
    }
    words = re.findall(r'\b\w{4,}\b', description.lower())
    triggers.extend([w for w in words if w not in stop_words])

    # Add common related terms for better matching
    related = {
        'api': ['fetch', 'request', 'endpoint', 'http', 'rest', 'graphql'],
        'auth': ['login', 'token', 'session', 'password', 'oauth', 'jwt'],
        'error': ['catch', 'exception', 'handling', 'throw', 'fail'],
        'test': ['jest', 'pytest', 'spec', 'assert', 'mock', 'unit'],
        'async': ['await', 'promise', 'callback', 'concurrent'],
        'database': ['sql', 'query', 'migration', 'schema', 'postgres', 'mysql'],
        'security': ['validation', 'sanitize', 'xss', 'injection', 'csrf'],
        'performance': ['optimize', 'cache', 'lazy', 'memo', 'index'],
        'type': ['typescript', 'typing', 'hints', 'annotation'],
    }
    for trigger in list(triggers):
        if trigger in related:
            triggers.extend(related[trigger])

    return list(set(triggers))


def format_intuitions_for_context(intuitions: list[Intuition]) -> str:
    """Format intuitions for injection into MIND:CONTEXT.

    Args:
        intuitions: List of detected intuitions

    Returns:
        Formatted string for context injection
    """
    if not intuitions:
        return ""

    lines = ["## Intuition (Pattern Radar)", "", "Based on your patterns:"]

    type_prefix = {
        "watch": "WATCH",
        "avoid": "AVOID",
        "tip": "TIP"
    }

    for i in intuitions:
        prefix = type_prefix.get(i.type, "NOTE")
        lines.append(f"- **{prefix}**: {i.message}")

    lines.append("")
    return "\n".join(lines)


# =============================================================================
# Phase 3: Feedback Capture - Pattern Extraction
# =============================================================================


def extract_patterns_from_feedback(
    feedback_entries: list[Pattern],
    min_occurrences: int = 3
) -> list[tuple[str, str, str]]:
    """Extract patterns from accumulated feedback.

    Looks for repeated themes in feedback to identify:
    - Preferences (consistent style choices)
    - Blind spots (repeated mistakes)
    - Anti-patterns (approaches that don't work)

    Args:
        feedback_entries: List of FEEDBACK patterns from SELF_IMPROVE.md
        min_occurrences: Minimum times a pattern must appear

    Returns:
        List of (type, category, description) tuples for new patterns
    """
    from collections import Counter

    if len(feedback_entries) < min_occurrences:
        return []

    # Extract themes from feedback descriptions
    themes: Counter = Counter()
    category_themes: dict[str, str] = {}

    for fb in feedback_entries:
        desc = fb.description.lower()

        # Look for common correction patterns
        if "->" in desc:
            parts = desc.split("->", 1)
            original = parts[0].strip()
            correction = parts[1].strip() if len(parts) > 1 else ""

            # Style preferences
            if any(w in correction for w in ["single", "double", "quotes"]):
                themes["style:quotes"] += 1
                category_themes["style:quotes"] = correction

            if any(w in correction for w in ["simple", "simpler", "less complex", "minimal"]):
                themes["approach:simplicity"] += 1
                category_themes["approach:simplicity"] = "prefers simpler solutions"

            if any(w in correction for w in ["detailed", "more thorough", "comprehensive"]):
                themes["approach:detail"] += 1
                category_themes["approach:detail"] = "prefers detailed solutions"

            # Type hints / documentation
            if any(w in correction for w in ["type hint", "typing", "annotation"]):
                themes["style:type_hints"] += 1
                category_themes["style:type_hints"] = "prefers type hints"

            if any(w in correction for w in ["docstring", "comment", "document"]):
                themes["style:documentation"] += 1
                category_themes["style:documentation"] = "prefers documentation"

            # Error handling patterns
            if any(w in original for w in ["error", "catch", "try", "exception", "handling"]):
                themes["blind_spot:error_handling"] += 1
                category_themes["blind_spot:error_handling"] = "tends to skip error handling"

            # Validation patterns
            if any(w in original for w in ["valid", "check", "sanitize", "input"]):
                themes["blind_spot:validation"] += 1
                category_themes["blind_spot:validation"] = "tends to skip input validation"

            # Over-engineering
            if any(w in correction for w in ["overkill", "yagni", "too much", "unnecessary"]):
                themes["anti_pattern:overengineering"] += 1
                category_themes["anti_pattern:overengineering"] = "tends to over-engineer"

            # Under-engineering
            if any(w in correction for w in ["too simple", "not enough", "missing"]):
                themes["anti_pattern:underengineering"] += 1
                category_themes["anti_pattern:underengineering"] = "tends to under-engineer"

    # Extract patterns that meet threshold
    new_patterns = []
    for theme, count in themes.items():
        if count >= min_occurrences:
            parts = theme.split(":", 1)
            if len(parts) != 2:
                continue
            pattern_type, category = parts
            description = category_themes.get(theme, category)

            # Map to actual types
            type_map = {
                "style": "preference",
                "approach": "preference",
                "blind_spot": "blind_spot",
                "anti_pattern": "anti_pattern"
            }
            actual_type = type_map.get(pattern_type, "preference")

            new_patterns.append((actual_type, category, description))

    return new_patterns


def promote_extracted_patterns(new_patterns: list[tuple[str, str, str]]) -> int:
    """Add extracted patterns to SELF_IMPROVE.md.

    Args:
        new_patterns: List of (type, category, description) tuples

    Returns:
        Number of patterns added.
    """
    if not new_patterns:
        return 0

    path = get_self_improve_path()
    if not path.exists():
        return 0

    content = path.read_text(encoding="utf-8")
    added = 0

    for pattern_type, category, description in new_patterns:
        # Skip if description already exists (avoid duplicates)
        if description.lower() in content.lower():
            continue

        # Use append_pattern which handles section finding
        ptype_map = {
            "preference": PatternType.PREFERENCE,
            "blind_spot": PatternType.BLIND_SPOT,
            "anti_pattern": PatternType.ANTI_PATTERN,
            "skill": PatternType.SKILL,
        }
        ptype = ptype_map.get(pattern_type)
        if ptype and append_pattern(ptype, category, description):
            added += 1

    return added


def process_feedback_for_patterns(min_occurrences: int = 3) -> int:
    """Process feedback log and extract new patterns.

    Call this periodically (e.g., on session end) to promote
    repeated feedback into permanent patterns.

    Args:
        min_occurrences: Minimum times a theme must appear

    Returns:
        Number of new patterns created.
    """
    data = load_self_improve()

    if len(data.feedback) < min_occurrences:
        return 0

    new_patterns = extract_patterns_from_feedback(data.feedback, min_occurrences)
    return promote_extracted_patterns(new_patterns)


# =============================================================================
# Phase 6: Confidence Decay - Patterns lose confidence over time
# Phase 7: Reinforcement Tracking - Patterns gain confidence when used
# =============================================================================

import hashlib
import json
from datetime import timedelta
from typing import Dict

from .storage import get_global_mind_dir


@dataclass
class PatternMetadata:
    """Metadata for tracking pattern lifecycle.

    Stored in ~/.mind/pattern_metadata.json alongside SELF_IMPROVE.md.
    Tracks when patterns were created, last reinforced, and their confidence.
    """
    pattern_hash: str  # MD5 hash of normalized description (first 12 chars)
    created_at: str  # ISO format datetime
    last_reinforced: str  # ISO format datetime
    reinforcement_count: int = 0
    base_confidence: float = 0.5  # Starting confidence for new patterns

    def current_confidence(
        self,
        decay_rate: float = 0.1,
        decay_period_days: int = 30
    ) -> float:
        """Get confidence with decay applied.

        Args:
            decay_rate: How much to decay per period (default 10%)
            decay_period_days: Days per decay period (default 30)

        Returns:
            Decayed confidence, minimum 0.1
        """
        last = datetime.fromisoformat(self.last_reinforced)
        return calculate_decayed_confidence(
            self.base_confidence,
            last,
            decay_rate,
            decay_period_days
        )


def calculate_decayed_confidence(
    base_confidence: float,
    last_reinforced: datetime,
    decay_rate: float = 0.1,
    decay_period_days: int = 30
) -> float:
    """Calculate confidence after time-based decay.

    The decay formula: confidence * (1 - decay_rate) ^ periods

    Examples:
        - 30 days inactive: 0.8 * 0.9^1 = 0.72
        - 60 days inactive: 0.8 * 0.9^2 = 0.648
        - 90 days inactive: 0.8 * 0.9^3 = 0.583

    Args:
        base_confidence: Original confidence (0.0 to 1.0)
        last_reinforced: When pattern was last used/reinforced
        decay_rate: How much to decay per period (default 10%)
        decay_period_days: Days per decay period (default 30)

    Returns:
        Decayed confidence, minimum 0.1 (patterns never fully disappear)
    """
    days_since = (datetime.now() - last_reinforced).days

    if days_since < decay_period_days:
        return base_confidence

    decay_periods = days_since // decay_period_days
    decayed = base_confidence * ((1 - decay_rate) ** decay_periods)

    return max(0.1, decayed)


def hash_pattern_description(description: str) -> str:
    """Create stable hash for pattern matching.

    Used to identify patterns across sessions without storing full text.

    Args:
        description: The pattern description text

    Returns:
        12-character MD5 hash of normalized description
    """
    normalized = description.lower().strip()
    return hashlib.md5(normalized.encode()).hexdigest()[:12]


def get_pattern_metadata_path() -> Path:
    """Get path to pattern_metadata.json."""
    return get_global_mind_dir() / "pattern_metadata.json"


def load_pattern_metadata() -> Dict[str, PatternMetadata]:
    """Load pattern metadata from state file.

    Returns:
        Dictionary mapping pattern_hash -> PatternMetadata
    """
    path = get_pattern_metadata_path()
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        result = {}
        for k, v in data.get("patterns", {}).items():
            result[k] = PatternMetadata(
                pattern_hash=v.get("pattern_hash", k),
                created_at=v.get("created_at", datetime.now().isoformat()),
                last_reinforced=v.get("last_reinforced", datetime.now().isoformat()),
                reinforcement_count=v.get("reinforcement_count", 0),
                base_confidence=v.get("base_confidence", 0.5),
            )
        return result
    except (json.JSONDecodeError, TypeError, KeyError):
        return {}


def save_pattern_metadata(metadata: Dict[str, PatternMetadata]) -> None:
    """Save pattern metadata to state file.

    Args:
        metadata: Dictionary mapping pattern_hash -> PatternMetadata
    """
    path = get_pattern_metadata_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "patterns": {
            k: {
                "pattern_hash": v.pattern_hash,
                "created_at": v.created_at,
                "last_reinforced": v.last_reinforced,
                "reinforcement_count": v.reinforcement_count,
                "base_confidence": v.base_confidence,
            }
            for k, v in metadata.items()
        },
        "last_updated": datetime.now().isoformat(),
        "schema_version": 1,
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def ensure_pattern_metadata(pattern: Pattern) -> PatternMetadata:
    """Ensure a pattern has metadata, creating if needed.

    Args:
        pattern: The Pattern to ensure metadata for

    Returns:
        PatternMetadata for the pattern
    """
    metadata = load_pattern_metadata()
    pattern_hash = hash_pattern_description(pattern.description)

    if pattern_hash not in metadata:
        now = datetime.now().isoformat()
        metadata[pattern_hash] = PatternMetadata(
            pattern_hash=pattern_hash,
            created_at=now,
            last_reinforced=now,
            reinforcement_count=0,
            base_confidence=0.5,
        )
        save_pattern_metadata(metadata)

    return metadata[pattern_hash]


def reinforce_pattern(description: str, boost: float = 0.1) -> dict:
    """Reinforce a pattern, boosting its confidence.

    Called when a pattern is used and helps the user. This:
    1. Updates last_reinforced to now (resets decay clock)
    2. Increments reinforcement_count
    3. Boosts base_confidence by boost amount (capped at 1.0)

    Args:
        description: The pattern description to reinforce
        boost: How much to increase confidence (default 10%)

    Returns:
        Dict with success status and updated metadata
    """
    metadata = load_pattern_metadata()
    pattern_hash = hash_pattern_description(description)

    if pattern_hash not in metadata:
        # Pattern not tracked yet, create it
        now = datetime.now().isoformat()
        metadata[pattern_hash] = PatternMetadata(
            pattern_hash=pattern_hash,
            created_at=now,
            last_reinforced=now,
            reinforcement_count=1,
            base_confidence=min(1.0, 0.5 + boost),
        )
    else:
        # Update existing pattern
        pattern_meta = metadata[pattern_hash]
        pattern_meta.last_reinforced = datetime.now().isoformat()
        pattern_meta.reinforcement_count += 1
        pattern_meta.base_confidence = min(1.0, pattern_meta.base_confidence + boost)

    save_pattern_metadata(metadata)

    return {
        "success": True,
        "pattern_hash": pattern_hash,
        "reinforcement_count": metadata[pattern_hash].reinforcement_count,
        "new_confidence": metadata[pattern_hash].base_confidence,
    }


def get_pattern_confidence(pattern: Pattern) -> float:
    """Get the current (decayed) confidence for a pattern.

    Args:
        pattern: The Pattern to get confidence for

    Returns:
        Current confidence after decay (0.1 to 1.0)
    """
    metadata = load_pattern_metadata()
    pattern_hash = hash_pattern_description(pattern.description)

    if pattern_hash not in metadata:
        # New pattern, use default confidence from pattern itself
        return pattern.confidence

    return metadata[pattern_hash].current_confidence()


def filter_by_confidence(
    patterns: list[Pattern],
    min_confidence: float = 0.3
) -> list[Pattern]:
    """Filter out patterns below confidence threshold.

    Used to prevent stale patterns from being surfaced.

    Args:
        patterns: List of patterns to filter
        min_confidence: Minimum confidence to include (default 0.3)

    Returns:
        Filtered list of patterns above threshold
    """
    return [
        p for p in patterns
        if get_pattern_confidence(p) >= min_confidence
    ]


def get_confidence_stats() -> dict:
    """Get statistics about pattern confidence distribution.

    Useful for debugging and understanding pattern health.

    Returns:
        Dict with confidence statistics
    """
    metadata = load_pattern_metadata()

    if not metadata:
        return {
            "total_patterns": 0,
            "avg_confidence": 0,
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0,
        }

    confidences = [m.current_confidence() for m in metadata.values()]

    return {
        "total_patterns": len(metadata),
        "avg_confidence": sum(confidences) / len(confidences),
        "high_confidence": len([c for c in confidences if c >= 0.7]),
        "medium_confidence": len([c for c in confidences if 0.3 <= c < 0.7]),
        "low_confidence": len([c for c in confidences if c < 0.3]),
    }


# =============================================================================
# Phase 8: Contradiction Detection - Detect conflicting patterns
# =============================================================================


def extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from text.

    Args:
        text: The text to extract keywords from

    Returns:
        List of keywords (4+ chars, no stop words)
    """
    # Stop words to filter out
    stop_words = {
        'this', 'that', 'with', 'from', 'have', 'been', 'like', 'prefer',
        'when', 'what', 'which', 'there', 'their', 'about', 'would', 'could',
        'should', 'very', 'just', 'only', 'some', 'more', 'also', 'into',
    }

    # Extract words 4+ chars
    words = re.findall(r'\b\w{4,}\b', text.lower())
    return [w for w in words if w not in stop_words]


def jaccard_similarity(set1: set, set2: set) -> float:
    """Calculate Jaccard similarity between two sets.

    Args:
        set1: First set of keywords
        set2: Second set of keywords

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not set1 or not set2:
        return 0.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    return intersection / union if union > 0 else 0.0


def find_similar_patterns(
    new_description: str,
    existing_patterns: list[Pattern],
    similarity_threshold: float = 0.4
) -> list[tuple[Pattern, float]]:
    """Find patterns similar to the new one.

    Uses Jaccard similarity on keyword overlap (no embeddings needed).

    Args:
        new_description: Description of the new pattern
        existing_patterns: List of existing patterns to compare against
        similarity_threshold: Minimum similarity to include (default 0.4)

    Returns:
        List of (pattern, similarity_score) tuples, sorted by similarity
    """
    new_keywords = set(extract_keywords(new_description))

    if not new_keywords:
        return []

    similar = []
    for pattern in existing_patterns:
        existing_keywords = set(extract_keywords(pattern.description))

        if not existing_keywords:
            continue

        similarity = jaccard_similarity(new_keywords, existing_keywords)

        if similarity >= similarity_threshold:
            similar.append((pattern, similarity))

    return sorted(similar, key=lambda x: x[1], reverse=True)


# Opposing word pairs for contradiction detection
OPPOSING_PAIRS = [
    ('prefer', 'avoid'),
    ('like', 'dislike'),
    ('always', 'never'),
    ('use', "don't use"),
    ('use', 'dont use'),
    ('simple', 'complex'),
    ('verbose', 'terse'),
    ('detailed', 'brief'),
    ('short', 'long'),
    ('minimal', 'comprehensive'),
    ('functional', 'object-oriented'),
    ('mutable', 'immutable'),
    ('sync', 'async'),
    ('monolith', 'microservice'),
    ('class', 'function'),
    ('explicit', 'implicit'),
    ('strict', 'lenient'),
]


def detect_contradiction(
    new_pattern: Pattern,
    similar_pattern: Pattern
) -> bool:
    """Check if two similar patterns contradict each other.

    Looks for opposing signals in the pattern descriptions.

    Args:
        new_pattern: The new pattern being added
        similar_pattern: An existing similar pattern

    Returns:
        True if patterns contradict each other
    """
    new_lower = new_pattern.description.lower()
    existing_lower = similar_pattern.description.lower()

    for pos, neg in OPPOSING_PAIRS:
        # Check if one has positive and other has negative
        new_has_pos = pos in new_lower
        new_has_neg = neg in new_lower
        existing_has_pos = pos in existing_lower
        existing_has_neg = neg in existing_lower

        # Contradiction: one prefers X, other avoids X
        if (new_has_pos and existing_has_neg) or (new_has_neg and existing_has_pos):
            return True

    return False


def find_contradictions(
    new_description: str,
    pattern_type: PatternType,
    existing_patterns: list[Pattern]
) -> list[dict]:
    """Find patterns that contradict the new one.

    Args:
        new_description: Description of the new pattern
        pattern_type: Type of the new pattern
        existing_patterns: List of existing patterns to check

    Returns:
        List of dicts describing contradictions found
    """
    # Create temporary pattern for comparison
    new_pattern = Pattern(
        type=pattern_type,
        category="temp",
        description=new_description
    )

    # Find similar patterns
    similar = find_similar_patterns(new_description, existing_patterns)

    # Check each similar pattern for contradictions
    contradictions = []
    for pattern, similarity in similar:
        if detect_contradiction(new_pattern, pattern):
            contradictions.append({
                "pattern": pattern.description,
                "type": pattern.type.value,
                "category": pattern.category,
                "similarity": round(similarity, 2),
            })

    return contradictions


def add_pattern_with_contradiction_check(
    pattern_type: PatternType,
    category: str,
    description: str
) -> dict:
    """Add a pattern, checking for contradictions first.

    Args:
        pattern_type: Type of pattern (PREFERENCE, SKILL, etc.)
        category: Category tag like [coding], [python], etc.
        description: The pattern description

    Returns:
        Dict with:
        - success: bool
        - action: "added" | "contradiction_detected" | "duplicate"
        - conflicts: list of conflicting patterns (if any)
        - suggestion: guidance on resolving conflicts
    """
    data = load_self_improve()
    all_patterns = data.all_patterns()

    # Check for exact duplicate
    for pattern in all_patterns:
        if pattern.description.lower().strip() == description.lower().strip():
            return {
                "success": False,
                "action": "duplicate",
                "message": "This exact pattern already exists",
            }

    # Check for contradictions
    contradictions = find_contradictions(description, pattern_type, all_patterns)

    if contradictions:
        return {
            "success": False,
            "action": "contradiction_detected",
            "conflicts": contradictions,
            "suggestion": (
                "Resolve conflict before adding. Options:\n"
                "1. Use mind_log type='reinforce' on the correct pattern\n"
                "2. Manually remove the outdated pattern from SELF_IMPROVE.md\n"
                "3. Update the existing pattern's description"
            ),
        }

    # No contradictions, safe to add
    success = append_pattern(pattern_type, category, description)

    if success:
        return {"success": True, "action": "added"}
    else:
        return {"success": False, "action": "failed", "message": "Failed to append pattern"}


# =============================================================================
# Phase 9: Learning Style - Model HOW user learns, not just WHAT
# =============================================================================

from collections import Counter

# Indicators for detecting learning style from feedback
LEARNING_STYLE_INDICATORS = {
    # How they want concepts explained
    "concepts:example_first": [
        "show me", "give example", "can you demonstrate", "what does this look like",
        "show an example", "concrete example", "for example"
    ],
    "concepts:theory_first": [
        "why does", "how does", "explain the", "what's the reason",
        "understand why", "explain why", "tell me why"
    ],
    # Communication preferences
    "communication:terse": [
        "too much", "too long", "shorter", "brief", "tldr", "just tell me",
        "get to the point", "too verbose", "too detailed"
    ],
    "communication:detailed": [
        "more detail", "explain more", "elaborate", "tell me more",
        "can you explain", "need more info", "more context"
    ],
    # Complexity handling
    "complexity:incremental": [
        "step by step", "one at a time", "break it down", "smaller pieces",
        "one thing at a time", "simpler", "too complex"
    ],
    "complexity:big_picture": [
        "overall", "big picture", "full context", "everything at once",
        "whole thing", "complete picture", "overview"
    ],
    # Debugging approach
    "debugging:logging_first": [
        "add log", "print", "console.log", "debug output", "trace",
        "let me see", "show me what"
    ],
    "debugging:understand_first": [
        "why is this", "what causes", "root cause", "understand the issue",
        "explain the bug", "what's happening"
    ],
    # Decision making
    "decisions:options": [
        "what are my options", "alternatives", "other ways", "compare",
        "pros and cons", "which should I", "trade-offs"
    ],
    "decisions:recommendation": [
        "just tell me", "what should I", "recommend", "best approach",
        "what would you do", "your suggestion"
    ],
}

# Human-readable descriptions for detected styles
LEARNING_STYLE_DESCRIPTIONS = {
    "concepts:example_first": "learns better with concrete examples before abstract explanations",
    "concepts:theory_first": "wants to understand the 'why' before seeing examples",
    "communication:terse": "prefers brief, to-the-point explanations",
    "communication:detailed": "appreciates thorough, detailed explanations",
    "complexity:incremental": "learns best with step-by-step, incremental reveals",
    "complexity:big_picture": "prefers seeing the full picture upfront",
    "debugging:logging_first": "debugs by adding logging/prints first, then reasons",
    "debugging:understand_first": "wants to understand the root cause before fixing",
    "decisions:options": "prefers seeing multiple options compared before deciding",
    "decisions:recommendation": "wants direct recommendations without listing alternatives",
}


def extract_learning_style_from_feedback(
    feedback_entries: list[Pattern],
    min_occurrences: int = 2
) -> list[tuple[str, str, str]]:
    """Extract learning style patterns from feedback.

    Analyzes feedback to detect patterns in how the user prefers to receive
    information, debug code, make decisions, etc.

    Args:
        feedback_entries: List of feedback patterns to analyze
        min_occurrences: Minimum times a style must appear (default 2)

    Returns:
        List of (style_key, category, description) tuples for detected styles
    """
    detected = Counter()

    for fb in feedback_entries:
        desc_lower = fb.description.lower()
        for style_key, phrases in LEARNING_STYLE_INDICATORS.items():
            if any(phrase in desc_lower for phrase in phrases):
                detected[style_key] += 1

    # Return styles that appear min_occurrences+ times
    results = []
    for style_key, count in detected.items():
        if count >= min_occurrences:
            category = style_key.split(':')[0]
            description = LEARNING_STYLE_DESCRIPTIONS.get(
                style_key,
                style_key.split(':')[1].replace('_', ' ')
            )
            results.append((style_key, category, description))

    return results


def generate_learning_style_context(learning_styles: list[Pattern]) -> str:
    """Generate learning style hints for Claude's context.

    Args:
        learning_styles: List of learning style patterns

    Returns:
        Formatted markdown section for context injection
    """
    if not learning_styles:
        return ""

    lines = ["## How You Learn Best", ""]

    for ls in learning_styles:
        lines.append(f"- **{ls.category}**: {ls.description}")

    lines.append("")
    lines.append("_Adapt explanations and approach to match these preferences._")
    lines.append("")

    return "\n".join(lines)


def promote_learning_styles_from_feedback(
    data: SelfImproveData,
    min_occurrences: int = 2
) -> list[Pattern]:
    """Extract and promote learning styles from feedback to patterns.

    Analyzes feedback entries, extracts learning style signals, and creates
    new LEARNING_STYLE patterns for those that meet the threshold.

    Args:
        data: SelfImproveData containing feedback entries
        min_occurrences: Minimum times a style must appear

    Returns:
        List of new learning style patterns to add
    """
    # Extract styles from feedback
    detected_styles = extract_learning_style_from_feedback(
        data.feedback,
        min_occurrences
    )

    # Filter out styles that already exist
    existing_descriptions = {
        ls.description.lower() for ls in data.learning_styles
    }

    new_patterns = []
    for style_key, category, description in detected_styles:
        if description.lower() not in existing_descriptions:
            new_patterns.append(Pattern(
                type=PatternType.LEARNING_STYLE,
                category=category,
                description=description,
            ))

    return new_patterns
