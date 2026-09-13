"""快照回滚测试：补偿事件、append-only、影响通知、快照不可变。"""

import pytest

from backend.engine.engine import STATUS_ADOPTED
from backend.engine.errors import SnapshotNotFoundError
from backend.engine.events import EVENT_CREATED, EVENT_DELETED, EVENT_UPDATED, ChangeEvent

from conftest import make_item


def _build_three_versions(engine):
    """构建三个定稿版本：
    v0: 空
    v2: A、B 两个条目（采纳 p1）
    v4: A 改名 + 新增 C（采纳 p2）
    v5: 删除 B（采纳 p3）
    """
    p1 = engine.create_proposal(
        "基线", "r", [
            ChangeEvent(EVENT_CREATED, "a", make_item("a", 1, 1, "A")),
            ChangeEvent(EVENT_CREATED, "b", make_item("b", 1, 2, "B")),
        ], "u1",
    )
    engine.submit(p1.id, "u1")
    engine.adopt(p1.id, actor="admin", confirmed=True)  # v2

    p2 = engine.create_proposal(
        "改A加C", "r", [
            ChangeEvent(EVENT_UPDATED, "a", {"title": "A2"}),
            ChangeEvent(EVENT_CREATED, "c", make_item("c", 2, 1, "C")),
        ], "u1",
    )
    engine.submit(p2.id, "u1")
    engine.adopt(p2.id, actor="admin", confirmed=True)  # v4

    p3 = engine.create_proposal("删B", "r", [ChangeEvent(EVENT_DELETED, "b")], "u2")
    engine.submit(p3.id, "u2")
    engine.adopt(p3.id, actor="admin")  # v5
    return p1, p2, p3


def test_rollback_restores_state_with_compensating_events(engine):
    p1, p2, p3 = _build_three_versions(engine)
    v5 = engine.version
    snap2 = engine.state_at(2)

    result = engine.rollback_to(2, actor="admin", reason="定错酒店")
    assert result.target_version == 2
    assert result.affected_proposals == [p2.id, p3.id]
    assert result.compensating_event_count == 3  # 还原 A、删 C、重建 B
    assert engine.version == v5 + 3

    # 状态精确恢复
    assert engine.state().items == snap2.items
    assert set(engine.state().items) == {"a", "b"}
    assert engine.state().items["a"].title == "A"

    # append-only：原始事件未动，新增补偿事件带标记
    assert len(engine.stream) == 8
    assert all(not e.meta.get("rollback") for e in engine.stream[:5])
    assert all(e.meta.get("rollback") for e in engine.stream[5:])
    assert all(e.meta["target_version"] == 2 for e in engine.stream[5:])


def test_rollback_notifies_affected_proposals(engine):
    p1, p2, p3 = _build_three_versions(engine)
    engine.rollback_to(2, actor="admin")
    affected = {n.payload["proposal_id"] for n in engine.notifications if n.kind == "rollback_affected"}
    assert affected == {p2.id, p3.id}
    # 提议记录仍在历史中（状态不回退）
    assert engine.proposal(p2.id).status == STATUS_ADOPTED
    assert engine.proposal(p3.id).status == STATUS_ADOPTED


def test_rollback_then_continue_adopting(engine):
    _build_three_versions(engine)
    engine.rollback_to(2, actor="admin")
    p4 = engine.create_proposal(
        "改A为A3", "r", [ChangeEvent(EVENT_UPDATED, "a", {"title": "A3"})], "u1"
    )
    engine.submit(p4.id, "u1")
    engine.adopt(p4.id, actor="admin")
    state = engine.state()
    assert state.items["a"].title == "A3"
    assert set(state.items) == {"a", "b"}  # C 保持被回滚，B 已恢复


def test_snapshot_immutable_across_later_adoptions(engine):
    p1, p2, p3 = _build_three_versions(engine)
    snap2 = engine.state_at(2)
    p4 = engine.create_proposal("加D", "r", [ChangeEvent(EVENT_CREATED, "d", make_item("d", 3, 1, "D"))], "u1")
    engine.submit(p4.id, "u1")
    engine.adopt(p4.id, actor="admin")
    # 历史快照不被后续采纳污染
    assert engine.state_at(2).items == snap2.items


def test_rollback_to_unknown_version_raises(engine):
    _build_three_versions(engine)
    with pytest.raises(SnapshotNotFoundError):
        engine.rollback_to(99, actor="admin")


def test_rollback_to_current_version_is_noop(engine):
    p1, p2, p3 = _build_three_versions(engine)
    r = engine.rollback_to(engine.version, actor="admin")
    assert r.compensating_event_count == 0
    assert r.new_version == r.target_version
