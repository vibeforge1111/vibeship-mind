"""
Background processing for Mind v3.

Processes captured events into structured data:
- Categorizes events by type
- Extracts structured information
- Links to existing graph nodes
- Consolidates redundant data
"""
from .categorize import EventCategorizer, CategorizedEvent

__all__ = ["EventCategorizer", "CategorizedEvent"]
