"""
Session synthesis for Mind v3.

AI-powered synthesis at session end:
- Generate session summaries
- Double-confirm decisions
- Extract cross-session patterns
"""
from .session_end import SessionEndSynthesizer, SessionSummary

__all__ = ["SessionEndSynthesizer", "SessionSummary"]
