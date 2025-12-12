"""File system watcher for Mind daemon."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from watchfiles import awatch, Change


class ChangeType(Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"


@dataclass
class FileEvent:
    change_type: ChangeType
    path: Path
    project_path: Path
    timestamp: datetime


# File patterns to watch
WATCHED_EXTENSIONS = {
    ".md",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".svelte",
    ".vue",
    ".rs",
    ".go",
}

# Directories to ignore
IGNORED_DIRS = {
    "node_modules",
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".mind/.index",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


def should_watch(path: Path, project_path: Path) -> bool:
    """Check if a file should be watched."""
    # Always watch MEMORY.md
    if path.name == "MEMORY.md" and ".mind" in path.parts:
        return True

    # Check if in ignored directory
    try:
        rel_path = path.relative_to(project_path)
        for part in rel_path.parts:
            if part in IGNORED_DIRS or part.startswith("."):
                # Allow .mind directory
                if part == ".mind":
                    continue
                return False
    except ValueError:
        return False

    # Check extension
    if path.suffix in WATCHED_EXTENSIONS:
        return True

    # Watch git commit messages
    if path.name == "COMMIT_EDITMSG":
        return True

    return False


class FileWatcher:
    """Watches project directories for file changes."""

    def __init__(self):
        self.projects: dict[str, Path] = {}
        self.event_queue: asyncio.Queue[FileEvent] = asyncio.Queue()
        self._stop_event = asyncio.Event()

    def add_project(self, path: Path) -> None:
        """Register a project for watching."""
        self.projects[str(path)] = path

    def remove_project(self, path: Path) -> None:
        """Unregister a project."""
        self.projects.pop(str(path), None)

    async def watch(self) -> None:
        """Watch all registered projects for changes."""
        if not self.projects:
            return

        paths = list(self.projects.values())

        async for changes in awatch(
            *paths,
            stop_event=self._stop_event,
            recursive=True,
        ):
            for change_type, path_str in changes:
                path = Path(path_str)

                # Find which project this belongs to
                project_path = self._find_project(path)
                if not project_path:
                    continue

                # Check if we should watch this file
                if not should_watch(path, project_path):
                    continue

                # Map watchfiles change type to our enum
                if change_type == Change.added:
                    ct = ChangeType.ADDED
                elif change_type == Change.modified:
                    ct = ChangeType.MODIFIED
                elif change_type == Change.deleted:
                    ct = ChangeType.DELETED
                else:
                    continue

                event = FileEvent(
                    change_type=ct,
                    path=path,
                    project_path=project_path,
                    timestamp=datetime.now(),
                )

                await self.event_queue.put(event)

    def _find_project(self, path: Path) -> Optional[Path]:
        """Find which project a path belongs to."""
        for project_path in self.projects.values():
            try:
                path.relative_to(project_path)
                return project_path
            except ValueError:
                continue
        return None

    def stop(self) -> None:
        """Stop watching."""
        self._stop_event.set()


class Debouncer:
    """Debounce rapid file changes."""

    def __init__(self, delay_ms: int = 100):
        self.delay = delay_ms / 1000
        self.pending: dict[str, asyncio.Task] = {}

    async def debounce(self, key: str, callback: Callable) -> None:
        """Debounce a callback by key."""
        if key in self.pending:
            self.pending[key].cancel()

        self.pending[key] = asyncio.create_task(self._delayed_call(key, callback))

    async def _delayed_call(self, key: str, callback: Callable) -> None:
        """Call callback after delay."""
        try:
            await asyncio.sleep(self.delay)
            del self.pending[key]
            if asyncio.iscoroutinefunction(callback):
                await callback()
            else:
                callback()
        except asyncio.CancelledError:
            pass
