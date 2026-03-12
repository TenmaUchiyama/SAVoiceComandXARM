"""
unity.routes — Unity デバッグ REST エンドポイント + WebSocket ハンドラ。

Unity HoloLens に対する KeyInput, Calibration, ファイル操作、
保存イベントの副作用処理などを定義。
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from debug import debug_log
from hub import (
    WSHub,
    parse_incoming,
    IncomingEvent,
    CALIB_REQ, CALIB_RES,
    LIST_REQ, LIST_RES,
    READ_REQ, READ_RES,
    KEY_INPUT_EVENT,
    SAVE_GRID_EVENT,
    SAVE_ROBOT_EVENT,
)
from files import FileManager

log = logging.getLogger("unified_debug")

router = APIRouter(tags=["unity"])


def init_unity_routes(files: FileManager, hub: WSHub) -> APIRouter:
    """FileManager と WSHub を注入してルーターを返す。"""

    # ---- REST ----
    @router.post("/unity/key")
    async def unity_key(request: Request):
        body = await request.json()
        key = body.get("key", "")
        normalized = "space" if key == " " else key
        await hub.send_legacy_to(
            "unity", KEY_INPUT_EVENT, {"type": "key", "key": normalized}
        )
        debug_log.info("unity", f"Key sent: {normalized}")
        return {"success": True, "key": normalized}

    @router.post("/unity/calib")
    async def unity_calib(request: Request):
        body = await request.json()
        action = body.get("action", "")
        if not hub.unity:
            debug_log.warn("unity", "Calibration request but no Unity client connected")
            return JSONResponse({"error": "No Unity client connected"}, 503)
        try:
            result = await hub.request("unity", CALIB_REQ, CALIB_RES, {"action": action})
            return result
        except asyncio.TimeoutError:
            debug_log.error("unity", "Calibration timeout")
            return JSONResponse({"error": "Unity did not respond in time"}, 504)

    @router.post("/unity/list")
    async def unity_list(request: Request):
        body = await request.json()
        recursive = body.get("recursive", False)
        if not hub.unity:
            return JSONResponse({"error": "No Unity client connected"}, 503)
        try:
            result = await hub.request(
                "unity", LIST_REQ, LIST_RES, {"recursive": recursive}
            )
            return result
        except asyncio.TimeoutError:
            return JSONResponse({"error": "Unity did not respond in time"}, 504)

    @router.post("/unity/read")
    async def unity_read(request: Request):
        body = await request.json()
        rel_path = body.get("relative_path", "")
        if not hub.unity:
            return JSONResponse({"error": "No Unity client connected"}, 503)
        try:
            result = await hub.request(
                "unity", READ_REQ, READ_RES, {"relative_path": rel_path}
            )
            return result
        except asyncio.TimeoutError:
            return JSONResponse({"error": "Unity did not respond in time"}, 504)

    @router.post("/unity/import")
    async def unity_import(request: Request):
        """Unity の persistentDataPath から JSON を取得しローカル保存。"""
        body = await request.json()
        rel_path = body.get("relative_path", "qr_grid_config.json")
        kind = body.get("kind", "grid")
        if not hub.unity:
            return JSONResponse({"error": "No Unity client connected"}, 503)
        try:
            result = await hub.request(
                "unity", READ_REQ, READ_RES, {"relative_path": rel_path}
            )
            if not result.get("success"):
                return JSONResponse(
                    {"error": result.get("error", "read failed")}, 500
                )
            content = result.get("content", "")
            try:
                parsed = json.loads(content) if isinstance(content, str) else content
            except Exception as e:
                return JSONResponse({"error": f"JSON parse failed: {e}"}, 500)
            if kind == "robot":
                path = files.save_robot(parsed)
            else:
                path = files.save_grid(parsed)
            debug_log.info("unity", f"Imported {kind} config: {path.name}")
            return {"success": True, "filename": path.name, "kind": kind}
        except asyncio.TimeoutError:
            return JSONResponse({"error": "Unity did not respond in time"}, 504)

    return router


# ===================================================================
# Unity WebSocket handler
# ===================================================================

def handle_unity_event(ev: IncomingEvent, files: FileManager):
    """Unity から受信したイベントの副作用を処理 (設定保存など)。"""
    if ev.event_id == SAVE_GRID_EVENT:
        data = ev.payload_raw
        if isinstance(data, dict) and "gridPoints" in data:
            data = data["gridPoints"]
        if isinstance(data, dict) and "value" in data and len(data) == 1:
            data = data["value"]
        if data:
            path = files.save_grid(data)
            count = len(data) if isinstance(data, list) else "?"
            debug_log.info("unity", f"Grid config saved: {path.name} ({count} points)")

    elif ev.event_id == SAVE_ROBOT_EVENT:
        data = ev.payload_raw
        if isinstance(data, dict) and "value" in data and len(data) == 1:
            data = data["value"]
        if data:
            path = files.save_robot(data)
            debug_log.info("unity", f"Robot config saved: {path.name}")
