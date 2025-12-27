# Security, Maintainability & Open Source Practices

<!-- doc-version: 1.0.0 | last-updated: 2025-12-14 -->

> **Purpose**: Security considerations, coding standards, and governance practices for Mind and the Vibeship ecosystem. Read this before contributing or deploying.

---

## Table of Contents

1. [Security by Phase](#security-by-phase)
   - Local (V1)
   - Cloud (V2)
   - Teams (V3)
2. [Threat Model](#threat-model)
3. [Security Checklist](#security-checklist)
4. [Data Privacy](#data-privacy)
5. [Maintainability Practices](#maintainability-practices)
6. [Documentation Standards](#documentation-standards)
7. [Open Source Governance](#open-source-governance)
8. [Contributor Security](#contributor-security)

---

## Security by Phase

### Phase 1: Local (V1) - Current

**Threat Surface**: Minimal - all data stays on user's machine.

#### Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Secrets in MEMORY.md | Medium | Secret detection before logging |
| File permissions too open | Low | Create with 0o700 (user-only) |
| Malicious CLAUDE.md injection | Low | Sanitize before injection |
| Path traversal in file ops | Low | Validate paths, use pathlib |

#### Security Controls (V1)

```python
# 1. File permissions - user-only access
def get_global_mind_dir() -> Path:
    global_dir = Path.home() / ".mind"
    if not global_dir.exists():
        global_dir.mkdir(parents=True, mode=0o700)
    return global_dir

# 2. Secret detection before logging
SECRET_PATTERNS = [
    r'(?i)password\s*[=:]\s*\S+',
    r'(?i)api[_-]?key\s*[=:]\s*\S+',
    r'(?i)secret\s*[=:]\s*\S+',
    r'(?i)token\s*[=:]\s*["\']?\w{20,}',
    r'(?i)bearer\s+\S{20,}',
    r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----',
    r'(?i)aws[_-]?(access|secret)',
    r'ghp_[a-zA-Z0-9]{36}',  # GitHub PAT
    r'sk-[a-zA-Z0-9]{48}',   # OpenAI key
]

def contains_secret(content: str) -> bool:
    """Check if content contains potential secrets."""
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, content):
            return True
    return False

def sanitize_for_logging(content: str) -> tuple[str, bool]:
    """Sanitize content before logging.

    Returns (sanitized_content, had_secrets).
    """
    if not contains_secret(content):
        return content, False

    # Redact secrets
    sanitized = content
    for pattern in SECRET_PATTERNS:
        sanitized = re.sub(pattern, '[REDACTED]', sanitized)

    return sanitized, True

# 3. Path validation
def validate_path(path: Path, base_dir: Path) -> bool:
    """Ensure path is within allowed directory."""
    try:
        resolved = path.resolve()
        base_resolved = base_dir.resolve()
        return resolved.is_relative_to(base_resolved)
    except (ValueError, RuntimeError):
        return False

# 4. Encoding safety (Windows cp1252 protection)
def safe_read(path: Path) -> str:
    """Read file with UTF-8, fallback to system encoding."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")

def safe_write(path: Path, content: str) -> None:
    """Write file with UTF-8 encoding."""
    path.write_text(content, encoding="utf-8")
```

#### .gitignore Defaults

```gitignore
# Mind - private by default
.mind/SESSION.md      # Always private (ephemeral)
.mind/state.json      # Always private (timestamps)
.mind/MEMORY.md       # Private by default, opt-in to share
.mind/REMINDERS.md    # Private (personal reminders)
```

---

### Phase 2: Cloud (V2) - Future

**Threat Surface**: Expands significantly - data in transit and at rest.

#### New Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Data in transit interception | High | TLS 1.3 only, certificate pinning |
| Data at rest exposure | High | Encryption at rest (AES-256) |
| Authentication bypass | High | OAuth 2.0 + PKCE, no password auth |
| API abuse / rate limiting | Medium | Rate limits, API keys with scopes |
| Cross-user data leak | Critical | Tenant isolation, row-level security |
| Backup exposure | Medium | Encrypted backups, key rotation |
| Third-party dependency vulns | Medium | Dependabot, regular audits |

#### Security Controls (V2)

```python
# 1. Transport security
ALLOWED_TLS_VERSIONS = ["TLSv1.3"]
CERTIFICATE_PINS = [
    "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
]

# 2. Authentication
AUTH_CONFIG = {
    "provider": "oauth2",
    "flow": "authorization_code_pkce",
    "token_expiry_minutes": 60,
    "refresh_token_expiry_days": 30,
    "require_email_verification": True,
}

# 3. Data encryption
ENCRYPTION_CONFIG = {
    "algorithm": "AES-256-GCM",
    "key_derivation": "PBKDF2-SHA256",
    "key_rotation_days": 90,
}

# 4. Rate limiting
RATE_LIMITS = {
    "mind_recall": "60/minute",
    "mind_log": "120/minute",
    "mind_search": "30/minute",
    "mind_sync": "10/minute",
}

# 5. Tenant isolation (Supabase RLS example)
"""
-- Row Level Security for memories table
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access own memories"
ON memories FOR ALL
USING (auth.uid() = user_id);

CREATE POLICY "Users can only insert own memories"
ON memories FOR INSERT
WITH CHECK (auth.uid() = user_id);
"""
```

#### Data Classification

| Data Type | Classification | Encryption | Sync |
|-----------|---------------|------------|------|
| MEMORY.md | Confidential | At rest + transit | User opt-in |
| SESSION.md | Internal | None (ephemeral) | Never |
| SELF_IMPROVE.md | Personal | At rest + transit | User account |
| Feedback | Personal | At rest + transit | User account |
| Usage analytics | Internal | Transit only | Aggregated only |

---

### Phase 3: Teams (V3) - Future

**Threat Surface**: Multi-tenant, shared data, access control complexity.

#### New Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Unauthorized team access | High | RBAC, invite-only |
| Data leak between teams | Critical | Strict tenant isolation |
| Privilege escalation | High | Least privilege, audit logs |
| Insider threat | Medium | Access logging, anomaly detection |
| Shared secret exposure | High | Separate team/personal memory |
| Member departure data retention | Medium | Offboarding workflow |
| Compliance (GDPR, SOC2) | High | Data residency, audit trails |

#### Security Controls (V3)

```python
# 1. Role-Based Access Control
TEAM_ROLES = {
    "owner": {
        "can_delete_team": True,
        "can_manage_members": True,
        "can_manage_billing": True,
        "can_view_all_memory": True,
        "can_edit_shared_memory": True,
    },
    "admin": {
        "can_delete_team": False,
        "can_manage_members": True,
        "can_manage_billing": False,
        "can_view_all_memory": True,
        "can_edit_shared_memory": True,
    },
    "member": {
        "can_delete_team": False,
        "can_manage_members": False,
        "can_manage_billing": False,
        "can_view_all_memory": True,
        "can_edit_shared_memory": True,
    },
    "viewer": {
        "can_delete_team": False,
        "can_manage_members": False,
        "can_manage_billing": False,
        "can_view_all_memory": True,
        "can_edit_shared_memory": False,
    },
}

# 2. Memory isolation
MEMORY_SCOPES = {
    "personal": "Only you can see this",
    "project": "Team members with project access",
    "team": "All team members",
    "public": "Anyone with link (future)",
}

# 3. Audit logging
AUDIT_EVENTS = [
    "memory.create",
    "memory.read",
    "memory.update",
    "memory.delete",
    "team.member_added",
    "team.member_removed",
    "team.role_changed",
    "auth.login",
    "auth.logout",
    "auth.failed_attempt",
]

# 4. Offboarding
def offboard_member(team_id: str, user_id: str):
    """Remove member and handle their data."""
    # 1. Revoke all access tokens
    revoke_user_tokens(user_id, team_id)

    # 2. Transfer ownership of shared resources
    transfer_ownership_to_team(user_id, team_id)

    # 3. Keep audit trail
    log_audit_event("team.member_removed", {
        "team_id": team_id,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # 4. Personal data stays with user
    # Team data stays with team
```

---

## Threat Model

### Assets to Protect

1. **User memories** - Decisions, learnings, personal patterns
2. **User preferences** - Code style, workflow habits
3. **Blind spots** - Sensitive self-improvement data
4. **Feedback** - Corrections that reveal user behavior
5. **Project context** - Potentially proprietary code references

### Threat Actors

| Actor | Motivation | Capability |
|-------|------------|------------|
| Opportunistic attacker | Data theft, ransom | Low-Medium |
| Targeted attacker | Competitive intel | Medium-High |
| Malicious insider | Data exfiltration | High |
| Nation state | Surveillance | Very High |
| Curious user | Accidental access | Low |

### Attack Vectors

```
LOCAL (V1):
├── File system access (physical or malware)
├── Malicious MCP server
└── Supply chain (compromised dependency)

CLOUD (V2):
├── API authentication bypass
├── Injection attacks (SQL, NoSQL, command)
├── Cross-site scripting (if web UI)
├── Man-in-the-middle (network)
├── Server compromise
└── Supply chain (npm, PyPI)

TEAMS (V3):
├── All of the above, plus:
├── Privilege escalation
├── Cross-tenant data leak
├── Social engineering (phishing for access)
└── Insider threat
```

---

## Security Checklist

### Before Every Release

- [ ] No secrets in codebase (run `gitleaks`)
- [ ] Dependencies scanned (`trivy`, `pip-audit`)
- [ ] No hardcoded credentials
- [ ] All user input validated
- [ ] SQL/command injection prevented
- [ ] File paths validated
- [ ] Encoding handled correctly
- [ ] Error messages don't leak info
- [ ] Logging doesn't include secrets

### Before Cloud Release (V2)

- [ ] TLS 1.3 only
- [ ] Authentication tested (OAuth, token expiry)
- [ ] Rate limiting configured
- [ ] Row-level security verified
- [ ] Encryption at rest enabled
- [ ] Backup encryption verified
- [ ] Penetration test completed
- [ ] OWASP Top 10 addressed
- [ ] Privacy policy updated
- [ ] Terms of service updated

### Before Team Release (V3)

- [ ] RBAC tested for all roles
- [ ] Tenant isolation verified
- [ ] Audit logging complete
- [ ] Offboarding workflow tested
- [ ] Data residency options
- [ ] SOC 2 compliance review
- [ ] GDPR compliance review
- [ ] Incident response plan

---

## Data Privacy

### What We Collect (V1 - Local)

Nothing. All data stays on user's machine.

### What We'll Collect (V2 - Cloud)

| Data | Purpose | Retention | User Control |
|------|---------|-----------|--------------|
| Account info | Authentication | Account lifetime | Delete account |
| Synced memories | Core feature | Until deleted | Delete anytime |
| Usage analytics | Product improvement | 90 days | Opt-out |
| Error logs | Debugging | 30 days | N/A (anonymized) |

### Data Rights

- **Access**: Export all your data anytime
- **Rectification**: Edit or correct your data
- **Erasure**: Delete your account and all data
- **Portability**: Export in standard format (JSON, Markdown)
- **Objection**: Opt out of analytics

### No-Sell Guarantee

**We will never sell user data.** Memory data is the user's, not ours.

---

## Maintainability Practices

### Code Standards

```python
# 1. Type hints everywhere
def parse_memory(content: str) -> dict[str, list[Entity]]:
    """Parse MEMORY.md into structured data.

    Args:
        content: Raw markdown content

    Returns:
        Dictionary with entity types as keys

    Raises:
        ParseError: If content is malformed
    """
    pass

# 2. Docstrings for public functions
# 3. No magic numbers - use constants
PATTERN_EXTRACTION_THRESHOLD = 3  # Not just "3"

# 4. Single responsibility - functions do one thing
# 5. Explicit over implicit
# 6. Fail fast with clear errors
```

### Testing Requirements

| Test Type | Coverage Target | When to Run |
|-----------|-----------------|-------------|
| Unit tests | >80% | Every commit |
| Integration tests | Critical paths | Every PR |
| Security tests | Auth, injection | Every release |
| Performance tests | Key operations | Before release |

```bash
# Run tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=mind --cov-report=html

# Run security scan
uv run pip-audit
trivy fs .
gitleaks detect
```

### Dependency Management

```toml
# pyproject.toml - pin major versions
[project]
dependencies = [
    "click>=8.0,<9.0",
    "mcp>=0.1.0,<1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pip-audit>=2.0",
]
```

```bash
# Update dependencies safely
uv sync
uv run pip-audit  # Check for vulnerabilities

# Lock for reproducibility
uv lock
```

### Error Handling

```python
# Good - specific, informative
class MindError(Exception):
    """Base exception for Mind errors."""
    pass

class MemoryParseError(MindError):
    """Failed to parse MEMORY.md."""
    def __init__(self, line: int, reason: str):
        self.line = line
        self.reason = reason
        super().__init__(f"Parse error at line {line}: {reason}")

# Bad - generic, unhelpful
raise Exception("Something went wrong")
```

### Logging Standards

```python
import logging

logger = logging.getLogger(__name__)

# Levels:
# DEBUG - Detailed diagnostic info
# INFO - Confirmation things work
# WARNING - Something unexpected but handled
# ERROR - Something failed
# CRITICAL - System unusable

# Good
logger.info("Session started", extra={"project": project_path.name})
logger.warning("Pattern decay applied", extra={"patterns": 5, "decayed": 2})
logger.error("Failed to parse MEMORY.md", extra={"error": str(e)})

# Bad - never log secrets
logger.info(f"User logged in with token {token}")  # NO!
```

---

## Documentation Standards

### Every File Needs

```python
"""
Module description - what this file does.

Key concepts:
- Concept 1
- Concept 2

Usage:
    from mind.parser import parse_memory
    entities = parse_memory(content)
"""
```

### Every Function Needs

```python
def complex_function(
    required_param: str,
    optional_param: int = 10,
) -> dict[str, Any]:
    """One-line description of what it does.

    Longer description if needed. Explain the "why"
    not just the "what".

    Args:
        required_param: What this parameter is for
        optional_param: What this controls (default: 10)

    Returns:
        Description of return value structure

    Raises:
        ValueError: When input is invalid
        IOError: When file operations fail

    Example:
        >>> result = complex_function("input")
        >>> result["key"]
        "expected_value"
    """
    pass
```

### Doc Files

| File | Purpose | Update Frequency |
|------|---------|------------------|
| README.md | Quick start, overview | Every release |
| CHANGELOG.md | Version history | Every release |
| docs/ARCHITECTURE.md | Technical deep dive | Major changes |
| docs/MCP_TOOLS.md | Tool reference | Tool changes |
| CONTRIBUTING.md | How to contribute | As needed |
| SECURITY.md | Security policy | As needed |

### Version Banners

Every doc file should have:

```markdown
<!-- doc-version: 2.1.0 | last-updated: 2025-12-14 -->
```

### Changelog Format

```markdown
# Changelog

## [2.1.0] - 2025-12-14

### Added
- SELF_IMPROVE.md for cross-project learning
- `mind patterns` CLI command
- Spawner integration hooks

### Changed
- mind_log now supports `type="feedback"`

### Fixed
- Windows encoding issue with mascot

### Security
- Added secret detection before logging

### Deprecated
- Old `mind daemon` commands (removed in 3.0)
```

---

## Open Source Governance

### License

**Apache 2.0** - Permissive, allows commercial use, requires attribution.

```
Copyright 2025 Vibeship

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
```

### Contribution Guidelines

See `CONTRIBUTING.md` for full details. Summary:

1. **Fork & Branch**: Create feature branch from `main`
2. **Code Standards**: Follow existing patterns
3. **Tests**: Add tests for new features
4. **Docs**: Update docs if behavior changes
5. **PR**: Submit with clear description
6. **Review**: Address feedback promptly

### Code of Conduct

We follow the [Contributor Covenant](https://www.contributor-covenant.org/).

**Be respectful. Be constructive. Be inclusive.**

### Decision Making

| Decision Type | Who Decides | Process |
|---------------|-------------|---------|
| Bug fix | Any maintainer | PR review |
| Small feature | 1 maintainer | PR review |
| Large feature | Core team | RFC + discussion |
| Architecture change | Core team | RFC + community input |
| Breaking change | Core team | Major version + migration guide |

### RFC Process

For significant changes:

1. Create `rfcs/000-feature-name.md`
2. Describe problem, solution, alternatives
3. Open PR for discussion
4. Core team votes after 1 week
5. Implement if approved

### Release Process

```bash
# 1. Update version
# pyproject.toml, CHANGELOG.md, docs

# 2. Create release branch
git checkout -b release/v2.1.0

# 3. Run full test suite
uv run pytest tests/ -v
uv run pip-audit

# 4. Build and test locally
uv build
uv run mind doctor

# 5. Tag and push
git tag v2.1.0
git push origin v2.1.0

# 6. Create GitHub release
# - Copy changelog section
# - Attach artifacts if any

# 7. Announce
# - Twitter
# - Discord
# - Changelog RSS
```

### Versioning

We use [Semantic Versioning](https://semver.org/):

- **MAJOR** (3.0.0): Breaking changes
- **MINOR** (2.1.0): New features, backward compatible
- **PATCH** (2.0.1): Bug fixes, backward compatible

### Security Vulnerability Reporting

**Do NOT open public issues for security vulnerabilities.**

Email: security@vibeship.co

We will:
1. Acknowledge within 48 hours
2. Investigate and fix
3. Release patch
4. Credit reporter (if desired)
5. Publish advisory after fix

---

## Contributor Security

### Before Contributing

1. **Never commit secrets** - Use environment variables
2. **Never log sensitive data** - Check your print statements
3. **Validate all input** - Assume it's malicious
4. **Use safe APIs** - pathlib over os.path, parameterized queries

### Security Review Checklist

For PRs touching security-sensitive code:

- [ ] No new dependencies without justification
- [ ] New dependencies scanned for vulnerabilities
- [ ] User input validated and sanitized
- [ ] File operations use validated paths
- [ ] No command injection possible
- [ ] No SQL/NoSQL injection possible
- [ ] Errors don't leak sensitive info
- [ ] Logging doesn't include secrets
- [ ] Authentication/authorization correct
- [ ] Rate limiting if applicable

### Signed Commits

For maintainers, enable commit signing:

```bash
git config --global commit.gpgsign true
git config --global user.signingkey YOUR_KEY_ID
```

---

## Quick Reference

### Security Contacts

- Security issues: security@vibeship.co
- General questions: GitHub Discussions
- Urgent issues: Twitter DM @meta_alchemist

### Key Files

| File | Purpose |
|------|---------|
| `.gitignore` | Excludes sensitive files |
| `SECURITY.md` | Security policy |
| `CONTRIBUTING.md` | How to contribute |
| `LICENSE` | Apache 2.0 |
| `CHANGELOG.md` | Version history |

### Commands

```bash
# Security scan
gitleaks detect
trivy fs .
uv run pip-audit

# Test
uv run pytest tests/ -v --cov=mind

# Release
git tag v2.1.0 && git push origin v2.1.0
```

---

*Security is everyone's responsibility. When in doubt, ask.*
