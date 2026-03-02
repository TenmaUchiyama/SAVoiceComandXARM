import argparse
import asyncio
import datetime as dt
import json
import uuid
from typing import Any, Dict, List, Optional, Set

import websockets


def now_iso() -> str:
    return dt.datetime.utcnow().isoformat() + "Z"


def ensure_dict_payload(payload: Any) -> Dict[str, Any]:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except Exception:
            return {"value": payload}
    return {"value": payload}


def parse_ws_packet(raw: str) -> Dict[str, Any]:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("packet must be json object")
    event_id = str(parsed.get("eventId", "")).strip()
    payload_obj = ensure_dict_payload(parsed.get("payload"))
    return {"eventId": event_id, "payload": payload_obj}


def encode_ws_packet(event_id: str, payload_obj: Dict[str, Any]) -> str:
    packet = {
        "eventId": event_id,
        "payload": json.dumps(payload_obj, ensure_ascii=False),
    }
    return json.dumps(packet, ensure_ascii=False)


def score_object(obj: Dict[str, Any], utterance: str) -> float:
    text = (utterance or "").lower()
    label = str(obj.get("label", "")).lower()
    color = str(obj.get("color", "")).lower()
    obj_id = str(obj.get("id", "")).lower()
    score = 0.2
    for token, bonus in [
        ("red", 0.25),
        ("青", 0.25),
        ("blue", 0.25),
        ("右", 0.2),
        ("left", 0.2),
        ("左", 0.2),
        ("front", 0.2),
        ("手前", 0.2),
        ("奥", 0.2),
    ]:
        if token in text and (token in label or token in color or token in obj_id):
            score += bonus
    return min(score, 0.99)


def select_candidate(request: Dict[str, Any], previous_target: Optional[str] = None) -> Dict[str, Any]:
    objects: List[Dict[str, Any]] = request.get("objects", []) or []
    utterance = ((request.get("utterance") or {}).get("text") or "")
    if not objects:
        return {
            "selected_object_id": "",
            "reasoning": "No objects in request",
            "candidates": [],
        }

    ranked = []
    for obj in objects:
        sc = score_object(obj, utterance)
        ranked.append(
            {
                "object_id": obj.get("id", ""),
                "score": round(sc, 3),
                "reason": f"matched label/color with utterance='{utterance}'",
            }
        )

    ranked.sort(key=lambda x: x["score"], reverse=True)
    selected = ranked[0]["object_id"] if ranked else ""

    if previous_target and selected == previous_target and len(ranked) > 1:
        selected = ranked[1]["object_id"]

    return {
        "selected_object_id": selected,
        "reasoning": "Simple heuristic pick for emulator",
        "candidates": ranked[:3],
    }


class UnityWSEmulator:
    def __init__(self, host: str, port: int, robot_delay_sec: float):
        self.host = host
        self.port = port
        self.robot_delay_sec = robot_delay_sec
        self.clients: Set[Any] = set()

    async def send_event(self, ws: Any, event_id: str, payload: Dict[str, Any]) -> None:
        await ws.send(encode_ws_packet(event_id, payload))
        print(f"[TX] {event_id}: {json.dumps(payload, ensure_ascii=False)}")

    async def broadcast_event(self, event_id: str, payload: Dict[str, Any]) -> None:
        if not self.clients:
            print("[INFO] No connected clients")
            return
        message = encode_ws_packet(event_id, payload)
        await asyncio.gather(*(client.send(message) for client in list(self.clients)), return_exceptions=True)
        print(f"[BROADCAST] {event_id}: {json.dumps(payload, ensure_ascii=False)}")

    async def handle_spatial_reference_request(self, ws: Any, req: Dict[str, Any]) -> None:
        selected = select_candidate(req)
        result = {
            "type": "spatial_reference_result",
            "request_id": req.get("request_id", str(uuid.uuid4())),
            "selected_object_id": selected["selected_object_id"],
            "reasoning": selected["reasoning"],
            "candidates": selected["candidates"],
        }
        await self.send_event(ws, "spatial_reference_result", result)

    async def handle_refinement_request(self, ws: Any, req: Dict[str, Any]) -> None:
        selected = select_candidate(req, previous_target=req.get("previous_target"))
        result = {
            "type": "spatial_reference_result",
            "request_id": req.get("request_id", str(uuid.uuid4())),
            "selected_object_id": selected["selected_object_id"],
            "reasoning": "Refinement processed by emulator",
            "candidates": selected["candidates"],
        }
        await self.send_event(ws, "spatial_reference_result", result)

    async def handle_confirmation(self, ws: Any, req: Dict[str, Any]) -> None:
        request_id = req.get("request_id", str(uuid.uuid4()))
        object_id = req.get("confirmed_object_id", "")
        running = {
            "type": "robot_command",
            "request_id": request_id,
            "object_id": object_id,
            "command": req.get("action", "pick"),
            "status": "running",
            "target_position": {"x": 0.25, "y": 0.0, "z": 0.12},
        }
        await self.send_event(ws, "robot_command", running)
        await asyncio.sleep(self.robot_delay_sec)
        done = dict(running)
        done["status"] = "done"
        await self.send_event(ws, "robot_command", done)

    async def handle_xarm_pick(self, ws: Any, req: Dict[str, Any]) -> None:
        x = req.get("x", "?")
        y = req.get("y", "?")
        await self.send_event(ws, "ServerReply", {"text": f"XarmPick received ({x}, {y}) @ {now_iso()}"})

    async def route(self, ws: Any, event_id: str, payload: Dict[str, Any]) -> None:
        if event_id == "spatial_reference_request":
            await self.handle_spatial_reference_request(ws, payload)
            return
        if event_id == "refinement_request":
            await self.handle_refinement_request(ws, payload)
            return
        if event_id == "confirmation":
            await self.handle_confirmation(ws, payload)
            return
        if event_id == "XarmPick":
            await self.handle_xarm_pick(ws, payload)
            return
        if event_id == "TestChat":
            text = str(payload.get("text", ""))
            await self.send_event(ws, "ServerReply", {"text": f"Echo: {text}"})
            return

        await self.send_event(
            ws,
            "server_error",
            {
                "type": "server_error",
                "request_id": payload.get("request_id", ""),
                "code": "UNSUPPORTED_EVENT",
                "message": f"Unsupported eventId: {event_id}",
            },
        )

    async def handle_client(self, ws: Any) -> None:
        self.clients.add(ws)
        print(f"[OPEN] client connected. total={len(self.clients)}")
        try:
            async for raw in ws:
                try:
                    packet = parse_ws_packet(raw)
                    event_id = packet["eventId"]
                    payload = packet["payload"]
                    print(f"[RX] {event_id}: {json.dumps(payload, ensure_ascii=False)}")
                    await self.route(ws, event_id, payload)
                except Exception as exc:
                    print(f"[WARN] invalid packet: {exc}")
                    await self.send_event(
                        ws,
                        "server_error",
                        {
                            "type": "server_error",
                            "request_id": "",
                            "code": "BAD_PACKET",
                            "message": str(exc),
                        },
                    )
        finally:
            self.clients.discard(ws)
            print(f"[CLOSE] client disconnected. total={len(self.clients)}")

    async def cli_loop(self) -> None:
        loop = asyncio.get_running_loop()
        help_text = (
            "commands: ping [text], key <k>, error <msg>, result <object_id>, quit"
        )
        print(help_text)
        while True:
            line = await loop.run_in_executor(None, input, "emu> ")
            parts = line.strip().split(maxsplit=1)
            if not parts:
                continue
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd in {"quit", "exit"}:
                break
            if cmd == "ping":
                text = arg if arg else f"tick {now_iso()}"
                await self.broadcast_event("Ping", {"text": text})
                continue
            if cmd == "key":
                key = arg if arg else "space"
                await self.broadcast_event("KeyInput", {"type": "keydown", "key": key})
                continue
            if cmd == "error":
                msg = arg if arg else "manual error"
                await self.broadcast_event(
                    "server_error",
                    {"type": "server_error", "request_id": "", "code": "MANUAL", "message": msg},
                )
                continue
            if cmd == "result":
                object_id = arg if arg else "obj_dummy"
                await self.broadcast_event(
                    "spatial_reference_result",
                    {
                        "type": "spatial_reference_result",
                        "request_id": str(uuid.uuid4()),
                        "selected_object_id": object_id,
                        "reasoning": "manual result",
                        "candidates": [{"object_id": object_id, "score": 0.99, "reason": "manual"}],
                    },
                )
                continue

            print(help_text)

    async def run(self, interactive: bool) -> None:
        print(f"[START] ws://{self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            if interactive:
                await self.cli_loop()
            else:
                await asyncio.Future()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unity WebSocket server emulator (single file)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--robot-delay", type=float, default=1.0)
    parser.add_argument("--no-cli", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    emu = UnityWSEmulator(host=args.host, port=args.port, robot_delay_sec=args.robot_delay)
    asyncio.run(emu.run(interactive=not args.no_cli))


if __name__ == "__main__":
    main()
