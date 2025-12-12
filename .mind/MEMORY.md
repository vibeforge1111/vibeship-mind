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
