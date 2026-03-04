# 通信プロトコル仕様 | Unity ↔ Server

---

## 接続情報

| 項目           | 値                                |
| -------------- | --------------------------------- |
| プロトコル     | WebSocket                         |
| パス           | `ws://<server_host>:8765/spatial` |
| データ形式     | JSON（UTF-8 テキストフレーム）    |
| メッセージ識別 | `type` フィールドで判別           |

---

## メッセージ一覧

| 方向           | type                        | トリガー                     |
| -------------- | --------------------------- | ---------------------------- |
| Unity → Server | `spatial_reference_request` | ユーザーが自然文を発話した   |
| Unity → Server | `refinement_request`        | ユーザーが「違う」と修正した |
| Unity → Server | `confirmation`              | ユーザーが「はい」と承認した |
| Server → Unity | `spatial_reference_result`  | LLM 推論が完了した           |
| Server → Unity | `robot_command`             | ロボット動作のステータス更新 |
| Server → Unity | `error`                     | サーバー側でエラーが発生した |

---

## シーケンス

```
Unity                              Server
  │                                   │
  │─ spatial_reference_request ──────►│  発話 + 空間情報を送信
  │                                   │  (LLM 推論)
  │◄── spatial_reference_result ──────│  候補リストを返却
  │                                   │
  ├─ [ユーザーが「はい」] ────────────┤
  │─ confirmation ───────────────────►│  ターゲット確定
  │◄── robot_command (started) ───────│  動作開始通知
  │◄── robot_command (completed) ─────│  動作完了通知
  │                                   │
  ├─ [ユーザーが「違う」] ────────────┤
  │─ refinement_request ─────────────►│  修正発話を送信
  │◄── spatial_reference_result ──────│  新しい候補リスト
  │                                   │
  ├─ [エラー発生時] ──────────────────┤
  │◄── error ─────────────────────────│  エラーコード + メッセージ
```

---

## 各メッセージの JSON 構造

### Unity → Server

#### `spatial_reference_request`

```json
{
  "type": "spatial_reference_request",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-03-04T12:00:00.000Z",
  "utterance": {
    "text": "右の赤いボトル取って",
    "language": "ja"
  },
  "user_pose": {
    "position": { "x": 0.0, "y": 1.2, "z": -0.5 },
    "forward": { "x": 0.0, "y": -0.3, "z": 1.0 }
  },
  "objects": [
    {
      "id": "obj_001",
      "label": "bottle",
      "color": "red",
      "shape": "cylinder",
      "size": "small",
      "position": { "x": 0.3, "y": 0.0, "z": 0.2 },
      "relative_direction": "front-right"
    }
  ],
  "robot_pose": {
    "position": { "x": 0.0, "y": 0.0, "z": 0.6 },
    "reach_radius": 0.5
  }
}
```

#### `refinement_request`

```json
{
  "type": "refinement_request",
  "request_id": "550e8400-...-002",
  "original_request_id": "550e8400-...-001",
  "utterance": {
    "text": "違う、もっと奥のやつ",
    "language": "ja"
  },
  "user_pose": {
    "position": { "x": 0.0, "y": 1.2, "z": -0.5 },
    "forward": { "x": 0.0, "y": -0.3, "z": 1.0 }
  },
  "previous_target": "obj_001"
}
```

**注意**: `refinement_request` には `objects` がない。サーバーは `original_request_id` に紐づくセッション内の物体リストを再利用する。

#### `confirmation`

```json
{
  "type": "confirmation",
  "request_id": "550e8400-...-003",
  "confirmed_object_id": "obj_001",
  "action": "pick"
}
```

---

### Server → Unity

#### `spatial_reference_result`

```json
{
  "type": "spatial_reference_result",
  "request_id": "550e8400-...-001",
  "candidates": [
    {
      "object_id": "obj_001",
      "score": 0.92,
      "reasoning": "ユーザー視点で右前方にある赤いボトル"
    },
    {
      "object_id": "obj_003",
      "score": 0.45,
      "reasoning": "赤色だが左側に位置する"
    }
  ],
  "top_candidate_id": "obj_001",
  "confidence": 0.92
}
```

#### `robot_command`

```json
{
  "type": "robot_command",
  "request_id": "550e8400-...-003",
  "action": "pick",
  "target_object_id": "obj_001",
  "target_position": { "x": 0.3, "y": 0.0, "z": 0.2 },
  "status": "started",
  "message": ""
}
```

`status` の遷移: `"started"` → `"in_progress"`（任意） → `"completed"` or `"failed"`

#### `error`

```json
{
  "type": "error",
  "request_id": "550e8400-...-001",
  "code": "E001",
  "message": "LLM 推論がタイムアウトしました"
}
```

---

## エラーコード一覧

| コード | 意味                   |
| ------ | ---------------------- |
| E001   | LLM タイムアウト       |
| E002   | LLM 出力のパース失敗   |
| E003   | 物体リストが空         |
| E004   | 無効な座標値           |
| E005   | WebSocket 切断         |
| E006   | セッションタイムアウト |

---

## 接続ライフサイクル

- 1 WebSocket 接続 = 1 セッション
- セッション状態（前回の objects, target_id）は接続中のみサーバー側で保持
- Unity 側は切断検知時に自動再接続（最大 5 回、指数バックオフ）
- 再接続後は新規セッション扱い（状態リセット）
- 無通信 300 秒でサーバーがタイムアウト切断
