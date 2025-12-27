"""Stack detection from project files."""

import json
from pathlib import Path


def detect_stack(project_path: Path) -> list[str]:
    """Auto-detect project stack from files."""
    stack = []

    # Package.json analysis
    pkg_json = project_path / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            if "@sveltejs/kit" in deps or "svelte" in deps:
                stack.append("sveltekit" if "@sveltejs/kit" in deps else "svelte")
            if "next" in deps:
                stack.append("nextjs")
            if "react" in deps and "next" not in deps:
                stack.append("react")
            if "vue" in deps:
                stack.append("vue")
            if "typescript" in deps:
                stack.append("typescript")
            if "tailwindcss" in deps:
                stack.append("tailwind")
        except (json.JSONDecodeError, OSError):
            pass

    # Python analysis
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        stack.append("python")
        try:
            content = pyproject.read_text().lower()
            if "fastapi" in content:
                stack.append("fastapi")
            if "django" in content:
                stack.append("django")
            if "flask" in content:
                stack.append("flask")
        except OSError:
            pass

    # Other project files
    if (project_path / "Cargo.toml").exists():
        stack.append("rust")
    if (project_path / "go.mod").exists():
        stack.append("go")
    if (project_path / "vercel.json").exists():
        stack.append("vercel")
    if (project_path / "supabase").is_dir():
        stack.append("supabase")
    if (project_path / "docker-compose.yml").exists() or (
        project_path / "docker-compose.yaml"
    ).exists():
        stack.append("docker")

    return stack
