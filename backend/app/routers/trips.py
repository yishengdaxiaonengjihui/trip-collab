"""行程路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.engine.errors import TripCollabError

from ..schemas import TripBrief, TripCreate, TripOut
from ..services.trip_service import TripService
from .deps import get_actor, get_service, map_error

router = APIRouter(prefix="/api/trips", tags=["trips"])


@router.post("", response_model=TripOut, status_code=201)
def create_trip(
    body: TripCreate,
    service: TripService = Depends(get_service),
    actor: str = Depends(get_actor),
):
    return service.create_trip(body.name, actor)


@router.get("", response_model=list[TripBrief])
def list_trips(service: TripService = Depends(get_service)):
    return service.list_trips()


@router.get("/{trip_id}", response_model=TripOut)
def get_trip(trip_id: str, service: TripService = Depends(get_service)):
    try:
        return service.get_trip(trip_id)
    except TripCollabError as exc:
        raise map_error(exc)
