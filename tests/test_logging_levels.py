"""Unit tests for logging_levels.py - Efficient/Balanced/Detailed modes."""

import pytest
from pathlib import Path

# Import functions to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mind.logging_levels import (
    get_logging_level,
    should_log_message,
    get_level_description,
    _has_insight_markers,
    _is_obvious_assumption,
)


class TestGetLoggingLevel:
    """Tests for get_logging_level function."""

    def test_returns_balanced_when_no_config(self, tmp_path):
        """Should return balanced as default when no config exists."""
        (tmp_path / ".mind").mkdir()

        result = get_logging_level(tmp_path)

        assert result == "balanced"

    def test_returns_configured_level(self, tmp_path):
        """Should return configured logging level."""
        import json
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        config = {"version": 2, "logging": {"level": "efficient"}}
        (mind_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")

        result = get_logging_level(tmp_path)

        assert result == "efficient"

    def test_returns_balanced_for_invalid_config(self, tmp_path):
        """Should return balanced when config is invalid."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        (mind_dir / "config.json").write_text("invalid json", encoding="utf-8")

        result = get_logging_level(tmp_path)

        assert result == "balanced"


class TestShouldLogMessage:
    """Tests for should_log_message function."""

    # Always-log types tests
    def test_always_logs_decision(self):
        """Decision type should always be logged."""
        should_log, reason = should_log_message("chose X", "decision", "efficient")
        assert should_log is True
        assert reason is None

    def test_always_logs_problem(self):
        """Problem type should always be logged."""
        should_log, reason = should_log_message("bug found", "problem", "efficient")
        assert should_log is True

    def test_always_logs_blocker(self):
        """Blocker type should always be logged."""
        should_log, reason = should_log_message("stuck on X", "blocker", "efficient")
        assert should_log is True

    def test_always_logs_learning(self):
        """Learning type should always be logged."""
        should_log, reason = should_log_message("discovered X", "learning", "efficient")
        assert should_log is True

    def test_always_logs_progress(self):
        """Progress type should always be logged."""
        should_log, reason = should_log_message("fixed Y", "progress", "efficient")
        assert should_log is True

    def test_always_logs_rejected(self):
        """Rejected type should always be logged."""
        should_log, reason = should_log_message("tried X", "rejected", "efficient")
        assert should_log is True

    # Efficient mode tests
    def test_efficient_skips_routine_experience(self):
        """Efficient mode should skip routine experiences."""
        should_log, reason = should_log_message("working on stuff", "experience", "efficient")
        assert should_log is False
        assert "efficient" in reason.lower()

    def test_efficient_logs_experience_with_insight(self):
        """Efficient mode should log experiences with insight markers."""
        should_log, reason = should_log_message(
            "found that `/src/config.ts` has the issue", "experience", "efficient"
        )
        assert should_log is True

    def test_efficient_skips_obvious_assumption(self):
        """Efficient mode should skip obvious assumptions."""
        should_log, reason = should_log_message(
            "assuming it works", "assumption", "efficient"
        )
        assert should_log is False

    def test_efficient_logs_detailed_assumption(self):
        """Efficient mode should log detailed assumptions."""
        should_log, reason = should_log_message(
            "assuming the user's auth token is stored in localStorage because that's the pattern in `auth.ts`",
            "assumption", "efficient"
        )
        assert should_log is True

    # Balanced mode tests
    def test_balanced_logs_most_experiences(self):
        """Balanced mode should log most experiences."""
        should_log, reason = should_log_message(
            "reading through the authentication module", "experience", "balanced"
        )
        assert should_log is True

    def test_balanced_skips_very_short_experience(self):
        """Balanced mode should skip very short experiences without insight."""
        should_log, reason = should_log_message("ok", "experience", "balanced")
        assert should_log is False
        assert "balanced" in reason.lower()

    def test_balanced_logs_short_experience_with_insight(self):
        """Balanced mode should log short experiences with insight markers."""
        should_log, reason = should_log_message(
            "found v2.1 issue", "experience", "balanced"
        )
        assert should_log is True

    def test_balanced_logs_assumptions(self):
        """Balanced mode should log assumptions."""
        should_log, reason = should_log_message(
            "assuming it works", "assumption", "balanced"
        )
        assert should_log is True

    # Detailed mode tests
    def test_detailed_logs_everything(self):
        """Detailed mode should log everything."""
        should_log, reason = should_log_message("x", "experience", "detailed")
        assert should_log is True
        assert reason is None

    def test_detailed_logs_short_experiences(self):
        """Detailed mode should log even short experiences."""
        should_log, reason = should_log_message("ok", "experience", "detailed")
        assert should_log is True

    def test_detailed_logs_obvious_assumptions(self):
        """Detailed mode should log obvious assumptions."""
        should_log, reason = should_log_message(
            "assuming it works", "assumption", "detailed"
        )
        assert should_log is True


class TestHasInsightMarkers:
    """Tests for _has_insight_markers function."""

    def test_detects_found(self):
        """Should detect 'found' as insight marker."""
        assert _has_insight_markers("found the bug in config") is True

    def test_detects_discovered(self):
        """Should detect 'discovered' as insight marker."""
        assert _has_insight_markers("discovered that X") is True

    def test_detects_because(self):
        """Should detect 'because' as insight marker."""
        assert _has_insight_markers("failed because of Y") is True

    def test_detects_workaround(self):
        """Should detect 'workaround' as insight marker."""
        assert _has_insight_markers("using workaround for now") is True

    def test_detects_file_path(self):
        """Should detect file paths as insight marker."""
        assert _has_insight_markers("issue in /src/auth.ts") is True
        assert _has_insight_markers("check C:\\Users\\file.js") is True

    def test_detects_backtick_code(self):
        """Should detect code in backticks as insight marker."""
        assert _has_insight_markers("the `handleAuth` function") is True

    def test_detects_version_numbers(self):
        """Should detect version numbers as insight marker."""
        assert _has_insight_markers("works in v2.1 but not v2.0") is True

    def test_detects_config_mention(self):
        """Should detect config mention as insight marker."""
        assert _has_insight_markers("changed the config setting") is True

    def test_detects_decision_indicators(self):
        """Should detect decision indicators as insight marker."""
        assert _has_insight_markers("chose X instead of Y") is True
        assert _has_insight_markers("decided to use Z") is True

    def test_no_insight_in_routine(self):
        """Should not detect insight in routine messages."""
        assert _has_insight_markers("working on stuff") is False
        assert _has_insight_markers("looking at code") is False


class TestIsObviousAssumption:
    """Tests for _is_obvious_assumption function."""

    def test_detects_simple_assuming_it_works(self):
        """Should detect 'assuming it works' as obvious."""
        assert _is_obvious_assumption("assuming it works") is True

    def test_detects_assuming_api_is(self):
        """Should detect 'assuming the api is...' as obvious."""
        assert _is_obvious_assumption("assuming api is up") is True

    def test_detects_assuming_user_has(self):
        """Should detect 'assuming user has...' as obvious."""
        assert _is_obvious_assumption("assuming user has access") is True

    def test_not_obvious_when_detailed(self):
        """Should not consider detailed assumptions as obvious."""
        assert _is_obvious_assumption(
            "assuming the auth token format is JWT based on the decode function signature"
        ) is False

    def test_not_obvious_when_long(self):
        """Should not consider long assumptions as obvious."""
        assert _is_obvious_assumption(
            "assuming this is correct based on documentation"
        ) is False


class TestGetLevelDescription:
    """Tests for get_level_description function."""

    def test_efficient_description(self):
        """Should return efficient description."""
        desc = get_level_description("efficient")
        assert "critical" in desc.lower() or "decision" in desc.lower()

    def test_balanced_description(self):
        """Should return balanced description."""
        desc = get_level_description("balanced")
        assert "key" in desc.lower() or "recommended" in desc.lower()

    def test_detailed_description(self):
        """Should return detailed description."""
        desc = get_level_description("detailed")
        assert "everything" in desc.lower() or "compact" in desc.lower()

    def test_unknown_returns_unknown(self):
        """Should return 'Unknown' for unknown levels."""
        desc = get_level_description("invalid")
        assert desc == "Unknown"
