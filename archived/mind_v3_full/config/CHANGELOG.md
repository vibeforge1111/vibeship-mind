# Changelog

All notable changes to Mind will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2025-12-15

### Added
- **Semantic similarity engine** - TF-IDF based similarity for smarter memory operations
- **Semantic search** - `mind_search()` now uses semantic matching, not just keywords
- **Loop detection** - Warns when logging rejected approaches similar to previous ones
- **Loop warning severity** - Critical/High/Moderate levels with methodology hints
- **Smart promotion** - Novelty checking prevents duplicate memories, links or supersedes similar entries
- **Bug memory filter** - Scores bugs for reusability (platform/library bugs promoted, one-off bugs skipped)
- **Memory -> Session retrieval** - Relevant memories surfaced when logging experiences/blockers
- **mind_spawn_helper tool** - Package problems for fresh agent investigation when stuck
- **Obsidian compatibility** - Wikilink format hints in docs, `.mind/` folder works as Obsidian vault

### Fixed
- `mind_spawn_helper` undefined function error (parse_session_content)

### Changed
- Now 13 MCP tools (was 12)

---

## [2.1.0] - 2025-12-13

### Added
- `mind_reminder_done` tool - Mark reminders as done manually
- Auto-mark "next session" reminders when surfaced in `mind_recall()`
- Version banners in all docs (`<!-- doc-version: X.X.X | last-updated: YYYY-MM-DD -->`)
- Periodic doc review reminder (every 30 days)

### Changed
- Now 12 MCP tools (was 11)
- Consolidated docs: merged DESIGN_RATIONALE.md into ARCHITECTURE.md
- Moved PARSER.md to archive (stable, rarely changes)
- Updated all docs to reflect 12 tool count

### Removed
- Outdated archive docs: CLI.md, IMPLEMENTATION.md, ONBOARDING.md

---

## [2.0.0] - 2025-12-13

### Added
- **Two-layer memory system**: MEMORY.md (permanent) + SESSION.md (ephemeral)
- **11 MCP tools**: mind_recall, mind_log, mind_session, mind_blocker, mind_search, mind_remind, mind_reminders, mind_edges, mind_checkpoint, mind_status, mind_add_global_edge
- **Unified mind_log routing**: Routes by type - session types (experience, blocker, assumption, rejected) go to SESSION.md, memory types (decision, learning, problem, progress) go to MEMORY.md
- **Reminder system**: Time-based (tomorrow, in 3 days, next session) and context-based (when I mention X)
- **Session gap detection**: Auto-promotes valuable SESSION.md items to MEMORY.md after 30 min gap
- **Feature flags**: `.mind/config.json` for experimental features
- **Mind website**: SvelteKit site with architecture diagrams

### Changed
- **Daemon-free architecture**: Removed daemon, MCP handles everything stateless
- **Simplified SESSION.md**: 4 sections (Experience, Blockers, Rejected, Assumptions) instead of 6

### Removed
- Daemon process and related code
- Manual session goal/approach/discovery tools (unified into mind_log)
- Claude Code hooks (decided against automation complexity)

## [1.0.0] - 2025-12-01

### Added
- Initial Mind release
- MEMORY.md-based persistent memory
- Basic MCP server with recall, search, checkpoint
- Parser for extracting decisions, issues, learnings from natural language
- Stack detection
- Global and project-level gotchas (edges)
