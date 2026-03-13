"""
files.routes — Grid / Robot 設定ファイル REST エンドポイント。

/api/files/... 以下のルートを定義。
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from loguru import logger

from debug import debug_log

# loguru は debug モジュールですでに初期化されている想定
log = logger.bind(source="FILES-API")

router = APIRouter(prefix="/api/files", tags=["files"])


def init_file_routes(files, hub) -> APIRouter:
    """FileManager と WSHub を注入してルーターを返す。"""
    from hub import RESTORE_GRID_EVENT, RESTORE_ROBOT_EVENT

    # ---- Grid configs ----
    @router.get("/grids")
    async def grids_list():
        log.info("GET /grids")
        return files.list_grid_names()

    @router.get("/grids/{name}")
    async def grids_get(name: str):
        log.info(f"GET /grids/{name}")
        try:
            filename, data = files.load_grid(name)
            return {"filename": filename, "data": data}
        except FileNotFoundError as e:
            debug_log.error("files", f"GET /grids/{name} failed: {e}", {"name": name})
            return JSONResponse({"error": str(e)}, 404)

    @router.post("/grids/save")
    async def grids_save(request: Request):
        body = await request.json()
        log.info("POST /grids/save")
        data = body.get("data") if isinstance(body, dict) and "data" in body else body
        filename = body.get("filename") if isinstance(body, dict) else None
        path = files.save_grid(data, filename=filename)
        debug_log.info("files", f"Grid saved: {path.name}")
        return {"success": True, "filename": path.name}

    @router.get("/grids/latest")
    async def grids_latest():
        log.info("GET /grids/latest")
        try:
            name, data = files.load_grid()
            return {"filename": name, "data": data}
        except FileNotFoundError as e:
            return JSONResponse({"error": str(e)}, 404)

    @router.post("/grids/restore")
    async def grids_restore(request: Request):
        body = await request.json()
        filename = body.get("filename")
        log.info(f"POST /grids/restore filename={filename}")
        grid_data = body.get("gridPoints")
        if grid_data is None:
            try:
                filename, grid_data = files.load_grid(filename)
            except FileNotFoundError as e:
                debug_log.error("files", f"POST /grids/restore load failed: {e}", {"filename": filename})
                return JSONResponse({"error": str(e)}, 404)
        payload = {
            "type": "grid_config",
            "filename": filename or "",
            "gridPoints": grid_data,
        }
        await hub.send_legacy_to("unity", RESTORE_GRID_EVENT, payload)
        debug_log.info("files", f"Grid restore sent: {filename}")
        return {"success": True, "message": f"restore sent: {filename}"}

    # ---- Robot marker configs ----
    @router.get("/robots")
    async def robots_list():
        log.info("GET /robots")
        return files.list_robot_names()

    @router.get("/robots/{name}")
    async def robots_get(name: str):
        log.info(f"GET /robots/{name}")
        try:
            filename, data = files.load_robot(name)
            return {"filename": filename, "data": data}
        except FileNotFoundError as e:
            debug_log.error("files", f"GET /robots/{name} failed: {e}", {"name": name})
            return JSONResponse({"error": str(e)}, 404)

    @router.post("/robots/save")
    async def robots_save(request: Request):
        log.info("POST /robots/save")
        body = await request.json()
        data = body.get("data") if isinstance(body, dict) and "data" in body else body
        filename = body.get("filename") if isinstance(body, dict) else None
        path = files.save_robot(data, filename=filename)
        debug_log.info("files", f"Robot config saved: {path.name}")
        return {"success": True, "filename": path.name}

    @router.get("/robots/latest")
    async def robots_latest():
        log.info("GET /robots/latest")
        try:
            name, data = files.load_robot()
            return {"filename": name, "data": data}
        except FileNotFoundError as e:
            debug_log.error("files", f"GET /robots/latest failed: {e}", {"error": str(e)})
            return JSONResponse({"error": str(e)}, 404)

    @router.post("/robots/restore")
    async def robots_restore(request: Request):
        body = await request.json()
        filename = body.get("filename")
        log.info(f"POST /robots/restore filename={filename}")
        marker_data = body.get("markerData")
        if marker_data is None:
            try:
                filename, marker_data = files.load_robot(filename)
            except FileNotFoundError as e:
                debug_log.error("files", f"POST /robots/restore load failed: {e}", {"filename": filename})
                return JSONResponse({"error": str(e)}, 404)
        payload = {
            "type": "marker_config",
            "filename": filename or "",
            "markerData": marker_data,
        }
        await hub.send_legacy_to("unity", RESTORE_ROBOT_EVENT, payload)
        debug_log.info("files", f"Robot config restore sent: {filename}")
        return {"success": True, "message": f"restore sent: {filename}"}

    return router
