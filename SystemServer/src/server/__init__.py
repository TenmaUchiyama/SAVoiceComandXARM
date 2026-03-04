"""
Server package for spatial robot controller.
"""
from fastapi import FastAPI

from .lifespan import lifespan
from .routes import command_router, calibration_router
from .websocket_handler import websocket_endpoint
from .connection_manager import manager
from .config import robot, XARM_ENABLE, XARM_IP


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Integrated Spatial Robot Controller",
        lifespan=lifespan,
    )
    
    # Include routers
    app.include_router(command_router)
    app.include_router(calibration_router)
    
    # WebSocket endpoint
    app.websocket("/")(websocket_endpoint)
    
    return app


# Create default app instance
app = create_app()


__all__ = [
    "app",
    "create_app",
    "manager",
    "robot",
    "XARM_ENABLE",
    "XARM_IP",
]
