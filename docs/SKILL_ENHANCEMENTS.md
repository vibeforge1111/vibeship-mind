# Mind v5 Skill Enhancements

> **Purpose**: Specific additions for each of the 20 existing skills
> **Format**: YAML snippets to merge into existing files
> **Priority**: High-value additions based on Mind v5 architecture

---

## Enhancement Strategy

For each skill, I'm providing:
1. **Identity Additions** - Mind v5 specific context for skill.yaml
2. **Critical Sharp Edges** - Must-have gotchas for sharp-edges.yaml
3. **Key Validations** - Automated checks for validations.yaml
4. **Collaboration Links** - Cross-skill connections for collaboration.yaml

---

## 1. event-architect

### skill.yaml additions

```yaml
# Add to identity section
mind_v5_context: |
  In Mind v5, you own the event backbone that powers everything:
  - NATS JetStream for 400K msg/sec event flow
  - Event-sourced memory system (all state from events)
  - Decision trace events for outcome learning
  
  Critical events you design:
  - InteractionRecorded (raw observations)
  - MemoryExtracted (processed memories)
  - DecisionMade (with context snapshot)
  - OutcomeObserved (feedback signal)
  - CausalLinkDiscovered (new causal edge)
  - PatternValidated (ready for federation)

# Add patterns
patterns:
  - name: Decision Trace Event
    description: Capture full decision context for outcome learning
    when: Any agent makes a decision using memory
    example: |
      @dataclass(frozen=True)
      class DecisionMade:
          event_id: UUID
          event_type: str = "DecisionMade"
          correlation_id: UUID
          causation_id: UUID
          
          # Decision context
          user_id: UUID
          memory_ids: List[UUID]  # Which memories influenced
          memory_weights: Dict[str, float]  # Influence weights
          
          # The decision
          decision_type: str
          decision_content: str
          confidence: float
          alternatives_considered: List[str]
          
          occurred_at: datetime
          
  - name: Causal Link Event
    description: Record discovered causal relationships
    when: Causal inference discovers new relationship
    example: |
      @dataclass(frozen=True)
      class CausalLinkDiscovered:
          event_id: UUID
          source_entity_id: UUID
          target_entity_id: UUID
          
          causal_direction: Literal["causes", "prevents", "correlates"]
          causal_strength: float
          confidence: float
          
          conditions: List[str]
          temporal_validity: Tuple[datetime, Optional[datetime]]
          discovery_method: str  # "statistical", "expert", "observed"
          evidence_count: int
```

### sharp-edges.yaml additions

```yaml
sharp_edges:
  - id: nats-consumer-ack-timeout
    summary: NATS consumer ack timeout too short for ML workloads
    severity: high
    situation: |
      Default NATS ack timeout is 30 seconds. ML extraction can take longer.
      Consumer times out, message redelivers, duplicate processing.
    why: |
      Mind v5 uses LLM for memory extraction. Claude Haiku can take 2-5 seconds,
      but under load or for complex content, can exceed 30s.
    solution: |
      # Configure longer ack timeout for ML consumers
      consumer_config = ConsumerConfig(
          ack_wait=timedelta(minutes=2),  # 2 minutes for ML
          max_deliver=3,  # Retry limit
          
          # Use explicit ack, not auto
          ack_policy=AckPolicy.EXPLICIT,
      )
      
      # Implement heartbeat during long processing
      async def process_with_heartbeat(msg):
          async def heartbeat():
              while True:
                  await msg.in_progress()
                  await asyncio.sleep(10)
          
          task = asyncio.create_task(heartbeat())
          try:
              result = await extract_memory(msg.data)
              await msg.ack()
          finally:
              task.cancel()
    symptoms:
      - "Message processed multiple times"
      - "Duplicate memories created"
      - "Consumer lag spikes then drops"
    detection_pattern: 'ConsumerConfig\([^)]*(?!ack_wait)'

  - id: event-replay-projection-state
    summary: Projection state lost if checkpoint not atomic
    severity: critical
    situation: |
      You update projection state, then store checkpoint position.
      Crash between the two = replay processes same events again.
    why: |
      Mind v5 projections feed the memory system. Duplicate processing
      creates duplicate memories, corrupts salience scores.
    solution: |
      # Atomic projection update with checkpoint
      async def project_event(event: Event):
          async with db.transaction():
              # Update projection
              await db.execute(
                  """
                  INSERT INTO memories (...) VALUES (...)
                  ON CONFLICT (memory_id) DO NOTHING
                  """,
                  event.payload
              )
              
              # Update checkpoint in SAME transaction
              await db.execute(
                  """
                  UPDATE projection_checkpoints
                  SET position = $1, updated_at = NOW()
                  WHERE projection_name = $2
                  """,
                  event.sequence, "memory_projection"
              )
    symptoms:
      - "Memories appear twice after restart"
      - "Projection position ahead of actual state"
    detection_pattern: 'await.*ack\(\)[\s\S]{0,50}(?!transaction)'
```

### validations.yaml additions

```yaml
validations:
  - id: event-missing-causation-id
    name: Event Without Causation ID
    severity: error
    type: regex
    pattern:
      - '@dataclass.*class\s+\w+(?:Event|Recorded|Made|Observed)[\s\S]{0,500}(?!causation_id)'
    message: "Mind v5 events require causation_id for decision trace lineage."
    fix_action: "Add causation_id: UUID field linking to triggering event"
    applies_to:
      - "src/core/events/*.py"
      - "**/events.py"

  - id: nats-publish-without-await
    name: NATS Publish Without Await
    severity: error
    type: regex
    pattern:
      - 'js\.publish\([^)]+\)(?!\s*$)(?!.*await)'
      - '(?<!await\s)nc\.publish\('
    message: "NATS publish must be awaited for delivery confirmation."
    fix_action: "Add await before publish call"
    applies_to:
      - "**/*.py"

  - id: event-handler-not-idempotent
    name: Event Handler INSERT Without Idempotency
    severity: error
    type: regex
    pattern:
      - 'async def (?:on_|handle_)\w+[\s\S]{0,300}INSERT INTO(?!.*ON CONFLICT)'
    message: "Event handlers must be idempotent for replay safety."
    fix_action: "Add ON CONFLICT clause or check-before-insert pattern"
    applies_to:
      - "src/workers/projectors/*.py"
      - "src/core/events/handlers/*.py"
```

### collaboration.yaml additions

```yaml
delegation:
  - trigger: "memory extraction from events"
    delegate_to: ml-memory
    pattern: sequential
    context: "Event schema for MemoryExtracted, extraction triggers"
    receive: "Extraction pipeline that produces MemoryExtracted events"

  - trigger: "causal relationship from event sequence"
    delegate_to: causal-scientist
    pattern: parallel
    context: "Event stream for pattern analysis"
    receive: "CausalLinkDiscovered events"

  - trigger: "decision outcome tracking"
    delegate_to: ml-memory
    pattern: sequential
    context: "DecisionMade event schema"
    receive: "OutcomeObserved event handling"

cross_domain_insights:
  - domain: distributed-systems
    insight: "Exactly-once is impossible; design for at-least-once with idempotency"
    applies_when: "Any event handler design"

  - domain: cqrs
    insight: "Read models can be eventually consistent; writes must be strongly consistent"
    applies_when: "Designing projection update strategies"

mind_v5_specific:
  critical_events:
    - InteractionRecorded
    - MemoryExtracted
    - DecisionMade
    - OutcomeObserved
    - CausalLinkDiscovered
    - PatternValidated
  
  event_flow: |
    Interaction → MemoryExtracted → (stored) → DecisionMade → OutcomeObserved
                                         ↓
                              CausalLinkDiscovered → PatternValidated
```

---

## 2. graph-engineer

### skill.yaml additions

```yaml
mind_v5_context: |
  In Mind v5, you own the Causal Knowledge Graph:
  - FalkorDB for 500x faster p99 vs Neo4j
  - Causal edges with strength, conditions, counterfactuals
  - Entity resolution and temporal validity
  
  Your graph is not just relational—it's CAUSAL:
  - Every edge has direction (cause → effect)
  - Edges have temporal validity windows
  - Store counterfactuals ("what if X didn't happen?")
  - Confidence scores based on evidence

patterns:
  - name: Causal Edge Schema
    description: Full causal relationship with metadata
    when: Any relationship that implies causation
    example: |
      // Cypher for causal edge creation
      MATCH (source:Entity {id: $source_id})
      MATCH (target:Entity {id: $target_id})
      CREATE (source)-[r:CAUSES {
          // Causal metadata
          causal_direction: $direction,
          causal_strength: $strength,
          confidence: $confidence,
          
          // Temporal validity
          valid_from: datetime($valid_from),
          valid_until: $valid_until,
          temporal_conditions: $conditions,
          
          // Evidence
          evidence_count: $evidence_count,
          discovery_method: $method,
          
          // Counterfactual
          counterfactual: $counterfactual
      }]->(target)
      RETURN r
      
  - name: Temporal Validity Query
    description: Query only currently valid relationships
    when: Any graph traversal for current state
    example: |
      // Only get currently valid causal edges
      MATCH (u:User {id: $user_id})-[:HAS_MEMORY]->(m:Memory)
      WHERE m.valid_until IS NULL OR m.valid_until > datetime()
      MATCH (m)-[c:CAUSES]->(effect:Entity)
      WHERE c.valid_until IS NULL OR c.valid_until > datetime()
        AND c.confidence > 0.7
      RETURN m, c, effect
      ORDER BY c.causal_strength DESC
      LIMIT 20
```

### sharp-edges.yaml additions

```yaml
sharp_edges:
  - id: falkordb-redis-memory-limit
    summary: FalkorDB inherits Redis memory limits
    severity: critical
    situation: |
      FalkorDB runs as a Redis module. If Redis hits maxmemory,
      FalkorDB operations fail silently or evict data.
    why: |
      Mind v5 causal graph grows with every user. At 100K users,
      graph can exceed default Redis memory allocation.
    solution: |
      # Redis config for FalkorDB
      maxmemory 16gb
      maxmemory-policy noeviction  # NEVER evict graph data
      
      # Monitor memory usage
      redis-cli INFO memory | grep used_memory_human
      
      # Alert before hitting limit
      - alert: FalkorDBMemoryHigh
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.8
        for: 5m
        labels:
          severity: warning
    symptoms:
      - "Graph queries return empty unexpectedly"
      - "MISCONF Redis is configured to save RDB snapshots"
      - "OOM command not allowed when used memory > maxmemory"
    detection_pattern: 'maxmemory-policy(?!.*noeviction)'

  - id: cypher-unbounded-traversal
    summary: MATCH without LIMIT can timeout on large graphs
    severity: high
    situation: |
      You write a MATCH query that traverses many relationships.
      Works in dev with 1000 nodes, times out in prod with 1M.
    why: |
      Mind v5 graph grows unbounded. A user with 5 years of memories
      can have millions of edges. Unbounded traversal = OOM.
    solution: |
      // ALWAYS use LIMIT and WHERE early
      // ❌ BAD
      MATCH (u:User)-[:HAS_MEMORY]->(m)-[:RELATES_TO]->(e)
      RETURN m, e
      
      // ✅ GOOD
      MATCH (u:User {id: $user_id})-[:HAS_MEMORY]->(m:Memory)
      WHERE m.valid_until IS NULL
      WITH m ORDER BY m.salience DESC LIMIT 100
      MATCH (m)-[:RELATES_TO]->(e:Entity)
      RETURN m, e
      LIMIT 500
    symptoms:
      - "Query timeout after 30 seconds"
      - "Redis CPU at 100%"
      - "Memory spike during query"
    detection_pattern: 'MATCH\s+\([^)]+\)-\[[^\]]*\]->\([^)]+\)(?![\s\S]{0,100}LIMIT)'

  - id: causal-graph-cycles
    summary: Causal graph must be acyclic (DAG)
    severity: critical
    situation: |
      You insert a causal edge A→B when B→A already exists.
      Now you have a cycle, which breaks causal inference.
    why: |
      DoWhy requires DAG for causal inference. Cycles make
      intervention calculations undefined. Counterfactuals break.
    solution: |
      async def add_causal_edge(source_id: UUID, target_id: UUID) -> Result:
          # Check for existing reverse path
          cycle_check = await graph.query(
              """
              MATCH path = (target:Entity {id: $target_id})-[:CAUSES*1..5]->(source:Entity {id: $source_id})
              RETURN count(path) as cycle_count
              """,
              {"source_id": str(source_id), "target_id": str(target_id)}
          )
          
          if cycle_check[0]["cycle_count"] > 0:
              return Result.err(CausalCycleError(
                  f"Adding edge would create cycle: {target_id} already causes {source_id}"
              ))
          
          # Safe to add
          await graph.query(...)
    symptoms:
      - "DoWhy raises 'Graph contains cycle' error"
      - "Counterfactual computation hangs"
      - "Infinite loop in causal traversal"
    detection_pattern: 'CREATE.*CAUSES.*(?!.*cycle)'
```

### validations.yaml additions

```yaml
validations:
  - id: cypher-match-without-limit
    name: Cypher MATCH Without LIMIT
    severity: warning
    type: regex
    pattern:
      - 'MATCH\s+\([^)]+\)-\[[^\]]*\]->\([^)]+\)[\s\S]*RETURN(?![\s\S]*LIMIT)'
    message: "Cypher traversal without LIMIT can timeout on large graphs."
    fix_action: "Add LIMIT clause to bound result set"
    applies_to:
      - "src/infrastructure/falkordb/*.py"
      - "**/graph/*.py"

  - id: causal-edge-missing-confidence
    name: Causal Edge Without Confidence Score
    severity: error
    type: regex
    pattern:
      - 'CREATE.*:CAUSES\s*\{(?![\s\S]*confidence)'
    message: "Causal edges must have confidence score for inference."
    fix_action: "Add confidence: $confidence to edge properties"
    applies_to:
      - "src/core/causal/*.py"
      - "src/infrastructure/falkordb/*.py"

  - id: graph-query-not-parameterized
    name: Graph Query With String Interpolation
    severity: error
    type: regex
    pattern:
      - 'graph\.query\([^)]*f["\']'
      - 'graph\.query\([^)]*\.format\('
      - 'graph\.query\([^)]*\+\s*["\']'
    message: "Graph queries must use parameters, not string interpolation."
    fix_action: "Use query parameters: graph.query(query, {'param': value})"
    applies_to:
      - "**/*.py"
```

---

## 3. vector-specialist

### skill.yaml additions

```yaml
mind_v5_context: |
  In Mind v5, you own semantic retrieval:
  - Qdrant for 38ms p99 vector search
  - pgvectorscale as fallback (11.4x throughput)
  - RRF fusion of vector + graph + keyword
  - Outcome-weighted salience adjustment
  
  Key challenge: Retrieval must be OUTCOME-AWARE.
  Memories that led to good decisions get boosted.

patterns:
  - name: Reciprocal Rank Fusion
    description: Combine multiple retrieval sources
    when: Any context retrieval operation
    example: |
      def reciprocal_rank_fusion(
          result_lists: List[List[SearchResult]],
          k: int = 60
      ) -> List[SearchResult]:
          """RRF fusion - robust, parameter-free."""
          scores: Dict[str, float] = defaultdict(float)
          items: Dict[str, SearchResult] = {}
          
          for results in result_lists:
              for rank, result in enumerate(results):
                  # RRF formula: 1/(k + rank)
                  scores[result.id] += 1.0 / (k + rank + 1)
                  items[result.id] = result
          
          sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
          return [items[id] for id in sorted_ids]

  - name: Outcome-Weighted Retrieval
    description: Boost memories based on decision outcomes
    when: Retrieving context for decisions
    example: |
      async def retrieve_with_outcome_weights(
          query: str,
          user_id: UUID,
      ) -> List[Memory]:
          # Get base retrieval
          vector_results = await qdrant.search(embed(query), limit=50)
          
          # Fetch outcome weights from decision traces
          memory_ids = [r.id for r in vector_results]
          weights = await db.fetch(
              """
              SELECT memory_id, 
                     SUM(outcome_quality * influence) as outcome_score
              FROM decision_traces dt
              JOIN decision_memory_links dml ON dt.trace_id = dml.trace_id
              WHERE dml.memory_id = ANY($1)
              GROUP BY memory_id
              """,
              memory_ids
          )
          weight_map = {w['memory_id']: w['outcome_score'] for w in weights}
          
          # Rerank with outcome weights
          for result in vector_results:
              outcome_boost = weight_map.get(result.id, 0) * 0.2
              result.score = result.score * (1 + outcome_boost)
          
          return sorted(vector_results, key=lambda x: x.score, reverse=True)
```

### sharp-edges.yaml additions

```yaml
sharp_edges:
  - id: qdrant-filter-after-search
    summary: Qdrant payload filters run AFTER vector search
    severity: high
    situation: |
      You add a filter to search: search(query, filter={"user_id": user_id}).
      Expect 20 results, get 3 because filter applied after top-K.
    why: |
      Mind v5 uses user_id filtering. If user has few memories in top-1000
      vector matches, filter returns almost nothing.
    solution: |
      # Use scroll with filter for guaranteed results
      results = await qdrant.scroll(
          collection_name="memories",
          scroll_filter=Filter(
              must=[FieldCondition(key="user_id", match=MatchValue(value=str(user_id)))]
          ),
          limit=100,
          with_vectors=True,  # Get vectors for reranking
      )
      
      # Then rerank by similarity to query
      query_vector = await embed(query)
      scored = [(r, cosine_sim(query_vector, r.vector)) for r in results]
      return sorted(scored, key=lambda x: x[1], reverse=True)[:20]
      
      # OR: Use separate collection per user (better for large scale)
    symptoms:
      - "Search returns fewer results than limit"
      - "Inconsistent result counts across users"
    detection_pattern: 'search\([^)]*filter.*limit'

  - id: embedding-model-mismatch
    summary: Query and corpus embedded with different models
    severity: critical
    situation: |
      You upgrade embedding model for new memories but query
      uses new model against old embeddings.
    why: |
      Different models have different vector spaces. Similarity
      scores become meaningless across models.
    solution: |
      # Track embedding model version in metadata
      @dataclass
      class MemoryEmbedding:
          memory_id: UUID
          embedding: List[float]
          model_version: str  # "text-embedding-3-small-v1"
          created_at: datetime
      
      # Query with model version filter
      async def search(query: str, model_version: str):
          return await qdrant.search(
              collection_name="memories",
              query_vector=embed(query, model=model_version),
              query_filter=Filter(
                  must=[FieldCondition(
                      key="model_version",
                      match=MatchValue(value=model_version)
                  )]
              )
          )
      
      # Migration: Re-embed old memories in background
    symptoms:
      - "Semantically similar items have low similarity scores"
      - "Search quality degrades after model upgrade"
    detection_pattern: 'embed\([^)]+\)(?!.*model_version)'
```

---

## 4. temporal-craftsman

### skill.yaml additions

```yaml
mind_v5_context: |
  In Mind v5, you own the Gardener workflows:
  - MemoryConsolidation (daily hierarchical merge)
  - CausalDiscovery (weekly pattern mining)
  - PatternFederation (continuous to Intent Graph)
  - OutcomeAttribution (async on feedback)
  - GraphMaintenance (monthly prune + reindex)
  
  Key principle: Workflows must be DETERMINISTIC.
  No I/O in workflow code. All side effects in activities.

patterns:
  - name: Memory Consolidation Workflow
    description: Daily workflow to consolidate hierarchical memory
    when: Scheduled daily or on-demand
    example: |
      @workflow.defn
      class MemoryConsolidationWorkflow:
          @workflow.run
          async def run(self, input: ConsolidationInput) -> ConsolidationResult:
              # 1. Fetch candidates (activity)
              candidates = await workflow.execute_activity(
                  fetch_consolidation_candidates,
                  input,
                  start_to_close_timeout=timedelta(minutes=5),
              )
              
              # 2. Evaluate each for promotion (deterministic logic)
              promotions = []
              for memory in candidates:
                  if self._should_promote(memory):
                      promotions.append(memory)
              
              # 3. Execute promotions (activity)
              if promotions:
                  await workflow.execute_activity(
                      execute_promotions,
                      promotions,
                      start_to_close_timeout=timedelta(minutes=10),
                      heartbeat_timeout=timedelta(minutes=2),
                  )
              
              return ConsolidationResult(
                  processed=len(candidates),
                  promoted=len(promotions),
              )
          
          def _should_promote(self, memory: Memory) -> bool:
              """Deterministic promotion logic - NO I/O here."""
              return (
                  memory.evidence_count >= 10 and
                  memory.confidence >= 0.8 and
                  memory.temporal_level < TemporalLevel.IDENTITY
              )
```

### sharp-edges.yaml additions

```yaml
sharp_edges:
  - id: temporal-workflow-nondeterminism
    summary: Random, time.now(), or I/O in workflow causes replay failures
    severity: critical
    situation: |
      You add datetime.now() in workflow to timestamp something.
      Workflow replays, gets different time, history diverges.
    why: |
      Temporal replays workflow from event history. Any non-deterministic
      operation produces different result on replay, causing NondeterminismError.
    solution: |
      # ❌ WRONG: Non-deterministic
      @workflow.defn
      class BadWorkflow:
          @workflow.run
          async def run(self):
              timestamp = datetime.now()  # FAILS ON REPLAY
              random_id = uuid4()  # FAILS ON REPLAY
              data = await fetch_from_db()  # FAILS ON REPLAY
      
      # ✅ CORRECT: Deterministic
      @workflow.defn
      class GoodWorkflow:
          @workflow.run
          async def run(self):
              # Use workflow time (replays correctly)
              timestamp = workflow.now()
              
              # Generate IDs in activities or use workflow.uuid4()
              random_id = workflow.uuid4()
              
              # All I/O through activities
              data = await workflow.execute_activity(fetch_from_db, ...)
    symptoms:
      - "NondeterminismError during workflow replay"
      - "Workflow stuck in 'Running' state"
      - "History mismatch error"
    detection_pattern: '@workflow\.(defn|run)[\s\S]*?(datetime\.now|uuid4\(\)|random\.|time\.time)'

  - id: temporal-activity-no-heartbeat
    summary: Long activities without heartbeat cause timeout
    severity: high
    situation: |
      Activity processes 10K items. Takes 5 minutes.
      Timeout is 10 minutes, but no heartbeat.
      Worker dies at minute 3. Temporal thinks it's still running.
    why: |
      Without heartbeat, Temporal can't detect worker failure.
      Activity sits "in progress" until start_to_close_timeout.
    solution: |
      @activity.defn
      async def process_batch(items: List[Item]) -> BatchResult:
          results = []
          for i, item in enumerate(items):
              # Heartbeat with progress
              activity.heartbeat(f"Processing {i+1}/{len(items)}")
              
              result = await process_item(item)
              results.append(result)
          
          return BatchResult(results=results)
      
      # Configure heartbeat timeout
      await workflow.execute_activity(
          process_batch,
          items,
          start_to_close_timeout=timedelta(hours=1),
          heartbeat_timeout=timedelta(minutes=2),  # Detect failure within 2 min
      )
    symptoms:
      - "Activity appears stuck but worker died"
      - "Duplicate processing after worker restart"
    detection_pattern: '@activity\.defn[\s\S]*?(?!heartbeat)'
```

---

## 5. ml-memory

### skill.yaml additions

```yaml
mind_v5_context: |
  In Mind v5, you own the hierarchical memory system:
  - Four temporal levels: immediate → situational → seasonal → identity
  - Outcome-weighted salience (memories that help decisions get boosted)
  - Integration with Zep/Graphiti for temporal knowledge graph
  - Memory consolidation and forgetting policies
  
  Key insight: Memory is not storage—it's decision support.
  Measure success by decision quality, not recall.

patterns:
  - name: Hierarchical Memory Levels
    description: Four-level temporal hierarchy
    when: Storing or retrieving any memory
    example: |
      class TemporalLevel(Enum):
          IMMEDIATE = 1     # Hours - current session
          SITUATIONAL = 2   # Days/weeks - active tasks
          SEASONAL = 3      # Months - projects, recurring patterns
          IDENTITY = 4      # Years - core values, stable preferences
      
      LEVEL_CONFIG = {
          TemporalLevel.IMMEDIATE: LevelConfig(
              decay_hours=24,
              max_items=100,
              promotion_threshold=5,
          ),
          TemporalLevel.SITUATIONAL: LevelConfig(
              decay_days=14,
              max_items=500,
              promotion_threshold=10,
          ),
          TemporalLevel.SEASONAL: LevelConfig(
              decay_months=6,
              max_items=1000,
              promotion_threshold=20,
          ),
          TemporalLevel.IDENTITY: LevelConfig(
              decay_years=10,
              max_items=200,
              promotion_threshold=None,  # No promotion from identity
          ),
      }

  - name: Outcome-Based Salience Update
    description: Adjust memory salience based on decision outcomes
    when: Outcome observed for a decision
    example: |
      async def update_salience_from_outcome(
          trace: DecisionTrace,
          outcome_quality: float,  # -1 to 1
      ) -> None:
          """Update memory salience based on decision outcome."""
          for memory_id, influence in trace.memory_attribution.items():
              # Positive outcome + high influence = boost
              # Negative outcome + high influence = reduce
              adjustment = outcome_quality * influence * 0.1
              
              await db.execute(
                  """
                  UPDATE memories
                  SET outcome_adjustment = outcome_adjustment + $1,
                      decision_count = decision_count + 1,
                      positive_outcomes = positive_outcomes + CASE WHEN $2 > 0 THEN 1 ELSE 0 END,
                      negative_outcomes = negative_outcomes + CASE WHEN $2 < 0 THEN 1 ELSE 0 END
                  WHERE memory_id = $3
                  """,
                  adjustment, outcome_quality, memory_id
              )
```

### sharp-edges.yaml additions

```yaml
sharp_edges:
  - id: memory-entity-duplication
    summary: Same entity stored under different names
    severity: high
    situation: |
      User mentions "my wife Sarah" and later "Sarah".
      System creates two entities. Memories don't connect.
    why: |
      Entity resolution is 80% of memory system work.
      Without it, knowledge fragments across duplicates.
    solution: |
      async def resolve_entity(mention: str, context: str) -> Entity:
          # 1. Exact match
          exact = await db.fetch_entity_by_name(mention)
          if exact:
              return exact
          
          # 2. Fuzzy match with context
          candidates = await db.fetch_similar_entities(
              embedding=embed(f"{mention} {context}"),
              threshold=0.85,
              limit=5,
          )
          
          if candidates:
              # Use LLM to confirm match
              best_match = await llm_confirm_entity_match(
                  mention=mention,
                  context=context,
                  candidates=candidates,
              )
              if best_match:
                  # Create alias
                  await db.add_entity_alias(best_match.id, mention)
                  return best_match
          
          # 3. Create new entity
          return await db.create_entity(name=mention)
    symptoms:
      - "Duplicate entities in graph"
      - "Memories about same person not connected"
      - "Search returns partial results"
    detection_pattern: 'create_entity\([^)]+\)(?!.*resolve)'

  - id: memory-no-forgetting
    summary: Memory system without decay becomes noisy
    severity: medium
    situation: |
      System stores everything forever. After 2 years,
      retrieval returns outdated info ranked higher than current.
    why: |
      Mind v5 is about decision quality. Old, irrelevant memories
      add noise that degrades decisions.
    solution: |
      # Implement forgetting curve
      async def apply_memory_decay():
          await db.execute(
              """
              UPDATE memories
              SET base_salience = base_salience * POWER(0.95, 
                  EXTRACT(DAYS FROM NOW() - last_retrieved) / 30
              )
              WHERE temporal_level != 4  -- Don't decay identity
                AND last_retrieved < NOW() - INTERVAL '30 days'
              """
          )
          
          # Forget very low salience memories
          await db.execute(
              """
              UPDATE memories
              SET valid_until = NOW()
              WHERE effective_salience < 0.1
                AND temporal_level = 1  -- Only forget immediate
              """
          )
    symptoms:
      - "Retrieval quality degrades over time"
      - "Old preferences override recent ones"
      - "Storage grows unbounded"
    detection_pattern: 'class.*Memory.*(?!.*decay|.*forget)'
```

---

## 6. causal-scientist

### skill.yaml additions

```yaml
mind_v5_context: |
  In Mind v5, you own causal inference:
  - DoWhy for causal discovery and estimation
  - CausalNex for Bayesian networks
  - Causal edges in FalkorDB with counterfactuals
  - Intervention effect prediction
  
  Key principle: Correlation is cheap, causation is gold.
  Store WHY relationships, not just WHAT.

patterns:
  - name: Causal Edge Discovery Pipeline
    description: Infer causal relationships from observational data
    when: Enough observations to detect patterns
    example: |
      async def discover_causal_edge(
          source: Entity,
          target: Entity,
          observations: pd.DataFrame,
      ) -> Optional[CausalEdge]:
          # 1. Check temporal ordering
          if not valid_temporal_order(source, target, observations):
              return None
          
          # 2. Build causal model
          model = dowhy.CausalModel(
              data=observations,
              treatment=source.feature_name,
              outcome=target.feature_name,
              common_causes=known_confounders(source, target),
          )
          
          # 3. Identify causal effect
          identified = model.identify_effect(proceed_when_unidentifiable=False)
          if not identified:
              return None
          
          # 4. Estimate with multiple methods
          estimates = []
          for method in ["backdoor.linear_regression", "backdoor.propensity_score"]:
              try:
                  estimate = model.estimate_effect(identified, method_name=method)
                  estimates.append(estimate)
              except:
                  continue
          
          if not estimates:
              return None
          
          # 5. Refutation tests
          for estimate in estimates:
              refutation = model.refute_estimate(
                  identified, estimate, method_name="random_common_cause"
              )
              if refutation.new_effect / estimate.value < 0.5:
                  return None  # Not robust
          
          # 6. Build causal edge
          avg_effect = np.mean([e.value for e in estimates])
          return CausalEdge(
              source_id=source.id,
              target_id=target.id,
              causal_strength=abs(avg_effect),
              confidence=1.0 / (1.0 + np.std([e.value for e in estimates])),
              discovery_method="dowhy_backdoor",
          )
```

### sharp-edges.yaml additions

```yaml
sharp_edges:
  - id: causal-confounding-ignored
    summary: Ignoring confounders produces spurious causal claims
    severity: critical
    situation: |
      You find correlation between coffee and productivity.
      Claim "coffee causes productivity" without checking confounders.
    why: |
      Deadline pressure causes both coffee drinking AND productivity.
      Without adjusting for confounders, effect estimate is biased.
    solution: |
      # Always include known confounders
      model = dowhy.CausalModel(
          data=observations,
          treatment="coffee_consumption",
          outcome="productivity",
          # Include confounders based on domain knowledge
          common_causes=[
              "deadline_pressure",
              "sleep_quality",
              "time_of_day",
          ],
      )
      
      # Use IV or other methods when confounding suspected
      # Sensitivity analysis for unobserved confounding
      refutation = model.refute_estimate(
          identified, estimate,
          method_name="add_unobserved_common_cause",
          confounders_effect_on_treatment=0.1,
          confounders_effect_on_outcome=0.1,
      )
    symptoms:
      - "Causal effect disappears when new variable added"
      - "Effect size much larger than expected"
      - "Refutation tests fail consistently"
    detection_pattern: 'CausalModel\([^)]*(?!common_causes)'
```

---

## 7-20: Quick Enhancement Summary

Due to length, here are the critical additions for remaining skills:

### 7. privacy-guardian
```yaml
# Critical validations
- id: pii-in-federation
  pattern: 'federate.*pattern.*(?!.*sanitize)'
  message: "Patterns must be sanitized before federation"
  
- id: differential-privacy-epsilon
  pattern: 'epsilon\s*[=>]\s*(?:0\.[2-9]|[1-9])'
  message: "Epsilon must be ≤0.1 for meaningful privacy"
```

### 8. performance-hunter
```yaml
# Critical sharp edges
- id: n-plus-one-memory-retrieval
  summary: Loading memories one-by-one instead of batch
  solution: "Use fetch_memories(ids) not loop of fetch_memory(id)"
```

### 9. infra-architect
```yaml
# Mind v5 specific
- kubernetes namespaces: mind-core, mind-platform, mind-workers
- resource quotas per user tier
- FalkorDB requires Redis operator
```

### 10. postgres-wizard
```yaml
# Critical validations
- id: memories-missing-partition
  pattern: 'CREATE TABLE memories(?!.*PARTITION)'
  message: "memories table must be partitioned by user_id"
```

### 11. observability-sre
```yaml
# Mind v5 specific metrics
- mind_decision_success_rate
- mind_memory_retrieval_relevance
- mind_causal_prediction_accuracy
- mind_federation_pattern_count
```

### 12. migration-specialist
```yaml
# Critical pattern
- name: Dual-Write Migration
  when: Any memory schema change
  why: Can't break retrieval during migration
```

### 13. chaos-engineer
```yaml
# Mind v5 experiments
- qdrant_latency: Test graceful degradation
- nats_partition: Test event persistence
- falkordb_oom: Test graph query limits
```

### 14. test-architect
```yaml
# Required test types
- decision_trace_tests: Verify outcome attribution
- causal_inference_tests: Verify edge discovery
- federation_privacy_tests: Verify no PII leakage
```

### 15. code-reviewer
```yaml
# Mind v5 checklist additions
- [ ] Events are immutable and past-tense
- [ ] Memory operations have outcome tracking
- [ ] Causal edges have confidence scores
```

### 16. data-engineer
```yaml
# Federation pipeline
- Pattern extraction from outcomes
- Privacy sanitization (ε=0.1)
- Aggregation thresholds (100+ sources)
```

### 17. api-designer
```yaml
# Mind v5 endpoints
- POST /v1/memories
- POST /v1/context/retrieve
- POST /v1/decisions/record
- POST /v1/decisions/{id}/outcome
```

### 18. sdk-builder
```yaml
# SDK methods
- client.memories.create()
- client.context.retrieve()
- client.decisions.record()
- client.decisions.record_outcome()
```

### 19. docs-engineer
```yaml
# Required documentation
- Memory hierarchy explanation
- Causal edge schema reference
- Outcome attribution guide
- Federation privacy model
```

### 20. python-craftsman
```yaml
# Mind v5 patterns
- Result type for all fallible operations
- Frozen dataclasses for events/memories
- Async everywhere for I/O
- Type hints required (mypy strict)
```

---

## Next Steps

1. **Run enhancement on each skill**: `enhance <skill-id>`
2. **Validate regex patterns work**: `validate <skill-id>`
3. **Cross-reference relationships**: `cross-reference <skill-id>`
4. **Generate test cases**: `generate-tests <skill-id>`

This document provides the Mind v5-specific content to merge into your existing Spawner V2 skills.
