# Session: 2025-12-13

## Focus
Implementing session memory (SESSION.md) for Mind v2

## Constraints
- No daemon, MCP-only
- Keep it simple - just a file Claude maintains

## Tried (didn't work)
- httpOnly cookies for JWT -> Safari blocks in iframe
- bcrypt default rounds (10) -> tests timeout

## Discovered
- `parse_session_section()` function extracts items from SESSION.md sections
- Promotion logic uses regex to detect tech patterns and file paths
- SESSION.md gets cleared on new session (30 min gap)

## Open Questions
- Should we add a CLI command to view session state?

## Out of Scope
- Database storage for session
- Complex session tracking
- Episode management from archived version
