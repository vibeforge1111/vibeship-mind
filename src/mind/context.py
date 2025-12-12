"""CLAUDE.md context injection."""

import re
from pathlib import Path

from .templates import CONTEXT_TEMPLATE


def generate_context(stack: list[str]) -> str:
    """Generate MIND:CONTEXT section."""
    stack_str = ", ".join(stack) if stack else "(not detected)"
    return CONTEXT_TEMPLATE.format(stack=stack_str)


def update_claude_md(project_path: Path, stack: list[str]) -> None:
    """Add/update MIND:CONTEXT section in CLAUDE.md."""
    claude_md = project_path / "CLAUDE.md"
    context = generate_context(stack)

    if claude_md.exists():
        content = claude_md.read_text()

        # Remove existing MIND:CONTEXT section
        content = re.sub(
            r"<!-- MIND:CONTEXT.*?<!-- MIND:END -->\n*",
            "",
            content,
            flags=re.DOTALL,
        )

        # Inject at top
        content = context + "\n\n" + content.lstrip()
    else:
        # Create new CLAUDE.md
        content = context + "\n\n# Project Instructions\n\n(Add your instructions here)\n"

    # Write atomically
    temp_path = claude_md.with_suffix(".md.tmp")
    temp_path.write_text(content)
    temp_path.replace(claude_md)
