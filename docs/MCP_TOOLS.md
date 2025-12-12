# Mind MCP Tools

Mind exposes 10 MCP tools for AI assistants to maintain context across sessions.

## Session Lifecycle

### mind_start_session

Start a new session, get project context and primer.

**Parameters:**
```typescript
{
  project_id?: string,    // Existing project ID
  project_name?: string,  // Or find/create by name
  detect_from_path?: string  // Or detect from repo path
}
```

**Returns:**
```typescript
{
  session_id: string,
  project: Project,
  primer: string,  // Human-readable context summary
  open_issues: Issue[],
  pending_decisions: Decision[],  // Decisions with revisit conditions met
  relevant_edges: SharpEdge[]
}
```

**Example:**
```
Claude calls: mind_start_session(project_name="spawner")

Returns:
{
  session_id: "sess_01HX...",
  project: { name: "spawner", current_goal: "Implement memory MCP", ... },
  primer: "Last session: Yesterday 11pm\nEnded with: Designed memory architecture\n...",
  open_issues: [{ title: "VibeMemo source access", status: "investigating" }],
  pending_decisions: [],
  relevant_edges: []
}
```

### mind_end_session

End the current session, capture summary and state.

**Parameters:**
```typescript
{
  summary: string,         // What happened
  progress: string[],      // What was accomplished
  still_open: string[],    // Unresolved threads
  next_steps: string[],    // For next session
  mood?: string            // Optional mood observation
}
```

**Returns:**
```typescript
{
  session_id: string,
  captured: boolean,
  episode_created?: string  // If session was significant enough
}
```

**Example:**
```
Claude calls: mind_end_session(
  summary="Implemented core data models for Mind",
  progress=["Created Project, Decision, Issue models", "Set up SQLite schema"],
  still_open=["MCP tool implementations", "Sync logic"],
  next_steps=["Implement storage layer", "Add embedding generation"],
  mood="Productive, clear direction"
)
```

## Context Retrieval

### mind_get_context

Search for relevant context across all entity types.

**Parameters:**
```typescript
{
  query: string,           // Natural language query
  types?: EntityType[],    // Filter to specific types
  project_id?: string,     // Scope to project (default: current)
  include_global?: boolean // Include global edges (default: true)
}
```

**Returns:**
```typescript
{
  decisions: Decision[],
  issues: Issue[],
  edges: SharpEdge[],
  episodes: Episode[]
}
```

**Example:**
```
Claude calls: mind_get_context(query="why did we choose supabase")

Returns:
{
  decisions: [{
    title: "Use Supabase for backend",
    reasoning: "Vercel Edge timeout too short for webhooks...",
    alternatives: [{ option: "Cloudflare Workers", rejected_because: "No native Postgres" }]
  }],
  issues: [],
  edges: [],
  episodes: []
}
```

### mind_check_edges

Check for sharp edges that might apply to current code or intent.

**Parameters:**
```typescript
{
  code?: string,           // Code being written/suggested
  intent?: string,         // What we're trying to do
  context?: {              // Additional context
    runtime?: string,      // "edge", "serverless", "node"
    framework?: string,    // "nextjs", "remix", etc.
    file_path?: string     // Current file
  }
}
```

**Returns:**
```typescript
{
  warnings: [{
    edge: SharpEdge,
    matched_pattern: DetectionPattern,
    severity: "high" | "medium" | "low",
    recommendation: string
  }]
}
```

**Example:**
```
Claude calls: mind_check_edges(
  code="const token = crypto.randomUUID()",
  context={ runtime: "edge" }
)

Returns:
{
  warnings: [{
    edge: { title: "Node crypto not available in Edge", workaround: "Use Web Crypto API" },
    matched_pattern: { type: "code", pattern: "crypto\\." },
    severity: "high",
    recommendation: "Use self.crypto.randomUUID() instead"
  }]
}
```

## Entity Management

### mind_add_decision

Record a new decision with full reasoning.

**Parameters:**
```typescript
{
  title: string,                    // Short description
  description: string,              // Full explanation
  context: string,                  // What situation led to this
  reasoning: string,                // Why this choice
  alternatives?: [{
    option: string,
    rejected_because?: string
  }],
  confidence?: number,              // 0.0 to 1.0 (default: 0.7)
  revisit_if?: string,              // Condition to reconsider
  trigger_phrases?: string[],       // For retrieval
  project_id?: string               // Default: current session's project
}
```

**Returns:**
```typescript
{
  decision: Decision,
  superseded?: Decision  // If this replaces an existing decision
}
```

**Example:**
```
Claude calls: mind_add_decision(
  title="Build Mind from scratch instead of forking VibeMemo",
  description="Create our own memory system rather than extending existing",
  context="After analyzing VibeMemo and finding we couldn't access source",
  reasoning="Full control, simpler architecture, no external dependencies",
  alternatives=[
    { option: "Fork VibeMemo", rejected_because: "Can't verify source quality" }
  ],
  confidence=0.8,
  revisit_if="We need features VibeMemo already has",
  trigger_phrases=["why not vibememo", "build vs fork"]
)
```

### mind_add_issue

Open a new issue.

**Parameters:**
```typescript
{
  title: string,
  description: string,
  severity?: "blocking" | "major" | "minor" | "cosmetic",
  symptoms?: string[],             // Error messages, behaviors
  trigger_phrases?: string[],
  project_id?: string
}
```

**Returns:**
```typescript
{
  issue: Issue
}
```

### mind_update_issue

Update an existing issue.

**Parameters:**
```typescript
{
  issue_id: string,
  status?: "open" | "investigating" | "blocked" | "resolved" | "wont_fix",
  add_attempt?: {
    what: string,
    result: string,
    learned?: string
  },
  current_theory?: string,
  blocked_by?: string,
  resolution?: string
}
```

**Returns:**
```typescript
{
  issue: Issue
}
```

**Example:**
```
Claude calls: mind_update_issue(
  issue_id="iss_01HX...",
  add_attempt={
    what: "Tried SameSite=None on cookies",
    result: "Still failing on Safari",
    learned: "Not a cookie scope issue"
  },
  current_theory="Safari ITP might be blocking cross-domain cookies entirely"
)
```

### mind_add_edge

Register a new sharp edge.

**Parameters:**
```typescript
{
  title: string,
  description: string,
  workaround: string,
  detection_patterns?: [{
    type: "code" | "context" | "intent",
    pattern: string,
    description: string
  }],
  symptoms?: string[],
  root_cause?: string,
  project_id?: string,              // null for global edge
  share_with_community?: boolean    // Contribute to registry
}
```

**Returns:**
```typescript
{
  edge: SharpEdge
}
```

**Example:**
```
Claude calls: mind_add_edge(
  title="Vercel Edge Functions can't use Node crypto module",
  description="Edge runtime is V8 isolate, not Node.js, so crypto module unavailable",
  workaround="Use Web Crypto API: self.crypto.randomUUID(), SubtleCrypto.digest()",
  detection_patterns=[
    { type: "code", pattern: "crypto\\.randomUUID|crypto\\.createHash", description: "Node crypto usage" },
    { type: "context", pattern: "edge.*crypto|crypto.*edge", description: "Crypto in edge context" }
  ],
  symptoms=["crypto is not defined", "Module not found: crypto"],
  root_cause="Edge runtime is V8 isolate without Node.js APIs",
  share_with_community=true
)
```

### mind_update_project

Update current project state.

**Parameters:**
```typescript
{
  current_goal?: string,
  blocked_by?: string[],
  open_threads?: string[],
  add_to_stack?: string[],
  status?: "active" | "paused" | "archived"
}
```

**Returns:**
```typescript
{
  project: Project
}
```

## Utility

### mind_export

Export all data for backup or migration.

**Parameters:**
```typescript
{
  format?: "json" | "markdown",
  project_id?: string,      // Specific project or all
  include_sessions?: boolean
}
```

**Returns:**
```typescript
{
  path: string,             // Path to export file
  entities: {
    projects: number,
    decisions: number,
    issues: number,
    edges: number,
    episodes: number,
    sessions: number
  }
}
```

## Tool Usage Guidelines

### When to Call Each Tool

| Situation | Tool |
|-----------|------|
| Starting work on a project | `mind_start_session` |
| Ending a conversation | `mind_end_session` |
| User asks "why did we..." | `mind_get_context` |
| About to write code | `mind_check_edges` |
| Made an important choice | `mind_add_decision` |
| Hit a problem | `mind_add_issue` |
| Tried a solution | `mind_update_issue` |
| Discovered a gotcha | `mind_add_edge` |
| Changed focus/goals | `mind_update_project` |
| User wants backup | `mind_export` |

### Best Practices

**DO:**
- Call `start_session` at the beginning of every conversation
- Store decisions with FULL reasoning and alternatives
- Update issues when attempting solutions (even failed ones)
- Add sharp edges with specific detection patterns
- Call `end_session` with meaningful summary

**DON'T:**
- Store code snippets (they go stale)
- Create duplicate entries (search first)
- Store generic knowledge (only project-specific)
- Skip the reasoning on decisions
- Forget to capture failed attempts on issues

### Natural Integration

Tools should be called silently. Don't announce database operations.

```
# BAD
"Let me check my memory database for that decision..."
"I'm now storing this in the decision log..."

# GOOD  
"We chose Supabase because of the webhook timeout constraints.
The alternative was Cloudflare Workers but we needed native Postgres."

[silently called mind_get_context, user doesn't need to know]
```

### Error Handling

All tools return errors in consistent format:

```typescript
{
  error: {
    code: string,
    message: string,
    details?: any
  }
}
```

Common errors:
- `PROJECT_NOT_FOUND` - Project doesn't exist
- `SESSION_NOT_ACTIVE` - No active session
- `ENTITY_NOT_FOUND` - Referenced entity doesn't exist
- `VALIDATION_ERROR` - Invalid parameters
