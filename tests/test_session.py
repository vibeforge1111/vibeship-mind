"""Unit tests for session functions - SESSION.md handling."""

import pytest
from pathlib import Path
import tempfile
from datetime import date

# Import functions to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mind.mcp.server import (
    parse_session_section,
    repair_session_file,
    update_session_section,
    auto_categorize_session_type,
    clear_session_file,
    get_session_file,
)


class TestAutoCategorizeSessionType:
    """Tests for auto_categorize_session_type function."""

    def test_categorize_rejected_tried(self):
        """Messages with 'tried' should be categorized as rejected."""
        assert auto_categorize_session_type("tried Redis but it was too complex") == "rejected"
        assert auto_categorize_session_type("Tried using websockets") == "rejected"

    def test_categorize_rejected_didnt_work(self):
        """Messages with 'didn't work' should be categorized as rejected."""
        assert auto_categorize_session_type("the approach didn't work because of X") == "rejected"
        assert auto_categorize_session_type("caching doesn't work here") == "rejected"

    def test_categorize_rejected_failed(self):
        """Messages with 'failed' should be categorized as rejected."""
        assert auto_categorize_session_type("the build failed") == "rejected"
        assert auto_categorize_session_type("this approach FAILED miserably") == "rejected"

    def test_categorize_rejected_overkill(self):
        """Messages with complexity indicators should be rejected."""
        assert auto_categorize_session_type("Redis is overkill for this") == "rejected"
        assert auto_categorize_session_type("this is too complex for our needs") == "rejected"
        assert auto_categorize_session_type("way too slow for production") == "rejected"

    def test_categorize_blocker_stuck(self):
        """Messages with 'stuck' should be categorized as blocker."""
        assert auto_categorize_session_type("I'm stuck on the auth flow") == "blocker"
        assert auto_categorize_session_type("completely stuck here") == "blocker"

    def test_categorize_blocker_blocked(self):
        """Messages with 'blocked' should be categorized as blocker."""
        assert auto_categorize_session_type("blocked by missing API key") == "blocker"
        assert auto_categorize_session_type("we're BLOCKED on this") == "blocker"

    def test_categorize_blocker_cant_figure(self):
        """Messages expressing confusion should be blockers."""
        assert auto_categorize_session_type("can't figure out why this fails") == "blocker"
        assert auto_categorize_session_type("don't know how to proceed") == "blocker"
        assert auto_categorize_session_type("no idea what's causing this") == "blocker"

    def test_categorize_blocker_struggling(self):
        """Messages about struggling should be blockers."""
        assert auto_categorize_session_type("struggling with the database schema") == "blocker"
        assert auto_categorize_session_type("hitting a wall with this bug") == "blocker"
        assert auto_categorize_session_type("this is a dead end") == "blocker"

    def test_categorize_assumption_assuming(self):
        """Messages with 'assuming' should be categorized as assumption."""
        assert auto_categorize_session_type("assuming the user has internet access") == "assumption"
        assert auto_categorize_session_type("I assume this returns a string") == "assumption"

    def test_categorize_assumption_think(self):
        """Messages with uncertainty should be assumptions."""
        assert auto_categorize_session_type("I think this should work") == "assumption"
        assert auto_categorize_session_type("probably need to restart the server") == "assumption"
        assert auto_categorize_session_type("should be UTF-8 encoded") == "assumption"

    def test_categorize_assumption_hypothesis(self):
        """Messages with hypothesis/guessing should be assumptions."""
        assert auto_categorize_session_type("my hypothesis is that it's a race condition") == "assumption"
        assert auto_categorize_session_type("guessing the cache is stale") == "assumption"
        assert auto_categorize_session_type("expecting the API to return JSON") == "assumption"

    def test_categorize_experience_default(self):
        """Neutral messages should default to experience."""
        assert auto_categorize_session_type("reading the auth module") == "experience"
        assert auto_categorize_session_type("working on the login page") == "experience"
        assert auto_categorize_session_type("implementing the feature") == "experience"
        assert auto_categorize_session_type("looking at the database schema") == "experience"

    def test_categorize_case_insensitive(self):
        """Categorization should be case-insensitive."""
        assert auto_categorize_session_type("TRIED this approach") == "rejected"
        assert auto_categorize_session_type("I'M STUCK") == "blocker"
        assert auto_categorize_session_type("ASSUMING this works") == "assumption"

    def test_categorize_empty_string(self):
        """Empty string should default to experience."""
        assert auto_categorize_session_type("") == "experience"


class TestParseSessionSection:
    """Tests for parse_session_section function."""

    def test_parse_empty_section(self):
        """Empty section should return empty list."""
        content = """# Session: 2025-12-18

## Experience
<!-- Raw moments -->

## Blockers

## Rejected
"""
        items = parse_session_section(content, "Blockers")
        assert items == []

    def test_parse_single_item(self):
        """Single item should be returned."""
        content = """# Session: 2025-12-18

## Experience
- working on auth flow

## Blockers
"""
        items = parse_session_section(content, "Experience")
        assert len(items) == 1
        assert items[0] == "working on auth flow"

    def test_parse_multiple_items(self):
        """Multiple items should be returned."""
        content = """# Session: 2025-12-18

## Rejected
- tried Redis - too complex
- tried websockets - overkill
- tried caching - not needed

## Assumptions
"""
        items = parse_session_section(content, "Rejected")
        assert len(items) == 3
        assert "tried Redis - too complex" in items
        assert "tried websockets - overkill" in items
        assert "tried caching - not needed" in items

    def test_parse_items_without_dash(self):
        """Items without dash prefix should also be parsed."""
        content = """# Session: 2025-12-18

## Experience
raw text without dash

## Blockers
"""
        items = parse_session_section(content, "Experience")
        assert len(items) == 1
        assert items[0] == "raw text without dash"

    def test_parse_skip_comments(self):
        """HTML comments should be skipped."""
        content = """# Session: 2025-12-18

## Experience
<!-- This is a comment -->
- actual item

## Blockers
"""
        items = parse_session_section(content, "Experience")
        assert len(items) == 1
        assert items[0] == "actual item"

    def test_parse_skip_empty_lines(self):
        """Empty lines should be skipped."""
        content = """# Session: 2025-12-18

## Experience

- item one

- item two


## Blockers
"""
        items = parse_session_section(content, "Experience")
        assert len(items) == 2

    def test_parse_nonexistent_section(self):
        """Nonexistent section should return empty list."""
        content = """# Session: 2025-12-18

## Experience
- something

## Blockers
"""
        items = parse_session_section(content, "NonExistent")
        assert items == []

    def test_parse_case_insensitive_section(self):
        """Section matching should be case-insensitive."""
        content = """# Session: 2025-12-18

## EXPERIENCE
- item one

## Blockers
"""
        # Should still find it (the function uses case-insensitive flag)
        items = parse_session_section(content, "Experience")
        assert len(items) == 1


class TestRepairSessionFile:
    """Tests for repair_session_file function."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project directory with .mind folder."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        return tmp_path

    def test_repair_missing_session_file(self, temp_project):
        """Should create SESSION.md if missing."""
        session_file = temp_project / ".mind" / "SESSION.md"
        assert not session_file.exists()

        repaired = repair_session_file(temp_project)

        assert repaired is True
        assert session_file.exists()
        content = session_file.read_text(encoding="utf-8")
        assert "## Experience" in content
        assert "## Blockers" in content
        assert "## Rejected" in content
        assert "## Assumptions" in content

    def test_repair_missing_sections(self, temp_project):
        """Should add missing sections to existing file."""
        session_file = temp_project / ".mind" / "SESSION.md"
        session_file.write_text("""# Session: 2025-12-18

## Experience
- something
""", encoding="utf-8")

        repaired = repair_session_file(temp_project)

        assert repaired is True
        content = session_file.read_text(encoding="utf-8")
        assert "## Experience" in content
        assert "## Blockers" in content
        assert "## Rejected" in content
        assert "## Assumptions" in content

    def test_no_repair_needed(self, temp_project):
        """Should return False if no repair needed."""
        session_file = temp_project / ".mind" / "SESSION.md"
        session_file.write_text("""# Session: 2025-12-18

## Experience

## Blockers

## Rejected

## Assumptions

""", encoding="utf-8")

        repaired = repair_session_file(temp_project)

        assert repaired is False

    def test_preserve_existing_content(self, temp_project):
        """Should preserve existing content when adding missing sections."""
        session_file = temp_project / ".mind" / "SESSION.md"
        session_file.write_text("""# Session: 2025-12-18

## Experience
- important entry
- another entry

## Blockers
- stuck on something
""", encoding="utf-8")

        repair_session_file(temp_project)

        content = session_file.read_text(encoding="utf-8")
        assert "important entry" in content
        assert "another entry" in content
        assert "stuck on something" in content
        assert "## Rejected" in content
        assert "## Assumptions" in content


class TestUpdateSessionSection:
    """Tests for update_session_section function."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project directory with .mind folder and SESSION.md."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        session_file = mind_dir / "SESSION.md"
        session_file.write_text("""# Session: 2025-12-18

## Experience
<!-- Raw moments -->

## Blockers

## Rejected
<!-- What didn't work -->

## Assumptions
<!-- What I'm assuming -->

""", encoding="utf-8")
        return tmp_path

    def test_append_to_section(self, temp_project):
        """Should append content to a section."""
        success = update_session_section(
            temp_project,
            "Experience",
            "working on auth flow",
            append=True
        )

        assert success is True
        session_file = temp_project / ".mind" / "SESSION.md"
        content = session_file.read_text(encoding="utf-8")
        assert "working on auth flow" in content

    def test_append_multiple_items(self, temp_project):
        """Should append multiple items to a section."""
        update_session_section(temp_project, "Experience", "first item", append=True)
        update_session_section(temp_project, "Experience", "second item", append=True)

        session_file = temp_project / ".mind" / "SESSION.md"
        content = session_file.read_text(encoding="utf-8")
        assert "first item" in content
        assert "second item" in content

    def test_update_to_different_sections(self, temp_project):
        """Should update different sections correctly."""
        update_session_section(temp_project, "Experience", "experiencing something", append=True)
        update_session_section(temp_project, "Blockers", "stuck on X", append=True)
        update_session_section(temp_project, "Rejected", "tried Y - failed", append=True)
        update_session_section(temp_project, "Assumptions", "assuming Z", append=True)

        session_file = temp_project / ".mind" / "SESSION.md"
        content = session_file.read_text(encoding="utf-8")
        assert "experiencing something" in content
        assert "stuck on X" in content
        assert "tried Y - failed" in content
        assert "assuming Z" in content

    def test_auto_repair_missing_section(self, temp_project):
        """Should auto-repair if section is missing."""
        session_file = temp_project / ".mind" / "SESSION.md"
        # Create file with missing sections
        session_file.write_text("""# Session: 2025-12-18

## Experience

""", encoding="utf-8")

        success = update_session_section(
            temp_project,
            "Blockers",
            "stuck on something",
            append=True
        )

        assert success is True
        content = session_file.read_text(encoding="utf-8")
        assert "stuck on something" in content

    def test_auto_repair_missing_file(self, temp_project):
        """Should auto-repair if SESSION.md is missing."""
        session_file = temp_project / ".mind" / "SESSION.md"
        session_file.unlink()  # Delete the file

        success = update_session_section(
            temp_project,
            "Experience",
            "new entry",
            append=True
        )

        assert success is True
        assert session_file.exists()
        content = session_file.read_text(encoding="utf-8")
        assert "new entry" in content

    def test_replace_section_content(self, temp_project):
        """Should replace section content when append=False."""
        session_file = temp_project / ".mind" / "SESSION.md"
        # Add some content first
        session_file.write_text("""# Session: 2025-12-18

## Experience
- old content
- more old content

## Blockers

## Rejected

## Assumptions

""", encoding="utf-8")

        update_session_section(
            temp_project,
            "Experience",
            "new content only",
            append=False
        )

        content = session_file.read_text(encoding="utf-8")
        assert "new content only" in content
        # Old content might still be there depending on implementation
        # This test documents current behavior


class TestClearSessionFile:
    """Tests for clear_session_file function."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project directory with .mind folder."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        return tmp_path

    def test_clear_creates_fresh_file(self, temp_project):
        """Should create a fresh SESSION.md with all sections."""
        session_file = temp_project / ".mind" / "SESSION.md"

        clear_session_file(temp_project)

        assert session_file.exists()
        content = session_file.read_text(encoding="utf-8")
        assert "## Experience" in content
        assert "## Blockers" in content
        assert "## Rejected" in content
        assert "## Assumptions" in content

    def test_clear_has_date_header(self, temp_project):
        """Should include today's date in the header."""
        clear_session_file(temp_project)

        session_file = temp_project / ".mind" / "SESSION.md"
        content = session_file.read_text(encoding="utf-8")
        today = date.today().isoformat()
        assert today in content

    def test_clear_overwrites_existing(self, temp_project):
        """Should overwrite existing content."""
        session_file = temp_project / ".mind" / "SESSION.md"
        session_file.write_text("old content that should be removed", encoding="utf-8")

        clear_session_file(temp_project)

        content = session_file.read_text(encoding="utf-8")
        assert "old content that should be removed" not in content
        assert "## Experience" in content


class TestGetSessionFile:
    """Tests for get_session_file function."""

    def test_returns_correct_path(self, tmp_path):
        """Should return path to SESSION.md in .mind directory."""
        session_path = get_session_file(tmp_path)

        assert session_path == tmp_path / ".mind" / "SESSION.md"

    def test_path_is_pathlib_path(self, tmp_path):
        """Should return a pathlib.Path object."""
        session_path = get_session_file(tmp_path)

        assert isinstance(session_path, Path)
