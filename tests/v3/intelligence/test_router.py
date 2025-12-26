"""Tests for intelligence router."""
import pytest

from mind.v3.intelligence.router import (
    IntelligenceLevel,
    IntelligenceRouter,
    RouterConfig,
    TaskResult,
    LEVEL_ORDER,
    get_router,
    reset_router,
)
from mind.v3.intelligence.local import (
    extract_decisions_local,
    extract_entities_local,
    extract_patterns_local,
)


@pytest.fixture
def router():
    """Create a fresh router for each test."""
    return IntelligenceRouter()


@pytest.fixture(autouse=True)
def reset_default_router():
    """Reset the default router after each test."""
    yield
    reset_router()


class TestIntelligenceLevel:
    """Test IntelligenceLevel enum."""

    def test_level_values(self):
        """Should have correct string values."""
        assert IntelligenceLevel.LOCAL.value == "local"
        assert IntelligenceLevel.LOW.value == "low"
        assert IntelligenceLevel.MEDIUM.value == "medium"
        assert IntelligenceLevel.HIGH.value == "high"
        assert IntelligenceLevel.ULTRA.value == "ultra"

    def test_level_order(self):
        """Should have correct ordering."""
        assert LEVEL_ORDER == [
            IntelligenceLevel.LOCAL,
            IntelligenceLevel.LOW,
            IntelligenceLevel.MEDIUM,
            IntelligenceLevel.HIGH,
            IntelligenceLevel.ULTRA,
        ]


class TestRouterConfig:
    """Test RouterConfig dataclass."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = RouterConfig()

        assert config.decision_level == IntelligenceLevel.MEDIUM
        assert config.entity_level == IntelligenceLevel.LOCAL
        assert config.pattern_level == IntelligenceLevel.LOW
        assert config.enable_fallback is True
        assert config.min_confidence == 0.5

    def test_custom_config(self):
        """Should accept custom values."""
        config = RouterConfig(
            decision_level=IntelligenceLevel.HIGH,
            entity_level=IntelligenceLevel.MEDIUM,
            enable_fallback=False,
        )

        assert config.decision_level == IntelligenceLevel.HIGH
        assert config.entity_level == IntelligenceLevel.MEDIUM
        assert config.enable_fallback is False


class TestIntelligenceRouter:
    """Test IntelligenceRouter class."""

    def test_create_router(self, router):
        """Should create router with default config."""
        assert router.config is not None
        assert IntelligenceLevel.LOCAL in router._available_levels

    def test_register_handler(self, router):
        """Should register handler for task type."""
        def dummy_handler(text: str) -> dict:
            return {"content": {}, "confidence": 0.5}

        router.register_handler("test", IntelligenceLevel.LOCAL, dummy_handler)

        assert "test" in router._handlers
        assert IntelligenceLevel.LOCAL in router._handlers["test"]

    def test_set_level_available(self, router):
        """Should update available levels."""
        router.set_level_available(IntelligenceLevel.MEDIUM, True)
        assert IntelligenceLevel.MEDIUM in router._available_levels

        router.set_level_available(IntelligenceLevel.MEDIUM, False)
        assert IntelligenceLevel.MEDIUM not in router._available_levels

    def test_get_level_for_task(self, router):
        """Should return configured level for task type."""
        assert router.get_level_for_task("decision") == IntelligenceLevel.MEDIUM
        assert router.get_level_for_task("entity") == IntelligenceLevel.LOCAL
        assert router.get_level_for_task("pattern") == IntelligenceLevel.LOW
        assert router.get_level_for_task("unknown") == IntelligenceLevel.LOCAL

    def test_get_effective_level_with_fallback(self, router):
        """Should fallback to lower level when higher not available."""
        # Only LOCAL is available by default
        assert router.get_effective_level("decision") == IntelligenceLevel.LOCAL

        # Make MEDIUM available
        router.set_level_available(IntelligenceLevel.MEDIUM, True)
        assert router.get_effective_level("decision") == IntelligenceLevel.MEDIUM

    def test_get_effective_level_no_fallback(self):
        """Should return desired level when fallback disabled."""
        config = RouterConfig(enable_fallback=False)
        router = IntelligenceRouter(config)

        # Returns desired level even if not available
        assert router.get_effective_level("decision") == IntelligenceLevel.MEDIUM

    def test_route_with_handler(self, router):
        """Should route to registered handler."""
        def test_handler(text: str) -> dict:
            return {
                "content": {"result": text.upper()},
                "confidence": 0.8,
                "handler_name": "test_handler",
            }

        router.register_handler("test", IntelligenceLevel.LOCAL, test_handler)
        result = router.route("test", "hello world")

        assert isinstance(result, TaskResult)
        assert result.content == {"result": "HELLO WORLD"}
        assert result.confidence == 0.8
        assert result.level_used == IntelligenceLevel.LOCAL

    def test_route_no_handler(self, router):
        """Should return error result when no handler."""
        result = router.route("nonexistent", "text")

        assert result.confidence == 0.0
        assert "error" in result.metadata

    def test_route_with_fallback(self, router):
        """Should fallback to lower level handler."""
        def local_handler(text: str) -> dict:
            return {"content": {"level": "local"}, "confidence": 0.6}

        # Register only LOCAL handler
        router.register_handler("test", IntelligenceLevel.LOCAL, local_handler)

        # Try to route at MEDIUM level - should fallback to LOCAL
        result = router.route("test", "text", level=IntelligenceLevel.MEDIUM)

        assert result.content == {"level": "local"}
        assert result.level_used == IntelligenceLevel.LOCAL

    def test_get_available_handlers(self, router):
        """Should return summary of handlers."""
        def dummy(text: str) -> dict:
            return {}

        router.register_handler("decision", IntelligenceLevel.LOCAL, dummy)
        router.register_handler("decision", IntelligenceLevel.MEDIUM, dummy)
        router.register_handler("entity", IntelligenceLevel.LOCAL, dummy)

        handlers = router.get_available_handlers()

        assert "decision" in handlers
        assert "entity" in handlers
        assert "local" in handlers["decision"]
        assert "medium" in handlers["decision"]


class TestLocalHandlers:
    """Test local extraction handlers."""

    def test_extract_decisions_local(self):
        """Should extract decisions using regex."""
        text = "I decided to use SQLite because it's simpler than PostgreSQL."

        result = extract_decisions_local(text)

        assert "content" in result
        assert "confidence" in result
        assert result["handler_name"] == "local_decision_regex"
        assert "decisions" in result["content"]

    def test_extract_decisions_no_match(self):
        """Should return empty when no decisions found."""
        text = "The weather is nice today."

        result = extract_decisions_local(text)

        assert result["content"]["decisions"] == []
        assert result["confidence"] == 0.0

    def test_extract_entities_local(self):
        """Should extract entities using regex."""
        text = "I modified storage.py to use the Read tool for file access."

        result = extract_entities_local(text)

        assert "content" in result
        assert "entities" in result["content"]
        assert result["handler_name"] == "local_entity_regex"

        # Should find the file
        entities = result["content"]["entities"]
        assert any(e["name"] == "storage.py" for e in entities)

    def test_extract_patterns_local(self):
        """Should extract patterns using regex."""
        text = "I always use type hints in Python code. I prefer functional programming style."

        result = extract_patterns_local(text)

        assert "content" in result
        assert "patterns" in result["content"]
        assert result["handler_name"] == "local_pattern_regex"

        patterns = result["content"]["patterns"]
        assert len(patterns) >= 1

    def test_extract_patterns_habit(self):
        """Should detect habit patterns."""
        text = "I typically run tests before committing code."

        result = extract_patterns_local(text)
        patterns = result["content"]["patterns"]

        assert len(patterns) >= 1
        assert any(p["pattern_type"] == "habit" for p in patterns)

    def test_extract_patterns_avoidance(self):
        """Should detect avoidance patterns."""
        text = "I avoid using global variables in my code."

        result = extract_patterns_local(text)
        patterns = result["content"]["patterns"]

        assert len(patterns) >= 1
        assert any(p["pattern_type"] == "avoidance" for p in patterns)


class TestDefaultRouter:
    """Test default router singleton."""

    def test_get_router(self):
        """Should return configured router."""
        router = get_router()

        assert router is not None
        assert isinstance(router, IntelligenceRouter)

    def test_get_router_singleton(self):
        """Should return same instance."""
        router1 = get_router()
        router2 = get_router()

        assert router1 is router2

    def test_default_router_has_local_handlers(self):
        """Should have LOCAL handlers registered."""
        router = get_router()

        handlers = router.get_available_handlers()

        assert "decision" in handlers
        assert "entity" in handlers
        assert "pattern" in handlers
        assert all("local" in h for h in handlers.values())

    def test_reset_router(self):
        """Should reset singleton."""
        router1 = get_router()
        reset_router()
        router2 = get_router()

        assert router1 is not router2


class TestRouterIntegration:
    """Integration tests for router with real handlers."""

    def test_full_decision_extraction(self):
        """Should extract decisions through router."""
        router = get_router()

        text = "After analysis, I went with React instead of Vue for the frontend."
        result = router.route("decision", text)

        assert result.confidence > 0
        assert result.level_used == IntelligenceLevel.LOCAL

    def test_full_entity_extraction(self):
        """Should extract entities through router."""
        router = get_router()

        text = "Check the config.json file and run the setup() function."
        result = router.route("entity", text)

        assert result.confidence > 0
        entities = result.content.get("entities", [])
        assert any("config.json" in e.get("name", "") for e in entities)

    def test_full_pattern_extraction(self):
        """Should extract patterns through router."""
        router = get_router()

        text = "I always prefer using TypeScript over plain JavaScript."
        result = router.route("pattern", text)

        assert result.confidence > 0
        patterns = result.content.get("patterns", [])
        assert len(patterns) >= 1
