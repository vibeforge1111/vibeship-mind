"""Tests for memory decay calculations."""

import pytest
from datetime import datetime, timedelta

from mind.models.base import EntityType
from mind.engine.decay import (
    calculate_decay,
    calculate_decay_from_timestamp,
    get_decay_threshold,
    HALF_LIFE_DAYS,
    STATUS_MULTIPLIERS,
)


class TestCalculateDecay:
    """Tests for calculate_decay function."""

    def test_zero_days_returns_one(self):
        """Entity accessed today should have no decay."""
        decay = calculate_decay(EntityType.DECISION, "active", days_since_access=0)
        assert decay == pytest.approx(1.0)

    def test_half_life_returns_half(self):
        """Entity accessed at half-life should have ~0.5 decay."""
        # Decision has 60-day half-life
        decay = calculate_decay(EntityType.DECISION, "active", days_since_access=60)
        assert decay == pytest.approx(0.5, rel=0.01)

        # Issue has 30-day half-life
        decay = calculate_decay(EntityType.ISSUE, "open", days_since_access=30)
        assert decay == pytest.approx(0.5, rel=0.01)

        # Sharp edge has 120-day half-life
        decay = calculate_decay(EntityType.SHARP_EDGE, None, days_since_access=120)
        assert decay == pytest.approx(0.5, rel=0.01)

        # Episode has 90-day half-life
        decay = calculate_decay(EntityType.EPISODE, None, days_since_access=90)
        assert decay == pytest.approx(0.5, rel=0.01)

    def test_two_half_lives_returns_quarter(self):
        """Entity accessed at 2x half-life should have ~0.25 decay."""
        decay = calculate_decay(EntityType.ISSUE, "open", days_since_access=60)
        assert decay == pytest.approx(0.25, rel=0.01)

    def test_superseded_decays_faster(self):
        """Superseded decisions should decay 5x faster."""
        active_decay = calculate_decay(EntityType.DECISION, "active", days_since_access=12)
        superseded_decay = calculate_decay(EntityType.DECISION, "superseded", days_since_access=12)

        # Superseded has effective half-life of 60 * 0.2 = 12 days
        # At 12 days, superseded should be ~0.5
        assert superseded_decay == pytest.approx(0.5, rel=0.01)
        # Active should still be high
        assert active_decay > 0.85

    def test_resolved_decays_faster(self):
        """Resolved issues should decay 2x faster."""
        open_decay = calculate_decay(EntityType.ISSUE, "open", days_since_access=15)
        resolved_decay = calculate_decay(EntityType.ISSUE, "resolved", days_since_access=15)

        # Resolved has effective half-life of 30 * 0.5 = 15 days
        # At 15 days, resolved should be ~0.5
        assert resolved_decay == pytest.approx(0.5, rel=0.01)
        # Open should still be higher
        assert open_decay > 0.7

    def test_wont_fix_same_as_resolved(self):
        """wont_fix should have same decay rate as resolved."""
        resolved_decay = calculate_decay(EntityType.ISSUE, "resolved", days_since_access=15)
        wont_fix_decay = calculate_decay(EntityType.ISSUE, "wont_fix", days_since_access=15)
        assert resolved_decay == pytest.approx(wont_fix_decay)

    def test_negative_days_treated_as_zero(self):
        """Negative days should be treated as zero (no decay)."""
        decay = calculate_decay(EntityType.DECISION, "active", days_since_access=-10)
        assert decay == pytest.approx(1.0)

    def test_entity_type_specific_half_lives(self):
        """Different entity types should have different half-lives."""
        # At 60 days, only decision should be at 0.5
        decision_decay = calculate_decay(EntityType.DECISION, "active", days_since_access=60)
        issue_decay = calculate_decay(EntityType.ISSUE, "open", days_since_access=60)
        edge_decay = calculate_decay(EntityType.SHARP_EDGE, None, days_since_access=60)

        assert decision_decay == pytest.approx(0.5, rel=0.01)
        assert issue_decay < 0.3  # Issues decay faster
        assert edge_decay > 0.7  # Edges decay slower

    def test_none_status_uses_default(self):
        """None status should use default multiplier of 1.0."""
        with_status = calculate_decay(EntityType.SHARP_EDGE, "active", days_since_access=30)
        without_status = calculate_decay(EntityType.SHARP_EDGE, None, days_since_access=30)
        assert with_status == pytest.approx(without_status)


class TestCalculateDecayFromTimestamp:
    """Tests for calculate_decay_from_timestamp function."""

    def test_recent_access_high_decay(self):
        """Recently accessed entity should have high decay value."""
        now = datetime.utcnow()
        last_accessed = now - timedelta(hours=1)
        decay = calculate_decay_from_timestamp(
            EntityType.DECISION,
            "active",
            last_accessed=last_accessed,
            now=now,
        )
        assert decay > 0.99

    def test_old_access_low_decay(self):
        """Entity not accessed for a long time should have low decay."""
        now = datetime.utcnow()
        last_accessed = now - timedelta(days=120)  # 2x decision half-life
        decay = calculate_decay_from_timestamp(
            EntityType.DECISION,
            "active",
            last_accessed=last_accessed,
            now=now,
        )
        assert decay == pytest.approx(0.25, rel=0.01)

    def test_never_accessed_low_decay(self):
        """Entity never accessed should have very low decay (180 days assumed)."""
        now = datetime.utcnow()
        decay = calculate_decay_from_timestamp(
            EntityType.DECISION,
            "active",
            last_accessed=None,
            now=now,
        )
        # 180 days / 60-day half-life = 3 half-lives = 0.125
        assert decay == pytest.approx(0.125, rel=0.01)

    def test_default_now_uses_utcnow(self):
        """If now is not provided, should use utcnow."""
        last_accessed = datetime.utcnow() - timedelta(days=1)
        decay = calculate_decay_from_timestamp(
            EntityType.DECISION,
            "active",
            last_accessed=last_accessed,
        )
        assert decay > 0.98

    def test_status_affects_timestamp_calculation(self):
        """Status should affect decay when calculated from timestamp."""
        now = datetime.utcnow()
        last_accessed = now - timedelta(days=12)

        active_decay = calculate_decay_from_timestamp(
            EntityType.DECISION,
            "active",
            last_accessed=last_accessed,
            now=now,
        )
        superseded_decay = calculate_decay_from_timestamp(
            EntityType.DECISION,
            "superseded",
            last_accessed=last_accessed,
            now=now,
        )

        # Superseded should be at ~0.5 (12 days = its half-life)
        assert superseded_decay == pytest.approx(0.5, rel=0.01)
        assert active_decay > 0.85


class TestDecayThreshold:
    """Tests for get_decay_threshold function."""

    def test_default_threshold(self):
        """Default threshold should be 0.1."""
        assert get_decay_threshold() == 0.1

    def test_custom_threshold(self):
        """Custom threshold should be returned."""
        assert get_decay_threshold(min_relevance=0.2) == 0.2
        assert get_decay_threshold(min_relevance=0.05) == 0.05


class TestDecayConstants:
    """Tests for decay constants and configuration."""

    def test_half_life_days_defined(self):
        """All entity types should have half-life defined."""
        assert EntityType.DECISION in HALF_LIFE_DAYS
        assert EntityType.ISSUE in HALF_LIFE_DAYS
        assert EntityType.SHARP_EDGE in HALF_LIFE_DAYS
        assert EntityType.EPISODE in HALF_LIFE_DAYS

    def test_status_multipliers_defined(self):
        """Key statuses should have multipliers defined."""
        assert "superseded" in STATUS_MULTIPLIERS
        assert "resolved" in STATUS_MULTIPLIERS
        assert "wont_fix" in STATUS_MULTIPLIERS
        assert "active" in STATUS_MULTIPLIERS
        assert "open" in STATUS_MULTIPLIERS

    def test_multiplier_values_in_range(self):
        """All multipliers should be between 0 and 1."""
        for status, multiplier in STATUS_MULTIPLIERS.items():
            assert 0 < multiplier <= 1, f"{status} multiplier out of range: {multiplier}"

    def test_half_life_values_positive(self):
        """All half-life values should be positive."""
        for entity_type, half_life in HALF_LIFE_DAYS.items():
            assert half_life > 0, f"{entity_type} half-life must be positive: {half_life}"


class TestDecayIntegration:
    """Integration tests for decay with real scenarios."""

    def test_scenario_old_but_accessed_stays_fresh(self):
        """A 6-month-old decision that's still accessed should be fresh."""
        now = datetime.utcnow()
        # Decision is 6 months old but was accessed yesterday
        last_accessed = now - timedelta(days=1)

        decay = calculate_decay_from_timestamp(
            EntityType.DECISION,
            "active",
            last_accessed=last_accessed,
            now=now,
        )

        # Should be nearly 1.0 because of recent access
        assert decay > 0.98

    def test_scenario_resolved_last_week_is_stale(self):
        """A resolved issue from last week should be stale."""
        now = datetime.utcnow()
        # Issue was resolved and accessed 15 days ago
        last_accessed = now - timedelta(days=15)

        decay = calculate_decay_from_timestamp(
            EntityType.ISSUE,
            "resolved",
            last_accessed=last_accessed,
            now=now,
        )

        # Resolved issue half-life is 15 days, so at 15 days = 0.5
        assert decay == pytest.approx(0.5, rel=0.01)

    def test_scenario_sharp_edge_lasts_longer(self):
        """Sharp edges should stay relevant much longer than issues."""
        now = datetime.utcnow()
        last_accessed = now - timedelta(days=60)

        issue_decay = calculate_decay_from_timestamp(
            EntityType.ISSUE,
            "open",
            last_accessed=last_accessed,
            now=now,
        )
        edge_decay = calculate_decay_from_timestamp(
            EntityType.SHARP_EDGE,
            None,
            last_accessed=last_accessed,
            now=now,
        )

        # Issue at 60 days = 2 half-lives = 0.25
        # Edge at 60 days = 0.5 half-lives = 0.7
        assert issue_decay == pytest.approx(0.25, rel=0.01)
        assert edge_decay > 0.7

    def test_scenario_superseded_decision_fades_quickly(self):
        """A superseded decision should become irrelevant quickly."""
        now = datetime.utcnow()
        last_accessed = now - timedelta(days=36)  # 3x superseded half-life

        decay = calculate_decay_from_timestamp(
            EntityType.DECISION,
            "superseded",
            last_accessed=last_accessed,
            now=now,
        )

        # Superseded half-life = 12 days, 36 days = 3 half-lives = 0.125
        assert decay == pytest.approx(0.125, rel=0.01)
