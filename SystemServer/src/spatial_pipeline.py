from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field


class Vec3Model(BaseModel):
    x: float
    y: float
    z: float


class UtteranceModel(BaseModel):
    text: str
    language: str = "ja"


class UserPoseModel(BaseModel):
    position: Vec3Model
    forward: Vec3Model
    up: Vec3Model = Field(default_factory=lambda: Vec3Model(x=0.0, y=1.0, z=0.0))


class RobotPoseModel(BaseModel):
    position: Vec3Model
    forward: Vec3Model


class ObjectModel(BaseModel):
    id: str
    label: str = "unknown"
    color: str = "unknown"
    position: Vec3Model


class SpatialReferenceRequest(BaseModel):
    type: Literal["spatial_reference_request"]
    request_id: str
    timestamp: Optional[str] = None
    utterance: UtteranceModel
    user_pose: UserPoseModel
    objects: List[ObjectModel] = Field(default_factory=list)
    robot_pose: Optional[RobotPoseModel] = None


class RefinementRequest(BaseModel):
    type: Literal["refinement_request"]
    request_id: str
    original_request_id: str
    utterance: UtteranceModel
    user_pose: Optional[UserPoseModel] = None
    previous_target: Optional[str] = None


class ConfirmationRequest(BaseModel):
    type: Literal["confirmation"]
    request_id: str
    confirmed_object_id: str
    action: str = "pick"


Vec3 = Tuple[float, float, float]


@dataclass
class SessionContext:
    request_id: str
    utterance: str
    reference_frame: Literal["user_egocentric", "robot_centric"]
    objects: List[ObjectModel]
    user_pose: UserPoseModel
    robot_pose: Optional[RobotPoseModel]
    ranked_candidates: List[Dict]


KEYWORD_MAP = {
    "right": ["右", "みぎ", "右側"],
    "left": ["左", "ひだり", "左側"],
    "front": ["手前", "前", "近い", "手元"],
    "back": ["奥", "後ろ", "遠い"],
    "closest": ["一番近", "最も近", "nearest"],
}


COLORS = ["red", "blue", "green", "yellow", "white", "black", "orange", "purple"]


def to_v3(value: Vec3Model) -> Vec3:
    return (value.x, value.y, value.z)


def sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(a: Vec3) -> float:
    return math.sqrt(dot(a, a))


def normalize(a: Vec3, eps: float = 1e-8) -> Vec3:
    n = norm(a)
    if n < eps:
        return (0.0, 0.0, 0.0)
    return (a[0] / n, a[1] / n, a[2] / n)


def rank_map(pairs: List[Tuple[str, float]], reverse: bool = False) -> Dict[str, int]:
    ordered = sorted(pairs, key=lambda x: x[1], reverse=reverse)
    return {object_id: idx + 1 for idx, (object_id, _) in enumerate(ordered)}


def relative_position_label(relative_x: float, relative_z: float) -> str:
    depth = "front" if relative_z >= 0 else "back"
    side = "right" if relative_x >= 0 else "left"
    return f"{depth}-{side}"


def compute_spatial_features(
    objects: List[ObjectModel],
    reference_frame: Literal["user_egocentric", "robot_centric"],
    user_pose: UserPoseModel,
    robot_pose: Optional[RobotPoseModel],
) -> List[Dict]:
    if reference_frame == "robot_centric":
        if robot_pose is None:
            raise ValueError("robot_centric requires robot_pose")
        origin = to_v3(robot_pose.position)
        forward = to_v3(robot_pose.forward)
        up = (0.0, 1.0, 0.0)
    else:
        origin = to_v3(user_pose.position)
        forward = to_v3(user_pose.forward)
        up = to_v3(user_pose.up)

    f_hat = normalize(forward)
    r_hat = normalize(cross(up, f_hat))
    u_hat = normalize(cross(f_hat, r_hat))

    rows: List[Dict] = []
    for item in objects:
        world_pos = to_v3(item.position)
        rel = sub(world_pos, origin)
        relative_x = dot(rel, r_hat)
        relative_y = dot(rel, u_hat)
        relative_z = dot(rel, f_hat)
        distance = math.sqrt(relative_x ** 2 + relative_y ** 2 + relative_z ** 2)
        azimuth = math.degrees(math.atan2(relative_x, relative_z))
        rows.append(
            {
                "object_id": item.id,
                "label": item.label,
                "color": item.color,
                "cluster_id": int(round(world_pos[2] / 0.10)),
                "relative_x": round(relative_x, 4),
                "relative_y": round(relative_y, 4),
                "relative_z": round(relative_z, 4),
                "distance": round(distance, 4),
                "azimuth_angle": round(azimuth, 2),
                "relative_position": relative_position_label(relative_x, relative_z),
            }
        )

    depth_ranks = rank_map([(row["object_id"], row["relative_z"]) for row in rows], reverse=False)
    lateral_ranks = rank_map([(row["object_id"], row["relative_x"]) for row in rows], reverse=False)
    min_distance = min((row["distance"] for row in rows), default=0.0)

    for row in rows:
        row["depth_rank"] = depth_ranks[row["object_id"]]
        row["lateral_rank"] = lateral_ranks[row["object_id"]]
        row["is_closest"] = abs(row["distance"] - min_distance) < 1e-6

    return rows


def _contains_any(text: str, words: List[str]) -> bool:
    return any(word in text for word in words)


def apply_fallback_ranking(
    utterance: str,
    features: List[Dict],
    previous_target: Optional[str] = None,
) -> List[Dict]:
    text = utterance.lower()
    candidates = features[:]

    for color in COLORS:
        if color in text:
            color_filtered = [row for row in candidates if row.get("color", "").lower() == color]
            if color_filtered:
                candidates = color_filtered

    if _contains_any(text, KEYWORD_MAP["right"]):
        candidates.sort(key=lambda row: row["relative_x"], reverse=True)
    elif _contains_any(text, KEYWORD_MAP["left"]):
        candidates.sort(key=lambda row: row["relative_x"])
    elif _contains_any(text, KEYWORD_MAP["back"]):
        candidates.sort(key=lambda row: row["relative_z"], reverse=True)
    elif _contains_any(text, KEYWORD_MAP["front"]) or _contains_any(text, KEYWORD_MAP["closest"]):
        candidates.sort(key=lambda row: row["distance"])
    else:
        candidates.sort(key=lambda row: row["distance"])

    if previous_target and _contains_any(text, KEYWORD_MAP["back"]):
        prev = next((row for row in features if row["object_id"] == previous_target), None)
        if prev is not None:
            deeper = [row for row in candidates if row["relative_z"] > prev["relative_z"]]
            if deeper:
                candidates = deeper

    total = max(1, len(candidates))
    ranked = []
    for idx, row in enumerate(candidates):
        score = max(0.01, 1.0 - (idx / total))
        ranked.append({"object_id": row["object_id"], "score": round(score, 3), "reason": "fallback"})
    return ranked
