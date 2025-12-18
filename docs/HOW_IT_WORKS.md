# How Mind Works

<!-- doc-version: 2.1.0 | last-updated: 2025-12-13 -->

Mind gives Claude persistent memory through simple markdown files. No database, no cloud, no friction.

---

## The Big Picture

```
┌─────────────────────────────────────────────────────────────┐
│                        YOUR PROJECT                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐         ┌─────────────┐                  │
│   │  CLAUDE.md  │◄────────│    Mind     │                  │
│   │  (context)  │ injects │   (MCP)     │                  │
│   └─────────────┘         └──────┬──────┘                  │
│                                  │                          │
│                    reads/writes  │                          │
│                                  ▼                          │
│   ┌─────────────────────────────────────────────────────┐  │
│   │                      .mind/                          │  │
│   │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │  │
│   │  │  MEMORY.md   │  │  SESSION.md  │  │REMINDERS  │  │  │
│   │  │  (permanent) │  │  (working)   │  │   .md     │  │  │
│   │  └──────────────┘  └──────────────┘  └───────────┘  │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Two-Layer Memory

```
┌────────────────────────────────────────────────────────────────┐
│                         MEMORY.md                              │
│                        (Permanent)                             │
├────────────────────────────────────────────────────────────────┤
│  Persists forever across all sessions                          │
│                                                                │
│  • Decisions    ->  "decided X because Y"                       │
│  • Learnings    ->  "learned that X", "TIL: X"                  │
│  • Problems     ->  "problem: X"                                │
│  • Progress     ->  "fixed: X"                                  │
│  • Gotchas      ->  Project-specific traps                      │
└────────────────────────────────────────────────────────────────┘
                              ▲
                              │ promotes valuable items
                              │ on session gap (>30 min)
                              │
┌────────────────────────────────────────────────────────────────┐
│                         SESSION.md                             │
│                         (Working)                              │
├────────────────────────────────────────────────────────────────┤
│  Cleared on new session, captures raw experience               │
│                                                                │
│  • Experience   ->  Raw moments, thoughts                       │
│  • Blockers     ->  Things stopping progress                    │
│  • Rejected     ->  What didn't work and why                    │
│  • Assumptions  ->  What I'm assuming true                      │
└────────────────────────────────────────────────────────────────┘
```

---

## Session Lifecycle

```
┌──────────────────────────────────────────────────────────────────┐
│                         SESSION FLOW                             │
└──────────────────────────────────────────────────────────────────┘

     ┌─────────────┐
     │   START     │
     │  (new chat) │
     └──────┬──────┘
            │
            ▼
    ┌───────────────┐      ┌─────────────────────────────────┐
    │ mind_recall() │─────►│  • Load MEMORY.md context       │
    │  CALL FIRST   │      │  • Check time since last active │
    └───────┬───────┘      │  • Detect session gap (>30 min) │
            │              └─────────────────────────────────┘
            │
            ▼
    ┌───────────────┐
    │  Gap > 30min? │
    └───────┬───────┘
            │
       ┌────┴────┐
       │         │
      YES        NO
       │         │
       ▼         │
┌─────────────┐  │
│ • Promote   │  │
│   learnings │  │
│ • Clear     │  │
│   SESSION   │  │
└──────┬──────┘  │
       │         │
       └────┬────┘
            │
            ▼
    ┌───────────────┐
    │ Claude works  │◄─────────────────────────────────┐
    └───────┬───────┘                                  │
            │                                          │
            ▼                                          │
    ┌───────────────┐      ┌─────────────────────┐    │
    │  mind_log()   │─────►│ Routes by type:     │    │
    └───────┬───────┘      │                     │    │
            │              │ SESSION.md:         │    │
            │              │  • experience       │    │
            │              │  • blocker          │    │
            │              │  • assumption       │    │
            │              │  • rejected         │    │
            │              │                     │    │
            │              │ MEMORY.md:          │    │
            │              │  • decision         │    │
            │              │  • learning         │    │
            │              │  • problem          │    │
            │              │  • progress         │    │
            │              └─────────────────────┘    │
            │                                          │
            └──────────────────────────────────────────┘
```

---

## mind_log() Routing

```
                        mind_log(message, type)
                                 │
                 ┌───────────────┴───────────────┐
                 │                               │
          ┌──────┴──────┐                 ┌──────┴──────┐
          │  SESSION.md │                 │  MEMORY.md  │
          │ (ephemeral) │                 │ (permanent) │
          └──────┬──────┘                 └──────┬──────┘
                 │                               │
    ┌────────────┼────────────┐     ┌────────────┼────────────┐
    │            │            │     │            │            │
    ▼            ▼            ▼     ▼            ▼            ▼
experience   blocker    rejected  decision  learning   progress
assumption                                   problem
```

---

## Promotion: What Gets Kept

When a new session starts, Mind automatically promotes valuable items:

```
SESSION.md                              MEMORY.md
┌────────────────────┐                 ┌────────────────────┐
│ ## Rejected        │                 │                    │
│                    │   promotes if   │ decided against:   │
│ - "Approach X -    │ ─────────────►  │ Approach X -       │
│    didn't scale"   │  has reasoning  │ didn't scale       │
│                    │                 │                    │
├────────────────────┤                 ├────────────────────┤
│ ## Experience      │                 │                    │
│                    │   promotes if   │ learned:           │
│ - "React hooks     │ ─────────────►  │ React hooks need   │
│    need cleanup"   │  has tech/path  │ cleanup            │
│                    │   or insight    │                    │
└────────────────────┘                 └────────────────────┘
```

---

## Reminders

```
┌─────────────────────────────────────────────────────────────┐
│                        REMINDERS                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  TIME-BASED                      CONTEXT-BASED              │
│  ───────────                     ─────────────              │
│                                                             │
│  "tomorrow"          ───┐    ┌───  "when I mention auth"    │
│  "in 3 days"            │    │     "when we work on API"    │
│  "next session"         │    │                              │
│  "2025-12-20"           │    │                              │
│                         ▼    ▼                              │
│                  ┌──────────────┐                           │
│                  │ mind_recall()│                           │
│                  │   surfaces   │                           │
│                  │  when due    │                           │
│                  └──────────────┘                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## MCP Tools (12 total)

```
┌─────────────────────────────────────────────────────────────┐
│                       CORE TOOLS                            │
├─────────────────────────────────────────────────────────────┤
│  mind_recall()     │  CALL FIRST - loads context            │
│  mind_log()        │  Log to session or memory              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      READING TOOLS                          │
├─────────────────────────────────────────────────────────────┤
│  mind_session()    │  Check current session state           │
│  mind_search()     │  Search past memories                  │
│  mind_status()     │  Check memory health                   │
│  mind_reminders()  │  List pending reminders                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      ACTION TOOLS                           │
├─────────────────────────────────────────────────────────────┤
│  mind_blocker()    │  Log blocker + auto-search memory      │
│  mind_remind()     │  Set time or context reminder          │
│  mind_edges()      │  Check for gotchas before coding       │
│  mind_checkpoint() │  Force process pending memories        │
│  mind_add_global_edge() │  Add cross-project gotcha         │
└─────────────────────────────────────────────────────────────┘
```

---

## Design Principles

```
┌────────────────────────────────────────────────────────────────┐
│  1. FILE IS THE MEMORY                                         │
│     MEMORY.md is source of truth, human-readable, git-tracked │
├────────────────────────────────────────────────────────────────┤
│  2. ZERO FRICTION                                              │
│     Claude writes naturally, Mind extracts meaning             │
├────────────────────────────────────────────────────────────────┤
│  3. LOOSE PARSING                                              │
│     Accept natural language, score confidence                  │
├────────────────────────────────────────────────────────────────┤
│  4. STATELESS MCP                                              │
│     Tools load and process on demand, no daemon                │
├────────────────────────────────────────────────────────────────┤
│  5. TWO LAYERS                                                 │
│     Permanent memory (MEMORY) + working buffer (SESSION)       │
└────────────────────────────────────────────────────────────────┘
```
