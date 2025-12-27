"""Mind v3 cognitive memory system.

Implements cognitively-inspired memory architecture:
- Working memory: Current session focus
- Episodic memory: Specific events with context
- Semantic memory: Generalized knowledge
- Procedural memory: Learned workflows
- Prospective memory: Future intentions/reminders

Processes:
- Encoding: Event -> Working memory
- Consolidation: Episodic -> Semantic
- Retrieval: Query -> Relevant memories
- Decay: Active -> Dormant
- Reinforcement: Use -> Strengthen
"""
from .working_memory import (
    WorkingMemory,
    WorkingMemoryConfig,
    MemoryItem,
    MemoryType,
)
from .consolidation import (
    MemoryConsolidator,
    ConsolidationConfig,
    ConsolidatedPattern,
)
from .decay import (
    DecayManager,
    DecayConfig,
    DecayCurve,
)
from .reinforcement import (
    ReinforcementManager,
    ReinforcementConfig,
    ReinforcementEvent,
    FeedbackType,
)

__all__ = [
    "WorkingMemory",
    "WorkingMemoryConfig",
    "MemoryItem",
    "MemoryType",
    "MemoryConsolidator",
    "ConsolidationConfig",
    "ConsolidatedPattern",
    "DecayManager",
    "DecayConfig",
    "DecayCurve",
    "ReinforcementManager",
    "ReinforcementConfig",
    "ReinforcementEvent",
    "FeedbackType",
]
