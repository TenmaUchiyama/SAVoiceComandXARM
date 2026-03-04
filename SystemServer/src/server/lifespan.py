"""
Application lifespan management.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from .config import robot, XARM_ENABLE, get_xarm_import_error
from .keyboard_monitor import keyboard_monitor_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown.
    
    On startup:
        - Connect to xArm robot if available
        - Start keyboard monitor loop
        
    On shutdown:
        - Disconnect from xArm robot
    """
    # Startup
    if robot is not None:
        try:
            ok, msg = robot.connect()
            if not ok:
                print(f"【Server】xArm 接続失敗のためロボット機能を無効化して起動します: {msg}")
        except Exception as e:
            print(f"【Server】xArm 接続例外のためロボット機能を無効化して起動します: {e!r}")
    else:
        if not XARM_ENABLE:
            print("【Server】環境変数 XARM_ENABLE=0 のためロボット機能は無効です")
        else:
            error = get_xarm_import_error()
            print(f"【Server】xArm SDK が見つからないためロボット機能は無効です: {error}")
    
    # Start keyboard monitor
    asyncio.create_task(keyboard_monitor_loop())
    
    yield
    
    # Shutdown
    if robot is not None:
        robot.disconnect()
