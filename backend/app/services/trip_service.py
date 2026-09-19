"""业务服务层：加载/保存引擎、把 API 动作翻译为引擎操作、组装响应。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.engine.conflicts import ConflictReport
from backend.engine.engine import (
    STATUS_ADOPTED,
    STATUS_DRAFT,
    STATUS_PENDING,
    AdoptionResult,
    Proposal,
    TripEngine,
)
from backend.engine.errors import (
    ConfirmationRequiredError,
    HardConflictError,
    ProposalNotFoundError,
    SnapshotNotFoundError,
    TripCollabError,
)
from backend.engine.events import ChangeEvent
from backend.engine.state import item_to_dict

from ..db import TripRepo
from ..schemas import AdoptIn, ProposalCreate, ProposalOut, TripOut


class TripNotFoundError(TripCollabError):
    """行程不存在（HTTP 404）。"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _proposal_out(p: Proposal) -> ProposalOut:
    report: Optional[ConflictReport] = p.last_report
    return ProposalOut(
        id=p.id,
        title=p.title,
        reason=p.reason,
        created_by=p.created_by,
        status=p.status,
        emergency=p.emergency,
        created_at=p.created_at,
        submitted_at=p.submitted_at,
        adopted_at=p.adopted_at,
        adopted_version=p.adopted_version,
        reject_reason=p.reject_reason,
        resolution_note=p.resolution_note,
        events=[{"kind": e.kind, "item_id": e.item_id, "payload": e.payload} for e in p.events],
        warnings=list(report.warnings) if report else [],
        hard_conflicts=list(report.hard) if report else [],
    )


def _items_payload(engine: TripEngine) -> dict:
    return {it.id: it for it in engine.state().items.values()}


class TripService:
    def __init__(self, repo: TripRepo):
        self.repo = repo

    # ---------------- 行程 ----------------

    def create_trip(self, name: str, created_by: str) -> dict:
        trip_id = uuid.uuid4().hex
        engine = TripEngine(trip_id=trip_id)
        self.repo.create_trip(trip_id, name, created_by, _now())
        self.repo.add_member(trip_id, created_by, "owner")
        self.repo.save_state(trip_id, json.dumps(engine.to_dict(), ensure_ascii=False), _now())
        return self.get_trip(trip_id)

    def list_trips(self) -> list[dict]:
        out = []
        for meta in self.repo.list_trips():
            engine = self._load(meta["id"])
            out.append(
                {
                    "id": meta["id"],
                    "name": meta["name"],
                    "created_by": meta["created_by"],
                    "created_at": meta["created_at"],
                    "version": engine.version,
                    "item_count": len(engine.state().items),
                    "pending_count": len(engine.pending_proposals()),
                }
            )
        return out

    def get_trip(self, trip_id: str) -> dict:
        meta = self._meta_or_404(trip_id)
        engine = self._load(trip_id)
        items = engine.state().items
        days: dict[int, list[dict]] = {}
        for it in sorted(items.values(), key=lambda x: (x.day, x.position, x.id)):
            days.setdefault(it.day, []).append(item_to_dict(it))
        return {
            "id": meta["id"],
            "name": meta["name"],
            "created_by": meta["created_by"],
            "created_at": meta["created_at"],
            "version": engine.version,
            "days": days,
            "members": self.repo.list_members(trip_id),
            "pending_count": len(engine.pending_proposals()),
            "notify_count": len(engine.notifications),
        }

    # ---------------- 提议 ----------------

    def create_proposal(self, trip_id: str, data: ProposalCreate, actor: str) -> ProposalOut:
        engine = self._load(trip_id)
        p = engine.create_proposal(
            title=data.title,
            reason=data.reason,
            events=[ChangeEvent(e.kind, e.item_id, e.payload) for e in data.events],
            created_by=actor,
            emergency=data.emergency,
        )
        self._commit(trip_id, engine)
        return _proposal_out(p)

    def list_proposals(self, trip_id: str, status: Optional[str] = None) -> list[ProposalOut]:
        engine = self._load(trip_id)
        items = list(engine.proposals.values())
        if status:
            items = [p for p in items if p.status == status]
        items.sort(key=lambda p: p.created_at)
        return [_proposal_out(p) for p in items]

    def submit(self, trip_id: str, proposal_id: str, actor: str) -> ProposalOut:
        engine = self._load(trip_id)
        p = engine.submit(proposal_id, actor)
        self._commit(trip_id, engine)
        return _proposal_out(p)

    def adopt(
        self, trip_id: str, proposal_id: str, actor: str, body: AdoptIn
    ) -> ProposalOut:
        engine = self._load(trip_id)
        result: AdoptionResult = engine.adopt(
            proposal_id,
            actor,
            confirmed=body.confirmed,
            force=body.force,
            resolution_note=body.resolution_note,
        )
        self._commit(trip_id, engine)
        out = _proposal_out(engine.proposal(proposal_id))
        return out

    def reject(self, trip_id: str, proposal_id: str, actor: str, reason: str) -> ProposalOut:
        engine = self._load(trip_id)
        p = engine.reject(proposal_id, actor, reason)
        self._commit(trip_id, engine)
        return _proposal_out(p)

    def submit_emergency(self, trip_id: str, proposal_id: str, actor: str) -> ProposalOut:
        """临时备选：提交即采纳（提议需以 emergency=True 创建，且处于草稿）。"""
        engine = self._load(trip_id)
        engine.submit_emergency(proposal_id, actor)
        self._commit(trip_id, engine)
        return _proposal_out(engine.proposal(proposal_id))

    def formalize(self, trip_id: str, proposal_id: str, actor: str) -> ProposalOut:
        engine = self._load(trip_id)
        p = engine.formalize(proposal_id, actor)
        self._commit(trip_id, engine)
        return _proposal_out(p)

    def revoke(self, trip_id: str, proposal_id: str, actor: str) -> ProposalOut:
        engine = self._load(trip_id)
        p = engine.revoke(proposal_id, actor)
        self._commit(trip_id, engine)
        return _proposal_out(p)

    # ---------------- 版本 / 回滚 ----------------

    def versions(self, trip_id: str) -> list[dict]:
        engine = self._load(trip_id)
        out: list[dict] = []
        for version in range(1, engine.version + 1):
            event = engine.stream[version - 1]
            is_rollback = event.meta.get("rollback") is True
            proposal_id = None if is_rollback else event.proposal_id
            title = None
            kind = "adopt"
            if is_rollback:
                kind = "revoke" if event.meta.get("revoke_of") else "rollback"
            elif event.meta.get("emergency"):
                kind = "emergency"
            if proposal_id:
                prop = engine.proposals.get(proposal_id)
                title = prop.title if prop else None
            out.append(
                {
                    "version": version,
                    "kind": kind,
                    "proposal_id": proposal_id,
                    "title": title,
                    "adopted_at": event.adopted_at,
                    "item_count": len(engine.snapshots[version].items),
                }
            )
        return out

    def rollback(self, trip_id: str, version: int, actor: str, reason: Optional[str]) -> dict:
        engine = self._load(trip_id)
        result = engine.rollback_to(version, actor, reason)
        self._commit(trip_id, engine)
        return {
            "target_version": result.target_version,
            "new_version": result.new_version,
            "affected_proposals": result.affected_proposals,
            "compensating_event_count": result.compensating_event_count,
        }

    def notifications(self, trip_id: str) -> list[dict]:
        engine = self._load(trip_id)
        return [
            {"seq": n.seq, "kind": n.kind, "actor": n.actor, "payload": n.payload}
            for n in engine.notifications
        ]

    # ---------------- 成员 ----------------

    def add_member(self, trip_id: str, user_id: str, role: str) -> dict:
        self._meta_or_404(trip_id)
        self.repo.add_member(trip_id, user_id, role)
        return {"trip_id": trip_id, "user_id": user_id, "role": role}

    def members(self, trip_id: str) -> list[dict]:
        self._meta_or_404(trip_id)
        return self.repo.list_members(trip_id)

    def set_member_role(self, trip_id: str, user_id: str, role: str) -> dict:
        self._meta_or_404(trip_id)
        row = self.repo.set_member_role(trip_id, user_id, role)
        if row is None:
            raise TripCollabError(f"成员不存在: {user_id}")
        return row

    # ---------------- 内部 ----------------

    def _meta_or_404(self, trip_id: str) -> dict:
        meta = self.repo.get_trip(trip_id)
        if meta is None:
            raise TripNotFoundError(f"行程不存在: {trip_id}")
        return meta

    def _load(self, trip_id: str) -> TripEngine:
        raw = self.repo.load_state(trip_id)
        if raw is None:
            raise TripNotFoundError(f"行程不存在: {trip_id}")
        return TripEngine.from_dict(json.loads(raw))

    def _commit(self, trip_id: str, engine: TripEngine) -> None:
        self.repo.save_state(trip_id, json.dumps(engine.to_dict(), ensure_ascii=False), _now())
