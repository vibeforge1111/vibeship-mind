"""
Query expansion for Mind v3 retrieval.

Expands user queries to find more relevant context by:
- Extracting key terms
- Adding synonyms and related terms
- Generating sub-queries for multi-intent queries
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ExpanderConfig:
    """Configuration for query expander."""

    enabled: bool = True
    max_expansions: int = 3
    include_synonyms: bool = True
    extract_entities: bool = True


@dataclass
class ExpandedQuery:
    """Result of query expansion."""

    original: str
    expanded_terms: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    sub_queries: list[str] = field(default_factory=list)

    def get_search_queries(self) -> list[str]:
        """Get all queries to search for."""
        queries = [self.original]
        queries.extend(self.sub_queries[:3])
        return queries

    def get_keywords(self) -> set[str]:
        """Get all keywords for filtering."""
        keywords = set(self.original.lower().split())
        keywords.update(term.lower() for term in self.expanded_terms)
        keywords.update(ent.lower() for ent in self.entities)
        return keywords


# Common programming synonyms
SYNONYMS = {
    "error": ["bug", "issue", "problem", "exception", "failure"],
    "bug": ["error", "issue", "problem", "defect"],
    "fix": ["resolve", "repair", "patch", "correct"],
    "function": ["method", "func", "procedure", "routine"],
    "class": ["type", "struct", "model"],
    "file": ["module", "script", "source"],
    "test": ["spec", "check", "verify", "validate"],
    "database": ["db", "storage", "store", "persistence"],
    "api": ["endpoint", "route", "interface"],
    "auth": ["authentication", "login", "authorization"],
    "config": ["configuration", "settings", "options"],
    "cache": ["caching", "memoize", "store"],
    "async": ["asynchronous", "concurrent", "parallel"],
    "deploy": ["deployment", "release", "ship"],
}

# Patterns to extract entities from queries
ENTITY_PATTERNS = [
    r"\b([A-Z][a-zA-Z]+(?:Service|Controller|Manager|Handler|Factory|Provider))\b",  # Class names
    r"\b([a-z_]+\.(?:py|ts|js|tsx|jsx|go|rs|java))\b",  # File names
    r"\bdef\s+([a-z_]+)\b",  # Python functions
    r"\bfunction\s+([a-zA-Z_]+)\b",  # JS functions
    r"\bclass\s+([A-Z][a-zA-Z]+)\b",  # Class definitions
]


class QueryExpander:
    """
    Expands queries for better retrieval.

    Uses synonyms, entity extraction, and sub-query generation
    to find more relevant context.
    """

    def __init__(self, config: ExpanderConfig | None = None):
        """Initialize expander."""
        self.config = config or ExpanderConfig()
        self._entity_patterns = [re.compile(p) for p in ENTITY_PATTERNS]

    def expand(self, query: str) -> ExpandedQuery:
        """
        Expand a query for better retrieval.

        Args:
            query: Original user query

        Returns:
            ExpandedQuery with expansions
        """
        if not self.config.enabled:
            return ExpandedQuery(original=query)

        result = ExpandedQuery(original=query)

        # Extract entities
        if self.config.extract_entities:
            result.entities = self._extract_entities(query)

        # Add synonyms
        if self.config.include_synonyms:
            result.expanded_terms = self._get_synonyms(query)

        # Generate sub-queries
        result.sub_queries = self._generate_sub_queries(query)

        return result

    def _extract_entities(self, query: str) -> list[str]:
        """Extract entity names from query."""
        entities = []

        for pattern in self._entity_patterns:
            matches = pattern.findall(query)
            entities.extend(matches)

        # Also look for CamelCase words
        camel_case = re.findall(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b", query)
        entities.extend(camel_case)

        return list(set(entities))[:self.config.max_expansions]

    def _get_synonyms(self, query: str) -> list[str]:
        """Get synonyms for query terms."""
        synonyms = []
        query_lower = query.lower()

        for term, syns in SYNONYMS.items():
            if term in query_lower:
                synonyms.extend(syns[:2])  # Max 2 synonyms per term

        return list(set(synonyms))[:self.config.max_expansions]

    def _generate_sub_queries(self, query: str) -> list[str]:
        """Generate sub-queries from a complex query."""
        sub_queries = []

        # Split on common conjunctions
        parts = re.split(r"\s+(?:and|or|but|then)\s+", query, flags=re.IGNORECASE)

        if len(parts) > 1:
            sub_queries.extend(part.strip() for part in parts if len(part.strip()) > 10)

        # Extract question parts
        if "?" in query:
            questions = query.split("?")
            sub_queries.extend(q.strip() + "?" for q in questions if len(q.strip()) > 10)

        return sub_queries[:self.config.max_expansions]
