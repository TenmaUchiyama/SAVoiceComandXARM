import json
import time
from pathlib import Path
from xarm.wrapper import XArmAPI

class XArmOperator:
    def __init__(self, ip: str = '192.168.1.199', json_file: str | None = None):
        self.ip = ip
        # ポーズファイルのパス解決
        if json_file is None:
            current_dir = Path(__file__).resolve().parent
            self.json_file = str(current_dir / "robot_grid" / "grid_pose_map.json")
        else:
            self.json_file = json_file



        self.gripper_open_pos = 850
        self.gripper_close_pos = 350
            
        self.arm = None
        self.pose_map = {}
        self.connected = False
        
        # 【重要】安全高さの設定 (mm)
        # 机や障害物にぶつからない十分な高さを設定してください
        self.SAFE_HEIGHT = 200.0 
        
        self.load_poses()

    def load_poses(self):
        try:
            pose_path = Path(self.json_file)
            if not pose_path.is_file():
                print(f"Warning: pose map not found at {pose_path.resolve()}")
                return
            with open(pose_path, 'r', encoding='utf-8') as f:
                self.pose_map = json.load(f)
            print(f"Loaded {len(self.pose_map)} poses.")
        except Exception as e:
            print(f"Failed to load poses: {e}")
    

    def go_to_initial_pos(self) -> tuple[bool, str]:
        if not self.connected or not self.arm:
            return False, "Robot not connected"

        INITIAL_JOINT_ANGLES = [
            0.799792,
            -52.700543,
            -0.900117,
            5.199592,
            -0.800365,
            57.899677,
            0.299943
        ]

        try:
            print("Moving to Joint Initial Position...")

            code = self.arm.set_servo_angle(
                angle=INITIAL_JOINT_ANGLES,
                speed=20,     # ← 超重要：最初は遅く
                mvacc=50,     # ← 加速度も抑える
                wait=True
            )

            if code != 0:
                return False, f"set_servo_angle failed (code={code})"

            return True, "Moved to Joint Initial Position"

        except Exception as e:
            return False, str(e)


    def connect(self) -> tuple[bool, str]:
        """ロボットへの接続と初期化"""
        try:
            self.arm = XArmAPI(self.ip)
            self.arm.connect()
            
            # エラー解除とモーション有効化
            self.arm.clean_error()
            self.arm.clean_gripper_error()
            self.arm.motion_enable(enable=True)
            self.arm.set_mode(0)
            self.arm.set_state(state=0)
            
            # グリッパー設定
            self.arm.set_gripper_mode(0)
            self.arm.set_gripper_enable(True)
            self.arm.set_gripper_position(self.gripper_open_pos, wait=True)
            self.connected = True
            print("Connected to xArm.")
            
            # 接続後にホームポジションへ移動
            self.go_to_initial_pos()
            
            return True, "ok"
        except Exception as e:
            self.connected = False
            self.arm = None
            return False, str(e)

    def disconnect(self):
        """切断処理"""
        try:
            if self.arm:
                self.arm.disconnect()
        except Exception:
            pass
        finally:
            self.arm = None
            self.connected = False
            print("Disconnected.")

    def home(self) -> bool:
        """安全な初期位置（Home）へ戻る"""
        if not self.connected or not self.arm:
            return False
        try:
            print("Moving to Home position...")
            self.arm.move_gohome(wait=True)
            return True
        except Exception as e:
            print(f"Failed to go home: {e}")
            return False

    def reset(self) -> tuple[bool, str]:
        """
        エラー発生時のリカバリー処理。
        切断 -> 再接続 -> エラークリア -> ホーム移動
        """
        print(">>> [Recovery] Starting Reset Sequence...")
        self.disconnect()
        time.sleep(1.0)
        
        ok, msg = self.connect()
        if not ok:
            return False, f"Reset failed at reconnection: {msg}"
        
        # リセット後はアームがどこにいるか不明なため、ホームに戻す
        if not self.home():
            return False, "Reset failed at homing"

        print(">>> [Recovery] Reset Success.")
        return True, "Recovered"
    

    def open_gripper(self) -> tuple[bool, str]:
        """グリッパーを開く"""
        if not self.connected or not self.arm:
            return False, "Robot not connected"
        try:
            self.arm.set_gripper_position(self.gripper_open_pos, wait=True)
            return True, "Gripper opened"
        except Exception as e:
            return False, str(e)
    
    def close_gripper(self) -> tuple[bool, str]:
        """グリッパーを閉じる"""
        if not self.connected or not self.arm:
            return False, "Robot not connected"
        try:
            self.arm.set_gripper_position(self.gripper_close_pos, wait=True)
            return True, "Gripper closed"
        except Exception as e:
            return False, str(e)

    def pick_at(self, x: int, y: int) -> tuple[bool, str]:
        """
        指定座標(x,y)のアイテムをピックする。
        【動作フロー】: (現在地) -> UP_Zへ移動 -> 横移動(UP_Z維持) -> DOWN_Zへ下降 -> 掴む -> UP_Zへ上昇
        """
        if not self.connected or not self.arm:
            return False, "Robot not connected"

        key = f"{x},{y}"
        if key not in self.pose_map:
            return False, f"Grid {key} not found"

        # 設定値の固定
        DOWN_Z = 179.3   # 下降時の高さ
        UP_Z = 290.0     # 上昇・移動時の高さ

        # 目標座標の取得 (x, y, roll, pitch, yaw を利用)
        target_pose = self.pose_map[key]
        tx, ty, _, tr, tp, tyaw = target_pose 

        try:
            # -------------------------------------------------
            # 1. 安全高さへ移動 (Safety Lift) -> UP_Zへ
            # -------------------------------------------------
            code, curr_pose = self.arm.get_position()
            if code != 0: raise Exception(f"Get position failed (code: {code})")
            
            curr_x, curr_y = curr_pose[0], curr_pose[1]
            curr_r, curr_p, curr_yaw = curr_pose[3], curr_pose[4], curr_pose[5]

            # 余計な分岐を入れず、必ず安全高さUP_Zへ揃える
            print(f"Move to safe Z={UP_Z}")
            code = self.arm.set_position(
                x=curr_x, y=curr_y, z=UP_Z,
                roll=curr_r, pitch=curr_p, yaw=curr_yaw,
                wait=True
            )
            if code != 0: raise Exception(f"Move to safe height failed (code: {code})")

            # -------------------------------------------------
            # 2. 空中移動 (Horizontal Move) -> 高さを290.0で維持
            # -------------------------------------------------
            print(f"Moving horizontally to {tx}, {ty} at Z={UP_Z}")
            code = self.arm.set_position(x=tx, y=ty, z=UP_Z, 
                                    roll=tr, pitch=tp, yaw=tyaw, wait=True)
            if code != 0: raise Exception(f"Horizontal move failed (code: {code})")

            # -------------------------------------------------
            # 3. ピッキング動作 (Pick Sequence)
            # -------------------------------------------------
            # グリッパーを開く
            self.arm.set_gripper_position(self.gripper_open_pos, wait=True)
     
            err_code = self.arm.get_err_warn_code()
            if err_code[1][0] != 0: # エラーがある場合
                 print(f"Error detected: {err_code}")
                 self.arm.clean_error()
                 self.arm.motion_enable(True)
            
                 # ステートを強制的に0(Ready)に戻す
                 self.arm.set_state(0)
            time.sleep(0.5)  # 少し待つ
            # 下りる (固定値 179.3 へ)
            print(f"Moving down to Z={DOWN_Z}")
            code = self.arm.set_position(x=tx, y=ty, z=DOWN_Z, 
                                    roll=tr, pitch=tp, yaw=tyaw, wait=True)
            

            # 掴む
            self.arm.set_gripper_position(self.gripper_close_pos, wait=True)
            time.sleep(0.5)  # 少し待つ
            err_code = self.arm.get_err_warn_code()
            if err_code[1][0] != 0: # エラーがある場合
                 print(f"Error detected: {err_code}")
                 self.arm.clean_error()
                 self.arm.motion_enable(True)
            
            # ステートを強制的に0(Ready)に戻す
            self.arm.set_state(0)

            # 上がる (固定値 290.0 へ)
            print(f"Moving up to Z={UP_Z}")
            code = self.arm.set_position(x=tx, y=ty, z=UP_Z, 
                                    roll=tr, pitch=tp, yaw=tyaw, wait=True)
            if code != 0: raise Exception(f"Move up failed (code: {code})")

            return True, "Success"

        except Exception as e:
            print(f"Pick Error: {e}")
            return False, str(e)