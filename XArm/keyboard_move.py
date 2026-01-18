import time
import json
import keyboard
from xarm.wrapper import XArmAPI

# --- 設定項目 ---
ARM_IP = "192.168.1.199"
SAVE_FILE = "manual_saved_poses.json"

STEP_MM = 4.0        # 1回（1フレーム）の移動量
LOOP_DT = 0.03       # 制御周期（30ms）

class XArmManualControl:
    def __init__(self, ip):
        self.arm = XArmAPI(ip)
        self.saved_poses = {} # 記録用辞書
        self.pose_counter = 1
        self.initialize_robot()

    def initialize_robot(self):
        """アームとグリッパーの初期化"""
        print(f"[Init] {ARM_IP} に接続中...")
        self.arm.connect()
        self.arm.clean_error()
        self.arm.clean_gripper_error()
        
        self.arm.motion_enable(True)
        self.arm.set_mode(1)  # Servo Mode (キーボード操作に適したリアルタイムモード)
        self.arm.set_state(0)

        self.arm.set_gripper_mode(0)
        self.arm.set_gripper_enable(True)
        self.arm.set_gripper_speed(2000)
        time.sleep(1)
        print("[Init] サーボモードで準備完了。")

    def safe_gripper_move(self, pos):
        """エラー監視付きグリッパー操作"""
        code = self.arm.set_gripper_position(pos, wait=False)
        if code != 0:
            self.arm.clean_gripper_error()
            self.arm.set_gripper_enable(True)
            self.arm.set_gripper_position(pos, wait=False)

    def send_servo_move(self, dx, dy, dz):
        """現在の姿勢から相対移動を行う（リミット判定付き）"""
        code, cur = self.arm.get_position()
        if code != 0: return

        new_pos = [
            cur[0] + dx,
            cur[1] + dy,
            cur[2] + dz,
            cur[3], cur[4], cur[5]
        ]

        # ワークスペース・リミット判定
        if new_pos[0] <= 200 and dx < 0: new_pos[0] = cur[0]
        if new_pos[1] <= -310 and dy < 0: new_pos[1] = cur[1]
        if new_pos[2] <= 80 and dz < 0: new_pos[2] = cur[2]

        code, joint = self.arm.get_inverse_kinematics(new_pos)
        if code == 0:
            self.arm.set_servo_angle_j(joint[:7], speed=10)

    def run(self):
        print(f"""
=========================================
   xArm Manual Control Mode
=========================================
[Arrows] : XY方向移動 (↑:前, ↓:後, ←:左, →:右)
[ 1 ]    : Z方向 上昇
[ 0 ]    : Z方向 下降
[ o ]    : グリッパーを開く
[ c ]    : グリッパーを閉じる
-----------------------------------------
[ Space ]: 現在の座標を連番で保存
[ p ]    : 現在の座標をコンソールに表示
[ q ]    : 終了
=========================================
""")

        try:
            while True:
                dx = dy = dz = 0.0

                # 移動キー判定
                if keyboard.is_pressed("up"):    dx -= STEP_MM
                if keyboard.is_pressed("down"):  dx += STEP_MM
                if keyboard.is_pressed("left"):  dy -= STEP_MM
                if keyboard.is_pressed("right"): dy += STEP_MM
                if keyboard.is_pressed("1"):     dz += STEP_MM
                if keyboard.is_pressed("0"):     dz -= STEP_MM

                if dx != 0 or dy != 0 or dz != 0:
                    self.send_servo_move(dx, dy, dz)

                # グリッパー操作
                if keyboard.is_pressed("o"):
                    self.safe_gripper_move(850)
                    time.sleep(0.1)
                if keyboard.is_pressed("c"):
                    self.safe_gripper_move(250)
                    time.sleep(0.1)

                # 表示 (Print)
                if keyboard.is_pressed("p"):
                    _, pose = self.arm.get_position()
                    print(f"Current Pose: {pose}")
                    time.sleep(0.3)

                # 記録 (Save)
                if keyboard.is_pressed("space"):
                    _, pose = self.arm.get_position()
                    code, servo = self.arm.get_servo_angle()

                    label = f"pose_{self.pose_counter}"
                    self.saved_poses[label] = pose
                    print(f"Saved [{label}]: {pose}")
                    print(f"Servo Angles: {servo[:7]}")
                    self.pose_counter += 1
                    time.sleep(0.5)

                # 終了
                if keyboard.is_pressed("q"):
                    print("\n終了します...")
                    break

                time.sleep(LOOP_DT)

        except KeyboardInterrupt:
            pass

        # ファイル保存
        if self.saved_poses:
            with open(SAVE_FILE, "w") as f:
                json.dump(self.saved_poses, f, indent=2)
            print(f"[Done] {len(self.saved_poses)} 件の座標を {SAVE_FILE} に書き出しました。")
        
        self.arm.disconnect()

if __name__ == "__main__":
    controller = XArmManualControl(ARM_IP)
    controller.run()