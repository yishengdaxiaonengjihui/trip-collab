"""提议路由：创建/提交/采纳/拒绝/临时备选/正式化/撤销。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from backend.engine.errors import TripCollabError

from ..schemas import AdoptIn, ProposalCreate, ProposalOut, RejectIn
from ..services.trip_service import TripService
from .deps import get_actor, get_service, map_error

router = APIRouter(prefix="/api/trips/{trip_id}/proposals", tags=["proposals"])


def _guard(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except TripCollabError as exc:
        raise map_error(exc)


@router.get("", response_model=list[ProposalOut])
def list_proposals(
    trip_id: str,
    status: Optional[str] = Query(default=None),
    service: TripService = Depends(get_service),
):
    return _guard(service.list_proposals, trip_id, status)


@router.post("", response_model=ProposalOut, status_code=201)
def create_proposal(
    trip_id: str,
    body: ProposalCreate,
    service: TripService = Depends(get_service),
    actor: str = Depends(get_actor),
):
    return _guard(service.create_proposal, trip_id, body, actor)


@router.post("/{proposal_id}/submit", response_model=ProposalOut)
def submit_proposal(
    trip_id: str,
    proposal_id: str,
    service: TripService = Depends(get_service),
    actor: str = Depends(get_actor),
):
    return _guard(service.submit, trip_id, proposal_id, actor)


@router.post("/{proposal_id}/adopt", response_model=ProposalOut)
def adopt_proposal(
    trip_id: str,
    proposal_id: str,
    body: AdoptIn,
    service: TripService = Depends(get_service),
    actor: str = Depends(get_actor),
):
    return _guard(service.adopt, trip_id, proposal_id, actor, body)


@router.post("/{proposal_id}/reject", response_model=ProposalOut)
def reject_proposal(
    trip_id: str,
    proposal_id: str,
    body: RejectIn,
    service: TripService = Depends(get_service),
    actor: str = Depends(get_actor),
):
    return _guard(service.reject, trip_id, proposal_id, actor, body.reason)


@router.post("/{proposal_id}/emergency", response_model=ProposalOut)
def apply_emergency(
    trip_id: str,
    proposal_id: str,
    service: TripService = Depends(get_service),
    actor: str = Depends(get_actor),
):
    """临时备选：提交即采纳、全员立即可见。"""
    return _guard(service.submit_emergency, trip_id, proposal_id, actor)


@router.post("/{proposal_id}/formalize", response_model=ProposalOut)
def formalize_proposal(
    trip_id: str,
    proposal_id: str,
    service: TripService = Depends(get_service),
    actor: str = Depends(get_actor),
):
    return _guard(service.formalize, trip_id, proposal_id, actor)


@router.post("/{proposal_id}/revoke", response_model=ProposalOut)
def revoke_proposal(
    trip_id: str,
    proposal_id: str,
    service: TripService = Depends(get_service),
    actor: str = Depends(get_actor),
):
    return _guard(service.revoke, trip_id, proposal_id, actor)
