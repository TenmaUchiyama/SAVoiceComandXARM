import asyncio
import json
import os
import traceback
from typing import Dict, Optional, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from contextlib import asynccontextmanager
from Calculator.AgentObjectSelectorCalculator import *
from LLM_Agent.agent import classify_reference_frame, decide_selection_rule, execute_decision
from manager import send_json_grid
from manager import manager, keyboard_monitor_loop
from utils import save_grid_to_file, save_robot_marker_config
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)