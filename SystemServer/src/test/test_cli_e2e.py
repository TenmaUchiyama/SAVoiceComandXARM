"""
Unity なしでサーバーの全フローを対話的にテストする CLI ツール。

使い方:
  1) サーバーを起動:  uvicorn src.server:app --host 0.0.0.0 --port 8765
  2) 別ターミナルで:   python src/test/test_cli_e2e.py [--url ws://localhost:8765]

各ステップごとに結果を表示し、Enter で次に進みます。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from typing import Any, Dict, Optional

try:
    import websockets
except ImportError:
    print("websockets パッケージが必要です。  pip install websockets")
    sys.exit(1)

try:
    import httpx
except ImportError:
    httpx = None  # REST テストはスキップ


# ──────────────────────────────────────────
# テストデータ (README の例をベースに拡張)
# ──────────────────────────────────────────

SAMPLE_OBJECTS = [
    {"id": "obj_001", "label": "box",    "color": "red",   "position": {"x": 0.3,  "y": 0.75, "z": 0.2}},
    {"id": "obj_002", "label": "cup",    "color": "blue",  "position": {"x": -0.2, "y": 0.75, "z": 0.5}},
    {"id": "obj_003", "label": "bottle", "color": "green", "position": {"x": 0.1,  "y": 0.75, "z": 0.8}},
    {"id": "obj_004", "label": "box",    "color": "red",   "position": {"x": 0.6,  "y": 0.75, "z": 0.4}},
]

SAMPLE_USER_POSE = {
    "position": {"x": 0.5, "y": 1.2, "z": -0.8},
    "forward":  {"x": 0.0, "y": 0.0, "z": 1.0},
    "up":       {"x": 0.0, "y": 1.0, "z": 0.0},
}

SAMPLE_ROBOT_POSE = {
    "position": {"x": -0.5, "y": 0.7, "z": 0.0},
    "forward":  {"x": 1.0,  "y": 0.0, "z": 0.0},
}

# ──────────────────────────────────────────
# ユーティリティ
# ──────────────────────────────────────────

CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
RESET   = "\033[0m"
BOLD    = "\033[1m"


def _pretty(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def _header(title: str):
    width = 60
    print(f"\n{CYAN}{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}{RESET}")


def _sub_header(title: str):
    print(f"\n{YELLOW}--- {title} ---{RESET}")


def _ok(msg: str):
    print(f"{GREEN}[OK]{RESET} {msg}")


def _err(msg: str):
    print(f"{RED}[ERROR]{RESET} {msg}")


def _pause(prompt: str = "Enter で次のステップへ (q で終了)"):
    ans = input(f"\n{BOLD}{prompt}{RESET} > ").strip().lower()
    if ans in ("q", "quit", "exit"):
        print("終了します。")
        sys.exit(0)


def _new_id() -> str:
    return str(uuid.uuid4())


# ──────────────────────────────────────────
# WebSocket テスト
# ──────────────────────────────────────────

async def ws_send_recv(uri: str, payload: dict, timeout: float = 30.0) -> dict:
    """WebSocket に 1 メッセージを送信し、レスポンスを受け取って切断する。"""
    async with websockets.connect(uri) as ws:
        msg = json.dumps(payload, ensure_ascii=False)
        _sub_header("送信メッセージ")
        print(_pretty(payload))
        await ws.send(msg)
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        resp = json.loads(raw)
        _sub_header("受信レスポンス")
        print(_pretty(resp))
        return resp


async def step_status(base_ws: str):
    """Step 0: /status で稼働確認。"""
    _header("Step 0: サーバー稼働確認 (/status)")
    uri = f"{base_ws}/status"
    try:
        async with websockets.connect(uri) as ws:
            await ws.send("ping")
            raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
            resp = json.loads(raw)
            _sub_header("ステータス")
            print(_pretty(resp))
            _ok(f"sessions={resp.get('active_sessions')}, robot={resp.get('robot_enabled')}")
    except Exception as e:
        _err(f"接続失敗: {e}")
        print(f"サーバーが {base_ws} で起動しているか確認してください。")
        sys.exit(1)


async def step_spatial_request(base_ws: str, utterance: str) -> str:
    """Step 1: spatial_reference_request を送信。request_id を返す。"""
    _header("Step 1: 空間参照リクエスト (spatial_reference_request)")
    request_id = _new_id()
    payload = {
        "type": "spatial_reference_request",
        "request_id": request_id,
        "utterance": {"text": utterance, "language": "ja"},
        "user_pose": SAMPLE_USER_POSE,
        "objects": SAMPLE_OBJECTS,
        "robot_pose": SAMPLE_ROBOT_POSE,
    }
    uri = f"{base_ws}/spatial"
    resp = await ws_send_recv(uri, payload)

    if resp.get("type") == "spatial_reference_result":
        target = resp.get("target", {})
        _ok(f"ターゲット: {target.get('object_id')}  (confidence={target.get('confidence')}, frame={target.get('reference_frame')})")
        candidates = resp.get("ranked_candidates", [])
        print(f"  候補数: {len(candidates)}")
        for c in candidates:
            print(f"    {c.get('object_id')}: score={c.get('score')}")
    else:
        _err(f"想定外の type={resp.get('type')} — {resp.get('message', '')}")

    return request_id


async def step_refinement(base_ws: str, original_request_id: str, utterance: str) -> str:
    """Step 2: refinement_request を送信。"""
    _header("Step 2: 修正リクエスト (refinement_request)")
    request_id = _new_id()
    payload = {
        "type": "refinement_request",
        "request_id": request_id,
        "original_request_id": original_request_id,
        "utterance": {"text": utterance, "language": "ja"},
    }
    uri = f"{base_ws}/spatial"
    resp = await ws_send_recv(uri, payload)

    if resp.get("type") == "spatial_reference_result":
        target = resp.get("target", {})
        _ok(f"ターゲット: {target.get('object_id')}  (confidence={target.get('confidence')})")
    else:
        _err(f"type={resp.get('type')} — {resp.get('message', '')}")

    return request_id


async def step_confirmation(base_ws: str, request_id: str, object_id: str):
    """Step 3: confirmation を送信 → robot_command を受信。"""
    _header("Step 3: 確認 (confirmation)")
    payload = {
        "type": "confirmation",
        "request_id": request_id,
        "confirmed_object_id": object_id,
        "action": "pick",
    }
    uri = f"{base_ws}/spatial"
    resp = await ws_send_recv(uri, payload)

    if resp.get("type") == "robot_command":
        _ok(f"action={resp.get('action')}, target={resp.get('target_object_id')}, status={resp.get('status')}")
    else:
        _err(f"type={resp.get('type')} — {resp.get('message', '')}")


# ──────────────────────────────────────────
# REST API テスト
# ──────────────────────────────────────────

async def step_rest_command_cord(base_http: str, utterance: str):
    """Step 4: POST /command_cord (座標ベース LLM)。"""
    _header("Step 4: REST /command_cord")
    if httpx is None:
        _err("httpx が未インストール — REST テストをスキップします (pip install httpx)")
        return
    payload = {
        "utterance": utterance,
        "user": {
            "position": [SAMPLE_USER_POSE["position"]["x"],
                         SAMPLE_USER_POSE["position"]["y"],
                         SAMPLE_USER_POSE["position"]["z"]],
            "forward":  [SAMPLE_USER_POSE["forward"]["x"],
                         SAMPLE_USER_POSE["forward"]["y"],
                         SAMPLE_USER_POSE["forward"]["z"]],
        },
        "robot": {
            "position": [SAMPLE_ROBOT_POSE["position"]["x"],
                         SAMPLE_ROBOT_POSE["position"]["y"],
                         SAMPLE_ROBOT_POSE["position"]["z"]],
            "forward":  [SAMPLE_ROBOT_POSE["forward"]["x"],
                         SAMPLE_ROBOT_POSE["forward"]["y"],
                         SAMPLE_ROBOT_POSE["forward"]["z"]],
        },
        "objects": [
            {"id": obj["id"], "position": [obj["position"]["x"], obj["position"]["y"], obj["position"]["z"]]}
            for obj in SAMPLE_OBJECTS
        ],
    }
    _sub_header("送信ペイロード")
    print(_pretty(payload))

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{base_http}/command_cord", json=payload)
    _sub_header(f"HTTP {resp.status_code}")
    try:
        body = resp.json()
        print(_pretty(body))
        if body.get("status") == "ok":
            _ok(f"target_id={body.get('target_id')}")
        else:
            _err(f"status={body.get('status')}")
    except Exception:
        print(resp.text[:500])


async def step_rest_command(base_http: str, utterance: str):
    """Step 5: POST /command (features ベース LLM)。"""
    _header("Step 5: REST /command")
    if httpx is None:
        _err("httpx が未インストール — REST テストをスキップします (pip install httpx)")
        return
    payload = {
        "utterance": utterance,
        "user": {
            "position": [SAMPLE_USER_POSE["position"]["x"],
                         SAMPLE_USER_POSE["position"]["y"],
                         SAMPLE_USER_POSE["position"]["z"]],
            "forward":  [SAMPLE_USER_POSE["forward"]["x"],
                         SAMPLE_USER_POSE["forward"]["y"],
                         SAMPLE_USER_POSE["forward"]["z"]],
        },
        "robot": {
            "position": [SAMPLE_ROBOT_POSE["position"]["x"],
                         SAMPLE_ROBOT_POSE["position"]["y"],
                         SAMPLE_ROBOT_POSE["position"]["z"]],
            "forward":  [SAMPLE_ROBOT_POSE["forward"]["x"],
                         SAMPLE_ROBOT_POSE["forward"]["y"],
                         SAMPLE_ROBOT_POSE["forward"]["z"]],
        },
    }
    _sub_header("送信ペイロード (objects 省略 → 固定グリッド使用)")
    print(_pretty(payload))

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{base_http}/command", json=payload)
    _sub_header(f"HTTP {resp.status_code}")
    try:
        body = resp.json()
        print(_pretty(body))
        if body.get("status") == "ok":
            _ok(f"target_id={body.get('target_id')}")
        else:
            _err(f"status={body.get('status')}")
    except Exception:
        print(resp.text[:500])


# ──────────────────────────────────────────
# メインフロー
# ──────────────────────────────────────────

async def main(base_ws: str, base_http: str):
    print(f"""
{BOLD}╔══════════════════════════════════════════════════╗
║  Spatial Reference Server — CLI E2E テスト       ║
║  WebSocket : {base_ws:<36s}║
║  HTTP      : {base_http:<36s}║
╚══════════════════════════════════════════════════╝{RESET}
""")

    # ── Step 0: ステータス確認 ──
    await step_status(base_ws)
    _pause()

    # ── Step 1: spatial_reference_request ──
    utterance1 = input(f"{BOLD}Step1 発話を入力 (空欄でデフォルト: '右側の赤い箱を取って'){RESET}\n > ").strip()
    if not utterance1:
        utterance1 = "右側の赤い箱を取って"
    request_id = await step_spatial_request(base_ws, utterance1)
    _pause()

    # ── Step 2: refinement_request ──
    utterance2 = input(f"{BOLD}Step2 修正発話を入力 (空欄でデフォルト: 'もう少し奥のやつ' / skip でスキップ){RESET}\n > ").strip()
    if utterance2.lower() == "skip":
        print("refinement をスキップします。")
        latest_request_id = request_id
    else:
        if not utterance2:
            utterance2 = "もう少し奥のやつ"
        latest_request_id = await step_refinement(base_ws, request_id, utterance2)
    _pause()

    # ── Step 3: confirmation ──
    obj_id = input(f"{BOLD}Step3 確定する object_id (空欄でデフォルト: 'obj_001'){RESET}\n > ").strip()
    if not obj_id:
        obj_id = "obj_001"
    await step_confirmation(base_ws, latest_request_id, obj_id)
    _pause()

    # ── Step 4: REST /command_cord ──
    utterance3 = input(f"{BOLD}Step4 発話を入力 for /command_cord (空欄でデフォルト: '手前の青いカップ' / skip){RESET}\n > ").strip()
    if utterance3.lower() == "skip":
        print("/command_cord をスキップします。")
    else:
        if not utterance3:
            utterance3 = "手前の青いカップ"
        await step_rest_command_cord(base_http, utterance3)
    _pause()

    # ── Step 5: REST /command ──
    utterance4 = input(f"{BOLD}Step5 発話を入力 for /command (空欄でデフォルト: '一番近いやつ' / skip){RESET}\n > ").strip()
    if utterance4.lower() == "skip":
        print("/command をスキップします。")
    else:
        if not utterance4:
            utterance4 = "一番近いやつ"
        await step_rest_command(base_http, utterance4)

    _header("テスト完了")
    print("全ステップ終了しました。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spatial Server CLI E2E テスト")
    parser.add_argument("--host", default="localhost", help="サーバーホスト (default: localhost)")
    parser.add_argument("--port", type=int, default=8765, help="サーバーポート (default: 8765)")
    args = parser.parse_args()

    base_ws   = f"ws://{args.host}:{args.port}"
    base_http = f"http://{args.host}:{args.port}"

    asyncio.run(main(base_ws, base_http))
