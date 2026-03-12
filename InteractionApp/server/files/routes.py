"""
files.routes — Grid / Robot 設定ファイル REST エンドポイント。

/api/files/... 以下のルートを定義。
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from debug import debug_log

router = APIRouter(prefix="/api/files", tags=["files"])


def init_file_routes(files, hub) -> APIRouter:
    """FileManager と WSHub を注入してルーターを返す。"""
    from hub import RESTORE_GRID_EVENT, RESTORE_ROBOT_EVENT

    # ---- Grid configs ----
    @router.get("/grids")
    async def grids_list():
        return files.list_grid_names()

    @router.get("/grids/{name}")
    async def grids_get(name: str):
        try:
            filename, data = files.load_grid(name)
            return {"filename": filename, "data": data}
        except FileNotFoundError as e:
            return JSONResponse({"error": str(e)}, 404)

    @router.post("/grids/save")
    async def grids_save(request: Request):
        data = await request.json()
        path = files.save_grid(data)
        debug_log.info("files", f"Grid saved: {path.name}")
        return {"success": True, "filename": path.name}

    @router.get("/grids/latest")
    async def grids_latest():
        try:
            name, data = files.load_grid()
            return {"filename": name, "data": data}
        except FileNotFoundError as e:
            return JSONResponse({"error": str(e)}, 404)

    @router.post("/grids/restore")
    async def grids_restore(request: Request):
        body = await request.json()
        filename = body.get("filename")
        grid_data = body.get("gridPoints")
        if grid_data is None:
            try:
                filename, grid_data = files.load_grid(filename)
            except FileNotFoundError as e:
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
        return files.list_robot_names()

    @router.get("/robots/{name}")
    async def robots_get(name: str):
        try:
            filename, data = files.load_robot(name)
            return {"filename": filename, "data": data}
        except FileNotFoundError as e:
            return JSONResponse({"error": str(e)}, 404)

    @router.post("/robots/save")
    async def robots_save(request: Request):
        data = await request.json()
        path = files.save_robot(data)
        debug_log.info("files", f"Robot config saved: {path.name}")
        return {"success": True, "filename": path.name}

    @router.get("/robots/latest")
    async def robots_latest():
        try:
            name, data = files.load_robot()
            return {"filename": name, "data": data}
        except FileNotFoundError as e:
            return JSONResponse({"error": str(e)}, 404)

    @router.post("/robots/restore")
    async def robots_restore(request: Request):
        body = await request.json()
        filename = body.get("filename")
        marker_data = body.get("markerData")
        if marker_data is None:
            try:
                filename, marker_data = files.load_robot(filename)
            except FileNotFoundError as e:
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
