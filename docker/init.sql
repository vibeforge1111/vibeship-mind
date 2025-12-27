-- Mind v5 Database Initialization
-- Run once on container startup

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255) UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Events table (append-only event store)
CREATE TABLE IF NOT EXISTS events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    event_type VARCHAR(50) NOT NULL,
    aggregate_id UUID NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    correlation_id UUID NOT NULL,
    causation_id UUID,
    version INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_user_type ON events (user_id, event_type);
CREATE INDEX IF NOT EXISTS idx_events_aggregate ON events (aggregate_id);
CREATE INDEX IF NOT EXISTS idx_events_correlation ON events (correlation_id);
CREATE INDEX IF NOT EXISTS idx_events_created ON events (created_at DESC);

-- Memories table (hierarchical temporal memory)
CREATE TABLE IF NOT EXISTS memories (
    memory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    content TEXT NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    embedding VECTOR(1536),
    temporal_level INT NOT NULL CHECK (temporal_level BETWEEN 1 AND 4),
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,
    base_salience FLOAT DEFAULT 1.0 CHECK (base_salience BETWEEN 0 AND 1),
    outcome_adjustment FLOAT DEFAULT 0.0,
    retrieval_count INT DEFAULT 0,
    decision_count INT DEFAULT 0,
    positive_outcomes INT DEFAULT 0,
    negative_outcomes INT DEFAULT 0,
    promoted_from_level INT,
    promotion_timestamp TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memories_user_level ON memories (user_id, temporal_level);
CREATE INDEX IF NOT EXISTS idx_memories_user_salience ON memories (user_id, (base_salience + outcome_adjustment) DESC);

-- Vector index (using ivfflat for pgvector)
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Decision traces table
CREATE TABLE IF NOT EXISTS decision_traces (
    trace_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    session_id UUID NOT NULL,
    context_memory_ids TEXT[] DEFAULT '{}',
    memory_scores JSONB DEFAULT '{}',
    decision_type VARCHAR(100) NOT NULL,
    decision_summary TEXT NOT NULL,
    confidence FLOAT NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    alternatives_count INT DEFAULT 0,
    outcome_observed BOOLEAN DEFAULT FALSE,
    outcome_quality FLOAT CHECK (outcome_quality IS NULL OR outcome_quality BETWEEN -1 AND 1),
    outcome_timestamp TIMESTAMPTZ,
    outcome_signal VARCHAR(100),
    memory_attribution JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_traces_user ON decision_traces (user_id);
CREATE INDEX IF NOT EXISTS idx_traces_session ON decision_traces (session_id);
CREATE INDEX IF NOT EXISTS idx_traces_pending ON decision_traces (outcome_observed) WHERE NOT outcome_observed;

-- Salience adjustments log (for auditing)
CREATE TABLE IF NOT EXISTS salience_adjustments (
    adjustment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID NOT NULL REFERENCES memories(memory_id),
    trace_id UUID NOT NULL REFERENCES decision_traces(trace_id),
    previous_adjustment FLOAT NOT NULL,
    new_adjustment FLOAT NOT NULL,
    delta FLOAT NOT NULL,
    reason VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_adjustments_memory ON salience_adjustments (memory_id);
CREATE INDEX IF NOT EXISTS idx_adjustments_trace ON salience_adjustments (trace_id);

-- Create a default test user
INSERT INTO users (user_id, external_id)
VALUES ('00000000-0000-0000-0000-000000000001', 'test-user')
ON CONFLICT (external_id) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mind;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mind;
