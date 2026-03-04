"""
WebSocket endpoint handler for Unity communication.
"""
import asyncio
import json

from fastapi import WebSocket, WebSocketDisconnect

from utils import save_grid_to_file, save_robot_marker_config
from .connection_manager import manager
from .config import robot


async def websocket_endpoint(websocket: WebSocket):
    """
    Handle WebSocket connections from Unity.
    
    Events handled:
        - SaveGridConfig: Save grid configuration
        - SaveRobotConfig: Save robot marker configuration
        - XarmPick: Execute robot pick action
    """
    await manager.connect(websocket)
    print("【Server】Unity接続完了")
    
    try:
        while True:
            # Receive message with timeout
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send keepalive to maintain connection
                await websocket.send_text(json.dumps({
                    "eventId": "KeepAlive",
                    "payload": "{}",
                }))
                continue

            message = json.loads(data)
            event_id = message.get("eventId")
            
            if event_id == "SaveGridConfig":
                await _handle_save_grid_config(websocket, message)
            
            elif event_id == "SaveRobotConfig":
                await _handle_save_robot_config(websocket, message)
            
            elif event_id == "XarmPick":
                await _handle_xarm_pick(websocket, message)

    except WebSocketDisconnect as e:
        manager.disconnect(websocket)
        print(f"【Server】Unity切断 code={getattr(e, 'code', None)}")
    except Exception as e:
        print(f"【Server】エラー: {e!r}")
        manager.disconnect(websocket)


async def _handle_save_grid_config(websocket: WebSocket, message: dict):
    """Handle SaveGridConfig event."""
    grid_data = json.loads(message.get("payload", "{}"))
    filename = save_grid_to_file(grid_data)
    
    response = {
        "eventId": "SaveGridConfigResult",
        "payload": json.dumps({"status": "success", "filename": filename}),
    }
    await websocket.send_text(json.dumps(response))


async def _handle_save_robot_config(websocket: WebSocket, message: dict):
    """Handle SaveRobotConfig event."""
    marker_data = json.loads(message.get("payload", "{}"))
    filename = save_robot_marker_config(marker_data)
    
    response = {
        "eventId": "SaveRobotMarkerConfigResult",
        "payload": json.dumps({"status": "success", "filename": filename}),
    }
    await websocket.send_text(json.dumps(response))
    print(f"【Server】ロボットマーカー設定を保存しました: {filename}")


async def _handle_xarm_pick(websocket: WebSocket, message: dict):
    """Handle XarmPick event."""
    payload = json.loads(message.get("payload", "{}"))
    x = payload.get("x")
    y = payload.get("y")

    if robot is not None:
        result = robot.pick_at(x, y)
    else:
        result = json.dumps({"status": "error", "message": "Robot not available"})

    await websocket.send_text(json.dumps({
        "eventId": "XarmPickResult",
        "payload": result,
    }))
