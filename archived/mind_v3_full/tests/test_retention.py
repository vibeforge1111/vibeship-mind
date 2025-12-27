"""Unit tests for retention.py - usage-based retention and decay."""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta

# Import functions to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mind.retention import (
    get_retention_mode,
    get_decay_settings,
    get_relevance_file,
    load_relevance_data,
    save_relevance_data,
    get_memory_id,
    track_memory_access,
    reinforce_memory,
    decay_memories,
    get_memory_relevance,
    filter_by_relevance,
    prioritize_by_relevance,
    get_relevance_tier,
    get_retention_stats,
)


@pytest.fixture
def project_with_mind(tmp_path):
    """Create project with .mind directory."""
    (tmp_path / ".mind").mkdir()
    return tmp_path


class TestGetRetentionMode:
    """Tests for get_retention_mode function."""

    def test_returns_smart_by_default(self, project_with_mind):
        """Should return smart as default."""
        result = get_retention_mode(project_with_mind)
        assert result == "smart"

    def test_returns_configured_mode(self, project_with_mind):
        """Should return configured retention mode."""
        config = {"version": 2, "memory": {"retention_mode": "keep_all"}}
        (project_with_mind / ".mind" / "config.json").write_text(
            json.dumps(config), encoding="utf-8"
        )

        result = get_retention_mode(project_with_mind)
        assert result == "keep_all"


class TestGetDecaySettings:
    """Tests for get_decay_settings function."""

    def test_returns_defaults_when_no_config(self, project_with_mind):
        """Should return default decay settings."""
        result = get_decay_settings(project_with_mind)

        assert result["decay_period_days"] == 30
        assert result["decay_rate"] == 0.1
        assert result["min_relevance"] == 0.2

    def test_returns_configured_settings(self, project_with_mind):
        """Should return configured decay settings."""
        config = {
            "version": 2,
            "memory": {
                "decay_period_days": 14,
                "decay_rate": 0.2,
                "min_relevance": 0.1,
            }
        }
        (project_with_mind / ".mind" / "config.json").write_text(
            json.dumps(config), encoding="utf-8"
        )

        result = get_decay_settings(project_with_mind)

        assert result["decay_period_days"] == 14
        assert result["decay_rate"] == 0.2
        assert result["min_relevance"] == 0.1


class TestGetRelevanceFile:
    """Tests for get_relevance_file function."""

    def test_returns_correct_path(self, tmp_path):
        """Should return .mind/relevance.json path."""
        result = get_relevance_file(tmp_path)
        assert result == tmp_path / ".mind" / "relevance.json"


class TestLoadRelevanceData:
    """Tests for load_relevance_data function."""

    def test_returns_empty_when_no_file(self, project_with_mind):
        """Should return empty data when file doesn't exist."""
        result = load_relevance_data(project_with_mind)

        assert result["version"] == 1
        assert result["entries"] == {}

    def test_loads_existing_data(self, project_with_mind):
        """Should load existing relevance data."""
        data = {
            "version": 1,
            "entries": {
                "abc123": {"score": 0.8, "last_accessed": "2025-01-01T00:00:00"}
            }
        }
        (project_with_mind / ".mind" / "relevance.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

        result = load_relevance_data(project_with_mind)

        assert result["entries"]["abc123"]["score"] == 0.8

    def test_returns_empty_for_invalid_json(self, project_with_mind):
        """Should return empty data for invalid JSON."""
        (project_with_mind / ".mind" / "relevance.json").write_text(
            "not json", encoding="utf-8"
        )

        result = load_relevance_data(project_with_mind)

        assert result["entries"] == {}


class TestSaveRelevanceData:
    """Tests for save_relevance_data function."""

    def test_saves_data_successfully(self, project_with_mind):
        """Should save relevance data."""
        data = {
            "version": 1,
            "entries": {"test": {"score": 0.5}}
        }

        result = save_relevance_data(project_with_mind, data)

        assert result is True
        saved = json.loads(
            (project_with_mind / ".mind" / "relevance.json").read_text(encoding="utf-8")
        )
        assert saved["entries"]["test"]["score"] == 0.5


class TestGetMemoryId:
    """Tests for get_memory_id function."""

    def test_returns_stable_id(self):
        """Should return same ID for same content."""
        id1 = get_memory_id("test content")
        id2 = get_memory_id("test content")
        assert id1 == id2

    def test_normalizes_whitespace(self):
        """Should normalize leading/trailing whitespace."""
        id1 = get_memory_id("test content")
        id2 = get_memory_id("  test content  ")
        assert id1 == id2

    def test_case_insensitive(self):
        """Should be case insensitive."""
        id1 = get_memory_id("Test Content")
        id2 = get_memory_id("test content")
        assert id1 == id2

    def test_different_content_different_id(self):
        """Should return different IDs for different content."""
        id1 = get_memory_id("content a")
        id2 = get_memory_id("content b")
        assert id1 != id2


class TestTrackMemoryAccess:
    """Tests for track_memory_access function."""

    def test_creates_new_entry(self, project_with_mind):
        """Should create new entry for untracked memory."""
        result = track_memory_access(project_with_mind, "new memory")

        assert result["score"] == 1.0
        assert result["access_count"] == 1
        assert "last_accessed" in result

    def test_increments_access_count(self, project_with_mind):
        """Should increment access count on subsequent access."""
        track_memory_access(project_with_mind, "memory")
        result = track_memory_access(project_with_mind, "memory")

        assert result["access_count"] == 2

    def test_boosts_score_on_access(self, project_with_mind):
        """Should boost score on access."""
        # Set initial low score
        data = {
            "version": 1,
            "entries": {
                get_memory_id("memory"): {"score": 0.5, "access_count": 1}
            }
        }
        save_relevance_data(project_with_mind, data)

        result = track_memory_access(project_with_mind, "memory")

        assert result["score"] == 0.6  # 0.5 + 0.1 boost

    def test_caps_score_at_1(self, project_with_mind):
        """Should cap score at 1.0."""
        result = track_memory_access(project_with_mind, "memory")
        result = track_memory_access(project_with_mind, "memory")

        assert result["score"] <= 1.0

    def test_keep_all_mode_skips_tracking(self, project_with_mind):
        """Should skip tracking in keep_all mode."""
        config = {"version": 2, "memory": {"retention_mode": "keep_all"}}
        (project_with_mind / ".mind" / "config.json").write_text(
            json.dumps(config), encoding="utf-8"
        )

        result = track_memory_access(project_with_mind, "memory")

        assert result["score"] == 1.0
        assert result["mode"] == "keep_all"


class TestReinforceMemory:
    """Tests for reinforce_memory function."""

    def test_boosts_existing_memory(self, project_with_mind):
        """Should boost score of existing memory."""
        # Create initial entry
        data = {
            "version": 1,
            "entries": {
                get_memory_id("memory"): {"score": 0.5}
            }
        }
        save_relevance_data(project_with_mind, data)

        result = reinforce_memory(project_with_mind, "memory", boost=0.3)

        assert result["score"] == 0.8

    def test_creates_entry_if_not_exists(self, project_with_mind):
        """Should create entry if memory not tracked."""
        result = reinforce_memory(project_with_mind, "new memory")

        assert result["score"] == 0.7  # 0.5 default + 0.2 boost

    def test_caps_at_1(self, project_with_mind):
        """Should cap score at 1.0."""
        data = {
            "version": 1,
            "entries": {
                get_memory_id("memory"): {"score": 0.9}
            }
        }
        save_relevance_data(project_with_mind, data)

        result = reinforce_memory(project_with_mind, "memory", boost=0.5)

        assert result["score"] == 1.0


class TestDecayMemories:
    """Tests for decay_memories function."""

    def test_decays_old_memories(self, project_with_mind):
        """Should decay memories not accessed recently."""
        old_date = (datetime.now() - timedelta(days=60)).isoformat()
        data = {
            "version": 1,
            "entries": {
                "old": {"score": 1.0, "last_accessed": old_date}
            }
        }
        save_relevance_data(project_with_mind, data)

        result = decay_memories(project_with_mind)

        assert result["decayed"] >= 1
        # Check score was reduced
        new_data = load_relevance_data(project_with_mind)
        assert new_data["entries"]["old"]["score"] < 1.0

    def test_respects_min_relevance(self, project_with_mind):
        """Should not decay below min_relevance."""
        old_date = (datetime.now() - timedelta(days=365)).isoformat()
        data = {
            "version": 1,
            "entries": {
                "old": {"score": 1.0, "last_accessed": old_date}
            }
        }
        save_relevance_data(project_with_mind, data)

        decay_memories(project_with_mind)

        new_data = load_relevance_data(project_with_mind)
        assert new_data["entries"]["old"]["score"] >= 0.2  # min_relevance default

    def test_keeps_recent_memories(self, project_with_mind):
        """Should not decay recently accessed memories."""
        recent_date = datetime.now().isoformat()
        data = {
            "version": 1,
            "entries": {
                "recent": {"score": 1.0, "last_accessed": recent_date}
            }
        }
        save_relevance_data(project_with_mind, data)

        result = decay_memories(project_with_mind)

        assert result["decayed"] == 0
        new_data = load_relevance_data(project_with_mind)
        assert new_data["entries"]["recent"]["score"] == 1.0

    def test_keep_all_mode_skips_decay(self, project_with_mind):
        """Should skip decay in keep_all mode."""
        config = {"version": 2, "memory": {"retention_mode": "keep_all"}}
        (project_with_mind / ".mind" / "config.json").write_text(
            json.dumps(config), encoding="utf-8"
        )

        result = decay_memories(project_with_mind)

        assert result["mode"] == "keep_all"
        assert result["decayed"] == 0


class TestGetMemoryRelevance:
    """Tests for get_memory_relevance function."""

    def test_returns_tracked_score(self, project_with_mind):
        """Should return tracked score."""
        data = {
            "version": 1,
            "entries": {
                get_memory_id("memory"): {"score": 0.8}
            }
        }
        save_relevance_data(project_with_mind, data)

        result = get_memory_relevance(project_with_mind, "memory")

        assert result == 0.8

    def test_returns_default_for_untracked(self, project_with_mind):
        """Should return 0.5 for untracked memories."""
        result = get_memory_relevance(project_with_mind, "untracked")
        assert result == 0.5

    def test_returns_1_in_keep_all_mode(self, project_with_mind):
        """Should return 1.0 in keep_all mode."""
        config = {"version": 2, "memory": {"retention_mode": "keep_all"}}
        (project_with_mind / ".mind" / "config.json").write_text(
            json.dumps(config), encoding="utf-8"
        )

        result = get_memory_relevance(project_with_mind, "anything")

        assert result == 1.0


class TestFilterByRelevance:
    """Tests for filter_by_relevance function."""

    def test_filters_low_relevance(self, project_with_mind):
        """Should filter out low relevance memories."""
        data = {
            "version": 1,
            "entries": {
                get_memory_id("high"): {"score": 0.9},
                get_memory_id("low"): {"score": 0.2},
            }
        }
        save_relevance_data(project_with_mind, data)

        result = filter_by_relevance(
            project_with_mind,
            ["high", "low"],
            threshold=0.4
        )

        assert "high" in result
        assert "low" not in result

    def test_uses_custom_threshold(self, project_with_mind):
        """Should use custom threshold."""
        data = {
            "version": 1,
            "entries": {
                get_memory_id("medium"): {"score": 0.6},
            }
        }
        save_relevance_data(project_with_mind, data)

        result = filter_by_relevance(
            project_with_mind,
            ["medium"],
            threshold=0.7
        )

        assert "medium" not in result

    def test_returns_all_in_keep_all_mode(self, project_with_mind):
        """Should return all memories in keep_all mode."""
        config = {"version": 2, "memory": {"retention_mode": "keep_all"}}
        (project_with_mind / ".mind" / "config.json").write_text(
            json.dumps(config), encoding="utf-8"
        )

        result = filter_by_relevance(
            project_with_mind,
            ["a", "b", "c"],
            threshold=0.99
        )

        assert len(result) == 3


class TestPrioritizeByRelevance:
    """Tests for prioritize_by_relevance function."""

    def test_sorts_by_score_descending(self, project_with_mind):
        """Should sort by score descending."""
        data = {
            "version": 1,
            "entries": {
                get_memory_id("low"): {"score": 0.3},
                get_memory_id("high"): {"score": 0.9},
                get_memory_id("mid"): {"score": 0.6},
            }
        }
        save_relevance_data(project_with_mind, data)

        result = prioritize_by_relevance(
            project_with_mind,
            ["low", "high", "mid"]
        )

        assert result[0][0] == "high"
        assert result[1][0] == "mid"
        assert result[2][0] == "low"

    def test_returns_scores(self, project_with_mind):
        """Should return scores with memories."""
        data = {
            "version": 1,
            "entries": {
                get_memory_id("test"): {"score": 0.75},
            }
        }
        save_relevance_data(project_with_mind, data)

        result = prioritize_by_relevance(project_with_mind, ["test"])

        assert result[0] == ("test", 0.75)


class TestGetRelevanceTier:
    """Tests for get_relevance_tier function."""

    def test_high_tier(self):
        """Should return 'high' for scores >= 0.7."""
        assert get_relevance_tier(0.7) == "high"
        assert get_relevance_tier(0.9) == "high"
        assert get_relevance_tier(1.0) == "high"

    def test_medium_tier(self):
        """Should return 'medium' for scores 0.4-0.7."""
        assert get_relevance_tier(0.4) == "medium"
        assert get_relevance_tier(0.5) == "medium"
        assert get_relevance_tier(0.69) == "medium"

    def test_low_tier(self):
        """Should return 'low' for scores < 0.4."""
        assert get_relevance_tier(0.0) == "low"
        assert get_relevance_tier(0.2) == "low"
        assert get_relevance_tier(0.39) == "low"


class TestGetRetentionStats:
    """Tests for get_retention_stats function."""

    def test_returns_stats_for_empty(self, project_with_mind):
        """Should return stats for empty data."""
        result = get_retention_stats(project_with_mind)

        assert result["total"] == 0
        assert result["mode"] == "smart"

    def test_returns_stats_with_data(self, project_with_mind):
        """Should return accurate stats."""
        data = {
            "version": 1,
            "entries": {
                "a": {"score": 0.9},  # high
                "b": {"score": 0.8},  # high
                "c": {"score": 0.5},  # medium
                "d": {"score": 0.2},  # low
            }
        }
        save_relevance_data(project_with_mind, data)

        result = get_retention_stats(project_with_mind)

        assert result["total"] == 4
        assert result["high_relevance"] == 2
        assert result["medium_relevance"] == 1
        assert result["low_relevance"] == 1
        assert result["average_score"] == 0.6
