"""
unified_debug_server.py
=======================
InteractionApp フロントエンドと WebSocket で接続しつつ、
Unity / xArm のデバッグができる統合サーバー。

モジュール構成:
  - robot/   … ロボット制御 (adapter=本番, mock=開発用)
  - hub/     … WebSocket 接続管理・イベントヘルパー
  - files/   … Grid / Robot 設定ファイル管理
  - debug/   … デバッグログ (アプリにリアルタイム配信)
  - unity/   … Unity デバッグ REST / WS ハンドラ

起動例:
  python unified_debug_server.py [--host 0.0.0.0] [--port 8765] [--arm-ip 192.168.1.199]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# server/ ディレクトリを sys.path に追加 (サブモジュール import 用)
# ---------------------------------------------------------------------------
_SERVER_DIR = Path(__file__).resolve().parent
if str(_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVER_DIR))

# ---------------------------------------------------------------------------
# FastAPI / Uvicorn
# ---------------------------------------------------------------------------
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ---------------------------------------------------------------------------
# 自作モジュール
# ---------------------------------------------------------------------------
from debug import debug_log
from hub import WSHub, parse_incoming
from hub import SAVE_GRID_EVENT, SAVE_ROBOT_EVENT
from files import FileManager
from robot import create_arm, XArmMock
from robot.routes import init_robot_routes
from robot.ws_handlers import dispatch as dispatch_robot_ws, cleanup_on_disconnect as robot_ws_cleanup
from files.routes import init_file_routes
from unity.routes import init_unity_routes, handle_unity_event
from debug.routes import init_debug_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("unified_debug")


# ===================================================================
# FastAPI Application — 組み立て
# ===================================================================

def create_app(arm, files: FileManager, hub: WSHub) -> FastAPI:
    app = FastAPI(title="Unified Debug Server")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # デバッグログの WS ブロードキャストを接続
    debug_log.set_broadcast(hub.broadcast_debug)

    # ---------------------------------------------------------------
    # REST — Health
    # ---------------------------------------------------------------
    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "xarm_mode": arm.status().get("mode", "unknown"),
            "unity_clients": len(hub.unity),
            "spatial_clients": len(hub.spatial),
        }

    # ---------------------------------------------------------------
    # REST Routers (各モジュールの routes)
    # ---------------------------------------------------------------
    app.include_router(init_robot_routes(arm, hub))
    app.include_router(init_file_routes(files, hub))
    app.include_router(init_unity_routes(files, hub))
    app.include_router(init_debug_routes())

    # ---------------------------------------------------------------
    # WebSocket Endpoints
    # ---------------------------------------------------------------
    @app.websocket("/")
    async def ws_unity(ws: WebSocket):
        await ws.accept()
        hub.add("unity", ws)
        debug_log.info("unity", "Unity client connected")
        try:
            while True:
                raw = await ws.receive_text()
                try:
                    ev = parse_incoming(raw)
                    # イベント種別に応じて詳細ログを出す
                    if ev.event_id == "pc_debug_read_json_response":
                        ok = ev.payload.get("success", False)
                        err = ev.payload.get("error", "")
                        rel = ev.payload.get("relative_path", "")
                        content = ev.payload.get("content", "")
                        clen = len(content) if isinstance(content, str) else "?"
                        log.info(
                            "[Unity RX] %s | path=%s success=%s len=%s%s",
                            ev.event_id, rel, ok, clen,
                            f" error={err!r}" if err else "",
                        )
                    elif ev.event_id == "pc_debug_read_json_request":
                        rel = ev.payload.get("relative_path", "")
                        log.info(
                            "[Unity RX] %s | path=%s  ← フロントエンドから誤送信の可能性あり",
                            ev.event_id, rel,
                        )
                    else:
                        log.info("[Unity RX] %s", ev.event_id)
                    handle_unity_event(ev, files)
                    hub.resolve_pending(ev.event_id, ev.payload)

                    # Broadcast set_language to all unity clients (so Unity app receives it)
                    if ev.event_id == "set_language":
                        lang = ev.payload.get("language", "ja")
                        log.info("[Unity] Broadcasting set_language: %s", lang)
                        await hub.send_to("unity", "set_language", {"language": lang})
                except Exception as e:
                    log.warning("[Unity] parse error: %s", e)
        except WebSocketDisconnect:
            pass
        except asyncio.CancelledError:
            raise
        finally:
            hub.remove("unity", ws)
            debug_log.info("unity", "Unity client disconnected")

    @app.websocket("/spatial")
    async def ws_spatial(ws: WebSocket):
        await ws.accept()
        hub.add("spatial", ws)
        debug_log.info("spatial", "Spatial client connected")
        try:
            while True:
                raw = await ws.receive_text()
                log.info("[Spatial RX] %s", raw[:120])
        except WebSocketDisconnect:
            pass
        except asyncio.CancelledError:
            raise
        finally:
            hub.remove("spatial", ws)
            debug_log.info("spatial", "Spatial client disconnected")

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
        except asyncio.CancelledError:
            raise
        finally:
            hub.remove("status", ws)

    @app.websocket("/robot")
    async def ws_robot(ws: WebSocket):
        """ロボットリアルタイム制御チャンネル (Jog 等)。"""
        await ws.accept()
        hub.add("robot", ws)
        debug_log.info("robot", "Robot WS client connected")
        try:
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                    log.info("[Robot WS RX] %s", msg.get("type", "unknown"))
                    await dispatch_robot_ws(ws, msg, arm, hub)
                except json.JSONDecodeError as e:
                    log.warning("[Robot WS] JSON parse error: %s", e)
                except Exception as e:
                    log.warning("[Robot WS] error: %s", e)
        except WebSocketDisconnect:
            pass
        except asyncio.CancelledError:
            raise
        finally:
            hub.remove("robot", ws)
            # 安全措置: 切断時に jog ループを停止し Mode 0 に戻す
            await robot_ws_cleanup(ws, arm)
            debug_log.info("robot", "Robot WS client disconnected (jog stopped)")

    return app


# ===================================================================
# Main
# ===================================================================

_DEFAULT_ARM_IP = "192.168.1.199"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Unified Debug Server for InteractionApp / Unity / xArm"
    )
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--arm-ip", default=_DEFAULT_ARM_IP, help="xArm IP address")
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
        Path(args.save_dir).resolve()
        if args.save_dir
        else Path(__file__).resolve().parent / "saved_grids"
    )
    files = FileManager(save_dir)

    # 起動時: saved_grids の中身を表示
    log.info("  [saved_grids] grids: %s", files.list_grid_names() or "(none)")
    
    log.info("  [saved_grids] robots: %s", files.list_robot_names() or "(none)")
    try:
        name, data = files.load_grid()
        points = data if isinstance(data, list) else (data.get("gridPoints") or data.get("points") or [])
        n = len(points) if isinstance(points, list) else 0
        log.info("  [saved_grids] latest grid: %s (%d points)", name, n)
    except FileNotFoundError:
        log.info("  [saved_grids] latest grid: (none)")

    # xArm instance (本番 or mock)
    arm = create_arm(mock=args.mock, ip=args.arm_ip)

    hub = WSHub()
    app = create_app(arm, files, hub)

    mode = arm.status().get("mode", "unknown")
    log.info("=" * 60)
    log.info("  Unified Debug Server")
    log.info("  http://%s:%d", args.host, args.port)
    log.info("  WS  /         → Unity channel")
    log.info("  WS  /spatial  → Spatial pipeline channel")
    log.info("  WS  /status   → Status broadcast channel")
    log.info("  WS  /robot    → Robot realtime control channel (jog etc.)")
    log.info("  xArm mode: %s", mode)
    log.info("  Save dir: %s", save_dir.resolve())
    log.info("=" * 60)

    debug_log.info("server", f"Starting — mode={mode}, port={args.port}")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
