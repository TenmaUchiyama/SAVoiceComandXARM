"""
Routes package for server endpoints.
"""
from .command import router as command_router
from .calibration import router as calibration_router

__all__ = ["command_router", "calibration_router"]
