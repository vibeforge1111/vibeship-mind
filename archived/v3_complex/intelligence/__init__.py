"""Mind v3 intelligence layer.

Model cascade for AI-powered extraction:
- Tier 1: Local models (free, instant)
- Tier 2: Fast API (Haiku, cheap)
- Tier 3: Powerful API (Sonnet/Opus, deep reasoning)
"""
from .cascade import (
    ModelTier,
    ModelCascade,
    CascadeConfig,
    ExtractionResult,
    Extractor,
)

__all__ = [
    "ModelTier",
    "ModelCascade",
    "CascadeConfig",
    "ExtractionResult",
    "Extractor",
]
