"""
Unified configuration system for Mind v3.

Provides a single entry point for all v3 configuration with:
- Sensible defaults
- File-based config support (.mind/v3.toml)
- Environment variable overrides
- Runtime config updates
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Import all component configs
from .memory.decay import DecayConfig
from .memory.consolidation import ConsolidationConfig
from .memory.working_memory import WorkingMemoryConfig
from .retrieval.embeddings import EmbeddingConfig
from .retrieval.search import SearchConfig
from .retrieval.query_expander import ExpanderConfig
from .capture.watcher import WatcherConfig
from .hooks.prompt_submit import PromptSubmitConfig
from .hooks.session_end import SessionEndConfig
from .autonomy.levels import AutonomyConfig
from .autonomy.confidence import ConfidenceConfig
from .api.client import ClaudeConfig


@dataclass
class V3Settings:
    """
    Unified v3 configuration.

    Groups all component configs with sensible defaults.
    Can be loaded from file or created programmatically.
    """

    # Core settings
    enabled: bool = True
    debug: bool = False

    # Memory settings
    decay: DecayConfig = field(default_factory=lambda: DecayConfig(half_life_hours=48))
    consolidation: ConsolidationConfig = field(default_factory=ConsolidationConfig)
    working_memory: WorkingMemoryConfig = field(default_factory=WorkingMemoryConfig)

    # Retrieval settings
    embeddings: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    query_expansion: ExpanderConfig = field(default_factory=ExpanderConfig)

    # Capture settings
    watcher: WatcherConfig = field(default_factory=WatcherConfig)

    # Hook settings
    prompt_submit: PromptSubmitConfig = field(default_factory=PromptSubmitConfig)
    session_end: SessionEndConfig = field(default_factory=SessionEndConfig)

    # Autonomy settings
    autonomy: AutonomyConfig = field(default_factory=AutonomyConfig)
    confidence: ConfidenceConfig = field(default_factory=ConfidenceConfig)

    # API settings
    api: ClaudeConfig = field(default_factory=ClaudeConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "V3Settings":
        """
        Create settings from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            V3Settings instance
        """
        settings = cls()

        # Core settings
        settings.enabled = data.get("enabled", settings.enabled)
        settings.debug = data.get("debug", settings.debug)

        # Memory settings
        if "decay" in data:
            settings.decay = DecayConfig(**data["decay"])
        if "consolidation" in data:
            settings.consolidation = ConsolidationConfig(**data["consolidation"])
        if "working_memory" in data:
            settings.working_memory = WorkingMemoryConfig(**data["working_memory"])

        # Retrieval settings
        if "embeddings" in data:
            settings.embeddings = EmbeddingConfig(**data["embeddings"])
        if "search" in data:
            settings.search = SearchConfig(**data["search"])
        if "query_expansion" in data:
            settings.query_expansion = ExpanderConfig(**data["query_expansion"])

        # Capture settings
        if "watcher" in data:
            settings.watcher = WatcherConfig(**data["watcher"])

        # Hook settings
        if "prompt_submit" in data:
            settings.prompt_submit = PromptSubmitConfig(**data["prompt_submit"])
        if "session_end" in data:
            settings.session_end = SessionEndConfig(**data["session_end"])

        # Autonomy settings
        if "autonomy" in data:
            settings.autonomy = AutonomyConfig(**data["autonomy"])
        if "confidence" in data:
            settings.confidence = ConfidenceConfig(**data["confidence"])

        # API settings
        if "api" in data:
            settings.api = ClaudeConfig(**data["api"])

        return settings

    @classmethod
    def from_file(cls, path: Path) -> "V3Settings":
        """
        Load settings from TOML file.

        Args:
            path: Path to config file

        Returns:
            V3Settings instance
        """
        if not path.exists():
            return cls()

        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        content = path.read_text(encoding="utf-8")
        data = tomllib.loads(content)
        return cls.from_dict(data)

    @classmethod
    def from_project(cls, project_path: Path) -> "V3Settings":
        """
        Load settings for a project.

        Config priority (highest to lowest):
        1. Environment variables
        2. .mind/v3.toml (detailed v3 config)
        3. .mind/config.json v3 section (unified config)
        4. Defaults

        Args:
            project_path: Project root directory

        Returns:
            V3Settings instance
        """
        # Try v3.toml first (detailed config)
        toml_file = project_path / ".mind" / "v3.toml"
        if toml_file.exists():
            settings = cls.from_file(toml_file)
        else:
            # Fall back to main config.json
            settings = cls()
            try:
                from ..config import get_v3_config
                v3_config = get_v3_config(project_path)
                settings.enabled = v3_config.get("enabled", settings.enabled)
                settings.debug = v3_config.get("debug", settings.debug)
            except ImportError:
                pass  # Main config not available, use defaults

        # Apply environment variable overrides
        settings._apply_env_overrides()

        return settings

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        if os.getenv("MIND_V3_DISABLED"):
            self.enabled = False
        if os.getenv("MIND_V3_DEBUG"):
            self.debug = True
        if os.getenv("MIND_V3_NO_GPU"):
            self.embeddings.use_gpu = False

        # API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            self.api.api_key = api_key
        level = os.getenv("MIND_INTELLIGENCE_LEVEL")
        if level:
            self.api.intelligence_level = level

    def to_dict(self) -> dict[str, Any]:
        """
        Convert settings to dictionary.

        Returns:
            Configuration dictionary
        """
        return {
            "enabled": self.enabled,
            "debug": self.debug,
            "decay": {
                "half_life_hours": self.decay.half_life_hours,
                "min_activation": self.decay.min_activation,
            },
            "consolidation": {
                "min_occurrences": self.consolidation.min_occurrences,
                "similarity_threshold": self.consolidation.similarity_threshold,
            },
            "embeddings": {
                "model_name": self.embeddings.model_name,
                "use_gpu": self.embeddings.use_gpu,
            },
            "search": {
                "top_k": self.search.top_k,
                "vector_weight": self.search.vector_weight,
                "keyword_weight": self.search.keyword_weight,
            },
            "watcher": {
                "enabled": self.watcher.enabled,
                "extract_decisions": self.watcher.extract_decisions,
                "extract_entities": self.watcher.extract_entities,
            },
        }


# Default singleton settings
_default_settings: V3Settings | None = None


def get_settings(project_path: Path | None = None) -> V3Settings:
    """
    Get v3 settings.

    Args:
        project_path: Optional project path for file-based config

    Returns:
        V3Settings instance
    """
    global _default_settings

    if project_path:
        return V3Settings.from_project(project_path)

    if _default_settings is None:
        _default_settings = V3Settings()

    return _default_settings


def reset_settings() -> None:
    """Reset to default settings."""
    global _default_settings
    _default_settings = None
