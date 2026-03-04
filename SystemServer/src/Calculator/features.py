"""
Feature computation for spatial object selection.
"""
from __future__ import annotations
import math
from typing import Dict, Optional

from .schemas import FrameFeatures
from .math_utils import (
    Vec3,
    sub,
    dot,
    norm,
    normalize,
    project_xz,
    cross,
    safe_cos_theta,
    stable_rank,
    quadrant_side,
)


def compute_frame_features(
    frame_name: str,
    origin: Vec3,
    forward: Vec3,
    objects_pos: Dict[str, Vec3],
    fov_deg: Optional[float] = None,
    up: Vec3 = (0.0, 1.0, 0.0),
    compute_side: bool = False,
    reachable_default: Optional[bool] = None,
) -> Dict[str, FrameFeatures]:
    """
    Compute spatial features for all objects from a given frame (user/robot).
    
    Args:
        frame_name: Name of the frame (for logging)
        origin: Origin position of the frame
        forward: Forward direction vector
        objects_pos: Dict of object_id -> world position
        fov_deg: Field of view in degrees (None = don't compute in_fov)
        up: Up vector (default Y-up)
        compute_side: Whether to compute robot_side quadrant
        reachable_default: Default value for reachable flag
        
    Returns:
        Dict of object_id -> FrameFeatures
    """
    # Project forward to XZ plane and normalize
    f_proj = project_xz(forward)
    f_hat = normalize(f_proj)
    
    # Fallback if forward is nearly vertical
    if norm(f_hat) < 1e-8:
        f_hat = normalize(forward)
    
    # Unity convention: right = cross(up, forward)
    r_hat = normalize(cross(up, f_hat))
    
    # Compute projections for each object
    p_map: Dict[str, float] = {}  # Forward projection
    l_map: Dict[str, float] = {}  # Lateral projection
    front_map: Dict[str, float] = {}  # Frontal-ness (cos theta)
    in_fov_map: Dict[str, bool] = {}
    
    cos_th_threshold: Optional[float] = None
    if fov_deg is not None:
        cos_th_threshold = math.cos(math.radians(fov_deg) * 0.5)
    
    for oid, pos in objects_pos.items():
        # Project displacement to XZ plane
        u3 = sub(pos, origin)
        u = project_xz(u3)
        
        p = dot(u, f_hat)  # Forward/backward (horizontal)
        l = dot(u, r_hat)  # Left/right (horizontal)
        c = safe_cos_theta(u, f_hat)
        
        p_map[oid] = p
        l_map[oid] = l
        front_map[oid] = c
        
        if cos_th_threshold is None:
            in_fov_map[oid] = True
        else:
            in_fov_map[oid] = (c >= cos_th_threshold)
    
    # Compute ranks
    depth_rank = stable_rank(p_map, "asc")  # Closer = lower rank
    right_rank = stable_rank(l_map, "desc")  # More right = lower rank
    front_rank = stable_rank(front_map, "desc")  # More frontal = lower rank
    
    # Build output
    out: Dict[str, FrameFeatures] = {}
    for oid in objects_pos.keys():
        ff = FrameFeatures(
            depth_rank=depth_rank[oid],
            right_rank=right_rank[oid],
            front_rank=front_rank[oid],
            in_fov=(in_fov_map[oid] if cos_th_threshold is not None else None),
            reachable=reachable_default,
            robot_side=(quadrant_side(l_map[oid], p_map[oid]) if compute_side else None),
        )
        out[oid] = ff
    
    return out
