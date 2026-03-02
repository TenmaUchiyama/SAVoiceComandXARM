import dotenv 

dotenv.load_dotenv("../.env")  # .env ファイルから環境変数を読み込む



import asyncio
import json
import os
import traceback
from typing import Dict, Optional, List
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


def _parse_json_message(payload: str) -> dict:
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid_json: {exc}") from exc


def _validate_coordinates(request: SpatialReferenceRequest):
    if not request.objects:
        raise ValueError("E003: objects is empty")
    for item in request.objects:
        values = [item.position.x, item.position.y, item.position.z]
        if any(abs(v) > 100.0 for v in values):
            raise ValueError(f"E004: invalid coordinate range for {item.id}")


async def _run_with_timeout(coro, timeout_sec: float):
    return await asyncio.wait_for(coro, timeout=timeout_sec)


async def _run_stage1(utterance: str):
    return await _run_with_timeout(asyncio.to_thread(classify_reference_frame_v2, utterance), timeout_sec=10.0)


async def _run_stage2(utterance: str, reference_frame: str, features: List[Dict], refinement_context: str = ""):
    return await _run_with_timeout(
        asyncio.to_thread(rank_objects_v2, utterance, reference_frame, features, refinement_context),
        timeout_sec=10.0,
    )


def _build_result_message(request_id: str, reference_frame: str, ranked_candidates: List[Dict], reasoning: str) -> dict:
    top = ranked_candidates[0] if ranked_candidates else {"object_id": None, "score": 0.0}
    return {
        "type": "spatial_reference_result",
        "request_id": request_id,
        "target": {
            "object_id": top.get("object_id"),
            "confidence": top.get("score", 0.0),
            "reference_frame": reference_frame,
        },
        "ranked_candidates": [
            {"object_id": row.get("object_id"), "score": row.get("score", 0.0)} for row in ranked_candidates
        ],
        "reasoning": reasoning,
    }


async def _process_spatial_reference_request(request_data: SpatialReferenceRequest) -> dict:
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
    except Exception:
        ranked_candidates = apply_fallback_ranking(request_data.utterance.text, features)

    SESSION_STORE[request_data.request_id] = SessionContext(
        request_id=request_data.request_id,
        utterance=request_data.utterance.text,
        reference_frame=reference_frame,
        objects=request_data.objects,
        user_pose=request_data.user_pose,
        robot_pose=request_data.robot_pose,
        ranked_candidates=ranked_candidates,
    )

    return _build_result_message(
        request_id=request_data.request_id,
        reference_frame=reference_frame,
        ranked_candidates=ranked_candidates,
        reasoning="LLM selection" if ranked_candidates and ranked_candidates[0].get("reason") != "fallback" else "fallback selection",
    )


async def _process_refinement_request(request_data: RefinementRequest) -> dict:
    previous = SESSION_STORE.get(request_data.original_request_id)
    if previous is None:
        return {
            "type": "error",
            "request_id": request_data.request_id,
            "error_code": "E006",
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
    except Exception:
        ranked_candidates = apply_fallback_ranking(request_data.utterance.text, features, request_data.previous_target)

    SESSION_STORE[request_data.request_id] = SessionContext(
        request_id=request_data.request_id,
        utterance=request_data.utterance.text,
        reference_frame=reference_frame,
        objects=previous.objects,
        user_pose=user_pose,
        robot_pose=previous.robot_pose,
        ranked_candidates=ranked_candidates,
    )

    return _build_result_message(
        request_id=request_data.request_id,
        reference_frame=reference_frame,
        ranked_candidates=ranked_candidates,
        reasoning="refined selection",
    )


async def _process_confirmation_request(request_data: ConfirmationRequest) -> dict:
    session = SESSION_STORE.get(request_data.request_id)
    if session is None:
        return {
            "type": "error",
            "request_id": request_data.request_id,
            "error_code": "E006",
            "message": "session expired or unknown request_id",
        }

    target = next((obj for obj in session.objects if obj.id == request_data.confirmed_object_id), None)
    if target is None:
        return {
            "type": "error",
            "request_id": request_data.request_id,
            "error_code": "E004",
            "message": "invalid confirmed_object_id",
        }

    command = {
        "type": "robot_command",
        "request_id": request_data.request_id,
        "action": request_data.action,
        "target_object_id": target.id,
        "target_position": {
            "x": target.position.x,
            "y": target.position.y,
            "z": target.position.z,
        },
        "status": "executing",
    }

    if robot is not None and request_data.action == "pick":
        try:
            robot.pick_at(target.position.x, target.position.y)
        except Exception as exc:
            command["status"] = "failed"
            command["error"] = str(exc)

    return command




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

            message = json.loads(data)
            
            if message.get("eventId") == "SaveGridConfig":
                grid_data = json.loads(message.get("payload", "{}"))
                filename = save_grid_to_file(grid_data)
                
                # 結果をUnityに返す
                response = {
                    "eventId": "SaveGridConfigResult",
                    "payload": json.dumps({"status": "success", "filename": filename})
                }
                await websocket.send_text(json.dumps(response))
            
            if message.get("eventId") == "SaveRobotMarkerConfig":
                marker_data = json.loads(message.get("payload", "{}"))
                filename = save_robot_marker_config(marker_data)
                
                response = {
                    "eventId": "SaveRobotMarkerConfigResult",
                    "payload": json.dumps({"status": "success", "filename": filename})
                }
                await websocket.send_text(json.dumps(response))
                print(f"【Server】ロボットマーカー設定を保存しました: {filename}")
            
            if message.get("eventId") == "XarmPick":
                payload = json.loads(message.get("payload", "{}"))
                x = payload.get("x")
                y = payload.get("y")

                result =  robot.pick_at(x, y)

                await websocket.send_text(json.dumps({
                    "eventId": "XarmPickResult",
                    "payload": result
                }))
                
    except WebSocketDisconnect as e:
        manager.disconnect(websocket)
        print(f"【Server】Unity切断 code={getattr(e, 'code', None)}")
    except Exception as e:
        print(f"【Server】エラー: {e!r}")
        manager.disconnect(websocket)


@app.websocket("/spatial")
async def spatial_ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = _parse_json_message(raw)
                msg_type = message.get("type")
                if msg_type == "spatial_reference_request":
                    req = SpatialReferenceRequest(**message)
                    response = await _process_spatial_reference_request(req)
                elif msg_type == "refinement_request":
                    req = RefinementRequest(**message)
                    response = await _process_refinement_request(req)
                elif msg_type == "confirmation":
                    req = ConfirmationRequest(**message)
                    response = await _process_confirmation_request(req)
                else:
                    response = {
                        "type": "error",
                        "error_code": "E004",
                        "message": f"unsupported message type: {msg_type}",
                    }
            except ValueError as exc:
                response = {
                    "type": "error",
                    "error_code": "E004",
                    "message": str(exc),
                }
            except Exception as exc:
                response = {
                    "type": "error",
                    "error_code": "E002",
                    "message": str(exc),
                }

            await websocket.send_text(json.dumps(response, ensure_ascii=False))
    except WebSocketDisconnect:
        return


@app.websocket("/status")
async def status_ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()
            status = {
                "type": "status",
                "active_sessions": len(SESSION_STORE),
                "robot_enabled": robot is not None,
            }
            await websocket.send_text(json.dumps(status, ensure_ascii=False))
    except WebSocketDisconnect:
        return

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)