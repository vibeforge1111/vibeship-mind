# Mind Daemon Specification

## Overview

The Mind daemon is a background process that handles automatic memory capture and context injection. It eliminates the need for explicit session management.

---

## Responsibilities

| Task | Description |
|------|-------------|
| File watching | Monitor MEMORY.md and code files for changes |
| Parsing | Extract entities from file changes |
| Indexing | Update search embeddings |
| Session detection | Infer session boundaries from activity |
| Context injection | Update MIND:CONTEXT in CLAUDE.md |
| Feedback generation | Add inline suggestions to MEMORY.md |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Mind Daemon                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ File Watcher │  │   Parser     │  │   Indexer    │       │
│  │              │──│              │──│              │       │
│  │ inotify/     │  │ Loose regex  │  │ Embeddings   │       │
│  │ FSEvents     │  │ extraction   │  │ SQLite       │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                                    │               │
│         ▼                                    ▼               │
│  ┌──────────────┐                    ┌──────────────┐       │
│  │  Activity    │                    │   Context    │       │
│  │  Tracker     │                    │  Generator   │       │
│  │              │                    │              │       │
│  │ Session      │                    │ MIND:CONTEXT │       │
│  │ boundaries   │                    │ injection    │       │
│  └──────────────┘                    └──────────────┘       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## File Watching

### Watched Paths

For each registered project:

```python
WATCHED_PATTERNS = [
    '.mind/MEMORY.md',           # Primary memory file
    '**/*.ts',                   # TypeScript
    '**/*.tsx',                  # React TypeScript
    '**/*.js',                   # JavaScript
    '**/*.jsx',                  # React JavaScript
    '**/*.py',                   # Python
    '**/*.svelte',               # Svelte
    '**/*.vue',                  # Vue
    '**/*.rs',                   # Rust
    '**/*.go',                   # Go
    '.git/COMMIT_EDITMSG',       # Git commits
]

IGNORED_PATTERNS = [
    'node_modules/**',
    '.git/**',                   # Except COMMIT_EDITMSG
    '.mind/.index/**',
    'dist/**',
    'build/**',
    '__pycache__/**',
    '.venv/**',
]
```

### Implementation

```python
import asyncio
from watchfiles import awatch

class FileWatcher:
    def __init__(self):
        self.projects: dict[str, ProjectWatch] = {}
        self.event_queue: asyncio.Queue = asyncio.Queue()
    
    def add_project(self, path: str):
        self.projects[path] = ProjectWatch(
            path=path,
            patterns=WATCHED_PATTERNS,
            ignored=IGNORED_PATTERNS
        )
    
    async def watch(self):
        """Watch all registered projects."""
        watchers = [
            self._watch_project(p) for p in self.projects.values()
        ]
        await asyncio.gather(*watchers)
    
    async def _watch_project(self, project: ProjectWatch):
        async for changes in awatch(project.path, watch_filter=project.filter):
            for change_type, path in changes:
                await self.event_queue.put(FileEvent(
                    type=change_type,
                    path=path,
                    project=project.path,
                    timestamp=datetime.now()
                ))
```

### Debouncing

Rapid changes are debounced to avoid excessive parsing:

```python
class Debouncer:
    def __init__(self, delay_ms: int = 100):
        self.delay = delay_ms / 1000
        self.pending: dict[str, asyncio.Task] = {}
    
    async def debounce(self, key: str, callback: Callable):
        if key in self.pending:
            self.pending[key].cancel()
        
        self.pending[key] = asyncio.create_task(
            self._delayed_call(key, callback)
        )
    
    async def _delayed_call(self, key: str, callback: Callable):
        await asyncio.sleep(self.delay)
        del self.pending[key]
        await callback()
```

---

## Session Detection

### Activity Tracking

```python
class ActivityTracker:
    def __init__(self, inactivity_threshold_minutes: int = 30):
        self.threshold = timedelta(minutes=inactivity_threshold_minutes)
        self.sessions: dict[str, ActiveSession] = {}
    
    def on_activity(self, project_path: str):
        """Record activity for a project."""
        now = datetime.now()
        
        if project_path not in self.sessions:
            self.sessions[project_path] = ActiveSession(
                start=now,
                last_activity=now
            )
        else:
            session = self.sessions[project_path]
            
            # Check if this is a new session (gap too large)
            if now - session.last_activity > self.threshold:
                # End previous session
                self._end_session(project_path, session)
                # Start new session
                self.sessions[project_path] = ActiveSession(
                    start=now,
                    last_activity=now
                )
            else:
                session.last_activity = now
    
    async def check_inactive(self):
        """Called periodically to detect ended sessions."""
        now = datetime.now()
        ended = []
        
        for project_path, session in self.sessions.items():
            if now - session.last_activity > self.threshold:
                ended.append((project_path, session))
        
        for project_path, session in ended:
            await self._end_session(project_path, session)
            del self.sessions[project_path]
    
    async def _end_session(self, project_path: str, session: ActiveSession):
        """Finalize session: update index, inject context."""
        # Trigger context generation
        await context_generator.generate(project_path)
```

### Session Boundaries

| Event | Interpretation |
|-------|----------------|
| First file change in project | Session start |
| 30+ min inactivity | Session end |
| Git commit | Activity (not session end) |
| Daemon restart | Previous sessions closed |

---

## Context Generation

### MIND:CONTEXT Structure

```python
class ContextGenerator:
    def __init__(self, storage: Storage, parser: Parser):
        self.storage = storage
        self.parser = parser
    
    async def generate(self, project_path: str) -> str:
        """Generate MIND:CONTEXT section."""
        
        # Get parsed data
        entities = await self.storage.get_entities(project_path)
        state = await self.storage.get_project_state(project_path)
        sessions = await self.storage.get_sessions(project_path)
        edges = await self.storage.get_edges(project_path)
        global_edges = await self.storage.get_global_edges(state.stack)
        
        # Build context
        context = self._build_context(
            state=state,
            entities=entities,
            sessions=sessions,
            project_edges=edges,
            global_edges=global_edges
        )
        
        # Inject into CLAUDE.md
        await self._inject_context(project_path, context)
        
        return context
    
    def _build_context(self, **kwargs) -> str:
        """Build the MIND:CONTEXT markdown section."""
        
        sections = []
        
        # Session context
        sections.append(self._session_context(kwargs['sessions']))
        
        # Project state
        sections.append(self._project_state(kwargs['state']))
        
        # Recent decisions
        sections.append(self._recent_decisions(kwargs['entities']))
        
        # Open loops (proactive prompts)
        sections.append(self._open_loops(kwargs['entities']))
        
        # Gotchas
        sections.append(self._gotchas(
            kwargs['project_edges'], 
            kwargs['global_edges']
        ))
        
        # Continue from
        sections.append(self._continue_from(kwargs['sessions']))
        
        return self._wrap_context('\n\n'.join(filter(None, sections)))
    
    def _wrap_context(self, content: str) -> str:
        return f"""<!-- MIND:CONTEXT - Auto-generated by Mind. Do not edit. -->
{content}
<!-- MIND:END -->"""
```

### Open Loops Detection

```python
def _open_loops(self, entities: list[Entity]) -> Optional[str]:
    """Detect unfinished business to prompt Claude."""
    
    loops = []
    
    # Issues open for > 2 sessions
    old_issues = [
        e for e in entities 
        if e.type == 'issue' 
        and e.status == 'open'
        and e.sessions_ago >= 2
    ]
    for issue in old_issues:
        loops.append(f"⚠️ {issue.title} - open for {issue.sessions_ago} sessions")
    
    # Mentioned "next" but not started
    next_items = self._find_unstarted_next_items(entities)
    for item in next_items:
        loops.append(f"⚠️ \"{item}\" - noted as next step, not started")
    
    # Decisions older than 2 weeks that might need revisiting
    stale_decisions = [
        e for e in entities
        if e.type == 'decision'
        and e.age_days > 14
        and 'mvp' in e.content.lower()  # MVP decisions often need revisiting
    ]
    for decision in stale_decisions:
        loops.append(f"📋 {decision.title} ({decision.age_days}d ago) - still valid?")
    
    if not loops:
        return None
    
    return "## Open Loops\n" + '\n'.join(loops)
```

### CLAUDE.md Injection

```python
async def _inject_context(self, project_path: str, context: str):
    """Inject MIND:CONTEXT into CLAUDE.md."""
    
    claude_md_path = os.path.join(project_path, 'CLAUDE.md')
    
    if os.path.exists(claude_md_path):
        content = read_file(claude_md_path)
        
        # Remove existing MIND:CONTEXT
        content = re.sub(
            r'<!-- MIND:CONTEXT.*?<!-- MIND:END -->\n*',
            '',
            content,
            flags=re.DOTALL
        )
        
        # Inject at top
        content = context + '\n\n' + content.lstrip()
    else:
        # Create new CLAUDE.md
        content = context + '\n\n# Project Instructions\n\n(Add your instructions here)\n'
    
    # Atomic write
    temp_path = claude_md_path + '.tmp'
    write_file(temp_path, content)
    os.rename(temp_path, claude_md_path)
```

---

## Feedback Generation

### Inline Feedback in MEMORY.md

```python
class FeedbackGenerator:
    def generate(self, entities: list[Entity]) -> list[Feedback]:
        feedback = []
        
        # Vague decisions
        for entity in entities:
            if entity.type == 'decision' and entity.confidence < 0.6:
                if not entity.reasoning:
                    feedback.append(Feedback(
                        line=entity.source_line,
                        message="Decision missing reasoning. Why this choice?"
                    ))
        
        # Stale open issues
        for entity in entities:
            if entity.type == 'issue' and entity.status == 'open':
                if entity.age_days > 7:
                    feedback.append(Feedback(
                        line=entity.source_line,
                        message=f"Issue open {entity.age_days} days. Still relevant?"
                    ))
        
        return feedback
    
    def inject_feedback(self, content: str, feedback: list[Feedback]) -> str:
        """Insert HTML comments after relevant lines."""
        
        # Remove old feedback
        content = re.sub(r'<!-- MIND:.*?-->\n?', '', content)
        
        # Insert new feedback (reverse order to preserve line numbers)
        lines = content.split('\n')
        for fb in sorted(feedback, key=lambda f: -f.line):
            comment = f"<!-- MIND: {fb.message} -->"
            lines.insert(fb.line + 1, comment)
        
        return '\n'.join(lines)
```

---

## Daemon Lifecycle

### Starting

```python
async def start_daemon():
    """Start the Mind daemon."""
    
    # Check if already running
    pid_file = os.path.expanduser('~/.mind/daemon.pid')
    if os.path.exists(pid_file):
        pid = int(read_file(pid_file))
        if is_process_running(pid):
            raise DaemonError("Daemon already running")
    
    # Write PID
    write_file(pid_file, str(os.getpid()))
    
    # Initialize components
    config = load_config()
    projects = load_projects()
    
    watcher = FileWatcher()
    parser = Parser()
    indexer = Indexer()
    tracker = ActivityTracker()
    generator = ContextGenerator(indexer, parser)
    
    # Register projects
    for project in projects:
        watcher.add_project(project.path)
    
    # Start main loop
    daemon = MindDaemon(watcher, parser, indexer, tracker, generator)
    await daemon.run()
```

### Main Loop

```python
class MindDaemon:
    async def run(self):
        """Main daemon loop."""
        
        # Start file watcher
        watcher_task = asyncio.create_task(self.watcher.watch())
        
        # Start inactivity checker
        checker_task = asyncio.create_task(self._check_inactive_loop())
        
        # Process events
        while True:
            try:
                event = await asyncio.wait_for(
                    self.watcher.event_queue.get(),
                    timeout=1.0
                )
                await self._handle_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Event handling error: {e}")
    
    async def _handle_event(self, event: FileEvent):
        """Handle a file change event."""
        
        # Track activity
        self.tracker.on_activity(event.project)
        
        # Determine event type
        if event.path.endswith('MEMORY.md'):
            await self._handle_memory_change(event)
        elif self._is_code_file(event.path):
            await self._handle_code_change(event)
        elif 'COMMIT_EDITMSG' in event.path:
            await self._handle_commit(event)
    
    async def _handle_memory_change(self, event: FileEvent):
        """Parse MEMORY.md and update index."""
        
        content = read_file(event.path)
        result = self.parser.parse(content)
        
        await self.indexer.update(event.project, result.entities)
    
    async def _check_inactive_loop(self):
        """Periodically check for inactive sessions."""
        
        while True:
            await asyncio.sleep(60)  # Check every minute
            await self.tracker.check_inactive()
```

### Stopping

```python
async def stop_daemon():
    """Stop the Mind daemon."""
    
    pid_file = os.path.expanduser('~/.mind/daemon.pid')
    if not os.path.exists(pid_file):
        raise DaemonError("Daemon not running")
    
    pid = int(read_file(pid_file))
    
    # Send SIGTERM
    os.kill(pid, signal.SIGTERM)
    
    # Wait for exit
    for _ in range(30):
        if not is_process_running(pid):
            break
        await asyncio.sleep(0.1)
    
    # Clean up PID file
    os.remove(pid_file)
```

### Signal Handling

```python
def setup_signal_handlers():
    """Setup graceful shutdown handlers."""
    
    async def shutdown(sig):
        logger.info(f"Received {sig}, shutting down...")
        
        # Finalize all active sessions
        for project_path in tracker.sessions:
            await generator.generate(project_path)
        
        # Clean up
        os.remove(os.path.expanduser('~/.mind/daemon.pid'))
        
        sys.exit(0)
    
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s)))
```

---

## Auto-Start (Optional)

### macOS (launchd)

```xml
<!-- ~/Library/LaunchAgents/com.mind.daemon.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mind.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/mind</string>
        <string>daemon</string>
        <string>run</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/mind.out.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/mind.err.log</string>
</dict>
</plist>
```

### Linux (systemd)

```ini
# ~/.config/systemd/user/mind.service
[Unit]
Description=Mind Memory Daemon
After=default.target

[Service]
Type=simple
ExecStart=/usr/local/bin/mind daemon run
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

### Windows (Task Scheduler)

```powershell
# Create scheduled task
$action = New-ScheduledTaskAction -Execute "mind" -Argument "daemon run"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "MindDaemon" -Action $action -Trigger $trigger -Settings $settings
```

---

## Configuration

### Config File

```toml
# ~/.mind/config.toml

[daemon]
inactivity_minutes = 30
check_interval_seconds = 60
debounce_ms = 100
log_level = "info"

[parser]
confidence_threshold = 0.3  # Minimum confidence to store
include_low_confidence = true

[context]
max_decisions = 5
max_open_loops = 3
max_gotchas = 5
show_stale_after_days = 14

[feedback]
enabled = true
vague_decision_threshold = 0.6
stale_issue_days = 7
```

### Per-Project Overrides

```toml
# project/.mind/config.toml

[daemon]
inactivity_minutes = 45  # Longer for this project

[context]
max_gotchas = 10  # More gotchas relevant
```

---

## Logging

### Log Locations

```
~/.mind/logs/
├── daemon.log        # Main daemon log
├── parser.log        # Parsing events
├── index.log         # Indexing events
└── errors.log        # Errors only
```

### Log Format

```python
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    level=logging.INFO
)

# Example output:
# 2024-12-12 15:30:45 [INFO] watcher: File changed: /project/.mind/MEMORY.md
# 2024-12-12 15:30:45 [INFO] parser: Extracted 2 decisions, 1 issue
# 2024-12-12 15:30:45 [INFO] indexer: Updated embeddings for project
# 2024-12-12 16:00:45 [INFO] tracker: Session ended for /project (30m inactivity)
# 2024-12-12 16:00:46 [INFO] generator: Updated CLAUDE.md for /project
```

---

## Health Checks

### Status Command

```bash
$ mind daemon status

Mind Daemon Status
──────────────────
Status: Running
PID: 12345
Uptime: 2h 34m
Memory: 45 MB

Projects Watching: 3
  /Users/cem/vibeship-mind (active, last: 5m ago)
  /Users/cem/vibeship-scanner (idle, last: 2h ago)
  /Users/cem/vibeship-spawner (idle, last: 1d ago)

Last Index: 5 minutes ago
Total Entities: 156
Global Edges: 12
```

### Doctor Command

```bash
$ mind doctor

Mind Health Check
─────────────────
[✓] Daemon running
[✓] Config valid
[✓] Projects registered: 3
[✓] All MEMORY.md files accessible
[✓] Index not corrupted
[⚠] Project 'vibeship-spawner' has stale MIND:CONTEXT (1d old)
[✓] Global edges loaded: 12

Recommendations:
- Run `mind index` for vibeship-spawner to refresh context
```
