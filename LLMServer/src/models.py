# models.py
from typing import List, Dict, Any
from pydantic import BaseModel, Field

# --- Request Models (HoloLensからの入力) ---

class UserPose(BaseModel):
    forward: List[float] = Field(..., min_items=3, max_items=3, description="User forward vector (normalized)")
    up: List[float] = Field(..., min_items=3, max_items=3, description="User up vector (normalized)")

class ObjectRel(BaseModel):
    id: str
    rel_pos: List[float] = Field(..., min_items=3, max_items=3, description="Object position relative to user")

class CommandRequest(BaseModel):
    timestamp: int
    utterance: str
    user: UserPose
    objects: List[ObjectRel]

# --- Response/Internal Models (LLMへの出力) ---

class ObjectFeatures(BaseModel):
    id: str
    features: Dict[str, Any]

class LLMInputContext(BaseModel):
    task: str = "spatial_target_selection"
    utterance: str
    candidates: List[ObjectFeatures]