"""
LLM input construction utilities.
"""
from __future__ import annotations
import math
from typing import Any, Dict, List, Literal, Optional

from .schemas import FrameFeatures
from .math_utils import (
    Vec3,
    sub,
    make_frame_basis,
    world_to_local,
    safe_cos_theta,
)


def build_llm_input(
    utterance: str,
    per_object_features: Dict[str, Dict[str, FrameFeatures]],
) -> Dict[str, Any]:
    """
    Build LLM input JSON with feature-based representation.
    
    Args:
        utterance: User's utterance
        per_object_features: Dict of object_id -> {frame_name -> FrameFeatures}
        
    Returns:
        LLM input dictionary
    """
    objects_payload = []
    for oid, frames in per_object_features.items():
        frames_dict: Dict[str, Any] = {}
        for frame_name, ff in frames.items():
            frames_dict[frame_name] = {
                "depth_rank": ff.depth_rank,
                "right_rank": ff.right_rank,
                "front_rank": ff.front_rank,
                "in_fov": ff.in_fov,
                "reachable": ff.reachable,
                "robot_side": ff.robot_side,
            }
        objects_payload.append({"id": oid, "features": frames_dict})

    return {
        "utterance": utterance,
        "available_reference_frames": ["user", "robot"],
        "objects": objects_payload,
    }


def build_llm_input_coordinate(
    *,
    utterance: str,
    objects_world: Dict[str, Vec3],
    frame: Literal["user", "robot"],
    user_origin: Vec3,
    user_forward: Vec3,
    robot_origin: Optional[Vec3] = None,
    robot_forward: Optional[Vec3] = None,
) -> Dict[str, Any]:
    """
    Build LLM input with coordinate-based representation.
    
    Args:
        utterance: User's utterance
        objects_world: Dict of object_id -> world position
        frame: Reference frame to use ("user" or "robot")
        user_*: User pose
        robot_*: Robot pose (required if frame="robot")
        
    Returns:
        LLM input dictionary with local coordinates
    """
    if frame == "user":
        origin = user_origin
        basis = make_frame_basis(user_forward)
    else:
        if robot_origin is None or robot_forward is None:
            raise ValueError("frame='robot' requires robot_origin and robot_forward.")
        origin = robot_origin
        basis = make_frame_basis(robot_forward)

    objects_payload: List[Dict[str, Any]] = []
    for oid, p_world in objects_world.items():
        p_local = world_to_local(p_world, origin, basis)
        
        # Compute distance and angle
        distance = math.sqrt(p_local[0]**2 + p_local[1]**2 + p_local[2]**2)
        angle_deg = math.degrees(math.acos(safe_cos_theta(sub(p_world, origin), basis[2])))
        
        objects_payload.append({
            "id": oid,
            "pos_local": [
                round(p_local[0], 2),
                round(p_local[1], 2),
                round(p_local[2], 2),
            ],
            "distance": round(distance, 2),
            "angle_from_forward_deg": round(angle_deg, 1),
        })

    return {
        "utterance": utterance,
        "input_frame": frame,
        "objects": objects_payload,
    }


def build_llm_input_coordinate_both(
    *,
    utterance: str,
    objects_world: Dict[str, Vec3],
    user_origin: Vec3,
    user_forward: Vec3,
    robot_origin: Optional[Vec3] = None,
    robot_forward: Optional[Vec3] = None,
) -> Dict[str, Any]:
    """
    Build LLM input with both user and robot local coordinates.
    Useful when LLM should decide which frame to use.
    """
    user_basis = make_frame_basis(user_forward)

    robot_basis = None
    if robot_origin is not None and robot_forward is not None:
        robot_basis = make_frame_basis(robot_forward)

    objects_payload: List[Dict[str, Any]] = []
    for oid, p_world in objects_world.items():
        p_user = world_to_local(p_world, user_origin, user_basis)
        item: Dict[str, Any] = {
            "id": oid,
            "pos_world": list(p_world),
            "pos_user": list(p_user),
        }
        if robot_basis is not None and robot_origin is not None:
            p_robot = world_to_local(p_world, robot_origin, robot_basis)
            item["pos_robot"] = list(p_robot)
        objects_payload.append(item)

    return {
        "utterance": utterance,
        "available_frames": ["user"] + (["robot"] if robot_basis is not None else []),
        "objects": objects_payload,
    }
