"""路由公共依赖：仓储/服务注入 + 引擎错误到 HTTP 状态的映射。"""

from __future__ import annotations

from fastapi import HTTPException, Request

from backend.engine.errors import (
    ConfirmationRequiredError,
    HardConflictError,
    InvalidStatusError,
    ProposalNotFoundError,
    SnapshotNotFoundError,
    TripCollabError,
)

from ..db import TripRepo
from ..services.trip_service import TripNotFoundError, TripService


def get_repo(request: Request) -> TripRepo:
    return request.app.state.repo


def get_service(request: Request) -> TripService:
    return request.app.state.service


def get_actor(request: Request) -> str:
    """MVP 身份占位：读 X-User-Id 头，缺省用演示用户。"""
    return request.headers.get("X-User-Id") or request.app.state.settings.default_user


_ERROR_TO_STATUS = {
    TripNotFoundError: 404,
    HardConflictError: 409,
    ConfirmationRequiredError: 422,
    InvalidStatusError: 409,
    ProposalNotFoundError: 404,
    SnapshotNotFoundError: 404,
    TripCollabError: 400,
}


def map_error(exc: TripCollabError) -> HTTPException:
    status = _ERROR_TO_STATUS.get(type(exc), 400)
    detail = getattr(exc, "args", None)
    body = {"code": type(exc).__name__, "message": str(exc), "detail": detail[0] if detail else None}
    return HTTPException(status_code=status, detail=body)
