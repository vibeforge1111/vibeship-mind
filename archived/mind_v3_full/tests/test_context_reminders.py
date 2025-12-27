"""Tests for context-matching reminders."""

import pytest
from pathlib import Path
import tempfile
import shutil

from mind.mcp.server import (
    parse_when,
    add_reminder,
    parse_reminders,
    get_context_reminders,
)


class TestParseWhenContext:
    """Test parse_when() with context-based triggers."""

    def test_when_i_mention_single_keyword(self):
        """'when I mention auth' -> ('auth', 'context')"""
        due, reminder_type = parse_when("when I mention auth")
        assert reminder_type == "context"
        assert due == "auth"

    def test_when_i_mention_multiple_keywords_comma(self):
        """'when I mention auth, login' -> ('auth,login', 'context')"""
        due, reminder_type = parse_when("when I mention auth, login")
        assert reminder_type == "context"
        assert due == "auth,login"

    def test_when_i_mention_multiple_keywords_and(self):
        """'when I mention auth and login' -> ('auth,login', 'context')"""
        due, reminder_type = parse_when("when I mention auth and login")
        assert reminder_type == "context"
        assert due == "auth,login"

    def test_when_we_work_on(self):
        """'when we work on authentication' -> ('authentication', 'context')"""
        due, reminder_type = parse_when("when we work on authentication")
        assert reminder_type == "context"
        assert due == "authentication"

    def test_when_comes_up(self):
        """'when database comes up' -> ('database', 'context')"""
        due, reminder_type = parse_when("when database comes up")
        assert reminder_type == "context"
        assert due == "database"

    def test_case_insensitive(self):
        """Context patterns should be case insensitive."""
        due, reminder_type = parse_when("When I Mention AUTH")
        assert reminder_type == "context"
        assert due == "auth"


class TestGetContextReminders:
    """Test get_context_reminders() function."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory with .mind folder."""
        temp_dir = Path(tempfile.mkdtemp())
        mind_dir = temp_dir / ".mind"
        mind_dir.mkdir()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_returns_only_context_reminders(self, temp_project):
        """Should return only context-type reminders, not time-based ones."""
        # Add a context reminder
        add_reminder(temp_project, "check security audit", "auth,login", "context")
        # Add a time-based reminder
        add_reminder(temp_project, "deploy fix", "2025-12-20", "absolute")

        context_reminders = get_context_reminders(temp_project)

        assert len(context_reminders) == 1
        assert context_reminders[0]["message"] == "check security audit"
        assert context_reminders[0]["type"] == "context"
        assert context_reminders[0]["due"] == "auth,login"

    def test_excludes_done_reminders(self, temp_project):
        """Should exclude completed context reminders."""
        add_reminder(temp_project, "check security audit", "auth", "context")

        # Manually mark it as done
        reminders_file = temp_project / ".mind" / "REMINDERS.md"
        content = reminders_file.read_text(encoding="utf-8")
        content = content.replace("- [ ]", "- [x]")
        reminders_file.write_text(content, encoding="utf-8")

        context_reminders = get_context_reminders(temp_project)
        assert len(context_reminders) == 0

    def test_empty_when_no_context_reminders(self, temp_project):
        """Should return empty list when no context reminders exist."""
        # Add only time-based reminder
        add_reminder(temp_project, "deploy fix", "2025-12-20", "absolute")

        context_reminders = get_context_reminders(temp_project)
        assert context_reminders == []


class TestContextRemindersInRecall:
    """Test that context reminders appear in mind_recall output."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory with required files."""
        temp_dir = Path(tempfile.mkdtemp())
        mind_dir = temp_dir / ".mind"
        mind_dir.mkdir()
        # Create minimal MEMORY.md
        (mind_dir / "MEMORY.md").write_text("# Memory\n\ndecided to use file-based storage\n", encoding="utf-8")
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_context_reminders_in_output_json(self, temp_project):
        """Context reminders should appear in the output JSON."""
        import json
        import asyncio
        from mind.mcp.server import handle_recall, add_reminder

        # Change to temp project directory for handle_recall to find it
        import os
        old_cwd = os.getcwd()
        os.chdir(temp_project)

        try:
            # Add a context reminder
            add_reminder(temp_project, "check security audit", "auth,login", "context")

            # Call handle_recall
            result = asyncio.run(handle_recall({"project_path": str(temp_project)}))
            output = json.loads(result[0].text)

            # Should have context_reminders in output
            assert "context_reminders" in output
            assert len(output["context_reminders"]) == 1
            assert output["context_reminders"][0]["message"] == "check security audit"
            assert output["context_reminders"][0]["keywords"] == "auth,login"
        finally:
            os.chdir(old_cwd)

    def test_context_reminders_in_context_string(self, temp_project):
        """Context reminders should appear in the context string for Claude to see."""
        import json
        import asyncio
        from mind.mcp.server import handle_recall, add_reminder

        import os
        old_cwd = os.getcwd()
        os.chdir(temp_project)

        try:
            # Add a context reminder
            add_reminder(temp_project, "check security audit", "auth,login", "context")

            # Call handle_recall
            result = asyncio.run(handle_recall({"project_path": str(temp_project)}))
            output = json.loads(result[0].text)

            # Context string should mention the reminder with keywords
            context = output["context"]
            assert "Context Reminders" in context
            assert "check security audit" in context
            assert "auth" in context
        finally:
            os.chdir(old_cwd)
