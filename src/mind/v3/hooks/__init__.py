"""Mind v3 Claude Code integration hooks.

- UserPromptSubmit: Inject relevant context before Claude sees prompt
- SessionEnd: Backup capture and consolidation
- TranscriptWatch: Real-time event capture (future)
"""
from .prompt_submit import (
    PromptSubmitHook,
    PromptSubmitConfig,
    HookResult,
)
from .session_end import (
    SessionEndHook,
    SessionEndConfig,
    SessionEndResult,
)

__all__ = [
    "PromptSubmitHook",
    "PromptSubmitConfig",
    "HookResult",
    "SessionEndHook",
    "SessionEndConfig",
    "SessionEndResult",
]
