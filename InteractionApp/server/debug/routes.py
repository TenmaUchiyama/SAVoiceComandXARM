"""
debug.routes — デバッグログ REST エンドポイント。

/api/debug/... 以下のルートを定義。
"""

from __future__ import annotations

from fastapi import APIRouter

from debug import debug_log

router = APIRouter(prefix="/api/debug", tags=["debug"])


def init_debug_routes() -> APIRouter:

    @router.get("/logs")
    async def debug_logs():
        """デバッグログ履歴を返す (最新 100 件)。"""
        return {"logs": debug_log.get_history(100)}

    @router.get("/logs/all")
    async def debug_logs_all():
        """デバッグログ履歴を全件返す。"""
        return {"logs": debug_log.get_history(500)}

    @router.post("/logs/clear")
    async def debug_logs_clear():
        """デバッグログ履歴をクリア。"""
        debug_log.clear_history()
        return {"success": True, "message": "logs cleared"}

    return router
