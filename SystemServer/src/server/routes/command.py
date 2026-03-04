"""
Command endpoints for spatial object selection.
"""
import json
import traceback
from typing import Dict, Optional, List

from fastapi import APIRouter, HTTPException

from Calculator import (
    CommandRequest,
    CommandResponse,
    FrameFeatures,
    ObjectFeaturesOut,
    Vec3,
    v3,
    FIXED_GRID_POS,
    compute_frame_features,
    build_llm_input,
    build_llm_input_coordinate,
)
from LLM_Agent import classify_reference_frame, decide_selection_rule, execute_decision
from server.config import robot, LLM_INPUT_MODE


router = APIRouter()


@router.post("/command", response_model=CommandResponse)
def command(req: CommandRequest):
    """
    Unified command endpoint.
    Behavior changes based on LLM_INPUT_MODE environment variable:
    - "coordinate": Uses coordinate-based selection (direct spatial reasoning)
    - "feature": Uses feature-based selection (rank-based filtering)
    """
    if LLM_INPUT_MODE == "coordinate":
        return _command_coordinate_mode(req)
    else:
        return _command_feature_mode(req)


@router.post("/command_cord", response_model=CommandResponse)
def command_cord(req: CommandRequest):
    """
    Legacy coordinate-based command endpoint.
    Always uses coordinate mode regardless of LLM_INPUT_MODE setting.
    """
    return _command_coordinate_mode(req)


def _command_coordinate_mode(req: CommandRequest) -> CommandResponse:
    """座標ベースモードの処理"""
    try:
        print("【Server】Command Request:", req.model_dump())

        # 1) Resolve objects (use fixed grid if not provided)
        objects_pos, objects_source = _resolve_objects(req)

        # 2) Extract poses
        user_origin = v3(req.user.position)
        user_forward = v3(req.user.forward)

        robot_origin: Optional[Vec3] = None
        robot_forward: Optional[Vec3] = None
        if req.robot is not None:
            robot_origin = v3(req.robot.position)
            robot_forward = v3(req.robot.forward)

        # 3) Classify reference frame
        input_frame = classify_reference_frame(req.utterance)
        print("【Server】Classified Reference Frame:", input_frame.model_dump())

        # 4) Build LLM input (coordinate-based)
        llm_input = build_llm_input_coordinate(
            utterance=req.utterance,
            objects_world=objects_pos,
            frame=input_frame.reference_frame,
            user_origin=user_origin,
            user_forward=user_forward,
            robot_origin=robot_origin,
            robot_forward=robot_forward,
        )
        print("【Server】LLM Input (coord only):", json.dumps(llm_input, indent=2, ensure_ascii=False))

        # 5) Get LLM decision
        print("【Server】Before decide_selection_rule", flush=True)
        try:
            decision = decide_selection_rule(llm_input)
            print("【Server】After decide_selection_rule", flush=True)
            print("【Server】LLM Decision:", json.dumps(decision.model_dump(), indent=2, ensure_ascii=False), flush=True)
        except Exception as e:
            print("【Server】decide_selection_rule ERROR:", repr(e), flush=True)
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

        selected_object_id = decision.target_id
        decision_out = {
            "reasoning": decision.reasoning,
            "target_id": decision.target_id,
        }

        # 6) Execute robot action
        print("【Server】Selected Object ID:", selected_object_id, flush=True)
        print("【Server】Decision Output:", decision_out, flush=True)

        if robot is not None:
            robot.pick_at_from_id(selected_object_id)

        return CommandResponse(
            status="ok",
            target_id=selected_object_id,
            decision=decision_out,
            llm_input=llm_input,
            computed_features=None,
            debug={
                "session_id": req.session_id,
                "objects_source": objects_source,
                "num_objects": len(objects_pos),
                "note": "coordinate-only input (pos_world + pos_user (+pos_robot if provided))",
                "mode": "coordinate",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        return CommandResponse(
            status="error",
            reason="internal_error",
            debug={"error": str(e)},
        )


def _command_feature_mode(req: CommandRequest) -> CommandResponse:
    """特徴量ベースモードの処理"""
    try:
        print("【Server】Command Request:", req.model_dump())

        # 1) Resolve objects
        objects_pos, objects_source = _resolve_objects(req)

        # 2) Compute user frame features
        print("【Server】Computing features for objects:", list(objects_pos.keys()))
        user_origin = v3(req.user.position)
        user_forward = v3(req.user.forward)

        user_feats = compute_frame_features(
            frame_name="user",
            origin=user_origin,
            forward=user_forward,
            objects_pos=objects_pos,
            fov_deg=req.user.fov_deg,
            compute_side=False,
            reachable_default=None,
        )

        # 3) Compute robot frame features (optional)
        print("【Server】Computing features for robot frame")
        robot_feats: Optional[Dict[str, FrameFeatures]] = None
        if req.robot is not None:
            robot_origin = v3(req.robot.position)
            robot_forward = v3(req.robot.forward)
            robot_feats = compute_frame_features(
                frame_name="robot",
                origin=robot_origin,
                forward=robot_forward,
                objects_pos=objects_pos,
                fov_deg=None,
                compute_side=True,
                reachable_default=True,
            )

        # 4) Merge per-object features
        print("【Server】Building per-object features")
        per_object: Dict[str, Dict[str, FrameFeatures]] = {}
        for oid in objects_pos.keys():
            per_object[oid] = {"user": user_feats[oid]}
            if robot_feats is not None:
                per_object[oid]["robot"] = robot_feats[oid]

        # 5) Build LLM input
        llm_input = build_llm_input(req.utterance, per_object)
        print("【Server】LLM Input:", llm_input)

        # 6) Get LLM decision
        decision = decide_selection_rule(llm_input)
        print("【Server】LLM Decision:", json.dumps(decision.model_dump(), indent=2, ensure_ascii=False))
        selected_object_id = execute_decision(decision, llm_input)
        print("【Server】Selected Object ID:", selected_object_id)

        # 7) Build response
        computed_features_out = [
            ObjectFeaturesOut(id=oid, features=frames)
            for oid, frames in per_object.items()
        ]

        return CommandResponse(
            status="ok",
            target_id=selected_object_id,
            decision=decision.model_dump(),
            llm_input=llm_input,
            computed_features=computed_features_out,
            debug={
                "session_id": req.session_id,
                "objects_source": objects_source,
                "num_objects": len(objects_pos),
                "mode": "feature",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        return CommandResponse(
            status="error",
            reason="internal_error",
            debug={"error": str(e)},
        )


def _resolve_objects(req: CommandRequest) -> tuple[Dict[str, Vec3], str]:
    """
    Resolve object positions from request or fixed grid.
    
    Returns:
        (objects_pos dict, source string)
    """
    if req.objects is None or len(req.objects) == 0:
        objects_pos: Dict[str, Vec3] = {
            oid: v3(pos) for oid, pos in FIXED_GRID_POS.items()
        }
        return objects_pos, "fixed_grid"
    
    objects_pos = {}
    missing = []
    for o in req.objects:
        if o.position is not None:
            objects_pos[o.id] = v3(o.position)
        else:
            if o.id in FIXED_GRID_POS:
                objects_pos[o.id] = v3(FIXED_GRID_POS[o.id])
            else:
                missing.append(o.id)

    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing object positions and not found in FIXED_GRID_POS: {missing}",
        )

    return objects_pos, "request_or_fixed_fallback"
