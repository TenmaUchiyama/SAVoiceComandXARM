"""
Calibration and grid config endpoints.
"""
import json
from fastapi import APIRouter

from utils import save_grid_to_file, load_latest_grid_json, load_robot_marker_config
from server.connection_manager import manager


router = APIRouter()


@router.post("/save_grid_config")
async def save_grid_api(payload: dict):
    """Save grid configuration from Unity."""
    filename = save_grid_to_file(payload)
    return {"status": "ok", "filename": filename}


@router.get("/calibration")
async def calibration_api():
    """Send calibration data to all connected Unity clients."""
    await send_json_grid()
    await send_robot_marker_config()
    return {"status": "ok"}


async def send_json_grid():
    """Send grid config to all connected Unity clients."""
    latest = load_latest_grid_json()
    if latest and manager.has_connections:
        payload = {
            "type": "grid_config",
            "filename": latest["filename"],
            "gridPoints": latest["data"],
        }
        packet = {"eventId": "RestoreGridConfig", "payload": json.dumps(payload)}
        print("Sending latest grid config...")
        await manager.broadcast(packet)
        print(f"✅ Grid JSON送信: {latest['filename']}")
    else:
        print("No active connections to send the grid config.")


async def send_robot_marker_config():
    """Send robot marker config to all connected Unity clients."""
    latest = load_robot_marker_config()
    if latest and manager.has_connections:
        payload = {
            "type": "robot_marker_config",
            "filename": latest["filename"],
            "markerData": latest["data"],
        }
        packet = {"eventId": "RestoreRobotConfig", "payload": json.dumps(payload)}
        print("Sending robot marker config...")
        await manager.broadcast(packet)
        print(f"✅ Robot Marker JSON送信: {latest['filename']}")
    else:
        print("No active connections to send the robot marker config.")
