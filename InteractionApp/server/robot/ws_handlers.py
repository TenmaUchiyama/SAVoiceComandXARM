"""
robot.ws_handlers — ロボット制御 WebSocket コマンドハンドラー。

keyboard_move.py と同じ方式:
  jog_start → Mode 1 (サーボモード) に切り替え + 30ms ループ開始
  jog_stop  → ループ停止 + Mode 0 (位置制御) に復元

新しい WS コマンドを追加する方法:
  @ws_command("your_command")
  async def handle_your_command(ws, msg, arm, hub):
      ...
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Dict

from fastapi import WebSocket

log = logging.getLogger("unified_debug")

# ハンドラーの型
WsCommandHandler = Callable[
    [WebSocket, Dict[str, Any], Any, Any],
    Awaitable[None],
]

# コマンド名 → ハンドラーのディスパッチテーブル
_HANDLERS: Dict[str, WsCommandHandler] = {}

# WS ごとに動いている jog ループタスク
_jog_tasks: Dict[int, asyncio.Task] = {}  # id(ws) → Task


def ws_command(name: str):
    """デコレーターでコマンドをディスパッチテーブルに登録する。"""

    def decorator(fn: WsCommandHandler) -> WsCommandHandler:
        _HANDLERS[name] = fn
        return fn

    return decorator


async def dispatch(ws: WebSocket, msg: Dict[str, Any], arm, hub) -> None:
    """受信メッセージをコマンド種別でディスパッチする。"""
    cmd_type = msg.get("type", "")
    handler = _HANDLERS.get(cmd_type)
    if handler is None:
        await _send(ws, {"type": "error", "message": f"Unknown command: {cmd_type}"})
        return
    try:
        await handler(ws, msg, arm, hub)
    except Exception as e:
        log.exception("[Robot WS] handler error for %s: %s", cmd_type, e)
        await _send(ws, {"type": "error", "message": str(e)})


async def cleanup_on_disconnect(ws: WebSocket, arm) -> None:
    """WS 切断時に jog ループを停止しマニュアルモードも解除する。"""
    await _stop_jog(ws, arm)
    # 切断時はマニュアルモードも必ず解除 (Mode 0 に戻す)
    try:
        if getattr(arm, "_manual_mode", False):
            await asyncio.to_thread(arm.set_manual_mode, False)
    except Exception:
        pass


async def _send(ws: WebSocket, data: dict) -> None:
    try:
        await ws.send_text(json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


async def _stop_jog(ws: WebSocket, arm) -> None:
    """実行中の jog ループを停止し、Mode 0 に戻す。"""
    task = _jog_tasks.pop(id(ws), None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    try:
        # jog_cleanup は SDK 呼び出しなのでスレッドで実行
        await asyncio.to_thread(arm.jog_cleanup)
    except Exception:
        pass


# ===================================================================
# コマンドハンドラー
# ===================================================================

# keyboard_move.py の STEP_MM / LOOP_DT と同じデフォルト値
_DEFAULT_STEP_MM = 4.0
_DEFAULT_LOOP_DT = 0.03  # 30ms


@ws_command("jog_start")
async def handle_jog_start(ws: WebSocket, msg: Dict[str, Any], arm, hub) -> None:
    """サーボモード jog 開始。ボタン押し下げ時に呼ぶ。

    受信: { type: "jog_start", axis: "x"|"-x"|"y"|"-y"|"z"|"-z",
            step_mm?: number, loop_dt?: number }
    返信: { type: "jog_started", success: bool, message: str }
    """
    axis = msg.get("axis", "")
    step_mm = float(msg.get("step_mm", _DEFAULT_STEP_MM))
    loop_dt = float(msg.get("loop_dt", _DEFAULT_LOOP_DT))

    if not axis:
        await _send(ws, {
            "type": "jog_started",
            "success": False,
            "message": "axis required (x,-x,y,-y,z,-z)",
        })
        return

    # 既存ループがあれば先に止める
    await _stop_jog(ws, arm)

    # jog_setup は SDK 呼び出し (ブロッキング) なのでスレッドで実行
    ok, message = await asyncio.to_thread(arm.jog_setup, axis)
    if not ok:
        await _send(ws, {"type": "jog_started", "success": False, "message": message})
        return

    await _send(ws, {"type": "jog_started", "success": True, "message": message})

    # 30ms ループを非同期タスクとして起動
    # arm.jog_step() はブロッキング (SDK network call) なので to_thread で実行し
    # イベントループをフリーズさせない
    async def _loop():
        try:
            while True:
                await asyncio.to_thread(arm.jog_step, axis, step_mm)
                await asyncio.sleep(loop_dt)
        except asyncio.CancelledError:
            pass

    _jog_tasks[id(ws)] = asyncio.create_task(_loop())


@ws_command("jog_stop")
async def handle_jog_stop(ws: WebSocket, msg: Dict[str, Any], arm, hub) -> None:
    """サーボモード jog 停止。ボタン離し時に呼ぶ。

    受信: { type: "jog_stop" }
    返信: { type: "jog_stopped", success: bool, position?: number[] }
    """
    await _stop_jog(ws, arm)

    status = await asyncio.to_thread(arm.status)
    await _send(ws, {
        "type": "jog_stopped",
        "success": True,
        "position": status.get("position"),
    })

    # 全 status クライアントに最終位置をブロードキャスト
    await hub.broadcast_status(status)
