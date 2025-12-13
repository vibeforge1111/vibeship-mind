# Mind CLI Reference (v2)

## Overview

The Mind CLI handles project initialization, status checks, and MCP server management.

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
3. Creates `.mind/SESSION.md` with template
4. Creates `.mind/.gitignore` (ignores state.json)
5. Adds MIND:CONTEXT section to `CLAUDE.md`
6. Auto-detects stack from project files
7. Registers project with Mind

**Example:**

```bash
$ cd ~/projects/my-app
$ mind init

[+] Created .mind/MEMORY.md
[+] Created .mind/SESSION.md
[+] Updated CLAUDE.md with MIND:CONTEXT
[+] Detected stack: sveltekit, typescript, tailwind
[+] Registered project with Mind

Mind initialized! Start working - append notes to .mind/MEMORY.md

MCP tools available:
  - mind_recall() : Load session context (call first!)
  - mind_session() : Get current session state
  - mind_search() : Search memories
  - mind_checkpoint() : Force process pending memories
  - mind_edges() : Check for gotchas
```

---

### `mind parse`

Parse MEMORY.md and show extracted entities.

```bash
mind parse [path] [options]
```

**Arguments:**
- `path` - Project directory (default: current directory)

**Options:**
- `--json` - Output as JSON
- `--inline` - Also scan code files for MEMORY: comments

**Example:**

```bash
$ mind parse

=== Project State ===
Goal: Ship v1 dashboard
Stack: python, fastapi
Blocked: None

=== Entities ===
[decision] [85%] Use JWT for auth (2024-12-12)
  Reason: simpler than sessions
  Source: .mind/MEMORY.md:45
[issue] [open] [70%] Safari cookies bug (2024-12-10)
  Source: .mind/MEMORY.md:32
[learning] [90%] Safari ITP blocks cross-domain (2024-12-10)
  Source: .mind/MEMORY.md:38

=== Gotchas ===
- Safari ITP blocks cross-domain cookies -> use same-domain auth

Total: 3 entities, 1 gotchas
```

---

### `mind list`

List registered projects.

```bash
$ mind list

Registered Projects
----------------------------------------

1. vibeship-mind
   Path: /Users/cem/vibeship-mind
   Stack: python
   Last activity: 5 minutes ago

2. vibeship-scanner
   Path: /Users/cem/vibeship-scanner
   Stack: sveltekit, typescript
   Last activity: 2 hours ago
```

---

### `mind add`

Register a project with Mind.

```bash
mind add [path]
```

**Example:**

```bash
$ mind add .
[+] Registered: /Users/cem/vibeship-mind
```

---

### `mind remove`

Unregister a project from Mind.

```bash
mind remove [path]
```

**Example:**

```bash
$ mind remove .
[+] Unregistered: /Users/cem/vibeship-mind
    (Files in .mind/ preserved)
```

---

### `mind status`

Show project status and stats.

```bash
mind status [path]
```

**Example:**

```bash
$ mind status

Project: vibeship-mind
----------------------------------------
Stack: python, fastapi
Goal: Ship v1 dashboard
Blocked: None

Stats:
  Decisions: 12
  Issues (open): 2
  Issues (resolved): 5
  Learnings: 8
  Gotchas: 3

MEMORY.md: 4.5KB
Last activity: 2024-12-13T10:30:00
```

---

### `mind doctor`

Run health checks on Mind installation.

```bash
$ mind doctor

Mind Health Check (v2)
----------------------------------------
[+] Config directory exists (~/.mind)
[+] Projects registered: 3
[+] vibeship-mind: MEMORY.md accessible (4KB)
[+] vibeship-mind: MIND:CONTEXT present
[+] vibeship-scanner: MEMORY.md accessible (2KB)
[.] vibeship-scanner: Last activity 7d ago
[+] Global edges loaded: 5

----------------------------------------
Warnings (1):
  - vibeship-scanner: Last activity 7 days ago

Overall: Healthy (1 warning)
```

---

### `mind mcp`

Run the MCP server for AI assistant integration.

```bash
mind mcp
```

This starts the MCP server that provides 8 tools:
- `mind_recall` - Load session context (call first!)
- `mind_session` - Get current session state
- `mind_blocker` - Log blocker + auto-search
- `mind_search` - Search memories
- `mind_edges` - Check for gotchas
- `mind_checkpoint` - Force process memories
- `mind_add_global_edge` - Add cross-project gotcha
- `mind_status` - Check health

**Usage with Claude Code:**

Add to `~/.config/claude/mcp.json`:

```json
{
  "mcpServers": {
    "mind": {
      "command": "uv",
      "args": ["--directory", "/path/to/mind", "run", "mind", "mcp"]
    }
  }
}
```

---

## Global Options

```bash
--help, -h       # Show help
--version        # Show version
```

---

## Quick Reference

```bash
# Project setup
mind init                    # Initialize Mind in project
mind add .                   # Register existing project

# Information
mind list                    # List projects
mind status                  # Show project stats
mind parse                   # Show parsed entities

# Maintenance
mind doctor                  # Health check
mind remove .                # Unregister project

# MCP Server
mind mcp                     # Run MCP server
```

---

## Environment Variables

```bash
MIND_HOME        # Config directory (default: ~/.mind)
```
