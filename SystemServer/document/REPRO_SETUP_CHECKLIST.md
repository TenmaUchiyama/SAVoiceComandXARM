# 技術構成メモ（役割ベース）

このドキュメントは、**環境再現手順ではなく**、
「このプロジェクトで何をどの技術で実現しているか」を簡潔に整理したものです。

## 1) 全体像

- フロント/クライアント: Unity（HoloLens/MR 側）
- バックエンド: Python サーバ
- 推論: LLM（OpenAI モデル）
- ロボット制御: xArm SDK

---

## 2) LLM サーバ周り

- LLM を呼び出しているのは Python 側の `LLM_Agent/agent.py`
- LLM 呼び出しのフレームワークは **LangChain**（`create_agent` を使用）
- モデル指定は `openai:<model_name>` 形式で OpenAI モデルを利用
- プロンプトは `src/LLM_Agent/prompt/` 配下のテキストを読み込んで使用

要するに:

- **LLM サーバーは LLM 推論を担当**
- **推論の実装基盤は LangChain**

---

## 3) サーバ実装

- サーバ本体は **FastAPI**
- WebSocket を使って Unity と双方向通信
- エンドポイントは主に `/spatial`, `/status`, `/` を利用

要するに:

- **サーバそのものは FastAPI**
- **Unity 連携は WebSocket 中心**

---

## 4) データ検証・型

- リクエスト/レスポンスの構造化には **Pydantic** を使用
- 空間参照リクエストや内部データの検証を Python 側で実施

---

## 5) ロボット制御

- xArm 実機制御は **xArm-Python-SDK**（`xarm.wrapper.XArmAPI`）
- サーバから pick 動作などのコマンドを実行
- 環境変数でロボット有効/無効を切り替える構成

---

## 6) Unity 側（MR）

- Unity 2022 系で構築
- MRTK / OpenXR 系パッケージを使用
- WebSocket クライアントとして `NativeWebSocket` を利用

---

## 7) このプロジェクトを一言で

**Unity(MR) + FastAPI(WebSocket) + LangChain(OpenAI LLM) + xArm SDK** で、
空間参照発話をロボット操作につなぐ構成。

---

## 8) 参照箇所（コード）

- `SystemServer/src/server.py`（FastAPI / WebSocket / サーバ処理）
- `SystemServer/src/LLM_Agent/agent.py`（LangChain 経由の LLM 呼び出し）
- `SystemServer/src/spatial_pipeline.py`（空間データの整形・検証）
- `SystemServer/src/XARmOperator.py`（xArm SDK による実機制御）
- `SpatiallyAwareRobotArm/Packages/manifest.json`（Unity 側パッケージ）
