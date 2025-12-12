"""Mind daemon - background process for file watching and context generation."""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .context import ContextGenerator
from .parser import Parser
from .storage import DaemonState, ProjectsRegistry, get_mind_home, get_pid_file
from .watcher import ChangeType, Debouncer, FileEvent, FileWatcher

logger = logging.getLogger("mind.daemon")


class ActivityTracker:
    """Tracks activity per project to detect session boundaries."""

    def __init__(self, inactivity_minutes: int = 30):
        self.threshold = timedelta(minutes=inactivity_minutes)
        self.last_activity: dict[str, datetime] = {}

    def on_activity(self, project_path: str) -> None:
        """Record activity for a project."""
        self.last_activity[project_path] = datetime.now()

    def get_last_activity(self, project_path: str) -> Optional[datetime]:
        """Get last activity time for a project."""
        return self.last_activity.get(project_path)

    def check_inactive(self) -> list[str]:
        """Return projects that have been inactive beyond threshold."""
        now = datetime.now()
        inactive = []

        for project_path, last in list(self.last_activity.items()):
            if now - last > self.threshold:
                inactive.append(project_path)

        return inactive

    def clear_project(self, project_path: str) -> None:
        """Clear activity tracking for a project."""
        self.last_activity.pop(project_path, None)


class MindDaemon:
    """Main daemon class that coordinates watching, parsing, and context generation."""

    def __init__(
        self,
        inactivity_minutes: int = 30,
        debounce_ms: int = 100,
    ):
        self.watcher = FileWatcher()
        self.tracker = ActivityTracker(inactivity_minutes)
        self.debouncer = Debouncer(debounce_ms)
        self.parser = Parser()
        self.context_generator = ContextGenerator()
        self.registry = ProjectsRegistry.load()
        self._running = False

    async def start(self) -> None:
        """Start the daemon."""
        logger.info("Starting Mind daemon...")

        # Load registered projects
        for project in self.registry.list_all():
            project_path = Path(project.path)
            if project_path.exists():
                self.watcher.add_project(project_path)
                logger.info(f"Watching: {project.path}")

        if not self.watcher.projects:
            logger.warning("No projects registered. Use 'mind init' to register a project.")

        self._running = True

        # Save daemon state
        state = DaemonState(
            pid=os.getpid(),
            started_at=datetime.now().isoformat(),
            projects_watching=list(self.watcher.projects.keys()),
        )
        state.save()

        # Write PID file
        get_pid_file().write_text(str(os.getpid()))

        # Run main loop
        try:
            await self._run()
        finally:
            self._cleanup()

    async def _run(self) -> None:
        """Main daemon loop."""
        # Start file watcher
        watcher_task = asyncio.create_task(self.watcher.watch())

        # Start inactivity checker
        checker_task = asyncio.create_task(self._check_inactive_loop())

        # Process events
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self.watcher.event_queue.get(),
                    timeout=1.0,
                )
                await self._handle_event(event)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error handling event: {e}")

        # Clean up tasks
        watcher_task.cancel()
        checker_task.cancel()

        try:
            await watcher_task
        except asyncio.CancelledError:
            pass

        try:
            await checker_task
        except asyncio.CancelledError:
            pass

    async def _handle_event(self, event: FileEvent) -> None:
        """Handle a file change event."""
        logger.debug(f"Event: {event.change_type.value} {event.path}")

        # Track activity
        project_key = str(event.project_path)
        self.tracker.on_activity(project_key)

        # Update registry activity
        self.registry.update_activity(event.project_path)

        # Debounce and process
        if event.path.name == "MEMORY.md":
            await self.debouncer.debounce(
                f"memory:{project_key}",
                lambda: self._process_memory_change(event),
            )
        elif event.change_type != ChangeType.DELETED:
            # Scan for inline comments
            await self.debouncer.debounce(
                f"inline:{event.path}",
                lambda: self._process_code_change(event),
            )

    async def _process_memory_change(self, event: FileEvent) -> None:
        """Process a change to MEMORY.md."""
        logger.info(f"Processing MEMORY.md change: {event.project_path}")

        try:
            memory_file = event.project_path / ".mind" / "MEMORY.md"
            if not memory_file.exists():
                return

            content = memory_file.read_text(encoding="utf-8")
            result = self.parser.parse(content, str(memory_file))

            # Update context
            last_activity = self.tracker.get_last_activity(str(event.project_path))
            self.context_generator.update_claude_md(
                event.project_path,
                result,
                last_activity,
            )

            logger.info(
                f"Updated CLAUDE.md: {len(result.entities)} entities, "
                f"{len(result.project_edges)} gotchas"
            )
        except Exception as e:
            logger.error(f"Error processing MEMORY.md: {e}")

    async def _process_code_change(self, event: FileEvent) -> None:
        """Process a change to a code file (scan for inline comments)."""
        # For now, we just log. Full inline processing would re-index.
        logger.debug(f"Code file changed: {event.path}")

    async def _check_inactive_loop(self) -> None:
        """Periodically check for inactive sessions."""
        while self._running:
            await asyncio.sleep(60)  # Check every minute

            inactive = self.tracker.check_inactive()
            for project_path in inactive:
                logger.info(f"Session ended (inactivity): {project_path}")
                await self._finalize_session(project_path)
                self.tracker.clear_project(project_path)

    async def _finalize_session(self, project_path: str) -> None:
        """Finalize a session - update context one last time."""
        path = Path(project_path)
        memory_file = path / ".mind" / "MEMORY.md"

        if not memory_file.exists():
            return

        try:
            content = memory_file.read_text(encoding="utf-8")
            result = self.parser.parse(content, str(memory_file))

            self.context_generator.update_claude_md(
                path,
                result,
                datetime.now(),
            )
            logger.info(f"Finalized session context: {project_path}")
        except Exception as e:
            logger.error(f"Error finalizing session: {e}")

    def stop(self) -> None:
        """Stop the daemon."""
        logger.info("Stopping Mind daemon...")
        self._running = False
        self.watcher.stop()

    def _cleanup(self) -> None:
        """Clean up daemon state."""
        # Remove PID file
        pid_file = get_pid_file()
        if pid_file.exists():
            pid_file.unlink()

        # Clear daemon state
        DaemonState().clear()

        logger.info("Mind daemon stopped.")


def setup_logging(verbose: bool = False) -> None:
    """Setup daemon logging."""
    level = logging.DEBUG if verbose else logging.INFO

    # Create logs directory
    log_dir = get_mind_home() / "logs"
    log_dir.mkdir(exist_ok=True)

    # File handler
    file_handler = logging.FileHandler(log_dir / "daemon.log")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("[%(levelname)s] %(message)s")
    )

    # Configure logger
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def run_daemon(verbose: bool = False) -> None:
    """Run the daemon (blocking)."""
    setup_logging(verbose)

    daemon = MindDaemon()

    # Setup signal handlers
    def handle_signal(signum, frame):
        daemon.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Run
    asyncio.run(daemon.start())


def stop_daemon() -> bool:
    """Stop the daemon by sending SIGTERM."""
    pid_file = get_pid_file()
    if not pid_file.exists():
        return False

    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        return True
    except (OSError, ValueError, ProcessLookupError):
        # Process not running or invalid PID
        if pid_file.exists():
            pid_file.unlink()
        DaemonState().clear()
        return False
