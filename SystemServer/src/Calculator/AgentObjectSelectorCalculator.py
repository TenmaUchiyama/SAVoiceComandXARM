# main.py
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple, Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


# =========================
# Config: Fixed grid (optional)
# =========================
# v0.1: objects が省略された場合にサーバ側固定定義を使うための例
# 座標系は HoloLens 側と整合している前提（同一ワールド系）
FIXED_GRID_POS: Dict[str, List[float]] = {
    # 例: 4x4 を 10cm 間隔で置く。row=手前->奥, col=左->右 のつもり
    # 必要に応じてあなたの環境に合わせて書き換えてOK
    "obj_00": [-0.15, 0.0, 0.15],
    "obj_01": [-0.05, 0.0, 0.15],
    "obj_02": [ 0.05, 0.0, 0.15],
    "obj_03": [ 0.15, 0.0, 0.15],
    "obj_10": [-0.15, 0.0, 0.05],
    "obj_11": [-0.05, 0.0, 0.05],
    "obj_12": [ 0.05, 0.0, 0.05],
    "obj_13": [ 0.15, 0.0, 0.05],
    "obj_20": [-0.15, 0.0, -0.05],
    "obj_21": [-0.05, 0.0, -0.05],
    "obj_22": [ 0.05, 0.0, -0.05],
    "obj_23": [ 0.15, 0.0, -0.05],
    "obj_30": [-0.15, 0.0, -0.15],
    "obj_31": [-0.05, 0.0, -0.15],
    "obj_32": [ 0.05, 0.0, -0.15],
    "obj_33": [ 0.15, 0.0, -0.15],
}


# =========================
# Pydantic Models
# =========================
class PoseIn(BaseModel):
    position: List[float] = Field(..., min_length=3, max_length=3)
    forward: List[float] = Field(..., min_length=3, max_length=3)
    fov_deg: Optional[float] = Field(None, description="user only; if None -> in_fov を計算しない")


class RobotPoseIn(BaseModel):
    position: List[float] = Field(..., min_length=3, max_length=3)
    forward: List[float] = Field(..., min_length=3, max_length=3)


class ObjectIn(BaseModel):
    id: str
    position: Optional[List[float]] = Field(None, min_length=3, max_length=3)


class CommandRequest(BaseModel):
    session_id: Optional[str] = None
    timestamp_ms: Optional[int] = None
    utterance: str
    user: PoseIn
    robot: Optional[RobotPoseIn] = None
    objects: Optional[List[ObjectIn]] = None  # v0.1: 固定グリッドなら id だけでもOK


# class FrameFeatures(BaseModel):
#     depth_rank: Optional[int] = None
#     right_rank: Optional[int] = None
#     front_rank: Optional[int] = None
#     in_fov: Optional[bool] = None
#     reachable: Optional[bool] = None
#     robot_side: Optional[Literal["front", "back", "left", "right"]] = None



#座標のやつ
class FrameFeatures(BaseModel):
    depth_rank: Optional[int]
    right_rank: Optional[int]
    front_rank: Optional[int]
    in_fov: Optional[bool]
    reachable: Optional[bool]
    robot_side: Optional[Literal["front", "back", "left", "right"]]



class ObjectFeaturesOut(BaseModel):
    id: str
    features: Dict[str, FrameFeatures]  # keys: "user", "robot"


class CommandResponse(BaseModel):
    status: Literal["ok", "error"]
    target_id: Optional[str] = None
    decision: Optional[dict] = None
    llm_input: Optional[dict] = None
    computed_features: Optional[List[ObjectFeaturesOut]] = None
    debug: Optional[dict] = None

# =========================
# Math Utils (pure python)
# =========================
Vec3 = Tuple[float, float, float]


def v3(x: List[float]) -> Vec3:
    return (float(x[0]), float(x[1]), float(x[2]))


def sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def project_xz(a: Vec3) -> Vec3:
    return (a[0], 0.0, a[2])


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


def safe_cos_theta(u: Vec3, forward_hat: Vec3, eps: float = 1e-8) -> float:
    nu = norm(u)
    if nu < eps:
        return 1.0  # origin と同位置なら正面扱い（好みで0.0でもOK）
    return dot(u, forward_hat) / nu


def stable_rank(values: Dict[str, float], direction: Literal["asc", "desc"]) -> Dict[str, int]:
    """
    v0.1: stable sort で 1-indexed rank を割当。
    tie は id で安定化（再現性のため）。
    """
    items = list(values.items())
    if direction == "asc":
        items_sorted = sorted(items, key=lambda kv: (kv[1], kv[0]))
    else:
        items_sorted = sorted(items, key=lambda kv: (-kv[1], kv[0]))
    return {obj_id: i + 1 for i, (obj_id, _) in enumerate(items_sorted)}


def quadrant_side(l: float, p: float) -> Literal["front", "back", "left", "right"]:
    """
    robot_side などの簡易カテゴリ。
    p=前後投影, l=左右投影
    """
    if abs(p) >= abs(l):
        return "front" if p >= 0 else "back"
    else:
        return "right" if l >= 0 else "left"


# =========================
# Feature Computation
# =========================
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

    # --- ★変更: forward を水平(XZ)に射影して正規化 ---
    f_proj = project_xz(forward)
    f_hat = normalize(f_proj)

    # forward がほぼ垂直などで潰れた場合の保険（任意だけどおすすめ）
    if norm(f_hat) < 1e-8:
        f_hat = normalize(forward)

    # Unity想定: right = cross(up, forward)
    r_hat = normalize(cross(up, f_hat))

    p_map: Dict[str, float] = {}
    l_map: Dict[str, float] = {}
    front_map: Dict[str, float] = {}
    in_fov_map: Dict[str, bool] = {}

    cos_th_threshold: Optional[float] = None
    if fov_deg is not None:
        cos_th_threshold = math.cos(math.radians(fov_deg) * 0.5)

    for oid, pos in objects_pos.items():
        # --- ★変更: u も水平(XZ)に射影 ---
        u3 = sub(pos, origin)
        u = project_xz(u3)

        # 水平前後・水平左右
        p = dot(u, f_hat)       # 前後（水平）
        l = dot(u, r_hat)       # 左右（水平）

        # 正面度（水平の角度）
        c = safe_cos_theta(u, f_hat)

        p_map[oid] = p
        l_map[oid] = l
        front_map[oid] = c

        if cos_th_threshold is None:
            in_fov_map[oid] = True
        else:
            in_fov_map[oid] = (c >= cos_th_threshold)

    # 近いほど手前: p が小さいほど近い（水平の前方距離）
    depth_rank = stable_rank(p_map, "asc")
    right_rank = stable_rank(l_map, "desc")
    front_rank = stable_rank(front_map, "desc")

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


def build_llm_input(utterance: str, per_object_features: Dict[str, Dict[str, FrameFeatures]]) -> Dict[str, Any]:
    """
    LLM入力JSONを「機械的に」生成する（判断を混ぜない）。
    """
    objects_payload = []
    for oid, frames in per_object_features.items():
        # FrameFeatures を dict に変換
        frames_dict: Dict[str, Any] = {}
        for frame_name, ff in frames.items():
            frames_dict[frame_name] = {
                # Noneは落としたいならここで除外してもOK
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




# -------------------------
# frame basis (Unity想定)
# - up は基本 (0,1,0)
# - right = cross(up, forward)
# - forward は正規化
# -------------------------
def make_frame_basis(forward: Vec3, up: Vec3 = (0.0, 1.0, 0.0)) -> Tuple[Vec3, Vec3, Vec3]:
    f = normalize(forward)
    r = normalize(cross(up, f))
    u = normalize(cross(f, r))  # 念のため直交化（微小誤差の保険）
    return r, u, f  # right, up, forward

def world_to_local(p_world: Vec3, origin_world: Vec3, basis_ruf: Tuple[Vec3, Vec3, Vec3]) -> Vec3:
    r, u, f = basis_ruf
    d = sub(p_world, origin_world)
    # local axes: x=right, y=up, z=forward
    return (dot(d, r), dot(d, u), dot(d, f))

# -------------------------
# LLM input builder (coordinates only)
# -------------------------
def CreateLLMInput_Coordinate(
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
    座標だけのLLM入力を作る。
    - objects_world: {object_id: (x,y,z)} すべてHoloLens/Unityの同一ワールド座標系で来る前提
    - frame: "user" or "robot"
    - user_origin/user_forward: req.user
    - robot_*: req.robot がある場合のみ
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
        objects_payload.append(
            {
                "id": oid,
                # ▼ ここを修正：座標を小数点2桁（センチ単位）に丸める
                "pos_local": [
                    round(p_local[0], 2), 
                    round(p_local[1], 2), 
                    round(p_local[2], 2)
                ],
                # ▼ ここを修正：距離も丸める
                "distance": round(math.sqrt(p_local[0]**2 + p_local[1]**2 + p_local[2]**2), 2),
                
                # ▼ ここを修正：角度は1桁あれば十分（むしろ整数でもいいくらい）
                "angle_from_forward_deg": round(math.degrees(math.acos(safe_cos_theta(sub(p_world, origin), basis[2]))), 1),
                
                # "pos_world": ... （デバッグ用は必要なら残す）
            }
        )

    return {
        "utterance": utterance,
        "input_frame": frame,  # この入力がどのフレームで表現されてるか
        "objects": objects_payload,
    }

def CreateLLMInput_Coordinate_Both(
    *,
    utterance: str,
    objects_world: Dict[str, Vec3],
    user_origin: Vec3,
    user_forward: Vec3,
    robot_origin: Optional[Vec3] = None,
    robot_forward: Optional[Vec3] = None,
) -> Dict[str, Any]:
    """
    user/robot両方のローカル座標を同時に渡したい場合。
    LLM側で「どっち基準で解釈するか」を選ばせたい時に便利。
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
            "pos_world": [p_world[0], p_world[1], p_world[2]],
            "pos_user": [p_user[0], p_user[1], p_user[2]],
        }
        if robot_basis is not None and robot_origin is not None:
            p_robot = world_to_local(p_world, robot_origin, robot_basis)
            item["pos_robot"] = [p_robot[0], p_robot[1], p_robot[2]]
        objects_payload.append(item)

    return {
        "utterance": utterance,
        "available_frames": ["user"] + (["robot"] if robot_basis is not None else []),
        "objects": objects_payload,
    }