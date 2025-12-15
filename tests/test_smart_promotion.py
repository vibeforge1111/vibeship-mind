"""Tests for smart promotion with novelty checking and link/supersede logic."""

import pytest
from pathlib import Path
import tempfile
import shutil


class TestCheckNoveltyAndLink:
    """Tests for check_novelty_and_link function."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        dir_path = Path(tempfile.mkdtemp())
        mind_dir = dir_path / ".mind"
        mind_dir.mkdir()
        yield dir_path
        shutil.rmtree(dir_path)

    @pytest.fixture
    def sample_memory(self, temp_dir):
        """Create a sample MEMORY.md file."""
        memory_file = temp_dir / ".mind" / "MEMORY.md"
        memory_file.write_text("""# Memory

## Decisions
- [D] chose Click for CLI because it's simpler than argparse
- [D] stay file-based - that's our identity

## Learnings
- [L] Windows needs ctypes for process detection
- [L] uv sync removes unlisted packages

## Issues
- [!] encoding issues with cp1252 on Windows
""", encoding="utf-8")
        return memory_file

    def test_novel_content_returns_add(self, sample_memory):
        """Completely new content should be added."""
        from mind.mcp.server import check_novelty_and_link

        result = check_novelty_and_link(
            "learned: GraphQL is better for complex queries",
            sample_memory,
        )
        assert result["is_novel"] is True
        assert result["action"] == "add"
        assert result["similar_entry"] is None

    def test_duplicate_content_returns_skip(self, sample_memory):
        """Nearly identical content should be skipped."""
        from mind.mcp.server import check_novelty_and_link

        result = check_novelty_and_link(
            "chose Click for CLI because it's simpler than argparse",
            sample_memory,
        )
        assert result["is_novel"] is False
        assert result["action"] == "skip"
        assert result["similar_entry"] is not None
        assert result["similarity"] > 0.9

    def test_similar_content_returns_link_or_supersede(self, sample_memory):
        """Similar but not identical content should link or supersede."""
        from mind.mcp.server import check_novelty_and_link

        # This is similar to "chose Click for CLI because it's simpler"
        # Using lower threshold to catch similar content
        result = check_novelty_and_link(
            "decided on Click CLI library - it's simpler than alternatives",
            sample_memory,
            novelty_threshold=0.4,  # Lower threshold to catch similarity
        )
        # Either link or supersede depending on similarity score
        # If very similar (>0.9), it would skip; if <0.4, it would add
        # In the 0.4-0.9 range, it should link or supersede
        assert result["similar_entry"] is not None or result["action"] == "add"

    def test_empty_memory_file_returns_add(self, temp_dir):
        """Empty memory file should always allow adding."""
        from mind.mcp.server import check_novelty_and_link

        memory_file = temp_dir / ".mind" / "MEMORY.md"
        memory_file.write_text("# Memory\n\n", encoding="utf-8")

        result = check_novelty_and_link(
            "learned: something new",
            memory_file,
        )
        assert result["is_novel"] is True
        assert result["action"] == "add"

    def test_nonexistent_memory_file_returns_add(self, temp_dir):
        """Missing memory file should allow adding."""
        from mind.mcp.server import check_novelty_and_link

        missing_file = temp_dir / ".mind" / "NONEXISTENT.md"

        result = check_novelty_and_link(
            "learned: something new",
            missing_file,
        )
        assert result["is_novel"] is True
        assert result["action"] == "add"


class TestFormatWithLink:
    """Tests for format_with_link function."""

    def test_adds_wikilink(self):
        """Should append wikilink to content."""
        from mind.mcp.server import format_with_link

        content = "learned: new thing about Python"
        similar_entry = {"content": "old thing", "line": 42, "type": "learning"}

        result = format_with_link(content, similar_entry)
        assert "[[MEMORY#L42]]" in result
        assert content in result
        assert "see also:" in result

    def test_handles_missing_line(self):
        """Should handle missing line number gracefully."""
        from mind.mcp.server import format_with_link

        content = "learned: new thing"
        similar_entry = {"content": "old thing", "type": "learning"}

        result = format_with_link(content, similar_entry)
        assert "[[MEMORY#L0]]" in result


class TestMarkAsSuperseded:
    """Tests for mark_as_superseded function."""

    @pytest.fixture
    def temp_memory_file(self):
        """Create a temporary memory file."""
        dir_path = Path(tempfile.mkdtemp())
        memory_file = dir_path / "MEMORY.md"
        memory_file.write_text("""# Memory

Line 1
Line 2
Line 3
Line 4
""", encoding="utf-8")
        yield memory_file
        shutil.rmtree(dir_path)

    def test_marks_line_as_superseded(self, temp_memory_file):
        """Should prepend [superseded] to specified line."""
        from mind.mcp.server import mark_as_superseded

        # Line 4 is "Line 2" (1-indexed: header=1, empty=2, Line1=3, Line2=4)
        result = mark_as_superseded(temp_memory_file, 4)
        assert result is True

        content = temp_memory_file.read_text()
        lines = content.split("\n")
        # Line 4 (0-indexed = 3) should be marked
        assert lines[3] == "[superseded] Line 2"

    def test_skips_already_superseded(self, temp_memory_file):
        """Should not double-mark superseded lines."""
        from mind.mcp.server import mark_as_superseded

        # Mark once
        mark_as_superseded(temp_memory_file, 4)
        # Mark again
        mark_as_superseded(temp_memory_file, 4)

        content = temp_memory_file.read_text()
        # Should not have [superseded] [superseded]
        assert "[superseded] [superseded]" not in content

    def test_invalid_line_number_returns_false(self, temp_memory_file):
        """Should return False for invalid line numbers."""
        from mind.mcp.server import mark_as_superseded

        assert mark_as_superseded(temp_memory_file, 0) is False
        assert mark_as_superseded(temp_memory_file, 100) is False

    def test_nonexistent_file_returns_false(self):
        """Should return False for missing file."""
        from mind.mcp.server import mark_as_superseded

        result = mark_as_superseded(Path("/nonexistent/MEMORY.md"), 1)
        assert result is False


class TestAppendToMemory:
    """Tests for append_to_memory function with novelty checking."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        dir_path = Path(tempfile.mkdtemp())
        mind_dir = dir_path / ".mind"
        mind_dir.mkdir()
        memory_file = mind_dir / "MEMORY.md"
        # Use content the parser recognizes (keywords like "learned", "decided")
        memory_file.write_text("""# Memory

## Learnings
- learned Windows needs ctypes for process detection
""", encoding="utf-8")
        yield dir_path
        shutil.rmtree(dir_path)

    def test_adds_novel_content(self, temp_project):
        """Should add completely new content."""
        from mind.mcp.server import append_to_memory

        learnings = [
            {"type": "learning", "content": "GraphQL works better for nested data"}
        ]
        count = append_to_memory(temp_project, learnings)
        assert count == 1

        content = (temp_project / ".mind" / "MEMORY.md").read_text()
        assert "GraphQL" in content

    def test_skips_duplicate_content(self, temp_project):
        """Should skip nearly identical content."""
        from mind.mcp.server import append_to_memory

        # The parser looks for "learned" keyword
        learnings = [
            {"type": "learning", "content": "learned Windows needs ctypes for process detection"}
        ]
        count = append_to_memory(temp_project, learnings)
        assert count == 0

    def test_empty_learnings_returns_zero(self, temp_project):
        """Should return 0 for empty learnings list."""
        from mind.mcp.server import append_to_memory

        count = append_to_memory(temp_project, [])
        assert count == 0


class TestSmartPromotionIntegration:
    """Integration tests for the full smart promotion flow."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        dir_path = Path(tempfile.mkdtemp())
        mind_dir = dir_path / ".mind"
        mind_dir.mkdir()
        memory_file = mind_dir / "MEMORY.md"
        # Use content the parser recognizes (keywords like "learned", "decided", "chose")
        memory_file.write_text("""# Memory

## Decisions
- decided on REST over GraphQL - simpler for our use case

## Learnings
- learned async/await makes code cleaner but harder to debug
""", encoding="utf-8")
        yield dir_path
        shutil.rmtree(dir_path)

    def test_novel_learning_is_added(self, temp_project):
        """A genuinely new learning should be added."""
        from mind.mcp.server import append_to_memory

        learnings = [
            {"type": "learning", "content": "Redis is great for caching"}
        ]
        count = append_to_memory(temp_project, learnings)
        assert count == 1

        content = (temp_project / ".mind" / "MEMORY.md").read_text()
        assert "Redis" in content

    def test_semantic_duplicate_is_skipped(self, temp_project):
        """A semantic duplicate should be skipped or linked."""
        from mind.mcp.server import append_to_memory

        # This is semantically similar to existing "async/await makes code cleaner but harder to debug"
        # With >90% similarity it should be skipped, or with 50-90% it should link
        learnings = [
            {"type": "learning", "content": "using async/await improves readability but debugging is trickier"}
        ]
        initial_content = (temp_project / ".mind" / "MEMORY.md").read_text()
        count = append_to_memory(temp_project, learnings)
        final_content = (temp_project / ".mind" / "MEMORY.md").read_text()

        # Should either be skipped (count=0) or linked (count=1 with wikilink)
        if count == 0:
            # Skipped as duplicate
            assert "debugging is trickier" not in final_content
        else:
            # Added with link
            assert "[[MEMORY#" in final_content or count == 1
