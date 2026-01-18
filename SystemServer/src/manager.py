import asyncio
import json
import msvcrt
from fastapi import WebSocket
from utils import load_latest_grid_json, load_robot_marker_config

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        json_str = json.dumps(message)
        for connection in self.active_connections[:]:
            try:
                await connection.send_text(json_str)
            except:
                self.active_connections.remove(connection)

async def send_json_grid():
    latest = load_latest_grid_json()
    if latest and manager.active_connections:
        payload = {"type": "grid_config", "filename": latest["filename"], "gridPoints": latest["data"]}
        packet = {"eventId": "RestoreGridConfig", "payload": json.dumps(payload)}
        print("Sending latest grid config...")
        await manager.broadcast(packet)
        print(f"✅ Grid JSON送信: {latest['filename']}")
    else:
        print("No active connections to send the grid config.")


manager = ConnectionManager()

async def keyboard_monitor_loop():
    print("【操作方法】w / r / space / j(JSON送信)")
    while True:
        if msvcrt.kbhit():
            key_bytes = msvcrt.getch()

            # Extended keys (arrows, function keys, etc.) are a 2-byte sequence.
            # Swallow and ignore them to avoid decode errors.
            if key_bytes in (b"\x00", b"\xe0"):
                _ = msvcrt.getch()
                await asyncio.sleep(0.05)
                continue

            # For our command keys we only need ASCII.
            # Fall back to a tolerant decode for non-ASCII bytes.
            try:
                key = key_bytes.decode("ascii")
            except UnicodeDecodeError:
                key = key_bytes.decode("cp932", errors="ignore")

            key = key.lower()
            if not key:
                await asyncio.sleep(0.05)
                continue

            if key == " ":
                key = "space"

            if key == "j":
                latest = load_latest_grid_json()
                robot_marker = load_robot_marker_config()
                
                if manager.active_connections:
                    # Grid設定を送信
                    if latest:
                        payload = {"type": "grid_config", "filename": latest["filename"], "gridPoints": latest["data"]}
                        packet = {"eventId": "RestoreGridConfig", "payload": json.dumps(payload)}
                        await manager.broadcast(packet)
                        print(f"✅ Grid JSON送信: {latest['filename']}")
                    else:
                        print("⚠️ Grid設定が見つかりません")
                    
                    # ロボットマーカー設定を送信
                    if robot_marker:
                        payload = {"type": "robot_marker_config", "filename": robot_marker["filename"], "markerData": robot_marker["data"]}
                        packet = {"eventId": "RestoreRobotMarkerConfig", "payload": json.dumps(payload)}
                        await manager.broadcast(packet)
                        print(f"✅ Robot Marker JSON送信: {robot_marker['filename']}")
                    else:
                        print("⚠️ ロボットマーカー設定が見つかりません")
                else:
                    print("No active connections to send the config.")
            else:
                if manager.active_connections:

                    data = {"type": "key", "key": key}
                    packet = {"eventId": "KeyInput", "payload": json.dumps(data)}
                    await manager.broadcast(packet)
                    print(f"送信: {key}")
                else:
                    print("No active connections to send the key input.")
        await asyncio.sleep(0.05)