# Mind Dashboard Design

> "Reunion, not retrieval."

## Design Philosophy

Mind isn't a database. It's continuity. The dashboard should feel like reconnecting with a colleague who was there, not opening a filing cabinet.

**Emotional hierarchy:**
1. **Continuity** - "We have history together"
2. **Readiness** - "I remember, let's continue"
3. **Depth** - "Look what we've built"

## Color System

Extends vibeship palette with warmer accents for Mind's "presence" feeling.

### Node Colors (by entity type)
```
Decisions:    #E8C547  (warm gold)      - choices made together
Issues:       #F07167  (pink-coral)     - struggles faced
Sharp Edges:  #FFB020  (amber)          - warnings/gotchas
Episodes:     #A78BFA  (cool violet)    - stories/breakthroughs
Sessions:     #00C49A  (teal)           - active/current
```

### Text Hierarchy
```
Primary:      #e2e4e9  (off-white)      - "Last together yesterday"
Secondary:    #9aa3b5  (muted)          - stats, counts
Tertiary:     #6b7280  (dim)            - earned highlights
Warm accent:  #E8C547  (gold)           - emphasis words
```

### Background (inherited from vibeship)
```
Dark mode:    #0e1016
Light mode:   #e8e8e8
```

## Typography (inherited from vibeship)

```
Headings:     Instrument Serif, italic
Body/UI:      JetBrains Mono
Code:         JetBrains Mono
```

## Page Structure

### Routes
```
/                           Home (hero + project list)
/projects/:id               Project detail (default: Decisions tab)
/projects/:id/decisions     Decisions tab active
/projects/:id/issues        Issues tab active
/projects/:id/edges         Edges tab active
/projects/:id/episodes      Episodes tab active
/projects/:id/sessions      Sessions tab active
/search?q=safari            Search results
```

Two levels only. Items expand inline, not separate pages.

---

## Home Page

### Hero Section

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ┌─ NAV ────────────────────────────────────────────────────────────────┐  │
│  │  ◉ mind                                    [Projects ▾]  [●] theme   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│                        ┌─────────────────────┐                              │
│                        │                     │                              │
│              ·  ∘  ·   │   LIVING MIND       │   ·  ∘  ·                    │
│           ∘ ─────────  │   VISUALIZATION     │  ───────── ∘                 │
│              ·  ∘  ·   │   (~300px height)   │   ·  ∘  ·                    │
│                        │                     │                              │
│                        └─────────────────────┘                              │
│                                                                             │
│                      "Last together yesterday"              ← PRIMARY       │
│                                                                             │
│               23 sessions since October · 4 breakthroughs   ← SECONDARY     │
│                                                                             │
│         ┌───────────────────────────────────────┐                           │
│         │  Last time: Designing Mind dashboard  │           ← READINESS     │
│         │  Next step: "Implement hero section"  │                           │
│         └───────────────────────────────────────┘                           │
│                                                                             │
│                        [ Continue Session ]                 ← CTA           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Living Mind Visualization

Nodes represent actual memories from user's data:
- **Bright nodes** (recent): Full opacity, visible labels, soft glow halo
- **Dim nodes** (older): 40% opacity, no label, reveals on hover
- **Connection lines**: rgba(232, 197, 71, 0.15), pulse between related items
- **Center glow**: radial-gradient(#E8C547 10%, transparent 70%), breathing animation

**Animation:**
```css
/* Organic drift - nodes breathe, don't march */
@keyframes drift {
  0%, 100% { transform: translate(0, 0); }
  33%      { transform: translate(3px, -2px); }
  66%      { transform: translate(-2px, 3px); }
}
/* 8-12s duration, randomized per node, staggered start */

/* Connection pulse */
@keyframes pulse-connection {
  0%, 100% { opacity: 0.1; }
  50%      { opacity: 0.3; }
}
/* 3-4s duration */

/* Center glow breathe */
@keyframes breathe {
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50%      { opacity: 0.6; transform: scale(1.05); }
}
/* 6s duration */
```

### Stats Evolution

The message deepens as relationship grows:

**Week 1 (new user):**
```
"First session together"
Ready to start building context.
```

**Week 2:**
```
"Last together yesterday"
5 sessions · 3 decisions made
```

**Month 2:**
```
"Last together 3 hours ago"
23 sessions since October · 4 breakthroughs
```

**Month 6:**
```
"Last together 2 days ago"
89 sessions over 6 months · 12 breakthroughs · Remember the auth saga?
```

### Context-Aware CTA

| State | CTA |
|-------|-----|
| New user | "Start First Session" |
| Has history | "Continue Session" |
| Active session | "Return to Session" |
| Stale (2+ weeks) | "Pick Up Where We Left Off" |

### Project List

```
┌─────────────────────────────────────────────────────────────┐
│  YOUR PROJECTS                                              │
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │  vibeship-mind                          ACTIVE ●   │    │
│  │  ────────────────────────────────────────────────  │    │
│  │  5 decisions · 2 open issues · 1 edge              │    │
│  │                                                    │    │
│  │  Last: "Designing the dashboard"        yesterday  │    │
│  │  Next: "Implement hero section"                    │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │  vibeship-scanner                       3 days ago │    │
│  │  ────────────────────────────────────────────────  │    │
│  │  12 decisions · 4 issues · 3 edges                 │    │
│  │  Last: "Agent escalation flow"                     │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │  + New Project                                     │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
│  ─────────────────────────────────────────────────────     │
│  ◦ Global Edges (4)    ◦ Search All    ◦ Export           │
└─────────────────────────────────────────────────────────────┘
```

### Empty State (No Projects)

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│     No projects yet.                                       │
│     Mind learns as you work.                               │
│                                                            │
│     [ Start First Project ]                                │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## Project Detail Page

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Projects          vibeship-mind      ACTIVE ●   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  5 decisions · 2 open issues · 1 edge · 8 sessions         │
│  Last: "Designing the dashboard" · Next: "Implement hero"  │
│                                                             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                             │
│  [Decisions]  [Issues]  [Edges]  [Episodes]  [Sessions]    │
│       ●                                                     │
└─────────────────────────────────────────────────────────────┘
```

### Decisions Tab

```
┌────────────────────────────────────────────────────────────┐
│  ▼ Use JWT for auth                              2 days   │
│  ──────────────────────────────────────────────────────── │
│                                                           │
│  Context                                                  │
│  Building auth for Mind dashboard                         │
│                                                           │
│  Reasoning                                                │
│  Simpler than OAuth for MVP. No server needed.            │
│  Stateless, easy to implement.                            │
│                                                           │
│  Alternatives considered                                  │
│  ◦ OAuth → Too complex for single-user tool               │
│  ◦ Session cookies → Wanted stateless                     │
│                                                           │
│  Revisit if                                               │
│  Need refresh tokens or SSO                               │
│                                                           │
│  Related                                                  │
│  ◦ Issue: Safari CORS bug                    ● coral      │
│  ◦ Edge: Vercel crypto limitation            ● amber      │
│                                                           │
│  [Edit] [Delete]                              0.8 conf ●  │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  ▶ SQLite over Postgres                          1 week   │
└────────────────────────────────────────────────────────────┘
```

Gold accent (#E8C547). Confidence as filled dots.

**Empty state:**
```
No decisions recorded yet.
As you make choices, Mind remembers why.
```

### Issues Tab

```
┌────────────────────────────────────────────────────────────┐
│  [All]  [Open ●2]  [Resolved]                    filter   │
├────────────────────────────────────────────────────────────┤
│  ▼ Safari CORS bug                      OPEN    3 days   │
│  ──────────────────────────────────────────────────────── │
│                                                           │
│  Symptoms                                                 │
│  ◦ "Access-Control-Allow-Origin" error                   │
│  ◦ Works in Chrome, fails in Safari                      │
│                                                           │
│  Current theory                                           │
│  Safari stricter about credentials: 'include'            │
│                                                           │
│  Attempts                                                 │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 1. Added CORS headers to API         ✗ didn't help │  │
│  │ 2. Tried credentials: 'same-origin'  ✗ broke auth  │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  Blocked by                                               │
│  Need to test on real Safari device                       │
│                                                           │
│  Related                                                  │
│  ◦ Decision: Use JWT for auth            ● gold          │
│                                                           │
│  [Edit] [Mark Resolved]                     MAJOR        │
└────────────────────────────────────────────────────────────┘
```

Pink-coral accent (#F07167). Status: OPEN (coral), RESOLVED (muted). Severity: BLOCKING (red), MAJOR (coral), MINOR (muted).

**Empty state:**
```
No issues tracked.
Problems you work through will appear here.
```

### Edges Tab

```
┌────────────────────────────────────────────────────────────┐
│  ▼ Vercel Edge crypto limitation                  1 week │
│  ──────────────────────────────────────────────────────── │
│                                                           │
│  ⚠ Vercel Edge runtime doesn't support Node crypto       │
│                                                           │
│  Symptoms                                                 │
│  ◦ "crypto is not defined"                               │
│  ◦ "Cannot find module 'crypto'"                         │
│                                                           │
│  Root cause                                               │
│  Edge runtime is V8 isolate, not Node.js environment     │
│                                                           │
│  Workaround                                               │
│  Use Web Crypto API: crypto.subtle.digest() or           │
│  crypto.getRandomValues()                                │
│                                                           │
│  Related                                                  │
│  ◦ Decision: Use Web Crypto for tokens   ● gold          │
│                                                           │
│  Detection patterns                                       │
│  ◦ Context: edge, vercel                                 │
│  ◦ Code: import.*crypto                                  │
│                                                           │
│  [Edit] [Delete]                                          │
└────────────────────────────────────────────────────────────┘
```

Amber accent (#FFB020). Warning icon prominent.

**Empty state:**
```
No sharp edges recorded.
Gotchas and workarounds will appear here.
```

### Episodes Tab

```
┌────────────────────────────────────────────────────────────┐
│  EPISODES                                     3 stories   │
│  "The significant moments"                                │
├────────────────────────────────────────────────────────────┤
│  ▼ The Safari Auth Saga                          Dec 8   │
│  ──────────────────────────────────────────────────────── │
│                                                           │
│  "Finally figured out ITP was blocking cross-domain      │
│   cookies. Two hours of confusion, then breakthrough."   │
│                                                           │
│  What happened                                            │
│  Long debugging session focused on Safari auth. Kept     │
│  trying CORS fixes when the real issue was ITP.          │
│                                                           │
│  Outcome                                                  │
│  Resolved Safari auth. Discovered 1 new gotcha.          │
│                                                           │
│  Lessons learned                                          │
│  ◦ Check Safari ITP first for auth issues                │
│  ◦ After 2 hours stuck, question assumptions             │
│                                                           │
│  Artifacts created                                        │
│  ◦ Decision: Move auth to same domain    ● gold          │
│  ◦ Edge: Safari ITP limitation           ● amber         │
│                                                           │
│  From session: Dec 8, 2.5 hrs                            │
└────────────────────────────────────────────────────────────┘
```

Violet accent (#A78BFA). User's words quoted at top.

**Empty state:**
```
No episodes yet.
Significant sessions become stories over time.
```

### Sessions Tab

```
┌────────────────────────────────────────────────────────────┐
│  SESSIONS                                    8 total      │
├────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────┐   │
│  │  Dec 12                              ACTIVE ●      │   │
│  │  Designing the dashboard                           │   │
│  │  Started 2 hours ago                               │   │
│  └────────────────────────────────────────────────────┘   │
│                                                           │
│  ▼ Dec 10 · "HTTP API routes"                   45 min   │
│  ──────────────────────────────────────────────────────── │
│                                                           │
│  Summary                                                  │
│  Built FastAPI server with full CRUD for all entities.   │
│                                                           │
│  Progress                                                 │
│  ◦ Created 10 API routes                                 │
│  ◦ Added 42 tests                                        │
│  ◦ Fixed deps.py bug                                     │
│                                                           │
│  Artifacts                                                │
│  ◦ 2 decisions made                          ● ●         │
│  ◦ 1 issue resolved                          ●           │
│  ◦ 1 episode created                         ●           │
│                                                           │
│  Next steps                                               │
│  ◦ "Implement hero section"                              │
│                                                           │
│  Mood: productive                                         │
│                                                           │
│  ▶ Dec 8  · "Phase 2 intelligence"              2.5 hrs  │
│  ▶ Dec 5  · "MCP server setup"                  1.5 hrs  │
└────────────────────────────────────────────────────────────┘
```

Teal accent (#00C49A) for active. Sessions are chronological, most recent first.

**Empty state:**
```
No sessions yet.
Your work history will appear here.
```

---

## Search Results

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back                    Search: "safari"                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  4 results across 2 projects                               │
│                                                             │
│  vibeship-mind                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │ ● Decision: Move auth to same domain       gold    │   │
│  │ ● Issue: Safari CORS bug                   coral   │   │
│  │ ● Edge: Safari ITP blocks cookies          amber   │   │
│  └────────────────────────────────────────────────────┘   │
│                                                             │
│  vibeship-scanner                                          │
│  ┌────────────────────────────────────────────────────┐   │
│  │ ● Edge: Safari input zoom on iOS           amber   │   │
│  └────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

Grouped by project. Color dots by type. Click navigates to project with item expanded.

---

## Delete Confirmation

```
┌────────────────────────────────────────────────────────────┐
│  Delete "vibeship-mind"?                                  │
│                                                            │
│  This will permanently delete:                            │
│  ◦ 5 decisions                                            │
│  ◦ 2 issues                                               │
│  ◦ 1 edge                                                 │
│  ◦ 3 episodes                                             │
│  ◦ 8 sessions                                             │
│                                                            │
│  This cannot be undone.                                   │
│                                                            │
│  [Cancel]                    [Delete Everything]          │
└────────────────────────────────────────────────────────────┘
```

Delete button in red, requires confirmation.

---

## Loading State

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│                    ◦ · ∘ · ◦                              │
│                                                            │
│                  Loading mind...                          │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

Same gentle animation as hero nodes.

---

## Technical Implementation

### Stack
- **Framework**: SvelteKit (matches spawner/scanner)
- **Styling**: Pure CSS with custom properties (no framework)
- **API**: Fetch from Mind HTTP API (localhost:8765)
- **Fonts**: JetBrains Mono, Instrument Serif (Google Fonts)

### API Endpoints Used
```
GET  /status                 - Stats for hero
GET  /user                   - Relationship stats
GET  /projects               - Project list
GET  /projects/:id           - Project detail
GET  /decisions/:project_id  - Decisions list
GET  /issues/:project_id     - Issues list
GET  /edges                  - Edges (global + project)
GET  /episodes/:project_id   - Episodes list
GET  /sessions/:project_id   - Sessions list
GET  /search?q=&project_id=  - Cross-entity search
GET  /export                 - JSON export
```

### Skip for Phase 1
- Edit forms (use simple inputs, not designed modals)
- Mobile optimization (works, but not polished)
- Keyboard shortcuts
- Accessibility audit

Get it working first. Polish later.

---

## Summary

| Component | Status |
|-----------|--------|
| Hero (living mind viz) | Designed |
| Project list | Designed |
| Project detail (5 tabs) | Designed |
| Cross-references | Designed |
| Search results | Designed |
| Empty states | Designed |
| Delete confirmation | Designed |
| Loading state | Designed |
