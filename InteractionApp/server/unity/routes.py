"""
unity.routes — Unity デバッグ REST エンドポイント + WebSocket ハンドラ。

Unity HoloLens に対する KeyInput, Calibration, ファイル操作、
保存イベントの副作用処理などを定義。
"""

from __future__ import annotations

import asyncio
import json
from loguru import logger

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from debug import debug_log
from hub import (
    WSHub,
    IncomingEvent,
    CALIB_REQ, CALIB_RES,
    LIST_REQ, LIST_RES,
    READ_REQ, READ_RES,
    KEY_INPUT_EVENT,
    SAVE_GRID_EVENT,
    SAVE_ROBOT_EVENT,
)
from files import FileManager

# loguru は debug モジュールですでに初期化されている想定
log = logger.bind(source="UNITY")

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
        unity_clients = len(hub.unity)
        debug_log.info("unity", f"import {kind}: rel_path={rel_path!r}, unity_clients={unity_clients}")
        if not hub.unity:
            debug_log.warn("unity", "import failed: Unity not connected")
            return JSONResponse({"error": "No Unity client connected"}, 503)
        try:
            debug_log.info("unity", f"Sending {READ_REQ} → Unity (rel_path={rel_path!r})")
            result = await hub.request(
                "unity", READ_REQ, READ_RES, {"relative_path": rel_path}
            )
            ok = result.get("success", False)
            err = result.get("error", "")
            content = result.get("content", "")
            clen = len(content) if isinstance(content, str) else "?"
            debug_log.info("unity", f"Got {READ_RES}: success={ok} len={clen}" + (f" error={err!r}" if err else ""))
            if not ok:
                return JSONResponse({"error": err or "read failed"}, 500)
            try:
                parsed = json.loads(content) if isinstance(content, str) else content
            except Exception as e:
                debug_log.error("unity", f"JSON parse failed: {e}")
                return JSONResponse({"error": f"JSON parse failed: {e}"}, 500)
            if kind == "robot":
                path = files.save_robot(parsed)
            else:
                path = files.save_grid(parsed)
            debug_log.info("unity", f"Saved {kind} → {path.name}")
            return {"success": True, "filename": path.name, "kind": kind}
        except asyncio.TimeoutError:
            debug_log.error("unity", f"Timeout waiting for {READ_RES} (rel_path={rel_path!r})")
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
            # タイムスタンプ付きファイルと manual ファイルの両方に保存
            ts_path = files.save_grid(data)
            files.save_grid(data, filename="qr_grid_config_manual.json")
            count = len(data) if isinstance(data, list) else "?"
            debug_log.info("unity", f"Grid config saved: {ts_path.name} + manual ({count} points)")

    elif ev.event_id == SAVE_ROBOT_EVENT:
        data = ev.payload_raw
        if isinstance(data, dict) and "value" in data and len(data) == 1:
            data = data["value"]
        if data:
            path = files.save_robot(data)
            debug_log.info("unity", f"Robot config saved: {path.name}")
