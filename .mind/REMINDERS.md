## Reminders
- [x] 2025-12-14 | done | Phase 9 (Learning Style) is the AGI step - model HOW user learns, not just WHAT. New pattern type LEARNING_STYLE with categories like [concepts], [debugging], [decisions], [communication]
- [x] 2025-12-14 | done | After Phases 6-7, build Phase 8 (Contradiction Detection) - uses Jaccard similarity for keyword overlap, detects opposing words like prefer/avoid, verbose/terse
- [x] 2025-12-14 | done | Build Phase 6 (Confidence Decay) + Phase 7 (Reinforcement) together - they work as a pair. Start with calculate_decayed_confidence() and PatternMetadata storage in pattern_metadata.json
- [ ] 2026-01-12 | absolute | Review all docs for accuracy - check version banners match implementation, update last-updated dates. Docs: README.md, ARCHITECTURE.md, HOW_IT_WORKS.md, MCP_TOOLS.md
- [ ] a/b test | context | A/B test whether explicit mind_recall() instruction in CLAUDE.md is needed when SessionStart hook already calls it. Test: remove instruction, see if context still loads correctly.
- [x] 2025-12-13 | done | Check if reminder marking works - mark_reminder_done() exists but isn't exposed via MCP tool. Either add mind_reminder_done tool or auto-mark on recall.
- [ ] self-improvement | context | Design SELF_IMPROVE.md once session system is validated - meta-learning layer for patterns, blind spots, what works
- [x] 2025-12-13 | done | Improve reminders with context-matching (Phase B) - add keyword triggers like 'remind me when we work on auth'
- [x] 2025-12-13 | done | Improve reminders with context-matching

