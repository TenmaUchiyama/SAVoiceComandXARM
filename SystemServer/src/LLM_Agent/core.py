"""
Core functions for LLM decision making.
"""
import json
import os
from typing import Dict, Any, Union

from .schemas import LLMDecisionCoordinate, LLMDecisionFeature, FrameDecision
from .agents import get_selection_agent, get_frame_classifier_agent, get_llm_input_mode


# =========================
# Frame Classification
# =========================
def classify_reference_frame(utterance: str) -> FrameDecision:
    """
    発話から参照フレーム（user/robot）を判定する。
    
    Args:
        utterance: ユーザーの発話テキスト
        
    Returns:
        FrameDecision: 参照フレームと判定理由
    """
    agent = get_frame_classifier_agent()
    result = agent.invoke({"messages": [{"role": "user", "content": utterance}]})
    
    if isinstance(result, FrameDecision):
        return result
    
    structured = result.get("structured_response", None)
    if structured is None:
        raise RuntimeError(f"structured_response not found. keys={list(result.keys())}")
    
    if isinstance(structured, dict):
        return FrameDecision(**structured)
    
    if isinstance(structured, FrameDecision):
        return structured
    
    raise RuntimeError(f"Unexpected structured_response type: {type(structured)}")


# =========================
# Selection Decision
# =========================
def decide_selection_rule(llm_input: Dict[str, Any]) -> Union[LLMDecisionCoordinate, LLMDecisionFeature]:
    """
    LLM入力(JSON)からオブジェクト選択ルールを決定する。
    
    Args:
        llm_input: サーバが生成した JSON（utterance + objects(features/coordinates)）
        
    Returns:
        LLMDecisionCoordinate or LLMDecisionFeature: モードに応じた選択結果
    """
    mode = get_llm_input_mode()
    DecisionClass = LLMDecisionCoordinate if mode == "coordinate" else LLMDecisionFeature
    
    agent = get_selection_agent()
    content = json.dumps(llm_input, ensure_ascii=False)
    result = agent.invoke({"messages": [{"role": "user", "content": content}]})

    if isinstance(result, (LLMDecisionCoordinate, LLMDecisionFeature)):
        return result

    structured = result.get("structured_response", None)
    if structured is None:
        raise RuntimeError(f"structured_response not found. keys={list(result.keys())}")

    if isinstance(structured, dict):
        return DecisionClass(**structured)

    if isinstance(structured, (LLMDecisionCoordinate, LLMDecisionFeature)):
        return structured

    raise RuntimeError(f"Unexpected structured_response type: {type(structured)}")


# =========================
# Decision Execution
# =========================
def execute_decision(decision: Union[LLMDecisionCoordinate, LLMDecisionFeature], llm_input: Dict[str, Any]) -> str:
    """
    決定結果を実行してオブジェクトIDを取得する。
    
    Args:
        decision: LLMの決定結果（CoordinateまたはFeature）
        llm_input: 元の入力データ
        
    Returns:
        str: 選択されたオブジェクトID
    """
    # 座標ベースモードの場合
    if isinstance(decision, LLMDecisionCoordinate):
        return decision.target_id
    
    # 特徴量ベースモードの場合
    frame = decision.reference_frame
    candidates = []
    for obj in llm_input["objects"]:
        oid = obj["id"]
        ff = obj["features"][frame]
        candidates.append((oid, ff))

    # フィルター適用
    for f in decision.filters:
        if f.type == "in_fov":
            candidates = [
                (o, ff) for o, ff in candidates
                if ff.get("in_fov") == f.value
            ]
        elif f.type == "reachable":
            candidates = [
                (o, ff) for o, ff in candidates
                if ff.get("reachable") == f.value
            ]
        elif f.type == "robot_side":
            candidates = [
                (o, ff) for o, ff in candidates
                if ff.get("robot_side") == f.value
            ]
        elif f.type == "front_top_k":
            candidates.sort(key=lambda x: x[1]["front_rank"])
            candidates = candidates[: f.k]
        else:
            raise ValueError(f"Unknown filter {f.type}")

        if not candidates:
            raise RuntimeError("No candidates after filter")

    # ソート
    key_fn = lambda x: x[1][decision.order_by.feature]
    candidates.sort(
        key=key_fn,
        reverse=(decision.order_by.direction == "desc")
    )

    # 選択
    idx = decision.select.rank - 1
    if idx >= len(candidates):
        raise RuntimeError("Rank out of range")

    selected = candidates[idx]

    # タイブレーカー
    if decision.tie_breaker:
        same = [c for c in candidates if key_fn(c) == key_fn(selected)]
        if len(same) > 1:
            tb = decision.tie_breaker
            same.sort(
                key=lambda x: x[1][tb.feature],
                reverse=(tb.direction == "desc")
            )
            selected = same[0]

    return selected[0]
