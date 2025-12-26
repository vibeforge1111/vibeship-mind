"""
Mind v3: Context Graph Architecture

A system of record for AI decisions - capturing not just what happened,
but why it was allowed to happen.

Modules:
- capture: Event capture from Claude Code transcripts
- intelligence: AI-powered analysis and extraction
- graph: Context graph storage (LanceDB)
- retrieval: Hybrid search and context injection
- memory: Cognitive memory system
- autonomy: Progressive autonomy tracking
- hooks: Claude Code integration hooks
- config: Unified configuration system
"""

from .config import V3Settings, get_settings, reset_settings

__version__ = "3.0.2"

__all__ = [
    "V3Settings",
    "get_settings",
    "reset_settings",
]
