import json
import time
from typing import Dict, List
from xarm.wrapper import XArmAPI

# =========================
# 設定
# =========================
ARM_IP = "192.168.1.199"
GRID_FILE = "grid_pose_map.json"

Z_SAFE_OFFSET = 80.0
Z_PICK_OFFSET = 0.0

MOVE_SPEED = 80
MOVE_ACC = 800

GRIPPER_OPEN_POS = 850
GRIPPER_CLOSE_POS = 0
GRIPPER_SPEED = 500


# =========================
# 最小ユーティリティ
# =========================
def ensure_ready(arm: XArmAPI) -> None:
    _, state = arm.get_state()
    if state != 0:
        raise RuntimeError(f"xArm not ready (state={state})")


def init_gripper(arm: XArmAPI) -> None:
    ensure_ready(arm)
    arm.set_gripper_enable(True)
    arm.set_gripper_mode(0)
    arm.set_gripper_speed(GRIPPER_SPEED)
    time.sleep(0.2)


def gripper_open(arm: XArmAPI) -> None:
    ensure_ready(arm)
    arm.set_gripper_position(GRIPPER_OPEN_POS, wait=True)
    time.sleep(0.1)


def gripper_close(arm: XArmAPI) -> None:
    ensure_ready(arm)
    arm.set_gripper_position(GRIPPER_CLOSE_POS, wait=True)
    time.sleep(0.1)


def move_pose(arm: XArmAPI, pose: List[float]) -> None:
    ensure_ready(arm)
    x, y, z, r, p, yaw = pose
    arm.set_position(
        x, y, z, r, p, yaw,
        speed=MOVE_SPEED,
        acceleration=MOVE_ACC,
        wait=True
    )


# =========================
# グリッドピック
# =========================
def load_grid_map(path: str) -> Dict[str, List[float]]:
    with open(path, "r") as f:
        return json.load(f)


def pick_from_grid(arm: XArmAPI, grid_map: Dict[str, List[float]], gx: int, gy: int) -> None:
    key = f"{gx},{gy}"
    if key not in grid_map:
        raise ValueError(f"Grid {key} not found")

    x, y, z, r, p, yaw = grid_map[key]

    safe_pose = [x, y, z + Z_SAFE_OFFSET, r, p, yaw]
    pick_pose = [x, y, z + Z_PICK_OFFSET, r, p, yaw]

    move_pose(arm, safe_pose)
    move_pose(arm, safe_pose)   # XY確定
    move_pose(arm, pick_pose)
    gripper_close(arm)
    move_pose(arm, safe_pose)


# =========================
# 実行例
# =========================
if __name__ == "__main__":
    arm = XArmAPI(ARM_IP)
    arm.connect()

    try:
        ensure_ready(arm)

        init_gripper(arm)
        gripper_open(arm)

        grid_map = load_grid_map(GRID_FILE)
        pick_from_grid(arm, grid_map, 1, 2)

    finally:
        arm.disconnect()
