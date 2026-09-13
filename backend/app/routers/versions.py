"""版本历史与回滚路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.engine.errors import TripCollabError

from ..schemas import RollbackIn, RollbackOut, VersionOut
from ..services.trip_service import TripService
from .deps import get_actor, get_service, map_error

router = APIRouter(prefix="/api/trips/{trip_id}", tags=["versions"])


@router.get("/versions", response_model=list[VersionOut])
def list_versions(trip_id: str, service: TripService = Depends(get_service)):
    try:
        return service.versions(trip_id)
    except TripCollabError as exc:
        raise map_error(exc)


@router.post("/rollback", response_model=RollbackOut)
def rollback(
    trip_id: str,
    body: RollbackIn,
    service: TripService = Depends(get_service),
    actor: str = Depends(get_actor),
):
    try:
        return service.rollback(trip_id, body.version, actor, body.reason)
    except TripCollabError as exc:
        raise map_error(exc)


@router.get("/notifications")
def list_notifications(trip_id: str, service: TripService = Depends(get_service)):
    try:
        return service.notifications(trip_id)
    except TripCollabError as exc:
        raise map_error(exc)
