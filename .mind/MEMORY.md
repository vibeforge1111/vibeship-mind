<!-- MIND MEMORY - Append as you work. Write naturally.
Keywords: decided, problem, learned, tried, fixed, blocked, todo -->

# vibeship-mind

## Project State
- Goal:
- Stack: python
- Blocked: None

## Gotchas
- Windows cp1252 encoding -> use ASCII symbols or set PYTHONIOENCODING=utf-8
- uv sync removes unlisted packages

---

## Session Log

## 2025-12-13

**Decided:** File-based memory over database approach - simpler, human-readable, git-trackable
**Decided:** Use Click for CLI because it's simple and well-documented

**Problem:** Windows console doesn't support Unicode checkmarks
**Fixed:** Replaced Unicode symbols with ASCII alternatives

**Learned:** Python on Windows uses cp1252 encoding by default, not UTF-8
TIL: uv sync removes packages not in dependencies

Going with loose regex parsing over strict schemas because lower friction

---

## 2025-12-13 (continued)

Built all 5 phases of Mind - CLI, Parser, Daemon, MCP Server, Polish

decided to rewrite README for vibe coders - simpler language, less jargon
decided on 5-command install instead of multi-step guides
decided to remove competitive comparison chart - felt too aggressive
learned that users get confused by technical paths like `uv --directory`
learned that "note taking" framing is wrong - it's about memory, not notes

problem: README was too confusing for beginners
fixed by simplifying to copy-paste commands and plain English

Added MCP tools explanation with easy install prompt:
> Add Mind MCP server from github.com/vibeforge1111/vibeship-mind to my config

decided to enhance capture instructions with ideas from archived version - alternatives rejected, symptoms/theories, mood tracking, session end notes
learned that the archived version had rich session management (Episodes, mood tracking, primer generation) that we can borrow concepts from
fixed memory capture gap by adding explicit instructions to CLAUDE.md template - Claude needs to be told to write memories

---

## 2025-12-13 | Added intelligence from archives: recency, KEY markers, session summaries, context budget, stack-aware edges | mood: productive

**Researched competition:** Mem0, mcp-memory-service, task-orchestrator, claude-memory-mcp, memory banks
KEY: decided to stay file-based - that's our identity vs database-heavy competitors
decided to add only necessary intelligence: recency scoring, KEY markers, session summaries, context budget, stack-aware edges
decided NOT to add: databases, embeddings, workflow commands, episodes, user model - too much friction

**Implemented:**
- Recency scoring (days_ago field, entities_by_recency() method)
- KEY: and important: markers for items that never fade
- Session summary lines: `## DATE | what happened | mood: X`
- Context budget: key items section, session history compression
- Stack-aware edge matching: surfaces relevant gotchas based on project stack

learned that competition (Mem0, mcp-memory-service) all use databases/embeddings - we stay simpler with files
learned that session summary format `## DATE | summary | mood` compresses history naturally
gotcha: session summary lines were being parsed as entities - fixed by skipping lines with `|` in _should_skip

---
