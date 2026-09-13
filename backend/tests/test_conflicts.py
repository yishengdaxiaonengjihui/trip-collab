"""冲突判定测试：硬冲突 / 依赖告警 / 采纳时刻判定 / 人工判定放行。"""

import pytest

from backend.engine.engine import STATUS_ADOPTED
from backend.engine.errors import ConfirmationRequiredError, HardConflictError
from backend.engine.events import EVENT_DELETED, EVENT_UPDATED, ChangeEvent

from conftest import adopt_base


def test_hard_conflict_between_two_pending_proposals(engine):
    """多个待审核提议同时修改同一条目 -> 禁止自动合并，强制人工判定。"""
    adopt_base(engine)
    p1 = engine.create_proposal(
        "改酒店标题", "写清楚", [ChangeEvent(EVENT_UPDATED, "d2_hotel", {"title": "D2 全季酒店(高楼层)"})], "u1"
    )
    p2 = engine.create_proposal(
        "改酒店位置", "换顺序", [ChangeEvent(EVENT_UPDATED, "d2_hotel", {"position": 3})], "u2"
    )
    engine.submit(p1.id, "u1")
    engine.submit(p2.id, "u2")
    with pytest.raises(HardConflictError):
        engine.adopt(p1.id, actor="admin")
    # 人工兜底：先拒绝 p2，p1 即可采纳
    engine.reject(p2.id, "admin", "放弃该提议")
    result = engine.adopt(p1.id, actor="admin")
    assert result.merged_event_count == 1
    assert engine.state().items["d2_hotel"].title == "D2 全季酒店(高楼层)"


def test_force_resolves_hard_conflict_with_record(engine):
    """硬冲突下管理员可强制人工判定，并留痕。"""
    adopt_base(engine)
    p1 = engine.create_proposal(
        "改酒店标题", "写清楚", [ChangeEvent(EVENT_UPDATED, "d2_hotel", {"title": "优先采纳"})], "u1"
    )
    p2 = engine.create_proposal(
        "改酒店位置", "换顺序", [ChangeEvent(EVENT_UPDATED, "d2_hotel", {"position": 3})], "u2"
    )
    engine.submit(p1.id, "u1")
    engine.submit(p2.id, "u2")
    with pytest.raises(HardConflictError):
        engine.adopt(p1.id, actor="admin")
    result = engine.adopt(p1.id, actor="admin", force=True, resolution_note="管理员判定优先采纳 p1")
    assert result.merged_event_count == 1
    assert p1.status == STATUS_ADOPTED
    assert "p1" in (p1.resolution_note or "")
    assert p1.last_report.hard  # 冲突记录保留


def test_conflict_detected_at_adopt_time_not_submit_time(engine):
    """采纳时刻冲突判定：提议提交时目标存在，采纳时已被移除 -> 硬冲突。"""
    adopt_base(engine)
    # 正常提议修改 d1_train（提交时刻无冲突）
    p_upd = engine.create_proposal(
        "改车次", "换一趟", [ChangeEvent(EVENT_UPDATED, "d1_train", {"title": "G1002"})], "u1"
    )
    engine.submit(p_upd.id, "u1")
    # 旅途中紧急删除 d1_train（提交即采纳，绕过并发硬冲突，但记录依赖告警）
    e_del = engine.create_proposal(
        "紧急删车次", "车次停运", [ChangeEvent(EVENT_DELETED, "d1_train")], "u2"
    )
    engine.submit_emergency(e_del.id, actor="u2")
    assert "d1_train" not in engine.state().items
    # 到 p_upd 采纳时刻：目标已不存在 -> 硬冲突（提交时无法预知）
    with pytest.raises(HardConflictError):
        engine.adopt(p_upd.id, actor="admin")


def test_dependency_warning_requires_confirmation(engine):
    """隐性依赖：修改被引用的条目（D1 车次）触发依赖告警，需人工复核确认。"""
    adopt_base(engine)
    p = engine.create_proposal(
        "改车次时间", "更合适", [ChangeEvent(EVENT_UPDATED, "d1_train", {"title": "G1002"})], "u1"
    )
    engine.submit(p.id, "u1")
    with pytest.raises(ConfirmationRequiredError):
        engine.adopt(p.id, actor="admin")
    result = engine.adopt(p.id, actor="admin", confirmed=True)
    assert any("d2_hotel" in w and "依赖" in w for w in result.report.warnings)
    assert engine.state().items["d1_train"].title == "G1002"
