## 概要

FastAPI ベースの Spatial Referring サーバです。主に WebSocket で Unity/HoloLens から空間参照リクエストを受信し、
2ステージ LLM（参照フレーム判定 + 物体選択）で推論結果を返します。

- **WebSocket `/spatial`**: `spatial_reference_request` / `refinement_request` / `confirmation`
- **WebSocket `/status`**: 稼働状態の簡易取得
- **WebSocket `/`**: 既存 Unity 連携（Grid 保存・xArm 操作）

## セットアップ

### 依存関係のインストール

```bash
python -m pip install -r requirements.txt
```

### 環境変数（OpenAI）

このリポジトリでは `.env` の作成を推奨します（この環境ではドットファイルの自動生成が制限される場合があるため、`env.example` を用意しています）。

```bash
cp env.example .env
```

`.env` の `OPENAI_API_KEY` を設定してください。

## 起動

```bash
uvicorn src.server:app --host 0.0.0.0 --port 8765
```

## 使い方（主要フロー）

1. `/spatial` に `spatial_reference_request` を送信
2. サーバーが `spatial_reference_result` を返却
3. 必要に応じて `refinement_request` を送信
4. `confirmation` 送信後に `robot_command` を受信

### 空間参照リクエスト例

```bash
{
  "type": "spatial_reference_request",
  "request_id": "uuid-v4",
  "utterance": {"text": "右側の赤い箱を取って", "language": "ja"},
  "user_pose": {
    "position": {"x": 0.5, "y": 1.2, "z": -0.8},
    "forward": {"x": 0.0, "y": 0.0, "z": 1.0},
    "up": {"x": 0.0, "y": 1.0, "z": 0.0}
  },
  "objects": [
    {
      "id": "obj_001",
      "label": "box",
      "color": "red",
      "position": {"x": 0.3, "y": 0.75, "z": 0.2}
    }
  ],
  "robot_pose": {
    "position": {"x": -0.5, "y": 0.7, "z": 0.0},
    "forward": {"x": 1.0, "y": 0.0, "z": 0.0}
  }
}
```


