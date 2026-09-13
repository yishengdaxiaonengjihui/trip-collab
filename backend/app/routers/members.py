"""成员路由（MVP 骨架：无真实认证，仅角色记录，供邀请/权限后续落地）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.engine.errors import TripCollabError

from ..schemas import MemberIn, MemberRoleIn
from ..services.trip_service import TripService
from .deps import get_service, map_error

router = APIRouter(prefix="/api/trips/{trip_id}/members", tags=["members"])


@router.get("", response_model=list[dict])
def list_members(trip_id: str, service: TripService = Depends(get_service)):
    try:
        return service.members(trip_id)
    except TripCollabError as exc:
        raise map_error(exc)


@router.post("", response_model=dict, status_code=201)
def add_member(
    trip_id: str,
    body: MemberIn,
    service: TripService = Depends(get_service),
):
    try:
        return service.add_member(trip_id, body.user_id, body.role)
    except TripCollabError as exc:
        raise map_error(exc)


@router.put("/{user_id}", response_model=dict)
def set_role(
    trip_id: str,
    user_id: str,
    body: MemberRoleIn,
    service: TripService = Depends(get_service),
):
    try:
        return service.set_member_role(trip_id, user_id, body.role)
    except TripCollabError as exc:
        raise map_error(exc)
