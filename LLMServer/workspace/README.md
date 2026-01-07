## 概要

FastAPI を使った簡単なAPIサーバです。

- **GET `/`**: `Hello World` を返します
- **POST `/llm`**: 文字列を受け取り、LangChain(OpenAI) で推論して返します

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
uvicorn app:app --host 0.0.0.0 --port 8000
```

## 使い方

### Hello World

```bash
curl http://localhost:8000/
```

### LLM 推論

```bash
curl -X POST http://localhost:8000/llm \
  -H "Content-Type: application/json" \
  -d '{"text":"こんにちは。短く自己紹介して。"}'
```


