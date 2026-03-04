"""
Calculator package for spatial object selection.
"""

# Config
from .config import FIXED_GRID_POS

# Schemas
from .schemas import (
    PoseIn,
    RobotPoseIn,
    ObjectIn,
    CommandRequest,
    FrameFeatures,
    ObjectFeaturesOut,
    CommandResponse,
)

# Math utilities
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

# Feature computation
from .features import compute_frame_features

# LLM input builders
from .llm_input_builder import (
    build_llm_input,
    build_llm_input_coordinate,
    build_llm_input_coordinate_both,
)

# Backward compatibility aliases
CreateLLMInput_Coordinate = build_llm_input_coordinate
CreateLLMInput_Coordinate_Both = build_llm_input_coordinate_both

__all__ = [
    # Config
    "FIXED_GRID_POS",
    # Schemas
    "PoseIn",
    "RobotPoseIn",
    "ObjectIn",
    "CommandRequest",
    "FrameFeatures",
    "ObjectFeaturesOut",
    "CommandResponse",
    # Math
    "Vec3",
    "v3",
    "sub",
    "dot",
    "cross",
    "norm",
    "normalize",
    "project_xz",
    "make_frame_basis",
    "world_to_local",
    "safe_cos_theta",
    "stable_rank",
    "quadrant_side",
    # Features
    "compute_frame_features",
    # LLM input
    "build_llm_input",
    "build_llm_input_coordinate",
    "build_llm_input_coordinate_both",
    # Aliases
    "CreateLLMInput_Coordinate",
    "CreateLLMInput_Coordinate_Both",
]
