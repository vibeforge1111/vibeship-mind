"""Unit tests for stack.py - editor detection and instruction injection."""

import pytest
from pathlib import Path

# Import functions to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mind.stack import (
    detect_stack,
    get_config_file_for_stack,
    check_instructions_present,
    inject_mind_instructions,
    remove_mind_instructions,
    get_stack_display_name,
    MIND_START_MARKER,
    MIND_VERSION_MARKER,
    MIND_INSTRUCTIONS,
)


class TestDetectStack:
    """Tests for detect_stack function."""

    def test_detect_claude_code_from_claude_dir(self, tmp_path):
        """Should detect Claude Code from .claude directory."""
        (tmp_path / ".claude").mkdir()

        result = detect_stack(tmp_path)

        assert result == "claude-code"

    def test_detect_claude_code_from_claude_md(self, tmp_path):
        """Should detect Claude Code from CLAUDE.md file."""
        (tmp_path / "CLAUDE.md").write_text("# CLAUDE.md", encoding="utf-8")

        result = detect_stack(tmp_path)

        assert result == "claude-code"

    def test_detect_cursor_from_cursor_dir(self, tmp_path):
        """Should detect Cursor from .cursor directory."""
        (tmp_path / ".cursor").mkdir()

        result = detect_stack(tmp_path)

        assert result == "cursor"

    def test_detect_cursor_from_cursorrules(self, tmp_path):
        """Should detect Cursor from .cursorrules file."""
        (tmp_path / ".cursorrules").write_text("rules", encoding="utf-8")

        result = detect_stack(tmp_path)

        assert result == "cursor"

    def test_detect_windsurf_from_windsurf_dir(self, tmp_path):
        """Should detect Windsurf from .windsurf directory."""
        (tmp_path / ".windsurf").mkdir()

        result = detect_stack(tmp_path)

        assert result == "windsurf"

    def test_detect_windsurf_from_windsurfrules(self, tmp_path):
        """Should detect Windsurf from .windsurfrules file."""
        (tmp_path / ".windsurfrules").write_text("rules", encoding="utf-8")

        result = detect_stack(tmp_path)

        assert result == "windsurf"

    def test_detect_cline_from_cline_dir(self, tmp_path):
        """Should detect Cline from .cline directory."""
        (tmp_path / ".cline").mkdir()

        result = detect_stack(tmp_path)

        assert result == "cline"

    def test_detect_cline_from_clinerules(self, tmp_path):
        """Should detect Cline from .clinerules file."""
        (tmp_path / ".clinerules").write_text("rules", encoding="utf-8")

        result = detect_stack(tmp_path)

        assert result == "cline"

    def test_fallback_to_generic(self, tmp_path):
        """Should fallback to generic when no editor detected."""
        result = detect_stack(tmp_path)

        assert result == "generic"

    def test_claude_code_takes_priority(self, tmp_path):
        """Claude Code should take priority over other editors."""
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".cursor").mkdir()  # Also has Cursor

        result = detect_stack(tmp_path)

        assert result == "claude-code"


class TestGetConfigFileForStack:
    """Tests for get_config_file_for_stack function."""

    def test_claude_code_uses_claude_md(self, tmp_path):
        """Claude Code should use CLAUDE.md."""
        result = get_config_file_for_stack(tmp_path, "claude-code")

        assert result == tmp_path / "CLAUDE.md"

    def test_cursor_uses_cursorrules(self, tmp_path):
        """Cursor should use .cursorrules."""
        result = get_config_file_for_stack(tmp_path, "cursor")

        assert result == tmp_path / ".cursorrules"

    def test_windsurf_uses_windsurfrules(self, tmp_path):
        """Windsurf should use .windsurfrules."""
        result = get_config_file_for_stack(tmp_path, "windsurf")

        assert result == tmp_path / ".windsurfrules"

    def test_cline_uses_clinerules(self, tmp_path):
        """Cline should use .clinerules."""
        result = get_config_file_for_stack(tmp_path, "cline")

        assert result == tmp_path / ".clinerules"

    def test_generic_uses_agents_md(self, tmp_path):
        """Generic should use AGENTS.md."""
        result = get_config_file_for_stack(tmp_path, "generic")

        assert result == tmp_path / "AGENTS.md"

    def test_auto_detects_when_stack_none(self, tmp_path):
        """Should auto-detect stack when not specified."""
        (tmp_path / ".cursor").mkdir()

        result = get_config_file_for_stack(tmp_path, None)

        assert result == tmp_path / ".cursorrules"


class TestCheckInstructionsPresent:
    """Tests for check_instructions_present function."""

    def test_returns_not_present_when_file_missing(self, tmp_path):
        """Should return not present when config file doesn't exist."""
        result = check_instructions_present(tmp_path, "claude-code")

        assert result["present"] is False
        assert result["outdated"] is False

    def test_returns_not_present_when_no_marker(self, tmp_path):
        """Should return not present when marker not found."""
        config_file = tmp_path / "CLAUDE.md"
        config_file.write_text("# Some other content", encoding="utf-8")

        result = check_instructions_present(tmp_path, "claude-code")

        assert result["present"] is False

    def test_returns_present_when_marker_found(self, tmp_path):
        """Should return present when Mind marker found."""
        config_file = tmp_path / "CLAUDE.md"
        config_file.write_text(f"{MIND_START_MARKER}\nsome content", encoding="utf-8")

        result = check_instructions_present(tmp_path, "claude-code")

        assert result["present"] is True

    def test_returns_outdated_when_no_version(self, tmp_path):
        """Should return outdated when version marker missing."""
        config_file = tmp_path / "CLAUDE.md"
        config_file.write_text(f"{MIND_START_MARKER}\nold content", encoding="utf-8")

        result = check_instructions_present(tmp_path, "claude-code")

        assert result["present"] is True
        assert result["outdated"] is True

    def test_returns_not_outdated_when_version_present(self, tmp_path):
        """Should return not outdated when version marker present."""
        config_file = tmp_path / "CLAUDE.md"
        config_file.write_text(
            f"{MIND_VERSION_MARKER}\n{MIND_START_MARKER}\ncontent",
            encoding="utf-8"
        )

        result = check_instructions_present(tmp_path, "claude-code")

        assert result["present"] is True
        assert result["outdated"] is False


class TestInjectMindInstructions:
    """Tests for inject_mind_instructions function."""

    def test_creates_new_file_with_instructions(self, tmp_path):
        """Should create config file with Mind instructions."""
        result = inject_mind_instructions(tmp_path, "claude-code")

        assert result["success"] is True
        assert result["action"] == "created"

        config_file = tmp_path / "CLAUDE.md"
        assert config_file.exists()

        content = config_file.read_text(encoding="utf-8")
        assert MIND_START_MARKER in content
        assert MIND_VERSION_MARKER in content

    def test_adds_instructions_to_existing_file(self, tmp_path):
        """Should add instructions to existing file."""
        config_file = tmp_path / "CLAUDE.md"
        config_file.write_text("# Existing content\n\nSome rules here.", encoding="utf-8")

        result = inject_mind_instructions(tmp_path, "claude-code")

        assert result["success"] is True
        assert result["action"] == "created"

        content = config_file.read_text(encoding="utf-8")
        # Mind instructions at top
        assert content.startswith(MIND_VERSION_MARKER)
        # Existing content preserved
        assert "Existing content" in content
        assert "Some rules here" in content

    def test_skips_when_already_present(self, tmp_path):
        """Should skip when instructions already present and up-to-date."""
        config_file = tmp_path / "CLAUDE.md"
        config_file.write_text(
            f"{MIND_VERSION_MARKER}\n{MIND_INSTRUCTIONS}",
            encoding="utf-8"
        )

        result = inject_mind_instructions(tmp_path, "claude-code")

        assert result["success"] is True
        assert result["action"] == "skipped"

    def test_updates_outdated_instructions(self, tmp_path):
        """Should update when instructions are outdated."""
        config_file = tmp_path / "CLAUDE.md"
        config_file.write_text(f"{MIND_START_MARKER}\nold instructions", encoding="utf-8")

        result = inject_mind_instructions(tmp_path, "claude-code")

        assert result["success"] is True
        assert result["action"] == "updated"

        content = config_file.read_text(encoding="utf-8")
        assert MIND_VERSION_MARKER in content

    def test_force_updates_even_when_current(self, tmp_path):
        """Should update when force=True even if current."""
        config_file = tmp_path / "CLAUDE.md"
        config_file.write_text(
            f"{MIND_VERSION_MARKER}\n{MIND_INSTRUCTIONS}",
            encoding="utf-8"
        )

        result = inject_mind_instructions(tmp_path, "claude-code", force=True)

        assert result["success"] is True
        assert result["action"] == "updated"

    def test_auto_detects_stack(self, tmp_path):
        """Should auto-detect stack when not specified."""
        (tmp_path / ".cursor").mkdir()

        result = inject_mind_instructions(tmp_path, None)

        assert result["success"] is True
        assert result["config_file"] == tmp_path / ".cursorrules"


class TestRemoveMindInstructions:
    """Tests for remove_mind_instructions function."""

    def test_removes_instructions_with_version(self):
        """Should remove Mind instructions with version marker."""
        content = f"""{MIND_VERSION_MARKER}
{MIND_START_MARKER}

Instructions here.

---

# Existing content
"""
        result = remove_mind_instructions(content)

        assert MIND_VERSION_MARKER not in result
        assert MIND_START_MARKER not in result
        assert "Existing content" in result

    def test_removes_instructions_without_version(self):
        """Should remove old-style instructions without version."""
        content = f"""{MIND_START_MARKER}

Old instructions.

---

# Existing content
"""
        result = remove_mind_instructions(content)

        assert MIND_START_MARKER not in result
        assert "Existing content" in result

    def test_preserves_unrelated_content(self):
        """Should preserve content that isn't Mind instructions."""
        content = """# My Project

Some documentation here.

## Rules

Follow these rules.
"""
        result = remove_mind_instructions(content)

        assert result == content

    def test_handles_empty_string(self):
        """Should handle empty string."""
        result = remove_mind_instructions("")
        assert result == ""


class TestGetStackDisplayName:
    """Tests for get_stack_display_name function."""

    def test_claude_code_name(self):
        """Should return 'Claude Code' for claude-code."""
        assert get_stack_display_name("claude-code") == "Claude Code"

    def test_cursor_name(self):
        """Should return 'Cursor' for cursor."""
        assert get_stack_display_name("cursor") == "Cursor"

    def test_windsurf_name(self):
        """Should return 'Windsurf' for windsurf."""
        assert get_stack_display_name("windsurf") == "Windsurf"

    def test_cline_name(self):
        """Should return 'Cline' for cline."""
        assert get_stack_display_name("cline") == "Cline"

    def test_generic_name(self):
        """Should return 'Generic (AGENTS.md)' for generic."""
        assert get_stack_display_name("generic") == "Generic (AGENTS.md)"

    def test_unknown_returns_itself(self):
        """Should return the stack itself for unknown types."""
        assert get_stack_display_name("unknown") == "unknown"
