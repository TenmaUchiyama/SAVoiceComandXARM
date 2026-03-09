"""
unified_debug_server.py
=======================
InteractionApp フロントエンドと WebSocket で接続しつつ、
Unity / xArm のデバッグができる統合サーバー。

外部モジュールの再利用:
  - XArm/pick_from_grid.py  … XArmPicker クラスを import
  - SystemServer/src/utils.py … _normalize_json_data を import
  - pc_debug_ws_cli.py のヘルパーはインライン移植 (削除予定のため)

起動例:
  python unified_debug_server.py [--host 0.0.0.0] [--port 8765] [--arm-ip 192.168.1.199]
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import logging
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Workspace layout
# ---------------------------------------------------------------------------
_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent  # SAVoiceComandXARM
_XARM_DIR = _WORKSPACE_ROOT / "XArm"
_SYSSERVER_SRC = _WORKSPACE_ROOT / "SystemServer" / "src"

# ---------------------------------------------------------------------------
# External imports: XArm SDK (optional)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(_XARM_DIR))
sys.path.insert(0, str(_SYSSERVER_SRC))

HAS_XARM_SDK = False
_XArmPickerCls = None
_GRIP_OPEN = 850
_GRIP_CLOSE = 350
_ARM_IP = "192.168.1.199"

try:
    from pick_from_grid import XArmPicker as _XArmPickerImport
    from pick_from_grid import ARM_IP, GRIP_OPEN, GRIP_CLOSE  # type: ignore

    HAS_XARM_SDK = True
    _XArmPickerCls = _XArmPickerImport
    _ARM_IP = ARM_IP
    _GRIP_OPEN = GRIP_OPEN
    _GRIP_CLOSE = GRIP_CLOSE
except ImportError:
    pass

# External imports: SystemServer utils
try:
    from utils import _normalize_json_data
except ImportError:
    # Fallback: handle JSON-in-JSON strings
    def _normalize_json_data(data: Any) -> Any:
        if isinstance(data, str):
            s = data.strip()
            if s and s[0] in "[{\"" and s[-1] in "]}\"":
                try:
                    return json.loads(s)
                except Exception:
                    pass
        return data

# FastAPI / Uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("unified_debug")


# ===================================================================
# pc_debug_ws_cli.py からインライン移植 (削除予定ファイルのため)
# ===================================================================

# -- Event constants --
LIST_REQ = "pc_debug_persistent_list_request"
LIST_RES = "pc_debug_persistent_list_response"
READ_REQ = "pc_debug_read_json_request"
READ_RES = "pc_debug_read_json_response"
CALIB_REQ = "pc_debug_calibration_request"
CALIB_RES = "pc_debug_calibration_response"
KEY_INPUT_EVENT = "KeyInput"
RESTORE_GRID_EVENT = "RestoreGridConfig"
RESTORE_ROBOT_EVENT = "RestoreRobotMarkerConfig"
SAVE_GRID_EVENT = "SaveGridConfig"
SAVE_ROBOT_EVENT = "SaveRobotConfig"


def ensure_dict(value: Any) -> Dict[str, Any]:
    """任意の値を dict に統一する。"""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except Exception:
            return {"value": value}
    if value is None:
        return {}
    return {"value": value}


def decode_json_value(value: Any) -> Any:
    """JSON 文字列をパース。失敗したらそのまま返す。"""
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            return value
    return value


@dataclass
class IncomingEvent:
    event_id: str
    payload: Dict[str, Any]
    payload_raw: Any


def parse_incoming(raw: str) -> IncomingEvent:
    """受信メッセージをパース (legacy 形式・raw 形式の両方に対応)。"""
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Incoming packet must be a JSON object")

    # Legacy format: {eventId, payload: JSON.stringify(...)}
    legacy_event = str(data.get("eventId", "")).strip()
    if legacy_event:
        payload_raw = decode_json_value(data.get("payload"))
        return IncomingEvent(
            event_id=legacy_event,
            payload=ensure_dict(payload_raw),
            payload_raw=payload_raw,
        )

    # Raw format: {type, ...rest}
    raw_event = str(data.get("type", "")).strip()
    if not raw_event:
        raise ValueError("Incoming packet missing eventId/type")
    return IncomingEvent(event_id=raw_event, payload=data, payload_raw=data)


def encode_raw_event(event_id: str, payload: Dict[str, Any]) -> str:
    """Raw 形式のイベントを JSON 文字列にエンコード。"""
    packet = dict(payload)
    packet["type"] = event_id
    return json.dumps(packet, ensure_ascii=False)


# ===================================================================
# FileManager — 設定ファイルの保存・読み込み
# ===================================================================

class FileManager:
    """Grid / Robot config ファイル管理。"""

    def __init__(self, save_dir: Path):
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)

    # --- Grid ---
    def list_grids(self) -> List[Path]:
        return sorted(
            self.save_dir.glob("qr_grid_config_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    def save_grid(self, data: Any) -> Path:
        data = _normalize_json_data(data)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.save_dir / f"qr_grid_config_{ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    def load_grid(self, name: Optional[str] = None) -> Tuple[str, Any]:
        target = self._resolve(name, self.list_grids, "grid")
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        return target.name, _normalize_json_data(data)

    # --- Robot ---
    def list_robots(self) -> List[Path]:
        return sorted(
            self.save_dir.glob("qr_robot_config_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    def save_robot(self, data: Any) -> Path:
        data = _normalize_json_data(data)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.save_dir / f"qr_robot_config_{ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    def load_robot(self, name: Optional[str] = None) -> Tuple[str, Any]:
        target = self._resolve(name, self.list_robots, "robot")
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        return target.name, _normalize_json_data(data)

    # --- helper ---
    def _resolve(self, name, list_fn, kind: str) -> Path:
        if name:
            p = self.save_dir / name
            if not p.exists():
                raise FileNotFoundError(f"{kind} file not found: {p}")
            return p
        files = list_fn()
        if not files:
            raise FileNotFoundError(f"No saved {kind} files in {self.save_dir}")
        return files[0]


# ===================================================================
# xArm — Adapter (XArmPicker をラップ) / Mock
# ===================================================================

class XArmMock:
    """SDK 不要のモックアーム (開発・UI テスト用)。"""

    def __init__(self):
        self._connected = False
        self._position = [300.0, 0.0, 200.0, 180.0, 0.0, 0.0]
        self._gripper = "open"

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> Tuple[bool, str]:
        self._connected = True
        return True, "mock connected"

    def disconnect(self) -> Tuple[bool, str]:
        self._connected = False
        return True, "mock disconnected"

    def home(self) -> Tuple[bool, str]:
        self._position = [300.0, 0.0, 200.0, 180.0, 0.0, 0.0]
        return True, "mock homed"

    def reset(self) -> Tuple[bool, str]:
        return True, "mock reset"

    def gripper(self, action: str) -> Tuple[bool, str]:
        self._gripper = action
        return True, f"mock gripper {action}"

    def pick_at(self, x: Any, y: Any) -> Tuple[bool, str]:
        return True, f"mock pick at ({x},{y})"

    def status(self) -> dict:
        return {
            "connected": self._connected,
            "mode": "mock",
            "state": 0 if self._connected else None,
            "position": self._position if self._connected else None,
            "error_code": 0,
        }


class XArmAdapter:
    """XArm/pick_from_grid.py の XArmPicker をラップしてサーバー用 I/F を提供。

    XArmPicker はコンストラクタで即接続するため、
    connect() 呼び出し時に初めてインスタンスを生成する。
    """

    def __init__(self, ip: str = _ARM_IP):
        self._ip = ip
        self._picker = None  # XArmPicker instance (lazy)
        self._grid_json = str(_XARM_DIR / "grid_pose_map.json")

    @property
    def connected(self) -> bool:
        return self._picker is not None

    def connect(self) -> Tuple[bool, str]:
        if self._picker is not None:
            return True, "already connected"
        try:
            self._picker = _XArmPickerCls(self._ip, self._grid_json)
            return True, f"connected to {self._ip}"
        except Exception as e:
            self._picker = None
            return False, str(e)

    def disconnect(self) -> Tuple[bool, str]:
        if self._picker is None:
            return True, "not connected"
        try:
            self._picker.arm.disconnect()
        except Exception:
            pass
        self._picker = None
        return True, "disconnected"

    def home(self) -> Tuple[bool, str]:
        if not self._picker:
            return False, "not connected"
        try:
            self._picker.arm.move_gohome(wait=True)
            return True, "homed"
        except Exception as e:
            return False, str(e)

    def reset(self) -> Tuple[bool, str]:
        if not self._picker:
            return False, "not connected"
        try:
            self._picker.arm.clean_error()
            self._picker.arm.clean_warn()
            self._picker.arm.motion_enable(True)
            self._picker.arm.set_mode(0)
            self._picker.arm.set_state(0)
            time.sleep(0.5)
            return True, "reset complete"
        except Exception as e:
            return False, str(e)

    def gripper(self, action: str) -> Tuple[bool, str]:
        if not self._picker:
            return False, "not connected"
        try:
            pos = _GRIP_OPEN if action == "open" else _GRIP_CLOSE
            self._picker.set_gripper_pos(pos)
            return True, f"gripper {action}"
        except Exception as e:
            return False, str(e)

    def pick_at(self, x: Any, y: Any) -> Tuple[bool, str]:
        if not self._picker:
            return False, "not connected"
        try:
            ok = self._picker.pick_at(x, y)
            return (True, "pick complete") if ok else (False, f"coordinate ({x},{y}) not found in grid map")
        except Exception as e:
            return False, str(e)

    def reload_poses(self) -> Tuple[bool, str]:
        """grid_pose_map.json を再読み込み。"""
        if not self._picker:
            return False, "not connected"
        try:
            self._picker.load_poses()
            return True, f"reloaded {len(self._picker.pose_map)} poses"
        except Exception as e:
            return False, str(e)

    def status(self) -> dict:
        if not self._picker:
            return {"connected": False}
        try:
            code, pos = self._picker.arm.get_position()
            return {
                "connected": True,
                "mode": "real",
                "state": self._picker.arm.state,
                "position": pos if code == 0 else None,
                "error_code": self._picker.arm.error_code,
                "grid_poses_loaded": len(self._picker.pose_map),
            }
        except Exception:
            return {"connected": True, "mode": "real", "state": "unknown"}


# ===================================================================
# WebSocket Hub — Unity / Spatial / Status channels
# ===================================================================

class WSHub:
    """WebSocket 接続管理 (Unity, Spatial, Status)。"""

    def __init__(self):
        self.unity: Set[WebSocket] = set()
        self.spatial: Set[WebSocket] = set()
        self.status: Set[WebSocket] = set()
        self.pending: Dict[str, asyncio.Future] = {}

    # --- connection management ---
    def add(self, channel: str, ws: WebSocket):
        self._ch(channel).add(ws)
        log.info("WS [%s] +1 (total=%d)", channel, len(self._ch(channel)))

    def remove(self, channel: str, ws: WebSocket):
        self._ch(channel).discard(ws)
        log.info("WS [%s] -1 (total=%d)", channel, len(self._ch(channel)))

    def _ch(self, channel: str) -> Set[WebSocket]:
        return {"unity": self.unity, "spatial": self.spatial, "status": self.status}[channel]

    # --- broadcast ---
    async def broadcast(self, channel: str, message: str):
        targets = list(self._ch(channel))
        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                self._ch(channel).discard(ws)

    async def broadcast_status(self, data: dict):
        msg = json.dumps({"type": "status_update", **data}, ensure_ascii=False)
        await self.broadcast("status", msg)

    # --- send helpers ---
    async def send_to(self, channel: str, event_id: str, payload: dict):
        msg = encode_raw_event(event_id, payload)
        await self.broadcast(channel, msg)

    async def send_legacy_to(self, channel: str, event_id: str, payload: dict):
        packet = json.dumps(
            {"eventId": event_id, "payload": json.dumps(payload, ensure_ascii=False)},
            ensure_ascii=False,
        )
        await self.broadcast(channel, packet)

    # --- request / response pattern ---
    async def request(
        self,
        channel: str,
        req_event: str,
        res_event: str,
        payload: dict,
        timeout_sec: float = 10.0,
    ) -> dict:
        request_id = str(uuid.uuid4())
        payload = dict(payload)
        payload["request_id"] = request_id

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        key = f"{res_event}:{request_id}"
        self.pending[key] = future

        try:
            await self.send_to(channel, req_event, payload)
            return await asyncio.wait_for(future, timeout=timeout_sec)
        finally:
            self.pending.pop(key, None)

    def resolve_pending(self, event_id: str, payload: dict):
        request_id = str(payload.get("request_id", "")).strip()
        if not request_id:
            return
        key = f"{event_id}:{request_id}"
        future = self.pending.get(key)
        if future and not future.done():
            future.set_result(payload)


# ===================================================================
# FastAPI Application
# ===================================================================

def create_app(arm, files: FileManager, hub: WSHub) -> FastAPI:
    app = FastAPI(title="Unified Debug Server")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------------------------------------------------------
    # REST — Health / Robot
    # ---------------------------------------------------------------
    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "xarm_mode": "real" if isinstance(arm, XArmAdapter) else "mock",
            "unity_clients": len(hub.unity),
            "spatial_clients": len(hub.spatial),
        }

    @app.get("/robot/status")
    async def robot_status():
        return arm.status()

    @app.post("/robot/connect")
    async def robot_connect():
        ok, msg = arm.connect()
        await hub.broadcast_status(arm.status())
        return {"success": ok, "message": msg}

    @app.post("/robot/disconnect")
    async def robot_disconnect():
        ok, msg = arm.disconnect()
        await hub.broadcast_status(arm.status())
        return {"success": ok, "message": msg}

    @app.post("/robot/home")
    async def robot_home():
        ok, msg = arm.home()
        return {"success": ok, "message": msg}

    @app.post("/robot/reset")
    async def robot_reset():
        ok, msg = arm.reset()
        return {"success": ok, "message": msg}

    @app.post("/robot/gripper")
    async def robot_gripper(request: Request):
        body = await request.json()
        action = body.get("action", "open")
        ok, msg = arm.gripper(action)
        return {"success": ok, "message": msg}

    @app.post("/robot/pick")
    async def robot_pick(request: Request):
        body = await request.json()
        x, y = body.get("x"), body.get("y")
        if x is None or y is None:
            return JSONResponse({"success": False, "message": "x and y required"}, 400)
        ok, msg = arm.pick_at(x, y)
        return {"success": ok, "message": msg}

    # ---------------------------------------------------------------
    # REST — Grid configs
    # ---------------------------------------------------------------
    @app.get("/grids")
    async def grids_list():
        return [
            {"name": p.name, "modified": p.stat().st_mtime}
            for p in files.list_grids()
        ]

    @app.post("/grids/save")
    async def grids_save(request: Request):
        data = await request.json()
        path = files.save_grid(data)
        return {"success": True, "filename": path.name}

    @app.get("/grids/latest")
    async def grids_latest():
        try:
            name, data = files.load_grid()
            return {"filename": name, "data": data}
        except FileNotFoundError as e:
            return JSONResponse({"error": str(e)}, 404)

    @app.post("/grids/restore")
    async def grids_restore(request: Request):
        body = await request.json()
        filename = body.get("filename")
        grid_data = body.get("gridPoints")
        if grid_data is None:
            try:
                filename, grid_data = files.load_grid(filename)
            except FileNotFoundError as e:
                return JSONResponse({"error": str(e)}, 404)
        payload = {
            "type": "grid_config",
            "filename": filename or "",
            "gridPoints": grid_data,
        }
        await hub.send_legacy_to("unity", RESTORE_GRID_EVENT, payload)
        return {"success": True, "message": f"restore sent: {filename}"}

    # ---------------------------------------------------------------
    # REST — Robot marker configs
    # ---------------------------------------------------------------
    @app.get("/robots")
    async def robots_list():
        return [
            {"name": p.name, "modified": p.stat().st_mtime}
            for p in files.list_robots()
        ]

    @app.post("/robots/save")
    async def robots_save(request: Request):
        data = await request.json()
        path = files.save_robot(data)
        return {"success": True, "filename": path.name}

    @app.get("/robots/latest")
    async def robots_latest():
        try:
            name, data = files.load_robot()
            return {"filename": name, "data": data}
        except FileNotFoundError as e:
            return JSONResponse({"error": str(e)}, 404)

    @app.post("/robots/restore")
    async def robots_restore(request: Request):
        body = await request.json()
        filename = body.get("filename")
        marker_data = body.get("markerData")
        if marker_data is None:
            try:
                filename, marker_data = files.load_robot(filename)
            except FileNotFoundError as e:
                return JSONResponse({"error": str(e)}, 404)
        payload = {
            "type": "marker_config",
            "filename": filename or "",
            "markerData": marker_data,
        }
        await hub.send_legacy_to("unity", RESTORE_ROBOT_EVENT, payload)
        return {"success": True, "message": f"restore sent: {filename}"}

    # ---------------------------------------------------------------
    # REST — Unity debug helpers
    # ---------------------------------------------------------------
    @app.post("/unity/key")
    async def unity_key(request: Request):
        body = await request.json()
        key = body.get("key", "")
        normalized = "space" if key == " " else key
        await hub.send_legacy_to(
            "unity", KEY_INPUT_EVENT, {"type": "key", "key": normalized}
        )
        return {"success": True, "key": normalized}

    @app.post("/unity/calib")
    async def unity_calib(request: Request):
        body = await request.json()
        action = body.get("action", "")
        if not hub.unity:
            return JSONResponse({"error": "No Unity client connected"}, 503)
        try:
            result = await hub.request("unity", CALIB_REQ, CALIB_RES, {"action": action})
            return result
        except asyncio.TimeoutError:
            return JSONResponse({"error": "Unity did not respond in time"}, 504)

    @app.post("/unity/list")
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

    @app.post("/unity/read")
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

    @app.post("/unity/import")
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
            return {"success": True, "filename": path.name, "kind": kind}
        except asyncio.TimeoutError:
            return JSONResponse({"error": "Unity did not respond in time"}, 504)

    # ---------------------------------------------------------------
    # WebSocket Endpoints
    # ---------------------------------------------------------------
    @app.websocket("/")
    async def ws_unity(ws: WebSocket):
        await ws.accept()
        hub.add("unity", ws)
        try:
            while True:
                raw = await ws.receive_text()
                try:
                    ev = parse_incoming(raw)
                    log.info("[Unity RX] %s", ev.event_id)
                    _handle_unity_event(ev, files)
                    hub.resolve_pending(ev.event_id, ev.payload)
                except Exception as e:
                    log.warning("[Unity] parse error: %s", e)
        except WebSocketDisconnect:
            pass
        finally:
            hub.remove("unity", ws)

    @app.websocket("/spatial")
    async def ws_spatial(ws: WebSocket):
        await ws.accept()
        hub.add("spatial", ws)
        try:
            while True:
                raw = await ws.receive_text()
                log.info("[Spatial RX] %s", raw[:120])
        except WebSocketDisconnect:
            pass
        finally:
            hub.remove("spatial", ws)

    @app.websocket("/status")
    async def ws_status(ws: WebSocket):
        await ws.accept()
        hub.add("status", ws)
        # 接続時に現在のステータスを送信
        try:
            await ws.send_text(
                json.dumps(
                    {"type": "status_update", **arm.status()}, ensure_ascii=False
                )
            )
        except Exception:
            pass
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            hub.remove("status", ws)

    return app


# ---------------------------------------------------------------
# Unity イベントの副作用ハンドラ
# ---------------------------------------------------------------

def _handle_unity_event(ev: IncomingEvent, files: FileManager):
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
            log.info("[SAVE] Grid config: %s (%s points)", path.name, count)

    elif ev.event_id == SAVE_ROBOT_EVENT:
        data = ev.payload_raw
        if isinstance(data, dict) and "value" in data and len(data) == 1:
            data = data["value"]
        if data:
            path = files.save_robot(data)
            log.info("[SAVE] Robot config: %s", path.name)


# ===================================================================
# Main
# ===================================================================

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Unified Debug Server for InteractionApp / Unity / xArm"
    )
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--arm-ip", default=_ARM_IP, help="xArm IP address")
    p.add_argument("--mock", action="store_true", help="Force mock xArm (ignore SDK)")
    p.add_argument(
        "--save-dir",
        default=None,
        help="Directory for grid/robot config files",
    )
    return p.parse_args()


def main():
    args = parse_args()

    # Save directory
    save_dir = (
        Path(args.save_dir)
        if args.save_dir
        else Path(__file__).resolve().parent / "saved_grids"
    )
    files = FileManager(save_dir)

    # xArm instance
    if args.mock or not HAS_XARM_SDK:
        if not HAS_XARM_SDK and not args.mock:
            log.warning("xArm SDK not found — using mock mode")
        arm = XArmMock()
    else:
        arm = XArmAdapter(args.arm_ip)

    hub = WSHub()
    app = create_app(arm, files, hub)

    log.info("=" * 60)
    log.info("  Unified Debug Server")
    log.info("  http://%s:%d", args.host, args.port)
    log.info("  WS  /         → Unity channel")
    log.info("  WS  /spatial  → Spatial pipeline channel")
    log.info("  WS  /status   → Status broadcast channel")
    log.info("  xArm mode: %s", "real" if isinstance(arm, XArmAdapter) else "mock")
    log.info("  Save dir: %s", save_dir.resolve())
    log.info("=" * 60)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
