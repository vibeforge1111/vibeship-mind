"""Tests for entity extraction."""
import pytest

from mind.v3.intelligence.cascade import ModelTier, ExtractionResult
from mind.v3.intelligence.extractors.entity import (
    Entity,
    EntityType,
    LocalEntityExtractor,
)


class TestEntityType:
    """Test EntityType enum."""

    def test_entity_types_exist(self):
        """Should have expected entity types."""
        assert EntityType.FILE.value == "file"
        assert EntityType.FUNCTION.value == "function"
        assert EntityType.CLASS.value == "class"
        assert EntityType.MODULE.value == "module"
        assert EntityType.CONCEPT.value == "concept"
        assert EntityType.TOOL.value == "tool"


class TestEntity:
    """Test Entity dataclass."""

    def test_create_entity(self):
        """Should create entity with required fields."""
        entity = Entity(
            name="storage.py",
            entity_type=EntityType.FILE,
        )

        assert entity.name == "storage.py"
        assert entity.entity_type == EntityType.FILE
        assert entity.description == ""

    def test_entity_with_description(self):
        """Should support description."""
        entity = Entity(
            name="UserService",
            entity_type=EntityType.CLASS,
            description="Handles user operations",
        )

        assert entity.description == "Handles user operations"

    def test_entity_to_dict(self):
        """Should serialize to dictionary."""
        entity = Entity(
            name="auth.py",
            entity_type=EntityType.FILE,
            description="Authentication module",
        )

        d = entity.to_dict()

        assert d["name"] == "auth.py"
        assert d["type"] == "file"
        assert d["description"] == "Authentication module"


class TestLocalEntityExtractor:
    """Test LocalEntityExtractor."""

    def test_create_extractor(self):
        """Should create extractor."""
        extractor = LocalEntityExtractor()

        assert extractor is not None

    def test_extract_python_file(self):
        """Should extract .py file references."""
        extractor = LocalEntityExtractor()

        result = extractor.extract(
            "I'm reading the auth.py file to understand the login flow."
        )

        entities = result.content.get("entities", [])
        assert any(e["name"] == "auth.py" and e["type"] == "file" for e in entities)

    def test_extract_multiple_files(self):
        """Should extract multiple file references."""
        extractor = LocalEntityExtractor()

        result = extractor.extract(
            "Need to update storage.py and database.py for the new schema."
        )

        entities = result.content.get("entities", [])
        file_names = [e["name"] for e in entities if e["type"] == "file"]
        assert "storage.py" in file_names
        assert "database.py" in file_names

    def test_extract_various_file_types(self):
        """Should extract various file extensions."""
        extractor = LocalEntityExtractor()

        result = extractor.extract(
            "Check config.json, styles.css, and index.html for issues."
        )

        entities = result.content.get("entities", [])
        file_names = [e["name"] for e in entities if e["type"] == "file"]
        assert "config.json" in file_names
        assert "styles.css" in file_names
        assert "index.html" in file_names

    def test_extract_file_path(self):
        """Should extract file paths."""
        extractor = LocalEntityExtractor()

        result = extractor.extract(
            "The bug is in src/utils/helpers.py at line 42."
        )

        entities = result.content.get("entities", [])
        assert any("helpers.py" in e["name"] for e in entities if e["type"] == "file")

    def test_extract_function_def(self):
        """Should extract function references."""
        extractor = LocalEntityExtractor()

        result = extractor.extract(
            "The calculate_total() function needs optimization."
        )

        entities = result.content.get("entities", [])
        assert any(
            "calculate_total" in e["name"] and e["type"] == "function"
            for e in entities
        )

    def test_extract_class_reference(self):
        """Should extract class references."""
        extractor = LocalEntityExtractor()

        result = extractor.extract(
            "The UserService class handles authentication."
        )

        entities = result.content.get("entities", [])
        assert any(
            "UserService" in e["name"] and e["type"] == "class"
            for e in entities
        )

    def test_extract_tool_reference(self):
        """Should extract tool references."""
        extractor = LocalEntityExtractor()

        result = extractor.extract(
            "Using the Read tool to check the file contents."
        )

        entities = result.content.get("entities", [])
        assert any(e["name"] == "Read" and e["type"] == "tool" for e in entities)

    def test_extract_multiple_tools(self):
        """Should extract multiple tool references."""
        extractor = LocalEntityExtractor()

        result = extractor.extract(
            "First use Glob to find files, then Read to check contents."
        )

        entities = result.content.get("entities", [])
        tool_names = [e["name"] for e in entities if e["type"] == "tool"]
        assert "Glob" in tool_names
        assert "Read" in tool_names

    def test_no_entities_in_text(self):
        """Should return empty when no entities found."""
        extractor = LocalEntityExtractor()

        result = extractor.extract(
            "The weather is nice today."
        )

        entities = result.content.get("entities", [])
        assert len(entities) == 0

    def test_returns_extraction_result(self):
        """Should return proper ExtractionResult."""
        extractor = LocalEntityExtractor()

        result = extractor.extract("Check the auth.py file.")

        assert isinstance(result, ExtractionResult)
        assert result.tier_used == ModelTier.LOCAL
        assert result.model_name == "regex"

    def test_confidence_based_on_matches(self):
        """Confidence should increase with more entities."""
        extractor = LocalEntityExtractor()

        result_one = extractor.extract("Check auth.py")
        result_many = extractor.extract(
            "Check auth.py, storage.py, database.py and UserService class"
        )

        # More entities = higher confidence (more context)
        assert result_many.confidence >= result_one.confidence

    def test_deduplication(self):
        """Should deduplicate repeated entities."""
        extractor = LocalEntityExtractor()

        result = extractor.extract(
            "First auth.py handles login, then auth.py validates tokens."
        )

        entities = result.content.get("entities", [])
        auth_count = sum(1 for e in entities if e["name"] == "auth.py")
        assert auth_count == 1  # Should only appear once


class TestLocalEntityExtractorIntegration:
    """Integration tests with cascade."""

    def test_works_with_cascade(self):
        """Should work when registered with cascade."""
        from mind.v3.intelligence.cascade import ModelCascade, CascadeConfig

        config = CascadeConfig(enable_local=True)
        cascade = ModelCascade(config=config)
        extractor = LocalEntityExtractor()

        cascade.register_extractor(ModelTier.LOCAL, extractor)

        result = cascade.extract("Reading the storage.py file now.")

        assert result.tier_used == ModelTier.LOCAL
        assert len(result.content.get("entities", [])) >= 1
