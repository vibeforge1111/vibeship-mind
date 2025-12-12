"""Tests for sharp edge detection."""

import pytest

from mind.models import SharpEdge, DetectionPattern
from mind.engine.detection import EdgeDetector


class TestEdgeDetector:
    """Tests for EdgeDetector."""

    def test_detect_code_pattern(self):
        """Test detecting code patterns."""
        detector = EdgeDetector()
        detector.load_edges([
            SharpEdge(
                title="No eval",
                description="Don't use eval()",
                workaround="Use safer alternatives",
                detection_patterns=[
                    DetectionPattern(
                        type="code",
                        pattern=r"eval\s*\(",
                        description="eval() usage",
                    ),
                ],
            ),
        ])

        warnings = detector.check(code="result = eval(user_input)")

        assert len(warnings) == 1
        assert warnings[0].severity == "high"
        assert "eval" in warnings[0].edge.title.lower()

    def test_detect_context_pattern(self):
        """Test detecting context patterns."""
        detector = EdgeDetector()
        detector.load_edges([
            SharpEdge(
                title="No Node crypto in Edge",
                description="Edge runtime doesn't have Node crypto",
                workaround="Use Web Crypto API",
                detection_patterns=[
                    DetectionPattern(
                        type="context",
                        pattern="edge|vercel",
                        description="Edge runtime context",
                    ),
                ],
            ),
        ])

        warnings = detector.check(
            code="import crypto",
            context={"runtime": "edge"},
        )

        assert len(warnings) == 1
        assert warnings[0].severity == "medium"

    def test_detect_intent_pattern(self):
        """Test detecting intent patterns."""
        detector = EdgeDetector()
        detector.load_edges([
            SharpEdge(
                title="Auth cookies in Safari",
                description="Safari ITP blocks third-party cookies",
                workaround="Use first-party cookies or tokens",
                detection_patterns=[
                    DetectionPattern(
                        type="intent",
                        pattern="auth|login|session",
                        description="Authentication intent",
                    ),
                ],
            ),
        ])

        warnings = detector.check(intent="implement user authentication")

        assert len(warnings) == 1
        assert warnings[0].severity == "low"

    def test_no_match(self):
        """Test when no patterns match."""
        detector = EdgeDetector()
        detector.load_edges([
            SharpEdge(
                title="SQL injection",
                description="Watch for SQL injection",
                workaround="Use parameterized queries",
                detection_patterns=[
                    DetectionPattern(
                        type="code",
                        pattern=r"execute\s*\(.*\+",
                        description="String concatenation in SQL",
                    ),
                ],
            ),
        ])

        warnings = detector.check(code="cursor.execute('SELECT * FROM users WHERE id = ?', [user_id])")

        assert len(warnings) == 0

    def test_multiple_edges(self):
        """Test detecting multiple edges."""
        detector = EdgeDetector()
        detector.load_edges([
            SharpEdge(
                title="No eval",
                description="Don't use eval()",
                workaround="Use safer alternatives",
                detection_patterns=[
                    DetectionPattern(type="code", pattern=r"eval\s*\(", description="eval usage"),
                ],
            ),
            SharpEdge(
                title="No exec",
                description="Don't use exec()",
                workaround="Use safer alternatives",
                detection_patterns=[
                    DetectionPattern(type="code", pattern=r"exec\s*\(", description="exec usage"),
                ],
            ),
        ])

        warnings = detector.check(code="eval(input); exec(code)")

        assert len(warnings) == 2

    def test_file_pattern_matching(self):
        """Test file pattern matching for code patterns."""
        detector = EdgeDetector()
        detector.load_edges([
            SharpEdge(
                title="No setTimeout in edge",
                description="setTimeout may not work as expected in edge",
                workaround="Use different timing approach",
                detection_patterns=[
                    DetectionPattern(
                        type="code",
                        pattern=r"setTimeout",
                        description="setTimeout usage",
                        file_pattern="*.edge.ts",
                    ),
                ],
            ),
        ])

        # Should not match - wrong file pattern
        warnings1 = detector.check(
            code="setTimeout(() => {}, 1000)",
            context={"file_path": "handler.ts"},
        )
        assert len(warnings1) == 0

        # Should match - correct file pattern
        warnings2 = detector.check(
            code="setTimeout(() => {}, 1000)",
            context={"file_path": "handler.edge.ts"},
        )
        assert len(warnings2) == 1
