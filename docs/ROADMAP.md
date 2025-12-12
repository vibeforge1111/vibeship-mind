# Mind Roadmap

Implementation plan in 4 phases over 8 weeks.

## Phase 1: Foundation (Weeks 1-2)

**Goal:** Working local Mind with core functionality.

### Week 1: Data Layer

- [ ] Set up project structure
  - Python package with uv
  - Basic CLI skeleton
  - Test infrastructure

- [ ] Implement data models
  - All Pydantic models from DATA_MODELS.md
  - Validation and defaults
  - Serialization helpers

- [ ] Implement SQLite storage
  - Schema creation
  - CRUD operations for all entities
  - JSON field handling
  - Change tracking for future sync

- [ ] Basic tests
  - Model validation
  - Storage operations
  - Round-trip serialization

### Week 2: MCP Integration

- [ ] Implement ChromaDB storage
  - Embedding generation (sentence-transformers)
  - Vector storage and retrieval
  - Collection per entity type

- [ ] Implement MCP server
  - Server skeleton
  - `mind_start_session` tool
  - `mind_end_session` tool
  - `mind_get_context` tool

- [ ] Implement remaining tools
  - `mind_add_decision`
  - `mind_add_issue`
  - `mind_update_issue`
  - `mind_add_edge`
  - `mind_update_project`
  - `mind_check_edges`
  - `mind_export`

- [ ] Integration test
  - Full session lifecycle
  - Context retrieval accuracy
  - Edge detection

**Deliverable:** Mind works locally with Claude Code. Can start sessions, store decisions/issues/edges, retrieve context.

---

## Phase 2: Intelligence (Weeks 3-4)

**Goal:** Smarter retrieval, edge detection, session management.

### Week 3: Context Engine

- [ ] Weighted retrieval
  - Recency weighting
  - Frequency tracking (access counts)
  - Project relevance scoring
  - Trigger phrase matching

- [ ] Multi-entity search
  - Cross-type queries
  - Result deduplication
  - Relevance ranking

- [ ] Session primer generation
  - Template system
  - Dynamic content selection
  - Length constraints

### Week 4: Detection & Lifecycle

- [ ] Sharp edge detection
  - Pattern matching engine
  - Code pattern detection
  - Context pattern detection
  - Intent pattern detection

- [ ] Episode extraction
  - Significance scoring
  - Narrative generation (rule-based)
  - Mood arc inference
  - Artifact linking

- [ ] Memory decay
  - Access tracking
  - Decay scoring
  - Archive threshold
  - Cleanup job

- [ ] User model updates
  - Pattern inference
  - Preference learning
  - Dynamic state tracking

**Deliverable:** Mind retrieves intelligently, catches sharp edges proactively, maintains user model.

---

## Phase 3: Cloud & Sync (Weeks 5-6)

**Goal:** Optional cloud sync for Pro users.

### Week 5: Cloudflare Backend

- [ ] D1 schema deployment
  - Same schema as SQLite
  - Migration scripts
  - Worker bindings

- [ ] Vectorize setup
  - Collection creation
  - Embedding pipeline
  - Search API

- [ ] Workers API
  - Authentication (API keys / JWT)
  - CRUD endpoints
  - Rate limiting (KV)

- [ ] R2 for exports
  - Backup storage
  - Export downloads

### Week 6: Sync Engine

- [ ] Change tracking
  - Local change log
  - Timestamp-based diff

- [ ] Sync protocol
  - Push local changes
  - Pull remote changes
  - Conflict resolution (last-write-wins)

- [ ] Encryption
  - Key derivation
  - Encrypt before upload
  - Decrypt on download

- [ ] Sync UX
  - Manual sync command
  - Auto-sync option
  - Conflict notifications

**Deliverable:** Pro users can sync Mind across devices with encrypted cloud storage.

---

## Phase 4: Polish (Weeks 7-8)

**Goal:** Production-ready, documented, community features.

### Week 7: Community Features

- [ ] Sharp Edge Registry
  - Submission API
  - Anonymization
  - Verification flow
  - Community voting

- [ ] Registry sync
  - Fetch community edges
  - Local caching
  - Update notifications

- [ ] CLI improvements
  - Project management commands
  - Search commands
  - Status dashboard

### Week 8: Polish & Launch

- [ ] Documentation
  - README finalization
  - Setup guide
  - Troubleshooting

- [ ] Error handling
  - Graceful failures
  - Recovery flows
  - User-friendly messages

- [ ] Performance
  - Startup time optimization
  - Query optimization
  - Caching

- [ ] Launch prep
  - GitHub release
  - Blog post
  - Community announcement

**Deliverable:** Mind 1.0 - ready for public use.

---

## Post-Launch

### v1.1 (Month 2)
- AI-powered episode extraction (Claude API)
- Smarter pattern inference
- Team features (shared projects)

### v1.2 (Month 3)
- VS Code extension
- Web dashboard
- Analytics (optional, private)

### v1.3 (Month 4)
- Integration with Scanner
- Integration with Spawner
- Marketplace hooks

---

## Success Metrics

### Phase 1 Success
- [ ] Can complete full session lifecycle
- [ ] Context retrieval returns relevant results
- [ ] Works with Claude Code

### Phase 2 Success
- [ ] Retrieval accuracy >80% (relevant results in top 3)
- [ ] Edge detection catches known patterns
- [ ] Primer generation <500ms

### Phase 3 Success
- [ ] Sync works across 2+ devices
- [ ] No data loss in conflict scenarios
- [ ] Encryption verified by third party

### Phase 4 Success
- [ ] 100+ community sharp edges
- [ ] <5% support tickets about setup
- [ ] Positive user feedback

---

## Risk Mitigation

### Technical Risks

| Risk | Mitigation |
|------|------------|
| ChromaDB cold start slow | Pre-download model during install |
| SQLite concurrent writes | WAL mode, serialize writes |
| MCP tool latency | Cache aggressively, defer expensive ops |
| Embedding model size | Use MiniLM-L6 (90MB), not larger models |

### Product Risks

| Risk | Mitigation |
|------|------------|
| Empty state problem | Smart onboarding, project detection |
| Memory creep | Decay system, archive threshold |
| Over-reliance | Show dates, confidence levels |
| Privacy concerns | Local-first, open source, encrypted sync |

---

## Dependencies

### Required
- Python 3.11+
- uv (package management)
- SQLite 3
- ChromaDB
- sentence-transformers

### Optional (Pro)
- Cloudflare account
- D1 database
- Vectorize index
- Workers deployment

### Development
- pytest
- ruff
- black
- mypy

---

## Team Allocation

For solo developer (Cem):

| Phase | Focus | Hours/Week |
|-------|-------|------------|
| 1 | Core implementation | 20-30 |
| 2 | Intelligence layer | 15-20 |
| 3 | Cloud (can defer) | 10-15 |
| 4 | Polish & launch | 15-20 |

**Recommendation:** Ship Phase 1+2 first. Cloud can wait. Local-first Mind is immediately valuable.
