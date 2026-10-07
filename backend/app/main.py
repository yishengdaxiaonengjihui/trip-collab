"""FastAPI 应用工厂。

启动：uvicorn backend.app.main:app --reload --port 8000
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import Settings
from .db import TripRepo
from .routers import members, plugins, proposals, trips, versions
from .services.trip_service import TripService

_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


class SPAStaticFiles(StaticFiles):
    """未命中的路径回落到 index.html（vue-router history 模式深链接需要）。

    注意：必须捕获 starlette 的 HTTPException —— StaticFiles 抛的是父类，
    fastapi.exceptions.HTTPException 是它的子类，捕获子类接不住。
    /api 前缀不回落，保持接口 404 的 JSON 语义。
    """

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or scope.get("path", "").startswith("/api/"):
                raise
            return await super().get_response("index.html", scope)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    repo = TripRepo(settings.db_path)
    repo.init_db()
    service = TripService(repo)

    app = FastAPI(
        title="trip-collab API",
        description="AI 多人版本化旅行协作规划系统（MVP 骨架）",
        version="0.1.0",
    )
    app.state.settings = settings
    app.state.repo = repo
    app.state.service = service

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(trips.router)
    app.include_router(proposals.router)
    app.include_router(versions.router)
    app.include_router(members.router)
    app.include_router(plugins.router)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "trip-collab"}

    # 单容器同源托管前端产物；dist 不存在时跳过（本地 dev 仍由 Vite 承担）
    dist = Path(os.environ.get("TRIP_DIST") or _DIST)
    if dist.is_dir():
        app.mount("/", SPAStaticFiles(directory=str(dist), html=True), name="spa")

    return app


app = create_app()
