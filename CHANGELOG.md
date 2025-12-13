# Changelog

All notable changes to Mind will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
