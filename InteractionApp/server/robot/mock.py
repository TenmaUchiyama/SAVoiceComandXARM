"""
robot.mock — SDK 不要のモック実装 (開発・UI テスト用)。

リアルアームと同じインターフェースを提供し、
全操作を成功レスポンスで返す。
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple

from debug import debug_log


class XArmMock:
    """SDK 不要のモックアーム。"""

    _JOG_AXIS_VEC = {
        "x":  (1, 0, 0),
        "-x": (-1, 0, 0),
        "y":  (0, 1, 0),
        "-y": (0, -1, 0),
        "z":  (0, 0, 1),
        "-z": (0, 0, -1),
    }

    def __init__(self):
        self._connected = False
        self._position = [300.0, 0.0, 200.0, 180.0, 0.0, 0.0]
        self._gripper = "open"
        self._manual_mode: bool = False
        # 4x4 デモグリッド
        self._grid_map: Dict[str, list] = {}
        for row in range(4):
            for col in range(4):
                self._grid_map[f"{col},{row}"] = [
                    210 + col * 100, -90 + row * 100, 180.0, 180.0, 0.0, 0.0
                ]
        debug_log.info("robot", "Mock arm initialized (4x4 demo grid)")

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> Tuple[bool, str]:
        self._connected = True
        debug_log.info("robot", "Mock connected")
        return True, "mock connected"

    def disconnect(self) -> Tuple[bool, str]:
        self._connected = False
        debug_log.info("robot", "Mock disconnected")
        return True, "mock disconnected"

    def home(self) -> Tuple[bool, str]:
        self._position = [300.0, 0.0, 200.0, 180.0, 0.0, 0.0]
        debug_log.info("robot", "Mock homed")
        return True, "mock homed"

    def initial(self) -> Tuple[bool, str]:
        self._position = [300.0, 0.0, 200.0, 180.0, 0.0, 0.0]
        debug_log.info("robot", "Mock initial position")
        return True, "mock initial position"

    def reset(self) -> Tuple[bool, str]:
        debug_log.info("robot", "Mock reset")
        return True, "mock reset"

    def gripper(self, action: str) -> Tuple[bool, str]:
        self._gripper = action
        debug_log.info("robot", f"Mock gripper {action}")
        return True, f"mock gripper {action}"

    def pick_at(self, x: Any, y: Any) -> Tuple[bool, str]:
        key = f"{x},{y}"
        if key not in self._grid_map:
            msg = f"Mock: coordinate ({x},{y}) not in grid"
            debug_log.error("robot", msg)
            return False, msg
        debug_log.step("robot", f"Mock pick at ({x},{y}) — simulating...")
        time.sleep(0.3)
        debug_log.info("robot", f"Mock pick at ({x},{y}) — complete")
        return True, f"mock pick at ({x},{y})"

    # ==== マニュアルモード ====

    def set_manual_mode(self, enabled: bool) -> Tuple[bool, str]:
        self._manual_mode = enabled
        debug_log.info("robot", f"Mock manual mode {'ON' if enabled else 'OFF'}")
        return True, f"mock manual mode {'ON' if enabled else 'OFF'}"

    # ==== Jog (ws_handlers の 30ms ループから呼ばれる) ====

    def jog_setup(self, axis: str) -> Tuple[bool, str]:
        """Mock: mode 切り替え不要。軸チェックのみ。"""
        if self._JOG_AXIS_VEC.get(axis.lower()) is None:
            return False, f"Unknown axis: {axis}"
        debug_log.info("robot", f"Mock jog setup: axis={axis}")
        return True, "mock servo mode (no-op)"

    def jog_step(self, axis: str, step_mm: float = 4.0) -> Tuple[bool, str]:
        """Mock: 1 ステップ分だけ位置を加算する。"""
        direction = self._JOG_AXIS_VEC.get(axis.lower())
        if direction is None:
            return False, f"Unknown axis: {axis}"
        self._position[0] += direction[0] * step_mm
        self._position[1] += direction[1] * step_mm
        self._position[2] += direction[2] * step_mm
        return True, "mock step ok"

    def jog_cleanup(self) -> Tuple[bool, str]:
        """Mock: mode 復元不要。"""
        debug_log.info("robot", f"Mock jog cleanup → {self._position[:3]}")
        return True, "mock jog cleanup (no-op)"

    # ==== 4x4 Grid Cell 移動 ====

    def grid_cells(self) -> List[Dict[str, Any]]:
        cells = []
        for key, pose in self._grid_map.items():
            parts = key.split(",")
            if len(parts) == 2:
                cells.append({
                    "key": key,
                    "col": int(parts[0]),
                    "row": int(parts[1]),
                    "pose": pose,
                })
        cells.sort(key=lambda c: (c["row"], c["col"]))
        return cells

    def move_to_cell(self, col: int, row: int) -> Tuple[bool, str]:
        key = f"{col},{row}"
        if key not in self._grid_map:
            msg = f"Mock: cell ({col},{row}) not in grid"
            debug_log.error("robot", msg)
            return False, msg
        pose = self._grid_map[key]
        self._position = list(pose)
        debug_log.info("robot", f"Mock moved to cell ({col},{row})")
        return True, f"mock moved to cell ({col},{row})"

    def reload_grid_map(self) -> Tuple[bool, str]:
        debug_log.info("robot", "Mock grid map reloaded")
        return True, "mock reloaded"

    def status(self) -> dict:
        return {
            "connected": self._connected,
            "mode": "mock",
            "state": 0 if self._connected else None,
            "position": list(self._position),
            "error_code": 0,
            "grid_cells_loaded": len(self._grid_map),
            "manual_mode": self._manual_mode,
        }
