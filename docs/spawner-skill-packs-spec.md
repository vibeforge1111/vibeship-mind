# Spawner Skill Packs Specification

> **Goal**: Zero-cost local skill loading with simple install UX
> **Status**: Draft v1.0
> **Date**: December 27, 2025

---

## Overview

Skill packs are collections of related skills that users install once and load locally forever. No per-load API costs, full file fidelity, works offline.

```
User: "I need the Mind v5 skills"
Claude: spawner_skills({ action: "install", pack: "mind-v5" })
→ "Installed 20 skills to ~/.spawner/skills/mind-v5"

User: "Load event-architect"
Claude: spawner_load({ skill_id: "event-architect" })
→ Returns FULL skill content from local files (zero cost)
```

---

## Directory Structure

### Local Installation Path

```
~/.spawner/
├── skills/
│   ├── mind-v5/                          # Installed pack
│   │   ├── manifest.yaml                 # Pack metadata
│   │   ├── event-architect/
│   │   │   ├── skill.yaml
│   │   │   ├── sharp-edges.yaml
│   │   │   ├── validations.yaml
│   │   │   └── collaboration.yaml
│   │   ├── vector-specialist/
│   │   │   └── ...
│   │   └── ... (20 skills)
│   │
│   └── web3-defi/                        # Another pack
│       └── ...
│
└── registry.yaml                         # Tracks installed packs
```

### Registry File (`~/.spawner/registry.yaml`)

```yaml
installed:
  - pack: mind-v5
    version: 1.0.0
    installed_at: 2025-12-27T10:30:00Z
    source: https://github.com/vibeship/spawner-skills
    path: ~/.spawner/skills/mind-v5
    skills_count: 20

  - pack: web3-defi
    version: 2.1.0
    installed_at: 2025-12-20T14:00:00Z
    source: https://github.com/vibeship/spawner-skills
    path: ~/.spawner/skills/web3-defi
    skills_count: 8

settings:
  auto_update_check: true
  update_check_interval_days: 7
  last_update_check: 2025-12-27T10:30:00Z
```

### Pack Manifest (`manifest.yaml`)

```yaml
# Inside each skill pack directory
id: mind-v5
name: Mind v5 AI Memory Skills
version: 1.0.0
description: 20 specialist skills for building AI memory systems
author: Vibeship
license: MIT
repository: https://github.com/vibeship/spawner-skills

skills:
  - id: event-architect
    name: Event Architect
    layer: 1

  - id: vector-specialist
    name: Vector Specialist
    layer: 1

  - id: graph-engineer
    name: Graph Engineer
    layer: 1

  # ... all 20 skills

dependencies: []  # Other packs this depends on

tags:
  - ai-memory
  - mind-v5
  - event-sourcing
  - vector-search

min_spawner_version: "2.0.0"
```

---

## MCP API Changes

### 1. `spawner_skills` - Extended Actions

```typescript
// NEW ACTIONS

// Install a skill pack
spawner_skills({
  action: "install",
  pack: "mind-v5",                    // Pack name
  source?: "github" | "local",        // Default: github
  path?: string                       // For local: path to pack directory
})
// Returns: { success: true, message: "Installed 20 skills", path: "~/.spawner/skills/mind-v5" }

// List installed packs
spawner_skills({
  action: "installed"
})
// Returns: [
//   { pack: "mind-v5", version: "1.0.0", skills_count: 20, path: "..." },
//   { pack: "web3-defi", version: "2.1.0", skills_count: 8, path: "..." }
// ]

// Check for updates
spawner_skills({
  action: "check-updates"
})
// Returns: [
//   { pack: "mind-v5", current: "1.0.0", latest: "1.1.0", changes: ["Added llm-architect", "Fixed event-architect patterns"] }
// ]

// Update installed packs
spawner_skills({
  action: "update",
  pack?: "mind-v5"                    // Optional: update specific pack, or all if omitted
})
// Returns: { updated: ["mind-v5"], from: "1.0.0", to: "1.1.0" }

// Uninstall a pack
spawner_skills({
  action: "uninstall",
  pack: "mind-v5"
})
// Returns: { success: true, message: "Removed mind-v5 (20 skills)" }

// List available packs (from registry)
spawner_skills({
  action: "available",
  tag?: "ai-memory"                   // Optional filter
})
// Returns: [
//   { pack: "mind-v5", description: "20 AI memory skills", version: "1.1.0" },
//   { pack: "web3-defi", description: "DeFi development skills", version: "2.1.0" }
// ]
```

### 2. `spawner_load` - Local File Loading

```typescript
// CHANGED BEHAVIOR

spawner_load({
  skill_id: "event-architect",
  pack?: "mind-v5"                    // Optional: specify pack if skill exists in multiple
})

// OLD: Made API call, returned combined markdown
// NEW: Reads from local files, returns structured content

// Returns:
{
  skill_id: "event-architect",
  pack: "mind-v5",
  source: "local",                    // Indicates loaded from disk

  // Full content from all YAML files:
  skill: { /* full skill.yaml content */ },
  sharp_edges: { /* full sharp-edges.yaml content */ },
  validations: { /* full validations.yaml content */ },
  collaboration: { /* full collaboration.yaml content */ },

  // Formatted for context injection:
  formatted_prompt: "## Event Architect\n\nYou are a senior event sourcing architect..."
}
```

### 3. `spawner_validate` - Run Local Validations

```typescript
// NEW: Run validations from installed skills against code

spawner_validate({
  skill_id: "event-architect",
  code: "class MyEvent:\n    def __init__(self)...",
  file_path: "src/events/my_event.py"
})

// Returns:
{
  passed: false,
  violations: [
    {
      rule_id: "event-missing-correlation-id",
      severity: "error",
      message: "Event class missing correlation_id field",
      fix_action: "Add correlation_id: UUID field",
      line: 1
    },
    {
      rule_id: "event-mutable-dataclass",
      severity: "error",
      message: "Event dataclass should be frozen",
      fix_action: "Change @dataclass to @dataclass(frozen=True)"
    }
  ]
}
```

---

## GitHub Repository Structure

```
github.com/vibeship/spawner-skills/
├── README.md
├── registry.yaml                     # Master list of all packs
│
├── mind-v5/                          # Skill pack
│   ├── manifest.yaml
│   ├── event-architect/
│   │   ├── skill.yaml
│   │   ├── sharp-edges.yaml
│   │   ├── validations.yaml
│   │   └── collaboration.yaml
│   ├── vector-specialist/
│   └── ...
│
├── web3-defi/                        # Another pack
│   ├── manifest.yaml
│   └── ...
│
└── templates/                        # For creating new skills
    ├── skill.yaml.template
    └── ...
```

### Master Registry (`registry.yaml`)

```yaml
# Central registry of available packs
packs:
  - id: mind-v5
    name: Mind v5 AI Memory Skills
    version: 1.1.0
    description: 20 specialist skills for AI memory systems
    skills_count: 20
    tags: [ai-memory, event-sourcing, vector-search]

  - id: web3-defi
    name: Web3 DeFi Skills
    version: 2.1.0
    description: Skills for DeFi development
    skills_count: 8
    tags: [web3, defi, solidity]

registry_version: 1
updated_at: 2025-12-27T10:00:00Z
```

---

## Implementation Details

### Install Flow

```python
async def install_pack(pack_name: str, source: str = "github") -> Result:
    """Install a skill pack from GitHub or local path."""

    # 1. Resolve source URL
    if source == "github":
        base_url = "https://github.com/vibeship/spawner-skills"
        manifest_url = f"{base_url}/raw/main/{pack_name}/manifest.yaml"
    else:
        manifest_url = Path(source) / "manifest.yaml"

    # 2. Fetch and validate manifest
    manifest = await fetch_yaml(manifest_url)
    if not validate_manifest(manifest):
        return Result.err("Invalid manifest")

    # 3. Determine install path
    install_path = Path.home() / ".spawner" / "skills" / pack_name

    # 4. Clone or copy skill pack
    if source == "github":
        # Use git sparse checkout for efficiency (only this pack)
        await git_sparse_clone(base_url, pack_name, install_path)
    else:
        await copy_directory(source, install_path)

    # 5. Update registry
    registry = load_registry()
    registry.installed.append({
        "pack": pack_name,
        "version": manifest.version,
        "installed_at": datetime.now(UTC),
        "source": base_url if source == "github" else source,
        "path": str(install_path),
        "skills_count": len(manifest.skills)
    })
    save_registry(registry)

    # 6. Validate installation
    validation = await validate_installation(install_path, manifest)
    if not validation.ok:
        return Result.err(f"Installation incomplete: {validation.errors}")

    return Result.ok({
        "success": True,
        "message": f"Installed {len(manifest.skills)} skills",
        "path": str(install_path)
    })
```

### Load Flow

```python
async def load_skill(skill_id: str, pack: str = None) -> Result:
    """Load a skill from local installation."""

    # 1. Find skill in installed packs
    skill_path = None
    found_pack = None

    registry = load_registry()
    for installed in registry.installed:
        check_path = Path(installed.path) / skill_id
        if check_path.exists():
            if pack and installed.pack != pack:
                continue
            skill_path = check_path
            found_pack = installed.pack
            break

    if not skill_path:
        # Skill not found - suggest installation
        available = await get_packs_containing_skill(skill_id)
        if available:
            return Result.err(
                f"Skill '{skill_id}' not installed. "
                f"Run: spawner_skills({{ action: 'install', pack: '{available[0]}' }})"
            )
        return Result.err(f"Skill '{skill_id}' not found in any pack")

    # 2. Read all YAML files
    skill_data = {}
    for filename in ["skill.yaml", "sharp-edges.yaml", "validations.yaml", "collaboration.yaml"]:
        file_path = skill_path / filename
        if file_path.exists():
            skill_data[filename.replace(".yaml", "").replace("-", "_")] = load_yaml(file_path)

    # 3. Generate formatted prompt for context injection
    formatted = format_skill_for_prompt(skill_data)

    return Result.ok({
        "skill_id": skill_id,
        "pack": found_pack,
        "source": "local",
        **skill_data,
        "formatted_prompt": formatted
    })


def format_skill_for_prompt(skill_data: dict) -> str:
    """Format skill data for LLM context injection."""

    skill = skill_data.get("skill", {})
    sharp_edges = skill_data.get("sharp_edges", {})
    validations = skill_data.get("validations", {})
    collaboration = skill_data.get("collaboration", {})

    sections = []

    # Identity
    sections.append(f"## {skill.get('name', 'Unknown Skill')}\n")
    sections.append(skill.get('identity', ''))

    # Handoff Protocol
    if skill.get('handoffs'):
        sections.append("\n---\n\n## HANDOFF PROTOCOL\n")
        sections.append(f"You are operating as: **{skill.get('name')}**\n")
        sections.append(f"Your specialty: {skill.get('description')}\n")
        sections.append("\n### HANDOFF TRIGGERS\n")
        sections.append("| If user mentions... | Action |")
        sections.append("|---------------------|--------|")
        for h in skill.get('handoffs', []):
            sections.append(f"| {h['trigger']} | `spawner_load({{ skill_id: \"{h['to']}\" }})` |")

    # Domain
    sections.append("\n---\n\n## Your Domain\n")
    sections.append("You are authoritative on:")
    for domain in skill.get('owns', []):
        sections.append(f"- {domain}")

    # Patterns with CODE EXAMPLES
    if skill.get('patterns'):
        sections.append("\n---\n\n## Patterns\n")
        for p in skill['patterns']:
            sections.append(f"**{p['name']}**: {p['description']}")
            sections.append(f"When: {p['when']}")
            if p.get('example'):
                sections.append(f"\n```python\n{p['example'].strip()}\n```\n")

    # Anti-Patterns
    if skill.get('anti_patterns'):
        sections.append("\n---\n\n## Anti-Patterns\n")
        for ap in skill['anti_patterns']:
            sections.append(f"**{ap['name']}**: {ap['description']}")
            sections.append(f"Why: {ap['why']}")
            sections.append(f"Instead: {ap['instead']}\n")

    # Sharp Edges with FULL DETAIL
    if sharp_edges.get('sharp_edges'):
        sections.append("\n---\n\n## Sharp Edges (Gotchas)\n")
        for edge in sharp_edges['sharp_edges']:
            sections.append(f"**[{edge['severity'].upper()}] {edge['summary']}**")
            sections.append(f"\n{edge['situation']}")
            sections.append(f"\nWhy: {edge['why']}")
            if edge.get('solution'):
                sections.append(f"\nSolution:\n```python\n{edge['solution'].strip()}\n```")
            if edge.get('symptoms'):
                sections.append("\nSymptoms:")
                for s in edge['symptoms']:
                    sections.append(f"- {s}")
            sections.append("")

    # Cross-Domain Insights
    if collaboration.get('cross_domain_insights'):
        sections.append("\n---\n\n## Cross-Domain Insights\n")
        for insight in collaboration['cross_domain_insights']:
            sections.append(f"**From {insight['domain']}:** {insight['insight']}")
            sections.append(f"_Applies when: {insight['applies_when']}_\n")

    # Prerequisites
    if collaboration.get('prerequisites'):
        sections.append("\n---\n\n## Prerequisites\n")
        prereqs = collaboration['prerequisites']
        if prereqs.get('knowledge'):
            sections.append("- **knowledge:** " + ", ".join(prereqs['knowledge']))

    return "\n".join(sections)
```

### Update Flow

```python
async def check_updates() -> list:
    """Check for updates to installed packs."""

    # Fetch current registry from GitHub
    remote_registry = await fetch_yaml(
        "https://github.com/vibeship/spawner-skills/raw/main/registry.yaml"
    )

    updates = []
    local_registry = load_registry()

    for installed in local_registry.installed:
        remote_pack = next(
            (p for p in remote_registry.packs if p.id == installed.pack),
            None
        )
        if remote_pack and version_gt(remote_pack.version, installed.version):
            updates.append({
                "pack": installed.pack,
                "current": installed.version,
                "latest": remote_pack.version,
                "changes": await get_changelog(installed.pack, installed.version, remote_pack.version)
            })

    return updates


async def update_pack(pack_name: str = None) -> Result:
    """Update one or all installed packs."""

    updates = await check_updates()

    if pack_name:
        updates = [u for u in updates if u["pack"] == pack_name]

    if not updates:
        return Result.ok({"message": "All packs up to date"})

    results = []
    for update in updates:
        # Git pull in the pack directory
        pack_path = get_pack_path(update["pack"])
        await git_pull(pack_path)

        # Update registry version
        update_registry_version(update["pack"], update["latest"])

        results.append({
            "pack": update["pack"],
            "from": update["current"],
            "to": update["latest"]
        })

    return Result.ok({"updated": results})
```

---

## Error Handling

### Skill Not Installed

```python
# When spawner_load is called for a skill that's not installed:

spawner_load({ skill_id: "event-architect" })

# Returns:
{
  "error": "skill_not_installed",
  "message": "Skill 'event-architect' is not installed locally.",
  "suggestion": "Run: spawner_skills({ action: 'install', pack: 'mind-v5' })",
  "available_in": ["mind-v5"]
}
```

### Pack Not Found

```python
spawner_skills({ action: "install", pack: "nonexistent" })

# Returns:
{
  "error": "pack_not_found",
  "message": "Pack 'nonexistent' not found in registry.",
  "available": ["mind-v5", "web3-defi", "..."],
  "suggestion": "Run: spawner_skills({ action: 'available' }) to see all packs"
}
```

### Offline Mode

```python
# If GitHub is unreachable during install:
{
  "error": "network_error",
  "message": "Cannot reach GitHub. Check your connection.",
  "suggestion": "For offline install, use: spawner_skills({ action: 'install', pack: 'mind-v5', source: 'local', path: '/path/to/pack' })"
}

# Loading always works offline (local files):
spawner_load({ skill_id: "event-architect" })  # Works offline
```

---

## Migration Path

### For Existing Users

```python
# Spawner detects old-style usage and suggests migration:

spawner_load({ skill_id: "event-architect" })

# If skill not installed locally but exists in remote registry:
{
  "warning": "legacy_mode",
  "message": "Loading from API (costs money). Install locally for free usage.",
  "suggestion": "Run: spawner_skills({ action: 'install', pack: 'mind-v5' })",

  # Still returns the skill (backwards compatible)
  "skill": { ... },
  "formatted_prompt": "..."
}
```

### Deprecation Timeline

1. **v2.0**: Add install/local features, API loading still works
2. **v2.5**: Warn on API loading, encourage local install
3. **v3.0**: API loading removed, local-only

---

## Cost Analysis

| Operation | Old Cost | New Cost |
|-----------|----------|----------|
| Install pack (20 skills) | N/A | ~$0.01 (one API call to fetch manifest) |
| Load skill | ~$0.02-0.05 | **$0** (local file read) |
| Check updates | N/A | ~$0.001 (fetch registry.yaml) |
| 100 skill loads/day | ~$2-5/day | **$0/day** |
| 1000 users, 100 loads each | ~$200-500/day | **$0.01/day** (just update checks) |

**Annual savings for 1000 active users: ~$70,000 - $180,000**

---

## Next Steps

1. [ ] Create `spawner-skills` GitHub repository
2. [ ] Implement `spawner_skills` install/update actions
3. [ ] Modify `spawner_load` to read from local files
4. [ ] Add `spawner_validate` for running validations
5. [ ] Migrate Mind v5 skills to new pack format
6. [ ] Write user documentation
7. [ ] Add to Spawner CLI: `spawner install mind-v5`
