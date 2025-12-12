"""Sharp edge detection engine."""

import re
from dataclasses import dataclass
from typing import Optional

from mind.models import SharpEdge, DetectionPattern


@dataclass
class EdgeWarning:
    """Warning about a potential sharp edge."""
    edge: SharpEdge
    matched_pattern: DetectionPattern
    severity: str  # "high", "medium", "low"
    recommendation: str


class EdgeDetector:
    """Detects sharp edges before mistakes happen."""

    def __init__(self):
        self._edges: list[SharpEdge] = []

    def load_edges(self, edges: list[SharpEdge]) -> None:
        """Load sharp edges for detection."""
        self._edges = edges

    def check(
        self,
        code: Optional[str] = None,
        intent: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> list[EdgeWarning]:
        """Check for potential sharp edges.

        Args:
            code: Code being written or suggested
            intent: What the user/AI is trying to do
            context: Additional context (runtime, framework, file_path, etc.)

        Returns:
            List of warnings about potential sharp edges
        """
        warnings: list[EdgeWarning] = []
        context = context or {}

        for edge in self._edges:
            for pattern in edge.detection_patterns:
                match = self._check_pattern(pattern, code, intent, context)
                if match:
                    severity = self._determine_severity(pattern.type, match)
                    warnings.append(EdgeWarning(
                        edge=edge,
                        matched_pattern=pattern,
                        severity=severity,
                        recommendation=edge.workaround,
                    ))
                    break  # One warning per edge is enough

        return warnings

    def _check_pattern(
        self,
        pattern: DetectionPattern,
        code: Optional[str],
        intent: Optional[str],
        context: dict,
    ) -> Optional[str]:
        """Check if a pattern matches.

        Returns the matched string or None.
        """
        if pattern.type == "code" and code:
            # Check file pattern first
            if pattern.file_pattern:
                file_path = context.get("file_path", "")
                if not self._match_glob(pattern.file_pattern, file_path):
                    return None

            # Check code pattern (regex)
            try:
                match = re.search(pattern.pattern, code, re.IGNORECASE)
                if match:
                    return match.group(0)
            except re.error:
                pass

        elif pattern.type == "context":
            # Check context keywords
            context_str = " ".join(str(v) for v in context.values()).lower()
            keywords = pattern.pattern.lower().split("|")
            for keyword in keywords:
                if keyword.strip() in context_str:
                    return keyword.strip()

        elif pattern.type == "intent" and intent:
            # Check intent keywords
            intent_lower = intent.lower()
            keywords = pattern.pattern.lower().split("|")
            for keyword in keywords:
                if keyword.strip() in intent_lower:
                    return keyword.strip()

        return None

    def _match_glob(self, pattern: str, path: str) -> bool:
        """Simple glob matching for file patterns."""
        import fnmatch
        return fnmatch.fnmatch(path, pattern)

    def _determine_severity(self, pattern_type: str, match: str) -> str:
        """Determine warning severity based on pattern type and match."""
        if pattern_type == "code":
            return "high"
        elif pattern_type == "context":
            return "medium"
        else:
            return "low"
