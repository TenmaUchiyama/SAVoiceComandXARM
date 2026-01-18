import json
import time
import sys
from xarm.wrapper import XArmAPI

# --- 設定項目 ---
ARM_IP = '192.168.1.199'
JSON_FILE = 'grid_pose_map.json'  # JSONファイル名を指定
GRIP_OPEN = 850
GRIP_CLOSE = 350
APPROACH_OFFSET_Z = 50.0

class XArmPicker:
    def __init__(self, ip=ARM_IP, json_file=JSON_FILE):
        self.arm = XArmAPI(ip)
        self.json_file = json_file
        self.pose_map = {}  # ここで初期化
        
        self.load_poses()   # JSONを読み込む
        self.initialize_robot()

    def load_poses(self):
        """JSONファイルから座標データを読み込む"""
        try:
            with open(self.json_file, 'r') as f:
                self.pose_map = json.load(f)
                print(f"[File] {len(self.pose_map)} 個の座標を読み込みました。")
        except FileNotFoundError:
            print(f"[Error] {self.json_file} が見つかりません。")
            sys.exit(1)

    def initialize_robot(self):
        """アームとグリッパーの初期化設定"""
        print("[Init] 接続とエラークリアを開始します...")
        self.arm.connect()
        self.arm.clean_error()
        self.arm.clean_gripper_error()
        
        self.arm.motion_enable(enable=True)
        self.arm.set_mode(0)  # 位置制御モード
        self.arm.set_state(state=0)
        
        self.arm.set_gripper_mode(0)
        self.arm.set_gripper_enable(True)
        self.arm.set_gripper_speed(1500)
        time.sleep(1)
        print("[Init] ロボットの準備が完了しました。")

    def set_gripper_pos(self, pos):
        """エラーが発生しても、復旧して成功するまでリトライする"""
        while True:
            print(f"[Gripper] Moving to {pos}...")
            code = self.arm.set_gripper_position(pos, wait=True)
            
            if code == 0:
                return True

            print(f"!! Gripper Error (Code: {code}) !! 復旧シーケンス開始...")
            self.arm.clean_error()
            self.arm.clean_gripper_error()
            time.sleep(1.0)
            
            self.arm.set_state(state=0)
            self.arm.motion_enable(enable=True)
            self.arm.set_gripper_mode(0)
            self.arm.set_gripper_enable(True)
            time.sleep(1.0)

    def pick_at(self, x, y):
        """指定したグリッド座標 (x, y) をピックアップする"""
        key = f"{x},{y}"
        if key not in self.pose_map:
            print(f"エラー: 座標 {key} がJSONファイルに見つかりません。")
            return False

        pose = self.pose_map[key]
        # poseの要素数に合わせて展開（x, y, z, roll, pitch, yaw）
        px, py, pz, r, p, yaw = pose

        print(f"\n--- Picking at Grid ({x}, {y}) ---")

        # 1. アプローチ位置（上空）へ移動
        self.arm.set_position(px, py, pz + APPROACH_OFFSET_Z, r, p, yaw, wait=True)
        
        # 2. グリッパーを開く
        self.set_gripper_pos(GRIP_OPEN)
        
        # 3. 下降
        self.arm.set_position(px, py, pz, r, p, yaw, wait=True)
        
        # 4. グリッパーを閉じる
        self.set_gripper_pos(GRIP_CLOSE)
        
        # 5. 退避（上昇）
        self.arm.set_position(px, py, pz + APPROACH_OFFSET_Z, r, p, yaw, wait=True)
        
        print(f"--- Pick Complete ({x}, {y}) ---")
        return True

# ==========================================
# メイン実行部分
# ==========================================
if __name__ == "__main__":
    system = XArmPicker(ARM_IP)

    # テスト実行 (0,0)
    system.pick_at(1, 1)
    
    try:
        while True:
            val = input("\nピックアップ座標を入力 (例: 0 1) / 終了は q > ")
            if val.lower() == 'q': break
            
            inputs = val.split()
            if len(inputs) == 2:
                system.pick_at(inputs[0], inputs[1])
            
            else: 
                #Cが押されたらグリッパーを閉じる
                if val.lower() == 'c':
                    system.set_gripper_pos(GRIP_CLOSE)
                if val.lower() == 'o':
                    system.set_gripper_pos(GRIP_OPEN)
                
    except KeyboardInterrupt:
        pass

    system.arm.disconnect()