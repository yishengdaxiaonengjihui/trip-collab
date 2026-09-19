"""TripEngine：一个旅行项目的定稿行程引擎（事件溯源原型）。

用法示例：

    engine = TripEngine()
    p = engine.create_proposal(
        "更换酒店", "原酒店评价差",
        [ChangeEvent(EVENT_UPDATED, "hotel1", {"title": "全季酒店"})],
        created_by="u1",
    )
    engine.submit(p.id)
    engine.adopt(p.id, actor="admin", confirmed=True)
    engine.rollback_to(0, actor="admin")
"""

from __future__ import annotations

import copy
import itertools
import uuid
from dataclasses import dataclass, field
from typing import Optional

from .conflicts import ConflictReport, detect_conflicts
from .errors import (
    ConfirmationRequiredError,
    HardConflictError,
    InvalidStatusError,
    ProposalNotFoundError,
    SnapshotNotFoundError,
    TripCollabError,
)
from .events import (
    EVENT_CREATED,
    EVENT_DELETED,
    EVENT_UPDATED,
    ChangeEvent,
    StreamEvent,
)
from .state import Item, TripState, apply_event, dict_to_item, item_to_dict

STATUS_DRAFT = "draft"  # 草稿
STATUS_PENDING = "pending"  # 待审核
STATUS_ADOPTED = "adopted"  # 已采纳（含 emergency 提交即采纳）
STATUS_REJECTED = "rejected"  # 已拒绝
STATUS_REVOKED = "revoked"  # 已撤销（仅 emergency 提议）

_ITEM_FIELDS = ("day", "position", "title", "refs", "amount", "note", "time", "tag")


@dataclass
class Proposal:
    """一份修改提议：一组批量操作事件 + 状态机。"""

    id: str
    title: str
    reason: str
    created_by: str
    events: list[ChangeEvent]
    status: str = STATUS_DRAFT
    emergency: bool = False
    created_at: int = 0
    submitted_at: Optional[int] = None
    adopted_at: Optional[int] = None
    adopted_version: Optional[int] = None  # 采纳后的事件流版本（回滚影响判定用）
    reject_reason: Optional[str] = None
    resolution_note: Optional[str] = None  # 硬冲突人工判定的记录
    last_report: Optional[ConflictReport] = None  # 最近一次采纳/紧急应用时的冲突报告


@dataclass
class Notification:
    """应用内通知记录（MVP 原型级：仅记录，不实现推送）。"""

    seq: int
    kind: str
    actor: str
    payload: dict = field(default_factory=dict)


@dataclass
class AdoptionResult:
    proposal_id: str
    version: int
    report: ConflictReport
    merged_event_count: int


@dataclass
class RollbackResult:
    target_version: int
    new_version: int
    affected_proposals: list[str]
    compensating_event_count: int


class TripEngine:
    def __init__(self, trip_id: Optional[str] = None):
        self.trip_id = trip_id or uuid.uuid4().hex
        self.stream: list[StreamEvent] = []  # append-only 定稿事件流
        self.proposals: dict[str, Proposal] = {}
        self.snapshots: dict[int, TripState] = {0: TripState()}  # 版本 -> 不可变状态快照
        self.notifications: list[Notification] = []
        self._clock = itertools.count(1)
        self._seq = itertools.count(1)
        self._state: TripState = TripState()  # 实时定稿状态（回放结果）

    # ---------------- 只读访问 ----------------

    @property
    def version(self) -> int:
        return len(self.stream)

    def state(self) -> TripState:
        """当前定稿状态（= 事件流全量回放结果）。"""
        return self._state

    def state_at(self, version: int) -> TripState:
        """历史版本快照（副本，后续修改不影响）。"""
        snapshot = self.snapshots.get(version)
        if snapshot is None:
            raise SnapshotNotFoundError(
                f"版本 {version} 没有快照（可用: {sorted(self.snapshots)}）"
            )
        return snapshot

    def event_history(self, version: Optional[int] = None) -> list[StreamEvent]:
        return list(self.stream[:version])

    def proposal(self, proposal_id: str) -> Proposal:
        p = self.proposals.get(proposal_id)
        if p is None:
            raise ProposalNotFoundError(proposal_id)
        return p

    def pending_proposals(self) -> list[Proposal]:
        return [p for p in self.proposals.values() if p.status == STATUS_PENDING]

    # ---------------- 提议生命周期 ----------------

    def create_proposal(
        self,
        title: str,
        reason: str,
        events: list[ChangeEvent],
        created_by: str,
        emergency: bool = False,
    ) -> Proposal:
        if not events:
            raise TripCollabError("提议不能为空：至少包含一条修改事件")
        for e in events:
            if e.kind not in (EVENT_CREATED, EVENT_UPDATED, EVENT_DELETED):
                raise TripCollabError(f"未知事件类型: {e.kind}")
            if e.kind == EVENT_CREATED and not isinstance(e.payload, dict):
                raise TripCollabError(f"新增事件 payload 必须是条目字段 dict: {e.item_id}")
        p = Proposal(
            id=uuid.uuid4().hex,
            title=title,
            reason=reason,
            created_by=created_by,
            events=list(events),
            emergency=emergency,
            created_at=next(self._clock),
        )
        self.proposals[p.id] = p
        self.notifications.append(
            Notification(next(self._clock), "proposal_created", created_by, {"proposal_id": p.id, "title": p.title})
        )
        return p

    def submit(self, proposal_id: str, actor: str) -> Proposal:
        """草稿 -> 待审核。"""
        p = self.proposal(proposal_id)
        if p.status != STATUS_DRAFT:
            raise InvalidStatusError(f"仅草稿可提交，当前状态: {p.status}")
        p.status = STATUS_PENDING
        p.submitted_at = next(self._clock)
        self.notifications.append(
            Notification(next(self._clock), "proposal_submitted", actor, {"proposal_id": p.id})
        )
        return p

    def reject(self, proposal_id: str, actor: str, reason: str) -> Proposal:
        """待审核 -> 已拒绝：变更丢弃，但完整记录保留。"""
        p = self.proposal(proposal_id)
        if p.status != STATUS_PENDING:
            raise InvalidStatusError(f"仅待审核提议可拒绝，当前状态: {p.status}")
        p.status = STATUS_REJECTED
        p.reject_reason = reason
        self.notifications.append(
            Notification(next(self._clock), "proposal_rejected", actor, {"proposal_id": p.id, "reason": reason})
        )
        return p

    def adopt(
        self,
        proposal_id: str,
        actor: str,
        confirmed: bool = False,
        force: bool = False,
        resolution_note: Optional[str] = None,
    ) -> AdoptionResult:
        """采纳提议：合并进定稿。

        confirmed: 软冲突自动合并 / 依赖告警时需要的人工复核确认。
        force:     硬冲突时的人工判定放行（记录 resolution_note）。
        """
        p = self.proposal(proposal_id)
        if p.status != STATUS_PENDING:
            raise InvalidStatusError(f"仅待审核提议可采纳，当前状态: {p.status}")

        report = detect_conflicts(
            p.events, self._state, [q for q in self.pending_proposals() if q.id != p.id]
        )
        if report.hard:
            if not force:
                raise HardConflictError(report.hard)
            p.resolution_note = resolution_note or f"管理员 {actor} 强制人工判定放行"
        elif (len(p.events) > 1 or report.warnings) and not confirmed:
            raise ConfirmationRequiredError(report.warnings)

        p.last_report = report
        base_version = self.version
        for e in p.events:
            self._apply(
                StreamEvent(next(self._seq), e.kind, e.item_id, e.payload, p.id, next(self._clock))
            )
        p.status = STATUS_ADOPTED
        p.adopted_at = next(self._clock)
        p.adopted_version = self.version
        self.notifications.append(
            Notification(
                next(self._clock),
                "proposal_adopted",
                actor,
                {
                    "proposal_id": p.id,
                    "base_version": base_version,
                    "merged_event_count": len(p.events),
                    "warnings": report.warnings,
                },
            )
        )
        return AdoptionResult(p.id, self.version, report, len(p.events))

    # ---------------- 临时备选（emergency） ----------------

    def submit_emergency(self, proposal_id: str, actor: str) -> AdoptionResult:
        """临时备选：提交即采纳，全员立即可见；可事后正式化或撤销。

        紧急场景绕过硬冲突/复核拦截，但冲突告警会记录在提议上并通知。
        """
        p = self.proposal(proposal_id)
        if p.status != STATUS_DRAFT:
            raise InvalidStatusError(f"仅草稿可作为临时备选提交，当前状态: {p.status}")

        report = detect_conflicts(p.events, self._state, self.pending_proposals())
        p.last_report = report
        p.emergency = True
        base_version = self.version
        for e in p.events:
            self._apply(
                StreamEvent(
                    next(self._seq), e.kind, e.item_id, e.payload, p.id, next(self._clock),
                    meta={"emergency": True},
                )
            )
        p.status = STATUS_ADOPTED
        p.adopted_at = next(self._clock)
        p.adopted_version = self.version
        self.notifications.append(
            Notification(
                next(self._clock),
                "emergency_applied",
                actor,
                {
                    "proposal_id": p.id,
                    "base_version": base_version,
                    "merged_event_count": len(p.events),
                    "warnings": report.warnings,
                    "hard_conflicts": report.hard,
                },
            )
        )
        return AdoptionResult(p.id, self.version, report, len(p.events))

    def formalize(self, proposal_id: str, actor: str) -> Proposal:
        """临时备选正式化：紧急标记移除，转为普通已采纳提议。"""
        p = self.proposal(proposal_id)
        if p.status != STATUS_ADOPTED or not p.emergency:
            raise InvalidStatusError("仅已采纳的临时备选可正式化")
        p.emergency = False
        self.notifications.append(
            Notification(next(self._clock), "proposal_formalized", actor, {"proposal_id": p.id})
        )
        return p

    def revoke(self, proposal_id: str, actor: str) -> Proposal:
        """撤销临时备选：追加逆操作事件，状态回到该提议生效前，历史保留。"""
        p = self.proposal(proposal_id)
        if p.status != STATUS_ADOPTED or not p.emergency:
            raise InvalidStatusError("仅已采纳的临时备选可撤销")
        base_version = p.adopted_version - len(p.events)  # 采纳前版本（事件连续入流）
        base_state = self.state_at(base_version)
        for e in reversed(p.events):
            comp = self._inverse_event(e, base_state)
            self._apply(
                StreamEvent(
                    next(self._seq), comp.kind, comp.item_id, comp.payload, p.id, next(self._clock),
                    meta={"rollback": True, "revoke_of": p.id},
                )
            )
        p.status = STATUS_REVOKED
        self.notifications.append(
            Notification(next(self._clock), "proposal_revoked", actor, {"proposal_id": p.id})
        )
        return p

    def _inverse_event(self, e: ChangeEvent, base_state: TripState) -> ChangeEvent:
        """基于采纳前状态生成逆操作事件（补偿事件）。"""
        if e.kind == EVENT_CREATED:
            return ChangeEvent(EVENT_DELETED, e.item_id)
        if e.kind == EVENT_DELETED:
            item = base_state.items[e.item_id]
            return ChangeEvent(EVENT_CREATED, e.item_id, item_to_dict(item))
        if e.kind == EVENT_UPDATED:
            item = base_state.items[e.item_id]
            changes = {k: getattr(item, k) for k in e.payload}
            return ChangeEvent(EVENT_UPDATED, e.item_id, changes)
        raise TripCollabError(f"未知事件类型: {e.kind}")

    # ---------------- 快照回滚 ----------------

    def rollback_to(self, version: int, actor: str, reason: Optional[str] = None) -> RollbackResult:
        """一键回滚至历史快照：追加补偿事件恢复状态，事件流保持 append-only。

        回滚后，目标版本之后被采纳的提议仍在历史中，其提交人会收到通知。
        """
        if version not in self.snapshots:
            raise SnapshotNotFoundError(f"版本 {version} 没有快照（可用: {sorted(self.snapshots)}）")
        if version == self.version:
            return RollbackResult(version, self.version, [], 0)

        target = self.snapshots[version]
        compensations = self._diff_to_restore(self._state, target)
        affected = [
            p.id
            for p in self.proposals.values()
            if p.status == STATUS_ADOPTED and (p.adopted_version or 0) > version
        ]
        for e in compensations:
            self._apply(
                StreamEvent(
                    next(self._seq), e.kind, e.item_id, e.payload, "__rollback__", next(self._clock),
                    meta={"rollback": True, "target_version": version},
                )
            )
        for pid in affected:
            self.notifications.append(
                Notification(
                    next(self._clock),
                    "rollback_affected",
                    actor,
                    {"proposal_id": pid, "target_version": version, "reason": reason or ""},
                )
            )
        return RollbackResult(version, self.version, affected, len(compensations))

    def _diff_to_restore(self, current: TripState, target: TripState) -> list[ChangeEvent]:
        """计算从 current 恢复到 target 所需的补偿事件（字段级 diff）。"""
        out: list[ChangeEvent] = []
        for item_id, cur_item in current.items.items():
            tgt_item = target.items.get(item_id)
            if tgt_item is None:
                out.append(ChangeEvent(EVENT_DELETED, item_id))
            elif cur_item != tgt_item:
                changes = {
                    k: getattr(tgt_item, k)
                    for k in _ITEM_FIELDS
                    if getattr(cur_item, k) != getattr(tgt_item, k)
                }
                out.append(ChangeEvent(EVENT_UPDATED, item_id, changes))
        for item_id, tgt_item in target.items.items():
            if item_id not in current.items:
                out.append(ChangeEvent(EVENT_CREATED, item_id, item_to_dict(tgt_item)))
        return out

    # ---------------- 内部 ----------------

    def _apply(self, event: StreamEvent) -> None:
        apply_event(self._state, event)
        self.stream.append(event)
        self.snapshots[len(self.stream)] = copy.deepcopy(self._state)

    # ---------------- 序列化（SQLite 持久化 / 反序列化重建） ----------------

    def to_dict(self) -> dict:
        """导出引擎全量状态（append-only 流 + 快照 + 提议 + 通知），用于持久化。"""
        return {
            "trip_id": self.trip_id,
            "stream": [
                {
                    "seq": e.seq,
                    "kind": e.kind,
                    "item_id": e.item_id,
                    "payload": e.payload,
                    "proposal_id": e.proposal_id,
                    "adopted_at": e.adopted_at,
                    "meta": e.meta,
                }
                for e in self.stream
            ],
            "proposals": {pid: _proposal_to_dict(p) for pid, p in self.proposals.items()},
            "snapshots": {
                str(version): {"items": {iid: item_to_dict(item) for iid, item in s.items.items()}}
                for version, s in self.snapshots.items()
            },
            "notifications": [
                {"seq": n.seq, "kind": n.kind, "actor": n.actor, "payload": n.payload}
                for n in self.notifications
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TripEngine":
        """从 to_dict 的产物重建引擎（状态 = 最新快照副本，等价于全量回放）。"""
        engine = cls(trip_id=data.get("trip_id"))
        engine.stream = [StreamEvent(**e) for e in data["stream"]]
        engine.proposals = {pid: _proposal_from_dict(p) for pid, p in data["proposals"].items()}
        engine.snapshots = {
            int(version): TripState(
                items={iid: dict_to_item(item) for iid, item in s["items"].items()}
            )
            for version, s in data["snapshots"].items()
        }
        engine.notifications = [Notification(**n) for n in data["notifications"]]
        clock_values = (
            [n.seq for n in engine.notifications]
            + [e.adopted_at for e in engine.stream]
            + [
                p.created_at
                for p in engine.proposals.values()
                if p.created_at is not None
            ]
            + [
                v
                for p in engine.proposals.values()
                for v in (p.submitted_at, p.adopted_at)
                if v is not None
            ]
        )
        engine._clock = itertools.count((max(clock_values) if clock_values else 0) + 1)
        engine._seq = itertools.count((max((e.seq for e in engine.stream), default=0)) + 1)
        engine._state = copy.deepcopy(engine.snapshots[engine.version])
        return engine


def _proposal_to_dict(p: Proposal) -> dict:
    return {
        "id": p.id,
        "title": p.title,
        "reason": p.reason,
        "created_by": p.created_by,
        "events": [
            {"kind": e.kind, "item_id": e.item_id, "payload": e.payload} for e in p.events
        ],
        "status": p.status,
        "emergency": p.emergency,
        "created_at": p.created_at,
        "submitted_at": p.submitted_at,
        "adopted_at": p.adopted_at,
        "adopted_version": p.adopted_version,
        "reject_reason": p.reject_reason,
        "resolution_note": p.resolution_note,
        "last_report": (
            {"hard": p.last_report.hard, "warnings": p.last_report.warnings}
            if p.last_report
            else None
        ),
    }


def _proposal_from_dict(d: dict) -> Proposal:
    last_report = d.get("last_report")
    return Proposal(
        id=d["id"],
        title=d["title"],
        reason=d["reason"],
        created_by=d["created_by"],
        events=[ChangeEvent(e["kind"], e["item_id"], e.get("payload")) for e in d["events"]],
        status=d["status"],
        emergency=d["emergency"],
        created_at=d["created_at"],
        submitted_at=d["submitted_at"],
        adopted_at=d["adopted_at"],
        adopted_version=d["adopted_version"],
        reject_reason=d["reject_reason"],
        resolution_note=d["resolution_note"],
        last_report=(
            ConflictReport(hard=last_report["hard"], warnings=last_report["warnings"])
            if last_report
            else None
        ),
    )
