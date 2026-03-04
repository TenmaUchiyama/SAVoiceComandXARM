# AgentObjectSelectorCalculator.py
"""
Backward compatibility module.

This module is deprecated. Import directly from the Calculator package:
    from Calculator import CommandRequest, compute_frame_features, ...

All functionality has been split into:
    - Calculator.config: FIXED_GRID_POS
    - Calculator.schemas: Pydantic models
    - Calculator.math_utils: Vector operations
    - Calculator.features: Feature computation
    - Calculator.llm_input_builder: LLM input construction
"""
from __future__ import annotations

# Re-export everything for backward compatibility
from .config import FIXED_GRID_POS
from .schemas import (
    PoseIn,
    RobotPoseIn,
    ObjectIn,
    CommandRequest,
    FrameFeatures,
    ObjectFeaturesOut,
    CommandResponse,
)
from .math_utils import (
    Vec3,
    v3,
    sub,
    dot,
    cross,
    norm,
    normalize,
    project_xz,
    make_frame_basis,
    world_to_local,
    safe_cos_theta,
    stable_rank,
    quadrant_side,
)
from .features import compute_frame_features
from .llm_input_builder import (
    build_llm_input,
    build_llm_input_coordinate as CreateLLMInput_Coordinate,
    build_llm_input_coordinate_both as CreateLLMInput_Coordinate_Both,
)