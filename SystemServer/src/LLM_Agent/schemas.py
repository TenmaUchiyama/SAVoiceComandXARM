"""
Pydantic schemas for LLM agent responses.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# =========================
# Filter/Order/Select Specs (for future use)
# =========================
class FilterSpec(BaseModel):
    """フィルタ仕様"""
    type: Literal["in_fov", "reachable", "robot_side", "front_top_k"] = Field(
        description="フィルタ種別"
    )
    value: Optional[Literal[True, False, "front", "back", "left", "right"]] = Field(
        default=None,
        description="in_fov/reachable は true/false、robot_side は front/back/left/right"
    )
    k: Optional[int] = Field(
        default=None,
        description="front_top_k 用のk（上位k個）"
    )


class OrderBySpec(BaseModel):
    """並べ替え仕様"""
    feature: Literal["depth_rank", "right_rank", "front_rank"] = Field(
        description="並べ替えに使う特徴量"
    )
    direction: Literal["asc", "desc"] = Field(
        description="昇順/降順"
    )


class SelectSpec(BaseModel):
    """選択仕様"""
    rank: int = Field(
        ge=1,
        description="1-indexed。並べ替え後の何番目を取るか"
    )


class TieBreakerSpec(BaseModel):
    """同順位解決仕様"""
    feature: Literal["depth_rank", "right_rank", "front_rank"] = Field(
        description="同順位のときに使う特徴量"
    )
    direction: Literal["asc", "desc"] = Field(
        description="昇順/降順"
    )


# =========================
# Main Decision Schemas
# =========================
class LLMDecisionCoordinate(BaseModel):
    """座標ベースの選択結果"""
    reasoning: str = Field(
        description="Brief explanation of the spatial groups found and how they were sorted"
    )
    target_id: str = Field(
        description="The exact ID string of the target object"
    )


class LLMDecisionFeature(BaseModel):
    """特徴量ベースの選択結果"""
    reference_frame: Literal["user", "robot"] = Field(
        description="参照フレーム（user/robot）"
    )
    filters: List[FilterSpec] = Field(
        default_factory=list,
        description="候補を絞るフィルタ（上から順に適用される想定）"
    )
    order_by: OrderBySpec = Field(
        description="並べ替えルール"
    )
    select: SelectSpec = Field(
        description="並べ替え後の選択"
    )
    tie_breaker: Optional[TieBreakerSpec] = Field(
        default=None,
        description="同順位解決（任意）"
    )


# Backward compatibility alias (defaults to coordinate mode)
LLMDecision = LLMDecisionCoordinate


class FrameDecision(BaseModel):
    """参照フレーム判定結果"""
    reference_frame: Literal["user", "robot"] = Field(
        description="参照フレーム（user/robot）"
    )
    reasoning: str = Field(
        description="判定理由の簡潔な説明"
    )
