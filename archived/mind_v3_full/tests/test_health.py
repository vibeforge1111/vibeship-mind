"""Unit tests for health.py - auto-repair and diagnostics."""

import pytest
import json
from pathlib import Path

# Import functions to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mind.health import (
    get_mind_dir,
    check_health,
    check_session_health,
    check_memory_health,
    check_config_health,
    check_reminders_health,
    repair_issues,
    repair_session_file,
    repair_session_sections,
    repair_memory_file,
    repair_config_file,
    repair_reminders_file,
    auto_repair,
)


class TestGetMindDir:
    """Tests for get_mind_dir function."""

    def test_returns_mind_dir_path(self, tmp_path):
        """Should return .mind directory path."""
        result = get_mind_dir(tmp_path)
        assert result == tmp_path / ".mind"


class TestCheckHealth:
    """Tests for check_health function."""

    def test_healthy_project(self, tmp_path):
        """Should return healthy for complete project."""
        # Create complete Mind setup
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()

        (mind_dir / "SESSION.md").write_text("""# Session

## Experience

## Blockers

## Rejected

## Assumptions
""", encoding="utf-8")

        (mind_dir / "MEMORY.md").write_text("""# Project

## Project State
- Goal: Test
""", encoding="utf-8")

        (mind_dir / "config.json").write_text('{"version": 1}', encoding="utf-8")

        (mind_dir / "REMINDERS.md").write_text("# Reminders\n", encoding="utf-8")

        result = check_health(tmp_path)

        assert result["healthy"] is True
        assert len(result["issues"]) == 0

    def test_missing_mind_dir(self, tmp_path):
        """Should detect missing .mind directory."""
        result = check_health(tmp_path)

        assert result["healthy"] is False
        assert any(i["type"] == "missing_mind_dir" for i in result["issues"])

    def test_multiple_issues(self, tmp_path):
        """Should detect multiple issues."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        # Missing all files

        result = check_health(tmp_path)

        assert result["healthy"] is False
        assert len(result["issues"]) > 0


class TestCheckSessionHealth:
    """Tests for check_session_health function."""

    @pytest.fixture
    def project_with_mind(self, tmp_path):
        """Create project with .mind directory."""
        (tmp_path / ".mind").mkdir()
        return tmp_path

    def test_missing_session_file(self, project_with_mind):
        """Should detect missing SESSION.md."""
        issues = check_session_health(project_with_mind)

        assert len(issues) == 1
        assert issues[0]["type"] == "missing_session"
        assert issues[0]["auto_fixable"] is True

    def test_missing_sections(self, project_with_mind):
        """Should detect missing sections."""
        session_file = project_with_mind / ".mind" / "SESSION.md"
        session_file.write_text("# Session\n\n## Experience\n", encoding="utf-8")

        issues = check_session_health(project_with_mind)

        # Should detect missing Blockers, Rejected, Assumptions
        assert len(issues) == 3
        section_names = [i["section"] for i in issues]
        assert "Blockers" in section_names
        assert "Rejected" in section_names
        assert "Assumptions" in section_names

    def test_complete_session(self, project_with_mind):
        """Should return no issues for complete session."""
        session_file = project_with_mind / ".mind" / "SESSION.md"
        session_file.write_text("""# Session

## Experience

## Blockers

## Rejected

## Assumptions
""", encoding="utf-8")

        issues = check_session_health(project_with_mind)

        assert len(issues) == 0


class TestCheckMemoryHealth:
    """Tests for check_memory_health function."""

    @pytest.fixture
    def project_with_mind(self, tmp_path):
        """Create project with .mind directory."""
        (tmp_path / ".mind").mkdir()
        return tmp_path

    def test_missing_memory_file(self, project_with_mind):
        """Should detect missing MEMORY.md."""
        issues = check_memory_health(project_with_mind)

        assert len(issues) == 1
        assert issues[0]["type"] == "missing_memory"

    def test_malformed_memory(self, project_with_mind):
        """Should detect malformed MEMORY.md."""
        memory_file = project_with_mind / ".mind" / "MEMORY.md"
        memory_file.write_text("# No project state section", encoding="utf-8")

        issues = check_memory_health(project_with_mind)

        assert len(issues) == 1
        assert issues[0]["type"] == "malformed_memory"

    def test_complete_memory(self, project_with_mind):
        """Should return no issues for complete memory."""
        memory_file = project_with_mind / ".mind" / "MEMORY.md"
        memory_file.write_text("# Project\n\n## Project State\n- Goal: Test", encoding="utf-8")

        issues = check_memory_health(project_with_mind)

        assert len(issues) == 0


class TestCheckConfigHealth:
    """Tests for check_config_health function."""

    @pytest.fixture
    def project_with_mind(self, tmp_path):
        """Create project with .mind directory."""
        (tmp_path / ".mind").mkdir()
        return tmp_path

    def test_missing_config(self, project_with_mind):
        """Should detect missing config.json."""
        issues = check_config_health(project_with_mind)

        assert len(issues) == 1
        assert issues[0]["type"] == "missing_config"

    def test_invalid_json(self, project_with_mind):
        """Should detect invalid JSON."""
        config_file = project_with_mind / ".mind" / "config.json"
        config_file.write_text("not valid json {{{", encoding="utf-8")

        issues = check_config_health(project_with_mind)

        assert len(issues) == 1
        assert issues[0]["type"] == "invalid_config_json"

    def test_valid_config(self, project_with_mind):
        """Should return no issues for valid config."""
        config_file = project_with_mind / ".mind" / "config.json"
        config_file.write_text('{"version": 1}', encoding="utf-8")

        issues = check_config_health(project_with_mind)

        assert len(issues) == 0


class TestCheckRemindersHealth:
    """Tests for check_reminders_health function."""

    @pytest.fixture
    def project_with_mind(self, tmp_path):
        """Create project with .mind directory."""
        (tmp_path / ".mind").mkdir()
        return tmp_path

    def test_missing_reminders(self, project_with_mind):
        """Should detect missing REMINDERS.md."""
        issues = check_reminders_health(project_with_mind)

        assert len(issues) == 1
        assert issues[0]["type"] == "missing_reminders"

    def test_existing_reminders(self, project_with_mind):
        """Should return no issues when REMINDERS.md exists."""
        reminders_file = project_with_mind / ".mind" / "REMINDERS.md"
        reminders_file.write_text("# Reminders\n", encoding="utf-8")

        issues = check_reminders_health(project_with_mind)

        assert len(issues) == 0


class TestRepairIssues:
    """Tests for repair_issues function."""

    def test_repairs_missing_mind_dir(self, tmp_path):
        """Should repair missing .mind directory."""
        issues = [{"type": "missing_mind_dir", "auto_fixable": True}]

        result = repair_issues(tmp_path, issues)

        assert len(result["repaired"]) == 1
        assert (tmp_path / ".mind").exists()

    def test_repairs_missing_session(self, tmp_path):
        """Should repair missing SESSION.md."""
        (tmp_path / ".mind").mkdir()
        issues = [{"type": "missing_session", "auto_fixable": True}]

        result = repair_issues(tmp_path, issues)

        assert len(result["repaired"]) == 1
        assert (tmp_path / ".mind" / "SESSION.md").exists()

    def test_repairs_missing_config(self, tmp_path):
        """Should repair missing config.json."""
        (tmp_path / ".mind").mkdir()
        issues = [{"type": "missing_config", "auto_fixable": True}]

        result = repair_issues(tmp_path, issues)

        assert len(result["repaired"]) == 1
        assert (tmp_path / ".mind" / "config.json").exists()

    def test_skips_non_auto_fixable(self, tmp_path):
        """Should skip issues that aren't auto-fixable."""
        (tmp_path / ".mind").mkdir()
        issues = [{"type": "malformed_memory", "auto_fixable": False}]

        result = repair_issues(tmp_path, issues)

        assert len(result["skipped"]) == 1
        assert len(result["repaired"]) == 0

    def test_runs_health_check_when_no_issues_provided(self, tmp_path):
        """Should run health check when issues not provided."""
        # Don't create .mind dir - should detect and fix

        result = repair_issues(tmp_path, None)

        # Should have detected and repaired missing_mind_dir
        assert any(r["type"] == "missing_mind_dir" for r in result["repaired"])


class TestRepairSessionFile:
    """Tests for repair_session_file function."""

    def test_creates_session_file(self, tmp_path):
        """Should create SESSION.md with template."""
        (tmp_path / ".mind").mkdir()

        result = repair_session_file(tmp_path)

        assert result is True
        session_file = tmp_path / ".mind" / "SESSION.md"
        assert session_file.exists()

        content = session_file.read_text(encoding="utf-8")
        assert "## Experience" in content
        assert "## Blockers" in content
        assert "## Rejected" in content
        assert "## Assumptions" in content


class TestRepairSessionSections:
    """Tests for repair_session_sections function."""

    def test_adds_missing_sections(self, tmp_path):
        """Should add missing sections to existing SESSION.md."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        session_file = mind_dir / "SESSION.md"
        session_file.write_text("# Session\n\n## Experience\n- entry\n", encoding="utf-8")

        result = repair_session_sections(tmp_path)

        assert result is True
        content = session_file.read_text(encoding="utf-8")
        assert "## Blockers" in content
        assert "## Rejected" in content
        assert "## Assumptions" in content
        assert "- entry" in content  # Original content preserved


class TestRepairMemoryFile:
    """Tests for repair_memory_file function."""

    def test_creates_memory_file(self, tmp_path):
        """Should create MEMORY.md with template."""
        (tmp_path / ".mind").mkdir()

        result = repair_memory_file(tmp_path)

        assert result is True
        memory_file = tmp_path / ".mind" / "MEMORY.md"
        assert memory_file.exists()

        content = memory_file.read_text(encoding="utf-8")
        assert "## Project State" in content


class TestRepairConfigFile:
    """Tests for repair_config_file function."""

    def test_creates_config_file(self, tmp_path):
        """Should create config.json with defaults."""
        (tmp_path / ".mind").mkdir()

        result = repair_config_file(tmp_path)

        assert result is True
        config_file = tmp_path / ".mind" / "config.json"
        assert config_file.exists()

        config = json.loads(config_file.read_text(encoding="utf-8"))
        assert "version" in config


class TestRepairRemindersFile:
    """Tests for repair_reminders_file function."""

    def test_creates_reminders_file(self, tmp_path):
        """Should create REMINDERS.md with template."""
        (tmp_path / ".mind").mkdir()

        result = repair_reminders_file(tmp_path)

        assert result is True
        reminders_file = tmp_path / ".mind" / "REMINDERS.md"
        assert reminders_file.exists()

        content = reminders_file.read_text(encoding="utf-8")
        assert "Reminders" in content


class TestAutoRepair:
    """Tests for auto_repair function."""

    def test_healthy_project_unchanged(self, tmp_path):
        """Should report healthy project without changes."""
        # Create complete setup
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        (mind_dir / "SESSION.md").write_text("""# Session

## Experience

## Blockers

## Rejected

## Assumptions
""", encoding="utf-8")
        (mind_dir / "MEMORY.md").write_text("# P\n\n## Project State\n", encoding="utf-8")
        (mind_dir / "config.json").write_text('{"version": 1}', encoding="utf-8")
        (mind_dir / "REMINDERS.md").write_text("# Reminders\n", encoding="utf-8")

        result = auto_repair(tmp_path)

        assert result["was_healthy"] is True
        assert result["is_healthy"] is True
        assert result["repaired_count"] == 0

    def test_repairs_unhealthy_project(self, tmp_path):
        """Should repair unhealthy project."""
        result = auto_repair(tmp_path)

        assert result["was_healthy"] is False
        assert result["is_healthy"] is True
        assert result["repaired_count"] > 0

    def test_returns_repair_types(self, tmp_path):
        """Should return list of repair types performed."""
        result = auto_repair(tmp_path)

        assert "missing_mind_dir" in result["repairs"]
