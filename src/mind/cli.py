"""Mind CLI - File-based memory for AI coding assistants (v2: daemon-free)."""

import json
from datetime import date
from pathlib import Path

import click

from . import __version__
from .context import update_claude_md
from .detection import detect_stack
from .mascot import get_mindful, can_use_unicode
from .parser import InlineScanner, Parser
from .storage import ProjectsRegistry
from .config import create_default_config, is_mascot_enabled, set_mascot_enabled
from .templates import GITIGNORE_CONTENT, MEMORY_TEMPLATE, SESSION_TEMPLATE


def echo_with_mindful(message: str, emotion: str = "idle", project_path: Path = None):
    """Print message with Mindful mascot (if enabled).

    Args:
        message: Message to display
        emotion: Mindful's emotion
        project_path: Project path to check mascot config (uses cwd if None)
    """
    # Check if mascot is enabled
    if project_path is None:
        project_path = Path.cwd()

    if is_mascot_enabled(project_path):
        fancy = can_use_unicode()
        art = get_mindful(emotion, fancy=fancy)
        click.echo(art)
        click.echo()

    click.echo(message)


def echo_mindful_only(emotion: str = "idle", project_path: Path = None):
    """Print just Mindful mascot (if enabled), no message.

    Args:
        emotion: Mindful's emotion
        project_path: Project path to check mascot config (uses cwd if None)
    """
    if project_path is None:
        project_path = Path.cwd()

    if is_mascot_enabled(project_path):
        fancy = can_use_unicode()
        art = get_mindful(emotion, fancy=fancy)
        click.echo(art)
        click.echo()


@click.group()
@click.version_option(version=__version__, prog_name="mind")
def cli():
    """Mind - File-based memory for AI coding assistants."""
    pass


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
def init(path: str):
    """Initialize Mind for a project."""
    project_path = Path(path).resolve()
    mind_dir = project_path / ".mind"

    # Create .mind directory
    mind_dir.mkdir(exist_ok=True)

    # Create .mind/.gitignore
    gitignore = mind_dir / ".gitignore"
    gitignore.write_text(GITIGNORE_CONTENT)

    # Detect stack
    stack = detect_stack(project_path)
    stack_str = ", ".join(stack) if stack else "(add your stack)"

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

    # Create config.json (don't overwrite if exists)
    config_file = mind_dir / "config.json"
    if not config_file.exists():
        create_default_config(project_path)
        click.echo("[+] Created .mind/config.json")
    else:
        click.echo("[.] .mind/config.json already exists (preserved)")

    # Update CLAUDE.md
    update_claude_md(project_path, stack)
    click.echo("[+] Updated CLAUDE.md with MIND:CONTEXT")

    # Show detected stack
    if stack:
        click.echo(f"[+] Detected stack: {', '.join(stack)}")
    else:
        click.echo("[.] No stack detected (update .mind/MEMORY.md manually)")

    # Register project
    registry = ProjectsRegistry.load()
    registry.register(project_path, stack)
    click.echo("[+] Registered project with Mind")

    click.echo()
    echo_with_mindful("Mind initialized! Ready to remember.", "happy")
    click.echo()
    click.echo("MCP tools available:")
    click.echo("  - mind_recall() : Load session context (call first!)")
    click.echo("  - mind_session() : Get current session state")
    click.echo("  - mind_search() : Search memories")
    click.echo("  - mind_checkpoint() : Force process pending memories")
    click.echo("  - mind_edges() : Check for gotchas")


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
        echo_with_mindful(f"Total: {total} entities, {len(result.project_edges)} gotchas", "thinking")


# Project management commands
@cli.command("list")
def list_projects():
    """List registered projects."""
    registry = ProjectsRegistry.load()
    projects = registry.list_all()

    if not projects:
        echo_with_mindful("No projects registered.", "sleepy")
        click.echo("Run 'mind init' in a project directory to register it.")
        return

    echo_mindful_only("idle")
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

    echo_with_mindful(f"Registered: {project_path.name}", "happy")


@cli.command("remove")
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
def remove_project(path: str):
    """Unregister a project from Mind."""
    project_path = Path(path).resolve()

    registry = ProjectsRegistry.load()
    if registry.unregister(project_path):
        echo_with_mindful(f"Unregistered: {project_path.name}", "sad")
        click.echo("(Files in .mind/ preserved)")
    else:
        echo_with_mindful(f"Project not registered: {project_path.name}", "confused")


@cli.command("mcp")
def mcp_server():
    """Run the MCP server for AI assistant integration."""
    from .mcp import run_server
    run_server()


@cli.command("config")
@click.argument("setting", required=False)
@click.argument("value", required=False)
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False), required=False)
def config_cmd(setting: str, value: str, path: str):
    """View or change Mind configuration.

    Examples:
        mind config              # Show all settings
        mind config mascot       # Show mascot setting
        mind config mascot on    # Enable Mindful mascot
        mind config mascot off   # Disable Mindful mascot
    """
    project_path = Path(path).resolve()
    mind_dir = project_path / ".mind"

    if not mind_dir.exists():
        click.echo(f"Error: {project_path} is not a Mind project.")
        click.echo("Run 'mind init' first.")
        raise SystemExit(1)

    # No arguments - show all settings
    if not setting:
        mascot_status = "on" if is_mascot_enabled(project_path) else "off"
        click.echo("Mind Configuration")
        click.echo("-" * 30)
        click.echo(f"mascot: {mascot_status}")
        return

    # Setting name only - show current value
    if setting and not value:
        if setting == "mascot":
            status = "on" if is_mascot_enabled(project_path) else "off"
            click.echo(f"mascot: {status}")
        else:
            click.echo(f"Unknown setting: {setting}")
            click.echo("Available settings: mascot")
        return

    # Setting name and value - update
    if setting == "mascot":
        if value.lower() in ("on", "true", "1", "yes"):
            set_mascot_enabled(project_path, True)
            echo_with_mindful("Mindful is now ON!", "happy")
        elif value.lower() in ("off", "false", "0", "no"):
            set_mascot_enabled(project_path, False)
            click.echo("Mindful mascot disabled.")
        else:
            click.echo(f"Invalid value: {value}")
            click.echo("Use 'on' or 'off'")
    else:
        click.echo(f"Unknown setting: {setting}")
        click.echo("Available settings: mascot")


@cli.command("doctor")
def doctor():
    """Run health checks on Mind installation."""
    from datetime import datetime, timedelta

    issues = []
    warnings = []

    click.echo("Mind Health Check (v2)")
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
        echo_with_mindful("Overall: UNHEALTHY", "error")
        raise SystemExit(1)
    elif warnings:
        echo_with_mindful(f"Overall: Healthy ({len(warnings)} warnings)", "warning")
    else:
        echo_with_mindful("Overall: Healthy", "happy")


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

    echo_mindful_only("curious", project_path)
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


if __name__ == "__main__":
    cli()
