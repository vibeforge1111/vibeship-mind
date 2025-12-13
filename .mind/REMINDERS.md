## Reminders
- [ ] 2026-01-12 | absolute | Review all docs for accuracy - check version banners match implementation, update last-updated dates. Docs: README.md, ARCHITECTURE.md, HOW_IT_WORKS.md, MCP_TOOLS.md
- [ ] a/b test | context | A/B test whether explicit mind_recall() instruction in CLAUDE.md is needed when SessionStart hook already calls it. Test: remove instruction, see if context still loads correctly.
- [x] 2025-12-13 | done | Check if reminder marking works - mark_reminder_done() exists but isn't exposed via MCP tool. Either add mind_reminder_done tool or auto-mark on recall.
- [ ] self-improvement | context | Design SELF_IMPROVE.md once session system is validated - meta-learning layer for patterns, blind spots, what works
- [x] 2025-12-13 | done | Improve reminders with context-matching (Phase B) - add keyword triggers like 'remind me when we work on auth'
- [x] 2025-12-13 | done | Improve reminders with context-matching

