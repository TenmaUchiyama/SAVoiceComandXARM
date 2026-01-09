import time
import json
import keyboard
from xarm.wrapper import XArmAPI

# --- 設定項目 ---
ARM_IP = "192.168.1.199"
SAVE_FILE = "grid_pose_map.json"
GRID_W = 4
GRID_H = 4

STEP_MM = 4.0        # 1回（1フレーム）の移動量
LOOP_DT = 0.03       # 制御周期

class XArmTeacher:
    def __init__(self, ip):
        self.arm = XArmAPI(ip)
        self.grid_pose_map = {}
        self.initialize_robot()
        self.load_existing_data()

    def initialize_robot(self):
        """アームとグリッパーの初期化、Error 19 対策を含む"""
        print("[Init] 接続中...")
        self.arm.connect()
        self.arm.clean_error()
        self.arm.clean_gripper_error()
        
        self.arm.motion_enable(True)
        self.arm.set_mode(1)  # Servo Mode (リアルタイム制御)
        self.arm.set_state(0)

        # グリッパーの初期設定
        self.arm.set_gripper_mode(0)
        self.arm.set_gripper_enable(True)
        self.arm.set_gripper_speed(2000) # 負荷軽減のため少し落とす
        time.sleep(1)
        print("[Init] サーボモードで準備完了")

    def load_existing_data(self):
        """既存のJSONファイルがあれば読み込む"""
        try:
            with open(SAVE_FILE, "r") as f:
                self.grid_pose_map = json.load(f)
                print(f"[File] {SAVE_FILE} を読み込みました。")
        except FileNotFoundError:
            print("[File] 新規ファイルを作成します。")

    def safe_gripper_move(self, pos):
        """エラー監視付きグリッパー操作"""
        code = self.arm.set_gripper_position(pos, wait=False)
        if code != 0:
            print(f"!! Gripper Error {code} !! クリアして再試行します...")
            self.arm.clean_gripper_error()
            time.sleep(0.5)
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

        # ワークスペース・リミット判定（元コード継承）
        if new_pos[0] <= 200 and dx < 0: new_pos[0] = cur[0]
        if new_pos[1] <= -310 and dy < 0: new_pos[1] = cur[1]
        if new_pos[2] <= 80 and dz < 0: new_pos[2] = cur[2]

        code, joint = self.arm.get_inverse_kinematics(new_pos)
        if code == 0:
            # joint[:7] は7軸分。speedはサーボモードではJerk的な役割
            self.arm.set_servo_angle_j(joint[:7], speed=10)

    def main_loop(self):
        print("""
=== Teaching Mode ===
[Arrows] : XY方向移動
[ [ ] / [ ] ] : Z方向移動 (上げ/下げ)
[ o ] : Open Gripper  [ c ] : Close Gripper
[ Space ] : 座標を保存して次のグリッドへ
[ p ] : 現在の座標を表示
[ q ] : 中断して終了
""")

        goto_end = False
        for gy in range(GRID_H):
            for gx in range(GRID_W):
                grid_key = f"{gx},{gy}"
                print(f"\n>>> Target: Grid ({grid_key}) を記録してください")

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
                        self.safe_gripper_move(850) # OPEN
                        time.sleep(0.2)
                    if keyboard.is_pressed("c"):
                        self.safe_gripper_move(350) # CLOSE
                        time.sleep(0.2)

                    # 表示
                    if keyboard.is_pressed("p"):
                        _, pose = self.arm.get_position()
                        print(f"Current: {pose}")
                        time.sleep(0.3)

                    # 保存 (Next Grid)
                    if keyboard.is_pressed("space"):
                        _, pose = self.arm.get_position()
                        self.grid_pose_map[grid_key] = pose
                        print(f"[Saved] {grid_key}: {pose}")
                        time.sleep(0.5)
                        break

                    # 終了
                    if keyboard.is_pressed("q"):
                        goto_end = True
                        break

                    time.sleep(LOOP_DT)

                if goto_end: break
            if goto_end: break

        # ファイル保存
        with open(SAVE_FILE, "w") as f:
            json.dump(self.grid_pose_map, f, indent=2)
        print(f"\n[Done] すべての座標を {SAVE_FILE} に保存しました。")
        self.arm.disconnect()

if __name__ == "__main__":
    teacher = XArmTeacher(ARM_IP)
    teacher.main_loop()