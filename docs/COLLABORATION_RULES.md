# Mind v5 Collaboration Rules

> **Purpose**: Explicit rules for how 20 agents collaborate
> **Enforcement**: All agents must follow these rules

---

## Rule 1: Domain Sovereignty

```yaml
rule: domain_sovereignty
principle: "The expert leads in their domain"

enforcement:
  - When a question is clearly in one agent's domain, that agent decides
  - Other agents provide input but don't override
  - Domain owner can veto suggestions that violate domain constraints

examples:
  correct:
    - postgres-wizard decides on index strategy
    - privacy-guardian decides on encryption approach
    - api-designer decides on endpoint naming
  
  incorrect:
    - performance-hunter overriding postgres-wizard on query structure
    - Any agent approving security changes without privacy-guardian
```

---

## Rule 2: Mandatory Consultation Matrix

```yaml
rule: mandatory_consultation
principle: "Some changes require specific expert sign-off"

matrix:
  database_schema:
    required: [postgres-wizard, migration-specialist]
    recommended: [data-engineer]
    
  api_changes:
    required: [api-designer]
    recommended: [sdk-builder, docs-engineer]
    
  security_sensitive:
    required: [privacy-guardian]
    blocking: true  # Cannot proceed without approval
    
  event_schema:
    required: [event-architect]
    recommended: [data-engineer]
    
  workflow_changes:
    required: [temporal-craftsman]
    recommended: [observability-sre]
    
  graph_schema:
    required: [graph-engineer]
    recommended: [causal-scientist]
    
  vector_operations:
    required: [vector-specialist]
    recommended: [performance-hunter]
    
  infrastructure:
    required: [infra-architect]
    recommended: [observability-sre, chaos-engineer]
    
  performance_critical:
    required: [performance-hunter]
    recommended: [domain_owner]

enforcement:
  - PRs tagged with change type
  - CI checks for required reviewers
  - Merge blocked until approvals received
```

---

## Rule 3: The 30-Minute Rule

```yaml
rule: thirty_minute_rule
principle: "Don't spin alone"

process:
  - Work on problem independently for max 30 minutes
  - If stuck, MUST consult relevant specialist
  - If specialist unavailable, broadcast to pod
  - If pod can't help, escalate to full team

anti_patterns:
  - Spending 2 hours stuck without asking
  - Asking without attempting first
  - Asking the wrong specialist repeatedly

tracking:
  - Time-to-consultation metric
  - Resolution rate after consultation
```

---

## Rule 4: Complete Handoffs

```yaml
rule: complete_handoffs
principle: "Never hand off without context"

required_fields:
  - task_summary: What needs to be done
  - work_completed: What's already done
  - decisions_made: With rationale
  - files_modified: What was touched
  - open_questions: Unresolved items

recommended_fields:
  - suggested_approach: How you'd continue
  - watch_out_for: Known risks/issues
  - related_resources: Helpful links

forbidden:
  - "Here's the code, figure it out"
  - Handoffs without decisions explained
  - Partial context that requires guessing

enforcement:
  - Handoff template required
  - Receiving agent can reject incomplete handoffs
```

---

## Rule 5: Review Requirements

```yaml
rule: review_requirements
principle: "Every change gets appropriate eyes"

by_change_type:
  
  trivial:  # Typos, formatting, comments
    reviewers: 1
    who: any
    turnaround: 4 hours
    
  standard:  # Normal features, bug fixes
    reviewers: 2
    who: [code-reviewer, domain_expert]
    turnaround: 24 hours
    
  significant:  # Architecture, API, schema
    reviewers: 3
    who: [code-reviewer, domain_expert, affected_specialist]
    turnaround: 48 hours
    
  critical:  # Security, core infrastructure
    reviewers: 4
    who: [code-reviewer, domain_expert, privacy-guardian, infra-architect]
    turnaround: 48 hours
    blocking: true

review_expectations:
  - Substantive feedback, not just "LGTM"
  - Specific line comments for issues
  - Approval only when satisfied
  - Re-review after significant changes
```

---

## Rule 6: Communication Protocols

```yaml
rule: communication_protocols
principle: "Right message, right channel, right time"

channels:
  
  task_thread:
    use_for: Discussion about specific task
    participants: Assigned agents
    
  pod_channel:
    use_for: Pod-level coordination
    participants: Pod members
    
  team_broadcast:
    use_for: Team-wide announcements
    participants: All agents
    requires: Significant impact
    
  incident_channel:
    use_for: Production issues only
    participants: Responders + relevant experts
    
  learning_channel:
    use_for: Knowledge sharing
    participants: All agents

message_format:
  - Start with intent: [INFO], [QUESTION], [DECISION], [BLOCKER]
  - Include context sufficient to understand without prior thread
  - Tag relevant agents explicitly
  - End with clear ask (if any)

example:
  bad: "This doesn't work"
  good: "[QUESTION] @postgres-wizard: Query in memory_retrieval.py:45 
         returns 0 rows when I expect data. Checked: table has data,
         index exists, WHERE clause matches. What am I missing?"
```

---

## Rule 7: Decision Documentation

```yaml
rule: decision_documentation
principle: "Decisions outlive discussions"

requires_adr:
  - Technology choices
  - Architecture patterns
  - API design decisions
  - Security approaches
  - Data model changes

adr_format:
  - Status: Proposed | Accepted | Deprecated | Superseded
  - Context: Why are we making this decision?
  - Decision: What did we decide?
  - Rationale: Why this over alternatives?
  - Consequences: Positive, negative, neutral

lightweight_documentation:
  - In-code comments for implementation decisions
  - PR descriptions for tactical decisions
  - CHANGELOG for user-visible changes

anti_patterns:
  - Verbal decisions not written down
  - Decisions in Slack/chat without ADR
  - "We decided this before" without reference
```

---

## Rule 8: Quality Gate Enforcement

```yaml
rule: quality_gates
principle: "Gates protect production"

gates:
  
  code_quality:
    owner: code-reviewer
    blocking: true
    checks:
      - Follows CLAUDE.md
      - Types complete
      - No obvious bugs
      
  tests:
    owner: test-architect
    blocking: true
    checks:
      - Unit tests pass
      - Integration tests pass
      - Coverage threshold met
      
  security:
    owner: privacy-guardian
    blocking: true
    checks:
      - No secrets in code
      - No PII in logs
      - Input validation
      
  performance:
    owner: performance-hunter
    blocking_for: [hot_path, data_intensive]
    checks:
      - No N+1 queries
      - Benchmarks pass
      
  documentation:
    owner: docs-engineer
    blocking_for: [new_feature, api_change]
    checks:
      - Docstrings present
      - API docs updated

override_process:
  - Only for emergencies
  - Requires 2 agent approval
  - Must create follow-up task
  - Documented in incident log
```

---

## Rule 9: Incident Response

```yaml
rule: incident_response
principle: "Structured response saves time"

severity_levels:
  
  P1_critical:
    definition: "Production down or data at risk"
    response_time: immediate
    responders: All relevant specialists
    communication: Continuous updates
    
  P2_high:
    definition: "Significant degradation"
    response_time: 15 minutes
    responders: Primary specialist + SRE
    communication: Hourly updates
    
  P3_medium:
    definition: "Partial impact"
    response_time: 1 hour
    responders: Primary specialist
    communication: Daily updates
    
  P4_low:
    definition: "Minor issue"
    response_time: Next business day
    responders: Assigned owner
    communication: On resolution

roles:
  incident_commander:
    responsibility: Coordinate response
    usually: observability-sre or domain owner
    
  investigator:
    responsibility: Find root cause
    usually: Domain specialist
    
  communicator:
    responsibility: Keep team informed
    usually: Incident commander

post_incident:
  required:
    - Incident report within 48 hours
    - Root cause identified
    - Follow-up tasks created
  recommended:
    - Blameless postmortem
    - Skill updates from learnings
    - Chaos test for failure mode
```

---

## Rule 10: Knowledge Sharing

```yaml
rule: knowledge_sharing
principle: "The team learns together"

triggers:
  - Bug found that wasn't obvious
  - Pattern discovered that others should know
  - Sharp edge encountered in a tool
  - Better approach found for common task
  - Mistake made that others could make

sharing_format:
  what_happened: Brief description
  why_it_matters: Impact/importance
  the_learning: What to know/do differently
  where_to_document: Skill file / ADR / code comment

destinations:
  - Relevant SKILL.md file for domain knowledge
  - CLAUDE.md for team-wide patterns
  - ADR for architectural learnings
  - Code comments for implementation details

frequency:
  minimum: 1 learning shared per week per active agent
  tracked: In retrospectives
```

---

## Rule 11: Conflict Resolution

```yaml
rule: conflict_resolution
principle: "Disagree, commit, and document"

escalation_ladder:
  
  level_1_domain:
    situation: Disagreement within one domain
    resolution: Domain expert decides
    timeframe: Immediate
    
  level_2_discussion:
    situation: Cross-domain disagreement
    resolution: Affected specialists discuss
    timeframe: 4 hours
    goal: Find solution satisfying all constraints
    
  level_3_principles:
    situation: Discussion doesn't resolve
    resolution: Refer to CLAUDE.md principles
    timeframe: 8 hours
    rule: Most principle-aligned option wins
    
  level_4_user_impact:
    situation: Principles don't clearly resolve
    resolution: Choose best for end user
    timeframe: 24 hours
    
  level_5_document:
    situation: Still unresolved
    resolution: Document both options, make decision, write ADR
    timeframe: 48 hours
    rule: Decision is final until new information

rules:
  - Once decided, all agents commit to the decision
  - Disagree openly during discussion
  - Support fully after decision
  - Revisit only with new information
```

---

## Rule 12: Async-First Communication

```yaml
rule: async_first
principle: "Respect focus time"

preferences:
  1. Written documentation (permanent)
  2. Async messages (reviewed when available)
  3. Scheduled discussions (for complex topics)
  4. Real-time only for incidents

guidelines:
  - Default to async
  - Include all context in first message
  - Don't expect immediate response
  - Use @mentions for urgency
  - Batch related questions

exceptions:
  - Active incidents (real-time)
  - Blocking issues after 4 hours (escalate)
  - Time-sensitive decisions (schedule sync)

expectations:
  - Acknowledge messages within 4 hours
  - Respond substantively within 24 hours
  - If delayed, communicate timeline
```

---

## Rule 13: Code Ownership

```yaml
rule: code_ownership
principle: "Clear ownership, shared responsibility"

ownership_model:
  primary_owner:
    - First reviewer for changes
    - Responsible for health of area
    - Makes tie-breaking decisions
    
  secondary_owners:
    - Can approve changes
    - Share maintenance burden
    - Backup when primary unavailable
    
  contributors:
    - Can modify with review
    - Follow area conventions
    - Defer to owners on disputes

ownership_map:
  src/core/events/: event-architect
  src/core/memory/: ml-memory
  src/core/causal/: causal-scientist
  src/core/decision/: ml-memory + causal-scientist
  src/infrastructure/postgres/: postgres-wizard
  src/infrastructure/qdrant/: vector-specialist
  src/infrastructure/falkordb/: graph-engineer
  src/infrastructure/nats/: event-architect
  src/infrastructure/temporal/: temporal-craftsman
  src/api/: api-designer
  src/workers/: temporal-craftsman
  deploy/: infra-architect
  tests/: test-architect
  docs/: docs-engineer

rotation:
  - Ownership can transfer with handoff
  - Document ownership changes
  - Minimum 1 month ownership for stability
```

---

## Rule 14: Technical Debt

```yaml
rule: technical_debt
principle: "Track it, schedule it, pay it"

identification:
  - Any agent can identify tech debt
  - Tag with [TECH_DEBT] in code comments
  - Create tracking issue immediately

classification:
  
  critical:
    definition: "Blocks important work or causes incidents"
    action: Fix in current sprint
    
  high:
    definition: "Slows development significantly"
    action: Schedule within 2 weeks
    
  medium:
    definition: "Causes friction but workable"
    action: Schedule within month
    
  low:
    definition: "Nice to fix, not urgent"
    action: Add to backlog

rules:
  - Never add tech debt without tracking issue
  - Include debt impact in PR description
  - Allocate 20% of time to debt reduction
  - Review debt backlog in retrospectives
```

---

## Rule 15: Testing Standards

```yaml
rule: testing_standards
principle: "Tests are first-class code"

requirements:
  
  unit_tests:
    coverage: ">80%"
    speed: "<1 second total"
    isolation: "No external dependencies"
    owner: Author + test-architect review
    
  integration_tests:
    coverage: "All critical paths"
    speed: "<5 minutes total"
    environment: "Containers"
    owner: Author + domain expert review
    
  e2e_tests:
    coverage: "Key user journeys"
    speed: "<15 minutes"
    environment: "Staging-like"
    owner: test-architect
    
  performance_tests:
    coverage: "Hot paths"
    frequency: "PR and nightly"
    owner: performance-hunter

rules:
  - No PR merged without tests
  - Flaky tests fixed or removed within 48 hours
  - Test failures block merge
  - New bugs require regression test
```

---

## Enforcement

These rules are enforced through:

1. **CI Checks**: Automated enforcement where possible
2. **PR Templates**: Prompt for required information
3. **Review Checklists**: Reviewers verify compliance
4. **Retrospectives**: Regular review of rule adherence
5. **Incident Reviews**: Rule violations identified and addressed

---

## Exceptions

Rules can be excepted for:
- Production emergencies (with post-fix compliance)
- Explicit team agreement (documented in ADR)
- Experimental/prototype work (clearly labeled)

Exceptions require:
- Documentation of why
- Plan to return to compliance
- Approval from relevant rule owner

---

*These rules create the structure that enables autonomy.*
