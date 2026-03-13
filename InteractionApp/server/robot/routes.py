"""
robot.routes — ロボット制御 REST エンドポイント。

/api/robot/... 以下のルートを定義。
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from loguru import logger

from debug import debug_log

# loguru は debug モジュールですでに初期化されている想定
log = logger.bind(source="ROBOT-API")

router = APIRouter(prefix="/api/robot", tags=["robot"])


def init_robot_routes(arm, hub) -> APIRouter:
    """arm (Adapter | Mock) と hub (WSHub) を注入してルーターを返す。"""

    @router.get("/status")
    async def robot_status():
        log.info("GET /status")
        return arm.status()

    @router.post("/connect")
    async def robot_connect():
        log.info("POST /connect")
        ok, msg = arm.connect()
        await hub.broadcast_status(arm.status())
        return {"success": ok, "message": msg}

    @router.post("/disconnect")
    async def robot_disconnect():
        log.info("POST /disconnect")
        ok, msg = arm.disconnect()
        await hub.broadcast_status(arm.status())
        return {"success": ok, "message": msg}

    @router.post("/home")
    async def robot_home():
        log.info("POST /home")
        ok, msg = arm.home()
        return {"success": ok, "message": msg}

    @router.post("/initial")
    async def robot_initial():
        log.info("POST /initial")
        ok, msg = arm.initial()
        return {"success": ok, "message": msg}

    @router.post("/reset")
    async def robot_reset():
        log.info("POST /reset")
        ok, msg = arm.reset()
        return {"success": ok, "message": msg}

    @router.post("/gripper")
    async def robot_gripper(request: Request):
        body = await request.json()
        action = body.get("action", "open")
        log.info(f"POST /gripper action={action}")
        ok, msg = arm.gripper(action)
        return {"success": ok, "message": msg}

    @router.post("/pick")
    async def robot_pick(request: Request):
        body = await request.json()
        x, y = body.get("x"), body.get("y")
        log.info(f"POST /pick x={x}, y={y}")
        if x is None or y is None:
            debug_log.error("robot", "pick: x and y required", body)
            return JSONResponse({"success": False, "message": "x and y required"}, 400)
        ok, msg = arm.pick_at(x, y)
        return {"success": ok, "message": msg}

    # ---- マニュアルモード ----
    @router.post("/manual_mode")
    async def robot_manual_mode(request: Request):
        """マニュアルモード ON/OFF。body: { enabled: bool }"""
        body = await request.json()
        enabled = bool(body.get("enabled", False))
        log.info(f"POST /manual_mode enabled={enabled}")
        ok, msg = arm.set_manual_mode(enabled)
        if ok:
            await hub.broadcast_status(arm.status())
        return {"success": ok, "message": msg}

    # ---- キャリブレーション ----

    @router.get("/calibration/status")
    async def robot_calib_status():
        """記録済みグリッドセル・Placeキー一覧を返す。"""
        log.info("GET /calibration/status")
        return arm.calibration_status()

    @router.post("/calibration/record_grid")
    async def robot_calib_record_grid(request: Request):
        """現在位置を grid_pose_map.json の指定セルに保存。body: { col, row }"""
        body = await request.json()
        col, row = body.get("col"), body.get("row")
        log.info(f"POST /calibration/record_grid col={col}, row={row}")
        if col is None or row is None:
            return JSONResponse({"success": False, "message": "col and row required"}, 400)
        ok, msg = arm.record_grid_cell(int(col), int(row))
        return {"success": ok, "message": msg}

    @router.post("/calibration/record_place")
    async def robot_calib_record_place(request: Request):
        """現在位置を place_pose_map.json の指定キーに保存。body: { place_key }"""
        body = await request.json()
        place_key = body.get("place_key", "default")
        log.info(f"POST /calibration/record_place place_key={place_key}")
        ok, msg = arm.record_place(place_key)
        return {"success": ok, "message": msg}

    # ---- プレース ----

    @router.post("/place")
    async def robot_place(request: Request):
        """指定キーの場所に置く。body: { place_key: "default" }"""
        body = await request.json()
        place_key = body.get("place_key", "default")
        log.info(f"POST /place place_key={place_key}")
        ok, msg = arm.place_at(place_key)
        return {"success": ok, "message": msg}

    @router.post("/pick_and_place")
    async def robot_pick_and_place(request: Request):
        """ピックしてプレース。body: { x, y, place_key }"""
        body = await request.json()
        x, y = body.get("x"), body.get("y")
        place_key = body.get("place_key", "default")
        log.info(f"POST /pick_and_place x={x}, y={y}, place_key={place_key}")
        if x is None or y is None:
            debug_log.error("robot", "pick_and_place: x and y required", body)
            return JSONResponse({"success": False, "message": "x and y required"}, 400)
        ok, msg = arm.pick_and_place(x, y, place_key)
        return {"success": ok, "message": msg}

    @router.post("/place/reload")
    async def robot_place_reload():
        """place_pose_map.json を再読み込み。"""
        log.info("POST /place/reload")
        ok, msg = arm.reload_place_map()
        return {"success": ok, "message": msg}

    # ---- 4x4 Grid Cells ----
    @router.get("/grid")
    async def robot_grid():
        """4x4 グリッドセル一覧を返す。"""
        log.info("GET /grid")
        cells = arm.grid_cells()
        return {"cells": cells, "count": len(cells)}

    @router.post("/grid/move")
    async def robot_grid_move(request: Request):
        """指定セルへ移動 (ピックしない)。body: { col: int, row: int }"""
        body = await request.json()
        col = body.get("col")
        row = body.get("row")
        log.info(f"POST /grid/move col={col}, row={row}")
        if col is None or row is None:
            debug_log.error("robot", "grid/move: col and row required", body)
            return JSONResponse({"success": False, "message": "col and row required"}, 400)
        ok, msg = arm.move_to_cell(int(col), int(row))
        return {"success": ok, "message": msg}

    @router.post("/grid/reload")
    async def robot_grid_reload():
        log.info("POST /grid/reload")
        ok, msg = arm.reload_grid_map()
        return {"success": ok, "message": msg}

    return router
