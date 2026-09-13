"""提议生命周期基础行为测试。"""

import pytest

from backend.engine.engine import (
    STATUS_ADOPTED,
    STATUS_DRAFT,
    STATUS_PENDING,
    STATUS_REJECTED,
)
from backend.engine.errors import ConfirmationRequiredError, InvalidStatusError, TripCollabError
from backend.engine.events import EVENT_CREATED, EVENT_UPDATED, ChangeEvent

from conftest import make_item


def test_create_proposal_starts_as_draft_and_does_not_pollute_state(engine):
    p = engine.create_proposal(
        "加景点", "路过值得看", [ChangeEvent(EVENT_CREATED, "x", make_item("x", 1, 3, "X 景点"))], "u1"
    )
    assert p.status == STATUS_DRAFT
    assert engine.state().items == {}  # 草稿事件绝不进入定稿
    assert len(engine.stream) == 0


def test_submit_then_reject_keeps_record_and_state_untouched(engine):
    p = engine.create_proposal(
        "换酒店", "评价差", [ChangeEvent(EVENT_CREATED, "x", make_item("x", 1, 1, "X"))], "u1"
    )
    engine.submit(p.id, "u1")
    assert p.status == STATUS_PENDING
    engine.reject(p.id, "admin", "理由不充分")
    assert p.status == STATUS_REJECTED
    assert p.reject_reason == "理由不充分"
    assert engine.state().items == {}
    assert len(engine.stream) == 0


def test_adopt_single_clean_event_needs_no_confirmation(engine):
    p = engine.create_proposal(
        "加景点", "路过值得看", [ChangeEvent(EVENT_CREATED, "x", make_item("x", 1, 3, "X 景点"))], "u1"
    )
    engine.submit(p.id, "u1")
    result = engine.adopt(p.id, actor="admin")
    assert result.merged_event_count == 1
    assert p.status == STATUS_ADOPTED
    assert engine.state().items["x"].title == "X 景点"
    assert len(engine.stream) == 1


def test_merge_multiple_events_requires_confirmation(engine):
    p = engine.create_proposal(
        "加两个景点",
        "充实行程",
        [
            ChangeEvent(EVENT_CREATED, "x", make_item("x", 1, 3, "X")),
            ChangeEvent(EVENT_CREATED, "y", make_item("y", 2, 1, "Y")),
        ],
        "u1",
    )
    engine.submit(p.id, "u1")
    with pytest.raises(ConfirmationRequiredError):
        engine.adopt(p.id, actor="admin")
    result = engine.adopt(p.id, actor="admin", confirmed=True)
    assert result.merged_event_count == 2
    assert set(engine.state().items) == {"x", "y"}


def test_actions_on_wrong_status_raise(engine):
    p = engine.create_proposal(
        "t", "r", [ChangeEvent(EVENT_CREATED, "x", make_item("x", 1, 1, "X"))], "u1"
    )
    # 草稿不可直接采纳/拒绝
    with pytest.raises(InvalidStatusError):
        engine.adopt(p.id, actor="admin")
    with pytest.raises(InvalidStatusError):
        engine.reject(p.id, "admin", "r")
    # 重复提交
    engine.submit(p.id, "u1")
    with pytest.raises(InvalidStatusError):
        engine.submit(p.id, "u1")


def test_proposal_requires_at_least_one_event(engine):
    with pytest.raises(TripCollabError):
        engine.create_proposal("t", "r", [], "u1")


def test_update_event_changes_fields_on_adopt(engine):
    p = engine.create_proposal(
        "改车次", "时间更合适",
        [ChangeEvent(EVENT_UPDATED, "x", {"title": "X 改", "amount": 50.0})],
        "u1",
    )
    # 先建立条目 x
    base = engine.create_proposal(
        "b", "r", [ChangeEvent(EVENT_CREATED, "x", make_item("x", 1, 1, "X"))], "u1"
    )
    engine.submit(base.id, "u1")
    engine.adopt(base.id, actor="admin")
    engine.submit(p.id, "u1")
    engine.adopt(p.id, actor="admin")
    item = engine.state().items["x"]
    assert item.title == "X 改"
    assert item.amount == 50.0
