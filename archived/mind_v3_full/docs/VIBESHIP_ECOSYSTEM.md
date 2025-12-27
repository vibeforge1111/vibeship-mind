# Vibeship Ecosystem Integration

<!-- doc-version: 1.0.0 | last-updated: 2025-12-14 -->

> **"You vibe. It ships."**
>
> Mind + Spawner = An intelligence that makes you better at building things people want.

---

## The Vision

Vibeship is not just tools - it's **compound intelligence for builders**.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                        VIBESHIP INTELLIGENCE                             │
│                                                                          │
│        The more you use it, the better it knows you.                     │
│        The better it knows you, the better you build.                    │
│        The better you build, the more value you create.                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### What We're Building

**Year 1**: Tools that help you ship faster
**Year 3**: Intelligence that knows your patterns
**Year 5**: A second brain that's built 50 products with you
**Year 10**: The way everyone builds software

---

## The Two Pillars

### Mind: The Coach

> "Claude that actually knows you"

Mind gives Claude **memory and self-improvement**:
- Remembers decisions across sessions
- Tracks what you're trying within sessions
- Learns your preferences, skills, blind spots
- Warns you before you repeat mistakes
- Grows smarter with every project

**The Aha Moment**: "How did Claude know I always forget that?"

### Spawner: The Expert

> "Claude with expert-level skills"

Spawner gives Claude **domain expertise**:
- Best practices Claude doesn't know by default
- Sharp edges that bite (gotchas, versioned)
- Guardrails that catch mistakes
- Templates for proven architectures
- Skill squads for complex tasks

**The Aha Moment**: "Claude just caught a bug I wouldn't have found for weeks"

---

## Why Together?

Alone, each tool is useful. Together, they're transformative.

| Scenario | Spawner Alone | Mind Alone | Both Together |
|----------|---------------|------------|---------------|
| New project | Best practices | Your history | Best practices + YOUR history |
| Hit a bug | Patterns to fix | You've seen this before | Pattern + "you hit this in project X" |
| Architecture choice | All options | Your preferences | Right option for YOU |
| Quality check | Generic guardrails | Your blind spots | Guardrails targeting YOUR gaps |

### The Magic Formula

```
SPAWNER knows:          MIND knows:              TOGETHER knows:
─────────────────       ────────────────         ─────────────────────────────
How to build auth   +   You forget tokens    =   Auth that handles YOUR gaps

React best practices +  You prefer hooks     =   Hooks-first patterns for YOU

Security patterns   +   You skip validation  =   Extra validation warnings

All architectures   +   Your past choices    =   Architecture YOU'LL maintain
```

---

## User Journey

### Day 1: Setup

```bash
# Install Mind
git clone https://github.com/vibeforge1111/vibeship-mind.git
cd vibeship-mind && uv sync && uv run mind init

# Add Spawner (remote MCP)
# Add to Claude's MCP config:
# "spawner": { "command": "npx", "args": ["-y", "mcp-remote", "https://mcp.vibeship.co"] }

# Tell Claude:
> "I have Mind and Spawner installed. Let's build something."
```

### Week 1: Learning Begins

```
PROJECT: Building a SaaS

SPAWNER: Loads SaaS template, auth skills, payments skills
         Sharp edges: RLS pitfalls, webhook gotchas, auth middleware

MIND: Blank slate - starts learning
      Captures: decisions made, approaches rejected, issues hit

END OF WEEK:
- Mind has 20 entries in MEMORY.md
- Hit 3 sharp edges that Spawner caught
- Made 5 architecture decisions Mind remembers
```

### Month 1: Patterns Emerge

```
PROJECT 2: Building a Marketplace

SPAWNER: Loads marketplace template, new skills for search/listings

MIND: Now has context from Project 1
      "Last time you chose Supabase + Next.js - use again?"
      "You hit auth middleware cold start - watch for it"
      "You prefer zustand for state - loading that skill"

RESULT: Project 2 starts 30% faster, fewer mistakes
```

### Month 6: Compound Intelligence

```
PROJECT 5: Complex AI App

SPAWNER: Full skill coverage, knows your stack
         Loads skills filtered by Mind's preference data

MIND: Has 100+ patterns from 4 projects
      "You've struggled with streaming before - here's what worked"
      "Your users complained about loading states - don't forget"
      "You tend to over-engineer - YAGNI reminder"

INTUITION: "This looks like the auth pattern from project 2.
           You hit token refresh issues there. Watch out."

RESULT: Ship in half the time with 2x quality
```

### Year 1+: Second Brain

```
MIND has learned:
├── 50 preferences (code style, workflow, communication)
├── 30 skills (approaches that work for you)
├── 20 blind spots (things you consistently miss)
├── 15 anti-patterns (things that don't work for you)
└── 100+ feedback entries (raw corrections)

SPAWNER has:
├── Full skill coverage for your stack
├── Your skill level per domain
├── Custom guardrails for your gaps
└── Sharp edges prioritized by your history

TOGETHER:
"Claude that's been your senior dev for a year"
```

---

## Integration Architecture

### How They Communicate

```
┌─────────────────────────────────────────────────────────────────┐
│                     SESSION START                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. mind_recall()                                                │
│     ├── Load MEMORY.md (project knowledge)                       │
│     ├── Load SESSION.md (working memory)                         │
│     ├── Load SELF_IMPROVE.md (personal patterns)                 │
│     ├── Detect intuitions (patterns triggering)                  │
│     └── Inject MIND:CONTEXT into CLAUDE.md                       │
│                                                                  │
│  2. spawner_load() [if available]                                │
│     ├── Read Mind context (preferences, blind spots)             │
│     ├── Detect stack (from package.json, files)                  │
│     ├── Load skills filtered by Mind preferences                 │
│     ├── Prioritize sharp edges by Mind blind spots               │
│     └── Inject SPAWNER:CONTEXT into CLAUDE.md                    │
│                                                                  │
│  3. Claude has unified intelligence                              │
│     ├── Project context (Mind)                                   │
│     ├── User patterns (Mind)                                     │
│     ├── Expert knowledge (Spawner)                               │
│     └── Personalized warnings (Both)                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
DURING SESSION:

User works ──► Claude uses Spawner skills
    │              │
    │              ├── Sharp edge hit? ──► Mind logs as BLIND_SPOT
    │              ├── Guardrail failed? ──► Mind logs pattern
    │              └── Skill helped? ──► Mind tracks preference
    │
    └──► Claude uses Mind memory
               │
               ├── User corrects? ──► Mind logs FEEDBACK
               ├── Decision made? ──► Mind logs to MEMORY.md
               └── Approach rejected? ──► Mind logs to SESSION.md


SESSION END:

Mind processes:
├── SESSION.md ──► MEMORY.md (valuable items promoted)
├── MEMORY.md ──► SELF_IMPROVE.md (KEY/SKILL/PREFERENCE promoted)
└── FEEDBACK patterns ──► new BLIND_SPOT/ANTI_PATTERN entries

Next session:
├── Mind provides richer context
├── Spawner loads more relevant skills
└── Both get better at helping YOU
```

### File Structure

```
~/.mind/                              # Mind: Global (cross-project)
├── SELF_IMPROVE.md                   # Your patterns
├── EDGES.md                          # Your personal gotchas
└── state.json                        # Global state

~/projects/my-app/
├── .mind/                            # Mind: Project
│   ├── MEMORY.md                     # Project knowledge
│   ├── SESSION.md                    # Working memory
│   ├── REMINDERS.md                  # Time/context reminders
│   └── state.json                    # Project state
│
├── CLAUDE.md                         # Both inject here
│   ├── <!-- MIND:CONTEXT -->         # Mind's injection
│   └── <!-- SPAWNER:CONTEXT -->      # Spawner's (future)
│
└── [your code]

Spawner Cloud (mcp.vibeship.co):
├── Skills database                   # Expert knowledge
├── Templates                         # Proven architectures
├── Sharp edges                       # Gotchas database
└── Guardrails                        # Quality checks
```

---

## Value Proposition

### For Vibe Coders (Non-Technical)

**Without Vibeship:**
- Build something, ship it, it breaks
- Don't know what you don't know
- Repeat same mistakes every project
- Code quality is luck

**With Vibeship:**
- Mind remembers what worked
- Spawner teaches best practices
- Compound learning over time
- Quality becomes systematic

### For Builders (Some Technical)

**Without Vibeship:**
- Know some patterns, miss others
- Architecture decisions are guesses
- Tech debt accumulates
- Each project starts fresh

**With Vibeship:**
- Mind tracks what you've learned
- Spawner fills knowledge gaps
- Architecture decisions informed by history
- Learning compounds across projects

### For Developers (Technical)

**Without Vibeship:**
- Context switching costs time
- Gotchas bite unexpectedly
- Same bugs in different projects
- Preferences not remembered

**With Vibeship:**
- Mind maintains context
- Spawner surfaces gotchas proactively
- Patterns prevent repeat bugs
- Preferences applied automatically

### For Teams (Future)

**Without Vibeship:**
- Knowledge silos
- Onboarding is slow
- Different standards per person
- Best practices not shared

**With Vibeship:**
- Shared project memory (MEMORY.md in git)
- Personal learning preserved (SELF_IMPROVE.md)
- Team skills layer (shared best practices)
- Faster onboarding via project context

---

## Use Cases

### Building a SaaS

```
USER: "I want to build a SaaS for team collaboration"

SPAWNER:
├── Template: SaaS starter (Next.js, Supabase, Stripe)
├── Skills: auth-complete, payments-complete, realtime-sync
├── Sharp edges: RLS policies, webhook handling, middleware auth
└── Guardrails: security checks, production readiness

MIND:
├── Memory: "Last SaaS you built, users complained about slow loads"
├── Preference: "You prefer Server Components for data fetching"
├── Blind spot: "You forget loading states"
└── Intuition: "Watch for N+1 queries - you hit this before"

RESULT: SaaS that's secure, performant, and avoids YOUR past mistakes
```

### Debugging Production Issues

```
USER: "My app is crashing in production but works locally"

SPAWNER:
├── Skills: production-debugging, error-handling
├── Sharp edges: env variable differences, build optimizations
└── Checklist: common prod vs dev differences

MIND:
├── Memory: "Similar issue in project-x was missing env var"
├── Session: "You've been assuming DATABASE_URL is set"
└── Pattern: "You've had 3 prod issues from env vars"

RESULT: Find issue in minutes, not hours
```

### UI/UX Polish

```
USER: "Make this dashboard look professional"

SPAWNER:
├── Skills: tailwind-ui, accessibility-patterns, responsive-design
├── Patterns: dashboard layouts, data visualization, loading states
└── Sharp edges: CLS issues, focus management, color contrast

MIND:
├── Feedback: "Users said buttons were too small on mobile"
├── Preference: "You like minimal design with clear hierarchy"
├── Blind spot: "You often forget dark mode"
└── Memory: "Dashboard in project-y got good feedback"

RESULT: Dashboard that's accessible, responsive, and avoids past complaints
```

### Scaling Architecture

```
USER: "My app is getting slow with more users"

SPAWNER:
├── Skills: performance-optimization, caching-patterns, database-indexing
├── Sharp edges: N+1 queries, unindexed columns, cache invalidation
└── Patterns: read replicas, edge caching, lazy loading

MIND:
├── Memory: "Last scaling issue was solved with edge caching"
├── Decision: "You chose Vercel for edge functions"
├── Blind spot: "You forget to add database indexes"
└── Skill: "You prefer Redis for caching"

RESULT: Scaled architecture based on what worked for YOU before
```

---

## The Billion Dollar Vision

### Why This Matters

The best products are built by people who:
1. **Know what they don't know** - Spawner fills gaps
2. **Learn from mistakes** - Mind remembers
3. **Compound their learning** - Both together
4. **Build for users, not ego** - Problem validation
5. **Ship quality consistently** - Guardrails + patterns

### The Compounding Effect

```
Projects Shipped    Learning Accumulated    Quality Level
─────────────────   ────────────────────    ─────────────
1                   10 patterns             Beginner
5                   50 patterns             Competent
15                  200 patterns            Proficient
50                  1000 patterns           Expert
100                 5000 patterns           Master

With Mind + Spawner, you get to "Expert" in 2 years instead of 10.
```

### The Moat

Everyone else:
- **ChatGPT**: Smart but forgets you
- **Cursor**: Fast but no learning
- **Copilot**: Autocomplete, not architect
- **Devin**: Autonomous but generic

**Vibeship**: Intelligence that grows WITH you
- Knows your patterns
- Knows your blind spots
- Knows your users
- Knows your code
- Gets better every day

---

## Roadmap

### Phase 1: Standalone Excellence (Now)

**Mind V1:**
- [x] SESSION.md - within-session memory
- [x] MEMORY.md - cross-session memory
- [ ] SELF_IMPROVE.md - cross-project learning
- [ ] Proactive intuition system

**Spawner V2:**
- [x] Unified skills (V1 + V2)
- [x] Sharp edges system
- [x] Guardrails
- [x] Skill level detection

### Phase 2: Awareness (V1.0)

- [ ] Mind detects Spawner availability
- [ ] Spawner detects Mind availability
- [ ] Documented combined setup
- [ ] Cross-promotion in READMEs

### Phase 3: Context Sharing (V1.1)

- [ ] Mind exposes preferences API
- [ ] Spawner exposes stack detection
- [ ] Shared blind spot format
- [ ] Cross-tool intuition

### Phase 4: Learning Loop (V1.2)

- [ ] Sharp edge hits -> Mind blind spots
- [ ] Mind corrections -> Spawner skill level
- [ ] Bidirectional tracking
- [ ] Combined warnings

### Phase 5: Unified Experience (V2.0)

- [ ] Single `vibeship_load()` coordinator
- [ ] Unified context injection
- [ ] Combined CLI
- [ ] Shared cloud sync (optional)

---

## For Contributors

### Adding Mind ↔ Spawner Integration

**In Mind (when Spawner is available):**
```python
# In mind_recall()
def check_spawner_availability():
    """Check if Spawner MCP is available."""
    # Look for spawner tools in MCP registry
    pass

def enrich_context_with_spawner(context, spawner_data):
    """Add Spawner stack detection to Mind context."""
    # Use stack to filter SELF_IMPROVE patterns
    pass
```

**In Spawner (when Mind is available):**
```typescript
// In spawner_load()
async function checkMindAvailability(): Promise<boolean> {
  // Check if Mind MCP is available
}

async function loadMindPreferences(): Promise<UserPreferences> {
  // Call mind_recall() and extract preferences
}

async function filterSkillsByPreferences(skills: Skill[], prefs: UserPreferences): Promise<Skill[]> {
  // Prioritize skills matching user preferences
}
```

### Testing Integration

```bash
# Test Mind alone
uv run mind doctor

# Test Spawner alone
# (via Claude with spawner MCP)

# Test together
# Start session, verify both contexts injected
# Check that Mind preferences affect Spawner skill loading
# Check that Spawner sharp edge hits appear in Mind
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Both tools installed | >30% of users | Install analytics |
| Cross-tool usage | >50% when both present | Tool call correlation |
| Blind spot prevention | >30% caught by Mind first | Warning comparison |
| Skill relevance | >80% loaded skills used | Skill -> action tracking |
| Time to ship | 30% faster with both | Project duration |
| User satisfaction | >4.5 stars | Feedback surveys |

---

## Join the Ecosystem

**Use Vibeship:**
- [Mind](https://github.com/vibeforge1111/vibeship-mind) - Memory for Claude
- [Spawner](https://mcp.vibeship.co) - Skills for Claude

**Contribute:**
- Report issues on GitHub
- Suggest skills for Spawner
- Share patterns that worked
- Build on top of the platform

**Connect:**
- Twitter: [@meta_alchemist](https://x.com/meta_alchemist)
- Website: [vibeship.co](https://vibeship.co)

---

*"You vibe. It ships."*

*The Vibeship ecosystem - building the future of how software gets made.*
