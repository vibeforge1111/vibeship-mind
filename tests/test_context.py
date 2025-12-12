"""Tests for context relevance scoring."""

import pytest
from datetime import datetime, timedelta

from mind.engine.context import (
    ContextEngine,
    RECENCY_HALF_LIFE_DAYS,
    MAX_RECENCY_BOOST,
    MAX_FREQUENCY_BOOST,
    MAX_TRIGGER_BOOST,
)


class TestRecencyBoost:
    """Tests for recency boost calculation."""

    def test_brand_new_entity_gets_max_boost(self):
        """Entity created today gets maximum recency boost."""
        engine = ContextEngine(embedding_store=None)
        boost = engine._calculate_recency_boost(days_old=0)
        assert boost == pytest.approx(MAX_RECENCY_BOOST, rel=0.01)

    def test_half_life_halves_boost(self):
        """Entity at half-life age gets half the boost."""
        engine = ContextEngine(embedding_store=None)
        boost = engine._calculate_recency_boost(days_old=RECENCY_HALF_LIFE_DAYS)
        assert boost == pytest.approx(MAX_RECENCY_BOOST / 2, rel=0.01)

    def test_two_half_lives_quarters_boost(self):
        """Entity at 2x half-life gets 1/4 the boost."""
        engine = ContextEngine(embedding_store=None)
        boost = engine._calculate_recency_boost(days_old=RECENCY_HALF_LIFE_DAYS * 2)
        assert boost == pytest.approx(MAX_RECENCY_BOOST / 4, rel=0.01)

    def test_old_entity_gets_minimal_boost(self):
        """Very old entity gets near-zero boost."""
        engine = ContextEngine(embedding_store=None)
        boost = engine._calculate_recency_boost(days_old=100)
        assert boost < 0.01  # Should be nearly zero

    def test_negative_days_treated_as_zero(self):
        """Negative days (future timestamp) treated as brand new."""
        engine = ContextEngine(embedding_store=None)
        boost = engine._calculate_recency_boost(days_old=-5)
        assert boost == pytest.approx(MAX_RECENCY_BOOST, rel=0.01)


class TestFrequencyBoost:
    """Tests for frequency boost calculation."""

    def test_zero_accesses_no_boost(self):
        """Entity with zero accesses gets no boost."""
        engine = ContextEngine(embedding_store=None)
        boost = engine._calculate_frequency_boost(access_count=0)
        assert boost == 0.0

    def test_one_access_gets_partial_boost(self):
        """Single access gets 0.1 boost."""
        engine = ContextEngine(embedding_store=None)
        boost = engine._calculate_frequency_boost(access_count=1)
        assert boost == pytest.approx(0.1, rel=0.01)

    def test_three_accesses_near_max(self):
        """Three accesses gets close to max."""
        engine = ContextEngine(embedding_store=None)
        boost = engine._calculate_frequency_boost(access_count=3)
        assert boost == pytest.approx(MAX_FREQUENCY_BOOST, rel=0.01)

    def test_many_accesses_capped_at_max(self):
        """Many accesses capped at MAX_FREQUENCY_BOOST."""
        engine = ContextEngine(embedding_store=None)
        boost = engine._calculate_frequency_boost(access_count=100)
        assert boost == MAX_FREQUENCY_BOOST

    def test_negative_count_no_boost(self):
        """Negative count (shouldn't happen) gets no boost."""
        engine = ContextEngine(embedding_store=None)
        boost = engine._calculate_frequency_boost(access_count=-5)
        assert boost == 0.0


class TestScoringConfiguration:
    """Tests for scoring configuration values."""

    def test_max_boosts_are_reasonable(self):
        """Max boosts should sum to less than 1 to avoid extreme scores."""
        total_max_boost = MAX_RECENCY_BOOST + MAX_FREQUENCY_BOOST + MAX_TRIGGER_BOOST
        # Multiplier would be 1 + total_max_boost, which should stay reasonable
        assert total_max_boost < 1.0  # Max multiplier would be < 2.0

    def test_half_life_is_positive(self):
        """Half-life should be a positive number of days."""
        assert RECENCY_HALF_LIFE_DAYS > 0
