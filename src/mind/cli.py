"""Mind CLI - File-based memory for AI coding assistants."""
# MEMORY: decided Click over Typer because simpler API

import json
from datetime import date
from pathlib import Path

import click

from . import __version__
from .context import update_claude_md
from .detection import detect_stack
from .parser import InlineScanner, Parser
from .storage import ProjectsRegistry, is_daemon_running, DaemonState
from .templates import GITIGNORE_CONTENT, MEMORY_TEMPLATE


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
    click.echo("Mind initialized! Start working - append notes to .mind/MEMORY.md")


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


# Daemon commands
@cli.group()
def daemon():
    """Manage the Mind daemon."""
    pass


@daemon.command("start")
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground (don't daemonize)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose logging")
def daemon_start(foreground: bool, verbose: bool):
    """Start the Mind daemon."""
    if is_daemon_running():
        click.echo("Mind daemon is already running.")
        return

    from .daemon import run_daemon

    if foreground:
        click.echo("Starting Mind daemon in foreground...")
        click.echo("Press Ctrl+C to stop.")
        run_daemon(verbose=verbose)
    else:
        # On Windows, we can't easily daemonize, so just run in foreground
        import sys
        if sys.platform == "win32":
            click.echo("Starting Mind daemon...")
            click.echo("(On Windows, daemon runs in foreground. Use Ctrl+C to stop.)")
            run_daemon(verbose=verbose)
        else:
            # Unix: fork and daemonize
            import os
            pid = os.fork()
            if pid > 0:
                click.echo(f"[+] Mind daemon started (PID: {pid})")
                return
            else:
                # Child process
                os.setsid()
                run_daemon(verbose=verbose)


@daemon.command("stop")
def daemon_stop():
    """Stop the Mind daemon."""
    from .daemon import stop_daemon

    if stop_daemon():
        click.echo("[+] Mind daemon stopped.")
    else:
        click.echo("Mind daemon is not running.")


@daemon.command("status")
def daemon_status():
    """Check Mind daemon status."""
    state = DaemonState.load()

    if is_daemon_running():
        click.echo("Mind Daemon Status")
        click.echo("-" * 40)
        click.echo(f"Status: Running")
        click.echo(f"PID: {state.pid}")
        if state.started_at:
            click.echo(f"Started: {state.started_at}")
        click.echo(f"Projects watching: {len(state.projects_watching)}")
        for p in state.projects_watching:
            click.echo(f"  - {p}")
    else:
        click.echo("Mind Daemon Status")
        click.echo("-" * 40)
        click.echo("Status: Not running")
        click.echo()
        click.echo("Start with: mind daemon start")


@daemon.command("logs")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--lines", "-n", default=20, help="Number of lines to show")
def daemon_logs(follow: bool, lines: int):
    """View daemon logs."""
    from .storage import get_mind_home

    log_file = get_mind_home() / "logs" / "daemon.log"
    if not log_file.exists():
        click.echo("No log file found. Daemon may not have been started yet.")
        return

    if follow:
        import subprocess
        import sys
        # Use tail -f on Unix, or type + loop on Windows
        if sys.platform == "win32":
            # Simple approach: just print last lines
            content = log_file.read_text()
            log_lines = content.strip().split("\n")
            for line in log_lines[-lines:]:
                click.echo(line)
            click.echo("\n(--follow not fully supported on Windows)")
        else:
            subprocess.run(["tail", "-f", "-n", str(lines), str(log_file)])
    else:
        content = log_file.read_text()
        log_lines = content.strip().split("\n")
        for line in log_lines[-lines:]:
            click.echo(line)


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

    click.echo("Registered Projects")
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
    """Register a project with Mind daemon."""
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

    click.echo(f"[+] Registered: {project_path}")


@cli.command("remove")
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
def remove_project(path: str):
    """Unregister a project from Mind daemon."""
    project_path = Path(path).resolve()

    registry = ProjectsRegistry.load()
    if registry.unregister(project_path):
        click.echo(f"[+] Unregistered: {project_path}")
        click.echo("    (Files in .mind/ preserved)")
    else:
        click.echo(f"Project not registered: {project_path}")


if __name__ == "__main__":
    cli()
