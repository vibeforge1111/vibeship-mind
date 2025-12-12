"""Sharp edge detection engine with session-aware throttling."""

import fnmatch
import re
from typing import Literal, Optional

from mind.models import SharpEdge, DetectionPattern, EdgeWarning


class EdgeDetector:
    """Detects sharp edges at decision points.

    Key features:
    - Session-based throttling: same edge won't warn twice per session
    - Intent detection: cheap string matching on queries
    - Code detection: regex patterns when code is present
    - Stack detection: match project tech stack
    """

    def __init__(self) -> None:
        self._edges: list[SharpEdge] = []
        self._warned_this_session: set[str] = set()

    def load_edges(self, edges: list[SharpEdge]) -> None:
        """Load sharp edges for detection."""
        self._edges = edges

    def reset_session(self) -> None:
        """Reset session state. Call when starting a new session."""
        self._warned_this_session.clear()

    def check_intent(
        self,
        query: str,
        project_stack: Optional[list[str]] = None,
    ) -> list[EdgeWarning]:
        """Check intent/query for potential edges. Cheap string matching.

        Use this on mind_get_context queries, decision reasoning, etc.

        Args:
            query: The user's query or intent text
            project_stack: Project's tech stack for context matching

        Returns:
            List of EdgeWarning for any matching edges
        """
        warnings: list[EdgeWarning] = []
        stack_str = " ".join(project_stack or []).lower()

        for edge in self._edges:
            # Skip if already warned this session
            if edge.id in self._warned_this_session:
                continue

            for pattern in edge.detection_patterns:
                match = None

                if pattern.type == "intent":
                    match = self._match_keywords(pattern.pattern, query)
                    if match:
                        match = f"query: '{match}'"

                elif pattern.type == "context" and stack_str:
                    match = self._match_keywords(pattern.pattern, stack_str)
                    if match:
                        match = f"stack: {match}"

                if match:
                    severity = self._determine_severity(pattern.type)
                    warnings.append(EdgeWarning(
                        edge_id=edge.id,
                        title=edge.title,
                        severity=severity,
                        matched=match,
                        workaround=edge.workaround,
                        symptoms=edge.symptoms,
                    ))
                    self._warned_this_session.add(edge.id)
                    break  # One warning per edge

        return warnings

    def check_code(
        self,
        code: str,
        file_path: Optional[str] = None,
    ) -> list[EdgeWarning]:
        """Check code for pattern matches. Use when code is present in query.

        Args:
            code: Code snippet to check
            file_path: Optional file path for file pattern filtering

        Returns:
            List of EdgeWarning for any matching edges
        """
        warnings: list[EdgeWarning] = []

        for edge in self._edges:
            # Skip if already warned this session
            if edge.id in self._warned_this_session:
                continue

            for pattern in edge.detection_patterns:
                if pattern.type != "code":
                    continue

                # Check file pattern first if specified
                if pattern.file_pattern and file_path:
                    if not fnmatch.fnmatch(file_path, pattern.file_pattern):
                        continue

                # Check code pattern (regex)
                try:
                    match = re.search(pattern.pattern, code, re.IGNORECASE)
                    if match:
                        matched_text = match.group(0)
                        # Truncate long matches
                        if len(matched_text) > 50:
                            matched_text = matched_text[:50] + "..."

                        warnings.append(EdgeWarning(
                            edge_id=edge.id,
                            title=edge.title,
                            severity="high",  # Code matches are always high
                            matched=f"code: '{matched_text}'",
                            workaround=edge.workaround,
                            symptoms=edge.symptoms,
                        ))
                        self._warned_this_session.add(edge.id)
                        break  # One warning per edge
                except re.error:
                    # Invalid regex, skip
                    pass

        return warnings

    def check_stack(
        self,
        stack: list[str],
        current_goal: Optional[str] = None,
    ) -> list[EdgeWarning]:
        """Check project stack for relevant edges. Use on session start.

        Args:
            stack: Project's tech stack (e.g., ["vercel", "edge-functions", "typescript"])
            current_goal: Current project goal for additional context

        Returns:
            List of EdgeWarning for relevant edges (severity: info)
        """
        warnings: list[EdgeWarning] = []
        stack_str = " ".join(stack).lower()
        goal_str = (current_goal or "").lower()
        combined = f"{stack_str} {goal_str}"

        for edge in self._edges:
            # Skip if already warned this session
            if edge.id in self._warned_this_session:
                continue

            for pattern in edge.detection_patterns:
                if pattern.type != "context":
                    continue

                match = self._match_keywords(pattern.pattern, combined)
                if match:
                    warnings.append(EdgeWarning(
                        edge_id=edge.id,
                        title=edge.title,
                        severity="info",  # Stack matches are informational
                        matched=f"stack: {match}",
                        workaround=edge.workaround,
                        symptoms=edge.symptoms,
                    ))
                    self._warned_this_session.add(edge.id)
                    break

        return warnings

    def check_symptoms(
        self,
        symptoms_text: str,
    ) -> list[EdgeWarning]:
        """Check if symptoms match known edges. Use on issue creation.

        Args:
            symptoms_text: Description of symptoms/problems

        Returns:
            List of EdgeWarning for edges with matching symptoms
        """
        warnings: list[EdgeWarning] = []
        symptoms_lower = symptoms_text.lower()

        for edge in self._edges:
            # Skip if already warned this session
            if edge.id in self._warned_this_session:
                continue

            # Check if any of the edge's symptoms match
            for symptom in edge.symptoms:
                if symptom.lower() in symptoms_lower:
                    warnings.append(EdgeWarning(
                        edge_id=edge.id,
                        title=edge.title,
                        severity="medium",
                        matched=f"symptom: '{symptom}'",
                        workaround=edge.workaround,
                        symptoms=edge.symptoms,
                    ))
                    self._warned_this_session.add(edge.id)
                    break

        return warnings

    def check_all(
        self,
        query: Optional[str] = None,
        code: Optional[str] = None,
        stack: Optional[list[str]] = None,
        file_path: Optional[str] = None,
    ) -> list[EdgeWarning]:
        """Combined check for all pattern types.

        Convenience method that runs all relevant checks based on provided inputs.

        Args:
            query: Query/intent text (triggers intent check)
            code: Code snippet (triggers code check)
            stack: Tech stack (triggers stack/context check)
            file_path: File path for code pattern filtering

        Returns:
            Combined list of warnings (deduplicated by edge_id)
        """
        warnings: list[EdgeWarning] = []
        seen_edges: set[str] = set()

        # Intent check (cheap, always run if query provided)
        if query:
            for w in self.check_intent(query, stack):
                if w.edge_id not in seen_edges:
                    warnings.append(w)
                    seen_edges.add(w.edge_id)

        # Code check (only if code provided)
        if code:
            for w in self.check_code(code, file_path):
                if w.edge_id not in seen_edges:
                    warnings.append(w)
                    seen_edges.add(w.edge_id)

        # Stack check (for context patterns)
        if stack and not query:  # Only if not already checked via intent
            for w in self.check_stack(stack):
                if w.edge_id not in seen_edges:
                    warnings.append(w)
                    seen_edges.add(w.edge_id)

        return warnings

    def _match_keywords(self, pattern: str, text: str) -> Optional[str]:
        """Match pipe-separated keywords against text.

        Args:
            pattern: Pipe-separated keywords (e.g., "crypto|uuid|token")
            text: Text to search in

        Returns:
            First matched keyword or None
        """
        text_lower = text.lower()
        keywords = pattern.lower().split("|")
        for keyword in keywords:
            keyword = keyword.strip()
            if keyword and keyword in text_lower:
                return keyword
        return None

    def _determine_severity(
        self,
        pattern_type: str,
    ) -> Literal["info", "medium", "high"]:
        """Determine warning severity based on pattern type."""
        if pattern_type == "code":
            return "high"
        elif pattern_type == "intent":
            return "high"
        elif pattern_type == "context":
            return "medium"
        return "info"
