import dotenv 

dotenv.load_dotenv("../.env")  # .env ファイルから環境変数を読み込む



import asyncio
import json
import os
import time
import traceback
from typing import Dict, Optional, List, Any, Tuple
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from contextlib import asynccontextmanager
from Calculator.AgentObjectSelectorCalculator import *
from LLM_Agent.agent import (
    classify_reference_frame,
    classify_reference_frame_v2,
    decide_selection_rule,
    execute_decision,
    rank_objects_v2,
)
from manager import send_json_grid
from manager import manager, keyboard_monitor_loop
from utils import save_grid_to_file, save_robot_marker_config
from spatial_pipeline import (
    SessionContext,
    SpatialReferenceRequest,
    RefinementRequest,
    ConfirmationRequest,
    compute_spatial_features,
    apply_fallback_ranking,
)
# from models import CommandRequest, XarmPickRequest
# from SpatialCalculator import SpatialCalculator

try:
    from XARmOperator import XArmOperator
except ModuleNotFoundError as e:
    XArmOperator = None  # type: ignore[assignment]
    _XARM_IMPORT_ERROR = e
# --- 初期化 ---
def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off", ""}

XARM_ENABLE = _env_flag("XARM_ENABLE", default=True)
XARM_IP = os.getenv("XARM_IP", "192.168.1.199")

robot = XArmOperator(ip=XARM_IP) if (XArmOperator and XARM_ENABLE) else None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時
    if robot is not None:
        try:
            ok, msg = robot.connect()
            if not ok:
                print(f"【Server】xArm 接続失敗のためロボット機能を無効化して起動します: {msg}")
        except Exception as e:
            print(f"【Server】xArm 接続例外のためロボット機能を無効化して起動します: {e!r}")
    else:
        if not XARM_ENABLE:
            print("【Server】環境変数 XARM_ENABLE=0 のためロボット機能は無効です")
        else:
            print(f"【Server】xArm SDK が見つからないためロボット機能は無効です: {_XARM_IMPORT_ERROR}")
    asyncio.create_task(keyboard_monitor_loop())
    yield
    # 終了時
    if robot is not None:
        robot.disconnect()

app = FastAPI(title="Integrated Spatial Robot Controller", lifespan=lifespan)

SESSION_STORE: Dict[str, SessionContext] = {}
LAST_SPATIAL_DISCONNECT: Optional[dict] = None

LLM_TIMEOUT_SEC = float(os.getenv("LLM_TIMEOUT_SEC", "10.0"))
LLM_MAX_RETRIES = max(1, int(os.getenv("LLM_MAX_RETRIES", "3")))
SESSION_TIMEOUT_SEC = float(os.getenv("SESSION_TIMEOUT_SEC", "300.0"))


def _now_epoch() -> float:
    return time.time()


def _prune_expired_sessions() -> int:
    now = _now_epoch()
    expired = [
        request_id
        for request_id, ctx in SESSION_STORE.items()
        if now - ctx.last_updated_epoch > SESSION_TIMEOUT_SEC
    ]
    for request_id in expired:
        SESSION_STORE.pop(request_id, None)
    return len(expired)


def _store_session(context: SessionContext):
    context.last_updated_epoch = _now_epoch()
    SESSION_STORE[context.request_id] = context


def _get_session(request_id: str) -> Optional[SessionContext]:
    _prune_expired_sessions()
    context = SESSION_STORE.get(request_id)
    if context is None:
        return None
    if _now_epoch() - context.last_updated_epoch > SESSION_TIMEOUT_SEC:
        SESSION_STORE.pop(request_id, None)
        return None
    return context


def _parse_json_message(payload: str) -> dict:
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid_json: {exc}") from exc


def _decode_spatial_message(payload: str) -> Tuple[dict, bool]:
    root = _parse_json_message(payload)
    if not isinstance(root, dict):
        raise ValueError("E004: message must be object")

    if "eventId" not in root:
        return root, False

    event_id = str(root.get("eventId") or "").strip()
    inner = root.get("payload")
    if isinstance(inner, str):
        inner = inner.strip()
        message = _parse_json_message(inner) if inner else {}
    elif isinstance(inner, dict):
        message = inner
    else:
        message = {}

    if not isinstance(message, dict):
        raise ValueError("E004: payload must be object")
    if "type" not in message and event_id:
        message["type"] = event_id
    return message, True


def _normalize_server_error(response: dict) -> dict:
    if response.get("type") != "error":
        return response
    code = response.get("code") or response.get("error_code") or "E002"
    return {
        "type": "error",
        "request_id": response.get("request_id"),
        "code": code,
        "message": response.get("message", "unknown error"),
    }


def _extract_error_code(message: str, default: str = "E004") -> str:
    if not message:
        return default
    code = message.split(":", 1)[0].strip()
    if len(code) == 4 and code.startswith("E") and code[1:].isdigit():
        return code
    return default


def _as_unity_packet(response: dict) -> dict:
    normalized = _normalize_server_error(response)
    event_id = str(normalized.get("type") or "server_error")
    return {
        "eventId": event_id,
        "payload": json.dumps(normalized, ensure_ascii=False),
    }


def _debug_ws(direction: str, ws_path: str, payload: dict, note: str = ""):
    try:
        msg_type = payload.get("type")
        request_id = payload.get("request_id")
        status = payload.get("status")
        code = payload.get("code") or payload.get("error_code")
        objects = payload.get("objects")
        parts = [
            f"dir={direction}",
            f"path={ws_path}",
            f"type={msg_type}",
            f"request_id={request_id}",
        ]
        if status:
            parts.append(f"status={status}")
        if code:
            parts.append(f"code={code}")
        if isinstance(objects, list):
            parts.append(f"objects_count={len(objects)}")
        elif "objects" in payload:
            parts.append(f"objects_type={type(objects).__name__}")
        if note:
            parts.append(f"note={note}")
        print("【WS DEBUG】" + " | ".join(parts))
    except Exception as exc:
        print(f"【WS DEBUG】failed to format log: {exc}")


def _validate_coordinates(request: SpatialReferenceRequest):
    if not request.objects:
        raise ValueError(f"E003: objects is empty (request_id={request.request_id})")
    for item in request.objects:
        values = [item.position.x, item.position.y, item.position.z]
        if any(abs(v) > 100.0 for v in values):
            raise ValueError(f"E004: invalid coordinate range for {item.id}")


async def _run_with_timeout(coro, timeout_sec: float):
    return await asyncio.wait_for(coro, timeout=timeout_sec)


async def _run_with_retry(func, *args):
    last_error = None
    for _ in range(LLM_MAX_RETRIES):
        try:
            return await _run_with_timeout(asyncio.to_thread(func, *args), timeout_sec=LLM_TIMEOUT_SEC)
        except asyncio.TimeoutError as exc:
            last_error = exc
            continue
    raise asyncio.TimeoutError(f"E001: llm timeout after {LLM_MAX_RETRIES} retries") from last_error


async def _run_stage1(utterance: str):
    return await _run_with_retry(classify_reference_frame_v2, utterance)


async def _run_stage2(utterance: str, reference_frame: str, features: List[Dict], refinement_context: str = ""):
    return await _run_with_retry(rank_objects_v2, utterance, reference_frame, features, refinement_context)


def _build_result_message(request_id: str, reference_frame: str, ranked_candidates: List[Dict], reasoning: str) -> dict:
    top = ranked_candidates[0] if ranked_candidates else {"object_id": None, "score": 0.0}
    candidate_rows = [
        {"object_id": row.get("object_id"), "score": row.get("score", 0.0), "reasoning": row.get("reason", "")} for row in ranked_candidates
    ]
    return {
        "type": "spatial_reference_result",
        "request_id": request_id,
        "candidates": candidate_rows,
        "top_candidate_id": top.get("object_id"),
        "confidence": top.get("score", 0.0),
        # backward-compatible fields
        "selected_object_id": top.get("object_id"),
        "target": {
            "object_id": top.get("object_id"),
            "confidence": top.get("score", 0.0),
            "reference_frame": reference_frame,
        },
        "ranked_candidates": candidate_rows,
        "reasoning": reasoning,
    }


def _build_robot_command_message(
    request_id: str,
    action: str,
    target_object_id: str,
    target_position: Dict[str, float],
    status: str,
    message: str = "",
) -> dict:
    return {
        "type": "robot_command",
        "request_id": request_id,
        "action": action,
        "target_object_id": target_object_id,
        "target_position": target_position,
        "status": status,
        "message": message,
    }


async def _route_spatial_message(message: dict) -> Any:
    try:
        msg_type = message.get("type")
        print(f"【Server】_route_spatial_message: type={msg_type}, request_id={message.get('request_id')}")
        if msg_type == "spatial_reference_request":
            req = SpatialReferenceRequest(**message)
            return await _process_spatial_reference_request(req)
        if msg_type == "refinement_request":
            req = RefinementRequest(**message)
            return await _process_refinement_request(req)
        if msg_type == "confirmation":
            req = ConfirmationRequest(**message)
            return await _process_confirmation_request(req)
        print(f"【Server】unsupported message type: {msg_type}")
        return {
            "type": "error",
            "request_id": message.get("request_id"),
            "code": "E004",
            "message": f"unsupported message type: {msg_type}",
        }
    except ValueError as exc:
        print(f"【Server】Spatial ValueError: {exc}")
        traceback.print_exc()
        msg = str(exc)
        error_code = _extract_error_code(msg, default="E004")
        error_message = msg.split(":", 1)[1].strip() if ":" in msg else msg
        return {
            "type": "error",
            "request_id": message.get("request_id"),
            "code": error_code,
            "message": error_message,
        }
    except asyncio.TimeoutError as exc:
        print(f"【Server】Spatial TimeoutError: {exc}")
        return {
            "type": "error",
            "request_id": message.get("request_id"),
            "code": "E001",
            "message": str(exc),
        }
    except Exception as exc:
        print(f"【Server】Spatial Exception ({type(exc).__name__}): {exc}")
        traceback.print_exc()
        return {
            "type": "error",
            "request_id": message.get("request_id"),
            "code": "E002",
            "message": str(exc),
        }


async def _process_spatial_reference_request(request_data: SpatialReferenceRequest) -> dict:
    _prune_expired_sessions()
    _validate_coordinates(request_data)
    frame_decision = await _run_stage1(request_data.utterance.text)
    reference_frame = frame_decision.reference_frame

    features = compute_spatial_features(
        objects=request_data.objects,
        reference_frame=reference_frame,
        user_pose=request_data.user_pose,
        robot_pose=request_data.robot_pose,
    )

    try:
        stage2 = await _run_stage2(request_data.utterance.text, reference_frame, features)
        ranked_candidates = [
            {"object_id": row.object_id, "score": row.score, "reason": row.reason}
            for row in stage2.ranked_objects
        ]
    except asyncio.TimeoutError:
        raise
    except Exception:
        ranked_candidates = apply_fallback_ranking(request_data.utterance.text, features)

    _store_session(SessionContext(
        request_id=request_data.request_id,
        utterance=request_data.utterance.text,
        reference_frame=reference_frame,
        objects=request_data.objects,
        user_pose=request_data.user_pose,
        robot_pose=request_data.robot_pose,
        ranked_candidates=ranked_candidates,
        last_updated_epoch=_now_epoch(),
    ))

    return _build_result_message(
        request_id=request_data.request_id,
        reference_frame=reference_frame,
        ranked_candidates=ranked_candidates,
        reasoning="LLM selection" if ranked_candidates and ranked_candidates[0].get("reason") != "fallback" else "fallback selection",
    )


async def _process_refinement_request(request_data: RefinementRequest) -> dict:
    previous = _get_session(request_data.original_request_id)
    if previous is None:
        return {
            "type": "error",
            "request_id": request_data.request_id,
            "code": "E006",
            "message": "session expired or unknown original_request_id",
        }

    user_pose = request_data.user_pose or previous.user_pose
    reference_frame = previous.reference_frame

    features = compute_spatial_features(
        objects=previous.objects,
        reference_frame=reference_frame,
        user_pose=user_pose,
        robot_pose=previous.robot_pose,
    )

    refinement_context = f"前回ターゲット: {request_data.previous_target or previous.ranked_candidates[0].get('object_id') if previous.ranked_candidates else 'unknown'}"
    try:
        stage2 = await _run_stage2(request_data.utterance.text, reference_frame, features, refinement_context)
        ranked_candidates = [
            {"object_id": row.object_id, "score": row.score, "reason": row.reason}
            for row in stage2.ranked_objects
        ]
    except asyncio.TimeoutError:
        raise
    except Exception:
        ranked_candidates = apply_fallback_ranking(request_data.utterance.text, features, request_data.previous_target)

    _store_session(SessionContext(
        request_id=request_data.request_id,
        utterance=request_data.utterance.text,
        reference_frame=reference_frame,
        objects=previous.objects,
        user_pose=user_pose,
        robot_pose=previous.robot_pose,
        ranked_candidates=ranked_candidates,
        last_updated_epoch=_now_epoch(),
    ))

    return _build_result_message(
        request_id=request_data.request_id,
        reference_frame=reference_frame,
        ranked_candidates=ranked_candidates,
        reasoning="refined selection",
    )


async def _process_confirmation_request(request_data: ConfirmationRequest) -> List[dict]:
    session_request_id = request_data.original_request_id or request_data.request_id
    session = _get_session(session_request_id)
    if session is None:
        return [{
            "type": "error",
            "request_id": request_data.request_id,
            "code": "E006",
            "message": "session expired or unknown request_id/original_request_id",
        }]

    target = next((obj for obj in session.objects if obj.id == request_data.confirmed_object_id), None)
    if target is None:
        return [{
            "type": "error",
            "request_id": request_data.request_id,
            "code": "E004",
            "message": "invalid confirmed_object_id",
        }]

    target_position = {
        "x": target.position.x,
        "y": target.position.y,
        "z": target.position.z,
    }

    started = _build_robot_command_message(
        request_id=request_data.request_id,
        action=request_data.action,
        target_object_id=target.id,
        target_position=target_position,
        status="started",
        message="robot action started",
    )

    final_status = "completed"
    final_message = "robot action completed"

    if robot is not None and request_data.action == "pick":
        try:
            ok, msg = robot.pick_at(target.position.x, target.position.y)
            if not ok:
                final_status = "failed"
                final_message = msg
        except Exception as exc:
            final_status = "failed"
            final_message = str(exc)
    elif robot is None and request_data.action == "pick":
        final_status = "failed"
        final_message = "robot is not connected"

    final = _build_robot_command_message(
        request_id=request_data.request_id,
        action=request_data.action,
        target_object_id=target.id,
        target_position=target_position,
        status=final_status,
        message=final_message,
    )

    return [started, final]




@app.post("/command_cord", response_model=CommandResponse)
def command_cord(req: CommandRequest):
    try:
        print("【Server】Command Request:", req.model_dump())

        # -------------------------
        # 1) objects を解決（positionが無ければ固定グリッドから）
        # -------------------------
        if req.objects is None or len(req.objects) == 0:
            objects_pos: Dict[str, Vec3] = {oid: v3(pos) for oid, pos in FIXED_GRID_POS.items()}
            objects_source = "fixed_grid"
        else:
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

            objects_source = "request_or_fixed_fallback"

        # -------------------------
        # 2) pose を取り出す（user は必須 / robot は任意）
        # -------------------------
        user_origin = v3(req.user.position)
        user_forward = v3(req.user.forward)

        robot_origin: Optional[Vec3] = None
        robot_forward: Optional[Vec3] = None
        if req.robot is not None:
            robot_origin = v3(req.robot.position)
            robot_forward = v3(req.robot.forward)



        input_frame = classify_reference_frame(req.utterance)
        print("【Server】Classified Reference Frame:", input_frame.model_dump())
        # -------------------------
        # 3) LLM入力（座標だけ）を作成
        #    - user/robot 両方のローカル座標を同時に入れる
        #    - LLM側で frame を選ばせる設計
        # -------------------------
        llm_input = CreateLLMInput_Coordinate(
            utterance=req.utterance,
            objects_world=objects_pos,
            frame=input_frame.reference_frame,  # "user" or "robot" を LLM 側で選ばせる設計
            user_origin=user_origin,
            user_forward=user_forward,
            robot_origin=robot_origin,
            robot_forward=robot_forward,
        )

        #とりあえず見やすい形にして出力
        print("【Server】LLM Input (coord only):", json.dumps(llm_input, indent=2, ensure_ascii=False))
        # # -------------------------
        # # 4) LLM decision -> executor
        # # -------------------------
        
        print("【Server】Before decide_selection_rule", flush=True)
        try:
            decision = decide_selection_rule(llm_input)
            print("【Server】After decide_selection_rule", flush=True)
            print("【Server】LLM Decision:", json.dumps(decision.model_dump(), indent=2, ensure_ascii=False), flush=True)
        except Exception as e:
            print("【Server】decide_selection_rule ERROR:", repr(e), flush=True)
            traceback.print_exc()
            # ここで一旦HTTP 500にして落とすとデバッグしやすい（任意）
            raise HTTPException(status_code=500, detail=str(e))

        # # decision が pydantic の場合
        # try:
        #     print("【Server】LLM Decision:", decision.model_dump())
        #     decision_out = decision.model_dump()
        # except Exception:
        #     print("【Server】LLM Decision(raw):", decision)
        #     decision_out = decision

        # selected_object_id = execute_decision(decision, llm_input)
        # print("【Server】Selected Object ID:", selected_object_id)

        selected_object_id = decision.selections[0].get("target_id")
        decision_out = {
            "reference_frame": decision.reference_frame,
            "selections": decision.selections,
        }
        # -------------------------
        # 5) response
        #    - computed_features はもう要らないなら返さない（None）
        # -------------------------

        print("【Server】Selected Object ID:", selected_object_id, flush=True)
        print("【Server】Decision Output:", decision_out, flush=True)
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

@app.post("/command", response_model=CommandResponse)
def command(req: CommandRequest):
    try:
        print("【Server】Command Request:", req.model_dump())
        # -------------------------
        # 1) objects を解決（positionが無ければ固定グリッドから）
        # -------------------------
        if req.objects is None or len(req.objects) == 0:
            # 固定グリッドを全投入（必要なら obj_00..33 のみなどに制限してOK）
            objects_pos: Dict[str, Vec3] = {oid: v3(pos) for oid, pos in FIXED_GRID_POS.items()}
            objects_source = "fixed_grid"
        else:
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
            objects_source = "request_or_fixed_fallback"

        # -------------------------
        # 2) user frame features
        # -------------------------
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

        # -------------------------
        # 3) robot frame features（任意）
        # -------------------------
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
                compute_side=True,          # robot_side を付ける
                reachable_default=True,     # v0.1は固定 true
            )

        # -------------------------
        # 4) per-object features を統合
        # -------------------------
        print("【Server】Building per-object features")
        per_object: Dict[str, Dict[str, FrameFeatures]] = {}
        for oid in objects_pos.keys():
            per_object[oid] = {"user": user_feats[oid]}
            if robot_feats is not None:
                per_object[oid]["robot"] = robot_feats[oid]
            else:
                # robot が無い場合も “available_reference_frames” は入れてよいが
                # features["robot"] を欠落させたくない場合は空を入れる
                per_object[oid]["robot"] = FrameFeatures()

        # -------------------------
        # 5) LLM入力 JSON を作成
        # -------------------------
        llm_input = build_llm_input(req.utterance, per_object)
        print("【Server】LLM Input:", llm_input)

        decision = decide_selection_rule(llm_input) 
        print("【Server】LLM Decision:", json.dumps(decision.model_dump(), indent=2, ensure_ascii=False))
        selected_object_id = execute_decision(decision, llm_input)
        print("【Server】Selected Object ID:", selected_object_id)


        computed_features_out: List[ObjectFeaturesOut] = []
        for oid, frames in per_object.items():
            computed_features_out.append(
                ObjectFeaturesOut(
                    id=oid,
                    features=frames,  # pydanticが FrameFeatures を解釈
                )
            )

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

# --- Unity連携 (WebSocket & JSON保存) ---
@app.post("/save_grid_config")
async def save_grid_api(payload: dict):
    filename = save_grid_to_file(payload)
    return {"status": "ok", "filename": filename}

@app.get("/calibration")
async def calibration_api():
    await send_json_grid()
    return {"status": "ok"}

@app.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    print("【Server】Unity接続完了")
    latest_spatial_request_id: Optional[str] = None
    try:
        while True:
            # Unityからのメッセージ受信
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Unity側が一定間隔で送信しない場合でも、サーバー側からは切断しない。
                # KeepAlive を送って接続維持を試みる。
                await websocket.send_text(json.dumps({"eventId": "KeepAlive", "payload": "{}"}))
                continue

            message = _parse_json_message(data)
            
            event_id = message.get("eventId")

            if event_id == "SaveGridConfig":
                grid_data = json.loads(message.get("payload", "{}"))
                filename = save_grid_to_file(grid_data)
                
                # 結果をUnityに返す
                response = {
                    "eventId": "SaveGridConfigResult",
                    "payload": json.dumps({"status": "success", "filename": filename})
                }
                await websocket.send_text(json.dumps(response))
            
            elif event_id == "SaveRobotMarkerConfig":
                marker_data = json.loads(message.get("payload", "{}"))
                filename = save_robot_marker_config(marker_data)
                
                response = {
                    "eventId": "SaveRobotMarkerConfigResult",
                    "payload": json.dumps({"status": "success", "filename": filename})
                }
                await websocket.send_text(json.dumps(response))
                print(f"【Server】ロボットマーカー設定を保存しました: {filename}")
            
            elif event_id == "XarmPick":
                payload = json.loads(message.get("payload", "{}"))
                x = payload.get("x")
                y = payload.get("y")

                if robot is not None:
                    try:
                        ok, msg = robot.pick_at(x, y)
                        result_payload = {"success": ok, "message": msg}
                    except Exception as exc:
                        result_payload = {"success": False, "message": str(exc)}
                else:
                    result_payload = {"success": False, "message": "robot is not connected"}

                await websocket.send_text(json.dumps({
                    "eventId": "XarmPickResult",
                    "payload": json.dumps(result_payload)
                }))

            elif event_id in {"spatial_reference_request", "refinement_request", "confirmation"}:
                payload = message.get("payload", "{}")
                if isinstance(payload, str):
                    spatial_message = _parse_json_message(payload) if payload.strip() else {}
                elif isinstance(payload, dict):
                    spatial_message = payload
                else:
                    spatial_message = {}

                if "type" not in spatial_message:
                    spatial_message["type"] = message.get("eventId")

                if spatial_message.get("type") in {"spatial_reference_request", "refinement_request"}:
                    request_id = spatial_message.get("request_id")
                    if isinstance(request_id, str) and request_id:
                        latest_spatial_request_id = request_id

                if spatial_message.get("type") == "confirmation":
                    if not spatial_message.get("original_request_id") and latest_spatial_request_id:
                        spatial_message["original_request_id"] = latest_spatial_request_id
                        _debug_ws("server", "/", spatial_message, note="filled original_request_id from latest session")

                _debug_ws("unity->server", "/", spatial_message, note=f"eventId={event_id}")
                response = await _route_spatial_message(spatial_message)

                response_list = response if isinstance(response, list) else [response]
                for item in response_list:
                    packet = _as_unity_packet(item)
                    _debug_ws("server->unity", "/", item, note=f"eventId={packet.get('eventId')}")
                    await websocket.send_text(json.dumps(packet, ensure_ascii=False))

            else:
                print(f"【Server】WS unhandled eventId: {event_id}")
                
    except WebSocketDisconnect as e:
        manager.disconnect(websocket)
        print(f"【Server】Unity切断 code={getattr(e, 'code', None)}")
    except Exception as e:
        print(f"【Server】エラー: {e!r}")
        manager.disconnect(websocket)


@app.websocket("/spatial")
async def spatial_ws_endpoint(websocket: WebSocket):
    global LAST_SPATIAL_DISCONNECT
    await websocket.accept()
    latest_spatial_request_id: Optional[str] = None
    try:
        while True:
            _prune_expired_sessions()
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=SESSION_TIMEOUT_SEC)
            except asyncio.TimeoutError:
                timeout_error = {
                    "type": "error",
                    "code": "E006",
                    "message": "session timeout",
                }
                _debug_ws("server->unity", "/spatial", timeout_error, note="closing socket due to inactivity")
                await websocket.send_text(json.dumps(timeout_error, ensure_ascii=False))
                await websocket.close(code=1001, reason="session timeout")
                return

            message, needs_packet = _decode_spatial_message(raw)

            if message.get("type") in {"spatial_reference_request", "refinement_request"}:
                request_id = message.get("request_id")
                if isinstance(request_id, str) and request_id:
                    latest_spatial_request_id = request_id

            if message.get("type") == "confirmation":
                if not message.get("original_request_id") and latest_spatial_request_id:
                    message["original_request_id"] = latest_spatial_request_id
                    _debug_ws("server", "/spatial", message, note="filled original_request_id from latest session")

            _debug_ws("unity->server", "/spatial", message)
            response = await _route_spatial_message(message)

            LAST_SPATIAL_DISCONNECT = None
            response_list = response if isinstance(response, list) else [response]
            for item in response_list:
                _debug_ws("server->unity", "/spatial", item)
                if needs_packet:
                    await websocket.send_text(json.dumps(_as_unity_packet(item), ensure_ascii=False))
                else:
                    await websocket.send_text(json.dumps(item, ensure_ascii=False))
    except WebSocketDisconnect as exc:
        LAST_SPATIAL_DISCONNECT = {
            "type": "error",
            "code": "E005",
            "message": "spatial websocket disconnected",
            "ws_close_code": getattr(exc, "code", None),
            "timestamp": _now_epoch(),
        }
        return


@app.websocket("/status")
async def status_ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()
            _prune_expired_sessions()
            status = {
                "type": "status",
                "active_sessions": len(SESSION_STORE),
                "robot_enabled": robot is not None,
                "session_timeout_sec": SESSION_TIMEOUT_SEC,
            }
            if LAST_SPATIAL_DISCONNECT is not None:
                status["last_error"] = LAST_SPATIAL_DISCONNECT
            await websocket.send_text(json.dumps(status, ensure_ascii=False))
    except WebSocketDisconnect:
        return

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)