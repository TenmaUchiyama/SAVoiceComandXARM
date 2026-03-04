"""
Keyboard monitor for development/debugging.
"""
import asyncio
import json
import msvcrt

from .connection_manager import manager
from utils import load_latest_grid_json, load_robot_marker_config


async def keyboard_monitor_loop():
    """
    Monitor keyboard input for development commands.
    
    Keys:
        j - Send grid and robot marker config to Unity
        space/w/r - Send key events to Unity
    """
    print("【操作方法】w / r / space / j(JSON送信)")
    
    while True:
        if msvcrt.kbhit():
            key_bytes = msvcrt.getch()

            # Handle extended keys (arrows, function keys)
            if key_bytes in (b"\x00", b"\xe0"):
                _ = msvcrt.getch()
                await asyncio.sleep(0.05)
                continue

            # Decode key
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

            # Handle JSON send command
            if key == "j":
                await _handle_json_send()
            else:
                await _handle_key_input(key)
                
        await asyncio.sleep(0.05)


async def _handle_json_send():
    """Send grid and robot marker config to Unity."""
    latest = load_latest_grid_json()
    robot_marker = load_robot_marker_config()
    
    if not manager.has_connections:
        print("No active connections to send the config.")
        return
    
    # Send grid config
    if latest:
        payload = {
            "type": "grid_config",
            "filename": latest["filename"],
            "gridPoints": latest["data"],
        }
        packet = {"eventId": "RestoreGridConfig", "payload": json.dumps(payload)}
        await manager.broadcast(packet)
        print(f"✅ Grid JSON送信: {latest['filename']}")
    else:
        print("⚠️ Grid設定が見つかりません")
    
    # Send robot marker config
    if robot_marker:
        payload = {
            "type": "robot_marker_config",
            "filename": robot_marker["filename"],
            "markerData": robot_marker["data"],
        }
        packet = {"eventId": "RestoreRobotMarkerConfig", "payload": json.dumps(payload)}
        await manager.broadcast(packet)
        print(f"✅ Robot Marker JSON送信: {robot_marker['filename']}")
    else:
        print("⚠️ ロボットマーカー設定が見つかりません")


async def _handle_key_input(key: str):
    """Send key input to Unity."""
    if not manager.has_connections:
        print("No active connections to send the key input.")
        return
    
    data = {"type": "key", "key": key}
    packet = {"eventId": "KeyInput", "payload": json.dumps(data)}
    await manager.broadcast(packet)
    print(f"送信: {key}")
