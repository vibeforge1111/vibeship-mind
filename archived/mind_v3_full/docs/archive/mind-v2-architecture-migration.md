# Mind v2 Architecture Migration: Daemon -> MCP-Only

## Executive Summary

We're removing the daemon from Mind v2 and shifting all functionality to the MCP layer. The daemon was the "when to run" trigger; the MCP becomes the trigger instead. All memory logic (parsing, indexing, context generation) stays identical.

**Why:** Daemons are inherently unstable (crashes, PID issues, platform-specific configs, resource leaks). MCP is stateless and reliable.

**Key Insight:** We don't need real-time session detection. We just need to detect session boundaries *before the next session starts*. `recall()` checks timestamps and handles it.

---

## What Changes

### Remove Entirely

```
DELETE these files/features:
├── daemon.py (or equivalent daemon module)
├── File watcher (watchdog/fsevents)
├── Session inactivity timer
├── PID file management
├── Signal handlers (SIGTERM, SIGINT)
├── launchd plist config
├── systemd service config
├── Windows Task Scheduler config
├── `mind daemon start/stop/status/logs` CLI commands
└── Any background process management
```

### Keep Unchanged

```
KEEP all of these:
├── .mind/MEMORY.md format and structure
├── .mind/state.json (repurposed slightly)
├── .mind/.index/ directory and embeddings
├── Loose parser (natural language -> structured entities)
├── Entity extraction logic
├── Confidence scoring
├── Context generation algorithm
├── Cross-project edges and global memory
├── All memory types (decisions, issues, gotchas, learnings, etc.)
├── Archive functionality
└── Search/embedding logic
```

### Modify

```
MODIFY these:
├── MCP tools (add session detection to recall)
├── state.json schema (simplified)
├── CLAUDE.md template (new instructions)
└── CLI (remove daemon commands, keep project management)
```

---

## New Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────┐
│  User starts Claude Code session                            │
│                        v                                    │
│  Claude reads CLAUDE.md (automatic behavior)                │
│                        v                                    │
│  CLAUDE.md says: "call mind.recall() first"                 │
│                        v                                    │
│  Claude calls mind.recall()                                 │
│                        v                                    │
│  MCP checks state.json:                                     │
│    - last_activity timestamp                                │
│    - MEMORY.md file hash                                    │
│                        v                                    │
│  Gap > 30 min OR hash changed?                              │
│    YES -> Parse new entries, regenerate context              │
│    NO  -> Return cached context                              │
│                        v                                    │
│  Update last_activity = now                                 │
│                        v                                    │
│  Return context to Claude                                   │
│                        v                                    │
│  Claude works, writes directly to MEMORY.md (no tool call)  │
│                        v                                    │
│  User leaves (no explicit end session needed)               │
│                        v                                    │
│  Next session: recall() detects gap, processes new entries  │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Role |
|-----------|------|
| CLAUDE.md | Automation trigger - tells Claude to call `recall()` |
| MCP `recall()` | Session detection + context delivery |
| MCP `search()` | Query memory (reads raw MEMORY.md for same-session) |
| MCP `checkpoint()` | Optional manual trigger for context regen |
| .mind/MEMORY.md | Human-readable storage, Claude writes directly |
| .mind/state.json | Timestamps and hashes for session detection |
| .mind/.index/ | Embeddings and parsed entities |

---

## MCP Tool Specifications

### `mind.recall()`

Primary tool. Called at session start.

```typescript
interface RecallInput {
  project_path?: string;  // defaults to cwd
  force_refresh?: boolean;  // bypass cache
}

interface RecallOutput {
  context: string;  // Generated context markdown
  session_info: {
    last_session: string;  // ISO timestamp
    gap_detected: boolean;
    entries_processed: number;
  };
  health: {
    memory_count: number;
    oldest_entry: string;
    suggestions: string[];  // e.g., "Consider archiving old entries"
  };
}
```

**Implementation pseudocode:**

```typescript
async function recall(input: RecallInput): Promise<RecallOutput> {
  const projectPath = input.project_path || process.cwd();
  const statePath = path.join(projectPath, '.mind/state.json');
  const memoryPath = path.join(projectPath, '.mind/MEMORY.md');
  
  // Read current state
  const state = readJsonSync(statePath) || { last_activity: 0, memory_hash: '' };
  const currentHash = hashFile(memoryPath);
  const now = Date.now();
  const gap = now - state.last_activity;
  const GAP_THRESHOLD = 30 * 60 * 1000; // 30 minutes
  
  let context: string;
  let gapDetected = false;
  let entriesProcessed = 0;
  
  // Check if we need to reprocess
  if (input.force_refresh || gap > GAP_THRESHOLD || currentHash !== state.memory_hash) {
    gapDetected = gap > GAP_THRESHOLD;
    
    // Parse MEMORY.md for new/changed entries
    const entries = await parseMemoryFile(memoryPath);
    entriesProcessed = entries.length;
    
    // Update index with new entries
    await updateIndex(projectPath, entries);
    
    // Generate fresh context
    context = await generateContext(projectPath);
    
    // Update state
    state.memory_hash = currentHash;
  } else {
    // Return cached context
    context = await getCachedContext(projectPath);
  }
  
  // Always update last_activity
  state.last_activity = now;
  writeJsonSync(statePath, state);
  
  return {
    context,
    session_info: {
      last_session: new Date(state.last_activity).toISOString(),
      gap_detected: gapDetected,
      entries_processed: entriesProcessed
    },
    health: await getMemoryHealth(projectPath)
  };
}
```

### `mind.search()`

Query memory. Must read raw MEMORY.md for same-session queries.

```typescript
interface SearchInput {
  query: string;
  project_path?: string;
  include_unparsed?: boolean;  // default true - includes raw MEMORY.md
}

interface SearchOutput {
  results: Array<{
    type: string;  // decision, issue, gotcha, etc.
    content: string;
    timestamp?: string;
    confidence: number;
    source: 'indexed' | 'unparsed';
  }>;
}
```

**Implementation note:** Always read raw MEMORY.md and search it too, not just the index. This catches same-session writes that haven't been indexed yet.

### `mind.checkpoint()`

Optional manual trigger. For when user wants to ensure memory is processed.

```typescript
interface CheckpointInput {
  project_path?: string;
}

interface CheckpointOutput {
  processed: number;
  context_updated: boolean;
}
```

### `mind.status()`

Health check and stats.

```typescript
interface StatusOutput {
  project: string;
  last_activity: string;
  memory_file: {
    exists: boolean;
    entries: number;
    size_kb: number;
  };
  index: {
    entities: number;
    last_updated: string;
  };
  suggestions: string[];
}
```

---

## State File Schema

### .mind/state.json (Simplified)

```json
{
  "last_activity": 1702400000000,
  "memory_hash": "a1b2c3d4e5f6",
  "last_context_gen": 1702399000000,
  "schema_version": 2
}
```

**Removed from v1:**
- Session tracking (not needed - gap detection is lazy)
- Active project list (daemon managed this)
- Watcher state

---

## CLAUDE.md Template

Update the injected CLAUDE.md section:

```markdown
## Memory (Mind)

This project uses Mind for persistent memory across sessions.

### Required Protocol

1. **Session Start**: ALWAYS call `mind.recall()` before responding to the first message. This loads context from previous sessions.

2. **During Work**: When you make decisions, hit issues, or learn gotchas, append to `.mind/MEMORY.md` directly:
   
   ```markdown
   ## Decision (2024-12-12)
   Using Redis for session storage because...
   
   ## Issue
   Safari blocks third-party cookies in iframes
   
   ## Gotcha
   Don't use `apt` in Dockerfile, use `apt-get`
   ```

3. **No End Session Needed**: Just stop working. Next `recall()` will process everything.

### Tools Available

- `mind.recall()` - Load session context (call first!)
- `mind.search(query)` - Find specific memories
- `mind.checkpoint()` - Force process pending memories
- `mind.status()` - Check memory health
```

---

## CLI Changes

### Remove

```bash
# DELETE these commands entirely
mind daemon start
mind daemon stop
mind daemon status
mind daemon logs
mind daemon restart
```

### Keep

```bash
# KEEP these (unchanged)
mind init [path]
mind add [path]
mind remove [path]
mind list
mind search <query>
mind status
mind archive
mind doctor
```

### Modify

```bash
# UPDATE mind doctor - remove daemon checks
mind doctor

# Old output:
# [✓] Daemon running
# [✓] Config valid
# ...

# New output:
# [✓] Config valid
# [✓] Projects registered: 3
# [✓] All MEMORY.md files accessible
# [✓] Index not corrupted
# [✓] State files valid
```

---

## Migration Checklist

### Phase 1: Remove Daemon

- [ ] Delete daemon module/file
- [ ] Delete file watcher code
- [ ] Delete PID management
- [ ] Delete signal handlers
- [ ] Delete platform auto-start configs
- [ ] Remove daemon CLI commands
- [ ] Update `mind doctor` to remove daemon checks

### Phase 2: Enhance MCP

- [ ] Add session gap detection to `recall()`
- [ ] Add MEMORY.md hash checking
- [ ] Update `search()` to read raw file (same-session support)
- [ ] Add `checkpoint()` tool
- [ ] Update `status()` output

### Phase 3: Update State Management

- [ ] Simplify state.json schema
- [ ] Add migration for existing state files
- [ ] Update state read/write functions

### Phase 4: Update CLAUDE.md

- [ ] Update template with new protocol
- [ ] Remove any daemon references
- [ ] Simplify instructions

### Phase 5: Update Docs

- [ ] Update README
- [ ] Update CLI help text
- [ ] Remove daemon setup instructions
- [ ] Add MCP-only architecture explanation

---

## Edge Cases to Handle

### 1. Same-Session Search

**Problem:** User writes decision at 2pm, searches at 3pm same session. Index doesn't have it yet.

**Solution:** `search()` reads raw MEMORY.md and searches both indexed + unparsed content.

```typescript
async function search(query: string) {
  // Search index
  const indexedResults = await searchIndex(query);
  
  // Also search raw file for unparsed content
  const rawContent = readFileSync('.mind/MEMORY.md', 'utf-8');
  const unparsedResults = searchRawContent(rawContent, query);
  
  // Merge and dedupe
  return mergeResults(indexedResults, unparsedResults);
}
```

### 2. Format Drift

**Problem:** Claude writes inconsistent formats.

**Solution:** Keep the loose parser. Accept natural language. Score confidence.

### 3. Large Files

**Problem:** MEMORY.md grows forever.

**Solution:** `recall()` returns suggestion when file > 100KB:

```typescript
if (fileSizeKb > 100) {
  health.suggestions.push('MEMORY.md is large. Consider running `mind archive` to move old entries.');
}
```

### 4. Cross-Project Memory

**Problem:** Without daemon, when do we scan other projects?

**Solution:** `recall()` can optionally scan registered projects for global edges:

```typescript
interface RecallInput {
  include_global?: boolean;  // Scan other projects for cross-references
}
```

Or defer to `mind search --global` for explicit cross-project queries.

### 5. No Timestamps in Entries

**Problem:** Claude forgets to add timestamps.

**Solution:** Parser infers from:
1. Explicit timestamp in entry
2. Git blame if available
3. File mtime as fallback
4. "Unknown" with current date as last resort

---

## Testing Checklist

- [ ] Fresh project init works
- [ ] `recall()` returns context
- [ ] Gap detection triggers reprocessing
- [ ] Hash change triggers reprocessing
- [ ] `force_refresh` works
- [ ] Same-session search finds unparsed entries
- [ ] `checkpoint()` processes pending entries
- [ ] State file persists correctly
- [ ] Large file warning appears
- [ ] Archive suggestion works
- [ ] Cross-project search works
- [ ] Error handling for missing files
- [ ] Error handling for corrupted state

---

## Summary

**Before (Daemon):**
```
Daemon watches -> Detects inactivity -> Processes -> Writes to CLAUDE.md
                 (proactive)          (eager)     (pre-baked)
```

**After (MCP):**
```
recall() called -> Checks timestamps -> Processes if needed -> Returns context
                  (reactive)          (lazy)                (on-demand)
```

Same outcome. Simpler system. No crashes.
