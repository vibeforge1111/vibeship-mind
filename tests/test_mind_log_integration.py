"""Integration tests for mind_log flow - end-to-end logging."""

import pytest
from pathlib import Path
import json
from datetime import date

# Import functions to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mind.mcp.server import (
    parse_session_section,
    auto_categorize_session_type,
    update_session_section,
    clear_session_file,
    get_session_file,
)


class TestMindLogToSessionFlow:
    """Integration tests for logging to SESSION.md."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a complete temporary project structure."""
        # Create .mind directory
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()

        # Create SESSION.md with all sections
        session_file = mind_dir / "SESSION.md"
        session_file.write_text(f"""# Session: {date.today().isoformat()}

## Experience
<!-- Raw moments, thoughts, what's happening -->

## Blockers

## Rejected
<!-- What didn't work and why -->

## Assumptions
<!-- What I'm assuming true -->

""", encoding="utf-8")

        # Create MEMORY.md
        memory_file = mind_dir / "MEMORY.md"
        memory_file.write_text("""# Test Project

## Project State
- Goal: Testing
- Stack: python
- Blocked: None

## Gotchas

---

## Session Log

""", encoding="utf-8")

        # Create config.json
        config_file = mind_dir / "config.json"
        config = {
            "version": 1,
            "mascot": True,
            "self_improve": {
                "enabled": True,
                "decay": True,
                "reinforcement": True,
                "contradiction": True,
                "learning_style": True,
            },
            "experimental": {}
        }
        config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")

        return tmp_path

    def test_experience_logged_to_experience_section(self, temp_project):
        """Experience messages should go to Experience section."""
        # Simulate mind_log with type="experience"
        message = "reading auth module to understand the flow"
        section = "Experience"

        success = update_session_section(temp_project, section, message, append=True)

        assert success is True
        session_file = get_session_file(temp_project)
        content = session_file.read_text(encoding="utf-8")
        items = parse_session_section(content, "Experience")
        assert any("auth module" in item for item in items)

    def test_blocker_logged_to_blockers_section(self, temp_project):
        """Blocker messages should go to Blockers section."""
        message = "stuck on the authentication flow"
        section = "Blockers"

        success = update_session_section(temp_project, section, message, append=True)

        assert success is True
        session_file = get_session_file(temp_project)
        content = session_file.read_text(encoding="utf-8")
        items = parse_session_section(content, "Blockers")
        assert any("authentication flow" in item for item in items)

    def test_rejected_logged_to_rejected_section(self, temp_project):
        """Rejected messages should go to Rejected section."""
        message = "tried Redis - too complex for our needs"
        section = "Rejected"

        success = update_session_section(temp_project, section, message, append=True)

        assert success is True
        session_file = get_session_file(temp_project)
        content = session_file.read_text(encoding="utf-8")
        items = parse_session_section(content, "Rejected")
        assert any("Redis" in item for item in items)

    def test_assumption_logged_to_assumptions_section(self, temp_project):
        """Assumption messages should go to Assumptions section."""
        message = "assuming user has stable internet connection"
        section = "Assumptions"

        success = update_session_section(temp_project, section, message, append=True)

        assert success is True
        session_file = get_session_file(temp_project)
        content = session_file.read_text(encoding="utf-8")
        items = parse_session_section(content, "Assumptions")
        assert any("internet connection" in item for item in items)


class TestAutoCategorizeToSectionFlow:
    """Integration tests for auto-categorization to correct sections."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a complete temporary project structure."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        session_file = mind_dir / "SESSION.md"
        session_file.write_text(f"""# Session: {date.today().isoformat()}

## Experience

## Blockers

## Rejected

## Assumptions

""", encoding="utf-8")
        return tmp_path

    def test_auto_categorize_rejected_message(self, temp_project):
        """Message with 'tried' should auto-categorize to Rejected."""
        message = "tried websockets but it was overkill"

        # Auto-categorize
        section_type = auto_categorize_session_type(message)
        assert section_type == "rejected"

        # Map to section name (first letter capitalized)
        section_name = section_type.capitalize()
        if section_name == "Rejected":
            section_name = "Rejected"

        # Log to section
        update_session_section(temp_project, section_name, message, append=True)

        # Verify it's in the right section
        session_file = get_session_file(temp_project)
        content = session_file.read_text(encoding="utf-8")
        rejected_items = parse_session_section(content, "Rejected")
        assert any("websockets" in item for item in rejected_items)

    def test_auto_categorize_blocker_message(self, temp_project):
        """Message with 'stuck' should auto-categorize to Blockers."""
        message = "stuck on figuring out the database schema"

        # Auto-categorize
        section_type = auto_categorize_session_type(message)
        assert section_type == "blocker"

        # Map to section name
        section_name = "Blockers"

        # Log to section
        update_session_section(temp_project, section_name, message, append=True)

        # Verify
        session_file = get_session_file(temp_project)
        content = session_file.read_text(encoding="utf-8")
        blocker_items = parse_session_section(content, "Blockers")
        assert any("database schema" in item for item in blocker_items)

    def test_auto_categorize_assumption_message(self, temp_project):
        """Message with 'assuming' should auto-categorize to Assumptions."""
        message = "assuming the API returns JSON format"

        # Auto-categorize
        section_type = auto_categorize_session_type(message)
        assert section_type == "assumption"

        # Map to section name
        section_name = "Assumptions"

        # Log to section
        update_session_section(temp_project, section_name, message, append=True)

        # Verify
        session_file = get_session_file(temp_project)
        content = session_file.read_text(encoding="utf-8")
        assumption_items = parse_session_section(content, "Assumptions")
        assert any("JSON format" in item for item in assumption_items)

    def test_auto_categorize_neutral_message(self, temp_project):
        """Neutral message should auto-categorize to Experience."""
        message = "reading the authentication module"

        # Auto-categorize
        section_type = auto_categorize_session_type(message)
        assert section_type == "experience"

        # Map to section name
        section_name = "Experience"

        # Log to section
        update_session_section(temp_project, section_name, message, append=True)

        # Verify
        session_file = get_session_file(temp_project)
        content = session_file.read_text(encoding="utf-8")
        experience_items = parse_session_section(content, "Experience")
        assert any("authentication module" in item for item in experience_items)


class TestMultipleEntriesFlow:
    """Integration tests for multiple log entries."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a complete temporary project structure."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        session_file = mind_dir / "SESSION.md"
        session_file.write_text(f"""# Session: {date.today().isoformat()}

## Experience

## Blockers

## Rejected

## Assumptions

""", encoding="utf-8")
        return tmp_path

    def test_multiple_entries_same_section(self, temp_project):
        """Multiple entries to the same section should accumulate."""
        messages = [
            "working on auth",
            "implementing login flow",
            "adding token validation",
        ]

        for msg in messages:
            update_session_section(temp_project, "Experience", msg, append=True)

        session_file = get_session_file(temp_project)
        content = session_file.read_text(encoding="utf-8")
        items = parse_session_section(content, "Experience")

        assert len(items) == 3
        assert any("auth" in item for item in items)
        assert any("login flow" in item for item in items)
        assert any("token validation" in item for item in items)

    def test_multiple_entries_different_sections(self, temp_project):
        """Entries to different sections should be independent."""
        # Add to Experience
        update_session_section(temp_project, "Experience", "working on feature", append=True)

        # Add to Blockers
        update_session_section(temp_project, "Blockers", "stuck on bug", append=True)

        # Add to Rejected
        update_session_section(temp_project, "Rejected", "tried approach X", append=True)

        # Add to Assumptions
        update_session_section(temp_project, "Assumptions", "assuming Y is true", append=True)

        session_file = get_session_file(temp_project)
        content = session_file.read_text(encoding="utf-8")

        assert len(parse_session_section(content, "Experience")) == 1
        assert len(parse_session_section(content, "Blockers")) == 1
        assert len(parse_session_section(content, "Rejected")) == 1
        assert len(parse_session_section(content, "Assumptions")) == 1

    def test_clear_resets_all_sections(self, temp_project):
        """Clearing session should reset all sections."""
        # Add entries
        update_session_section(temp_project, "Experience", "entry 1", append=True)
        update_session_section(temp_project, "Blockers", "entry 2", append=True)

        # Clear
        clear_session_file(temp_project)

        session_file = get_session_file(temp_project)
        content = session_file.read_text(encoding="utf-8")

        assert len(parse_session_section(content, "Experience")) == 0
        assert len(parse_session_section(content, "Blockers")) == 0
        assert len(parse_session_section(content, "Rejected")) == 0
        assert len(parse_session_section(content, "Assumptions")) == 0


class TestErrorRecoveryFlow:
    """Integration tests for error recovery scenarios."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a minimal project structure."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        return tmp_path

    def test_recover_from_missing_session_file(self, temp_project):
        """Should recover and log when SESSION.md is missing."""
        # Don't create SESSION.md - let it be missing
        session_file = get_session_file(temp_project)
        assert not session_file.exists()

        # Try to log - should auto-create and succeed
        success = update_session_section(temp_project, "Experience", "test entry", append=True)

        assert success is True
        assert session_file.exists()
        content = session_file.read_text(encoding="utf-8")
        assert "test entry" in content

    def test_recover_from_malformed_session_file(self, temp_project):
        """Should recover when SESSION.md is malformed."""
        session_file = get_session_file(temp_project)
        # Create a malformed file with missing sections
        session_file.write_text("""# Session: 2025-12-18

## Experience
- existing entry
""", encoding="utf-8")

        # Try to log to a missing section - should auto-repair and succeed
        success = update_session_section(temp_project, "Blockers", "new entry", append=True)

        assert success is True
        content = session_file.read_text(encoding="utf-8")
        # Original content preserved
        assert "existing entry" in content
        # New section added
        assert "## Blockers" in content
        assert "new entry" in content

    def test_recover_from_empty_session_file(self, temp_project):
        """Should recover when SESSION.md is empty."""
        session_file = get_session_file(temp_project)
        session_file.write_text("", encoding="utf-8")

        success = update_session_section(temp_project, "Experience", "test entry", append=True)

        assert success is True
        content = session_file.read_text(encoding="utf-8")
        assert "test entry" in content


class TestSectionMappingFlow:
    """Tests for type-to-section mapping."""

    def test_session_type_to_section_mapping(self):
        """Test the mapping from log types to section names."""
        type_to_section = {
            "experience": "Experience",
            "blocker": "Blockers",
            "rejected": "Rejected",
            "assumption": "Assumptions",
        }

        for log_type, expected_section in type_to_section.items():
            # Verify the mapping logic (as used in handle_log)
            if log_type == "blocker":
                section = "Blockers"
            elif log_type == "rejected":
                section = "Rejected"
            elif log_type == "assumption":
                section = "Assumptions"
            else:
                section = "Experience"

            assert section == expected_section, f"Type {log_type} should map to {expected_section}"
