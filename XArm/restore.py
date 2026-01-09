"""
restore_pose.py

共有されている xArm を
「実行前の姿勢に必ず戻す」ための専用スクリプト。

用途：
- 実験前に現在のジョイント角を保存
- 実験後（または異常終了時）に完全復元

注意：
- エンドエフェクタ座標ではなく
  「全ジョイント角」を保存・復元する
"""

import json
import sys
from xarm.wrapper import XArmAPI

# =========================
# 設定
# =========================
ARM_IP = "192.168.1.199"
SAVE_FILE = "original_joint_state.json"

# =========================
# 接続
# =========================
arm = XArmAPI(ARM_IP)
arm.connect()
arm.motion_enable(True)
arm.set_mode(0)   # position control
arm.set_state(0)

# =========================
# 保存
# =========================
def save_current_joint_state():
    code, joints = arm.get_servo_angle(is_radian=False)
    if code != 0:
        raise RuntimeError("Failed to get joint angles")

    data = {
        "joint_angles_deg": joints
    }

    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print("[SAVE] Original joint state saved")
    print(joints)

# =========================
# 復元
# =========================
def restore_joint_state():
    with open(SAVE_FILE, "r") as f:
        data = json.load(f)

    joints = data["joint_angles_deg"]

    print("[RESTORE] Restoring joint angles...")
    print(joints)

    arm.set_servo_angle(
        angle=joints,
        speed=30,
        acceleration=500,
        wait=True
    )

    print("[RESTORE] Done")

# =========================
# エントリポイント
# =========================
if __name__ == "__main__":
    """
    使い方：
    python restore_pose.py save
    python restore_pose.py restore
    """

    if len(sys.argv) < 2:
        print("Usage: python restore_pose.py [save|restore]")
        sys.exit(1)

    try:
        if sys.argv[1] == "save":
            save_current_joint_state()

        elif sys.argv[1] == "restore":
            restore_joint_state()

        else:
            print("Unknown command")
    finally:
        arm.disconnect()
