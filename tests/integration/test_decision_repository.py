"""Integration tests for DecisionRepository."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from mind.core.errors import ErrorCode
from mind.core.decision.models import DecisionTrace, Outcome
from mind.infrastructure.postgres.repositories import DecisionRepository


pytestmark = pytest.mark.asyncio


class TestDecisionTraceCreate:
    """Tests for decision trace creation."""

    async def test_create_trace_success(
        self,
        session: AsyncSession,
        user_id,
        sample_trace_data,
    ):
        """Creating a valid decision trace should succeed."""
        repo = DecisionRepository(session)

        trace = DecisionTrace(**sample_trace_data)
        result = await repo.create_trace(trace)

        assert result.is_ok
        assert result.value.trace_id == trace.trace_id
        assert result.value.decision_type == trace.decision_type

    async def test_create_trace_with_memories(
        self,
        session: AsyncSession,
        user_id,
    ):
        """Creating trace with memory references should work."""
        repo = DecisionRepository(session)

        memory_ids = [uuid4(), uuid4(), uuid4()]
        memory_scores = {str(mid): 0.8 - (i * 0.1) for i, mid in enumerate(memory_ids)}

        trace = DecisionTrace(
            trace_id=uuid4(),
            user_id=user_id,
            session_id=uuid4(),
            memory_ids=memory_ids,
            memory_scores=memory_scores,
            decision_type="action_selection",
            decision_summary="Selected action A based on context",
            confidence=0.9,
            alternatives_count=3,
        )

        result = await repo.create_trace(trace)

        assert result.is_ok
        assert result.value.memory_ids == memory_ids
        assert result.value.memory_scores == memory_scores


class TestDecisionTraceGet:
    """Tests for decision trace retrieval."""

    async def test_get_existing_trace(
        self,
        session: AsyncSession,
        user_id,
        sample_trace_data,
    ):
        """Getting an existing trace should return it."""
        repo = DecisionRepository(session)

        trace = DecisionTrace(**sample_trace_data)
        await repo.create_trace(trace)

        result = await repo.get_trace(trace.trace_id)

        assert result.is_ok
        assert result.value.trace_id == trace.trace_id
        assert result.value.decision_summary == trace.decision_summary

    async def test_get_nonexistent_trace(
        self,
        session: AsyncSession,
    ):
        """Getting a nonexistent trace should return error."""
        repo = DecisionRepository(session)

        result = await repo.get_trace(uuid4())

        assert not result.is_ok
        assert result.error.code == ErrorCode.DECISION_NOT_FOUND


class TestOutcomeRecording:
    """Tests for outcome recording."""

    async def test_record_positive_outcome(
        self,
        session: AsyncSession,
        user_id,
        sample_trace_data,
    ):
        """Recording a positive outcome should update the trace."""
        repo = DecisionRepository(session)

        trace = DecisionTrace(**sample_trace_data)
        await repo.create_trace(trace)

        outcome = Outcome(
            trace_id=trace.trace_id,
            quality=0.8,
            signal="user_satisfaction",
            observed_at=datetime.now(UTC),
        )
        attributions = {"mem1": 0.5, "mem2": 0.3}

        result = await repo.record_outcome(trace.trace_id, outcome, attributions)

        assert result.is_ok
        assert result.value.outcome_observed is True
        assert result.value.outcome_quality == 0.8
        assert result.value.outcome_signal == "user_satisfaction"

    async def test_record_negative_outcome(
        self,
        session: AsyncSession,
        user_id,
        sample_trace_data,
    ):
        """Recording a negative outcome should work."""
        repo = DecisionRepository(session)

        trace = DecisionTrace(**sample_trace_data)
        await repo.create_trace(trace)

        outcome = Outcome(
            trace_id=trace.trace_id,
            quality=-0.5,
            signal="user_correction",
            observed_at=datetime.now(UTC),
        )

        result = await repo.record_outcome(trace.trace_id, outcome, {})

        assert result.is_ok
        assert result.value.outcome_quality == -0.5

    async def test_record_outcome_twice_fails(
        self,
        session: AsyncSession,
        user_id,
        sample_trace_data,
    ):
        """Recording outcome twice should fail."""
        repo = DecisionRepository(session)

        trace = DecisionTrace(**sample_trace_data)
        await repo.create_trace(trace)

        outcome = Outcome(
            trace_id=trace.trace_id,
            quality=0.5,
            signal="completion",
            observed_at=datetime.now(UTC),
        )

        # First recording succeeds
        await repo.record_outcome(trace.trace_id, outcome, {})

        # Second recording fails
        result = await repo.record_outcome(trace.trace_id, outcome, {})

        assert not result.is_ok
        assert result.error.code == ErrorCode.DECISION_ALREADY_OBSERVED

    async def test_record_outcome_nonexistent_trace(
        self,
        session: AsyncSession,
    ):
        """Recording outcome for nonexistent trace should fail."""
        repo = DecisionRepository(session)

        outcome = Outcome(
            trace_id=uuid4(),
            quality=0.5,
            signal="completion",
            observed_at=datetime.now(UTC),
        )

        result = await repo.record_outcome(uuid4(), outcome, {})

        assert not result.is_ok
        assert result.error.code == ErrorCode.DECISION_NOT_FOUND


class TestPendingTraces:
    """Tests for pending trace retrieval."""

    async def test_get_pending_traces(
        self,
        session: AsyncSession,
        user_id,
    ):
        """Should return traces without outcomes."""
        repo = DecisionRepository(session)

        # Create pending trace
        pending = DecisionTrace(
            trace_id=uuid4(),
            user_id=user_id,
            session_id=uuid4(),
            memory_ids=[],
            memory_scores={},
            decision_type="test",
            decision_summary="Pending decision",
            confidence=0.7,
        )
        await repo.create_trace(pending)

        # Create observed trace
        observed = DecisionTrace(
            trace_id=uuid4(),
            user_id=user_id,
            session_id=uuid4(),
            memory_ids=[],
            memory_scores={},
            decision_type="test",
            decision_summary="Observed decision",
            confidence=0.7,
        )
        await repo.create_trace(observed)

        # Record outcome for observed trace
        outcome = Outcome(
            trace_id=observed.trace_id,
            quality=0.5,
            signal="test",
            observed_at=datetime.now(UTC),
        )
        await repo.record_outcome(observed.trace_id, outcome, {})

        # Get pending traces
        pending_traces = await repo.get_pending_traces(user_id)

        trace_ids = [t.trace_id for t in pending_traces]
        assert pending.trace_id in trace_ids
        assert observed.trace_id not in trace_ids

    async def test_get_pending_traces_respects_limit(
        self,
        session: AsyncSession,
        user_id,
    ):
        """Pending traces query should respect limit."""
        repo = DecisionRepository(session)

        # Create multiple pending traces
        for i in range(10):
            trace = DecisionTrace(
                trace_id=uuid4(),
                user_id=user_id,
                session_id=uuid4(),
                memory_ids=[],
                memory_scores={},
                decision_type="test",
                decision_summary=f"Decision {i}",
                confidence=0.7,
            )
            await repo.create_trace(trace)

        pending = await repo.get_pending_traces(user_id, limit=5)

        assert len(pending) == 5


class TestDecisionTraceFiltering:
    """Tests for decision trace filtering by session."""

    async def test_traces_per_session(
        self,
        session: AsyncSession,
        user_id,
    ):
        """Traces should be correctly associated with sessions."""
        repo = DecisionRepository(session)

        session_a = uuid4()
        session_b = uuid4()

        # Create traces for session A
        for i in range(3):
            trace = DecisionTrace(
                trace_id=uuid4(),
                user_id=user_id,
                session_id=session_a,
                memory_ids=[],
                memory_scores={},
                decision_type="test",
                decision_summary=f"Session A decision {i}",
                confidence=0.7,
            )
            await repo.create_trace(trace)

        # Create traces for session B
        for i in range(2):
            trace = DecisionTrace(
                trace_id=uuid4(),
                user_id=user_id,
                session_id=session_b,
                memory_ids=[],
                memory_scores={},
                decision_type="test",
                decision_summary=f"Session B decision {i}",
                confidence=0.7,
            )
            await repo.create_trace(trace)

        # All traces should be retrievable
        pending = await repo.get_pending_traces(user_id, limit=100)

        session_a_count = sum(1 for t in pending if t.session_id == session_a)
        session_b_count = sum(1 for t in pending if t.session_id == session_b)

        assert session_a_count >= 3
        assert session_b_count >= 2
