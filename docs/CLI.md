# Mind CLI Reference

## Overview

The Mind CLI handles project initialization, daemon management, and manual operations.

```bash
mind <command> [options]
```

---

## Commands

### `mind init`

Initialize Mind for a project.

```bash
mind init [path]
```

**Arguments:**
- `path` - Project directory (default: current directory)

**What it does:**
1. Creates `.mind/` directory
2. Creates `.mind/MEMORY.md` with template
3. Creates `.mind/.gitignore` (ignores .index/)
4. Adds MIND:CONTEXT section to `CLAUDE.md`
5. Registers project with daemon
6. Auto-detects stack from project files

**Example:**

```bash
$ cd ~/projects/my-app
$ mind init

✓ Created .mind/MEMORY.md
✓ Added MIND:CONTEXT to CLAUDE.md
✓ Detected stack: sveltekit, typescript, tailwind
✓ Registered project with daemon

Mind initialized! Start working - memory will accumulate automatically.
```

**Options:**

```bash
--no-register    # Don't register with daemon
--no-claude-md   # Don't modify CLAUDE.md
--template FILE  # Use custom MEMORY.md template
```

---

### `mind daemon`

Manage the Mind daemon.

#### `mind daemon start`

Start the daemon in background.

```bash
$ mind daemon start

✓ Mind daemon started (PID: 12345)
  Watching 3 projects
  Log: ~/.mind/logs/daemon.log
```

#### `mind daemon stop`

Stop the daemon.

```bash
$ mind daemon stop

✓ Mind daemon stopped
```

#### `mind daemon status`

Check daemon status.

```bash
$ mind daemon status

Mind Daemon Status
──────────────────
Status: Running
PID: 12345
Uptime: 2h 34m

Projects: 3 watching
  ~/vibeship-mind      (active, 5m ago)
  ~/vibeship-scanner   (idle, 2h ago)
  ~/vibeship-spawner   (idle, 1d ago)
```

#### `mind daemon logs`

View daemon logs.

```bash
$ mind daemon logs

# Or follow logs
$ mind daemon logs -f
```

#### `mind daemon restart`

Restart the daemon.

```bash
$ mind daemon restart

✓ Mind daemon restarted (PID: 12346)
```

---

### `mind add`

Register a project with the daemon.

```bash
mind add [path]
```

**Example:**

```bash
$ mind add .
✓ Registered: /Users/cem/vibeship-mind

$ mind add ~/projects/*
✓ Registered: /Users/cem/projects/app1
✓ Registered: /Users/cem/projects/app2
✓ Skipped: /Users/cem/projects/app3 (no .mind/ directory)
```

---

### `mind remove`

Unregister a project from the daemon.

```bash
mind remove [path]
```

**Example:**

```bash
$ mind remove .
✓ Unregistered: /Users/cem/vibeship-mind
  (Files in .mind/ preserved)
```

---

### `mind list`

List registered projects.

```bash
$ mind list

Registered Projects
───────────────────
1. vibeship-mind
   Path: /Users/cem/vibeship-mind
   Stack: python, fastapi, sqlite
   Last: 5 minutes ago
   Memory: 12 decisions, 3 issues, 5 learnings

2. vibeship-scanner
   Path: /Users/cem/vibeship-scanner
   Stack: sveltekit, typescript
   Last: 2 hours ago
   Memory: 8 decisions, 1 issue, 3 learnings

3. vibeship-spawner
   Path: /Users/cem/vibeship-spawner
   Stack: typescript, mcp
   Last: 1 day ago
   Memory: 5 decisions, 2 issues, 4 learnings
```

---

### `mind index`

Force re-index a project.

```bash
mind index [path]
```

**Example:**

```bash
$ mind index .

Indexing /Users/cem/vibeship-mind...
├─ Parsing MEMORY.md... found 12 decisions, 3 issues
├─ Scanning code files... found 5 inline comments
├─ Processing git history... found 8 relevant commits
├─ Generating embeddings... done
└─ Updating CLAUDE.md... done

✓ Indexed 28 entities in 2.3s
```

**Options:**

```bash
--full           # Full reindex (delete and rebuild)
--no-context     # Don't update CLAUDE.md
```

---

### `mind context`

Show or regenerate MIND:CONTEXT.

```bash
# Show current context
$ mind context

<!-- MIND:CONTEXT -->
## Session Context
Last active: 2 hours ago

## Project State
- Goal: Ship v1 dashboard
- Stack: SvelteKit, FastAPI
...

# Regenerate context
$ mind context --regenerate
✓ CLAUDE.md updated
```

---

### `mind search`

Search memories from CLI.

```bash
mind search <query> [options]
```

**Example:**

```bash
$ mind search "authentication"

Found 5 results:

1. [decision] Use JWT for auth (Dec 10)
   "Simpler than sessions, stateless..."
   File: .mind/MEMORY.md:45

2. [issue] Safari cookies bug (Dec 8) - resolved
   "ITP blocking cross-domain..."
   File: .mind/MEMORY.md:32

3. [learning] Safari ITP behavior (Dec 8)
   "Blocks third-party cookies after 7 days"
   File: src/lib/auth.ts:12
```

**Options:**

```bash
--scope all      # Search all projects
--type decision  # Filter by type
--limit 10       # Max results
--json           # Output as JSON
```

---

### `mind edges`

List or search global edges.

```bash
# List all global edges
$ mind edges

Global Sharp Edges (12)
───────────────────────
1. Vercel Edge crypto limitation [warning]
   Vercel Edge runtime doesn't support Node.js crypto
   Workaround: Use Web Crypto API
   Tags: vercel, edge, crypto

2. Safari ITP cookie blocking [warning]
   Safari blocks third-party cookies after 7 days
   Workaround: Use same-domain auth
   Tags: safari, auth, cookies

...

# Search edges
$ mind edges --search "safari"

# Filter by stack
$ mind edges --stack vercel,edge
```

---

### `mind doctor`

Run health checks.

```bash
$ mind doctor

Mind Health Check
─────────────────
[✓] Config valid (~/.mind/config.toml)
[✓] Daemon running (PID: 12345)
[✓] Projects registered: 3
[✓] All .mind/MEMORY.md files accessible
[✓] Index not corrupted
[⚠] vibeship-spawner: MIND:CONTEXT stale (1d old)
[✓] Global edges loaded: 12
[✓] Embeddings model available

Warnings:
- Project 'vibeship-spawner' has stale context
  Fix: Run `mind index ~/vibeship-spawner`

Overall: Healthy (1 warning)
```

---

### `mind export`

Export project memories.

```bash
mind export [path] [options]
```

**Example:**

```bash
# Export as JSON
$ mind export . --format json > memories.json

# Export as Markdown
$ mind export . --format markdown > memories.md

# Export all projects
$ mind export --all --format json > all-memories.json
```

**Options:**

```bash
--format json|markdown   # Output format
--all                    # Export all projects
--include-index          # Include search index
```

---

### `mind config`

Manage configuration.

```bash
# Show config
$ mind config

# Edit config
$ mind config edit

# Set value
$ mind config set daemon.inactivity_minutes 45

# Reset to defaults
$ mind config reset
```

---

## Global Options

```bash
--verbose, -v    # Verbose output
--quiet, -q      # Suppress output
--json           # Output as JSON
--help, -h       # Show help
--version        # Show version
```

---

## Environment Variables

```bash
MIND_HOME        # Config directory (default: ~/.mind)
MIND_LOG_LEVEL   # Log level: debug, info, warn, error
MIND_NO_DAEMON   # Disable daemon features (1 to disable)
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Project not found |
| 4 | Daemon not running |
| 5 | Permission denied |

---

## Shell Completions

```bash
# Bash
$ mind completions bash >> ~/.bashrc

# Zsh
$ mind completions zsh >> ~/.zshrc

# Fish
$ mind completions fish > ~/.config/fish/completions/mind.fish
```

---

## Quick Reference

```bash
# Project setup
mind init                    # Initialize Mind in project
mind add .                   # Register with daemon

# Daemon
mind daemon start            # Start daemon
mind daemon stop             # Stop daemon
mind daemon status           # Check status

# Information
mind list                    # List projects
mind search "query"          # Search memories
mind context                 # Show current context
mind edges                   # List global edges

# Maintenance
mind index                   # Reindex project
mind doctor                  # Health check
mind export                  # Export memories
```
