import argparse
import asyncio
import datetime
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import websockets


LIST_REQ = "pc_debug_persistent_list_request"
LIST_RES = "pc_debug_persistent_list_response"
READ_REQ = "pc_debug_read_json_request"
READ_RES = "pc_debug_read_json_response"
KEY_INPUT_EVENT = "KeyInput"
RESTORE_GRID_EVENT = "RestoreGridConfig"
SAVE_GRID_EVENT = "SaveGridConfig"


def ensure_dict(value: Any) -> Dict[str, Any]:
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
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Incoming packet must be a JSON object")

    legacy_event = str(data.get("eventId", "")).strip()
    if legacy_event:
        payload_raw = decode_json_value(data.get("payload"))
        return IncomingEvent(event_id=legacy_event, payload=ensure_dict(payload_raw), payload_raw=payload_raw)

    raw_event = str(data.get("type", "")).strip()
    if not raw_event:
        raise ValueError("Incoming packet missing eventId/type")
    return IncomingEvent(event_id=raw_event, payload=data, payload_raw=data)


def encode_raw_event(event_id: str, payload: Dict[str, Any]) -> str:
    packet = dict(payload)
    packet["type"] = event_id
    return json.dumps(packet, ensure_ascii=False)


class PCDebugWsCliServer:
    def __init__(self, host: str, port: int, save_dir: Path):
        self.host = host
        self.port = port
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.client: Optional[Any] = None
        self.pending: Dict[str, asyncio.Future] = {}

    def has_client(self) -> bool:
        return self.client is not None

    async def send_event(self, event_id: str, payload: Dict[str, Any]) -> None:
        if not self.client:
            raise RuntimeError("No Unity client connected")
        message = encode_raw_event(event_id, payload)
        await self.client.send(message)
        print(f"[TX] {event_id}: {json.dumps(payload, ensure_ascii=False)}")

    async def send_legacy_event(self, event_id: str, payload: Dict[str, Any]) -> None:
        if not self.client:
            raise RuntimeError("No Unity client connected")
        packet = {
            "eventId": event_id,
            "payload": json.dumps(payload, ensure_ascii=False),
        }
        await self.client.send(json.dumps(packet, ensure_ascii=False))
        print(f"[TX-LEGACY] {event_id}: {json.dumps(payload, ensure_ascii=False)}")

    def list_saved_grids(self) -> List[Path]:
        return sorted(
            self.save_dir.glob("qr_grid_config_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    def save_grid_json(self, grid_data: Any) -> Path:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = self.save_dir / f"qr_grid_config_{timestamp}.json"
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(grid_data, f, indent=2, ensure_ascii=False)
        return save_path

    def load_saved_grid(self, name: Optional[str] = None) -> Tuple[str, Any]:
        target: Optional[Path] = None
        if name:
            candidate = self.save_dir / name
            if not candidate.exists():
                raise FileNotFoundError(f"Grid file not found: {candidate}")
            target = candidate
        else:
            files = self.list_saved_grids()
            if not files:
                raise FileNotFoundError(f"No saved grid JSON found in: {self.save_dir}")
            target = files[0]

        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        return target.name, data

    async def send_key(self, key: str) -> None:
        normalized = "space" if key == " " else key
        await self.send_legacy_event(KEY_INPUT_EVENT, {"type": "key", "key": normalized})

    async def restore_grid(self, name: Optional[str] = None) -> None:
        filename, grid_data = self.load_saved_grid(name)
        payload = {
            "type": "grid_config",
            "filename": filename,
            "gridPoints": grid_data,
        }
        await self.send_legacy_event(RESTORE_GRID_EVENT, payload)
        print(f"[INFO] Restored grid sent: {filename}")

    def handle_save_grid_event(self, payload_raw: Any) -> None:
        if payload_raw is None or payload_raw == "":
            print("[WARN] SaveGridConfig payload is empty")
            return

        grid_data = payload_raw
        if isinstance(grid_data, dict) and "value" in grid_data and len(grid_data) == 1:
            grid_data = grid_data["value"]

        save_path = self.save_grid_json(grid_data)
        count = len(grid_data) if isinstance(grid_data, list) else "unknown"
        print(f"[SAVE] Grid config saved: {save_path} (points={count})")

    async def request(self, req_event: str, res_event: str, payload: Dict[str, Any], timeout_sec: float = 10.0) -> Dict[str, Any]:
        request_id = str(payload.get("request_id") or uuid.uuid4())
        payload = dict(payload)
        payload["request_id"] = request_id

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        key = f"{res_event}:{request_id}"
        self.pending[key] = future

        try:
            await self.send_event(req_event, payload)
            result = await asyncio.wait_for(future, timeout=timeout_sec)
            return result
        finally:
            self.pending.pop(key, None)

    async def handle_client(self, websocket: Any) -> None:
        self.client = websocket
        print("[OPEN] Unity client connected")

        try:
            async for raw in websocket:
                try:
                    incoming = parse_incoming(raw)
                    payload = incoming.payload
                    payload_raw = incoming.payload_raw
                    event_id = incoming.event_id
                    print(f"[RX] {event_id}: {json.dumps(payload_raw, ensure_ascii=False)}")

                    if event_id == SAVE_GRID_EVENT:
                        self.handle_save_grid_event(payload_raw)

                    request_id = str(payload.get("request_id", "")).strip()
                    if request_id:
                        key = f"{event_id}:{request_id}"
                        future = self.pending.get(key)
                        if future and not future.done():
                            future.set_result(payload)
                except Exception as exc:
                    print(f"[WARN] failed to parse packet: {exc}")
        finally:
            if self.client is websocket:
                self.client = None
            for future in list(self.pending.values()):
                if not future.done():
                    future.set_exception(RuntimeError("Unity client disconnected"))
            self.pending.clear()
            print("[CLOSE] Unity client disconnected")

    async def cli_loop(self) -> None:
        loop = asyncio.get_running_loop()
        help_text = (
            "commands:\n"
            "  wait                          : wait for Unity connection\n"
            "  list [recursive]              : list Application.persistentDataPath\n"
            "  read <relative_path.json>     : read JSON file content\n"
            "  key <w|r|space|...>           : send legacy KeyInput event\n"
            "  restore [saved_file.json]     : send RestoreGridConfig from local save_dir\n"
            "  grids [limit]                 : list saved local grid files\n"
            "  legacy <event> <json_object>  : send legacy eventId/payload packet\n"
            "  raw <event> <json_object>     : send raw event for debug\n"
            "  help                          : show this help\n"
            "  quit                          : exit"
        )
        print(help_text)

        while True:
            line = await loop.run_in_executor(None, input, "pcdbg> ")
            text = line.strip()
            if not text:
                continue

            parts = text.split(maxsplit=2)
            cmd = parts[0].lower()

            if cmd in {"quit", "exit"}:
                break

            if cmd == "help":
                print(help_text)
                continue

            if cmd == "grids":
                limit = 10
                if len(parts) > 1:
                    try:
                        limit = max(1, int(parts[1]))
                    except Exception:
                        print("[ERR] grids limit must be integer")
                        continue
                files = self.list_saved_grids()
                if not files:
                    print(f"[INFO] No saved grids in: {self.save_dir}")
                    continue
                print(f"[INFO] saved grids ({min(limit, len(files))}/{len(files)}):")
                for file_path in files[:limit]:
                    print(f"  - {file_path.name}")
                continue

            if cmd == "wait":
                if self.has_client():
                    print("[INFO] Unity is already connected")
                else:
                    print("[INFO] Waiting for Unity connection...")
                while not self.has_client():
                    await asyncio.sleep(0.2)
                print("[INFO] Unity connected")
                continue

            if not self.has_client():
                print("[ERR] Unity is not connected. Run 'wait' first.")
                continue

            if cmd == "list":
                recursive = len(parts) > 1 and parts[1].lower() in {"1", "true", "yes", "recursive"}
                try:
                    result = await self.request(
                        LIST_REQ,
                        LIST_RES,
                        {"recursive": recursive},
                    )
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                except Exception as exc:
                    print(f"[ERR] list failed: {exc}")
                continue

            if cmd == "key":
                if len(parts) < 2:
                    print("usage: key <w|r|space|...>")
                    continue
                key_value = parts[1]
                if key_value.lower() == "space":
                    key_value = " "
                try:
                    await self.send_key(key_value)
                except Exception as exc:
                    print(f"[ERR] key failed: {exc}")
                continue

            if cmd in {"restore", "j"}:
                target_name = parts[1] if len(parts) > 1 else None
                try:
                    await self.restore_grid(target_name)
                except Exception as exc:
                    print(f"[ERR] restore failed: {exc}")
                continue

            if cmd == "legacy":
                if len(parts) < 3:
                    print("usage: legacy <event> <json_object>")
                    continue
                event_id = parts[1]
                try:
                    payload = json.loads(parts[2])
                    if not isinstance(payload, dict):
                        raise ValueError("payload must be JSON object")
                    await self.send_legacy_event(event_id, payload)
                except Exception as exc:
                    print(f"[ERR] legacy failed: {exc}")
                continue

            if cmd == "read":
                if len(parts) < 2:
                    print("usage: read <relative_path.json>")
                    continue
                rel_path = parts[1]
                try:
                    result = await self.request(
                        READ_REQ,
                        READ_RES,
                        {"relative_path": rel_path},
                    )
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                except Exception as exc:
                    print(f"[ERR] read failed: {exc}")
                continue

            if cmd == "raw":
                if len(parts) < 3:
                    print("usage: raw <event> <json_object>")
                    continue
                event_id = parts[1]
                try:
                    payload = json.loads(parts[2])
                    if not isinstance(payload, dict):
                        raise ValueError("payload must be JSON object")
                    await self.send_event(event_id, payload)
                except Exception as exc:
                    print(f"[ERR] raw failed: {exc}")
                continue

            print("[ERR] unknown command. run 'help'.")

    async def run(self) -> None:
        print(f"[START] ws://{self.host}:{self.port} (path is accepted as-is, e.g. /spatial)")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await self.cli_loop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PC debugger WebSocket CLI for Unity/HoloLens")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--save-dir", default="saved_grids", help="Directory for local grid JSON save/load")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = PCDebugWsCliServer(args.host, args.port, Path(args.save_dir))
    asyncio.run(app.run())


if __name__ == "__main__":
    main()
