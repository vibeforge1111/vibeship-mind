# Mind Parser Specification

## Overview

The parser extracts structured entities from natural language text. It uses loose regex patterns to accept various writing styles while scoring confidence based on explicitness.

**Philosophy:** Lower friction > perfect extraction. Accept messy input, extract what we can.

---

## Capture Sources

The parser handles three input sources:

| Source | Location | Format |
|--------|----------|--------|
| Memory file | `.mind/MEMORY.md` | Markdown |
| Inline comments | `*.ts, *.py, *.svelte, etc.` | `// MEMORY:` or `<!-- MEMORY: -->` |
| Git commits | `.git/COMMIT_EDITMSG` | Plain text |

---

## Entity Types

### Decision

A choice that was made.

**Extraction Patterns:**

```python
DECISION_PATTERNS = [
    # Explicit format (highest confidence)
    r"\*\*[Dd]ecided:?\*\*\s*(.+)",
    
    # Direct statements
    r"[Dd]ecided\s+(?:to\s+)?(.+?)(?:\.|$)",
    r"[Cc]hose\s+(.+?)\s+(?:over|because|instead|\.|$)",
    r"[Gg]oing\s+with\s+(.+?)(?:\.|$)",
    r"[Uu]sing\s+(.+?)\s+(?:instead|over|because|rather|\.|$)",
    r"[Ww]ent\s+with\s+(.+?)(?:\.|$)",
    r"[Ss]ettled\s+on\s+(.+?)(?:\.|$)",
    r"[Pp]icked\s+(.+?)\s+(?:over|because|\.|$)",
    
    # Quick syntax
    r"MEMORY:\s*decided\s+(.+)",
]
```

**Confidence Scoring:**

```python
def score_decision(line: str, match: str) -> float:
    confidence = 0.5  # Base
    
    if '**' in line:  # Explicit markdown
        confidence += 0.3
    if re.search(r'\bbecause\b', line, re.I):  # Has reasoning
        confidence += 0.2
    if re.search(r'\bover\b', line, re.I):  # Has alternative
        confidence += 0.1
    if line.strip().startswith('MEMORY:'):  # Quick syntax
        confidence += 0.2
    
    return min(confidence, 1.0)
```

**Examples:**

| Input | Extracted | Confidence |
|-------|-----------|------------|
| `**Decided:** Use JWT because simpler` | "Use JWT because simpler" | 1.0 |
| `decided to use JWT` | "use JWT" | 0.5 |
| `Going with Supabase over Firebase` | "Supabase over Firebase" | 0.6 |
| `MEMORY: decided JWT over OAuth` | "JWT over OAuth" | 0.7 |

---

### Issue

A problem encountered.

**Extraction Patterns:**

```python
ISSUE_PATTERNS = [
    # Explicit format
    r"\*\*[Pp]roblem:?\*\*\s*(.+)",
    r"\*\*[Ii]ssue:?\*\*\s*(.+)",
    r"\*\*[Bb]ug:?\*\*\s*(.+)",
    
    # Direct statements
    r"[Pp]roblem:?\s*(.+?)(?:\.|$)",
    r"[Ii]ssue:?\s*(.+?)(?:\.|$)",
    r"[Bb]ug:?\s*(.+?)(?:\.|$)",
    r"[Hh]it\s+(?:a\s+)?(?:problem|issue|bug)\s+(?:with\s+)?(.+?)(?:\.|$)",
    r"[Ss]truggling\s+with\s+(.+?)(?:\.|$)",
    r"[Ss]tuck\s+on\s+(.+?)(?:\.|$)",
    
    # Negation patterns
    r"(.+?)\s+(?:doesn't|does not|won't|isn't|is not)\s+work",
    r"(.+?)\s+(?:broken|failing|failed)",
    
    # Quick syntax
    r"MEMORY:\s*problem\s+(.+)",
    r"MEMORY:\s*issue\s+(.+)",
]
```

**Status Detection:**

```python
STATUS_PATTERNS = {
    "resolved": [
        r"\*\*[Ff]ixed:?\*\*",
        r"[Ff]ixed:?\s",
        r"[Rr]esolved:?\s",
        r"[Ss]olved:?\s",
        r"✓",
        r"\[x\]",
    ],
    "blocked": [
        r"[Bb]locked\s+(?:by|on)",
        r"[Ww]aiting\s+(?:for|on)",
        r"[Nn]eed(?:s)?\s+(?:to|more)",
    ],
    "open": []  # Default if no status detected
}
```

**Examples:**

| Input | Extracted | Status | Confidence |
|-------|-----------|--------|------------|
| `**Problem:** Safari CORS` | "Safari CORS" | open | 0.9 |
| `**Fixed:** Safari CORS - added preflight` | "Safari CORS" | resolved | 0.9 |
| `hit an issue with auth` | "auth" | open | 0.5 |
| `blocked on API access` | "API access" | blocked | 0.6 |

---

### Learning

Something discovered or understood.

**Extraction Patterns:**

```python
LEARNING_PATTERNS = [
    # Explicit format
    r"\*\*[Ll]earned:?\*\*\s*(.+)",
    r"\*\*[Tt][Ii][Ll]:?\*\*\s*(.+)",
    r"\*\*[Gg]otcha:?\*\*\s*(.+)",
    
    # Direct statements
    r"[Ll]earned\s+(?:that\s+)?(.+?)(?:\.|$)",
    r"[Dd]iscovered\s+(?:that\s+)?(.+?)(?:\.|$)",
    r"[Rr]ealized\s+(?:that\s+)?(.+?)(?:\.|$)",
    r"[Tt]urns\s+out\s+(?:that\s+)?(.+?)(?:\.|$)",
    r"[Ff]ound\s+out\s+(?:that\s+)?(.+?)(?:\.|$)",
    r"[Tt][Ii][Ll]:?\s*(.+?)(?:\.|$)",
    r"[Gg]otcha:?\s*(.+?)(?:\.|$)",
    
    # Quick syntax
    r"MEMORY:\s*learned\s+(.+)",
    r"MEMORY:\s*til\s+(.+)",
]
```

**Examples:**

| Input | Extracted | Confidence |
|-------|-----------|------------|
| `**Learned:** Safari needs -webkit prefix` | "Safari needs -webkit prefix" | 0.9 |
| `TIL: Edge functions can't use Node crypto` | "Edge functions can't use Node crypto" | 0.7 |
| `turns out Safari ITP is the cause` | "Safari ITP is the cause" | 0.6 |

---

### Edge (Project-Specific)

A gotcha specific to this project, extracted from the Gotchas section.

**Extraction Method:**

```python
def extract_project_edges(content: str) -> list[Edge]:
    """Extract edges from ## Gotchas section."""
    
    # Find Gotchas section
    gotchas_match = re.search(
        r'##\s*[Gg]otchas?\s*\n(.*?)(?=\n##|\Z)', 
        content, 
        re.DOTALL
    )
    
    if not gotchas_match:
        return []
    
    edges = []
    for line in gotchas_match.group(1).split('\n'):
        line = line.strip()
        if line.startswith('-') or line.startswith('*'):
            # Parse: "- Thing -> Workaround" or "- Thing - Workaround"
            parts = re.split(r'\s*[->\-:]\s*', line.lstrip('-* '), maxsplit=1)
            edge = Edge(
                title=parts[0].strip(),
                workaround=parts[1].strip() if len(parts) > 1 else None,
                source="project"
            )
            edges.append(edge)
    
    return edges
```

**Examples:**

```markdown
## Gotchas
- Safari ITP blocks cross-domain cookies -> use same-domain auth
- Our API rate limits to 100/min
- Edge functions timeout at 10s - use serverless for webhooks
```

Extracts:
1. `Safari ITP blocks cross-domain cookies` -> workaround: `use same-domain auth`
2. `Our API rate limits to 100/min` -> workaround: None
3. `Edge functions timeout at 10s` -> workaround: `use serverless for webhooks`

---

### Reasoning Extraction

When a decision or issue is found, look for reasoning nearby.

**Patterns:**

```python
REASONING_PATTERNS = [
    r"\bbecause\s+(.+?)(?:\.|$)",
    r"\bsince\s+(.+?)(?:\.|$)",
    r"\bso\s+(?:that\s+)?(.+?)(?:\.|$)",
    r"\bdue\s+to\s+(.+?)(?:\.|$)",
    r"\breason:?\s*(.+?)(?:\.|$)",
    r"\bwhy:?\s*(.+?)(?:\.|$)",
]
```

**Strategy:**

1. Check same line after entity match
2. Check next line if current line ends without reasoning
3. Look for `-` or `•` bullet points following

```python
def extract_reasoning(content: str, entity_line: int) -> Optional[str]:
    lines = content.split('\n')
    
    # Check same line
    current = lines[entity_line]
    for pattern in REASONING_PATTERNS:
        if match := re.search(pattern, current, re.I):
            return match.group(1).strip()
    
    # Check next line (if it's a continuation)
    if entity_line + 1 < len(lines):
        next_line = lines[entity_line + 1].strip()
        if next_line.startswith('-') or next_line.startswith('•'):
            return next_line.lstrip('-•').strip()
        for pattern in REASONING_PATTERNS:
            if match := re.search(pattern, next_line, re.I):
                return match.group(1).strip()
    
    return None
```

---

### Alternative Extraction

For decisions, extract what was rejected.

**Patterns:**

```python
ALTERNATIVE_PATTERNS = [
    r"\bover\s+(.+?)(?:\s+because|\.|$)",
    r"\binstead\s+of\s+(.+?)(?:\.|$)",
    r"\brather\s+than\s+(.+?)(?:\.|$)",
    r"\bnot\s+(.+?)(?:\s+because|\.|$)",
    r"\brejected:?\s*(.+?)(?:\.|$)",
]
```

---

## Inline Comment Parsing

### Detection

```python
MEMORY_COMMENT_PATTERNS = [
    r'//\s*MEMORY:\s*(.+)',           # JS/TS single line
    r'#\s*MEMORY:\s*(.+)',            # Python
    r'<!--\s*MEMORY:\s*(.+?)\s*-->',  # HTML/Svelte
    r'/\*\s*MEMORY:\s*(.+?)\s*\*/',   # Multi-line
]
```

### Processing

```python
def extract_from_code_file(path: str) -> list[Entity]:
    content = read_file(path)
    entities = []
    
    for line_num, line in enumerate(content.split('\n')):
        for pattern in MEMORY_COMMENT_PATTERNS:
            if match := re.search(pattern, line):
                memory_content = match.group(1)
                # Parse as if it were MEMORY.md content
                entity = parse_memory_line(memory_content, line_num, path)
                if entity:
                    entities.append(entity)
    
    return entities
```

### Examples

```typescript
// MEMORY: decided to use Zod for validation - runtime safety
// MEMORY: problem - TypeScript inference broken with generics
// MEMORY: learned - must use 'as const' for literal types
```

```python
# MEMORY: decided SQLite over Postgres - no server needed
# MEMORY: blocked on chromadb installation
```

```svelte
<!-- MEMORY: decided CSS modules over Tailwind - better scoping -->
<!-- MEMORY: issue - hydration mismatch on theme toggle -->
```

---

## Git Commit Parsing

### Detection

Monitor `.git/COMMIT_EDITMSG` or parse `git log`.

### Processing

```python
def extract_from_commit(message: str) -> list[Entity]:
    entities = []
    
    # Parse body (after first empty line)
    parts = message.split('\n\n', 1)
    if len(parts) > 1:
        body = parts[1]
        
        # Look for keyword lines
        for line in body.split('\n'):
            line = line.strip()
            if line.lower().startswith('decided:'):
                entities.append(parse_decision(line))
            elif line.lower().startswith('problem:'):
                entities.append(parse_issue(line))
            elif line.lower().startswith('learned:'):
                entities.append(parse_learning(line))
            elif line.lower().startswith('fixed:'):
                entities.append(parse_resolution(line))
    
    return entities
```

### Example Commit

```
feat: add JWT authentication

decided: JWT over sessions - stateless, scales better
learned: Safari ITP blocks third-party cookies
problem: refresh token flow not implemented yet
```

---

## Session Inference

Sessions are inferred from activity patterns, not explicit markers.

### Detection

```python
def infer_sessions(entries: list[Entry]) -> list[Session]:
    """Group entries into sessions based on time gaps."""
    
    SESSION_GAP = timedelta(hours=2)  # Gap that defines new session
    
    sessions = []
    current_session = None
    
    for entry in sorted(entries, key=lambda e: e.timestamp):
        if current_session is None:
            current_session = Session(start=entry.timestamp)
        elif entry.timestamp - current_session.last_activity > SESSION_GAP:
            # Gap too large, start new session
            sessions.append(current_session)
            current_session = Session(start=entry.timestamp)
        
        current_session.entries.append(entry)
        current_session.last_activity = entry.timestamp
    
    if current_session:
        sessions.append(current_session)
    
    return sessions
```

### Session Metadata

```python
class InferredSession(BaseModel):
    start: datetime
    end: datetime
    duration_minutes: int
    entries: list[Entry]
    decisions_count: int
    issues_opened: int
    issues_resolved: int
    learnings_count: int
    files_touched: list[str]
    
    @property
    def is_significant(self) -> bool:
        """Determine if session warrants highlight."""
        return (
            self.duration_minutes >= 30 or
            self.decisions_count >= 2 or
            self.issues_resolved >= 1 or
            self.learnings_count >= 2
        )
```

---

## Date Parsing

### Header Patterns

```python
DATE_PATTERNS = [
    r'^##\s*(\d{4}-\d{2}-\d{2})',           # ## 2024-12-12
    r'^##\s*(\w+\s+\d{1,2},?\s+\d{4})',     # ## December 12, 2024
    r'^##\s*(\w+\s+\d{1,2})',               # ## Dec 12 (assume current year)
    r'^---+\s*(\d{4}-\d{2}-\d{2})',         # --- 2024-12-12
]
```

### Processing

```python
def extract_date_context(content: str) -> dict[int, date]:
    """Map line numbers to their date context."""
    date_map = {}
    current_date = None
    
    for line_num, line in enumerate(content.split('\n')):
        for pattern in DATE_PATTERNS:
            if match := re.match(pattern, line):
                current_date = parse_date(match.group(1))
                break
        
        if current_date:
            date_map[line_num] = current_date
    
    return date_map
```

---

## Project State Extraction

### Parsing Project State Section

```python
def extract_project_state(content: str) -> ProjectState:
    """Extract from ## Project State section."""
    
    state_match = re.search(
        r'##\s*[Pp]roject\s*[Ss]tate\s*\n(.*?)(?=\n##|\Z)',
        content,
        re.DOTALL
    )
    
    if not state_match:
        return ProjectState()
    
    section = state_match.group(1)
    state = ProjectState()
    
    for line in section.split('\n'):
        line = line.strip()
        if match := re.match(r'-\s*[Gg]oal:?\s*(.+)', line):
            state.goal = match.group(1)
        elif match := re.match(r'-\s*[Ss]tack:?\s*(.+)', line):
            state.stack = [s.strip() for s in match.group(1).split(',')]
        elif match := re.match(r'-\s*[Bb]locked:?\s*(.+)', line):
            blocked = match.group(1).strip()
            state.blocked_by = None if blocked.lower() == 'none' else blocked
    
    return state
```

---

## Output Format

### Extracted Entity

```python
class ExtractedEntity(BaseModel):
    type: Literal["decision", "issue", "learning", "edge"]
    title: str
    content: str
    reasoning: Optional[str]
    alternatives: list[str]
    status: Optional[str]       # For issues
    source_file: str
    source_line: int
    date: Optional[date]
    confidence: float           # 0.0 - 1.0
    matched_pattern: str        # Which pattern matched
```

### Parsing Result

```python
class ParseResult(BaseModel):
    project_state: ProjectState
    entities: list[ExtractedEntity]
    sessions: list[InferredSession]
    project_edges: list[Edge]
    parse_errors: list[ParseError]
    stats: ParseStats

class ParseStats(BaseModel):
    lines_processed: int
    entities_found: int
    high_confidence: int        # confidence >= 0.8
    medium_confidence: int      # 0.5 <= confidence < 0.8
    low_confidence: int         # confidence < 0.5
```

---

## Error Handling

### Ambiguous Matches

When multiple patterns match, pick highest confidence:

```python
def resolve_ambiguous(matches: list[Match]) -> Match:
    return max(matches, key=lambda m: m.confidence)
```

### False Positive Mitigation

Skip common false positives:

```python
FALSE_POSITIVE_PATTERNS = [
    r"i\s+decided\s+not\s+to",      # Negation
    r"haven't\s+decided",            # Haven't decided
    r"should\s+we\s+decide",         # Question
    r"if\s+we\s+decide",             # Hypothetical
    r"might\s+decide",               # Uncertainty
]

def is_false_positive(line: str) -> bool:
    for pattern in FALSE_POSITIVE_PATTERNS:
        if re.search(pattern, line, re.I):
            return True
    return False
```

### Graceful Degradation

```python
def parse_safely(content: str) -> ParseResult:
    try:
        return full_parse(content)
    except Exception as e:
        # Return partial results
        return ParseResult(
            entities=[],
            parse_errors=[ParseError(str(e))],
            stats=ParseStats(lines_processed=0)
        )
```
