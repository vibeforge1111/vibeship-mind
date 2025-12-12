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
