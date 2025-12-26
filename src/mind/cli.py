"""Mind CLI - File-based memory for AI coding assistants (v2: daemon-free)."""

import json
from datetime import date
from pathlib import Path

import click

from . import __version__
from .legacy.context import update_claude_md
from .detection import detect_stack
from .legacy.parser import InlineScanner, Parser
from .storage import ProjectsRegistry, get_global_mind_dir, get_self_improve_path
from .config import create_default_config, load_config, save_config
from .templates import GITIGNORE_CONTENT, MEMORY_TEMPLATE, SESSION_TEMPLATE, REMINDERS_TEMPLATE, SELF_IMPROVE_TEMPLATE
from .preferences import (
    has_existing_preferences,
    load_global_preferences,
    save_global_preferences,
    get_default_preferences,
    update_last_project,
)
from .stack import detect_stack as detect_editor_stack, inject_mind_instructions, get_stack_display_name
from .health import auto_repair


@click.group()
@click.version_option(version=__version__, prog_name="mind")
def cli():
    """Mind - File-based memory for AI coding assistants."""
    pass


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option("--quick", "-q", is_flag=True, help="Skip interactive setup, use defaults or existing preferences")
def init(path: str, quick: bool):
    """Initialize Mind for a project.

    PATH is the project directory to initialize. Defaults to current directory.

    Interactive setup asks 3 questions on first install. Use --quick to skip.

    When running from another directory via uv --directory, you MUST specify
    the target path explicitly:

        uv --directory /path/to/vibeship-mind run mind init /path/to/your/project
    """
    project_path = Path(path).resolve()

    # Warn if path is "." and we might be in the wrong directory
    # (common mistake when using uv --directory)
    if path == "." and project_path.name == "vibeship-mind":
        click.echo("Warning: Initializing vibeship-mind itself.", err=True)
        click.echo("If you meant to init a different project, specify the path:", err=True)
        click.echo("  uv --directory /path/to/vibeship-mind run mind init /path/to/your/project", err=True)
        click.echo()

    click.echo()
    click.echo("Welcome to Mind! Let me set things up for you.")
    click.echo()

    # Check for existing preferences
    existing_prefs = load_global_preferences()

    if existing_prefs and not quick:
        # Returning user - offer to reuse preferences
        click.echo("Found your Mind preferences from other projects:")
        click.echo(f"  - Logging: {existing_prefs.get('logging_level', 'balanced').title()}")
        click.echo(f"  - Auto-promote: {'Yes' if existing_prefs.get('auto_promote', True) else 'No'}")
        click.echo(f"  - Memory aging: {existing_prefs.get('retention_mode', 'smart').title()}")
        click.echo()

        reuse = click.confirm("Use these settings?", default=True)
        if reuse:
            prefs = existing_prefs
        else:
            prefs = _interactive_setup()
    elif quick and existing_prefs:
        # Quick mode with existing prefs
        prefs = existing_prefs
    elif quick:
        # Quick mode without existing prefs - use defaults
        prefs = get_default_preferences()
    else:
        # First install - interactive setup
        prefs = _interactive_setup()

    # Save preferences globally
    save_global_preferences(prefs)

    # Create .mind directory
    mind_dir = project_path / ".mind"
    mind_dir.mkdir(exist_ok=True)

    # Ensure global Mind directory exists with SELF_IMPROVE.md
    global_dir = get_global_mind_dir()
    self_improve_file = get_self_improve_path()
    if not self_improve_file.exists():
        self_improve_file.write_text(SELF_IMPROVE_TEMPLATE)
        click.echo(f"[+] Created global ~/.mind/SELF_IMPROVE.md")
    else:
        click.echo(f"[.] Global ~/.mind/SELF_IMPROVE.md already exists (preserved)")

    # Create .mind/.gitignore
    gitignore = mind_dir / ".gitignore"
    gitignore.write_text(GITIGNORE_CONTENT)

    # Detect tech stack
    stack = detect_stack(project_path)
    stack_str = ", ".join(stack) if stack else "(add your stack)"

    # Detect editor stack
    editor_stack = detect_editor_stack(project_path)
    editor_name = get_stack_display_name(editor_stack)

    # Create MEMORY.md (don't overwrite if exists)
    memory_file = mind_dir / "MEMORY.md"
    if not memory_file.exists():
        content = MEMORY_TEMPLATE.format(
            project_name=project_path.name,
            stack=stack_str,
            date=date.today().isoformat(),
        )
        memory_file.write_text(content)
        click.echo("[+] Created .mind/MEMORY.md")
    else:
        click.echo("[.] .mind/MEMORY.md already exists (preserved)")

    # Create SESSION.md (don't overwrite if exists)
    session_file = mind_dir / "SESSION.md"
    if not session_file.exists():
        session_content = SESSION_TEMPLATE.format(date=date.today().isoformat())
        session_file.write_text(session_content)
        click.echo("[+] Created .mind/SESSION.md")
    else:
        click.echo("[.] .mind/SESSION.md already exists (preserved)")

    # Create REMINDERS.md (don't overwrite if exists)
    reminders_file = mind_dir / "REMINDERS.md"
    if not reminders_file.exists():
        reminders_file.write_text(REMINDERS_TEMPLATE)
        click.echo("[+] Created .mind/REMINDERS.md")
    else:
        click.echo("[.] .mind/REMINDERS.md already exists (preserved)")

    # Create/update config.json with user preferences
    config_file = mind_dir / "config.json"
    if not config_file.exists():
        # Create new config with preferences
        config = {
            "version": 2,
            "mascot": True,
            "logging": {
                "level": prefs.get("logging_level", "balanced"),
                "auto_categorize": True,
            },
            "session": {
                "auto_promote": prefs.get("auto_promote", True),
                "promote_threshold": 0.5,
            },
            "memory": {
                "retention_mode": prefs.get("retention_mode", "smart"),
                "decay_period_days": 30,
                "decay_rate": 0.1,
                "min_relevance": 0.2,
            },
            "health": {
                "auto_repair": True,
            },
            "stack": {
                "detected": editor_stack,
                "config_file": str(inject_mind_instructions(project_path, editor_stack)["config_file"].name),
            },
            "self_improve": {
                "enabled": True,
                "decay": True,
                "reinforcement": True,
                "contradiction": True,
                "learning_style": True,
            },
        }
        save_config(project_path, config)
        click.echo("[+] Created .mind/config.json")
    else:
        click.echo("[.] .mind/config.json already exists (preserved)")

    # Inject Mind instructions into editor config file
    inject_result = inject_mind_instructions(project_path, editor_stack)
    if inject_result["success"]:
        if inject_result["action"] == "created":
            click.echo(f"[+] Added Mind instructions to {inject_result['config_file'].name}")
        elif inject_result["action"] == "updated":
            click.echo(f"[+] Updated Mind instructions in {inject_result['config_file'].name}")
        else:
            click.echo(f"[.] Mind instructions already in {inject_result['config_file'].name}")

    # Also update CLAUDE.md with MIND:CONTEXT (for backwards compatibility)
    update_claude_md(project_path, stack)
    click.echo("[+] Updated CLAUDE.md with MIND:CONTEXT")

    # Show detected stack
    click.echo(f"[+] Detected editor: {editor_name}")
    if stack:
        click.echo(f"[+] Detected tech stack: {', '.join(stack)}")
    else:
        click.echo("[.] No tech stack detected (update .mind/MEMORY.md manually)")

    # Update last project in global preferences
    update_last_project(project_path)

    # Register project
    registry = ProjectsRegistry.load()
    registry.register(project_path, stack)
    click.echo("[+] Registered project with Mind")

    # Run auto-repair to ensure everything is healthy
    repair_result = auto_repair(project_path)
    if repair_result["repaired_count"] > 0:
        click.echo(f"[+] Auto-repaired {repair_result['repaired_count']} issue(s)")

    click.echo()
    click.echo("Mind is ready! I'll remember what matters.")
    click.echo()
    click.echo("Settings:")
    click.echo(f"  - Logging: {prefs.get('logging_level', 'balanced').title()}")
    click.echo(f"  - Auto-promote: {'Yes' if prefs.get('auto_promote', True) else 'No'}")
    click.echo(f"  - Memory aging: {prefs.get('retention_mode', 'smart').title()}")


def _interactive_setup() -> dict:
    """Run interactive setup questions and return preferences."""
    click.echo()

    # Question 1: Logging level
    click.echo("? How much should I remember?")
    logging_choices = [
        ("balanced", "Balanced - Key moments + context (recommended)"),
        ("efficient", "Efficient - Only critical decisions and blockers"),
        ("detailed", "Detailed - Everything, compacted to Memory periodically"),
    ]
    for i, (_, desc) in enumerate(logging_choices, 1):
        click.echo(f"  {i}. {desc}")

    logging_choice = click.prompt("Choose", type=click.IntRange(1, 3), default=1)
    logging_level = logging_choices[logging_choice - 1][0]
    click.echo()

    # Question 2: Auto-promote
    click.echo("? Should learnings auto-promote to long-term memory?")
    promote_choices = [
        (True, "Yes - Good insights move from Session to Memory automatically"),
        (False, "No - I'll decide what to keep"),
    ]
    for i, (_, desc) in enumerate(promote_choices, 1):
        click.echo(f"  {i}. {desc}")

    promote_choice = click.prompt("Choose", type=click.IntRange(1, 2), default=1)
    auto_promote = promote_choices[promote_choice - 1][0]
    click.echo()

    # Question 3: Retention mode
    click.echo("? How should memories age over time?")
    retention_choices = [
        ("smart", "Smart - Frequently-used memories stay strong, unused ones fade"),
        ("keep_all", "Keep all - Everything stays at full strength forever"),
    ]
    for i, (_, desc) in enumerate(retention_choices, 1):
        click.echo(f"  {i}. {desc}")

    retention_choice = click.prompt("Choose", type=click.IntRange(1, 2), default=1)
    retention_mode = retention_choices[retention_choice - 1][0]
    click.echo()

    return {
        "version": 1,
        "logging_level": logging_level,
        "auto_promote": auto_promote,
        "retention_mode": retention_mode,
        "created": date.today().isoformat(),
    }


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--inline", is_flag=True, help="Also scan code files for MEMORY: comments")
def parse(path: str, as_json: bool, inline: bool):
    """Parse MEMORY.md and show extracted entities."""
    project_path = Path(path).resolve()
    memory_file = project_path / ".mind" / "MEMORY.md"

    if not memory_file.exists():
        click.echo(f"Error: {memory_file} not found. Run 'mind init' first.", err=True)
        raise SystemExit(1)

    parser = Parser()
    content = memory_file.read_text(encoding="utf-8")
    result = parser.parse(content, source_file=str(memory_file))

    # Optionally scan inline comments
    inline_entities = []
    if inline:
        scanner = InlineScanner()
        inline_entities = scanner.scan_directory(project_path)

    if as_json:
        output = {
            "project_state": {
                "goal": result.project_state.goal,
                "stack": result.project_state.stack,
                "blocked_by": result.project_state.blocked_by,
            },
            "entities": [
                {
                    "type": e.type.value,
                    "title": e.title,
                    "content": e.content,
                    "confidence": e.confidence,
                    "reasoning": e.reasoning,
                    "status": e.status.value if e.status else None,
                    "date": e.date.isoformat() if e.date else None,
                    "source_file": e.source_file,
                    "source_line": e.source_line,
                }
                for e in result.entities + inline_entities
            ],
            "edges": [
                {"title": e.title, "workaround": e.workaround}
                for e in result.project_edges
            ],
        }
        click.echo(json.dumps(output, indent=2))
    else:
        # Human-readable output
        click.echo("=== Project State ===")
        click.echo(f"Goal: {result.project_state.goal or '(not set)'}")
        click.echo(f"Stack: {', '.join(result.project_state.stack) or '(not set)'}")
        click.echo(f"Blocked: {result.project_state.blocked_by or 'None'}")
        click.echo()

        if result.entities or inline_entities:
            click.echo("=== Entities ===")
            for e in result.entities + inline_entities:
                status_str = f" [{e.status.value}]" if e.status else ""
                date_str = f" ({e.date})" if e.date else ""
                confidence_str = f" [{e.confidence:.0%}]"
                click.echo(f"[{e.type.value}]{status_str}{confidence_str} {e.title}{date_str}")
                if e.reasoning:
                    click.echo(f"  Reason: {e.reasoning}")
                click.echo(f"  Source: {e.source_file}:{e.source_line}")
            click.echo()

        if result.project_edges:
            click.echo("=== Gotchas ===")
            for edge in result.project_edges:
                if edge.workaround:
                    click.echo(f"- {edge.title} -> {edge.workaround}")
                else:
                    click.echo(f"- {edge.title}")

        click.echo()
        total = len(result.entities) + len(inline_entities)
        click.echo(f"Total: {total} entities, {len(result.project_edges)} gotchas")


# Project management commands
@cli.command("list")
def list_projects():
    """List registered projects."""
    registry = ProjectsRegistry.load()
    projects = registry.list_all()

    if not projects:
        click.echo("No projects registered.")
        click.echo("Run 'mind init' in a project directory to register it.")
        return

    click.echo(f"Registered Projects ({len(projects)})")
    click.echo("-" * 40)

    for i, project in enumerate(projects, 1):
        click.echo(f"\n{i}. {project.name}")
        click.echo(f"   Path: {project.path}")
        if project.stack:
            click.echo(f"   Stack: {', '.join(project.stack)}")
        if project.last_activity:
            click.echo(f"   Last activity: {project.last_activity}")


@cli.command("add")
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
def add_project(path: str):
    """Register a project with Mind."""
    project_path = Path(path).resolve()
    mind_dir = project_path / ".mind"

    if not mind_dir.exists():
        click.echo(f"Error: {project_path} is not a Mind project.")
        click.echo("Run 'mind init' first.")
        raise SystemExit(1)

    from .detection import detect_stack

    stack = detect_stack(project_path)
    registry = ProjectsRegistry.load()
    registry.register(project_path, stack)

    click.echo(f"Registered: {project_path.name}")


@cli.command("remove")
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
def remove_project(path: str):
    """Unregister a project from Mind."""
    project_path = Path(path).resolve()

    registry = ProjectsRegistry.load()
    if registry.unregister(project_path):
        click.echo(f"Unregistered: {project_path.name}")
        click.echo("(Files in .mind/ preserved)")
    else:
        click.echo(f"Project not registered: {project_path.name}")


@cli.command("mcp")
def mcp_server():
    """Run the MCP server for AI assistant integration."""
    from .mcp import run_server
    run_server()


@cli.command("doctor")
def doctor():
    """Run health checks on Mind installation."""
    from datetime import datetime, timedelta

    issues = []
    warnings = []

    click.echo("Mind Health Check (v3)")
    click.echo("-" * 40)

    # Check Mind home directory
    from .storage import get_mind_home

    mind_home = get_mind_home()
    if mind_home.exists():
        click.echo(f"[+] Config directory exists ({mind_home})")
    else:
        click.echo(f"[!] Config directory missing ({mind_home})")
        issues.append("Mind home directory not found")

    # Check registered projects
    registry = ProjectsRegistry.load()
    projects = registry.list_all()
    click.echo(f"[+] Projects registered: {len(projects)}")

    # Check each project
    for project in projects:
        project_path = Path(project.path)

        # Check project exists
        if not project_path.exists():
            click.echo(f"[!] Project missing: {project.path}")
            issues.append(f"Project directory not found: {project.path}")
            continue

        # Check .mind directory
        mind_dir = project_path / ".mind"
        if not mind_dir.exists():
            click.echo(f"[!] No .mind/ in: {project.name}")
            issues.append(f"No .mind/ directory in {project.name}")
            continue

        # Check MEMORY.md
        memory_file = mind_dir / "MEMORY.md"
        if not memory_file.exists():
            click.echo(f"[!] No MEMORY.md in: {project.name}")
            issues.append(f"No MEMORY.md in {project.name}")
            continue

        # Check MEMORY.md is readable
        try:
            content = memory_file.read_text(encoding="utf-8")
            file_size_kb = memory_file.stat().st_size / 1024
            if file_size_kb > 100:
                click.echo(f"[.] {project.name}: MEMORY.md large ({file_size_kb:.0f}KB)")
                warnings.append(f"{project.name}: MEMORY.md is {file_size_kb:.0f}KB - consider archiving")
            else:
                click.echo(f"[+] {project.name}: MEMORY.md accessible ({file_size_kb:.0f}KB)")
        except Exception as e:
            click.echo(f"[!] {project.name}: Cannot read MEMORY.md")
            issues.append(f"Cannot read MEMORY.md in {project.name}: {e}")
            continue

        # Check state.json
        state_file = mind_dir / "state.json"
        if state_file.exists():
            try:
                import json
                state = json.loads(state_file.read_text())
                if state.get("last_activity"):
                    last = datetime.fromtimestamp(state["last_activity"] / 1000)
                    age = datetime.now() - last
                    if age > timedelta(days=7):
                        click.echo(f"[.] {project.name}: Last activity {age.days}d ago")
                        warnings.append(f"{project.name}: Last activity {age.days} days ago")
            except:
                pass

        # Check CLAUDE.md has MIND:CONTEXT
        claude_md = project_path / "CLAUDE.md"
        if claude_md.exists():
            claude_content = claude_md.read_text(encoding="utf-8")
            if "MIND:CONTEXT" in claude_content:
                click.echo(f"[+] {project.name}: MIND:CONTEXT present")
            else:
                click.echo(f"[.] {project.name}: No MIND:CONTEXT in CLAUDE.md")
                warnings.append(f"{project.name}: Run 'mind init' to add MIND:CONTEXT")
        else:
            click.echo(f"[.] {project.name}: No CLAUDE.md")
            warnings.append(f"{project.name}: No CLAUDE.md file")

    # Check global edges
    from .mcp.server import load_global_edges

    global_edges = load_global_edges()
    click.echo(f"[+] Global edges loaded: {len(global_edges)}")

    # Summary
    click.echo()
    click.echo("-" * 40)

    if issues:
        click.echo(f"Issues ({len(issues)}):")
        for issue in issues:
            click.echo(f"  - {issue}")
        click.echo()

    if warnings:
        click.echo(f"Warnings ({len(warnings)}):")
        for warning in warnings:
            click.echo(f"  - {warning}")
        click.echo()

    if issues:
        click.echo("Overall: UNHEALTHY")
        raise SystemExit(1)
    elif warnings:
        click.echo(f"Overall: Healthy ({len(warnings)} warnings)")
    else:
        click.echo("Overall: Healthy")


@cli.command("patterns")
@click.option("--type", "pattern_type", type=click.Choice(["all", "preference", "skill", "blind_spot", "anti_pattern"]), default="all", help="Filter by pattern type")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def patterns(pattern_type: str, as_json: bool):
    """View learned patterns from SELF_IMPROVE.md."""
    from .self_improve import load_self_improve

    data = load_self_improve()

    # Select patterns based on type filter
    if pattern_type == "all":
        patterns_to_show = {
            "preferences": data.preferences,
            "skills": data.skills,
            "blind_spots": data.blind_spots,
            "anti_patterns": data.anti_patterns,
        }
    elif pattern_type == "preference":
        patterns_to_show = {"preferences": data.preferences}
    elif pattern_type == "skill":
        patterns_to_show = {"skills": data.skills}
    elif pattern_type == "blind_spot":
        patterns_to_show = {"blind_spots": data.blind_spots}
    elif pattern_type == "anti_pattern":
        patterns_to_show = {"anti_patterns": data.anti_patterns}
    else:
        patterns_to_show = {}

    if as_json:
        output = {}
        for key, plist in patterns_to_show.items():
            output[key] = [
                {"category": p.category, "description": p.description, "confidence": p.confidence}
                for p in plist
            ]
        click.echo(json.dumps(output, indent=2))
    else:
        total = 0
        for type_name, plist in patterns_to_show.items():
            if plist:
                # Format header: "preferences" -> "Preferences"
                header = type_name.replace("_", " ").title()
                click.echo(f"=== {header} ===")
                for p in plist:
                    click.echo(f"  [{p.category}] {p.description}")
                click.echo()
                total += len(plist)

        if total == 0:
            click.echo("No patterns found.")
            click.echo("Patterns are learned over time from your feedback.")
            click.echo()
            click.echo("Add patterns manually:")
            click.echo("  PREFERENCE: [category] description")
            click.echo("  SKILL: [stack:context] description")
            click.echo("  BLIND_SPOT: [category] description")
            click.echo("  ANTI_PATTERN: [category] description")
        else:
            click.echo(f"Total: {total} patterns")


@cli.command("feedback")
@click.option("--limit", default=20, help="Maximum entries to show")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def feedback(limit: int, as_json: bool):
    """View feedback log from SELF_IMPROVE.md."""
    from .self_improve import load_self_improve

    data = load_self_improve()
    entries = data.feedback[:limit]

    if as_json:
        output = [
            {"date": str(e.date_added), "description": e.description}
            for e in entries
        ]
        click.echo(json.dumps(output, indent=2))
    else:
        if not entries:
            click.echo("No feedback entries found.")
            click.echo()
            click.echo("Log feedback during sessions with:")
            click.echo("  mind_log('context -> correction', type='feedback')")
        else:
            click.echo(f"=== Feedback Log ({len(entries)}/{len(data.feedback)}) ===")
            for e in entries:
                click.echo(f"  [{e.date_added}] {e.description}")
            click.echo()
            if len(data.feedback) > limit:
                click.echo(f"({len(data.feedback) - limit} more entries, use --limit to see more)")


@cli.command("self")
def self_status():
    """Show SELF_IMPROVE.md summary and stats."""
    from .self_improve import load_self_improve, get_self_improve_path

    path = get_self_improve_path()
    if not path.exists():
        click.echo("SELF_IMPROVE.md not found.")
        click.echo("Run 'mind init' in any project to create it.")
        return

    data = load_self_improve()

    click.echo("=== Self-Improvement Summary ===")
    click.echo(f"Location: {path}")
    click.echo()

    # Stats
    click.echo("Patterns:")
    click.echo(f"  Preferences:   {len(data.preferences)}")
    click.echo(f"  Skills:        {len(data.skills)}")
    click.echo(f"  Blind Spots:   {len(data.blind_spots)}")
    click.echo(f"  Anti-Patterns: {len(data.anti_patterns)}")
    click.echo(f"  Feedback Log:  {len(data.feedback)} entries")
    click.echo()

    total = len(data.all_patterns())
    click.echo(f"Total: {total} patterns")

    # File size
    file_size_kb = path.stat().st_size / 1024
    click.echo(f"File size: {file_size_kb:.1f}KB")
    click.echo()

    # Quick preview of each type
    if data.blind_spots:
        click.echo("Recent Blind Spots (watch out!):")
        for bs in data.blind_spots[:3]:
            click.echo(f"  - [{bs.category}] {bs.description}")
        click.echo()

    if data.anti_patterns:
        click.echo("Recent Anti-Patterns (avoid!):")
        for ap in data.anti_patterns[:3]:
            click.echo(f"  - [{ap.category}] {ap.description}")


@cli.command("status")
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
def status(path: str):
    """Show project status and stats."""
    project_path = Path(path).resolve()
    mind_dir = project_path / ".mind"

    if not mind_dir.exists():
        click.echo(f"Error: {project_path} is not a Mind project.")
        click.echo("Run 'mind init' first.")
        raise SystemExit(1)

    memory_file = mind_dir / "MEMORY.md"
    state_file = mind_dir / "state.json"

    click.echo(f"Project: {project_path.name}")
    click.echo("-" * 40)

    # Parse MEMORY.md
    if memory_file.exists():
        parser = Parser()
        content = memory_file.read_text(encoding="utf-8")
        result = parser.parse(content, str(memory_file))

        click.echo(f"Stack: {', '.join(result.project_state.stack) or '(not set)'}")
        click.echo(f"Goal: {result.project_state.goal or '(not set)'}")
        click.echo(f"Blocked: {result.project_state.blocked_by or 'None'}")
        click.echo()

        # Count by type
        decisions = sum(1 for e in result.entities if e.type.value == "decision")
        issues_open = sum(1 for e in result.entities if e.type.value == "issue" and (not e.status or e.status.value == "open"))
        issues_resolved = sum(1 for e in result.entities if e.type.value == "issue" and e.status and e.status.value == "resolved")
        learnings = sum(1 for e in result.entities if e.type.value == "learning")

        click.echo("Stats:")
        click.echo(f"  Decisions: {decisions}")
        click.echo(f"  Issues (open): {issues_open}")
        click.echo(f"  Issues (resolved): {issues_resolved}")
        click.echo(f"  Learnings: {learnings}")
        click.echo(f"  Gotchas: {len(result.project_edges)}")
        click.echo()

        # File size
        file_size_kb = memory_file.stat().st_size / 1024
        click.echo(f"MEMORY.md: {file_size_kb:.1f}KB")

    # Load state
    if state_file.exists():
        import json
        from datetime import datetime
        try:
            state = json.loads(state_file.read_text())
            if state.get("last_activity"):
                last = datetime.fromtimestamp(state["last_activity"] / 1000)
                click.echo(f"Last activity: {last.isoformat()}")
        except:
            pass

    # v3 Graph Status
    graph_path = mind_dir / "v3" / "graph"
    if graph_path.exists():
        try:
            from .v3.graph.store import GraphStore
            store = GraphStore(graph_path)
            counts = store.get_counts()
            click.echo()
            click.echo("v3 Graph: ACTIVE")
            click.echo(f"  Memories: {counts.get('memories', 0)}")
            click.echo(f"  Decisions: {counts.get('decisions', 0)}")
            click.echo(f"  Entities: {counts.get('entities', 0)}")
            click.echo(f"  Patterns: {counts.get('patterns', 0)}")
        except Exception:
            click.echo()
            click.echo("v3 Graph: ERROR")
    else:
        click.echo()
        click.echo("v3 Graph: NOT INITIALIZED")
        click.echo("  Run 'mind migrate .' to enable v3 features")


@cli.command("generate-views")
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
def generate_views(path: str):
    """Generate human-readable markdown views from the graph.

    Creates DECISIONS.md, PATTERNS.md, and POLICIES.md in the .mind directory.
    """
    project_path = Path(path).resolve()
    mind_dir = project_path / ".mind"

    if not mind_dir.exists():
        click.echo(f"Error: {project_path} is not a Mind project.")
        click.echo("Run 'mind init' first.")
        raise SystemExit(1)

    try:
        from .v3.graph.store import GraphStore
        from .v3.views import ViewGenerator

        graph_path = mind_dir / "v3" / "graph"
        store = GraphStore(graph_path)
        if not store.is_initialized():
            click.echo("Graph store not initialized. No views to generate.")
            raise SystemExit(1)

        generator = ViewGenerator(store, mind_dir)
        paths = generator.generate_all()

        click.echo("Generated views:")
        for p in paths:
            click.echo(f"  {p.name}")

    except ImportError as e:
        click.echo(f"Error: v3 modules not available: {e}")
        raise SystemExit(1)


@cli.command("migrate")
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option("--force", is_flag=True, help="Force re-migration even if already done")
def migrate_v3(path: str, force: bool):
    """Migrate MEMORY.md data to v3 structured tables.

    This command processes your existing MEMORY.md content and extracts:
    - Decisions (choices made and why)
    - Entities (files, functions, tools mentioned)
    - Patterns (preferences, habits, avoidances)

    Migration runs automatically on v3 init, but you can use this command
    to force re-processing or see detailed migration stats.
    """
    project_path = Path(path).resolve()
    mind_dir = project_path / ".mind"

    if not mind_dir.exists():
        click.echo(f"Error: {project_path} is not a Mind project.")
        click.echo("Run 'mind init' first.")
        raise SystemExit(1)

    try:
        from .v3.migration import migrate_project

        click.echo("Migrating MEMORY.md to v3 structured tables...")
        stats = migrate_project(project_path, force=force)

        click.echo()
        click.echo("Migration complete:")
        click.echo(f"  Memories processed: {stats.memories_processed}")
        click.echo(f"  Decisions extracted: {stats.decisions_added}")
        click.echo(f"  Entities extracted: {stats.entities_added}")
        click.echo(f"  Patterns extracted: {stats.patterns_added}")

        if stats.errors:
            click.echo()
            click.echo(f"  Warnings: {len(stats.errors)}")
            for err in stats.errors[:5]:  # Show first 5 errors
                click.echo(f"    - {err[:80]}")
            if len(stats.errors) > 5:
                click.echo(f"    ... and {len(stats.errors) - 5} more")

        click.echo()
        click.echo("Run 'mind generate-views' to create human-readable markdown files.")

    except ImportError as e:
        click.echo(f"Error: v3 modules not available: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
