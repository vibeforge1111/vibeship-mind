# Mind v5: Service Level Objectives (SLOs)

> **Version**: 1.0
> **Date**: December 27, 2025
> **Status**: Active
> **Owners**: SRE Team, Platform Engineering

---

## Table of Contents

1. [SLO Philosophy](#slo-philosophy)
2. [Core SLOs](#core-slos)
3. [Error Budget Policy](#error-budget-policy)
4. [Prometheus Metrics](#prometheus-metrics)
5. [Alerting Rules](#alerting-rules)
6. [Dashboard Specifications](#dashboard-specifications)
7. [On-Call Runbook References](#on-call-runbook-references)

---

## SLO Philosophy

### Guiding Principles

Mind v5 SLOs are built on three foundational principles:

#### 1. User-Centric Measurement

SLOs measure what users experience, not what the system reports internally. A user making a context retrieval call cares about total latency, not whether the delay occurred in vector search, graph traversal, or network transit.

```
User Experience = End-to-End Latency + Success Rate
                  Not: Component A + Component B + Component C (internal metrics)
```

**Implications:**
- All latency SLOs are measured at API gateway ingress
- Success rates include partial failures visible to users
- Timeouts count as failures, not "not counted"

#### 2. Error Budgets Enable Velocity

Error budgets are the difference between 100% and the SLO target. They represent the acceptable amount of unreliability that enables development velocity.

```
Error Budget = 100% - SLO Target

Example: 99.9% availability SLO
         Error Budget = 0.1% = 8.76 hours/year
```

**The Error Budget Contract:**
- Engineering owns the error budget
- Product releases consume error budget
- When budget is exhausted, reliability work takes priority
- Budget resets monthly (rolling 30-day window)

#### 3. Burn Rate Alerting

Traditional threshold-based alerting is either too noisy (tight thresholds) or too slow (loose thresholds). Burn rate alerting solves this by measuring how fast you're consuming your error budget.

```
Burn Rate = (Error Rate / Error Budget Rate)

If consuming 1 month of budget in 1 month: Burn Rate = 1x
If consuming 1 month of budget in 1 hour:  Burn Rate = 720x (CRITICAL)
If consuming 1 month of budget in 1 day:   Burn Rate = 30x (HIGH)
```

---

## Core SLOs

### SLO-1: Memory Retrieval Performance

**Service**: Memory Retrieval API (`/v1/memory/retrieve`, gRPC `MemoryService.RetrieveContext`)

| Metric | Target | Measurement Window |
|--------|--------|-------------------|
| Availability | 99.9% | Rolling 30 days |
| Latency p50 | < 50ms | Rolling 1 hour |
| Latency p99 | < 200ms | Rolling 1 hour |
| Throughput | 1,000 queries/sec sustained | Rolling 5 minutes |

**Definition of Success:**
- Request returns HTTP 2xx or gRPC OK within latency threshold
- Response contains at least one relevant memory (non-empty result set)
- No partial failures in fusion pipeline

**Exclusions:**
- Requests with invalid authentication (401/403)
- Requests exceeding rate limits (429)
- Explicit client cancellations

**Error Budget Calculation:**
```
Monthly requests (estimated): 2,592,000,000 (1000/sec * 86400 * 30)
Allowed failures at 99.9%:    2,592,000 requests/month
Daily budget:                 86,400 failures/day
Hourly budget:                3,600 failures/hour
```

---

### SLO-2: Event Processing Pipeline

**Service**: NATS JetStream Event Backbone, Event Projectors

| Metric | Target | Measurement Window |
|--------|--------|-------------------|
| Availability | 99.95% | Rolling 30 days |
| Processing Latency p50 | < 10ms | Rolling 1 hour |
| Processing Latency p99 | < 100ms | Rolling 1 hour |
| Throughput | 400,000 events/sec sustained | Rolling 5 minutes |
| Ordering Guarantee | 100% within partition | Rolling 24 hours |

**Definition of Success:**
- Event published to NATS receives ACK within latency threshold
- Event delivered to all subscribed consumers exactly once
- Event projections complete within 1 minute of publication

**Exclusions:**
- Planned maintenance windows (announced 72h in advance)
- Events with malformed payloads (client errors)

**Error Budget Calculation:**
```
Monthly events (estimated):    1,036,800,000,000 (400K/sec * 86400 * 30)
Allowed failures at 99.95%:    518,400,000 events/month
Daily budget:                  17,280,000 events/day
Hourly budget:                 720,000 events/hour
```

---

### SLO-3: Decision Tracking Service

**Service**: Decision Service API (`/v1/decisions/*`, gRPC `DecisionService.*`)

| Metric | Target | Measurement Window |
|--------|--------|-------------------|
| Availability | 99.95% | Rolling 30 days |
| Record Latency p50 | < 20ms | Rolling 1 hour |
| Record Latency p99 | < 100ms | Rolling 1 hour |
| Outcome Recording Success | 99.9% | Rolling 24 hours |
| Attribution Accuracy | > 80% | Rolling 7 days |

**Definition of Success:**
- Decision trace recorded with full context snapshot
- Trace ID returned for future outcome correlation
- Outcome feedback properly attributed to source memories

**Exclusions:**
- Duplicate outcome recordings (idempotent, not counted as failure)
- Outcomes for expired traces (> 30 days old)

**Error Budget Calculation:**
```
Monthly decisions (estimated): 259,200,000 (100/sec * 86400 * 30)
Allowed failures at 99.95%:    129,600 decisions/month
Daily budget:                  4,320 failures/day
Hourly budget:                 180 failures/hour
```

---

### SLO-4: API Gateway Availability

**Service**: All Mind v5 API endpoints (REST + gRPC)

| Metric | Target | Measurement Window |
|--------|--------|-------------------|
| Overall Availability | 99.9% | Rolling 30 days |
| Error Rate (5xx) | < 0.1% | Rolling 1 hour |
| SSL/TLS Handshake Success | 99.99% | Rolling 24 hours |

**Definition of Success:**
- API gateway accepts and routes request
- Response returned (success or client error 4xx)
- No gateway-level 502/503/504 errors

**Exclusions:**
- DDoS mitigation responses
- Requests blocked by WAF rules

**Downtime Budget:**
```
Monthly minutes: 43,200 (30 days * 24 hours * 60 minutes)
Allowed downtime at 99.9%: 43.2 minutes/month = 8.76 hours/year
```

---

### SLO-5: Causal Query Performance

**Service**: Causal Inference Engine, FalkorDB Graph Queries

| Metric | Target | Measurement Window |
|--------|--------|-------------------|
| Availability | 99.5% | Rolling 30 days |
| Query Latency p50 | < 100ms | Rolling 1 hour |
| Query Latency p99 | < 500ms | Rolling 1 hour |
| 2-hop Traversal p99 | < 150ms | Rolling 1 hour |

**Definition of Success:**
- Causal chain query returns within latency threshold
- Graph traversal completes without timeout
- Results include causal strength and confidence scores

**Exclusions:**
- Queries exceeding maximum depth (> 5 hops)
- Cold-start queries after graph rebuild

---

### SLO-6: Gardener Workflow Reliability

**Service**: Temporal.io Gardener Workflows

| Metric | Target | Measurement Window |
|--------|--------|-------------------|
| Workflow Success Rate | 99.5% | Rolling 7 days |
| MemoryConsolidation Completion | 99.9% | Rolling 24 hours |
| CausalDiscovery Completion | 99% | Rolling 7 days |
| Maximum Workflow Duration | < 4 hours | Per execution |

**Definition of Success:**
- Workflow reaches terminal success state
- All activities complete within timeout
- Durable state correctly persisted

**Exclusions:**
- Explicit workflow cancellations
- Workflows blocked by upstream data unavailability

---

## Error Budget Policy

### Budget States

| State | Remaining Budget | Actions |
|-------|-----------------|---------|
| **Healthy** | > 50% | Normal development velocity, feature releases proceed |
| **Warning** | 25-50% | Increased monitoring, defer risky changes, postmortem any incidents |
| **Critical** | 10-25% | Freeze non-critical releases, prioritize reliability work |
| **Exhausted** | < 10% | Full feature freeze, all hands on reliability |

### Escalation Matrix

```
Budget < 50%:
  - Notify: #mind-sre-alerts Slack channel
  - Action: Review recent deployments, increase monitoring

Budget < 25%:
  - Notify: Engineering Manager, Product Manager
  - Action: Defer feature releases, schedule reliability sprint

Budget < 10%:
  - Notify: VP Engineering, CTO
  - Action: War room, all deployments require SRE approval

Budget Exhausted (< 5%):
  - Notify: Executive team
  - Action: Customer communication, incident retrospective
```

### Budget Recovery

Error budget resets on a rolling 30-day window. Recovery strategies:

1. **Immediate**: Fix the root cause of budget consumption
2. **Short-term**: Deploy targeted reliability improvements
3. **Long-term**: Architecture changes to prevent recurrence

### Budget Borrowing

In exceptional cases, teams may "borrow" from next period's budget with:
- VP Engineering approval
- Documented repayment plan
- Post-incident commitment to reliability work

---

## Prometheus Metrics

### Memory Retrieval Metrics

```yaml
# Histogram: Retrieval latency distribution
- name: mind_retrieval_latency_seconds
  type: histogram
  description: "End-to-end memory retrieval latency"
  labels:
    - user_id_hash    # Hashed for privacy
    - temporal_level  # immediate, situational, seasonal, identity
    - retrieval_type  # vector, graph, keyword, fusion
  buckets: [0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0]

# Counter: Total retrieval requests
- name: mind_retrieval_requests_total
  type: counter
  description: "Total memory retrieval requests"
  labels:
    - status        # success, error, timeout
    - error_code    # MEMORY_NOT_FOUND, DATABASE_ERROR, etc.

# Gauge: Current retrieval queue depth
- name: mind_retrieval_queue_depth
  type: gauge
  description: "Current pending retrieval requests"
  labels:
    - priority      # high, normal, low

# Histogram: Memories returned per request
- name: mind_retrieval_results_count
  type: histogram
  description: "Number of memories returned per retrieval"
  buckets: [0, 1, 5, 10, 25, 50, 100]

# Histogram: Effective salience distribution
- name: mind_memory_salience_distribution
  type: histogram
  description: "Distribution of effective salience scores"
  labels:
    - temporal_level
  buckets: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
```

### Event Processing Metrics

```yaml
# Counter: Events processed
- name: mind_events_processed_total
  type: counter
  description: "Total events processed by type"
  labels:
    - event_type    # InteractionRecorded, MemoryExtracted, etc.
    - status        # success, error, dropped
    - consumer_id   # Which consumer processed

# Histogram: Event processing latency
- name: mind_event_processing_latency_seconds
  type: histogram
  description: "Time from event publish to consumer ACK"
  labels:
    - event_type
    - consumer_id
  buckets: [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]

# Gauge: Consumer lag
- name: mind_nats_consumer_lag
  type: gauge
  description: "Number of unprocessed messages per consumer"
  labels:
    - stream_name
    - consumer_name

# Counter: Event publishing errors
- name: mind_event_publish_errors_total
  type: counter
  description: "Failed event publications"
  labels:
    - event_type
    - error_type    # timeout, nack, connection_lost

# Gauge: NATS JetStream stream stats
- name: mind_nats_stream_messages
  type: gauge
  description: "Current messages in stream"
  labels:
    - stream_name
```

### API Metrics

```yaml
# Counter: Total API requests
- name: mind_api_requests_total
  type: counter
  description: "Total API requests by endpoint and status"
  labels:
    - method        # GET, POST, etc.
    - endpoint      # /v1/memory/retrieve, etc.
    - status_code   # 200, 400, 500, etc.
    - grpc_code     # OK, INVALID_ARGUMENT, etc. (for gRPC)

# Histogram: API request latency
- name: mind_api_latency_seconds
  type: histogram
  description: "API request latency distribution"
  labels:
    - method
    - endpoint
  buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]

# Gauge: Active connections
- name: mind_api_active_connections
  type: gauge
  description: "Current active API connections"
  labels:
    - protocol      # http, grpc

# Counter: Rate limit hits
- name: mind_api_rate_limit_total
  type: counter
  description: "Requests rejected by rate limiter"
  labels:
    - endpoint
    - limit_type    # per_user, per_ip, global
```

### Decision Tracking Metrics

```yaml
# Counter: Decisions recorded
- name: mind_decisions_recorded_total
  type: counter
  description: "Total decisions recorded"
  labels:
    - decision_type
    - status        # success, error

# Histogram: Decision recording latency
- name: mind_decision_recording_latency_seconds
  type: histogram
  description: "Time to record decision trace"
  buckets: [0.005, 0.01, 0.02, 0.05, 0.1, 0.2]

# Gauge: Pending outcome attributions
- name: mind_outcomes_pending
  type: gauge
  description: "Decisions awaiting outcome feedback"

# Counter: Outcomes recorded
- name: mind_outcomes_recorded_total
  type: counter
  description: "Total outcomes recorded"
  labels:
    - outcome_quality  # positive, negative, neutral
    - outcome_signal   # explicit, implicit, inferred

# Gauge: Decision Success Rate (DSR)
- name: mind_decision_success_rate
  type: gauge
  description: "Rolling decision success rate"
  labels:
    - cohort        # new_users, power_users, etc.
    - time_window   # 24h, 7d, 30d
```

### SLO-Specific Metrics

```yaml
# Gauge: SLO burn rate
- name: mind_slo_burn_rate
  type: gauge
  description: "Current error budget burn rate"
  labels:
    - slo_name      # retrieval, events, decisions, api
    - window        # 1h, 6h, 24h

# Gauge: Error budget remaining
- name: mind_error_budget_remaining
  type: gauge
  description: "Remaining error budget as percentage"
  labels:
    - slo_name
    - period        # current_month, rolling_30d

# Counter: SLO violations
- name: mind_slo_violations_total
  type: counter
  description: "Total SLO violation events"
  labels:
    - slo_name
    - violation_type  # availability, latency, throughput
```

---

## Alerting Rules

### Burn Rate Alert Strategy

Multi-window, multi-burn-rate alerting provides both fast detection of severe incidents and reliable detection of slower budget consumption.

```
Alert Windows:
  - 5 minute window:  Detects 144x burn rate (budget gone in 5 hours)
  - 1 hour window:    Detects 14.4x burn rate (budget gone in 2 days)
  - 6 hour window:    Detects 6x burn rate (budget gone in 5 days)
  - 24 hour window:   Detects 1x burn rate (budget gone in 30 days)
```

### Memory Retrieval Alerts

```yaml
# Critical: Fast burn (2% budget in 1 hour)
- alert: MemoryRetrievalBurnRateCritical
  expr: |
    (
      sum(rate(mind_retrieval_requests_total{status="error"}[5m]))
      /
      sum(rate(mind_retrieval_requests_total[5m]))
    ) > (14.4 * 0.001)
    AND
    (
      sum(rate(mind_retrieval_requests_total{status="error"}[1h]))
      /
      sum(rate(mind_retrieval_requests_total[1h]))
    ) > (14.4 * 0.001)
  for: 2m
  labels:
    severity: critical
    slo: memory_retrieval
    runbook: "docs/runbooks/MEMORY_RETRIEVAL_BURN_RATE.md"
  annotations:
    summary: "Memory retrieval burning error budget at 14x rate"
    description: "Error rate {{ $value | humanizePercentage }} will exhaust monthly budget in ~2 days"
    action: "Check Qdrant cluster health, FalkorDB connectivity, recent deployments"

# High: Moderate burn (5% budget in 6 hours)
- alert: MemoryRetrievalBurnRateHigh
  expr: |
    (
      sum(rate(mind_retrieval_requests_total{status="error"}[30m]))
      /
      sum(rate(mind_retrieval_requests_total[30m]))
    ) > (6 * 0.001)
    AND
    (
      sum(rate(mind_retrieval_requests_total{status="error"}[6h]))
      /
      sum(rate(mind_retrieval_requests_total[6h]))
    ) > (6 * 0.001)
  for: 15m
  labels:
    severity: high
    slo: memory_retrieval
    runbook: "docs/runbooks/MEMORY_RETRIEVAL_BURN_RATE.md"
  annotations:
    summary: "Memory retrieval burning error budget at 6x rate"
    description: "Error rate {{ $value | humanizePercentage }} will exhaust monthly budget in ~5 days"

# Warning: Slow burn (10% budget in 24 hours)
- alert: MemoryRetrievalBurnRateWarning
  expr: |
    (
      sum(rate(mind_retrieval_requests_total{status="error"}[2h]))
      /
      sum(rate(mind_retrieval_requests_total[2h]))
    ) > (3 * 0.001)
    AND
    (
      sum(rate(mind_retrieval_requests_total{status="error"}[24h]))
      /
      sum(rate(mind_retrieval_requests_total[24h]))
    ) > (1 * 0.001)
  for: 1h
  labels:
    severity: warning
    slo: memory_retrieval
    runbook: "docs/runbooks/MEMORY_RETRIEVAL_BURN_RATE.md"
  annotations:
    summary: "Memory retrieval error budget being consumed"
    description: "Sustained error rate may exhaust monthly budget"

# Latency breach
- alert: MemoryRetrievalLatencyBreach
  expr: |
    histogram_quantile(0.99,
      sum(rate(mind_retrieval_latency_seconds_bucket[5m])) by (le)
    ) > 0.2
  for: 5m
  labels:
    severity: high
    slo: memory_retrieval
    runbook: "docs/runbooks/MEMORY_RETRIEVAL_LATENCY.md"
  annotations:
    summary: "Memory retrieval p99 latency exceeds 200ms SLO"
    description: "Current p99: {{ $value | humanizeDuration }}"
```

### Event Processing Alerts

```yaml
# Critical: Consumer lag spike
- alert: EventProcessingLagCritical
  expr: mind_nats_consumer_lag > 10000
  for: 2m
  labels:
    severity: critical
    slo: event_processing
    runbook: "docs/runbooks/NATS_CONSUMER_LAG.md"
  annotations:
    summary: "NATS consumer lag exceeds 10,000 messages"
    description: "Consumer {{ $labels.consumer_name }} has {{ $value }} messages pending"
    action: "Scale consumers, check for slow handlers, verify NATS cluster health"

# High: Consumer lag warning
- alert: EventProcessingLagHigh
  expr: mind_nats_consumer_lag > 1000
  for: 10m
  labels:
    severity: high
    slo: event_processing
    runbook: "docs/runbooks/NATS_CONSUMER_LAG.md"
  annotations:
    summary: "NATS consumer lag exceeds 1,000 messages"
    description: "Consumer {{ $labels.consumer_name }} falling behind"

# Critical: Event processing errors
- alert: EventProcessingErrorRateCritical
  expr: |
    (
      sum(rate(mind_events_processed_total{status="error"}[5m]))
      /
      sum(rate(mind_events_processed_total[5m]))
    ) > 0.01
  for: 2m
  labels:
    severity: critical
    slo: event_processing
    runbook: "docs/runbooks/EVENT_PROCESSING_ERRORS.md"
  annotations:
    summary: "Event processing error rate exceeds 1%"
    description: "{{ $value | humanizePercentage }} of events failing"

# High: Processing latency
- alert: EventProcessingLatencyHigh
  expr: |
    histogram_quantile(0.99,
      sum(rate(mind_event_processing_latency_seconds_bucket[5m])) by (le)
    ) > 0.1
  for: 5m
  labels:
    severity: high
    slo: event_processing
    runbook: "docs/runbooks/EVENT_PROCESSING_LATENCY.md"
  annotations:
    summary: "Event processing p99 latency exceeds 100ms"
    description: "Current p99: {{ $value | humanizeDuration }}"
```

### API Availability Alerts

```yaml
# Critical: API availability burn rate
- alert: APIAvailabilityBurnRateCritical
  expr: |
    (
      sum(rate(mind_api_requests_total{status_code=~"5.."}[5m]))
      /
      sum(rate(mind_api_requests_total[5m]))
    ) > (14.4 * 0.001)
    AND
    (
      sum(rate(mind_api_requests_total{status_code=~"5.."}[1h]))
      /
      sum(rate(mind_api_requests_total[1h]))
    ) > (14.4 * 0.001)
  for: 2m
  labels:
    severity: critical
    slo: api_availability
    runbook: "docs/runbooks/API_AVAILABILITY.md"
  annotations:
    summary: "API availability SLO at risk - fast error budget burn"
    description: "5xx rate {{ $value | humanizePercentage }} consuming budget rapidly"
    action: "Check recent deployments, database connectivity, upstream dependencies"

# High: Elevated 5xx rate
- alert: APIErrorRateHigh
  expr: |
    (
      sum(rate(mind_api_requests_total{status_code=~"5.."}[5m]))
      /
      sum(rate(mind_api_requests_total[5m]))
    ) > 0.005
  for: 5m
  labels:
    severity: high
    slo: api_availability
    runbook: "docs/runbooks/API_5XX_ERRORS.md"
  annotations:
    summary: "API 5xx error rate elevated"
    description: "Current rate: {{ $value | humanizePercentage }}"

# High: API latency breach
- alert: APILatencyBreach
  expr: |
    histogram_quantile(0.99,
      sum(rate(mind_api_latency_seconds_bucket[5m])) by (le, endpoint)
    ) > 1.0
  for: 5m
  labels:
    severity: high
    slo: api_availability
    runbook: "docs/runbooks/API_LATENCY.md"
  annotations:
    summary: "API p99 latency exceeds 1 second"
    description: "Endpoint {{ $labels.endpoint }} p99: {{ $value | humanizeDuration }}"
```

### Decision Tracking Alerts

```yaml
# Critical: Decision recording failures
- alert: DecisionRecordingFailureCritical
  expr: |
    (
      sum(rate(mind_decisions_recorded_total{status="error"}[5m]))
      /
      sum(rate(mind_decisions_recorded_total[5m]))
    ) > 0.005
  for: 5m
  labels:
    severity: critical
    slo: decision_tracking
    runbook: "docs/runbooks/DECISION_RECORDING.md"
  annotations:
    summary: "Decision recording failure rate exceeds 0.5%"
    description: "{{ $value | humanizePercentage }} of decisions failing to record"
    action: "Check PostgreSQL connectivity, trace table constraints"

# Warning: Pending outcomes growing
- alert: OutcomeBacklogGrowing
  expr: |
    delta(mind_outcomes_pending[1h]) > 10000
  for: 30m
  labels:
    severity: warning
    slo: decision_tracking
    runbook: "docs/runbooks/OUTCOME_BACKLOG.md"
  annotations:
    summary: "Pending outcome attributions growing rapidly"
    description: "Backlog increased by {{ $value }} in last hour"

# High: Decision latency breach
- alert: DecisionRecordingLatencyHigh
  expr: |
    histogram_quantile(0.99,
      sum(rate(mind_decision_recording_latency_seconds_bucket[5m])) by (le)
    ) > 0.1
  for: 5m
  labels:
    severity: high
    slo: decision_tracking
    runbook: "docs/runbooks/DECISION_LATENCY.md"
  annotations:
    summary: "Decision recording p99 latency exceeds 100ms"
    description: "Current p99: {{ $value | humanizeDuration }}"
```

### Infrastructure Alerts

```yaml
# Critical: Database connection pool exhaustion
- alert: PostgresConnectionPoolExhausted
  expr: mind_postgres_connections_active / mind_postgres_connections_max > 0.9
  for: 2m
  labels:
    severity: critical
    component: postgres
    runbook: "docs/runbooks/POSTGRES_CONNECTIONS.md"
  annotations:
    summary: "PostgreSQL connection pool near exhaustion"
    description: "{{ $value | humanizePercentage }} of connections in use"

# Critical: Qdrant cluster unhealthy
- alert: QdrantClusterUnhealthy
  expr: mind_qdrant_cluster_status != 1
  for: 1m
  labels:
    severity: critical
    component: qdrant
    runbook: "docs/runbooks/QDRANT_CLUSTER.md"
  annotations:
    summary: "Qdrant cluster in unhealthy state"
    action: "Check Qdrant node status, disk space, memory pressure"

# Critical: FalkorDB connection errors
- alert: FalkorDBConnectionErrors
  expr: rate(mind_falkordb_connection_errors_total[5m]) > 0.1
  for: 2m
  labels:
    severity: critical
    component: falkordb
    runbook: "docs/runbooks/FALKORDB_CONNECTIVITY.md"
  annotations:
    summary: "FalkorDB connection errors detected"
    description: "{{ $value }} errors/sec"

# High: Temporal workflow failures
- alert: TemporalWorkflowFailures
  expr: |
    (
      sum(rate(temporal_workflow_completed_total{status="failed"}[1h]))
      /
      sum(rate(temporal_workflow_completed_total[1h]))
    ) > 0.01
  for: 30m
  labels:
    severity: high
    component: temporal
    runbook: "docs/runbooks/TEMPORAL_WORKFLOWS.md"
  annotations:
    summary: "Temporal workflow failure rate elevated"
    description: "{{ $value | humanizePercentage }} of workflows failing"
```

### Alert Routing Configuration

```yaml
# Alertmanager configuration
route:
  receiver: 'default'
  group_by: ['alertname', 'slo']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty-critical'
      continue: true
    - match:
        severity: high
      receiver: 'slack-high'
      continue: true
    - match:
        severity: warning
      receiver: 'slack-warning'

receivers:
  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: '<PAGERDUTY_SERVICE_KEY>'
        severity: critical
        description: '{{ .CommonAnnotations.summary }}'
        details:
          action: '{{ .CommonAnnotations.action }}'
          runbook: '{{ .CommonLabels.runbook }}'

  - name: 'slack-high'
    slack_configs:
      - channel: '#mind-sre-alerts'
        title: '{{ .CommonAnnotations.summary }}'
        text: '{{ .CommonAnnotations.description }}'
        actions:
          - type: button
            text: 'Runbook'
            url: '{{ .CommonLabels.runbook }}'

  - name: 'slack-warning'
    slack_configs:
      - channel: '#mind-sre-warnings'
        title: '{{ .CommonAnnotations.summary }}'
        text: '{{ .CommonAnnotations.description }}'

  - name: 'default'
    slack_configs:
      - channel: '#mind-sre-info'
```

---

## Dashboard Specifications

### Dashboard 1: Mind v5 Overview

**Purpose**: Executive-level view of system health and SLO status

**Panels**:

| Panel | Type | Query | Purpose |
|-------|------|-------|---------|
| SLO Status Grid | Stat | `mind_error_budget_remaining` | Show all SLOs at a glance |
| Error Budget Burn | Time series | `mind_slo_burn_rate{window="1h"}` | Track budget consumption |
| Active Incidents | Stat | `ALERTS{alertstate="firing"}` | Count of firing alerts |
| Request Rate | Time series | `sum(rate(mind_api_requests_total[5m]))` | Overall traffic |
| Success Rate | Gauge | `1 - (error_rate)` | Current success percentage |
| p99 Latency | Time series | `histogram_quantile(0.99, ...)` | End-to-end latency |

**Refresh**: 30 seconds
**Time Range**: Last 6 hours (default), selectable

---

### Dashboard 2: Memory Retrieval Performance

**Purpose**: Deep dive into memory retrieval pipeline

**Panels**:

| Panel | Type | Query | Purpose |
|-------|------|-------|---------|
| Retrieval Latency Heatmap | Heatmap | `mind_retrieval_latency_seconds_bucket` | Latency distribution over time |
| p50/p95/p99 Latency | Time series | Multiple quantiles | Track latency percentiles |
| Request Rate by Status | Time series | `rate(mind_retrieval_requests_total)` by status | Success vs error |
| Retrieval by Temporal Level | Bar chart | Count by temporal_level | Which levels queried |
| Fusion Pipeline Breakdown | Stacked | Latency by retrieval_type | Vector vs graph vs keyword |
| Result Count Distribution | Histogram | `mind_retrieval_results_count` | How many memories returned |
| Salience Score Distribution | Histogram | `mind_memory_salience_distribution` | Quality of retrieved memories |
| Cache Hit Rate | Gauge | Cache hits / total | Caching effectiveness |

**Refresh**: 15 seconds
**Time Range**: Last 1 hour (default)

---

### Dashboard 3: Event Processing Pipeline

**Purpose**: NATS JetStream and event projector health

**Panels**:

| Panel | Type | Query | Purpose |
|-------|------|-------|---------|
| Events/Second | Time series | `sum(rate(mind_events_processed_total[1m]))` | Throughput |
| Consumer Lag | Time series | `mind_nats_consumer_lag` by consumer | Backlog per consumer |
| Processing Latency | Heatmap | `mind_event_processing_latency_seconds_bucket` | Latency distribution |
| Events by Type | Pie chart | Count by event_type | Event type breakdown |
| Error Rate | Time series | Error events / total | Processing errors |
| Stream Size | Time series | `mind_nats_stream_messages` | Messages in stream |
| Oldest Unacked | Stat | Age of oldest pending | Processing delay |
| Consumer Status | Table | Consumer health checks | Consumer by consumer |

**Refresh**: 10 seconds
**Time Range**: Last 30 minutes (default)

---

### Dashboard 4: Decision Outcome Tracking

**Purpose**: Decision quality and outcome attribution

**Panels**:

| Panel | Type | Query | Purpose |
|-------|------|-------|---------|
| Decision Success Rate | Gauge | `mind_decision_success_rate` | Overall DSR |
| DSR Trend | Time series | DSR over time windows | Improvement tracking |
| Outcomes by Quality | Pie chart | positive/negative/neutral | Outcome distribution |
| Pending Outcomes | Stat | `mind_outcomes_pending` | Backlog |
| Attribution Latency | Time series | Time to attribute | Processing speed |
| Memory Effectiveness | Table | Top memories by positive outcomes | Which memories help |
| Decision Recording Rate | Time series | `rate(mind_decisions_recorded_total)` | Volume |
| Recording Latency | Time series | p50/p95/p99 | Recording performance |

**Refresh**: 1 minute
**Time Range**: Last 24 hours (default)

---

### Dashboard 5: Gardener Workflow Status

**Purpose**: Temporal.io workflow monitoring

**Panels**:

| Panel | Type | Query | Purpose |
|-------|------|-------|---------|
| Active Workflows | Stat | Count by workflow type | Running workflows |
| Workflow Success Rate | Gauge | Success / total | Reliability |
| Workflow Duration | Heatmap | Duration by type | Performance |
| Activity Success Rate | Table | By activity name | Activity reliability |
| Failed Workflows | Table | Recent failures with details | Troubleshooting |
| Workflow Queue Depth | Time series | Pending per task queue | Backlog |
| Worker Utilization | Gauge | Active / capacity | Worker health |
| Schedule Status | Table | Cron schedules with next run | Scheduled tasks |

**Refresh**: 1 minute
**Time Range**: Last 24 hours (default)

---

### Dashboard 6: Causal Discovery Progress

**Purpose**: Causal inference engine monitoring

**Panels**:

| Panel | Type | Query | Purpose |
|-------|------|-------|---------|
| Causal Edges Discovered | Counter | Total edges in graph | Growth |
| Edge Confidence Distribution | Histogram | Confidence scores | Quality |
| Query Latency | Time series | p50/p95/p99 | Performance |
| Graph Traversal Depth | Histogram | Hops per query | Complexity |
| DoWhy Pipeline Success | Gauge | Successful inferences | Reliability |
| Edge Types | Pie chart | causes/correlates/prevents | Relationship types |
| Temporal Validity | Table | Edges by validity period | Currency |
| Counterfactual Queries | Time series | Rate over time | Usage |

**Refresh**: 5 minutes
**Time Range**: Last 7 days (default)

---

### Dashboard 7: Infrastructure Health

**Purpose**: Underlying infrastructure monitoring

**Panels**:

| Panel | Type | Query | Purpose |
|-------|------|-------|---------|
| PostgreSQL Connections | Time series | Active/idle/max | Connection pool |
| PostgreSQL Query Latency | Heatmap | Query duration | DB performance |
| Qdrant Memory Usage | Time series | Used/available | Vector DB capacity |
| Qdrant Segment Count | Stat | Segments per collection | Index health |
| FalkorDB Memory | Time series | Memory usage | Graph DB capacity |
| FalkorDB Query Latency | Time series | p50/p95/p99 | Graph performance |
| NATS Memory | Time series | JetStream memory | Event backbone |
| NATS Disk Usage | Time series | Stream storage | Persistence |

**Refresh**: 30 seconds
**Time Range**: Last 6 hours (default)

---

## On-Call Runbook References

### Runbook Structure

All runbooks follow a consistent structure stored in `docs/runbooks/`:

```
docs/runbooks/
├── MEMORY_RETRIEVAL_BURN_RATE.md
├── MEMORY_RETRIEVAL_LATENCY.md
├── NATS_CONSUMER_LAG.md
├── EVENT_PROCESSING_ERRORS.md
├── EVENT_PROCESSING_LATENCY.md
├── API_AVAILABILITY.md
├── API_5XX_ERRORS.md
├── API_LATENCY.md
├── DECISION_RECORDING.md
├── OUTCOME_BACKLOG.md
├── DECISION_LATENCY.md
├── POSTGRES_CONNECTIONS.md
├── QDRANT_CLUSTER.md
├── FALKORDB_CONNECTIVITY.md
├── TEMPORAL_WORKFLOWS.md
└── INCIDENT_RESPONSE_TEMPLATE.md
```

### Runbook Template

Each runbook contains:

```markdown
# [Alert Name] Runbook

## Alert Details
- **Severity**: [critical/high/warning]
- **SLO Impacted**: [SLO name]
- **Expected Response Time**: [5m/15m/1h]

## Symptoms
- [What the user experiences]
- [What metrics show]

## Likely Causes
1. [Most common cause]
2. [Second most common]
3. [Third most common]

## Diagnostic Steps
1. Check [specific dashboard/metric]
2. Run [diagnostic command]
3. Verify [component status]

## Remediation Steps

### For Cause 1:
```bash
# Commands to fix
```

### For Cause 2:
```bash
# Commands to fix
```

## Escalation
- **After 15 minutes**: Notify [team/person]
- **After 30 minutes**: Page [escalation path]
- **After 1 hour**: Incident commander required

## Post-Incident
- [ ] Create incident report
- [ ] Update runbook with new learnings
- [ ] File follow-up tickets
```

### Critical Runbook Quick Reference

| Alert | First Check | Common Fix | Escalate After |
|-------|-------------|------------|----------------|
| MemoryRetrievalBurnRateCritical | Qdrant dashboard | Restart Qdrant pods | 15 min |
| EventProcessingLagCritical | NATS consumer lag panel | Scale consumers | 10 min |
| APIAvailabilityBurnRateCritical | Recent deployments | Rollback | 5 min |
| PostgresConnectionPoolExhausted | Active connections | Kill idle connections | 10 min |
| QdrantClusterUnhealthy | Qdrant node status | Node restart | 5 min |
| FalkorDBConnectionErrors | FalkorDB logs | Restart FalkorDB | 10 min |
| TemporalWorkflowFailures | Workflow history | Fix + retry | 30 min |

---

## Appendix: SLO Calculation Examples

### Error Budget Consumption Example

```
Monthly SLO Target: 99.9% availability
Monthly Error Budget: 0.1% = 43.2 minutes

Week 1:
  - Incident A: 5 minutes downtime
  - Budget consumed: 5/43.2 = 11.6%
  - Budget remaining: 88.4%

Week 2:
  - Incident B: 10 minutes downtime
  - Additional consumed: 10/43.2 = 23.1%
  - Budget remaining: 65.3%

Week 3:
  - No incidents
  - Budget remaining: 65.3%

Week 4:
  - Incident C: 15 minutes downtime
  - Additional consumed: 15/43.2 = 34.7%
  - Budget remaining: 30.6%

Status: WARNING (< 50% remaining)
Action: Review reliability, defer risky changes
```

### Burn Rate Calculation Example

```
SLO: 99.9% availability
Error budget rate: 0.1% per 30 days = 0.0033% per day

Current error rate (measured over 1 hour): 0.05%

Burn rate = Current rate / Budget rate
         = 0.05% / 0.0033%
         = 15.15x

At this burn rate:
  - Daily budget consumed: 15.15 days worth
  - Time to exhaust monthly budget: 30/15.15 = 1.98 days

Alert level: CRITICAL (> 14.4x burn rate)
```

---

*Document Version: 1.0*
*Created: December 27, 2025*
*Last Updated: December 27, 2025*
*Next Review: January 27, 2026*
