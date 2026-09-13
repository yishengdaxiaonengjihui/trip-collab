"""FastAPI 应用工厂。

启动：uvicorn backend.app.main:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .db import TripRepo
from .routers import members, plugins, proposals, trips, versions
from .services.trip_service import TripService


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

    return app


app = create_app()
