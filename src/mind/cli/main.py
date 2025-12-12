"""Mind CLI entry point."""

import asyncio
import os
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

console = Console()
stderr_console = Console(stderr=True)


def get_data_dir() -> Path:
    """Get the Mind data directory."""
    env_dir = os.environ.get("MIND_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".mind"


@click.group()
@click.version_option(version="0.1.0", prog_name="mind")
def cli():
    """Mind - Context and continuity for AI-assisted development."""
    pass


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8765, help="Port to bind to")
def serve(host: str, port: int):
    """Run Mind as an HTTP server for dashboard and integrations."""
    from mind.api.server import run_server

    console.print(f"[bold]Mind HTTP API[/bold]")
    console.print(f"Starting server at [green]http://{host}:{port}[/green]")
    console.print(f"API docs at [blue]http://{host}:{port}/docs[/blue]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    run_server(host=host, port=port)


@cli.command()
def mcp():
    """Run Mind as an MCP server (for Claude Code)."""
    from mind.mcp.server import run_server

    stderr_console.print("[dim]Starting Mind MCP server...[/dim]")

    data_dir = get_data_dir()
    asyncio.run(run_server(data_dir))


@cli.command()
@click.option("--name", "-n", help="Project name")
def projects(name: Optional[str]):
    """List or create projects."""
    from mind.storage.sqlite import SQLiteStorage

    async def run():
        storage = SQLiteStorage(get_data_dir() / "mind.db")
        await storage.initialize()

        if name:
            # Create new project
            from mind.models import ProjectCreate
            project = await storage.create_project(ProjectCreate(name=name))
            console.print(f"[green]Created project:[/green] {project.name} ({project.id})")
        else:
            # List projects
            projects = await storage.list_projects()

            if not projects:
                console.print("[dim]No projects yet. Create one with: mind projects --name <name>[/dim]")
                return

            table = Table(title="Projects")
            table.add_column("Name", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Goal", style="white")
            table.add_column("Last Session", style="dim")

            for p in projects:
                last_session = ""
                if p.last_session_date:
                    last_session = p.last_session_date.strftime("%Y-%m-%d %H:%M")

                table.add_row(
                    p.name,
                    p.status,
                    p.current_goal or "-",
                    last_session or "-",
                )

            console.print(table)

        await storage.close()

    asyncio.run(run())


@cli.command()
@click.argument("project_name")
def decisions(project_name: str):
    """List decisions for a project."""
    from mind.storage.sqlite import SQLiteStorage

    async def run():
        storage = SQLiteStorage(get_data_dir() / "mind.db")
        await storage.initialize()

        project = await storage.get_project_by_name(project_name)
        if not project:
            console.print(f"[red]Project not found:[/red] {project_name}")
            return

        decisions = await storage.list_decisions(project.id)

        if not decisions:
            console.print(f"[dim]No decisions for {project_name}[/dim]")
            return

        table = Table(title=f"Decisions for {project_name}")
        table.add_column("Title", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Confidence", style="yellow")
        table.add_column("Date", style="dim")

        for d in decisions:
            table.add_row(
                d.title,
                d.status,
                f"{d.confidence:.0%}",
                d.decided_at.strftime("%Y-%m-%d"),
            )

        console.print(table)
        await storage.close()

    asyncio.run(run())


@cli.command()
@click.argument("project_name")
def issues(project_name: str):
    """List issues for a project."""
    from mind.storage.sqlite import SQLiteStorage

    async def run():
        storage = SQLiteStorage(get_data_dir() / "mind.db")
        await storage.initialize()

        project = await storage.get_project_by_name(project_name)
        if not project:
            console.print(f"[red]Project not found:[/red] {project_name}")
            return

        issues = await storage.list_issues(project.id)

        if not issues:
            console.print(f"[dim]No issues for {project_name}[/dim]")
            return

        table = Table(title=f"Issues for {project_name}")
        table.add_column("Title", style="cyan")
        table.add_column("Severity", style="red")
        table.add_column("Status", style="green")
        table.add_column("Opened", style="dim")

        severity_colors = {
            "blocking": "red",
            "major": "yellow",
            "minor": "blue",
            "cosmetic": "dim",
        }

        for i in issues:
            table.add_row(
                i.title,
                f"[{severity_colors.get(i.severity, 'white')}]{i.severity}[/]",
                i.status,
                i.opened_at.strftime("%Y-%m-%d"),
            )

        console.print(table)
        await storage.close()

    asyncio.run(run())


@cli.command()
def edges():
    """List all sharp edges."""
    from mind.storage.sqlite import SQLiteStorage

    async def run():
        storage = SQLiteStorage(get_data_dir() / "mind.db")
        await storage.initialize()

        edges = await storage.list_sharp_edges()

        if not edges:
            console.print("[dim]No sharp edges recorded yet[/dim]")
            return

        table = Table(title="Sharp Edges")
        table.add_column("Title", style="cyan")
        table.add_column("Project", style="dim")
        table.add_column("Discovered", style="dim")

        for e in edges:
            table.add_row(
                e.title,
                e.project_id or "[global]",
                e.discovered_at.strftime("%Y-%m-%d"),
            )

        console.print(table)
        await storage.close()

    asyncio.run(run())


@cli.command()
@click.option("--format", "-f", type=click.Choice(["json", "markdown"]), default="json")
@click.option("--project", "-p", help="Export specific project")
def export(format: str, project: Optional[str]):
    """Export all Mind data."""
    from mind.storage.sqlite import SQLiteStorage
    import json
    from datetime import datetime

    async def run():
        storage = SQLiteStorage(get_data_dir() / "mind.db")
        await storage.initialize()

        project_id = None
        if project:
            p = await storage.get_project_by_name(project)
            if p:
                project_id = p.id

        # Build export data
        export_data = {
            "exported_at": datetime.utcnow().isoformat(),
            "projects": [],
            "decisions": [],
            "issues": [],
            "edges": [],
        }

        projects = await storage.list_projects()
        if project_id:
            projects = [p for p in projects if p.id == project_id]

        for p in projects:
            export_data["projects"].append(p.model_dump())

            decisions = await storage.list_decisions(p.id)
            export_data["decisions"].extend([d.model_dump() for d in decisions])

            issues = await storage.list_issues(p.id)
            export_data["issues"].extend([i.model_dump() for i in issues])

        edges = await storage.list_sharp_edges(project_id)
        export_data["edges"] = [e.model_dump() for e in edges]

        # Save
        export_dir = get_data_dir() / "exports"
        export_dir.mkdir(exist_ok=True)

        filename = f"mind_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format}"
        export_path = export_dir / filename

        with open(export_path, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        console.print(f"[green]Exported to:[/green] {export_path}")
        console.print(f"  Projects: {len(export_data['projects'])}")
        console.print(f"  Decisions: {len(export_data['decisions'])}")
        console.print(f"  Issues: {len(export_data['issues'])}")
        console.print(f"  Edges: {len(export_data['edges'])}")

        await storage.close()

    asyncio.run(run())


@cli.command()
def status():
    """Show Mind status and statistics."""
    from mind.storage.sqlite import SQLiteStorage

    async def run():
        storage = SQLiteStorage(get_data_dir() / "mind.db")
        await storage.initialize()

        user = await storage.get_or_create_user()
        projects = await storage.list_projects()

        console.print("[bold]Mind Status[/bold]\n")
        console.print(f"Data directory: {get_data_dir()}")
        console.print(f"Total sessions: {user.total_sessions}")
        console.print(f"Projects: {len(projects)}")

        if user.last_session:
            console.print(f"Last session: {user.last_session.strftime('%Y-%m-%d %H:%M')}")

        if projects:
            console.print("\n[bold]Active Projects:[/bold]")
            for p in projects[:5]:
                if p.status == "active":
                    goal = f" - {p.current_goal}" if p.current_goal else ""
                    console.print(f"  • {p.name}{goal}")

        await storage.close()

    asyncio.run(run())


if __name__ == "__main__":
    cli()
