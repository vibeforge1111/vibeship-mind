# Mind Stability & Customization Redesign

**Date:** 2025-12-18
**Status:** Design Complete, Ready for Implementation

## Problem Statement

Mind's SESSION.md feature isn't being used effectively:
- Claude doesn't log consistently
- Silent failures when files are malformed
- No visibility when things break
- One-size-fits-all approach doesn't work for all users
- Different editors (Claude Code, Cursor, Windsurf) need different setups

## Design Goals

1. **Reliability** - Things just work, auto-repair when broken
2. **Smart defaults** - Works well out of the box
3. **Simple customization** - 3 questions, not 30
4. **Stack-aware** - Knows your editor, sets up correctly
5. **Clean codebase** - Remove legacy code, add tests

---

## User Experience

### First Install (`mind init`)

```
$ mind init

Welcome to Mind! Let me set things up for you.

? How much should I remember? (Use arrows)
> Balanced - Key moments + context (recommended)
  Efficient - Only critical decisions and blockers
  Detailed - Everything, compacted to Memory periodically

? Should learnings auto-promote to long-term memory?
> Yes - Good insights move from Session to Memory automatically
  No - I'll decide what to keep
  Ask me - Prompt before promoting

? How should memories age over time?
> Smart - Frequently-used memories stay strong, unused ones fade
  Keep all - Everything stays at full strength forever

Detected: Claude Code
[+] Created .mind/MEMORY.md
[+] Created .mind/SESSION.md
[+] Created .mind/REMINDERS.md
[+] Created .mind/config.json
[+] Updated CLAUDE.md with Mind instructions (prominent)
[+] Saved preferences to ~/.mind/preferences.json

Mind is ready! I'll remember what matters.
```

### Returning User (new project)

```
$ mind init

Found your Mind preferences from other projects:
  - Logging: Balanced
  - Auto-promote: Yes
  - Memory aging: Smart

? Use these settings?
> Yes, same as before
  No, let me customize
```

### Changing Settings Later

User says: "adjust my mind settings" or "change mind config"

Claude responds with options, saves to config.json.

---

## Logging Levels

### Efficient (Lighter)

**What gets logged:**
- Decisions with reasoning ("chose X because Y")
- Blockers ("stuck on X")
- Learnings ("discovered X")
- Problems solved ("fixed X by Y")

**What's skipped:**
- Routine actions ("reading file X")
- Search operations ("looking for Y")
- General observations without insight

**Session-to-Memory promotion:**
- Only items with clear reasoning or solutions
- High threshold for promotion

### Balanced (Default)

**What gets logged:**
- Everything in Efficient, plus:
- Assumptions ("assuming X is true")
- Rejected approaches ("tried X, didn't work because Y")
- Context around decisions

**Auto-categorization:**
- Detects type from message content
- "tried X, failed" -> rejected
- "stuck on" -> blocker
- "assuming" -> assumption

**Session-to-Memory promotion:**
- Items with reasoning, patterns, or reusable insights
- Moderate threshold

### Detailed (Verbose)

**What gets logged:**
- Most actions into Session
- Full context and thinking
- More verbose capture

**Compaction:**
- On session gap (30+ min): Summarize Session entries into concise Memory entries
- On task completion (commit, "done"): Same compaction
- Raw Session cleared after compaction
- Memory gets clean summaries, not raw logs

---

## Auto-Health System

### Silent Auto-Repair

| Issue | Detection | Fix |
|-------|-----------|-----|
| SESSION.md missing sections | Section regex fails | Add missing sections |
| SESSION.md malformed | Parse errors | Regenerate from template |
| MEMORY.md corrupted | Parse errors | Backup + regenerate structure |
| Config invalid JSON | JSON parse fails | Reset to defaults |
| Mind instructions missing | Check editor config files | Auto-inject |

### Stack-Aware Setup

Detect editor and inject Mind instructions:

| Editor | Config File | Detection |
|--------|-------------|-----------|
| Claude Code | `CLAUDE.md` | `.claude/` dir or explicit |
| Cursor | `.cursorrules` | `.cursor/` dir |
| Windsurf | `.windsurfrules` | Windsurf markers |
| Cline | `.clinerules` | Cline markers |
| Generic | `AGENTS.md` | Fallback |

**Injection rules:**
- Instructions go at TOP of file (prominent)
- Include clear "USE EVERY SESSION" language
- Don't duplicate if already present
- Update if outdated version detected

### Update Notifications

On `mind_recall()`:
- Check installed version vs latest (cached, check daily max)
- If update available: Include in response "Mind update available: X.Y.Z -> A.B.C. Run: `pip install --upgrade mind`"

---

## Usage-Based Retention

### How It Works

Each memory entry has a `relevance_score` (0.0 to 1.0):
- Starts at 1.0 when created
- **Reinforced** when:
  - Memory appears in search results user acts on
  - Memory helps solve a problem (detected by follow-up "fixed" log)
  - Memory explicitly referenced
- **Decays** when:
  - Not accessed for 30+ days: -0.1
  - Not accessed for 60+ days: additional -0.1
  - Minimum floor: 0.2 (never fully forgotten)

### Context Priority

When generating MIND:CONTEXT for CLAUDE.md:
- High relevance (0.7+): Always included
- Medium relevance (0.4-0.7): Included if space
- Low relevance (0.2-0.4): Only if directly searched

### User Choice

- **Smart retention**: Above behavior (default)
- **Keep all**: No decay, all at 1.0 forever

---

## Global Preferences

### File: `~/.mind/preferences.json`

```json
{
  "version": 1,
  "logging_level": "balanced",
  "auto_promote": true,
  "retention_mode": "smart",
  "created": "2025-12-18",
  "last_project": "/path/to/last/project"
}
```

### Migration

- On `mind init`, check for `~/.mind/preferences.json`
- If exists, offer to reuse
- If not, ask questions and create

---

## Project Config

### File: `.mind/config.json`

```json
{
  "version": 2,
  "logging": {
    "level": "balanced",
    "auto_categorize": true
  },
  "session": {
    "auto_promote": true,
    "promote_threshold": 0.5,
    "compaction_enabled": true
  },
  "memory": {
    "retention_mode": "smart",
    "decay_period_days": 30,
    "decay_rate": 0.1,
    "min_relevance": 0.2
  },
  "health": {
    "auto_repair": true,
    "check_updates": true
  },
  "stack": {
    "detected": "claude-code",
    "config_file": "CLAUDE.md"
  }
}
```

---

## Implementation Plan

### Phase 1: Foundation & Tests (No Breaking Changes)

**Goal:** Add test infrastructure, don't change behavior yet.

1. **Add unit tests for existing functions:**
   - `test_session.py`: Test `update_session_section`, `parse_session_section`
   - `test_config.py`: Test `load_config`, `save_config`
   - `test_categorization.py`: Test `auto_categorize_session_type`

2. **Add integration tests:**
   - `test_mind_log_integration.py`: Full flow of mind_log -> file write -> read back
   - `test_session_repair.py`: Test `repair_session_file`

3. **Verify all 157 existing tests still pass**

### Phase 2: Global Preferences

**Goal:** Add `~/.mind/preferences.json` support.

1. **New file:** `src/mind/preferences.py`
   - `load_global_preferences()`
   - `save_global_preferences()`
   - `get_default_preferences()`

2. **Tests:** `test_preferences.py`
   - Test load/save
   - Test defaults
   - Test migration from no prefs

3. **Update `mind init`:**
   - Check for existing preferences
   - Offer to reuse

### Phase 3: Interactive Setup

**Goal:** `mind init` asks questions.

1. **Update `cli.py`:**
   - Add interactive prompts (using `click.prompt` with choices)
   - Add `--quick` flag to skip
   - Save answers to both local config and global prefs

2. **Tests:** `test_cli_init.py`
   - Test interactive flow (mock input)
   - Test `--quick` mode
   - Test preference reuse

### Phase 4: Stack Detection & Injection

**Goal:** Auto-detect editor, inject Mind instructions.

1. **New file:** `src/mind/stack.py`
   - `detect_stack()` - Returns editor type
   - `get_config_file_for_stack()` - Returns path
   - `inject_mind_instructions()` - Adds/updates instructions
   - `check_instructions_present()` - Validates setup

2. **Instruction templates:** `src/mind/templates.py`
   - `CLAUDE_MD_INSTRUCTIONS`
   - `CURSORRULES_INSTRUCTIONS`
   - `WINDSURFRULES_INSTRUCTIONS`
   - `GENERIC_INSTRUCTIONS`

3. **Tests:** `test_stack.py`
   - Test detection logic
   - Test injection (doesn't duplicate)
   - Test update detection

### Phase 5: Health System

**Goal:** Auto-repair, silent fixes, update checks.

1. **New file:** `src/mind/health.py`
   - `check_health()` - Returns list of issues
   - `repair_issues()` - Fixes what it can
   - `check_for_updates()` - Version check (cached)

2. **Integrate into `mind_recall()`:**
   - Run health check on recall
   - Auto-repair silently
   - Include update notice if available

3. **Tests:** `test_health.py`
   - Test each repair scenario
   - Test update check caching

### Phase 6: Logging Levels

**Goal:** Implement Efficient/Balanced/Detailed behavior.

1. **Update `handle_log()`:**
   - Check config for logging level
   - Filter based on level
   - Track for compaction (Detailed mode)

2. **New file:** `src/mind/compaction.py`
   - `should_compact()` - Check if compaction needed
   - `compact_session()` - Summarize Session -> Memory
   - `trigger_compaction()` - Called on gap/completion

3. **Tests:** `test_logging_levels.py`
   - Test each level's filtering
   - Test compaction logic

### Phase 7: Usage-Based Retention

**Goal:** Implement relevance scoring and decay.

1. **Update `src/mind/self_improve.py`:**
   - Add `relevance_score` to patterns
   - Add `reinforce_on_access()`
   - Add `apply_decay()`

2. **Update context generation:**
   - Sort by relevance
   - Filter by threshold

3. **Tests:** `test_retention.py`
   - Test reinforcement
   - Test decay over time
   - Test context filtering

### Phase 8: Cleanup Legacy Code

**Goal:** Remove unused code, simplify.

1. **Audit and remove:**
   - Unused functions
   - Dead config options
   - Redundant code paths

2. **Ensure all tests pass after cleanup**

3. **Update documentation**

---

## Migration Strategy

### For Existing Users

- Config v1 auto-migrates to v2 on first load
- Missing fields get defaults
- No data loss

### For New Users

- Fresh start with new config structure
- Interactive setup guides them

### Backwards Compatibility

- Keep function signatures stable
- Deprecate old functions with warnings before removing
- Phase 8 cleanup only after all tests green

---

## Success Criteria

1. **SESSION.md actually gets used** - Entries appear without manual effort
2. **No silent failures** - Every write either succeeds or reports why
3. **Setup takes < 1 minute** - 3 questions, done
4. **Works across editors** - Claude Code, Cursor, Windsurf all work
5. **Tests cover critical paths** - 90%+ coverage on new code
6. **Clean codebase** - No dead code, clear structure

---

## Files to Create/Modify

### New Files
- `src/mind/preferences.py` - Global preferences
- `src/mind/stack.py` - Stack detection & injection
- `src/mind/health.py` - Health checks & repair
- `src/mind/compaction.py` - Session compaction
- `tests/test_preferences.py`
- `tests/test_stack.py`
- `tests/test_health.py`
- `tests/test_logging_levels.py`
- `tests/test_retention.py`
- `tests/test_cli_init.py`

### Modified Files
- `src/mind/cli.py` - Interactive setup
- `src/mind/config.py` - New config structure
- `src/mind/templates.py` - Editor instruction templates
- `src/mind/mcp/server.py` - Logging levels, health integration
- `src/mind/self_improve.py` - Relevance scoring
- `src/mind/context.py` - Context priority by relevance

### Potentially Remove (Phase 8)
- Audit after implementation for dead code
