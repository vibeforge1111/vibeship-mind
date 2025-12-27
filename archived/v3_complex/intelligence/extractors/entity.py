"""
Entity extraction for Mind v3.

Extracts entities from text:
- Files: .py, .js, .ts, .json, etc.
- Functions: function_name(), method_name()
- Classes: ClassName, PascalCase identifiers
- Modules: module_name, package references
- Tools: Claude Code tools (Read, Write, Bash, etc.)
- Concepts: Technical terms and concepts
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mind.v3.intelligence.cascade import ModelTier, ExtractionResult


class EntityType(str, Enum):
    """Types of entities that can be extracted."""

    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    TOOL = "tool"
    CONCEPT = "concept"


# Known Claude Code tools
CLAUDE_TOOLS = {
    "Read", "Write", "Edit", "Bash", "Glob", "Grep",
    "Task", "TodoWrite", "WebFetch", "WebSearch",
    "AskUserQuestion", "NotebookEdit",
}

# File extension patterns
FILE_EXTENSIONS = [
    "py", "js", "ts", "jsx", "tsx", "json", "yaml", "yml",
    "md", "txt", "html", "css", "scss", "sql", "sh", "bash",
    "go", "rs", "java", "cpp", "c", "h", "hpp", "rb", "php",
    "toml", "ini", "cfg", "conf", "env", "xml", "csv",
]


@dataclass
class Entity:
    """Represents an extracted entity."""

    name: str
    entity_type: EntityType
    description: str = ""
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.entity_type.value,
            "description": self.description,
            "properties": self.properties,
        }


class LocalEntityExtractor:
    """
    Extracts entities using regex patterns.

    This is Tier 1 (local) extraction - free and instant.
    For deeper understanding, escalate to API tiers.
    """

    def __init__(self):
        """Initialize with compiled patterns."""
        # File pattern: word.extension or path/to/file.extension
        ext_pattern = "|".join(FILE_EXTENSIONS)
        self.file_pattern = re.compile(
            rf"(?:[\w\-./\\]+/)?[\w\-]+\.({ext_pattern})\b",
            re.IGNORECASE,
        )

        # Function pattern: function_name() or method_name()
        self.function_pattern = re.compile(
            r"\b([a-z_][a-z0-9_]*)\s*\(\)",
            re.IGNORECASE,
        )

        # Class pattern: PascalCase followed by "class" or standalone
        self.class_pattern = re.compile(
            r"\b([A-Z][a-zA-Z0-9]+)(?:\s+class|\s+object|\s+instance)?\b"
        )

        # Tool pattern: Known Claude tools
        tool_names = "|".join(CLAUDE_TOOLS)
        self.tool_pattern = re.compile(
            rf"\b({tool_names})\s+tool\b|\bthe\s+({tool_names})\b|\busing\s+({tool_names})\b|\buse\s+({tool_names})\b|\bthen\s+({tool_names})\b",
            re.IGNORECASE,
        )

    def extract(self, text: str) -> ExtractionResult:
        """
        Extract entities from text.

        Args:
            text: Text to extract entities from

        Returns:
            ExtractionResult with entities and confidence
        """
        entities = []
        seen = set()  # For deduplication

        # Extract files
        for match in self.file_pattern.finditer(text):
            name = match.group(0)
            # Get just the filename if it's a path
            if "/" in name or "\\" in name:
                name = name.split("/")[-1].split("\\")[-1]
            if name not in seen:
                seen.add(name)
                entities.append(Entity(
                    name=name,
                    entity_type=EntityType.FILE,
                ))

        # Extract functions
        for match in self.function_pattern.finditer(text):
            name = match.group(1)
            # Filter out common words that might match
            if name.lower() not in {"if", "for", "while", "print", "return", "and", "or"}:
                key = f"func:{name}"
                if key not in seen:
                    seen.add(key)
                    entities.append(Entity(
                        name=name,
                        entity_type=EntityType.FUNCTION,
                    ))

        # Extract tools
        for match in self.tool_pattern.finditer(text):
            # Get whichever group matched (we have 5 groups now)
            name = match.group(1) or match.group(2) or match.group(3) or match.group(4) or match.group(5)
            if name:
                key = f"tool:{name}"
                if key not in seen:
                    seen.add(key)
                    entities.append(Entity(
                        name=name,
                        entity_type=EntityType.TOOL,
                    ))

        # Extract classes (PascalCase words that look like class names)
        for match in self.class_pattern.finditer(text):
            name = match.group(1)
            # Filter: must be followed by class-like context or be multi-word camelcase
            # Also filter out common words and tool names
            if (name not in CLAUDE_TOOLS and
                name.lower() not in {"the", "this", "that", "first", "second"} and
                len(name) > 3 and
                # Check if it's followed by class-related words
                re.search(rf"\b{name}\s+(class|object|instance|service|handler|manager|controller)",
                         text, re.IGNORECASE)):
                key = f"class:{name}"
                if key not in seen:
                    seen.add(key)
                    entities.append(Entity(
                        name=name,
                        entity_type=EntityType.CLASS,
                    ))

        # Calculate confidence
        if not entities:
            confidence = 0.0
        else:
            # Base confidence + bonus for multiple entities
            confidence = min(0.5 + (len(entities) * 0.1), 0.9)

        return ExtractionResult(
            content={
                "entities": [e.to_dict() for e in entities],
            },
            confidence=confidence,
            tier_used=ModelTier.LOCAL,
            model_name="regex",
            metadata={
                "entity_count": len(entities),
                "types_found": list(set(e.entity_type.value for e in entities)),
            },
        )
