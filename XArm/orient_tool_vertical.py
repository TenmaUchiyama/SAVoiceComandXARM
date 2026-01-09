import time
from typing import Optional
from xarm.wrapper import XArmAPI

# ============================================================
# CONFIG
# ============================================================
# 床に対して垂直な姿勢（xArm座標系前提）
VERTICAL_ROLL = 90
VERTICAL_PITCH = 0.0

ROTATE_SPEED = 40
ROTATE_ACC = 300


# ============================================================
# STATE MANAGEMENT (最小)
# ============================================================
def ensure_commandable(arm: XArmAPI) -> None:
    """
    最低限の state チェック（pick 側の recover を前提）
    """
    _, state = arm.get_state()
    if state != 2:
        raise RuntimeError(f"xArm not commandable (state={state})")

def recover_and_prepare(arm: XArmAPI) -> None:
    """
    xArm をコマンド可能へ遷移させる正しい最小手順
    """

    # ① 明示的に STOP
    arm.set_state(4)
    time.sleep(0.15)

    # ② エラー・警告クリア
    arm.clean_error()
    arm.clean_warn()
    time.sleep(0.15)

    # ③ READY 要求（← 先）
    arm.set_state(0)
    time.sleep(0.3)

    # ④ モーション有効化（← READY の後）
    arm.motion_enable(True)
    time.sleep(0.2)

    # ⑤ ポジションモード
    arm.set_mode(0)
    time.sleep(0.1)

    # ⑥ 最終確認
    _, state = arm.get_state()
    if state != 2:
        raise RuntimeError(f"xArm not commandable (state={state})")

# ============================================================
# ORIENTATION CONTROL
# ============================================================
def rotate_tool_vertical(
    arm: XArmAPI,
    yaw: Optional[float] = None,
    z_offset: float = 0.0,
    wait: bool = True,
) -> None:
    """
    エンドエフェクターを床に対して垂直に回転させる

    Parameters
    ----------
    arm : XArmAPI
        接続済み xArm
    yaw : float | None
        None の場合、現在の yaw を維持
    z_offset : float
        回転時に Z を少し上げたい場合（干渉防止）
    wait : bool
        True: 同期 / False: 非同期
    """
    ensure_commandable(arm)

    x, y, z, r, p, current_yaw = arm.get_position()[1]

    target_yaw = current_yaw if yaw is None else yaw
    target_z = z + z_offset

    arm.set_position(
        x,
        y,
        target_z,
        VERTICAL_ROLL,
        VERTICAL_PITCH,
        target_yaw,
        speed=ROTATE_SPEED,
        acceleration=ROTATE_ACC,
        wait=wait,
    )

# ============================================================
# OPTIONAL: 安全に垂直へ回す（Z退避付き）
# ============================================================
def rotate_tool_vertical_safe(
    arm: XArmAPI,
    yaw: Optional[float] = None,
    lift_z: float = 30.0,
) -> None:
    """
    一度 Z を上げてから垂直に回す安全版
    """
    ensure_commandable(arm)

    x, y, z, r, p, current_yaw = arm.get_position()[1]
    target_yaw = current_yaw if yaw is None else yaw

    # 上に退避
    arm.set_position(
        x, y, z + lift_z, r, p, current_yaw,
        speed=ROTATE_SPEED,
        acceleration=ROTATE_ACC,
        wait=True,
    )

    # 垂直回転
    arm.set_position(
        x, y, z + lift_z,
        VERTICAL_ROLL,
        VERTICAL_PITCH,
        target_yaw,
        speed=ROTATE_SPEED,
        acceleration=ROTATE_ACC,
        wait=True,
    )
arm = XArmAPI("192.168.1.199")
arm.connect()

recover_and_prepare(arm)

try:
    rotate_tool_vertical(arm)
    rotate_tool_vertical(arm, yaw=90.0)
    rotate_tool_vertical(arm, wait=False)
    rotate_tool_vertical_safe(arm, yaw=180.0)
finally:
    arm.disconnect()