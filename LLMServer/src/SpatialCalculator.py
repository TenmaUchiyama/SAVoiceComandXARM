# services.py
import numpy as np
import math
from typing import List, Dict, Any
from models import CommandRequest, ObjectFeatures, LLMInputContext

class SpatialCalculator:
    """
    ユーザー座標系における幾何特徴量の計算を担当するクラス
    """
    def __init__(self, fov_horizontal_deg: float = 43.0, fov_vertical_deg: float = 29.0):
        """HoloLens 2のFOV: 水平43度 × 垂直29度"""
        self.fov_h_rad = np.deg2rad(fov_horizontal_deg)
        self.fov_v_rad = np.deg2rad(fov_vertical_deg)

    def process_request(self, request: CommandRequest) -> LLMInputContext:
        """
        リクエストを受け取り、計算済みのLLM用コンテキストを返すメインメソッド
        """
        candidates = self._compute_features(request)
        
        return LLMInputContext(
            task="spatial_target_selection",
            utterance=request.utterance,
            candidates=candidates
        )

    def _compute_features(self, request: CommandRequest) -> List[ObjectFeatures]:
        """
        内部計算ロジック：各オブジェクトの特徴量算出とランク付け
        """
        # User基本ベクトル
        u_forward = self._normalize(np.array(request.user.forward, dtype=float))
        u_up = self._normalize(np.array(request.user.up, dtype=float))
        u_right = np.cross(u_forward, u_up)

        temp_results = []

        # 各オブジェクトの計算
        for obj in request.objects:
            pos = np.array(obj.rel_pos, dtype=float)
            distance = float(np.linalg.norm(pos))

            # 特徴量計算
            if distance < 1e-6:
                front_score, right_score, up_score = 0.0, 0.0, 0.0
                in_fov = False
            else:
                pos_norm = pos / distance
                front_score = float(np.dot(pos_norm, u_forward))
                right_score = float(np.dot(pos_norm, u_right))
                up_score = float(np.dot(pos_norm, u_up))
                
                # FOV判定（矩形FOV: HoloLens 2対応）
                if front_score > 0:
                    horizontal_angle = np.arctan2(abs(right_score), front_score)
                    vertical_angle = np.arctan2(abs(up_score), front_score)
                    in_fov = bool(
                        horizontal_angle < (self.fov_h_rad / 2.0) and
                        vertical_angle < (self.fov_v_rad / 2.0)
                    )
                else:
                    in_fov = False

            temp_results.append({
                "id": obj.id,
                "raw_distance": distance,
                "features": {
                    "distance": round(distance, 3),
                    "front_score": round(front_score, 3),
                    "right_score": round(right_score, 3),
                    "up_score": round(up_score, 3),
                    "in_fov": in_fov
                }
            })

        # ランク付け (Sort by distance)
        temp_results.sort(key=lambda x: x["raw_distance"])

        # 結果リストの構築
        final_objects = []
        for rank, item in enumerate(temp_results, 1):
            item["features"]["depth_rank"] = rank
            final_objects.append(ObjectFeatures(
                id=item["id"],
                features=item["features"]
            ))

        return final_objects

    @staticmethod
    def _normalize(v: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(v)
        if norm == 0: 
            return v
        return v / norm