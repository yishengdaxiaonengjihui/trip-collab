"""临时备选（emergency 提议）测试：提交即采纳、正式化、撤销、冲突记录。"""

import pytest

from backend.engine.engine import STATUS_ADOPTED, STATUS_REVOKED
from backend.engine.errors import InvalidStatusError
from backend.engine.events import EVENT_CREATED, EVENT_DELETED, EVENT_UPDATED, ChangeEvent

from conftest import adopt_base, make_item


def test_emergency_submit_adopts_immediately_with_marker(engine):
    p = engine.create_proposal(
        "景区闭园改去XX公园", "现场应急", [ChangeEvent(EVENT_CREATED, "park", make_item("park", 1, 3, "XX 公园"))], "u1"
    )
    assert p.status != STATUS_ADOPTED  # 提交前仍是草稿
    result = engine.submit_emergency(p.id, actor="u1")
    assert p.status == STATUS_ADOPTED
    assert p.emergency
    assert result.merged_event_count == 1
    assert engine.state().items["park"].title == "XX 公园"
    # 事件带 emergency 标记，全员立即可见
    assert engine.stream[-1].meta.get("emergency") is True


def test_emergency_bypasses_hard_conflict_but_records_warning(engine):
    adopt_base(engine)
    p1 = engine.create_proposal(
        "改酒店", "r", [ChangeEvent(EVENT_UPDATED, "d2_hotel", {"title": "改"})], "u1"
    )
    engine.submit(p1.id, "u1")
    e = engine.create_proposal(
        "紧急删酒店", "现场问题", [ChangeEvent(EVENT_DELETED, "d2_hotel")], "u2"
    )
    result = engine.submit_emergency(e.id, actor="u2")
    # 紧急场景绕过硬冲突拦截，但冲突告警被记录并通知
    assert result.report.hard
    assert e.last_report is not None and e.last_report.hard
    assert "d2_hotel" not in engine.state().items
    emergency_notice = next(n for n in engine.notifications if n.kind == "emergency_applied")
    assert emergency_notice.payload["hard_conflicts"]


def test_emergency_formalize_then_cannot_revoke(engine):
    adopt_base(engine)
    e = engine.create_proposal(
        "临时改酒店", "r", [ChangeEvent(EVENT_UPDATED, "d2_hotel", {"title": "临时民宿"})], "u1"
    )
    engine.submit_emergency(e.id, actor="u1")
    engine.formalize(e.id, actor="admin")
    assert e.emergency is False
    assert e.status == STATUS_ADOPTED
    with pytest.raises(InvalidStatusError):
        engine.revoke(e.id, actor="admin")


def test_emergency_revoke_restores_previous_state(engine):
    adopt_base(engine)  # d1_train, d2_hotel
    e = engine.create_proposal(
        "紧急加景点", "r", [ChangeEvent(EVENT_CREATED, "x", make_item("x", 2, 1, "X"))], "u1"
    )
    engine.submit_emergency(e.id, actor="u1")
    v_before = engine.version
    assert "x" in engine.state().items

    engine.revoke(e.id, actor="admin")
    assert e.status == STATUS_REVOKED
    assert "x" not in engine.state().items
    assert set(engine.state().items) == {"d1_train", "d2_hotel"}
    # append-only：撤销 = 追加补偿事件
    assert engine.stream[-1].meta.get("revoke_of") == e.id
    assert engine.stream[-1].meta.get("rollback") is True
    assert engine.version > v_before


def test_emergency_revoke_restores_original_field_values(engine):
    adopt_base(engine)
    e = engine.create_proposal(
        "紧急换酒店", "r", [ChangeEvent(EVENT_UPDATED, "d2_hotel", {"title": "隔壁民宿"})], "u1"
    )
    engine.submit_emergency(e.id, actor="u1")
    assert engine.state().items["d2_hotel"].title == "隔壁民宿"
    engine.revoke(e.id, actor="admin")
    assert engine.state().items["d2_hotel"].title == "D2 全季酒店"
