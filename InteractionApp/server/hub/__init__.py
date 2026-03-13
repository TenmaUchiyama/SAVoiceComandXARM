"""
hub — WebSocket 接続管理 + イベントヘルパー。

WSHub: Unity / Spatial / Status チャンネルの接続管理と
       request-response パターンをサポートする WebSocket ハブ。

イベント定数・パーサー・エンコーダーもここに集約。
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Set

from fastapi import WebSocket
from loguru import logger

# loguru は debug モジュールですでに初期化されている想定
log = logger.bind(source="HUB")


# ===================================================================
# Event constants
# ===================================================================
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


# ===================================================================
# Payload helpers
# ===================================================================

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
# WSHub — WebSocket 接続管理
# ===================================================================

class WSHub:
    """WebSocket 接続管理 (Unity, Spatial, Status)。"""

    def __init__(self):
        self.unity: Set[WebSocket] = set()
        self.spatial: Set[WebSocket] = set()
        self.status: Set[WebSocket] = set()
        self.robot: Set[WebSocket] = set()
        self.pending: Dict[str, asyncio.Future] = {}

    # --- connection management ---
    def add(self, channel: str, ws: WebSocket):
        self._ch(channel).add(ws)
        log.info(f"WS [{channel}] +1 (total={len(self._ch(channel))})")

    def remove(self, channel: str, ws: WebSocket):
        self._ch(channel).discard(ws)
        log.info(f"WS [{channel}] -1 (total={len(self._ch(channel))})")

    def _ch(self, channel: str) -> Set[WebSocket]:
        return {
            "unity": self.unity,
            "spatial": self.spatial,
            "status": self.status,
            "robot": self.robot,
        }[channel]

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

    async def broadcast_debug(self, message: str):
        """デバッグログを status チャンネルにブロードキャスト。"""
        await self.broadcast("status", message)

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
