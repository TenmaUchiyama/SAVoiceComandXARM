import json
import os
from pathlib import Path
from typing import Any, Dict, List, Literal

import dotenv
from langchain.agents import create_agent
from pydantic import BaseModel, Field


dotenv.load_dotenv()

_PROMPT_DIR = Path(__file__).resolve().parent / "prompt"

# --- Language selection via env var (default: ja) ---
_PROMPT_LANG = os.getenv("PROMPT_LANG", "ja").strip().lower()
_SUFFIX = "_en" if _PROMPT_LANG == "en" else ""


class Stage1FrameDecision(BaseModel):
    reference_frame: Literal["user_egocentric", "robot_centric"]
    confidence: float = Field(ge=0.0, le=1.0)
    spatial_keywords: List[str] = Field(default_factory=list)


class RankedObject(BaseModel):
    object_id: str
    score: float = Field(ge=0.0, le=1.0)
    reason: str = ""


class Stage2Selection(BaseModel):
    ranked_objects: List[RankedObject] = Field(default_factory=list)


class FrameDecision(BaseModel):
    reference_frame: Literal["user", "robot"]
    reasoning: str


class LLMDecision(BaseModel):
    reference_frame: Literal["user", "robot"]
    selections: List[Dict[str, Any]]


FRAME_CLASSIFIER_PROMPT = (_PROMPT_DIR / f"stage1_interpreter{_SUFFIX}.txt").read_text(encoding="utf-8")

OBJECT_SELECTOR_PROMPT = (_PROMPT_DIR / f"stage2_object_selector{_SUFFIX}.txt").read_text(encoding="utf-8")


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


def _extract_structured(result: Any, model_cls: Any) -> Any:
    if isinstance(result, model_cls):
        return result
    structured = result.get("structured_response", None) if isinstance(result, dict) else None
    if isinstance(structured, model_cls):
        return structured
    if isinstance(structured, dict):
        return model_cls(**structured)
    raise RuntimeError(f"structured_response not found or invalid: {type(result)}")


def classify_reference_frame_v2(utterance: str) -> Stage1FrameDecision:
    result = stage1_agent.invoke({"messages": [{"role": "user", "content": utterance}]})
    return _extract_structured(result, Stage1FrameDecision)


def rank_objects_v2(utterance: str, reference_frame: str, spatial_context: List[Dict[str, Any]], refinement_context: str = "") -> Stage2Selection:
    payload = {
        "utterance": utterance,
        "reference_frame": reference_frame,
        "objects": spatial_context,
    }
    if refinement_context:
        payload["refinement_context"] = refinement_context

    result = stage2_agent.invoke({"messages": [{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]})
    return _extract_structured(result, Stage2Selection)


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

