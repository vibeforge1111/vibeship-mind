"""Stack detection and editor-specific instruction injection.

Detects which AI coding assistant is being used and injects
Mind instructions into the appropriate config file.
"""

import re
from pathlib import Path
from typing import Literal


# Editor type definitions
EditorType = Literal["claude-code", "cursor", "windsurf", "cline", "generic"]


# Mind instructions template - injected at TOP of editor config files
MIND_INSTRUCTIONS = '''## Memory (Mind)

This project uses Mind for persistent memory across sessions.

### Required Protocol

1. **Session Start**: ALWAYS call `mind_recall()` before responding to the first message. This loads context from previous sessions.

2. **During Work**: Use `mind_log(message, type)` to capture what happens:
   - `mind_log("chose X over Y - simpler", type="decision")` -> MEMORY.md
   - `mind_log("API returns 500 on large payloads", type="problem")` -> MEMORY.md
   - `mind_log("Safari needs vendor prefix for X", type="learning")` -> MEMORY.md
   - `mind_log("resolved by increasing timeout", type="progress")` -> MEMORY.md
   - `mind_log("working on auth flow", type="experience")` -> SESSION.md
   - `mind_log("build keeps failing", type="blocker")` -> SESSION.md
   - `mind_log("tried Redis - too complex", type="rejected")` -> SESSION.md
   - `mind_log("assuming user has stable internet", type="assumption")` -> SESSION.md

3. **Session End**: Summarize with `## DATE | what happened | mood: X`

### Two-Layer Memory

**MEMORY.md** (permanent, cross-session):
- Decisions, learnings, problems, progress
- Use types: `decision`, `learning`, `problem`, `progress`

**SESSION.md** (ephemeral, within-session):
- Raw experience, blockers, rejected approaches, assumptions
- Use types: `experience`, `blocker`, `rejected`, `assumption`
- Valuable items get promoted to MEMORY.md on session gap (>30 min)

### Tools Available

- `mind_recall()` - Load session context (CALL FIRST!)
- `mind_log(msg, type)` - Log to session or memory (routes by type)
- `mind_session()` - Get current session state
- `mind_blocker(description)` - Log blocker + auto-search memory for solutions
- `mind_search(query)` - Find specific memories
- `mind_remind(msg, when)` - Set time or context reminder
- `mind_checkpoint()` - Force process pending memories
- `mind_edges(intent)` - Check for gotchas before coding
- `mind_status()` - Check memory health
'''

# Version marker for detecting outdated instructions
MIND_VERSION_MARKER = "<!-- MIND:VERSION:2 -->"

# Markers for detecting Mind instruction blocks
MIND_START_MARKER = "## Memory (Mind)"
MIND_END_MARKER = "<!-- MIND:END -->"


def detect_stack(project_path: Path) -> EditorType:
    """Detect which AI coding assistant is being used.

    Detection order (first match wins):
    1. .claude/ directory -> claude-code
    2. .cursor/ directory -> cursor
    3. .windsurf/ directory or .windsurfrules -> windsurf
    4. .cline/ directory or .clinerules -> cline
    5. Fallback -> generic

    Returns:
        EditorType indicating detected editor.
    """
    # Claude Code detection
    if (project_path / ".claude").exists():
        return "claude-code"

    # Also check for CLAUDE.md as indicator
    if (project_path / "CLAUDE.md").exists():
        return "claude-code"

    # Cursor detection
    if (project_path / ".cursor").exists():
        return "cursor"
    if (project_path / ".cursorrules").exists():
        return "cursor"

    # Windsurf detection
    if (project_path / ".windsurf").exists():
        return "windsurf"
    if (project_path / ".windsurfrules").exists():
        return "windsurf"

    # Cline detection
    if (project_path / ".cline").exists():
        return "cline"
    if (project_path / ".clinerules").exists():
        return "cline"

    # Generic fallback
    return "generic"


def get_config_file_for_stack(project_path: Path, stack: EditorType | None = None) -> Path:
    """Get the config file path for the detected stack.

    Args:
        project_path: Project root directory.
        stack: Optional stack override. If None, auto-detects.

    Returns:
        Path to the config file to use.
    """
    if stack is None:
        stack = detect_stack(project_path)

    config_files = {
        "claude-code": project_path / "CLAUDE.md",
        "cursor": project_path / ".cursorrules",
        "windsurf": project_path / ".windsurfrules",
        "cline": project_path / ".clinerules",
        "generic": project_path / "AGENTS.md",
    }

    return config_files.get(stack, config_files["generic"])


def check_instructions_present(project_path: Path, stack: EditorType | None = None) -> dict:
    """Check if Mind instructions are present and up-to-date.

    Returns:
        dict with:
        - present: bool - Whether instructions exist
        - outdated: bool - Whether instructions need updating
        - config_file: Path - Config file checked
    """
    config_file = get_config_file_for_stack(project_path, stack)

    result = {
        "present": False,
        "outdated": False,
        "config_file": config_file,
    }

    if not config_file.exists():
        return result

    try:
        content = config_file.read_text(encoding="utf-8")
    except OSError:
        return result

    # Check for Mind instructions
    if MIND_START_MARKER in content:
        result["present"] = True

        # Check if outdated (no version marker or old version)
        if MIND_VERSION_MARKER not in content:
            result["outdated"] = True

    return result


def inject_mind_instructions(
    project_path: Path,
    stack: EditorType | None = None,
    force: bool = False
) -> dict:
    """Inject Mind instructions into the appropriate config file.

    Instructions are added at the TOP of the file for prominence.

    Args:
        project_path: Project root directory.
        stack: Optional stack override. If None, auto-detects.
        force: If True, update even if instructions already present.

    Returns:
        dict with:
        - success: bool
        - action: str - 'created', 'updated', 'skipped', or 'error'
        - config_file: Path
        - message: str
    """
    if stack is None:
        stack = detect_stack(project_path)

    config_file = get_config_file_for_stack(project_path, stack)

    result = {
        "success": False,
        "action": "error",
        "config_file": config_file,
        "message": "",
    }

    # Check current state
    check = check_instructions_present(project_path, stack)

    if check["present"] and not check["outdated"] and not force:
        result["success"] = True
        result["action"] = "skipped"
        result["message"] = "Mind instructions already present and up-to-date"
        return result

    try:
        # Read existing content if file exists
        existing_content = ""
        if config_file.exists():
            existing_content = config_file.read_text(encoding="utf-8")

        # Remove old Mind instructions if present
        if check["present"]:
            existing_content = remove_mind_instructions(existing_content)

        # Build new content with Mind instructions at TOP
        mind_block = f"{MIND_VERSION_MARKER}\n{MIND_INSTRUCTIONS}\n---\n\n"

        # Add existing content after Mind instructions
        new_content = mind_block + existing_content.lstrip()

        # Write to file
        config_file.write_text(new_content, encoding="utf-8")

        if check["present"]:
            result["action"] = "updated"
            result["message"] = f"Updated Mind instructions in {config_file.name}"
        else:
            result["action"] = "created"
            result["message"] = f"Added Mind instructions to {config_file.name}"

        result["success"] = True

    except OSError as e:
        result["message"] = f"Failed to write {config_file.name}: {e}"

    return result


def remove_mind_instructions(content: str) -> str:
    """Remove existing Mind instruction block from content.

    Handles both old and new format instructions.
    """
    # Pattern to match the Mind instruction block
    # Matches from version marker or start marker to end marker or next major section
    patterns = [
        # New format with version marker
        rf"{re.escape(MIND_VERSION_MARKER)}.*?(?={re.escape(MIND_END_MARKER)}|---\n\n|\Z)",
        # Old format without version marker
        rf"{re.escape(MIND_START_MARKER)}.*?(?={re.escape(MIND_END_MARKER)}|---\n\n|\Z)",
    ]

    result = content
    for pattern in patterns:
        result = re.sub(pattern, "", result, flags=re.DOTALL)

    # Also remove the end marker if present
    result = result.replace(MIND_END_MARKER, "")

    # Clean up extra blank lines at start
    result = result.lstrip("\n")

    # Remove stray --- separators at start
    if result.startswith("---"):
        result = result[3:].lstrip("\n")

    return result


def get_stack_display_name(stack: EditorType) -> str:
    """Get human-readable name for a stack type."""
    names = {
        "claude-code": "Claude Code",
        "cursor": "Cursor",
        "windsurf": "Windsurf",
        "cline": "Cline",
        "generic": "Generic (AGENTS.md)",
    }
    return names.get(stack, stack)
