# SELF_IMPROVE Architecture Specification

<!-- doc-version: 1.0.0 | last-updated: 2025-12-14 -->

> **Scope**: This document specifies the self-improvement layer for Mind - the "learning" system that makes Claude better at helping YOU over time.

---

## Executive Summary

Mind currently has two memory layers:
- **SESSION.md** - Within-session working memory (ephemeral)
- **MEMORY.md** - Project-specific permanent knowledge

This document adds a third layer:
- **SELF_IMPROVE.md** - Cross-project meta-learning (global, in `~/.mind/`)

The key insight: **Proactive Intuition** - Claude that predicts and warns based on YOUR patterns, not just recalls facts. The aha moment: "Claude actually knows me now."

---

## Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SELF_IMPROVE.md                             │
│                  (~/.mind/SELF_IMPROVE.md)                      │
│                                                                 │
│  Cross-project meta-learning: preferences, skills, blind spots │
│  Synced across all projects. Tagged by stack.                  │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ Promotes KEY/SKILL/PREFERENCE markers
                              │
┌─────────────────────────────────────────────────────────────────┐
│                       MEMORY.md                                 │
│                  (.mind/MEMORY.md per project)                  │
│                                                                 │
│  Project-specific: decisions, learnings, gotchas, progress      │
│  Permanent. Version controlled.                                │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ Promotes on session gap (30 min)
                              │
┌─────────────────────────────────────────────────────────────────┐
│                       SESSION.md                                │
│                  (.mind/SESSION.md per project)                 │
│                                                                 │
│  Working memory: experience, blockers, rejected, assumptions    │
│  Ephemeral. Cleared each session.                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## SELF_IMPROVE.md - The Global Learning Layer

### Purpose

Store cross-project knowledge that improves Claude's ability to help this specific user:
- Communication preferences
- Reusable problem-solving skills
- Known blind spots to watch for
- Anti-patterns to avoid
- Raw feedback for pattern extraction

### Location

```
~/.mind/
├── SELF_IMPROVE.md    # Global learnings
├── EDGES.md           # Cross-project gotchas (existing)
└── state.json         # Global state
```

### File Structure

```markdown
<!-- MIND SELF-IMPROVE - Global meta-learning across projects -->
<!-- Keywords: SKILL:, PREFERENCE:, BLIND_SPOT:, ANTI_PATTERN:, FEEDBACK: -->

# Self-Improvement

## Preferences
<!-- How this user likes to work -->

PREFERENCE: [communication] prefers concise responses, no emojis unless requested
PREFERENCE: [code-style] uses single quotes in Python, double in JS
PREFERENCE: [workflow] likes TDD approach, test first

## Skills
<!-- Reusable approaches that work for this user -->

SKILL: [debugging:python] add print(f"DEBUG: {var=}") statements, not logging
SKILL: [architecture:react] prefer hooks over classes, zustand over redux
SKILL: [git:workflow] squash commits on feature branches

## Blind Spots
<!-- Patterns this user tends to miss -->

BLIND_SPOT: [error-handling] often forgets to handle network timeouts
BLIND_SPOT: [security] tends to skip input validation on internal APIs
BLIND_SPOT: [testing] usually skips edge case tests for empty arrays

## Anti-Patterns
<!-- Things to avoid for this user -->

ANTI_PATTERN: [overengineering] tends to add abstraction layers too early
ANTI_PATTERN: [scope-creep] "while we're here" leads to 3x scope
ANTI_PATTERN: [premature-optimization] optimizes before profiling

## Feedback Log
<!-- Raw corrections for pattern extraction -->
<!-- Format: FEEDBACK: [date] context -> correction -->

FEEDBACK: [2025-12-14] suggested complex solution -> user wanted simple approach
FEEDBACK: [2025-12-13] used emojis in code comments -> user prefers no emojis
```

### Categories Explained

| Category | What It Captures | Example |
|----------|-----------------|---------|
| **Preferences** | Communication style, code conventions, workflow habits | "prefers TypeScript strict mode" |
| **Skills** | Reusable approaches tagged by stack | "SKILL: [api:rest] always version URLs /v1/..." |
| **Blind Spots** | Patterns user consistently misses | "forgets null checks on optional fields" |
| **Anti-Patterns** | Things that don't work for this user | "abstract base classes overcomplicate" |
| **Feedback Log** | Raw corrections for pattern mining | "said X was wrong, wanted Y instead" |

### Stack Tags

Skills and patterns are tagged with stack identifiers for filtered retrieval:

```
[python], [javascript], [react], [fastapi], [postgres]
[debugging], [architecture], [testing], [git], [deployment]
[api:rest], [api:graphql], [frontend], [backend]
```

When `mind_recall()` runs, it filters SELF_IMPROVE.md by the project's detected stack.

---

## Proactive Intuition System

### The Core Innovation

Standard memory: "What did we decide?"
Proactive intuition: "Based on your patterns, watch out for X"

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROACTIVE INTUITION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. PATTERN RADAR                                               │
│     - Scans current context (SESSION.md, recent messages)       │
│     - Matches against SELF_IMPROVE.md patterns                  │
│     - Detects: blind spots activating, anti-patterns emerging   │
│                                                                 │
│  2. INTUITION INJECTION                                         │
│     - Adds warnings/predictions to mind_recall() output         │
│     - Format: "## Intuition" section in context                 │
│     - Triggered by pattern confidence threshold                 │
│                                                                 │
│  3. FEEDBACK CAPTURE                                            │
│     - Detects when user corrects Claude                         │
│     - Logs to FEEDBACK section of SELF_IMPROVE.md               │
│     - Periodic pattern extraction from feedback log             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Pattern Radar Logic

```python
def detect_intuitions(session_context: str, self_improve: dict) -> list[str]:
    """Scan for patterns that should trigger warnings."""
    intuitions = []

    # Check blind spots
    for blind_spot in self_improve['blind_spots']:
        if blind_spot.trigger_pattern in session_context:
            intuitions.append(f"WATCH: {blind_spot.description}")

    # Check anti-patterns
    for anti_pattern in self_improve['anti_patterns']:
        if anti_pattern.trigger_pattern in session_context:
            intuitions.append(f"AVOID: {anti_pattern.description}")

    # Check applicable skills
    for skill in self_improve['skills']:
        if skill.stack_tag in project_stack:
            intuitions.append(f"TIP: {skill.description}")

    return intuitions
```

### Intuition Output Format

When `mind_recall()` detects relevant patterns:

```markdown
## Intuition

Based on your patterns:
- WATCH: You tend to skip error handling on network calls - this looks like API code
- AVOID: "While we're here" detected - check if this expands scope
- TIP: For Python debugging, you prefer print(f"DEBUG: {var=}") over logging
```

### Feedback Capture Protocol

Claude should capture feedback when:

| Trigger | Action |
|---------|--------|
| User says "no", "not like that", "I meant..." | Log correction to FEEDBACK |
| User explicitly corrects code style | Log preference to FEEDBACK |
| User rejects suggested approach | Log anti-pattern to FEEDBACK |
| User points out missed issue | Log blind spot to FEEDBACK |

Capture format:
```
mind_log("user corrected: suggested X -> wanted Y", type="decision")
```

This gets promoted to SELF_IMPROVE.md with `FEEDBACK:` marker.

---

## Data Flow

### Session to Memory (Existing)

```
SESSION.md → (30 min gap) → MEMORY.md

Promotion rules:
- Rejected approaches with tech patterns → decisions
- Discoveries with file paths → learnings
- Blockers with error codes → problems
```

### Memory to Self-Improve (New)

```
MEMORY.md → (on session end) → SELF_IMPROVE.md

Promotion rules:
- KEY: markers → Always promote
- SKILL: markers → Promote with stack tag
- PREFERENCE: markers → Promote to preferences
- Patterns detected in feedback → Extract and promote
```

### Self-Improve to Context (New)

```
SELF_IMPROVE.md → (mind_recall) → CLAUDE.md context

Injection rules:
- Filter by project stack
- Include top 5 most relevant skills
- Include all blind spots (they're warnings)
- Include recent feedback (last 10)
- Add Intuition section if patterns detected
```

### Full Flow Diagram

```
User works with Claude
         │
         ▼
┌─────────────────┐
│  SESSION.md     │◄──── mind_log(type="experience/blocker/rejected/assumption")
│  (working)      │
└────────┬────────┘
         │ 30 min gap
         ▼
┌─────────────────┐
│  MEMORY.md      │◄──── mind_log(type="decision/learning/problem/progress")
│  (project)      │
└────────┬────────┘
         │ KEY/SKILL/PREFERENCE markers
         ▼
┌─────────────────┐
│ SELF_IMPROVE.md │◄──── Feedback patterns extracted
│  (global)       │
└────────┬────────┘
         │ mind_recall()
         ▼
┌─────────────────┐
│  CLAUDE.md      │ ← Injected: context + intuitions
│  (delivered)    │
└─────────────────┘
```

---

## Use Cases

### Use Case 1: Learning User Preferences

**Scenario**: User consistently uses single quotes in Python.

1. Claude suggests code with double quotes
2. User changes to single quotes
3. Claude detects correction, logs: `FEEDBACK: [2025-12-14] used double quotes -> user changed to single`
4. After 3 similar corrections, Claude extracts pattern
5. Promotes to: `PREFERENCE: [code-style:python] uses single quotes for strings`
6. Next project, `mind_recall()` includes this preference
7. Claude uses single quotes automatically

### Use Case 2: Detecting Blind Spots

**Scenario**: User often forgets error handling on fetch calls.

1. Over several sessions, feedback log shows:
   - "forgot try/catch on API call"
   - "no timeout handling"
   - "missing error state in UI"
2. Pattern extraction detects: API + error handling
3. Promotes to: `BLIND_SPOT: [error-handling:api] tends to skip error handling on network calls`
4. Next time user works on API code:
5. `mind_recall()` returns: `WATCH: You tend to skip error handling on network calls`
6. Claude proactively suggests error handling

### Use Case 3: Reusable Skills

**Scenario**: User has a debugging approach that works for them.

1. User says "I like to add print statements with f-strings for debugging"
2. Claude logs: `SKILL: [debugging:python] add print(f"DEBUG: {var=}") statements`
3. Next Python project, skill is included in context
4. Claude uses this approach automatically when debugging

### Use Case 4: Preventing Anti-Patterns

**Scenario**: User tends to over-engineer.

1. Multiple feedback entries show:
   - "this is too complex, just do X"
   - "we don't need an abstraction here"
   - "YAGNI - remove the factory"
2. Pattern extraction detects: complexity, abstraction, unnecessary
3. Promotes to: `ANTI_PATTERN: [overengineering] tends to add abstraction layers too early`
4. When Claude is about to suggest an abstraction:
5. `mind_recall()` returns: `AVOID: You've told me to avoid over-engineering`
6. Claude suggests simpler approach first

---

## Sync Architecture

### Focus: LOCAL First

This V1 focuses entirely on local operation:

```
Local Machine
├── ~/.mind/
│   ├── SELF_IMPROVE.md    # Global learnings
│   ├── EDGES.md           # Global gotchas
│   └── state.json         # Global state
│
└── ~/projects/
    ├── project-a/.mind/
    │   ├── MEMORY.md      # Project-specific
    │   └── SESSION.md     # Ephemeral
    │
    └── project-b/.mind/
        ├── MEMORY.md
        └── SESSION.md
```

### Future: Cloud Perspective

When cloud sync is added (V2+), the architecture supports:

```
Option C: Hybrid Sync (Recommended for V2)

PROJECT MEMORY (Git-based):
├── .mind/MEMORY.md        # Shared via git
├── .mind/config.json      # Shared via git
└── .mind/SESSION.md       # NOT committed (in .gitignore)

PERSONAL MEMORY (User's choice):
├── ~/.mind/SELF_IMPROVE.md   # Dropbox/iCloud/dotfiles
├── ~/.mind/EDGES.md          # Dropbox/iCloud/dotfiles
└── ~/.mind/state.json        # Local only
```

### Future: Team Considerations

Team sync would require:
- Shared project memory via git (already supported)
- Personal learning isolation (SELF_IMPROVE.md stays personal)
- Optional "team skills" layer (shared best practices)

Not designed in V1 - noted for future.

---

## Risks and Mitigations

### Risk 1: Secrets in Git (HIGH)

**Risk**: User accidentally commits sensitive data to MEMORY.md which is tracked in git.

**Mitigation**:
- SESSION.md is always .gitignored (ephemeral)
- MEMORY.md default: Add to .gitignore, require explicit opt-in to share
- Add warning in init: "MEMORY.md is private by default. To share with team, remove from .gitignore"
- Future: Add secret scanning before promotion

**Ruleset**:
```python
# In mind init
GITIGNORE_ENTRIES = [
    ".mind/SESSION.md",
    ".mind/state.json",
    ".mind/MEMORY.md",  # Private by default
]
```

### Risk 2: Pattern Corruption Cascade (HIGH)

**Risk**: Bad pattern gets promoted, affects all future projects.

**Mitigation**:
- Require 3+ similar feedback entries before pattern extraction
- Add confidence scores to patterns
- Decay unused patterns (reduce weight if not triggered in 30 days)
- Manual review: `mind patterns` CLI to see/edit learned patterns
- Nuclear option: `mind reset-patterns` to clear SELF_IMPROVE.md

**Ruleset**:
```python
PATTERN_EXTRACTION_THRESHOLD = 3  # Min similar feedback entries
PATTERN_DECAY_DAYS = 30           # Days before weight reduction
PATTERN_MIN_CONFIDENCE = 0.7      # Min score to surface
```

### Risk 3: Feedback Misinterpretation (MEDIUM)

**Risk**: Claude logs incorrect feedback, learns wrong pattern.

**Mitigation**:
- Log raw feedback, not interpretations
- Keep feedback log for audit trail
- Patterns require human-visible reasoning
- Add `mind feedback` CLI to review recent captures

**Ruleset**:
```
FEEDBACK entries must include:
- Context (what was happening)
- Original (what Claude did)
- Correction (what user wanted)
- NO interpretation of why
```

### Risk 4: Over-Personalization (MEDIUM)

**Risk**: Claude becomes too rigid, doesn't adapt to new contexts.

**Mitigation**:
- Preferences are hints, not rules
- Stack filtering ensures relevance
- Context can override patterns
- "In this case..." in user message overrides learned patterns

**Ruleset**:
```
Pattern application priority:
1. Explicit user instruction (this message)
2. Project-specific MEMORY.md
3. Global SELF_IMPROVE.md patterns
4. Claude defaults
```

### Risk 5: Context Bloat (MEDIUM)

**Risk**: Too many patterns make context too long.

**Mitigation**:
- Stack filtering (only relevant patterns)
- Top-N selection (max 5 skills, all blind spots, 10 recent feedback)
- Intuition section only when triggered
- Total budget: 500 tokens for SELF_IMPROVE context

**Ruleset**:
```python
SELF_IMPROVE_CONTEXT_BUDGET = 500  # tokens
MAX_SKILLS_IN_CONTEXT = 5
MAX_FEEDBACK_IN_CONTEXT = 10
INCLUDE_ALL_BLIND_SPOTS = True     # These are warnings
```

### Risk 6: User Friction (LOW)

**Risk**: Users need to manually set up sync for ~/.mind/.

**Mitigation**:
- Document simple options (Dropbox folder, dotfiles repo)
- `mind sync-setup` wizard (future)
- Works perfectly fine without sync (just local to machine)

### Risk 7: Merge Conflicts (LOW)

**Risk**: MEMORY.md conflicts when multiple people edit.

**Mitigation**:
- Append-only format reduces conflicts
- Date-stamped entries for ordering
- Standard git conflict resolution
- SESSION.md never committed (no conflict possible)

### Risk 8: Stale Patterns (LOW)

**Risk**: User's preferences change but old patterns persist.

**Mitigation**:
- last_used timestamps on patterns
- Weight decay over time
- `mind review-patterns` periodic prompt
- Set reminder: `mind remind "review learned patterns" "in 30 days"`

---

## SELF_IMPROVE.md Template

```markdown
<!-- MIND SELF-IMPROVE - Global meta-learning across projects -->
<!-- Keywords: SKILL:, PREFERENCE:, BLIND_SPOT:, ANTI_PATTERN:, FEEDBACK: -->
<!-- Created: {date} | Last processed: {date} -->

# Self-Improvement

## Preferences
<!-- How this user likes to work. Format: PREFERENCE: [category] description -->


## Skills
<!-- Reusable approaches. Format: SKILL: [stack:context] description -->


## Blind Spots
<!-- Patterns to watch for. Format: BLIND_SPOT: [category] description -->


## Anti-Patterns
<!-- Things to avoid. Format: ANTI_PATTERN: [category] description -->


## Feedback Log
<!-- Raw corrections. Format: FEEDBACK: [date] context -> correction -->


---

<!-- Pattern metadata (machine-readable) -->
<!-- pattern_count: 0 | last_extraction: never | schema_version: 1 -->
```

---

## Context Injection Format

When `mind_recall()` runs, SELF_IMPROVE data is injected into the CLAUDE.md context:

```markdown
## Self-Improvement: Active

### Your Preferences
- [code-style] single quotes in Python
- [workflow] TDD approach preferred

### Relevant Skills (python)
- SKILL: [debugging:python] print(f"DEBUG: {var=}") over logging
- SKILL: [testing:python] pytest fixtures over setup methods

### Watch For (Blind Spots)
- BLIND_SPOT: tends to skip error handling on API calls
- BLIND_SPOT: often forgets empty array edge cases

### Intuition
Based on your patterns:
- WATCH: This looks like API code - remember error handling
- TIP: For debugging, you prefer print statements

### Recent Feedback (last 3)
- [2025-12-14] suggested complex pattern -> user wanted simple approach
- [2025-12-13] used double quotes -> user prefers single
- [2025-12-12] added abstraction layer -> user said YAGNI
```

---

## Implementation Phases

### Phase 1: Foundation (V1.0)
- [ ] Create ~/.mind/ directory structure
- [ ] Create SELF_IMPROVE.md template
- [ ] Add SKILL/PREFERENCE/BLIND_SPOT/ANTI_PATTERN/FEEDBACK markers
- [ ] Update mind init to create global directory
- [ ] Basic promotion from MEMORY.md to SELF_IMPROVE.md

### Phase 2: Pattern Radar (V1.1)
- [ ] Implement pattern matching in mind_recall()
- [ ] Add Intuition section to context output
- [ ] Stack filtering for relevant patterns
- [ ] Confidence scoring for patterns

### Phase 3: Feedback Capture (V1.2)
- [ ] Add feedback detection heuristics
- [ ] Auto-log corrections to FEEDBACK section
- [ ] Pattern extraction from feedback (3+ threshold)
- [ ] Decay mechanism for unused patterns

### Phase 4: CLI Tools (V1.3)
- [ ] `mind patterns` - View learned patterns
- [ ] `mind feedback` - Review recent feedback
- [ ] `mind review-patterns` - Interactive pattern review
- [ ] `mind reset-patterns` - Nuclear option

### Phase 5: Polish (V2.0)
- [ ] Sync setup wizard
- [ ] Secret scanning
- [ ] Team patterns layer
- [ ] Cloud sync option

---

## Success Metrics

How do we know SELF_IMPROVE is working?

| Metric | Target | Measurement |
|--------|--------|-------------|
| Pattern accuracy | >80% useful | User doesn't override pattern |
| Blind spot catches | >50% prevented | Issues caught before user notices |
| Preference adoption | >90% correct | User doesn't correct style |
| Feedback capture | >70% of corrections | Compare user edits to logged feedback |
| Context relevance | <20% ignored | Patterns in context that get used |

---

## Appendix: Research Foundation

This design is informed by:

1. **Letta/MemGPT**: Hierarchical memory, self-editing via tool calls
2. **Mem0**: Vector-based extraction, 26% accuracy boost
3. **A-MEM**: Zettelkasten-style linking
4. **Production lessons**: Quality > quantity, verification gates, corruption cascades

Key insights applied:
- File-based > database (our identity)
- Lazy processing > real-time (mind_recall pattern)
- Stack-filtered > everything (relevance over volume)
- Proactive warnings > passive recall (the aha moment)

---

## Vibeship Ecosystem Integration

### The Vision: Vibeship Intelligence

Mind and Spawner together create something greater than either alone - **an intelligence that makes you better at building things people want**.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        THE VIBESHIP INTELLIGENCE                         │
│                                                                          │
│   SPAWNER                              MIND                              │
│   "The Expert"                         "The Coach"                       │
│                                                                          │
│   HOW to build                         WHO you are                       │
│   - Best patterns                      - Your blind spots                │
│   - Sharp edges                        - Your strengths                  │
│   - Quality checks                     - Your preferences                │
│   - Architecture templates             - Your learning history           │
│   - Problem validation                 - Your past pivots                │
│   - UX patterns                        - Your users' feedback            │
│                                                                          │
│                         ┌───────────┐                                    │
│                         │   VIBE    │                                    │
│                         │   CODER   │                                    │
│                         └───────────┘                                    │
│                              │                                           │
│                              ▼                                           │
│                    BILLION DOLLAR PRODUCTS                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### What Billion Dollar Products Have in Common

Looking at Stripe, Notion, Figma, Linear - they share:

1. **Obsessive problem focus** - Solve ONE thing exceptionally
2. **Quality as moat** - Better is the best marketing
3. **User experience first** - Every interaction matters
4. **Architectural foresight** - Built to scale from day one
5. **Learning loops** - Get better with every user

Mind + Spawner create ALL of these systematically.

---

### Spawner: The Expert

Spawner provides **domain expertise** Claude doesn't have by default:

| Capability | What It Does |
|------------|--------------|
| **Skills** | Structured knowledge for specific technologies (Next.js, Supabase, Stripe) |
| **Sharp Edges** | Gotchas that bite - versioned, situation-matched |
| **Guardrails** | Machine-runnable checks (security, patterns, production) |
| **Squads** | Pre-configured skill combinations for common tasks |
| **Templates** | Starting points with proven architecture |
| **Skill Levels** | Adapts guidance to vibe-coder/builder/developer/expert |

**Key MCP Tools:**
- `spawner_plan` - Plan and create projects
- `spawner_analyze` - Detect stack and recommend skills
- `spawner_skills` - Load specialist knowledge
- `spawner_validate` - Run quality checks
- `spawner_watch_out` - Surface relevant gotchas
- `spawner_unstick` - Help when stuck

---

### Mind: The Coach

Mind provides **personalized learning** that compounds over time:

| Capability | What It Does |
|------------|--------------|
| **Memory** | What you decided, what broke, what worked |
| **Session** | What you're trying, what failed, what you assumed |
| **Self-Improve** | Your preferences, skills, blind spots across all projects |
| **Intuition** | Proactive warnings based on YOUR patterns |
| **Reminders** | Time and context-triggered nudges |

**Key MCP Tools:**
- `mind_recall` - Load context + intuitions
- `mind_log` - Capture learnings in real-time
- `mind_session` - Check current working state
- `mind_blocker` - Log blockers + auto-search solutions
- `mind_search` - Find relevant past knowledge
- `mind_edges` - Check for gotchas before risky code

---

### Integration Points

#### 1. Skill Selection Enhancement

Mind informs which Spawner skills are most relevant for THIS user:

```
USER: "Let's add state management"

SPAWNER: Has skills for Redux, Zustand, Jotai, Context...

MIND: "PREFERENCE: [architecture:react] prefers zustand over redux"
      "FEEDBACK: [2025-11] said Redux was overkill for this"

RESULT: Spawner loads zustand skill, skips Redux
```

#### 2. Sharp Edge to Blind Spot Learning

When user hits a Spawner sharp edge, Mind learns it as a personal blind spot:

```
SPAWNER: Sharp edge triggered - "async client component"
         User wrote async function in 'use client' component

MIND: Logs → BLIND_SPOT: [nextjs] tends to write async client components

NEXT PROJECT: Mind warns BEFORE Spawner even checks
              "WATCH: This is a client component - remember async doesn't work here"
```

#### 3. Personalized Skill Level

Mind tracks expertise per domain, Spawner adapts guidance:

```
MIND: Knows from history:
      - Expert in Python (5 projects, few corrections)
      - Builder in React (2 projects, many blind spots)
      - Vibe-coder in DevOps (never done it)

SPAWNER: Adapts:
         - Python: Terse, expert-level guidance
         - React: More explanation, more guardrails
         - DevOps: Step-by-step, maximum hand-holding
```

#### 4. Problem Validation Loop

Spawner provides framework, Mind provides history:

```
USER: "I want to build a task management app"

SPAWNER: "Before we code - what problem are you solving that
         Linear, Notion, Asana don't?"

MIND: "You've built 3 apps that pivoted mid-development.
       Last time you wrote: 'Should have validated the problem first.'
       Want to do user research before coding?"

RESULT: User validates → builds something people actually want
```

#### 5. UX Excellence Loop

Spawner provides patterns, Mind provides your users' actual feedback:

```
USER: "Building the dashboard page"

SPAWNER: Loading UI patterns...
         - Accessibility guidelines
         - Loading state patterns
         - Responsive breakpoints

MIND: "Your users have complained about:
       - Buttons too small on mobile (project-a)
       - No loading indicators (project-b)
       - Confusing navigation (project-c)"

RESULT: Dashboard that avoids YOUR known UX pitfalls
```

#### 6. Architecture Compounding

Every architectural decision improves future projects:

```
PROJECT 1: User builds with bad state management
           → Pain, refactor, Mind learns

PROJECT 3: Mind warns about state before Spawner loads
           → User picks right pattern first time

PROJECT 10: User has compound wisdom of 10 architectures
            → Spawner skills + Mind patterns = senior architect
```

---

### The Compounding Effect

This is the billion dollar insight - **learning compounds**:

```
Year 1: Mind + Spawner make you 2x better
        - Spawner: Best practices from day 1
        - Mind: Remembers your first mistakes

Year 2: 5 projects shipped, 100 patterns learned
        - Spawner: Full skill coverage
        - Mind: Knows your blind spots

Year 3: 15 products, 500 patterns
        - Spawner: You use advanced skills
        - Mind: Predicts problems before they happen

Year 5: 50 products worth of wisdom
        - Your Claude is a senior developer who:
          • Knows every mistake you've ever made
          • Knows every pattern that worked
          • Knows your users' complaints
          • Knows your architectural preferences
          • Can validate problems before you build
          • Can predict what will go wrong
```

**This is the moat:**
- ChatGPT: Smart but doesn't know you
- Cursor: Fast but forgets everything
- Copilot: Autocomplete, not architect
- **Mind + Spawner: Intelligence that grows WITH you**

---

### Integration Architecture

#### File Structure

```
USER'S MACHINE
├── ~/.mind/                          # Mind: Global
│   ├── SELF_IMPROVE.md               # Cross-project learning
│   ├── EDGES.md                      # Personal gotchas
│   └── state.json
│
└── ~/projects/my-app/
    ├── .mind/                        # Mind: Project
    │   ├── MEMORY.md                 # Project decisions
    │   ├── SESSION.md                # Working memory
    │   └── state.json
    │
    ├── .spawner/                     # Spawner: Project (future)
    │   └── config.yaml               # Stack, skills, level
    │
    └── CLAUDE.md                     # Both inject here
        ├── <!-- MIND:CONTEXT -->     # Mind's injection
        └── <!-- SPAWNER:CONTEXT -->  # Spawner's injection

CLOUD
├── Spawner Skills API                # Expert knowledge
│   └── mcp.vibeship.co
│
└── Mind Cloud (future V2)            # Personal sync
    └── Optional premium feature
```

#### Context Injection Order

When Claude starts a session:

```
1. mind_recall()
   └── Loads: MEMORY.md, SESSION.md, SELF_IMPROVE.md
   └── Injects: MIND:CONTEXT with intuitions

2. spawner_load()
   └── Reads: Mind context (user preferences, blind spots)
   └── Loads: Relevant skills filtered by Mind data
   └── Injects: SPAWNER:CONTEXT with personalized skills

3. Claude has unified context
   └── Knows the project (Mind)
   └── Knows the user (Mind)
   └── Knows best practices (Spawner)
   └── Knows user's specific gaps (Mind + Spawner)
```

#### Data Flow Between Tools

```
┌──────────────────────────────────────────────────────────────────┐
│                         DATA FLOW                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  SPAWNER → MIND                                                   │
│  ─────────────                                                    │
│  • Sharp edge hits → BLIND_SPOT entries                          │
│  • Stack detection → Filter SELF_IMPROVE by stack                │
│  • Skill usage → Track which skills helped                       │
│  • Guardrail failures → Pattern for future warning               │
│                                                                   │
│  MIND → SPAWNER                                                   │
│  ─────────────                                                    │
│  • User preferences → Filter skill recommendations               │
│  • Blind spots → Prioritize relevant sharp edges                 │
│  • Skill level per domain → Adjust guidance depth                │
│  • Past decisions → Inform architecture choices                  │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

### Value Matrix

| User Goal | Spawner Provides | Mind Provides | Combined Result |
|-----------|------------------|---------------|-----------------|
| **Ship faster** | Templates, patterns, guardrails | What worked before, what to skip | 3x faster, better quality |
| **Better code** | Best practices, anti-patterns | YOUR mistakes to avoid | Clean code first time |
| **Great UI/UX** | UI patterns, accessibility | Your users' past complaints | UI that delights |
| **Solve real problems** | Problem validation framework | History of pivots, actual needs | Products people pay for |
| **Scale** | Architecture patterns | Your past scaling issues | Built to grow |
| **Maintain** | Code organization, testing | What confused you before | Future you understands |
| **Learn faster** | Expert knowledge on demand | Tracks what you've learned | Compound improvement |

---

### Integration Phases

#### Phase 1: Awareness (V1.0)
- [ ] Mind detects if Spawner MCP is available
- [ ] Spawner detects if Mind MCP is available
- [ ] Both check for each other on load/recall
- [ ] Document combined setup

#### Phase 2: Context Sharing (V1.1)
- [ ] Mind exposes user preferences API for Spawner
- [ ] Spawner exposes stack detection for Mind
- [ ] Shared project identity
- [ ] Cross-tool blind spot format

#### Phase 3: Learning Loop (V1.2)
- [ ] Spawner sharp edge hits → Mind blind spots
- [ ] Mind corrections → Spawner skill level adjustment
- [ ] Bidirectional improvement tracking
- [ ] Combined intuition system

#### Phase 4: Unified Experience (V2.0)
- [ ] Single `vibeship_load()` that coordinates both
- [ ] Unified context injection
- [ ] Combined CLI (`vibeship` command)
- [ ] Shared cloud sync (optional)

---

### The Aha Moments

What users will say:

> "Claude remembered that I always forget error handling on API calls,
> AND it loaded the exact error handling patterns I need. Before I even asked."

> "I started a new project and Claude already knew I prefer Zustand,
> use single quotes, and tend to over-engineer. It was like working
> with a colleague who actually knows me."

> "Spawner caught a security issue, and Mind remembered I'd had the
> same issue before. Now it warns me proactively on every project."

> "I've shipped 10 products with Mind + Spawner. My Claude is basically
> a senior developer who's worked with me for years. It knows my patterns
> better than I do."

---

### Success Metrics for Integration

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Cross-tool usage | >50% use both | Analytics on tool calls |
| Blind spot prevention | >30% caught by Mind before Spawner | Compare warnings |
| Skill relevance | >80% loaded skills used | Track skill → action |
| User preference accuracy | >90% correct | Corrections needed |
| Compound learning | 2x better by project 5 | Quality metrics over time |
| Time to ship | 30% faster with both | Project duration tracking |

---

*This document is the source of truth for SELF_IMPROVE architecture. Implementation should follow these specifications exactly.*
