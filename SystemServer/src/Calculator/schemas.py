"""
Pydantic schemas for Calculator module.
"""
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field


# =========================
# Input Schemas
# =========================
class PoseIn(BaseModel):
    """ユーザーのポーズ入力"""
    position: List[float] = Field(..., min_length=3, max_length=3)
    forward: List[float] = Field(..., min_length=3, max_length=3)
    fov_deg: Optional[float] = Field(None, description="user only; if None -> in_fov を計算しない")


class RobotPoseIn(BaseModel):
    """ロボットのポーズ入力"""
    position: List[float] = Field(..., min_length=3, max_length=3)
    forward: List[float] = Field(..., min_length=3, max_length=3)


class ObjectIn(BaseModel):
    """オブジェクト入力"""
    id: str
    position: Optional[List[float]] = Field(None, min_length=3, max_length=3)


class CommandRequest(BaseModel):
    """コマンドリクエスト"""
    session_id: Optional[str] = None
    timestamp_ms: Optional[int] = None
    utterance: str
    user: PoseIn
    robot: Optional[RobotPoseIn] = None
    objects: Optional[List[ObjectIn]] = None


# =========================
# Feature Schemas
# =========================
class FrameFeatures(BaseModel):
    """フレーム特徴量"""
    depth_rank: Optional[int] = None
    right_rank: Optional[int] = None
    front_rank: Optional[int] = None
    in_fov: Optional[bool] = None
    reachable: Optional[bool] = None
    robot_side: Optional[Literal["front", "back", "left", "right"]] = None


# =========================
# Output Schemas
# =========================
class ObjectFeaturesOut(BaseModel):
    """オブジェクト特徴量出力"""
    id: str
    features: Dict[str, FrameFeatures]  # keys: "user", "robot"


class CommandResponse(BaseModel):
    """コマンドレスポンス"""
    status: Literal["ok", "error"]
    target_id: Optional[str] = None
    reason: Optional[str] = None
    decision: Optional[dict] = None
    llm_input: Optional[dict] = None
    computed_features: Optional[List[ObjectFeaturesOut]] = None
    debug: Optional[dict] = None
