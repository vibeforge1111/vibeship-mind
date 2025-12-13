# Mind v2: Within-Session Memory (SESSION.md)

## The Problem

Mind's MEMORY.md + recall() solves cross-session memory. But Claude also forgets things within a single session:

- Suggests the same failed fix multiple times
- Loses track of discoveries made 30 minutes ago
- Rabbit holes into out-of-scope work
- Forgets constraints mentioned at session start

This is different from cross-session forgetting. It happens because long conversations push early context out of Claude's attention window.

---

## Solution: SESSION.md

A lightweight, ephemeral file that Claude maintains and checks during work.

```
.mind/
├── MEMORY.md    → Long-term (persists across sessions)
├── SESSION.md   → Short-term (this session only)
└── state.json   → Timestamps and hashes
```

---

## SESSION.md Format

```markdown
# Session: 2024-12-12

## Focus
What we're working on right now. The anchor to prevent drift.

## Constraints
Hard limits for this task. Check before going deep.

## Tried (didn't work)
Things attempted that failed. CHECK THIS BEFORE SUGGESTING FIXES.

## Discovered
Useful findings during this session. Context that matters.

## Open Questions
Unresolved items to address or ask user about.

## Out of Scope
Things we're explicitly NOT doing. Rabbit hole prevention.
```

---

## Example: Auth Implementation Session

```markdown
# Session: 2024-12-12

## Focus
Implement JWT authentication for API routes

## Constraints
- MVP only, no OAuth
- Must work in Safari iframe (cookie restrictions)
- Target: 2 hours
- Use existing User table

## Tried (didn't work)
- httpOnly cookies for JWT → Safari blocks in iframe, SameSite issues
- bcrypt with default rounds (10) → tests timeout, too slow for CI
- localStorage + Authorization header → works but XSS concerns noted

## Discovered
- User table missing `email_verified` column - migration needed
- Existing rateLimit middleware at `/lib/rateLimit.ts` - can reuse
- Test user in seed: test@example.com / password123
- Safari iframe requires `SameSite=None; Secure` but still inconsistent

## Open Questions
- Do we need refresh tokens for MVP or just longer expiry?
- Should failed login attempts be logged?

## Out of Scope
- Password reset flow
- Email verification
- OAuth/social login
- Admin roles
- 2FA
```

---

## CLAUDE.md Instructions

Add this to the project's CLAUDE.md:

```markdown
## Session Memory Protocol

Maintain `.mind/SESSION.md` during work to prevent loops and drift.

### Writing (do these as you work)
- When starting a task: Set "Focus" and "Constraints"
- When something fails: Add to "Tried (didn't work)" with WHY it failed
- When you discover something useful: Add to "Discovered"
- When questions arise: Add to "Open Questions"
- When user says "not now" or "out of scope": Add to "Out of Scope"

### Reading (check before acting)
- Before suggesting a fix: Check "Tried" - don't repeat failures
- Before going deep on something: Check "Focus" and "Out of Scope"
- When you feel stuck: Review "Discovered" for missed context

### Format
Keep entries brief. One line each. This file is for you, not documentation.

Bad:  "We attempted to use bcrypt with the default cost factor of 10 rounds, 
       but this caused the test suite to timeout because..."
Good: "bcrypt default rounds (10) → tests timeout"
```

---

## Lifecycle

```
Session Start
     ↓
recall() returns cross-session context from MEMORY.md
     ↓
Claude checks SESSION.md (may have stale content from last session)
     ↓
Claude clears or updates SESSION.md with current focus
     ↓
Claude works, updating SESSION.md as things happen:
  - Failures → "Tried"
  - Findings → "Discovered"  
  - Scope changes → "Focus" / "Out of Scope"
     ↓
Session ends (user leaves)
     ↓
Next session: recall() processes SESSION.md
  - Moves important learnings to MEMORY.md
  - Clears SESSION.md for fresh start
```

---

## Integration with recall()

Update the `recall()` function to handle SESSION.md:

```typescript
async function recall(input: RecallInput): Promise<RecallOutput> {
  // ... existing gap detection logic ...
  
  if (gapDetected) {
    // New session - process old SESSION.md before clearing
    const sessionPath = path.join(projectPath, '.mind/SESSION.md');
    
    if (existsSync(sessionPath)) {
      const oldSession = readFileSync(sessionPath, 'utf-8');
      
      // Extract learnings worth keeping
      const learnings = extractLearnings(oldSession);
      
      // Append important stuff to MEMORY.md
      if (learnings.length > 0) {
        appendToMemory(projectPath, learnings);
      }
      
      // Clear SESSION.md for new session
      writeFileSync(sessionPath, `# Session: ${today()}\n\n## Focus\n\n## Tried (didn't work)\n\n## Discovered\n\n## Open Questions\n\n## Out of Scope\n`);
    }
  }
  
  // Return both long-term and current session context
  return {
    context: generateContext(projectPath),
    session: readSessionFile(projectPath),
    // ... rest
  };
}
```

---

## What Gets Promoted to MEMORY.md

When a session ends, `recall()` scans SESSION.md for items worth keeping:

| SESSION.md Section | Promote to MEMORY.md? | As Type |
|-------------------|----------------------|---------|
| Focus | No | (ephemeral) |
| Constraints | No | (ephemeral) |
| Tried (didn't work) | Yes, if significant | Gotcha |
| Discovered | Yes, if reusable | Learning |
| Open Questions | Maybe, if unresolved | Issue |
| Out of Scope | No | (ephemeral) |

**Promotion logic (simple heuristic):**

```typescript
function extractLearnings(sessionContent: string): Learning[] {
  const learnings = [];
  
  // "Tried" items that mention specific tech become gotchas
  // "Safari blocks X" → Gotcha: Safari iframe cookie behavior
  const triedSection = parseSection(sessionContent, 'Tried');
  for (const item of triedSection) {
    if (hasSpecificTech(item) || hasEnvironmentDetail(item)) {
      learnings.push({ type: 'gotcha', content: item });
    }
  }
  
  // "Discovered" items about project structure persist
  // "rateLimit middleware at /lib/..." → Learning
  const discoveredSection = parseSection(sessionContent, 'Discovered');
  for (const item of discoveredSection) {
    if (hasFilePath(item) || hasProjectStructure(item)) {
      learnings.push({ type: 'learning', content: item });
    }
  }
  
  return learnings;
}
```

---

## User Nudges

When Claude starts looping, user can say:

- "Check SESSION.md" → Claude re-reads and adjusts
- "Add X to tried" → Claude updates the file
- "That's out of scope" → Claude adds to Out of Scope and refocuses

These are lightweight corrections, not full re-explanations.

---

## Two-Layer Memory Model

```
┌─────────────────────────────────────────────────────────────┐
│                      USER + CLAUDE                          │
└─────────────────────────────────────────────────────────────┘
                            ↓↑
┌─────────────────────────────────────────────────────────────┐
│  SESSION.md (Short-Term)                                    │
│  ├── Updated constantly during work                         │
│  ├── Checked before suggesting fixes                        │
│  ├── Cleared each new session                               │
│  └── Cost: FREE (just file edits)                          │
└─────────────────────────────────────────────────────────────┘
                            ↓↑
┌─────────────────────────────────────────────────────────────┐
│  MEMORY.md (Long-Term)                                      │
│  ├── Decisions, gotchas, learnings                          │
│  ├── Parsed once per session by recall()                    │
│  ├── Persists forever (with archiving)                      │
│  └── Cost: 1 tool call per session                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Expected Outcomes

| Problem | Before | After |
|---------|--------|-------|
| Repeating failed fixes | Common | Rare (check "Tried" first) |
| Rabbit holes | Common | Less common (check "Focus") |
| Losing discoveries | Common | Rare (written in "Discovered") |
| "Didn't we try that?" | Frustrating | "Yes, SESSION.md says it failed because X" |
| Cross-session amnesia | Total | Solved (MEMORY.md) |

---

## Limitations (Honest Assessment)

**Still depends on Claude following instructions:**
- Claude must write to SESSION.md when things fail
- Claude must check SESSION.md before suggesting
- Instructions in CLAUDE.md are sticky but not 100%

**User nudging still needed sometimes:**
- "Check SESSION.md" when loops happen
- "Add that to tried" to reinforce the habit

**Not bulletproof, but much better:**
- Estimated 70% reduction in within-session repetition
- Known location beats hoping Claude remembers
- Writing reinforces memory even without re-reading

---

## Implementation Checklist

- [ ] Add SESSION.md template to `mind init`
- [ ] Update CLAUDE.md template with session protocol
- [ ] Add SESSION.md processing to `recall()`
- [ ] Add promotion logic (SESSION → MEMORY)
- [ ] Add `mind.session()` tool for manual check (optional)
- [ ] Update docs

---

## Summary

MEMORY.md = What Claude learned across all sessions (long-term)
SESSION.md = What's happening right now (short-term)

Both are just files. Claude writes freely. MCP reads lazily.

Cost: Still just one tool call per session. Everything else is file I/O.
