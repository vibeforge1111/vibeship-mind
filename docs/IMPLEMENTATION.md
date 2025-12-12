# Mind Implementation Plan

## Overview

This document outlines the implementation phases for Mind, a file-based memory system for AI coding assistants.

---

## Target Architecture

```
src/mind/
├── cli.py               # CLI commands
├── daemon.py            # Background daemon
├── watcher.py           # File system watcher
├── parser.py            # Loose markdown parser
├── indexer.py           # Search index management
├── context.py           # MIND:CONTEXT generation
├── storage/
│   ├── sqlite.py        # Simplified schema
│   └── embeddings.py    # Vector search
├── mcp/
│   └── server.py        # 4 MCP tools
└── edges/
    ├── detector.py      # Edge detection
    └── global_edges.py  # Global edge storage
```

### Core Components

| Component | Purpose |
|-----------|---------|
| Source of truth | .mind/MEMORY.md |
| MCP tools | 4 (search, edges, add_global_edge, status) |
| Session tracking | Inferred from activity |
| Context delivery | CLAUDE.md injection |
| Parsing | Loose regex, confidence scoring |

---

## Phase 1: Foundation

**Duration:** 1 week
**Goal:** Basic file-based capture working

### Tasks

#### 1.1 Create MEMORY.md Template

```python
# src/mind/templates.py

MEMORY_TEMPLATE = """<!-- MIND MEMORY - Append as you work. Write naturally.
Keywords: decided, problem, learned, tried, fixed, blocked, todo -->

# {project_name}

## Project State
- Goal: 
- Stack: {stack}
- Blocked: None

## Gotchas
<!-- Project-specific gotchas -->

---

## Session Log

## {date}

(Start writing here)

---
"""
```

#### 1.2 Implement `mind init`

```python
# src/mind/cli.py

@cli.command()
@click.argument('path', default='.')
def init(path: str):
    """Initialize Mind for a project."""
    
    project_path = Path(path).resolve()
    mind_dir = project_path / '.mind'
    
    # Create directories
    mind_dir.mkdir(exist_ok=True)
    (mind_dir / '.index').mkdir(exist_ok=True)
    
    # Detect stack
    stack = detect_stack(project_path)
    
    # Create MEMORY.md
    memory_file = mind_dir / 'MEMORY.md'
    if not memory_file.exists():
        content = MEMORY_TEMPLATE.format(
            project_name=project_path.name,
            stack=', '.join(stack) if stack else '(add your stack)',
            date=date.today().isoformat()
        )
        memory_file.write_text(content)
    
    # Create .gitignore
    gitignore = mind_dir / '.gitignore'
    gitignore.write_text('.index/\n')
    
    # Update CLAUDE.md
    update_claude_md(project_path, stack)
    
    # Register project
    register_project(project_path, stack)
    
    click.echo(f"✓ Mind initialized for {project_path.name}")
```

#### 1.3 Stack Detection

```python
# src/mind/detection.py

def detect_stack(project_path: Path) -> list[str]:
    """Auto-detect project stack from files."""
    
    stack = []
    
    # Package.json analysis
    pkg_json = project_path / 'package.json'
    if pkg_json.exists():
        pkg = json.loads(pkg_json.read_text())
        deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
        
        if 'svelte' in deps or '@sveltejs/kit' in deps:
            stack.append('sveltekit')
        if 'next' in deps:
            stack.append('nextjs')
        if 'react' in deps:
            stack.append('react')
        if 'vue' in deps:
            stack.append('vue')
        if 'typescript' in deps:
            stack.append('typescript')
        if 'tailwindcss' in deps:
            stack.append('tailwind')
    
    # Python analysis
    if (project_path / 'pyproject.toml').exists():
        stack.append('python')
        pyproject = (project_path / 'pyproject.toml').read_text()
        if 'fastapi' in pyproject.lower():
            stack.append('fastapi')
        if 'django' in pyproject.lower():
            stack.append('django')
    
    # Other files
    if (project_path / 'Cargo.toml').exists():
        stack.append('rust')
    if (project_path / 'go.mod').exists():
        stack.append('go')
    if (project_path / 'vercel.json').exists():
        stack.append('vercel')
    if (project_path / 'supabase').is_dir():
        stack.append('supabase')
    
    return stack
```

#### 1.4 CLAUDE.md Injection

```python
# src/mind/context.py

def update_claude_md(project_path: Path, stack: list[str]):
    """Add MIND:CONTEXT section to CLAUDE.md."""
    
    claude_md = project_path / 'CLAUDE.md'
    
    context = generate_initial_context(stack)
    
    if claude_md.exists():
        content = claude_md.read_text()
        # Remove existing MIND:CONTEXT
        content = re.sub(
            r'<!-- MIND:CONTEXT.*?<!-- MIND:END -->\n*',
            '',
            content,
            flags=re.DOTALL
        )
        content = context + '\n\n' + content.lstrip()
    else:
        content = context + '\n\n# Project Instructions\n\n'
    
    claude_md.write_text(content)

def generate_initial_context(stack: list[str]) -> str:
    """Generate initial MIND:CONTEXT."""
    
    # Get relevant global edges for stack
    edges = get_global_edges_for_stack(stack)
    
    edge_lines = []
    for edge in edges[:5]:  # Top 5
        edge_lines.append(f"- {edge.title}")
    
    return f"""<!-- MIND:CONTEXT - Auto-generated by Mind. Do not edit. -->
## Session Context
- Status: New project
- Stack: {', '.join(stack) if stack else 'Unknown'}

## Memory
Append notes to `.mind/MEMORY.md` as you work.
Use keywords: decided, problem, learned, tried, fixed

## Gotchas (This Stack)
{chr(10).join(edge_lines) if edge_lines else '(None loaded yet)'}
<!-- MIND:END -->"""
```

### Phase 1 Tests

```python
# tests/test_init.py

def test_mind_init_creates_structure():
    with temp_project() as project:
        result = runner.invoke(cli, ['init', str(project)])
        
        assert result.exit_code == 0
        assert (project / '.mind' / 'MEMORY.md').exists()
        assert (project / '.mind' / '.gitignore').exists()
        assert (project / 'CLAUDE.md').exists()

def test_stack_detection():
    with temp_project() as project:
        (project / 'package.json').write_text('{"dependencies": {"svelte": "4.0.0"}}')
        
        stack = detect_stack(project)
        
        assert 'sveltekit' in stack or 'svelte' in stack

def test_claude_md_injection():
    with temp_project() as project:
        (project / 'CLAUDE.md').write_text('# Existing Content\n\nSome instructions.')
        
        update_claude_md(project, ['python'])
        
        content = (project / 'CLAUDE.md').read_text()
        assert '<!-- MIND:CONTEXT' in content
        assert '# Existing Content' in content  # Preserved
```

### Phase 1 Deliverable

- `mind init` works
- Creates proper file structure
- Detects stack
- Injects basic MIND:CONTEXT

---

## Phase 2: Parser

**Duration:** 1 week
**Goal:** Extract entities from natural language

### Tasks

#### 2.1 Implement Loose Parser

```python
# src/mind/parser.py

class Parser:
    def parse(self, content: str) -> ParseResult:
        """Parse MEMORY.md content."""
        
        entities = []
        date_context = self._extract_date_context(content)
        
        for line_num, line in enumerate(content.split('\n')):
            # Skip empty, headers, comments
            if self._should_skip(line):
                continue
            
            # Try each entity type
            if entity := self._try_parse_decision(line, line_num, date_context):
                entities.append(entity)
            elif entity := self._try_parse_issue(line, line_num, date_context):
                entities.append(entity)
            elif entity := self._try_parse_learning(line, line_num, date_context):
                entities.append(entity)
        
        # Extract project state
        state = self._extract_project_state(content)
        
        # Extract project edges
        edges = self._extract_project_edges(content)
        
        return ParseResult(
            project_state=state,
            entities=entities,
            project_edges=edges
        )
    
    def _try_parse_decision(self, line: str, line_num: int, dates: dict) -> Optional[Entity]:
        for pattern in DECISION_PATTERNS:
            if match := re.search(pattern, line, re.I):
                return Entity(
                    type='decision',
                    title=match.group(1).strip(),
                    content=line,
                    reasoning=self._find_reasoning(line),
                    source_line=line_num,
                    date=dates.get(line_num),
                    confidence=self._score_confidence(line, 'decision')
                )
        return None
```

#### 2.2 Implement Inline Comment Scanner

```python
# src/mind/parser.py

class InlineScanner:
    PATTERNS = {
        '.py': r'#\s*MEMORY:\s*(.+)',
        '.ts': r'//\s*MEMORY:\s*(.+)',
        '.js': r'//\s*MEMORY:\s*(.+)',
        '.svelte': r'<!--\s*MEMORY:\s*(.+?)\s*-->',
    }
    
    def scan_file(self, path: Path) -> list[Entity]:
        """Scan code file for MEMORY: comments."""
        
        suffix = path.suffix
        if suffix not in self.PATTERNS:
            return []
        
        pattern = self.PATTERNS[suffix]
        content = path.read_text()
        entities = []
        
        for line_num, line in enumerate(content.split('\n')):
            if match := re.search(pattern, line):
                memory_content = match.group(1)
                entity = self.parser.parse_line(memory_content, line_num, str(path))
                if entity:
                    entities.append(entity)
        
        return entities
```

### Phase 2 Tests

```python
def test_parse_decision():
    parser = Parser()
    
    result = parser.parse("**Decided:** Use JWT because simpler")
    assert len(result.entities) == 1
    assert result.entities[0].type == 'decision'
    assert result.entities[0].confidence >= 0.8

def test_parse_natural_language():
    parser = Parser()
    
    result = parser.parse("decided to go with Supabase over Firebase")
    assert len(result.entities) == 1
    assert 'Supabase' in result.entities[0].title

def test_inline_comments():
    scanner = InlineScanner()
    
    with temp_file('.ts', '// MEMORY: decided JWT for auth') as f:
        entities = scanner.scan_file(f)
        assert len(entities) == 1
```

### Phase 2 Deliverable

- Parser extracts decisions, issues, learnings
- Confidence scoring works
- Inline comment scanning works

---

## Phase 3: Daemon & File Watching

**Duration:** 1 week
**Goal:** Automatic capture and context updates

### Tasks

#### 3.1 Implement File Watcher

```python
# src/mind/watcher.py

class FileWatcher:
    def __init__(self):
        self.projects: dict[str, Path] = {}
        self.debouncer = Debouncer(delay_ms=100)
    
    async def watch(self):
        """Watch all registered projects."""
        
        async for changes in awatch(*self.projects.values()):
            for change_type, path in changes:
                if self._should_process(path):
                    await self.debouncer.debounce(
                        path,
                        lambda: self._handle_change(change_type, path)
                    )
```

#### 3.2 Implement Activity Tracker

```python
# src/mind/daemon.py

class ActivityTracker:
    def __init__(self, timeout_minutes: int = 30):
        self.timeout = timedelta(minutes=timeout_minutes)
        self.sessions: dict[str, datetime] = {}
    
    def on_activity(self, project: str):
        self.sessions[project] = datetime.now()
    
    async def check_inactive(self) -> list[str]:
        """Return projects with ended sessions."""
        now = datetime.now()
        ended = []
        
        for project, last in list(self.sessions.items()):
            if now - last > self.timeout:
                ended.append(project)
                del self.sessions[project]
        
        return ended
```

#### 3.3 Implement Context Generator

```python
# src/mind/context.py

class ContextGenerator:
    def generate(self, project_path: str, entities: list[Entity]) -> str:
        """Generate MIND:CONTEXT section."""
        
        sections = [
            self._session_context(project_path),
            self._project_state(entities),
            self._recent_decisions(entities),
            self._open_loops(entities),
            self._gotchas(project_path, entities),
            self._continue_from(entities),
        ]
        
        content = '\n\n'.join(filter(None, sections))
        return f"<!-- MIND:CONTEXT -->\n{content}\n<!-- MIND:END -->"
```

### Phase 3 Tests

```python
def test_file_watcher_detects_changes():
    watcher = FileWatcher()
    watcher.add_project('/tmp/test-project')
    
    # Simulate file change
    Path('/tmp/test-project/.mind/MEMORY.md').write_text('updated')
    
    # Check event received
    ...

def test_activity_tracker_detects_inactivity():
    tracker = ActivityTracker(timeout_minutes=1)
    tracker.on_activity('/project')
    
    # Wait for timeout
    await asyncio.sleep(61)
    
    ended = await tracker.check_inactive()
    assert '/project' in ended
```

### Phase 3 Deliverable

- Daemon runs in background
- File changes trigger parsing
- Inactivity triggers context update
- CLAUDE.md auto-updated

---

## Phase 4: MCP Server

**Duration:** 1 week
**Goal:** 4 MCP tools working

### Tasks

#### 4.1 Implement `mind_search`

```python
# src/mind/mcp/server.py

@mcp.tool()
async def mind_search(
    query: str,
    scope: str = "project",
    types: list[str] = None,
    limit: int = 10
) -> dict:
    """Search across memories."""
    
    results = await indexer.search(
        query=query,
        scope=scope,
        types=types,
        limit=limit
    )
    
    return {
        "query": query,
        "total": len(results),
        "results": [r.to_dict() for r in results]
    }
```

#### 4.2 Implement `mind_edges`

```python
@mcp.tool()
async def mind_edges(
    intent: str,
    code: str = None,
    stack: list[str] = None
) -> list[dict]:
    """Check for gotchas."""
    
    warnings = await edge_detector.check(
        intent=intent,
        code=code,
        stack=stack or current_project_stack()
    )
    
    return [w.to_dict() for w in warnings]
```

#### 4.3 Implement `mind_add_global_edge`

```python
@mcp.tool()
async def mind_add_global_edge(
    title: str,
    description: str,
    workaround: str,
    detection: dict,
    stack_tags: list[str] = None,
    severity: str = "warning"
) -> dict:
    """Add cross-project gotcha."""
    
    edge = GlobalEdge(
        id=generate_id(),
        title=title,
        description=description,
        workaround=workaround,
        detection=EdgePatterns(**detection),
        stack_tags=stack_tags or [],
        severity=severity
    )
    
    await storage.add_global_edge(edge)
    
    return edge.to_dict()
```

#### 4.4 Implement `mind_status`

```python
@mcp.tool()
async def mind_status() -> dict:
    """Check Mind status."""
    
    return {
        "daemon": {
            "running": daemon_is_running(),
            "pid": get_daemon_pid(),
            "uptime_seconds": get_daemon_uptime()
        },
        "current_project": get_current_project_status(),
        "global_stats": get_global_stats()
    }
```

### Phase 4 Deliverable

- 4 MCP tools working
- Search returns relevant results
- Edge detection works
- Global edges can be added

---

## Phase 5: Polish

**Duration:** 1 week
**Goal:** Production ready

### Tasks

#### 5.1 Doctor Command

```python
@cli.command()
def doctor():
    """Run health checks."""
    
    checks = [
        ('Config valid', check_config),
        ('Daemon running', check_daemon),
        ('Projects registered', check_projects),
        ('Memory files accessible', check_memory_files),
        ('Index not corrupted', check_index),
        ('Global edges loaded', check_global_edges),
    ]
    
    for name, check in checks:
        try:
            result = check()
            status = '✓' if result.ok else '⚠'
            click.echo(f"[{status}] {name}")
            if result.message:
                click.echo(f"    {result.message}")
        except Exception as e:
            click.echo(f"[✗] {name}: {e}")
```

#### 5.2 Documentation

- Update README.md
- Document all CLI commands
- Add troubleshooting guide
- Write onboarding guide

### Phase 5 Deliverable

- Doctor command catches issues
- Documentation complete
- Ready for release

---

## Files to Create

| File | Purpose |
|------|---------|
| `src/mind/cli.py` | CLI commands |
| `src/mind/daemon.py` | Background daemon |
| `src/mind/watcher.py` | File watching |
| `src/mind/parser.py` | Loose parsing |
| `src/mind/context.py` | MIND:CONTEXT generation |
| `src/mind/indexer.py` | Search index |
| `src/mind/storage/sqlite.py` | Database |
| `src/mind/storage/embeddings.py` | Vector search |
| `src/mind/mcp/server.py` | MCP tools |
| `src/mind/edges/detector.py` | Edge detection |
| `src/mind/edges/global_edges.py` | Global edge storage |

---

## Testing Strategy

### Unit Tests

- Parser patterns
- Confidence scoring
- Stack detection
- Context generation

### Integration Tests

- File watcher → Parser → Indexer flow
- Daemon lifecycle
- MCP tools

### End-to-End Tests

- `mind init` creates working setup
- Claude can read MIND:CONTEXT
- Memories accumulate over sessions
- Search finds relevant results

---

## Rollout Plan

1. **Alpha (Week 1-2):** Core team testing
2. **Beta (Week 3-4):** Expanded testing, feedback
3. **RC (Week 5):** Bug fixes, polish
4. **Release (Week 6):** Public release

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Memories per session | > 2 average |
| CLAUDE.md context used | > 80% of sessions |
| Parser false positives | < 10% |
| Daemon uptime | > 99% |
