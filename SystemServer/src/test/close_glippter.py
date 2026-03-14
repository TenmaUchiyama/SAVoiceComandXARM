"""グリッパーを完全に閉じるテストスクリプト"""

from xarm.wrapper import XArmAPI

XARM_IP = "192.168.1.199"
GRIPPER_CLOSE_POS = 0  # 完全に閉じる（0 = 最小開度）


def main():
    arm = XArmAPI(XARM_IP)
    arm.connect()

    arm.clean_error()
    arm.clean_gripper_error()
    arm.motion_enable(enable=True)
    arm.set_mode(0)
    arm.set_state(state=0)

    # グリッパー初期化
    arm.set_gripper_mode(0)
    arm.set_gripper_enable(True)
    arm.set_gripper_speed(2000)

    # グリッパーを完全に閉じる
    print("グリッパーを完全に閉じます...")
    code = arm.set_gripper_position(GRIPPER_CLOSE_POS, wait=True)
    if code == 0:
        print("グリッパーを閉じました")
    else:
        print(f"エラーが発生しました (code: {code})")
        arm.clean_gripper_error()

    arm.disconnect()


if __name__ == "__main__":
    main()
