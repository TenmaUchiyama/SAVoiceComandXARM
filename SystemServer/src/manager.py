"""
ConnectionManager - Backward compatibility module.

This module is deprecated. Use 'server.connection_manager' instead.
"""
# Re-export everything for backward compatibility
from server.connection_manager import manager, ConnectionManager
from server.keyboard_monitor import keyboard_monitor_loop
from server.routes.calibration import send_json_grid, send_robot_marker_config

__all__ = [
    "manager",
    "ConnectionManager",
    "keyboard_monitor_loop",
    "send_json_grid",
    "send_robot_marker_config",
]