"""
robot.routes — ロボット制御 REST エンドポイント。

/api/robot/... 以下のルートを定義。
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from debug import debug_log

router = APIRouter(prefix="/api/robot", tags=["robot"])


def init_robot_routes(arm, hub) -> APIRouter:
    """arm (Adapter | Mock) と hub (WSHub) を注入してルーターを返す。"""

    @router.get("/status")
    async def robot_status():
        return arm.status()

    @router.post("/connect")
    async def robot_connect():
        ok, msg = arm.connect()
        await hub.broadcast_status(arm.status())
        return {"success": ok, "message": msg}

    @router.post("/disconnect")
    async def robot_disconnect():
        ok, msg = arm.disconnect()
        await hub.broadcast_status(arm.status())
        return {"success": ok, "message": msg}

    @router.post("/home")
    async def robot_home():
        ok, msg = arm.home()
        return {"success": ok, "message": msg}

    @router.post("/initial")
    async def robot_initial():
        ok, msg = arm.initial()
        return {"success": ok, "message": msg}

    @router.post("/reset")
    async def robot_reset():
        ok, msg = arm.reset()
        return {"success": ok, "message": msg}

    @router.post("/gripper")
    async def robot_gripper(request: Request):
        body = await request.json()
        action = body.get("action", "open")
        ok, msg = arm.gripper(action)
        return {"success": ok, "message": msg}

    @router.post("/pick")
    async def robot_pick(request: Request):
        body = await request.json()
        x, y = body.get("x"), body.get("y")
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
        ok, msg = arm.set_manual_mode(enabled)
        if ok:
            await hub.broadcast_status(arm.status())
        return {"success": ok, "message": msg}

    # ---- 4x4 Grid Cells ----
    @router.get("/grid")
    async def robot_grid():
        """4x4 グリッドセル一覧を返す。"""
        cells = arm.grid_cells()
        return {"cells": cells, "count": len(cells)}

    @router.post("/grid/move")
    async def robot_grid_move(request: Request):
        """指定セルへ移動 (ピックしない)。body: { col: int, row: int }"""
        body = await request.json()
        col = body.get("col")
        row = body.get("row")
        if col is None or row is None:
            debug_log.error("robot", "grid/move: col and row required", body)
            return JSONResponse({"success": False, "message": "col and row required"}, 400)
        ok, msg = arm.move_to_cell(int(col), int(row))
        return {"success": ok, "message": msg}

    @router.post("/grid/reload")
    async def robot_grid_reload():
        """grid_pose_map.json を再読み込み。"""
        ok, msg = arm.reload_grid_map()
        return {"success": ok, "message": msg}

    return router
