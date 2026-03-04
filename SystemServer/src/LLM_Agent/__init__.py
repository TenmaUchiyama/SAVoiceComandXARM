"""
LLM Agent package for spatial object selection.

This package provides LLM-based decision making for selecting objects
based on user utterances and spatial features.
"""

# Schemas
from .schemas import (
    FilterSpec,
    OrderBySpec,
    SelectSpec,
    TieBreakerSpec,
    LLMDecision,
    LLMDecisionCoordinate,
    LLMDecisionFeature,
    FrameDecision,
)

# Core functions
from .core import (
    classify_reference_frame,
    decide_selection_rule,
    execute_decision,
)

# Agent factories (for advanced use)
from .agents import (
    get_selection_agent,
    get_frame_classifier_agent,
    create_selection_agent,
    create_frame_classifier_agent,
)

__all__ = [
    # Schemas
    "FilterSpec",
    "OrderBySpec",
    "SelectSpec",
    "TieBreakerSpec",
    "LLMDecision",
    "LLMDecisionCoordinate",
    "LLMDecisionFeature",
    "FrameDecision",
    # Core functions
    "classify_reference_frame",
    "decide_selection_rule",
    "execute_decision",
    # Agent factories
    "get_selection_agent",
    "get_frame_classifier_agent",
    "create_selection_agent",
    "create_frame_classifier_agent",
]
