# SELF_IMPROVE Implementation Guide

<!-- doc-version: 2.0.0 | last-updated: 2025-12-14 -->

> **Purpose**: Step-by-step guide to implement the self-improvement layer in Mind. Follow the Architecture document for what to build; follow this guide for how to build it.

---

## Overview

Implementation is split into 9 phases:

### Completed
- [x] **Phase 1: Foundation** - Global directory, template, basic promotion
- [x] **Phase 2: Pattern Radar** - Detection and injection in mind_recall()
- [x] **Phase 3: Feedback Capture** - Auto-logging and pattern extraction
- [x] **Phase 4: CLI Tools** - User-facing pattern management
- [x] **Phase 5: Testing Playground** - Unit tests + interactive test runner

### In Progress / Planned
- [ ] **Phase 6: Confidence Decay** - Patterns lose confidence over time if not reinforced
- [ ] **Phase 7: Reinforcement Tracking** - Track when patterns help, boost confidence
- [ ] **Phase 8: Contradiction Detection** - Flag conflicting patterns
- [ ] **Phase 9: Learning Style** - Model HOW the user learns, not just WHAT they know

---

## Why These Phases Matter

**The Self-Correcting Loop:**
```
User works → Mind suggests → User accepts/ignores/corrects → Mind learns → Better suggestions
```

Currently broken at step 4. Phases 6-8 fix this:
- **Decay** (Phase 6): Old wrong patterns fade away
- **Reinforcement** (Phase 7): Useful patterns get stronger
- **Contradiction** (Phase 8): Conflicting patterns get flagged

**The AGI Step:**
- **Learning Style** (Phase 9): Adapt HOW to help, not just WHAT to say

---

---

## Phase 1: Foundation

### Task 1.1: Create Global Directory Structure

**File**: `src/mind/storage.py`

Add function to get/create global Mind directory:

```python
from pathlib import Path

def get_global_mind_dir() -> Path:
    """Get the global Mind directory (~/.mind/).

    Creates it if it doesn't exist.
    """
    global_dir = Path.home() / ".mind"
    if not global_dir.exists():
        global_dir.mkdir(parents=True)
    return global_dir


def get_self_improve_path() -> Path:
    """Get path to global SELF_IMPROVE.md."""
    return get_global_mind_dir() / "SELF_IMPROVE.md"


def get_global_state_path() -> Path:
    """Get path to global state.json."""
    return get_global_mind_dir() / "state.json"
```

**Testing**:
```bash
# Manual test
python -c "from mind.storage import get_global_mind_dir; print(get_global_mind_dir())"
# Should print: /Users/yourname/.mind (or C:\Users\yourname\.mind on Windows)
```

---

### Task 1.2: Create SELF_IMPROVE.md Template

**File**: `src/mind/templates.py`

Add template constant:

```python
SELF_IMPROVE_TEMPLATE = """<!-- MIND SELF-IMPROVE - Global meta-learning across projects -->
<!-- Keywords: SKILL:, PREFERENCE:, BLIND_SPOT:, ANTI_PATTERN:, FEEDBACK: -->
<!-- Created: {date} | Last processed: never -->

# Self-Improvement

## Preferences
<!-- How this user likes to work. Format: PREFERENCE: [category] description -->


## Skills
<!-- Reusable approaches. Format: SKILL: [stack:context] description -->


## Blind Spots
<!-- Patterns to watch for. Format: BLIND_SPOT: [category] description -->


## Anti-Patterns
<!-- Things to avoid. Format: ANTI_PATTERN: [category] description -->


## Feedback Log
<!-- Raw corrections. Format: FEEDBACK: [date] context -> correction -->


---

<!-- Pattern metadata (machine-readable) -->
<!-- pattern_count: 0 | last_extraction: never | schema_version: 1 -->
"""
```

---

### Task 1.3: Initialize Global Mind Directory

**File**: `src/mind/cli.py`

Update `init` command to also initialize global directory:

```python
from .storage import get_global_mind_dir, get_self_improve_path
from .templates import SELF_IMPROVE_TEMPLATE

@cli.command()
def init():
    """Initialize Mind in current directory."""
    # Existing project init code...

    # NEW: Also ensure global Mind exists
    init_global_mind()


def init_global_mind():
    """Ensure global Mind directory and files exist."""
    global_dir = get_global_mind_dir()
    self_improve_path = get_self_improve_path()

    if not self_improve_path.exists():
        from datetime import datetime
        content = SELF_IMPROVE_TEMPLATE.format(date=datetime.now().strftime("%Y-%m-%d"))
        self_improve_path.write_text(content, encoding="utf-8")
        click.echo(f"Created {self_improve_path}")
```

**Testing**:
```bash
# Run init
uv run mind init

# Check global directory
ls ~/.mind/
# Should show: SELF_IMPROVE.md
```

---

### Task 1.4: Parse SELF_IMPROVE.md

**File**: `src/mind/parser.py` (or new file `src/mind/self_improve.py`)

Create parser for SELF_IMPROVE.md markers:

```python
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Pattern:
    """A learned pattern from SELF_IMPROVE.md."""
    type: str  # preference, skill, blind_spot, anti_pattern, feedback
    category: str  # The [tag] part
    description: str
    raw_line: str
    confidence: float = 1.0
    last_used: Optional[str] = None


def parse_self_improve(content: str) -> dict:
    """Parse SELF_IMPROVE.md into structured data.

    Returns:
        {
            'preferences': [Pattern, ...],
            'skills': [Pattern, ...],
            'blind_spots': [Pattern, ...],
            'anti_patterns': [Pattern, ...],
            'feedback': [Pattern, ...],
        }
    """
    result = {
        'preferences': [],
        'skills': [],
        'blind_spots': [],
        'anti_patterns': [],
        'feedback': [],
    }

    # Pattern for: TYPE: [category] description
    # or: FEEDBACK: [date] context -> correction
    pattern_re = re.compile(
        r'^(PREFERENCE|SKILL|BLIND_SPOT|ANTI_PATTERN|FEEDBACK):\s*\[([^\]]+)\]\s*(.+)$',
        re.IGNORECASE
    )

    for line in content.splitlines():
        line = line.strip()
        match = pattern_re.match(line)
        if match:
            type_name = match.group(1).lower()
            category = match.group(2)
            description = match.group(3)

            # Map to result key
            key_map = {
                'preference': 'preferences',
                'skill': 'skills',
                'blind_spot': 'blind_spots',
                'anti_pattern': 'anti_patterns',
                'feedback': 'feedback',
            }
            key = key_map.get(type_name)
            if key:
                result[key].append(Pattern(
                    type=type_name,
                    category=category,
                    description=description,
                    raw_line=line,
                ))

    return result


def filter_by_stack(patterns: dict, stack: list[str]) -> dict:
    """Filter patterns to only those relevant to the given stack.

    Skills are filtered by stack tag.
    Other types are always included.
    """
    result = patterns.copy()

    # Filter skills by stack
    filtered_skills = []
    for skill in patterns['skills']:
        # Check if any stack tag matches
        cat_parts = skill.category.lower().split(':')
        if any(tag.lower() in cat_parts for tag in stack):
            filtered_skills.append(skill)
        elif any(tag.lower() in skill.description.lower() for tag in stack):
            filtered_skills.append(skill)

    result['skills'] = filtered_skills
    return result
```

**Testing**:
```python
# Unit test
content = """
PREFERENCE: [communication] concise responses
SKILL: [python:debugging] print(f"DEBUG: {var=}")
BLIND_SPOT: [error-handling] forgets network timeouts
"""
result = parse_self_improve(content)
assert len(result['preferences']) == 1
assert len(result['skills']) == 1
assert len(result['blind_spots']) == 1
```

---

### Task 1.5: Load SELF_IMPROVE in mind_recall()

**File**: `src/mind/mcp/server.py`

Update `handle_recall()` to include SELF_IMPROVE data:

```python
from ..storage import get_self_improve_path
from ..self_improve import parse_self_improve, filter_by_stack

async def handle_recall(project_path: Path = None, force_refresh: bool = False) -> dict:
    """Load session context including self-improvement data."""
    # Existing code...

    # NEW: Load SELF_IMPROVE.md
    self_improve_context = load_self_improve_context(project_path)

    # Include in response
    result["self_improve"] = self_improve_context

    return result


def load_self_improve_context(project_path: Path) -> dict:
    """Load and filter SELF_IMPROVE.md for current project."""
    self_improve_path = get_self_improve_path()

    if not self_improve_path.exists():
        return {"enabled": False, "reason": "SELF_IMPROVE.md not found"}

    content = self_improve_path.read_text(encoding="utf-8")
    patterns = parse_self_improve(content)

    # Get project stack for filtering
    from ..detection import detect_stack
    stack = detect_stack(project_path)

    # Filter patterns by stack
    filtered = filter_by_stack(patterns, stack)

    # Budget: max 5 skills, all blind spots, 10 recent feedback
    return {
        "enabled": True,
        "preferences": [p.description for p in filtered['preferences'][:10]],
        "skills": [f"[{p.category}] {p.description}" for p in filtered['skills'][:5]],
        "blind_spots": [p.description for p in filtered['blind_spots']],  # All
        "anti_patterns": [p.description for p in filtered['anti_patterns']],
        "recent_feedback": [f"[{p.category}] {p.description}" for p in filtered['feedback'][-10:]],
    }
```

---

### Task 1.6: Inject SELF_IMPROVE into Context

**File**: `src/mind/context.py`

Update context generation to include SELF_IMPROVE section:

```python
def generate_self_improve_context(self_improve: dict) -> str:
    """Generate the SELF_IMPROVE section for CLAUDE.md context."""
    if not self_improve.get("enabled"):
        return ""

    lines = ["## Self-Improvement: Active", ""]

    # Preferences
    if self_improve.get("preferences"):
        lines.append("### Your Preferences")
        for pref in self_improve["preferences"]:
            lines.append(f"- {pref}")
        lines.append("")

    # Skills
    if self_improve.get("skills"):
        lines.append("### Relevant Skills")
        for skill in self_improve["skills"]:
            lines.append(f"- {skill}")
        lines.append("")

    # Blind spots (always show - these are warnings)
    if self_improve.get("blind_spots"):
        lines.append("### Watch For (Blind Spots)")
        for bs in self_improve["blind_spots"]:
            lines.append(f"- {bs}")
        lines.append("")

    # Recent feedback
    if self_improve.get("recent_feedback"):
        lines.append("### Recent Feedback")
        for fb in self_improve["recent_feedback"][-3:]:  # Only last 3 in context
            lines.append(f"- {fb}")
        lines.append("")

    return "\n".join(lines)
```

---

### Task 1.7: Basic Promotion from MEMORY.md

**File**: `src/mind/mcp/server.py`

Add promotion logic for KEY/SKILL/PREFERENCE markers:

```python
def promote_to_self_improve(memory_content: str, self_improve_path: Path):
    """Promote marked items from MEMORY.md to SELF_IMPROVE.md.

    Markers: KEY:, SKILL:, PREFERENCE:, BLIND_SPOT:, ANTI_PATTERN:
    """
    # Find markers in memory
    markers_re = re.compile(
        r'^(KEY|SKILL|PREFERENCE|BLIND_SPOT|ANTI_PATTERN):\s*(.+)$',
        re.MULTILINE | re.IGNORECASE
    )

    matches = markers_re.findall(memory_content)
    if not matches:
        return 0

    # Load current SELF_IMPROVE.md
    current = self_improve_path.read_text(encoding="utf-8") if self_improve_path.exists() else ""

    promoted = 0
    for marker_type, content in matches:
        # Skip if already in SELF_IMPROVE
        if content in current:
            continue

        # Determine section
        marker_type = marker_type.upper()
        if marker_type == "KEY":
            # KEY items go to Skills or Preferences based on content
            if "prefer" in content.lower():
                section = "## Preferences"
                line = f"PREFERENCE: [general] {content}"
            else:
                section = "## Skills"
                line = f"SKILL: [general] {content}"
        else:
            section_map = {
                "SKILL": "## Skills",
                "PREFERENCE": "## Preferences",
                "BLIND_SPOT": "## Blind Spots",
                "ANTI_PATTERN": "## Anti-Patterns",
            }
            section = section_map.get(marker_type, "## Skills")
            line = f"{marker_type}: [general] {content}"

        # Append to appropriate section
        # (Simple append - just add after section header)
        if section in current:
            idx = current.index(section) + len(section)
            # Find next line
            next_newline = current.index("\n", idx)
            current = current[:next_newline+1] + line + "\n" + current[next_newline+1:]
            promoted += 1

    if promoted > 0:
        self_improve_path.write_text(current, encoding="utf-8")

    return promoted
```

Call this in `handle_recall()` when processing session gap:

```python
# In handle_recall(), after session promotion
if gap_detected:
    # Existing session promotion...

    # NEW: Promote markers to SELF_IMPROVE
    memory_path = project_path / ".mind" / "MEMORY.md"
    if memory_path.exists():
        from ..storage import get_self_improve_path
        promoted = promote_to_self_improve(
            memory_path.read_text(encoding="utf-8"),
            get_self_improve_path()
        )
        if promoted > 0:
            result["promoted_to_self_improve"] = promoted
```

---

## File Structure After Phase 1

```
src/mind/
├── storage.py          # + get_global_mind_dir(), get_self_improve_path()
├── templates.py        # + SELF_IMPROVE_TEMPLATE
├── parser.py           # (or self_improve.py)
│   └── parse_self_improve(), filter_by_stack()
├── context.py          # + generate_self_improve_context()
├── cli.py              # + init_global_mind()
└── mcp/
    └── server.py       # + load_self_improve_context(), promote_to_self_improve()
```

---

## Testing Checklist

### Unit Tests

```python
# tests/test_self_improve.py

def test_parse_self_improve_preferences():
    content = "PREFERENCE: [style] concise responses"
    result = parse_self_improve(content)
    assert len(result['preferences']) == 1
    assert result['preferences'][0].category == "style"

def test_parse_self_improve_skills():
    content = "SKILL: [python:debug] use print(f'{var=}')"
    result = parse_self_improve(content)
    assert len(result['skills']) == 1
    assert "python" in result['skills'][0].category

def test_filter_by_stack():
    patterns = {
        'skills': [
            Pattern(type='skill', category='python:debug', description='...', raw_line=''),
            Pattern(type='skill', category='javascript:debug', description='...', raw_line=''),
        ],
        'preferences': [],
        'blind_spots': [],
        'anti_patterns': [],
        'feedback': [],
    }
    filtered = filter_by_stack(patterns, ['python'])
    assert len(filtered['skills']) == 1
    assert 'python' in filtered['skills'][0].category

def test_global_mind_dir_created():
    from mind.storage import get_global_mind_dir
    path = get_global_mind_dir()
    assert path.exists()
    assert path.name == ".mind"
```

### Integration Tests

```bash
# 1. Test init creates global directory
rm -rf ~/.mind  # Clean slate
uv run mind init
ls ~/.mind/SELF_IMPROVE.md  # Should exist

# 2. Test mind_recall includes self_improve
uv run mind mcp  # Start MCP
# Call mind_recall, check response has self_improve key

# 3. Test promotion
echo "KEY: stay file-based" >> .mind/MEMORY.md
# Wait for session gap or force checkpoint
uv run mind mcp  # Call recall
cat ~/.mind/SELF_IMPROVE.md  # Should have the KEY item
```

---

## Security Considerations

### 1. File Permissions

Global Mind directory should be user-private:

```python
def get_global_mind_dir() -> Path:
    global_dir = Path.home() / ".mind"
    if not global_dir.exists():
        global_dir.mkdir(parents=True, mode=0o700)  # User-only access
    return global_dir
```

### 2. No Secrets in Patterns

Add validation to reject patterns that look like secrets:

```python
SECRET_PATTERNS = [
    r'password',
    r'api[_-]?key',
    r'secret',
    r'token',
    r'credential',
]

def is_safe_pattern(content: str) -> bool:
    """Check if pattern content doesn't contain secrets."""
    content_lower = content.lower()
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, content_lower):
            return False
    return True
```

### 3. Encoding Safety

Always use UTF-8 encoding:

```python
# Good
path.write_text(content, encoding="utf-8")
path.read_text(encoding="utf-8")

# Bad (uses system default, breaks on Windows)
path.write_text(content)
path.read_text()
```

---

## Phase 2: Pattern Radar (Detailed)

### Task 2.1: Add Intuition Detection

**File**: `src/mind/self_improve.py`

```python
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Intuition:
    """A proactive warning or tip based on learned patterns."""
    type: str  # "watch", "avoid", "tip"
    message: str
    source_pattern: str  # Which pattern triggered this
    confidence: float


def detect_intuitions(
    session_context: str,
    patterns: dict,
    project_stack: list[str]
) -> list[Intuition]:
    """Scan current context for patterns that should trigger warnings.

    Args:
        session_context: Current SESSION.md content + recent activity
        patterns: Parsed SELF_IMPROVE.md data
        project_stack: Detected stack tags for this project

    Returns:
        List of intuitions to surface to the user
    """
    intuitions = []
    context_lower = session_context.lower()

    # Check blind spots - these are warnings
    for blind_spot in patterns.get('blind_spots', []):
        triggers = _extract_triggers(blind_spot.category, blind_spot.description)
        for trigger in triggers:
            if trigger.lower() in context_lower:
                intuitions.append(Intuition(
                    type="watch",
                    message=f"You tend to: {blind_spot.description}",
                    source_pattern=blind_spot.raw_line,
                    confidence=0.8
                ))
                break  # One match per blind spot

    # Check anti-patterns - these are avoid warnings
    for anti_pattern in patterns.get('anti_patterns', []):
        triggers = _extract_triggers(anti_pattern.category, anti_pattern.description)
        for trigger in triggers:
            if trigger.lower() in context_lower:
                intuitions.append(Intuition(
                    type="avoid",
                    message=f"Watch out: {anti_pattern.description}",
                    source_pattern=anti_pattern.raw_line,
                    confidence=0.7
                ))
                break

    # Check skills - these are tips (only for matching stack)
    for skill in patterns.get('skills', []):
        # Check if skill is relevant to current stack
        skill_stack = skill.category.split(':')[0].lower()
        if skill_stack in [s.lower() for s in project_stack]:
            # Check if context suggests this skill applies
            skill_triggers = _extract_triggers(skill.category, skill.description)
            for trigger in skill_triggers:
                if trigger.lower() in context_lower:
                    intuitions.append(Intuition(
                        type="tip",
                        message=f"Remember: {skill.description}",
                        source_pattern=skill.raw_line,
                        confidence=0.6
                    ))
                    break

    # Dedupe and limit
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

    # From category
    triggers.extend(category.replace('-', ' ').replace(':', ' ').split())

    # From description - extract key nouns/verbs
    # Simple heuristic: words > 4 chars that aren't stop words
    stop_words = {'this', 'that', 'with', 'from', 'have', 'been', 'were', 'they'}
    words = re.findall(r'\b\w{4,}\b', description.lower())
    triggers.extend([w for w in words if w not in stop_words])

    # Add common related terms
    related = {
        'api': ['fetch', 'request', 'endpoint', 'http'],
        'auth': ['login', 'token', 'session', 'password'],
        'error': ['catch', 'try', 'exception', 'handling'],
        'test': ['jest', 'pytest', 'spec', 'assert'],
        'async': ['await', 'promise', 'callback'],
    }
    for trigger in list(triggers):
        if trigger in related:
            triggers.extend(related[trigger])

    return list(set(triggers))
```

---

### Task 2.2: Integrate Intuitions into mind_recall()

**File**: `src/mind/mcp/server.py`

```python
from ..self_improve import detect_intuitions

async def handle_recall(project_path: Path = None, force_refresh: bool = False) -> dict:
    """Load session context including intuitions."""
    # ... existing code ...

    # Load SELF_IMPROVE patterns
    self_improve_data = load_self_improve_context(project_path)

    # Detect intuitions from current session
    intuitions = []
    if self_improve_data.get("enabled"):
        session_content = load_session_content(project_path)
        patterns = parse_self_improve(
            get_self_improve_path().read_text(encoding="utf-8")
        )
        stack = detect_stack(project_path)

        raw_intuitions = detect_intuitions(session_content, patterns, stack)
        intuitions = [
            {
                "type": i.type,
                "message": i.message,
                "confidence": i.confidence
            }
            for i in raw_intuitions
        ]

    result["self_improve"] = self_improve_data
    result["intuitions"] = intuitions

    return result


def load_session_content(project_path: Path) -> str:
    """Load current session content for pattern matching."""
    session_path = project_path / ".mind" / "SESSION.md"
    if session_path.exists():
        return session_path.read_text(encoding="utf-8")
    return ""
```

---

### Task 2.3: Format Intuitions in Context

**File**: `src/mind/context.py`

```python
def generate_intuition_context(intuitions: list[dict]) -> str:
    """Generate the Intuition section for CLAUDE.md context."""
    if not intuitions:
        return ""

    lines = ["## Intuition", "", "Based on your patterns:"]

    type_prefix = {
        "watch": "WATCH",
        "avoid": "AVOID",
        "tip": "TIP"
    }

    for i in intuitions:
        prefix = type_prefix.get(i["type"], "NOTE")
        lines.append(f"- {prefix}: {i['message']}")

    lines.append("")
    return "\n".join(lines)
```

---

### Task 2.4: Add Confidence Scoring and Decay

**File**: `src/mind/self_improve.py`

```python
from datetime import datetime, timedelta
import json


@dataclass
class PatternMetadata:
    """Metadata for tracking pattern usage and confidence."""
    pattern_id: str
    created_at: str
    last_used: Optional[str] = None
    use_count: int = 0
    confidence: float = 1.0

    def decay(self, days_inactive: int = 30) -> float:
        """Calculate decayed confidence based on inactivity."""
        if not self.last_used:
            return self.confidence * 0.5  # Never used = low confidence

        last = datetime.fromisoformat(self.last_used)
        days_since = (datetime.now() - last).days

        if days_since < days_inactive:
            return self.confidence

        # Decay by 10% per 30 days of inactivity
        decay_periods = days_since // days_inactive
        return max(0.1, self.confidence * (0.9 ** decay_periods))


def load_pattern_metadata(global_mind_dir: Path) -> dict[str, PatternMetadata]:
    """Load pattern metadata from state file."""
    state_path = global_mind_dir / "pattern_state.json"
    if not state_path.exists():
        return {}

    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        return {
            k: PatternMetadata(**v)
            for k, v in data.get("patterns", {}).items()
        }
    except (json.JSONDecodeError, TypeError):
        return {}


def save_pattern_metadata(global_mind_dir: Path, metadata: dict[str, PatternMetadata]):
    """Save pattern metadata to state file."""
    state_path = global_mind_dir / "pattern_state.json"
    data = {
        "patterns": {k: vars(v) for k, v in metadata.items()},
        "last_updated": datetime.now().isoformat()
    }
    state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def mark_pattern_used(global_mind_dir: Path, pattern_id: str):
    """Mark a pattern as used, updating its metadata."""
    metadata = load_pattern_metadata(global_mind_dir)

    if pattern_id not in metadata:
        metadata[pattern_id] = PatternMetadata(
            pattern_id=pattern_id,
            created_at=datetime.now().isoformat()
        )

    metadata[pattern_id].last_used = datetime.now().isoformat()
    metadata[pattern_id].use_count += 1

    save_pattern_metadata(global_mind_dir, metadata)
```

---

## Phase 3: Feedback Capture (Detailed)

### Task 3.1: Add Feedback Type to mind_log()

**File**: `src/mind/mcp/server.py`

Update the `handle_log()` function to support feedback:

```python
async def handle_log(message: str, log_type: str = "experience") -> dict:
    """Log to session or memory based on type.

    Types that go to SESSION.md (ephemeral):
    - experience, blocker, assumption, rejected

    Types that go to MEMORY.md (permanent):
    - decision, learning, problem, progress

    NEW: Types that go to SELF_IMPROVE.md (global):
    - feedback (user corrections)
    - preference (explicit preference)
    - blind_spot (identified blind spot)
    """
    project_path = find_project_path()

    # Determine target file
    global_types = {"feedback", "preference", "blind_spot", "skill"}
    session_types = {"experience", "blocker", "assumption", "rejected"}
    memory_types = {"decision", "learning", "problem", "progress"}

    if log_type in global_types:
        target = "SELF_IMPROVE.md"
        await log_to_self_improve(message, log_type, project_path)
    elif log_type in session_types:
        target = "SESSION.md"
        await log_to_session(message, log_type, project_path)
    else:
        target = "MEMORY.md"
        await log_to_memory(message, log_type, project_path)

    touch_activity(project_path)

    return {
        "success": True,
        "logged": message,
        "type": log_type,
        "target": target
    }


async def log_to_self_improve(message: str, log_type: str, project_path: Path):
    """Log directly to global SELF_IMPROVE.md."""
    from ..storage import get_self_improve_path

    self_improve_path = get_self_improve_path()
    if not self_improve_path.exists():
        # Initialize if needed
        init_global_mind()

    content = self_improve_path.read_text(encoding="utf-8")

    # Format based on type
    date = datetime.now().strftime("%Y-%m-%d")

    if log_type == "feedback":
        line = f"FEEDBACK: [{date}] {message}"
        section = "## Feedback Log"
    elif log_type == "preference":
        line = f"PREFERENCE: [general] {message}"
        section = "## Preferences"
    elif log_type == "blind_spot":
        line = f"BLIND_SPOT: [general] {message}"
        section = "## Blind Spots"
    elif log_type == "skill":
        line = f"SKILL: [general] {message}"
        section = "## Skills"
    else:
        return

    # Insert after section header
    if section in content:
        idx = content.index(section) + len(section)
        # Find next newline
        next_newline = content.index("\n", idx)
        content = content[:next_newline+1] + line + "\n" + content[next_newline+1:]
        self_improve_path.write_text(content, encoding="utf-8")
```

---

### Task 3.2: Feedback Detection Heuristics

**File**: `src/mind/feedback.py`

```python
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class DetectedFeedback:
    """A detected user correction."""
    original: str  # What Claude did/said
    correction: str  # What user wanted
    context: str  # What was happening
    confidence: float


# Patterns that indicate user correction
CORRECTION_PATTERNS = [
    # Direct corrections
    r"no[,.]?\s+(?:I\s+)?(?:want|meant|need)(?:ed)?\s+(.+)",
    r"not\s+like\s+that[,.]?\s+(.+)",
    r"actually[,.]?\s+(.+)",
    r"I\s+(?:meant|want|need)\s+(.+)",

    # Style corrections
    r"(?:use|prefer|like)\s+(.+)\s+(?:instead|not)",
    r"don't\s+(?:use|add|include)\s+(.+)",

    # Approach corrections
    r"(?:too|overly)\s+(complex|simple|verbose|terse)",
    r"(?:this\s+is\s+)?(?:overkill|overengineered|too\s+much)",
    r"(?:keep\s+it\s+)?(?:simple|simpler|KISS)",
    r"YAGNI",
]


def detect_feedback_in_message(
    user_message: str,
    previous_claude_action: Optional[str] = None
) -> Optional[DetectedFeedback]:
    """Detect if a user message contains feedback/correction.

    Args:
        user_message: The user's message
        previous_claude_action: What Claude just did (for context)

    Returns:
        DetectedFeedback if correction detected, None otherwise
    """
    message_lower = user_message.lower()

    for pattern in CORRECTION_PATTERNS:
        match = re.search(pattern, message_lower, re.IGNORECASE)
        if match:
            correction = match.group(1) if match.groups() else user_message
            return DetectedFeedback(
                original=previous_claude_action or "unknown",
                correction=correction.strip(),
                context=user_message[:100],
                confidence=0.7
            )

    # Check for explicit negative sentiment
    negative_starters = ["no", "nope", "wrong", "that's not", "not what"]
    if any(message_lower.startswith(neg) for neg in negative_starters):
        return DetectedFeedback(
            original=previous_claude_action or "unknown",
            correction=user_message,
            context="negative response",
            confidence=0.5
        )

    return None


def format_feedback_for_log(feedback: DetectedFeedback) -> str:
    """Format detected feedback for logging to SELF_IMPROVE.md."""
    return f"{feedback.original} -> {feedback.correction}"
```

---

### Task 3.3: Pattern Extraction from Feedback

**File**: `src/mind/self_improve.py`

```python
from collections import Counter
import re


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
    if len(feedback_entries) < min_occurrences:
        return []

    # Extract themes from feedback descriptions
    themes = Counter()
    category_themes = {}

    for fb in feedback_entries:
        desc = fb.description.lower()

        # Look for common correction patterns
        if "->" in desc:
            original, correction = desc.split("->", 1)

            # Style preferences
            if any(w in correction for w in ["single", "double", "quotes"]):
                themes["style:quotes"] += 1
                category_themes["style:quotes"] = correction.strip()

            if any(w in correction for w in ["simple", "simpler", "less"]):
                themes["approach:simplicity"] += 1
                category_themes["approach:simplicity"] = "prefers simpler solutions"

            if any(w in correction for w in ["complex", "more", "detailed"]):
                themes["approach:detail"] += 1
                category_themes["approach:detail"] = "prefers detailed solutions"

            # Error handling patterns
            if any(w in original for w in ["error", "catch", "try", "handling"]):
                themes["blind_spot:error_handling"] += 1
                category_themes["blind_spot:error_handling"] = "tends to skip error handling"

            # Over-engineering
            if any(w in correction for w in ["overkill", "yagni", "too much"]):
                themes["anti_pattern:overengineering"] += 1
                category_themes["anti_pattern:overengineering"] = "tends to over-engineer"

    # Extract patterns that meet threshold
    new_patterns = []
    for theme, count in themes.items():
        if count >= min_occurrences:
            pattern_type, category = theme.split(":", 1)
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


def promote_extracted_patterns(
    self_improve_path: Path,
    new_patterns: list[tuple[str, str, str]]
) -> int:
    """Add extracted patterns to SELF_IMPROVE.md.

    Returns number of patterns added.
    """
    if not new_patterns:
        return 0

    content = self_improve_path.read_text(encoding="utf-8")
    added = 0

    section_map = {
        "preference": "## Preferences",
        "blind_spot": "## Blind Spots",
        "anti_pattern": "## Anti-Patterns",
        "skill": "## Skills"
    }

    for pattern_type, category, description in new_patterns:
        # Format the line
        type_prefix = pattern_type.upper().replace("_", " ")
        line = f"{type_prefix}: [{category}] {description}"

        # Skip if already exists
        if description in content:
            continue

        # Find section and insert
        section = section_map.get(pattern_type)
        if section and section in content:
            idx = content.index(section) + len(section)
            next_newline = content.index("\n", idx)
            content = content[:next_newline+1] + line + "\n" + content[next_newline+1:]
            added += 1

    if added > 0:
        self_improve_path.write_text(content, encoding="utf-8")

    return added
```

---

## Phase 4: CLI Tools (Detailed)

### Task 4.1: mind patterns Command

**File**: `src/mind/cli.py`

```python
@cli.command()
@click.option('--type', '-t', 'pattern_type',
              type=click.Choice(['all', 'preferences', 'skills', 'blind_spots', 'anti_patterns']),
              default='all', help='Filter by pattern type')
@click.option('--stack', '-s', help='Filter by stack tag')
def patterns(pattern_type: str, stack: str):
    """View learned patterns from SELF_IMPROVE.md."""
    from .storage import get_self_improve_path
    from .self_improve import parse_self_improve, filter_by_stack

    self_improve_path = get_self_improve_path()
    if not self_improve_path.exists():
        click.echo("No SELF_IMPROVE.md found. Run 'mind init' first.")
        return

    content = self_improve_path.read_text(encoding="utf-8")
    patterns = parse_self_improve(content)

    # Filter by stack if specified
    if stack:
        patterns = filter_by_stack(patterns, [stack])

    # Display patterns
    sections = {
        'preferences': ('Preferences', patterns.get('preferences', [])),
        'skills': ('Skills', patterns.get('skills', [])),
        'blind_spots': ('Blind Spots', patterns.get('blind_spots', [])),
        'anti_patterns': ('Anti-Patterns', patterns.get('anti_patterns', [])),
    }

    total = 0
    for key, (title, items) in sections.items():
        if pattern_type != 'all' and key != pattern_type:
            continue

        if items:
            click.echo(f"\n## {title}")
            for item in items:
                click.echo(f"  [{item.category}] {item.description}")
                total += 1

    if total == 0:
        click.echo("No patterns found.")
    else:
        click.echo(f"\nTotal: {total} patterns")


@cli.command()
@click.option('--limit', '-n', default=10, help='Number of entries to show')
def feedback(limit: int):
    """View recent feedback log."""
    from .storage import get_self_improve_path
    from .self_improve import parse_self_improve

    self_improve_path = get_self_improve_path()
    if not self_improve_path.exists():
        click.echo("No SELF_IMPROVE.md found.")
        return

    content = self_improve_path.read_text(encoding="utf-8")
    patterns = parse_self_improve(content)
    feedback_entries = patterns.get('feedback', [])

    if not feedback_entries:
        click.echo("No feedback logged yet.")
        return

    click.echo(f"## Recent Feedback (last {limit})\n")
    for entry in feedback_entries[-limit:]:
        click.echo(f"  [{entry.category}] {entry.description}")


@cli.command('reset-patterns')
@click.confirmation_option(prompt='This will clear all learned patterns. Continue?')
def reset_patterns():
    """Clear all learned patterns (nuclear option)."""
    from .storage import get_self_improve_path
    from .templates import SELF_IMPROVE_TEMPLATE
    from datetime import datetime

    self_improve_path = get_self_improve_path()

    # Backup first
    if self_improve_path.exists():
        backup_path = self_improve_path.with_suffix('.md.backup')
        backup_path.write_text(
            self_improve_path.read_text(encoding="utf-8"),
            encoding="utf-8"
        )
        click.echo(f"Backed up to {backup_path}")

    # Reset
    content = SELF_IMPROVE_TEMPLATE.format(date=datetime.now().strftime("%Y-%m-%d"))
    self_improve_path.write_text(content, encoding="utf-8")
    click.echo("Patterns reset. Fresh start!")
```

---

## Phase 5: Spawner Integration (Detailed)

### Task 5.1: Detect Spawner Availability

**File**: `src/mind/integrations/spawner.py`

```python
"""Spawner integration for Mind.

Detects if Spawner MCP is available and coordinates context sharing.
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class SpawnerContext:
    """Context received from Spawner."""
    available: bool
    stack: list[str]
    skill_level: str  # vibe-coder, builder, developer, expert
    active_skills: list[str]
    sharp_edges_hit: list[str]


def detect_spawner() -> bool:
    """Check if Spawner MCP is available.

    Looks for spawner in MCP config or environment.
    """
    # Check common MCP config locations
    config_paths = [
        Path.home() / ".config" / "claude" / "mcp.json",
        Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                servers = config.get("mcpServers", {})
                if "spawner" in servers:
                    return True
            except (json.JSONDecodeError, OSError):
                continue

    return False


def get_spawner_context() -> Optional[SpawnerContext]:
    """Get context from Spawner if available.

    This would be called via MCP tool call in practice.
    For now, returns None (placeholder for integration).
    """
    if not detect_spawner():
        return None

    # TODO: Actual MCP call to spawner_load()
    # For now, return placeholder
    return None


def export_preferences_for_spawner(patterns: dict) -> dict:
    """Export Mind patterns in format Spawner can use.

    Returns dict that Spawner can use to filter skills.
    """
    return {
        "preferences": [
            {"category": p.category, "value": p.description}
            for p in patterns.get('preferences', [])
        ],
        "blind_spots": [
            {"category": b.category, "trigger": b.description}
            for b in patterns.get('blind_spots', [])
        ],
        "anti_patterns": [
            a.description for a in patterns.get('anti_patterns', [])
        ],
        "preferred_stack": [
            s.category.split(':')[0]
            for s in patterns.get('skills', [])
        ]
    }


def import_sharp_edge_as_blind_spot(
    edge_name: str,
    edge_description: str,
    category: str
) -> str:
    """Convert a Spawner sharp edge hit to Mind blind spot format.

    When user hits a Spawner sharp edge, Mind should learn it.
    """
    return f"BLIND_SPOT: [{category}] {edge_description} (from Spawner: {edge_name})"
```

---

### Task 5.2: Coordinate Context Loading

**File**: `src/mind/mcp/server.py`

Add Spawner coordination to `handle_recall()`:

```python
from ..integrations.spawner import detect_spawner, export_preferences_for_spawner

async def handle_recall(project_path: Path = None, force_refresh: bool = False) -> dict:
    """Load session context with optional Spawner coordination."""
    # ... existing code ...

    # Check for Spawner integration
    spawner_available = detect_spawner()

    if spawner_available and self_improve_data.get("enabled"):
        # Export preferences for Spawner to use
        patterns = parse_self_improve(
            get_self_improve_path().read_text(encoding="utf-8")
        )
        result["spawner_hints"] = export_preferences_for_spawner(patterns)

    result["integrations"] = {
        "spawner": {
            "available": spawner_available,
            "hint": "Use spawner_hints to filter skills" if spawner_available else None
        }
    }

    return result
```

---

### Task 5.3: Learn from Spawner Sharp Edges

**File**: `src/mind/mcp/server.py`

Add new MCP tool for Spawner to report sharp edge hits:

```python
@server.tool()
async def mind_learn_edge(
    edge_name: str,
    edge_description: str,
    category: str = "general"
) -> dict:
    """Learn from a Spawner sharp edge hit.

    Called by Spawner when user hits a sharp edge, so Mind
    can track it as a personal blind spot.

    Args:
        edge_name: Name of the sharp edge (e.g., "async-client-component")
        edge_description: What the gotcha is
        category: Category tag (e.g., "nextjs", "react")
    """
    from ..storage import get_self_improve_path
    from ..integrations.spawner import import_sharp_edge_as_blind_spot

    self_improve_path = get_self_improve_path()
    if not self_improve_path.exists():
        return {"success": False, "reason": "SELF_IMPROVE.md not found"}

    content = self_improve_path.read_text(encoding="utf-8")

    # Check if already learned
    if edge_name in content:
        return {"success": True, "action": "already_known"}

    # Add as blind spot
    line = import_sharp_edge_as_blind_spot(edge_name, edge_description, category)

    section = "## Blind Spots"
    if section in content:
        idx = content.index(section) + len(section)
        next_newline = content.index("\n", idx)
        content = content[:next_newline+1] + line + "\n" + content[next_newline+1:]
        self_improve_path.write_text(content, encoding="utf-8")

    return {
        "success": True,
        "action": "learned",
        "blind_spot": line
    }
```

---

## Phase 6: Confidence Decay

**Goal**: Patterns that aren't reinforced should lose confidence over time, preventing stale assumptions from persisting.

### Why This Matters

Without decay:
```
Day 1: User says "I prefer verbose comments"
Day 30: User's style evolved, now prefers minimal comments
Day 60: Mind still pushing verbose comments (confidence never dropped)
```

Old patterns become lies the system believes with high confidence.

### Task 6.1: Add Decay Calculation

**File**: `src/mind/self_improve.py`

```python
from datetime import datetime, timedelta

def calculate_decayed_confidence(
    base_confidence: float,
    last_reinforced: datetime,
    decay_rate: float = 0.1,
    decay_period_days: int = 30
) -> float:
    """Calculate confidence after time-based decay.

    Args:
        base_confidence: Original confidence (0.0 to 1.0)
        last_reinforced: When pattern was last used/reinforced
        decay_rate: How much to decay per period (default 10%)
        decay_period_days: Days per decay period (default 30)

    Returns:
        Decayed confidence, minimum 0.1
    """
    days_since = (datetime.now() - last_reinforced).days

    if days_since < decay_period_days:
        return base_confidence

    decay_periods = days_since // decay_period_days
    decayed = base_confidence * ((1 - decay_rate) ** decay_periods)

    return max(0.1, decayed)
```

### Task 6.2: Add Pattern Metadata Storage

**File**: `src/mind/self_improve.py`

```python
@dataclass
class PatternMetadata:
    """Metadata for tracking pattern lifecycle."""
    pattern_hash: str  # Hash of pattern content for identification
    created_at: datetime
    last_reinforced: datetime
    reinforcement_count: int = 0
    base_confidence: float = 0.5

    def current_confidence(self) -> float:
        """Get confidence with decay applied."""
        return calculate_decayed_confidence(
            self.base_confidence,
            self.last_reinforced
        )
```

Store in `~/.mind/pattern_metadata.json`:
```json
{
  "patterns": {
    "abc123": {
      "pattern_hash": "abc123",
      "created_at": "2025-12-01T10:00:00",
      "last_reinforced": "2025-12-10T14:30:00",
      "reinforcement_count": 3,
      "base_confidence": 0.7
    }
  }
}
```

### Task 6.3: Apply Decay in mind_recall()

Update `handle_recall()` to filter low-confidence patterns:

```python
def filter_by_confidence(patterns: dict, min_confidence: float = 0.3) -> dict:
    """Filter out patterns below confidence threshold."""
    metadata = load_pattern_metadata()

    filtered = {}
    for key, pattern_list in patterns.items():
        filtered[key] = [
            p for p in pattern_list
            if get_pattern_confidence(p, metadata) >= min_confidence
        ]
    return filtered
```

### Testing

```python
def test_confidence_decay():
    # Pattern not reinforced for 90 days should decay
    old_date = datetime.now() - timedelta(days=90)
    confidence = calculate_decayed_confidence(0.8, old_date)
    assert confidence < 0.8  # Should have decayed
    assert confidence >= 0.1  # Should not go below minimum

def test_recent_pattern_no_decay():
    # Pattern reinforced recently should not decay
    recent = datetime.now() - timedelta(days=5)
    confidence = calculate_decayed_confidence(0.8, recent)
    assert confidence == 0.8
```

---

## Phase 7: Reinforcement Tracking

**Goal**: Track when patterns actually help the user, and boost their confidence.

### Task 7.1: Add Reinforcement Log Type

Update `handle_log()` to accept reinforcement:

```python
# In handle_log()
if log_type == "reinforce":
    # Format: "pattern description that helped"
    pattern_hash = hash_pattern_description(message)
    reinforce_pattern(pattern_hash)
    return {"success": True, "action": "reinforced", "pattern": message}
```

### Task 7.2: Implement Reinforcement

**File**: `src/mind/self_improve.py`

```python
def reinforce_pattern(pattern_hash: str, boost: float = 0.1) -> bool:
    """Reinforce a pattern, boosting its confidence.

    Args:
        pattern_hash: Hash identifying the pattern
        boost: How much to increase confidence (default 10%)

    Returns:
        True if pattern was found and reinforced
    """
    metadata = load_pattern_metadata()

    if pattern_hash not in metadata:
        return False

    pattern = metadata[pattern_hash]
    pattern.last_reinforced = datetime.now()
    pattern.reinforcement_count += 1
    pattern.base_confidence = min(1.0, pattern.base_confidence + boost)

    save_pattern_metadata(metadata)
    return True


def hash_pattern_description(description: str) -> str:
    """Create stable hash for pattern matching."""
    import hashlib
    normalized = description.lower().strip()
    return hashlib.md5(normalized.encode()).hexdigest()[:12]
```

### Task 7.3: Usage Pattern

When Claude uses a pattern and it helps:

```python
# Claude notices pattern was useful
mind_log("prefers functional style - used this, worked well", type="reinforce")
```

### Testing

```python
def test_reinforcement_boosts_confidence():
    # Setup: pattern with 0.5 confidence
    create_test_pattern("test pattern", confidence=0.5)

    # Reinforce it
    reinforce_pattern(hash_pattern_description("test pattern"))

    # Check confidence increased
    meta = load_pattern_metadata()
    pattern = meta[hash_pattern_description("test pattern")]
    assert pattern.base_confidence == 0.6

def test_reinforcement_resets_decay():
    # Old pattern that has decayed
    old_pattern = create_test_pattern("old pattern", days_ago=90)

    # Reinforce it
    reinforce_pattern(hash_pattern_description("old pattern"))

    # last_reinforced should be now, confidence restored
    meta = load_pattern_metadata()
    pattern = meta[hash_pattern_description("old pattern")]
    assert pattern.current_confidence() > 0.5  # Decay reset
```

---

## Phase 8: Contradiction Detection

**Goal**: When adding a new pattern, detect if it conflicts with existing patterns.

### Task 8.1: Similarity Detection

**File**: `src/mind/self_improve.py`

```python
def find_similar_patterns(
    new_description: str,
    existing_patterns: list[Pattern],
    similarity_threshold: float = 0.6
) -> list[tuple[Pattern, float]]:
    """Find patterns similar to the new one.

    Uses keyword overlap for simplicity (no embeddings needed).

    Returns:
        List of (pattern, similarity_score) tuples
    """
    new_keywords = set(extract_keywords(new_description))

    similar = []
    for pattern in existing_patterns:
        existing_keywords = set(extract_keywords(pattern.description))

        if not new_keywords or not existing_keywords:
            continue

        # Jaccard similarity
        intersection = len(new_keywords & existing_keywords)
        union = len(new_keywords | existing_keywords)
        similarity = intersection / union if union > 0 else 0

        if similarity >= similarity_threshold:
            similar.append((pattern, similarity))

    return sorted(similar, key=lambda x: x[1], reverse=True)


def extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from text."""
    import re
    # Words 4+ chars, not stop words
    stop_words = {'this', 'that', 'with', 'from', 'have', 'been', 'like', 'prefer'}
    words = re.findall(r'\b\w{4,}\b', text.lower())
    return [w for w in words if w not in stop_words]
```

### Task 8.2: Contradiction Detection

```python
def detect_contradiction(
    new_pattern: Pattern,
    similar_pattern: Pattern
) -> bool:
    """Check if two similar patterns contradict each other.

    Looks for opposing signals like:
    - "prefer X" vs "avoid X"
    - "always X" vs "never X"
    - "like X" vs "dislike X"
    """
    new_lower = new_pattern.description.lower()
    existing_lower = similar_pattern.description.lower()

    # Opposing word pairs
    opposites = [
        ('prefer', 'avoid'),
        ('like', 'dislike'),
        ('always', 'never'),
        ('use', 'dont use'),
        ('simple', 'complex'),
        ('verbose', 'terse'),
        ('detailed', 'brief'),
    ]

    for pos, neg in opposites:
        if (pos in new_lower and neg in existing_lower) or \
           (neg in new_lower and pos in existing_lower):
            return True

    return False
```

### Task 8.3: Integrate into Pattern Addition

```python
def add_pattern_with_contradiction_check(
    pattern_type: PatternType,
    category: str,
    description: str
) -> dict:
    """Add a pattern, checking for contradictions first.

    Returns:
        {
            "success": bool,
            "action": "added" | "contradiction_detected" | "duplicate",
            "conflicts": [list of conflicting patterns if any]
        }
    """
    data = load_self_improve()
    all_patterns = data.all_patterns()

    new_pattern = Pattern(type=pattern_type, category=category, description=description)

    # Check for similar patterns
    similar = find_similar_patterns(description, all_patterns)

    # Check for contradictions
    contradictions = []
    for pattern, similarity in similar:
        if detect_contradiction(new_pattern, pattern):
            contradictions.append({
                "pattern": pattern.description,
                "type": pattern.type.value,
                "similarity": similarity
            })

    if contradictions:
        return {
            "success": False,
            "action": "contradiction_detected",
            "conflicts": contradictions,
            "suggestion": "Resolve conflict before adding. Use mind_log to update existing pattern or remove old one."
        }

    # No contradictions, safe to add
    append_pattern(pattern_type, category, description)
    return {"success": True, "action": "added"}
```

### Testing

```python
def test_detect_contradiction():
    p1 = Pattern(PatternType.PREFERENCE, "style", "prefer verbose comments")
    p2 = Pattern(PatternType.PREFERENCE, "style", "prefer terse comments")

    assert detect_contradiction(p1, p2) == True

def test_no_contradiction_different_topics():
    p1 = Pattern(PatternType.PREFERENCE, "style", "prefer verbose comments")
    p2 = Pattern(PatternType.PREFERENCE, "testing", "prefer integration tests")

    assert detect_contradiction(p1, p2) == False

def test_similar_but_not_contradicting():
    p1 = Pattern(PatternType.SKILL, "python", "good at asyncio")
    p2 = Pattern(PatternType.SKILL, "python", "good at asyncio patterns")

    similar = find_similar_patterns(p1.description, [p2])
    assert len(similar) > 0  # Similar
    assert detect_contradiction(p1, p2) == False  # But not contradicting
```

---

## Phase 9: Learning Style

**Goal**: Model HOW the user learns, not just WHAT they know. This is the AGI-like step.

### Why This Matters

Same information, different delivery:

**Without learning style:**
> "Here's how to fix the auth bug: change line 42 to use `await`"

**With `LEARNING_STYLE: [debugging] wants to understand the "why" first`:**
> "The bug happens because `fetchUser()` is async but you're not awaiting it, so `user` is a Promise, not the actual data. The fix is adding `await` on line 42."

**With `LEARNING_STYLE: [debugging] learns by adding logging first`:**
> "Let's add a `console.log(user)` on line 43 first - you'll see it's a Promise object, which confirms the issue is missing `await` on line 42."

### Task 9.1: Add Learning Style Pattern Type

**File**: `src/mind/self_improve.py`

```python
class PatternType(Enum):
    PREFERENCE = "preference"
    SKILL = "skill"
    BLIND_SPOT = "blind_spot"
    ANTI_PATTERN = "anti_pattern"
    FEEDBACK = "feedback"
    LEARNING_STYLE = "learning_style"  # NEW
```

Update parser:
```python
LEARNING_STYLE_PATTERN = re.compile(
    r"^(?:-\s*)?LEARNING_STYLE:\s*\[([^\]]+)\]\s*(.+)$",
    re.IGNORECASE | re.MULTILINE
)
```

### Task 9.2: Learning Style Categories

```markdown
## Learning Styles
<!-- How you best absorb information. Format: LEARNING_STYLE: [context] description -->

# Common categories:
LEARNING_STYLE: [concepts] needs concrete example before abstract explanation
LEARNING_STYLE: [debugging] adds logging first, reasons second
LEARNING_STYLE: [decisions] needs 2-3 options compared, not single recommendation
LEARNING_STYLE: [feedback] responds better to questions than direct corrections
LEARNING_STYLE: [complexity] prefers incremental reveal over full picture upfront
LEARNING_STYLE: [new-tech] tries first, reads docs when stuck
LEARNING_STYLE: [communication] prefers terse bullet points over prose
```

### Task 9.3: Extract from Feedback

Detect learning style from correction patterns:

```python
def extract_learning_style_from_feedback(feedback_entries: list[Pattern]) -> list[tuple[str, str]]:
    """Extract learning style patterns from feedback.

    Looks for signals like:
    - "show me an example" -> learns by example
    - "why does this work" -> needs understanding
    - "too much detail" -> prefers terse
    - "step by step" -> prefers incremental
    """
    indicators = {
        "concepts:example_first": [
            "show me", "give example", "can you demonstrate", "what does this look like"
        ],
        "concepts:theory_first": [
            "why does", "how does", "explain the", "what's the reason"
        ],
        "communication:terse": [
            "too much", "too long", "shorter", "brief", "tldr", "just tell me"
        ],
        "communication:detailed": [
            "more detail", "explain more", "elaborate", "tell me more"
        ],
        "complexity:incremental": [
            "step by step", "one at a time", "break it down", "smaller pieces"
        ],
        "complexity:big_picture": [
            "overall", "big picture", "full context", "everything at once"
        ],
    }

    detected = Counter()
    for fb in feedback_entries:
        desc_lower = fb.description.lower()
        for style, phrases in indicators.items():
            if any(phrase in desc_lower for phrase in phrases):
                detected[style] += 1

    # Return styles that appear 2+ times
    return [(style, style.split(':')[1]) for style, count in detected.items() if count >= 2]
```

### Task 9.4: Inject Learning Style into Context

```python
def generate_learning_style_context(learning_styles: list[Pattern]) -> str:
    """Generate learning style hints for Claude."""
    if not learning_styles:
        return ""

    lines = ["## How You Learn Best", ""]

    for ls in learning_styles:
        lines.append(f"- **{ls.category}**: {ls.description}")

    lines.append("")
    lines.append("_Adapt your explanations to match these preferences._")
    lines.append("")

    return "\n".join(lines)
```

### Testing

```python
def test_learning_style_extraction():
    feedback = [
        Pattern(PatternType.FEEDBACK, "2025-01-01", "too abstract -> show me an example"),
        Pattern(PatternType.FEEDBACK, "2025-01-02", "confused -> can you demonstrate"),
        Pattern(PatternType.FEEDBACK, "2025-01-03", "still unclear -> give example please"),
    ]

    styles = extract_learning_style_from_feedback(feedback)
    assert any("example" in s[1] for s in styles)

def test_learning_style_in_context():
    data = load_self_improve()
    # Add learning style
    append_pattern(PatternType.LEARNING_STYLE, "debugging", "learns by adding print statements first")

    context = generate_full_context(data, ["python"])
    assert "How You Learn Best" in context
    assert "print statements" in context
```

---

## Rollout Plan

### Phase 1-5: COMPLETE
Already shipped and tested.

### Phase 6-9: Incremental Rollout

1. **Phase 6 (Decay)**: Ship first - low risk, high value
2. **Phase 7 (Reinforcement)**: Ship with Phase 6 - they work together
3. **Phase 8 (Contradiction)**: Ship after 6+7 proven stable
4. **Phase 9 (Learning Style)**: Ship last - most experimental

### Feature Flags

```python
DEFAULT_CONFIG = {
    "version": 1,
    "mascot": True,
    "self_improve": {
        "enabled": True,          # Phases 1-5
        "decay": False,           # Phase 6
        "reinforcement": False,   # Phase 7
        "contradiction": False,   # Phase 8
        "learning_style": False,  # Phase 9
    },
}
```

---

*This guide will be updated as implementation progresses. Check git history for changes.*
