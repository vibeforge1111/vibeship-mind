# Maintainability System Design

## Overview

A system to keep Mind's codebase clean and ready for rapid iteration, A/B testing, and continuous improvement.

## Components

### 1. Versioning

**Semantic versioning** in `pyproject.toml`:
```toml
[project]
version = "2.0.0"
```

**CHANGELOG.md** at repo root:
```markdown
# Changelog

## [2.1.0] - 2025-12-14
### Added
- Feature flags system
- mind_reminder_done tool

### Changed
- Simplified SESSION.md to 4 sections

### Fixed
- Session routing for mind_log types
```

**Git tags** for releases:
```bash
git tag -a v2.1.0 -m "Release 2.1.0"
git push origin v2.1.0
```

**When to version:**
- Breaking changes = major (3.0.0)
- New features = minor (2.1.0)
- Bug fixes = patch (2.0.1)

---

### 2. Feature Flags

**Location:** `.mind/config.json` (per-project)

**Schema:**
```json
{
  "version": 1,
  "experimental": {
    "auto_mark_reminders": false,
    "self_improve": false
  }
}
```

**Code pattern:**
```python
# src/mind/config.py (new file)

def load_config(project_path: Path) -> dict:
    """Load project config, return defaults if missing."""
    config_file = project_path / ".mind" / "config.json"
    if not config_file.exists():
        return {"version": 1, "experimental": {}}
    try:
        return json.loads(config_file.read_text())
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "experimental": {}}

def is_feature_enabled(feature: str, project_path: Path) -> bool:
    """Check if an experimental feature is enabled."""
    config = load_config(project_path)
    return config.get("experimental", {}).get(feature, False)
```

**Usage in handlers:**
```python
if is_feature_enabled("auto_mark_reminders", project_path):
    mark_reminder_done(project_path, reminder["index"])
```

**Adding a new experimental feature:**
1. Add to config schema above
2. Wrap new code in `if is_feature_enabled("feature_name", ...)`
3. Document in CHANGELOG as experimental
4. When stable, remove flag and make default

---

### 3. Layered Documentation

| Doc | Scope | Audience |
|-----|-------|----------|
| `README.md` | Install, quick start, why Mind | First-time users |
| `docs/HOW_IT_WORKS.md` | Architecture, concepts, diagrams | Curious users |
| `docs/MCP_TOOLS.md` | Tool reference, all parameters | Power users |
| `CHANGELOG.md` | Version history, what changed | Everyone |

**Rules:**
- Each doc has ONE purpose
- When updating a feature, identify which layer(s) it affects
- Don't duplicate - link instead
- README links to other docs, doesn't repeat them

**Archive policy:** Old docs go in `docs/archive/` with date prefix. Delete after 30 days if not referenced.

---

### 4. Code Organization

**Current structure (keep):**
```
src/mind/
├── __init__.py
├── cli.py           # CLI commands
├── config.py        # NEW: feature flags
├── context.py       # Context generation
├── detection.py     # Stack detection
├── parser.py        # Entity parsing
├── storage.py       # Projects registry
├── templates.py     # File templates
└── mcp/
    ├── __init__.py
    └── server.py    # MCP server (keep as single file)
```

**server.py organization:**
```
Lines 1-130:     Session management (SESSION.md)
Lines 131-185:   State management (state.json)
Lines 186-410:   Reminders (REMINDERS.md)
Lines 411-465:   Memory/Session writing helpers
Lines 466-650:   Search and edge matching
Lines 651-895:   Server setup and tool definitions
Lines 896-1528:  Tool handlers
```

**When to split:** Only if file exceeds 3000 lines or logic needs sharing with CLI.

---

### 5. Cleanup Checklist

**Immediate:**
- [ ] Create `CHANGELOG.md` with current state as v2.0.0
- [ ] Add version to `pyproject.toml`
- [ ] Create `src/mind/config.py` for feature flags
- [ ] Update `.mind/` gitignore to include `config.json`
- [ ] Verify docs match current implementation

**Gaps to address (via reminders):**
- `mark_reminder_done()` not exposed - add tool or auto-mark
- SESSION.md template sync verified

---

## Implementation Order

1. Create `CHANGELOG.md` with v2.0.0 baseline
2. Add version field to `pyproject.toml`
3. Create `config.py` with feature flag functions
4. Update `mind init` to create default `config.json`
5. Verify/update docs for accuracy
6. Tag v2.0.0 in git

---

## Success Criteria

- [ ] Can bump version in one place (`pyproject.toml`)
- [ ] Can toggle experimental features without code changes
- [ ] Know which doc to update for any change
- [ ] No dead code in codebase
- [ ] CHANGELOG reflects actual state
