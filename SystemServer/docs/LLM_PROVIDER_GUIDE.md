# Spatial Robot Controller - LLM Provider Guide

## 対応LLMプロバイダー

このシステムは以下のLLMプロバイダーに対応しています：

- **OpenAI** (GPT-4o, GPT-4o-mini)
- **Google Gemini** (Gemini 2.0 Flash, Gemini 1.5 Flash)
- **Anthropic** (Claude 3.5 Sonnet, Claude 3.5 Haiku)

## プロバイダーの切り替え方法

### 1. 環境変数ファイルの準備

```bash
# .env.example をコピー
cp .env.example .env

# .env を編集
```

### 2. Gemini に切り替える例

`.env` ファイルを編集：

```env
LLM_PROVIDER=google-genai

GOOGLE_API_KEY=your_gemini_api_key_here
GOOGLE_MODEL=gemini-2.0-flash-exp
GOOGLE_MODEL_LIGHT=gemini-1.5-flash
```

### 3. サーバー起動

```bash
cd src
python server.py
```

## 各プロバイダーの設定例

### OpenAI (デフォルト)

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_MODEL_LIGHT=gpt-4o-mini
```

### Google Gemini

```env
LLM_PROVIDER=google-genai
GOOGLE_API_KEY=...
GOOGLE_MODEL=gemini-2.0-flash-exp
GOOGLE_MODEL_LIGHT=gemini-1.5-flash
```

**推奨モデル:**

- `gemini-2.0-flash-exp` - 最新、高速、構造化出力対応
- `gemini-1.5-pro` - より高精度が必要な場合

### Anthropic Claude

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_MODEL_LIGHT=claude-3-5-haiku-20241022
```

## モデル選択のガイドライン

| 用途                           | Heavy Model                                   | Light Model                                       |
| ------------------------------ | --------------------------------------------- | ------------------------------------------------- |
| **空間推論 & 座標解析**        | GPT-4o / Gemini 2.0 Flash / Claude 3.5 Sonnet | 左記のLightバージョン                             |
| **フレーム判定（user/robot）** | -                                             | GPT-4o-mini / Gemini 1.5 Flash / Claude 3.5 Haiku |

## 注意事項

### 構造化出力 (Structured Outputs)

すべてのモデルが Pydantic `response_format` に対応している必要があります：

- ✅ OpenAI GPT-4o 以降
- ✅ Gemini 1.5 以降（JSON mode対応）
- ✅ Claude 3.5 以降

### コスト比較（参考）

| プロバイダー | Heavy Model                   | Light Model                   |
| ------------ | ----------------------------- | ----------------------------- |
| OpenAI       | gpt-4o ($5/1M tokens)         | gpt-4o-mini ($0.15/1M)        |
| Gemini       | gemini-2.0-flash (無料枠あり) | gemini-1.5-flash (無料枠あり) |
| Anthropic    | claude-3-5-sonnet ($3/1M)     | claude-3-5-haiku ($0.25/1M)   |

_料金は変動する可能性があります。最新情報は各プロバイダーの公式サイトを確認してください。_

## トラブルシューティング

### エラー: "Model not found"

→ APIキーが正しく設定されているか確認

```bash
echo $GOOGLE_API_KEY  # Linux/Mac
echo %GOOGLE_API_KEY% # Windows
```

### 構造化出力が動作しない

→ モデルが構造化出力に対応しているか確認（Gemini 1.5以降、Claude 3.5以降が必要）

### レスポンスが遅い

→ Light Modelの使用を検討（フレーム判定はLight推奨）
