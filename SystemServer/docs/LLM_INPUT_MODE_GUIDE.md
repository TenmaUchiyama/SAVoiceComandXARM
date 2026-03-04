# LLM Input Mode Configuration Guide

## 環境変数で座標モードと特徴量モードを切り替える

`.env` ファイルで `LLM_INPUT_MODE` を設定することで、システムの動作モードを切り替えられます。

## 設定方法

### `.env` ファイル

```env
# 座標ベースモード（推奨）
LLM_INPUT_MODE=coordinate

# または特徴量ベースモード
# LLM_INPUT_MODE=feature
```

## 2つのモード比較

### 1. Coordinate Mode（座標ベース） - **推奨**

```env
LLM_INPUT_MODE=coordinate
```

**特徴:**

- LLMが生の座標データを受け取る
- 空間推論をLLM自身が行う
- より柔軟で自然な指示に対応

**入力例:**

```json
{
  "utterance": "右から2番目の箱を取って",
  "input_frame": "user",
  "objects": [
    {
      "id": "obj_01",
      "pos_local": [0.15, 0.0, 0.25],
      "distance": 0.29,
      "angle_from_forward_deg": 30.5
    },
    {
      "id": "obj_02",
      "pos_local": [0.05, 0.0, 0.25],
      "distance": 0.25,
      "angle_from_forward_deg": 11.3
    }
  ]
}
```

**出力:**

```json
{
  "reasoning": "User's perspective, sorted by right-to-left position, selecting 2nd item",
  "target_id": "obj_02"
}
```

### 2. Feature Mode（特徴量ベース）

```env
LLM_INPUT_MODE=feature
```

**特徴:**

- サーバー側で事前に特徴量（ランク）を計算
- LLMはフィルタと並べ替えルールを返す
- より構造化されたアプローチ

**入力例:**

```json
{
  "utterance": "右から2番目の箱を取って",
  "objects": [
    {
      "id": "obj_01",
      "features": {
        "user": {
          "depth_rank": 1,
          "right_rank": 1,
          "front_rank": 2,
          "in_fov": true
        }
      }
    }
  ]
}
```

**出力:**

```json
{
  "reference_frame": "user",
  "filters": [],
  "order_by": { "feature": "right_rank", "direction": "asc" },
  "select": { "rank": 2 }
}
```

## エンドポイント

### `/command` - 統合エンドポイント

- `LLM_INPUT_MODE` の設定に従って動作が変わる
- 推奨：このエンドポイントを使用

### `/command_cord` - レガシーエンドポイント

- 常に座標モードで動作（`LLM_INPUT_MODE` 無視）
- 後方互換性のために維持

## プロンプトファイル

モードに応じて適切なプロンプトが自動的に選択されます：

- **Coordinate Mode**: `LLM_Agent/prompt/system_prompt_cord.txt`
- **Feature Mode**: `LLM_Agent/prompt/system_prompt.txt`

## どちらを使うべきか？

### Coordinate Mode を推奨する理由:

✅ **より自然な指示に対応**

- 「手前から3番目」「少し右寄りの」など柔軟な表現

✅ **LLMの空間推論能力を活用**

- GPT-4o, Gemini 2.0などの最新モデルに最適

✅ **シンプルな実装**

- サーバー側の計算が少ない
- メンテナンスが容易

### Feature Mode を選ぶ場合:

- 厳密なルールベースの選択が必要
- 特徴量を事前計算してキャッシュしたい
- デバッグ時にランクを確認したい

## 起動時の確認

サーバー起動時にモードが表示されます：

```bash
$ python server.py
===== SYSTEM PROMPT =====
...
===== MODEL: openai:gpt-4o =====
===== INPUT MODE: coordinate =====  # ← ここで確認
```

## 実行例

### Coordinate Mode

```bash
# .env
LLM_INPUT_MODE=coordinate

# リクエスト
POST /command
{
  "utterance": "一番手前の箱",
  "user": {"position": [0, 0, 0], "forward": [0, 0, 1]},
  "objects": [{"id": "obj_01", "position": [0.1, 0, 0.3]}]
}

# レスポンス（debug.mode で確認）
{
  "status": "ok",
  "target_id": "obj_01",
  "debug": {"mode": "coordinate"}
}
```

### Feature Mode

```bash
# .env
LLM_INPUT_MODE=feature

# 同じリクエストでも、computed_featuresが返される
{
  "status": "ok",
  "target_id": "obj_01",
  "computed_features": [...],
  "debug": {"mode": "feature"}
}
```

## トラブルシューティング

### モードが切り替わらない

→ サーバーを再起動してください（`.env`の変更は再起動が必要）

### Invalid LLM_INPUT_MODE エラー

→ `coordinate` または `feature` のいずれかを指定してください

### 意図しない結果が返る

→ `debug.mode` を確認して、期待するモードで動作しているか確認
