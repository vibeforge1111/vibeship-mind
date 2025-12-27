-- =============================================================================
-- Mind v5 PostgreSQL DDL
-- =============================================================================
-- Version: 5.0.0
-- Date: December 27, 2025
-- Purpose: Production-ready schema for Mind v5 decision intelligence system
--
-- Architecture Overview:
--   - mind_events: Append-only event store (primary source of truth)
--   - mind_memories: Read projections for memory queries
--
-- Performance Targets:
--   - Event append: <10ms p99
--   - Memory query: <50ms p99
--   - Connection pool: pgbouncer, 100 connections
--
-- Security:
--   - Row-Level Security (RLS) for user isolation
--   - Encrypted content fields (application-level encryption)
--   - No PII in indexes or logs
-- =============================================================================

-- =============================================================================
-- SECTION 1: DATABASE AND EXTENSION SETUP
-- =============================================================================

-- Create databases (run as superuser)
-- Note: Execute these commands outside of a transaction
-- CREATE DATABASE mind_events OWNER mind_admin;
-- CREATE DATABASE mind_memories OWNER mind_admin;

-- Connect to mind_events database
\c mind_events;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";          -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";           -- Cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pg_partman";         -- Partition management
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements"; -- Query statistics

-- Enable pgvector for vector similarity search (fallback for Qdrant)
CREATE EXTENSION IF NOT EXISTS "vector";

-- =============================================================================
-- SECTION 2: CUSTOM TYPES AND ENUMS
-- =============================================================================

-- Event types for the event backbone
-- Matches NATS JetStream event taxonomy
CREATE TYPE event_type_enum AS ENUM (
    'InteractionRecorded',      -- Raw user/agent interaction
    'MemoryExtracted',          -- Processed memory from interaction
    'DecisionMade',             -- Decision with context snapshot
    'OutcomeObserved',          -- Feedback signal received
    'CausalLinkDiscovered',     -- New causal relationship found
    'PatternValidated',         -- Pattern ready for federation
    'MemoryPromoted',           -- Memory level promotion
    'MemoryDemoted',            -- Memory salience decreased
    'SalienceAdjusted',         -- Outcome-based salience change
    'UserCreated',              -- New user registration
    'UserSettingsChanged',      -- User preferences updated
    'SessionStarted',           -- New session began
    'SessionEnded'              -- Session completed
);

-- Temporal levels for hierarchical memory
-- L1=Immediate (session), L2=Situational (weeks), L3=Seasonal (months), L4=Identity (years)
CREATE TYPE temporal_level_enum AS ENUM (
    'immediate',    -- L1: Current session, working memory
    'situational',  -- L2: Active tasks, recent events (weeks)
    'seasonal',     -- L3: Projects, recurring patterns (months)
    'identity'      -- L4: Core values, stable preferences (years)
);

-- Memory content types
CREATE TYPE content_type_enum AS ENUM (
    'fact',         -- Factual information about user
    'preference',   -- User preferences
    'event',        -- Past event/interaction
    'goal',         -- User goals and objectives
    'constraint',   -- Limitations or restrictions
    'relationship', -- Relationships between entities
    'skill',        -- User abilities/knowledge
    'context'       -- Contextual information
);

-- Outcome quality indicators
CREATE TYPE outcome_signal_enum AS ENUM (
    'explicit_positive',    -- User explicitly said it helped
    'explicit_negative',    -- User explicitly said it didn't help
    'implicit_positive',    -- User engaged positively (clicks, follows)
    'implicit_negative',    -- User disengaged (abandoned, corrected)
    'correction',           -- User corrected the system
    'task_completed',       -- Associated task was completed
    'task_abandoned',       -- Associated task was abandoned
    'unknown'               -- Outcome unclear
);

-- =============================================================================
-- SECTION 3: USERS TABLE
-- =============================================================================

-- Users table with encryption key management
-- Primary key for all user-scoped data
CREATE TABLE users (
    -- Primary identification
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- External identity (encrypted)
    -- Store encrypted references to external auth systems
    external_id_encrypted BYTEA,
    auth_provider VARCHAR(50) NOT NULL DEFAULT 'internal',

    -- Encryption key reference (actual key in Vault)
    -- Each user has unique encryption key for their data
    encryption_key_id UUID NOT NULL,
    encryption_key_version INTEGER NOT NULL DEFAULT 1,

    -- Account status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,

    -- Privacy settings
    federation_consent BOOLEAN NOT NULL DEFAULT FALSE,  -- Allow pattern federation
    data_retention_days INTEGER DEFAULT NULL,           -- NULL = indefinite

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT users_encryption_key_version_positive CHECK (encryption_key_version > 0),
    CONSTRAINT users_data_retention_positive CHECK (data_retention_days IS NULL OR data_retention_days > 0)
);

-- Index for active users lookup
CREATE INDEX idx_users_active ON users (is_active) WHERE is_active = TRUE;

-- Index for federation-consenting users
CREATE INDEX idx_users_federation ON users (federation_consent) WHERE federation_consent = TRUE;

COMMENT ON TABLE users IS 'User accounts with encryption key references. All PII is encrypted.';
COMMENT ON COLUMN users.encryption_key_id IS 'Reference to user encryption key in HashiCorp Vault';
COMMENT ON COLUMN users.federation_consent IS 'User consent for cross-user pattern federation (GDPR compliant)';

-- =============================================================================
-- SECTION 4: EVENTS TABLE (Append-Only Event Store)
-- =============================================================================

-- Events table - append-only, partitioned by month
-- This is the source of truth for all state changes
-- Performance target: <10ms p99 for event append
CREATE TABLE events (
    -- Event identification
    event_id UUID NOT NULL DEFAULT uuid_generate_v4(),

    -- Event metadata
    event_type event_type_enum NOT NULL,
    event_version INTEGER NOT NULL DEFAULT 1,  -- Schema version for evolution

    -- Aggregate identification (what entity this event belongs to)
    aggregate_type VARCHAR(50) NOT NULL,  -- 'user', 'memory', 'decision', etc.
    aggregate_id UUID NOT NULL,

    -- Event ownership
    user_id UUID NOT NULL,

    -- Event payload (JSONB for flexibility)
    -- Contains the actual event data, encrypted fields as needed
    payload JSONB NOT NULL,

    -- Event metadata for tracing
    metadata JSONB NOT NULL DEFAULT '{}',

    -- Correlation for request tracing (OpenTelemetry integration)
    correlation_id UUID NOT NULL,  -- Links related events across services
    causation_id UUID,             -- The event that caused this event

    -- Timestamps
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- When the event logically occurred
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- When we recorded it

    -- Partition key (required for partitioning)
    partition_key TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT events_pkey PRIMARY KEY (event_id, partition_key),
    CONSTRAINT events_version_positive CHECK (event_version > 0),
    CONSTRAINT events_recorded_after_occurred CHECK (recorded_at >= occurred_at)
) PARTITION BY RANGE (partition_key);

-- Create partitions for the next 12 months (pg_partman will manage ongoing)
-- Each partition covers one month
CREATE TABLE events_y2025m12 PARTITION OF events
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');
CREATE TABLE events_y2026m01 PARTITION OF events
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE events_y2026m02 PARTITION OF events
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE events_y2026m03 PARTITION OF events
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE events_y2026m04 PARTITION OF events
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE events_y2026m05 PARTITION OF events
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE events_y2026m06 PARTITION OF events
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE events_y2026m07 PARTITION OF events
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE events_y2026m08 PARTITION OF events
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE events_y2026m09 PARTITION OF events
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE events_y2026m10 PARTITION OF events
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE events_y2026m11 PARTITION OF events
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');

-- Indexes optimized for event replay and correlation lookups
-- Index for correlation_id lookup (request tracing)
-- Performance critical for distributed tracing
CREATE INDEX idx_events_correlation ON events (correlation_id);

-- Index for aggregate replay (rebuild projections)
CREATE INDEX idx_events_aggregate ON events (aggregate_type, aggregate_id, occurred_at);

-- Index for user event history
CREATE INDEX idx_events_user_type ON events (user_id, event_type, occurred_at DESC);

-- Index for time-based queries
CREATE INDEX idx_events_occurred ON events (occurred_at DESC);

-- GIN index for payload queries (selective use)
CREATE INDEX idx_events_payload ON events USING GIN (payload jsonb_path_ops);

COMMENT ON TABLE events IS 'Append-only event store. Source of truth for all state. Partitioned by month.';
COMMENT ON COLUMN events.correlation_id IS 'OpenTelemetry trace ID for distributed request tracing';
COMMENT ON COLUMN events.causation_id IS 'Event ID that caused this event (event chain)';
COMMENT ON COLUMN events.payload IS 'Event data. Sensitive fields encrypted at application level.';

-- =============================================================================
-- SECTION 5: MEMORIES TABLE (Hierarchical Memory Store)
-- =============================================================================

-- Switch to mind_memories database for read projections
-- \c mind_memories;

-- Re-create extensions for memories database
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- CREATE EXTENSION IF NOT EXISTS "vector";

-- Memories table - hierarchical temporal memory storage
-- Performance target: <50ms p99 for memory queries
CREATE TABLE memories (
    -- Primary identification
    memory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Ownership (RLS enforced)
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Content (encrypted at application level)
    content_encrypted BYTEA NOT NULL,           -- AES-256 encrypted content
    content_hash VARCHAR(64) NOT NULL,          -- SHA-256 for deduplication
    content_type content_type_enum NOT NULL,

    -- Vector embedding for similarity search
    -- Dimension 1536 matches text-embedding-3-small
    embedding vector(1536),

    -- Hierarchical temporal level
    temporal_level temporal_level_enum NOT NULL,

    -- Temporal validity (bi-temporal model)
    valid_from TIMESTAMPTZ NOT NULL,            -- When this memory became valid
    valid_until TIMESTAMPTZ,                    -- NULL = still valid

    -- Salience (outcome-weighted)
    -- Base salience from extraction confidence
    base_salience FLOAT NOT NULL DEFAULT 1.0,
    -- Adjustment from decision outcomes (-1.0 to +1.0)
    outcome_adjustment FLOAT NOT NULL DEFAULT 0.0,
    -- Computed effective salience (clamped 0.0 to 1.0)
    effective_salience FLOAT GENERATED ALWAYS AS (
        GREATEST(0.0, LEAST(1.0, base_salience + outcome_adjustment))
    ) STORED,

    -- Usage statistics (for salience tuning)
    retrieval_count INTEGER NOT NULL DEFAULT 0,
    last_retrieved_at TIMESTAMPTZ,
    decision_count INTEGER NOT NULL DEFAULT 0,  -- How many decisions used this
    positive_outcomes INTEGER NOT NULL DEFAULT 0,
    negative_outcomes INTEGER NOT NULL DEFAULT 0,

    -- Promotion tracking
    promoted_from_level temporal_level_enum,
    promotion_timestamp TIMESTAMPTZ,

    -- Source event reference
    source_event_id UUID NOT NULL,              -- Event that created this memory
    source_correlation_id UUID NOT NULL,        -- For tracing

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT memories_salience_range CHECK (base_salience >= 0.0 AND base_salience <= 1.0),
    CONSTRAINT memories_outcome_range CHECK (outcome_adjustment >= -1.0 AND outcome_adjustment <= 1.0),
    CONSTRAINT memories_valid_range CHECK (valid_until IS NULL OR valid_until > valid_from),
    CONSTRAINT memories_counts_positive CHECK (
        retrieval_count >= 0 AND
        decision_count >= 0 AND
        positive_outcomes >= 0 AND
        negative_outcomes >= 0
    )
);

-- Composite index for primary memory retrieval pattern
-- user_id + temporal_level + salience (most common query)
CREATE INDEX idx_memories_user_level_salience ON memories (
    user_id,
    temporal_level,
    effective_salience DESC
) WHERE valid_until IS NULL;  -- Only active memories

-- Index for salience-based retrieval across all levels
CREATE INDEX idx_memories_user_salience ON memories (
    user_id,
    effective_salience DESC
) WHERE valid_until IS NULL;

-- Index for content deduplication
CREATE INDEX idx_memories_user_hash ON memories (user_id, content_hash);

-- Vector similarity index using IVFFlat (faster builds) or HNSW (faster queries)
-- Using HNSW for production workloads (<50ms p99 requirement)
CREATE INDEX idx_memories_embedding ON memories USING hnsw (
    embedding vector_cosine_ops
) WITH (m = 16, ef_construction = 64);

-- Index for source event tracing
CREATE INDEX idx_memories_source_event ON memories (source_event_id);

-- Index for recently created memories (for projector catch-up)
CREATE INDEX idx_memories_created ON memories (created_at DESC);

-- Index for memories pending promotion analysis
CREATE INDEX idx_memories_promotion_candidates ON memories (
    user_id,
    temporal_level,
    decision_count DESC
) WHERE promoted_from_level IS NULL AND valid_until IS NULL;

COMMENT ON TABLE memories IS 'Hierarchical temporal memories projected from events. RLS enforced.';
COMMENT ON COLUMN memories.content_encrypted IS 'AES-256 encrypted content. Key from user encryption_key_id in Vault.';
COMMENT ON COLUMN memories.effective_salience IS 'Computed: base_salience + outcome_adjustment, clamped [0,1]';
COMMENT ON COLUMN memories.embedding IS 'Vector(1536) from text-embedding-3-small for similarity search';

-- =============================================================================
-- SECTION 6: DECISION TRACES TABLE
-- =============================================================================

-- Decision traces - tracks which memories influenced each decision
-- Critical for outcome attribution and salience learning
CREATE TABLE decision_traces (
    -- Primary identification
    trace_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Ownership (RLS enforced)
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Session context
    session_id UUID NOT NULL,

    -- Context snapshot (what memories were retrieved)
    context_snapshot JSONB NOT NULL,        -- Serialized memory summaries (no full content)
    context_memory_ids UUID[] NOT NULL,     -- Memory IDs used for attribution
    retrieval_scores JSONB NOT NULL,        -- {memory_id: {vector: 0.8, graph: 0.7, final: 0.85}}
    retrieval_latency_ms FLOAT NOT NULL,    -- For SLO tracking

    -- Decision made
    decision_type VARCHAR(100) NOT NULL,    -- Category of decision
    decision_summary VARCHAR(500) NOT NULL, -- Brief, non-PII description
    confidence FLOAT NOT NULL,              -- Model confidence (0.0 to 1.0)
    alternatives_considered JSONB DEFAULT '[]',  -- Other options ranked

    -- Outcome tracking (filled asynchronously)
    outcome_observed BOOLEAN NOT NULL DEFAULT FALSE,
    outcome_quality FLOAT,                  -- -1.0 (harmful) to +1.0 (helpful)
    outcome_signal outcome_signal_enum,
    outcome_timestamp TIMESTAMPTZ,
    outcome_details JSONB,                  -- Additional outcome context

    -- Attribution (computed after outcome)
    -- Maps memory_id -> contribution_score
    memory_attribution JSONB,
    attribution_computed_at TIMESTAMPTZ,

    -- Source event
    source_event_id UUID NOT NULL,
    correlation_id UUID NOT NULL,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT traces_confidence_range CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CONSTRAINT traces_outcome_range CHECK (outcome_quality IS NULL OR (outcome_quality >= -1.0 AND outcome_quality <= 1.0)),
    CONSTRAINT traces_latency_positive CHECK (retrieval_latency_ms >= 0),
    CONSTRAINT traces_memory_ids_not_empty CHECK (array_length(context_memory_ids, 1) > 0)
);

-- Index for pending outcome collection
CREATE INDEX idx_traces_pending_outcome ON decision_traces (
    user_id,
    created_at DESC
) WHERE NOT outcome_observed;

-- Index for outcome analysis by user
CREATE INDEX idx_traces_user_outcome ON decision_traces (
    user_id,
    outcome_observed,
    outcome_quality
) WHERE outcome_observed = TRUE;

-- Index for session-based queries
CREATE INDEX idx_traces_session ON decision_traces (session_id, created_at);

-- Index for correlation tracing
CREATE INDEX idx_traces_correlation ON decision_traces (correlation_id);

-- GIN index for memory_ids array lookups (find decisions using specific memory)
CREATE INDEX idx_traces_memory_ids ON decision_traces USING GIN (context_memory_ids);

-- Index for attribution computation (unprocessed outcomes)
CREATE INDEX idx_traces_attribution_pending ON decision_traces (
    created_at
) WHERE outcome_observed = TRUE AND attribution_computed_at IS NULL;

COMMENT ON TABLE decision_traces IS 'Tracks memory-to-decision-to-outcome chains for salience learning';
COMMENT ON COLUMN decision_traces.context_memory_ids IS 'Array of memory IDs used. Enables attribution computation.';
COMMENT ON COLUMN decision_traces.memory_attribution IS 'Post-outcome attribution: {memory_id: contribution_score}';

-- =============================================================================
-- SECTION 7: OUTCOMES TABLE
-- =============================================================================

-- Outcomes - observed results linked to decision traces
-- Supports multiple outcome signals per decision
CREATE TABLE outcomes (
    -- Primary identification
    outcome_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Link to decision
    trace_id UUID NOT NULL REFERENCES decision_traces(trace_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Outcome signal
    signal_type outcome_signal_enum NOT NULL,
    quality_score FLOAT NOT NULL,               -- -1.0 to +1.0
    confidence FLOAT NOT NULL DEFAULT 1.0,      -- How confident in this signal

    -- Signal source and evidence
    signal_source VARCHAR(100) NOT NULL,        -- 'user_feedback', 'task_tracker', 'implicit', etc.
    evidence JSONB,                             -- Supporting data (no PII)

    -- Timing
    observed_at TIMESTAMPTZ NOT NULL,           -- When outcome was observed
    latency_from_decision_ms BIGINT,            -- Time from decision to outcome

    -- Source event
    source_event_id UUID NOT NULL,
    correlation_id UUID NOT NULL,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT outcomes_quality_range CHECK (quality_score >= -1.0 AND quality_score <= 1.0),
    CONSTRAINT outcomes_confidence_range CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CONSTRAINT outcomes_latency_positive CHECK (latency_from_decision_ms IS NULL OR latency_from_decision_ms >= 0)
);

-- Index for trace-based lookups
CREATE INDEX idx_outcomes_trace ON outcomes (trace_id);

-- Index for user outcome history
CREATE INDEX idx_outcomes_user ON outcomes (user_id, observed_at DESC);

-- Index for signal type analysis
CREATE INDEX idx_outcomes_signal ON outcomes (signal_type, quality_score);

-- Index for correlation tracing
CREATE INDEX idx_outcomes_correlation ON outcomes (correlation_id);

COMMENT ON TABLE outcomes IS 'Observed outcomes for decisions. Multiple outcomes per decision supported.';
COMMENT ON COLUMN outcomes.quality_score IS 'Normalized quality: -1.0 (harmful) to +1.0 (helpful)';

-- =============================================================================
-- SECTION 8: SALIENCE ADJUSTMENTS TABLE
-- =============================================================================

-- Salience adjustments - tracks all changes to memory salience
-- Audit trail for outcome-based learning
CREATE TABLE salience_adjustments (
    -- Primary identification
    adjustment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Memory affected
    memory_id UUID NOT NULL REFERENCES memories(memory_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Adjustment details
    adjustment_delta FLOAT NOT NULL,            -- Change amount
    previous_adjustment FLOAT NOT NULL,         -- Before this change
    new_adjustment FLOAT NOT NULL,              -- After this change

    -- Reason and source
    reason VARCHAR(100) NOT NULL,               -- 'outcome_attribution', 'manual', 'decay', etc.
    source_trace_id UUID REFERENCES decision_traces(trace_id),
    source_outcome_id UUID REFERENCES outcomes(outcome_id),

    -- Attribution details (when from outcome)
    attribution_weight FLOAT,                   -- Memory's weight in the decision
    outcome_quality FLOAT,                      -- Outcome quality that triggered this

    -- Source event
    source_event_id UUID NOT NULL,
    correlation_id UUID NOT NULL,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT adjustments_delta_range CHECK (adjustment_delta >= -2.0 AND adjustment_delta <= 2.0),
    CONSTRAINT adjustments_consistency CHECK (
        ABS((previous_adjustment + adjustment_delta) - new_adjustment) < 0.0001
    )
);

-- Index for memory adjustment history
CREATE INDEX idx_adjustments_memory ON salience_adjustments (memory_id, created_at DESC);

-- Index for user adjustment analytics
CREATE INDEX idx_adjustments_user ON salience_adjustments (user_id, created_at DESC);

-- Index for trace-based lookups
CREATE INDEX idx_adjustments_trace ON salience_adjustments (source_trace_id)
    WHERE source_trace_id IS NOT NULL;

-- Index for correlation tracing
CREATE INDEX idx_adjustments_correlation ON salience_adjustments (correlation_id);

COMMENT ON TABLE salience_adjustments IS 'Audit trail of all salience changes. Enables learning analysis.';
COMMENT ON COLUMN salience_adjustments.adjustment_delta IS 'The change applied. Positive = memory helped, Negative = memory hurt.';

-- =============================================================================
-- SECTION 9: FEDERATED PATTERNS TABLE
-- =============================================================================

-- Federated patterns - sanitized patterns for cross-user intelligence
-- Privacy: Minimum thresholds enforced (source_count >= 100, user_count >= 10)
CREATE TABLE federated_patterns (
    -- Primary identification
    pattern_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Abstract pattern (NO PII)
    trigger_type VARCHAR(100) NOT NULL,         -- Abstract category
    trigger_indicators JSONB NOT NULL,          -- Abstract signals (no content)

    -- Response strategy
    response_strategy VARCHAR(100) NOT NULL,    -- Abstract response type
    response_template TEXT,                     -- Parameterized template (no PII)

    -- Measured outcome
    outcome_improvement FLOAT NOT NULL,         -- Average improvement percentage
    confidence_interval JSONB NOT NULL,         -- {lower: x, upper: y}

    -- Aggregation statistics (privacy thresholds)
    source_count INTEGER NOT NULL,              -- Must be >= 100
    user_count INTEGER NOT NULL,                -- Must be >= 10

    -- Differential privacy
    differential_privacy_applied BOOLEAN NOT NULL DEFAULT TRUE,
    epsilon FLOAT NOT NULL DEFAULT 0.1,         -- Privacy parameter
    delta FLOAT NOT NULL DEFAULT 0.00001,       -- Privacy parameter (10^-5)

    -- Validity
    first_observed TIMESTAMPTZ NOT NULL,
    last_validated TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Pattern versioning
    version INTEGER NOT NULL DEFAULT 1,
    parent_pattern_id UUID REFERENCES federated_patterns(pattern_id),

    -- Source event
    source_event_id UUID NOT NULL,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Privacy enforcement constraints
    CONSTRAINT patterns_source_count_privacy CHECK (source_count >= 100),
    CONSTRAINT patterns_user_count_privacy CHECK (user_count >= 10),
    CONSTRAINT patterns_epsilon_valid CHECK (epsilon > 0 AND epsilon <= 1.0),
    CONSTRAINT patterns_delta_valid CHECK (delta > 0 AND delta <= 0.001),
    CONSTRAINT patterns_improvement_range CHECK (outcome_improvement >= -1.0 AND outcome_improvement <= 10.0)
);

-- Index for active pattern lookup by trigger
CREATE INDEX idx_patterns_trigger ON federated_patterns (trigger_type)
    WHERE is_active = TRUE;

-- Index for pattern validation queue
CREATE INDEX idx_patterns_validation ON federated_patterns (last_validated)
    WHERE is_active = TRUE;

-- Index for pattern versioning
CREATE INDEX idx_patterns_parent ON federated_patterns (parent_pattern_id)
    WHERE parent_pattern_id IS NOT NULL;

COMMENT ON TABLE federated_patterns IS 'Privacy-preserving patterns for collective intelligence. Strict thresholds enforced.';
COMMENT ON COLUMN federated_patterns.source_count IS 'Minimum 100 sources required for privacy. Hard constraint.';
COMMENT ON COLUMN federated_patterns.user_count IS 'Minimum 10 users required for privacy. Hard constraint.';
COMMENT ON COLUMN federated_patterns.epsilon IS 'Differential privacy epsilon. Default 0.1 for strong privacy.';

-- =============================================================================
-- SECTION 10: ROW-LEVEL SECURITY (RLS)
-- =============================================================================

-- Enable RLS on user-scoped tables
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE decision_traces ENABLE ROW LEVEL SECURITY;
ALTER TABLE outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE salience_adjustments ENABLE ROW LEVEL SECURITY;

-- Create application role
-- Note: Execute as superuser
-- CREATE ROLE mind_app LOGIN PASSWORD 'change_in_production';

-- RLS policies for memories table
CREATE POLICY memories_user_isolation ON memories
    FOR ALL
    USING (user_id = current_setting('app.current_user_id')::UUID)
    WITH CHECK (user_id = current_setting('app.current_user_id')::UUID);

-- RLS policies for decision_traces table
CREATE POLICY traces_user_isolation ON decision_traces
    FOR ALL
    USING (user_id = current_setting('app.current_user_id')::UUID)
    WITH CHECK (user_id = current_setting('app.current_user_id')::UUID);

-- RLS policies for outcomes table
CREATE POLICY outcomes_user_isolation ON outcomes
    FOR ALL
    USING (user_id = current_setting('app.current_user_id')::UUID)
    WITH CHECK (user_id = current_setting('app.current_user_id')::UUID);

-- RLS policies for salience_adjustments table
CREATE POLICY adjustments_user_isolation ON salience_adjustments
    FOR ALL
    USING (user_id = current_setting('app.current_user_id')::UUID)
    WITH CHECK (user_id = current_setting('app.current_user_id')::UUID);

-- Admin bypass policy (for system operations)
-- Use with caution - only for Temporal workers and admin tasks
CREATE POLICY memories_admin_bypass ON memories
    FOR ALL
    TO mind_admin
    USING (TRUE)
    WITH CHECK (TRUE);

CREATE POLICY traces_admin_bypass ON decision_traces
    FOR ALL
    TO mind_admin
    USING (TRUE)
    WITH CHECK (TRUE);

CREATE POLICY outcomes_admin_bypass ON outcomes
    FOR ALL
    TO mind_admin
    USING (TRUE)
    WITH CHECK (TRUE);

CREATE POLICY adjustments_admin_bypass ON salience_adjustments
    FOR ALL
    TO mind_admin
    USING (TRUE)
    WITH CHECK (TRUE);

COMMENT ON POLICY memories_user_isolation ON memories IS
    'Users can only access their own memories. Set app.current_user_id before queries.';

-- =============================================================================
-- SECTION 11: FUNCTIONS AND TRIGGERS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_memories_updated_at
    BEFORE UPDATE ON memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_traces_updated_at
    BEFORE UPDATE ON decision_traces
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_patterns_updated_at
    BEFORE UPDATE ON federated_patterns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to increment retrieval count
CREATE OR REPLACE FUNCTION increment_memory_retrieval(
    p_memory_id UUID,
    p_user_id UUID
)
RETURNS VOID AS $$
BEGIN
    UPDATE memories
    SET
        retrieval_count = retrieval_count + 1,
        last_retrieved_at = NOW()
    WHERE memory_id = p_memory_id
      AND user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Function to apply salience adjustment
CREATE OR REPLACE FUNCTION apply_salience_adjustment(
    p_memory_id UUID,
    p_user_id UUID,
    p_delta FLOAT,
    p_reason VARCHAR(100),
    p_trace_id UUID DEFAULT NULL,
    p_outcome_id UUID DEFAULT NULL,
    p_event_id UUID DEFAULT NULL,
    p_correlation_id UUID DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_current_adjustment FLOAT;
    v_new_adjustment FLOAT;
    v_adjustment_id UUID;
BEGIN
    -- Get current adjustment
    SELECT outcome_adjustment INTO v_current_adjustment
    FROM memories
    WHERE memory_id = p_memory_id AND user_id = p_user_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Memory not found: %', p_memory_id;
    END IF;

    -- Calculate new adjustment (clamped to prevent extreme values)
    v_new_adjustment := GREATEST(-1.0, LEAST(1.0, v_current_adjustment + p_delta));

    -- Update memory
    UPDATE memories
    SET outcome_adjustment = v_new_adjustment
    WHERE memory_id = p_memory_id AND user_id = p_user_id;

    -- Record adjustment
    INSERT INTO salience_adjustments (
        memory_id, user_id,
        adjustment_delta, previous_adjustment, new_adjustment,
        reason, source_trace_id, source_outcome_id,
        source_event_id, correlation_id
    ) VALUES (
        p_memory_id, p_user_id,
        p_delta, v_current_adjustment, v_new_adjustment,
        p_reason, p_trace_id, p_outcome_id,
        COALESCE(p_event_id, uuid_generate_v4()),
        COALESCE(p_correlation_id, uuid_generate_v4())
    ) RETURNING adjustment_id INTO v_adjustment_id;

    RETURN v_adjustment_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get decision success rate (DSR) for a user
CREATE OR REPLACE FUNCTION get_decision_success_rate(
    p_user_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    total_decisions BIGINT,
    positive_outcomes BIGINT,
    negative_outcomes BIGINT,
    success_rate FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT AS total_decisions,
        COUNT(*) FILTER (WHERE dt.outcome_quality > 0)::BIGINT AS positive_outcomes,
        COUNT(*) FILTER (WHERE dt.outcome_quality < 0)::BIGINT AS negative_outcomes,
        CASE
            WHEN COUNT(*) FILTER (WHERE dt.outcome_quality IS NOT NULL) = 0 THEN 0.0
            ELSE COUNT(*) FILTER (WHERE dt.outcome_quality > 0)::FLOAT /
                 COUNT(*) FILTER (WHERE dt.outcome_quality IS NOT NULL)::FLOAT
        END AS success_rate
    FROM decision_traces dt
    WHERE dt.user_id = p_user_id
      AND dt.outcome_observed = TRUE
      AND dt.created_at >= NOW() - (p_days || ' days')::INTERVAL;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_decision_success_rate IS
    'Calculate Decision Success Rate (DSR) for a user over specified days';

-- =============================================================================
-- SECTION 12: MATERIALIZED VIEWS FOR ANALYTICS
-- =============================================================================

-- Materialized view for memory effectiveness by temporal level
CREATE MATERIALIZED VIEW mv_memory_effectiveness AS
SELECT
    m.user_id,
    m.temporal_level,
    COUNT(*) AS memory_count,
    AVG(m.effective_salience) AS avg_salience,
    AVG(m.positive_outcomes::FLOAT / NULLIF(m.decision_count, 0)) AS avg_success_rate,
    SUM(m.decision_count) AS total_decisions,
    SUM(m.positive_outcomes) AS total_positive,
    SUM(m.negative_outcomes) AS total_negative
FROM memories m
WHERE m.valid_until IS NULL
GROUP BY m.user_id, m.temporal_level;

CREATE UNIQUE INDEX idx_mv_memory_effectiveness ON mv_memory_effectiveness (user_id, temporal_level);

-- Materialized view for pattern effectiveness
CREATE MATERIALIZED VIEW mv_pattern_effectiveness AS
SELECT
    fp.trigger_type,
    COUNT(*) AS pattern_count,
    AVG(fp.outcome_improvement) AS avg_improvement,
    SUM(fp.source_count) AS total_sources,
    SUM(fp.user_count) AS total_users
FROM federated_patterns fp
WHERE fp.is_active = TRUE
GROUP BY fp.trigger_type;

CREATE UNIQUE INDEX idx_mv_pattern_effectiveness ON mv_pattern_effectiveness (trigger_type);

-- Refresh function for materialized views
CREATE OR REPLACE FUNCTION refresh_analytics_views()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_memory_effectiveness;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_pattern_effectiveness;
END;
$$ LANGUAGE plpgsql;

COMMENT ON MATERIALIZED VIEW mv_memory_effectiveness IS
    'Pre-aggregated memory effectiveness metrics. Refresh hourly.';
COMMENT ON MATERIALIZED VIEW mv_pattern_effectiveness IS
    'Pre-aggregated pattern effectiveness metrics. Refresh daily.';

-- =============================================================================
-- SECTION 13: PARTITION MANAGEMENT (pg_partman)
-- =============================================================================

-- Configure pg_partman for automatic partition management
-- Note: Requires pg_partman extension to be installed

-- SELECT partman.create_parent(
--     p_parent_table => 'public.events',
--     p_control => 'partition_key',
--     p_type => 'native',
--     p_interval => '1 month',
--     p_premake => 3,          -- Create 3 future partitions
--     p_start_partition => '2025-12-01'
-- );

-- -- Update partman config for retention
-- UPDATE partman.part_config
-- SET retention = '24 months',
--     retention_keep_table = TRUE,  -- Keep old partitions (archive)
--     retention_keep_index = FALSE  -- Drop indexes on detached partitions
-- WHERE parent_table = 'public.events';

-- Schedule partition maintenance (run daily via pg_cron or external scheduler)
-- SELECT partman.run_maintenance();

-- =============================================================================
-- SECTION 14: PERFORMANCE TUNING RECOMMENDATIONS
-- =============================================================================

/*
PERFORMANCE TUNING RECOMMENDATIONS
==================================

Connection Pooling (pgbouncer):
- Use pgbouncer in transaction mode
- Pool size: 100 connections (as per spec)
- Reserve 10 connections for admin

PostgreSQL Configuration (for 16GB RAM, 4 vCPU):
- shared_buffers = 4GB
- effective_cache_size = 12GB
- work_mem = 64MB
- maintenance_work_mem = 1GB
- random_page_cost = 1.1 (for SSD)
- effective_io_concurrency = 200
- max_parallel_workers_per_gather = 2
- max_parallel_workers = 4

Vacuum Configuration:
- autovacuum_vacuum_scale_factor = 0.05
- autovacuum_analyze_scale_factor = 0.02
- autovacuum_vacuum_cost_delay = 2ms

Write-Ahead Log (WAL):
- wal_level = replica
- max_wal_size = 4GB
- checkpoint_completion_target = 0.9

Monitoring Queries:

-- Event append latency (should be <10ms p99)
SELECT
    percentile_cont(0.99) WITHIN GROUP (ORDER BY extract(epoch from (recorded_at - occurred_at)) * 1000) as p99_ms
FROM events
WHERE recorded_at > NOW() - INTERVAL '1 hour';

-- Memory query performance (should be <50ms p99)
-- Monitor via pg_stat_statements

-- Check partition sizes
SELECT
    schemaname || '.' || tablename as partition,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) as size
FROM pg_tables
WHERE tablename LIKE 'events_y%'
ORDER BY tablename;

-- Index usage
SELECT
    schemaname, tablename, indexname,
    idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- RLS overhead check
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM memories
WHERE user_id = 'test-uuid'::uuid
LIMIT 10;

*/

-- =============================================================================
-- SECTION 15: SECURITY HARDENING
-- =============================================================================

-- Revoke public access
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC;

-- Grant specific permissions to application role
-- GRANT SELECT, INSERT, UPDATE, DELETE ON users TO mind_app;
-- GRANT SELECT, INSERT ON events TO mind_app;  -- Append only
-- GRANT SELECT, INSERT, UPDATE ON memories TO mind_app;
-- GRANT SELECT, INSERT, UPDATE ON decision_traces TO mind_app;
-- GRANT SELECT, INSERT ON outcomes TO mind_app;
-- GRANT SELECT, INSERT ON salience_adjustments TO mind_app;
-- GRANT SELECT ON federated_patterns TO mind_app;  -- Read only for app

-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mind_app;
-- GRANT EXECUTE ON FUNCTION increment_memory_retrieval TO mind_app;
-- GRANT EXECUTE ON FUNCTION apply_salience_adjustment TO mind_app;
-- GRANT EXECUTE ON FUNCTION get_decision_success_rate TO mind_app;

-- Create read-only role for analytics
-- CREATE ROLE mind_analytics LOGIN PASSWORD 'change_in_production';
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO mind_analytics;
-- GRANT SELECT ON mv_memory_effectiveness TO mind_analytics;
-- GRANT SELECT ON mv_pattern_effectiveness TO mind_analytics;

-- =============================================================================
-- SECTION 16: INITIALIZATION VERIFICATION
-- =============================================================================

-- Verification queries to run after setup
DO $$
BEGIN
    -- Verify all tables exist
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'users') THEN
        RAISE EXCEPTION 'Table users not created';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'events') THEN
        RAISE EXCEPTION 'Table events not created';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'memories') THEN
        RAISE EXCEPTION 'Table memories not created';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'decision_traces') THEN
        RAISE EXCEPTION 'Table decision_traces not created';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'outcomes') THEN
        RAISE EXCEPTION 'Table outcomes not created';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'salience_adjustments') THEN
        RAISE EXCEPTION 'Table salience_adjustments not created';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'federated_patterns') THEN
        RAISE EXCEPTION 'Table federated_patterns not created';
    END IF;

    -- Verify RLS is enabled
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_tables t ON c.relname = t.tablename
        WHERE t.tablename = 'memories' AND c.relrowsecurity = TRUE
    ) THEN
        RAISE EXCEPTION 'RLS not enabled on memories table';
    END IF;

    -- Verify vector extension
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        RAISE WARNING 'pgvector extension not installed - vector search disabled';
    END IF;

    RAISE NOTICE 'Database schema verification completed successfully';
END $$;

-- =============================================================================
-- END OF DDL
-- =============================================================================

/*
DEPLOYMENT CHECKLIST:
=====================
1. [ ] Create databases: mind_events, mind_memories
2. [ ] Create roles: mind_admin, mind_app, mind_analytics
3. [ ] Run this DDL as mind_admin
4. [ ] Configure pg_partman for automatic partition management
5. [ ] Set up pgbouncer connection pooling
6. [ ] Configure Prometheus postgres_exporter
7. [ ] Set up backup strategy (WAL archiving + pg_basebackup)
8. [ ] Test RLS policies with sample data
9. [ ] Run EXPLAIN ANALYZE on critical queries
10. [ ] Document connection strings in HashiCorp Vault

MONITORING ALERTS:
==================
- Event append latency > 10ms p99
- Memory query latency > 50ms p99
- Connection pool saturation > 80%
- Partition size > 10GB
- Vacuum lag > 1 hour
- Replication lag > 1 second

SCHEMA VERSION: 5.0.0
DATE: December 27, 2025
*/
