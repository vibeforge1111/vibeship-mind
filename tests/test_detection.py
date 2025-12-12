"""Tests for sharp edge detection."""

import pytest

from mind.models import SharpEdge, DetectionPattern, EdgeWarning
from mind.engine.detection import EdgeDetector


class TestEdgeDetector:
    """Tests for EdgeDetector."""

    def test_check_code_pattern(self):
        """Test detecting code patterns."""
        detector = EdgeDetector()
        detector.load_edges([
            SharpEdge(
                id="edge_eval",
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

        warnings = detector.check_code(code="result = eval(user_input)")

        assert len(warnings) == 1
        assert warnings[0].severity == "high"
        assert "eval" in warnings[0].title.lower()
        assert "code:" in warnings[0].matched

    def test_check_intent_pattern(self):
        """Test detecting intent patterns."""
        detector = EdgeDetector()
        detector.load_edges([
            SharpEdge(
                id="edge_auth",
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

        warnings = detector.check_intent(query="implement user authentication")

        assert len(warnings) == 1
        assert warnings[0].severity == "high"  # Intent is now high severity
        assert "query:" in warnings[0].matched

    def test_check_stack_context(self):
        """Test detecting stack/context patterns."""
        detector = EdgeDetector()
        detector.load_edges([
            SharpEdge(
                id="edge_crypto",
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

        warnings = detector.check_stack(stack=["vercel", "edge-runtime"])

        assert len(warnings) == 1
        assert warnings[0].severity == "info"  # Stack matches are info
        assert "stack:" in warnings[0].matched

    def test_check_symptoms(self):
        """Test detecting symptoms that match known edges."""
        detector = EdgeDetector()
        detector.load_edges([
            SharpEdge(
                id="edge_timeout",
                title="Edge function timeout",
                description="Vercel Edge functions have 10s limit",
                workaround="Move to serverless function",
                symptoms=["timeout", "function execution exceeded"],
                detection_patterns=[],
            ),
        ])

        warnings = detector.check_symptoms("Getting timeout errors in production")

        assert len(warnings) == 1
        assert warnings[0].severity == "medium"
        assert "symptom:" in warnings[0].matched

    def test_no_match(self):
        """Test when no patterns match."""
        detector = EdgeDetector()
        detector.load_edges([
            SharpEdge(
                id="edge_sql",
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

        warnings = detector.check_code(
            code="cursor.execute('SELECT * FROM users WHERE id = ?', [user_id])"
        )

        assert len(warnings) == 0

    def test_session_throttling(self):
        """Test that same edge doesn't warn twice per session."""
        detector = EdgeDetector()
        detector.load_edges([
            SharpEdge(
                id="edge_eval",
                title="No eval",
                description="Don't use eval()",
                workaround="Use safer alternatives",
                detection_patterns=[
                    DetectionPattern(
                        type="code",
                        pattern=r"eval\s*\(",
                        description="eval usage",
                    ),
                ],
            ),
        ])

        # First check should warn
        warnings1 = detector.check_code(code="eval(x)")
        assert len(warnings1) == 1

        # Second check should NOT warn (already warned this session)
        warnings2 = detector.check_code(code="eval(y)")
        assert len(warnings2) == 0

    def test_session_reset(self):
        """Test that reset_session clears throttling."""
        detector = EdgeDetector()
        detector.load_edges([
            SharpEdge(
                id="edge_eval",
                title="No eval",
                description="Don't use eval()",
                workaround="Use safer alternatives",
                detection_patterns=[
                    DetectionPattern(
                        type="code",
                        pattern=r"eval\s*\(",
                        description="eval usage",
                    ),
                ],
            ),
        ])

        # First check warns
        warnings1 = detector.check_code(code="eval(x)")
        assert len(warnings1) == 1

        # Reset session
        detector.reset_session()

        # Now should warn again
        warnings2 = detector.check_code(code="eval(y)")
        assert len(warnings2) == 1

    def test_multiple_edges(self):
        """Test detecting multiple different edges."""
        detector = EdgeDetector()
        detector.load_edges([
            SharpEdge(
                id="edge_eval",
                title="No eval",
                description="Don't use eval()",
                workaround="Use safer alternatives",
                detection_patterns=[
                    DetectionPattern(type="code", pattern=r"eval\s*\(", description="eval usage"),
                ],
            ),
            SharpEdge(
                id="edge_exec",
                title="No exec",
                description="Don't use exec()",
                workaround="Use safer alternatives",
                detection_patterns=[
                    DetectionPattern(type="code", pattern=r"exec\s*\(", description="exec usage"),
                ],
            ),
        ])

        warnings = detector.check_code(code="eval(input); exec(code)")

        assert len(warnings) == 2

    def test_file_pattern_matching(self):
        """Test file pattern matching for code patterns."""
        detector = EdgeDetector()
        detector.load_edges([
            SharpEdge(
                id="edge_settimeout",
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
        warnings1 = detector.check_code(
            code="setTimeout(() => {}, 1000)",
            file_path="handler.ts",
        )
        assert len(warnings1) == 0

        # Should match - correct file pattern
        warnings2 = detector.check_code(
            code="setTimeout(() => {}, 1000)",
            file_path="handler.edge.ts",
        )
        assert len(warnings2) == 1

    def test_check_all_combined(self):
        """Test check_all runs all relevant checks."""
        detector = EdgeDetector()
        detector.load_edges([
            SharpEdge(
                id="edge_intent",
                title="Intent edge",
                description="Test",
                workaround="Test",
                detection_patterns=[
                    DetectionPattern(type="intent", pattern="token|auth", description="Auth intent"),
                ],
            ),
            SharpEdge(
                id="edge_code",
                title="Code edge",
                description="Test",
                workaround="Test",
                detection_patterns=[
                    DetectionPattern(type="code", pattern=r"crypto\.random", description="Crypto usage"),
                ],
            ),
        ])

        # Should find both - intent and code
        warnings = detector.check_all(
            query="generate auth token",
            code="const id = crypto.randomUUID()",
        )

        assert len(warnings) == 2
        edge_ids = {w.edge_id for w in warnings}
        assert "edge_intent" in edge_ids
        assert "edge_code" in edge_ids

    def test_edge_warning_model(self):
        """Test EdgeWarning model serialization."""
        warning = EdgeWarning(
            edge_id="edge_test",
            title="Test Edge",
            severity="high",
            matched="code: 'eval('",
            workaround="Don't use eval",
            symptoms=["Error", "Crash"],
        )

        data = warning.model_dump()
        assert data["edge_id"] == "edge_test"
        assert data["severity"] == "high"
        assert data["matched"] == "code: 'eval('"
        assert data["symptoms"] == ["Error", "Crash"]
