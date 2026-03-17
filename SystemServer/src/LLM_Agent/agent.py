import json
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import dotenv
from langchain.agents import create_agent
from pydantic import BaseModel, Field


dotenv.load_dotenv()

_PROMPT_DIR = Path(__file__).resolve().parent / "prompt"

# --- Language selection via env var (default: ja) ---
_PROMPT_LANG = os.getenv("PROMPT_LANG", "en").strip().lower()
_SUFFIX = "_en" if _PROMPT_LANG == "en" else ""


class Stage1FrameDecision(BaseModel):
    reference_frame: Literal["user_egocentric", "robot_centric"]
    confidence: float = Field(ge=0.0, le=1.0)
    spatial_keywords: List[str] = Field(default_factory=list)


class Stage2Selection(BaseModel):
    selected_object_id: Optional[str] = None
    reason: str = ""


class Stage3ConfirmationDecision(BaseModel):
    intent: Literal["accept", "reject", "refine", "unknown"]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ""
    refinement_utterance: str = ""
    confirmed_object_id: Optional[str] = None


class FrameDecision(BaseModel):
    reference_frame: Literal["user", "robot"]
    reasoning: str


class LLMDecision(BaseModel):
    reference_frame: Literal["user", "robot"]
    selections: List[Dict[str, Any]]


FRAME_CLASSIFIER_PROMPT = (_PROMPT_DIR / f"stage1_interpreter{_SUFFIX}.txt").read_text(encoding="utf-8")

OBJECT_SELECTOR_PROMPT = (_PROMPT_DIR / f"stage2_object_selector{_SUFFIX}.txt").read_text(encoding="utf-8")
CONFIRMATION_INTERPRETER_PROMPT = (_PROMPT_DIR / f"stage3_confirmation_interpreter{_SUFFIX}.txt").read_text(encoding="utf-8")


stage1_agent = create_agent(
    model=f"openai:{os.getenv('OPENAI_MODEL_LIGHT', 'gpt-4o-mini')}",
    tools=[],
    response_format=Stage1FrameDecision,
    system_prompt=FRAME_CLASSIFIER_PROMPT,
)


stage2_agent = create_agent(
    model=f"openai:{os.getenv('OPENAI_MODEL', 'gpt-5.2')}",
    tools=[],
    response_format=Stage2Selection,
    system_prompt=OBJECT_SELECTOR_PROMPT,
)


stage3_agent = create_agent(
    model=f"openai:{os.getenv('OPENAI_MODEL_LIGHT', 'gpt-5.2')}",
    tools=[],
    response_format=Stage3ConfirmationDecision,
    system_prompt=CONFIRMATION_INTERPRETER_PROMPT,
)


def _extract_structured(result: Any, model_cls: Any) -> Any:
    if isinstance(result, model_cls):
        return result
    structured = result.get("structured_response", None) if isinstance(result, dict) else None
    if isinstance(structured, model_cls):
        return structured
    if isinstance(structured, dict):
        return model_cls(**structured)
    raise RuntimeError(f"structured_response not found or invalid: {type(result)}")


def _dump_for_log(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump()
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except TypeError:
        return str(value)


def _print_stage_io(stage_name: str, stage_input: Any, stage_output: Any):
    print(f"======= {stage_name} 入力 =======")
    print(_dump_for_log(stage_input))
    print("=====================")
    print(f"======= {stage_name} 出力 =======")
    print(_dump_for_log(stage_output))
    print("=====================")


_STAGE2_EXCLUDED_KEYS = {
    "shape",
    "size",
    "relative_direction_hint",
    "cluster_id",
    "relative_position",
    "is_closest",
}


def _prepare_stage2_objects(spatial_context: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned = [
        {k: v for k, v in obj.items() if k not in _STAGE2_EXCLUDED_KEYS}
        for obj in spatial_context
    ]
    return sorted(cleaned, key=lambda obj: obj.get("distance", float("inf")))


def classify_reference_frame_v2(utterance: str) -> Stage1FrameDecision:
    stage_input = {"utterance": utterance}
    result = stage1_agent.invoke({"messages": [{"role": "user", "content": utterance}]})
    structured = _extract_structured(result, Stage1FrameDecision)
    _print_stage_io("Stage 1", stage_input, structured)
    return structured


def rank_objects_v2(utterance: str, reference_frame: str, spatial_context: List[Dict[str, Any]], refinement_context: str = "") -> Stage2Selection:
    stage2_objects = _prepare_stage2_objects(spatial_context)
    payload = {
        "utterance": utterance,
        "reference_frame": reference_frame,
        "objects": stage2_objects,
    }
    if refinement_context:
        payload["refinement_context"] = refinement_context

    result = stage2_agent.invoke({"messages": [{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]})
    structured = _extract_structured(result, Stage2Selection)
    if not structured.selected_object_id and stage2_objects:
        structured.selected_object_id = stage2_objects[0].get("object_id")
        if not structured.reason:
            structured.reason = "fallback to nearest after empty selected_object_id"
    _print_stage_io("Stage 2", payload, structured)
    return structured


def interpret_confirmation_v2(
    utterance: str,
    reference_frame: str,
    top_candidate_id: str,
    ranked_candidates: List[Dict[str, Any]],
    current_target_id: Optional[str] = None,
) -> Stage3ConfirmationDecision:
    payload = {
        "utterance": utterance,
        "reference_frame": reference_frame,
        "top_candidate_id": top_candidate_id,
        "current_target_id": current_target_id,
        "ranked_candidates": ranked_candidates,
    }
    result = stage3_agent.invoke({"messages": [{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]})
    structured = _extract_structured(result, Stage3ConfirmationDecision)
    _print_stage_io("Stage 3", payload, structured)
    return structured


def classify_reference_frame(utterance: str) -> FrameDecision:
    v2 = classify_reference_frame_v2(utterance)
    mapped = "user" if v2.reference_frame == "user_egocentric" else "robot"
    return FrameDecision(reference_frame=mapped, reasoning=f"confidence={v2.confidence:.2f}")


def decide_selection_rule(llm_input: dict) -> LLMDecision:
    objects = llm_input.get("objects", [])
    ranked = sorted(objects, key=lambda obj: obj.get("distance", 9999.0))
    selections = [{"target_id": obj.get("id")} for obj in ranked if obj.get("id")]
    frame = llm_input.get("input_frame", "user")
    if frame not in ("user", "robot"):
        frame = "user"
    return LLMDecision(reference_frame=frame, selections=selections)


def execute_decision(decision: Any, llm_input: dict) -> str:
    if hasattr(decision, "selections") and decision.selections:
        target_id = decision.selections[0].get("target_id")
        if target_id:
            return target_id
    objects = llm_input.get("objects", [])
    if not objects:
        raise RuntimeError("No objects available")
    return objects[0]["id"]


if __name__ == "__main__":
    print(classify_reference_frame_v2("右側の赤い箱を取って"))

