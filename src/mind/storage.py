"""Storage for Mind - projects registry and global config (v2: daemon-free)."""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


def get_mind_home() -> Path:
    """Get Mind home directory (~/.mind)."""
    home = Path(os.environ.get("MIND_HOME", Path.home() / ".mind"))
    home.mkdir(parents=True, exist_ok=True)
    return home


@dataclass
class ProjectInfo:
    path: str
    name: str
    stack: list[str] = field(default_factory=list)
    registered_at: str = ""
    last_activity: Optional[str] = None

    def __post_init__(self):
        if not self.registered_at:
            self.registered_at = datetime.now().isoformat()


@dataclass
class ProjectsRegistry:
    projects: dict[str, ProjectInfo] = field(default_factory=dict)

    @classmethod
    def load(cls) -> "ProjectsRegistry":
        """Load projects registry from disk."""
        path = get_mind_home() / "projects.json"
        if not path.exists():
            return cls()

        try:
            data = json.loads(path.read_text())
            projects = {}
            for key, info in data.get("projects", {}).items():
                projects[key] = ProjectInfo(**info)
            return cls(projects=projects)
        except (json.JSONDecodeError, OSError):
            return cls()

    def save(self) -> None:
        """Save projects registry to disk."""
        path = get_mind_home() / "projects.json"
        data = {
            "projects": {k: asdict(v) for k, v in self.projects.items()}
        }
        path.write_text(json.dumps(data, indent=2))

    def register(self, path: Path, stack: list[str]) -> ProjectInfo:
        """Register a project."""
        path_str = str(path.resolve())
        info = ProjectInfo(
            path=path_str,
            name=path.name,
            stack=stack,
        )
        self.projects[path_str] = info
        self.save()
        return info

    def unregister(self, path: Path) -> bool:
        """Unregister a project."""
        path_str = str(path.resolve())
        if path_str in self.projects:
            del self.projects[path_str]
            self.save()
            return True
        return False

    def get(self, path: Path) -> Optional[ProjectInfo]:
        """Get project info."""
        return self.projects.get(str(path.resolve()))

    def update_activity(self, path: Path) -> None:
        """Update last activity time for a project."""
        path_str = str(path.resolve())
        if path_str in self.projects:
            self.projects[path_str].last_activity = datetime.now().isoformat()
            self.save()

    def list_all(self) -> list[ProjectInfo]:
        """List all registered projects."""
        return list(self.projects.values())
