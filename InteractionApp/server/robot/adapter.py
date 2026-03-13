"""
robot.adapter — 本番 XArmOperator をラップしたアダプター。

SystemServer/src/XARmOperator.py の XArmOperator を import して使う。
追加機能: jog (相対移動), grid_cells (4x4 マップ), move_to_cell。
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from debug import debug_log

# loguru は debug モジュールですでに初期化されている想定
log = logger.bind(source="ROBOT-ADPT")

# ---------------------------------------------------------------------------
# 本番モジュールのパスを追加
# ---------------------------------------------------------------------------
_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # SAVoiceComandXARM
_SYSSERVER_SRC = _WORKSPACE_ROOT / "SystemServer" / "src"
_XARM_DIR = _WORKSPACE_ROOT / "XArm"

sys.path.insert(0, str(_SYSSERVER_SRC))
sys.path.insert(0, str(_XARM_DIR))

# ---------------------------------------------------------------------------
# 本番 import
# ---------------------------------------------------------------------------
try:
    from XARmOperator import XArmOperator  # SystemServer/src/XARmOperator.py
    HAS_OPERATOR = True
except ImportError:
    HAS_OPERATOR = False
    XArmOperator = None  # type: ignore

try:
    from pick_from_grid import (
        ARM_IP,
        GRIP_OPEN,
        GRIP_CLOSE,
    )
except ImportError:
    ARM_IP = "192.168.1.199"
    GRIP_OPEN = 850
    GRIP_CLOSE = 350

# デフォルトの grid_pose_map.json / place_pose_map.json
_DEFAULT_GRID_JSON = str(_XARM_DIR / "grid_pose_map.json")
_DEFAULT_PLACE_JSON = str(_XARM_DIR / "place_pose_map.json")


class XArmAdapter:
    """本番 XArmOperator をラップし、サーバー用 I/F を提供。

    XArmOperator はコンストラクタで即接続しないため、
    connect() 呼び出し時に初めて接続する。
    """

    def __init__(self, ip: str = ARM_IP, grid_json: str = _DEFAULT_GRID_JSON, place_json: str = _DEFAULT_PLACE_JSON):
        if not HAS_OPERATOR:
            raise ImportError(
                "XArmOperator が import できません。"
                " SystemServer/src/XARmOperator.py を確認してください。"
            )
        self._ip = ip
        self._grid_json = grid_json
        self._place_json = place_json
        self._op: Optional[XArmOperator] = None
        self._manual_mode: bool = False
        # 4x4 grid pose map (別途ロード)
        self._grid_map: Dict[str, list] = {}
        self._load_grid_map()
        # place pose map
        self._place_map: Dict[str, list] = {}
        self._load_place_map()

    # ==== 接続 ====

    @property
    def connected(self) -> bool:
        return self._op is not None and self._op.connected

    def connect(self) -> Tuple[bool, str]:
        if self._op is not None and self._op.connected:
            debug_log.info("robot", "Already connected")
            return True, "already connected"
        try:
            self._op = XArmOperator(ip=self._ip, json_file=self._grid_json)
            ok, msg = self._op.connect()
            if ok:
                debug_log.info("robot", f"Connected to {self._ip}")
            else:
                debug_log.error("robot", f"Connection failed: {msg}")
                self._op = None
            return ok, msg
        except Exception as e:
            debug_log.error("robot", f"Connection exception: {e}")
            self._op = None
            return False, str(e)

    def disconnect(self) -> Tuple[bool, str]:
        if self._op is None:
            return True, "not connected"
        try:
            self._op.disconnect()
            debug_log.info("robot", "Disconnected")
        except Exception:
            pass
        self._op = None
        return True, "disconnected"

    # ==== 基本操作 ====

    def home(self) -> Tuple[bool, str]:
        if not self._ensure():
            return False, "not connected"
        try:
            ok = self._op.home()  # type: ignore
            msg = "homed" if ok else "home failed"
            debug_log.info("robot", msg)
            return ok, msg
        except Exception as e:
            debug_log.error("robot", f"Home error: {e}")
            return False, str(e)

    def initial(self) -> Tuple[bool, str]:
        """初期位置（ジョイント角度）へ移動。"""
        if not self._ensure():
            return False, "not connected"
        try:
            ok, msg = self._op.go_to_initial_pos()  # type: ignore
            debug_log.info("robot", f"Initial position: {msg}")
            return ok, msg
        except Exception as e:
            debug_log.error("robot", f"Initial position error: {e}")
            return False, str(e)

    def reset(self) -> Tuple[bool, str]:
        if not self._ensure():
            return False, "not connected"
        try:
            ok, msg = self._op.reset()  # type: ignore
            debug_log.info("robot", f"Reset: {msg}")
            return ok, msg
        except Exception as e:
            debug_log.error("robot", f"Reset error: {e}")
            return False, str(e)

    # ==== グリッパー ====

    def gripper(self, action: str) -> Tuple[bool, str]:
        if not self._ensure():
            return False, "not connected"
        try:
            if action == "open":
                ok, msg = self._op.open_gripper()  # type: ignore
            else:
                ok, msg = self._op.close_gripper()  # type: ignore
            debug_log.info("robot", f"Gripper {action}: {msg}")
            return ok, msg
        except Exception as e:
            debug_log.error("robot", f"Gripper error: {e}")
            return False, str(e)

    # ==== ピック ====

    def pick_at(self, x: Any, y: Any) -> Tuple[bool, str]:
        if not self._ensure():
            return False, "not connected"
        try:
            debug_log.step("robot", f"Pick at ({x}, {y}) — starting")
            ok, msg = self._op.pick_at(int(x), int(y))  # type: ignore
            if ok:
                debug_log.info("robot", f"Pick at ({x}, {y}) — success")
            else:
                debug_log.error("robot", f"Pick at ({x}, {y}) — failed: {msg}")
            return ok, msg
        except Exception as e:
            debug_log.error("robot", f"Pick exception: {e}")
            return False, str(e)

    # ==== プレース ====

    def place_at(self, place_key: str = "default") -> Tuple[bool, str]:
        if not self._ensure():
            return False, "not connected"
        try:
            debug_log.step("robot", f"Place at '{place_key}' — starting")
            ok, msg = self._op.place_at(place_key)  # type: ignore
            if ok:
                debug_log.info("robot", f"Place at '{place_key}' — success")
            else:
                debug_log.error("robot", f"Place at '{place_key}' — failed: {msg}")
            return ok, msg
        except Exception as e:
            debug_log.error("robot", f"Place exception: {e}")
            return False, str(e)

    def pick_and_place(self, x: Any, y: Any, place_key: str = "default") -> Tuple[bool, str]:
        ok, msg = self.pick_at(x, y)
        if not ok:
            return False, f"Pick failed: {msg}"
        ok, msg = self.place_at(place_key)
        if not ok:
            return False, f"Place failed: {msg}"
        return True, f"pick_and_place complete: ({x},{y}) -> '{place_key}'"

    def reload_place_map(self) -> Tuple[bool, str]:
        """place_pose_map.json を再読み込み。"""
        try:
            self._load_place_map()
            if self._op:
                self._op.load_place_poses()
            debug_log.info("robot", f"Reloaded place map: {len(self._place_map)} entries")
            return True, f"reloaded {len(self._place_map)} place entries"
        except Exception as e:
            debug_log.error("robot", f"Reload place map error: {e}")
            return False, str(e)

    # ==== キャリブレーション ====

    def record_grid_cell(self, col: int, row: int) -> Tuple[bool, str]:
        """現在のロボット位置を grid_pose_map.json の指定セルに保存する。"""
        if not self._ensure():
            return False, "not connected"
        arm = self._op.arm  # type: ignore
        try:
            code, pos = arm.get_position()
            if code != 0:
                return False, f"get_position failed (code={code})"

            pose = list(pos[:6])
            key = f"{col},{row}"

            path = Path(self._grid_json)
            data: Dict[str, list] = {}
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data[key] = pose
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self._grid_map[key] = pose
            if self._op:
                self._op.pose_map[key] = pose  # type: ignore

            debug_log.info("robot", f"Recorded grid cell ({col},{row}): {[round(v,2) for v in pose[:3]]}")
            return True, f"recorded ({col},{row})"
        except Exception as e:
            debug_log.error("robot", f"record_grid_cell error: {e}")
            return False, str(e)

    def record_place(self, place_key: str = "default") -> Tuple[bool, str]:
        """現在のロボット位置を place_pose_map.json の指定キーに保存する。"""
        if not self._ensure():
            return False, "not connected"
        arm = self._op.arm  # type: ignore
        try:
            code, pos = arm.get_position()
            if code != 0:
                return False, f"get_position failed (code={code})"

            pose = list(pos[:6])

            path = Path(self._place_json)
            data: Dict[str, list] = {}
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data[place_key] = pose
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self._place_map[place_key] = pose
            if self._op:
                self._op.place_pose_map[place_key] = pose  # type: ignore

            debug_log.info("robot", f"Recorded place '{place_key}': {[round(v,2) for v in pose[:3]]}")
            return True, f"recorded place '{place_key}'"
        except Exception as e:
            debug_log.error("robot", f"record_place error: {e}")
            return False, str(e)

    def calibration_status(self) -> dict:
        """記録済みのグリッドセルとPlaceキー一覧を返す。"""
        return {
            "grid_keys": list(self._grid_map.keys()),
            "place_keys": list(self._place_map.keys()),
        }

    # ==== マニュアルモード ====

    def set_manual_mode(self, enabled: bool) -> Tuple[bool, str]:
        """マニュアルモードを ON/OFF する。
        ON: Mode 1 (サーボモード) に切り替え → jog ごとのモード切り替え不要
        OFF: Mode 0 (通常位置制御) に戻す
        """
        if not self._ensure():
            return False, "not connected"
        arm = self._op.arm  # type: ignore
        try:
            if enabled:
                arm.set_mode(1)
                arm.set_state(0)
                self._manual_mode = True
                debug_log.info("robot", "Manual mode ON (servo mode)")
                return True, "manual mode ON"
            else:
                arm.set_mode(0)
                arm.set_state(0)
                self._manual_mode = False
                debug_log.info("robot", "Manual mode OFF (position mode)")
                return True, "manual mode OFF"
        except Exception as e:
            debug_log.error("robot", f"set_manual_mode error: {e}")
            return False, str(e)

    # ==== Jog (keyboard_move.py と同方式: Mode1 サーボ + 30ms ループ) ====

    _JOG_AXIS_VEC = {
        "x":  (1, 0, 0),
        "-x": (-1, 0, 0),
        "y":  (0, 1, 0),
        "-y": (0, -1, 0),
        "z":  (0, 0, 1),
        "-z": (0, 0, -1),
    }

    def jog_setup(self, axis: str) -> Tuple[bool, str]:
        """Jog 開始前処理。マニュアルモード時はモード切り替えをスキップ。"""
        if not self._ensure():
            return False, "not connected"
        if self._JOG_AXIS_VEC.get(axis.lower()) is None:
            return False, f"Unknown axis: {axis}. Use x,-x,y,-y,z,-z"
        if self._manual_mode:
            # すでに Mode 1 なのでスキップ
            return True, "jog ready (manual mode)"
        arm = self._op.arm  # type: ignore
        try:
            arm.set_mode(1)
            arm.set_state(0)
            debug_log.info("robot", f"Jog setup: mode=1 axis={axis}")
            return True, "servo mode enabled"
        except Exception as e:
            debug_log.error("robot", f"Jog setup error: {e}")
            return False, str(e)

    def jog_step(self, axis: str, step_mm: float = 4.0) -> Tuple[bool, str]:
        """サーボモード中に 1 ステップ (step_mm) 分だけ相対移動する。
        keyboard_move.py の send_servo_move と同じロジック。
        ws_handlers の 30ms ループから呼ばれる。
        """
        if not self._ensure():
            return False, "not connected"
        direction = self._JOG_AXIS_VEC.get(axis.lower())
        if direction is None:
            return False, f"Unknown axis: {axis}"

        arm = self._op.arm  # type: ignore
        try:
            code, cur = arm.get_position()
            if code != 0:
                return False, f"get_position failed (code={code})"

            new_pos = [
                cur[0] + direction[0] * step_mm,
                cur[1] + direction[1] * step_mm,
                cur[2] + direction[2] * step_mm,
                cur[3], cur[4], cur[5],
            ]

            # ワークスペース・リミット (keyboard_move.py 準拠)
            if new_pos[0] <= 200 and direction[0] < 0: new_pos[0] = cur[0]
            if new_pos[1] <= -310 and direction[1] < 0: new_pos[1] = cur[1]
            if new_pos[2] <= 80 and direction[2] < 0: new_pos[2] = cur[2]

            code2, joint = arm.get_inverse_kinematics(new_pos)
            if code2 == 0:
                arm.set_servo_angle_j(joint[:7], speed=10)
            return True, "step ok"
        except Exception as e:
            debug_log.error("robot", f"Jog step error: {e}")
            return False, str(e)

    def jog_cleanup(self) -> Tuple[bool, str]:
        """Jog 終了後処理。マニュアルモード時は Mode 1 をキープ。"""
        if not self._ensure():
            return True, "not connected (nothing to clean up)"
        if self._manual_mode:
            # マニュアルモード中は Mode 1 を維持
            return True, "jog stopped (manual mode kept)"
        arm = self._op.arm  # type: ignore
        try:
            arm.set_mode(0)
            arm.set_state(0)
            debug_log.info("robot", "Jog cleanup: mode=0 restored")
            return True, "position mode restored"
        except Exception as e:
            debug_log.error("robot", f"Jog cleanup error: {e}")
            return False, str(e)

    # ==== 4x4 Grid Cell 移動 ====

    def grid_cells(self) -> List[Dict[str, Any]]:
        """4x4 グリッドセル一覧を返す (フロントエンドのボタン描画用)。"""
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
        """指定グリッドセルの座標へ移動 (ピックせずに上空で停止)。"""
        if not self._ensure():
            return False, "not connected"

        key = f"{col},{row}"
        if key not in self._grid_map:
            msg = f"Grid cell ({col},{row}) not found in grid_pose_map"
            debug_log.error("robot", msg)
            return False, msg

        pose = self._grid_map[key]
        px, py, pz, r, p, yaw = pose

        arm = self._op.arm  # type: ignore
        try:
            # 安全高さで移動 (ピックの UP_Z と同じ 290mm)
            safe_z = max(pz + 80, 290.0)

            debug_log.step("robot", f"Moving to cell ({col},{row}) at safe height {safe_z:.0f}")
            code = arm.set_position(
                x=px, y=py, z=safe_z,
                roll=r, pitch=p, yaw=yaw,
                wait=True,
            )
            if code != 0:
                return False, f"move failed (code={code})"

            debug_log.info("robot", f"Arrived at cell ({col},{row})")
            return True, f"moved to cell ({col},{row})"
        except Exception as e:
            debug_log.error("robot", f"move_to_cell error: {e}")
            return False, str(e)

    # ==== ステータス ====

    def status(self) -> dict:
        if not self._op or not self._op.connected:
            return {"connected": False, "mode": "real", "manual_mode": self._manual_mode}
        try:
            arm = self._op.arm
            code, pos = arm.get_position()
            return {
                "connected": True,
                "mode": "real",
                "state": arm.state,
                "position": pos if code == 0 else None,
                "error_code": arm.error_code,
                "grid_cells_loaded": len(self._grid_map),
                "manual_mode": self._manual_mode,
            }
        except Exception:
            return {"connected": True, "mode": "real", "state": "unknown", "manual_mode": self._manual_mode}

    def reload_grid_map(self) -> Tuple[bool, str]:
        """grid_pose_map.json を再読み込み。"""
        try:
            self._load_grid_map()
            if self._op:
                self._op.load_poses()
            debug_log.info("robot", f"Reloaded grid map: {len(self._grid_map)} cells")
            return True, f"reloaded {len(self._grid_map)} cells"
        except Exception as e:
            debug_log.error("robot", f"Reload error: {e}")
            return False, str(e)

    # ==== internal ====

    def _load_place_map(self):
        try:
            path = Path(self._place_json)
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self._place_map = json.load(f)
                debug_log.info("robot", f"Place map loaded: {len(self._place_map)} entries from {path.name}")
            else:
                debug_log.warn("robot", f"Place map not found: {path}")
                self._place_map = {}
        except Exception as e:
            debug_log.warn("robot", f"Place map load error: {e}")
            self._place_map = {}

    def _ensure(self) -> bool:
        return self._op is not None and self._op.connected

    def _load_grid_map(self):
        try:
            path = Path(self._grid_json)
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self._grid_map = json.load(f)
                debug_log.info("robot", f"Grid map loaded: {len(self._grid_map)} cells from {path.name}")
            else:
                debug_log.warn("robot", f"Grid map not found: {path}")
                self._grid_map = {}
        except Exception as e:
            debug_log.warn("robot", f"Grid map load error: {e}")
            self._grid_map = {}
