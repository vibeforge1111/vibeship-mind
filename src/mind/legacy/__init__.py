"""
Legacy Mind modules (v1/v2).

These modules are archived for reference but will be replaced by v3 implementations.
Import from here only for migration purposes.
"""

from .parser import Parser, InlineScanner, Entity, EntityType, IssueStatus, ParseResult, SessionSummary
from .context import ContextGenerator, update_claude_md
from .similarity import (
    semantic_similarity,
    semantic_search,
    semantic_search_strings,
    find_similar_rejection,
)

__all__ = [
    # Parser
    "Parser",
    "InlineScanner",
    "Entity",
    "EntityType",
    "IssueStatus",
    "ParseResult",
    "SessionSummary",
    # Context
    "ContextGenerator",
    "update_claude_md",
    # Similarity
    "semantic_similarity",
    "semantic_search",
    "semantic_search_strings",
    "find_similar_rejection",
]
