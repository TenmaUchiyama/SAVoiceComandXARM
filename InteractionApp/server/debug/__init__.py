"""
debug — アプリ側で確認できるデバッグログ・ブロードキャスト。

print() の代わりに debug_log.info() / .warn() / .error() を使うと、
WebSocket /status チャンネル経由でフロントエンドにリアルタイム配信される。
"""

from __future__ import annotations

import asyncio
import datetime
import json
import sys
from collections import deque
from typing import Any, Callable, Coroutine, Deque, List, Optional

from loguru import logger

# ログのフォーマット設定
# loguru のデフォルトを無効にして、カスタムフォーマットを追加
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{extra[source]: <10}</cyan> | <level>{message}</level>",
    level="DEBUG",
    enqueue=True,
)

# 最大保持件数 (REST で履歴取得する用)
_MAX_HISTORY = 500


class DebugEntry:
    __slots__ = ("ts", "level", "source", "message", "detail")

    def __init__(
        self,
        level: str,
        source: str,
        message: str,
        detail: Any = None,
    ):
        self.ts = datetime.datetime.now().isoformat(timespec="milliseconds")
        self.level = level
        self.source = source
        self.message = message
        self.detail = detail

    def to_dict(self) -> dict:
        d: dict = {
            "ts": self.ts,
            "level": self.level,
            "source": self.source,
            "message": self.message,
        }
        if self.detail is not None:
            d["detail"] = self.detail
        return d


# broadcast コールバック型
BroadcastFn = Callable[[str], Coroutine[Any, Any, None]]


class DebugLogger:
    """サーバー全体で共有するデバッグログ管理。

    使い方:
        debug_log = DebugLogger()
        debug_log.set_broadcast(hub.broadcast_debug)   # WS 配信関数をセット
        debug_log.info("robot", "Connected to xArm")
        debug_log.error("robot", "pick failed", {"x": 1, "y": 2, "reason": "not found"})
    """

    def __init__(self):
        self._history: Deque[DebugEntry] = deque(maxlen=_MAX_HISTORY)
        self._broadcast_fn: Optional[BroadcastFn] = None

    def set_broadcast(self, fn: BroadcastFn):
        """WebSocket ブロードキャスト関数を登録 (async def fn(json_str))。"""
        self._broadcast_fn = fn

    # ------ public log methods ------
    def info(self, source: str, message: str, detail: Any = None):
        self._emit("info", source, message, detail)

    def warn(self, source: str, message: str, detail: Any = None):
        self._emit("warn", source, message, detail)

    def error(self, source: str, message: str, detail: Any = None):
        self._emit("error", source, message, detail)

    def step(self, source: str, message: str, detail: Any = None):
        """処理の途中経過 (ステップ) を表す。"""
        self._emit("step", source, message, detail)

    # ------ history ------
    def get_history(self, limit: int = 100) -> List[dict]:
        items = list(self._history)[-limit:]
        return [e.to_dict() for e in items]

    def clear_history(self):
        self._history.clear()

    # ------ internal ------
    def _emit(self, level: str, source: str, message: str, detail: Any):
        entry = DebugEntry(level, source, message, detail)
        self._history.append(entry)

        # ターミナルにも出力（loguru を使用）
        # detail があればメッセージに付与
        detail_str = f" | Detail: {detail}" if detail else ""
        full_message = f"{message}{detail_str}"
        
        scoped_logger = logger.bind(source=source.upper())
        
        if level == "error":
            scoped_logger.error(full_message)
        elif level == "warn":
            scoped_logger.warning(full_message)
        elif level == "step":
            # STEP は青色にするために DEBUG レベルを使用
            scoped_logger.log("SUCCESS", f"[STEP] {full_message}")
        else:
            scoped_logger.info(full_message)

        # WS ブロードキャスト (fire-and-forget)
        if self._broadcast_fn is not None:
            packet = json.dumps(
                {"type": "debug_log", **entry.to_dict()},
                ensure_ascii=False,
                default=str,
            )
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._broadcast_fn(packet))
            except RuntimeError:
                pass  # no running loop


# シングルトンインスタンス
debug_log = DebugLogger()
