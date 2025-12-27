# Semantic Memory Architecture Design

**Date:** 2025-12-15
**Status:** Ready for implementation

## Overview

Enhance Mind's memory system with semantic intelligence - making Session and Memory work as a connected loop rather than separate buckets. Adds smart retrieval, novelty-based promotion, bug/overwhelm handling, and Obsidian compatibility for cloud sync.

## Design Decisions

### 1. Session <-> Memory Bidirectional Flow

**Problem:** Session and Memory are disconnected. Promotion is rare, retrieval is keyword-based, no semantic understanding.

**Solution:** Continuous loop where each layer informs the other.

#### Memory -> Session (Retrieval)

| Trigger | Behavior |
|---------|----------|
| `mind_recall()` with existing SESSION.md | Semantic scan session content -> surface top relevant memories |
| First `experience` log of new session | Semantic search -> "you've dealt with this before..." |
| `blocker` log | Semantic search -> "you solved similar with..." |
| `rejected` log | Loop detection (existing) + past solutions check |

**Key insight:** Retrieval triggers when we have signal (know what user is working on), not blindly at session start.

#### Session -> Memory (Promotion)

| Condition | Behavior |
|-----------|----------|
| Novelty check | Only promote if similarity < 0.5 vs existing memory |
| Similar exists, low confidence | **Link** - add with `[[wikilink]]` reference to related |
| Similar exists, high confidence (>=0.7) | **Supersede** - mark old as `[superseded]`, new is truth |

**Confidence ties to existing reinforcement system** - reuse Phases 6-7 confidence scores.

### 2. Bug Memory & Overwhelm Response

**Problem:** Bugs aren't captured in reusable way. No methodology when stuck beyond looping.

#### Bug Memory

**Which bugs to remember:** Surprising OR reusable (would future-me benefit?)

**Signals for reusable bugs:**
- Platform names (Windows, macOS, Linux)
- Library/framework names
- Error patterns
- Root cause + solution structure

**Implementation:** On promotion, semantic filter keeps bugs with reusability signals.

#### Overwhelm Flow

```
Bug encountered
    |
    +-- 1st-2nd attempt: Try fixes naturally
    |
    +-- mind_blocker() -> semantic search memory for past solutions
    |
    +-- 3rd+ attempt: Loop detection warns if repeating
    |
    +-- Still stuck:
        |
        +-- METHODOLOGY (zoom out checklist)
        |   - Question assumptions (check SESSION.md Assumptions)
        |   - Reframe the problem ("what am I actually trying to do?")
        |   - Check if solving wrong problem
        |   - Try opposite approach
        |   - Simplify (remove variables)
        |
        +-- If still stuck -> SPAWN AGENT (semi-auto)
            - Mind suggests in loop warning, user confirms
            - Agent gets: problem + SESSION.md (what's been tried)
            - Agent works on: current branch (not isolated)
            - Agent can: implement fix directly
            - Fresh perspective, no rabbit hole baggage
```

#### Enhanced Loop Warning Response

```
Current:
"WARNING: Similar rejection found! 89% similar"

New:
"WARNING: You're looping (89% similar to previous attempt)

Suggestions:
1. Try methodology: question assumptions, reframe problem, simplify
2. Spawn fresh agent to help? (confirm: yes/no)"
```

### 3. Personal Cloud / Cross-Device Sync

**Problem:** .mind/ is gitignored for privacy. How to sync across devices?

**Solution:** File-based + Obsidian compatibility. No graph DB needed.

| Layer | Approach |
|-------|----------|
| Storage | File-based markdown (no graph DB) |
| Sync | User's existing tools (Obsidian Sync, iCloud, Syncthing) |
| Compatibility | Obsidian-friendly by default |
| Integration | Optional vault path config |
| Plugin | Future nice-to-have |
| Linking | Wikilinks `[[MEMORY#section]]` for navigable memory graph |

**Why not Graphiti/graph DB:** Our files are tiny (<1MB). Graph DB adds infrastructure, cost, complexity. Obsidian gives us graph visualization for free via wikilinks.

**Aha moment:** User opens .mind/ in Obsidian, sees graph of their thinking - decisions linked to problems, learnings linked to bugs, thought evolution visible.

## Implementation Phases

### Phase 1: Semantic Search for mind_search()
- Replace keyword grep with semantic similarity
- Use existing sentence-transformers model
- Return results ranked by relevance score
- **Files:** `src/mind/mcp/server.py`, `src/mind/similarity.py`

### Phase 2: Memory -> Session Retrieval
- On `mind_recall()` with session content, scan against MEMORY.md
- On first `experience` log, semantic search
- On `blocker` log, upgrade from keyword to semantic search
- Surface top 1-2 relevant memories (threshold 0.7)
- **Files:** `src/mind/mcp/server.py`

### Phase 3: Smart Promotion (Session -> Memory)
- Novelty check: skip if similarity > 0.5 to existing
- Link vs Supersede based on confidence score
- Wikilink format for references: `[[MEMORY#2025-12-15-section]]`
- **Files:** `src/mind/mcp/server.py`, `src/mind/context.py`

### Phase 4: Bug Memory Filter
- On promotion, detect reusability signals (platform, library, error patterns)
- Only promote bugs that pass reusability check
- Structure: problem -> root cause -> solution
- **Files:** `src/mind/mcp/server.py`

### Phase 5: Enhanced Loop Warning
- Update loop warning response with methodology suggestions
- Add spawn suggestion with confirm prompt
- **Files:** `src/mind/mcp/server.py`

### Phase 6: Agent Spawning Integration
- New tool or flow: `mind_spawn_helper()`
- Packages problem + SESSION.md for fresh agent
- Agent works on current branch
- Returns recommendation or implements fix
- **Files:** `src/mind/mcp/server.py` (or integration with Spawner)

### Phase 7: Obsidian Compatibility
- Ensure wikilinks work: `[[MEMORY#section]]` format
- Document: "Want cloud sync? Add .mind/ to your Obsidian vault"
- Optional: vault path config
- **Files:** `src/mind/templates.py`, docs

## Success Criteria

1. **Retrieval works:** When logging experience/blocker, relevant past memories surface automatically
2. **Promotion is smart:** Only novel learnings get promoted, duplicates skipped or linked
3. **Bugs are reusable:** Platform/library gotchas captured with root cause + solution
4. **Overwhelm has escape hatch:** Methodology + agent spawn option when looping
5. **Cloud sync possible:** User can sync .mind/ via Obsidian with zero Mind config

## Out of Scope

- Team memory (future - personal cloud first)
- Graph database (file-based is enough)
- Built-in sync service (leverage existing tools)
- Obsidian plugin (future nice-to-have)

## Obsidian Cloud Sync

Want to sync your Mind memory across devices? Add `.mind/` to an Obsidian vault:

1. **Simple:** Copy/symlink `.mind/` into your vault folder
2. **Advanced:** Create a central vault for all project `.mind/` folders
3. **Sync:** Use Obsidian Sync, iCloud, Syncthing, or any file sync

Benefits:
- Graph view shows connections between decisions, learnings, problems
- Search across all memories with Obsidian's search
- Wikilinks `[[MEMORY#L123]]` navigate between related entries
- Version history via Obsidian's built-in git or sync versioning

## Dependencies

- `sentence-transformers` (already installed)
- Existing confidence/reinforcement system (Phases 6-7)
- Existing loop detection (semantic similarity)

## Risks

- **Embedding model load time:** Already lazy-loaded, should be fine
- **False positive retrieval:** Use high threshold (0.7) to avoid noise
- **Agent spawning complexity:** Start with recommendation-only, add implementation later
