"""Tests for decision domain models."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from mind.core.decision.models import DecisionTrace, Outcome, SalienceUpdate


class TestOutcome:
    """Tests for Outcome model."""

    def test_positive_outcome(self):
        """Positive quality should be detected."""
        outcome = Outcome(
            trace_id=uuid4(),
            quality=0.8,
            signal="explicit_feedback",
        )
        assert outcome.is_positive() is True
        assert outcome.is_negative() is False

    def test_negative_outcome(self):
        """Negative quality should be detected."""
        outcome = Outcome(
            trace_id=uuid4(),
            quality=-0.5,
            signal="implicit_rejection",
        )
        assert outcome.is_positive() is False
        assert outcome.is_negative() is True

    def test_neutral_outcome(self):
        """Zero quality should be neither positive nor negative."""
        outcome = Outcome(
            trace_id=uuid4(),
            quality=0.0,
            signal="unknown",
        )
        assert outcome.is_positive() is False
        assert outcome.is_negative() is False


class TestSalienceUpdate:
    """Tests for SalienceUpdate model."""

    def test_from_positive_outcome(self):
        """Positive outcome should create positive delta."""
        outcome = Outcome(
            trace_id=uuid4(),
            quality=0.8,
            signal="explicit_positive",
        )

        update = SalienceUpdate.from_outcome(
            memory_id=uuid4(),
            trace_id=outcome.trace_id,
            outcome=outcome,
            contribution=0.5,  # 50% contribution
        )

        # Delta = quality * contribution * 0.1 = 0.8 * 0.5 * 0.1 = 0.04
        assert update.delta == pytest.approx(0.04)
        assert update.reason == "positive_outcome"

    def test_from_negative_outcome(self):
        """Negative outcome should create negative delta."""
        outcome = Outcome(
            trace_id=uuid4(),
            quality=-0.6,
            signal="explicit_negative",
        )

        update = SalienceUpdate.from_outcome(
            memory_id=uuid4(),
            trace_id=outcome.trace_id,
            outcome=outcome,
            contribution=1.0,  # 100% contribution
        )

        # Delta = quality * contribution * 0.1 = -0.6 * 1.0 * 0.1 = -0.06
        assert update.delta == pytest.approx(-0.06)
        assert update.reason == "negative_outcome"

    def test_max_delta_capped(self):
        """Delta should be capped at 0.1 max."""
        outcome = Outcome(
            trace_id=uuid4(),
            quality=1.0,  # Maximum quality
            signal="perfect",
        )

        update = SalienceUpdate.from_outcome(
            memory_id=uuid4(),
            trace_id=outcome.trace_id,
            outcome=outcome,
            contribution=1.0,  # 100% contribution
        )

        # Max delta = 1.0 * 1.0 * 0.1 = 0.1
        assert update.delta == pytest.approx(0.1)


class TestDecisionTrace:
    """Tests for DecisionTrace model."""

    @pytest.fixture
    def sample_trace(self) -> DecisionTrace:
        """Create a sample decision trace."""
        return DecisionTrace(
            trace_id=uuid4(),
            user_id=uuid4(),
            session_id=uuid4(),
            memory_ids=[uuid4(), uuid4()],
            memory_scores={"mem1": 0.9, "mem2": 0.7},
            decision_type="recommendation",
            decision_summary="Recommended dark mode",
            confidence=0.85,
            alternatives_count=2,
        )

    def test_default_outcome_not_observed(self, sample_trace: DecisionTrace):
        """New traces should not have outcome observed."""
        assert sample_trace.outcome_observed is False
        assert sample_trace.outcome_quality is None

    def test_timestamps(self, sample_trace: DecisionTrace):
        """Trace should have created_at timestamp."""
        assert sample_trace.created_at is not None
        assert sample_trace.created_at <= datetime.now(UTC)
